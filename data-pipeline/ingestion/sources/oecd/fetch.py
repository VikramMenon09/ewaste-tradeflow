"""
OECD.Stat SDMX-JSON API client for transboundary hazardous waste movements.

Dataset: ENV_WASTE_TRAN (Transboundary movements of hazardous waste)
API docs: https://data.oecd.org/api/sdmx-json-documentation/

Key characteristics:
  - No API key required (open access)
  - Returns SDMX-JSON format (different from standard REST JSON)
  - Country codes are OECD's own scheme, NOT ISO3 — crosswalk is in parse.py
  - Rate limits are generous but still need polite backoff on 429/503
  - Data coverage: ~38 OECD members + some partner countries
  - Annual frequency; typical lag is 2-3 years behind current year
"""

import logging
import time
import random
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# OECD SDMX-JSON base URL
OECD_SDMX_BASE = "https://stats.oecd.org/SDMX-JSON/data"

# Dataset identifier for transboundary hazardous waste movements
DATASET_ID = "ENV_WASTE_TRAN"

# Request timeout in seconds
REQUEST_TIMEOUT = 60


class OecdApiError(Exception):
    """Raised when the OECD API returns an unexpected non-200 response."""
    pass


class OecdClient:
    """
    Client for the OECD.Stat SDMX-JSON API (ENV_WASTE_TRAN dataset).

    The OECD SDMX-JSON response is structured as a multi-dimensional
    data cube rather than a flat record array. The parse.py module handles
    the dimensional unpacking into a flat pandas DataFrame.

    Usage:
        client = OecdClient()
        df = client.fetch_transboundary_flows(year=2020)
        # df has raw OECD-format columns; pass to parse.normalize() before upload
    """

    def __init__(self, max_retries: int = 5):
        self.session = self._build_session(max_retries)

    def _build_session(self, max_retries: int) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=max_retries,
            backoff_factor=2,           # 2s, 4s, 8s, 16s, 32s
            status_forcelist=[500, 502, 504],   # 503 handled manually below
            allowed_methods=["GET"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.headers.update({
            "Accept": "application/vnd.sdmx.data+json;version=1.0",
            "User-Agent": "EWasteTradeFlow/1.0 (research project; contact via GitHub)",
        })
        return session

    def fetch_transboundary_flows(self, year: int) -> "pd.DataFrame":
        """
        Fetch all transboundary waste movements for a given year.

        Queries the ENV_WASTE_TRAN dataset for all reporter countries,
        all partner countries, and all waste categories for the specified year.
        Returns the raw SDMX-JSON parsed into a flat DataFrame (OECD country
        codes, not ISO3 — call parse.normalize() before using downstream).

        Args:
            year: The reporting year to fetch (e.g. 2020)

        Returns:
            DataFrame with columns: oecd_exporter_code, oecd_importer_code,
            oecd_waste_code, year, volume_tonnes
            Returns empty DataFrame if no data available for the year.

        Raises:
            OecdApiError: on persistent HTTP errors
        """
        import pandas as pd

        # OECD SDMX-JSON filter format: dataset/filter_expression
        # "all" fetches all members on a dimension
        # Dimensions order for ENV_WASTE_TRAN: REPORTER.PARTNER.WASTE.YEAR
        filter_expr = f"all.all.all.{year}"
        url = f"{OECD_SDMX_BASE}/{DATASET_ID}/{filter_expr}/all"

        params = {
            "contentType": "application/vnd.sdmx.data+json",
            "detail": "dataonly",
            "startPeriod": str(year),
            "endPeriod": str(year),
        }

        logger.info("OECD fetch: dataset=%s year=%d", DATASET_ID, year)

        response = self._get_with_backoff(url, params)

        if response.status_code == 404:
            logger.info("OECD: no data found for year=%d (HTTP 404)", year)
            return pd.DataFrame()

        if response.status_code != 200:
            raise OecdApiError(
                f"OECD API returned HTTP {response.status_code} for year={year}. "
                f"Body: {response.text[:500]}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise OecdApiError(
                f"OECD API returned non-JSON response for year={year}: {exc}"
            ) from exc

        return self._parse_sdmx_json(payload, year)

    def fetch_all_years(
        self, start_year: int, end_year: int
    ) -> "pd.DataFrame":
        """
        Fetch all available years in [start_year, end_year] inclusive.

        Concatenates results across years. Skips years with no data silently.

        Args:
            start_year: First year to fetch (inclusive)
            end_year: Last year to fetch (inclusive)

        Returns:
            Concatenated DataFrame across all years. May be empty.
        """
        import pandas as pd

        frames = []
        for yr in range(start_year, end_year + 1):
            df = self.fetch_transboundary_flows(yr)
            if len(df) > 0:
                frames.append(df)
            # Polite delay between years to avoid hammering the OECD servers
            time.sleep(1.0)

        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True)

    def _get_with_backoff(
        self, url: str, params: dict, max_attempts: int = 6
    ) -> requests.Response:
        """
        GET with exponential backoff + jitter on 429 and 503 responses.

        The OECD API occasionally returns 503 during maintenance windows;
        unlike urllib3's built-in retry (which handles 503), we also need
        to handle 429 (rate limit) manually with header-respecting logic.
        """
        for attempt in range(max_attempts):
            try:
                response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            except requests.exceptions.Timeout:
                logger.warning(
                    "OECD request timed out (attempt %d/%d)", attempt + 1, max_attempts
                )
                if attempt == max_attempts - 1:
                    raise
                time.sleep(2 ** (attempt + 1))
                continue

            if response.status_code not in (429, 503):
                return response

            if attempt == max_attempts - 1:
                # Return the response and let the caller handle the non-200
                return response

            # Respect Retry-After header if present; otherwise exponential backoff
            retry_after = response.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                wait = int(retry_after)
            else:
                wait = (2 ** (attempt + 2)) + random.uniform(0, 3)

            logger.info(
                "OECD API %d (attempt %d/%d). Waiting %.1fs...",
                response.status_code, attempt + 1, max_attempts, wait,
            )
            time.sleep(wait)

        return response  # unreachable; satisfies type checker

    def _parse_sdmx_json(self, payload: dict, year: int) -> "pd.DataFrame":
        """
        Parse OECD SDMX-JSON data structure into a flat DataFrame.

        SDMX-JSON structure:
          payload["dataSets"][0]["series"] = {
            "0:1:2": {                           <- dimension indices joined by ":"
              "observations": { "0": [value] }   <- time series observations
            }
          }
          payload["structure"]["dimensions"]["series"] = [
            {"id": "REPORTER", "values": [...]},
            {"id": "PARTNER", "values": [...]},
            {"id": "WASTE", "values": [...]},
          ]
          payload["structure"]["dimensions"]["observation"] = [
            {"id": "TIME_PERIOD", "values": [{"id": "2020"}]},
          ]

        Returns flat DataFrame with raw OECD dimension codes (not ISO3).
        """
        import pandas as pd

        try:
            datasets = payload.get("dataSets", [])
            if not datasets:
                logger.info("OECD: empty dataSets in SDMX-JSON response for year=%d", year)
                return pd.DataFrame()

            series_data = datasets[0].get("series", {})
            if not series_data:
                logger.info("OECD: no series data for year=%d", year)
                return pd.DataFrame()

            structure = payload["structure"]["dimensions"]
            series_dims = structure["series"]    # list of dimension descriptors
            obs_dims = structure.get("observation", [])

            # Build lookup: dimension index → list of value dicts
            dim_values = [dim["values"] for dim in series_dims]

            rows = []
            for key, series_obj in series_data.items():
                # key is "0:1:2" — indices into each dimension's values list
                dim_indices = [int(i) for i in key.split(":")]

                # Map dimension indices to their string codes
                dim_codes = {}
                for dim_pos, idx in enumerate(dim_indices):
                    dim_id = series_dims[dim_pos]["id"]
                    dim_code = dim_values[dim_pos][idx].get("id", "")
                    dim_codes[dim_id] = dim_code

                observations = series_obj.get("observations", {})
                for obs_idx_str, obs_vals in observations.items():
                    # obs_vals is [value, status, ...] — value is first element
                    value = obs_vals[0] if obs_vals else None
                    if value is None:
                        continue

                    row = {
                        "oecd_reporter_code": dim_codes.get("REPORTER", ""),
                        "oecd_partner_code": dim_codes.get("PARTNER", ""),
                        "oecd_waste_code": dim_codes.get("WASTE", dim_codes.get("HAZARD_TYPE", "")),
                        "year": year,
                        # OECD reports in tonnes (metric tons)
                        "volume_tonnes": float(value),
                    }
                    rows.append(row)

        except (KeyError, IndexError, TypeError, ValueError) as exc:
            logger.error(
                "OECD SDMX-JSON parse error for year=%d: %s. "
                "The API response structure may have changed.",
                year, exc,
            )
            raise OecdApiError(
                f"Failed to parse OECD SDMX-JSON for year={year}: {exc}"
            ) from exc

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        logger.info(
            "OECD parsed %d flow records for year=%d", len(df), year
        )
        return df
