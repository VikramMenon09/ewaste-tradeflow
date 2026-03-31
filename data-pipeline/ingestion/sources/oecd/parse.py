"""
Normalization of raw OECD ENV_WASTE_TRAN data into the project's standard schema.

Responsibilities:
  1. Map OECD country codes (their own scheme) → ISO 3166-1 alpha-3
  2. Map OECD waste category codes → UN e-waste category codes (0-6)
  3. Drop rows with unresolvable country codes (log warnings, count drops)
  4. Rename and type-cast columns to match EXPECTED_COLUMNS in schema.py
  5. Return a DataFrame ready for SchemaValidation and S3 upload

OECD country codes vs ISO3:
  - OECD uses its own 3-letter codes that *mostly* match ISO3 but differ for
    several members (e.g., "GBR" is the same, but older OECD data may use
    "UK" or "GBR", and codes for partner territories vary).
  - The OECD_TO_ISO3 crosswalk covers all 38 OECD members plus key partner
    countries that appear in ENV_WASTE_TRAN data.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OECD country code → ISO 3166-1 alpha-3 crosswalk
# ---------------------------------------------------------------------------
# Sources:
#   - OECD member list: https://www.oecd.org/about/members-and-partners/
#   - ISO 3166-1: https://www.iso.org/iso-3166-country-codes.html
#   - OECD.Stat country codes observed in ENV_WASTE_TRAN data
#
# Most codes are identical to ISO3; we include them all for completeness so
# that lookup is O(1) with no fallthrough logic in the hot path.

OECD_TO_ISO3: dict[str, str] = {
    # --- 38 OECD Members ---
    "AUS": "AUS",  # Australia
    "AUT": "AUT",  # Austria
    "BEL": "BEL",  # Belgium
    "CAN": "CAN",  # Canada
    "CHL": "CHL",  # Chile
    "COL": "COL",  # Colombia
    "CRI": "CRI",  # Costa Rica
    "CZE": "CZE",  # Czech Republic
    "DNK": "DNK",  # Denmark
    "EST": "EST",  # Estonia
    "FIN": "FIN",  # Finland
    "FRA": "FRA",  # France
    "DEU": "DEU",  # Germany
    "GRC": "GRC",  # Greece
    "HUN": "HUN",  # Hungary
    "ISL": "ISL",  # Iceland
    "IRL": "IRL",  # Ireland
    "ISR": "ISR",  # Israel
    "ITA": "ITA",  # Italy
    "JPN": "JPN",  # Japan
    "KOR": "KOR",  # Korea (Republic of)
    "LVA": "LVA",  # Latvia
    "LTU": "LTU",  # Lithuania
    "LUX": "LUX",  # Luxembourg
    "MEX": "MEX",  # Mexico
    "NLD": "NLD",  # Netherlands
    "NZL": "NZL",  # New Zealand
    "NOR": "NOR",  # Norway
    "POL": "POL",  # Poland
    "PRT": "PRT",  # Portugal
    "SVK": "SVK",  # Slovak Republic
    "SVN": "SVN",  # Slovenia
    "ESP": "ESP",  # Spain
    "SWE": "SWE",  # Sweden
    "CHE": "CHE",  # Switzerland
    "TUR": "TUR",  # Turkey (Türkiye)
    "GBR": "GBR",  # United Kingdom
    "USA": "USA",  # United States

    # --- Key partner / accession countries ---
    "ARG": "ARG",  # Argentina
    "BRA": "BRA",  # Brazil
    "BGR": "BGR",  # Bulgaria
    "CHN": "CHN",  # China
    "HRV": "HRV",  # Croatia
    "CYP": "CYP",  # Cyprus
    "EGY": "EGY",  # Egypt
    "IDN": "IDN",  # Indonesia
    "IND": "IND",  # India
    "KAZ": "KAZ",  # Kazakhstan
    "MYS": "MYS",  # Malaysia
    "MAR": "MAR",  # Morocco
    "NGA": "NGA",  # Nigeria
    "PER": "PER",  # Peru
    "PHL": "PHL",  # Philippines
    "ROU": "ROU",  # Romania
    "RUS": "RUS",  # Russia
    "SAU": "SAU",  # Saudi Arabia
    "ZAF": "ZAF",  # South Africa
    "THA": "THA",  # Thailand
    "TUN": "TUN",  # Tunisia
    "UKR": "UKR",  # Ukraine
    "VNM": "VNM",  # Vietnam

    # --- OECD-specific code aliases (alternate codes used in older data) ---
    "UK":  "GBR",   # United Kingdom (older OECD code)
    "KS":  "XKX",   # Kosovo (OECD uses "KS"; no ISO3 — use XKX convention)
    "OAVG": None,   # OECD Average aggregate — drop
    "OECD": None,   # OECD total aggregate — drop
    "EU27_2020": None,  # EU aggregate — drop
    "EA19": None,   # Euro area aggregate — drop
    "G20": None,    # G20 aggregate — drop
    "WLD": None,    # World aggregate — drop
}


# ---------------------------------------------------------------------------
# OECD waste category code → UN e-waste category code
# ---------------------------------------------------------------------------
# OECD ENV_WASTE_TRAN uses Basel Convention waste categories (Y-codes and
# Basel Annex codes), not the 6-category UN Monitor scheme. This mapping is
# a best-effort approximation based on the material composition of each OECD
# waste code.
#
# UN e-waste categories:
#   1 = Temperature exchange equipment (fridges, ACs, heat pumps)
#   2 = Screens and monitors (TVs, laptops, monitors)
#   3 = Lamps (fluorescent, LED, discharge lamps)
#   4 = Large equipment (washing machines, dishwashers, large IT servers)
#   5 = Small equipment (toasters, electric tools, medical devices)
#   6 = Small IT and telecommunications equipment (phones, computers, tablets)
#   0 = All categories (mixed / unspecified)

OECD_WASTE_TO_UN_CATEGORY: dict[str, int] = {
    # Basel Annex VIII / IX codes for electrical/electronic waste
    "A1180": 0,   # Waste electrical and electronic assemblies (mixed)
    "A1181": 6,   # Printed circuit boards
    "A2060": 4,   # Power generating equipment waste
    "B1110": 0,   # Electrical and electronic assemblies for re-use (mixed)
    "B1115": 6,   # Electronic components (diodes, transistors, etc.)

    # OECD-specific ENV_WASTE_TRAN dimension codes
    "EEWASTE": 0,   # General electrical/electronic waste (catch-all)
    "HAZWASTE": 0,  # Hazardous waste (general category, includes e-waste)
    "IT_EQ": 6,     # IT equipment
    "TELECOM": 6,   # Telecommunications equipment
    "CONSUMER": 5,  # Consumer electronics (small equipment proxy)
    "REFRIG": 1,    # Refrigeration/temperature exchange equipment
    "LIGHTING": 3,  # Lighting equipment
    "LARGE_EQ": 4,  # Large household appliances
    "SMALL_EQ": 5,  # Small household appliances
    "SCREENS": 2,   # Screens and monitors
    "PCB": 6,       # Printed circuit boards / small IT

    # Total / aggregate codes
    "TOTAL": 0,
    "_T": 0,
    "TOT": 0,
}

# Default UN category when OECD code is not in the mapping
DEFAULT_UN_CATEGORY = 0  # 0 = mixed/unknown


def normalize(df: "pd.DataFrame") -> "pd.DataFrame":
    """
    Normalize a raw OECD DataFrame (output of OecdClient._parse_sdmx_json)
    into the standard schema expected by the ingestion pipeline.

    Steps:
      1. Map oecd_reporter_code and oecd_partner_code → ISO3 using OECD_TO_ISO3
      2. Drop rows where either country code cannot be resolved (log count)
      3. Map oecd_waste_code → UN ewaste_category_code (0-6)
      4. Rename volume_tonnes → volume_mt (already in metric tons from OECD)
      5. Add confidence_tier = 'reported'
      6. Validate schema and return

    Args:
        df: Raw DataFrame from OecdClient.fetch_transboundary_flows()

    Returns:
        Normalized DataFrame matching OECD schema.EXPECTED_COLUMNS
        May be empty if all rows had unresolvable country codes.
    """
    import pandas as pd
    from .schema import validate_dataframe_schema

    if len(df) == 0:
        logger.info("OECD normalize: empty input DataFrame")
        return pd.DataFrame()

    original_len = len(df)

    # 1. Map OECD reporter/partner codes to ISO3
    df = df.copy()
    df["exporter_iso3"] = df["oecd_reporter_code"].map(
        lambda c: _resolve_oecd_code(c)
    )
    df["importer_iso3"] = df["oecd_partner_code"].map(
        lambda c: _resolve_oecd_code(c)
    )

    # 2. Drop rows with unresolvable codes (None from crosswalk or empty string)
    before_drop = len(df)
    df = df[
        df["exporter_iso3"].notna() &
        df["importer_iso3"].notna() &
        (df["exporter_iso3"] != "") &
        (df["importer_iso3"] != "")
    ]
    dropped = before_drop - len(df)
    if dropped > 0:
        logger.warning(
            "OECD normalize: dropped %d/%d rows with unresolvable country codes "
            "(aggregates like OECD_TOTAL, WLD, etc. are expected drops)",
            dropped, before_drop,
        )

    # 3. Drop self-flows
    df = df[df["exporter_iso3"] != df["importer_iso3"]]

    # 4. Map OECD waste code → UN e-waste category code
    df["ewaste_category_code"] = df["oecd_waste_code"].map(
        lambda c: OECD_WASTE_TO_UN_CATEGORY.get(str(c).upper(), DEFAULT_UN_CATEGORY)
    ).astype(int)

    # 5. Rename volume and set to metric tons
    #    OECD ENV_WASTE_TRAN reports quantities in metric tonnes (= metric tons)
    df["volume_mt"] = df["volume_tonnes"].astype(float)

    # 6. Filter out zero/negative volumes
    df = df[df["volume_mt"] > 0]

    # 7. Select and type-cast final columns
    df["year"] = df["year"].astype(int)
    df["confidence_tier"] = "reported"

    result = df[["year", "exporter_iso3", "importer_iso3", "ewaste_category_code",
                  "volume_mt", "confidence_tier"]].reset_index(drop=True)

    filtered_total = original_len - len(result)
    if filtered_total > 0:
        logger.debug(
            "OECD normalize: %d input rows → %d output rows (%d dropped)",
            original_len, len(result), filtered_total,
        )

    # 8. Validate schema contract
    validate_dataframe_schema(result)

    return result


def _resolve_oecd_code(oecd_code: str) -> Optional[str]:
    """
    Map an OECD country code to ISO3. Returns None for aggregates and unknowns.

    Tries the crosswalk first; if not found and the code is a valid 3-letter
    string, passes it through as a best-effort ISO3 (handles new OECD members
    added after this crosswalk was written). If the code is an aggregate
    sentinel, returns None.
    """
    code = str(oecd_code).strip().upper()

    if not code or code in ("", "NaN", "NONE", "NULL"):
        return None

    # Try exact crosswalk lookup
    if code in OECD_TO_ISO3:
        result = OECD_TO_ISO3[code]
        if result is None:
            # Explicit None means "this is an aggregate, drop it"
            return None
        return result

    # If the code is exactly 3 uppercase letters and not in our drop list,
    # pass it through — it may be a valid ISO3 for a country added after
    # this crosswalk was written
    if len(code) == 3 and code.isalpha():
        logger.warning(
            "OECD country code '%s' not in OECD_TO_ISO3 crosswalk — "
            "passing through as ISO3. Add to crosswalk if this recurs.",
            code,
        )
        return code

    # Code is non-standard (e.g. "EU27_2020", "OAVG") — treat as aggregate
    logger.debug("OECD: treating code '%s' as aggregate, dropping row", code)
    return None
