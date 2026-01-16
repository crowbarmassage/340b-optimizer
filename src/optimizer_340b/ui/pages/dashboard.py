"""Dashboard page for 340B Optimizer - Ranked opportunity list."""

import logging
from decimal import Decimal

import polars as pl
import streamlit as st

from optimizer_340b.compute.margins import analyze_drug_margin
from optimizer_340b.models import Drug, MarginAnalysis
from optimizer_340b.risk import check_ira_status
from optimizer_340b.ui.components.capture_slider import render_capture_slider
from optimizer_340b.ui.components.risk_badge import (
    render_ira_badge_inline,
    render_penny_badge_inline,
)

logger = logging.getLogger(__name__)


def render_dashboard_page() -> None:
    """Render the main optimization dashboard.

    Shows ranked list of optimization opportunities with:
    - Margin comparison (Retail vs Medical)
    - Risk flags (IRA, Penny Pricing)
    - Capture rate adjustment
    - Search and filter capabilities
    """
    st.title("340B Optimization Dashboard")

    # Check if data is loaded
    if not _check_data_loaded():
        st.warning(
            "Please upload data files first. "
            "Select **Upload Data** from the sidebar."
        )
        return

    # Sidebar controls
    with st.sidebar:
        st.markdown("### Analysis Controls")
        capture_rate = render_capture_slider()

        st.markdown("---")
        st.markdown("### Filters")
        show_ira_only = st.checkbox("Show IRA drugs only", value=False)
        hide_penny = st.checkbox("Hide penny pricing drugs", value=True)
        min_delta = st.number_input(
            "Minimum margin delta ($)",
            min_value=0,
            max_value=10000,
            value=100,
            step=50,
        )

    # Main content
    _render_summary_metrics()

    st.markdown("---")

    # Search
    search_query = st.text_input(
        "Search drugs",
        placeholder="Enter drug name or NDC...",
        key="drug_search",
    )

    # Get and display opportunities
    opportunities = _calculate_opportunities(capture_rate)

    # Apply filters
    filtered = _apply_filters(
        opportunities,
        search_query=search_query,
        show_ira_only=show_ira_only,
        hide_penny=hide_penny,
        min_delta=Decimal(str(min_delta)),
    )

    st.markdown(f"**Showing {len(filtered)} of {len(opportunities)} drugs**")

    # Render opportunity table
    _render_opportunity_table(filtered)


def _check_data_loaded() -> bool:
    """Check if required data is loaded in session state."""
    uploaded = st.session_state.get("uploaded_data", {})
    return "catalog" in uploaded


def _render_summary_metrics() -> None:
    """Render summary metrics at top of dashboard."""
    uploaded = st.session_state.get("uploaded_data", {})

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        catalog = uploaded.get("catalog")
        drug_count = catalog.height if catalog is not None else 0
        st.metric("Total Drugs", f"{drug_count:,}")

    with col2:
        crosswalk = uploaded.get("crosswalk")
        hcpcs_count = crosswalk.height if crosswalk is not None else 0
        st.metric("HCPCS Mappings", f"{hcpcs_count:,}")

    with col3:
        # Calculate medical-eligible drugs
        joined = uploaded.get("joined_data")
        if joined is not None:
            medical_eligible = joined.filter(pl.col("HCPCS Code").is_not_null()).height
        else:
            medical_eligible = 0
        st.metric("Medical Eligible", f"{medical_eligible:,}")

    with col4:
        nadac = uploaded.get("nadac")
        if nadac is not None:
            penny_count = nadac.filter(
                pl.col("total_discount_340b_pct") >= 95.0
            ).height
        else:
            penny_count = 0
        st.metric("Penny Pricing", f"{penny_count:,}")


def _calculate_opportunities(capture_rate: Decimal) -> list[MarginAnalysis]:
    """Calculate margin opportunities for all drugs.

    Args:
        capture_rate: Retail capture rate.

    Returns:
        List of MarginAnalysis objects sorted by margin delta.
    """
    uploaded = st.session_state.get("uploaded_data", {})
    catalog = uploaded.get("catalog")
    asp_pricing = uploaded.get("asp_pricing")
    crosswalk = uploaded.get("crosswalk")
    nadac = uploaded.get("nadac")

    if catalog is None:
        return []

    # Build drug objects and analyze margins
    analyses: list[MarginAnalysis] = []

    # Prepare lookup tables
    hcpcs_lookup = _build_hcpcs_lookup(crosswalk, asp_pricing)
    nadac_lookup = _build_nadac_lookup(nadac)

    for row in catalog.iter_rows(named=True):
        try:
            drug = _row_to_drug(row, hcpcs_lookup, nadac_lookup)
            if drug is not None:
                analysis = analyze_drug_margin(drug, capture_rate)
                analyses.append(analysis)
        except Exception as e:
            logger.debug(f"Error analyzing drug: {e}")
            continue

    # Sort by margin delta descending
    analyses.sort(key=lambda a: a.margin_delta, reverse=True)

    return analyses


def _build_hcpcs_lookup(
    crosswalk: pl.DataFrame | None,
    asp_pricing: pl.DataFrame | None,
) -> dict[str, dict[str, object]]:
    """Build HCPCS lookup from crosswalk and ASP pricing.

    Returns:
        Dictionary mapping normalized NDC to HCPCS info.
    """
    if crosswalk is None or asp_pricing is None:
        return {}

    lookup: dict[str, dict[str, object]] = {}

    # Normalize column names for crosswalk
    ndc_col = "NDC" if "NDC" in crosswalk.columns else "NDC2"
    hcpcs_col = (
        "HCPCS Code" if "HCPCS Code" in crosswalk.columns else "_2025_CODE"
    )

    if ndc_col not in crosswalk.columns or hcpcs_col not in crosswalk.columns:
        return {}

    # Build ASP pricing lookup by HCPCS
    asp_lookup: dict[str, float] = {}
    payment_col = (
        "Payment Limit"
        if "Payment Limit" in asp_pricing.columns
        else "PAYMENT_LIMIT"
    )

    if payment_col in asp_pricing.columns and "HCPCS Code" in asp_pricing.columns:
        for row in asp_pricing.iter_rows(named=True):
            hcpcs = row.get("HCPCS Code")
            payment = row.get(payment_col)
            if hcpcs and payment:
                # Handle N/A and other non-numeric values
                try:
                    asp_lookup[str(hcpcs).upper()] = float(payment)
                except (ValueError, TypeError):
                    continue  # Skip non-numeric payment values

    # Build combined lookup
    for row in crosswalk.iter_rows(named=True):
        ndc = str(row.get(ndc_col, "")).replace("-", "").strip()
        hcpcs = str(row.get(hcpcs_col, "")).upper().strip()

        if ndc and hcpcs:
            asp = asp_lookup.get(hcpcs)
            bill_units = row.get("Billing Units Per Package", 1) or 1

            lookup[ndc] = {
                "hcpcs_code": hcpcs,
                "asp": asp,
                "bill_units": int(bill_units),
            }

    return lookup


def _build_nadac_lookup(nadac: pl.DataFrame | None) -> dict[str, dict[str, object]]:
    """Build NADAC lookup for penny pricing detection.

    Returns:
        Dictionary mapping normalized NDC to NADAC info.
    """
    if nadac is None:
        return {}

    lookup: dict[str, dict[str, object]] = {}

    for row in nadac.iter_rows(named=True):
        ndc = str(row.get("ndc", "")).replace("-", "").strip()
        discount = row.get("total_discount_340b_pct")
        penny = row.get("penny_pricing", False)

        if ndc:
            is_penny = penny or (discount is not None and float(discount) >= 95.0)
            lookup[ndc] = {
                "discount_pct": discount,
                "penny_pricing": is_penny,
            }

    return lookup


def _row_to_drug(
    row: dict[str, object],
    hcpcs_lookup: dict[str, dict[str, object]],
    nadac_lookup: dict[str, dict[str, object]],
) -> Drug | None:
    """Convert a catalog row to a Drug object.

    Args:
        row: Row from catalog DataFrame.
        hcpcs_lookup: HCPCS/ASP lookup by NDC.
        nadac_lookup: NADAC lookup by NDC.

    Returns:
        Drug object or None if invalid.
    """
    # Get NDC
    ndc = str(row.get("NDC", ""))
    if not ndc:
        return None

    ndc_normalized = ndc.replace("-", "").strip()

    # Get drug name (handle different column names)
    drug_name = (
        row.get("Drug Name")
        or row.get("Trade Name")
        or row.get("DRUG_NAME")
        or "Unknown"
    )

    # Get manufacturer
    manufacturer = row.get("Manufacturer") or row.get("MANUFACTURER") or "Unknown"

    # Get contract cost
    contract_cost = row.get("Contract Cost") or row.get("CONTRACT_COST") or 0
    try:
        contract_cost = Decimal(str(contract_cost))
    except Exception:
        return None

    # Get AWP (handle different column names)
    awp = row.get("AWP") or row.get("Medispan AWP") or row.get("MEDISPAN_AWP") or 0
    try:
        awp = Decimal(str(awp))
    except Exception:
        return None

    # Lookup HCPCS/ASP info
    hcpcs_info = hcpcs_lookup.get(ndc_normalized, {})
    asp = hcpcs_info.get("asp")
    hcpcs_code = hcpcs_info.get("hcpcs_code")
    bill_units = hcpcs_info.get("bill_units", 1)

    # Lookup NADAC info
    nadac_info = nadac_lookup.get(ndc_normalized, {})
    penny_pricing = nadac_info.get("penny_pricing", False)

    # Check IRA status
    ira_status = check_ira_status(str(drug_name))
    ira_flag = ira_status.get("is_ira_drug", False)

    return Drug(
        ndc=ndc,
        drug_name=str(drug_name),
        manufacturer=str(manufacturer),
        contract_cost=contract_cost,
        awp=awp,
        asp=Decimal(str(asp)) if asp else None,
        hcpcs_code=str(hcpcs_code) if hcpcs_code else None,
        bill_units_per_package=int(str(bill_units)) if bill_units else 1,
        ira_flag=bool(ira_flag),
        penny_pricing_flag=bool(penny_pricing),
    )


def _apply_filters(
    analyses: list[MarginAnalysis],
    search_query: str = "",
    show_ira_only: bool = False,
    hide_penny: bool = True,
    min_delta: Decimal = Decimal("0"),
) -> list[MarginAnalysis]:
    """Apply filters to opportunity list.

    Args:
        analyses: List of MarginAnalysis objects.
        search_query: Drug name or NDC search.
        show_ira_only: Show only IRA-affected drugs.
        hide_penny: Hide penny-priced drugs.
        min_delta: Minimum margin delta.

    Returns:
        Filtered list of analyses.
    """
    filtered = analyses

    # Search filter
    if search_query:
        query = search_query.upper()
        filtered = [
            a for a in filtered
            if query in a.drug.drug_name.upper() or query in a.drug.ndc
        ]

    # IRA filter
    if show_ira_only:
        filtered = [a for a in filtered if a.drug.ira_flag]

    # Penny pricing filter
    if hide_penny:
        filtered = [a for a in filtered if not a.drug.penny_pricing_flag]

    # Margin delta filter
    filtered = [a for a in filtered if a.margin_delta >= min_delta]

    return filtered


def _render_opportunity_table(analyses: list[MarginAnalysis]) -> None:
    """Render the opportunity table with clickable rows."""
    if not analyses:
        st.info("No opportunities match the current filters.")
        return

    # Prepare data for display
    table_data = []

    for analysis in analyses[:100]:  # Limit to top 100 for performance
        drug = analysis.drug

        # Build risk badges HTML
        badges = ""
        if drug.ira_flag:
            badges += render_ira_badge_inline(drug.drug_name) + " "
        if drug.penny_pricing_flag:
            badges += render_penny_badge_inline(True)

        # Determine best margin
        best_margin = analysis.retail_net_margin
        if analysis.commercial_margin and analysis.commercial_margin > best_margin:
            best_margin = analysis.commercial_margin
        if analysis.medicare_margin and analysis.medicare_margin > best_margin:
            best_margin = analysis.medicare_margin

        table_data.append({
            "Drug": drug.drug_name,
            "NDC": drug.ndc,
            "Best Margin": f"${best_margin:,.2f}",
            "Retail": f"${analysis.retail_net_margin:,.2f}",
            "Medicare": (
                f"${analysis.medicare_margin:,.2f}"
                if analysis.medicare_margin else "N/A"
            ),
            "Commercial": (
                f"${analysis.commercial_margin:,.2f}"
                if analysis.commercial_margin else "N/A"
            ),
            "Recommendation": analysis.recommended_path.value.replace("_", " "),
            "Delta": f"${analysis.margin_delta:,.2f}",
            "Risk": badges,
        })

    # Create DataFrame
    df = pl.DataFrame(table_data)

    # Display with st.dataframe for performance
    st.dataframe(
        df.to_pandas(),
        width="stretch",
        hide_index=True,
        column_config={
            "Risk": st.column_config.Column(
                "Risk Flags",
                help="IRA and Penny Pricing alerts",
            ),
        },
    )

    # Drug detail links
    st.markdown("---")
    st.markdown("**View Drug Details** - Select drug, then go to Drug Detail page")

    cols = st.columns(5)
    for i, analysis in enumerate(analyses[:5]):
        with cols[i]:
            if st.button(analysis.drug.drug_name, key=f"detail_{i}"):
                st.session_state.selected_drug = analysis.drug.ndc
                st.info(f"Selected {analysis.drug.drug_name}. Go to Drug Detail.")
