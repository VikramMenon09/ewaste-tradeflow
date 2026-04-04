"""
Basel Convention party status — Excel/CSV parser.

Reads the file returned by BaselClient.get_data_path() and normalizes it
to a standard DataFrame.

Supported input formats:
  - CSV with headers: Country, ISO3, Is_Party, Ban_Amendment, Ratification_Year
  - Excel (xlsx) from the UNEP Basel Secretariat website

Output columns:
  iso3, country_name, is_party, ban_amendment_ratified,
  ratification_year, ban_ratification_year
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Known column name spellings → internal names
_COLUMN_ALIASES: dict[str, str] = {
    # ISO3
    "ISO3": "iso3",
    "ISO 3": "iso3",
    "Code": "iso3",
    # Country name
    "Country": "country_name",
    "Country or Area": "country_name",
    "Party": "country_name",
    # Is party / ratified Convention
    "Is_Party": "is_party",
    "Party to Convention": "is_party",
    "Status": "is_party",
    "Ratification": "is_party",
    # Ban Amendment ratified
    "Ban_Amendment": "ban_amendment_ratified",
    "Ban Amendment": "ban_amendment_ratified",
    "Annex VII": "ban_amendment_ratified",
    # Ratification year (Convention)
    "Ratification_Year": "ratification_year",
    "Year of Ratification": "ratification_year",
    "Date of Ratification": "ratification_year",
    # Ban Amendment ratification year
    "Ban_Ratification_Year": "ban_ratification_year",
    "Ban Amendment Year": "ban_ratification_year",
}

_TRUTHY = {"yes", "y", "1", "true", "x", "✓", "✔", "ratified", "acceded", "party"}
_MISSING = {"-", "n/a", "n.a.", "", "none", "–", "—"}


def normalize(data_path: Path) -> "pd.DataFrame":
    """Read and normalize a Basel party status file.

    Args:
        data_path: Path to a .csv or .xlsx file.

    Returns:
        DataFrame with columns:
          iso3, country_name, is_party, ban_amendment_ratified,
          ratification_year, ban_ratification_year
    """
    import pandas as pd

    suffix = data_path.suffix.lower()
    if suffix in (".xlsx", ".xls"):
        df = _read_excel(data_path)
    elif suffix == ".csv":
        df = pd.read_csv(str(data_path))
    else:
        raise ValueError(f"Basel: unsupported file format '{suffix}'. Use .csv or .xlsx.")

    # Strip column whitespace
    df.columns = [str(c).strip() for c in df.columns]

    # Rename to internal names
    rename_map = {col: alias for col, alias in _COLUMN_ALIASES.items() if col in df.columns}
    df = df.rename(columns=rename_map)

    # Ensure required columns exist
    if "iso3" not in df.columns:
        raise ValueError(
            "Basel: 'iso3' column not found after alias mapping. "
            f"Available columns: {list(df.columns)}"
        )
    if "is_party" not in df.columns:
        # If we only have an ISO3 list, assume all rows are parties
        logger.warning("Basel: 'is_party' column not found — assuming all rows are Convention Parties")
        df["is_party"] = True

    # Fill missing optional columns
    for col in ["country_name", "ban_amendment_ratified", "ratification_year", "ban_ratification_year"]:
        if col not in df.columns:
            df[col] = None

    # Normalize ISO3
    df["iso3"] = df["iso3"].apply(lambda v: str(v).strip().upper() if _is_present(v) else None)
    df = df[df["iso3"].notna() & (df["iso3"].str.len() == 3)]

    # Normalize boolean columns
    df["is_party"] = df["is_party"].apply(_to_bool)
    df["ban_amendment_ratified"] = df["ban_amendment_ratified"].apply(_to_bool)

    # Normalize year columns
    df["ratification_year"] = df["ratification_year"].apply(_extract_year)
    df["ban_ratification_year"] = df["ban_ratification_year"].apply(_extract_year)

    df["country_name"] = df["country_name"].fillna("").astype(str).str.strip()

    result = df[[
        "iso3", "country_name", "is_party", "ban_amendment_ratified",
        "ratification_year", "ban_ratification_year",
    ]].drop_duplicates(subset=["iso3"]).reset_index(drop=True)

    parties = result["is_party"].sum()
    ban = result["ban_amendment_ratified"].sum()
    logger.info(
        "Basel: %d countries parsed — %d Convention Parties, %d Ban Amendment ratifiers",
        len(result), parties, ban,
    )
    return result


# ── Private helpers ───────────────────────────────────────────────────────────

def _read_excel(path: Path) -> "pd.DataFrame":
    """Read the first sheet of an Excel file, detecting the header row."""
    import pandas as pd

    xl = pd.ExcelFile(str(path))
    raw = xl.parse(xl.sheet_names[0], header=None)

    # Find the header row
    known = {k.lower() for k in _COLUMN_ALIASES}
    for idx, row in raw.iterrows():
        row_strs = {str(v).strip().lower() for v in row if _is_present(v)}
        if row_strs & known:
            return xl.parse(xl.sheet_names[0], header=int(idx))

    # Fallback: assume row 0 is the header
    return xl.parse(xl.sheet_names[0], header=0)


def _to_bool(value) -> bool:
    """Interpret a cell value as True/False."""
    import pandas as pd
    if pd.isna(value):
        return False
    s = str(value).strip().lower()
    if s in _MISSING:
        return False
    return s in _TRUTHY


def _is_present(value) -> bool:
    """Return True if value is not NaN/None and not a missing marker string."""
    import pandas as pd
    if pd.isna(value):
        return False
    return str(value).strip().lower() not in _MISSING


def _extract_year(value) -> Optional[int]:
    """Extract a 4-digit year from a cell value (handles dates and strings)."""
    import pandas as pd
    if pd.isna(value) or str(value).strip().lower() in _MISSING:
        return None
    # datetime objects
    if hasattr(value, "year"):
        return int(value.year)
    # String — find first 4-digit number
    import re
    match = re.search(r"\b(19|20)\d{2}\b", str(value))
    return int(match.group(0)) if match else None
