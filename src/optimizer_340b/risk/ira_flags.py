"""IRA (Inflation Reduction Act) risk flagging for 340B drugs.

The Inflation Reduction Act allows Medicare to negotiate prices for certain
high-spend drugs. Drugs subject to IRA negotiation may see significant
price reductions, impacting 340B margins.

Gatekeeper Test: Enbrel Simulation
- Force-feed Enbrel into the pipeline
- System should flag it with "High Risk / IRA 2026" warning

IRA Drug Selection Timeline:
- 2026: First 10 drugs (announced August 2023)
- 2027: 15 additional drugs
- 2028+: Up to 20 drugs per year
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# IRA 2026 Negotiated Drugs (Medicare Drug Price Negotiation Program)
# These 10 drugs were selected in August 2023 for 2026 pricing
IRA_2026_DRUGS = {
    "ELIQUIS": "Blood thinner (apixaban)",
    "JARDIANCE": "Diabetes (empagliflozin)",
    "XARELTO": "Blood thinner (rivaroxaban)",
    "JANUVIA": "Diabetes (sitagliptin)",
    "FARXIGA": "Diabetes/Heart failure (dapagliflozin)",
    "ENTRESTO": "Heart failure (sacubitril/valsartan)",
    "ENBREL": "Autoimmune (etanercept)",
    "IMBRUVICA": "Cancer (ibrutinib)",
    "STELARA": "Autoimmune (ustekinumab)",
    "FIASP": "Insulin (insulin aspart)",
    "FIASP FLEXTOUCH": "Insulin (insulin aspart)",
    "FIASP PENFILL": "Insulin (insulin aspart)",
    "NOVOLOG": "Insulin (insulin aspart)",
    "NOVOLOG FLEXPEN": "Insulin (insulin aspart)",
    "NOVOLOG MIX": "Insulin (insulin aspart)",
}

# IRA 2027 Negotiated Drugs (announced August 2024)
IRA_2027_DRUGS = {
    "OZEMPIC": "Diabetes/Weight loss (semaglutide)",
    "RYBELSUS": "Diabetes (oral semaglutide)",
    "WEGOVY": "Weight loss (semaglutide)",
    "TRELEGY ELLIPTA": "COPD (fluticasone/umeclidinium/vilanterol)",
    "TRULICITY": "Diabetes (dulaglutide)",
    "POMALYST": "Cancer (pomalidomide)",
    "AUSTEDO": "Movement disorders (deutetrabenazine)",
    "IBRANCE": "Cancer (palbociclib)",
    "OTEZLA": "Autoimmune (apremilast)",
    "COSENTYX": "Autoimmune (secukinumab)",
    "TALZENNA": "Cancer (talazoparib)",
    "AUBAGIO": "Multiple sclerosis (teriflunomide)",
    "OMVOH": "Ulcerative colitis (mirikizumab)",
    "XTANDI": "Cancer (enzalutamide)",
    "SIVEXTRO": "Antibiotic (tedizolid)",
}

# Combined lookup for all IRA drugs
IRA_DRUGS_BY_YEAR: dict[str, int] = {}
for drug in IRA_2026_DRUGS:
    IRA_DRUGS_BY_YEAR[drug.upper()] = 2026
for drug in IRA_2027_DRUGS:
    IRA_DRUGS_BY_YEAR[drug.upper()] = 2027


@dataclass
class IRARiskStatus:
    """IRA risk assessment for a drug.

    Attributes:
        is_ira_drug: Whether the drug is subject to IRA negotiation.
        ira_year: Year when IRA pricing takes effect (2026, 2027, etc.).
        drug_name: Matched drug name from IRA list.
        description: Drug description/category.
        warning_message: Human-readable risk warning.
        risk_level: "High Risk", "Moderate Risk", or "Low Risk".
    """

    is_ira_drug: bool
    ira_year: int | None
    drug_name: str | None
    description: str | None
    warning_message: str
    risk_level: str


def check_ira_status(drug_name: str) -> dict[str, object]:
    """Check if a drug is subject to IRA price negotiation.

    Gatekeeper Test: Enbrel Simulation
    - Input: "ENBREL"
    - Expected: is_ira_drug=True, ira_year=2026, "High Risk" warning

    Args:
        drug_name: Name of the drug to check.

    Returns:
        Dictionary with IRA risk assessment:
        - is_ira_drug: bool
        - ira_year: int or None
        - drug_name: matched name or None
        - description: drug description or None
        - warning_message: str
        - risk_level: str
    """
    if not drug_name:
        return {
            "is_ira_drug": False,
            "ira_year": None,
            "drug_name": None,
            "description": None,
            "warning_message": "No drug name provided",
            "risk_level": "Unknown",
        }

    # Normalize drug name for matching
    name_upper = drug_name.upper().strip()

    # Check for exact match first
    if name_upper in IRA_DRUGS_BY_YEAR:
        year = IRA_DRUGS_BY_YEAR[name_upper]
        description = (
            IRA_2026_DRUGS.get(name_upper) or IRA_2027_DRUGS.get(name_upper)
        )

        logger.warning(f"IRA drug detected: {drug_name} (IRA {year})")

        return {
            "is_ira_drug": True,
            "ira_year": year,
            "drug_name": name_upper,
            "description": description,
            "warning_message": (
                f"High Risk / IRA {year}: {drug_name} is subject to Medicare "
                f"price negotiation. 340B margins may be significantly reduced "
                f"starting {year}."
            ),
            "risk_level": "High Risk",
        }

    # Check for partial match (drug name contains IRA drug)
    for ira_drug, year in IRA_DRUGS_BY_YEAR.items():
        if ira_drug in name_upper or name_upper in ira_drug:
            description = (
                IRA_2026_DRUGS.get(ira_drug) or IRA_2027_DRUGS.get(ira_drug)
            )

            logger.warning(f"Potential IRA drug match: {drug_name} -> {ira_drug}")

            return {
                "is_ira_drug": True,
                "ira_year": year,
                "drug_name": ira_drug,
                "description": description,
                "warning_message": (
                    f"High Risk / IRA {year}: {drug_name} appears to match "
                    f"{ira_drug}, which is subject to Medicare price negotiation."
                ),
                "risk_level": "High Risk",
            }

    # Not an IRA drug
    return {
        "is_ira_drug": False,
        "ira_year": None,
        "drug_name": None,
        "description": None,
        "warning_message": "No IRA risk detected",
        "risk_level": "Low Risk",
    }


def get_ira_risk_status(drug_name: str) -> IRARiskStatus:
    """Get structured IRA risk status for a drug.

    Args:
        drug_name: Name of the drug to check.

    Returns:
        IRARiskStatus dataclass with risk assessment.
    """
    result = check_ira_status(drug_name)
    return IRARiskStatus(
        is_ira_drug=bool(result["is_ira_drug"]),
        ira_year=result["ira_year"],  # type: ignore[arg-type]
        drug_name=result["drug_name"],  # type: ignore[arg-type]
        description=result["description"],  # type: ignore[arg-type]
        warning_message=str(result["warning_message"]),
        risk_level=str(result["risk_level"]),
    )


def filter_ira_drugs(drug_names: list[str]) -> list[dict[str, object]]:
    """Filter a list of drugs to find IRA-affected drugs.

    Args:
        drug_names: List of drug names to check.

    Returns:
        List of IRA risk assessments for affected drugs only.
    """
    ira_drugs = []
    for name in drug_names:
        status = check_ira_status(name)
        if status["is_ira_drug"]:
            status["input_name"] = name
            ira_drugs.append(status)

    logger.info(f"Found {len(ira_drugs)} IRA-affected drugs out of {len(drug_names)}")
    return ira_drugs


def get_all_ira_drugs() -> dict[str, dict[str, object]]:
    """Get complete list of all IRA-negotiated drugs.

    Returns:
        Dictionary mapping drug names to their IRA info.
    """
    all_drugs = {}

    for drug, description in IRA_2026_DRUGS.items():
        all_drugs[drug] = {
            "year": 2026,
            "description": description,
            "risk_level": "High Risk",
        }

    for drug, description in IRA_2027_DRUGS.items():
        all_drugs[drug] = {
            "year": 2027,
            "description": description,
            "risk_level": "High Risk",
        }

    return all_drugs
