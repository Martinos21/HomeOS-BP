"""
SQLite vrstva pro Zigbee zarizeni.

- tabulka `devices` = registr zarizeni (IEEE adresa -> nazev -> nazev tabulky)
- pro kazde zarizeni vlastni tabulka `dev_<nazev>` s merenimi (at, metric, value)

Zarizeni se identifikuje IEEE adresou (unikatni, vypalena v cipu). Nazev se
vezme z Model ID, ktery ESP posila v Basic clusteru (setManufacturerAndModel).
Jakmile je zarizeni jednou zaregistrovane, jeho nazev i tabulka zustavaji
stejne, i kdyz se ESP preflashuje s jinym nazvem.
"""

import os
import re
import sqlite3
from datetime import datetime, timezone

DB_PATH = (
    os.environ.get("HOMEOS_DB_PATH")
    or os.environ.get("STATS_DB_PATH")
    or "/home/pi/homeos.db"
)

TABLE_PREFIX = "dev_"


def iso_now() -> str:
    """Stejny format jako solarAPI: 2026-06-19T08:45:00.519Z"""
    dt = datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def sanitize(name: str) -> str:
    """'Obyvak Teplota-1' -> 'obyvak_teplota_1' (jen a-z, 0-9, _)."""
    name = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return name[:40]


def ieee_suffix(ieee: str) -> str:
    return ieee.replace(":", "")[-4:].lower()


class Database:
    def __init__(self, path: str = DB_PATH):
        self.conn = sqlite3.connect(path, timeout=10)
        # WAL: zigbee sluzba, solarAPI i backend muzou do jednoho souboru naraz
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS devices (
                ieee         TEXT PRIMARY KEY,
                name         TEXT NOT NULL UNIQUE,
                table_name   TEXT NOT NULL UNIQUE,
                kind         TEXT,
                manufacturer TEXT,
                model        TEXT,
                first_seen   TEXT NOT NULL,
                last_seen    TEXT NOT NULL
            )
            """
        )
        self.conn.commit()
        self._tables = {}  # ieee -> table_name (cache)

    def register_device(self, ieee: str, model: str | None,
                        manufacturer: str | None, kind: str) -> str:
        """Vrati nazev tabulky zarizeni; pri prvnim pripojeni ji vytvori."""
        row = self.conn.execute(
            "SELECT table_name FROM devices WHERE ieee = ?", (ieee,)
        ).fetchone()
        if row:
            table = row[0]
            self.conn.execute(
                "UPDATE devices SET kind = ?, manufacturer = ?, model = ?, "
                "last_seen = ? WHERE ieee = ?",
                (kind, manufacturer, model, iso_now(), ieee),
            )
        else:
            name = self._free_name(sanitize(model or "") or f"zb_{ieee_suffix(ieee)}", ieee)
            table = TABLE_PREFIX + name
            now = iso_now()
            self.conn.execute(
                "INSERT INTO devices (ieee, name, table_name, kind, manufacturer,"
                " model, first_seen, last_seen) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (ieee, name, table, kind, manufacturer, model, now, now),
            )
            print(f"[DB] nove zarizeni {ieee} -> tabulka {table}")

        # table je vzdy nas vlastni sanitizovany nazev, proto je f-string bezpecny
        self.conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS "{table}" (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                at     TEXT NOT NULL,
                metric TEXT NOT NULL,
                value  REAL NOT NULL
            )
            """
        )
        self.conn.execute(
            f'CREATE INDEX IF NOT EXISTS "{table}_at" ON "{table}" (metric, at)'
        )
        self.conn.commit()
        self._tables[ieee] = table
        return table

    def _free_name(self, base: str, ieee: str) -> str:
        """Kdyz uz nazev ma jine zarizeni, prida konec IEEE adresy."""
        taken = self.conn.execute(
            "SELECT 1 FROM devices WHERE name = ?", (base,)
        ).fetchone()
        return f"{base}_{ieee_suffix(ieee)}" if taken else base

    def insert(self, ieee: str, metric: str, value: float):
        table = self._tables.get(ieee)
        if table is None:
            return  # zarizeni jeste neni zaregistrovane
        now = iso_now()
        self.conn.execute(
            f'INSERT INTO "{table}" (at, metric, value) VALUES (?, ?, ?)',
            (now, metric, float(value)),
        )
        self.conn.execute(
            "UPDATE devices SET last_seen = ? WHERE ieee = ?", (now, ieee)
        )
        self.conn.commit()

    def ieee_by_name(self, name: str) -> str | None:
        row = self.conn.execute(
            "SELECT ieee FROM devices WHERE name = ?", (name,)
        ).fetchone()
        return row[0] if row else None
