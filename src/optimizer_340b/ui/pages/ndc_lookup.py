"""NDC Lookup page for batch margin analysis.

Upload a CSV with drug names and NDC codes, validate matches against
product catalog, and output pharmacy channel margins.
"""

import io
import logging
from decimal import Decimal

import pandas as pd
import polars as pl
import streamlit as st

logger = logging.getLogger(__name__)

# AWP multipliers by drug type
AWP_MULTIPLIERS = {
    "BRAND": Decimal("0.85"),
    "SPECIALTY": Decimal("0.85"),
    "GENERIC": Decimal("0.20"),
}


def render_ndc_lookup_page() -> None:
    """Render the NDC Lookup page for batch margin analysis."""
    st.title("NDC Lookup & Margin Calculator")
    st.markdown(
        """
        Upload a CSV with drug names and NDC codes to:
        - Validate drug name matches against the product catalog
        - Calculate pharmacy channel margins (Medicaid & Medicare/Commercial)
        - Download results with match status and margins
        """
    )

    # Check if catalog is loaded
    uploaded = st.session_state.get("uploaded_data", {})
    catalog = uploaded.get("catalog")

    if catalog is None:
        st.warning(
            "Please upload the Product Catalog first. "
            "Go to **Upload Data** in the sidebar."
        )
        return

    st.markdown("---")

    # File format instructions
    with st.expander("CSV Format Requirements", expanded=False):
        st.markdown(
            """
            **Required columns (in order):**
            1. `Drug Description` - Your drug name/description
            2. `NDC11` - NDC code (will be left-padded to 11 digits)
            3. `Type` - BRAND, SPECIALTY, or GENERIC
            4. `Product Description` - Expected catalog description (optional)

            **Example:**
            ```
            Drug Description,NDC11,Type,Product Description
            HUMIRA PEN 40 MG/0.8ML,74433902,SPECIALTY,HUMIRA PEN KT 40MG/0.8ML 2
            ELIQUIS 5 MG TABLET,3089421,BRAND,ELIQUIS TB 5MG 60
            ```
            """
        )

    # File upload
    uploaded_file = st.file_uploader(
        "Upload NDC List (CSV)",
        type=["csv"],
        help="CSV with Drug Description, NDC11, Type, Product Description columns",
    )

    if uploaded_file is not None:
        try:
            # Read the uploaded CSV
            input_df = _parse_input_csv(uploaded_file)

            if input_df is None or len(input_df) == 0:
                st.error("Could not parse CSV. Please check the format.")
                return

            st.success(f"Loaded {len(input_df)} rows from CSV")

            # Show preview
            with st.expander("Preview Input Data", expanded=True):
                st.dataframe(input_df.head(10), use_container_width=True)

            # Process button
            if st.button("Calculate Margins", type="primary"):
                with st.spinner("Processing NDC lookups..."):
                    results_df = _process_ndc_lookup(input_df, catalog)

                if results_df is not None and len(results_df) > 0:
                    st.markdown("---")
                    st.markdown("### Results")

                    # Summary metrics
                    _render_summary_metrics(results_df)

                    # Results table
                    st.dataframe(results_df, use_container_width=True)

                    # Download button
                    csv_buffer = io.StringIO()
                    results_df.to_csv(csv_buffer, index=False)
                    csv_data = csv_buffer.getvalue()

                    st.download_button(
                        label="Download Results CSV",
                        data=csv_data,
                        file_name="ndc_margin_results.csv",
                        mime="text/csv",
                    )

        except Exception as e:
            logger.exception("Error processing NDC lookup")
            st.error(f"Error processing file: {e}")


def _parse_input_csv(uploaded_file) -> pd.DataFrame | None:
    """Parse the uploaded CSV file.

    Expected columns: Drug Description, NDC11, Type, Product Description

    Args:
        uploaded_file: Streamlit uploaded file object.

    Returns:
        DataFrame with standardized columns, or None if parsing fails.
    """
    try:
        # Try reading with different options
        content = uploaded_file.getvalue().decode("utf-8")

        # Check if it has headers
        first_line = content.split("\n")[0].strip()

        # If no comma in first line, try tab-separated
        if "," not in first_line:
            df = pd.read_csv(
                io.StringIO(content),
                sep="\t",
                header=None,
                names=["Drug Description", "NDC11", "Type", "Product Description"],
            )
        elif "Drug Description" in first_line or "drug" in first_line.lower():
            # Has headers
            df = pd.read_csv(io.StringIO(content))
        else:
            # No headers, assign column names
            df = pd.read_csv(
                io.StringIO(content),
                header=None,
                names=["Drug Description", "NDC11", "Type", "Product Description"],
            )

        # Standardize column names
        df.columns = [
            "Drug Description",
            "NDC11",
            "Type",
            "Product Description",
        ][: len(df.columns)]

        # Ensure we have at least the required columns
        if len(df.columns) < 2:
            logger.error("CSV must have at least Drug Description and NDC11 columns")
            return None

        # Add missing columns if needed
        if "Type" not in df.columns:
            df["Type"] = "BRAND"
        if "Product Description" not in df.columns:
            df["Product Description"] = ""

        return df

    except Exception as e:
        logger.exception(f"Error parsing CSV: {e}")
        return None


def _normalize_ndc(ndc: str | int | float) -> str:
    """Normalize NDC to 11 digits with left-padding.

    Args:
        ndc: NDC value (may be numeric or string).

    Returns:
        11-digit NDC string with leading zeros.
    """
    if pd.isna(ndc):
        return ""

    # Convert to string and clean
    ndc_str = str(ndc).strip()

    # Remove any non-numeric characters
    ndc_clean = "".join(c for c in ndc_str if c.isdigit())

    # Left-pad to 11 digits
    return ndc_clean.zfill(11)


def _names_match(str1: str, str2: str) -> bool:
    """Check if two drug names match (case-insensitive).

    Args:
        str1: First drug name.
        str2: Second drug name.

    Returns:
        True if names match (case-insensitive).
    """
    if not str1 or not str2:
        return False

    # Normalize strings: uppercase and strip whitespace
    s1 = str1.upper().strip()
    s2 = str2.upper().strip()

    return s1 == s2


def _extract_trade_name(description: str) -> str:
    """Extract trade name from drug description.

    Takes the first word(s) before common suffixes like MG, ML, TB, etc.

    Args:
        description: Full drug description.

    Returns:
        Extracted trade name.
    """
    if not description:
        return ""

    # Common patterns that indicate end of trade name
    stop_patterns = [
        " MG", " MCG", " ML", " TB", " CP", " SY", " VL", " PR", " KT",
        " IN", " GL", " AP", " SF", " PF", " PPN", " PFS", " SPD",
        " 0.", " 1.", " 2.", " 3.", " 4.", " 5.", " 6.", " 7.", " 8.", " 9.",
        " 10", " 20", " 30", " 40", " 50", " 60", " 70", " 80", " 90",
        " 100", " 200", " 300", " 400", " 500",
    ]

    desc_upper = description.upper()

    # Find earliest stop pattern
    earliest_pos = len(desc_upper)
    for pattern in stop_patterns:
        pos = desc_upper.find(pattern)
        if pos > 0 and pos < earliest_pos:
            earliest_pos = pos

    return desc_upper[:earliest_pos].strip()


def _determine_match_status(
    input_name: str,
    catalog_name: str | None,
    ndc_found: bool,
) -> tuple[str, bool]:
    """Determine match status based on drug name comparison.

    Args:
        input_name: User's drug name.
        catalog_name: Catalog drug name (None if NDC not found).
        ndc_found: Whether NDC was found in catalog.

    Returns:
        Tuple of (status_string, is_match).
    """
    if not ndc_found:
        return "NDC NOT FOUND", False

    if not catalog_name:
        return "NO CATALOG NAME", False

    # Extract trade names for comparison
    input_trade = _extract_trade_name(input_name)
    catalog_trade = _extract_trade_name(catalog_name)

    # Simple case-insensitive comparison
    if _names_match(input_trade, catalog_trade):
        return "MATCH", True
    else:
        return "MISMATCH - VERIFY", False


def _process_ndc_lookup(
    input_df: pd.DataFrame,
    catalog: pl.DataFrame,
) -> pd.DataFrame:
    """Process NDC lookup and calculate margins.

    Args:
        input_df: Input DataFrame with drug list.
        catalog: Product catalog DataFrame.

    Returns:
        Results DataFrame with match status and margins.
    """
    # Build catalog lookup by NDC
    catalog_lookup = _build_catalog_lookup(catalog)

    results = []

    for _, row in input_df.iterrows():
        input_name = str(row.get("Drug Description", "")).strip()
        raw_ndc = row.get("NDC11", "")
        drug_type = str(row.get("Type", "BRAND")).upper().strip()
        expected_desc = str(row.get("Product Description", "")).strip()

        # Normalize NDC
        ndc11 = _normalize_ndc(raw_ndc)

        # Look up in catalog
        catalog_data = catalog_lookup.get(ndc11)

        if catalog_data:
            catalog_name = catalog_data.get("drug_name", "")
            contract_cost = catalog_data.get("contract_cost")
            awp = catalog_data.get("awp")

            # Determine match status (simple case-insensitive comparison)
            match_status, is_match = _determine_match_status(
                input_name, catalog_name, True
            )

            # Calculate margins if we have pricing
            medicaid_margin, medicare_commercial_margin = _calculate_pharmacy_margins(
                contract_cost, awp, drug_type
            )
        else:
            catalog_name = ""
            contract_cost = None
            awp = None
            match_status, is_match = _determine_match_status(
                input_name, None, False
            )
            medicaid_margin = None
            medicare_commercial_margin = None

        results.append({
            "Input Drug Name": input_name,
            "NDC11": ndc11,
            "Match Status": match_status,
            "Catalog Description": catalog_name,
            "Type": drug_type,
            "Contract Cost": _format_currency(contract_cost),
            "AWP": _format_currency(awp),
            "Pharmacy Medicaid Margin": _format_currency(medicaid_margin),
            "Pharmacy Medicare/Commercial Margin": _format_currency(
                medicare_commercial_margin
            ),
        })

    return pd.DataFrame(results)


def _build_catalog_lookup(catalog: pl.DataFrame) -> dict[str, dict]:
    """Build lookup dictionary from catalog by NDC.

    Args:
        catalog: Product catalog DataFrame.

    Returns:
        Dictionary mapping NDC11 to catalog data.
    """
    lookup = {}

    # Find column names
    ndc_col = "NDC" if "NDC" in catalog.columns else None
    name_col = "Product Description" if "Product Description" in catalog.columns else None
    cost_col = "Contract Cost" if "Contract Cost" in catalog.columns else None
    awp_col = "Medispan AWP" if "Medispan AWP" in catalog.columns else None

    if not ndc_col:
        logger.error("NDC column not found in catalog")
        return lookup

    for row in catalog.iter_rows(named=True):
        raw_ndc = row.get(ndc_col, "")
        ndc11 = _normalize_ndc(raw_ndc)

        if not ndc11:
            continue

        # Get values
        drug_name = str(row.get(name_col, "")) if name_col else ""
        contract_cost = row.get(cost_col) if cost_col else None
        awp = row.get(awp_col) if awp_col else None

        # Convert to Decimal if numeric
        if contract_cost is not None:
            try:
                contract_cost = Decimal(str(contract_cost))
            except (ValueError, TypeError):
                contract_cost = None

        if awp is not None:
            try:
                awp = Decimal(str(awp))
            except (ValueError, TypeError):
                awp = None

        # Store first occurrence (or best price)
        if ndc11 not in lookup:
            lookup[ndc11] = {
                "drug_name": drug_name,
                "contract_cost": contract_cost,
                "awp": awp,
            }
        else:
            # Keep the one with lower contract cost (best 340B price)
            existing_cost = lookup[ndc11].get("contract_cost")
            if (
                contract_cost is not None
                and (existing_cost is None or contract_cost < existing_cost)
            ):
                lookup[ndc11] = {
                    "drug_name": drug_name,
                    "contract_cost": contract_cost,
                    "awp": awp,
                }

    logger.info(f"Built catalog lookup with {len(lookup)} unique NDCs")
    return lookup


def _calculate_pharmacy_margins(
    contract_cost: Decimal | None,
    awp: Decimal | None,
    drug_type: str,
) -> tuple[Decimal | None, Decimal | None]:
    """Calculate pharmacy channel margins.

    Pharmacy Medicaid: NADAC - Contract Cost (NADAC not in product_catalog, so N/A)
    Pharmacy Medicare/Commercial: AWP × Rate - Contract Cost

    Args:
        contract_cost: 340B acquisition cost.
        awp: Average Wholesale Price.
        drug_type: BRAND, SPECIALTY, or GENERIC.

    Returns:
        Tuple of (medicaid_margin, medicare_commercial_margin).
    """
    # Pharmacy Medicaid requires NADAC which is not in product_catalog
    # So we return None for this pathway
    medicaid_margin = None

    # Pharmacy Medicare/Commercial
    if contract_cost is not None and awp is not None:
        # Get AWP multiplier based on drug type
        multiplier = AWP_MULTIPLIERS.get(drug_type.upper(), Decimal("0.85"))
        revenue = awp * multiplier
        medicare_commercial_margin = revenue - contract_cost
    else:
        medicare_commercial_margin = None

    return medicaid_margin, medicare_commercial_margin


def _format_currency(value: Decimal | None) -> str:
    """Format value as currency string.

    Args:
        value: Decimal value or None.

    Returns:
        Formatted string like "$1,234.56" or "N/A".
    """
    if value is None:
        return "N/A"

    try:
        return f"${float(value):,.2f}"
    except (ValueError, TypeError):
        return "N/A"


def _render_summary_metrics(results_df: pd.DataFrame) -> None:
    """Render summary metrics for the results.

    Args:
        results_df: Results DataFrame.
    """
    col1, col2, col3, col4 = st.columns(4)

    total = len(results_df)

    with col1:
        st.metric("Total Drugs", total)

    with col2:
        matches = len(results_df[results_df["Match Status"] == "MATCH"])
        st.metric("Matches", matches)

    with col3:
        mismatches = len(
            results_df[results_df["Match Status"].str.contains("MISMATCH|NOT FOUND")]
        )
        st.metric("Mismatches", mismatches)

    with col4:
        has_margin = len(
            results_df[results_df["Pharmacy Medicare/Commercial Margin"] != "N/A"]
        )
        st.metric("With Margins", has_margin)
