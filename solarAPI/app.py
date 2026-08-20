#!/usr/bin/env python3
"""
Fetches the current status from the Infigy device API and appends matching
rows to the local `stats` SQLite table (same shape/semantics as the
historical export: metric, delta, total, at).

Intended to be run every 5 minutes (e.g. via cron).
"""

import os
import sqlite3
import sys
from datetime import datetime, timezone

import requests

# ---- Config -----------------------------------------------------------
DB_PATH = os.environ.get("STATS_DB_PATH", "/home/claude/export.db")
API_URL = "https://app.infigy.cz/api/devices/1000000066b0baf6/get"
AUTH_TOKEN = os.environ.get("INFIGY_AUTH_TOKEN")  # set this in your environment

METRICS = (
    "em-consumed-graph",
    "em-overflow-graph",
    "pl-power-graph",
    "pv-battery-soc-graph",
)


def iso_now(offset_ms: int = 0) -> str:
    """Match the DB's timestamp format: 2026-06-19T08:45:00.519Z"""
    dt = datetime.now(timezone.utc)
    ms = dt.microsecond // 1000 + offset_ms
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ms:03d}Z"


def fetch_status() -> dict:
    if not AUTH_TOKEN:
        sys.exit("INFIGY_AUTH_TOKEN environment variable is not set.")
    resp = requests.get(
        API_URL,
        headers={"x-auth-token": AUTH_TOKEN},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def get_last(cur: sqlite3.Cursor, metric: str):
    """Return the most recent (delta, total) for a metric, or None if absent."""
    cur.execute(
        "SELECT delta, total FROM stats WHERE metric = ? ORDER BY id DESC LIMIT 1",
        (metric,),
    )
    row = cur.fetchone()
    return row  # (delta, total) or None


def build_rows(data: dict, cur: sqlite3.Cursor):
    rows = []

    # em-consumed-graph: cumulative total from API, delta = diff since last
    last = get_last(cur, "em-consumed-graph")
    new_total = float(data.get("gridConsumedTotal", 0.0))
    prev_total = last[1] if last else new_total
    delta = new_total - prev_total
    rows.append(("em-consumed-graph", delta, new_total, iso_now(0)))

    # em-overflow-graph: cumulative total from API, delta = diff since last
    last = get_last(cur, "em-overflow-graph")
    new_total = float(data.get("gridOverflowTotal", 0.0))
    prev_total = last[1] if last else new_total
    delta = new_total - prev_total
    rows.append(("em-overflow-graph", delta, new_total, iso_now(4)))

    # pl-power-graph: historically always 0/0 (device not licensed/active)
    rows.append(("pl-power-graph", 0.0, 0.0, iso_now(11)))

    # pv-battery-soc-graph: total = current SoC, delta = diff since last SoC reading
    last = get_last(cur, "pv-battery-soc-graph")
    new_soc = float(data.get("batterySoc", 0.0))
    prev_soc = last[1] if last else new_soc
    delta = new_soc - prev_soc
    rows.append(("pv-battery-soc-graph", delta, new_soc, iso_now(18)))

    return rows


def insert_rows(conn: sqlite3.Connection, rows):
    conn.executemany(
        "INSERT INTO stats (metric, delta, total, at) VALUES (?, ?, ?, ?)",
        rows,
    )
    conn.commit()


def main():
    data = fetch_status()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    rows = build_rows(data, cur)
    insert_rows(conn, rows)

    for metric, delta, total, at in rows:
        print(f"{at}  {metric:<24} delta={delta:.6f}  total={total:.6f}")

    conn.close()


if __name__ == "__main__":
    main()