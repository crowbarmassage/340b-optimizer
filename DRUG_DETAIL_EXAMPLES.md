# Drug Detail Schema - Complete Examples

This document provides two fully detailed examples showing every field in the drug detail schema and where each value comes from in the source data.

---

## Example 1: Injectable with Medical Pathway

### IRON SUCROSE SF 20MG/ML 10X5ML

An injectable generic drug with full HCPCS/ASP mapping, demonstrating concentration parsing and medical billing pathways.

---

#### Source Data Extracts

**From: `product_catalog.xlsx`**
```
NDC: 67457063810
Product Description: IRON SUCROSE SF 20MG/ML 10X5ML
Trade Name: IRON SUCROSE
Generic Name: FE SUCROSE COMPLEX
Form: SDPF
Package Size: 5.0
Package Qty: 10
Manufacturer: MYLAN INSTITUTIONAL LLC
Medispan AWP: $704.82
Unit Price (Current Catalog): $162.22
```

**From: `asp_crosswalk.csv`**
```
_2025_CODE: J1756
Short Description: Iron sucrose injection
NDC2: 67457-0638-10
Drug Name: Iron Sucrose
HCPCS dosage: 1 MG
PKG SIZE: 5
PKG QTY: 10
BILLUNITS: 100
BILLUNITSPKG: 1000
```

**From: `asp_pricing.csv`**
```
HCPCS Code: J1756
Short Description: Iron sucrose injection
HCPCS Code Dosage: 1 MG
Payment Limit: $0.229
```

**From: `Ravenswood_AWP_Reimbursement_Matrix.xlsx`**
```
Drug Category: GENERIC (based on name classification)
AWP Multiplier: 0.20 (Generic)
```

---

#### Complete Field Mapping

### Section 1: Drug Identity (9 fields)

| Field | Value | Source | Column/Logic |
|-------|-------|--------|--------------|
| `ndc_raw` | `67457063810` | product_catalog.xlsx | NDC |
| `ndc_11` | `67457063810` | Derived | `normalize_ndc(ndc_raw)` - pad to 11 digits |
| `ndc_formatted` | `67457-0638-10` | Derived | `substr(1,5)-substr(6,4)-substr(10,2)` |
| `ndc_10` | `6745706381` | Derived | Alternative 10-digit format |
| `drug_name` | `IRON SUCROSE` | product_catalog.xlsx | Trade Name |
| `generic_name` | `FE SUCROSE COMPLEX` | product_catalog.xlsx | Generic Name |
| `product_description` | `IRON SUCROSE SF 20MG/ML 10X5ML` | product_catalog.xlsx | Product Description |
| `manufacturer_name` | `MYLAN INSTITUTIONAL LLC` | product_catalog.xlsx | Manufacturer |
| `manufacturer_labeler_code` | `67457` | Derived | First 5 digits of NDC |

### Section 2: Drug Classification (7 fields)

| Field | Value | Source | Column/Logic |
|-------|-------|--------|--------------|
| `drug_category` | `GENERIC` | Ravenswood / Derived | `classify_drug_category("IRON SUCROSE")` - not in SPECIALTY/BRAND lists, matches GENERIC pattern |
| `is_brand` | `FALSE` | Derived | `drug_category != 'GENERIC'` |
| `is_generic` | `TRUE` | Derived | `drug_category == 'GENERIC'` |
| `is_specialty` | `FALSE` | Derived | `drug_category == 'SPECIALTY'` |
| `is_biologic` | `FALSE` | biologics_grid | Not found in biologics list |
| `therapeutic_class` | `null` | product_catalog.xlsx | Not provided in source |
| `therapeutic_class_code` | `null` | product_catalog.xlsx | Not provided in source |

### Section 3: Dosage Form & Route (10 fields)

| Field | Value | Source | Column/Logic |
|-------|-------|--------|--------------|
| `form_code` | `SDPF` | product_catalog.xlsx | Form |
| `dosage_form` | `SINGLE DOSE PREFILLED` | Derived | `form_code_mapping['SDPF']` |
| `dosage_form_category` | `INJECTABLE` | Derived | `form_code_mapping['SDPF'].category` |
| `route_of_administration` | `INJECTABLE` | Derived | `form_code_mapping['SDPF'].route` |
| `is_oral` | `FALSE` | Derived | `route == 'ORAL'` |
| `is_injectable` | `TRUE` | Derived | `route == 'INJECTABLE'` |
| `is_topical` | `FALSE` | Derived | `route == 'TOPICAL'` |
| `is_ophthalmic` | `FALSE` | Derived | `route == 'OPHTHALMIC'` |
| `is_inhalation` | `FALSE` | Derived | `route == 'INHALATION'` |
| `is_transdermal` | `FALSE` | Derived | `route == 'TRANSDERMAL'` |

### Section 4: Strength & Dosage (8 fields)

| Field | Value | Source | Column/Logic |
|-------|-------|--------|--------------|
| `strength_raw` | `20MG/ML` | Parsed from description | regex: `(\d+)(MG|MCG)/` |
| `strength_value_1` | `20.0` | Parsed | `20` from `20MG/ML` |
| `strength_unit_1` | `MG` | Parsed | `MG` from `20MG/ML` |
| `strength_value_2` | `null` | Parsed | No secondary strength (not a combo) |
| `strength_unit_2` | `null` | Parsed | N/A |
| `is_combination_drug` | `FALSE` | Derived | No `-` pattern in strength |
| `strength_per_unit` | `20.0` | Calculated | `strength_value_1` (per ML basis) |
| `strength_display` | `20 MG/ML` | Derived | Formatted display |

### Section 5: Concentration (7 fields)

| Field | Value | Source | Column/Logic |
|-------|-------|--------|--------------|
| `concentration_raw` | `20MG/ML` | Parsed from description | regex: `(\d+)(MG)/(\d*)(ML)` |
| `concentration_numerator` | `20.0` | Parsed | `20` from `20MG/ML` |
| `concentration_numerator_unit` | `MG` | Parsed | `MG` |
| `concentration_denominator` | `1.0` | Parsed | Implied `1` when no number before ML |
| `concentration_denominator_unit` | `ML` | Parsed | `ML` |
| `concentration_per_ml` | `20.0` | Calculated | `20 / 1 = 20 MG/ML` |
| `has_concentration` | `TRUE` | Derived | Concentration pattern found |

### Section 6: Volume & Package (10 fields)

| Field | Value | Source | Column/Logic |
|-------|-------|--------|--------------|
| `package_size_raw` | `5.0` | product_catalog.xlsx | Package Size |
| `package_qty_raw` | `10` | product_catalog.xlsx | Package Qty |
| `total_volume_value` | `50.0` | Calculated | `5.0 × 10 = 50 ML` |
| `total_volume_unit` | `ML` | Derived | From concentration unit |
| `package_inner_count` | `10` | Parsed from description | `10` from `10X5ML` pattern |
| `package_inner_size` | `5.0` | Parsed from description | `5` from `10X5ML` pattern |
| `package_inner_unit` | `ML` | Parsed from description | `ML` from `10X5ML` pattern |
| `total_units_per_package` | `10` | Calculated | 10 vials per package |
| `total_doses_per_package` | `10` | Calculated | 10 single-dose vials |
| `package_description` | `10 × 5ML single-dose vials` | Derived | Human-readable format |

### Section 7: Drug Flags (14 fields)

| Field | Value | Source | Column/Logic |
|-------|-------|--------|--------------|
| `dea_schedule` | `null` | Parsed from description | No C2/C3/C4/C5 pattern found |
| `is_controlled_substance` | `FALSE` | Derived | `dea_schedule IS NULL` |
| `is_schedule_ii` | `FALSE` | Derived | `dea_schedule != 'C2'` |
| `is_extended_release` | `FALSE` | Parsed | No ER/XR/XL/CR/SR/LA pattern |
| `is_delayed_release` | `FALSE` | Parsed | No DR/EC pattern |
| `is_immediate_release` | `TRUE` | Derived | Not ER or DR |
| `is_unit_dose` | `FALSE` | Parsed | No UD pattern |
| `is_preservative_free` | `FALSE` | Parsed | No PF pattern (Note: SF = Single Fill, not preservative free) |
| `is_latex_free` | `FALSE` | Parsed | No LF pattern |
| `is_specialty_pharmacy` | `FALSE` | Parsed | No SPD pattern |
| `is_pen_device` | `FALSE` | Parsed | No PPN/PEN pattern |
| `is_blister_pack` | `FALSE` | Parsed | No BPK pattern |
| `is_tip_lok` | `FALSE` | Parsed | No TPLK pattern |
| `release_mechanism` | `IR` | Derived | Immediate release (default for injectables) |

### Section 8: Acquisition Pricing (5 fields)

| Field | Value | Source | Column/Logic |
|-------|-------|--------|--------------|
| `contract_cost` | `162.22` | product_catalog.xlsx | Unit Price (Current Catalog) |
| `contract_cost_per_unit` | `16.222` | Calculated | `162.22 / 10 vials = $16.22/vial` |
| `contract_effective_date` | `2025-01-01` | Metadata | File load date (assumed) |
| `contract_source` | `product_catalog.xlsx` | Metadata | Source file name |
| `contract_vendor` | `340B PRIME-VENDOR-PROGRAM` | product_catalog.xlsx | Contract Name (if available) |

### Section 9: AWP Pricing (5 fields)

| Field | Value | Source | Column/Logic |
|-------|-------|--------|--------------|
| `awp` | `704.82` | product_catalog.xlsx | Medispan AWP |
| `awp_per_unit` | `70.482` | Calculated | `704.82 / 10 = $70.48/vial` |
| `awp_effective_date` | `2025-01-01` | Metadata | File load date (assumed) |
| `awp_source` | `MEDISPAN` | Metadata | Column name indicates source |
| `awp_unit_price` | `70.482` | Calculated | Per-vial price |

### Section 10: NADAC Pricing (7 fields)

| Field | Value | Source | Column/Logic |
|-------|-------|--------|--------------|
| `nadac_price` | `null` | nadac_statistics.csv | NDC not found in NADAC file (branded NDCs only) |
| `nadac_per_unit` | `null` | Calculated | N/A |
| `nadac_effective_date` | `null` | nadac_statistics.csv | N/A |
| `nadac_as_of_date` | `null` | nadac_statistics.csv | N/A |
| `nadac_pricing_unit` | `null` | nadac_statistics.csv | N/A |
| `nadac_explanation_code` | `null` | nadac_statistics.csv | N/A |
| `nadac_classification` | `null` | nadac_statistics.csv | N/A |

### Section 11: ASP Pricing (7 fields)

| Field | Value | Source | Column/Logic |
|-------|-------|--------|--------------|
| `asp_payment_limit` | `0.229` | asp_pricing.csv | Payment Limit (per 1 MG) |
| `asp_true` | `0.216` | Calculated | `0.229 / 1.06 = $0.216 per MG` |
| `asp_per_billing_unit` | `0.216` | Calculated | `asp_true` (1 MG = 1 billing unit) |
| `asp_effective_quarter` | `2025Q1` | asp_pricing.csv | Derived from file name/date |
| `asp_effective_date` | `2025-01-01` | Derived | Quarter start date |
| `asp_end_date` | `2025-03-31` | Derived | Quarter end date |
| `asp_source_file` | `asp_pricing.csv` | Metadata | Source file |

### Section 12: HCPCS/Billing (11 fields)

| Field | Value | Source | Column/Logic |
|-------|-------|--------|--------------|
| `hcpcs_code` | `J1756` | asp_crosswalk.csv | _2025_CODE |
| `hcpcs_description` | `Iron sucrose injection` | asp_crosswalk.csv | Short Description |
| `hcpcs_short_description` | `Iron sucrose injection` | asp_pricing.csv | Short Description |
| `bill_units_per_package` | `1000` | asp_crosswalk.csv | BILLUNITSPKG |
| `hcpcs_dosage_descriptor` | `1 MG` | asp_crosswalk.csv | HCPCS dosage |
| `has_medical_path` | `TRUE` | Derived | `hcpcs_code IS NOT NULL AND asp_payment_limit IS NOT NULL` |
| `is_noc` | `FALSE` | noc_crosswalk.csv | Not in NOC file |
| `noc_hcpcs_code` | `null` | noc_crosswalk.csv | N/A |
| `noc_payment_limit` | `null` | noc_pricing.csv | N/A |
| `crosswalk_effective_quarter` | `2025Q1` | asp_crosswalk.csv | Derived from column name (_2025_CODE) |

### Section 13: Reimbursement Rates (9 fields)

| Field | Value | Source | Column/Logic |
|-------|-------|--------|--------------|
| `awp_factor_brand` | `0.85` | Constant | Brand rate |
| `awp_factor_generic` | `0.20` | Constant | Generic rate |
| `awp_factor_applicable` | `0.20` | Derived | `is_generic ? 0.20 : 0.85` → `0.20` |
| `medicare_part_d_multiplier` | `0.20` | Ravenswood | Generic Medicare rate |
| `commercial_multiplier` | `0.15` | Ravenswood | Generic Commercial rate |
| `medicaid_mco_multiplier` | `0.15` | Ravenswood | Generic Medicaid rate |
| `asp_medicaid_multiplier` | `1.04` | Constant | ASP + 4% |
| `asp_medicare_multiplier` | `1.06` | Constant | ASP + 6% |
| `asp_commercial_multiplier` | `1.15` | Configurable | ASP + 15% (default) |

### Section 14: Wholesale/Retail Pricing (5 fields)

| Field | Value | Source | Column/Logic |
|-------|-------|--------|--------------|
| `wholesaler_retail_price` | `null` | wholesaler_catalog.xlsx | NDC not found |
| `wholesaler_name` | `null` | wholesaler_catalog.xlsx | N/A |
| `wholesaler_as_of_date` | `null` | wholesaler_catalog.xlsx | N/A |
| `retail_price_variance_pct` | `null` | Calculated | N/A |
| `retail_confidence` | `null` | Derived | N/A |

### Section 15: Risk Flags (11 fields)

| Field | Value | Source | Column/Logic |
|-------|-------|--------|--------------|
| `is_ira_drug` | `FALSE` | ira_drug_list.csv | "IRON SUCROSE" not in IRA list |
| `ira_year` | `null` | ira_drug_list.csv | N/A |
| `ira_max_fair_price` | `null` | ira_drug_list.csv | N/A |
| `ira_description` | `null` | ira_drug_list.csv | N/A |
| `is_penny_priced` | `FALSE` | nadac_statistics.csv | Not in NADAC; assumed not penny-priced |
| `penny_override_cost` | `null` | Derived | N/A |
| `discount_340b_pct` | `null` | nadac_statistics.csv | N/A |
| `has_inflation_penalty` | `FALSE` | nadac_statistics.csv | N/A |
| `inflation_penalty_pct` | `null` | nadac_statistics.csv | N/A |
| `risk_level` | `LOW` | Derived | No IRA, no penny pricing |
| `risk_factors` | `[]` | Derived | Empty array |

### Section 16: Biologic/Loading Dose (10 fields)

| Field | Value | Source | Column/Logic |
|-------|-------|--------|--------------|
| `has_loading_dose` | `FALSE` | biologics_grid.xlsx | Not a biologic |
| `loading_dose_count` | `null` | biologics_grid.xlsx | N/A |
| `year_1_fills` | `null` | biologics_grid.xlsx | N/A |
| `year_2_plus_fills` | `null` | biologics_grid.xlsx | N/A |
| `adjusted_year_1_fills` | `null` | biologics_grid.xlsx | N/A |
| `adjusted_year_2_fills` | `null` | biologics_grid.xlsx | N/A |
| `compliance_rate` | `null` | biologics_grid.xlsx | N/A |
| `indication` | `null` | biologics_grid.xlsx | N/A |
| `loading_dose_delta_pct` | `null` | Calculated | N/A |

### Section 17: Calculated Margins (10 fields)

**Calculation Inputs:**
- Contract Cost: $162.22 (per package)
- AWP: $704.82 (per package)
- AWP Factor: 0.20 (Generic)
- ASP: $0.216 per MG (true ASP)
- Bill Units: 1000 MG per package

| Field | Value | Source | Calculation |
|-------|-------|--------|-------------|
| `margin_pharmacy_medicaid` | `null` | Calculated | NADAC not available |
| `margin_pharmacy_medicaid_formula` | `null` | Derived | N/A |
| `margin_pharmacy_medicare_commercial` | `-$21.26` | Calculated | `(704.82 × 0.20) - 162.22 = 140.96 - 162.22 = -21.26` |
| `margin_pharmacy_medicare_commercial_formula` | `AWP × 0.20 - Contract = 704.82 × 0.20 - 162.22` | Derived | Formula breakdown |
| `margin_medical_medicaid` | `$62.42` | Calculated | `(0.216 × 1.04 × 1000) - 162.22 = 224.64 - 162.22 = 62.42` |
| `margin_medical_medicaid_formula` | `ASP × 1.04 × Units - Contract = 0.216 × 1.04 × 1000 - 162.22` | Derived | Formula |
| `margin_medical_medicare` | `$66.78` | Calculated | `(0.216 × 1.06 × 1000) - 162.22 = 229.00 - 162.22 = 66.78` |
| `margin_medical_medicare_formula` | `ASP × 1.06 × Units - Contract = 0.216 × 1.06 × 1000 - 162.22` | Derived | Formula |
| `margin_medical_commercial` | `$86.18` | Calculated | `(0.216 × 1.15 × 1000) - 162.22 = 248.40 - 162.22 = 86.18` |
| `margin_medical_commercial_formula` | `ASP × 1.15 × Units - Contract = 0.216 × 1.15 × 1000 - 162.22` | Derived | Formula |

### Section 18: Margin Analysis Summary (10 fields)

| Field | Value | Source | Calculation |
|-------|-------|--------|-------------|
| `best_margin` | `$86.18` | Derived | `MAX(all margins)` |
| `best_pathway` | `MEDICAL_COMMERCIAL` | Derived | Pathway with best margin |
| `second_best_margin` | `$66.78` | Derived | Second highest |
| `second_best_pathway` | `MEDICAL_MEDICARE` | Derived | Second best pathway |
| `margin_delta` | `$19.40` | Calculated | `86.18 - 66.78 = 19.40` |
| `margin_delta_pct` | `29.1%` | Calculated | `19.40 / 66.78 × 100` |
| `recommendation` | `COMMERCIAL_MEDICAL` | Derived | Best pathway |
| `recommendation_confidence` | `HIGH` | Derived | Clear winner, positive margins |
| `all_margins_positive` | `FALSE` | Derived | Pharmacy margin is negative |
| `has_negative_margin` | `TRUE` | Derived | Pharmacy margin < 0 |

### Section 19-22: Additional Sections

*Capture rate sensitivity, revenue projections, data quality, and timestamps follow similar patterns with values derived from the above calculations.*

---

## Example 2: Oral Controlled Substance (Retail Only)

### HYDROCODONE/ACETAMINOPHEN 10-325MG 500 C2

An oral generic combination controlled substance with no medical pathway, demonstrating combo strength parsing and DEA schedule flags.

---

#### Source Data Extracts

**From: `product_catalog.xlsx`**
```
NDC: 71930002152
Product Description: HYDROCOD/APAP TB 10-325MG 500  C2
Trade Name: HYDROCODONE/ACETAMINOPHEN
Generic Name: HYDROCOD/ACETAMIN
Form: TABS
Package Size: 500.0
Package Qty: 1
Manufacturer: EYWA PHARM CS NCB
Medispan AWP: $228.00
Unit Price (Current Catalog): $9.87
```

**From: `asp_crosswalk.csv`**
```
(NO MATCH - Oral drugs not in ASP crosswalk)
```

**From: `Ravenswood_AWP_Reimbursement_Matrix.xlsx`**
```
Drug Category: GENERIC (based on name classification)
AWP Multiplier: 0.20 (Generic)
```

---

#### Complete Field Mapping

### Section 1: Drug Identity (9 fields)

| Field | Value | Source | Column/Logic |
|-------|-------|--------|--------------|
| `ndc_raw` | `71930002152` | product_catalog.xlsx | NDC |
| `ndc_11` | `71930002152` | Derived | Already 11 digits |
| `ndc_formatted` | `71930-0021-52` | Derived | 5-4-2 format |
| `ndc_10` | `7193000215` | Derived | 10-digit format |
| `drug_name` | `HYDROCODONE/ACETAMINOPHEN` | product_catalog.xlsx | Trade Name |
| `generic_name` | `HYDROCOD/ACETAMIN` | product_catalog.xlsx | Generic Name |
| `product_description` | `HYDROCOD/APAP TB 10-325MG 500  C2` | product_catalog.xlsx | Product Description |
| `manufacturer_name` | `EYWA PHARM CS NCB` | product_catalog.xlsx | Manufacturer |
| `manufacturer_labeler_code` | `71930` | Derived | First 5 digits of NDC |

### Section 2: Drug Classification (7 fields)

| Field | Value | Source | Column/Logic |
|-------|-------|--------|--------------|
| `drug_category` | `GENERIC` | Ravenswood / Derived | Name not in SPECIALTY/BRAND lists |
| `is_brand` | `FALSE` | Derived | `drug_category != 'GENERIC'` |
| `is_generic` | `TRUE` | Derived | `drug_category == 'GENERIC'` |
| `is_specialty` | `FALSE` | Derived | Not specialty |
| `is_biologic` | `FALSE` | biologics_grid | Oral tablet, not biologic |
| `therapeutic_class` | `ANALGESIC` | product_catalog.xlsx | Inferred from drug name |
| `therapeutic_class_code` | `null` | product_catalog.xlsx | Not provided |

### Section 3: Dosage Form & Route (10 fields)

| Field | Value | Source | Column/Logic |
|-------|-------|--------|--------------|
| `form_code` | `TABS` | product_catalog.xlsx | Form |
| `dosage_form` | `TABLET` | Derived | `form_code_mapping['TABS']` |
| `dosage_form_category` | `SOLID` | Derived | Tablets are solid |
| `route_of_administration` | `ORAL` | Derived | `form_code_mapping['TABS'].route` |
| `is_oral` | `TRUE` | Derived | `route == 'ORAL'` |
| `is_injectable` | `FALSE` | Derived | Not injectable |
| `is_topical` | `FALSE` | Derived | Not topical |
| `is_ophthalmic` | `FALSE` | Derived | Not ophthalmic |
| `is_inhalation` | `FALSE` | Derived | Not inhaled |
| `is_transdermal` | `FALSE` | Derived | Not transdermal |

### Section 4: Strength & Dosage (8 fields)

| Field | Value | Source | Column/Logic |
|-------|-------|--------|--------------|
| `strength_raw` | `10-325MG` | Parsed from description | regex: `(\d+)-(\d+)(MG)` |
| `strength_value_1` | `10.0` | Parsed | Hydrocodone: `10` from `10-325MG` |
| `strength_unit_1` | `MG` | Parsed | `MG` |
| `strength_value_2` | `325.0` | Parsed | Acetaminophen: `325` from `10-325MG` |
| `strength_unit_2` | `MG` | Parsed | `MG` (same unit) |
| `is_combination_drug` | `TRUE` | Derived | `-` pattern found between strengths |
| `strength_per_unit` | `10.0` | Calculated | Primary ingredient per tablet |
| `strength_display` | `10/325 MG` | Derived | Formatted display |

### Section 5: Concentration (7 fields)

| Field | Value | Source | Column/Logic |
|-------|-------|--------|--------------|
| `concentration_raw` | `null` | Parsed | No concentration pattern (solid dosage form) |
| `concentration_numerator` | `null` | N/A | Not applicable to tablets |
| `concentration_numerator_unit` | `null` | N/A | N/A |
| `concentration_denominator` | `null` | N/A | N/A |
| `concentration_denominator_unit` | `null` | N/A | N/A |
| `concentration_per_ml` | `null` | N/A | Not a liquid |
| `has_concentration` | `FALSE` | Derived | No concentration pattern |

### Section 6: Volume & Package (10 fields)

| Field | Value | Source | Column/Logic |
|-------|-------|--------|--------------|
| `package_size_raw` | `500.0` | product_catalog.xlsx | Package Size |
| `package_qty_raw` | `1` | product_catalog.xlsx | Package Qty |
| `total_volume_value` | `null` | N/A | Not a liquid |
| `total_volume_unit` | `null` | N/A | N/A |
| `package_inner_count` | `null` | Parsed | No `XxY` pattern in description |
| `package_inner_size` | `null` | Parsed | N/A |
| `package_inner_unit` | `null` | Parsed | N/A |
| `total_units_per_package` | `500` | Calculated | 500 tablets per bottle |
| `total_doses_per_package` | `500` | Calculated | 500 doses (1 tablet = 1 dose) |
| `package_description` | `500 tablets` | Derived | Human-readable |

### Section 7: Drug Flags (14 fields)

| Field | Value | Source | Column/Logic |
|-------|-------|--------|--------------|
| `dea_schedule` | `C2` | Parsed from description | regex: `\b(C[2-5])\b` → `C2` |
| `is_controlled_substance` | `TRUE` | Derived | `dea_schedule IS NOT NULL` |
| `is_schedule_ii` | `TRUE` | Derived | `dea_schedule == 'C2'` |
| `is_extended_release` | `FALSE` | Parsed | No ER/XR pattern |
| `is_delayed_release` | `FALSE` | Parsed | No DR/EC pattern |
| `is_immediate_release` | `TRUE` | Derived | Not ER or DR |
| `is_unit_dose` | `FALSE` | Parsed | No UD pattern |
| `is_preservative_free` | `FALSE` | Parsed | N/A for oral solids |
| `is_latex_free` | `FALSE` | Parsed | N/A for oral solids |
| `is_specialty_pharmacy` | `FALSE` | Parsed | No SPD pattern |
| `is_pen_device` | `FALSE` | Parsed | Not a pen |
| `is_blister_pack` | `FALSE` | Parsed | No BPK pattern (500 count = bottle) |
| `is_tip_lok` | `FALSE` | Parsed | N/A |
| `release_mechanism` | `IR` | Derived | Immediate release |

### Section 8: Acquisition Pricing (5 fields)

| Field | Value | Source | Column/Logic |
|-------|-------|--------|--------------|
| `contract_cost` | `9.87` | product_catalog.xlsx | Unit Price (Current Catalog) |
| `contract_cost_per_unit` | `0.01974` | Calculated | `9.87 / 500 = $0.0197/tablet` |
| `contract_effective_date` | `2025-01-01` | Metadata | File load date |
| `contract_source` | `product_catalog.xlsx` | Metadata | Source file |
| `contract_vendor` | `PUBLIC HEALTH SERVICES` | product_catalog.xlsx | Contract Name |

### Section 9: AWP Pricing (5 fields)

| Field | Value | Source | Column/Logic |
|-------|-------|--------|--------------|
| `awp` | `228.00` | product_catalog.xlsx | Medispan AWP |
| `awp_per_unit` | `0.456` | Calculated | `228.00 / 500 = $0.456/tablet` |
| `awp_effective_date` | `2025-01-01` | Metadata | File load date |
| `awp_source` | `MEDISPAN` | Metadata | Column name |
| `awp_unit_price` | `0.456` | Calculated | Per-tablet |

### Section 10: NADAC Pricing (7 fields)

| Field | Value | Source | Column/Logic |
|-------|-------|--------|--------------|
| `nadac_price` | `null` | nadac_statistics.csv | NDC not found (or branded only) |
| `nadac_per_unit` | `null` | N/A | N/A |
| `nadac_effective_date` | `null` | N/A | N/A |
| `nadac_as_of_date` | `null` | N/A | N/A |
| `nadac_pricing_unit` | `null` | N/A | N/A |
| `nadac_explanation_code` | `null` | N/A | N/A |
| `nadac_classification` | `null` | N/A | N/A |

### Section 11: ASP Pricing (7 fields)

| Field | Value | Source | Column/Logic |
|-------|-------|--------|--------------|
| `asp_payment_limit` | `null` | asp_pricing.csv | **No HCPCS for oral drugs** |
| `asp_true` | `null` | N/A | N/A |
| `asp_per_billing_unit` | `null` | N/A | N/A |
| `asp_effective_quarter` | `null` | N/A | N/A |
| `asp_effective_date` | `null` | N/A | N/A |
| `asp_end_date` | `null` | N/A | N/A |
| `asp_source_file` | `null` | N/A | N/A |

### Section 12: HCPCS/Billing (11 fields)

| Field | Value | Source | Column/Logic |
|-------|-------|--------|--------------|
| `hcpcs_code` | `null` | asp_crosswalk.csv | **Oral drugs not in ASP crosswalk** |
| `hcpcs_description` | `null` | N/A | N/A |
| `hcpcs_short_description` | `null` | N/A | N/A |
| `bill_units_per_package` | `null` | N/A | N/A |
| `hcpcs_dosage_descriptor` | `null` | N/A | N/A |
| `has_medical_path` | `FALSE` | Derived | `hcpcs_code IS NULL` |
| `is_noc` | `FALSE` | noc_crosswalk.csv | Not in NOC file |
| `noc_hcpcs_code` | `null` | N/A | N/A |
| `noc_payment_limit` | `null` | N/A | N/A |
| `crosswalk_effective_quarter` | `null` | N/A | N/A |

### Section 13: Reimbursement Rates (9 fields)

| Field | Value | Source | Column/Logic |
|-------|-------|--------|--------------|
| `awp_factor_brand` | `0.85` | Constant | Brand rate |
| `awp_factor_generic` | `0.20` | Constant | Generic rate |
| `awp_factor_applicable` | `0.20` | Derived | Generic drug |
| `medicare_part_d_multiplier` | `0.20` | Ravenswood | Generic rate |
| `commercial_multiplier` | `0.15` | Ravenswood | Generic rate |
| `medicaid_mco_multiplier` | `0.15` | Ravenswood | Generic rate |
| `asp_medicaid_multiplier` | `1.04` | Constant | N/A (no ASP) |
| `asp_medicare_multiplier` | `1.06` | Constant | N/A (no ASP) |
| `asp_commercial_multiplier` | `1.15` | Configurable | N/A (no ASP) |

### Section 14: Wholesale/Retail Pricing (5 fields)

| Field | Value | Source | Column/Logic |
|-------|-------|--------|--------------|
| `wholesaler_retail_price` | `null` | wholesaler_catalog.xlsx | NDC not found |
| `wholesaler_name` | `null` | N/A | N/A |
| `wholesaler_as_of_date` | `null` | N/A | N/A |
| `retail_price_variance_pct` | `null` | N/A | N/A |
| `retail_confidence` | `null` | N/A | N/A |

### Section 15: Risk Flags (11 fields)

| Field | Value | Source | Column/Logic |
|-------|-------|--------|--------------|
| `is_ira_drug` | `FALSE` | ira_drug_list.csv | Not in IRA list |
| `ira_year` | `null` | N/A | N/A |
| `ira_max_fair_price` | `null` | N/A | N/A |
| `ira_description` | `null` | N/A | N/A |
| `is_penny_priced` | `FALSE` | nadac_statistics.csv | Not in NADAC |
| `penny_override_cost` | `null` | N/A | N/A |
| `discount_340b_pct` | `null` | N/A | N/A |
| `has_inflation_penalty` | `FALSE` | N/A | N/A |
| `inflation_penalty_pct` | `null` | N/A | N/A |
| `risk_level` | `MEDIUM` | Derived | Controlled substance (C2) |
| `risk_factors` | `["DEA Schedule II"]` | Derived | C2 flagged |

### Section 16: Biologic/Loading Dose (10 fields)

*All null - not a biologic*

### Section 17: Calculated Margins (10 fields)

**Calculation Inputs:**
- Contract Cost: $9.87 (per 500-count bottle)
- AWP: $228.00 (per 500-count bottle)
- AWP Factor: 0.20 (Generic)
- ASP: null (no medical path)
- Bill Units: null

| Field | Value | Source | Calculation |
|-------|-------|--------|-------------|
| `margin_pharmacy_medicaid` | `null` | Calculated | NADAC not available |
| `margin_pharmacy_medicaid_formula` | `null` | N/A | N/A |
| `margin_pharmacy_medicare_commercial` | `$35.73` | Calculated | `(228.00 × 0.20) - 9.87 = 45.60 - 9.87 = 35.73` |
| `margin_pharmacy_medicare_commercial_formula` | `AWP × 0.20 - Contract = 228.00 × 0.20 - 9.87` | Derived | Formula |
| `margin_medical_medicaid` | `null` | N/A | No ASP/HCPCS |
| `margin_medical_medicaid_formula` | `null` | N/A | N/A |
| `margin_medical_medicare` | `null` | N/A | No ASP/HCPCS |
| `margin_medical_medicare_formula` | `null` | N/A | N/A |
| `margin_medical_commercial` | `null` | N/A | No ASP/HCPCS |
| `margin_medical_commercial_formula` | `null` | N/A | N/A |

### Section 18: Margin Analysis Summary (10 fields)

| Field | Value | Source | Calculation |
|-------|-------|--------|-------------|
| `best_margin` | `$35.73` | Derived | Only pharmacy margin available |
| `best_pathway` | `PHARMACY_MEDICARE_COMMERCIAL` | Derived | Only option |
| `second_best_margin` | `null` | Derived | No medical pathway |
| `second_best_pathway` | `null` | Derived | N/A |
| `margin_delta` | `$35.73` | Calculated | Margin vs $0 (no alternative) |
| `margin_delta_pct` | `100%` | Calculated | N/A |
| `recommendation` | `RETAIL` | Derived | Only viable pathway |
| `recommendation_confidence` | `HIGH` | Derived | No alternative |
| `all_margins_positive` | `TRUE` | Derived | Pharmacy margin positive |
| `has_negative_margin` | `FALSE` | Derived | No negative margins |

---

## Key Differences Between Examples

| Aspect | Iron Sucrose (Injectable) | Hydrocodone/APAP (Oral) |
|--------|---------------------------|-------------------------|
| **Route** | Injectable (SDPF) | Oral (TABS) |
| **HCPCS** | J1756 ✓ | None ✗ |
| **Medical Path** | Yes - 5 pathways | No - retail only |
| **Concentration** | 20MG/ML | N/A (solid) |
| **Combination** | No | Yes (10/325 MG) |
| **DEA Schedule** | None | C2 |
| **Package Pattern** | 10X5ML | 500 count |
| **Best Pathway** | Medical Commercial | Retail |
| **Margin Count** | 4 (1 negative) | 1 |

---

## Data Source Summary

| Source File | Iron Sucrose Fields | Hydrocodone Fields |
|-------------|--------------------|--------------------|
| product_catalog.xlsx | 15 | 15 |
| asp_crosswalk.csv | 8 | 0 |
| asp_pricing.csv | 5 | 0 |
| nadac_statistics.csv | 0 | 0 |
| biologics_grid.xlsx | 0 | 0 |
| Ravenswood_AWP.xlsx | 3 | 3 |
| ira_drug_list.csv | 1 | 1 |
| **Parsed from Description** | 12 | 10 |
| **Derived/Calculated** | ~50 | ~35 |
