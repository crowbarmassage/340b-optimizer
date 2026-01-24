# PRICE_UNITS_REFERENCE.md — Price Field Unit Documentation

> **Version:** 1.0
> **Last Updated:** January 24, 2026
> **Status:** UNDER REVIEW - Unit consistency needs verification

---

## Overview

This document tracks all price-related fields used in the 340B Optimizer, their source files, assumed units, and package context. The **11-digit NDC** is the primary key for matching prices across data sources.

**Key Question:** Are we comparing apples to apples when calculating margins?

---

## Price Fields Summary

| Price Field | Source File | Assumed Unit | Package Context | Used In | Status |
|-------------|-------------|--------------|-----------------|---------|--------|
| Unit Price (Current Catalog) | product_catalog.xlsx | Per package? | NDC package | Contract Cost | ⚠️ VERIFY |
| Medispan AWP | product_catalog.xlsx | Per package? | NDC package | Retail margin | ⚠️ VERIFY |
| Payment Limit | asp_pricing.csv | Per billing unit | HCPCS dosage | ASP calculation | ⚠️ VERIFY |
| NADAC (last_price) | ndc_nadac_master_statistics.csv | Per unit? | pricing_unit column | Reference | ⚠️ VERIFY |
| Wholesaler Retail | wholesaler_catalog.xlsx | Per unit? | Unknown | Validation | ⚠️ VERIFY |

---

## Detailed Price Field Documentation

### 1. Unit Price (Current Catalog)
- **Source:** `product_catalog.xlsx` → Column 15
- **Used As:** 340B Acquisition Cost (Contract Cost)
- **Assumed Unit:** Per NDC package (?)
- **Package Context:**
  - `Package Size` (column 6): Size of individual unit
  - `Package Qty` (column 7): Number of units per package
- **Sample Values:** $4.75, $257.89, $246.82
- **Questions:**
  - [ ] Is this per package or per unit within the package?
  - [ ] How does Package Qty affect interpretation?

### 2. Medispan AWP
- **Source:** `product_catalog.xlsx` → Column 12
- **Used As:** Retail reimbursement basis (AWP × multiplier)
- **Assumed Unit:** Per NDC package (?)
- **Package Context:** Same as above
- **Sample Values:** $165.16, $5.51
- **Questions:**
  - [ ] Confirm AWP is per package, not per unit
  - [ ] Should match Package Size × Package Qty interpretation

### 3. Payment Limit (ASP × 1.06)
- **Source:** `asp_pricing.csv` → Column 4
- **Used As:** Medicare reimbursement; back-calculate true ASP
- **Assumed Unit:** Per HCPCS billing unit
- **Package Context:**
  - `HCPCS Code Dosage` (column 3): Billing unit definition (e.g., "5 mcg")
  - Crosswalk provides `BILLUNITSPKG` for NDC → billing unit conversion
- **Sample Values:** $134.19, $279.85, $222.25
- **Calculation:** `True ASP = Payment Limit / 1.06`
- **Questions:**
  - [ ] Verify billing unit definition per HCPCS
  - [ ] Confirm BILLUNITSPKG correctly converts package to billing units

### 4. NADAC Price (last_price)
- **Source:** `ndc_nadac_master_statistics.csv` → Column 15
- **Used As:** Reference price (market acquisition cost)
- **Assumed Unit:** Per pricing unit (see `pricing_unit` column)
- **Package Context:**
  - `pricing_unit` (column 6): Unit of measure (e.g., "EA", "ML", "GM")
- **Sample Values:** $478.15, $713.79
- **Questions:**
  - [ ] What is the pricing_unit for each NDC?
  - [ ] How to convert to per-package for comparison?
  - [ ] Is this per unit or per package?

### 5. Wholesaler Retail Price
- **Source:** `wholesaler_catalog.xlsx` → Column 13
- **Column Name:** `Product Catalog Unit Price (Current Retail) Average`
- **Used As:** Retail price validation
- **Assumed Unit:** Per unit (?)
- **Package Context:** Unknown
- **Sample Values:** $7.68, $6.40, $6.19
- **Questions:**
  - [ ] What unit does "Unit Price" refer to?
  - [ ] How to match to NDC package size?

---

## NDC as Primary Key

The **11-digit NDC** uniquely identifies a drug product at the package level:

```
NDC Format: LABELER-PRODUCT-PACKAGE
            5 digits - 4 digits - 2 digits
Example:    00074-4339-02

- Labeler (5): Manufacturer ID
- Product (4): Drug/strength/form
- Package (2): Package size/type
```

**Important:** The last 2 digits specify the package configuration. Two NDCs that differ only in the package code represent the same drug in different package sizes.

### NDC Matching Considerations

| Data Source | NDC Column | Format | Normalization Needed |
|-------------|------------|--------|---------------------|
| Product Catalog | NDC | 11-digit string | Preserve leading zeros |
| ASP Crosswalk | NDC2 | With dashes (xxxxx-xxxx-xx) | Remove dashes, normalize |
| NOC Crosswalk | NDC or ALTERNATE ID | With dashes | Remove dashes, normalize |
| NADAC | ndc | 11-digit string | Verify format |
| Wholesaler Catalog | Product Catalog NDC | Unknown | Verify format |

---

## Unit Conversion Factors

### From ASP Crosswalk

| Column | Description | Example |
|--------|-------------|---------|
| PKG SIZE | Amount in one item | 0.5 (mL per vial) |
| PKG QTY | Items per NDC | 4 (vials per shelf pack) |
| BILLUNITS | Billing units per item | 20 (if 100mcg/item ÷ 5mcg/billing unit) |
| BILLUNITSPKG | Billing units per NDC | 80 (BILLUNITS × PKG QTY) |

### Conversion Example

```
Drug: 100mcg/0.5mL vial, 4 vials per NDC
HCPCS Dosage: 5 mcg

PKG SIZE = 0.5 (mL)
PKG QTY = 4 (vials)
BILLUNITS = 100mcg ÷ 5mcg = 20 per vial
BILLUNITSPKG = 20 × 4 = 80 billing units per NDC

If Payment Limit = $10.00 per billing unit
Then: Revenue per NDC = $10.00 × 80 = $800.00
```

---

## Margin Formula Unit Requirements

### Retail Margin
```
Margin = (AWP × Multiplier × Capture Rate) - Contract Cost

Required: AWP and Contract Cost must be in SAME units (per package)
```

### Medicare Margin
```
Margin = (ASP × 1.06 × Bill Units per Package) - Contract Cost

Required:
- ASP in per-billing-unit
- Bill Units converts to per-package
- Contract Cost in per-package
```

### Commercial Margin
```
Margin = (ASP × 1.15 × Bill Units per Package) - Contract Cost

Same requirements as Medicare
```

---

## Verification Checklist

### Phase 1: Document Current Assumptions
- [x] List all price fields and sources
- [x] Document assumed units
- [x] Identify package context columns
- [ ] Sample 5-10 drugs and manually trace units

### Phase 2: Verify Unit Consistency
- [ ] Confirm Product Catalog prices are per-package
- [ ] Confirm NADAC pricing_unit interpretation
- [ ] Verify BILLUNITSPKG calculation in crosswalk
- [ ] Cross-check AWP between Product Catalog and Wholesaler Catalog

### Phase 3: Implement Corrections
- [ ] Add unit normalization if needed
- [ ] Update margin calculations if units differ
- [ ] Add unit indicators to Price Reference display

---

## Test Cases for Verification

### Test Case 1: High-Value Biologic (e.g., HUMIRA)
```
NDC: 00074-4339-02
Expected: Trace all prices for this NDC
- Product Catalog: AWP, Contract Cost, Package Size, Package Qty
- ASP Crosswalk: HCPCS, BILLUNITSPKG
- ASP Pricing: Payment Limit
- NADAC: last_price, pricing_unit
```

### Test Case 2: Generic Oral (e.g., Metformin)
```
NDC: TBD
Expected: May not have ASP/HCPCS mapping
- Product Catalog: AWP, Contract Cost
- NADAC: last_price
```

### Test Case 3: Unit Dose vs Bulk Package
```
Compare two NDCs for same drug with different package codes
Expected: Prices should scale proportionally
```

---

## Notes

- This document is a living reference that should be updated as unit consistency is verified
- The warning banner in the app Price Reference section alerts users to this ongoing verification
- 11-digit NDC is the safest join key as it specifies exact package configuration

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-24 | Initial documentation of price fields and units |
