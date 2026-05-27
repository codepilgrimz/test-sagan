import sqlite3
from contextlib import contextmanager
from pathlib import Path

import config


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_db():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    schema_path = Path(__file__).resolve().parent.parent / "db" / "schema.sql"
    with get_db() as conn:
        conn.executescript(schema_path.read_text())
