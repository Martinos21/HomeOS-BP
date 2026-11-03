"""
Databaze HomeOS pro Zigbee zarizeni (SQLite).

  devices          registr: IEEE adresa -> nazev -> nazev tabulky
  dev_<nazev>      jedna tabulka pro kazde ESP, jeden sloupec pro kazdou hodnotu
                   napr. dev_obyvak_teplota(id, at, temperature, humidity)

Nazev posila ESP jako Model ID (setManufacturerAndModel("HomeOS", "obyvak_teplota")).
Zarizeni se ale pozna podle IEEE adresy (vypalena v cipu), takze po
preflashovani nebo znovusparovani se data dal ukladaji do stejne tabulky.
"""

import os
import re
import sqlite3
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

# stejna DB jako solarAPI (STATS_DB_PATH), pokud neni nastavena vlastni
DB_PATH = (os.environ.get("HOMEOS_DB_PATH") or os.environ.get("STATS_DB_PATH")
           or "/home/pi/homeos.db")
TABLE_PREFIX = "dev_"


def iso_now() -> str:
    """Stejny format jako solarAPI: 2026-11-03T20:45:00.519Z"""
    dt = datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def sanitize(name: str | None) -> str:
    """'Obyvak Teplota-1' -> 'obyvak_teplota_1' (jen a-z, 0-9, _)."""
    return re.sub(r"[^a-z0-9]+", "_", (name or "").strip().lower()).strip("_")[:40]


def q(ident: str) -> str:
    """Identifikator do SQL. Pouziva se jen na nase vlastni nazvy
    (sanitize() / klice METRICS), nikdy na vstup od uzivatele."""
    return '"' + ident + '"'


class Database:
    def __init__(self, path: str = DB_PATH):
        self.conn = sqlite3.connect(path, timeout=10)
        # WAL: Zigbee sluzba, solarAPI i API muzou cist/zapisovat zaroven
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS devices (
                ieee         TEXT PRIMARY KEY,
                name         TEXT NOT NULL UNIQUE,
                table_name   TEXT NOT NULL UNIQUE,
                manufacturer TEXT,
                model        TEXT,
                paired_at    TEXT NOT NULL,
                last_seen    TEXT
            )
            """
        )
        self.conn.commit()

    def close(self):
        self.conn.close()

    # --- registrace ---------------------------------------------------------
    def register_device(self, ieee: str, model: str | None,
                        manufacturer: str | None, columns: list[str]) -> str:
        """Zaregistruje ESP a vytvori/doplni jeho tabulku. Vrati nazev tabulky."""
        row = self.conn.execute(
            "SELECT table_name FROM devices WHERE ieee = ?", (ieee,)
        ).fetchone()
        if row:
            table = row[0]
            self.conn.execute(
                "UPDATE devices SET manufacturer = ?, model = ? WHERE ieee = ?",
                (manufacturer, model, ieee),
            )
        else:
            base = sanitize(model) or "zb_" + ieee.replace(":", "")[-4:]
            name = self._free_name(base, ieee)
            table = TABLE_PREFIX + name
            self.conn.execute(
                "INSERT INTO devices (ieee, name, table_name, manufacturer, model,"
                " paired_at) VALUES (?, ?, ?, ?, ?, ?)",
                (ieee, name, table, manufacturer, model, iso_now()),
            )
            print(f"[DB] nove zarizeni {ieee} -> tabulka {table}")

        self.conn.execute(
            f"CREATE TABLE IF NOT EXISTS {q(table)} ("
            " id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL)"
        )
        # nova hodnota na ESP (napr. pribyla vlhkost) = novy sloupec
        existing = self.columns(table)
        for col in columns:
            if col not in existing:
                self.conn.execute(f"ALTER TABLE {q(table)} ADD COLUMN {q(col)} REAL")
        self.conn.execute(f"CREATE INDEX IF NOT EXISTS {q(table + '_at')} ON {q(table)} (at)")
        self.conn.commit()
        return table

    def _free_name(self, base: str, ieee: str) -> str:
        """Dve ESP se stejnym nazvem: druhe dostane konec IEEE adresy."""
        taken = self.conn.execute(
            "SELECT 1 FROM devices WHERE name = ?", (base,)
        ).fetchone()
        return f"{base}_{ieee.replace(':', '')[-4:]}" if taken else base

    # --- zapis ------------------------------------------------------------------
    def insert(self, table: str, ieee: str, values: dict[str, float]):
        """Jeden radek = jedno mereni ESP (vsechny hodnoty se stejnym casem)."""
        now = iso_now()
        cols = ", ".join(q(c) for c in values)
        marks = ", ".join("?" for _ in values)
        self.conn.execute(
            f"INSERT INTO {q(table)} (at, {cols}) VALUES (?, {marks})",
            (now, *values.values()),
        )
        self.conn.execute("UPDATE devices SET last_seen = ? WHERE ieee = ?", (now, ieee))
        self.conn.commit()

    # --- cteni (pro API) ---------------------------------------------------
    def columns(self, table: str) -> list[str]:
        """Sloupce s hodnotami (bez id a at)."""
        return [r[1] for r in self.conn.execute(f"PRAGMA table_info({q(table)})")
                if r[1] not in ("id", "at")]

    def devices(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT ieee, name, table_name, manufacturer, model, paired_at, last_seen"
            " FROM devices ORDER BY name"
        ).fetchall()
        keys = ("ieee", "name", "table", "manufacturer", "model", "paired_at", "last_seen")
        return [dict(zip(keys, r)) for r in rows]

    def table_of(self, name: str) -> str | None:
        row = self.conn.execute(
            "SELECT table_name FROM devices WHERE name = ?", (name,)
        ).fetchone()
        return row[0] if row else None

    def readings(self, table: str, since: str | None = None,
                 limit: int = 500) -> list[dict]:
        cols = ["at", *self.columns(table)]
        sql = f"SELECT {', '.join(q(c) for c in cols)} FROM {q(table)}"
        args: list = []
        if since:
            sql += " WHERE at >= ?"
            args.append(since)
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        rows = self.conn.execute(sql, args).fetchall()
        return [dict(zip(cols, r)) for r in reversed(rows)]
