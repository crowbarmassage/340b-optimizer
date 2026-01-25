# 340B Optimizer Database Design

This document outlines the proposed SQL database schema for the 340B Optimizer application.

## Design Philosophy

### Third Normal Form (3NF)

**Pros of 3NF:**
- Data integrity (single source of truth)
- Easier maintenance (update in one place)
- Smaller storage footprint
- Clear entity relationships

**Cons of 3NF:**
- More JOINs for reporting queries
- Can be slower for analytical workloads
- More complex queries

**Recommendation:** Use 3NF for **source/staging tables**, but create **denormalized views or materialized tables** for dashboard queries. This gives clean data management with fast reporting.

---

## Current Data Sources → Table Mapping

| Source File | Target Table(s) |
|-------------|-----------------|
| `product_catalog.xlsx` | `drug`, `manufacturer`, `contract_pricing`, `awp_pricing` |
| `asp_pricing.csv` | `asp_payment_limit` |
| `asp_crosswalk.csv` | `ndc_hcpcs_crosswalk`, `hcpcs_code` |
| `ndc_nadac_master_statistics.csv` | `nadac_pricing`, `penny_pricing_status` |
| `biologics_logic_grid.xlsx` | `biologic_dosing_profile` |
| `Ravenswood_AWP_Reimbursement_Matrix.xlsx` | `drug_category`, `payer_type`, `reimbursement_rate` |
| `wholesaler_catalog.xlsx` | `wholesaler_pricing` |
| `ira_drug_list.csv` | `ira_drug` |
| `noc_pricing.csv` / `noc_crosswalk.csv` | `hcpcs_code` (is_noc=TRUE), `ndc_hcpcs_crosswalk` |

---

## Entity Relationship Diagram

```
                    ┌─────────────────┐
                    │  manufacturer   │
                    └────────┬────────┘
                             │ 1:N
┌──────────────┐    ┌────────┴────────┐    ┌─────────────────┐
│ therapeutic  │←───│      drug       │───→│  drug_category  │
│    class     │    │   (NDC = PK)    │    │ (Brand/Generic) │
└──────────────┘    └────────┬────────┘    └────────┬────────┘
                             │                      │
         ┌───────────────────┼───────────────────┐  │
         │                   │                   │  │
         ▼                   ▼                   ▼  │
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│contract_pricing │ │  awp_pricing    │ │ nadac_pricing   │
│  (time-series)  │ │  (time-series)  │ │  (time-series)  │
└─────────────────┘ └─────────────────┘ └─────────────────┘

         │
         ▼
┌─────────────────┐    ┌─────────────────┐
│ ndc_hcpcs_      │───→│   hcpcs_code    │
│   crosswalk     │    └────────┬────────┘
└─────────────────┘             │
                                ▼
                    ┌─────────────────────┐
                    │  asp_payment_limit  │
                    │   (by quarter)      │
                    └─────────────────────┘

┌─────────────────┐         ┌─────────────────┐
│   payer_type    │────────→│reimbursement_   │
└─────────────────┘    N:M  │     rate        │←── drug_category
                            └─────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    ira_drug     │    │ penny_pricing   │    │biologic_dosing  │
│  (risk flag)    │    │    _status      │    │   _profile      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## Table Definitions

### Core Entities

#### 1. drug (Central Entity)
```sql
CREATE TABLE drug (
    ndc CHAR(11) PRIMARY KEY,              -- Normalized 11-digit NDC
    drug_name VARCHAR(255) NOT NULL,
    generic_name VARCHAR(255),
    manufacturer_id INT REFERENCES manufacturer(id),
    therapeutic_class_id INT REFERENCES therapeutic_class(id),
    drug_category_id INT REFERENCES drug_category(id),  -- Brand/Generic/Specialty
    is_biologic BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_drug_name ON drug(drug_name);
CREATE INDEX idx_drug_manufacturer ON drug(manufacturer_id);
CREATE INDEX idx_drug_category ON drug(drug_category_id);
```

#### 2. manufacturer
```sql
CREATE TABLE manufacturer (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_manufacturer_name ON manufacturer(name);
```

#### 3. therapeutic_class
```sql
CREATE TABLE therapeutic_class (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,     -- e.g., "TNF Inhibitor"
    description TEXT
);
```

#### 4. drug_category (Brand/Generic/Specialty)
```sql
CREATE TABLE drug_category (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,      -- 'BRAND', 'GENERIC', 'SPECIALTY'
    awp_factor DECIMAL(5,4) NOT NULL       -- 0.85 for Brand/Specialty, 0.20 for Generic
);

-- Seed data
INSERT INTO drug_category (name, awp_factor) VALUES
    ('GENERIC', 0.20),
    ('BRAND', 0.85),
    ('SPECIALTY', 0.85);
```

---

### Pricing Tables (Time-Variant)

#### 5. contract_pricing (340B Acquisition Cost)
```sql
CREATE TABLE contract_pricing (
    id SERIAL PRIMARY KEY,
    ndc CHAR(11) REFERENCES drug(ndc),
    contract_cost DECIMAL(12,2) NOT NULL,
    effective_date DATE NOT NULL,
    end_date DATE,
    source_file VARCHAR(255),              -- Audit trail
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(ndc, effective_date)
);

CREATE INDEX idx_contract_pricing_ndc ON contract_pricing(ndc);
CREATE INDEX idx_contract_pricing_date ON contract_pricing(effective_date);
```

#### 6. awp_pricing (Average Wholesale Price)
```sql
CREATE TABLE awp_pricing (
    id SERIAL PRIMARY KEY,
    ndc CHAR(11) REFERENCES drug(ndc),
    awp DECIMAL(12,2) NOT NULL,
    effective_date DATE NOT NULL,
    end_date DATE,
    source VARCHAR(50),                    -- 'MEDISPAN', etc.
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(ndc, effective_date)
);

CREATE INDEX idx_awp_pricing_ndc ON awp_pricing(ndc);
CREATE INDEX idx_awp_pricing_date ON awp_pricing(effective_date);
```

#### 7. nadac_pricing (National Average Drug Acquisition Cost)
```sql
CREATE TABLE nadac_pricing (
    id SERIAL PRIMARY KEY,
    ndc CHAR(11) REFERENCES drug(ndc),
    nadac_price DECIMAL(12,4) NOT NULL,
    effective_date DATE NOT NULL,
    as_of_date DATE,
    pricing_unit VARCHAR(20),              -- 'EA', 'ML', etc.
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(ndc, effective_date)
);

CREATE INDEX idx_nadac_pricing_ndc ON nadac_pricing(ndc);
CREATE INDEX idx_nadac_pricing_date ON nadac_pricing(effective_date);
```

---

### Billing/Reimbursement Tables

#### 8. hcpcs_code (Medicare Billing Codes)
```sql
CREATE TABLE hcpcs_code (
    code CHAR(5) PRIMARY KEY,              -- e.g., 'J0135'
    short_description VARCHAR(255),
    long_description TEXT,
    is_noc BOOLEAN DEFAULT FALSE,          -- Not Otherwise Classified
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 9. ndc_hcpcs_crosswalk (NDC to HCPCS Mapping)
```sql
-- Many-to-Many: NDC can map to multiple HCPCS over time
CREATE TABLE ndc_hcpcs_crosswalk (
    id SERIAL PRIMARY KEY,
    ndc CHAR(11) REFERENCES drug(ndc),
    hcpcs_code CHAR(5) REFERENCES hcpcs_code(code),
    bill_units_per_package INT NOT NULL DEFAULT 1,
    effective_quarter VARCHAR(6),          -- '2025Q1'
    effective_date DATE,
    end_date DATE,
    source_file VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(ndc, hcpcs_code, effective_date)
);

CREATE INDEX idx_crosswalk_ndc ON ndc_hcpcs_crosswalk(ndc);
CREATE INDEX idx_crosswalk_hcpcs ON ndc_hcpcs_crosswalk(hcpcs_code);
CREATE INDEX idx_crosswalk_quarter ON ndc_hcpcs_crosswalk(effective_quarter);
```

#### 10. asp_payment_limit (CMS Quarterly Pricing)
```sql
CREATE TABLE asp_payment_limit (
    id SERIAL PRIMARY KEY,
    hcpcs_code CHAR(5) REFERENCES hcpcs_code(code),
    payment_limit DECIMAL(12,4) NOT NULL,  -- This is ASP × 1.06
    asp_true DECIMAL(12,4) GENERATED ALWAYS AS (payment_limit / 1.06) STORED,
    effective_quarter VARCHAR(6) NOT NULL, -- '2025Q1'
    effective_date DATE NOT NULL,
    end_date DATE,
    source_file VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(hcpcs_code, effective_quarter)
);

CREATE INDEX idx_asp_hcpcs ON asp_payment_limit(hcpcs_code);
CREATE INDEX idx_asp_quarter ON asp_payment_limit(effective_quarter);
```

---

### Payer/Reimbursement Tables

#### 11. payer_type
```sql
CREATE TABLE payer_type (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,     -- 'Medicare Part D', 'Commercial', 'Medicaid MCO'
    channel VARCHAR(20) NOT NULL,          -- 'PHARMACY', 'MEDICAL'
    description TEXT
);

-- Seed data
INSERT INTO payer_type (name, channel) VALUES
    ('Medicare Part D', 'PHARMACY'),
    ('Commercial', 'PHARMACY'),
    ('Medicaid MCO', 'PHARMACY'),
    ('Self Pay', 'PHARMACY'),
    ('Medicare Part B', 'MEDICAL'),
    ('Commercial Medical', 'MEDICAL'),
    ('Medicaid Medical', 'MEDICAL');
```

#### 12. reimbursement_rate (Payer × Drug Category Matrix)
```sql
CREATE TABLE reimbursement_rate (
    id SERIAL PRIMARY KEY,
    payer_type_id INT REFERENCES payer_type(id),
    drug_category_id INT REFERENCES drug_category(id),
    awp_multiplier DECIMAL(5,4),           -- For pharmacy channel
    asp_multiplier DECIMAL(5,4),           -- For medical channel
    effective_date DATE NOT NULL,
    end_date DATE,
    source VARCHAR(100),                   -- 'Ravenswood Matrix'
    UNIQUE(payer_type_id, drug_category_id, effective_date)
);

-- Seed data (from Ravenswood Matrix)
-- Medicare Part D
INSERT INTO reimbursement_rate (payer_type_id, drug_category_id, awp_multiplier, effective_date, source)
SELECT p.id, d.id,
    CASE d.name WHEN 'GENERIC' THEN 0.20 ELSE 0.85 END,
    '2024-01-01', 'Ravenswood Matrix'
FROM payer_type p, drug_category d WHERE p.name = 'Medicare Part D';

-- Commercial
INSERT INTO reimbursement_rate (payer_type_id, drug_category_id, awp_multiplier, effective_date, source)
SELECT p.id, d.id,
    CASE d.name WHEN 'GENERIC' THEN 0.15 WHEN 'BRAND' THEN 0.84 ELSE 0.86 END,
    '2024-01-01', 'Ravenswood Matrix'
FROM payer_type p, drug_category d WHERE p.name = 'Commercial';

-- Medicaid MCO
INSERT INTO reimbursement_rate (payer_type_id, drug_category_id, awp_multiplier, effective_date, source)
SELECT p.id, d.id,
    CASE d.name WHEN 'GENERIC' THEN 0.15 WHEN 'BRAND' THEN 0.78 ELSE 0.80 END,
    '2024-01-01', 'Ravenswood Matrix'
FROM payer_type p, drug_category d WHERE p.name = 'Medicaid MCO';
```

---

### Risk/Flag Tables

#### 13. ira_drug (Inflation Reduction Act)
```sql
CREATE TABLE ira_drug (
    id SERIAL PRIMARY KEY,
    drug_name VARCHAR(255) NOT NULL,
    ira_year INT NOT NULL,                 -- 2026, 2027, etc.
    description TEXT,
    max_fair_price DECIMAL(12,2),
    effective_date DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(drug_name, ira_year)
);

CREATE INDEX idx_ira_drug_name ON ira_drug(UPPER(drug_name));
CREATE INDEX idx_ira_year ON ira_drug(ira_year);
```

#### 14. penny_pricing_status (Derived from NADAC)
```sql
CREATE TABLE penny_pricing_status (
    id SERIAL PRIMARY KEY,
    ndc CHAR(11) REFERENCES drug(ndc),
    is_penny_priced BOOLEAN NOT NULL,
    discount_340b_pct DECIMAL(6,2),
    inflation_penalty_pct DECIMAL(6,2),
    override_cost DECIMAL(12,4),           -- $0.01 if penny priced
    as_of_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(ndc, as_of_date)
);

CREATE INDEX idx_penny_ndc ON penny_pricing_status(ndc);
CREATE INDEX idx_penny_flag ON penny_pricing_status(is_penny_priced);
```

---

### Biologic/Loading Dose Tables

#### 15. biologic_dosing_profile
```sql
CREATE TABLE biologic_dosing_profile (
    id SERIAL PRIMARY KEY,
    drug_name VARCHAR(255) NOT NULL,
    indication VARCHAR(255),
    has_loading_dose BOOLEAN DEFAULT TRUE,
    loading_dose_count INT,
    year_1_fills INT NOT NULL,
    year_2_plus_fills INT NOT NULL,
    adjusted_year_1_fills DECIMAL(5,2),
    adjusted_year_2_fills DECIMAL(5,2),
    compliance_rate DECIMAL(5,4) DEFAULT 0.80,
    source VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_biologic_drug ON biologic_dosing_profile(UPPER(drug_name));
```

---

### Retail Validation

#### 16. wholesaler_pricing
```sql
CREATE TABLE wholesaler_pricing (
    id SERIAL PRIMARY KEY,
    ndc CHAR(11) REFERENCES drug(ndc),
    retail_price DECIMAL(12,2),
    wholesaler_name VARCHAR(100),
    as_of_date DATE NOT NULL,
    source_file VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(ndc, wholesaler_name, as_of_date)
);

CREATE INDEX idx_wholesaler_ndc ON wholesaler_pricing(ndc);
```

---

## Denormalized View for Dashboard

This materialized view pre-computes all margins for fast dashboard queries:

```sql
CREATE MATERIALIZED VIEW mv_drug_margin_analysis AS
SELECT
    d.ndc,
    d.drug_name,
    m.name AS manufacturer,
    tc.name AS therapeutic_class,
    dc.name AS drug_category,
    dc.awp_factor,
    d.is_biologic,

    -- Current pricing (latest effective)
    cp.contract_cost,
    ap.awp,
    np.nadac_price,
    apl.asp_true AS asp,
    apl.payment_limit,

    -- Billing info
    xw.hcpcs_code,
    xw.bill_units_per_package,

    -- Risk flags
    CASE WHEN ira.id IS NOT NULL THEN TRUE ELSE FALSE END AS is_ira_drug,
    ira.ira_year,
    COALESCE(pp.is_penny_priced, FALSE) AS is_penny_priced,
    pp.inflation_penalty_pct,
    pp.discount_340b_pct,

    -- Pharmacy margins
    CASE WHEN np.nadac_price IS NOT NULL THEN
        np.nadac_price - cp.contract_cost
    END AS pharmacy_medicaid_margin,

    (ap.awp * dc.awp_factor) - cp.contract_cost AS pharmacy_medicare_commercial_margin,

    -- Medical margins (if HCPCS exists)
    CASE WHEN apl.asp_true IS NOT NULL THEN
        (apl.asp_true * 1.04 * xw.bill_units_per_package) - cp.contract_cost
    END AS medical_medicaid_margin,

    CASE WHEN apl.asp_true IS NOT NULL THEN
        (apl.asp_true * 1.06 * xw.bill_units_per_package) - cp.contract_cost
    END AS medical_medicare_margin,

    CASE WHEN apl.asp_true IS NOT NULL THEN
        (apl.asp_true * 1.15 * xw.bill_units_per_package) - cp.contract_cost
    END AS medical_commercial_margin,

    -- Best margin calculation
    GREATEST(
        COALESCE((ap.awp * dc.awp_factor) - cp.contract_cost, 0),
        COALESCE((apl.asp_true * 1.04 * xw.bill_units_per_package) - cp.contract_cost, 0),
        COALESCE((apl.asp_true * 1.06 * xw.bill_units_per_package) - cp.contract_cost, 0),
        COALESCE((apl.asp_true * 1.15 * xw.bill_units_per_package) - cp.contract_cost, 0)
    ) AS best_margin,

    -- Timestamps for freshness
    cp.effective_date AS contract_effective_date,
    ap.effective_date AS awp_effective_date,
    apl.effective_quarter AS asp_quarter

FROM drug d
LEFT JOIN manufacturer m ON d.manufacturer_id = m.id
LEFT JOIN therapeutic_class tc ON d.therapeutic_class_id = tc.id
LEFT JOIN drug_category dc ON d.drug_category_id = dc.id

-- Latest contract pricing
LEFT JOIN LATERAL (
    SELECT contract_cost, effective_date
    FROM contract_pricing
    WHERE ndc = d.ndc
    ORDER BY effective_date DESC
    LIMIT 1
) cp ON TRUE

-- Latest AWP pricing
LEFT JOIN LATERAL (
    SELECT awp, effective_date
    FROM awp_pricing
    WHERE ndc = d.ndc
    ORDER BY effective_date DESC
    LIMIT 1
) ap ON TRUE

-- Latest NADAC pricing
LEFT JOIN LATERAL (
    SELECT nadac_price
    FROM nadac_pricing
    WHERE ndc = d.ndc
    ORDER BY effective_date DESC
    LIMIT 1
) np ON TRUE

-- Latest HCPCS crosswalk
LEFT JOIN LATERAL (
    SELECT hcpcs_code, bill_units_per_package
    FROM ndc_hcpcs_crosswalk
    WHERE ndc = d.ndc
    ORDER BY effective_date DESC
    LIMIT 1
) xw ON TRUE

-- Latest ASP payment limit
LEFT JOIN LATERAL (
    SELECT asp_true, payment_limit, effective_quarter
    FROM asp_payment_limit
    WHERE hcpcs_code = xw.hcpcs_code
    ORDER BY effective_date DESC
    LIMIT 1
) apl ON TRUE

-- IRA drug check (fuzzy match)
LEFT JOIN ira_drug ira ON UPPER(d.drug_name) LIKE '%' || UPPER(ira.drug_name) || '%'

-- Penny pricing status
LEFT JOIN LATERAL (
    SELECT is_penny_priced, inflation_penalty_pct, discount_340b_pct
    FROM penny_pricing_status
    WHERE ndc = d.ndc
    ORDER BY as_of_date DESC
    LIMIT 1
) pp ON TRUE;

-- Index for common queries
CREATE INDEX idx_mv_margin_drug_name ON mv_drug_margin_analysis(drug_name);
CREATE INDEX idx_mv_margin_ira ON mv_drug_margin_analysis(is_ira_drug);
CREATE INDEX idx_mv_margin_penny ON mv_drug_margin_analysis(is_penny_priced);
CREATE INDEX idx_mv_margin_best ON mv_drug_margin_analysis(best_margin DESC);

-- Refresh command (run periodically or after data loads)
-- REFRESH MATERIALIZED VIEW mv_drug_margin_analysis;
```

---

## Utility Functions

### NDC Normalization
```sql
CREATE OR REPLACE FUNCTION normalize_ndc(raw_ndc TEXT)
RETURNS CHAR(11) AS $$
BEGIN
    -- Remove dashes and spaces, pad to 11 digits
    RETURN LPAD(REGEXP_REPLACE(raw_ndc, '[-\s]', '', 'g'), 11, '0');
END;
$$ LANGUAGE plpgsql IMMUTABLE;
```

### Format NDC (5-4-2)
```sql
CREATE OR REPLACE FUNCTION format_ndc(ndc CHAR(11))
RETURNS VARCHAR(13) AS $$
BEGIN
    RETURN SUBSTRING(ndc, 1, 5) || '-' || SUBSTRING(ndc, 6, 4) || '-' || SUBSTRING(ndc, 10, 2);
END;
$$ LANGUAGE plpgsql IMMUTABLE;
```

---

## Primary Key & Uniqueness Considerations

### The NDC Uniqueness Problem

**Critical Finding:** NDC alone is NOT unique in the product catalog data.

| Metric | Value |
|--------|-------|
| Total rows in product_catalog | 34,229 |
| Unique NDCs | 30,212 |
| Duplicate NDCs | 4,017 (11.7%) |

The same NDC can appear multiple times with:
- Different **contract names** (PUBLIC HEALTH SERVICES, SPD PHS, etc.)
- Different **prices** (ranging from $0.01 to $31,788.25 for the same NDC)
- Different **effective dates**

### Real Data Examples

#### Example 1: HUMIRA (Unique NDCs)

HUMIRA is a **good example** where each NDC is unique - no duplicates:

| NDC | Description | Contract Cost |
|-----|-------------|---------------|
| 00074433902 | HUMIRA PEN SF 40MG/0.8 2 SPD | $5,550.00 |
| 00074432802 | HUMIRA SF 40MG/0.8ML 2 KIT SPD | $5,550.00 |
| 00074906802 | HUMIRA PEN SF 80MG/0.8 2 SPD | $5,550.00 |
| 00074028902 | HUMIRA SF PEDI 10MG/0.1 2 KIT SPD | $2,818.55 |
| 00074028802 | HUMIRA SF PEDI 20MG/0.2 2 KIT SPD | $2,818.55 |
| 00074433702 | HUMIRA PEN SF 40/0.4 2 CF SPD | $5,550.00 |
| 00074432902 | HUMIRA SF 40MG/0.4ML 2 KIT SPD | $5,550.00 |
| 00074055402 | HUMIRA PEDI SF 80MG/0.8 2 SPD | $5,550.00 |
| 00074055302 | HUMIRA PEDI SF 40MG/0.4 2 SPD | $2,775.00 |

**9 unique NDCs, 9 rows = 1:1 mapping (ideal)**

#### Example 2: ACTEMRA (Duplicate NDCs, Different Contracts)

ACTEMRA shows the **same NDC appearing with different contracts**:

| NDC | Description | Contract Name | Contract Cost |
|-----|-------------|---------------|---------------|
| 50242013501 | ACTEMRA VL 400MG/20ML 1 | Off-Contract | $1,404.01 |
| 50242013501 | ACTEMRA VL 400MG/20ML 1 | PUBLIC HEALTH SERVICES | $884.76 |
| 50242013401 | ACTEMRA VL 200MG/10ML 1 | Off-Contract | $702.01 |
| 50242013401 | ACTEMRA VL 200MG/10ML 1 | PUBLIC HEALTH SERVICES | $442.58 |
| 50242013601 | ACTEMRA VL 80MG/4ML 1 | Off-Contract | $280.81 |
| 50242013601 | ACTEMRA VL 80MG/4ML 1 | PUBLIC HEALTH SERVICES | $177.03 |

**3 unique NDCs, 6 rows = 1:2 mapping (contract-based)**

#### Example 3: KRYSTEXXA (Extreme Price Variance)

KRYSTEXXA shows the **most extreme price variance** for the same NDC:

| NDC | Description | Contract Name | Contract Cost |
|-----|-------------|---------------|---------------|
| 75987008010 | KRYSTEXXA VL 8MG/ML 2X1ML | Off-Contract | $31,788.25 |
| 75987008010 | KRYSTEXXA VL 8MG/ML 2X1ML | SPD PHS (ORPHAN/BILL TO PD) | $0.01 |

**Same NDC, price difference of $31,788.24** - this is the "penny pricing" pattern for orphan drugs through the SPD PHS contract.

### Primary Key Strategies

#### Option 1: Surrogate Key (Recommended)

```sql
CREATE TABLE contract_pricing (
    id SERIAL PRIMARY KEY,                    -- Surrogate key
    ndc CHAR(11) NOT NULL REFERENCES drug(ndc),
    contract_name VARCHAR(100) NOT NULL,
    contract_cost DECIMAL(12,4) NOT NULL,
    effective_date DATE NOT NULL,
    UNIQUE(ndc, contract_name, effective_date)  -- Business uniqueness
);
```

**Pros:**
- Simple, auto-incrementing
- Joins are fast
- Stable foreign key references

**Cons:**
- No business meaning
- Requires separate uniqueness constraint

#### Option 2: Composite Business Key

```sql
CREATE TABLE contract_pricing (
    ndc CHAR(11) NOT NULL REFERENCES drug(ndc),
    contract_name VARCHAR(100) NOT NULL,
    effective_date DATE NOT NULL,
    contract_cost DECIMAL(12,4) NOT NULL,
    PRIMARY KEY (ndc, contract_name, effective_date)
);
```

**Pros:**
- Business-meaningful key
- Enforces uniqueness naturally
- Self-documenting

**Cons:**
- Larger composite keys in joins
- Must include all key columns in foreign keys

#### Option 3: Deduplicated Drug Table + Pricing History

```sql
-- Core drug table (NDC is unique)
CREATE TABLE drug (
    ndc CHAR(11) PRIMARY KEY,
    drug_name VARCHAR(255) NOT NULL,
    -- ... other drug attributes
);

-- Contract pricing (many rows per NDC)
CREATE TABLE contract_pricing (
    id SERIAL PRIMARY KEY,
    ndc CHAR(11) REFERENCES drug(ndc),
    contract_type VARCHAR(50),  -- 'OFF_CONTRACT', 'PHS', 'SPD_PHS', etc.
    contract_cost DECIMAL(12,4),
    effective_date DATE,
    end_date DATE,
    UNIQUE(ndc, contract_type, effective_date)
);
```

**Recommendation:** Use **Option 3** (this document's approach) - separate `drug` table with unique NDC, and `contract_pricing` table with surrogate key plus composite uniqueness constraint.

---

## Design Considerations

### Questions to Address Before Implementation

1. **Historical tracking**: Do you need to query historical margins (e.g., "What was HUMIRA's margin in Q3 2024")?
   - If yes, the time-series pricing tables with `effective_date`/`end_date` are essential
   - Consider SCD Type 2 for full audit trail

2. **Multi-entity**: Will multiple health systems use this?
   - Add `facility_id` or `entity_id` to `contract_pricing` table
   - Consider row-level security

3. **Audit requirements**: Do you need full change tracking?
   - Add audit trigger tables
   - Consider CDC (Change Data Capture)

4. **Update frequency**:
   - NADAC: Updated weekly by CMS
   - ASP: Updated quarterly by CMS
   - Contract pricing: Updated as vendor contracts change
   - Schedule materialized view refresh accordingly

5. **Database choice**:
   - PostgreSQL recommended (supports generated columns, lateral joins, materialized views)
   - Could adapt for MySQL, SQL Server, or cloud (BigQuery, Snowflake)

---

## ETL Process Overview

```
1. Load Raw Files
   ├── product_catalog.xlsx → staging_catalog
   ├── asp_pricing.csv → staging_asp
   ├── asp_crosswalk.csv → staging_crosswalk
   └── ... other files

2. Normalize & Validate
   ├── Normalize NDCs (11-digit)
   ├── Map column names
   ├── Validate data types
   └── Log validation errors

3. Upsert to 3NF Tables
   ├── manufacturer (dedupe by name)
   ├── drug (upsert by NDC)
   ├── contract_pricing (insert new effective dates)
   ├── awp_pricing (insert new effective dates)
   └── ... other tables

4. Refresh Materialized View
   └── REFRESH MATERIALIZED VIEW mv_drug_margin_analysis;

5. Validate Results
   ├── Row counts match expectations
   ├── No orphan NDCs
   └── Margin calculations spot-check
```

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-01-25 | Claude | Initial design based on current Streamlit app data sources |
| 1.1 | 2025-01-25 | Claude | Added Primary Key & Uniqueness section with HUMIRA, ACTEMRA, KRYSTEXXA examples |
