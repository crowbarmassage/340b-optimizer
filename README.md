# 340B Site-of-Care Optimization Engine

A Streamlit web application that determines the optimal treatment pathway (Retail Pharmacy vs. Medical Billing) for 340B-eligible drugs by calculating **Net Realizable Revenue**.

## Problem Statement

Current 340B operational models calculate "Buying Power" (WAC vs. 340B Cost) rather than "Net Realizable Revenue." This leads to critical blind spots:

- **Channel Blind Spot**: Comparing pharmacy reimbursement to medical billing requires nuance
- **Capture Rate Gap**: PBM networks restrict billing eligibility, reducing capture rates to ~40-50%
- **Clinical Disconnect**: Models that ignore loading doses underestimate Year 1 revenue by >30%
- **Regulatory Cliff**: IRA price negotiations will compress margins on key drugs in 2026

## Solution

This engine provides:

1. **Dual-Channel Margin Comparison** — Retail (AWP-based) vs. Medical (ASP-based) side-by-side
2. **Payer-Adjusted Revenue** — Medicare Part B (ASP+6%) and Commercial Medical (ASP+15%)
3. **Variable Stress Testing** — Capture rate slider for realistic pharmacy constraints
4. **Loading Dose Modeling** — Year 1 vs. Maintenance revenue projections
5. **Risk Flagging** — IRA 2026/2027 warnings and Penny Pricing alerts

## Features (v1)

- [x] File upload for proprietary data sources (XLSX, CSV)
- [x] **Quick Start with sample data** - Load demo data instantly
- [x] Schema validation with clear error messages
- [x] NDC-to-HCPCS crosswalk integration
- [x] Margin calculations for 34k+ drugs
- [x] Interactive capture rate slider
- [x] IRA price negotiation warnings
- [x] Penny pricing alerts
- [x] Full provenance chain for auditability
- [x] Drug detail view with sensitivity analysis

## Installation

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager (recommended)

### Setup

```bash
# Clone the repository
git clone https://github.com/crowbarmassage/340b-optimizer.git
cd 340b-optimizer

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Copy environment template
cp .env.example .env
```

## Usage

### Running the Application

```bash
streamlit run src/optimizer_340b/ui/app.py
```

The application will open in your browser at `http://localhost:8501`.

### Quick Start (Recommended)

1. Click **"Load & Process Sample Data"** on the Upload page
2. Navigate to **Dashboard** using the sidebar
3. Explore optimization opportunities for 34,229 drugs

### Data Files (For Custom Data)

Upload the following files through the web interface:

| File Type | Purpose | Required Columns |
|-----------|---------|------------------|
| Product Catalog (XLSX) | 340B contract pricing | NDC, Contract Cost, AWP (or Medispan AWP) |
| ASP Pricing File (CSV) | Medicare payment limits | HCPCS Code, Payment Limit |
| NDC-HCPCS Crosswalk (CSV) | Billing code mapping | NDC (or NDC2), HCPCS Code (or _2025_CODE) |
| NOC Pricing File (CSV) | Fallback pricing for drugs without J-codes | Drug Generic Name, Payment Limit |
| NOC Crosswalk (CSV) | Fallback NDC mapping for NOC drugs | NDC, Drug Generic Name |
| NADAC Statistics (CSV) | Penny pricing detection | ndc, total_discount_340b_pct |
| Biologics Logic Grid (XLSX) | Loading dose profiles | Drug Name, Year 1 Fills, Year 2+ Fills |

**Note**: CMS files (ASP Pricing, Crosswalk) have 8 header rows that are automatically skipped.

### Workflow

1. **Upload** your data files (or click "Load & Process Sample Data" for demo)
2. **Navigate** to Dashboard to see ranked opportunities
3. **Filter** by IRA status, penny pricing, minimum margin delta
4. **Search** for specific drugs (< 30 seconds lookup)
5. **Adjust** capture rate slider to stress-test assumptions
6. **View Details** for individual drug analysis with provenance chain

## Development

### Running Tests

```bash
# Run all tests (277 tests)
uv run pytest tests/ -v

# Run with coverage report
uv run pytest tests/ --cov=src --cov-report=term-missing

# Run only integration tests (24 tests)
uv run pytest tests/test_integration.py -v

# Run unit tests only (253 tests)
uv run pytest -m "not integration" -v

# Run specific test module
uv run pytest tests/test_margins.py -v
```

### Code Quality

```bash
# Linting
ruff check .

# Formatting
ruff format .

# Type checking
mypy src/

# All pre-commit hooks
pre-commit run --all-files
```

### Project Structure

```
340b-optimizer/
├── src/optimizer_340b/
│   ├── __init__.py
│   ├── config.py              # Environment configuration
│   ├── models.py              # Drug, MarginAnalysis data models
│   ├── ingest/                # Data loading and validation
│   │   ├── loaders.py         # CSV/Excel file loaders
│   │   ├── validators.py      # Schema validation
│   │   └── normalizers.py     # Column mapping, NDC normalization
│   ├── compute/               # Margin calculations
│   │   ├── margins.py         # Retail/Medicare/Commercial margins
│   │   └── dosing.py          # Loading dose calculations
│   ├── risk/                  # Risk flagging
│   │   ├── ira_flags.py       # IRA 2026/2027 detection
│   │   └── penny_pricing.py   # Penny pricing alerts
│   └── ui/                    # Streamlit application
│       ├── app.py             # Main entry point
│       ├── pages/
│       │   ├── upload.py      # File upload interface
│       │   ├── dashboard.py   # Optimization dashboard
│       │   └── drug_detail.py # Single drug deep-dive
│       └── components/
│           ├── margin_card.py     # Margin comparison card
│           ├── capture_slider.py  # Capture rate slider
│           └── risk_badge.py      # IRA/Penny badges
├── tests/                     # Test suite (277 tests)
│   ├── test_integration.py    # End-to-end pipeline tests
│   ├── test_margins.py        # Margin calculation tests
│   ├── test_loaders.py        # Data loading tests
│   └── ...
├── data/sample/               # Sample data files
│   ├── product_catalog.xlsx   # 34,229 drugs
│   ├── asp_pricing.csv        # CMS ASP pricing
│   ├── asp_crosswalk.csv      # NDC-HCPCS mapping
│   ├── noc_pricing.csv        # NOC fallback pricing
│   ├── noc_crosswalk.csv      # NOC NDC mapping
│   ├── ndc_nadac_master_statistics.csv
│   └── biologics_logic_grid.xlsx
└── .streamlit/config.toml     # Streamlit configuration
```

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   File Upload   │────▶│  Bronze Layer   │────▶│  Silver Layer   │
│   (XLSX, CSV)   │     │   (Validate)    │     │  (Normalize)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Streamlit UI  │◀────│   Watchtower    │◀────│   Gold Layer    │
│   (Dashboard)   │     │  (Risk Flags)   │     │   (Margins)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Key Formulas

| Calculation | Formula |
|-------------|---------|
| Retail Gross Margin | AWP × 0.85 - Contract Cost |
| Retail Net Margin | Gross Margin × Capture Rate |
| Medicare Margin | ASP × 1.06 × Billing Units - Contract Cost |
| Commercial Margin | ASP × 1.15 × Billing Units - Contract Cost |

## Success Metrics (Validated)

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Optimization Velocity | < 30 seconds | < 5 seconds (100 drugs) | ✅ |
| Financial Accuracy | +/- 5% | Within tolerance | ✅ |
| Auditability | 100% | Full provenance chain | ✅ |
| Test Coverage | 80%+ | 95%+ (core modules) | ✅ |

## Verified Test Results

```
277 tests passing
├── Unit Tests: 253
└── Integration Tests: 24

Core Module Coverage:
├── compute/margins.py:     95%
├── compute/dosing.py:      90%
├── ingest/loaders.py:      95%
├── ingest/normalizers.py:  91%
├── ingest/validators.py:   99%
├── risk/ira_flags.py:     100%
├── risk/penny_pricing.py:  93%
└── models.py:             100%
```

## Known Issues & Debugging Notes

### CMS File Handling
- CMS ASP Pricing and Crosswalk files have 8 header rows that must be skipped
- Column names vary by quarter (e.g., `_2025_CODE` vs `HCPCS Code`)
- The normalizer automatically maps these variations

### Data Validation
- Catalog requires: NDC, Contract Cost, AWP (or "Medispan AWP")
- ASP files may contain "N/A" values - these are safely skipped
- Crosswalk join rate is ~14% (expected for infusible drugs only)

### NOC (Not Otherwise Classified) Fallback
- NOC files provide pricing for drugs without permanent J-codes
- When a drug has no ASP crosswalk match, the system checks NOC crosswalk
- NOC pricing uses the same ASP+6%/ASP+15% formulas for margin calculation
- NOC files are optional - system works without them but won't price unmapped drugs

### Streamlit Specifics
- Navigation uses sidebar radio buttons (not page-based routing)
- Session state persists uploaded data across page navigation
- Sample data auto-loads from `data/sample/` directory

## License

Private - All rights reserved.

## Contributing

This is a private project. Contact the repository owner for contribution guidelines.

## Support

For issues and feature requests, contact the development team.
