# Complete Drug Detail Schema

This document defines the most atomized, comprehensive drug detail record combining ALL available data sources.

## Design Goal

A single "Gold Record" for each drug that contains:
- Every raw data point from every source
- All derived/calculated fields
- Full audit trail of data provenance
- Temporal validity (when each piece of data is effective)

---

## Master Drug Detail Schema

### Section 1: Drug Identity

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `ndc_raw` | VARCHAR(20) | product_catalog | Original NDC as provided |
| `ndc_11` | CHAR(11) | Derived | Normalized 11-digit NDC |
| `ndc_formatted` | VARCHAR(13) | Derived | 5-4-2 format (00074-4339-02) |
| `ndc_10` | CHAR(10) | Derived | 10-digit format (for legacy systems) |
| `drug_name` | VARCHAR(255) | product_catalog | Trade/brand name |
| `generic_name` | VARCHAR(255) | product_catalog / crosswalk | Generic/chemical name |
| `product_description` | TEXT | product_catalog | Full product description |
| `manufacturer_name` | VARCHAR(255) | product_catalog | Manufacturer name |
| `manufacturer_labeler_code` | CHAR(5) | Derived from NDC | First 5 digits of NDC |

### Section 2: Drug Classification

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `drug_category` | ENUM | Ravenswood / Derived | 'BRAND', 'GENERIC', 'SPECIALTY' |
| `is_brand` | BOOLEAN | Derived | TRUE if BRAND or SPECIALTY |
| `is_generic` | BOOLEAN | Derived | TRUE if GENERIC |
| `is_specialty` | BOOLEAN | Derived | TRUE if SPECIALTY |
| `is_biologic` | BOOLEAN | biologics_grid | TRUE if biologic drug |
| `therapeutic_class` | VARCHAR(100) | product_catalog | e.g., "TNF Inhibitor" |
| `therapeutic_class_code` | VARCHAR(20) | product_catalog | Class code if available |

### Section 3: Dosage Form & Route (From Form Code + Description Parsing)

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `form_code` | VARCHAR(10) | product_catalog.Form | Raw form code (TABS, PWVL, SDPF, etc.) |
| `dosage_form` | VARCHAR(50) | Derived from form_code | Expanded form (TABLET, POWDER VIAL, etc.) |
| `dosage_form_category` | VARCHAR(30) | Derived | SOLID, LIQUID, INJECTABLE, TOPICAL, etc. |
| `route_of_administration` | VARCHAR(30) | Derived from form_code | ORAL, INJECTABLE, TOPICAL, etc. |
| `is_oral` | BOOLEAN | Derived | TRUE if oral administration |
| `is_injectable` | BOOLEAN | Derived | TRUE if injectable |
| `is_topical` | BOOLEAN | Derived | TRUE if topical |
| `is_ophthalmic` | BOOLEAN | Derived | TRUE if eye drops/ointment |
| `is_inhalation` | BOOLEAN | Derived | TRUE if inhaled |
| `is_transdermal` | BOOLEAN | Derived | TRUE if patch/transdermal |

### Section 4: Strength & Dosage (Parsed from Description)

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `strength_raw` | VARCHAR(100) | Parsed from description | Raw strength string (e.g., "10-325MG") |
| `strength_value_1` | DECIMAL(12,4) | Parsed | Primary strength value (e.g., 10) |
| `strength_unit_1` | VARCHAR(10) | Parsed | Primary strength unit (MG, MCG, G, etc.) |
| `strength_value_2` | DECIMAL(12,4) | Parsed | Secondary strength for combos (e.g., 325) |
| `strength_unit_2` | VARCHAR(10) | Parsed | Secondary unit (usually same as primary) |
| `is_combination_drug` | BOOLEAN | Derived | TRUE if multiple active ingredients |
| `strength_per_unit` | DECIMAL(12,6) | Calculated | Strength per single dosage unit |
| `strength_display` | VARCHAR(50) | Derived | Formatted display (e.g., "10/325 MG") |

### Section 5: Concentration (Parsed from Description - Liquids/Injectables)

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `concentration_raw` | VARCHAR(50) | Parsed | Raw concentration (e.g., "20MG/ML") |
| `concentration_numerator` | DECIMAL(12,4) | Parsed | Amount of drug (e.g., 20) |
| `concentration_numerator_unit` | VARCHAR(10) | Parsed | Drug amount unit (MG, MCG, U, IU, ELU) |
| `concentration_denominator` | DECIMAL(12,4) | Parsed | Volume (e.g., 1 or 0.5) |
| `concentration_denominator_unit` | VARCHAR(10) | Parsed | Volume unit (ML, L) |
| `concentration_per_ml` | DECIMAL(12,6) | Calculated | Normalized to per-ML basis |
| `has_concentration` | BOOLEAN | Derived | TRUE if liquid with concentration |

### Section 6: Volume & Package (From Catalog + Description Parsing)

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `package_size_raw` | DECIMAL(12,4) | product_catalog.Package Size | Raw package size value |
| `package_qty_raw` | INT | product_catalog.Package Qty | Raw package quantity |
| `total_volume_value` | DECIMAL(12,4) | Parsed/Calculated | Total liquid volume |
| `total_volume_unit` | VARCHAR(10) | Parsed | Volume unit (ML, L) |
| `package_inner_count` | INT | Parsed from "25X5ML" pattern | Inner package count (25) |
| `package_inner_size` | DECIMAL(12,4) | Parsed | Inner container size (5) |
| `package_inner_unit` | VARCHAR(10) | Parsed | Inner container unit (ML) |
| `total_units_per_package` | INT | Calculated | Total dispensable units |
| `total_doses_per_package` | INT | Calculated | Total doses based on strength |
| `package_description` | VARCHAR(100) | Derived | Human-readable package description |

### Section 7: Drug Flags (Parsed from Description)

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `dea_schedule` | VARCHAR(2) | Parsed (C2, C3, C4, C5) | DEA controlled substance schedule |
| `is_controlled_substance` | BOOLEAN | Derived | TRUE if has DEA schedule |
| `is_schedule_ii` | BOOLEAN | Derived | TRUE if C2 (highest restriction) |
| `is_extended_release` | BOOLEAN | Parsed (ER, XR, XL, CR, SR, LA) | Extended release formulation |
| `is_delayed_release` | BOOLEAN | Parsed (DR, EC) | Delayed/enteric coated |
| `is_immediate_release` | BOOLEAN | Derived | TRUE if not ER/DR |
| `is_unit_dose` | BOOLEAN | Parsed (UD) | Unit dose packaging |
| `is_preservative_free` | BOOLEAN | Parsed (PF) | No preservatives |
| `is_latex_free` | BOOLEAN | Parsed (LF) | Latex-free |
| `is_specialty_pharmacy` | BOOLEAN | Parsed (SPD) | Specialty pharmacy distribution |
| `is_pen_device` | BOOLEAN | Parsed (PPN, PEN) | Pen injector device |
| `is_blister_pack` | BOOLEAN | Parsed (BPK) | Blister pack packaging |
| `is_tip_lok` | BOOLEAN | Parsed (TPLK) | Tip-Lok syringe |
| `release_mechanism` | VARCHAR(30) | Derived | IR, ER, DR, or combination |

### Section 8: Acquisition Pricing (340B)

> **Note:** Sections 8-22 continue the original schema (renumbered from 3-17)

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `contract_cost` | DECIMAL(12,4) | product_catalog | 340B acquisition cost per package |
| `contract_cost_per_unit` | DECIMAL(12,6) | Derived | Contract cost / units per package |
| `contract_effective_date` | DATE | product_catalog | When this price became effective |
| `contract_source` | VARCHAR(100) | Metadata | Source file name |
| `contract_vendor` | VARCHAR(100) | product_catalog | 340B vendor (if specified) |

### Section 9: AWP Pricing (Retail Benchmark)

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `awp` | DECIMAL(12,4) | product_catalog | Average Wholesale Price per package |
| `awp_per_unit` | DECIMAL(12,6) | Derived | AWP / units per package |
| `awp_effective_date` | DATE | product_catalog | When this AWP became effective |
| `awp_source` | VARCHAR(50) | Metadata | 'MEDISPAN', 'REDBOOK', etc. |
| `awp_unit_price` | DECIMAL(12,6) | product_catalog | AWP per billing unit (if different) |

### Section 10: NADAC Pricing (Market Benchmark)

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `nadac_price` | DECIMAL(12,4) | nadac_statistics | National Avg Drug Acquisition Cost |
| `nadac_per_unit` | DECIMAL(12,6) | Derived | NADAC per unit |
| `nadac_effective_date` | DATE | nadac_statistics | NADAC effective date |
| `nadac_as_of_date` | DATE | nadac_statistics | When NADAC was published |
| `nadac_pricing_unit` | VARCHAR(20) | nadac_statistics | Unit of measure for NADAC |
| `nadac_explanation_code` | VARCHAR(10) | nadac_statistics | CMS explanation code |
| `nadac_classification` | VARCHAR(50) | nadac_statistics | CMS classification |

### Section 11: ASP Pricing (Medicare Medical)

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `asp_payment_limit` | DECIMAL(12,4) | asp_pricing | CMS Payment Limit (ASP × 1.06) |
| `asp_true` | DECIMAL(12,4) | Derived | True ASP (Payment Limit / 1.06) |
| `asp_per_billing_unit` | DECIMAL(12,6) | Derived | ASP per HCPCS billing unit |
| `asp_effective_quarter` | VARCHAR(6) | asp_pricing | e.g., '2025Q1' |
| `asp_effective_date` | DATE | asp_pricing | Quarter start date |
| `asp_end_date` | DATE | asp_pricing | Quarter end date |
| `asp_source_file` | VARCHAR(255) | Metadata | CMS source file |

### Section 12: HCPCS/Billing Information

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `hcpcs_code` | CHAR(5) | crosswalk | Primary HCPCS code (e.g., 'J0135') |
| `hcpcs_description` | VARCHAR(255) | asp_pricing | HCPCS description |
| `hcpcs_short_description` | VARCHAR(50) | asp_pricing | Short description |
| `bill_units_per_package` | INT | crosswalk | Billing units per NDC package |
| `hcpcs_dosage_descriptor` | VARCHAR(100) | crosswalk | e.g., "PER 10 MG" |
| `has_medical_path` | BOOLEAN | Derived | TRUE if HCPCS + ASP available |
| `is_noc` | BOOLEAN | noc_crosswalk | TRUE if Not Otherwise Classified |
| `noc_hcpcs_code` | CHAR(5) | noc_crosswalk | NOC code if applicable |
| `noc_payment_limit` | DECIMAL(12,4) | noc_pricing | NOC fallback payment limit |
| `crosswalk_effective_quarter` | VARCHAR(6) | crosswalk | Crosswalk quarter |

### Section 13: Reimbursement Rates (Payer-Specific)

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `awp_factor_brand` | DECIMAL(5,4) | Ravenswood | AWP multiplier for brand (0.85) |
| `awp_factor_generic` | DECIMAL(5,4) | Ravenswood | AWP multiplier for generic (0.20) |
| `awp_factor_applicable` | DECIMAL(5,4) | Derived | Factor based on drug category |
| `medicare_part_d_multiplier` | DECIMAL(5,4) | Ravenswood | Medicare Part D rate |
| `commercial_multiplier` | DECIMAL(5,4) | Ravenswood | Commercial payer rate |
| `medicaid_mco_multiplier` | DECIMAL(5,4) | Ravenswood | Medicaid MCO rate |
| `asp_medicaid_multiplier` | DECIMAL(5,4) | Constant | 1.04 (ASP + 4%) |
| `asp_medicare_multiplier` | DECIMAL(5,4) | Constant | 1.06 (ASP + 6%) |
| `asp_commercial_multiplier` | DECIMAL(5,4) | Configurable | Default 1.15 (ASP + 15%) |

### Section 14: Wholesale/Retail Pricing (Validation)

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `wholesaler_retail_price` | DECIMAL(12,4) | wholesaler_catalog | Actual retail price |
| `wholesaler_name` | VARCHAR(100) | wholesaler_catalog | Wholesaler source |
| `wholesaler_as_of_date` | DATE | wholesaler_catalog | Price effective date |
| `retail_price_variance_pct` | DECIMAL(6,2) | Derived | % diff from calculated |
| `retail_confidence` | ENUM | Derived | 'HIGH', 'MEDIUM', 'LOW' |

### Section 15: Risk Flags

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `is_ira_drug` | BOOLEAN | ira_drug_list | Subject to IRA negotiation |
| `ira_year` | INT | ira_drug_list | Year price takes effect (2026, 2027) |
| `ira_max_fair_price` | DECIMAL(12,4) | ira_drug_list | Negotiated max price (if known) |
| `ira_description` | TEXT | ira_drug_list | IRA notes |
| `is_penny_priced` | BOOLEAN | nadac_statistics | TRUE if 340B discount ≥95% |
| `penny_override_cost` | DECIMAL(12,4) | Derived | $0.01 if penny priced |
| `discount_340b_pct` | DECIMAL(6,2) | nadac_statistics | Total 340B discount % |
| `has_inflation_penalty` | BOOLEAN | nadac_statistics | TRUE if penalty >20% |
| `inflation_penalty_pct` | DECIMAL(6,2) | nadac_statistics | Inflation penalty % |
| `risk_level` | ENUM | Derived | 'LOW', 'MEDIUM', 'HIGH' |
| `risk_factors` | TEXT[] | Derived | Array of risk descriptions |

### Section 16: Biologic/Loading Dose Profile

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `has_loading_dose` | BOOLEAN | biologics_grid | TRUE if loading dose pattern |
| `loading_dose_count` | INT | biologics_grid | Number of loading doses |
| `year_1_fills` | INT | biologics_grid | Total fills in Year 1 |
| `year_2_plus_fills` | INT | biologics_grid | Annual maintenance fills |
| `adjusted_year_1_fills` | DECIMAL(5,2) | biologics_grid | Compliance-adjusted Y1 |
| `adjusted_year_2_fills` | DECIMAL(5,2) | biologics_grid | Compliance-adjusted Y2+ |
| `compliance_rate` | DECIMAL(5,4) | biologics_grid | Assumed compliance rate |
| `indication` | VARCHAR(255) | biologics_grid | Primary indication |
| `loading_dose_delta_pct` | DECIMAL(6,2) | Derived | Y1 uplift percentage |

### Section 17: Calculated Margins (5 Pathways)

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| **Pharmacy - Medicaid** |
| `margin_pharmacy_medicaid` | DECIMAL(12,4) | Calculated | NADAC + fees - contract |
| `margin_pharmacy_medicaid_formula` | TEXT | Derived | Calculation breakdown |
| **Pharmacy - Medicare/Commercial** |
| `margin_pharmacy_medicare_commercial` | DECIMAL(12,4) | Calculated | AWP × factor - contract |
| `margin_pharmacy_medicare_commercial_formula` | TEXT | Derived | Calculation breakdown |
| **Medical - Medicaid** |
| `margin_medical_medicaid` | DECIMAL(12,4) | Calculated | ASP × 1.04 × units - contract |
| `margin_medical_medicaid_formula` | TEXT | Derived | Calculation breakdown |
| **Medical - Medicare** |
| `margin_medical_medicare` | DECIMAL(12,4) | Calculated | ASP × 1.06 × units - contract |
| `margin_medical_medicare_formula` | TEXT | Derived | Calculation breakdown |
| **Medical - Commercial** |
| `margin_medical_commercial` | DECIMAL(12,4) | Calculated | ASP × markup × units - contract |
| `margin_medical_commercial_formula` | TEXT | Derived | Calculation breakdown |

### Section 18: Margin Analysis Summary

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `best_margin` | DECIMAL(12,4) | Derived | Highest margin value |
| `best_pathway` | ENUM | Derived | Pathway with best margin |
| `second_best_margin` | DECIMAL(12,4) | Derived | Second highest margin |
| `second_best_pathway` | ENUM | Derived | Second best pathway |
| `margin_delta` | DECIMAL(12,4) | Derived | Best - Second best |
| `margin_delta_pct` | DECIMAL(6,2) | Derived | Delta as percentage |
| `recommendation` | VARCHAR(50) | Derived | Recommended pathway |
| `recommendation_confidence` | ENUM | Derived | 'HIGH', 'MEDIUM', 'LOW' |
| `all_margins_positive` | BOOLEAN | Derived | All pathways profitable? |
| `has_negative_margin` | BOOLEAN | Derived | Any pathway unprofitable? |

### Section 19: Capture Rate Sensitivity

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `capture_rate_breakeven` | DECIMAL(5,4) | Calculated | Rate where retail = medical |
| `margin_at_40_pct_capture` | DECIMAL(12,4) | Calculated | Retail margin at 40% |
| `margin_at_60_pct_capture` | DECIMAL(12,4) | Calculated | Retail margin at 60% |
| `margin_at_80_pct_capture` | DECIMAL(12,4) | Calculated | Retail margin at 80% |
| `margin_at_100_pct_capture` | DECIMAL(12,4) | Calculated | Retail margin at 100% |
| `recommendation_changes_at` | DECIMAL(5,4) | Calculated | Capture rate where rec changes |

### Section 20: Revenue Projections (Biologic)

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `year_1_revenue_retail` | DECIMAL(14,2) | Calculated | Y1 retail pathway revenue |
| `year_1_revenue_medicare` | DECIMAL(14,2) | Calculated | Y1 Medicare pathway revenue |
| `year_1_revenue_commercial` | DECIMAL(14,2) | Calculated | Y1 Commercial pathway revenue |
| `year_2_revenue_retail` | DECIMAL(14,2) | Calculated | Y2+ retail pathway revenue |
| `year_2_revenue_medicare` | DECIMAL(14,2) | Calculated | Y2+ Medicare pathway revenue |
| `year_2_revenue_commercial` | DECIMAL(14,2) | Calculated | Y2+ Commercial pathway revenue |
| `loading_dose_revenue_delta` | DECIMAL(14,2) | Calculated | Y1 - Y2 revenue difference |
| `patient_lifetime_value_3yr` | DECIMAL(14,2) | Calculated | Y1 + 2×Y2 revenue |

### Section 21: Data Quality & Provenance

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `data_completeness_score` | DECIMAL(5,2) | Derived | % of fields populated |
| `has_contract_cost` | BOOLEAN | Derived | Contract cost available |
| `has_awp` | BOOLEAN | Derived | AWP available |
| `has_asp` | BOOLEAN | Derived | ASP available |
| `has_nadac` | BOOLEAN | Derived | NADAC available |
| `has_hcpcs` | BOOLEAN | Derived | HCPCS mapping available |
| `has_wholesaler_price` | BOOLEAN | Derived | Retail validation available |
| `missing_fields` | TEXT[] | Derived | List of missing critical fields |
| `data_sources_used` | TEXT[] | Derived | List of source files used |
| `last_updated_at` | TIMESTAMP | System | When record was last updated |
| `catalog_load_date` | DATE | Metadata | When catalog was loaded |
| `asp_load_date` | DATE | Metadata | When ASP data was loaded |
| `nadac_load_date` | DATE | Metadata | When NADAC data was loaded |

### Section 22: Timestamps & Audit

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `created_at` | TIMESTAMP | System | Record creation time |
| `updated_at` | TIMESTAMP | System | Last update time |
| `version` | INT | System | Record version number |
| `created_by` | VARCHAR(100) | System | User/process that created |
| `updated_by` | VARCHAR(100) | System | User/process that updated |

---

## SQL Schema Definition

```sql
-- Complete atomized drug detail table
CREATE TABLE drug_detail_complete (
    -- SECTION 1: Identity
    id SERIAL PRIMARY KEY,
    ndc_raw VARCHAR(20),
    ndc_11 CHAR(11) NOT NULL UNIQUE,
    ndc_formatted VARCHAR(13) GENERATED ALWAYS AS (
        SUBSTRING(ndc_11, 1, 5) || '-' ||
        SUBSTRING(ndc_11, 6, 4) || '-' ||
        SUBSTRING(ndc_11, 10, 2)
    ) STORED,
    ndc_10 CHAR(10) GENERATED ALWAYS AS (
        SUBSTRING(ndc_11, 1, 5) || SUBSTRING(ndc_11, 6, 4) || SUBSTRING(ndc_11, 11, 1)
    ) STORED,
    drug_name VARCHAR(255) NOT NULL,
    generic_name VARCHAR(255),
    product_description TEXT,
    manufacturer_name VARCHAR(255),
    manufacturer_labeler_code CHAR(5) GENERATED ALWAYS AS (SUBSTRING(ndc_11, 1, 5)) STORED,

    -- SECTION 2: Classification
    drug_category VARCHAR(20) CHECK (drug_category IN ('BRAND', 'GENERIC', 'SPECIALTY')),
    is_brand BOOLEAN GENERATED ALWAYS AS (drug_category IN ('BRAND', 'SPECIALTY')) STORED,
    is_generic BOOLEAN GENERATED ALWAYS AS (drug_category = 'GENERIC') STORED,
    is_specialty BOOLEAN GENERATED ALWAYS AS (drug_category = 'SPECIALTY') STORED,
    is_biologic BOOLEAN DEFAULT FALSE,
    therapeutic_class VARCHAR(100),
    therapeutic_class_code VARCHAR(20),
    route_of_administration VARCHAR(50),
    dosage_form VARCHAR(100),
    strength VARCHAR(100),
    package_size VARCHAR(50),
    unit_of_measure VARCHAR(20),

    -- SECTION 3: Contract Pricing
    contract_cost DECIMAL(12,4),
    contract_cost_per_unit DECIMAL(12,6),
    contract_effective_date DATE,
    contract_source VARCHAR(100),
    contract_vendor VARCHAR(100),

    -- SECTION 4: AWP Pricing
    awp DECIMAL(12,4),
    awp_per_unit DECIMAL(12,6),
    awp_effective_date DATE,
    awp_source VARCHAR(50),
    awp_unit_price DECIMAL(12,6),

    -- SECTION 5: NADAC Pricing
    nadac_price DECIMAL(12,4),
    nadac_per_unit DECIMAL(12,6),
    nadac_effective_date DATE,
    nadac_as_of_date DATE,
    nadac_pricing_unit VARCHAR(20),
    nadac_explanation_code VARCHAR(10),
    nadac_classification VARCHAR(50),

    -- SECTION 6: ASP Pricing
    asp_payment_limit DECIMAL(12,4),
    asp_true DECIMAL(12,4) GENERATED ALWAYS AS (
        CASE WHEN asp_payment_limit IS NOT NULL
        THEN asp_payment_limit / 1.06
        ELSE NULL END
    ) STORED,
    asp_per_billing_unit DECIMAL(12,6),
    asp_effective_quarter VARCHAR(6),
    asp_effective_date DATE,
    asp_end_date DATE,
    asp_source_file VARCHAR(255),

    -- SECTION 7: HCPCS/Billing
    hcpcs_code CHAR(5),
    hcpcs_description VARCHAR(255),
    hcpcs_short_description VARCHAR(50),
    bill_units_per_package INT DEFAULT 1,
    hcpcs_dosage_descriptor VARCHAR(100),
    has_medical_path BOOLEAN GENERATED ALWAYS AS (
        hcpcs_code IS NOT NULL AND asp_payment_limit IS NOT NULL
    ) STORED,
    is_noc BOOLEAN DEFAULT FALSE,
    noc_hcpcs_code CHAR(5),
    noc_payment_limit DECIMAL(12,4),
    crosswalk_effective_quarter VARCHAR(6),

    -- SECTION 8: Reimbursement Rates
    awp_factor_brand DECIMAL(5,4) DEFAULT 0.85,
    awp_factor_generic DECIMAL(5,4) DEFAULT 0.20,
    awp_factor_applicable DECIMAL(5,4) GENERATED ALWAYS AS (
        CASE drug_category
        WHEN 'GENERIC' THEN 0.20
        ELSE 0.85 END
    ) STORED,
    medicare_part_d_multiplier DECIMAL(5,4) DEFAULT 0.85,
    commercial_multiplier DECIMAL(5,4) DEFAULT 0.84,
    medicaid_mco_multiplier DECIMAL(5,4) DEFAULT 0.78,
    asp_medicaid_multiplier DECIMAL(5,4) DEFAULT 1.04,
    asp_medicare_multiplier DECIMAL(5,4) DEFAULT 1.06,
    asp_commercial_multiplier DECIMAL(5,4) DEFAULT 1.15,

    -- SECTION 9: Wholesale/Retail
    wholesaler_retail_price DECIMAL(12,4),
    wholesaler_name VARCHAR(100),
    wholesaler_as_of_date DATE,
    retail_price_variance_pct DECIMAL(6,2),
    retail_confidence VARCHAR(10) CHECK (retail_confidence IN ('HIGH', 'MEDIUM', 'LOW')),

    -- SECTION 10: Risk Flags
    is_ira_drug BOOLEAN DEFAULT FALSE,
    ira_year INT,
    ira_max_fair_price DECIMAL(12,4),
    ira_description TEXT,
    is_penny_priced BOOLEAN DEFAULT FALSE,
    penny_override_cost DECIMAL(12,4) GENERATED ALWAYS AS (
        CASE WHEN is_penny_priced THEN 0.01 ELSE NULL END
    ) STORED,
    discount_340b_pct DECIMAL(6,2),
    has_inflation_penalty BOOLEAN DEFAULT FALSE,
    inflation_penalty_pct DECIMAL(6,2),
    risk_level VARCHAR(10) CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH')),
    risk_factors TEXT[],

    -- SECTION 11: Biologic Profile
    has_loading_dose BOOLEAN DEFAULT FALSE,
    loading_dose_count INT,
    year_1_fills INT,
    year_2_plus_fills INT,
    adjusted_year_1_fills DECIMAL(5,2),
    adjusted_year_2_fills DECIMAL(5,2),
    compliance_rate DECIMAL(5,4) DEFAULT 0.80,
    indication VARCHAR(255),
    loading_dose_delta_pct DECIMAL(6,2),

    -- SECTION 12: Calculated Margins
    margin_pharmacy_medicaid DECIMAL(12,4),
    margin_pharmacy_medicaid_formula TEXT,
    margin_pharmacy_medicare_commercial DECIMAL(12,4),
    margin_pharmacy_medicare_commercial_formula TEXT,
    margin_medical_medicaid DECIMAL(12,4),
    margin_medical_medicaid_formula TEXT,
    margin_medical_medicare DECIMAL(12,4),
    margin_medical_medicare_formula TEXT,
    margin_medical_commercial DECIMAL(12,4),
    margin_medical_commercial_formula TEXT,

    -- SECTION 13: Margin Summary
    best_margin DECIMAL(12,4),
    best_pathway VARCHAR(50),
    second_best_margin DECIMAL(12,4),
    second_best_pathway VARCHAR(50),
    margin_delta DECIMAL(12,4),
    margin_delta_pct DECIMAL(6,2),
    recommendation VARCHAR(50),
    recommendation_confidence VARCHAR(10),
    all_margins_positive BOOLEAN,
    has_negative_margin BOOLEAN,

    -- SECTION 14: Capture Rate Sensitivity
    capture_rate_breakeven DECIMAL(5,4),
    margin_at_40_pct_capture DECIMAL(12,4),
    margin_at_60_pct_capture DECIMAL(12,4),
    margin_at_80_pct_capture DECIMAL(12,4),
    margin_at_100_pct_capture DECIMAL(12,4),
    recommendation_changes_at DECIMAL(5,4),

    -- SECTION 15: Revenue Projections
    year_1_revenue_retail DECIMAL(14,2),
    year_1_revenue_medicare DECIMAL(14,2),
    year_1_revenue_commercial DECIMAL(14,2),
    year_2_revenue_retail DECIMAL(14,2),
    year_2_revenue_medicare DECIMAL(14,2),
    year_2_revenue_commercial DECIMAL(14,2),
    loading_dose_revenue_delta DECIMAL(14,2),
    patient_lifetime_value_3yr DECIMAL(14,2),

    -- SECTION 16: Data Quality
    data_completeness_score DECIMAL(5,2),
    has_contract_cost BOOLEAN GENERATED ALWAYS AS (contract_cost IS NOT NULL) STORED,
    has_awp BOOLEAN GENERATED ALWAYS AS (awp IS NOT NULL) STORED,
    has_asp BOOLEAN GENERATED ALWAYS AS (asp_payment_limit IS NOT NULL) STORED,
    has_nadac BOOLEAN GENERATED ALWAYS AS (nadac_price IS NOT NULL) STORED,
    has_hcpcs BOOLEAN GENERATED ALWAYS AS (hcpcs_code IS NOT NULL) STORED,
    has_wholesaler_price BOOLEAN GENERATED ALWAYS AS (wholesaler_retail_price IS NOT NULL) STORED,
    missing_fields TEXT[],
    data_sources_used TEXT[],
    last_updated_at TIMESTAMP DEFAULT NOW(),
    catalog_load_date DATE,
    asp_load_date DATE,
    nadac_load_date DATE,

    -- SECTION 17: Audit
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    version INT DEFAULT 1,
    created_by VARCHAR(100),
    updated_by VARCHAR(100)
);

-- Indexes for common queries
CREATE INDEX idx_drug_detail_name ON drug_detail_complete(drug_name);
CREATE INDEX idx_drug_detail_manufacturer ON drug_detail_complete(manufacturer_name);
CREATE INDEX idx_drug_detail_hcpcs ON drug_detail_complete(hcpcs_code);
CREATE INDEX idx_drug_detail_category ON drug_detail_complete(drug_category);
CREATE INDEX idx_drug_detail_ira ON drug_detail_complete(is_ira_drug) WHERE is_ira_drug = TRUE;
CREATE INDEX idx_drug_detail_penny ON drug_detail_complete(is_penny_priced) WHERE is_penny_priced = TRUE;
CREATE INDEX idx_drug_detail_biologic ON drug_detail_complete(is_biologic) WHERE is_biologic = TRUE;
CREATE INDEX idx_drug_detail_best_margin ON drug_detail_complete(best_margin DESC);
CREATE INDEX idx_drug_detail_recommendation ON drug_detail_complete(recommendation);
```

---

## Field Count Summary

| Section | Field Count |
|---------|-------------|
| 1. Drug Identity | 9 |
| 2. Drug Classification | 12 |
| 3. Acquisition Pricing | 5 |
| 4. AWP Pricing | 5 |
| 5. NADAC Pricing | 7 |
| 6. ASP Pricing | 7 |
| 7. HCPCS/Billing | 11 |
| 8. Reimbursement Rates | 9 |
| 9. Wholesale/Retail | 5 |
| 10. Risk Flags | 11 |
| 11. Biologic Profile | 10 |
| 12. Calculated Margins | 10 |
| 13. Margin Summary | 10 |
| 14. Capture Rate Sensitivity | 6 |
| 15. Revenue Projections | 8 |
| 16. Data Quality | 13 |
| 17. Timestamps & Audit | 5 |
| **TOTAL** | **143 fields** |

---

## Data Source Coverage Matrix

| Source File | Fields Populated |
|-------------|------------------|
| product_catalog.xlsx | ~25 fields (Identity, Classification, Contract, AWP) |
| asp_crosswalk.csv | ~8 fields (HCPCS, Billing) |
| asp_pricing.csv | ~7 fields (ASP, Payment Limit) |
| ndc_nadac_master_statistics.csv | ~12 fields (NADAC, Risk) |
| biologics_logic_grid.xlsx | ~10 fields (Biologic Profile) |
| Ravenswood_AWP_Reimbursement_Matrix.xlsx | ~9 fields (Rates, Category) |
| wholesaler_catalog.xlsx | ~5 fields (Retail Validation) |
| ira_drug_list.csv | ~4 fields (IRA Risk) |
| noc_pricing.csv / noc_crosswalk.csv | ~3 fields (NOC Fallback) |
| **Derived/Calculated** | ~60 fields (Margins, Summaries, Quality) |

---

## JSON Representation

For API responses or document storage:

```json
{
  "identity": {
    "ndc_11": "00074433902",
    "ndc_formatted": "00074-4339-02",
    "drug_name": "HUMIRA",
    "generic_name": "adalimumab",
    "product_description": "HUMIRA PEN SF 40MG/0.8ML 2 SPD",
    "manufacturer_name": "ABBVIE",
    "manufacturer_labeler_code": "00074"
  },
  "classification": {
    "drug_category": "SPECIALTY",
    "is_brand": true,
    "is_biologic": true,
    "therapeutic_class": "TNF Inhibitor"
  },
  "dosage_form": {
    "form_code": "SDPF",
    "dosage_form": "SINGLE DOSE PREFILLED",
    "dosage_form_category": "INJECTABLE",
    "route_of_administration": "INJECTABLE",
    "is_injectable": true
  },
  "strength": {
    "strength_raw": "40MG/0.8ML",
    "strength_value_1": 40.0,
    "strength_unit_1": "MG",
    "is_combination_drug": false,
    "strength_display": "40 MG"
  },
  "concentration": {
    "concentration_raw": "40MG/0.8ML",
    "concentration_numerator": 40.0,
    "concentration_numerator_unit": "MG",
    "concentration_denominator": 0.8,
    "concentration_denominator_unit": "ML",
    "concentration_per_ml": 50.0,
    "has_concentration": true
  },
  "package": {
    "package_size_raw": 0.8,
    "package_qty_raw": 2,
    "total_volume_value": 1.6,
    "total_volume_unit": "ML",
    "package_inner_count": 2,
    "package_inner_size": 0.8,
    "package_inner_unit": "ML",
    "total_units_per_package": 2,
    "package_description": "2 x 0.8ML prefilled pens"
  },
  "flags": {
    "dea_schedule": null,
    "is_controlled_substance": false,
    "is_extended_release": false,
    "is_specialty_pharmacy": true,
    "is_pen_device": true,
    "is_preservative_free": false
  },
  "pricing": {
    "contract": {
      "cost": 150.00,
      "effective_date": "2025-01-01",
      "source": "product_catalog.xlsx"
    },
    "awp": {
      "price": 6500.00,
      "factor_applicable": 0.85,
      "effective_date": "2025-01-01"
    },
    "nadac": {
      "price": 5800.00,
      "effective_date": "2025-01-15"
    },
    "asp": {
      "payment_limit": 2968.00,
      "true_asp": 2800.00,
      "effective_quarter": "2025Q1"
    }
  },
  "billing": {
    "hcpcs_code": "J0135",
    "hcpcs_description": "ADALIMUMAB INJECTION",
    "bill_units_per_package": 2,
    "has_medical_path": true
  },
  "risk": {
    "is_ira_drug": false,
    "is_penny_priced": false,
    "has_inflation_penalty": false,
    "risk_level": "LOW",
    "risk_factors": []
  },
  "biologic_profile": {
    "has_loading_dose": true,
    "year_1_fills": 15,
    "year_2_plus_fills": 12,
    "compliance_rate": 0.80
  },
  "margins": {
    "pharmacy_medicaid": 5650.00,
    "pharmacy_medicare_commercial": 5375.00,
    "medical_medicaid": 5678.00,
    "medical_medicare": 5786.00,
    "medical_commercial": 6290.00
  },
  "analysis": {
    "best_margin": 6290.00,
    "best_pathway": "MEDICAL_COMMERCIAL",
    "margin_delta": 504.00,
    "recommendation": "COMMERCIAL_MEDICAL",
    "recommendation_confidence": "HIGH"
  },
  "data_quality": {
    "completeness_score": 95.2,
    "missing_fields": [],
    "data_sources_used": [
      "product_catalog.xlsx",
      "asp_crosswalk.csv",
      "asp_pricing.csv",
      "ndc_nadac_master_statistics.csv",
      "biologics_logic_grid.xlsx"
    ]
  },
  "metadata": {
    "created_at": "2025-01-25T10:00:00Z",
    "updated_at": "2025-01-25T10:00:00Z",
    "version": 1
  }
}
```

---

## Primary Key & Record Uniqueness

### The NDC Uniqueness Problem

**Critical Finding:** NDC alone does NOT uniquely identify a record in the source data.

```
Total rows in product_catalog:  34,229
Unique NDCs:                    30,212
Duplicate NDCs:                  4,017 (11.7%)
```

The same NDC can appear multiple times with different:
- **Contract names** (Off-Contract, PUBLIC HEALTH SERVICES, SPD PHS)
- **Contract prices** (ranging from $0.01 to $31,788.25)
- **Effective dates**

### Uniqueness Examples from Real Data

#### HUMIRA: Unique NDCs (1:1 Mapping)

HUMIRA is a **good example** where each NDC is unique:

```
NDC           | Description                        | Cost
--------------|------------------------------------|----------
00074433902   | HUMIRA PEN SF 40MG/0.8 2 SPD       | $5,550.00
00074432802   | HUMIRA SF 40MG/0.8ML 2 KIT SPD     | $5,550.00
00074906802   | HUMIRA PEN SF 80MG/0.8 2 SPD       | $5,550.00
00074028902   | HUMIRA SF PEDI 10MG/0.1 2 KIT SPD  | $2,818.55
00074028802   | HUMIRA SF PEDI 20MG/0.2 2 KIT SPD  | $2,818.55
00074433702   | HUMIRA PEN SF 40/0.4 2 CF SPD      | $5,550.00
00074432902   | HUMIRA SF 40MG/0.4ML 2 KIT SPD     | $5,550.00
00074055402   | HUMIRA PEDI SF 80MG/0.8 2 SPD      | $5,550.00
00074055302   | HUMIRA PEDI SF 40MG/0.4 2 SPD      | $2,775.00
--------------|------------------------------------|----------
9 NDCs → 9 rows = 1:1 (ideal)
```

#### ACTEMRA: Duplicate NDCs by Contract

ACTEMRA shows the **same NDC with different contracts**:

```
NDC           | Description              | Contract Name           | Cost
--------------|--------------------------|-------------------------|----------
50242013501   | ACTEMRA VL 400MG/20ML 1  | Off-Contract            | $1,404.01
50242013501   | ACTEMRA VL 400MG/20ML 1  | PUBLIC HEALTH SERVICES  | $884.76
50242013401   | ACTEMRA VL 200MG/10ML 1  | Off-Contract            | $702.01
50242013401   | ACTEMRA VL 200MG/10ML 1  | PUBLIC HEALTH SERVICES  | $442.58
50242013601   | ACTEMRA VL 80MG/4ML 1    | Off-Contract            | $280.81
50242013601   | ACTEMRA VL 80MG/4ML 1    | PUBLIC HEALTH SERVICES  | $177.03
--------------|--------------------------|-------------------------|----------
3 NDCs → 6 rows = 1:2 (contract-based duplication)
```

#### KRYSTEXXA: Extreme Price Variance

KRYSTEXXA demonstrates the **most extreme price variance** for a single NDC:

```
NDC           | Description               | Contract Name              | Cost
--------------|---------------------------|----------------------------|------------
75987008010   | KRYSTEXXA VL 8MG/ML 2X1ML | Off-Contract               | $31,788.25
75987008010   | KRYSTEXXA VL 8MG/ML 2X1ML | SPD PHS (ORPHAN/BILL TO PD)| $0.01
--------------|---------------------------|----------------------------|------------
Same NDC → Price difference of $31,788.24 (penny pricing for orphan drug)
```

### Schema Implications

For the **drug_detail_complete** table, you have three options:

#### Option A: Deduplicate by NDC (Recommended for Gold Layer)

Keep one record per NDC, use the **best available contract price**:

```sql
-- Primary key is NDC alone
ndc_11 CHAR(11) PRIMARY KEY,

-- Store best contract price
contract_cost DECIMAL(12,4),           -- Lowest price (or PHS price)
contract_name VARCHAR(100),            -- Which contract
contract_cost_off_contract DECIMAL(12,4),  -- Off-contract price for reference
```

**Best for:** Dashboard queries, drug detail views, margin calculations

#### Option B: Composite Key (One Row Per NDC + Contract)

Maintain separate records for each contract:

```sql
PRIMARY KEY (ndc_11, contract_name),
```

**Best for:** Contract comparison analysis, historical tracking

#### Option C: Surrogate Key with Uniqueness Constraint

```sql
id SERIAL PRIMARY KEY,
ndc_11 CHAR(11) NOT NULL,
contract_name VARCHAR(100),
UNIQUE(ndc_11, contract_name, effective_date)
```

**Best for:** Data warehousing, ETL pipelines

### Recommendation

For this schema (**Gold Layer drug detail**), use **Option A**:
- One record per NDC
- Use the best/lowest contract price
- Store off-contract price separately for reference
- Calculate margins against the best available price

This aligns with the dashboard use case where you want to show the best opportunity for each drug.

---

## Implementation Notes

### When to Use This Schema

1. **Full Drug Detail Page**: When displaying comprehensive drug information
2. **Export/Reporting**: When generating complete drug reports
3. **API Responses**: When serving drug data to external systems
4. **Data Warehouse**: As the gold layer in a medallion architecture

### When NOT to Use This Schema

1. **Dashboard List View**: Too heavy - use summarized view instead
2. **Search Results**: Only need identity + key metrics
3. **High-Frequency Queries**: Use indexed summary tables

### Recommended Approach

```
Bronze Layer:  Raw source files (as-is)
     ↓
Silver Layer:  3NF normalized tables (DATABASE_DESIGN.md)
     ↓
Gold Layer:    Denormalized drug_detail_complete (this schema)
```

---

## Appendix A: Form Code Reference Table

Maps the `Form` column from product_catalog to expanded dosage form and route of administration.

| Form Code | Dosage Form | Route | Category | Count |
|-----------|-------------|-------|----------|-------|
| TABS | Tablet | ORAL | SOLID | 13,191 |
| PWVL | Powder Vial (reconstitute) | INJECTABLE | INJECTABLE | 4,640 |
| CAPS | Capsule | ORAL | SOLID | 3,545 |
| SYRN | Syringe/Pen | INJECTABLE | INJECTABLE | 1,304 |
| SDPF | Single Dose Prefilled | INJECTABLE | INJECTABLE | 1,061 |
| POWD | Powder | ORAL | SOLID | 997 |
| SDV | Single Dose Vial | INJECTABLE | INJECTABLE | 890 |
| SOLN | Solution | ORAL | LIQUID | 720 |
| MDV | Multi Dose Vial | INJECTABLE | INJECTABLE | 623 |
| CRM | Cream | TOPICAL | TOPICAL | 606 |
| DROP | Drops | OPHTHALMIC/OTIC | LIQUID | 536 |
| KIT | Kit | COMBINATION | COMBINATION | 520 |
| IVSL | IV Solution | INJECTABLE | INJECTABLE | 419 |
| EACH | Each/Misc | SUPPLY | SUPPLY | 398 |
| GEL | Gel | TOPICAL | TOPICAL | 327 |
| OINT | Ointment | TOPICAL | TOPICAL | 320 |
| POSR | Powder for Oral Solution | ORAL | SOLID | 298 |
| SUSP | Suspension | ORAL | LIQUID | 257 |
| IPSL | IV Solution Premix | INJECTABLE | INJECTABLE | 250 |
| PTCH | Patch | TRANSDERMAL | TRANSDERMAL | 241 |
| NEDL | Needle | SUPPLY | SUPPLY | 226 |
| PCKT | Packet | ORAL | SOLID | 223 |
| AMIH | Ampule/Inhaler | INJECTABLE/INHALATION | INJECTABLE | 200 |
| TDIS | Transdermal Disc | TRANSDERMAL | TRANSDERMAL | 200 |
| LIQD | Liquid | ORAL | LIQUID | 168 |
| GCAP | Gel Capsule | ORAL | SOLID | 151 |
| CHEW | Chewable Tablet | ORAL | SOLID | 144 |
| ARIN | Inhaler/Aerosol | INHALATION | INHALATION | 132 |
| SPRT | Spray/Solution | TOPICAL | TOPICAL | 109 |
| AMPS | Ampule | INJECTABLE | INJECTABLE | 108 |
| LOTN | Lotion | TOPICAL | TOPICAL | 84 |
| FOAM | Foam | TOPICAL | TOPICAL | 45 |
| SPRK | Sprinkle Capsule | ORAL | SOLID | 29 |

---

## Appendix B: Description Parsing Patterns

### Regex Patterns for Field Extraction

```python
import re

def parse_drug_description(description: str) -> dict:
    """
    Parse product description to extract structured fields.

    Example inputs:
    - "HYDROCOD/APAP TB 10-325MG 500 C2"
    - "MOUNJARO SY 7.5MG/0.5ML 4 PPN"
    - "IRON SUCROSE SF 20MG/ML 25X2.5ML"
    """
    result = {}
    desc = str(description).upper() if description else ""

    # 1. DEA Schedule (C2, C3, C4, C5)
    dea_match = re.search(r'\b(C[2-5])\b', desc)
    result['dea_schedule'] = dea_match.group(1) if dea_match else None

    # 2. Combination Strength (10-325MG)
    combo_match = re.search(r'(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)(MG|MCG|G)', desc)
    if combo_match:
        result['strength_value_1'] = float(combo_match.group(1))
        result['strength_value_2'] = float(combo_match.group(2))
        result['strength_unit'] = combo_match.group(3)
        result['is_combination_drug'] = True
    else:
        # Single Strength (100MG, 50MCG)
        strength_match = re.search(r'\b(\d+(?:\.\d+)?)\s*(MG|MCG|G|MEQ|UNIT|U|IU)\b', desc)
        if strength_match:
            result['strength_value_1'] = float(strength_match.group(1))
            result['strength_unit'] = strength_match.group(2)
        result['is_combination_drug'] = False

    # 3. Concentration (20MG/ML, 7.5MG/0.5ML, 1000U/ML)
    conc_match = re.search(
        r'(\d+(?:\.\d+)?)(MG|MCG|G|U|IU|UNIT|ELU)/(\d*\.?\d*)(ML|L)',
        desc
    )
    if conc_match:
        result['concentration_numerator'] = float(conc_match.group(1))
        result['concentration_numerator_unit'] = conc_match.group(2)
        denom = conc_match.group(3)
        result['concentration_denominator'] = float(denom) if denom else 1.0
        result['concentration_denominator_unit'] = conc_match.group(4)

    # 4. Package Pattern (25X5ML, 10X20ML, 4X21)
    pkg_match = re.search(r'(\d+)X(\d+(?:\.\d+)?)(ML|MG|GM|L)?', desc)
    if pkg_match:
        result['package_inner_count'] = int(pkg_match.group(1))
        result['package_inner_size'] = float(pkg_match.group(2))
        result['package_inner_unit'] = pkg_match.group(3)

    # 5. Total Volume (standalone, e.g., "23ML" at end)
    if not pkg_match:
        vol_match = re.search(r'\b(\d+(?:\.\d+)?)(ML|L)\b', desc)
        if vol_match:
            result['total_volume_value'] = float(vol_match.group(1))
            result['total_volume_unit'] = vol_match.group(2)

    # 6. Release Mechanism Flags
    result['is_extended_release'] = bool(re.search(r'\b(ER|XR|XL|CR|SR|LA)\b', desc))
    result['is_delayed_release'] = bool(re.search(r'\b(DR|EC)\b', desc))

    # 7. Special Flags
    result['is_unit_dose'] = 'UD' in desc
    result['is_preservative_free'] = 'PF' in desc
    result['is_latex_free'] = 'LF' in desc
    result['is_specialty_pharmacy'] = 'SPD' in desc
    result['is_pen_device'] = bool(re.search(r'\b(PPN|PEN)\b', desc))
    result['is_blister_pack'] = 'BPK' in desc
    result['is_tip_lok'] = 'TPLK' in desc

    return result
```

### Parsing Examples

| Input Description | Parsed Fields |
|-------------------|---------------|
| `HYDROCOD/APAP TB 10-325MG 500 C2` | strength_value_1=10, strength_value_2=325, strength_unit=MG, is_combination_drug=True, dea_schedule=C2 |
| `MOUNJARO SY 7.5MG/0.5ML 4 PPN` | concentration_numerator=7.5, concentration_denominator=0.5, concentration_*_unit=MG/ML, is_pen_device=True |
| `IRON SUCROSE SF 20MG/ML 25X2.5ML` | concentration=20MG/ML, package_inner_count=25, package_inner_size=2.5, package_inner_unit=ML |
| `COREG CR CP 80MG 30 ER` | strength_value_1=80, strength_unit=MG, is_extended_release=True |
| `LACOSAMIDE SD 10MG/ML 10X20ML C5` | concentration=10MG/ML, package=10X20ML, dea_schedule=C5 |
| `LYNPARZA TB 100MG 120 SPD` | strength_value_1=100, strength_unit=MG, is_specialty_pharmacy=True |
| `SODIUM CL IS 0.9% 18X500ML LF` | package_inner_count=18, package_inner_size=500, package_inner_unit=ML, is_latex_free=True |

---

## Appendix C: Unit Standardization

### Strength Unit Conversions

| From | To | Factor |
|------|----|--------|
| G | MG | × 1000 |
| MCG | MG | ÷ 1000 |
| IU | UNIT | 1:1 |
| U | UNIT | 1:1 |
| ELU | UNIT | 1:1 (ELISA Units) |
| MEQ | MEQ | (no conversion, electrolytes) |

### Volume Unit Conversions

| From | To | Factor |
|------|----|--------|
| L | ML | × 1000 |
| CC | ML | 1:1 |

### Calculated Fields

```sql
-- Concentration per ML (normalized)
concentration_per_ml = concentration_numerator /
    CASE concentration_denominator_unit
        WHEN 'L' THEN concentration_denominator * 1000
        ELSE concentration_denominator
    END;

-- Total volume in package
total_volume_ml = package_inner_count * package_inner_size *
    CASE package_inner_unit
        WHEN 'L' THEN 1000
        ELSE 1
    END;

-- Total drug amount in package
total_drug_amount = concentration_per_ml * total_volume_ml;

-- Doses per package (if single-dose strength known)
doses_per_package = total_drug_amount / strength_value_1;
```

---

## Updated Field Count Summary

| Section | Field Count | New in v1.1 |
|---------|-------------|-------------|
| 1. Drug Identity | 9 | - |
| 2. Drug Classification | 7 | - |
| 3. Dosage Form & Route | 10 | ✓ NEW |
| 4. Strength & Dosage | 8 | ✓ NEW |
| 5. Concentration | 7 | ✓ NEW |
| 6. Volume & Package | 10 | ✓ NEW |
| 7. Drug Flags | 14 | ✓ NEW |
| 8-22. (Original sections 3-17) | 98 | - |
| **TOTAL** | **163 fields** | +49 new |

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-01-25 | Claude | Initial complete schema with 143 fields |
| 1.1 | 2025-01-25 | Claude | Added description parsing (Sections 3-7), form code reference, +49 fields to 163 total |
| 1.2 | 2025-01-25 | Claude | Added Primary Key & Record Uniqueness section with HUMIRA, ACTEMRA, KRYSTEXXA examples |
