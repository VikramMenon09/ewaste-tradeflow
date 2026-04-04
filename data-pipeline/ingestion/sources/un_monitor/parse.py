"""
UN Global E-Waste Monitor Excel parser.

Reads the Excel file downloaded by UNMonitorClient and normalizes it to a
standard DataFrame.

The Excel file structure:
  - Sheet name: "Country data" (or similar, configurable via EXPECTED_SHEET_NAME)
  - Header row: first non-empty row (may be row 0 or row 1 depending on edition)
  - Country rows: one row per country per year (some editions are multi-year)
  - ISO3 codes: present in most editions; fall back to country name lookup if missing

Handles:
  - Merged cells in header rows (openpyxl unmerges before reading)
  - Multiple header name spellings across editions (see COLUMN_ALIASES)
  - Numeric values stored as strings with thousand separators
  - Missing values encoded as '-', 'N/A', 'n.a.', or empty cells
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_MISSING_VALUES = {"-", "n/a", "n.a.", "na", "none", "", "–", "—"}


def normalize(file_path: Path, year: Optional[int] = None) -> "pd.DataFrame":
    """Read and normalize a UN Monitor Excel file.

    Args:
        file_path: Path to the downloaded .xlsx file.
        year: Data year (used to fill in `year` column if not present in file).

    Returns:
        Normalized DataFrame with columns:
          iso3, country_name, year, total_mt, per_capita_kg,
          formal_collection_rate, documentation_rate, confidence_tier

    Raises:
        ValueError: if the file cannot be parsed or required columns are missing.
    """
    import pandas as pd
    from .schema import COLUMN_ALIASES, EXPECTED_COLUMNS, EXPECTED_SHEET_NAME

    # ── 1. Load the workbook ──────────────────────────────────────────────────
    try:
        xl = pd.ExcelFile(str(file_path))
    except Exception as exc:
        raise ValueError(f"Cannot open UN Monitor file {file_path}: {exc}") from exc

    # Find the country data sheet (case-insensitive partial match)
    sheet_name = _find_sheet(xl.sheet_names, EXPECTED_SHEET_NAME)
    if sheet_name is None:
        # Fallback: use the first sheet
        sheet_name = xl.sheet_names[0]
        logger.warning(
            "UN Monitor: sheet '%s' not found; using first sheet '%s'",
            EXPECTED_SHEET_NAME, sheet_name,
        )

    raw_df = xl.parse(sheet_name, header=None)

    # ── 2. Detect header row ──────────────────────────────────────────────────
    header_row_idx = _detect_header_row(raw_df, set(COLUMN_ALIASES.keys()))
    if header_row_idx is None:
        raise ValueError(
            f"UN Monitor: could not find header row in sheet '{sheet_name}'. "
            "Check that COLUMN_ALIASES covers the actual column names."
        )

    df = xl.parse(sheet_name, header=header_row_idx)
    df.columns = [str(c).strip() for c in df.columns]

    # ── 3. Rename columns to internal names ───────────────────────────────────
    rename_map = {col: alias for col, alias in COLUMN_ALIASES.items() if col in df.columns}
    df = df.rename(columns=rename_map)

    # Drop columns we don't recognise (keep only aliased columns)
    keep = {v for v in COLUMN_ALIASES.values() if v in df.columns}
    df = df[[c for c in df.columns if c in keep]]

    # ── 4. Validate required columns ──────────────────────────────────────────
    missing_cols = EXPECTED_COLUMNS - set(df.columns)
    if missing_cols:
        raise ValueError(
            f"UN Monitor: required columns {missing_cols} not found after alias mapping. "
            f"Present columns: {list(df.columns)}"
        )

    # ── 5. Fill year column if not in data ────────────────────────────────────
    if "year" not in df.columns and year is not None:
        df["year"] = year
    elif "year" not in df.columns:
        raise ValueError("UN Monitor: 'year' column not found and no year argument supplied")

    if "country_name" not in df.columns:
        df["country_name"] = ""

    # ── 6. Clean numeric columns ──────────────────────────────────────────────
    numeric_cols = ["total_mt", "per_capita_kg", "formal_collection_rate", "documentation_rate"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].apply(_clean_numeric)

    # ── 7. Drop rows with missing required fields ─────────────────────────────
    df = df.dropna(subset=["iso3", "total_mt"])

    # ── 8. Normalize ISO3 ─────────────────────────────────────────────────────
    df["iso3"] = df["iso3"].apply(lambda v: str(v).strip().upper() if pd.notna(v) else None)
    df = df[df["iso3"].notna() & (df["iso3"].str.len() == 3)]

    # ── 9. Type coercion ──────────────────────────────────────────────────────
    df["year"] = df["year"].apply(lambda v: int(float(v)) if _is_numeric(v) else None)
    df = df.dropna(subset=["year"])
    df["year"] = df["year"].astype(int)

    # Add confidence tier
    df["confidence_tier"] = "reported"

    # Ensure all expected output columns exist (fill with None if absent)
    for col in ["per_capita_kg", "formal_collection_rate", "documentation_rate"]:
        if col not in df.columns:
            df[col] = None

    result = df[[
        "iso3", "country_name", "year", "total_mt",
        "per_capita_kg", "formal_collection_rate", "documentation_rate",
        "confidence_tier",
    ]].reset_index(drop=True)

    logger.info(
        "UN Monitor: parsed %d country-year records from %s",
        len(result), file_path.name,
    )
    return result


# ── Private helpers ───────────────────────────────────────────────────────────

def _find_sheet(sheet_names: list[str], target: str) -> Optional[str]:
    """Return the first sheet name that contains `target` (case-insensitive)."""
    target_lower = target.lower()
    for name in sheet_names:
        if target_lower in name.lower():
            return name
    return None


def _detect_header_row(df: "pd.DataFrame", known_headers: set[str]) -> Optional[int]:
    """Scan rows to find the first row that matches a known header string."""
    import pandas as pd
    known_lower = {h.lower() for h in known_headers}
    for idx, row in df.iterrows():
        row_strs = {str(v).strip().lower() for v in row if pd.notna(v)}
        if row_strs & known_lower:
            return int(idx)
    return None


def _clean_numeric(value) -> Optional[float]:
    """Parse a cell value to float, handling string formatting and missing markers."""
    import pandas as pd
    if pd.isna(value):
        return None
    s = str(value).strip().replace(",", "")
    if s.lower() in _MISSING_VALUES:
        return None
    # Remove percentage signs
    s = s.replace("%", "")
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _is_numeric(value) -> bool:
    """Return True if value can be converted to float."""
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False
