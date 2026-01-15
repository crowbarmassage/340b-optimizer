"""Tests for data models."""

from decimal import Decimal

from optimizer_340b.models import (
    DosingProfile,
    Drug,
    MarginAnalysis,
    RecommendedPath,
    RiskLevel,
)


class TestDrug:
    """Tests for Drug model."""

    def test_has_medical_path_with_hcpcs_and_asp(self, sample_drug: Drug) -> None:
        """Drug with both HCPCS and ASP should have medical path."""
        assert sample_drug.has_medical_path() is True

    def test_has_medical_path_without_hcpcs(
        self, sample_drug_retail_only: Drug
    ) -> None:
        """Drug without HCPCS should not have medical path."""
        assert sample_drug_retail_only.has_medical_path() is False

    def test_has_medical_path_with_hcpcs_but_no_asp(self) -> None:
        """Drug with HCPCS but no ASP should not have medical path."""
        drug = Drug(
            ndc="1111111111",
            drug_name="TEST",
            manufacturer="TEST",
            contract_cost=Decimal("10.00"),
            awp=Decimal("100.00"),
            asp=None,  # No ASP
            hcpcs_code="J9999",  # Has HCPCS
        )
        assert drug.has_medical_path() is False

    def test_ndc_normalized_removes_dashes(self, sample_drug: Drug) -> None:
        """NDC normalization should remove dashes."""
        # sample_drug has ndc="0074-4339-02"
        assert sample_drug.ndc_normalized == "0074433902"

    def test_ndc_normalized_pads_short_ndc(self) -> None:
        """Short NDCs should be zero-padded to 10 digits."""
        drug = Drug(
            ndc="12345",
            drug_name="TEST",
            manufacturer="TEST",
            contract_cost=Decimal("10.00"),
            awp=Decimal("100.00"),
        )
        assert drug.ndc_normalized == "0000012345"
        assert len(drug.ndc_normalized) == 10

    def test_ndc_normalized_handles_11_digit(self) -> None:
        """11-digit NDCs should drop the check digit."""
        drug = Drug(
            ndc="12345678901",  # 11 digits
            drug_name="TEST",
            manufacturer="TEST",
            contract_cost=Decimal("10.00"),
            awp=Decimal("100.00"),
        )
        assert drug.ndc_normalized == "1234567890"
        assert len(drug.ndc_normalized) == 10

    def test_ndc_normalized_handles_spaces(self) -> None:
        """NDC normalization should remove spaces."""
        drug = Drug(
            ndc="0074 4339 02",
            drug_name="TEST",
            manufacturer="TEST",
            contract_cost=Decimal("10.00"),
            awp=Decimal("100.00"),
        )
        assert drug.ndc_normalized == "0074433902"

    def test_drug_default_values(self) -> None:
        """Drug should have sensible defaults for optional fields."""
        drug = Drug(
            ndc="1234567890",
            drug_name="TEST",
            manufacturer="TEST",
            contract_cost=Decimal("10.00"),
            awp=Decimal("100.00"),
        )
        assert drug.asp is None
        assert drug.hcpcs_code is None
        assert drug.bill_units_per_package == 1
        assert drug.therapeutic_class is None
        assert drug.is_biologic is False
        assert drug.ira_flag is False
        assert drug.penny_pricing_flag is False


class TestDosingProfile:
    """Tests for DosingProfile model."""

    def test_year_1_revenue_calculation(
        self, sample_dosing_profile: DosingProfile
    ) -> None:
        """Year 1 revenue should multiply adjusted fills by margin."""
        margin_per_fill = Decimal("500.00")
        expected = Decimal("15.3") * margin_per_fill  # 7650.0

        result = sample_dosing_profile.year_1_revenue(margin_per_fill)

        assert result == expected

    def test_maintenance_revenue_calculation(
        self, sample_dosing_profile: DosingProfile
    ) -> None:
        """Maintenance revenue should use year_2_plus_fills."""
        margin_per_fill = Decimal("500.00")
        expected = Decimal("12") * margin_per_fill  # 6000

        result = sample_dosing_profile.maintenance_revenue(margin_per_fill)

        assert result == expected

    def test_loading_dose_delta_positive(
        self, sample_dosing_profile: DosingProfile
    ) -> None:
        """Loading dose delta should be positive for drugs with loading doses."""
        margin_per_fill = Decimal("500.00")

        delta = sample_dosing_profile.loading_dose_delta(margin_per_fill)

        # Year 1: 15.3 * 500 = 7650
        # Maintenance: 12 * 500 = 6000
        # Delta: 1650
        assert delta > Decimal("0")
        assert delta == Decimal("1650.0")

    def test_loading_dose_delta_percentage(
        self, sample_dosing_profile: DosingProfile
    ) -> None:
        """Loading dose should represent significant Year 1 uplift."""
        margin_per_fill = Decimal("500.00")

        year_1 = sample_dosing_profile.year_1_revenue(margin_per_fill)
        maintenance = sample_dosing_profile.maintenance_revenue(margin_per_fill)
        delta_pct = (year_1 - maintenance) / maintenance * 100

        # Cosentyx loading dose should provide >25% Year 1 uplift
        assert delta_pct > Decimal("25")

    def test_zero_margin_returns_zero_revenue(
        self, sample_dosing_profile: DosingProfile
    ) -> None:
        """Zero margin should result in zero revenue."""
        result = sample_dosing_profile.year_1_revenue(Decimal("0"))
        assert result == Decimal("0")


class TestMarginAnalysis:
    """Tests for MarginAnalysis model."""

    def test_to_display_dict_includes_all_fields(
        self, sample_margin_analysis: MarginAnalysis
    ) -> None:
        """Display dict should include all required fields."""
        result = sample_margin_analysis.to_display_dict()

        # Check all expected fields are present
        assert "ndc" in result
        assert "drug_name" in result
        assert "manufacturer" in result
        assert "contract_cost" in result
        assert "awp" in result
        assert "asp" in result
        assert "retail_gross_margin" in result
        assert "retail_net_margin" in result
        assert "retail_capture_rate" in result
        assert "medicare_margin" in result
        assert "commercial_margin" in result
        assert "recommendation" in result
        assert "margin_delta" in result
        assert "ira_risk" in result
        assert "penny_pricing" in result

    def test_to_display_dict_correct_values(
        self, sample_margin_analysis: MarginAnalysis
    ) -> None:
        """Display dict should have correct values."""
        result = sample_margin_analysis.to_display_dict()

        assert result["ndc"] == "0074-4339-02"
        assert result["drug_name"] == "HUMIRA"
        assert result["recommendation"] == "COMMERCIAL_MEDICAL"
        assert result["ira_risk"] is False
        assert result["penny_pricing"] is False

    def test_to_display_dict_converts_decimals_to_float(
        self, sample_margin_analysis: MarginAnalysis
    ) -> None:
        """Display dict should convert Decimal values to float."""
        result = sample_margin_analysis.to_display_dict()

        assert isinstance(result["contract_cost"], float)
        assert isinstance(result["retail_gross_margin"], float)
        assert isinstance(result["margin_delta"], float)

    def test_to_display_dict_handles_none_values(
        self, sample_drug_retail_only: Drug
    ) -> None:
        """Display dict should handle None margins gracefully."""
        analysis = MarginAnalysis(
            drug=sample_drug_retail_only,
            retail_gross_margin=Decimal("75.00"),
            retail_net_margin=Decimal("33.75"),
            retail_capture_rate=Decimal("0.45"),
            medicare_margin=None,  # No medical path
            commercial_margin=None,
            recommended_path=RecommendedPath.RETAIL,
            margin_delta=Decimal("33.75"),
        )

        result = analysis.to_display_dict()

        assert result["medicare_margin"] is None
        assert result["commercial_margin"] is None
        assert result["asp"] is None


class TestEnums:
    """Tests for enum types."""

    def test_recommended_path_values(self) -> None:
        """RecommendedPath should have expected values."""
        assert RecommendedPath.RETAIL.value == "RETAIL"
        assert RecommendedPath.MEDICARE_MEDICAL.value == "MEDICARE_MEDICAL"
        assert RecommendedPath.COMMERCIAL_MEDICAL.value == "COMMERCIAL_MEDICAL"

    def test_risk_level_values(self) -> None:
        """RiskLevel should have expected values."""
        assert RiskLevel.LOW.value == "LOW"
        assert RiskLevel.MEDIUM.value == "MEDIUM"
        assert RiskLevel.HIGH.value == "HIGH"

    def test_enums_are_string_enums(self) -> None:
        """Enums should be string enums for easy serialization."""
        assert isinstance(RecommendedPath.RETAIL, str)
        assert isinstance(RiskLevel.HIGH, str)
