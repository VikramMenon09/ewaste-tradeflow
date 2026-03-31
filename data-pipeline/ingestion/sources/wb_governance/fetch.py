"""
World Bank Governance Indicators API client.

API: World Bank Data API v2 (https://datahelpdesk.worldbank.org/knowledgebase/articles/898581)
No API key required. Free, open access.

Indicators fetched:
  RL.EST  — Rule of Law Estimate          (-2.5 to +2.5)
  GE.EST  — Government Effectiveness Est. (-2.5 to +2.5)
  CC.EST  — Control of Corruption Est.    (-2.5 to +2.5)

These are the three WGI indicators most correlated with informal e-waste
processing rates in the academic literature (Nnorom & Osibanjo 2008;
Baldé et al. 2017). The composite (average) feeds into the PRS enforcement
score component.

API response format:
  JSON: [ metadata_dict, [ {country: {id, value}, indicator: {...}, value, date}, ... ] ]
  Pages: "page" and "pages" fields in metadata. Default page size = 50; we use 300.
"""

import logging
import time
from typing import Iterator

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

WB_API_BASE = "https://api.worldbank.org/v2"

# The three governance indicators to fetch
GOVERNANCE_INDICATORS = ["RL.EST", "GE.EST", "CC.EST"]

# Page size for WBI API (max 1000; 300 comfortably covers all countries)
PAGE_SIZE = 300

# Request timeout in seconds
REQUEST_TIMEOUT = 30


class WbApiError(Exception):
    """Raised when the World Bank API returns an unexpected error response."""
    pass


class WbGovernanceClient:
    """
    Client for the World Bank Governance Indicators (WGI) API.

    Fetches Rule of Law, Government Effectiveness, and Control of Corruption
    for all countries in a given year. Handles WBI pagination transparently.

    Usage:
        client = WbGovernanceClient()
        df = client.fetch_governance_indicators(year=2021)
        # df has raw WBI JSON fields; pass to parse.normalize() before upload
    """

    def __init__(self, max_retries: int = 4):
        self.session = self._build_session(max_retries)

    def _build_session(self, max_retries: int) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=max_retries,
            backoff_factor=1.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.headers.update({
            "Accept": "application/json",
            "User-Agent": "EWasteTradeFlow/1.0 (research project; contact via GitHub)",
        })
        return session

    def fetch_governance_indicators(self, year: int) -> "pd.DataFrame":
        """
        Fetch all three governance indicators for all countries for a given year.

        The WBI API is queried once per indicator. Results are merged by country
        into a single wide-format DataFrame (one row per country).

        Args:
            year: The data year to fetch (e.g. 2021). Note: WBI governance data
                  is typically available with a 1-2 year lag.

        Returns:
            Wide-format DataFrame with columns:
              country_id (ISO2), country_name, year,
              rl_est, ge_est, cc_est (raw WBI values or NaN)
            Returns empty DataFrame if no data found for the year.
        """
        import pandas as pd

        all_indicator_dfs = {}

        for indicator in GOVERNANCE_INDICATORS:
            records = list(self._fetch_indicator_all_pages(indicator, year))
            if records:
                indicator_df = pd.DataFrame(records)
                all_indicator_dfs[indicator] = indicator_df
            else:
                logger.warning("WBI: no records returned for %s year=%d", indicator, year)

        if not all_indicator_dfs:
            logger.info("WBI: no governance data for year=%d", year)
            return pd.DataFrame()

        # Build a base DataFrame with all countries from whichever indicator
        # returned the most records (they should all be the same countries)
        base_indicator = max(all_indicator_dfs, key=lambda k: len(all_indicator_dfs[k]))
        base_df = all_indicator_dfs[base_indicator][["country_id", "country_name", "year"]].copy()
        base_df = base_df.drop_duplicates(subset=["country_id"])

        # Merge each indicator as a new column
        for indicator, ind_df in all_indicator_dfs.items():
            col_name = indicator.replace(".", "_").lower()  # RL.EST -> rl_est
            values = ind_df[["country_id", "value"]].rename(columns={"value": col_name})
            base_df = base_df.merge(values, on="country_id", how="left")

        return base_df.reset_index(drop=True)

    def _fetch_indicator_all_pages(
        self, indicator: str, year: int
    ) -> Iterator[dict]:
        """
        Fetch all pages for a single indicator and yield individual country records.

        Handles WBI's page-based pagination. The WBI API returns metadata in
        the first element of the response array and data records in the second.

        Args:
            indicator: WBI indicator code (e.g. "RL.EST")
            year: Data year

        Yields:
            Dicts with keys: country_id, country_name, indicator, year, value
        """
        page = 1
        total_pages = None

        while True:
            url = f"{WB_API_BASE}/country/all/indicator/{indicator}"
            params = {
                "date": str(year),
                "format": "json",
                "per_page": str(PAGE_SIZE),
                "page": str(page),
                "mrv": "1",   # Most recent value — helps when year has sparse coverage
            }

            logger.debug("WBI fetch: indicator=%s year=%d page=%d", indicator, year, page)

            response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)

            if response.status_code == 404:
                logger.info("WBI: indicator %s not found (HTTP 404)", indicator)
                return

            if response.status_code != 200:
                raise WbApiError(
                    f"WBI API returned HTTP {response.status_code} for "
                    f"indicator={indicator} year={year} page={page}. "
                    f"Body: {response.text[:500]}"
                )

            try:
                payload = response.json()
            except ValueError as exc:
                raise WbApiError(
                    f"WBI API returned non-JSON for {indicator}/{year}: {exc}"
                ) from exc

            # WBI response: [metadata, [records...]]
            if not isinstance(payload, list) or len(payload) < 2:
                logger.warning("WBI: unexpected response structure for %s year=%d", indicator, year)
                return

            metadata = payload[0]
            records = payload[1]

            if records is None:
                logger.info("WBI: null records for %s year=%d (no data for this year)", indicator, year)
                return

            # Parse total pages from metadata on first request
            if total_pages is None:
                total_pages = int(metadata.get("pages", 1))
                total_records = int(metadata.get("total", 0))
                logger.info(
                    "WBI: indicator=%s year=%d total_records=%d pages=%d",
                    indicator, year, total_records, total_pages,
                )

            for record in records:
                country = record.get("country", {})
                country_id = country.get("id", "")
                country_name = country.get("value", "")
                value_raw = record.get("value")

                # Skip aggregate regions (WBI uses 2-letter codes for countries
                # and longer codes like "1W", "EAP", "SSA" for aggregates)
                if len(country_id) != 2:
                    continue

                yield {
                    "country_id": country_id,
                    "country_name": country_name,
                    "indicator": indicator,
                    "year": year,
                    "value": float(value_raw) if value_raw is not None else None,
                }

            # Check if we need to fetch more pages
            if page >= total_pages:
                break

            page += 1
            # Small polite delay between pages
            time.sleep(0.3)
