"""
Post-fetch normalization for Comtrade data.

After fetch.py retrieves raw API data and validates the schema, this module
applies further cleaning and enrichment before the data is written to S3:
  - Filters out aggregate rows (World-level, regional totals)
  - Normalizes quantity to metric tons
  - Applies ISO3 country code corrections for known Comtrade anomalies
  - Tags each record with source metadata (source_id FK will be resolved at load time)
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Comtrade uses non-standard codes for some territories and aggregates.
# Map these to ISO 3166-1 alpha-3 or a canonical placeholder.
COMTRADE_ISO_CORRECTIONS: dict[str, str] = {
    "W00": "WORLD",     # World aggregate — should be filtered before this step
    "WLD": "WORLD",
    "EU": "EU27",        # European Union aggregate
    "EUN": "EU27",
    "CHN+HKG": "CHN",    # China including HK (some older data)
    "ROM": "ROU",        # Romania old code
    "ZAR": "COD",        # Congo, Dem. Rep. old code
    "TMP": "TLS",        # East Timor old code
    "YUG": "SRB",        # Yugoslavia → Serbia (best approximation)
    "CSK": "CZE",        # Czechoslovakia → Czech Republic (best approximation)
    "ANT": "CUW",        # Netherlands Antilles → Curaçao (best approximation)
    "SCG": "SRB",        # Serbia and Montenegro → Serbia
}

# Minimum volume threshold in metric tons — rows below this are likely
# administrative entries or data errors, not real trade flows.
MIN_VOLUME_MT = 0.001


def normalize(df: "pd.DataFrame") -> "pd.DataFrame":
    """
    Apply all normalization steps to a raw Comtrade DataFrame.

    Returns a cleaned DataFrame ready for S3 upload. May return fewer rows
    than the input after filtering aggregates and near-zero volumes.

    Args:
        df: Raw DataFrame from ComtradeClient._records_to_dataframe()

    Returns:
        Normalized DataFrame with standardized column values
    """
    import pandas as pd

    original_len = len(df)

    # 1. Drop aggregate rows (World, EU, regional totals)
    df = df[~df["is_aggregate"]].copy()

    # 2. Apply ISO3 code corrections
    df["reporter_iso3"] = df["reporter_iso3"].map(
        lambda c: COMTRADE_ISO_CORRECTIONS.get(c, c)
    )
    df["partner_iso3"] = df["partner_iso3"].map(
        lambda c: COMTRADE_ISO_CORRECTIONS.get(c, c)
    )

    # 3. Drop rows that map to WORLD or have empty country codes after correction
    df = df[
        (df["reporter_iso3"] != "WORLD") &
        (df["partner_iso3"] != "WORLD") &
        (df["reporter_iso3"] != "") &
        (df["partner_iso3"] != "")
    ]

    # 4. Normalize quantity to metric tons
    df["volume_mt"] = df.apply(_compute_volume_mt, axis=1)

    # 5. Drop near-zero volume rows
    df = df[df["volume_mt"] >= MIN_VOLUME_MT]

    # 6. Normalize flow_code to uppercase
    df["flow_code"] = df["flow_code"].str.upper().str.strip()

    # 7. Drop self-trade rows (reporter == partner) — these are data errors
    df = df[df["reporter_iso3"] != df["partner_iso3"]]

    # 8. Add derived confidence tier — all Comtrade data is tier 1 (officially reported)
    df["confidence_tier"] = "reported"

    # 9. Add ingestion timestamp
    df["ingested_at"] = pd.Timestamp.utcnow()

    filtered = original_len - len(df)
    if filtered > 0:
        logger.debug("Comtrade normalize: dropped %d/%d rows (aggregates/near-zero/self-trade)", filtered, original_len)

    return df.reset_index(drop=True)


def _compute_volume_mt(row: Any) -> float:
    """Convert row quantity to metric tons based on qty_unit."""
    qty = row["qty"]
    unit = str(row["qty_unit"]).lower().strip()

    if unit in ("kg", "kilograms", "kilogram"):
        return qty / 1000.0
    elif unit in ("t", "mt", "metric tons", "metric ton", "tonnes", "tonne"):
        return qty
    elif unit in ("g", "grams", "gram"):
        return qty / 1_000_000.0
    elif unit in ("lb", "lbs", "pounds", "pound"):
        return qty * 0.000453592
    elif unit in ("no", "number", "pieces", "units", "u"):
        # Count-based quantity — cannot convert to metric tons
        # Return 0 so the row is filtered by MIN_VOLUME_MT check
        return 0.0
    else:
        # Unknown unit — log and pass through raw value
        logger.warning("Unknown qty_unit '%s' in Comtrade data — using raw qty as MT", unit)
        return qty


def deduplicate(df: "pd.DataFrame") -> "pd.DataFrame":
    """
    Remove duplicate rows within a DataFrame batch.

    Comtrade sometimes returns the same flow in both directions (export from A
    matches import to B for the same HS code/year). We keep both — they are
    different reporter perspectives — but we remove exact duplicates.
    """
    key_cols = ["period", "reporter_iso3", "partner_iso3", "flow_code", "hs_code"]
    before = len(df)
    df = df.drop_duplicates(subset=key_cols, keep="first")
    dropped = before - len(df)
    if dropped:
        logger.debug("Comtrade deduplicate: dropped %d exact duplicate rows", dropped)
    return df
