"""Margin calculation engine for 340B site-of-care optimization (Gold Layer).

This module implements the core margin formulas:
- Retail Pathway: AWP × 85% × Capture_Rate - Contract_Cost
- Medicare Medical: ASP × 1.06 × Bill_Units - Contract_Cost
- Commercial Medical: ASP × 1.15 × Bill_Units - Contract_Cost

Gatekeeper Tests (from Project Charter):
- Medicare Unit Test: Manual calculation matches to the penny
- Commercial Unit Test: 1.15x multiplier correctly applied
- Capture Rate Stress Test: 40% toggle reduces retail proportionally
"""

import logging
from decimal import Decimal

from optimizer_340b.models import Drug, MarginAnalysis, RecommendedPath

logger = logging.getLogger(__name__)

# Pricing constants
AWP_DISCOUNT_FACTOR = Decimal("0.85")  # Retail reimburses at AWP - 15%
MEDICARE_ASP_MULTIPLIER = Decimal("1.06")  # Medicare Part B: ASP + 6%
COMMERCIAL_ASP_MULTIPLIER = Decimal("1.15")  # Commercial: ASP + 15%
DEFAULT_CAPTURE_RATE = Decimal("0.45")  # Default retail capture rate


def calculate_retail_margin(
    drug: Drug,
    capture_rate: Decimal = DEFAULT_CAPTURE_RATE,
) -> tuple[Decimal, Decimal]:
    """Calculate retail pharmacy margin.

    Formula:
        Gross Margin = AWP × 85% - Contract_Cost
        Net Margin = Gross Margin × Capture_Rate

    Args:
        drug: Drug with AWP and contract cost.
        capture_rate: Expected capture rate (0.0-1.0).

    Returns:
        Tuple of (gross_margin, net_margin).
    """
    # Revenue at AWP discount
    revenue = drug.awp * AWP_DISCOUNT_FACTOR

    # Gross margin before capture rate
    gross_margin = revenue - drug.contract_cost

    # Net margin after capture rate
    net_margin = gross_margin * capture_rate

    logger.debug(
        f"Retail margin for {drug.ndc}: "
        f"AWP=${drug.awp} × {AWP_DISCOUNT_FACTOR} - ${drug.contract_cost} = "
        f"${gross_margin} gross, ${net_margin} net @ {capture_rate:.0%} capture"
    )

    return gross_margin, net_margin


def calculate_medicare_margin(drug: Drug) -> Decimal | None:
    """Calculate Medicare Part B medical margin.

    Formula:
        Revenue = ASP × 1.06 × Bill_Units
        Margin = Revenue - Contract_Cost

    Gatekeeper Test: Medicare Unit Test
    - Manually calculate margin for one vial using ASP + 6%
    - Engine output must match to the penny

    Args:
        drug: Drug with ASP, HCPCS code, and bill units.

    Returns:
        Medicare margin, or None if drug has no medical path.
    """
    if not drug.has_medical_path():
        logger.debug(f"Drug {drug.ndc} has no medical path (no ASP/HCPCS)")
        return None

    # Type narrowing: has_medical_path() guarantees asp is not None
    assert drug.asp is not None

    # Revenue at ASP + 6%
    revenue = drug.asp * MEDICARE_ASP_MULTIPLIER * drug.bill_units_per_package

    # Margin after contract cost
    margin = revenue - drug.contract_cost

    logger.debug(
        f"Medicare margin for {drug.ndc}: "
        f"ASP=${drug.asp} × {MEDICARE_ASP_MULTIPLIER} × {drug.bill_units_per_package} "
        f"- ${drug.contract_cost} = ${margin}"
    )

    return margin


def calculate_commercial_margin(drug: Drug) -> Decimal | None:
    """Calculate Commercial payer medical margin.

    Formula:
        Revenue = ASP × 1.15 × Bill_Units
        Margin = Revenue - Contract_Cost

    Gatekeeper Test: Commercial Medical Unit Test
    - Verify 1.15x multiplier is correctly applied
    - Switching payer toggle should use this multiplier

    Args:
        drug: Drug with ASP, HCPCS code, and bill units.

    Returns:
        Commercial margin, or None if drug has no medical path.
    """
    if not drug.has_medical_path():
        logger.debug(f"Drug {drug.ndc} has no medical path (no ASP/HCPCS)")
        return None

    # Type narrowing: has_medical_path() guarantees asp is not None
    assert drug.asp is not None

    # Revenue at ASP + 15%
    revenue = drug.asp * COMMERCIAL_ASP_MULTIPLIER * drug.bill_units_per_package

    # Margin after contract cost
    margin = revenue - drug.contract_cost

    logger.debug(
        f"Commercial margin for {drug.ndc}: "
        f"ASP=${drug.asp} × {COMMERCIAL_ASP_MULTIPLIER} "
        f"× {drug.bill_units_per_package} - ${drug.contract_cost} = ${margin}"
    )

    return margin


def determine_recommendation(
    retail_net: Decimal,
    medicare: Decimal | None,
    commercial: Decimal | None,
) -> tuple[RecommendedPath, Decimal]:
    """Determine optimal pathway based on margins.

    Compares all available pathways and returns the one with highest margin.

    Args:
        retail_net: Net retail margin (after capture rate).
        medicare: Medicare medical margin (or None).
        commercial: Commercial medical margin (or None).

    Returns:
        Tuple of (recommended_path, margin_delta).
        margin_delta is the difference between best and second-best option.
    """
    # Build list of (path, margin) for available options
    options: list[tuple[RecommendedPath, Decimal]] = [
        (RecommendedPath.RETAIL, retail_net),
    ]

    if medicare is not None:
        options.append((RecommendedPath.MEDICARE_MEDICAL, medicare))

    if commercial is not None:
        options.append((RecommendedPath.COMMERCIAL_MEDICAL, commercial))

    # Sort by margin descending
    options.sort(key=lambda x: x[1], reverse=True)

    best_path, best_margin = options[0]

    # Calculate delta (difference from second best, or just the margin if only one)
    if len(options) > 1:
        second_margin = options[1][1]
        delta = best_margin - second_margin
    else:
        delta = best_margin

    logger.debug(
        f"Recommendation: {best_path.value} with margin ${best_margin}, "
        f"delta ${delta} over next best"
    )

    return best_path, delta


def analyze_drug_margin(
    drug: Drug,
    capture_rate: Decimal = DEFAULT_CAPTURE_RATE,
) -> MarginAnalysis:
    """Perform complete margin analysis for a drug.

    Calculates all pathway margins and determines optimal recommendation.

    Args:
        drug: Drug to analyze.
        capture_rate: Retail capture rate (0.0-1.0).

    Returns:
        MarginAnalysis with all calculated margins and recommendation.
    """
    # Calculate all margins
    retail_gross, retail_net = calculate_retail_margin(drug, capture_rate)
    medicare = calculate_medicare_margin(drug)
    commercial = calculate_commercial_margin(drug)

    # Determine recommendation
    recommended_path, margin_delta = determine_recommendation(
        retail_net, medicare, commercial
    )

    analysis = MarginAnalysis(
        drug=drug,
        retail_gross_margin=retail_gross,
        retail_net_margin=retail_net,
        retail_capture_rate=capture_rate,
        medicare_margin=medicare,
        commercial_margin=commercial,
        recommended_path=recommended_path,
        margin_delta=margin_delta,
    )

    logger.info(
        f"Analyzed {drug.drug_name} ({drug.ndc}): "
        f"Recommend {recommended_path.value}, delta=${margin_delta:.2f}"
    )

    return analysis


def analyze_drug_with_payer(
    drug: Drug,
    payer_type: str = "commercial",
    capture_rate: Decimal = DEFAULT_CAPTURE_RATE,
) -> MarginAnalysis:
    """Analyze drug margin with specific payer comparison.

    Compares retail pathway against specified medical payer.

    Args:
        drug: Drug to analyze.
        payer_type: "medicare" or "commercial".
        capture_rate: Retail capture rate.

    Returns:
        MarginAnalysis comparing retail vs specified payer.
    """
    retail_gross, retail_net = calculate_retail_margin(drug, capture_rate)

    if payer_type.lower() == "medicare":
        medical_margin = calculate_medicare_margin(drug)
        if medical_margin is not None and medical_margin > retail_net:
            recommended = RecommendedPath.MEDICARE_MEDICAL
            delta = medical_margin - retail_net
        else:
            recommended = RecommendedPath.RETAIL
            delta = retail_net - (medical_margin or Decimal("0"))
    else:  # commercial
        medical_margin = calculate_commercial_margin(drug)
        if medical_margin is not None and medical_margin > retail_net:
            recommended = RecommendedPath.COMMERCIAL_MEDICAL
            delta = medical_margin - retail_net
        else:
            recommended = RecommendedPath.RETAIL
            delta = retail_net - (medical_margin or Decimal("0"))

    return MarginAnalysis(
        drug=drug,
        retail_gross_margin=retail_gross,
        retail_net_margin=retail_net,
        retail_capture_rate=capture_rate,
        medicare_margin=calculate_medicare_margin(drug),
        commercial_margin=calculate_commercial_margin(drug),
        recommended_path=recommended,
        margin_delta=abs(delta),
    )


def calculate_margin_sensitivity(
    drug: Drug,
    capture_rates: list[Decimal] | None = None,
) -> list[dict[str, Decimal | str]]:
    """Calculate margin sensitivity across capture rate scenarios.

    Gatekeeper Test: Capture Rate Stress Test
    - If capture rate toggles from 100% to 40%, retail margin should
      drop proportionately

    Args:
        drug: Drug to analyze.
        capture_rates: List of capture rates to test.
            Defaults to [0.40, 0.45, 0.60, 0.80, 1.00].

    Returns:
        List of sensitivity results with margins at each capture rate.
    """
    if capture_rates is None:
        capture_rates = [
            Decimal("0.40"),
            Decimal("0.45"),
            Decimal("0.60"),
            Decimal("0.80"),
            Decimal("1.00"),
        ]

    results = []
    medicare = calculate_medicare_margin(drug)
    commercial = calculate_commercial_margin(drug)

    for rate in capture_rates:
        _, retail_net = calculate_retail_margin(drug, rate)

        # Determine best path at this capture rate
        best_path, _ = determine_recommendation(retail_net, medicare, commercial)

        results.append({
            "capture_rate": rate,
            "retail_net": retail_net,
            "medicare": medicare or Decimal("0"),
            "commercial": commercial or Decimal("0"),
            "recommended": best_path.value,
        })

    return results
