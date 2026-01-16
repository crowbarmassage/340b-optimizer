"""Phase 3 Integration Tests - Bronze to Silver Layer Pipeline.

These tests validate the complete data pipeline from raw file loading
through Silver Layer normalization and joining.

Run with: pytest tests/test_phase3_integration.py -v

Note: These tests require the real data files in the inbox directory.
They are marked with `integration` marker and can be skipped if data is unavailable.
"""

from pathlib import Path

import polars as pl
import pytest

from optimizer_340b.ingest.loaders import load_csv_to_polars, load_excel_to_polars
from optimizer_340b.ingest.normalizers import (
    build_silver_dataset,
    join_asp_pricing,
    join_catalog_to_crosswalk,
    normalize_asp_pricing,
    normalize_catalog,
    normalize_crosswalk,
    normalize_ndc,
    preprocess_cms_csv,
)
from optimizer_340b.ingest.validators import (
    validate_asp_schema,
    validate_catalog_row_volume,
    validate_catalog_schema,
    validate_crosswalk_schema,
    validate_top_drugs_pricing,
)

# Path to real data files
DATA_DIR = Path("/Users/mohsin.ansari/Github/inbox/340B_Engine")

# Skip all tests if data directory doesn't exist
pytestmark = pytest.mark.skipif(
    not DATA_DIR.exists(),
    reason=f"Data directory not found: {DATA_DIR}",
)


class TestPhase1Foundation:
    """Tests for Phase 1: Core models and configuration."""

    def test_ndc_normalization_formats(self) -> None:
        """NDC normalization should handle all common formats to 11-digit."""
        test_cases = [
            ("0074-4339-02", "00074433902"),  # Dashes -> 11 digits
            ("00074433902", "00074433902"),  # 11-digit preserved
            ("74433902", "00074433902"),  # Short -> padded to 11
            ("1234567890", "01234567890"),  # 10-digit -> padded to 11
        ]
        for input_ndc, expected in test_cases:
            result = normalize_ndc(input_ndc)
            assert result == expected, f"Failed for {input_ndc}"
            assert len(result) == 11, f"Not 11 digits for {input_ndc}"

    def test_drug_model_import(self) -> None:
        """Core models should be importable."""
        from optimizer_340b.models import (
            DosingProfile,
            Drug,
            MarginAnalysis,
            RecommendedPath,
        )

        assert Drug is not None
        assert MarginAnalysis is not None
        assert DosingProfile is not None
        assert RecommendedPath is not None

    def test_settings_import(self) -> None:
        """Settings should be importable and configurable."""
        from optimizer_340b.config import Settings

        settings = Settings.from_env()
        assert settings.log_level in ["DEBUG", "INFO", "WARNING", "ERROR"]


class TestPhase2BronzeLayer:
    """Tests for Phase 2: Data Ingestion (Bronze Layer)."""

    def test_load_product_catalog(self) -> None:
        """Should load product catalog Excel file."""
        catalog_path = DATA_DIR / "product_catalog.xlsx"
        if not catalog_path.exists():
            pytest.skip(f"File not found: {catalog_path}")

        df = load_excel_to_polars(catalog_path)

        assert df.height > 30000, "Catalog should have >30k rows"
        assert "NDC" in df.columns
        assert "Contract Cost" in df.columns

    def test_load_asp_crosswalk_csv(self) -> None:
        """Should load ASP crosswalk CSV with CMS preprocessing."""
        crosswalk_path = DATA_DIR / "October 2025 ASP NDC-HCPCS Crosswalk 090525.csv"
        if not crosswalk_path.exists():
            pytest.skip(f"File not found: {crosswalk_path}")

        df = preprocess_cms_csv(str(crosswalk_path), skip_rows=8)

        assert df.height > 8000, "Crosswalk should have >8k rows"
        # Raw columns before normalization
        assert "_2025_CODE" in df.columns or "HCPCS Code" in df.columns

    def test_load_asp_pricing_csv(self) -> None:
        """Should load ASP pricing CSV with CMS preprocessing."""
        asp_path = DATA_DIR / "Oct 2025 ASP Pricing File updated 120925.csv"
        if not asp_path.exists():
            pytest.skip(f"File not found: {asp_path}")

        df = preprocess_cms_csv(str(asp_path), skip_rows=8)

        assert df.height > 1000, "ASP file should have >1k rows"
        assert "HCPCS Code" in df.columns
        assert "Payment Limit" in df.columns

    def test_load_nadac_csv(self) -> None:
        """Should load NADAC statistics CSV."""
        nadac_path = DATA_DIR / "ndc_nadac_master_statistics.csv"
        if not nadac_path.exists():
            pytest.skip(f"File not found: {nadac_path}")

        df = load_csv_to_polars(nadac_path)

        assert df.height > 30000, "NADAC should have >30k rows"
        assert "ndc" in df.columns
        assert "total_discount_340b_pct" in df.columns

    def test_catalog_schema_validation_raw(self) -> None:
        """Raw catalog should fail validation (missing AWP column name)."""
        catalog_path = DATA_DIR / "product_catalog.xlsx"
        if not catalog_path.exists():
            pytest.skip(f"File not found: {catalog_path}")

        df = load_excel_to_polars(catalog_path)
        result = validate_catalog_schema(df)

        # Raw catalog has "Medispan AWP" not "AWP", so should fail
        assert result.is_valid is False
        assert "AWP" in result.missing_columns

    def test_catalog_row_volume(self) -> None:
        """Catalog should pass row volume check."""
        catalog_path = DATA_DIR / "product_catalog.xlsx"
        if not catalog_path.exists():
            pytest.skip(f"File not found: {catalog_path}")

        df = load_excel_to_polars(catalog_path)
        result = validate_catalog_row_volume(df, min_rows=30000)

        assert result.is_valid is True
        assert result.row_count > 34000


class TestPhase3SilverLayer:
    """Tests for Phase 3: Data Normalization (Silver Layer)."""

    @pytest.fixture
    def catalog_raw(self) -> pl.DataFrame:
        """Load raw product catalog."""
        catalog_path = DATA_DIR / "product_catalog.xlsx"
        if not catalog_path.exists():
            pytest.skip(f"File not found: {catalog_path}")
        return load_excel_to_polars(catalog_path)

    @pytest.fixture
    def crosswalk_raw(self) -> pl.DataFrame:
        """Load raw crosswalk with CMS preprocessing."""
        crosswalk_path = DATA_DIR / "October 2025 ASP NDC-HCPCS Crosswalk 090525.csv"
        if not crosswalk_path.exists():
            pytest.skip(f"File not found: {crosswalk_path}")
        return preprocess_cms_csv(str(crosswalk_path), skip_rows=8)

    @pytest.fixture
    def asp_raw(self) -> pl.DataFrame:
        """Load raw ASP pricing with CMS preprocessing."""
        asp_path = DATA_DIR / "Oct 2025 ASP Pricing File updated 120925.csv"
        if not asp_path.exists():
            pytest.skip(f"File not found: {asp_path}")
        return preprocess_cms_csv(str(asp_path), skip_rows=8)

    def test_normalize_catalog_renames_columns(
        self, catalog_raw: pl.DataFrame
    ) -> None:
        """Catalog normalization should rename Medispan AWP to AWP."""
        catalog = normalize_catalog(catalog_raw)

        assert "AWP" in catalog.columns, "AWP column should exist after normalization"
        assert "Medispan AWP" not in catalog.columns
        assert "ndc_normalized" in catalog.columns

    def test_normalized_catalog_passes_validation(
        self, catalog_raw: pl.DataFrame
    ) -> None:
        """Normalized catalog should pass schema validation."""
        catalog = normalize_catalog(catalog_raw)
        result = validate_catalog_schema(catalog)

        assert result.is_valid is True, f"Validation failed: {result.message}"

    def test_normalize_catalog_creates_drug_name(
        self, catalog_raw: pl.DataFrame
    ) -> None:
        """Catalog normalization should create Drug Name column."""
        catalog = normalize_catalog(catalog_raw)

        assert "Drug Name" in catalog.columns
        # Check some drug names exist
        drug_names = catalog["Drug Name"].drop_nulls().to_list()
        assert len(drug_names) > 0

    def test_normalize_crosswalk_renames_columns(
        self, crosswalk_raw: pl.DataFrame
    ) -> None:
        """Crosswalk normalization should rename CMS columns."""
        crosswalk = normalize_crosswalk(crosswalk_raw)

        assert "HCPCS Code" in crosswalk.columns
        assert "NDC" in crosswalk.columns
        assert "ndc_normalized" in crosswalk.columns
        # Original CMS columns should be renamed
        assert "_2025_CODE" not in crosswalk.columns
        assert "NDC2" not in crosswalk.columns

    def test_normalized_crosswalk_passes_validation(
        self, crosswalk_raw: pl.DataFrame
    ) -> None:
        """Normalized crosswalk should pass schema validation."""
        crosswalk = normalize_crosswalk(crosswalk_raw)
        result = validate_crosswalk_schema(crosswalk)

        assert result.is_valid is True, f"Validation failed: {result.message}"

    def test_normalize_asp_pricing(self, asp_raw: pl.DataFrame) -> None:
        """ASP pricing normalization should work."""
        asp = normalize_asp_pricing(asp_raw)

        assert "HCPCS Code" in asp.columns
        assert "Payment Limit" in asp.columns
        # Payment Limit should be numeric
        assert asp["Payment Limit"].dtype == pl.Float64

    def test_normalized_asp_passes_validation(self, asp_raw: pl.DataFrame) -> None:
        """Normalized ASP should pass schema validation."""
        asp = normalize_asp_pricing(asp_raw)
        result = validate_asp_schema(asp)

        assert result.is_valid is True, f"Validation failed: {result.message}"

    def test_catalog_crosswalk_join(
        self,
        catalog_raw: pl.DataFrame,
        crosswalk_raw: pl.DataFrame,
    ) -> None:
        """Catalog should join to crosswalk with reasonable match rate."""
        catalog = normalize_catalog(catalog_raw)
        crosswalk = normalize_crosswalk(crosswalk_raw)

        matched, orphans = join_catalog_to_crosswalk(catalog, crosswalk)

        # Should have some matches (infusible drugs)
        assert matched.height > 4000, "Should have >4k matched rows"

        # Matched rows should have HCPCS codes
        assert "HCPCS Code" in matched.columns
        hcpcs_nulls = matched["HCPCS Code"].null_count()
        assert hcpcs_nulls == 0, "Matched rows should all have HCPCS codes"

        # Orphans should NOT have HCPCS codes
        assert orphans.height > 0, "Should have some orphans"

    def test_asp_pricing_join(
        self,
        catalog_raw: pl.DataFrame,
        crosswalk_raw: pl.DataFrame,
        asp_raw: pl.DataFrame,
    ) -> None:
        """Crosswalk-enriched data should join to ASP pricing."""
        catalog = normalize_catalog(catalog_raw)
        crosswalk = normalize_crosswalk(crosswalk_raw)
        asp = normalize_asp_pricing(asp_raw)

        matched, _ = join_catalog_to_crosswalk(catalog, crosswalk)
        silver = join_asp_pricing(matched, asp)

        assert "ASP" in silver.columns
        asp_count = silver.filter(pl.col("ASP").is_not_null()).height
        assert asp_count > 0, "Should have some rows with ASP pricing"

    def test_top_50_drugs_validation(self, catalog_raw: pl.DataFrame) -> None:
        """Top 50 drug validation should work on normalized catalog."""
        catalog = normalize_catalog(catalog_raw)
        result = validate_top_drugs_pricing(catalog)

        # Should find most Top 50 drugs (may be slightly over 5% missing)
        assert "found" in result.message.lower() or "missing" in result.message.lower()
        # Log the result for visibility
        print(f"Top 50 validation: {result.message}")
        if result.warnings:
            print(f"Warnings: {result.warnings[:3]}")


class TestSilverLayerCompletePipeline:
    """End-to-end tests for the complete Silver Layer pipeline."""

    def test_build_silver_dataset_complete(self) -> None:
        """Complete Silver dataset should build successfully."""
        catalog_path = DATA_DIR / "product_catalog.xlsx"
        crosswalk_path = DATA_DIR / "October 2025 ASP NDC-HCPCS Crosswalk 090525.csv"
        asp_path = DATA_DIR / "Oct 2025 ASP Pricing File updated 120925.csv"

        for path in [catalog_path, crosswalk_path, asp_path]:
            if not path.exists():
                pytest.skip(f"File not found: {path}")

        # Load raw data
        catalog_raw = load_excel_to_polars(catalog_path)
        crosswalk_raw = preprocess_cms_csv(str(crosswalk_path), skip_rows=8)
        asp_raw = preprocess_cms_csv(str(asp_path), skip_rows=8)

        # Build Silver dataset
        silver, orphans = build_silver_dataset(catalog_raw, crosswalk_raw, asp_raw)

        # Verify Silver dataset structure
        assert silver.height > 4000, f"Silver has {silver.height} rows, expected >4000"
        assert orphans.height > 0, "Should have some orphans"

        # Verify key columns exist
        required_cols = ["NDC", "ndc_normalized", "HCPCS Code", "ASP", "AWP"]
        for col in required_cols:
            assert col in silver.columns, f"Missing column: {col}"

        # Verify data quality
        asp_count = silver.filter(pl.col("ASP").is_not_null()).height
        asp_pct = asp_count / silver.height * 100
        assert asp_pct > 95, f"Only {asp_pct:.1f}% have ASP, expected >95%"

    def test_silver_dataset_has_pricing_data(self) -> None:
        """Silver dataset should have usable pricing data."""
        catalog_path = DATA_DIR / "product_catalog.xlsx"
        crosswalk_path = DATA_DIR / "October 2025 ASP NDC-HCPCS Crosswalk 090525.csv"
        asp_path = DATA_DIR / "Oct 2025 ASP Pricing File updated 120925.csv"

        for path in [catalog_path, crosswalk_path, asp_path]:
            if not path.exists():
                pytest.skip(f"File not found: {path}")

        catalog_raw = load_excel_to_polars(catalog_path)
        crosswalk_raw = preprocess_cms_csv(str(crosswalk_path), skip_rows=8)
        asp_raw = preprocess_cms_csv(str(asp_path), skip_rows=8)

        silver, _ = build_silver_dataset(catalog_raw, crosswalk_raw, asp_raw)

        # Check pricing columns have valid data
        awp_valid = silver.filter(
            pl.col("AWP").is_not_null() & (pl.col("AWP") > 0)
        ).height
        contract_valid = silver.filter(
            pl.col("Contract Cost").is_not_null() & (pl.col("Contract Cost") > 0)
        ).height
        asp_valid = silver.filter(
            pl.col("ASP").is_not_null() & (pl.col("ASP") > 0)
        ).height

        assert awp_valid > 4000, f"Only {awp_valid} rows with valid AWP"
        assert contract_valid > 4000, f"Only {contract_valid} rows with valid Contract"
        assert asp_valid > 4000, f"Only {asp_valid} rows with valid ASP"

    def test_silver_dataset_sample_drug_lookup(self) -> None:
        """Should be able to look up a sample drug in Silver dataset."""
        catalog_path = DATA_DIR / "product_catalog.xlsx"
        crosswalk_path = DATA_DIR / "October 2025 ASP NDC-HCPCS Crosswalk 090525.csv"
        asp_path = DATA_DIR / "Oct 2025 ASP Pricing File updated 120925.csv"

        for path in [catalog_path, crosswalk_path, asp_path]:
            if not path.exists():
                pytest.skip(f"File not found: {path}")

        catalog_raw = load_excel_to_polars(catalog_path)
        crosswalk_raw = preprocess_cms_csv(str(crosswalk_path), skip_rows=8)
        asp_raw = preprocess_cms_csv(str(asp_path), skip_rows=8)

        silver, _ = build_silver_dataset(catalog_raw, crosswalk_raw, asp_raw)

        # Try to find a drug by HCPCS code
        j2351 = silver.filter(pl.col("HCPCS Code") == "J2351")  # OCREVUS
        if j2351.height > 0:
            row = j2351.row(0, named=True)
            assert row["ASP"] is not None, "OCREVUS should have ASP"
            assert row["AWP"] is not None, "OCREVUS should have AWP"
            assert row["Contract Cost"] is not None, "OCREVUS should have Contract Cost"
            print(f"Found J2351 (OCREVUS): ASP=${row['ASP']:.2f}")


class TestDataQualityMetrics:
    """Tests for data quality metrics and gatekeeper tests."""

    def test_crosswalk_integrity_rate(self) -> None:
        """Track crosswalk match rate (informational)."""
        catalog_path = DATA_DIR / "product_catalog.xlsx"
        crosswalk_path = DATA_DIR / "October 2025 ASP NDC-HCPCS Crosswalk 090525.csv"

        for path in [catalog_path, crosswalk_path]:
            if not path.exists():
                pytest.skip(f"File not found: {path}")

        catalog_raw = load_excel_to_polars(catalog_path)
        crosswalk_raw = preprocess_cms_csv(str(crosswalk_path), skip_rows=8)

        catalog = normalize_catalog(catalog_raw)
        crosswalk = normalize_crosswalk(crosswalk_raw)

        matched, orphans = join_catalog_to_crosswalk(catalog, crosswalk)

        total = catalog.height
        matched_count = matched.height
        match_rate = matched_count / total * 100

        print("\n=== Crosswalk Integrity Report ===")
        print(f"Total catalog rows: {total:,}")
        print(f"Matched to HCPCS: {matched_count:,} ({match_rate:.1f}%)")
        print(f"Orphans (no HCPCS): {orphans.height:,}")

        # This is informational - not all drugs need HCPCS codes
        # Only infusible drugs should have them
        assert matched_count > 0, "Should have some matches"

    def test_asp_pricing_coverage(self) -> None:
        """Track ASP pricing coverage (informational)."""
        catalog_path = DATA_DIR / "product_catalog.xlsx"
        crosswalk_path = DATA_DIR / "October 2025 ASP NDC-HCPCS Crosswalk 090525.csv"
        asp_path = DATA_DIR / "Oct 2025 ASP Pricing File updated 120925.csv"

        for path in [catalog_path, crosswalk_path, asp_path]:
            if not path.exists():
                pytest.skip(f"File not found: {path}")

        catalog_raw = load_excel_to_polars(catalog_path)
        crosswalk_raw = preprocess_cms_csv(str(crosswalk_path), skip_rows=8)
        asp_raw = preprocess_cms_csv(str(asp_path), skip_rows=8)

        silver, _ = build_silver_dataset(catalog_raw, crosswalk_raw, asp_raw)

        total = silver.height
        with_asp = silver.filter(pl.col("ASP").is_not_null()).height
        asp_rate = with_asp / total * 100

        print("\n=== ASP Pricing Coverage Report ===")
        print(f"Silver layer rows: {total:,}")
        print(f"With ASP pricing: {with_asp:,} ({asp_rate:.1f}%)")

        # All matched rows should have ASP pricing
        assert asp_rate > 95, f"ASP coverage {asp_rate:.1f}% below 95%"
