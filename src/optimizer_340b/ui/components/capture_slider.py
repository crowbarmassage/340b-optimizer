"""Capture rate slider component for 340B Optimizer."""

from decimal import Decimal

import streamlit as st


def render_capture_slider(
    key: str = "capture_rate",
    default: float = 0.45,
    label: str = "Retail Capture Rate",
) -> Decimal:
    """Render an interactive capture rate slider.

    The capture rate represents the percentage of eligible prescriptions
    that are actually captured through the retail pharmacy channel.

    Gatekeeper Test: Capture Rate Stress Test
    - If capture rate toggles from 100% to 40%, retail margin should
      drop proportionally.

    Args:
        key: Unique key for the slider widget.
        default: Default capture rate (0.0-1.0).
        label: Label to display above the slider.

    Returns:
        Selected capture rate as Decimal.
    """
    st.markdown(f"**{label}**")

    # Help text
    st.caption(
        "Adjust the expected percentage of eligible prescriptions "
        "captured through retail pharmacy."
    )

    # Preset buttons
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("40%", key=f"{key}_40"):
            st.session_state[key] = 0.40

    with col2:
        if st.button("45%", key=f"{key}_45"):
            st.session_state[key] = 0.45

    with col3:
        if st.button("60%", key=f"{key}_60"):
            st.session_state[key] = 0.60

    with col4:
        if st.button("100%", key=f"{key}_100"):
            st.session_state[key] = 1.00

    # Get current value from session state or use default
    current_value = st.session_state.get(key, default)

    # Slider
    capture_rate = st.slider(
        label="Capture Rate",
        min_value=0.0,
        max_value=1.0,
        value=float(current_value),
        step=0.05,
        format="%.0f%%",
        key=f"{key}_slider",
        label_visibility="collapsed",
        help="Drag to adjust capture rate. Lower rates reduce retail margins.",
    )

    # Store in session state
    st.session_state[key] = capture_rate

    # Display impact info
    if capture_rate < 0.45:
        st.warning(
            f"Low capture rate ({capture_rate:.0%}) significantly reduces "
            "retail margins. Consider medical billing pathway."
        )
    elif capture_rate >= 0.80:
        st.info(
            f"High capture rate ({capture_rate:.0%}) maximizes retail margins. "
            "Ensure this is achievable."
        )

    return Decimal(str(capture_rate))


def render_payer_toggle(key: str = "payer_type") -> str:
    """Render a payer type toggle for medical billing comparison.

    Args:
        key: Unique key for the toggle widget.

    Returns:
        Selected payer type ("medicare" or "commercial").
    """
    st.markdown("**Payer Type for Medical Comparison**")

    payer_type = st.radio(
        label="Payer Type",
        options=["Medicare (ASP + 6%)", "Commercial (ASP + 15%)"],
        horizontal=True,
        key=key,
        label_visibility="collapsed",
        help="Select payer type to compare against retail margins.",
    )

    # Map display name to internal value
    if "Medicare" in payer_type:
        return "medicare"
    return "commercial"


def render_sensitivity_controls() -> dict[str, Decimal]:
    """Render controls for margin sensitivity analysis.

    Returns:
        Dictionary with sensitivity parameters.
    """
    st.markdown("### Sensitivity Analysis")

    with st.expander("Configure Scenarios", expanded=False):
        st.caption("Define capture rate scenarios for comparison.")

        # Allow user to select multiple capture rates
        scenarios = st.multiselect(
            "Select capture rate scenarios:",
            options=["40%", "45%", "60%", "80%", "100%"],
            default=["40%", "45%", "60%"],
            key="sensitivity_scenarios",
        )

        # Convert to decimals
        rate_map = {
            "40%": Decimal("0.40"),
            "45%": Decimal("0.45"),
            "60%": Decimal("0.60"),
            "80%": Decimal("0.80"),
            "100%": Decimal("1.00"),
        }

        return {s: rate_map[s] for s in scenarios}
