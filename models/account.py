from dataclasses import dataclass
from typing import Optional

from .database import get_db


CATEGORIES = ("retirement", "non_retirement", "trust", "liability")
OWNERS = ("client1", "client2", "joint")
SACS_ROLES = ("inflow", "outflow", "private_reserve", "investment")


ACCOUNT_TYPE_OPTIONS = {
    "retirement": [
        "IRA", "Roth IRA", "401K", "Pension", "403(b)", "SEP IRA", "Other",
    ],
    "non_retirement": [
        "Wells Fargo Checking", "Wells Fargo Savings",
        "StoneCastle FICA",
        "Pinnacle Inflow", "Pinnacle Outflow", "Pinnacle Private Reserve",
        "Schwab Brokerage", "Schwab JT TEN", "Schwab IRA",
        "Fidelity", "E-Trade", "Vanguard",
        "Other Checking", "Other Savings", "Other Brokerage",
    ],
    "trust": [
        "Family Trust", "Living Trust", "Other Trust",
    ],
    "liability": [
        "Primary Mortgage", "Secondary Mortgage", "Auto Loan",
        "Credit Card", "Medical Debt", "Student Loan", "Other",
    ],
}


def auto_sacs_role(account_type: str) -> Optional[str]:
    """Suggest a SACS role based on account type name."""
    if not account_type:
        return None
    t = account_type.lower()
    if "pinnacle inflow" in t:
        return "inflow"
    if "pinnacle outflow" in t:
        return "outflow"
    if "pinnacle private reserve" in t or "stonecastle" in t:
        return "private_reserve"
    if "schwab brokerage" in t or "schwab ira" in t:
        return "investment"
    return None


@dataclass
class Account:
    id: Optional[int]
    client_id: int
    category: str
    owner: Optional[str]
    account_type: str
    account_number_last4: Optional[str]
    sacs_role: Optional[str]
    property_address: Optional[str]
    interest_rate: Optional[float]
    last_balance: Optional[float]
    last_cash_balance: Optional[float]
    last_value_date: Optional[str]
    sort_order: int

    @staticmethod
    def from_row(row) -> "Account":
        return Account(
            id=row["id"],
            client_id=row["client_id"],
            category=row["category"],
            owner=row["owner"],
            account_type=row["account_type"],
            account_number_last4=row["account_number_last4"],
            sacs_role=row["sacs_role"],
            property_address=row["property_address"],
            interest_rate=row["interest_rate"],
            last_balance=row["last_balance"],
            last_cash_balance=row["last_cash_balance"],
            last_value_date=row["last_value_date"],
            sort_order=row["sort_order"] or 0,
        )


def list_accounts(client_id: int) -> list[Account]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT * FROM accounts WHERE client_id = ?
            ORDER BY
              CASE category
                WHEN 'retirement' THEN 1
                WHEN 'non_retirement' THEN 2
                WHEN 'trust' THEN 3
                WHEN 'liability' THEN 4
                ELSE 5
              END,
              CASE owner WHEN 'client1' THEN 1 WHEN 'client2' THEN 2 WHEN 'joint' THEN 3 ELSE 4 END,
              sort_order, id
            """,
            (client_id,),
        ).fetchall()
    return [Account.from_row(r) for r in rows]


def get_account(account_id: int) -> Optional[Account]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM accounts WHERE id = ?", (account_id,)
        ).fetchone()
    return Account.from_row(row) if row else None


def _opt_float(v):
    """Convert to float, but preserve 0; only None/empty-string becomes None."""
    if v is None or v == "":
        return None
    return float(v)


def create_account(client_id: int, data: dict) -> int:
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO accounts (
                client_id, category, owner, account_type, account_number_last4,
                sacs_role, property_address, interest_rate,
                last_balance, last_cash_balance, last_value_date, sort_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                client_id,
                data["category"],
                data.get("owner") or None,
                data["account_type"],
                data.get("account_number_last4") or None,
                data.get("sacs_role") or None,
                data.get("property_address") or None,
                _opt_float(data.get("interest_rate")),
                _opt_float(data.get("last_balance")),
                _opt_float(data.get("last_cash_balance")),
                data.get("last_value_date") or None,
                int(data.get("sort_order") or 0),
            ),
        )
        return cur.lastrowid


def delete_account(account_id: int) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))


def update_account_snapshot(
    account_id: int,
    balance: Optional[float],
    cash_balance: Optional[float],
    value_date: Optional[str],
) -> None:
    """Cache the latest entered values after a report is generated."""
    with get_db() as conn:
        conn.execute(
            """
            UPDATE accounts
            SET last_balance = ?, last_cash_balance = ?, last_value_date = ?
            WHERE id = ?
            """,
            (balance, cash_balance, value_date, account_id),
        )
