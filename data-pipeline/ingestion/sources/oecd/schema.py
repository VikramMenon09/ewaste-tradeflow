"""
Expected column contracts for OECD ENV_WASTE_TRAN normalized output.

If the OECD SDMX-JSON API changes its schema or if the parse step
deviates from these contracts, validate_dataframe_schema() raises
SchemaValidationError with a clear diff, rather than silently producing
bad downstream data.
"""

from dataclasses import dataclass
from typing import Any


# Columns expected in the normalized DataFrame after parse.py has processed
# the raw OECD SDMX-JSON response.
EXPECTED_COLUMNS: dict[str, type] = {
    "year": int,                  # Reporting year (e.g. 2022)
    "exporter_iso3": str,         # Exporting country ISO 3166-1 alpha-3
    "importer_iso3": str,         # Importing country ISO 3166-1 alpha-3
    "ewaste_category_code": int,  # UN e-waste category code (0-6; 0 = mixed/unknown)
    "volume_mt": float,           # Volume in metric tons
    "confidence_tier": str,       # Always 'reported' for OECD ENV_WASTE_TRAN
}


class SchemaValidationError(Exception):
    """Raised when the OECD normalized output deviates from the expected schema."""
    pass


@dataclass
class OecdFlowRecord:
    """Typed record representing one normalized OECD transboundary waste flow row."""
    year: int
    exporter_iso3: str
    importer_iso3: str
    ewaste_category_code: int
    volume_mt: float
    confidence_tier: str


def validate_dataframe_schema(df: Any) -> None:
    """
    Validate that a normalized OECD DataFrame has the expected columns.

    Extra columns are allowed (logged as warnings). Missing columns raise
    SchemaValidationError with a diff showing what is absent.

    Args:
        df: pandas DataFrame to validate (after parse.py normalization)

    Raises:
        SchemaValidationError: if any required column is missing
    """
    import logging

    _log = logging.getLogger(__name__)

    missing = set(EXPECTED_COLUMNS.keys()) - set(df.columns)
    extra = set(df.columns) - set(EXPECTED_COLUMNS.keys())

    if extra:
        _log.warning("OECD schema: unexpected extra columns %s (ignored)", sorted(extra))

    if missing:
        raise SchemaValidationError(
            "OECD normalized output is missing required columns:\n"
            f"  Missing: {sorted(missing)}\n"
            f"  Present: {sorted(df.columns.tolist())}"
        )
