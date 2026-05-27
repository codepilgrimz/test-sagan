"""
Seed the database with the "Sample Client" from the TCC screenshot, plus a
fully-populated quarterly report so PDFs can be generated immediately.

Run from the project root:
    python -m db.seed_sample
"""
from __future__ import annotations

from datetime import date

from models import account as account_model
from models import client as client_model
from models import report as report_model
from models.database import init_db, get_db
from services import calculations


SAMPLE_REPORT_DATE = "2023-07-26"


def seed():
    init_db()

    # Skip if the sample is already there
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM clients WHERE client1_name = ? AND client2_name = ?",
            ("Sample Client 1", "Sample Client 2"),
        ).fetchone()
    if row:
        print(f"Sample Client already seeded (id={row['id']}). Skipping.")
        return row["id"]

    client_id = client_model.create_client({
        "client1_name": "Sample Client 1",
        "client1_dob": "1975-04-15",
        "client1_ssn_last4": "1234",
        "client1_salary": 8000,
        "client2_name": "Sample Client 2",
        "client2_dob": "1977-09-22",
        "client2_ssn_last4": "5678",
        "client2_salary": 7000,
        "monthly_outflow": 12000,
        "insurance_deductibles_total": 4000,
        "account_floor": 1000,
    })
    print(f"Created Sample Client (id={client_id}).")

    # Accounts from the TCC screenshot
    accounts_data = [
        # Client 1 retirement
        {"category": "retirement", "owner": "client1", "account_type": "Roth IRA",
         "last_balance": 11162.47, "last_cash_balance": 316, "last_value_date": "2023-07-25"},
        {"category": "retirement", "owner": "client1", "account_type": "IRA",
         "last_balance": 0, "last_value_date": "2023-07-25"},
        # Client 2 retirement
        {"category": "retirement", "owner": "client2", "account_type": "IRA",
         "last_balance": 37232.46, "last_cash_balance": 914, "last_value_date": "2023-07-25"},
        {"category": "retirement", "owner": "client2", "account_type": "401K",
         "last_balance": 70042, "last_value_date": "2023-04-01"},
        {"category": "retirement", "owner": "client2", "account_type": "Roth IRA",
         "last_balance": 18885.92, "last_cash_balance": 508, "last_value_date": "2023-07-25"},
        # Non-retirement (joint + client2)
        {"category": "non_retirement", "owner": "joint", "account_type": "Wells Fargo Checking",
         "last_balance": 448.26, "last_value_date": "2023-05-23"},
        {"category": "non_retirement", "owner": "joint", "account_type": "StoneCastle FICA",
         "last_balance": 44067.78, "last_value_date": "2023-07-25"},
        {"category": "non_retirement", "owner": "joint", "account_type": "Wells Fargo Savings",
         "last_balance": 44024, "last_value_date": "2023-05-23"},
        {"category": "non_retirement", "owner": "joint", "account_type": "Schwab JT TEN",
         "sacs_role": "investment", "last_balance": 0, "last_value_date": "2023-07-25"},
        {"category": "non_retirement", "owner": "client2", "account_type": "Pinnacle Inflow",
         "sacs_role": "inflow", "last_balance": 980, "last_value_date": "2023-07-25"},
        {"category": "non_retirement", "owner": "client2", "account_type": "Pinnacle Outflow",
         "sacs_role": "outflow", "last_balance": 12990, "last_value_date": "2023-07-25"},
        {"category": "non_retirement", "owner": "client2", "account_type": "Pinnacle Private Reserve",
         "sacs_role": "private_reserve", "last_balance": 86788, "last_value_date": "2023-07-25"},
        # Trust
        {"category": "trust", "account_type": "Family Trust", "property_address": "123 Sample St",
         "last_balance": 0, "last_value_date": "2023-07-25"},
        # Liabilities
        {"category": "liability", "account_type": "Primary Mortgage", "interest_rate": 4.25,
         "last_balance": 224218.24},
        {"category": "liability", "account_type": "Secondary Mortgage", "interest_rate": 5.5,
         "last_balance": 107587.31},
        {"category": "liability", "account_type": "Mercedes", "interest_rate": 6.0,
         "last_balance": 11152.00},
        {"category": "liability", "account_type": "GMC Sierra", "interest_rate": 5.75,
         "last_balance": 25992.00},
        {"category": "liability", "account_type": "Escalade", "interest_rate": 6.25,
         "last_balance": 31627.52},
        {"category": "liability", "account_type": "PNC", "interest_rate": 21.99,
         "last_balance": 14026.00},
        {"category": "liability", "account_type": "Health", "interest_rate": 0,
         "last_balance": 1447.00},
    ]

    for a in accounts_data:
        account_model.create_account(client_id, a)
    print(f"Added {len(accounts_data)} accounts.")

    # Generate one report from the seeded data
    accounts = account_model.list_accounts(client_id)
    snapshot_accounts = []
    sacs_balances = {"private_reserve": None, "investment": None,
                     "private_reserve_date": None, "investment_date": None}
    for a in accounts:
        item = {
            "id": a.id,
            "category": a.category,
            "owner": a.owner,
            "account_type": a.account_type,
            "account_number_last4": a.account_number_last4,
            "sacs_role": a.sacs_role,
            "property_address": a.property_address,
            "interest_rate": a.interest_rate,
            "balance": a.last_balance,
            "cash_balance": a.last_cash_balance,
            "value_date": a.last_value_date,
            "stale": bool(a.last_value_date and a.last_value_date < SAMPLE_REPORT_DATE),
        }
        snapshot_accounts.append(item)
        if a.sacs_role == "private_reserve":
            sacs_balances["private_reserve"] = a.last_balance
            sacs_balances["private_reserve_date"] = a.last_value_date
        elif a.sacs_role == "investment":
            sacs_balances["investment"] = a.last_balance
            sacs_balances["investment_date"] = a.last_value_date

    sacs = calculations.sacs_totals(8000, 7000, 12000, 4000)
    tcc = calculations.tcc_totals(snapshot_accounts)
    snapshot = {
        "report_date": SAMPLE_REPORT_DATE,
        "client": {
            "client1_name": "Sample Client 1",
            "client1_dob": "1975-04-15",
            "client1_ssn_last4": "1234",
            "client1_age": client_model.calculate_age("1975-04-15"),
            "client1_salary": 8000,
            "client2_name": "Sample Client 2",
            "client2_dob": "1977-09-22",
            "client2_ssn_last4": "5678",
            "client2_age": client_model.calculate_age("1977-09-22"),
            "client2_salary": 7000,
            "monthly_outflow": 12000,
            "insurance_deductibles_total": 4000,
            "account_floor": 1000,
        },
        "sacs": {**sacs, **sacs_balances},
        "tcc": tcc,
        "accounts": snapshot_accounts,
    }
    report_id = report_model.create_report(client_id, SAMPLE_REPORT_DATE, snapshot)
    print(f"Created seed report (id={report_id}).")
    print(f"  Grand Total: ${tcc['grand_total']:,.2f}")
    print(f"  Liabilities: ${tcc['liabilities']:,.2f}")
    return client_id


if __name__ == "__main__":
    seed()
