import sqlite3
import json
import time
from pathlib import Path

DB_PATH = Path.home() / ".cache" / "phone_lookup" / "cache.db"
DEFAULT_TTL = 60 * 60 * 24 * 7  # 7 days


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS lookups (
            e164      TEXT PRIMARY KEY,
            data      TEXT NOT NULL,
            cached_at REAL NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def get(e164: str, ttl: int = DEFAULT_TTL) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT data, cached_at FROM lookups WHERE e164 = ?", (e164,)
        ).fetchone()
    if not row:
        return None
    data, cached_at = row
    if time.time() - cached_at > ttl:
        return None
    return json.loads(data)


def put(e164: str, data: dict) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO lookups (e164, data, cached_at) VALUES (?, ?, ?)",
            (e164, json.dumps(data), time.time()),
        )


def clear(e164: str | None = None) -> None:
    with _conn() as conn:
        if e164:
            conn.execute("DELETE FROM lookups WHERE e164 = ?", (e164,))
        else:
            conn.execute("DELETE FROM lookups")
