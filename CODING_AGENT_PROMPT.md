# CODING_AGENT_PROMPT.md — Implementation Instructions

> **Project:** 340B Site-of-Care Optimization Engine
> **Version:** 1.0
> **Last Updated:** January 15, 2026

---

## Context

The **340B Optimizer** is a Streamlit web application that determines the optimal treatment pathway (Retail Pharmacy vs. Medical Billing) for 340B-eligible drugs. It calculates Net Realizable Revenue across three channels:

1. **Retail Pharmacy** — AWP-based reimbursement with capture rate variability
2. **Medicare Medical** — ASP + 6% billing
3. **Commercial Medical** — ASP + 15% billing (conservative estimate)

Target users are **Financial Analysts** and **Strategic Consultants** performing due diligence and valuation analysis.

---

## Current State

The repository contains complete design documentation:
- `TECH_SPECS.md` — Technical architecture and starter code
- `ATOMIC_STEPS.md` — 9-phase implementation plan with tests
- `FUTURE_FEATURES.md` — Deferred features for v2+
- `pyproject.toml` — Dependencies and tooling config
- `.pre-commit-config.yaml` — Code quality hooks

No implementation code exists yet. You will build from Phase 1.

---

## Objective

Implement the 340B Optimizer following the phased plan in `ATOMIC_STEPS.md`.

**Success Metrics** (from Project Charter):
1. **Optimization Velocity** — Drug lookup in <30 seconds
2. **Financial Accuracy** — Projections within +/- 5% of historical data
3. **Auditability** — Full provenance chain for every margin calculation
4. **Extensibility** — New ASP file ingestion without code changes

---

## Code Standards

Before writing any code, read and follow:
`/Users/mohsin.ansari/Github/PYTHON_STANDARDS.md`

**Key requirements:**
- Use `uv` for package management
- Run `ruff check` and `ruff format` before commits
- Run `mypy` for type checking
- All functions must have type hints and Google-style docstrings
- Pytest for all tests with >80% coverage target
- Pre-commit hooks must pass

---

## Implementation Constraints

### Data Handling
- Use **Polars** for DataFrame operations (performance on 34k+ rows)
- Use **pandas + openpyxl** for Excel file I/O only (then convert to Polars)
- NDC normalization: Always 11-digit, zero-padded (preserves leading zeros)
- Fuzzy matching threshold: 80% for drug name alignment

### Margin Calculations
- Medicare: `ASP * 1.06 * bill_units - contract_cost`
- Commercial: `ASP * 1.15 * bill_units - contract_cost`
- Retail: `AWP * 0.85 * capture_rate - contract_cost`
- Default capture rate: 45%

### Risk Flags
- IRA 2026 drugs: Enbrel, Stelara, Imbruvica, Januvia, Farxiga, Entresto, Xarelto, Eliquis, Jardiance, Fiasp/NovoLog Mix
- Penny pricing: Flag when NADAC `total_discount_340b_pct` > 99%

### UI Requirements
- Streamlit multi-page app structure
- File upload with validation feedback
- Capture rate slider (0-100%)
- Risk badges (IRA, Penny Pricing)
- Export to CSV

---

## Step Reference

Follow the phases in `ATOMIC_STEPS.md`:

| Phase | Description | Key Deliverables |
|-------|-------------|------------------|
| 1 | Foundation | Config, models, fixtures |
| 2 | Bronze Layer | File loaders, validators |
| 3 | Silver Layer | NDC normalization, crosswalk joins |
| 4 | Gold Layer | Margin calculations, dosing logic |
| 5 | Watchtower | IRA flags, penny pricing alerts |
| 6 | Streamlit UI | Upload, dashboard, drug detail |
| 7 | Integration | End-to-end tests, success metrics |
| 8 | Notebook | Google Colab demo |
| 9 | Polish | Documentation, coverage |

---

## Checkpoint Instructions

After completing each phase:

1. **Run phase tests**: `pytest tests/test_<phase>.py -v`
2. **Run quality checks**: `ruff check . && ruff format . && mypy src/`
3. **Update CHECKPOINT.md** with current state
4. **Commit** with conventional message: `feat: complete phase N - <description>`
5. **Push** to remote
6. **Ask for human review** before proceeding to next phase

---

## Data Files Location

Source data files for testing are in:
`/Users/mohsin.ansari/Github/inbox/340B_Engine/`

| File | Purpose | Key Columns |
|------|---------|-------------|
| `product_catalog.xlsx` | 340B catalog (34k NDCs) | NDC, Contract Cost, AWP |
| `wholesaler_catalog.xlsx` | Market catalog (47k rows) | NDC, AWP |
| `biologics_logic_grid.xlsx` | Dosing profiles | Drug Name, Year 1 Fills |
| `Oct 2025 ASP Pricing File*.csv` | Medicare pricing | HCPCS Code, Payment Limit |
| `October 2025 ASP NDC-HCPCS Crosswalk*.csv` | NDC→HCPCS mapping | NDC, HCPCS Code |
| `ndc_nadac_master_statistics.csv` | Penny pricing data | ndc, total_discount_340b_pct |

**Important**: CSV files use `latin-1` encoding, not UTF-8.

---

## Testing Approach

### Unit Tests
- Test each calculation function in isolation
- Use fixtures from `conftest.py` for consistent test data
- Parametrize edge cases (empty inputs, zero values, missing fields)

### Gatekeeper Tests (from Project Charter)
- **Medicare Unit Test**: Manual calculation matches engine to the penny
- **Commercial Unit Test**: 1.15x multiplier correctly applied
- **Loading Dose Test**: Cosentyx Year 1 = 17 fills
- **Capture Rate Test**: 40% toggle reduces retail proportionally
- **Enbrel Simulation**: IRA 2026 flag present
- **Penny Pricing Alert**: Flagged drugs excluded from Top Opportunities

### Integration Tests
- Full pipeline from file upload to margin output
- Validate success metrics (velocity, accuracy, auditability)

---

## Common Pitfalls to Avoid

1. **NDC Format Mismatches** — Always normalize to 11 digits before joining
2. **Float Precision** — Use `Decimal` for all financial calculations
3. **Empty Crosswalk Columns** — ASP crosswalk file has 250 columns, only 9-10 populated
4. **CSV Encoding** — CMS files are latin-1, not UTF-8
5. **Orphan Drugs** — Some drugs show $0.00 retail (special billing)
6. **Loading Dose Assumptions** — Year 1 fills include loading; don't double-count

---

## Questions?

If unclear on requirements, check these resources in order:
1. `TECH_SPECS.md` — Technical details
2. `ATOMIC_STEPS.md` — Implementation steps
3. `/Users/mohsin.ansari/Github/inbox/340B_Engine/Project_Charter_340B_Engine.md` — Business requirements
4. Ask the human for clarification

---

## Start Here

```bash
cd /Users/mohsin.ansari/Github/repos/340b-optimizer
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
pre-commit install
```

Then begin with **Phase 1: Project Foundation** in `ATOMIC_STEPS.md`.
