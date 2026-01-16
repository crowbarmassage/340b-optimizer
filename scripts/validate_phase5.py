#!/usr/bin/env python
"""Validate Phase 5 functionality - Risk Flagging (Watchtower Layer)."""

import polars as pl

from optimizer_340b.risk import (
    IRA_2026_DRUGS,
    IRA_2027_DRUGS,
    check_ira_status,
    check_penny_pricing,
    filter_top_opportunities,
)


def main() -> None:
    print("=" * 60)
    print("Phase 5 Validation: Risk Flagging (Watchtower Layer)")
    print("=" * 60)

    # Gatekeeper Test 1: Enbrel Simulation
    print("\n[TEST 1] Enbrel Simulation (IRA 2026)")
    print("-" * 40)
    enbrel_status = check_ira_status("ENBREL")
    print(f"  is_ira_drug: {enbrel_status['is_ira_drug']}")
    print(f"  ira_year: {enbrel_status['ira_year']}")
    print(f"  risk_level: {enbrel_status['risk_level']}")
    print(f"  warning: {enbrel_status['warning_message']}")

    assert enbrel_status["is_ira_drug"] is True, "FAIL: Enbrel not flagged as IRA drug"
    assert enbrel_status["ira_year"] == 2026, "FAIL: Wrong IRA year for Enbrel"
    assert enbrel_status["risk_level"] == "High Risk", "FAIL: Wrong risk level"
    print("  ✅ PASSED: Enbrel correctly flagged as IRA 2026 High Risk")

    # Test IRA 2027 drugs
    print("\n[TEST 2] IRA 2027 Detection (Ozempic)")
    print("-" * 40)
    ozempic_status = check_ira_status("OZEMPIC")
    print(f"  is_ira_drug: {ozempic_status['is_ira_drug']}")
    print(f"  ira_year: {ozempic_status['ira_year']}")

    assert ozempic_status["is_ira_drug"] is True, "FAIL: Ozempic not flagged"
    assert ozempic_status["ira_year"] == 2027, "FAIL: Wrong IRA year for Ozempic"
    print("  ✅ PASSED: Ozempic correctly flagged as IRA 2027")

    # Test non-IRA drug
    print("\n[TEST 3] Non-IRA Drug (Humira)")
    print("-" * 40)
    humira_status = check_ira_status("HUMIRA")
    print(f"  is_ira_drug: {humira_status['is_ira_drug']}")
    print(f"  risk_level: {humira_status['risk_level']}")

    assert humira_status["is_ira_drug"] is False, "FAIL: Humira incorrectly flagged"
    assert humira_status["risk_level"] == "Low Risk", "FAIL: Wrong risk level"
    print("  ✅ PASSED: Humira correctly identified as non-IRA (Low Risk)")

    # Gatekeeper Test 2: Penny Pricing Alert
    print("\n[TEST 4] Penny Pricing Alert")
    print("-" * 40)
    nadac_df = pl.DataFrame({
        "ndc": ["1111111111", "2222222222", "3333333333"],
        "penny_pricing": [True, False, False],
        "total_discount_340b_pct": [99.9, 50.0, 96.0],
    })

    flagged = check_penny_pricing(nadac_df)
    print("  Total drugs: 3")
    print(f"  Penny-priced drugs found: {len(flagged)}")

    assert len(flagged) == 2, "FAIL: Should find 2 penny-priced drugs"
    print("  ✅ PASSED: Penny pricing detection working")

    # Test filtering Top Opportunities
    print("\n[TEST 5] Filter Top Opportunities (Exclude Penny Pricing)")
    print("-" * 40)
    opportunities: list[dict[str, object]] = [
        {"ndc": "AAA", "margin": 1000, "penny_pricing": False},
        {"ndc": "BBB", "margin": 5000, "penny_pricing": True},  # High margin but penny
        {"ndc": "CCC", "margin": 2000, "penny_pricing": False},
    ]

    filtered = filter_top_opportunities(opportunities)
    print("  Original opportunities: 3")
    print(f"  After filtering: {len(filtered)}")

    filtered_ndcs = {item["ndc"] for item in filtered}
    assert "BBB" not in filtered_ndcs, "FAIL: Penny-priced drug not excluded"
    assert len(filtered) == 2, "FAIL: Wrong number of opportunities"
    print("  ✅ PASSED: Penny-priced drugs excluded from Top Opportunities")

    # Summary
    print("\n" + "=" * 60)
    print("IRA Drug Lists Summary")
    print("=" * 60)
    print(f"  IRA 2026 drugs: {len(IRA_2026_DRUGS)}")
    print(f"  IRA 2027 drugs: {len(IRA_2027_DRUGS)}")
    print(f"  Total IRA drugs: {len(IRA_2026_DRUGS) + len(IRA_2027_DRUGS)}")

    print("\n" + "=" * 60)
    print("✅ ALL PHASE 5 GATEKEEPER TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
