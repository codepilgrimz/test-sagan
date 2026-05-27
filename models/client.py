from dataclasses import dataclass
from datetime import date
from typing import Optional

from .database import get_db


@dataclass
class Client:
    id: Optional[int]
    client1_name: str
    client1_dob: Optional[str]
    client1_ssn_last4: Optional[str]
    client1_salary: float
    client2_name: Optional[str]
    client2_dob: Optional[str]
    client2_ssn_last4: Optional[str]
    client2_salary: float
    monthly_outflow: float
    insurance_deductibles_total: float
    account_floor: float

    @property
    def monthly_inflow(self) -> float:
        return (self.client1_salary or 0) + (self.client2_salary or 0)

    @property
    def excess_to_private_reserve(self) -> float:
        return self.monthly_inflow - (self.monthly_outflow or 0)

    @property
    def private_reserve_target(self) -> float:
        return 6 * (self.monthly_outflow or 0) + (self.insurance_deductibles_total or 0)

    @property
    def display_name(self) -> str:
        if self.client2_name:
            return f"{self.client1_name} & {self.client2_name}"
        return self.client1_name

    @staticmethod
    def from_row(row) -> "Client":
        return Client(
            id=row["id"],
            client1_name=row["client1_name"],
            client1_dob=row["client1_dob"],
            client1_ssn_last4=row["client1_ssn_last4"],
            client1_salary=row["client1_salary"] or 0,
            client2_name=row["client2_name"],
            client2_dob=row["client2_dob"],
            client2_ssn_last4=row["client2_ssn_last4"],
            client2_salary=row["client2_salary"] or 0,
            monthly_outflow=row["monthly_outflow"] or 0,
            insurance_deductibles_total=row["insurance_deductibles_total"] or 0,
            account_floor=row["account_floor"] or 1000,
        )


def list_clients() -> list[Client]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM clients ORDER BY client1_name COLLATE NOCASE"
        ).fetchall()
    return [Client.from_row(r) for r in rows]


def get_client(client_id: int) -> Optional[Client]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM clients WHERE id = ?", (client_id,)
        ).fetchone()
    return Client.from_row(row) if row else None


def create_client(data: dict) -> int:
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO clients (
                client1_name, client1_dob, client1_ssn_last4, client1_salary,
                client2_name, client2_dob, client2_ssn_last4, client2_salary,
                monthly_outflow, insurance_deductibles_total, account_floor
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["client1_name"],
                data.get("client1_dob") or None,
                data.get("client1_ssn_last4") or None,
                float(data.get("client1_salary") or 0),
                data.get("client2_name") or None,
                data.get("client2_dob") or None,
                data.get("client2_ssn_last4") or None,
                float(data.get("client2_salary") or 0),
                float(data.get("monthly_outflow") or 0),
                float(data.get("insurance_deductibles_total") or 0),
                float(data.get("account_floor") or 1000),
            ),
        )
        return cur.lastrowid


def update_client(client_id: int, data: dict) -> None:
    with get_db() as conn:
        conn.execute(
            """
            UPDATE clients SET
                client1_name = ?, client1_dob = ?, client1_ssn_last4 = ?, client1_salary = ?,
                client2_name = ?, client2_dob = ?, client2_ssn_last4 = ?, client2_salary = ?,
                monthly_outflow = ?, insurance_deductibles_total = ?, account_floor = ?
            WHERE id = ?
            """,
            (
                data["client1_name"],
                data.get("client1_dob") or None,
                data.get("client1_ssn_last4") or None,
                float(data.get("client1_salary") or 0),
                data.get("client2_name") or None,
                data.get("client2_dob") or None,
                data.get("client2_ssn_last4") or None,
                float(data.get("client2_salary") or 0),
                float(data.get("monthly_outflow") or 0),
                float(data.get("insurance_deductibles_total") or 0),
                float(data.get("account_floor") or 1000),
                client_id,
            ),
        )


def delete_client(client_id: int) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))


def calculate_age(dob_str: Optional[str]) -> Optional[int]:
    if not dob_str:
        return None
    try:
        dob = date.fromisoformat(dob_str)
    except ValueError:
        return None
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
