# FUTURE_FEATURES.md — Deferred Features for v2+

> **Version:** 1.0
> **Last Updated:** January 15, 2026

This document tracks features explicitly out of scope for v1, with rationale and prerequisites.

---

## Deferred to v2

### 1. Patient Cohort Simulations

**Description**: Model specific patient histories and cohort mix rather than "Standard New Patient" vs "Standard Maintenance Patient."

**Why Deferred**:
- v1 scope focuses on drug-level analysis, not patient-level
- Requires additional data inputs (patient demographics, adherence patterns)
- Loading dose logic in v1 provides 80% of the value with 20% of complexity

**Rough Complexity**: Medium-High (3-4 weeks)

**Prerequisites from v1**:
- Working dosing profile system (Phase 4)
- Validated Year 1 vs Maintenance calculations
- UI framework for parameter input

---

### 2. Automated CMS ASP File Ingestion

**Description**: Automatically fetch quarterly CMS ASP pricing files from CMS.gov instead of manual upload.

**Why Deferred**:
- CMS file URLs change each quarter (no stable API)
- Manual upload provides explicit human verification
- Most data sources (Wholesaler Catalog, Financial Matrix) are proprietary anyway
- v1 prioritizes accuracy over automation

**Rough Complexity**: Low-Medium (1-2 weeks)

**Prerequisites from v1**:
- Schema validation passing (Phase 2)
- Clear file format expectations documented

---

### 3. Historical Trend Analysis

**Description**: Track pricing trends over time to identify drugs with increasing/decreasing margins.

**Why Deferred**:
- Requires storing historical snapshots (database layer)
- v1 is decision-support for current quarter, not forecasting
- IRA flags provide the most critical forward-looking risk indicator

**Rough Complexity**: Medium (2-3 weeks)

**Prerequisites from v1**:
- Working data pipeline (Phases 2-4)
- Database infrastructure (not in v1)

---

### 4. Multi-Site Portfolio Optimization

**Description**: Optimize across multiple 340B sites (e.g., hospital system with 5 covered entities).

**Why Deferred**:
- v1 targets single-site analysis (financial analyst use case)
- Multi-site requires contract cost variations per entity
- Adds significant UI complexity

**Rough Complexity**: High (4-6 weeks)

**Prerequisites from v1**:
- Stable single-site analysis
- Export functionality working
- User authentication (not in v1)

---

### 5. PBM Network Eligibility Lookup

**Description**: Integrate with PBM data to show actual capture rate by payer mix, not just variable slider.

**Why Deferred**:
- PBM network data is highly proprietary
- Variable slider provides adequate stress-testing capability
- Different capture rates per PBM adds analysis complexity

**Rough Complexity**: High (4-6 weeks, plus data acquisition)

**Prerequisites from v1**:
- Capture rate slider working (Phase 6)
- User understands variable sensitivity

---

### 6. Export to EHR/Pharmacy Systems

**Description**: Push recommendations directly to Epic, Cerner, or pharmacy dispensing systems.

**Why Deferred**:
- Requires integration partnerships
- v1 serves strategic consultants (export to CSV/Excel sufficient)
- EHR integration is a v3+ enterprise feature

**Rough Complexity**: Very High (6-12 weeks per system)

**Prerequisites from v1**:
- Validated recommendations (Phase 7)
- Audit trail for regulatory compliance

---

### 7. Real-Time Denial Rate Tracking

**Description**: Track actual claim denials to refine the Commercial Medical margin estimate (currently ASP+15% conservative).

**Why Deferred**:
- Requires claims data integration
- v1 conservative estimate (5% denial compression) is sufficient
- Better to be conservative and exceed expectations

**Rough Complexity**: High (4-6 weeks, plus data acquisition)

**Prerequisites from v1**:
- Commercial margin calculation working (Phase 4)
- Provenance chain for margin components

---

### 8. Biosimilar Switch Analysis

**Description**: Compare originator biologic to biosimilar alternatives with margin impact.

**Why Deferred**:
- Requires maintaining biosimilar mapping table
- v1 analyzes drugs individually (user can compare manually)
- Clinical equivalence decisions are outside software scope

**Rough Complexity**: Medium (2-3 weeks)

**Prerequisites from v1**:
- Full catalog loaded (Phase 2)
- Drug detail view working (Phase 6)

---

## Feature Prioritization Matrix (v2)

| Feature | Business Value | Technical Complexity | Data Availability | Priority |
|---------|---------------|---------------------|-------------------|----------|
| Patient Cohort Simulations | High | Medium-High | Internal | P1 |
| Historical Trend Analysis | Medium | Medium | Internal | P2 |
| Biosimilar Switch Analysis | Medium | Low-Medium | Internal | P2 |
| Automated CMS Ingestion | Low | Low | Public | P3 |
| Multi-Site Portfolio | High | High | Internal | P3 |
| PBM Network Eligibility | High | High | Requires acquisition | P4 |
| EHR Integration | Medium | Very High | Requires partnerships | P5 |

---

## Notes

- All features assume v1 is complete and stable
- Complexity estimates assume one senior developer
- "Data Availability" indicates whether data is internal, public, or requires external acquisition
- Priority based on combination of value/complexity/data factors
