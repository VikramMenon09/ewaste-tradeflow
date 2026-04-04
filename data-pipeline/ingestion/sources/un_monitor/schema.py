"""
Schema definition for UN Global E-Waste Monitor records.

The UN Monitor publishes Excel files annually with per-country e-waste
generation estimates.  File format documented in:
  Forti V., et al. (2020). "The Global E-waste Monitor 2020"
  UNU/UNITAR — ITU, Geneva, Switzerland.

The sheet "Country data" contains columns (approximate English headers):
  Country, ISO3, Year, Total_Mt, Per_Capita_Kg, Formal_Collection_Rate,
  Documentation_Rate (fraction of total where data is documented)

Source file URL is configurable via UN_MONITOR_EXCEL_URL environment variable.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

# Name of the worksheet to read in the UN Monitor Excel file
EXPECTED_SHEET_NAME = "Country data"

# Expected column name mappings from the Excel file to internal names.
# Keys are possible Excel header spellings; values are internal field names.
COLUMN_ALIASES: dict[str, str] = {
    # Country name
    "Country": "country_name",
    "Country or Area": "country_name",
    # ISO3 code
    "ISO3": "iso3",
    "ISO 3166-1 alpha-3": "iso3",
    # Year
    "Year": "year",
    "Reference year": "year",
    # Total e-waste generated in metric tonnes
    "Total_Mt": "total_mt",
    "Total (Mt)": "total_mt",
    "E-waste generated (Mt)": "total_mt",
    # Per-capita in kg
    "Per_Capita_Kg": "per_capita_kg",
    "Per Capita (kg)": "per_capita_kg",
    "E-waste per capita (kg)": "per_capita_kg",
    # Formal collection / recycling rate (0.0–1.0)
    "Formal_Collection_Rate": "formal_collection_rate",
    "Formal collection rate": "formal_collection_rate",
    "Documented collection rate": "formal_collection_rate",
    # Documentation / data quality rate (0.0–1.0)
    "Documentation_Rate": "documentation_rate",
    "Documentation rate": "documentation_rate",
}

# Columns that must be present after alias resolution
EXPECTED_COLUMNS = {"iso3", "year", "total_mt"}


@dataclass
class UNMonitorRecord:
    """One normalized UN Monitor record — one row per (country, year)."""

    iso3: str
    country_name: str
    year: int
    total_mt: float
    per_capita_kg: Optional[float]
    formal_collection_rate: Optional[float]
    documentation_rate: Optional[float]
    confidence_tier: str = "reported"
    ingested_at: datetime = None

    def __post_init__(self) -> None:
        if self.ingested_at is None:
            self.ingested_at = datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "iso3": self.iso3,
            "country_name": self.country_name,
            "year": self.year,
            "total_mt": self.total_mt,
            "per_capita_kg": self.per_capita_kg,
            "formal_collection_rate": self.formal_collection_rate,
            "documentation_rate": self.documentation_rate,
            "confidence_tier": self.confidence_tier,
            "ingested_at": self.ingested_at.isoformat(),
        }
