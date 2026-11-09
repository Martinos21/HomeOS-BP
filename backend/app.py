import asyncio
import logging
import os
import platform
import secrets
import socket
import threading
import time
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
LOCAL_NO_KEY = os.environ.get("HOMEOS_LOCAL_NO_KEY", "1") != "0"
LOCAL_ADDRS = {"127.0.0.1", "::1", "::ffff:127.0.0.1"}
 
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
def is_local() -> bool:
    """Pozadavek ze stejneho zarizeni (frontend bezi vedle backendu)."""
    return LOCAL_NO_KEY and request.remote_addr in LOCAL_ADDRS
 
 
def require_key(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if is_local():
            return view(*args, **kwargs)
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
    return jsonify(ok=True, zigbee_online=zigbee.service is not None,
                   key_required=not is_local())
 
 
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
 
 
def _series_args():
    """Spolecne parametry pro /stats a /history: column, since, points."""
    return (request.args.get("column", ""), request.args.get("since") or None,
            request.args.get("points", 300, type=int))
 
 
def _device_table_and_column(name):
    table = db().table_of(name)
    if not table:
        return None, (jsonify(error=f"Zarizeni {name} neexistuje"), 404)
    column = request.args.get("column", "")
    if column not in db().columns(table):   # nazev sloupce jen z PRAGMA, ne z URL
        return None, (jsonify(error=f"Zarizeni {name} nema hodnotu '{column}'"), 400)
    return table, None
 
 
@app.get("/api/devices/<name>/stats")
@require_key
def device_stats(name):
    table, err = _device_table_and_column(name)
    if err:
        return err
    column, since, _ = _series_args()
    return jsonify(db().stats(table, column, since))
 
 
@app.get("/api/devices/<name>/history")
@require_key
def device_history(name):
    table, err = _device_table_and_column(name)
    if err:
        return err
    column, since, points = _series_args()
    if not 2 <= points <= 2000:
        return jsonify(error="points musi byt 2-2000"), 400
    return jsonify(db().history(table, column, since, points))
 
 
# --------------------------------------------------------------------------
# Solar (tabulka `stats` ze solarAPI, pokud je ve stejne DB)
# --------------------------------------------------------------------------
@app.get("/api/solar")
@require_key
def solar():
    return jsonify(db().solar_metrics())
 
 
def _solar_check(metric):
    if metric not in {m["metric"] for m in db().solar_metrics()}:
        return jsonify(error=f"Metrika {metric} neexistuje"), 404
    if request.args.get("column", "") not in Database.SOLAR_COLUMNS:
        return jsonify(error="column musi byt total nebo delta"), 400
    return None
 
 
@app.get("/api/solar/<metric>/stats")
@require_key
def solar_stats(metric):
    if err := _solar_check(metric):
        return err
    column, since, _ = _series_args()
    return jsonify(db().stats(Database.SOLAR_TABLE, column, since, metric=metric))
 
 
@app.get("/api/solar/<metric>/history")
@require_key
def solar_history(metric):
    if err := _solar_check(metric):
        return err
    column, since, points = _series_args()
    if not 2 <= points <= 2000:
        return jsonify(error="points musi byt 2-2000"), 400
    return jsonify(db().history(Database.SOLAR_TABLE, column, since, points, metric=metric))
 
 
# --------------------------------------------------------------------------
# System (stranka Nastaveni ve frontendu)
# --------------------------------------------------------------------------
STARTED_AT = time.time()
 
 
def _os_name() -> str:
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    return line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return f"{platform.system()} {platform.release()}"
 
 
def _uptime_s() -> float | None:
    try:
        with open("/proc/uptime") as f:
            return float(f.read().split()[0])
    except OSError:
        return None
 
 
@app.get("/api/system")
@require_key
def system():
    return jsonify(
        hostname=socket.gethostname(),
        os=_os_name(),
        kernel=platform.release(),
        arch=platform.machine(),
        python=platform.python_version(),
        python_impl=platform.python_implementation(),
        uptime_s=_uptime_s(),
        api_uptime_s=round(time.time() - STARTED_AT),
        zigbee_online=zigbee.service is not None,
        device_count=len(db().devices()),
        db_path=os.path.abspath(db().conn.execute("PRAGMA database_list").fetchone()[2]),
    )
 
 
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