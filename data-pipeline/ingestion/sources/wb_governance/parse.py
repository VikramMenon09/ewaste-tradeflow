"""
Normalization of raw World Bank Governance Indicators data.

Responsibilities:
  1. Convert WBI ISO2 country codes → ISO3 using the comprehensive crosswalk
  2. Rename indicator columns to human-readable names
  3. Compute data_completeness (fraction of 3 indicators present)
  4. Set confidence_tier = 'reported'
  5. Drop aggregate regions (ISO2 codes > 2 chars, e.g. "1W", "EAP")

ISO2 → ISO3 note:
  The World Bank uses ISO 3166-1 alpha-2 (2-letter) country codes in its API
  responses. We convert to alpha-3 for consistency with the rest of the pipeline.
  The WBI also uses non-standard 2-letter codes for some territories (e.g. "KV"
  for Kosovo) that don't appear in the standard ISO 3166 tables.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ISO 3166-1 alpha-2 → alpha-3 crosswalk
# ---------------------------------------------------------------------------
# Comprehensive mapping covering all 249 ISO 3166-1 entries plus selected
# WBI-specific codes. Sourced from ISO 3166 Maintenance Agency.

ISO2_TO_ISO3: dict[str, str] = {
    "AF": "AFG", "AX": "ALA", "AL": "ALB", "DZ": "DZA", "AS": "ASM",
    "AD": "AND", "AO": "AGO", "AI": "AIA", "AQ": "ATA", "AG": "ATG",
    "AR": "ARG", "AM": "ARM", "AW": "ABW", "AU": "AUS", "AT": "AUT",
    "AZ": "AZE", "BS": "BHS", "BH": "BHR", "BD": "BGD", "BB": "BRB",
    "BY": "BLR", "BE": "BEL", "BZ": "BLZ", "BJ": "BEN", "BM": "BMU",
    "BT": "BTN", "BO": "BOL", "BQ": "BES", "BA": "BIH", "BW": "BWA",
    "BV": "BVT", "BR": "BRA", "IO": "IOT", "BN": "BRN", "BG": "BGR",
    "BF": "BFA", "BI": "BDI", "CV": "CPV", "KH": "KHM", "CM": "CMR",
    "CA": "CAN", "KY": "CYM", "CF": "CAF", "TD": "TCD", "CL": "CHL",
    "CN": "CHN", "CX": "CXR", "CC": "CCK", "CO": "COL", "KM": "COM",
    "CG": "COG", "CD": "COD", "CK": "COK", "CR": "CRI", "CI": "CIV",
    "HR": "HRV", "CU": "CUB", "CW": "CUW", "CY": "CYP", "CZ": "CZE",
    "DK": "DNK", "DJ": "DJI", "DM": "DMA", "DO": "DOM", "EC": "ECU",
    "EG": "EGY", "SV": "SLV", "GQ": "GNQ", "ER": "ERI", "EE": "EST",
    "SZ": "SWZ", "ET": "ETH", "FK": "FLK", "FO": "FRO", "FJ": "FJI",
    "FI": "FIN", "FR": "FRA", "GF": "GUF", "PF": "PYF", "TF": "ATF",
    "GA": "GAB", "GM": "GMB", "GE": "GEO", "DE": "DEU", "GH": "GHA",
    "GI": "GIB", "GR": "GRC", "GL": "GRL", "GD": "GRD", "GP": "GLP",
    "GU": "GUM", "GT": "GTM", "GG": "GGY", "GN": "GIN", "GW": "GNB",
    "GY": "GUY", "HT": "HTI", "HM": "HMD", "VA": "VAT", "HN": "HND",
    "HK": "HKG", "HU": "HUN", "IS": "ISL", "IN": "IND", "ID": "IDN",
    "IR": "IRN", "IQ": "IRQ", "IE": "IRL", "IM": "IMN", "IL": "ISR",
    "IT": "ITA", "JM": "JAM", "JP": "JPN", "JE": "JEY", "JO": "JOR",
    "KZ": "KAZ", "KE": "KEN", "KI": "KIR", "KP": "PRK", "KR": "KOR",
    "KW": "KWT", "KG": "KGZ", "LA": "LAO", "LV": "LVA", "LB": "LBN",
    "LS": "LSO", "LR": "LBR", "LY": "LBY", "LI": "LIE", "LT": "LTU",
    "LU": "LUX", "MO": "MAC", "MG": "MDG", "MW": "MWI", "MY": "MYS",
    "MV": "MDV", "ML": "MLI", "MT": "MLT", "MH": "MHL", "MQ": "MTQ",
    "MR": "MRT", "MU": "MUS", "YT": "MYT", "MX": "MEX", "FM": "FSM",
    "MD": "MDA", "MC": "MCO", "MN": "MNG", "ME": "MNE", "MS": "MSR",
    "MA": "MAR", "MZ": "MOZ", "MM": "MMR", "NA": "NAM", "NR": "NRU",
    "NP": "NPL", "NL": "NLD", "NC": "NCL", "NZ": "NZL", "NI": "NIC",
    "NE": "NER", "NG": "NGA", "NU": "NIU", "NF": "NFK", "MK": "MKD",
    "MP": "MNP", "NO": "NOR", "OM": "OMN", "PK": "PAK", "PW": "PLW",
    "PS": "PSE", "PA": "PAN", "PG": "PNG", "PY": "PRY", "PE": "PER",
    "PH": "PHL", "PN": "PCN", "PL": "POL", "PT": "PRT", "PR": "PRI",
    "QA": "QAT", "RE": "REU", "RO": "ROU", "RU": "RUS", "RW": "RWA",
    "BL": "BLM", "SH": "SHN", "KN": "KNA", "LC": "LCA", "MF": "MAF",
    "PM": "SPM", "VC": "VCT", "WS": "WSM", "SM": "SMR", "ST": "STP",
    "SA": "SAU", "SN": "SEN", "RS": "SRB", "SC": "SYC", "SL": "SLE",
    "SG": "SGP", "SX": "SXM", "SK": "SVK", "SI": "SVN", "SB": "SLB",
    "SO": "SOM", "ZA": "ZAF", "GS": "SGS", "SS": "SSD", "ES": "ESP",
    "LK": "LKA", "SD": "SDN", "SR": "SUR", "SJ": "SJM", "SE": "SWE",
    "CH": "CHE", "SY": "SYR", "TW": "TWN", "TJ": "TJK", "TZ": "TZA",
    "TH": "THA", "TL": "TLS", "TG": "TGO", "TK": "TKL", "TO": "TON",
    "TT": "TTO", "TN": "TUN", "TR": "TUR", "TM": "TKM", "TC": "TCA",
    "TV": "TUV", "UG": "UGA", "UA": "UKR", "AE": "ARE", "GB": "GBR",
    "US": "USA", "UM": "UMI", "UY": "URY", "UZ": "UZB", "VU": "VUT",
    "VE": "VEN", "VN": "VNM", "VG": "VGB", "VI": "VIR", "WF": "WLF",
    "EH": "ESH", "YE": "YEM", "ZM": "ZMB", "ZW": "ZWE",
    # WBI-specific non-standard codes
    "XK": "XKX",   # Kosovo (WBI uses XK)
    "KV": "XKX",   # Kosovo (alternative WBI code)
}


def normalize(df: "pd.DataFrame") -> "pd.DataFrame":
    """
    Normalize a raw WBI DataFrame (output of WbGovernanceClient.fetch_governance_indicators)
    into the standard schema for upload.

    Steps:
      1. Convert country_id (ISO2) → country_iso3 (ISO3) using ISO2_TO_ISO3
      2. Drop rows with unresolvable ISO2 codes (aggregate regions)
      3. Rename columns: rl_est → rule_of_law, ge_est → gov_effectiveness,
         cc_est → control_of_corruption
      4. Compute data_completeness (0.0–1.0, fraction of 3 indicators non-null)
      5. Set confidence_tier = 'reported'
      6. Add ingested_at timestamp

    Args:
        df: Wide-format DataFrame from WbGovernanceClient.fetch_governance_indicators().
            Expected columns: country_id, country_name, year, rl_est, ge_est, cc_est

    Returns:
        Normalized DataFrame with columns:
          country_iso3, year, rule_of_law, gov_effectiveness,
          control_of_corruption, data_completeness, confidence_tier
    """
    import pandas as pd

    if len(df) == 0:
        logger.info("WBI normalize: empty input DataFrame")
        return pd.DataFrame()

    df = df.copy()

    # 1. Map ISO2 → ISO3
    df["country_iso3"] = df["country_id"].map(
        lambda code: ISO2_TO_ISO3.get(str(code).upper()) if code else None
    )

    # 2. Drop rows without a valid ISO3 code
    before = len(df)
    df = df[df["country_iso3"].notna()].copy()
    dropped = before - len(df)
    if dropped > 0:
        logger.info(
            "WBI normalize: dropped %d rows with unresolvable ISO2 codes "
            "(regional aggregates expected)", dropped
        )

    if len(df) == 0:
        return pd.DataFrame()

    # 3. Rename indicator columns
    col_renames = {
        "rl_est": "rule_of_law",
        "ge_est": "gov_effectiveness",
        "cc_est": "control_of_corruption",
    }
    # Only rename columns that exist (fetch may return partial data)
    existing_renames = {k: v for k, v in col_renames.items() if k in df.columns}
    df = df.rename(columns=existing_renames)

    # Ensure all three indicator columns exist (fill with NaN if missing)
    for col in ["rule_of_law", "gov_effectiveness", "control_of_corruption"]:
        if col not in df.columns:
            df[col] = None
            logger.warning("WBI normalize: column '%s' missing — filled with NULL", col)

    # Cast indicator values to float (handles None gracefully)
    for col in ["rule_of_law", "gov_effectiveness", "control_of_corruption"]:
        df[col] = df[col].apply(lambda v: float(v) if v is not None else None)

    # 4. Compute data_completeness (fraction of 3 indicators non-null per row)
    indicator_cols = ["rule_of_law", "gov_effectiveness", "control_of_corruption"]
    df["data_completeness"] = df[indicator_cols].notna().sum(axis=1) / len(indicator_cols)

    # 5. Set confidence tier
    df["confidence_tier"] = "reported"

    # 6. Select and type-cast final columns
    df["year"] = df["year"].astype(int)

    result = df[[
        "country_iso3", "year",
        "rule_of_law", "gov_effectiveness", "control_of_corruption",
        "data_completeness", "confidence_tier",
    ]].reset_index(drop=True)

    logger.info(
        "WBI normalize: %d countries normalized for year=%d "
        "(avg completeness=%.2f)",
        len(result),
        result["year"].iloc[0] if len(result) > 0 else 0,
        result["data_completeness"].mean(),
    )

    return result


def iso2_to_iso3(iso2: str) -> Optional[str]:
    """
    Public helper: convert a single ISO2 code to ISO3.
    Returns None if not found in the crosswalk.
    """
    return ISO2_TO_ISO3.get(str(iso2).strip().upper())
