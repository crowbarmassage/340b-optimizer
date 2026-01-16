"""File upload page for 340B Optimizer."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
import polars as pl
import streamlit as st

from optimizer_340b.ingest.loaders import load_csv_to_polars, load_excel_to_polars
from optimizer_340b.ingest.normalizers import (
    normalize_catalog,
    normalize_crosswalk,
    normalize_noc_crosswalk,
    normalize_noc_pricing,
    preprocess_cms_csv,
)
from optimizer_340b.ingest.validators import (
    ValidationResult,
    validate_asp_schema,
    validate_catalog_schema,
    validate_crosswalk_schema,
    validate_nadac_schema,
    validate_noc_crosswalk_schema,
    validate_noc_pricing_schema,
)
from optimizer_340b.risk.ira_flags import reload_ira_drugs

# Sample data directory
SAMPLE_DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data" / "sample"

logger = logging.getLogger(__name__)


def _load_cms_csv_with_skip(uploaded_file: Any, skip_rows: int = 8) -> pl.DataFrame:
    """Load CMS CSV file, skipping header metadata rows.

    Args:
        uploaded_file: Streamlit uploaded file object.
        skip_rows: Number of header rows to skip.

    Returns:
        Polars DataFrame.
    """
    # Save to temp file and use preprocess function
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        return preprocess_cms_csv(tmp_path, skip_rows=skip_rows)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _check_sample_data_available() -> bool:
    """Check if sample data files are available."""
    required_files = [
        "product_catalog.xlsx",
        "asp_pricing.csv",
        "asp_crosswalk.csv",
    ]
    return all((SAMPLE_DATA_DIR / f).exists() for f in required_files)


def _load_sample_data() -> None:
    """Load sample data files into session state."""
    if "uploaded_data" not in st.session_state:
        st.session_state.uploaded_data = {}

    # Load product catalog (normalize first to map column names)
    catalog_path = SAMPLE_DATA_DIR / "product_catalog.xlsx"
    if catalog_path.exists():
        df = load_excel_to_polars(str(catalog_path))
        df = normalize_catalog(df)  # Maps Medispan AWP -> AWP, etc.
        result = validate_catalog_schema(df)
        if result.is_valid:
            st.session_state.uploaded_data["catalog"] = df
            logger.info(f"Loaded sample catalog: {df.height} rows")
        else:
            logger.warning(f"Catalog validation failed: {result.message}")

    # Load ASP pricing (CMS file with header rows)
    asp_path = SAMPLE_DATA_DIR / "asp_pricing.csv"
    if asp_path.exists():
        df = preprocess_cms_csv(str(asp_path), skip_rows=8)
        result = validate_asp_schema(df)
        if result.is_valid:
            st.session_state.uploaded_data["asp_pricing"] = df
            logger.info(f"Loaded sample ASP pricing: {df.height} rows")

    # Load crosswalk (CMS file with header rows, normalize column names)
    crosswalk_path = SAMPLE_DATA_DIR / "asp_crosswalk.csv"
    if crosswalk_path.exists():
        df = preprocess_cms_csv(str(crosswalk_path), skip_rows=8)
        df = normalize_crosswalk(df)  # Maps _2025_CODE -> HCPCS Code, NDC2 -> NDC
        result = validate_crosswalk_schema(df)
        if result.is_valid:
            st.session_state.uploaded_data["crosswalk"] = df
            logger.info(f"Loaded sample crosswalk: {df.height} rows")
        else:
            logger.warning(f"Crosswalk validation failed: {result.message}")

    # Load NADAC (optional)
    nadac_path = SAMPLE_DATA_DIR / "ndc_nadac_master_statistics.csv"
    if nadac_path.exists():
        df = load_csv_to_polars(str(nadac_path))
        result = validate_nadac_schema(df)
        if result.is_valid:
            st.session_state.uploaded_data["nadac"] = df
            logger.info(f"Loaded sample NADAC: {df.height} rows")

    # Load biologics logic grid (optional)
    biologics_path = SAMPLE_DATA_DIR / "biologics_logic_grid.xlsx"
    if biologics_path.exists():
        df = load_excel_to_polars(str(biologics_path))
        st.session_state.uploaded_data["biologics"] = df
        logger.info(f"Loaded sample biologics: {df.height} rows")

    # Load NOC pricing (optional - fallback for drugs without J-codes)
    noc_pricing_path = SAMPLE_DATA_DIR / "noc_pricing.csv"
    if noc_pricing_path.exists():
        df = preprocess_cms_csv(str(noc_pricing_path), skip_rows=12)
        df = normalize_noc_pricing(df)
        result = validate_noc_pricing_schema(df)
        if result.is_valid:
            st.session_state.uploaded_data["noc_pricing"] = df
            logger.info(f"Loaded sample NOC pricing: {df.height} rows")

    # Load NOC crosswalk (optional - fallback for drugs without J-codes)
    noc_crosswalk_path = SAMPLE_DATA_DIR / "noc_crosswalk.csv"
    if noc_crosswalk_path.exists():
        df = preprocess_cms_csv(str(noc_crosswalk_path), skip_rows=9)
        df = normalize_noc_crosswalk(df)
        result = validate_noc_crosswalk_schema(df)
        if result.is_valid:
            st.session_state.uploaded_data["noc_crosswalk"] = df
            logger.info(f"Loaded sample NOC crosswalk: {df.height} rows")

    # Load Ravenswood AWP Reimbursement Matrix (optional - payer-specific multipliers)
    ravenswood_path = SAMPLE_DATA_DIR / "Ravenswood_AWP_Reimbursement_Matrix.xlsx"
    if ravenswood_path.exists():
        try:
            # Load Drug Categories sheet for drug classification
            df = load_excel_to_polars(
                str(ravenswood_path), sheet_name="Drug Categories"
            )
            st.session_state.uploaded_data["ravenswood_categories"] = df
            logger.info(f"Loaded Ravenswood drug categories: {df.height} rows")
        except Exception as e:
            logger.warning(f"Could not load Ravenswood drug categories: {e}")

        try:
            # Load Summary sheet for payer mix (may have mixed types)
            pdf = pd.read_excel(str(ravenswood_path), sheet_name="Summary")
            # Convert all columns to string to avoid type issues
            df_summary = pl.from_pandas(pdf.astype(str))
            st.session_state.uploaded_data["ravenswood_summary"] = df_summary
            logger.info(f"Loaded Ravenswood payer summary: {df_summary.height} rows")
        except Exception as e:
            logger.warning(f"Could not load Ravenswood summary: {e}")

    # Load Wholesaler Catalog (optional - retail validation)
    wholesaler_path = SAMPLE_DATA_DIR / "wholesaler_catalog.xlsx"
    if wholesaler_path.exists():
        df = load_excel_to_polars(str(wholesaler_path))
        st.session_state.uploaded_data["wholesaler_catalog"] = df
        logger.info(f"Loaded wholesaler catalog: {df.height} rows")

    # Load IRA Drug List (optional - data-driven IRA flags)
    ira_path = SAMPLE_DATA_DIR / "ira_drug_list.csv"
    if ira_path.exists():
        df = load_csv_to_polars(str(ira_path))
        st.session_state.uploaded_data["ira_drugs"] = df
        # Reload the IRA flags module with the new data
        reload_ira_drugs(df=df)
        logger.info(f"Loaded IRA drug list: {df.height} drugs")


def render_upload_page() -> None:
    """Render the file upload page.

    Allows users to upload required data files:
    - Product Catalog (XLSX)
    - ASP Pricing File (CSV)
    - ASP NDC-HCPCS Crosswalk (CSV)
    - NADAC Statistics (CSV) - Optional
    - Biologics Logic Grid (XLSX) - Optional
    """
    st.title("Data Upload")
    st.markdown(
        "Upload your data files to begin optimization analysis. "
        "Required files are marked with an asterisk (*)."
    )

    # Initialize session state for uploaded data
    if "uploaded_data" not in st.session_state:
        st.session_state.uploaded_data = {}

    # Quick start with sample data
    if _check_sample_data_available():
        st.markdown("### Quick Start")
        st.info(
            "Sample data files are available. Click below to load and process them "
            "instantly, then explore the app without uploading your own files."
        )
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("Load & Process Sample Data", type="primary"):
                with st.spinner("Loading and processing sample data..."):
                    _load_sample_data()
                    _process_uploaded_data()
                st.success("Sample data loaded and processed! Navigate to Dashboard.")
                st.rerun()
        with col2:
            st.caption(
                "Includes: Product Catalog, ASP Pricing, Crosswalk, NADAC, "
                "Biologics Logic Grid, and NOC fallback files"
            )

        st.markdown("---")

    # File upload sections
    _render_catalog_upload()
    _render_asp_pricing_upload()
    _render_crosswalk_upload()
    _render_noc_pricing_upload()
    _render_noc_crosswalk_upload()
    _render_nadac_upload()
    _render_biologics_upload()
    _render_ravenswood_upload()
    _render_wholesaler_upload()
    _render_ira_upload()

    # Validation summary
    st.markdown("---")
    _render_validation_summary()


def _render_catalog_upload() -> None:
    """Render product catalog upload section."""
    st.markdown("### Product Catalog *")
    st.caption(
        "Excel file containing NDC, Drug Name, Contract Cost, and AWP. "
        "Expected columns: NDC, Drug Name, Contract Cost, AWP (or Medispan AWP)"
    )

    uploaded_file = st.file_uploader(
        "Upload Product Catalog",
        type=["xlsx", "xls"],
        key="catalog_upload",
        help="Your 340B product catalog with pricing information",
    )

    if uploaded_file is not None:
        with st.spinner("Loading catalog..."):
            try:
                # Save to temp file and load
                df = load_excel_to_polars(uploaded_file)

                # Validate schema
                result = validate_catalog_schema(df)

                if result.is_valid:
                    st.session_state.uploaded_data["catalog"] = df
                    st.success(f"Loaded {df.height:,} drugs from catalog")
                    _show_validation_result(result)

                    # Preview
                    with st.expander("Preview Data"):
                        st.dataframe(df.head(10).to_pandas(), width="stretch")
                else:
                    st.error("Validation failed")
                    _show_validation_result(result)

            except Exception as e:
                st.error(f"Error loading file: {e}")
                logger.exception("Error loading catalog")


def _render_asp_pricing_upload() -> None:
    """Render ASP pricing file upload section."""
    st.markdown("### ASP Pricing File *")
    st.caption(
        "CMS ASP pricing file (CSV). Note: First 8 rows are typically header metadata. "
        "Expected columns: HCPCS Code, Payment Limit"
    )

    uploaded_file = st.file_uploader(
        "Upload ASP Pricing File",
        type=["csv"],
        key="asp_upload",
        help="CMS Medicare Part B ASP pricing file",
    )

    if uploaded_file is not None:
        with st.spinner("Loading ASP pricing..."):
            try:
                # CMS files have 8 header rows to skip
                df = _load_cms_csv_with_skip(uploaded_file, skip_rows=8)

                # Validate schema
                result = validate_asp_schema(df)

                if result.is_valid:
                    st.session_state.uploaded_data["asp_pricing"] = df
                    st.success(f"Loaded {df.height:,} HCPCS pricing records")
                    _show_validation_result(result)

                    with st.expander("Preview Data"):
                        st.dataframe(df.head(10).to_pandas(), width="stretch")
                else:
                    st.error("Validation failed")
                    _show_validation_result(result)

            except Exception as e:
                st.error(f"Error loading file: {e}")
                logger.exception("Error loading ASP pricing")


def _render_crosswalk_upload() -> None:
    """Render NDC-HCPCS crosswalk upload section."""
    st.markdown("### ASP NDC-HCPCS Crosswalk *")
    st.caption(
        "CMS crosswalk mapping NDC to HCPCS codes (CSV). "
        "Note: First 8 rows are typically header metadata. "
        "Expected columns: NDC (or NDC2), HCPCS Code (or _2025_CODE)"
    )

    uploaded_file = st.file_uploader(
        "Upload NDC-HCPCS Crosswalk",
        type=["csv"],
        key="crosswalk_upload",
        help="CMS NDC to HCPCS code mapping file",
    )

    if uploaded_file is not None:
        with st.spinner("Loading crosswalk..."):
            try:
                # CMS files have 8 header rows to skip
                df = _load_cms_csv_with_skip(uploaded_file, skip_rows=8)

                # Validate schema
                result = validate_crosswalk_schema(df)

                if result.is_valid:
                    st.session_state.uploaded_data["crosswalk"] = df
                    st.success(f"Loaded {df.height:,} NDC-HCPCS mappings")
                    _show_validation_result(result)

                    with st.expander("Preview Data"):
                        st.dataframe(df.head(10).to_pandas(), width="stretch")
                else:
                    st.error("Validation failed")
                    _show_validation_result(result)

            except Exception as e:
                st.error(f"Error loading file: {e}")
                logger.exception("Error loading crosswalk")


def _render_noc_pricing_upload() -> None:
    """Render NOC pricing file upload section."""
    st.markdown("### NOC Pricing File (Optional)")
    st.caption(
        "CMS NOC pricing file for drugs without permanent J-codes (CSV). "
        "Provides fallback reimbursement rates for new drugs. "
        "Expected columns: Drug Generic Name, Payment Limit"
    )

    uploaded_file = st.file_uploader(
        "Upload NOC Pricing File",
        type=["csv"],
        key="noc_pricing_upload",
        help="CMS NOC (Not Otherwise Classified) drug pricing file",
    )

    if uploaded_file is not None:
        with st.spinner("Loading NOC pricing..."):
            try:
                # NOC pricing file has 12 header rows to skip
                df = _load_cms_csv_with_skip(uploaded_file, skip_rows=12)
                df = normalize_noc_pricing(df)

                # Validate schema
                result = validate_noc_pricing_schema(df)

                if result.is_valid:
                    st.session_state.uploaded_data["noc_pricing"] = df
                    st.success(f"Loaded {df.height:,} NOC drug pricing records")
                    _show_validation_result(result)

                    with st.expander("Preview Data"):
                        st.dataframe(df.head(10).to_pandas(), width="stretch")
                else:
                    st.error("Validation failed")
                    _show_validation_result(result)

            except Exception as e:
                st.error(f"Error loading file: {e}")
                logger.exception("Error loading NOC pricing")


def _render_noc_crosswalk_upload() -> None:
    """Render NOC crosswalk file upload section."""
    st.markdown("### NOC NDC-HCPCS Crosswalk (Optional)")
    st.caption(
        "CMS NOC crosswalk for drugs without permanent J-codes (CSV). "
        "Maps NDCs to generic drug names for fallback pricing lookup. "
        "Expected columns: NDC, Drug Generic Name"
    )

    uploaded_file = st.file_uploader(
        "Upload NOC Crosswalk",
        type=["csv"],
        key="noc_crosswalk_upload",
        help="CMS NOC NDC to generic drug name mapping file",
    )

    if uploaded_file is not None:
        with st.spinner("Loading NOC crosswalk..."):
            try:
                # NOC crosswalk file has 9 header rows to skip
                df = _load_cms_csv_with_skip(uploaded_file, skip_rows=9)
                df = normalize_noc_crosswalk(df)

                # Validate schema
                result = validate_noc_crosswalk_schema(df)

                if result.is_valid:
                    st.session_state.uploaded_data["noc_crosswalk"] = df
                    st.success(f"Loaded {df.height:,} NOC NDC mappings")
                    _show_validation_result(result)

                    with st.expander("Preview Data"):
                        st.dataframe(df.head(10).to_pandas(), width="stretch")
                else:
                    st.error("Validation failed")
                    _show_validation_result(result)

            except Exception as e:
                st.error(f"Error loading file: {e}")
                logger.exception("Error loading NOC crosswalk")


def _render_nadac_upload() -> None:
    """Render NADAC statistics upload section."""
    st.markdown("### NADAC Statistics (Optional)")
    st.caption(
        "NADAC pricing statistics for penny pricing detection (CSV). "
        "Expected columns: ndc, total_discount_340b_pct"
    )

    uploaded_file = st.file_uploader(
        "Upload NADAC Statistics",
        type=["csv"],
        key="nadac_upload",
        help="National Average Drug Acquisition Cost statistics",
    )

    if uploaded_file is not None:
        with st.spinner("Loading NADAC data..."):
            try:
                df = load_csv_to_polars(uploaded_file)

                # Validate schema
                result = validate_nadac_schema(df)

                if result.is_valid:
                    st.session_state.uploaded_data["nadac"] = df
                    st.success(f"Loaded {df.height:,} NADAC records")
                    _show_validation_result(result)

                    with st.expander("Preview Data"):
                        st.dataframe(df.head(10).to_pandas(), width="stretch")
                else:
                    st.warning("Validation warnings")
                    _show_validation_result(result)

            except Exception as e:
                st.error(f"Error loading file: {e}")
                logger.exception("Error loading NADAC")


def _render_biologics_upload() -> None:
    """Render biologics logic grid upload section."""
    st.markdown("### Biologics Logic Grid (Optional)")
    st.caption(
        "Excel file with loading dose patterns for biologics. "
        "Expected columns: Drug Name, Indication, Year 1 Fills, Year 2+ Fills"
    )

    uploaded_file = st.file_uploader(
        "Upload Biologics Logic Grid",
        type=["xlsx", "xls"],
        key="biologics_upload",
        help="Loading dose schedule for biologics",
    )

    if uploaded_file is not None:
        with st.spinner("Loading biologics grid..."):
            try:
                df = load_excel_to_polars(uploaded_file)
                st.session_state.uploaded_data["biologics"] = df
                st.success(f"Loaded {df.height:,} dosing profiles")

                with st.expander("Preview Data"):
                    st.dataframe(df.head(10).to_pandas(), width="stretch")

            except Exception as e:
                st.error(f"Error loading file: {e}")
                logger.exception("Error loading biologics grid")


def _render_ravenswood_upload() -> None:
    """Render Ravenswood AWP Reimbursement Matrix upload section."""
    st.markdown("### AWP Reimbursement Matrix (Optional)")
    st.caption(
        "Excel file with payer-specific AWP multipliers for retail revenue "
        "calculation. Contains drug category classifications "
        "(Generic/Brand/Specialty) and payer mix. "
        "If not provided, a default 85% AWP multiplier will be used."
    )

    uploaded_file = st.file_uploader(
        "Upload AWP Reimbursement Matrix",
        type=["xlsx", "xls"],
        key="ravenswood_upload",
        help="Payer-specific AWP reimbursement multipliers",
    )

    if uploaded_file is not None:
        with st.spinner("Loading AWP matrix..."):
            try:
                # Load Drug Categories sheet
                df_categories = load_excel_to_polars(
                    uploaded_file, sheet_name="Drug Categories"
                )
                st.session_state.uploaded_data["ravenswood_categories"] = df_categories

                # Reload file for Summary sheet (may have mixed types)
                uploaded_file.seek(0)
                pdf_summary = pd.read_excel(uploaded_file, sheet_name="Summary")
                df_summary = pl.from_pandas(pdf_summary.astype(str))
                st.session_state.uploaded_data["ravenswood_summary"] = df_summary

                st.success(
                    f"Loaded AWP matrix: {df_categories.height} drug categories, "
                    f"{df_summary.height} payer entries"
                )

                with st.expander("Preview Drug Categories"):
                    st.dataframe(df_categories.head(10).to_pandas(), width="stretch")

                with st.expander("Preview Payer Summary"):
                    st.dataframe(df_summary.head(10).to_pandas(), width="stretch")

            except Exception as e:
                st.error(f"Error loading file: {e}")
                logger.exception("Error loading Ravenswood matrix")


def _render_wholesaler_upload() -> None:
    """Render Wholesaler Catalog upload section."""
    st.markdown("### Wholesaler Catalog (Optional)")
    st.caption(
        "Excel file with real-world retail pricing for validation. "
        "Used to flag records where calculated retail differs from actual by >20%. "
        "Expected column: Product Catalog Unit Price (Current Retail) Average"
    )

    uploaded_file = st.file_uploader(
        "Upload Wholesaler Catalog",
        type=["xlsx", "xls"],
        key="wholesaler_upload",
        help="Wholesaler pricing data for retail validation",
    )

    if uploaded_file is not None:
        with st.spinner("Loading wholesaler catalog..."):
            try:
                df = load_excel_to_polars(uploaded_file)
                st.session_state.uploaded_data["wholesaler_catalog"] = df
                st.success(f"Loaded {df.height:,} wholesaler catalog entries")

                with st.expander("Preview Data"):
                    st.dataframe(df.head(10).to_pandas(), width="stretch")

            except Exception as e:
                st.error(f"Error loading file: {e}")
                logger.exception("Error loading wholesaler catalog")


def _render_ira_upload() -> None:
    """Render IRA Drug List upload section."""
    st.markdown("### IRA Drug List (Optional)")
    st.caption(
        "CSV file with IRA (Inflation Reduction Act) negotiated drugs. "
        "Updates the IRA risk flagging with the latest drug list. "
        "Expected columns: drug_name, ira_year, description"
    )

    uploaded_file = st.file_uploader(
        "Upload IRA Drug List",
        type=["csv"],
        key="ira_upload",
        help="List of drugs subject to Medicare price negotiation under IRA",
    )

    if uploaded_file is not None:
        with st.spinner("Loading IRA drug list..."):
            try:
                df = load_csv_to_polars(uploaded_file)

                # Validate expected columns
                expected_cols = {"drug_name", "ira_year", "description"}
                actual_cols = set(df.columns)
                if not expected_cols.issubset(actual_cols):
                    missing = expected_cols - actual_cols
                    st.error(f"Missing required columns: {', '.join(missing)}")
                    return

                st.session_state.uploaded_data["ira_drugs"] = df
                # Reload the IRA flags module with the new data
                reload_ira_drugs(df=df)
                st.success(f"Loaded {df.height:,} IRA drugs and updated risk flags")

                # Show breakdown by year
                year_counts = df.group_by("ira_year").len().sort("ira_year")
                st.caption(
                    "Drugs by year: "
                    + ", ".join(
                        f"{row['ira_year']}: {row['len']}"
                        for row in year_counts.iter_rows(named=True)
                    )
                )

                with st.expander("Preview Data"):
                    st.dataframe(df.head(10).to_pandas(), width="stretch")

            except Exception as e:
                st.error(f"Error loading file: {e}")
                logger.exception("Error loading IRA drug list")


def _show_validation_result(result: ValidationResult) -> None:
    """Display validation result details."""
    if result.warnings:
        for warning in result.warnings:
            st.warning(warning)

    if not result.is_valid:
        st.error(result.message)
        if result.missing_columns:
            st.error(f"Missing columns: {', '.join(result.missing_columns)}")


def _render_validation_summary() -> None:
    """Render summary of uploaded data and readiness status."""
    st.markdown("### Upload Status")

    uploaded = st.session_state.get("uploaded_data", {})

    # Required files
    required = {
        "catalog": "Product Catalog",
        "asp_pricing": "ASP Pricing",
        "crosswalk": "NDC-HCPCS Crosswalk",
    }

    # Optional files
    optional = {
        "noc_pricing": "NOC Pricing (fallback)",
        "noc_crosswalk": "NOC Crosswalk (fallback)",
        "nadac": "NADAC Statistics",
        "biologics": "Biologics Logic Grid",
        "ravenswood_categories": "AWP Reimbursement Matrix",
        "wholesaler_catalog": "Wholesaler Catalog (validation)",
        "ira_drugs": "IRA Drug List",
    }

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Required Files**")
        all_required = True
        for key, name in required.items():
            if key in uploaded:
                st.markdown(f"- :white_check_mark: {name}")
            else:
                st.markdown(f"- :x: {name}")
                all_required = False

    with col2:
        st.markdown("**Optional Files**")
        for key, name in optional.items():
            if key in uploaded:
                st.markdown(f"- :white_check_mark: {name}")
            else:
                st.markdown(f"- :heavy_minus_sign: {name}")

    # Ready status
    st.markdown("---")

    if all_required:
        st.success(
            "All required files uploaded! "
            "Select **Dashboard** from the sidebar to view optimization opportunities."
        )

        if st.button("Process Data", type="primary", key="process_data_bottom"):
            with st.spinner("Processing data..."):
                _process_uploaded_data()
            st.success("Data processed! Use sidebar to navigate to Dashboard.")
    else:
        st.info("Upload all required files to proceed to analysis.")


def _process_uploaded_data() -> None:
    """Process and normalize uploaded data."""
    from optimizer_340b.ingest.normalizers import (
        join_catalog_to_crosswalk,
        normalize_catalog,
        normalize_crosswalk,
    )

    uploaded = st.session_state.uploaded_data

    # Normalize catalog
    if "catalog" in uploaded:
        catalog_normalized = normalize_catalog(uploaded["catalog"])
        st.session_state.uploaded_data["catalog_normalized"] = catalog_normalized

    # Normalize crosswalk
    if "crosswalk" in uploaded:
        crosswalk_normalized = normalize_crosswalk(uploaded["crosswalk"])
        st.session_state.uploaded_data["crosswalk_normalized"] = crosswalk_normalized

    # Join catalog to crosswalk
    catalog_ready = "catalog_normalized" in st.session_state.uploaded_data
    crosswalk_ready = "crosswalk_normalized" in st.session_state.uploaded_data
    if catalog_ready and crosswalk_ready:
        # join_catalog_to_crosswalk returns (joined_df, orphan_df)
        joined_df, orphan_df = join_catalog_to_crosswalk(
            st.session_state.uploaded_data["catalog_normalized"],
            st.session_state.uploaded_data["crosswalk_normalized"],
        )
        st.session_state.uploaded_data["joined_data"] = joined_df
        st.session_state.uploaded_data["orphan_data"] = orphan_df

    st.session_state.data_processed = True
