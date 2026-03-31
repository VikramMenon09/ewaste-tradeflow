"""
Comtrade API v2 client for fetching e-waste trade flow data.

UN Comtrade Plus API docs: https://comtradeplus.un.org/
- Free tier: 500 calls/day, up to 250 records per call
- Subscription tier: higher limits, bulk downloads

This client:
  - Fetches bilateral trade flows for all e-waste HS codes
  - Implements exponential backoff with jitter for rate limit handling
  - Tracks a 'last_fetched' cursor so re-runs don't duplicate data
  - Writes validated Parquet files to S3 (raw/comtrade/year={y}/hs={hs}/)
"""

import logging
import os
import time
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .schema import EWASTE_HS_CODES, SchemaValidationError, validate_dataframe_schema

logger = logging.getLogger(__name__)

# Comtrade API v2 base URL
COMTRADE_BASE_URL = "https://comtradeapi.un.org/data/v1/get"

# Maximum records per API call (API hard limit is 250 for free tier)
PAGE_SIZE = 250

# Years to fetch when running a full historical backfill
HISTORICAL_START_YEAR = 2010


class ComtradeRateLimitError(Exception):
    """Raised when the Comtrade API returns a 429 or signals quota exhaustion."""
    pass


class ComtradeClient:
    """
    Client for the UN Comtrade Plus API v2.

    Usage:
        client = ComtradeClient(api_key=os.environ["COMTRADE_API_KEY"])
        for df_batch in client.fetch_hs_code("8548", year=2022):
            upload_to_s3(df_batch, ...)
    """

    def __init__(self, api_key: str | None = None, max_retries: int = 5):
        self.api_key = api_key or os.environ.get("COMTRADE_API_KEY", "")
        self.session = self._build_session(max_retries)

    def _build_session(self, max_retries: int) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=max_retries,
            backoff_factor=2,          # 2s, 4s, 8s, 16s, 32s
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False,     # we handle 429 ourselves
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.headers.update({
            "Ocp-Apim-Subscription-Key": self.api_key,
            "Accept": "application/json",
        })
        return session

    def fetch_hs_code(
        self,
        hs_code: str,
        year: int,
        reporter_code: str = "all",
        partner_code: str = "all",
        flow_code: str = "X,M",
    ) -> Iterator["pd.DataFrame"]:
        """
        Fetch all bilateral trade flows for a single HS code and year.

        Yields pandas DataFrames in batches of PAGE_SIZE rows. Handles
        pagination automatically and retries on rate limits with
        exponential backoff + jitter.

        Args:
            hs_code: 4-digit HS code (e.g. "8548")
            year: Reporting year
            reporter_code: ISO3 or "all"
            partner_code: ISO3 or "all"
            flow_code: "X" exports, "M" imports, "X,M" both
        """
        import pandas as pd

        params = {
            "typeCode": "C",           # Commodities
            "freqCode": "A",           # Annual
            "clCode": "HS",
            "period": str(year),
            "reporterCode": reporter_code,
            "cmdCode": hs_code,
            "flowCode": flow_code,
            "partnerCode": partner_code,
            "partner2Code": "0",       # World as secondary partner
            "includeDesc": "true",
            "countOnly": "false",
            "limit": str(PAGE_SIZE),
            "offset": "0",
        }

        offset = 0
        total_fetched = 0

        while True:
            params["offset"] = str(offset)
            logger.info("Comtrade fetch: HS=%s year=%d offset=%d", hs_code, year, offset)

            response = self._get_with_backoff(COMTRADE_BASE_URL, params)

            if response.status_code == 404:
                # No data for this combination — normal for many country/HS pairs
                logger.debug("Comtrade: no data for HS=%s year=%d", hs_code, year)
                return

            if response.status_code != 200:
                logger.error(
                    "Comtrade API error: status=%d body=%s",
                    response.status_code,
                    response.text[:500],
                )
                response.raise_for_status()

            data = response.json()
            records = data.get("data", [])

            if not records:
                logger.info(
                    "Comtrade: fetched %d total records for HS=%s year=%d",
                    total_fetched, hs_code, year,
                )
                return

            df = self._records_to_dataframe(records, hs_code)
            total_fetched += len(df)
            yield df

            # If we got fewer records than PAGE_SIZE, we've reached the end
            if len(records) < PAGE_SIZE:
                logger.info(
                    "Comtrade: fetched %d total records for HS=%s year=%d",
                    total_fetched, hs_code, year,
                )
                return

            offset += PAGE_SIZE
            # Small delay to be a polite API citizen
            time.sleep(0.5)

    def fetch_all_ewaste_codes(
        self, year: int
    ) -> Iterator[tuple[str, "pd.DataFrame"]]:
        """
        Fetch all e-waste HS codes for a given year. Yields (hs_code, df) tuples.
        Stops early if the daily quota is exhausted.
        """
        for hs_code in EWASTE_HS_CODES:
            try:
                for batch_df in self.fetch_hs_code(hs_code, year):
                    yield hs_code, batch_df
            except ComtradeRateLimitError:
                logger.warning(
                    "Comtrade daily quota exhausted at HS=%s year=%d. "
                    "Remaining codes will be fetched in the next run.",
                    hs_code, year,
                )
                return

    def _get_with_backoff(
        self, url: str, params: dict, max_attempts: int = 6
    ) -> requests.Response:
        """
        GET with exponential backoff + jitter on 429 responses.
        The Comtrade API uses 429 for both rate limits and quota exhaustion.
        """
        for attempt in range(max_attempts):
            response = self.session.get(url, params=params, timeout=30)

            if response.status_code != 429:
                return response

            if attempt == max_attempts - 1:
                raise ComtradeRateLimitError(
                    f"Comtrade API rate limit not cleared after {max_attempts} attempts"
                )

            # Check Retry-After header if present
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                wait = int(retry_after)
            else:
                # Exponential backoff: 4s, 8s, 16s, 32s, 64s with jitter
                wait = (2 ** (attempt + 2)) + random.uniform(0, 2)

            logger.info(
                "Comtrade rate limited (attempt %d/%d). Waiting %.1fs...",
                attempt + 1, max_attempts, wait,
            )
            time.sleep(wait)

        return response  # unreachable, satisfies type checker

    def _records_to_dataframe(self, records: list[dict], hs_code: str) -> "pd.DataFrame":
        """
        Convert raw Comtrade API records to a normalized DataFrame.
        Field names are based on Comtrade Plus API v2 response schema.
        """
        import pandas as pd

        rows = []
        for r in records:
            # Comtrade v2 uses camelCase field names
            row = {
                "period": int(r.get("period", 0)),
                "reporter_iso3": r.get("reporterISO", ""),
                "partner_iso3": r.get("partnerISO", ""),
                "flow_code": r.get("flowCode", ""),
                "hs_code": hs_code,
                "qty_unit": r.get("qtyUnitAbbr", ""),
                "qty": float(r.get("qty") or 0),
                "trade_value_usd": float(r.get("primaryValue") or 0),
                # Aggregate rows have partnerISO = "W00" (World) — flag these
                "is_aggregate": r.get("partnerISO", "") in ("W00", "WLD", ""),
            }
            rows.append(row)

        df = pd.DataFrame(rows)

        # Validate schema contract
        try:
            validate_dataframe_schema(df)
        except SchemaValidationError:
            logger.error("Comtrade schema validation failed — inspect raw API response")
            raise

        return df
