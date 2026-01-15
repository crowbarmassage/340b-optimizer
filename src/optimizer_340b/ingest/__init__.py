"""Data ingestion module for 340B Optimizer.

This module handles loading and validating raw data files (Bronze Layer).
"""

from optimizer_340b.ingest.loaders import (
    detect_file_type,
    load_csv_to_polars,
    load_excel_to_polars,
    load_file_auto,
)
from optimizer_340b.ingest.validators import (
    ValidationResult,
    validate_asp_quarter,
    validate_asp_schema,
    validate_catalog_row_volume,
    validate_catalog_schema,
    validate_crosswalk_integrity,
    validate_crosswalk_schema,
    validate_top_drugs_pricing,
)

__all__ = [
    # Loaders
    "load_excel_to_polars",
    "load_csv_to_polars",
    "load_file_auto",
    "detect_file_type",
    # Validators
    "ValidationResult",
    "validate_catalog_schema",
    "validate_catalog_row_volume",
    "validate_asp_schema",
    "validate_asp_quarter",
    "validate_crosswalk_schema",
    "validate_crosswalk_integrity",
    "validate_top_drugs_pricing",
]
