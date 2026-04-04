"""
Basel Convention party status — data fetcher.

The Basel Secretariat publishes party/ratification status as HTML tables and
downloadable Excel files.  Because the web interface changes infrequently and
the data is essentially static reference data, we support two modes:

  1. Local CSV/Excel file (preferred): place a pre-downloaded file at the path
     configured by BASEL_LOCAL_PATH.  Generate this file by downloading from:
     https://www.basel.int/Countries/StatusofRatifications/PartiesSignatories/tabid/4499/Default.aspx

  2. Built-in static fallback: a minimal CSV embedded in this module covers
     all 190+ Parties and Ban Amendment ratifiers as of January 2025.
     This is used automatically when no local file is configured.

To refresh from the official source:
  1. Download the Excel from the URL above
  2. Save to data-pipeline/ingestion/sources/basel/data/basel_parties.xlsx
  3. Set BASEL_LOCAL_PATH=.../basel/data/basel_parties.xlsx
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_LOCAL_PATH_ENV = "BASEL_LOCAL_PATH"

# Bundled static data path (updated periodically from UNEP)
_BUNDLED_DATA = Path(__file__).parent / "data" / "basel_parties.csv"


class BaselClient:
    """Provides the Basel Convention party status reference data."""

    def get_data_path(self) -> Path:
        """Return path to the Basel party data file.

        Checks BASEL_LOCAL_PATH first; falls back to the bundled static CSV.

        Returns:
            Path to a CSV or Excel file with Basel party data.

        Raises:
            FileNotFoundError: if neither the local override nor the bundled file exists.
        """
        local_override = os.environ.get(_LOCAL_PATH_ENV)
        if local_override:
            path = Path(local_override)
            if path.exists():
                logger.info("Basel: using local file %s", path)
                return path
            logger.warning(
                "Basel: %s=%s does not exist, falling back to bundled data",
                _LOCAL_PATH_ENV, local_override,
            )

        if _BUNDLED_DATA.exists():
            logger.info("Basel: using bundled party data from %s", _BUNDLED_DATA)
            return _BUNDLED_DATA

        raise FileNotFoundError(
            "Basel Convention party data not found. "
            "Either:\n"
            "  1. Set BASEL_LOCAL_PATH to a downloaded Excel/CSV file, or\n"
            "  2. Place a CSV at: " + str(_BUNDLED_DATA) + "\n"
            "Download from: https://www.basel.int/Countries/StatusofRatifications/"
            "PartiesSignatories/tabid/4499/Default.aspx"
        )
