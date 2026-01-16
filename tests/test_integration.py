"""Integration tests for 340B Optimizer.

These tests validate the complete data pipeline from ingestion to margin calculation.
They use real sample data from data/sample/ to ensure end-to-end functionality.
"""

import time
from decimal import Decimal
from pathlib import Path

import polars as pl
import pytest

from optimizer_340b.compute.margins import analyze_drug_margin
from optimizer_340b.ingest.loaders import load_csv_to_polars, load_excel_to_polars
from optimizer_340b.ingest.normalizers import (
    join_catalog_to_crosswalk,
    normalize_catalog,
    normalize_crosswalk,
    preprocess_cms_csv,
)
from optimizer_340b.ingest.validators import (
    validate_asp_schema,
    validate_catalog_schema,
    validate_crosswalk_schema,
)
from optimizer_340b.models import Drug, RecommendedPath
from optimizer_340b.risk import check_ira_status
from optimizer_340b.risk.penny_pricing import (
    check_penny_pricing_for_drug,
)

pytestmark = pytest.mark.integration

# Sample data directory
SAMPLE_DATA_DIR = Path(__file__).parent.parent / "data" / "sample"


class TestDataIngestionPipeline:
    """Tests for the complete data ingestion pipeline."""

    @pytest.fixture
    def catalog_df(self) -> pl.DataFrame:
        """Load and normalize product catalog."""
        path = SAMPLE_DATA_DIR / "product_catalog.xlsx"
        if not path.exists():
            pytest.skip("Sample data not available")
        df = load_excel_to_polars(str(path))
        return normalize_catalog(df)

    @pytest.fixture
    def asp_pricing_df(self) -> pl.DataFrame:
        """Load ASP pricing data."""
        path = SAMPLE_DATA_DIR / "asp_pricing.csv"
        if not path.exists():
            pytest.skip("Sample data not available")
        return preprocess_cms_csv(str(path), skip_rows=8)

    @pytest.fixture
    def crosswalk_df(self) -> pl.DataFrame:
        """Load and normalize crosswalk data."""
        path = SAMPLE_DATA_DIR / "asp_crosswalk.csv"
        if not path.exists():
            pytest.skip("Sample data not available")
        df = preprocess_cms_csv(str(path), skip_rows=8)
        return normalize_crosswalk(df)

    @pytest.fixture
    def nadac_df(self) -> pl.DataFrame:
        """Load NADAC data."""
        path = SAMPLE_DATA_DIR / "ndc_nadac_master_statistics.csv"
        if not path.exists():
            pytest.skip("Sample data not available")
        return load_csv_to_polars(str(path))

    def test_catalog_loads_and_validates(self, catalog_df: pl.DataFrame) -> None:
        """Test that product catalog loads and passes validation."""
        result = validate_catalog_schema(catalog_df)
        assert result.is_valid, f"Catalog validation failed: {result.message}"
        assert catalog_df.height > 30000, "Expected >30k drugs in catalog"

    def test_asp_pricing_loads_and_validates(
        self, asp_pricing_df: pl.DataFrame
    ) -> None:
        """Test that ASP pricing loads and passes validation."""
        result = validate_asp_schema(asp_pricing_df)
        assert result.is_valid, f"ASP validation failed: {result.message}"
        assert asp_pricing_df.height > 900, "Expected >900 HCPCS codes"

    def test_crosswalk_loads_and_validates(self, crosswalk_df: pl.DataFrame) -> None:
        """Test that crosswalk loads and passes validation."""
        result = validate_crosswalk_schema(crosswalk_df)
        assert result.is_valid, f"Crosswalk validation failed: {result.message}"
        assert crosswalk_df.height > 8000, "Expected >8000 NDC-HCPCS mappings"

    def test_catalog_crosswalk_join(
        self, catalog_df: pl.DataFrame, crosswalk_df: pl.DataFrame
    ) -> None:
        """Test that catalog joins to crosswalk with expected match rate."""
        joined_df, orphan_df = join_catalog_to_crosswalk(catalog_df, crosswalk_df)

        # Verify we got meaningful joins
        assert joined_df.height > 4000, "Expected >4000 matched drugs"

        # Match rate should be ~14% for infusible drugs
        match_rate = joined_df.height / (joined_df.height + orphan_df.height)
        assert 0.10 <= match_rate <= 0.25, f"Unexpected match rate: {match_rate:.1%}"


class TestFinancialAccuracy:
    """Tests for financial calculation accuracy (Success Metric #2)."""

    def test_retail_margin_calculation(self) -> None:
        """Test retail margin calculation with known values."""
        drug = Drug(
            ndc="0074433902",
            drug_name="HUMIRA",
            manufacturer="ABBVIE",
            contract_cost=Decimal("150.00"),
            awp=Decimal("6500.00"),
        )

        analysis = analyze_drug_margin(drug)

        # Retail margin = AWP × 0.85 - Contract Cost = 6500 × 0.85 - 150 = 5375
        expected_retail = Decimal("5375.00")
        assert analysis.retail_gross_margin == expected_retail

    def test_medicare_margin_calculation(self) -> None:
        """Test Medicare margin calculation: ASP × 1.06."""
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

        # Medicare = ASP × 1.06 × bill_units - contract_cost
        # = 2800 × 1.06 × 2 - 150 = 5936 - 150 = 5786
        expected_medicare = Decimal("5786.00")
        assert analysis.medicare_margin == expected_medicare

    def test_commercial_margin_calculation(self) -> None:
        """Test Commercial margin calculation: ASP × 1.15."""
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

        # Commercial = ASP × 1.15 × bill_units - contract_cost
        # = 2800 × 1.15 × 2 - 150 = 6440 - 150 = 6290
        expected_commercial = Decimal("6290.00")
        assert analysis.commercial_margin == expected_commercial

    def test_financial_accuracy_within_tolerance(self) -> None:
        """Success Metric #2: Financial Accuracy.

        Projections should match expected values within +/- 5% margin of error.
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

        # Known expected commercial margin
        expected_commercial = Decimal("6290.00")

        # Allow 5% tolerance
        tolerance = expected_commercial * Decimal("0.05")
        lower_bound = expected_commercial - tolerance
        upper_bound = expected_commercial + tolerance

        assert analysis.commercial_margin is not None
        assert lower_bound <= analysis.commercial_margin <= upper_bound

    def test_capture_rate_impact(self) -> None:
        """Test that capture rate correctly reduces retail margin."""
        drug = Drug(
            ndc="0074433902",
            drug_name="HUMIRA",
            manufacturer="ABBVIE",
            contract_cost=Decimal("150.00"),
            awp=Decimal("6500.00"),
        )

        # Full capture
        analysis_100 = analyze_drug_margin(drug, capture_rate=Decimal("1.0"))

        # 40% capture
        analysis_40 = analyze_drug_margin(drug, capture_rate=Decimal("0.4"))

        # Net margin at 40% should be ~40% of full margin
        ratio = analysis_40.retail_net_margin / analysis_100.retail_net_margin
        assert Decimal("0.35") <= ratio <= Decimal("0.45")


class TestAuditability:
    """Tests for auditability and provenance (Success Metric #3)."""

    def test_provenance_chain_complete(self) -> None:
        """Success Metric #3: Auditability.

        Every calculated margin should have a complete provenance chain.
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
        required_fields = [
            "ndc",
            "drug_name",
            "contract_cost",
            "awp",
            "retail_gross_margin",
            "recommendation",
        ]
        for field in required_fields:
            assert field in display_dict, f"Missing provenance field: {field}"

    def test_display_dict_includes_medical_margins(self) -> None:
        """Test that medical margins are included when ASP is present."""
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

        # Should include Medicare and Commercial margins
        assert "medicare_margin" in display_dict
        assert "commercial_margin" in display_dict
        assert display_dict["medicare_margin"] is not None
        assert display_dict["commercial_margin"] is not None


class TestOptimizationVelocity:
    """Tests for performance benchmarks (Success Metric #1)."""

    def test_single_drug_lookup_fast(self) -> None:
        """Test that single drug lookup is fast (<100ms)."""
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

        start = time.time()
        analysis = analyze_drug_margin(drug)
        _ = analysis.recommended_path
        elapsed = time.time() - start

        msg = f"Single lookup took {elapsed*1000:.1f}ms, expected <100ms"
        assert elapsed < 0.1, msg

    def test_batch_lookup_performance(self) -> None:
        """Success Metric #1: Optimization Velocity.

        A user can identify the optimal site of care within 30 seconds.
        Test: 100 drug lookups should complete in <5 seconds.
        """
        # Create 100 test drugs
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

    def test_data_loading_performance(self) -> None:
        """Test that sample data loads in reasonable time."""
        catalog_path = SAMPLE_DATA_DIR / "product_catalog.xlsx"
        if not catalog_path.exists():
            pytest.skip("Sample data not available")

        start = time.time()
        df = load_excel_to_polars(str(catalog_path))
        df = normalize_catalog(df)
        elapsed = time.time() - start

        # Should load and normalize 34k drugs in <10s
        assert elapsed < 10.0, f"Catalog load took {elapsed:.2f}s, expected <10s"


class TestRiskFlagging:
    """Tests for IRA and Penny Pricing risk flagging."""

    def test_ira_drug_detection(self) -> None:
        """Test that known IRA drugs are flagged."""
        # Enbrel is an IRA 2026 drug
        ira_status = check_ira_status("ENBREL")
        assert ira_status["is_ira_drug"] is True
        assert "2026" in str(ira_status.get("ira_year", ""))

    def test_non_ira_drug_not_flagged(self) -> None:
        """Test that non-IRA drugs are not flagged."""
        ira_status = check_ira_status("METFORMIN")
        assert ira_status["is_ira_drug"] is False

    def test_penny_pricing_detection(self) -> None:
        """Test penny pricing detection from discount percentage."""
        # Create mock NADAC data with penny-priced drug (99% discount)
        nadac_df = pl.DataFrame({
            "ndc": ["12345678901"],
            "total_discount_340b_pct": [99.0],
        })

        result = check_penny_pricing_for_drug("12345678901", nadac_df)
        assert result.is_penny_priced is True

    def test_non_penny_drug_not_flagged(self) -> None:
        """Test that normal priced drugs are not flagged."""
        # Create mock NADAC data with normal priced drug (50% discount)
        nadac_df = pl.DataFrame({
            "ndc": ["12345678901"],
            "total_discount_340b_pct": [50.0],
        })

        result = check_penny_pricing_for_drug("12345678901", nadac_df)
        assert result.is_penny_priced is False

    def test_risk_flags_in_drug_model(self) -> None:
        """Test that risk flags work in Drug model."""
        drug = Drug(
            ndc="0074433902",
            drug_name="ENBREL",
            manufacturer="AMGEN",
            contract_cost=Decimal("150.00"),
            awp=Decimal("6500.00"),
            ira_flag=True,
            penny_pricing_flag=False,
        )

        assert drug.ira_flag is True
        assert drug.penny_pricing_flag is False


class TestRecommendationLogic:
    """Tests for treatment pathway recommendation logic."""

    def test_recommends_retail_when_no_asp(self) -> None:
        """Test that retail is recommended when ASP is not available."""
        drug = Drug(
            ndc="0074433902",
            drug_name="ORAL_DRUG",
            manufacturer="TEST",
            contract_cost=Decimal("50.00"),
            awp=Decimal("200.00"),
            asp=None,  # No ASP means oral/retail only
            hcpcs_code=None,
        )

        analysis = analyze_drug_margin(drug)
        assert analysis.recommended_path == RecommendedPath.RETAIL

    def test_recommends_medical_when_better_margin(self) -> None:
        """Test that medical is recommended when it has better margin."""
        # Drug where commercial medical margin > retail margin
        drug = Drug(
            ndc="0074433902",
            drug_name="HUMIRA",
            manufacturer="ABBVIE",
            contract_cost=Decimal("5000.00"),  # High contract cost
            awp=Decimal("6500.00"),  # Low AWP spread
            asp=Decimal("6000.00"),  # High ASP
            hcpcs_code="J0135",
            bill_units_per_package=2,
        )

        analysis = analyze_drug_margin(drug)
        # With high ASP and low AWP spread, medical should be better
        assert analysis.recommended_path in [
            RecommendedPath.MEDICARE_MEDICAL,
            RecommendedPath.COMMERCIAL_MEDICAL,
        ]

    def test_margin_delta_calculation(self) -> None:
        """Test that margin delta is calculated correctly."""
        drug = Drug(
            ndc="0074433902",
            drug_name="TEST",
            manufacturer="TEST",
            contract_cost=Decimal("100.00"),
            awp=Decimal("1000.00"),
            asp=Decimal("500.00"),
            hcpcs_code="J0135",
            bill_units_per_package=1,
        )

        analysis = analyze_drug_margin(drug)

        # Margin delta should be best margin - retail margin (for medical drugs)
        # or 0 for retail-only drugs
        assert analysis.margin_delta >= Decimal("0")


class TestEndToEndWithSampleData:
    """End-to-end tests using real sample data."""

    @pytest.fixture
    def joined_data(self) -> pl.DataFrame:
        """Load and join all sample data."""
        catalog_path = SAMPLE_DATA_DIR / "product_catalog.xlsx"
        crosswalk_path = SAMPLE_DATA_DIR / "asp_crosswalk.csv"

        if not catalog_path.exists() or not crosswalk_path.exists():
            pytest.skip("Sample data not available")

        catalog_df = load_excel_to_polars(str(catalog_path))
        catalog_df = normalize_catalog(catalog_df)

        crosswalk_df = preprocess_cms_csv(str(crosswalk_path), skip_rows=8)
        crosswalk_df = normalize_crosswalk(crosswalk_df)

        joined_df, _ = join_catalog_to_crosswalk(catalog_df, crosswalk_df)
        return joined_df

    def test_joined_data_has_required_columns(
        self, joined_data: pl.DataFrame
    ) -> None:
        """Test that joined data has all columns needed for margin calc."""
        required_cols = ["NDC", "Contract Cost", "AWP", "HCPCS Code"]
        for col in required_cols:
            assert col in joined_data.columns, f"Missing column: {col}"

    def test_can_analyze_joined_drugs(self, joined_data: pl.DataFrame) -> None:
        """Test that we can analyze drugs from joined data."""
        # Take first 10 rows with required data
        sample = joined_data.head(10)

        analyzed_count = 0
        for row in sample.iter_rows(named=True):
            try:
                ndc = str(row.get("NDC", ""))
                drug_name = str(row.get("Drug Name", "Unknown"))
                contract_cost = row.get("Contract Cost")
                awp = row.get("AWP")
                hcpcs = row.get("HCPCS Code")

                if not all([ndc, contract_cost, awp]):
                    continue

                drug = Drug(
                    ndc=ndc,
                    drug_name=drug_name,
                    manufacturer="Unknown",
                    contract_cost=Decimal(str(contract_cost)),
                    awp=Decimal(str(awp)),
                    hcpcs_code=str(hcpcs) if hcpcs else None,
                )

                analysis = analyze_drug_margin(drug)
                assert analysis.recommended_path is not None
                analyzed_count += 1
            except (ValueError, TypeError):
                continue

        assert analyzed_count > 0, "Should analyze at least some drugs"
