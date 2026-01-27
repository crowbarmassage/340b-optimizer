"""NDC Lookup page for batch margin analysis.

Upload a CSV with drug names and NDC codes, validate matches against
product catalog, and output pharmacy channel margins.
"""

import io
import logging
from decimal import Decimal, InvalidOperation

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
    nadac = uploaded.get("nadac")

    if catalog is None:
        st.warning(
            "Please upload the Product Catalog first. "
            "Go to **Upload Data** in the sidebar."
        )
        return

    # Show data status
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"Product Catalog: {catalog.height:,} drugs loaded")
    with col2:
        if nadac is not None:
            st.info(f"NADAC Pricing: {nadac.height:,} prices loaded")
        else:
            st.warning("NADAC not loaded - Medicaid margins will be N/A")

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
                    results_df = _process_ndc_lookup(input_df, catalog, nadac)

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


def _extract_first_word(description: str) -> str:
    """Extract the first word (trade name) from drug description.

    Args:
        description: Full drug description.

    Returns:
        First word (trade name) in uppercase.
    """
    if not description:
        return ""

    # Get the first word - this is the trade name
    desc_upper = description.upper().strip()

    # Split on whitespace and take first word
    words = desc_upper.split()
    if words:
        return words[0]

    return ""


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

    # Extract first word (trade name) for comparison
    input_trade = _extract_first_word(input_name)
    catalog_trade = _extract_first_word(catalog_name)

    # Simple case-insensitive comparison of first word
    if _names_match(input_trade, catalog_trade):
        return "MATCH", True
    else:
        return "MISMATCH - VERIFY", False


def _process_ndc_lookup(
    input_df: pd.DataFrame,
    catalog: pl.DataFrame,
    nadac: pl.DataFrame | None = None,
) -> pd.DataFrame:
    """Process NDC lookup and calculate margins.

    Args:
        input_df: Input DataFrame with drug list.
        catalog: Product catalog DataFrame.
        nadac: Optional NADAC pricing DataFrame.

    Returns:
        Results DataFrame with match status and margins.
    """
    # Build catalog lookup by NDC
    catalog_lookup = _build_catalog_lookup(catalog)

    # Build NADAC lookup if available
    nadac_lookup = _build_nadac_lookup(nadac) if nadac is not None else {}

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

        # Look up NADAC price
        nadac_price = nadac_lookup.get(ndc11)

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
                contract_cost, awp, nadac_price, drug_type
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


def _find_column(columns: list[str], *candidates: str) -> str | None:
    """Find a column name from a list of candidates (case-insensitive).

    Args:
        columns: List of available column names.
        candidates: Possible column names to search for.

    Returns:
        Matching column name or None.
    """
    columns_upper = {c.upper(): c for c in columns}
    for candidate in candidates:
        if candidate.upper() in columns_upper:
            return columns_upper[candidate.upper()]
    return None


def _build_catalog_lookup(catalog: pl.DataFrame) -> dict[str, dict]:
    """Build lookup dictionary from catalog by NDC.

    Args:
        catalog: Product catalog DataFrame.

    Returns:
        Dictionary mapping NDC11 to catalog data.
    """
    lookup = {}

    # Find column names (case-insensitive)
    ndc_col = _find_column(catalog.columns, "NDC", "NDC11", "NDC Code")
    name_col = _find_column(catalog.columns, "Product Description", "Description", "Drug Name")
    cost_col = _find_column(catalog.columns, "Contract Cost", "ContractCost", "Cost")
    awp_col = _find_column(catalog.columns, "Medispan AWP", "AWP", "MedispanAWP", "Medispan_AWP")

    if not ndc_col:
        logger.error(f"NDC column not found in catalog. Available: {catalog.columns}")
        return lookup

    logger.info(f"Using columns: NDC={ndc_col}, Name={name_col}, Cost={cost_col}, AWP={awp_col}")

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
            except (ValueError, TypeError, InvalidOperation):
                contract_cost = None

        if awp is not None:
            try:
                awp = Decimal(str(awp))
            except (ValueError, TypeError, InvalidOperation):
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


def _build_nadac_lookup(nadac: pl.DataFrame) -> dict[str, Decimal]:
    """Build NADAC price lookup by NDC.

    Args:
        nadac: NADAC pricing DataFrame.

    Returns:
        Dictionary mapping NDC11 to NADAC price.
    """
    lookup = {}

    # Find column names
    ndc_col = _find_column(nadac.columns, "NDC", "ndc", "NDC11")
    price_col = _find_column(
        nadac.columns,
        "NADAC_Per_Unit",
        "nadac_per_unit",
        "NADAC",
        "nadac_price",
        "Price"
    )

    if not ndc_col or not price_col:
        logger.warning(f"NADAC columns not found. Available: {nadac.columns}")
        return lookup

    for row in nadac.iter_rows(named=True):
        raw_ndc = row.get(ndc_col, "")
        ndc11 = _normalize_ndc(raw_ndc)

        if not ndc11:
            continue

        price = row.get(price_col)
        if price is not None:
            try:
                lookup[ndc11] = Decimal(str(price))
            except (ValueError, TypeError, InvalidOperation):
                continue

    logger.info(f"Built NADAC lookup with {len(lookup)} NDCs")
    return lookup


def _calculate_pharmacy_margins(
    contract_cost: Decimal | None,
    awp: Decimal | None,
    nadac_price: Decimal | None,
    drug_type: str,
) -> tuple[Decimal | None, Decimal | None]:
    """Calculate pharmacy channel margins.

    Pharmacy Medicaid: NADAC - Contract Cost
    Pharmacy Medicare/Commercial: AWP × Rate - Contract Cost

    Args:
        contract_cost: 340B acquisition cost.
        awp: Average Wholesale Price.
        nadac_price: NADAC price per unit.
        drug_type: BRAND, SPECIALTY, or GENERIC.

    Returns:
        Tuple of (medicaid_margin, medicare_commercial_margin).
    """
    # Pharmacy Medicaid: NADAC - Contract Cost
    if contract_cost is not None and nadac_price is not None:
        medicaid_margin = nadac_price - contract_cost
    else:
        medicaid_margin = None

    # Pharmacy Medicare/Commercial: AWP × Rate - Contract Cost
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
