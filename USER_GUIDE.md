# 340B Optimizer User Guide

This guide explains how to use the 340B Site-of-Care Optimization Engine to analyze drug margins and identify optimal treatment pathways.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [App Navigation](#app-navigation)
3. [Data File Requirements](#data-file-requirements)
4. [Using the Dashboard](#using-the-dashboard)
5. [Drug Detail View](#drug-detail-view)
6. [Understanding the Calculations](#understanding-the-calculations)
7. [Calculation Verification Examples](#calculation-verification-examples)
8. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Launching the Application

```bash
cd 340b-optimizer
streamlit run src/optimizer_340b/ui/app.py
```

The app opens in your browser at `http://localhost:8501`.

### Quick Start (Recommended for First-Time Users)

1. Click **"Load Sample Data"** on the Upload page
2. Click **"Process Data"** button
3. Select **"Dashboard"** from the sidebar
4. Explore 34,229 drugs with pre-loaded data

---

## App Navigation

The app has three main pages, accessible via the **sidebar radio buttons**:

### 1. Upload Data

**Purpose**: Load your data files or use sample data.

| Section | Description |
|---------|-------------|
| Quick Start | One-click sample data loading |
| Product Catalog | Your 340B contract pricing (required) |
| ASP Pricing File | CMS Medicare payment limits (required) |
| NDC-HCPCS Crosswalk | Billing code mapping (required) |
| NADAC Statistics | Penny pricing detection (optional) |
| Biologics Logic Grid | Loading dose profiles (optional) |
| Upload Status | Shows which files are loaded |
| Process Data | Normalizes and joins data for analysis |

### 2. Dashboard

**Purpose**: View ranked optimization opportunities.

| Section | Description |
|---------|-------------|
| Summary Metrics | Total drugs, HCPCS mappings, medical eligible, penny pricing counts |
| Analysis Controls | Capture rate slider (sidebar) |
| Filters | IRA drugs only, hide penny pricing, minimum margin delta |
| Search | Find drugs by name or NDC |
| Opportunity Table | Ranked list with margins and recommendations |
| Drug Detail Links | Quick access to top 5 drugs |

### 3. Drug Detail

**Purpose**: Deep-dive analysis of a single drug.

| Section | Description |
|---------|-------------|
| Drug Header | Name, NDC, manufacturer |
| Risk Assessment | IRA and Penny Pricing badges |
| Margin Analysis | Side-by-side comparison cards |
| Sensitivity Chart | Margin vs. capture rate visualization |
| Loading Dose Impact | Year 1 vs. Maintenance projections |
| Calculation Provenance | Step-by-step calculation breakdown |

### Sidebar Elements

| Element | Description |
|---------|-------------|
| Navigation | Radio buttons to switch pages |
| Data Status | Shows loaded files with row counts |
| Analysis Controls | Capture rate slider, payer type toggle |
| About | App version and feature summary |

---

## Data File Requirements

### 1. Product Catalog (Required)

**Format**: Excel (.xlsx, .xls)

| Column | Required | Description | Example |
|--------|----------|-------------|---------|
| `NDC` | Yes | 10 or 11-digit NDC code | `00074433902` |
| `Contract Cost` | Yes | 340B acquisition cost | `150.00` |
| `AWP` or `Medispan AWP` | Yes | Average Wholesale Price | `6500.00` |
| `Drug Name` or `Trade Name` | Recommended | Drug trade name | `HUMIRA` |
| `Manufacturer` | Recommended | Manufacturer name | `ABBVIE` |

**Example rows**:
```
NDC,Drug Name,Manufacturer,Contract Cost,Medispan AWP
00074433902,HUMIRA,ABBVIE,150.00,6500.00
00006307761,KEYTRUDA,MERCK,5200.00,10500.00
```

### 2. ASP Pricing File (Required)

**Format**: CSV
**Note**: CMS files have 8 header rows that are automatically skipped.

| Column | Required | Description | Example |
|--------|----------|-------------|---------|
| `HCPCS Code` | Yes | Medicare billing code | `J0135` |
| `Payment Limit` | Yes | ASP-based payment amount | `2968.94` |
| `Short Description` | Optional | Drug description | `ADALIMUMAB INJ` |

**Example rows** (after header):
```
HCPCS Code,Short Description,Payment Limit
J0135,ADALIMUMAB INJ,2968.94
J9271,PEMBROLIZUMAB INJ,5270.11
```

**Important**: Values of "N/A" in Payment Limit are automatically skipped.

### 3. NDC-HCPCS Crosswalk (Required)

**Format**: CSV
**Note**: CMS files have 8 header rows that are automatically skipped.

| Column | Required | Description | Example |
|--------|----------|-------------|---------|
| `NDC` or `NDC2` | Yes | NDC code | `00074433902` |
| `HCPCS Code` or `_2025_CODE` | Yes | Billing code mapping | `J0135` |
| `Billing Units Per Package` | Optional | Units per NDC | `2` |

**Example rows** (after header):
```
NDC2,_2025_CODE,Billing Units Per Package
00074433902,J0135,2
00006307761,J9271,1
```

### 4. NADAC Statistics (Optional)

**Format**: CSV

| Column | Required | Description | Example |
|--------|----------|-------------|---------|
| `ndc` | Yes | NDC code | `00074433902` |
| `total_discount_340b_pct` | Yes | 340B discount percentage | `85.5` |
| `penny_pricing` | Optional | Boolean flag | `True` |

**Penny Pricing Detection**: Drugs with discount >= 95% are flagged.

### 5. Biologics Logic Grid (Optional)

**Format**: Excel (.xlsx, .xls)

| Column | Required | Description | Example |
|--------|----------|-------------|---------|
| `Drug Name` | Yes | Trade name for matching | `HUMIRA` |
| `Indication` | Optional | Treatment indication | `Rheumatoid Arthritis` |
| `Year 1 Fills` | Yes | Fills including loading doses | `17` |
| `Year 2+ Fills` | Yes | Maintenance fills per year | `12` |

---

## Using the Dashboard

### Step-by-Step Workflow

1. **Load Data**: Use sample data or upload your files
2. **Process Data**: Click "Process Data" to normalize and join
3. **Go to Dashboard**: Select "Dashboard" from sidebar
4. **Set Capture Rate**: Adjust slider (default 45%)
5. **Apply Filters**:
   - Check "Show IRA drugs only" to focus on at-risk drugs
   - Check "Hide penny pricing drugs" (default) to exclude low-margin items
   - Set minimum margin delta to filter small opportunities
6. **Search**: Type drug name or NDC in search box
7. **Review Results**: Table shows ranked opportunities
8. **Drill Down**: Click drug name to select, then go to Drug Detail

### Understanding the Table Columns

| Column | Description |
|--------|-------------|
| Drug | Trade name |
| NDC | National Drug Code |
| Best Margin | Highest margin across all pathways |
| Retail | AWP-based pharmacy margin |
| Medicare | ASP + 6% medical margin |
| Commercial | ASP + 15% medical margin |
| Recommendation | Optimal pathway |
| Delta | Margin improvement vs. retail |
| Risk | IRA/Penny pricing badges |

---

## Drug Detail View

### Accessing Drug Details

1. From Dashboard, click a drug name button
2. Message appears: "Selected [drug]. Go to Drug Detail."
3. Select "Drug Detail" from sidebar

### Analysis Parameters (Sidebar)

- **Capture Rate**: Adjust to see retail margin sensitivity
- **Payer Type**: Toggle Medicare vs. Commercial comparison

### Sections Explained

#### Risk Assessment
- Red badge: IRA 2026 or 2027 drug (price negotiation risk)
- Orange badge: Penny pricing (minimal 340B opportunity)

#### Margin Analysis Cards
- **Retail**: AWP × 0.85 - Contract Cost
- **Medicare Medical**: ASP × 1.06 × Billing Units - Contract Cost
- **Commercial Medical**: ASP × 1.15 × Billing Units - Contract Cost
- Green border indicates recommended pathway

#### Sensitivity Analysis
Interactive chart showing margin at different capture rates (40%-100%).

#### Loading Dose Impact
For biologics: Year 1 revenue (with loading doses) vs. Maintenance.

#### Calculation Provenance
Complete audit trail showing every step of the calculation.

---

## Understanding the Calculations

### Retail Margin Formula

```
Revenue = AWP × 0.85 (industry standard discount)
Gross Margin = Revenue - Contract Cost
Net Margin = Gross Margin × Capture Rate
```

**Why 0.85?** Pharmacies typically reimburse at AWP minus 15%.

### Medicare Margin Formula (ASP + 6%)

```
Revenue = ASP × 1.06 × Billing Units Per Package
Margin = Revenue - Contract Cost
```

**Note**: Medicare Part B reimburses at ASP plus 6%.

### Commercial Margin Formula (ASP + 15%)

```
Revenue = ASP × 1.15 × Billing Units Per Package
Margin = Revenue - Contract Cost
```

**Note**: Commercial payers typically reimburse at ASP plus 15%.

### Recommendation Logic

1. Calculate all three margins (Retail Net, Medicare, Commercial)
2. Find the maximum margin
3. Recommend the pathway with highest margin
4. Calculate delta (improvement vs. retail)

---

## Calculation Verification Examples

### Example 1: HUMIRA (Dual-Eligible Drug)

**Input Data**:
| Field | Value |
|-------|-------|
| NDC | 00074433902 |
| Contract Cost | $150.00 |
| AWP | $6,500.00 |
| ASP | $2,800.00 |
| HCPCS Code | J0135 |
| Billing Units | 2 |
| Capture Rate | 45% |

**Retail Calculation**:
```
Revenue = $6,500 × 0.85 = $5,525.00
Gross Margin = $5,525 - $150 = $5,375.00
Net Margin = $5,375 × 0.45 = $2,418.75
```

**Medicare Calculation**:
```
Revenue = $2,800 × 1.06 × 2 = $5,936.00
Margin = $5,936 - $150 = $5,786.00
```

**Commercial Calculation**:
```
Revenue = $2,800 × 1.15 × 2 = $6,440.00
Margin = $6,440 - $150 = $6,290.00
```

**Recommendation**: Commercial Medical ($6,290 > $5,786 > $2,418.75)
**Margin Delta**: $6,290 - $2,418.75 = $3,871.25

### Example 2: Oral Drug (Retail Only)

**Input Data**:
| Field | Value |
|-------|-------|
| NDC | 68382076010 |
| Drug Name | METFORMIN HCL |
| Contract Cost | $5.00 |
| AWP | $150.00 |
| ASP | N/A |
| HCPCS Code | N/A |
| Capture Rate | 45% |

**Retail Calculation**:
```
Revenue = $150 × 0.85 = $127.50
Gross Margin = $127.50 - $5 = $122.50
Net Margin = $122.50 × 0.45 = $55.13
```

**Medicare/Commercial**: Not applicable (no HCPCS code)

**Recommendation**: Retail (only option)
**Margin Delta**: $55.13 (vs. $0)

### Example 3: Capture Rate Sensitivity

**HUMIRA at different capture rates**:

| Capture Rate | Retail Net | Medicare | Commercial | Best Path |
|--------------|------------|----------|------------|-----------|
| 40% | $2,150.00 | $5,786.00 | $6,290.00 | Commercial |
| 45% | $2,418.75 | $5,786.00 | $6,290.00 | Commercial |
| 60% | $3,225.00 | $5,786.00 | $6,290.00 | Commercial |
| 80% | $4,300.00 | $5,786.00 | $6,290.00 | Commercial |
| 100% | $5,375.00 | $5,786.00 | $6,290.00 | Commercial |

**Key Insight**: Even at 100% capture, Commercial Medical is still better for HUMIRA.

### Example 4: When Retail Wins

**High-AWP, Low-ASP Drug**:
| Field | Value |
|-------|-------|
| Contract Cost | $100.00 |
| AWP | $2,000.00 |
| ASP | $200.00 |
| Billing Units | 1 |
| Capture Rate | 80% |

**Calculations**:
```
Retail Net = ($2,000 × 0.85 - $100) × 0.80 = $1,280.00
Medicare = $200 × 1.06 × 1 - $100 = $112.00
Commercial = $200 × 1.15 × 1 - $100 = $130.00
```

**Recommendation**: Retail ($1,280 >> $130)

---

## Troubleshooting

### Common Issues

#### "Please upload data files first"
- Go to Upload Data page
- Click "Load Sample Data" or upload your files
- Click "Process Data" button

#### Missing columns error
- Check file has required columns (see format requirements)
- Column names are case-sensitive
- Alternative column names are supported (e.g., "Medispan AWP" for "AWP")

#### Low match rate in crosswalk
- Only ~14% of drugs match (expected for infusible drugs)
- Oral drugs don't have HCPCS codes
- This is normal behavior

#### "N/A" values in ASP file
- These are automatically skipped
- No action required

#### Slow dashboard loading
- First load takes 5-10 seconds for 34k drugs
- Subsequent filters are faster
- Consider filtering to reduce dataset

### Data Quality Checks

1. **Verify row counts** in sidebar Data Status
2. **Check Upload Status** section for green checkmarks
3. **Review validation warnings** after upload
4. **Spot-check calculations** using examples above

---

## Support

For issues or questions:
1. Check this guide's troubleshooting section
2. Review README.md for technical details
3. Contact the development team

---

*Last updated: January 2026*
