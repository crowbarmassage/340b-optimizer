# DATA_REFERENCE.md — 340B Optimizer Data File Reference

> **Version:** 1.0
> **Last Updated:** January 24, 2026

This document provides a detailed reference for each data file used by the 340B Optimizer, including descriptions, column definitions, and usage notes.

---

## Table of Contents

1. [Product Catalog](#1-product-catalog)
2. [ASP Pricing](#2-asp-pricing)
3. [ASP Crosswalk](#3-asp-crosswalk)
4. [NOC Pricing](#4-noc-pricing)
5. [NOC Crosswalk](#5-noc-crosswalk)
6. [NADAC Statistics](#6-nadac-statistics)
7. [Biologics Logic Grid](#7-biologics-logic-grid)
8. [AWP Reimbursement Matrix](#8-awp-reimbursement-matrix)
9. [Wholesaler Catalog](#9-wholesaler-catalog)
10. [IRA Drug List](#10-ira-drug-list)
11. [CMS Crosswalk Reference](#11-cms-crosswalk-reference)

---

## 1. Product Catalog

**File:** `product_catalog.xlsx`
**Format:** Excel (.xlsx)
**Rows:** 34,229
**Source:** Wholesaler/GPO contract pricing

### Description
The primary drug catalog containing 340B contract pricing, AWP, and product details for all drugs available through the wholesaler. This is the "Golden Record" source for drug identification and acquisition costs.

### Columns

| # | Column Name | Description |
|---|-------------|-------------|
| 1 | **NDC** | 11-digit National Drug Code (primary identifier) |
| 2 | **Product Description** | Full product description including strength and form |
| 3 | **Trade Name** | Brand/trade name of the drug |
| 4 | **Generic Name** | Generic/chemical name |
| 5 | **Form** | Dosage form (TAB, CAP, VIAL, INJ, etc.) |
| 6 | **Package Size** | Size of individual unit (e.g., 0.5 mL) |
| 7 | **Package Qty** | Number of units per package |
| 8 | **Manufacturer** | Drug manufacturer/labeler name |
| 9 | **Active Status** | Whether the NDC is currently active |
| 10 | **Unit Dose** | Unit dose indicator |
| 11 | **Contract Name** | Name of the 340B contract |
| 12 | **Medispan AWP** | Average Wholesale Price from Medispan |
| 13 | **Contract Cost** | 340B acquisition cost (what the entity pays) |
| 14 | **Unit Price (Previous Catalog)** | Unit price from previous catalog |
| 15 | **Unit Price (Current Catalog)** | Current catalog unit price |
| 16 | **Unit Price (Current Retail)** | Current retail unit price |
| 17 | **Gross Margin %** | Pre-calculated gross margin percentage |

### Key Usage
- **NDC**: Primary join key to crosswalk files
- **Contract Cost**: Used in margin calculations (acquisition cost)
- **Medispan AWP**: Used for retail reimbursement calculations

---

## 2. ASP Pricing

**File:** `asp_pricing.csv`
**Format:** CSV (8 header rows to skip)
**Rows:** 1,012
**Source:** CMS ASP Drug Pricing Files (quarterly)

### Description
Medicare Part B Average Sales Price (ASP) payment allowance limits by HCPCS code. Updated quarterly by CMS. Used to determine Medicare reimbursement for infusible/injectable drugs.

### Columns

| # | Column Name | Description |
|---|-------------|-------------|
| 1 | **HCPCS Code** | Healthcare Common Procedure Coding System code (Jxxxx format) |
| 2 | **Short Description** | Brief description of the HCPCS code |
| 3 | **HCPCS Code Dosage** | Dosage descriptor for the HCPCS code (e.g., "5 mcg") |
| 4 | **Payment Limit** | ASP-based payment limit per billing unit |
| 5 | **Co-insurance Percentage** | Medicare co-insurance percentage |
| 6 | **Vaccine AWP%** | AWP percentage for vaccines (paid at 95% AWP) |
| 7 | **Vaccine Limit** | Payment limit for vaccines |
| 8 | **Blood AWP%** | AWP percentage for blood products |
| 9 | **Blood limit** | Payment limit for blood products |
| 10 | **Clotting Factor** | Clotting factor indicator |
| 11 | **Notes** | Additional notes about the code |

### Key Usage
- **HCPCS Code**: Join key to ASP Crosswalk
- **Payment Limit**: ASP value used in Medicare margin calculation (ASP × 1.06)

### Notes
- File has 8 header rows of metadata that must be skipped when loading
- Payment limits are per billing unit, not per package
- Some values may be "N/A" (not applicable)

---

## 3. ASP Crosswalk

**File:** `asp_crosswalk.csv`
**Format:** CSV (8 header rows to skip)
**Rows:** 8,245
**Source:** CMS ASP NDC-HCPCS Crosswalk (quarterly)

### Description
Maps 11-digit NDCs to HCPCS billing codes. Essential for determining which drugs can be billed through Medicare Part B medical benefit and how many billing units are in each package.

### Columns

| # | Column Name | Description |
|---|-------------|-------------|
| 1 | **_2025_CODE** | HCPCS code (column name varies by quarter, e.g., "2025_CODE") |
| 2 | **Short Description** | Brief description of the HCPCS code |
| 3 | **LABELER NAME** | Manufacturer/labeler name |
| 4 | **NDC2** | 11-digit NDC (may include dashes: xxxxx-xxxx-xx) |
| 5 | **Drug Name** | Product name (brand or generic) |
| 6 | **HCPCS dosage** | Dosage descriptor for the HCPCS code |
| 7 | **PKG SIZE** | Package size (amount in one item) |
| 8 | **PKG QTY** | Package quantity (number of items in NDC) |
| 9 | **BILLUNITS** | Billable units per package |
| 10 | **BILLUNITSPKG** | Billable units per NDC (BILLUNITS × PKG QTY) |

### Key Usage
- **NDC2**: Join key to Product Catalog (after normalization)
- **_2025_CODE**: Join key to ASP Pricing file
- **BILLUNITSPKG**: Multiplier for Medicare margin calculation

### Notes
- File has 8 header rows of metadata that must be skipped
- The HCPCS code column name changes quarterly (e.g., "2024_CODE", "2025_CODE")
- NDCs may include dashes and need normalization

---

## 4. NOC Pricing

**File:** `noc_pricing.csv`
**Format:** CSV (12 header rows to skip)
**Rows:** ~2 (varies)
**Source:** CMS NOC Drug Pricing Files (quarterly)

### Description
Payment limits for "Not Otherwise Classified" (NOC) drugs that don't have specific HCPCS codes. Fallback pricing for drugs billed with unlisted/unclassified codes.

### Columns

| # | Column Name | Description |
|---|-------------|-------------|
| 1 | **Drug Generic Name (Trade Name)** | Drug name with trade name in parentheses |
| 2 | **Dosage** | Dosage unit descriptor |
| 3 | **Payment Limit** | ASP-based payment limit |
| 4 | **Notes** | Additional notes |

### Key Usage
- Used as fallback pricing when drug has no specific HCPCS code
- Currently only contains Vasopressin (Long Grove)

---

## 5. NOC Crosswalk

**File:** `noc_crosswalk.csv`
**Format:** CSV (9 header rows to skip)
**Rows:** ~2 (varies)
**Source:** CMS NOC NDC-HCPCS Crosswalk (quarterly)

### Description
Maps NDCs to NOC billing codes for drugs without specific HCPCS assignments.

### Columns

| # | Column Name | Description |
|---|-------------|-------------|
| 1 | **Drug Generic Name** | Generic name of the drug |
| 2 | **LABELER NAME** | Manufacturer/labeler name |
| 3 | **NDC or ALTERNATE ID** | 11-digit NDC or alternate identifier |
| 4 | **Drug Name** | Product name |
| 5 | **Dosage** | Dosage descriptor |
| 6 | **PKG SIZE** | Package size |
| 7 | **PKG QTY** | Package quantity |
| 8 | **BILLUNITS** | Billable units per package |
| 9 | **BILLUNITSPKG** | Billable units per NDC |

### Key Usage
- **NDC or ALTERNATE ID**: Join key for NOC drug identification
- **BILLUNITSPKG**: Billing units multiplier for NOC drugs

---

## 6. NADAC Statistics

**File:** `ndc_nadac_master_statistics.csv`
**Format:** CSV (no header rows to skip)
**Rows:** ~33,000
**Source:** CMS NADAC (National Average Drug Acquisition Cost) historical analysis

### Description
Historical NADAC pricing statistics used for penny pricing detection. Contains 11 years of pricing data (2014-2025) to identify drugs at the 340B floor price.

### Columns

| # | Column Name | Description |
|---|-------------|-------------|
| 1 | **ndc** | 11-digit National Drug Code |
| 2 | **ndc_description** | Drug description |
| 3 | **classification** | Drug classification code |
| 4 | **classification_name** | Classification name (Generic, Brand, etc.) |
| 5 | **otc** | Over-the-counter indicator (Y/N) |
| 6 | **pricing_unit** | Unit of measure for pricing |
| 7 | **first_year_appeared** | First year drug appeared in NADAC |
| 8 | **years_of_data** | Number of years with data |
| 9 | **missing_years** | Years with no data |
| 10 | **has_gaps** | Whether data has gaps |
| 11 | **total_records** | Total number of records |
| 12 | **date_range_start** | First date in dataset |
| 13 | **date_range_end** | Last date in dataset |
| 14 | **first_price** | First recorded price |
| 15 | **last_price** | Most recent price |
| 16 | **min_price** | Minimum price observed |
| 17 | **min_price_date** | Date of minimum price |
| 18 | **max_price** | Maximum price observed |
| 19 | **max_price_date** | Date of maximum price |
| 20 | **mean_price** | Average price |
| 21 | **median_price** | Median price |
| 22 | **std_dev** | Standard deviation of prices |
| 23 | **price_change_absolute** | Absolute price change |
| 24 | **price_change_pct** | Percentage price change |
| 25 | **price_direction** | Direction of price movement |
| 26 | **cpi_start** | CPI at start date |
| 27 | **cpi_end** | CPI at end date |
| 28 | **cpi_change_pct** | CPI change percentage |
| 29 | **inflation_penalty_pct** | 340B inflation penalty percentage |
| 30 | **baseline_discount_pct** | Baseline 340B discount percentage |
| 31 | **total_discount_340b_pct** | Total 340B discount (baseline + penalty) |
| 32 | **penny_pricing** | Boolean flag for penny pricing detection |
| 33-44 | **yearly_avg_2014-2025** | Average price for each year (2014-2025) |

### Key Usage
- **ndc**: Join key to Product Catalog
- **penny_pricing**: Flag for drugs at 340B floor ($0.01)
- **last_price**: Current NADAC price for margin comparison
- **total_discount_340b_pct**: Expected 340B discount percentage

---

## 7. Biologics Logic Grid

**File:** `biologics_logic_grid.xlsx`
**Format:** Excel (.xlsx)
**Rows:** 64
**Source:** Internal clinical/operational data

### Description
Loading dose and maintenance dosing profiles for specialty biologics. Used to calculate Year 1 vs. Year 2+ revenue projections accounting for loading dose regimens.

### Columns

| # | Column Name | Description |
|---|-------------|-------------|
| 1 | **Drug Name** | Brand name of the biologic |
| 2 | **Generic Name** | Generic/chemical name |
| 3 | **Manufacturer** | Drug manufacturer |
| 4 | **Therapeutic Class** | Therapeutic category (e.g., TNF Inhibitor) |
| 5 | **Indication** | Primary indication (e.g., Psoriasis, RA) |
| 6 | **ICD-10 Primary** | Primary ICD-10 diagnosis code |
| 7 | **ICD-10 Range** | Range of applicable ICD-10 codes |
| 8 | **Specialty** | Medical specialty (e.g., Rheumatology) |
| 9 | **Route** | Route of administration (SC, IV, etc.) |
| 10 | **Loading Dose** | Loading dose description |
| 11 | **Loading Fills** | Number of fills during loading period |
| 12 | **Maintenance Dose** | Maintenance dose description |
| 13 | **Maint Fills/Yr** | Annual maintenance fills |
| 14 | **Year 1 Fills** | Total fills in Year 1 (loading + maintenance) |
| 15 | **Year 2+ Fills** | Annual fills after Year 1 |
| 16 | **Adj Y1 Fills** | Compliance-adjusted Year 1 fills |
| 17 | **Adj Y2+ Fills** | Compliance-adjusted Year 2+ fills |
| 18 | **Notes** | Additional clinical notes |

### Key Usage
- **Drug Name**: Fuzzy match key to Product Catalog
- **Year 1 Fills / Year 2+ Fills**: Revenue projection multipliers
- **Adj Y1 Fills / Adj Y2+ Fills**: Compliance-adjusted projections

---

## 8. AWP Reimbursement Matrix

**File:** `Ravenswood_AWP_Reimbursement_Matrix.xlsx`
**Format:** Excel (.xlsx) - Complex layout
**Rows:** ~32 (structured data starts at row 16)
**Source:** Payer contract analysis

### Description
Payer-specific AWP reimbursement multipliers by drug category (Generic, Brand, Specialty). Used to calculate realistic retail reimbursement based on payer mix.

### Structure

**Section 1: Payer Mix Summary (rows 5-11)**

| Payer Category | Est. Claims | % Mix | Reimbursement Basis |
|----------------|-------------|-------|---------------------|
| Medicare Part D (Standalone PDP) | 380 | 23% | AWP - 15% (brand/specialty), AWP - 80% (generic) |
| Medicare Part D (MA-PD) | 290 | 17% | AWP - 15% (brand/specialty), AWP - 80% (generic) |
| Commercial | 850 | 51% | AWP - 16% (brand), AWP - 14% (specialty), MAC (generic) |
| IL Medicaid MCO | 45 | 3% | AWP - 22% (brand), AWP - 20% (specialty), NADAC-based (generic) |
| Self Pay | 85 | 5% | AWP / U&C |
| Unknown/Null | 25 | 1% | TBD - verify payer |

**Section 2: AWP Multiplier Matrix (rows 16-19)**

| Payer Category | Generic | Brand | Specialty |
|----------------|---------|-------|-----------|
| Medicare Part D (All) | AWP × 0.20 | AWP × 0.85 | AWP × 0.85 |
| Commercial | AWP × 0.15 (or MAC) | AWP × 0.84 | AWP × 0.86 |
| IL Medicaid MCO | AWP × 0.15 (NADAC) | AWP × 0.78 | AWP × 0.80 |
| Self Pay | AWP × 1.00 | AWP × 1.00 | AWP × 1.00 |

### Key Usage
- Multipliers applied to Medispan AWP for retail margin calculation
- Drug category (Generic/Brand/Specialty) determines which multiplier to use
- Payer mix percentages can weight the expected reimbursement

---

## 9. Wholesaler Catalog

**File:** `wholesaler_catalog.xlsx`
**Format:** Excel (.xlsx)
**Rows:** 47,541
**Source:** Wholesaler product master

### Description
Complete wholesaler product catalog with retail pricing. Used for retail price validation and additional product details not in the 340B contract catalog.

### Columns

| # | Column Name | Description |
|---|-------------|-------------|
| 1 | **Product Catalog NDC** | 11-digit National Drug Code |
| 2 | **Product Catalog Generic Name** | Generic/chemical name |
| 3 | **Product Catalog Product Description** | Full product description |
| 4 | **Product Catalog Form** | Dosage form |
| 5 | **Product Catalog Trade Name** | Brand/trade name |
| 6 | **Product Catalog Package Size** | Package size |
| 7 | **Product Catalog Manufacturer** | Manufacturer name |
| 8 | **Product Catalog Medispan AWP** | Average Wholesale Price |
| 9 | **Product Catalog Rx/Non-Rx** | Prescription vs OTC indicator |
| 10 | **Product Catalog Size** | Size description |
| 11 | **Product Catalog Strength** | Drug strength |
| 12 | **Product Catalog UOI Measure** | Unit of issue measure |
| 13 | **Product Catalog Unit Price (Current Retail) Average** | Current average retail unit price |

### Key Usage
- **Product Catalog NDC**: Join key for retail price validation
- **Product Catalog Unit Price (Current Retail) Average**: Retail price benchmark

---

## 10. IRA Drug List

**File:** `ira_drug_list.csv`
**Format:** CSV (no header rows to skip)
**Rows:** 31
**Source:** CMS IRA Medicare Drug Price Negotiation Program

### Description
Drugs subject to Medicare price negotiation under the Inflation Reduction Act (IRA). Split into 2026 and 2027 implementation years. Used to flag drugs at risk of future price changes.

### Columns

| # | Column Name | Description |
|---|-------------|-------------|
| 1 | **drug_name** | Drug name (brand name, uppercase) |
| 2 | **ira_year** | Implementation year (2026 or 2027) |
| 3 | **description** | Brief description including generic name |

### Current Drug List

**IRA 2026 Drugs (16):**
- ELIQUIS, JARDIANCE, XARELTO, JANUVIA, FARXIGA, ENTRESTO, ENBREL, IMBRUVICA, STELARA
- FIASP, FIASP FLEXTOUCH, FIASP PENFILL, NOVOLOG, NOVOLOG FLEXPEN, NOVOLOG MIX

**IRA 2027 Drugs (15):**
- OZEMPIC, RYBELSUS, WEGOVY, TRELEGY ELLIPTA, TRULICITY, POMALYST, AUSTEDO, IBRANCE
- OTEZLA, COSENTYX, TALZENNA, AUBAGIO, OMVOH, XTANDI, SIVEXTRO

### Key Usage
- **drug_name**: Fuzzy match key to Product Catalog
- **ira_year**: Determines which year the negotiated price takes effect

---

## 11. CMS Crosswalk Reference

**File:** `cms_crosswalk_reference.csv`
**Format:** CSV (text/documentation file)
**Rows:** N/A (documentation only)
**Source:** CMS ASP Crosswalk documentation

### Description
Reference documentation explaining the CMS ASP crosswalk file structure and field definitions. Not used programmatically but helpful for understanding the data model.

### Key Definitions

| Field | Description |
|-------|-------------|
| **HCPCS Code** | Jxxxx format billing code |
| **11-Digit NDC** | Format: xxxxx-xxxx-xx (dashes included) |
| **Package Size** | Amount in one item (e.g., 0.5 mL per vial) |
| **Package Quantity** | Number of items in NDC (e.g., 4 vials per shelf pack) |
| **Billable Units Per Package** | Package content ÷ HCPCS dosage (e.g., 100mcg ÷ 5mcg = 20) |
| **Billable Units Per NDC** | Billable units × Package quantity (e.g., 20 × 4 = 80) |

### Notes
- Medicare Part B drug payment = ASP × 106%
- Vaccines and blood products paid at 95% AWP (exception)

---

## Data Loading Notes

### CMS CSV Files (ASP Pricing, ASP Crosswalk, NOC files)

```python
# Skip 8 header rows for ASP files
df = pl.read_csv("asp_pricing.csv", skip_rows=8, encoding="latin-1")

# Skip 9 header rows for NOC crosswalk
df = pl.read_csv("noc_crosswalk.csv", skip_rows=9, encoding="latin-1")

# Skip 12 header rows for NOC pricing
df = pl.read_csv("noc_pricing.csv", skip_rows=12, encoding="latin-1")
```

### NDC Column Handling

All NDC columns must be read as strings to preserve leading zeros:

```python
NDC_COLUMN_NAMES = {
    "NDC", "NDC2", "ndc", "ndc2", "Ndc",
    "NDC or ALTERNATE ID",      # NOC crosswalk
    "Product Catalog NDC",       # Wholesaler catalog
}
```

### NDC Normalization

NDCs should be normalized to 11-digit format without dashes:

```python
def normalize_ndc(ndc: str) -> str:
    """Normalize NDC to 11-digit format."""
    cleaned = ndc.replace("-", "").replace(" ", "")
    return cleaned.zfill(11)[-11:]
```

---

## Join Relationships

```
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│ Product Catalog  │      │  ASP Crosswalk   │      │   ASP Pricing    │
│                  │      │                  │      │                  │
│  NDC ────────────┼──────┼─► NDC2           │      │                  │
│                  │      │  _2025_CODE ─────┼──────┼─► HCPCS Code     │
│                  │      │  BILLUNITSPKG    │      │  Payment Limit   │
└──────────────────┘      └──────────────────┘      └──────────────────┘
         │
         │ NDC
         ▼
┌──────────────────┐      ┌──────────────────┐
│ NADAC Statistics │      │ Wholesaler Cat.  │
│                  │      │                  │
│  ndc             │      │  Product Cat NDC │
│  penny_pricing   │      │  Retail Price    │
└──────────────────┘      └──────────────────┘
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-24 | Initial documentation |
