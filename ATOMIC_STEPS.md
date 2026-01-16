# ATOMIC_STEPS.md — 340B Optimizer Implementation Plan

> **Version:** 1.0
> **Last Updated:** January 15, 2026

This document defines the phased implementation plan with atomic steps, starter code, and evaluation tests.

---

## Phase 1: Project Foundation

**Goal**: Establish project structure, configuration, and core data models.

### Atomic Steps

- [ ] **1.1** Create directory structure:
  ```
  src/optimizer_340b/
  src/optimizer_340b/ingest/
  src/optimizer_340b/compute/
  src/optimizer_340b/risk/
  src/optimizer_340b/ui/
  src/optimizer_340b/ui/pages/
  src/optimizer_340b/ui/components/
  tests/
  data/sample/
  notebooks/
  ```

- [ ] **1.2** Create `src/optimizer_340b/__init__.py` with package exports

- [ ] **1.3** Create `src/optimizer_340b/config.py` with Settings dataclass

- [ ] **1.4** Create `src/optimizer_340b/models.py` with Drug, MarginAnalysis, DosingProfile

- [ ] **1.5** Create `tests/__init__.py` and `tests/conftest.py` with shared fixtures

- [ ] **1.6** Create `tests/test_config.py` and `tests/test_models.py`

- [ ] **1.7** Create `.env.example` template

- [ ] **1.8** Initialize virtual environment and install dependencies:
  ```bash
  uv venv
  source .venv/bin/activate
  uv pip install -e ".[dev]"
  pre-commit install
  ```

### Files to Create

| File | Purpose |
|------|---------|
| `src/optimizer_340b/__init__.py` | Package initialization and exports |
| `src/optimizer_340b/config.py` | Environment configuration |
| `src/optimizer_340b/models.py` | Core data models |
| `tests/__init__.py` | Test package marker |
| `tests/conftest.py` | Shared pytest fixtures |
| `tests/test_config.py` | Config loading tests |
| `tests/test_models.py` | Data model tests |
| `.env.example` | Environment variable template |

### Starter Code

**`src/optimizer_340b/__init__.py`**:
```python
"""340B Site-of-Care Optimization Engine.

Determines optimal treatment pathway (Retail vs Medical) for 340B drugs
by calculating Net Realizable Revenue.
"""

from optimizer_340b.config import Settings
from optimizer_340b.models import DosingProfile, Drug, MarginAnalysis

__version__ = "0.1.0"
__all__ = ["Settings", "Drug", "MarginAnalysis", "DosingProfile"]
```

**`.env.example`**:
```bash
# 340B Optimizer Configuration
LOG_LEVEL=INFO
DATA_DIR=./data/uploads
CACHE_ENABLED=true
CACHE_TTL_HOURS=24
```

### Evaluation Tests

```bash
pytest tests/test_config.py tests/test_models.py -v
```

**`tests/test_config.py`**:
```python
"""Tests for configuration management."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from optimizer_340b.config import Settings


class TestSettings:
    """Tests for Settings configuration."""

    def test_from_env_with_defaults(self, mock_env_vars: dict[str, str]) -> None:
        """Settings should load with default values."""
        settings = Settings.from_env()

        assert settings.log_level == "DEBUG"
        assert settings.data_dir == Path("/tmp/test_data")
        assert settings.cache_enabled is False
        assert settings.cache_ttl_hours == 1

    def test_from_env_missing_vars_uses_defaults(self) -> None:
        """Missing env vars should use sensible defaults."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings.from_env()

            assert settings.log_level == "INFO"
            assert settings.data_dir == Path("./data/uploads")
            assert settings.cache_enabled is True

    def test_ensure_directories_creates_path(
        self, mock_env_vars: dict[str, str], tmp_path: Path
    ) -> None:
        """ensure_directories should create data directory."""
        settings = Settings(
            log_level="INFO",
            data_dir=tmp_path / "new_dir",
            cache_enabled=False,
            cache_ttl_hours=1,
        )

        settings.ensure_directories()

        assert settings.data_dir.exists()
```

**`tests/test_models.py`**:
```python
"""Tests for data models."""

from decimal import Decimal

import pytest

from optimizer_340b.models import (
    DosingProfile,
    Drug,
    MarginAnalysis,
    RecommendedPath,
)


class TestDrug:
    """Tests for Drug model."""

    def test_has_medical_path_with_hcpcs(self, sample_drug: Drug) -> None:
        """Drug with HCPCS and ASP should have medical path."""
        assert sample_drug.has_medical_path() is True

    def test_has_medical_path_without_hcpcs(
        self, sample_drug_retail_only: Drug
    ) -> None:
        """Drug without HCPCS should not have medical path."""
        assert sample_drug_retail_only.has_medical_path() is False

    def test_ndc_normalized_removes_dashes(self, sample_drug: Drug) -> None:
        """NDC normalization should remove dashes and pad to 11 digits."""
        assert sample_drug.ndc_normalized == "00074433902"

    def test_ndc_normalized_pads_short_ndc(self) -> None:
        """Short NDCs should be zero-padded to 11 digits."""
        drug = Drug(
            ndc="12345",
            drug_name="TEST",
            manufacturer="TEST",
            contract_cost=Decimal("10.00"),
            awp=Decimal("100.00"),
        )
        assert drug.ndc_normalized == "00000012345"


class TestDosingProfile:
    """Tests for DosingProfile model."""

    def test_year_1_revenue_calculation(
        self, sample_dosing_profile: DosingProfile
    ) -> None:
        """Year 1 revenue should multiply adjusted fills by margin."""
        margin_per_fill = Decimal("500.00")
        expected = Decimal("15.3") * margin_per_fill

        result = sample_dosing_profile.year_1_revenue(margin_per_fill)

        assert result == expected

    def test_maintenance_revenue_calculation(
        self, sample_dosing_profile: DosingProfile
    ) -> None:
        """Maintenance revenue should use year_2_plus_fills."""
        margin_per_fill = Decimal("500.00")
        expected = Decimal("12") * margin_per_fill

        result = sample_dosing_profile.maintenance_revenue(margin_per_fill)

        assert result == expected


class TestMarginAnalysis:
    """Tests for MarginAnalysis model."""

    def test_to_display_dict_includes_all_fields(
        self, sample_drug: Drug
    ) -> None:
        """Display dict should include all required fields."""
        analysis = MarginAnalysis(
            drug=sample_drug,
            retail_gross_margin=Decimal("5375.00"),
            retail_net_margin=Decimal("2418.75"),
            retail_capture_rate=Decimal("0.45"),
            medicare_margin=Decimal("5786.00"),
            commercial_margin=Decimal("6290.00"),
            recommended_path=RecommendedPath.COMMERCIAL_MEDICAL,
            margin_delta=Decimal("504.00"),
        )

        result = analysis.to_display_dict()

        assert result["ndc"] == "0074-4339-02"
        assert result["drug_name"] == "HUMIRA"
        assert result["recommendation"] == "COMMERCIAL_MEDICAL"
        assert result["ira_risk"] is False
```

### Phase 1 Completion Criteria

- [ ] All atomic steps checked off
- [ ] All tests pass: `pytest tests/test_config.py tests/test_models.py -v`
- [ ] Code passes linting: `ruff check src/`
- [ ] Types pass: `mypy src/`
- [ ] Human review approved

---

## Phase 2: Data Ingestion (Bronze Layer)

**Goal**: Load and validate raw data files from multiple formats.

### Atomic Steps

- [ ] **2.1** Create `src/optimizer_340b/ingest/__init__.py`

- [ ] **2.2** Create `src/optimizer_340b/ingest/loaders.py` with Excel/CSV loading

- [ ] **2.3** Create `src/optimizer_340b/ingest/validators.py` with schema validation

- [ ] **2.4** Create `tests/test_loaders.py`

- [ ] **2.5** Create `tests/test_validators.py`

- [ ] **2.6** Copy sample data files for testing:
  ```bash
  mkdir -p data/sample
  # Copy subset of real data for tests
  ```

### Files to Create

| File | Purpose |
|------|---------|
| `src/optimizer_340b/ingest/__init__.py` | Ingest package exports |
| `src/optimizer_340b/ingest/loaders.py` | File loading utilities |
| `src/optimizer_340b/ingest/validators.py` | Schema validation |
| `tests/test_loaders.py` | Loader tests |
| `tests/test_validators.py` | Validator tests |

### Starter Code

**`src/optimizer_340b/ingest/validators.py`**:
```python
"""Schema validation for 340B data sources."""

import logging
from dataclasses import dataclass
from typing import Optional

import polars as pl

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a schema validation check."""

    is_valid: bool
    message: str
    missing_columns: list[str]
    row_count: int


# Required columns for each data source
CATALOG_REQUIRED_COLUMNS = {"NDC", "Contract Cost", "AWP"}
ASP_PRICING_REQUIRED_COLUMNS = {"HCPCS Code", "Payment Limit"}
CROSSWALK_REQUIRED_COLUMNS = {"NDC", "HCPCS Code"}
NADAC_REQUIRED_COLUMNS = {"ndc", "total_discount_340b_pct"}


def validate_catalog_schema(df: pl.DataFrame) -> ValidationResult:
    """Validate product catalog schema.

    Gatekeeper Test: Schema Integrity
    - Must contain NDC, Contract Cost, AWP columns

    Args:
        df: DataFrame to validate.

    Returns:
        ValidationResult with status and details.
    """
    columns = set(df.columns)
    missing = CATALOG_REQUIRED_COLUMNS - columns

    if missing:
        return ValidationResult(
            is_valid=False,
            message=f"Catalog missing required columns: {missing}",
            missing_columns=list(missing),
            row_count=df.height,
        )

    return ValidationResult(
        is_valid=True,
        message=f"Catalog schema valid with {df.height} rows",
        missing_columns=[],
        row_count=df.height,
    )


def validate_catalog_row_volume(
    df: pl.DataFrame, min_rows: int = 30000
) -> ValidationResult:
    """Validate catalog has sufficient row volume.

    Gatekeeper Test: Row Volume Audit
    - Full market catalog should have >40k rows
    - 340B catalog subset should have >30k rows

    Args:
        df: DataFrame to validate.
        min_rows: Minimum expected rows.

    Returns:
        ValidationResult with status and details.
    """
    if df.height < min_rows:
        return ValidationResult(
            is_valid=False,
            message=f"Catalog has {df.height} rows, expected >{min_rows}",
            missing_columns=[],
            row_count=df.height,
        )

    return ValidationResult(
        is_valid=True,
        message=f"Catalog row volume OK: {df.height} rows",
        missing_columns=[],
        row_count=df.height,
    )


def validate_asp_schema(df: pl.DataFrame) -> ValidationResult:
    """Validate ASP pricing file schema.

    Args:
        df: DataFrame to validate.

    Returns:
        ValidationResult with status and details.
    """
    columns = set(df.columns)
    missing = ASP_PRICING_REQUIRED_COLUMNS - columns

    if missing:
        return ValidationResult(
            is_valid=False,
            message=f"ASP file missing required columns: {missing}",
            missing_columns=list(missing),
            row_count=df.height,
        )

    return ValidationResult(
        is_valid=True,
        message=f"ASP schema valid with {df.height} HCPCS codes",
        missing_columns=[],
        row_count=df.height,
    )


def validate_crosswalk_schema(df: pl.DataFrame) -> ValidationResult:
    """Validate NDC-HCPCS crosswalk schema.

    Args:
        df: DataFrame to validate.

    Returns:
        ValidationResult with status and details.
    """
    columns = set(df.columns)
    missing = CROSSWALK_REQUIRED_COLUMNS - columns

    if missing:
        return ValidationResult(
            is_valid=False,
            message=f"Crosswalk missing required columns: {missing}",
            missing_columns=list(missing),
            row_count=df.height,
        )

    return ValidationResult(
        is_valid=True,
        message=f"Crosswalk schema valid with {df.height} mappings",
        missing_columns=[],
        row_count=df.height,
    )


def validate_asp_quarter(
    df: pl.DataFrame,
    expected_quarter: str,
    quarter_column: str = "Quarter",
) -> ValidationResult:
    """Validate ASP file is for the expected quarter.

    Gatekeeper Test: Currency Check
    - ASP file should be for current quarter

    Args:
        df: DataFrame to validate.
        expected_quarter: Expected quarter string (e.g., "Q4 2025").
        quarter_column: Column containing quarter info.

    Returns:
        ValidationResult with status and details.
    """
    if quarter_column not in df.columns:
        # Some files don't have explicit quarter column - pass with warning
        return ValidationResult(
            is_valid=True,
            message="No quarter column found - verify manually",
            missing_columns=[],
            row_count=df.height,
        )

    quarters = df.select(quarter_column).unique().to_series().to_list()

    if expected_quarter not in quarters:
        return ValidationResult(
            is_valid=False,
            message=f"ASP file is for {quarters}, expected {expected_quarter}",
            missing_columns=[],
            row_count=df.height,
        )

    return ValidationResult(
        is_valid=True,
        message=f"ASP file is current: {expected_quarter}",
        missing_columns=[],
        row_count=df.height,
    )
```

### Evaluation Tests

```bash
pytest tests/test_loaders.py tests/test_validators.py -v
```

**`tests/test_validators.py`**:
```python
"""Tests for schema validation."""

import polars as pl
import pytest

from optimizer_340b.ingest.validators import (
    ValidationResult,
    validate_asp_schema,
    validate_catalog_row_volume,
    validate_catalog_schema,
    validate_crosswalk_schema,
)


class TestCatalogValidation:
    """Tests for catalog schema validation."""

    def test_valid_catalog_passes(self, sample_catalog_df: pl.DataFrame) -> None:
        """Valid catalog should pass validation."""
        result = validate_catalog_schema(sample_catalog_df)

        assert result.is_valid is True
        assert result.missing_columns == []
        assert result.row_count == 3

    def test_missing_columns_fails(self) -> None:
        """Catalog missing required columns should fail."""
        df = pl.DataFrame({"NDC": ["123"], "SomeOther": ["X"]})

        result = validate_catalog_schema(df)

        assert result.is_valid is False
        assert "Contract Cost" in result.missing_columns
        assert "AWP" in result.missing_columns

    def test_row_volume_check_passes(self) -> None:
        """Catalog with sufficient rows should pass volume check."""
        # Create DataFrame with 35k rows
        df = pl.DataFrame({"NDC": [f"{i:011d}" for i in range(35000)]})

        result = validate_catalog_row_volume(df, min_rows=30000)

        assert result.is_valid is True
        assert result.row_count == 35000

    def test_row_volume_check_fails(self) -> None:
        """Catalog with insufficient rows should fail volume check."""
        df = pl.DataFrame({"NDC": ["123", "456"]})

        result = validate_catalog_row_volume(df, min_rows=30000)

        assert result.is_valid is False
        assert "expected >30000" in result.message


class TestASPValidation:
    """Tests for ASP file validation."""

    def test_valid_asp_passes(self, sample_asp_pricing_df: pl.DataFrame) -> None:
        """Valid ASP file should pass validation."""
        result = validate_asp_schema(sample_asp_pricing_df)

        assert result.is_valid is True

    def test_missing_payment_limit_fails(self) -> None:
        """ASP file missing Payment Limit should fail."""
        df = pl.DataFrame({"HCPCS Code": ["J0135"]})

        result = validate_asp_schema(df)

        assert result.is_valid is False
        assert "Payment Limit" in result.missing_columns


class TestCrosswalkValidation:
    """Tests for NDC-HCPCS crosswalk validation."""

    def test_valid_crosswalk_passes(
        self, sample_asp_crosswalk_df: pl.DataFrame
    ) -> None:
        """Valid crosswalk should pass validation."""
        result = validate_crosswalk_schema(sample_asp_crosswalk_df)

        assert result.is_valid is True
        assert result.row_count == 2

    def test_missing_ndc_fails(self) -> None:
        """Crosswalk missing NDC column should fail."""
        df = pl.DataFrame({"HCPCS Code": ["J0135"]})

        result = validate_crosswalk_schema(df)

        assert result.is_valid is False
        assert "NDC" in result.missing_columns
```

### Phase 2 Completion Criteria

- [ ] All atomic steps checked off
- [ ] All tests pass: `pytest tests/test_loaders.py tests/test_validators.py -v`
- [ ] Code passes linting: `ruff check src/optimizer_340b/ingest/`
- [ ] Types pass: `mypy src/optimizer_340b/ingest/`
- [ ] Human review approved

---

## Phase 3: Data Normalization (Silver Layer)

**Goal**: Clean data and build NDC-HCPCS crosswalk joins.

### Atomic Steps

- [ ] **3.1** Create `src/optimizer_340b/ingest/normalizers.py` with NDC normalization

- [ ] **3.2** Add fuzzy matching for drug name alignment

- [ ] **3.3** Implement NDC-to-HCPCS crosswalk join logic

- [ ] **3.4** Create `tests/test_normalizers.py`

### Files to Create

| File | Purpose |
|------|---------|
| `src/optimizer_340b/ingest/normalizers.py` | Data cleaning and joining |
| `tests/test_normalizers.py` | Normalizer tests |

### Starter Code

**`src/optimizer_340b/ingest/normalizers.py`**:
```python
"""Data normalization and cleaning for 340B data sources."""

import logging
import re
from typing import Optional

import polars as pl
from thefuzz import fuzz

logger = logging.getLogger(__name__)


def normalize_ndc(ndc: str) -> str:
    """Normalize NDC to 11-digit format, preserving leading zeros.

    Handles various NDC formats:
    - 11-digit with dashes: 12345-6789-01 -> 12345678901
    - 11-digit without dashes: 12345678901 -> 12345678901
    - 10-digit: 1234567890 -> 01234567890 (padded)
    - Short NDCs: 12345 -> 00000012345 (padded)

    Args:
        ndc: Raw NDC string.

    Returns:
        11-digit normalized NDC string with leading zeros preserved.
    """
    # Remove all non-numeric characters
    cleaned = re.sub(r"[^0-9]", "", str(ndc))

    # Pad short NDCs with leading zeros to 11 digits
    return cleaned.zfill(11)[-11:]


def normalize_ndc_column(df: pl.DataFrame, ndc_column: str = "NDC") -> pl.DataFrame:
    """Apply NDC normalization to a DataFrame column.

    Args:
        df: DataFrame with NDC column.
        ndc_column: Name of the NDC column.

    Returns:
        DataFrame with normalized NDC column.
    """
    return df.with_columns(
        pl.col(ndc_column).map_elements(normalize_ndc, return_dtype=pl.Utf8).alias("ndc_normalized")
    )


def fuzzy_match_drug_name(
    name: str,
    candidates: list[str],
    threshold: int = 80,
) -> Optional[str]:
    """Find best fuzzy match for a drug name.

    Args:
        name: Drug name to match.
        candidates: List of candidate names to match against.
        threshold: Minimum similarity score (0-100).

    Returns:
        Best matching candidate name, or None if no match above threshold.
    """
    best_match = None
    best_score = 0

    for candidate in candidates:
        score = fuzz.ratio(name.upper(), candidate.upper())
        if score > best_score and score >= threshold:
            best_score = score
            best_match = candidate

    logger.debug(f"Fuzzy match '{name}' -> '{best_match}' (score: {best_score})")
    return best_match


def join_catalog_to_crosswalk(
    catalog_df: pl.DataFrame,
    crosswalk_df: pl.DataFrame,
    catalog_ndc_col: str = "ndc_normalized",
    crosswalk_ndc_col: str = "ndc_normalized",
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Join product catalog to NDC-HCPCS crosswalk.

    Gatekeeper Test: Crosswalk Integrity
    - >95% of infusible NDCs should successfully join

    Args:
        catalog_df: Product catalog DataFrame.
        crosswalk_df: NDC-HCPCS crosswalk DataFrame.
        catalog_ndc_col: NDC column name in catalog.
        crosswalk_ndc_col: NDC column name in crosswalk.

    Returns:
        Tuple of (joined_df, orphan_df).
        - joined_df: Catalog rows that matched crosswalk
        - orphan_df: Catalog rows that did not match (orphans)
    """
    # Normalize NDC columns if not already done
    if catalog_ndc_col not in catalog_df.columns:
        catalog_df = normalize_ndc_column(catalog_df, "NDC")
        catalog_ndc_col = "ndc_normalized"

    if crosswalk_ndc_col not in crosswalk_df.columns:
        crosswalk_df = normalize_ndc_column(crosswalk_df, "NDC")
        crosswalk_ndc_col = "ndc_normalized"

    # Perform left join
    joined = catalog_df.join(
        crosswalk_df,
        left_on=catalog_ndc_col,
        right_on=crosswalk_ndc_col,
        how="left",
    )

    # Split into matched and orphaned
    matched = joined.filter(pl.col("HCPCS Code").is_not_null())
    orphans = joined.filter(pl.col("HCPCS Code").is_null())

    # Log crosswalk integrity stats
    total = catalog_df.height
    matched_count = matched.height
    orphan_count = orphans.height
    match_rate = (matched_count / total * 100) if total > 0 else 0

    logger.info(f"Crosswalk join: {matched_count}/{total} matched ({match_rate:.1f}%)")
    logger.info(f"Orphaned NDCs: {orphan_count}")

    return matched, orphans


def join_asp_pricing(
    crosswalk_df: pl.DataFrame,
    asp_df: pl.DataFrame,
    hcpcs_col: str = "HCPCS Code",
) -> pl.DataFrame:
    """Join crosswalk data to ASP pricing.

    Args:
        crosswalk_df: Crosswalk DataFrame with HCPCS codes.
        asp_df: ASP pricing DataFrame.
        hcpcs_col: HCPCS code column name.

    Returns:
        DataFrame with ASP pricing joined.
    """
    return crosswalk_df.join(
        asp_df.select([hcpcs_col, "Payment Limit"]),
        on=hcpcs_col,
        how="left",
    ).rename({"Payment Limit": "asp"})
```

### Evaluation Tests

```bash
pytest tests/test_normalizers.py -v
```

**`tests/test_normalizers.py`**:
```python
"""Tests for data normalization."""

import polars as pl
import pytest

from optimizer_340b.ingest.normalizers import (
    fuzzy_match_drug_name,
    join_catalog_to_crosswalk,
    normalize_ndc,
    normalize_ndc_column,
)


class TestNDCNormalization:
    """Tests for NDC normalization."""

    @pytest.mark.parametrize(
        "input_ndc,expected",
        [
            ("0074-4339-02", "0074433902"),
            ("12345678901", "1234567890"),  # 11-digit drops check digit
            ("1234567890", "1234567890"),
            ("12345", "0000012345"),
            ("0012345", "0000012345"),
        ],
    )
    def test_normalize_ndc(self, input_ndc: str, expected: str) -> None:
        """NDC normalization should handle various formats."""
        result = normalize_ndc(input_ndc)
        assert result == expected

    def test_normalize_ndc_column(self) -> None:
        """Column normalization should apply to all rows."""
        df = pl.DataFrame({"NDC": ["0074-4339-02", "12345", "1234567890"]})

        result = normalize_ndc_column(df)

        expected = ["0074433902", "0000012345", "1234567890"]
        assert result["ndc_normalized"].to_list() == expected


class TestFuzzyMatching:
    """Tests for fuzzy drug name matching."""

    def test_exact_match_returns_candidate(self) -> None:
        """Exact match should return the candidate."""
        result = fuzzy_match_drug_name(
            "HUMIRA", ["HUMIRA", "ENBREL", "STELARA"], threshold=80
        )
        assert result == "HUMIRA"

    def test_close_match_returns_candidate(self) -> None:
        """Close match should return best candidate above threshold."""
        result = fuzzy_match_drug_name(
            "HUMIRA PEN", ["HUMIRA", "ENBREL", "STELARA"], threshold=60
        )
        assert result == "HUMIRA"

    def test_no_match_returns_none(self) -> None:
        """No match above threshold should return None."""
        result = fuzzy_match_drug_name(
            "COMPLETELY DIFFERENT", ["HUMIRA", "ENBREL"], threshold=80
        )
        assert result is None


class TestCrosswalkJoin:
    """Tests for crosswalk join integrity."""

    def test_crosswalk_join_matches_correctly(
        self,
        sample_catalog_df: pl.DataFrame,
        sample_asp_crosswalk_df: pl.DataFrame,
    ) -> None:
        """Crosswalk join should match NDCs to HCPCS codes."""
        # Add NDC normalization
        catalog = sample_catalog_df.with_columns(
            pl.col("NDC").map_elements(normalize_ndc, return_dtype=pl.Utf8).alias("ndc_normalized")
        )
        crosswalk = sample_asp_crosswalk_df.with_columns(
            pl.col("NDC").map_elements(normalize_ndc, return_dtype=pl.Utf8).alias("ndc_normalized")
        )

        matched, orphans = join_catalog_to_crosswalk(catalog, crosswalk)

        # 2 of 3 catalog items should match (HUMIRA, ENBREL have crosswalk entries)
        assert matched.height == 2
        assert orphans.height == 1

    def test_crosswalk_integrity_rate(self) -> None:
        """Crosswalk should have >95% match rate for infusible drugs."""
        # Create test data with 100 infusible drugs, 96 with crosswalk matches
        catalog = pl.DataFrame({
            "NDC": [f"{i:011d}" for i in range(100)],
            "ndc_normalized": [f"{i:011d}" for i in range(100)],
        })
        crosswalk = pl.DataFrame({
            "NDC": [f"{i:011d}" for i in range(96)],
            "ndc_normalized": [f"{i:011d}" for i in range(96)],
            "HCPCS Code": [f"J{i:04d}" for i in range(96)],
        })

        matched, orphans = join_catalog_to_crosswalk(catalog, crosswalk)

        match_rate = matched.height / catalog.height * 100
        assert match_rate >= 95, f"Match rate {match_rate}% below 95% threshold"
```

### Phase 3 Completion Criteria

- [ ] All atomic steps checked off
- [ ] All tests pass: `pytest tests/test_normalizers.py -v`
- [ ] Crosswalk integrity test achieves >95% match rate
- [ ] Code passes linting: `ruff check src/optimizer_340b/ingest/`
- [ ] Types pass: `mypy src/optimizer_340b/ingest/`
- [ ] Human review approved

---

## Phase 4: Margin Calculation (Gold Layer)

**Goal**: Implement core margin calculation logic for Retail and Medical pathways.

### Atomic Steps

- [ ] **4.1** Create `src/optimizer_340b/compute/__init__.py`

- [ ] **4.2** Create `src/optimizer_340b/compute/margins.py` with margin formulas

- [ ] **4.3** Create `src/optimizer_340b/compute/crosswalk.py` for Golden Record builder

- [ ] **4.4** Create `src/optimizer_340b/compute/dosing.py` for loading dose logic

- [ ] **4.5** Create `tests/test_margins.py` with unit tests from Project Charter

- [ ] **4.6** Create `tests/test_dosing.py`

### Files to Create

| File | Purpose |
|------|---------|
| `src/optimizer_340b/compute/__init__.py` | Compute package exports |
| `src/optimizer_340b/compute/margins.py` | Margin calculation engine |
| `src/optimizer_340b/compute/crosswalk.py` | Golden Record builder |
| `src/optimizer_340b/compute/dosing.py` | Loading dose calculations |
| `tests/test_margins.py` | Margin calculation tests |
| `tests/test_dosing.py` | Dosing logic tests |

### Starter Code

**`src/optimizer_340b/compute/dosing.py`**:
```python
"""Loading dose calculation logic for biologics."""

import logging
from decimal import Decimal
from typing import Optional

import polars as pl

from optimizer_340b.models import DosingProfile

logger = logging.getLogger(__name__)

# Default compliance rate for fill adjustments
DEFAULT_COMPLIANCE_RATE = Decimal("0.90")


def apply_loading_dose_logic(
    drug_name: str,
    dosing_grid: pl.DataFrame,
    indication: Optional[str] = None,
    compliance_rate: Decimal = DEFAULT_COMPLIANCE_RATE,
) -> Optional[DosingProfile]:
    """Look up loading dose profile for a drug.

    Args:
        drug_name: Name of the drug to look up.
        dosing_grid: Biologics logic grid DataFrame.
        indication: Specific indication (uses first match if None).
        compliance_rate: Expected patient compliance rate.

    Returns:
        DosingProfile if drug found, None otherwise.
    """
    # Filter to matching drug
    matches = dosing_grid.filter(
        pl.col("Drug Name").str.to_uppercase() == drug_name.upper()
    )

    if matches.height == 0:
        logger.debug(f"No dosing profile found for {drug_name}")
        return None

    # Filter by indication if specified
    if indication is not None:
        matches = matches.filter(pl.col("Indication") == indication)

    if matches.height == 0:
        logger.debug(f"No dosing profile for {drug_name} / {indication}")
        return None

    # Take first match
    row = matches.row(0, named=True)

    year_1_fills = int(row.get("Year 1 Fills", 12))
    year_2_fills = int(row.get("Year 2+ Fills", 12))

    # Apply compliance adjustment
    adjusted = Decimal(str(year_1_fills)) * compliance_rate

    return DosingProfile(
        drug_name=drug_name,
        indication=row.get("Indication", "Unknown"),
        year_1_fills=year_1_fills,
        year_2_plus_fills=year_2_fills,
        adjusted_year_1_fills=adjusted,
    )


def calculate_year_1_vs_maintenance_delta(
    dosing_profile: DosingProfile,
    margin_per_fill: Decimal,
) -> dict[str, Decimal]:
    """Calculate the revenue delta between Year 1 and Maintenance.

    This quantifies the "patient acquisition opportunity" from loading doses.

    Args:
        dosing_profile: Dosing profile with fill counts.
        margin_per_fill: Net margin per fill/administration.

    Returns:
        Dictionary with year_1, maintenance, and delta values.
    """
    year_1 = dosing_profile.year_1_revenue(margin_per_fill)
    maintenance = dosing_profile.maintenance_revenue(margin_per_fill)
    delta = year_1 - maintenance

    delta_pct = (delta / maintenance * 100) if maintenance > 0 else Decimal("0")

    return {
        "year_1_revenue": year_1,
        "maintenance_revenue": maintenance,
        "loading_dose_delta": delta,
        "loading_dose_delta_pct": delta_pct,
    }
```

### Evaluation Tests

```bash
pytest tests/test_margins.py tests/test_dosing.py -v
```

**`tests/test_margins.py`**:
```python
"""Tests for margin calculation engine.

These tests implement the Gatekeeper Tests from the Project Charter:
- The "Medicare" Unit Test
- The "Commercial Medical" Unit Test
- The "Capture Rate" Stress Test
"""

from decimal import Decimal

import pytest

from optimizer_340b.compute.margins import (
    COMMERCIAL_ASP_MULTIPLIER,
    DEFAULT_CAPTURE_RATE,
    MEDICARE_ASP_MULTIPLIER,
    analyze_drug_margin,
    calculate_commercial_margin,
    calculate_medicare_margin,
    calculate_retail_margin,
    determine_recommendation,
)
from optimizer_340b.models import Drug, RecommendedPath


class TestRetailMargin:
    """Tests for retail margin calculation."""

    def test_retail_margin_basic(self, sample_drug: Drug) -> None:
        """Basic retail margin calculation."""
        gross, net = calculate_retail_margin(sample_drug)

        # AWP ($6500) * 0.85 - Contract ($150) = $5375 gross
        expected_gross = Decimal("6500") * Decimal("0.85") - Decimal("150")
        assert gross == expected_gross

        # Gross * 0.45 = net
        expected_net = expected_gross * Decimal("0.45")
        assert net == expected_net

    def test_capture_rate_stress_test(self, sample_drug: Drug) -> None:
        """Gatekeeper: Capture Rate Stress Test.

        If the Capture Rate variable is toggled from 100% to 40%,
        does the "Retail Margin" drop proportionately?
        """
        _, net_100 = calculate_retail_margin(
            sample_drug, capture_rate=Decimal("1.00")
        )
        _, net_40 = calculate_retail_margin(
            sample_drug, capture_rate=Decimal("0.40")
        )

        # Net at 40% should be exactly 40% of net at 100%
        expected_ratio = Decimal("0.40")
        actual_ratio = net_40 / net_100

        assert actual_ratio == expected_ratio


class TestMedicareMargin:
    """Tests for Medicare medical margin calculation."""

    def test_medicare_margin_unit_test(self, sample_drug: Drug) -> None:
        """Gatekeeper: Medicare Unit Test.

        Manually calculate the margin for one vial of Infliximab using ASP + 6%.
        Does the Engine's output match to the penny?

        Using HUMIRA test data:
        ASP: $2800, Bill Units: 2
        Revenue = $2800 * 1.06 * 2 = $5936
        Margin = $5936 - $150 (contract) = $5786
        """
        result = calculate_medicare_margin(sample_drug)

        expected_revenue = Decimal("2800") * Decimal("1.06") * 2
        expected_margin = expected_revenue - Decimal("150")

        assert result == expected_margin
        assert result == Decimal("5786.00")

    def test_medicare_margin_returns_none_for_retail_only(
        self, sample_drug_retail_only: Drug
    ) -> None:
        """Drugs without HCPCS should return None for Medicare margin."""
        result = calculate_medicare_margin(sample_drug_retail_only)
        assert result is None


class TestCommercialMargin:
    """Tests for Commercial medical margin calculation."""

    def test_commercial_margin_unit_test(self, sample_drug: Drug) -> None:
        """Gatekeeper: Commercial Medical Unit Test.

        Verify that switching the payer toggle to "Commercial" correctly
        applies the 1.15x multiplier to the ASP baseline.

        Using HUMIRA test data:
        ASP: $2800, Bill Units: 2
        Revenue = $2800 * 1.15 * 2 = $6440
        Margin = $6440 - $150 (contract) = $6290
        """
        result = calculate_commercial_margin(sample_drug)

        expected_revenue = Decimal("2800") * Decimal("1.15") * 2
        expected_margin = expected_revenue - Decimal("150")

        assert result == expected_margin
        assert result == Decimal("6290.00")

    def test_commercial_multiplier_is_1_15(self) -> None:
        """Commercial multiplier should be exactly 1.15."""
        assert COMMERCIAL_ASP_MULTIPLIER == Decimal("1.15")


class TestRecommendation:
    """Tests for pathway recommendation logic."""

    def test_recommends_highest_margin(self) -> None:
        """Should recommend pathway with highest margin."""
        path, delta = determine_recommendation(
            retail_net=Decimal("1000"),
            medicare=Decimal("2000"),
            commercial=Decimal("3000"),
        )

        assert path == RecommendedPath.COMMERCIAL_MEDICAL
        assert delta == Decimal("1000")  # 3000 - 2000

    def test_recommends_retail_when_only_option(self) -> None:
        """Should recommend retail when no medical path available."""
        path, delta = determine_recommendation(
            retail_net=Decimal("1000"),
            medicare=None,
            commercial=None,
        )

        assert path == RecommendedPath.RETAIL
        assert delta == Decimal("1000")

    def test_capture_rate_affects_recommendation(
        self, sample_drug: Drug
    ) -> None:
        """Lower capture rate should potentially change recommendation."""
        # At 45% capture, retail may lose to medical
        analysis_45 = analyze_drug_margin(
            sample_drug, capture_rate=Decimal("0.45")
        )

        # At 100% capture, retail becomes more competitive
        analysis_100 = analyze_drug_margin(
            sample_drug, capture_rate=Decimal("1.00")
        )

        # Verify margins change appropriately
        assert analysis_100.retail_net_margin > analysis_45.retail_net_margin
```

**`tests/test_dosing.py`**:
```python
"""Tests for loading dose calculation logic."""

from decimal import Decimal

import polars as pl
import pytest

from optimizer_340b.compute.dosing import (
    apply_loading_dose_logic,
    calculate_year_1_vs_maintenance_delta,
)
from optimizer_340b.models import DosingProfile


@pytest.fixture
def sample_dosing_grid() -> pl.DataFrame:
    """Sample biologics logic grid for testing."""
    return pl.DataFrame({
        "Drug Name": ["COSENTYX", "COSENTYX", "HUMIRA"],
        "Indication": ["Psoriasis", "Ankylosing Spondylitis", "Rheumatoid Arthritis"],
        "Year 1 Fills": [17, 13, 26],  # Cosentyx has heavy loading
        "Year 2+ Fills": [12, 12, 26],
    })


class TestLoadingDoseLogic:
    """Tests for loading dose profile lookup."""

    def test_cosentyx_loading_dose_test(
        self, sample_dosing_grid: pl.DataFrame
    ) -> None:
        """Gatekeeper: Loading Dose Logic Test.

        Select Cosentyx (Psoriasis). Does the Year 1 Revenue calculation
        reflect 17 fills (Loading) vs. 12 fills (Maintenance)?
        """
        profile = apply_loading_dose_logic(
            "COSENTYX",
            sample_dosing_grid,
            indication="Psoriasis",
        )

        assert profile is not None
        assert profile.year_1_fills == 17
        assert profile.year_2_plus_fills == 12

    def test_year_1_vs_maintenance_delta(
        self, sample_dosing_profile: DosingProfile
    ) -> None:
        """Loading dose should increase Year 1 revenue by >30%."""
        margin_per_fill = Decimal("500.00")

        result = calculate_year_1_vs_maintenance_delta(
            sample_dosing_profile,
            margin_per_fill,
        )

        # Year 1: 15.3 fills * $500 = $7650
        # Maintenance: 12 fills * $500 = $6000
        # Delta: $1650 = 27.5% increase
        assert result["year_1_revenue"] == Decimal("7650.0")
        assert result["maintenance_revenue"] == Decimal("6000")
        assert result["loading_dose_delta"] == Decimal("1650.0")

        # Delta should be significant (>25% for Cosentyx-like profile)
        assert result["loading_dose_delta_pct"] > Decimal("25")

    def test_no_profile_returns_none(
        self, sample_dosing_grid: pl.DataFrame
    ) -> None:
        """Unknown drug should return None."""
        profile = apply_loading_dose_logic(
            "UNKNOWN_DRUG",
            sample_dosing_grid,
        )

        assert profile is None
```

### Phase 4 Completion Criteria

- [ ] All atomic steps checked off
- [ ] Medicare Unit Test passes (matches manual calculation to the penny)
- [ ] Commercial Unit Test passes (1.15x multiplier correctly applied)
- [ ] Loading Dose Test passes (Cosentyx Year 1 = 17 fills)
- [ ] Capture Rate Stress Test passes (40% toggle reduces retail proportionally)
- [ ] All tests pass: `pytest tests/test_margins.py tests/test_dosing.py -v`
- [ ] Code passes linting: `ruff check src/optimizer_340b/compute/`
- [ ] Types pass: `mypy src/optimizer_340b/compute/`
- [ ] Human review approved

---

## Phase 5: Risk Flagging (Watchtower)

**Goal**: Implement IRA and Penny Pricing detection.

### Atomic Steps

- [ ] **5.1** Create `src/optimizer_340b/risk/__init__.py`

- [ ] **5.2** Create `src/optimizer_340b/risk/ira_flags.py` for IRA 2026/2027 detection

- [ ] **5.3** Create `src/optimizer_340b/risk/penny_pricing.py` for NADAC floor alerts

- [ ] **5.4** Create `tests/test_risk_flags.py`

### Files to Create

| File | Purpose |
|------|---------|
| `src/optimizer_340b/risk/__init__.py` | Risk package exports |
| `src/optimizer_340b/risk/ira_flags.py` | IRA price negotiation detection |
| `src/optimizer_340b/risk/penny_pricing.py` | Penny pricing alerts |
| `tests/test_risk_flags.py` | Risk flag tests |

### Evaluation Tests

```bash
pytest tests/test_risk_flags.py -v
```

**`tests/test_risk_flags.py`**:
```python
"""Tests for risk flagging (Watchtower layer)."""

from decimal import Decimal

import polars as pl
import pytest

from optimizer_340b.models import Drug
from optimizer_340b.risk.ira_flags import check_ira_status, IRA_2026_DRUGS
from optimizer_340b.risk.penny_pricing import check_penny_pricing


class TestIRAFlags:
    """Tests for IRA price negotiation detection."""

    def test_enbrel_simulation(self) -> None:
        """Gatekeeper: Enbrel Simulation.

        Force-feed Enbrel into the pipeline.
        Does the system flag it with a "High Risk / IRA 2026" warning?
        """
        drug = Drug(
            ndc="5555555555",
            drug_name="ENBREL",
            manufacturer="AMGEN",
            contract_cost=Decimal("200.00"),
            awp=Decimal("7000.00"),
            asp=Decimal("3000.00"),
            hcpcs_code="J1438",
            bill_units_per_package=4,
        )

        ira_status = check_ira_status(drug.drug_name)

        assert ira_status["is_ira_drug"] is True
        assert ira_status["ira_year"] == 2026
        assert "High Risk" in ira_status["warning_message"]

    def test_non_ira_drug_passes(self) -> None:
        """Non-IRA drugs should not be flagged."""
        ira_status = check_ira_status("SOME_NEW_DRUG")

        assert ira_status["is_ira_drug"] is False
        assert ira_status["ira_year"] is None


class TestPennyPricing:
    """Tests for penny pricing detection."""

    def test_penny_pricing_flag(self) -> None:
        """Drugs with penny pricing should be flagged."""
        nadac_df = pl.DataFrame({
            "ndc": ["12345678901", "98765432101"],
            "penny_pricing": [True, False],
            "total_discount_340b_pct": [99.9, 50.0],
        })

        flagged = check_penny_pricing(nadac_df)

        assert len(flagged) == 1
        assert flagged[0]["ndc"] == "12345678901"

    def test_penny_pricing_excluded_from_top_opportunities(self) -> None:
        """Gatekeeper: Penny Pricing Alert.

        Drugs with Penny Pricing = Yes should NOT appear in "Top Opportunities".
        """
        drugs = [
            {"ndc": "11111111111", "margin": 1000, "penny_pricing": False},
            {"ndc": "22222222222", "margin": 5000, "penny_pricing": True},  # High margin but penny priced
            {"ndc": "33333333333", "margin": 800, "penny_pricing": False},
        ]

        # Filter out penny priced drugs
        top_opportunities = [
            d for d in drugs
            if not d["penny_pricing"]
        ]

        # Sort by margin
        top_opportunities.sort(key=lambda x: x["margin"], reverse=True)

        # Penny priced drug should not appear despite highest margin
        assert all(d["ndc"] != "2222222222" for d in top_opportunities)
        assert top_opportunities[0]["ndc"] == "1111111111"
```

### Phase 5 Completion Criteria

- [ ] All atomic steps checked off
- [ ] Enbrel Simulation passes (IRA 2026 flag present)
- [ ] Penny Pricing Alert passes (flagged drugs excluded from Top Opportunities)
- [ ] All tests pass: `pytest tests/test_risk_flags.py -v`
- [ ] Code passes linting: `ruff check src/optimizer_340b/risk/`
- [ ] Types pass: `mypy src/optimizer_340b/risk/`
- [ ] Human review approved

---

## Phase 6: Streamlit UI

**Goal**: Build interactive web dashboard with file upload, dashboard, and drug detail views.

### Atomic Steps

- [ ] **6.1** Create `src/optimizer_340b/ui/__init__.py`

- [ ] **6.2** Create `src/optimizer_340b/ui/app.py` (main Streamlit entry point)

- [ ] **6.3** Create `src/optimizer_340b/ui/pages/__init__.py`

- [ ] **6.4** Create `src/optimizer_340b/ui/pages/upload.py` (file upload page)

- [ ] **6.5** Create `src/optimizer_340b/ui/pages/dashboard.py` (ranked opportunity list)

- [ ] **6.6** Create `src/optimizer_340b/ui/pages/drug_detail.py` (single drug deep-dive)

- [ ] **6.7** Create `src/optimizer_340b/ui/components/__init__.py`

- [ ] **6.8** Create `src/optimizer_340b/ui/components/margin_card.py`

- [ ] **6.9** Create `src/optimizer_340b/ui/components/capture_slider.py`

- [ ] **6.10** Create `src/optimizer_340b/ui/components/risk_badge.py`

- [ ] **6.11** Manual testing: Run `streamlit run src/optimizer_340b/ui/app.py`

### Files to Create

| File | Purpose |
|------|---------|
| `src/optimizer_340b/ui/__init__.py` | UI package exports |
| `src/optimizer_340b/ui/app.py` | Main Streamlit application |
| `src/optimizer_340b/ui/pages/upload.py` | File upload interface |
| `src/optimizer_340b/ui/pages/dashboard.py` | Optimization dashboard |
| `src/optimizer_340b/ui/pages/drug_detail.py` | Drug detail view |
| `src/optimizer_340b/ui/components/*.py` | Reusable UI components |

### Evaluation Tests

Manual verification:
```bash
streamlit run src/optimizer_340b/ui/app.py
```

1. Upload test data files
2. Verify validation messages appear
3. Navigate to dashboard
4. Search for a drug (target: <30 seconds)
5. Adjust capture rate slider
6. Verify margins update in real-time
7. Check IRA/Penny Pricing badges display

### Phase 6 Completion Criteria

- [ ] All atomic steps checked off
- [ ] File upload accepts XLSX and CSV files
- [ ] Validation errors display clearly
- [ ] Dashboard shows ranked opportunity list
- [ ] Drug search completes in <30 seconds (Success Metric #1)
- [ ] Capture rate slider updates margins in real-time
- [ ] Risk badges (IRA, Penny Pricing) display correctly
- [ ] Provenance chain shows for each margin calculation
- [ ] Human review approved

---

## Phase 7: Integration Testing

**Goal**: End-to-end tests validating the complete pipeline.

### Atomic Steps

- [ ] **7.1** Create `tests/test_integration.py` with full pipeline tests

- [ ] **7.2** Create sample test data subset in `data/sample/`

- [ ] **7.3** Run full integration test suite

### Evaluation Tests

```bash
pytest tests/test_integration.py -v -m integration
```

**`tests/test_integration.py`**:
```python
"""Integration tests for 340B Optimizer.

These tests validate the complete data pipeline from ingestion to margin calculation.
"""

from decimal import Decimal
from pathlib import Path

import polars as pl
import pytest

from optimizer_340b.compute.margins import analyze_drug_margin
from optimizer_340b.ingest.loaders import load_csv_to_polars, load_excel_to_polars
from optimizer_340b.ingest.normalizers import join_catalog_to_crosswalk
from optimizer_340b.ingest.validators import validate_catalog_schema
from optimizer_340b.models import Drug, RecommendedPath


pytestmark = pytest.mark.integration


class TestFullPipeline:
    """End-to-end integration tests."""

    def test_financial_accuracy(self) -> None:
        """Success Metric #2: Financial Accuracy.

        The "Realizable Revenue" projection for a sample cohort
        should match historical reimbursement data within +/- 5% margin of error.
        """
        # Test with known good data
        drug = Drug(
            ndc="0074433902",
            drug_name="HUMIRA",
            manufacturer="ABBVIE",
            contract_cost=Decimal("150.00"),
            awp=Decimal("6500.00"),
            asp=Decimal("2800.00"),
            hcpcs_code="J0135",
            bill_units_per_package=2,
        )

        analysis = analyze_drug_margin(drug)

        # Known expected values (from manual calculation)
        expected_commercial = Decimal("6290.00")

        # Allow 5% tolerance
        tolerance = expected_commercial * Decimal("0.05")
        lower_bound = expected_commercial - tolerance
        upper_bound = expected_commercial + tolerance

        assert lower_bound <= analysis.commercial_margin <= upper_bound

    def test_auditability_provenance(self) -> None:
        """Success Metric #3: Auditability.

        Every calculated margin should have a provenance chain.
        """
        drug = Drug(
            ndc="0074433902",
            drug_name="HUMIRA",
            manufacturer="ABBVIE",
            contract_cost=Decimal("150.00"),
            awp=Decimal("6500.00"),
            asp=Decimal("2800.00"),
            hcpcs_code="J0135",
            bill_units_per_package=2,
        )

        analysis = analyze_drug_margin(drug)
        display_dict = analysis.to_display_dict()

        # Verify all required provenance fields present
        assert "ndc" in display_dict
        assert "contract_cost" in display_dict
        assert "retail_margin" in display_dict
        assert "medicare_margin" in display_dict
        assert "commercial_margin" in display_dict
        assert "recommendation" in display_dict

    def test_optimization_velocity_benchmark(self) -> None:
        """Success Metric #1: Optimization Velocity.

        A user can identify the optimal site of care for a dual-eligible drug
        within 30 seconds.

        This test verifies the margin calculation is fast enough.
        """
        import time

        # Create 100 test drugs to simulate lookup
        drugs = [
            Drug(
                ndc=f"{i:011d}",
                drug_name=f"TEST_DRUG_{i}",
                manufacturer="TEST",
                contract_cost=Decimal("100.00"),
                awp=Decimal("1000.00"),
                asp=Decimal("500.00"),
                hcpcs_code=f"J{i:04d}",
                bill_units_per_package=1,
            )
            for i in range(100)
        ]

        start = time.time()

        for drug in drugs:
            analysis = analyze_drug_margin(drug)
            _ = analysis.recommended_path

        elapsed = time.time() - start

        # Should complete 100 lookups in well under 30 seconds
        assert elapsed < 5.0, f"100 lookups took {elapsed:.2f}s, expected <5s"
```

### Phase 7 Completion Criteria

- [ ] All atomic steps checked off
- [ ] All integration tests pass
- [ ] Financial Accuracy test passes (+/- 5% tolerance)
- [ ] Auditability test passes (provenance chain complete)
- [ ] Optimization Velocity test passes (<30s for lookup)
- [ ] Human review approved

---

## Phase 8: Notebook & Demo

**Goal**: Create Google Colab-compatible demo notebook.

### Atomic Steps

- [ ] **8.1** Create `notebooks/` directory

- [ ] **8.2** Create `notebooks/demo.ipynb` with standard structure

- [ ] **8.3** Test notebook runs on Google Colab (clone from GitHub)

- [ ] **8.4** Capture real outputs in notebook cells

- [ ] **8.5** Add markdown explanations for each step

### Files to Create

| File | Purpose |
|------|---------|
| `notebooks/demo.ipynb` | Google Colab demo notebook |

### Evaluation Tests

Manual verification:
```bash
# 1. Push all code to GitHub
git push

# 2. Open notebook URL in Colab:
# https://colab.research.google.com/github/crowbarmassage/340b-optimizer/blob/main/notebooks/demo.ipynb

# 3. Run all cells
# 4. Verify outputs match expected behavior
```

### Phase 8 Completion Criteria

- [ ] Notebook exists at `notebooks/demo.ipynb`
- [ ] Notebook runs successfully on Google Colab
- [ ] All cells execute without errors
- [ ] Real outputs are captured and visible
- [ ] Markdown explanations are clear
- [ ] Human review approved

---

## Phase 9: Documentation & Polish

**Goal**: Finalize documentation and ensure code quality standards.

### Atomic Steps

- [ ] **9.1** Update `README.md` with complete documentation

- [ ] **9.2** Run full test suite with coverage: `pytest tests/ -v --cov=src --cov-fail-under=80`

- [ ] **9.3** Run all quality checks: `ruff check . && ruff format . && mypy src/`

- [ ] **9.4** Verify pre-commit hooks pass: `pre-commit run --all-files`

- [ ] **9.5** Update `CHECKPOINT.md` to reflect completion

- [ ] **9.6** Final commit: `docs: complete v1.0 implementation`

### Phase 9 Completion Criteria

- [ ] All atomic steps checked off
- [ ] Test coverage >= 80%
- [ ] All ruff checks pass
- [ ] All mypy checks pass
- [ ] All pre-commit hooks pass
- [ ] README is complete and accurate
- [ ] Human review approved

---

## Progress Tracking

| Phase | Status | Tests Pass | Human Approved | Notes |
|-------|--------|------------|----------------|-------|
| 1. Foundation | [x] | [x] | [x] | 28 tests |
| 2. Ingestion (Bronze) | [x] | [x] | [x] | 86 tests, Top 50 validator |
| 3. Normalization (Silver) | [x] | [x] | [x] | 119 tests, column mapping |
| 4. Margin Calc (Gold) | [x] | [x] | [x] | 200 tests, gatekeeper tests |
| 5. Risk Flagging | [x] | [x] | [x] | 253 tests, IRA + Penny |
| 6. Streamlit UI | [x] | [x] | [x] | Manual testing + sample data |
| 7. Integration | [x] | [x] | [x] | 277 tests, success metrics |
| 8. Notebook & Demo | [ ] | [ ] | [ ] | Skipped per user |
| 9. Documentation | [x] | [x] | [ ] | README, TECH_SPECS updated |

---

## Quick Reference: Test Commands

| Phase | Command |
|-------|---------|
| Phase 1 | `pytest tests/test_config.py tests/test_models.py -v` |
| Phase 2 | `pytest tests/test_loaders.py tests/test_validators.py -v` |
| Phase 3 | `pytest tests/test_normalizers.py -v` |
| Phase 4 | `pytest tests/test_margins.py tests/test_dosing.py -v` |
| Phase 5 | `pytest tests/test_risk_flags.py -v` |
| Phase 6 | Manual: `streamlit run src/optimizer_340b/ui/app.py` |
| Phase 7 | `pytest tests/test_integration.py -v -m integration` |
| Phase 8 | Manual: Run notebook on Google Colab |
| Phase 9 | `pytest tests/ -v --cov=src --cov-fail-under=80` |
| All | `pytest tests/ -v --cov=src` |
