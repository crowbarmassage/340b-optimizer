"""Phase 4 Integration Tests - Complete Pipeline Through Gold Layer.

These tests validate the complete data pipeline from raw file loading
through margin calculation and pathway recommendation.

Run with: pytest tests/test_phase4_integration.py -v

Note: These tests require the real data files in the inbox directory.
"""

from decimal import Decimal
from pathlib import Path

import polars as pl
import pytest

from optimizer_340b.compute.dosing import (
    apply_loading_dose_logic,
    calculate_year_1_vs_maintenance_delta,
    load_biologics_grid,
)
from optimizer_340b.compute.margins import (
    COMMERCIAL_ASP_MULTIPLIER,
    MEDICARE_ASP_MULTIPLIER,
    analyze_drug_margin,
    calculate_commercial_margin,
    calculate_margin_sensitivity,
    calculate_medicare_margin,
    calculate_retail_margin,
)
from optimizer_340b.ingest.loaders import load_excel_to_polars
from optimizer_340b.ingest.normalizers import (
    build_silver_dataset,
    preprocess_cms_csv,
)
from optimizer_340b.models import Drug, RecommendedPath

# Path to real data files
DATA_DIR = Path("/Users/mohsin.ansari/Github/inbox/340B_Engine")

# Skip all tests if data directory doesn't exist
pytestmark = pytest.mark.skipif(
    not DATA_DIR.exists(),
    reason=f"Data directory not found: {DATA_DIR}",
)


class TestGatekeeperMedicareUnitTest:
    """Gatekeeper: Medicare Unit Test.

    Manually calculate the margin for one vial using ASP + 6%.
    Does the Engine's output match to the penny?
    """

    def test_medicare_formula_asp_plus_6_percent(self) -> None:
        """Medicare reimbursement should be exactly ASP × 1.06."""
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

        margin = calculate_medicare_margin(drug)

        # Manual calculation: $2800 × 1.06 × 2 - $150 = $5786
        expected = Decimal("2800") * Decimal("1.06") * 2 - Decimal("150")
        assert margin == expected
        assert margin == Decimal("5786.00")

    def test_medicare_multiplier_constant(self) -> None:
        """Medicare multiplier should be exactly 1.06."""
        assert Decimal("1.06") == MEDICARE_ASP_MULTIPLIER


class TestGatekeeperCommercialUnitTest:
    """Gatekeeper: Commercial Medical Unit Test.

    Verify that switching the payer toggle to "Commercial" correctly
    applies the 1.15x multiplier to the ASP baseline.
    """

    def test_commercial_formula_asp_plus_15_percent(self) -> None:
        """Commercial reimbursement should be exactly ASP × 1.15."""
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

        margin = calculate_commercial_margin(drug)

        # Manual calculation: $2800 × 1.15 × 2 - $150 = $6290
        expected = Decimal("2800") * Decimal("1.15") * 2 - Decimal("150")
        assert margin == expected
        assert margin == Decimal("6290.00")

    def test_commercial_multiplier_constant(self) -> None:
        """Commercial multiplier should be exactly 1.15."""
        assert Decimal("1.15") == COMMERCIAL_ASP_MULTIPLIER

    def test_commercial_higher_than_medicare(self) -> None:
        """Commercial margin should always exceed Medicare (1.15 > 1.06)."""
        drug = Drug(
            ndc="1234567890",
            drug_name="TEST_DRUG",
            manufacturer="TEST",
            contract_cost=Decimal("100.00"),
            awp=Decimal("1000.00"),
            asp=Decimal("500.00"),
            hcpcs_code="J9999",
            bill_units_per_package=1,
        )

        medicare = calculate_medicare_margin(drug)
        commercial = calculate_commercial_margin(drug)

        assert commercial is not None
        assert medicare is not None
        assert commercial > medicare


class TestGatekeeperCaptureRateStressTest:
    """Gatekeeper: Capture Rate Stress Test.

    If the Capture Rate variable is toggled from 100% to 40%,
    does the "Retail Margin" drop proportionately?
    """

    def test_capture_rate_100_to_40_proportional(self) -> None:
        """Retail margin at 40% should be exactly 40% of margin at 100%."""
        drug = Drug(
            ndc="0074433902",
            drug_name="HUMIRA",
            manufacturer="ABBVIE",
            contract_cost=Decimal("150.00"),
            awp=Decimal("6500.00"),
        )

        _, net_100 = calculate_retail_margin(drug, Decimal("1.00"))
        _, net_40 = calculate_retail_margin(drug, Decimal("0.40"))

        # 40% capture should yield exactly 40% of 100% capture
        assert net_40 == net_100 * Decimal("0.40")

    def test_capture_rate_sensitivity_linear(self) -> None:
        """Retail margins should scale linearly with capture rate."""
        drug = Drug(
            ndc="1234567890",
            drug_name="TEST_DRUG",
            manufacturer="TEST",
            contract_cost=Decimal("100.00"),
            awp=Decimal("1000.00"),
        )

        results = calculate_margin_sensitivity(
            drug,
            [Decimal("0.20"), Decimal("0.40"), Decimal("0.60"), Decimal("0.80")],
        )

        # Each step should increase by same amount (linear)
        margins = [r["retail_net"] for r in results]
        deltas = [margins[i + 1] - margins[i] for i in range(len(margins) - 1)]

        # All deltas should be equal (within floating point tolerance)
        assert all(d == deltas[0] for d in deltas)


class TestGatekeeperLoadingDoseLogicTest:
    """Gatekeeper: Loading Dose Logic Test.

    Select Cosentyx (Psoriasis). Does the Year 1 Revenue calculation
    reflect 17 fills (Loading) vs. 12 fills (Maintenance)?
    """

    @pytest.fixture
    def dosing_grid(self) -> pl.DataFrame:
        """Sample dosing grid with Cosentyx."""
        return pl.DataFrame({
            "Drug Name": ["COSENTYX", "COSENTYX", "HUMIRA"],
            "Indication": ["Psoriasis", "Ankylosing Spondylitis", "RA"],
            "Year 1 Fills": [17, 13, 26],
            "Year 2+ Fills": [12, 12, 26],
        })

    def test_cosentyx_psoriasis_year_1_fills(
        self, dosing_grid: pl.DataFrame
    ) -> None:
        """Cosentyx Psoriasis should have 17 Year 1 fills."""
        profile = apply_loading_dose_logic(
            "COSENTYX", dosing_grid, indication="Psoriasis"
        )

        assert profile is not None
        assert profile.year_1_fills == 17
        assert profile.year_2_plus_fills == 12

    def test_cosentyx_loading_dose_delta(
        self, dosing_grid: pl.DataFrame
    ) -> None:
        """Cosentyx Year 1 should generate ~42% more revenue than Maintenance."""
        profile = apply_loading_dose_logic(
            "COSENTYX", dosing_grid, indication="Psoriasis"
        )
        assert profile is not None

        margin_per_fill = Decimal("1000.00")
        result = calculate_year_1_vs_maintenance_delta(profile, margin_per_fill)

        # Year 1: 17 × 0.90 compliance × $1000 = $15,300
        # Maintenance: 12 × $1000 = $12,000
        # Delta: $3,300 = 27.5% increase (with compliance)
        assert result["loading_dose_delta"] > 0
        assert result["loading_dose_delta_pct"] > Decimal("20")

    def test_loading_biologics_grid_file(self) -> None:
        """Should load real biologics grid file if available."""
        grid_path = DATA_DIR / "biologics_logic_grid.xlsx"
        if not grid_path.exists():
            pytest.skip(f"File not found: {grid_path}")

        grid = load_biologics_grid(str(grid_path))

        assert grid.height > 0
        assert "Drug Name" in grid.columns or "Drug" in grid.columns


class TestCompleteMarginAnalysis:
    """Tests for complete drug margin analysis workflow."""

    def test_analyze_drug_all_pathways(self) -> None:
        """Should calculate all three pathway margins."""
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

        analysis = analyze_drug_margin(drug, Decimal("0.45"))

        # Verify all margins calculated
        assert analysis.retail_gross_margin > 0
        assert analysis.retail_net_margin > 0
        assert analysis.medicare_margin is not None
        assert analysis.commercial_margin is not None

        # Verify recommendation exists
        assert analysis.recommended_path in [
            RecommendedPath.RETAIL,
            RecommendedPath.MEDICARE_MEDICAL,
            RecommendedPath.COMMERCIAL_MEDICAL,
        ]

    def test_retail_only_drug_analysis(self) -> None:
        """Drug without HCPCS should only have retail pathway."""
        drug = Drug(
            ndc="9999999999",
            drug_name="ORAL_DRUG",
            manufacturer="TEST",
            contract_cost=Decimal("50.00"),
            awp=Decimal("500.00"),
            # No ASP or HCPCS - retail only
        )

        analysis = analyze_drug_margin(drug)

        assert analysis.retail_gross_margin > 0
        assert analysis.medicare_margin is None
        assert analysis.commercial_margin is None
        assert analysis.recommended_path == RecommendedPath.RETAIL

    def test_recommendation_changes_with_capture_rate(self) -> None:
        """Lower capture rate may shift recommendation to medical."""
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

        # At very low capture, medical should win
        analysis_low = analyze_drug_margin(drug, Decimal("0.10"))
        # At very high capture, retail might win
        analysis_high = analyze_drug_margin(drug, Decimal("1.00"))

        # Both should have valid recommendations
        assert analysis_low.recommended_path is not None
        assert analysis_high.recommended_path is not None

        # Retail margin should be much higher at 100% capture
        assert analysis_high.retail_net_margin > analysis_low.retail_net_margin


class TestEndToEndPipeline:
    """End-to-end tests using real data through margin calculation."""

    def test_silver_to_margin_calculation(self) -> None:
        """Build Silver dataset and calculate margins for sample drugs."""
        catalog_path = DATA_DIR / "product_catalog.xlsx"
        crosswalk_path = DATA_DIR / "October 2025 ASP NDC-HCPCS Crosswalk 090525.csv"
        asp_path = DATA_DIR / "Oct 2025 ASP Pricing File updated 120925.csv"

        for path in [catalog_path, crosswalk_path, asp_path]:
            if not path.exists():
                pytest.skip(f"File not found: {path}")

        # Build Silver dataset
        catalog_raw = load_excel_to_polars(catalog_path)
        crosswalk_raw = preprocess_cms_csv(str(crosswalk_path), skip_rows=8)
        asp_raw = preprocess_cms_csv(str(asp_path), skip_rows=8)

        silver, _ = build_silver_dataset(catalog_raw, crosswalk_raw, asp_raw)

        # Get a sample drug with complete data
        sample = silver.filter(
            pl.col("ASP").is_not_null()
            & pl.col("AWP").is_not_null()
            & pl.col("Contract Cost").is_not_null()
            & (pl.col("ASP") > 0)
            & (pl.col("AWP") > 0)
        ).head(1)

        if sample.height == 0:
            pytest.skip("No drugs with complete pricing data")

        row = sample.row(0, named=True)

        # Create Drug model from Silver data
        drug = Drug(
            ndc=str(row["NDC"]),
            drug_name=row.get("Drug Name", "UNKNOWN") or "UNKNOWN",
            manufacturer="UNKNOWN",
            contract_cost=Decimal(str(row["Contract Cost"])),
            awp=Decimal(str(row["AWP"])),
            asp=Decimal(str(row["ASP"])),
            hcpcs_code=row["HCPCS Code"],
            bill_units_per_package=1,
        )

        # Calculate margins
        analysis = analyze_drug_margin(drug)

        # Verify we got results
        assert analysis.retail_gross_margin is not None
        assert analysis.medicare_margin is not None
        assert analysis.commercial_margin is not None
        assert analysis.recommended_path is not None

        print("\nSample Drug Analysis:")
        print(f"  Drug: {drug.drug_name}")
        print(f"  HCPCS: {drug.hcpcs_code}")
        print(f"  Contract: ${drug.contract_cost}")
        print(f"  AWP: ${drug.awp}")
        print(f"  ASP: ${drug.asp}")
        print(f"  Retail Gross: ${analysis.retail_gross_margin:.2f}")
        print(f"  Medicare: ${analysis.medicare_margin:.2f}")
        print(f"  Commercial: ${analysis.commercial_margin:.2f}")
        print(f"  Recommendation: {analysis.recommended_path.value}")


class TestFinancialAccuracy:
    """Success Metric #2: Financial Accuracy.

    The "Realizable Revenue" projection should match historical
    reimbursement data within +/- 5% margin of error.
    """

    def test_margin_calculation_precision(self) -> None:
        """Margin calculations should be precise to the penny."""
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
        expected_retail_gross = Decimal("5375.00")
        expected_medicare = Decimal("5786.00")
        expected_commercial = Decimal("6290.00")

        # Must match exactly (to the penny)
        assert analysis.retail_gross_margin == expected_retail_gross
        assert analysis.medicare_margin == expected_medicare
        assert analysis.commercial_margin == expected_commercial


class TestAuditability:
    """Success Metric #3: Auditability.

    Every calculated margin should have a clear provenance chain.
    """

    def test_analysis_contains_all_inputs(self) -> None:
        """Analysis should preserve all input values for audit trail."""
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

        analysis = analyze_drug_margin(drug, Decimal("0.45"))
        display = analysis.to_display_dict()

        # All key inputs should be in display dict
        assert "ndc" in display
        assert "drug_name" in display
        assert "contract_cost" in display
        assert "retail_net_margin" in display
        assert "medicare_margin" in display
        assert "commercial_margin" in display
        assert "recommendation" in display

    def test_capture_rate_recorded(self) -> None:
        """Analysis should record the capture rate used."""
        drug = Drug(
            ndc="1234567890",
            drug_name="TEST",
            manufacturer="TEST",
            contract_cost=Decimal("100.00"),
            awp=Decimal("1000.00"),
        )

        analysis = analyze_drug_margin(drug, Decimal("0.60"))

        assert analysis.retail_capture_rate == Decimal("0.60")


class TestOptimizationVelocity:
    """Success Metric #1: Optimization Velocity.

    A user can identify the optimal site of care for a dual-eligible drug
    within 30 seconds.
    """

    def test_margin_calculation_performance(self) -> None:
        """100 drug margin calculations should complete in <5 seconds."""
        import time

        drugs = [
            Drug(
                ndc=f"{i:010d}",
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

        # Should complete 100 lookups very quickly
        assert elapsed < 5.0, f"100 lookups took {elapsed:.2f}s, expected <5s"
        print(f"\n100 margin calculations completed in {elapsed:.3f}s")
