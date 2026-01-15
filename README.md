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
- [x] Schema validation with clear error messages
- [x] NDC-to-HCPCS crosswalk integration
- [x] Margin calculations for 34k+ drugs
- [x] Interactive capture rate slider
- [x] IRA price negotiation warnings
- [x] Penny pricing alerts
- [x] Export to CSV
- [x] Full provenance chain for auditability

## Installation

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager

### Setup

```bash
# Clone the repository
git clone https://github.com/crowbarmassage/340b-optimizer.git
cd 340b-optimizer

# Create virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
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

### Data Files Required

Upload the following files through the web interface:

| File Type | Purpose | Required Columns |
|-----------|---------|------------------|
| Product Catalog (XLSX) | 340B contract pricing | NDC, Contract Cost, AWP |
| ASP Pricing File (CSV) | Medicare payment limits | HCPCS Code, Payment Limit |
| NDC-HCPCS Crosswalk (CSV) | Billing code mapping | NDC, HCPCS Code |
| Biologics Logic Grid (XLSX) | Dosing profiles | Drug Name, Year 1 Fills |
| NADAC Statistics (CSV) | Penny pricing detection | ndc, total_discount_340b_pct |

### Quick Start Workflow

1. **Upload** your data files on the Upload page
2. **Review** validation results (schema checks, row counts)
3. **Navigate** to the Dashboard to see ranked opportunities
4. **Search** for specific drugs (< 30 seconds lookup)
5. **Adjust** the capture rate slider to stress-test assumptions
6. **Export** results to CSV for further analysis

## Development

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src --cov-report=term-missing

# Run specific phase tests
pytest tests/test_margins.py -v
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
│   ├── config.py           # Environment configuration
│   ├── models.py           # Data models
│   ├── ingest/             # Data loading and validation
│   ├── compute/            # Margin calculations
│   ├── risk/               # IRA and penny pricing flags
│   └── ui/                 # Streamlit application
├── tests/                  # Test suite
├── notebooks/              # Demo notebooks
└── data/sample/            # Sample test data
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

## Success Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| Optimization Velocity | < 30 seconds | Time to identify optimal pathway for a drug |
| Financial Accuracy | +/- 5% | Projection vs. historical reimbursement |
| Auditability | 100% | Every margin has full provenance chain |
| Extensibility | No code change | New ASP file ingestion via upload |

## License

Private - All rights reserved.

## Contributing

This is a private project. Contact the repository owner for contribution guidelines.

## Support

For issues and feature requests, contact the development team.
