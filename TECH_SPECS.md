# TECH_SPECS.md — 340B Site-of-Care Optimization Engine

> **Version:** 1.1
> **Last Updated:** January 16, 2026

---

## Overview

The **340B Optimizer** is a Streamlit web application that determines the optimal treatment pathway (Retail Pharmacy vs. Medical Billing) for 340B-eligible drugs by calculating **Net Realizable Revenue** rather than simplistic "Buying Power."

Key capabilities:
1. **Dual-Channel Margin Comparison** — Side-by-side analysis of Retail (AWP-based) vs. Medical (ASP-based) margins
2. **Payer-Adjusted Revenue** — Separate logic for Medicare Part B (ASP+6%) and Commercial Medical (ASP+15%)
3. **Variable Stress Testing** — Real-time sliders for Capture Rate to model realistic pharmacy constraints
4. **Loading Dose Modeling** — Year 1 vs. Maintenance revenue projections for biologics
5. **Risk Flagging** — IRA 2026/2027 warnings and Penny Pricing alerts

The system uses a **batch pre-compute + interactive query** architecture where the "Golden Record" (34k+ drugs) is processed on data upload, then users can instantly drill into specific drugs with variable toggles.

---

## Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Language | Python 3.11+ | Core implementation |
| UI Framework | Streamlit 1.30+ | Interactive web dashboard |
| Data Processing | Polars | High-performance DataFrame operations on 34k+ rows |
| Data I/O | Pandas + openpyxl | Excel file reading (proprietary formats) |
| Visualization | Plotly | Interactive charts for margin comparisons |
| Fuzzy Matching | thefuzz | Drug name matching across data sources |
| Validation | Pydantic | Data model validation |
| Configuration | python-dotenv | Environment variable management |
| Serialization | orjson | Fast JSON for caching computed results |
| Package Manager | uv | Dependency management |
| Linting | ruff | Code quality |
| Type Checking | mypy | Static analysis |
| Testing | pytest | Test framework |

---

## File Structure

```
340b-optimizer/
├── src/
│   └── optimizer_340b/
│       ├── __init__.py              # Package exports
│       ├── config.py                # Environment and settings
│       ├── models.py                # Data models (Drug, Margin, etc.)
│       ├── ingest/
│       │   ├── __init__.py
│       │   ├── loaders.py           # File loading (Excel, CSV)
│       │   ├── validators.py        # Schema validation (Bronze layer)
│       │   └── normalizers.py       # Data cleaning (Silver layer)
│       ├── compute/
│       │   ├── __init__.py
│       │   ├── margins.py           # Margin calculation engine (Gold layer)
│       │   ├── crosswalk.py         # NDC-HCPCS join logic
│       │   └── dosing.py            # Loading dose calculations
│       ├── risk/
│       │   ├── __init__.py
│       │   ├── ira_flags.py         # IRA price negotiation detection
│       │   └── penny_pricing.py     # NADAC penny pricing alerts
│       └── ui/
│           ├── __init__.py
│           ├── app.py               # Streamlit main entry point
│           ├── pages/
│           │   ├── __init__.py
│           │   ├── upload.py        # Data upload page
│           │   ├── dashboard.py     # Main optimization dashboard
│           │   └── drug_detail.py   # Single drug deep-dive
│           └── components/
│               ├── __init__.py
│               ├── margin_card.py   # Margin comparison card
│               ├── capture_slider.py # Capture rate slider
│               └── risk_badge.py    # Risk flag badges
├── tests/
│   ├── __init__.py
│   ├── conftest.py                  # Shared fixtures
│   ├── test_loaders.py
│   ├── test_validators.py
│   ├── test_margins.py
│   ├── test_crosswalk.py
│   ├── test_dosing.py
│   ├── test_risk_flags.py
│   └── test_integration.py          # End-to-end tests
├── data/
│   └── sample/                      # Sample data files
│       ├── product_catalog.xlsx     # 34,229 drugs with contract pricing
│       ├── asp_pricing.csv          # CMS ASP payment limits
│       ├── asp_crosswalk.csv        # NDC-HCPCS billing code mapping
│       ├── noc_pricing.csv          # NOC fallback pricing
│       ├── noc_crosswalk.csv        # NOC NDC mapping
│       ├── ndc_nadac_master_statistics.csv  # NADAC penny pricing data
│       ├── biologics_logic_grid.xlsx # Loading dose profiles
│       ├── Ravenswood_AWP_Reimbursement_Matrix.xlsx  # Payer multipliers
│       ├── wholesaler_catalog.xlsx  # Retail price validation
│       ├── ira_drug_list.csv        # IRA 2026/2027 drugs (data-driven)
│       └── cms_crosswalk_reference.csv  # CMS field descriptions
├── notebooks/
│   └── demo.ipynb                   # Google Colab demo
├── .env                             # Environment variables (gitignored)
├── .env.example                     # Template for .env
├── .gitignore
├── .pre-commit-config.yaml
├── pyproject.toml
├── requirements.txt
├── README.md
├── TECH_SPECS.md
├── ATOMIC_STEPS.md
├── CODING_AGENT_PROMPT.md
├── FUTURE_FEATURES.md
└── CHECKPOINT.md
```

---

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `LOG_LEVEL` | Logging verbosity (DEBUG, INFO, WARNING, ERROR) | No | `INFO` |
| `DATA_DIR` | Directory for uploaded data files | No | `./data/uploads` |
| `CACHE_ENABLED` | Enable computed results caching | No | `true` |
| `CACHE_TTL_HOURS` | Cache time-to-live in hours | No | `24` |

**Note**: This application does not require external API keys. All data is uploaded manually.

---

## Data Model

### Core Entities

```python
@dataclass
class Drug:
    """Core drug entity combining catalog and pricing data."""
    ndc: str                          # 11-digit normalized NDC
    drug_name: str                    # Trade name
    manufacturer: str
    contract_cost: Decimal            # 340B acquisition cost
    awp: Decimal                      # Average Wholesale Price
    asp: Decimal | None               # Average Sales Price (if HCPCS mapped)
    hcpcs_code: str | None            # Medicare billing code
    bill_units_per_package: int       # HCPCS billing units per NDC package
    therapeutic_class: str | None
    is_biologic: bool
    ira_flag: bool                    # Subject to IRA price negotiation
    penny_pricing_flag: bool          # NADAC at 340B floor


@dataclass
class MarginAnalysis:
    """Complete margin analysis for a drug."""
    drug: Drug

    # Retail Path
    retail_gross_margin: Decimal      # AWP * Reimb_Rate - Contract_Cost
    retail_net_margin: Decimal        # Gross * Capture_Rate
    retail_capture_rate: Decimal      # Default 0.45 (45%)

    # Medical Path - Medicare
    medicare_margin: Decimal          # ASP * 1.06 * Bill_Units - Contract_Cost

    # Medical Path - Commercial
    commercial_margin: Decimal        # ASP * 1.15 * Bill_Units - Contract_Cost

    # Recommendation
    recommended_path: str             # "RETAIL", "MEDICARE_MEDICAL", "COMMERCIAL_MEDICAL"
    margin_delta: Decimal             # Difference between best and second-best path


@dataclass
class DosingProfile:
    """Loading dose profile for biologics."""
    drug_name: str
    indication: str
    year_1_fills: int                 # Including loading doses
    year_2_plus_fills: int            # Maintenance only
    adjusted_year_1_fills: Decimal    # Compliance-adjusted

    def year_1_revenue(self, margin_per_fill: Decimal) -> Decimal:
        """Calculate Year 1 revenue including loading doses."""
        return self.adjusted_year_1_fills * margin_per_fill
```

---

## Starter Code

### `src/optimizer_340b/__init__.py`

```python
"""340B Site-of-Care Optimization Engine.

Determines optimal treatment pathway (Retail vs Medical) for 340B drugs
by calculating Net Realizable Revenue.
"""

from optimizer_340b.config import Settings
from optimizer_340b.models import Drug, MarginAnalysis, DosingProfile

__version__ = "0.1.0"
__all__ = ["Settings", "Drug", "MarginAnalysis", "DosingProfile"]
```

### `src/optimizer_340b/config.py`

```python
"""Configuration management for 340B Optimizer."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Settings:
    """Application settings loaded from environment variables."""

    log_level: str
    data_dir: Path
    cache_enabled: bool
    cache_ttl_hours: int

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables.

        Returns:
            Settings instance with loaded configuration.
        """
        load_dotenv()

        return cls(
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            data_dir=Path(os.getenv("DATA_DIR", "./data/uploads")),
            cache_enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
            cache_ttl_hours=int(os.getenv("CACHE_TTL_HOURS", "24")),
        )

    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
```

### `src/optimizer_340b/models.py`

```python
"""Data models for 340B Optimizer."""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional


class RecommendedPath(str, Enum):
    """Recommended site-of-care pathway."""

    RETAIL = "RETAIL"
    MEDICARE_MEDICAL = "MEDICARE_MEDICAL"
    COMMERCIAL_MEDICAL = "COMMERCIAL_MEDICAL"


class RiskLevel(str, Enum):
    """Risk classification for regulatory flags."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class Drug:
    """Core drug entity combining catalog and pricing data."""

    ndc: str
    drug_name: str
    manufacturer: str
    contract_cost: Decimal
    awp: Decimal
    asp: Optional[Decimal] = None
    hcpcs_code: Optional[str] = None
    bill_units_per_package: int = 1
    therapeutic_class: Optional[str] = None
    is_biologic: bool = False
    ira_flag: bool = False
    penny_pricing_flag: bool = False

    def has_medical_path(self) -> bool:
        """Check if drug can be billed through medical channel."""
        return self.hcpcs_code is not None and self.asp is not None

    @property
    def ndc_normalized(self) -> str:
        """Return 11-digit normalized NDC with leading zeros preserved."""
        cleaned = self.ndc.replace("-", "").replace(" ", "")
        return cleaned.zfill(11)[-11:]


@dataclass
class MarginAnalysis:
    """Complete margin analysis for a drug."""

    drug: Drug
    retail_gross_margin: Decimal
    retail_net_margin: Decimal
    retail_capture_rate: Decimal
    medicare_margin: Optional[Decimal]
    commercial_margin: Optional[Decimal]
    recommended_path: RecommendedPath
    margin_delta: Decimal

    def to_display_dict(self) -> dict:
        """Convert to dictionary for UI display."""
        return {
            "ndc": self.drug.ndc,
            "drug_name": self.drug.drug_name,
            "contract_cost": float(self.drug.contract_cost),
            "retail_margin": float(self.retail_net_margin),
            "medicare_margin": float(self.medicare_margin) if self.medicare_margin else None,
            "commercial_margin": float(self.commercial_margin) if self.commercial_margin else None,
            "recommendation": self.recommended_path.value,
            "margin_delta": float(self.margin_delta),
            "ira_risk": self.drug.ira_flag,
            "penny_pricing": self.drug.penny_pricing_flag,
        }


@dataclass
class DosingProfile:
    """Loading dose profile for biologics."""

    drug_name: str
    indication: str
    year_1_fills: int
    year_2_plus_fills: int
    adjusted_year_1_fills: Decimal

    def year_1_revenue(self, margin_per_fill: Decimal) -> Decimal:
        """Calculate Year 1 revenue including loading doses.

        Args:
            margin_per_fill: Net margin per fill/administration.

        Returns:
            Total Year 1 revenue.
        """
        return self.adjusted_year_1_fills * margin_per_fill

    def maintenance_revenue(self, margin_per_fill: Decimal) -> Decimal:
        """Calculate annual maintenance revenue (Year 2+).

        Args:
            margin_per_fill: Net margin per fill/administration.

        Returns:
            Annual maintenance revenue.
        """
        return Decimal(self.year_2_plus_fills) * margin_per_fill
```

### `src/optimizer_340b/ingest/loaders.py`

```python
"""File loading utilities for 340B data sources."""

import logging
from pathlib import Path
from typing import BinaryIO

import pandas as pd
import polars as pl

logger = logging.getLogger(__name__)


def load_excel_to_polars(
    file: BinaryIO | Path,
    sheet_name: str | int = 0,
) -> pl.DataFrame:
    """Load Excel file into Polars DataFrame.

    Uses pandas as intermediate step for Excel parsing, then converts to Polars
    for downstream processing efficiency.

    Args:
        file: File path or file-like object.
        sheet_name: Sheet name or index to load.

    Returns:
        Polars DataFrame with loaded data.

    Raises:
        ValueError: If file cannot be parsed as Excel.
    """
    logger.info(f"Loading Excel file, sheet: {sheet_name}")

    try:
        # Use pandas for Excel parsing (openpyxl backend)
        pdf = pd.read_excel(file, sheet_name=sheet_name, engine="openpyxl")
        df = pl.from_pandas(pdf)
        logger.info(f"Loaded {df.height} rows, {df.width} columns")
        return df
    except Exception as e:
        logger.error(f"Failed to load Excel file: {e}")
        raise ValueError(f"Cannot parse Excel file: {e}") from e


def load_csv_to_polars(
    file: BinaryIO | Path,
    encoding: str = "latin-1",
) -> pl.DataFrame:
    """Load CSV file into Polars DataFrame.

    Args:
        file: File path or file-like object.
        encoding: Character encoding (CMS files use latin-1).

    Returns:
        Polars DataFrame with loaded data.

    Raises:
        ValueError: If file cannot be parsed as CSV.
    """
    logger.info(f"Loading CSV file with encoding: {encoding}")

    try:
        if isinstance(file, Path):
            df = pl.read_csv(file, encoding=encoding, infer_schema_length=10000)
        else:
            # File-like object - read bytes and parse
            content = file.read()
            df = pl.read_csv(content, encoding=encoding, infer_schema_length=10000)

        logger.info(f"Loaded {df.height} rows, {df.width} columns")
        return df
    except Exception as e:
        logger.error(f"Failed to load CSV file: {e}")
        raise ValueError(f"Cannot parse CSV file: {e}") from e


def detect_file_type(filename: str) -> str:
    """Detect file type from filename extension.

    Args:
        filename: Name of the file.

    Returns:
        File type: "excel" or "csv".

    Raises:
        ValueError: If file type is not supported.
    """
    lower_name = filename.lower()
    if lower_name.endswith((".xlsx", ".xls")):
        return "excel"
    elif lower_name.endswith(".csv"):
        return "csv"
    else:
        raise ValueError(f"Unsupported file type: {filename}")
```

### `src/optimizer_340b/compute/margins.py`

```python
"""Margin calculation engine for 340B optimization."""

import logging
from decimal import Decimal
from typing import Optional

from optimizer_340b.models import Drug, MarginAnalysis, RecommendedPath

logger = logging.getLogger(__name__)

# Constants for margin calculations
MEDICARE_ASP_MULTIPLIER = Decimal("1.06")  # ASP + 6%
COMMERCIAL_ASP_MULTIPLIER = Decimal("1.15")  # ASP + 15% (conservative estimate)
DEFAULT_RETAIL_REIMB_RATE = Decimal("0.85")  # 85% of AWP (typical)
DEFAULT_CAPTURE_RATE = Decimal("0.45")  # 45% capture rate for retail


def calculate_retail_margin(
    drug: Drug,
    reimb_rate: Decimal = DEFAULT_RETAIL_REIMB_RATE,
    capture_rate: Decimal = DEFAULT_CAPTURE_RATE,
) -> tuple[Decimal, Decimal]:
    """Calculate retail pharmacy margin.

    Formula: (AWP * Reimb_Rate * Capture_Rate) - Contract_Cost

    Args:
        drug: Drug entity with AWP and contract cost.
        reimb_rate: Reimbursement rate as decimal (0.85 = 85% of AWP).
        capture_rate: Expected capture rate (0.45 = 45% of eligible claims).

    Returns:
        Tuple of (gross_margin, net_margin).
    """
    gross_margin = (drug.awp * reimb_rate) - drug.contract_cost
    net_margin = gross_margin * capture_rate
    return gross_margin, net_margin


def calculate_medicare_margin(drug: Drug) -> Optional[Decimal]:
    """Calculate Medicare Part B medical margin.

    Formula: (ASP * 1.06 * Bill_Units_Per_Package) - Contract_Cost

    Args:
        drug: Drug entity with ASP and billing units.

    Returns:
        Medicare margin or None if drug has no HCPCS mapping.
    """
    if not drug.has_medical_path():
        return None

    assert drug.asp is not None  # Guaranteed by has_medical_path()
    revenue = drug.asp * MEDICARE_ASP_MULTIPLIER * Decimal(drug.bill_units_per_package)
    margin = revenue - drug.contract_cost
    return margin


def calculate_commercial_margin(drug: Drug) -> Optional[Decimal]:
    """Calculate Commercial Medical margin.

    Formula: (ASP * 1.15 * Bill_Units_Per_Package) - Contract_Cost

    The 1.15 multiplier is conservative, accounting for:
    - Higher commercial rates (typically ASP+20%)
    - Adjusted down ~5% for denial compression

    Args:
        drug: Drug entity with ASP and billing units.

    Returns:
        Commercial margin or None if drug has no HCPCS mapping.
    """
    if not drug.has_medical_path():
        return None

    assert drug.asp is not None
    revenue = drug.asp * COMMERCIAL_ASP_MULTIPLIER * Decimal(drug.bill_units_per_package)
    margin = revenue - drug.contract_cost
    return margin


def determine_recommendation(
    retail_net: Decimal,
    medicare: Optional[Decimal],
    commercial: Optional[Decimal],
) -> tuple[RecommendedPath, Decimal]:
    """Determine the recommended pathway based on highest margin.

    Args:
        retail_net: Net retail margin (after capture rate).
        medicare: Medicare medical margin (or None).
        commercial: Commercial medical margin (or None).

    Returns:
        Tuple of (recommended_path, margin_delta).
    """
    options: list[tuple[RecommendedPath, Decimal]] = [
        (RecommendedPath.RETAIL, retail_net),
    ]

    if medicare is not None:
        options.append((RecommendedPath.MEDICARE_MEDICAL, medicare))

    if commercial is not None:
        options.append((RecommendedPath.COMMERCIAL_MEDICAL, commercial))

    # Sort by margin descending
    options.sort(key=lambda x: x[1], reverse=True)

    best_path, best_margin = options[0]

    # Calculate delta to second-best option
    if len(options) > 1:
        _, second_margin = options[1]
        delta = best_margin - second_margin
    else:
        delta = best_margin

    return best_path, delta


def analyze_drug_margin(
    drug: Drug,
    capture_rate: Decimal = DEFAULT_CAPTURE_RATE,
) -> MarginAnalysis:
    """Perform complete margin analysis for a drug.

    Args:
        drug: Drug entity to analyze.
        capture_rate: Retail capture rate assumption.

    Returns:
        Complete MarginAnalysis with recommendation.
    """
    logger.debug(f"Analyzing margins for {drug.drug_name} ({drug.ndc})")

    retail_gross, retail_net = calculate_retail_margin(drug, capture_rate=capture_rate)
    medicare = calculate_medicare_margin(drug)
    commercial = calculate_commercial_margin(drug)

    recommended, delta = determine_recommendation(retail_net, medicare, commercial)

    return MarginAnalysis(
        drug=drug,
        retail_gross_margin=retail_gross,
        retail_net_margin=retail_net,
        retail_capture_rate=capture_rate,
        medicare_margin=medicare,
        commercial_margin=commercial,
        recommended_path=recommended,
        margin_delta=delta,
    )
```

### `tests/conftest.py`

```python
"""Shared pytest fixtures for 340B Optimizer tests."""

import os
from decimal import Decimal
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import polars as pl
import pytest

from optimizer_340b.config import Settings
from optimizer_340b.models import DosingProfile, Drug, MarginAnalysis, RecommendedPath


@pytest.fixture
def mock_env_vars() -> Generator[dict[str, str], None, None]:
    """Set up mock environment variables for testing."""
    env_vars = {
        "LOG_LEVEL": "DEBUG",
        "DATA_DIR": "/tmp/test_data",
        "CACHE_ENABLED": "false",
        "CACHE_TTL_HOURS": "1",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        yield env_vars


@pytest.fixture
def test_settings(mock_env_vars: dict[str, str]) -> Settings:
    """Create test settings with mock values."""
    return Settings.from_env()


@pytest.fixture
def sample_drug() -> Drug:
    """Sample drug for testing - Humira-like profile."""
    return Drug(
        ndc="0074-4339-02",
        drug_name="HUMIRA",
        manufacturer="ABBVIE",
        contract_cost=Decimal("150.00"),
        awp=Decimal("6500.00"),
        asp=Decimal("2800.00"),
        hcpcs_code="J0135",
        bill_units_per_package=2,
        therapeutic_class="TNF Inhibitor",
        is_biologic=True,
        ira_flag=False,
        penny_pricing_flag=False,
    )


@pytest.fixture
def sample_drug_retail_only() -> Drug:
    """Sample drug without HCPCS mapping (retail only)."""
    return Drug(
        ndc="1234567890",
        drug_name="GENERIC ORAL",
        manufacturer="TEVA",
        contract_cost=Decimal("10.00"),
        awp=Decimal("100.00"),
        asp=None,
        hcpcs_code=None,
        bill_units_per_package=1,
        therapeutic_class="Generic",
        is_biologic=False,
        ira_flag=False,
        penny_pricing_flag=False,
    )


@pytest.fixture
def sample_drug_ira_flagged() -> Drug:
    """Sample drug subject to IRA price negotiation."""
    return Drug(
        ndc="5555555555",
        drug_name="ENBREL",
        manufacturer="AMGEN",
        contract_cost=Decimal("200.00"),
        awp=Decimal("7000.00"),
        asp=Decimal("3000.00"),
        hcpcs_code="J1438",
        bill_units_per_package=4,
        therapeutic_class="TNF Inhibitor",
        is_biologic=True,
        ira_flag=True,
        penny_pricing_flag=False,
    )


@pytest.fixture
def sample_dosing_profile() -> DosingProfile:
    """Sample dosing profile for Cosentyx-like drug."""
    return DosingProfile(
        drug_name="COSENTYX",
        indication="Psoriasis",
        year_1_fills=17,  # Loading: 5 fills in month 1, then monthly
        year_2_plus_fills=12,  # Monthly maintenance
        adjusted_year_1_fills=Decimal("15.3"),  # 90% compliance
    )


@pytest.fixture
def sample_catalog_df() -> pl.DataFrame:
    """Sample product catalog DataFrame."""
    return pl.DataFrame({
        "NDC": ["0074-4339-02", "1234567890", "5555555555"],
        "Drug Name": ["HUMIRA", "GENERIC ORAL", "ENBREL"],
        "Manufacturer": ["ABBVIE", "TEVA", "AMGEN"],
        "Contract Cost": [150.00, 10.00, 200.00],
        "AWP": [6500.00, 100.00, 7000.00],
    })


@pytest.fixture
def sample_asp_crosswalk_df() -> pl.DataFrame:
    """Sample ASP NDC-HCPCS crosswalk DataFrame."""
    return pl.DataFrame({
        "NDC": ["0074-4339-02", "5555555555"],
        "HCPCS Code": ["J0135", "J1438"],
        "Billing Units Per Package": [2, 4],
    })


@pytest.fixture
def sample_asp_pricing_df() -> pl.DataFrame:
    """Sample ASP pricing file DataFrame."""
    return pl.DataFrame({
        "HCPCS Code": ["J0135", "J1438"],
        "Payment Limit": [2800.00, 3000.00],
    })
```

---

## API Design

### Internal Data Flow API

This application does not expose external HTTP APIs. The internal data flow is:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FILE UPLOAD (Streamlit)                           │
│                  (XLSX: Catalog, Matrix, Biologics Grid)                    │
│                  (CSV: ASP Files, Crosswalk, NADAC)                         │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        BRONZE LAYER (Raw Ingestion)                          │
│                                                                              │
│   loaders.py                validators.py                                    │
│   ┌──────────────┐           ┌─────────────────────────────────┐            │
│   │ load_excel() │           │ validate_catalog_schema()       │            │
│   │ load_csv()   │───────────│ validate_asp_schema()           │            │
│   └──────────────┘           │ validate_crosswalk_schema()     │            │
│                              └─────────────────────────────────┘            │
│   Gatekeeper Tests:                                                          │
│   - Schema Integrity: Required columns present                               │
│   - Row Volume Audit: >40k rows for catalog                                  │
│   - Currency Check: ASP file quarter matches current                         │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SILVER LAYER (Normalization)                          │
│                                                                              │
│   normalizers.py                                                             │
│   ┌──────────────────────────────────────────────────────────────┐          │
│   │ normalize_ndc()         # 11-digit standardization           │          │
│   │ fuzzy_match_drug_names() # Match biologics grid to catalog   │          │
│   │ join_ndc_to_hcpcs()     # Crosswalk integration              │          │
│   └──────────────────────────────────────────────────────────────┘          │
│                                                                              │
│   Gatekeeper Tests:                                                          │
│   - Crosswalk Integrity: >95% infusible NDCs map to HCPCS                   │
│   - Clinical Map: Drug names fuzzy-match successfully                        │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        GOLD LAYER (Computation)                              │
│                                                                              │
│   margins.py              crosswalk.py              dosing.py               │
│   ┌───────────────┐       ┌───────────────┐        ┌────────────────┐       │
│   │ retail_margin │       │ build_golden_ │        │ apply_loading_ │       │
│   │ medicare_marg │       │ _record()     │        │ _dose_logic()  │       │
│   │ commercial_   │       └───────────────┘        └────────────────┘       │
│   │ _margin       │                                                          │
│   └───────────────┘                                                          │
│                                                                              │
│   Gatekeeper Tests:                                                          │
│   - Medicare Unit Test: Manual calc matches engine for Infliximab           │
│   - Commercial Unit Test: 1.15x multiplier correctly applied                 │
│   - Loading Dose Test: Cosentyx Year 1 = 17 fills, not 12                   │
│   - Capture Rate Test: 40% toggle reduces retail proportionally              │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      WATCHTOWER (Risk Flagging)                              │
│                                                                              │
│   ira_flags.py                         penny_pricing.py                      │
│   ┌────────────────────────┐           ┌──────────────────────────┐         │
│   │ check_ira_2026_list()  │           │ check_penny_pricing()    │         │
│   │ check_ira_2027_list()  │           │ get_nadac_floor_alerts() │         │
│   └────────────────────────┘           └──────────────────────────┘         │
│                                                                              │
│   Gatekeeper Tests:                                                          │
│   - Enbrel Simulation: IRA 2026 flag present                                │
│   - Penny Pricing: Flagged drugs excluded from "Top Opportunities"          │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      STREAMLIT UI (Presentation)                             │
│                                                                              │
│   ┌─────────────────┐    ┌────────────────────┐    ┌────────────────────┐   │
│   │   Upload Page   │    │  Optimization      │    │   Drug Detail      │   │
│   │                 │    │  Dashboard         │    │   Page             │   │
│   │ - File dropzone │    │                    │    │                    │   │
│   │ - Validation    │    │ - Ranked list      │    │ - Margin breakdown │   │
│   │   status        │    │ - Filter by class  │    │ - Capture slider   │   │
│   │ - Schema report │    │ - Risk badges      │    │ - Dosing projector │   │
│   └─────────────────┘    │ - Export CSV       │    │ - Provenance chain │   │
│                          └────────────────────┘    └────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE                                  │
│                         (Streamlit Web Application)                          │
│                                                                              │
│   ┌────────────┐     ┌─────────────────────┐     ┌──────────────────────┐   │
│   │   Upload   │     │    Dashboard        │     │    Drug Detail       │   │
│   │    Page    │────▶│    (Ranked List)    │────▶│    (Deep Dive)       │   │
│   └────────────┘     └─────────────────────┘     └──────────────────────┘   │
│         │                      │                           │                 │
└─────────┼──────────────────────┼───────────────────────────┼─────────────────┘
          │                      │                           │
          ▼                      ▼                           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SESSION STATE CACHE                                │
│                      (Pre-computed Golden Record)                            │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  34,000+ Drug Records with:                                          │   │
│   │  - NDC, Name, Manufacturer                                           │   │
│   │  - Contract Cost, AWP, ASP                                           │   │
│   │  - Retail Margin, Medicare Margin, Commercial Margin                 │   │
│   │  - Recommendation, Risk Flags                                        │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  │ On Upload Trigger
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        COMPUTATION PIPELINE                                  │
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   ┌────────────┐  │
│  │    BRONZE    │    │    SILVER    │    │     GOLD     │   │ WATCHTOWER │  │
│  │   (Ingest)   │───▶│ (Normalize)  │───▶│  (Compute)   │──▶│   (Risk)   │  │
│  │              │    │              │    │              │   │            │  │
│  │ - Load XLSX  │    │ - NDC clean  │    │ - Retail $   │   │ - IRA flag │  │
│  │ - Load CSV   │    │ - Name match │    │ - Medicare $ │   │ - Penny $  │  │
│  │ - Validate   │    │ - Join data  │    │ - Commerc. $ │   │            │  │
│  └──────────────┘    └──────────────┘    └──────────────┘   └────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          │ File Sources (Manual Upload)
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA SOURCES                                       │
│                                                                              │
│   ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐       │
│   │ Wholesaler        │  │ CMS ASP           │  │ NADAC             │       │
│   │ Catalog           │  │ Pricing           │  │ Statistics        │       │
│   │ (34k NDCs)        │  │ (1k HCPCS)        │  │ (33k NDCs)        │       │
│   └───────────────────┘  └───────────────────┘  └───────────────────┘       │
│                                                                              │
│   ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐       │
│   │ Product           │  │ NDC-HCPCS         │  │ Biologics         │       │
│   │ Catalog           │  │ Crosswalk         │  │ Logic Grid        │       │
│   │ (47k rows)        │  │ (8k mappings)     │  │ (64 drugs)        │       │
│   └───────────────────┘  └───────────────────┘  └───────────────────┘       │
│                                                                              │
│   ┌───────────────────┐  ┌───────────────────┐                              │
│   │ NOC Pricing       │  │ NOC Crosswalk     │  (Optional fallback for      │
│   │ (Payment limits   │  │ (NDC mappings for │   drugs without J-codes)     │
│   │  for NOC drugs)   │  │  NOC drugs)       │                              │
│   └───────────────────┘  └───────────────────┘                              │
│                                                                              │
│   ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐       │
│   │ AWP Matrix        │  │ Wholesaler        │  │ IRA Drug List     │       │
│   │ (Payer-specific   │  │ Catalog           │  │ (Data-driven      │       │
│   │  multipliers)     │  │ (Retail valid.)   │  │  IRA 2026/2027)   │       │
│   └───────────────────┘  └───────────────────┘  └───────────────────┘       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Security Considerations

1. **No External API Keys Required**
   - All data is uploaded manually by users
   - No credentials stored or transmitted

2. **Data Privacy**
   - Uploaded files are processed in-memory
   - Files are not persisted beyond the session (unless explicitly saved)
   - No PHI or patient data processed — only drug pricing data

3. **Input Validation**
   - All uploaded files validated against expected schemas
   - File size limits enforced (max 50MB per file)
   - Malformed files rejected with clear error messages

4. **Session Isolation**
   - Each Streamlit session maintains isolated state
   - No cross-session data leakage

5. **Sensitive Data Handling**
   - Contract costs are proprietary — not logged or displayed in error messages
   - No data exported without explicit user action

---

## Performance Considerations

1. **Batch Pre-Computation**
   - The "Golden Record" (34k+ drugs) is computed once on file upload
   - Subsequent queries read from in-memory cache
   - Target: <10 seconds for full pipeline on initial load

2. **Polars for Heavy Lifting**
   - All DataFrame operations use Polars (not pandas) for batch processing
   - Lazy evaluation where beneficial
   - Columnar storage for efficient filtering

3. **Interactive Query Speed**
   - Target: <30 seconds for drug lookup (per Success Metric #1)
   - Capture rate slider recalculates in real-time (<100ms)
   - Filtering and sorting leverage pre-computed indices

4. **Memory Management**
   - Large DataFrames (NADAC: 33k rows × 44 cols) loaded on-demand
   - Unused columns dropped after join operations
   - Session state cleared on file re-upload

5. **Caching Strategy**
   - Streamlit `@st.cache_data` for expensive computations
   - TTL-based invalidation (configurable, default 24h)
   - Manual cache clear on data refresh

---

## Success Metrics Alignment

| Metric | Target | Implementation |
|--------|--------|----------------|
| **Optimization Velocity** | <30s drug lookup | Pre-computed Golden Record + indexed search |
| **Financial Accuracy** | +/- 5% vs historical | Gatekeeper unit tests with manual verification |
| **Auditability** | Full provenance chain | Each margin shows source file + calculation logic |
| **Extensibility** | New ASP file without code change | Schema-driven loader with column mapping config |

---

## Implementation Status (January 2026)

### Completed Features

| Feature | Status | Notes |
|---------|--------|-------|
| File upload interface | ✅ Complete | XLSX/CSV with validation |
| Sample data loading | ✅ Complete | One-click "Load & Process" demo |
| Schema validation | ✅ Complete | Clear error messages |
| NDC-HCPCS crosswalk | ✅ Complete | ~14% match rate (infusibles) |
| NOC fallback pricing | ✅ Complete | For drugs without J-codes |
| Retail margin calculation | ✅ Complete | AWP × 0.85 formula |
| Medicare margin (ASP+6%) | ✅ Complete | With billing units |
| Commercial margin (ASP+15%) | ✅ Complete | With billing units |
| Capture rate slider | ✅ Complete | Real-time recalculation |
| IRA drug detection | ✅ Complete | Data-driven from CSV (2026/2027 drugs) |
| Penny pricing alerts | ✅ Complete | NADAC-based detection with cost override |
| AWP payer multipliers | ✅ Complete | Ravenswood matrix (Brand/Generic/Specialty) |
| Retail price validation | ✅ Complete | Wholesaler catalog comparison |
| NDC format handling | ✅ Complete | Supports 11-digit and 5-4-2 dash formats |
| Dashboard with filters | ✅ Complete | Search, min delta, IRA filter |
| Drug detail view | ✅ Complete | Sensitivity analysis, provenance |
| Loading dose modeling | ✅ Complete | Year 1 vs Maintenance |

### Implementation Decisions & Changes

1. **Navigation System**
   - Original: Streamlit page-based routing
   - Implemented: Sidebar radio buttons (avoids conflicts with auto-discovery)

2. **Retail Margin Formula**
   - Formula: `AWP × 0.85 - Contract Cost` (industry standard discount)
   - Net margin: `Gross × Capture Rate`

3. **CMS File Handling**
   - ASP Pricing and Crosswalk files have 8 header rows (metadata)
   - Automatic column mapping for quarterly variations

4. **Data Validation Robustness**
   - ASP pricing files may contain "N/A" values (safely skipped)
   - Column name variations handled via normalizers

5. **Streamlit Configuration**
   - `.streamlit/config.toml` disables auto-page navigation
   - Session state persists data across page switches

6. **NDC Handling**
   - All NDC columns read as strings to preserve leading zeros
   - Search supports both 11-digit (`12345678901`) and 5-4-2 (`12345-6789-01`) formats
   - Normalization via `normalize_ndc()` strips dashes and pads to 11 digits

7. **IRA Drug List (Data-Driven)**
   - IRA drugs loaded from `data/sample/ira_drug_list.csv` at runtime
   - Supports dynamic updates without code changes
   - Fallback to hardcoded values if CSV not found
   - Can be reloaded via `reload_ira_drugs()` function

8. **Payer-Specific AWP Multipliers**
   - Ravenswood matrix provides multipliers by drug category and payer
   - Categories: Generic (15% AWP), Brand (84% AWP), Specialty (86% AWP)
   - Falls back to 85% AWP if matrix not loaded

### Test Coverage

| Module | Coverage | Notes |
|--------|----------|-------|
| `compute/margins.py` | 95% | Core calculations |
| `compute/dosing.py` | 90% | Loading dose logic |
| `ingest/loaders.py` | 95% | File I/O |
| `ingest/normalizers.py` | 91% | Data cleaning |
| `ingest/validators.py` | 99% | Schema checks |
| `risk/ira_flags.py` | 100% | IRA detection |
| `risk/penny_pricing.py` | 93% | NADAC checks |
| `models.py` | 100% | Data models |
| **UI modules** | 0% | Manual testing only |

### Known Limitations

1. **Performance**: Dashboard re-calculates on each page load (no persistent cache)
2. **Export**: CSV export not yet implemented in UI
3. **Crosswalk Rate**: Only ~14% of drugs match (expected for infusibles only)
