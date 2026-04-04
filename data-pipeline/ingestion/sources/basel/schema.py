"""
Schema definition for Basel Convention party/signatory status records.

The Basel Convention Secretariat (UNEP) publishes the list of Parties at:
  https://www.basel.int/Countries/StatusofRatifications/PartiesSignatories/tabid/4499/Default.aspx

Key columns:
  Country         — country name
  ISO3            — ISO 3166-1 alpha-3 code
  is_party        — True if country has ratified/acceded to the Convention
  ban_amendment_ratified — True if country has ratified the Ban Amendment (Annex VII restriction)
  ratification_year — year of convention ratification (may be null)
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

# Expected column names in the normalized output DataFrame
EXPECTED_COLUMNS = {"iso3", "is_party"}


@dataclass
class BaselStatusRecord:
    """One Basel Convention status record per country (static reference data)."""

    iso3: str
    country_name: str
    is_party: bool
    ban_amendment_ratified: bool
    ratification_year: Optional[int]
    ban_ratification_year: Optional[int]
    ingested_at: datetime = None

    def __post_init__(self) -> None:
        if self.ingested_at is None:
            self.ingested_at = datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "iso3": self.iso3,
            "country_name": self.country_name,
            "is_party": self.is_party,
            "ban_amendment_ratified": self.ban_amendment_ratified,
            "ratification_year": self.ratification_year,
            "ban_ratification_year": self.ban_ratification_year,
            "ingested_at": self.ingested_at.isoformat(),
        }
