import json
from dataclasses import dataclass
from typing import Optional

from .database import get_db


@dataclass
class Report:
    id: Optional[int]
    client_id: int
    generated_at: str
    report_date: str
    snapshot: dict

    @staticmethod
    def from_row(row) -> "Report":
        return Report(
            id=row["id"],
            client_id=row["client_id"],
            generated_at=row["generated_at"],
            report_date=row["report_date"],
            snapshot=json.loads(row["snapshot_json"]),
        )


def list_reports(client_id: int) -> list[Report]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM reports WHERE client_id = ? ORDER BY generated_at DESC",
            (client_id,),
        ).fetchall()
    return [Report.from_row(r) for r in rows]


def get_report(report_id: int) -> Optional[Report]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM reports WHERE id = ?", (report_id,)
        ).fetchone()
    return Report.from_row(row) if row else None


def last_report_for_client(client_id: int) -> Optional[Report]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM reports WHERE client_id = ? ORDER BY generated_at DESC LIMIT 1",
            (client_id,),
        ).fetchone()
    return Report.from_row(row) if row else None


def create_report(client_id: int, report_date: str, snapshot: dict) -> int:
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO reports (client_id, report_date, snapshot_json) VALUES (?, ?, ?)",
            (client_id, report_date, json.dumps(snapshot)),
        )
        return cur.lastrowid
