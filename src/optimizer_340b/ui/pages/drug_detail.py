"""Drug detail page for 340B Optimizer - Single drug deep-dive."""

import logging
from decimal import Decimal

import plotly.graph_objects as go  # type: ignore[import-untyped]
import streamlit as st

from optimizer_340b.compute.dosing import apply_loading_dose_logic
from optimizer_340b.compute.margins import (
    analyze_drug_margin,
    calculate_margin_sensitivity,
)
from optimizer_340b.models import Drug, MarginAnalysis
from optimizer_340b.risk import check_ira_status
from optimizer_340b.ui.components.capture_slider import (
    render_capture_slider,
    render_payer_toggle,
)
from optimizer_340b.ui.components.margin_card import render_margin_card
from optimizer_340b.ui.components.risk_badge import render_risk_badges

logger = logging.getLogger(__name__)


def render_drug_detail_page() -> None:
    """Render the drug detail page.

    Shows comprehensive analysis for a single drug including:
    - Margin comparison across pathways
    - Capture rate sensitivity analysis
    - Loading dose impact (for biologics)
    - Risk flags and warnings
    - Calculation provenance
    """
    st.title("Drug Detail Analysis")

    # Get selected drug or show search
    drug = _get_or_search_drug()

    if drug is None:
        return

    # Sidebar controls
    with st.sidebar:
        st.markdown("### Analysis Parameters")
        capture_rate = render_capture_slider(key="detail_capture")
        render_payer_toggle(key="detail_payer")  # Renders toggle, value in session

    # Main content
    _render_drug_header(drug)

    # Risk warnings at top
    st.markdown("### Risk Assessment")
    render_risk_badges(drug)

    st.markdown("---")

    # Margin analysis
    st.markdown("### Margin Analysis")
    analysis = analyze_drug_margin(drug, capture_rate)
    render_margin_card(analysis)

    st.markdown("---")

    # Sensitivity analysis
    st.markdown("### Capture Rate Sensitivity")
    _render_sensitivity_chart(drug)

    st.markdown("---")

    # Loading dose analysis (if biologic)
    if drug.is_biologic or _has_loading_dose(drug):
        st.markdown("### Loading Dose Impact")
        _render_loading_dose_analysis(drug, analysis)
        st.markdown("---")

    # Provenance chain
    st.markdown("### Calculation Provenance")
    _render_provenance_chain(drug, analysis)


def _get_or_search_drug() -> Drug | None:
    """Get selected drug from session state or show search."""
    # Check if drug was selected from dashboard
    selected_ndc = st.session_state.get("selected_drug")

    if selected_ndc:
        drug = _lookup_drug_by_ndc(selected_ndc)
        if drug:
            return drug

    # Show search interface
    st.markdown("Search for a drug to analyze:")

    col1, col2 = st.columns([3, 1])

    with col1:
        search = st.text_input(
            "Drug name or NDC",
            placeholder="Enter drug name or NDC...",
            key="drug_detail_search",
        )

    with col2:
        search_btn = st.button("Search", type="primary")

    if search and search_btn:
        drug = _search_drug(search)
        if drug:
            st.session_state.selected_drug = drug.ndc
            return drug
        else:
            st.error("Drug not found. Please check the name or NDC.")

    # Demo mode with sample drug
    st.markdown("---")
    st.info("Or try a demo drug:")

    if st.button("Demo: HUMIRA"):
        drug = _create_demo_drug("HUMIRA")
        st.session_state.selected_drug = drug.ndc
        return drug

    if st.button("Demo: ENBREL (IRA 2026)"):
        drug = _create_demo_drug("ENBREL")
        st.session_state.selected_drug = drug.ndc
        return drug

    return None


def _lookup_drug_by_ndc(ndc: str) -> Drug | None:
    """Look up drug by NDC from uploaded data."""
    uploaded = st.session_state.get("uploaded_data", {})
    catalog = uploaded.get("catalog")

    if catalog is None:
        return _create_demo_drug("HUMIRA")  # Fallback to demo

    # Find matching row
    ndc_clean = ndc.replace("-", "").strip()

    for row in catalog.iter_rows(named=True):
        row_ndc = str(row.get("NDC", "")).replace("-", "").strip()
        if row_ndc == ndc_clean:
            return _row_to_drug(row)

    return None


def _search_drug(query: str) -> Drug | None:
    """Search for drug by name or NDC."""
    uploaded = st.session_state.get("uploaded_data", {})
    catalog = uploaded.get("catalog")

    if catalog is None:
        # Check if it's a demo drug
        if "HUMIRA" in query.upper():
            return _create_demo_drug("HUMIRA")
        if "ENBREL" in query.upper():
            return _create_demo_drug("ENBREL")
        return None

    query_upper = query.upper()

    for row in catalog.iter_rows(named=True):
        drug_name = str(row.get("Drug Name") or row.get("Trade Name") or "").upper()
        ndc = str(row.get("NDC", ""))

        if query_upper in drug_name or query in ndc:
            return _row_to_drug(row)

    return None


def _row_to_drug(row: dict[str, object]) -> Drug:
    """Convert catalog row to Drug object."""
    from optimizer_340b.ui.pages.dashboard import (
        _build_hcpcs_lookup,
        _build_nadac_lookup,
    )

    uploaded = st.session_state.get("uploaded_data", {})
    hcpcs_lookup = _build_hcpcs_lookup(
        uploaded.get("crosswalk"),
        uploaded.get("asp_pricing"),
    )
    nadac_lookup = _build_nadac_lookup(uploaded.get("nadac"))

    ndc = str(row.get("NDC", ""))
    ndc_normalized = ndc.replace("-", "").strip()

    drug_name = (
        row.get("Drug Name")
        or row.get("Trade Name")
        or "Unknown"
    )

    contract_cost = Decimal(str(row.get("Contract Cost", 0) or 0))
    awp = Decimal(str(row.get("AWP") or row.get("Medispan AWP") or 0))

    hcpcs_info = hcpcs_lookup.get(ndc_normalized, {})
    nadac_info = nadac_lookup.get(ndc_normalized, {})

    ira_status = check_ira_status(str(drug_name))

    hcpcs_code = hcpcs_info.get("hcpcs_code")
    bill_units = hcpcs_info.get("bill_units", 1)

    return Drug(
        ndc=ndc,
        drug_name=str(drug_name),
        manufacturer=str(row.get("Manufacturer", "Unknown")),
        contract_cost=contract_cost,
        awp=awp,
        asp=Decimal(str(hcpcs_info.get("asp"))) if hcpcs_info.get("asp") else None,
        hcpcs_code=str(hcpcs_code) if hcpcs_code else None,
        bill_units_per_package=int(str(bill_units)) if bill_units else 1,
        ira_flag=bool(ira_status.get("is_ira_drug", False)),
        penny_pricing_flag=bool(nadac_info.get("penny_pricing", False)),
    )


def _create_demo_drug(name: str) -> Drug:
    """Create a demo drug for testing."""
    if name == "ENBREL":
        return Drug(
            ndc="5555555555",
            drug_name="ENBREL",
            manufacturer="AMGEN",
            contract_cost=Decimal("200.00"),
            awp=Decimal("7000.00"),
            asp=Decimal("3000.00"),
            hcpcs_code="J1438",
            bill_units_per_package=4,
            therapeutic_class="TNF Inhibitor",
            is_biologic=True,
            ira_flag=True,  # ENBREL is IRA 2026
            penny_pricing_flag=False,
        )
    else:  # HUMIRA
        return Drug(
            ndc="0074-4339-02",
            drug_name="HUMIRA",
            manufacturer="ABBVIE",
            contract_cost=Decimal("150.00"),
            awp=Decimal("6500.00"),
            asp=Decimal("2800.00"),
            hcpcs_code="J0135",
            bill_units_per_package=2,
            therapeutic_class="TNF Inhibitor",
            is_biologic=True,
            ira_flag=False,
            penny_pricing_flag=False,
        )


def _render_drug_header(drug: Drug) -> None:
    """Render drug header with basic info."""
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header(drug.drug_name)
        st.caption(f"NDC: {drug.ndc}")
        st.caption(f"Manufacturer: {drug.manufacturer}")

        if drug.therapeutic_class:
            st.caption(f"Class: {drug.therapeutic_class}")

    with col2:
        st.markdown("**Pricing**")
        st.metric("Contract Cost", f"${drug.contract_cost:,.2f}")
        st.metric("AWP", f"${drug.awp:,.2f}")

        if drug.asp:
            st.metric("ASP", f"${drug.asp:,.2f}")


def _render_sensitivity_chart(drug: Drug) -> None:
    """Render capture rate sensitivity chart."""
    sensitivity = calculate_margin_sensitivity(drug)

    if not sensitivity:
        st.info("Sensitivity analysis not available.")
        return

    # Extract data for chart
    capture_rates = [float(s["capture_rate"]) * 100 for s in sensitivity]
    retail_margins = [float(s["retail_net"]) for s in sensitivity]
    medicare_margins = [float(s["medicare"]) for s in sensitivity]
    commercial_margins = [float(s["commercial"]) for s in sensitivity]

    # Create Plotly chart
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=capture_rates,
        y=retail_margins,
        mode="lines+markers",
        name="Retail",
        line={"color": "#1f77b4", "width": 2},
    ))

    if any(m > 0 for m in medicare_margins):
        fig.add_trace(go.Scatter(
            x=capture_rates,
            y=medicare_margins,
            mode="lines+markers",
            name="Medicare",
            line={"color": "#2ca02c", "width": 2},
        ))

    if any(m > 0 for m in commercial_margins):
        fig.add_trace(go.Scatter(
            x=capture_rates,
            y=commercial_margins,
            mode="lines+markers",
            name="Commercial",
            line={"color": "#ff7f0e", "width": 2},
        ))

    fig.update_layout(
        title="Margin by Capture Rate",
        xaxis_title="Capture Rate (%)",
        yaxis_title="Margin ($)",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02},
        hovermode="x unified",
    )

    st.plotly_chart(fig, width="stretch")

    # Crossover point analysis
    _analyze_crossover_points(sensitivity)


def _analyze_crossover_points(
    sensitivity: list[dict[str, Decimal | str]],
) -> None:
    """Analyze where retail becomes better/worse than medical."""
    for i, s in enumerate(sensitivity):
        retail = float(str(s["retail_net"]))
        commercial = float(str(s["commercial"]))

        if i > 0 and commercial > 0:
            prev = sensitivity[i - 1]
            prev_retail = float(str(prev["retail_net"]))
            prev_commercial = float(str(prev["commercial"]))

            # Check for crossover
            if (prev_retail < prev_commercial) and (retail >= commercial):
                rate = float(str(s["capture_rate"])) * 100
                st.info(
                    f"**Crossover Point:** At {rate:.0f}% capture rate, "
                    "retail becomes more profitable than medical billing."
                )
                return
            elif (prev_retail >= prev_commercial) and (retail < commercial):
                rate = float(str(s["capture_rate"])) * 100
                st.info(
                    f"**Crossover Point:** Below {rate:.0f}% capture rate, "
                    "medical billing becomes more profitable than retail."
                )
                return


def _has_loading_dose(drug: Drug) -> bool:
    """Check if drug has loading dose profile."""
    uploaded = st.session_state.get("uploaded_data", {})
    biologics = uploaded.get("biologics")

    if biologics is None:
        # Check common biologics
        loading_drugs = ["COSENTYX", "STELARA", "SKYRIZI", "TREMFYA"]
        return drug.drug_name.upper() in loading_drugs

    # Check biologics grid
    for row in biologics.iter_rows(named=True):
        if drug.drug_name.upper() in str(row.get("Drug Name", "")).upper():
            return True

    return False


def _render_loading_dose_analysis(drug: Drug, analysis: MarginAnalysis) -> None:
    """Render loading dose impact analysis."""
    uploaded = st.session_state.get("uploaded_data", {})
    biologics = uploaded.get("biologics")

    profile = None
    if biologics is not None:
        profile = apply_loading_dose_logic(drug.drug_name, biologics)

    if profile is None:
        # Use default profile for demo
        if drug.drug_name.upper() == "COSENTYX":
            st.markdown("""
            **Cosentyx Loading Dose Pattern:**
            - Year 1: 17 fills (5 loading doses + 12 monthly)
            - Year 2+: 12 fills (monthly maintenance)
            - Loading dose delta: +42% revenue in Year 1
            """)
        else:
            st.info("Loading dose profile not available for this drug.")
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Year 1 Fills",
            profile.year_1_fills,
            delta=f"+{profile.year_1_fills - profile.year_2_plus_fills} loading",
        )

    with col2:
        st.metric(
            "Maintenance Fills",
            profile.year_2_plus_fills,
            help="Annual fills after Year 1",
        )

    with col3:
        delta_pct = (
            (profile.year_1_fills - profile.year_2_plus_fills)
            / profile.year_2_plus_fills
            * 100
        )
        st.metric(
            "Year 1 Uplift",
            f"+{delta_pct:.0f}%",
            help="Additional revenue from loading doses",
        )


def _render_provenance_chain(drug: Drug, analysis: MarginAnalysis) -> None:
    """Render calculation provenance for auditability."""
    st.markdown(
        "Every calculated margin has a complete audit trail. "
        "Click to expand each calculation."
    )

    with st.expander("Retail Margin Calculation"):
        revenue = drug.awp * Decimal("0.85")
        st.markdown(f"""
        **Formula:** AWP × 85% × Capture Rate - Contract Cost

        **Inputs:**
        - AWP: ${drug.awp:,.2f}
        - Contract Cost: ${drug.contract_cost:,.2f}
        - Capture Rate: {analysis.retail_capture_rate:.0%}

        **Calculation:**
        1. Revenue = ${drug.awp:,.2f} × 0.85 = ${revenue:,.2f}
        2. Gross Margin = ${revenue:,.2f} - ${drug.contract_cost:,.2f}
           = ${analysis.retail_gross_margin:,.2f}
        3. Net Margin = ${analysis.retail_gross_margin:,.2f}
           × {analysis.retail_capture_rate:.0%} = ${analysis.retail_net_margin:,.2f}

        **Result:** ${analysis.retail_net_margin:,.2f}
        """)

    if analysis.medicare_margin is not None and drug.asp is not None:
        with st.expander("Medicare Margin Calculation"):
            med_rev = drug.asp * Decimal("1.06") * drug.bill_units_per_package
            st.markdown(f"""
            **Formula:** ASP × 1.06 × Bill Units - Contract Cost

            **Inputs:**
            - ASP: ${drug.asp:,.2f}
            - Bill Units per Package: {drug.bill_units_per_package}
            - Contract Cost: ${drug.contract_cost:,.2f}

            **Calculation:**
            1. Revenue = ${drug.asp:,.2f} × 1.06 × {drug.bill_units_per_package}
               = ${med_rev:,.2f}
            2. Margin = ${med_rev:,.2f} - ${drug.contract_cost:,.2f}
               = ${analysis.medicare_margin:,.2f}

            **Result:** ${analysis.medicare_margin:,.2f}
            """)

    if analysis.commercial_margin is not None and drug.asp is not None:
        with st.expander("Commercial Margin Calculation"):
            comm_rev = drug.asp * Decimal("1.15") * drug.bill_units_per_package
            st.markdown(f"""
            **Formula:** ASP × 1.15 × Bill Units - Contract Cost

            **Inputs:**
            - ASP: ${drug.asp:,.2f}
            - Bill Units per Package: {drug.bill_units_per_package}
            - Contract Cost: ${drug.contract_cost:,.2f}

            **Calculation:**
            1. Revenue = ${drug.asp:,.2f} × 1.15 × {drug.bill_units_per_package}
               = ${comm_rev:,.2f}
            2. Margin = ${comm_rev:,.2f} - ${drug.contract_cost:,.2f}
               = ${analysis.commercial_margin:,.2f}

            **Result:** ${analysis.commercial_margin:,.2f}
            """)

    with st.expander("Recommendation Logic"):
        med_display = (
            f"${analysis.medicare_margin:,.2f}"
            if analysis.medicare_margin else "N/A"
        )
        comm_display = (
            f"${analysis.commercial_margin:,.2f}"
            if analysis.commercial_margin else "N/A"
        )
        path_name = analysis.recommended_path.value.replace("_", " ")
        st.markdown(f"""
        **Available Pathways:**
        - Retail: ${analysis.retail_net_margin:,.2f}
        - Medicare: {med_display}
        - Commercial: {comm_display}

        **Selection:** Highest margin pathway selected.

        **Result:** {path_name}
        (${analysis.margin_delta:,.2f} better than next best option)
        """)
