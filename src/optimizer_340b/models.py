"""Data models for 340B Optimizer."""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class RecommendedPath(str, Enum):
    """Recommended site-of-care pathway."""

    RETAIL = "RETAIL"
    MEDICARE_MEDICAL = "MEDICARE_MEDICAL"
    COMMERCIAL_MEDICAL = "COMMERCIAL_MEDICAL"


class RiskLevel(str, Enum):
    """Risk classification for regulatory flags."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class Drug:
    """Core drug entity combining catalog and pricing data.

    Attributes:
        ndc: National Drug Code (various formats accepted, normalized internally).
        drug_name: Trade/brand name of the drug.
        manufacturer: Drug manufacturer name.
        contract_cost: 340B acquisition cost per package.
        awp: Average Wholesale Price per package.
        asp: Average Sales Price per billing unit (None if no HCPCS mapping).
        hcpcs_code: Medicare billing code (None for retail-only drugs).
        bill_units_per_package: Number of HCPCS billing units per NDC package.
        therapeutic_class: Drug classification (e.g., "TNF Inhibitor").
        is_biologic: Whether the drug is a biologic (affects dosing logic).
        ira_flag: Whether subject to IRA price negotiation.
        penny_pricing_flag: Whether NADAC is at 340B floor.
    """

    ndc: str
    drug_name: str
    manufacturer: str
    contract_cost: Decimal
    awp: Decimal
    asp: Decimal | None = None
    hcpcs_code: str | None = None
    bill_units_per_package: int = 1
    therapeutic_class: str | None = None
    is_biologic: bool = False
    ira_flag: bool = False
    penny_pricing_flag: bool = False

    def has_medical_path(self) -> bool:
        """Check if drug can be billed through medical channel.

        Returns:
            True if drug has both HCPCS code and ASP pricing.
        """
        return self.hcpcs_code is not None and self.asp is not None

    @property
    def ndc_normalized(self) -> str:
        """Return 11-digit normalized NDC with leading zeros preserved.

        Removes dashes and pads to 11 digits.

        Returns:
            11-digit NDC string without dashes, with leading zeros.
        """
        cleaned = self.ndc.replace("-", "").replace(" ", "")
        return cleaned.zfill(11)[-11:]


@dataclass
class MarginAnalysis:
    """Complete margin analysis for a drug.

    Attributes:
        drug: The analyzed drug entity.
        retail_gross_margin: AWP * Reimb_Rate - Contract_Cost.
        retail_net_margin: Gross margin * Capture_Rate.
        retail_capture_rate: Assumed capture rate for retail channel.
        medicare_margin: ASP * 1.06 * Bill_Units - Contract_Cost.
        commercial_margin: ASP * 1.15 * Bill_Units - Contract_Cost.
        recommended_path: Pathway with highest margin.
        margin_delta: Difference between best and second-best path.
    """

    drug: Drug
    retail_gross_margin: Decimal
    retail_net_margin: Decimal
    retail_capture_rate: Decimal
    medicare_margin: Decimal | None
    commercial_margin: Decimal | None
    recommended_path: RecommendedPath
    margin_delta: Decimal

    def to_display_dict(self) -> dict[str, object]:
        """Convert to dictionary for UI display.

        Returns:
            Dictionary with all fields formatted for display.
        """
        return {
            "ndc": self.drug.ndc,
            "drug_name": self.drug.drug_name,
            "manufacturer": self.drug.manufacturer,
            "contract_cost": float(self.drug.contract_cost),
            "awp": float(self.drug.awp),
            "asp": float(self.drug.asp) if self.drug.asp else None,
            "retail_gross_margin": float(self.retail_gross_margin),
            "retail_net_margin": float(self.retail_net_margin),
            "retail_capture_rate": float(self.retail_capture_rate),
            "medicare_margin": (
                float(self.medicare_margin) if self.medicare_margin else None
            ),
            "commercial_margin": (
                float(self.commercial_margin) if self.commercial_margin else None
            ),
            "recommendation": self.recommended_path.value,
            "margin_delta": float(self.margin_delta),
            "ira_risk": self.drug.ira_flag,
            "penny_pricing": self.drug.penny_pricing_flag,
        }


@dataclass
class DosingProfile:
    """Loading dose profile for biologics.

    Attributes:
        drug_name: Name of the drug.
        indication: Clinical indication for dosing.
        year_1_fills: Number of fills in Year 1 (including loading doses).
        year_2_plus_fills: Annual fills for maintenance (Year 2+).
        adjusted_year_1_fills: Year 1 fills adjusted for compliance.
    """

    drug_name: str
    indication: str
    year_1_fills: int
    year_2_plus_fills: int
    adjusted_year_1_fills: Decimal

    def year_1_revenue(self, margin_per_fill: Decimal) -> Decimal:
        """Calculate Year 1 revenue including loading doses.

        Args:
            margin_per_fill: Net margin per fill/administration.

        Returns:
            Total Year 1 revenue.
        """
        return self.adjusted_year_1_fills * margin_per_fill

    def maintenance_revenue(self, margin_per_fill: Decimal) -> Decimal:
        """Calculate annual maintenance revenue (Year 2+).

        Args:
            margin_per_fill: Net margin per fill/administration.

        Returns:
            Annual maintenance revenue.
        """
        return Decimal(self.year_2_plus_fills) * margin_per_fill

    def loading_dose_delta(self, margin_per_fill: Decimal) -> Decimal:
        """Calculate the revenue delta from loading doses.

        This quantifies the "patient acquisition opportunity."

        Args:
            margin_per_fill: Net margin per fill/administration.

        Returns:
            Additional revenue in Year 1 vs. Maintenance year.
        """
        return self.year_1_revenue(margin_per_fill) - self.maintenance_revenue(
            margin_per_fill
        )
