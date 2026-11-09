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
        path = os.path.abspath(os.path.expanduser(path))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            self.conn = sqlite3.connect(path, timeout=10)
        except sqlite3.OperationalError as e:
            raise RuntimeError(f"Nejde otevrit databazi {path}: {e} "
                               "(zkontroluj HOMEOS_DB_PATH / STATS_DB_PATH a prava)") from e
        print(f"[DB] {path}")
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS devices
            (
                ieee
                TEXT
                PRIMARY
                KEY,
                name
                TEXT
                NOT
                NULL
                UNIQUE,
                table_name
                TEXT
                NOT
                NULL
                UNIQUE,
                manufacturer
                TEXT,
                model
                TEXT,
                paired_at
                TEXT
                NOT
                NULL,
                last_seen
                TEXT
            )
            """
        )
        self.conn.commit()

    def close(self):
        self.conn.close()

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

    def _where(self, column: str, since: str | None, metric: str | None = None):
        where, args = f"WHERE {q(column)} IS NOT NULL", []
        if metric is not None:
            where += " AND metric = ?"
            args.append(metric)
        if since:
            where += " AND at >= ?"
            args.append(since)
        return where, args

    def stats(self, table: str, column: str, since: str | None = None,
              metric: str | None = None) -> dict:
        """Posledni / prumer / min / max jednoho sloupce (od `since`)."""
        where, args = self._where(column, since, metric)
        avg, mn, mx, cnt = self.conn.execute(
            f"SELECT AVG({q(column)}), MIN({q(column)}), MAX({q(column)}), COUNT(*)"
            f" FROM {q(table)} {where}", args
        ).fetchone()
        last = self.conn.execute(
            f"SELECT at, {q(column)} FROM {q(table)} {where} ORDER BY id DESC LIMIT 1", args
        ).fetchone()
        return {"last": last[1] if last else None, "last_at": last[0] if last else None,
                "avg": avg, "min": mn, "max": mx, "count": cnt}

    def history(self, table: str, column: str, since: str | None = None,
                points: int = 300, metric: str | None = None) -> list[dict]:
        """Prubeh hodnot zhusteny do max. `points` useku (prumer/min/max v kazdem),
        aby graf za mesic nemusel tahat desitky tisic radku."""
        where, args = self._where(column, since, metric)
        t0, t1, cnt = self.conn.execute(
            f"SELECT MIN(julianday(at)), MAX(julianday(at)), COUNT(*) FROM {q(table)} {where}",
            args,
        ).fetchone()
        if not cnt:
            return []
        if cnt <= points or t1 == t0:
            rows = self.conn.execute(
                f"SELECT at, {q(column)} FROM {q(table)} {where} ORDER BY at", args
            ).fetchall()
            return [{"at": at, "avg": v, "min": v, "max": v} for at, v in rows]
        rows = self.conn.execute(
            f"SELECT MIN(at), AVG({q(column)}), MIN({q(column)}), MAX({q(column)})"
            f" FROM {q(table)} {where}"
            f" GROUP BY MIN(CAST((julianday(at) - ?) / ? AS INTEGER), ? - 1) ORDER BY 1",
            [*args, t0, (t1 - t0) / points, points],
        ).fetchall()
        return [{"at": at, "avg": a, "min": mn, "max": mx} for at, a, mn, mx in rows]

    SOLAR_TABLE = "stats"
    SOLAR_COLUMNS = ["total", "delta"]

    def solar_metrics(self) -> list[dict]:
        exists = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (self.SOLAR_TABLE,)
        ).fetchone()
        if not exists:
            return []
        rows = self.conn.execute(
            "SELECT metric, at, total, delta FROM stats WHERE id IN"
            " (SELECT MAX(id) FROM stats GROUP BY metric) ORDER BY metric"
        ).fetchall()
        return [{"metric": m, "columns": self.SOLAR_COLUMNS,
                 "latest": {"at": at, "total": t, "delta": d}} for m, at, t, d in rows]
