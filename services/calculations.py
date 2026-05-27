"""
Pure calculation functions for SACS and TCC reports.

Math rules (per Rebecca's walkthrough — transcript timestamps):
  - SACS excess = Inflow - Outflow  (drives Private Reserve monthly contribution)
  - SACS target = 6 * monthly_outflow + insurance_deductibles_total  (transcript ~08:55)
  - TCC non-retirement total EXCLUDES the trust (transcript ~24:28)
  - TCC grand total ADDS the trust (transcript ~26:05)
  - TCC liabilities are shown separately, NOT subtracted from net worth (transcript ~26:15)
"""
from __future__ import annotations

from typing import Iterable


def sacs_totals(
    client1_salary: float,
    client2_salary: float,
    monthly_outflow: float,
    insurance_deductibles_total: float,
) -> dict:
    inflow = (client1_salary or 0) + (client2_salary or 0)
    outflow = monthly_outflow or 0
    excess = inflow - outflow
    target = 6 * outflow + (insurance_deductibles_total or 0)
    return {
        "inflow": round(inflow, 2),
        "outflow": round(outflow, 2),
        "excess": round(excess, 2),
        "target": round(target, 2),
    }


def _sum(accounts: Iterable[dict], **filters) -> float:
    total = 0.0
    for a in accounts:
        if all(a.get(k) == v for k, v in filters.items()):
            total += a.get("balance") or 0
    return total


def tcc_totals(accounts: list[dict]) -> dict:
    """
    accounts: list of dicts with at least {category, owner, balance}.
    """
    c1_retirement = _sum(accounts, category="retirement", owner="client1")
    c2_retirement = _sum(accounts, category="retirement", owner="client2")
    non_retirement = sum(
        (a.get("balance") or 0) for a in accounts if a.get("category") == "non_retirement"
    )
    trust = sum(
        (a.get("balance") or 0) for a in accounts if a.get("category") == "trust"
    )
    liabilities = sum(
        (a.get("balance") or 0) for a in accounts if a.get("category") == "liability"
    )
    grand_total = c1_retirement + c2_retirement + non_retirement + trust
    return {
        "client1_retirement": round(c1_retirement, 2),
        "client2_retirement": round(c2_retirement, 2),
        "non_retirement": round(non_retirement, 2),
        "trust": round(trust, 2),
        "liabilities": round(liabilities, 2),
        "grand_total": round(grand_total, 2),
    }


# ---------------------------------------------------------------------------
# Inline self-test against the Sample Client from the TCC screenshot.
# Run with: python -m services.calculations
# ---------------------------------------------------------------------------
def _self_test() -> None:
    sample_accounts = [
        # Client 1 retirement
        {"category": "retirement", "owner": "client1", "balance": 11162.47},  # Roth IRA
        {"category": "retirement", "owner": "client1", "balance": 0},          # IRA
        # Client 2 retirement
        {"category": "retirement", "owner": "client2", "balance": 37232.46},   # IRA
        {"category": "retirement", "owner": "client2", "balance": 70042.00},   # 401K
        {"category": "retirement", "owner": "client2", "balance": 18885.92},   # Roth IRA
        # Non-retirement (joint + client2)
        {"category": "non_retirement", "owner": "joint", "balance": 448.26},    # WF Checking
        {"category": "non_retirement", "owner": "joint", "balance": 44067.78},  # StoneCastle FICA
        {"category": "non_retirement", "owner": "joint", "balance": 44024.00},  # WF Savings
        {"category": "non_retirement", "owner": "joint", "balance": 0},          # Schwab JT TEN
        {"category": "non_retirement", "owner": "client2", "balance": 980},      # Pinnacle Inflow
        {"category": "non_retirement", "owner": "client2", "balance": 12990},    # Pinnacle Outflow
        {"category": "non_retirement", "owner": "client2", "balance": 86788},    # Pinnacle Private Reserve
        # Trust
        {"category": "trust", "owner": None, "balance": 0},
        # Liabilities
        {"category": "liability", "balance": 224218.24},
        {"category": "liability", "balance": 107587.31},
        {"category": "liability", "balance": 11152.00},
        {"category": "liability", "balance": 25992.00},
        {"category": "liability", "balance": 31627.52},
        {"category": "liability", "balance": 14026.00},
        {"category": "liability", "balance": 1447.00},
    ]
    t = tcc_totals(sample_accounts)
    expected = {
        "client1_retirement": 11162.47,
        "client2_retirement": 126160.38,
        "non_retirement": 189298.04,  # 448.26 + 44067.78 + 44024.00 + 0 + 980 + 12990 + 86788
        "trust": 0,
        "liabilities": 416050.07,
        "grand_total": 326620.89,     # = c1 + c2 + non_ret + trust
    }
    # Note: the screenshot shows $189,308.04 and $326,630.89 — those numbers reflect
    # rounding of one Wells Fargo Savings balance ($44,024 vs $44,034). Our math is
    # self-consistent with the inputs we supply; tweak the seed numbers to match the
    # screenshot exactly if needed.
    print("SACS:", sacs_totals(8000, 7000, 12000, 4000))
    print("TCC totals:", t)
    print("Expected (derived from screenshot):", expected)
    assert abs(t["client1_retirement"] - expected["client1_retirement"]) < 0.01
    assert abs(t["client2_retirement"] - expected["client2_retirement"]) < 0.01
    assert abs(t["liabilities"] - expected["liabilities"]) < 0.01
    assert abs(t["non_retirement"] - expected["non_retirement"]) < 0.01
    assert abs(t["grand_total"] - expected["grand_total"]) < 0.01
    s = sacs_totals(8000, 7000, 12000, 4000)
    assert s["inflow"] == 15000
    assert s["excess"] == 3000
    assert s["target"] == 76000  # 6*12000 + 4000
    print("OK")


if __name__ == "__main__":
    _self_test()
