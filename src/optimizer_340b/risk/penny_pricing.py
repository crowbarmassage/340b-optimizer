"""Penny Pricing detection for 340B drugs.

Penny Pricing occurs when a drug's NADAC (National Average Drug Acquisition Cost)
is extremely low (often $0.01 or less), indicating the drug is effectively
available at near-zero cost. These drugs should NOT appear in "Top Opportunities"
because the 340B margin is already maximized with minimal room for improvement.

Gatekeeper Test: Penny Pricing Alert
- Drugs with Penny Pricing = Yes should NOT appear in "Top Opportunities"
- These drugs should be flagged with a warning explaining why
"""

import logging
from dataclasses import dataclass
from decimal import Decimal

import polars as pl

logger = logging.getLogger(__name__)

# Threshold below which pricing is considered "penny pricing"
PENNY_THRESHOLD = Decimal("0.10")  # $0.10 per unit

# High discount threshold for NADAC-based penny pricing detection
HIGH_DISCOUNT_THRESHOLD = Decimal("95.0")  # 95% discount indicates penny pricing


@dataclass
class PennyPricingStatus:
    """Penny pricing assessment for a drug.

    Attributes:
        is_penny_priced: Whether the drug has penny pricing.
        ndc: NDC of the drug.
        nadac_price: NADAC price if available.
        discount_pct: 340B discount percentage from NADAC.
        warning_message: Human-readable warning.
        should_exclude: Whether to exclude from Top Opportunities.
    """

    is_penny_priced: bool
    ndc: str
    nadac_price: Decimal | None
    discount_pct: Decimal | None
    warning_message: str
    should_exclude: bool


def check_penny_pricing(nadac_df: pl.DataFrame) -> list[dict[str, object]]:
    """Check NADAC data for penny-priced drugs.

    Drugs with penny_pricing=True or extremely high discount percentages
    are flagged as having limited 340B opportunity.

    Args:
        nadac_df: NADAC DataFrame with columns:
            - ndc: Drug NDC
            - penny_pricing: Boolean flag (if available)
            - total_discount_340b_pct: Discount percentage (if available)

    Returns:
        List of flagged drugs with their penny pricing status.
    """
    flagged: list[dict[str, object]] = []

    # Check if required columns exist
    has_penny_column = "penny_pricing" in nadac_df.columns
    has_discount_column = "total_discount_340b_pct" in nadac_df.columns

    if not has_penny_column and not has_discount_column:
        logger.warning("NADAC data missing penny_pricing and discount columns")
        return flagged

    for row in nadac_df.iter_rows(named=True):
        ndc = str(row.get("ndc", ""))
        is_penny = False
        reason = ""

        # Check explicit penny_pricing flag
        if has_penny_column and row.get("penny_pricing"):
            is_penny = True
            reason = "Penny pricing flag is set"

        # Check high discount percentage
        if has_discount_column:
            discount = row.get("total_discount_340b_pct")
            if discount is not None:
                discount_decimal = Decimal(str(discount))
                if discount_decimal >= HIGH_DISCOUNT_THRESHOLD:
                    is_penny = True
                    reason = f"340B discount is {discount_decimal:.1f}%"

        if is_penny:
            flagged.append({
                "ndc": ndc,
                "is_penny_priced": True,
                "discount_pct": row.get("total_discount_340b_pct"),
                "warning_message": (
                    f"Penny Pricing Alert: {ndc} - {reason}. "
                    "This drug should NOT appear in Top Opportunities."
                ),
                "should_exclude": True,
            })

            logger.info(f"Penny pricing detected: NDC {ndc} - {reason}")

    logger.info(
        f"Found {len(flagged)} penny-priced drugs out of {nadac_df.height} total"
    )

    return flagged


def check_penny_pricing_for_drug(
    ndc: str,
    nadac_df: pl.DataFrame,
) -> PennyPricingStatus:
    """Check if a specific drug has penny pricing.

    Args:
        ndc: NDC to check.
        nadac_df: NADAC DataFrame with pricing data.

    Returns:
        PennyPricingStatus with assessment.
    """
    # Normalize NDC for matching
    ndc_clean = ndc.replace("-", "").strip()

    # Filter for matching NDC
    if "ndc" not in nadac_df.columns:
        return PennyPricingStatus(
            is_penny_priced=False,
            ndc=ndc,
            nadac_price=None,
            discount_pct=None,
            warning_message="NADAC data not available",
            should_exclude=False,
        )

    # Create normalized NDC column for matching
    matches = nadac_df.filter(
        pl.col("ndc").cast(pl.Utf8).str.replace_all("-", "").str.strip_chars()
        == ndc_clean
    )

    if matches.height == 0:
        return PennyPricingStatus(
            is_penny_priced=False,
            ndc=ndc,
            nadac_price=None,
            discount_pct=None,
            warning_message="NDC not found in NADAC data",
            should_exclude=False,
        )

    row = matches.row(0, named=True)

    # Check penny pricing indicators
    is_penny = False
    nadac_price = None
    discount_pct = None
    reason = ""

    # Check explicit flag
    if "penny_pricing" in matches.columns and row.get("penny_pricing"):
        is_penny = True
        reason = "Penny pricing flag is set"

    # Check NADAC price
    if "nadac_per_unit" in matches.columns:
        price = row.get("nadac_per_unit")
        if price is not None:
            nadac_price = Decimal(str(price))
            if nadac_price <= PENNY_THRESHOLD:
                is_penny = True
                reason = f"NADAC price is ${nadac_price:.4f}"

    # Check discount percentage
    if "total_discount_340b_pct" in matches.columns:
        discount = row.get("total_discount_340b_pct")
        if discount is not None:
            discount_pct = Decimal(str(discount))
            if discount_pct >= HIGH_DISCOUNT_THRESHOLD:
                is_penny = True
                reason = f"340B discount is {discount_pct:.1f}%"

    if is_penny:
        warning = (
            f"Penny Pricing Alert: {ndc} - {reason}. "
            "Exclude from Top Opportunities."
        )
    else:
        warning = "No penny pricing detected"

    return PennyPricingStatus(
        is_penny_priced=is_penny,
        ndc=ndc,
        nadac_price=nadac_price,
        discount_pct=discount_pct,
        warning_message=warning,
        should_exclude=is_penny,
    )


def filter_top_opportunities(
    opportunities: list[dict[str, object]],
    nadac_df: pl.DataFrame | None = None,
    penny_ndcs: set[str] | None = None,
) -> list[dict[str, object]]:
    """Filter out penny-priced drugs from Top Opportunities.

    Gatekeeper Test: Penny Pricing Alert
    - Drugs with Penny Pricing = Yes should NOT appear in "Top Opportunities"

    Args:
        opportunities: List of drug opportunities with 'ndc' and 'margin' keys.
        nadac_df: Optional NADAC DataFrame for penny pricing lookup.
        penny_ndcs: Optional pre-computed set of penny-priced NDCs.

    Returns:
        Filtered list excluding penny-priced drugs.
    """
    if penny_ndcs is None and nadac_df is not None:
        # Build penny NDC set from NADAC data
        flagged = check_penny_pricing(nadac_df)
        penny_ndcs = {str(item["ndc"]) for item in flagged}
    elif penny_ndcs is None:
        penny_ndcs = set()

    filtered = []
    excluded_count = 0

    for opp in opportunities:
        ndc = str(opp.get("ndc", ""))
        is_penny = opp.get("penny_pricing", False)

        # Check against penny_ndcs set or explicit flag
        if ndc in penny_ndcs or is_penny:
            excluded_count += 1
            logger.debug(f"Excluding penny-priced drug from opportunities: {ndc}")
            continue

        filtered.append(opp)

    if excluded_count > 0:
        logger.info(
            f"Excluded {excluded_count} penny-priced drugs from Top Opportunities"
        )

    return filtered


def get_penny_pricing_summary(nadac_df: pl.DataFrame) -> dict[str, object]:
    """Get summary statistics for penny pricing in dataset.

    Args:
        nadac_df: NADAC DataFrame with pricing data.

    Returns:
        Dictionary with penny pricing summary statistics.
    """
    flagged = check_penny_pricing(nadac_df)

    total_drugs = nadac_df.height
    penny_count = len(flagged)
    penny_pct = (penny_count / total_drugs * 100) if total_drugs > 0 else 0

    return {
        "total_drugs": total_drugs,
        "penny_priced_count": penny_count,
        "penny_priced_pct": round(penny_pct, 2),
        "flagged_ndcs": [item["ndc"] for item in flagged],
    }
