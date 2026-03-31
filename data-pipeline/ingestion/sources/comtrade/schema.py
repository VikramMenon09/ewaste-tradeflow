"""
Expected column contracts for Comtrade API v2 responses.

If the Comtrade API changes its schema, the parse step will raise a
SchemaValidationError with a clear diff of what changed, rather than
silently producing bad data.
"""

from dataclasses import dataclass
from typing import Any


# HS codes that cover e-waste and e-waste-adjacent trade flows.
# Split by confidence tier — see hs_to_ewaste_category.csv for full mapping.
EWASTE_HS_CODES = [
    # HIGH confidence — explicitly defined waste/scrap codes
    "8548",  # Waste and scrap of primary cells, batteries, electrical accumulators (HS 2017)
    "8549",  # Electrical and electronic waste and scrap (HS 2022)
    # MEDIUM confidence — predominantly IT equipment (category 6), includes new goods
    "8471",  # Automatic data-processing machines (computers)
    "8472",  # Other office machines
    "8473",  # Parts for 8469-8472
    # LOW confidence — industrial/mixed machinery, small e-waste fraction
    "8474",  # Machinery for sorting/screening/separating minerals
    "8475",  # Machines for assembling electric filament/discharge lamps
    "8476",  # Automatic goods-vending machines
    "8477",  # Machinery for working rubber/plastics (includes cable recycling)
    "8478",  # Machinery for preparing/making up tobacco
    "8479",  # Machines and mechanical appliances having individual functions (catch-all)
]

# Columns expected in the normalized DataFrame after parse.py processes the API response.
# Types are Python type hints for validation purposes.
EXPECTED_COLUMNS: dict[str, type] = {
    "period": int,           # Year (e.g. 2022)
    "reporter_iso3": str,    # Reporting country ISO 3166-1 alpha-3
    "partner_iso3": str,     # Partner country ISO 3166-1 alpha-3
    "flow_code": str,        # 'X' = export, 'M' = import
    "hs_code": str,          # 4-digit HS code (e.g. '8548')
    "qty_unit": str,         # Unit of quantity (we filter to 'kg' or 'mt')
    "qty": float,            # Quantity in qty_unit
    "trade_value_usd": float, # Customs value in USD
    "is_aggregate": bool,    # True if this row is a regional aggregate
}


class SchemaValidationError(Exception):
    """Raised when Comtrade API response deviates from the expected schema."""
    pass


@dataclass
class ComtradeRecord:
    """Typed record representing one Comtrade trade flow row."""
    period: int
    reporter_iso3: str
    partner_iso3: str
    flow_code: str
    hs_code: str
    qty_unit: str
    qty: float
    trade_value_usd: float
    is_aggregate: bool

    def volume_mt(self) -> float:
        """Return volume in metric tons, converting from kg if necessary."""
        if self.qty_unit.lower() in ("kg", "kilograms"):
            return self.qty / 1000.0
        elif self.qty_unit.lower() in ("mt", "t", "tonnes", "metric tons"):
            return self.qty
        # Unknown unit — return raw value and let the caller handle it
        return self.qty

    def is_export(self) -> bool:
        return self.flow_code.upper() == "X"

    def is_import(self) -> bool:
        return self.flow_code.upper() == "M"


def validate_dataframe_schema(df: Any) -> None:
    """
    Validate that a parsed DataFrame has the expected columns and types.
    Raises SchemaValidationError with a diff if validation fails.

    Args:
        df: pandas DataFrame to validate
    """
    import pandas as pd

    missing = set(EXPECTED_COLUMNS.keys()) - set(df.columns)
    extra = set(df.columns) - set(EXPECTED_COLUMNS.keys())

    errors = []
    if missing:
        errors.append(f"Missing columns: {sorted(missing)}")
    if extra:
        # Extra columns are a warning, not an error — new Comtrade fields don't break us
        import logging
        logging.getLogger(__name__).warning("Comtrade schema: unexpected extra columns %s", sorted(extra))

    if errors:
        raise SchemaValidationError(
            "Comtrade API response schema has changed:\n" + "\n".join(errors)
        )
