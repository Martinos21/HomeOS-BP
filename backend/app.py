"""
API HomeOS (Flask). Ve stejnem procesu bezi i Zigbee sit, takze tlacitko
"Pridat zarizeni" na webu zavola primo service.start_pairing().

Flask je synchronni, zigpy asynchronni: Zigbee bezi ve vlastnim vlakne
s asyncio smyckou a Flask do ni posila prikazy pres run_coroutine_threadsafe().

Spusteni (z rootu projektu, jen jeden proces, dongle umi ovladat jen jeden):
    uv run python -m backend.app
Nespoustej pres `flask run --debug`: reloader by spustil Zigbee dvakrat.

Promenne (.env): HOMEOS_API_KEY (povinne), HOMEOS_CORS_ORIGINS (default *),
HOMEOS_HOST (0.0.0.0), HOMEOS_PORT (8080), HOMEOS_DB_PATH, ZIGBEE_PORT, ZIGPY_DB_PATH

Vse krome /api/health chce hlavicku  X-API-Key: <klic>
  GET    /api/health                         bezi API / bezi Zigbee
  GET    /api/devices                        ESP + posledni mereni
  GET    /api/devices/<name>/readings        historie (?since=ISO&limit=500)
  GET    /api/zigbee/pairing                 stav parovani + nove pripojena ESP
  POST   /api/zigbee/pairing {"seconds":120} otevre parovani
  DELETE /api/zigbee/pairing                 zavre parovani
"""

import asyncio
import logging
import os
import secrets
import threading
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, g, jsonify, request

from tools.db import Database
from zigbee.zigbee_service import MAX_PAIRING_S, ZigbeeService, start_zigbee

load_dotenv()

API_KEY = os.environ.get("HOMEOS_API_KEY")
if not API_KEY:
    raise RuntimeError("Nastav HOMEOS_API_KEY (napr. v .env)")
CORS_ORIGINS = os.environ.get("HOMEOS_CORS_ORIGINS", "*").split(",")

log = logging.getLogger("homeos")
app = Flask(__name__)


# --------------------------------------------------------------------------
# Zigbee ve vlastnim vlakne
# --------------------------------------------------------------------------
class ZigbeeThread:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.service: ZigbeeService | None = None
        self._ready = threading.Event()

    def start(self, timeout: float = 30):
        threading.Thread(target=self._run, name="zigbee", daemon=True).start()
        self._ready.wait(timeout)

    def _run(self):
        asyncio.set_event_loop(self.loop)
        try:
            self.service = self.loop.run_until_complete(start_zigbee())
        except Exception:
            # bez donglu API dal vraci data, jen parovani hlasi 503
            log.exception("Zigbee se nepodarilo nastartovat")
        finally:
            self._ready.set()
        if self.service:
            self.loop.run_forever()

    def call(self, coro, timeout: float = 10):
        """Spusti korutinu v Zigbee smycce a pocka na vysledek."""
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(timeout)


zigbee = ZigbeeThread()


# --------------------------------------------------------------------------
# Pomocne veci: API klic, CORS, DB spojeni, chyby jako JSON
# --------------------------------------------------------------------------
def require_key(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not secrets.compare_digest(request.headers.get("X-API-Key", ""), API_KEY):
            return jsonify(error="Spatny nebo chybejici X-API-Key"), 401
        return view(*args, **kwargs)
    return wrapper


def require_zigbee(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if zigbee.service is None:
            return jsonify(error="Zigbee nebezi (zkontroluj dongle)"), 503
        return view(*args, **kwargs)
    return wrapper


def db() -> Database:
    if "db" not in g:
        g.db = Database()   # vlastni spojeni pro kazdy pozadavek
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    conn = g.pop("db", None)
    if conn:
        conn.close()


@app.after_request
def cors(resp):
    origin = request.headers.get("Origin")
    if "*" in CORS_ORIGINS or origin in CORS_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"] = "*" if "*" in CORS_ORIGINS else origin
        resp.headers["Access-Control-Allow-Headers"] = "X-API-Key, Content-Type"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
    return resp


@app.errorhandler(404)
def not_found(_e):
    return jsonify(error="Nenalezeno"), 404


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return jsonify(ok=True, zigbee_online=zigbee.service is not None)


@app.get("/api/devices")
@require_key
def devices():
    out = []
    for d in db().devices():
        latest = db().readings(d["table"], limit=1)
        out.append({**d, "columns": db().columns(d["table"]),
                    "latest": latest[0] if latest else None})
    return jsonify(out)


@app.get("/api/devices/<name>/readings")
@require_key
def readings(name):
    table = db().table_of(name)   # nazev tabulky jen z registru, ne z URL
    if not table:
        return jsonify(error=f"Zarizeni {name} neexistuje"), 404
    limit = request.args.get("limit", 500, type=int)
    if not 1 <= limit <= 10000:
        return jsonify(error="limit musi byt 1-10000"), 400
    return jsonify(db().readings(table, since=request.args.get("since"), limit=limit))


# --------------------------------------------------------------------------
# Parovani
# --------------------------------------------------------------------------
@app.get("/api/zigbee/pairing")
@require_key
@require_zigbee
def get_pairing():
    return jsonify(zigbee.service.pairing_state())


@app.post("/api/zigbee/pairing")
@require_key
@require_zigbee
def start_pairing():
    body = request.get_json(silent=True) or {}
    seconds = body.get("seconds", 120)
    if not isinstance(seconds, int) or not 1 <= seconds <= MAX_PAIRING_S:
        return jsonify(error=f"seconds musi byt cele cislo 1-{MAX_PAIRING_S}"), 400
    zigbee.call(zigbee.service.start_pairing(seconds))
    return jsonify(zigbee.service.pairing_state())


@app.delete("/api/zigbee/pairing")
@require_key
@require_zigbee
def stop_pairing():
    zigbee.call(zigbee.service.stop_pairing())
    return jsonify(zigbee.service.pairing_state())


# --------------------------------------------------------------------------
if __name__ == "__main__":
    if os.environ.get("ZIGBEE_DISABLED") != "1":
        zigbee.start()
    app.run(host=os.environ.get("HOMEOS_HOST", "0.0.0.0"),
            port=int(os.environ.get("HOMEOS_PORT", "8080")),
            threaded=True, use_reloader=False)
