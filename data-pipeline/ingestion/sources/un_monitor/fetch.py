"""
UN Global E-Waste Monitor — file downloader.

The UN Monitor publishes Excel (.xlsx) files.  The URL is configured via
the UN_MONITOR_EXCEL_URL environment variable.  Files can also be placed
locally (UN_MONITOR_LOCAL_PATH) to avoid downloading on every run.

Typical usage:
    client = UNMonitorClient()
    local_path = client.download(year=2020)
    # Pass local_path to parse.normalize()
"""

from __future__ import annotations

import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# Environment variable overrides
_URL_ENV = "UN_MONITOR_EXCEL_URL"
_LOCAL_PATH_ENV = "UN_MONITOR_LOCAL_PATH"

# Public UN/UNU-SCYCLE Excel links (update when new editions are published)
# See: https://ewastemonitor.info/gem-2024/
_DEFAULT_URLS: dict[int, str] = {
    2024: "https://ewastemonitor.info/wp-content/uploads/2024/03/GEM_2024_Country-Data.xlsx",
    2020: "https://ewastemonitor.info/wp-content/uploads/2020/11/GEM_2020_def_july1_low.xlsx",
}

_REQUEST_TIMEOUT = 60  # seconds


class UNMonitorClient:
    """Downloads the UN Global E-Waste Monitor Excel file."""

    def __init__(self, max_retries: int = 3) -> None:
        self.session = self._build_session(max_retries)

    def _build_session(self, max_retries: int) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=max_retries,
            backoff_factor=2.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        session.mount("https://", HTTPAdapter(max_retries=retry))
        session.headers.update({
            "User-Agent": "EWasteTradeFlow/1.0 (research; github.com/your-org/ewaste-tradeflow)",
        })
        return session

    def download(self, year: Optional[int] = None, dest_dir: Optional[str] = None) -> Path:
        """Download the UN Monitor Excel file and return the local path.

        Checks UN_MONITOR_LOCAL_PATH first (skip download if file exists).
        Falls back to UN_MONITOR_EXCEL_URL or the built-in URL for `year`.

        Args:
            year: Edition year (2020, 2024, …). Used to select the default URL.
            dest_dir: Directory to save the file.  Defaults to a temp directory.

        Returns:
            Path to the downloaded (or pre-existing) Excel file.
        """
        # 1. Check for a pre-placed local file
        local_override = os.environ.get(_LOCAL_PATH_ENV)
        if local_override:
            path = Path(local_override)
            if path.exists():
                logger.info("UN Monitor: using local file %s", path)
                return path
            logger.warning("UN Monitor: %s=%s does not exist, falling back to download", _LOCAL_PATH_ENV, local_override)

        # 2. Determine download URL
        url = os.environ.get(_URL_ENV)
        if not url:
            if year and year in _DEFAULT_URLS:
                url = _DEFAULT_URLS[year]
            else:
                # Use the most recent known edition
                most_recent = max(_DEFAULT_URLS.keys())
                url = _DEFAULT_URLS[most_recent]
                logger.info("UN Monitor: year=%s not in known URLs, using %d edition", year, most_recent)

        # 3. Download
        dest = Path(dest_dir) if dest_dir else Path(tempfile.mkdtemp())
        dest.mkdir(parents=True, exist_ok=True)
        filename = f"un_monitor_{year or 'latest'}.xlsx"
        file_path = dest / filename

        logger.info("UN Monitor: downloading from %s → %s", url, file_path)
        start = time.monotonic()
        response = self.session.get(url, timeout=_REQUEST_TIMEOUT, stream=True)
        response.raise_for_status()

        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        elapsed = time.monotonic() - start
        size_kb = file_path.stat().st_size / 1024
        logger.info("UN Monitor: downloaded %.1f KB in %.1fs", size_kb, elapsed)
        return file_path
