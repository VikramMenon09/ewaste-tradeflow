"""
Schema definition for World Bank Governance Indicators records.

Three indicators are fetched (Rule of Law, Government Effectiveness,
Control of Corruption) and stored as a wide-format record per country-year.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

# Canonical indicator codes fetched from the WBI API
GOVERNANCE_INDICATORS = ["RL.EST", "GE.EST", "CC.EST"]


@dataclass
class WBGovernanceRecord:
    """One normalized governance record — one row per (country, year)."""

    country_iso3: str
    year: int
    rule_of_law: Optional[float]
    gov_effectiveness: Optional[float]
    control_of_corruption: Optional[float]
    data_completeness: float          # 0.0–1.0 (fraction of 3 indicators present)
    confidence_tier: str              # always 'reported'
    ingested_at: datetime = None

    def __post_init__(self) -> None:
        if self.ingested_at is None:
            self.ingested_at = datetime.utcnow()

    @property
    def composite_governance_score(self) -> Optional[float]:
        """Simple average of the three indicators (None if all are missing)."""
        values = [
            v for v in [self.rule_of_law, self.gov_effectiveness, self.control_of_corruption]
            if v is not None
        ]
        return sum(values) / len(values) if values else None

    def to_dict(self) -> dict:
        return {
            "country_iso3": self.country_iso3,
            "year": self.year,
            "rule_of_law": self.rule_of_law,
            "gov_effectiveness": self.gov_effectiveness,
            "control_of_corruption": self.control_of_corruption,
            "data_completeness": self.data_completeness,
            "confidence_tier": self.confidence_tier,
            "ingested_at": self.ingested_at.isoformat(),
        }


# Expected columns in the normalized DataFrame after parse.normalize() runs
EXPECTED_COLUMNS = {
    "country_iso3": str,
    "year": int,
    "rule_of_law": float,
    "gov_effectiveness": float,
    "control_of_corruption": float,
    "data_completeness": float,
    "confidence_tier": str,
}
