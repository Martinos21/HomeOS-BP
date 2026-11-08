#!/usr/bin/env python3
"""
Zigbee koordinator HomeOS (Raspberry Pi + USB dongle Silicon Labs, zigpy/bellows).

Co dela:
  1. nastartuje Zigbee sit (pri prvnim spusteni ji sam zalozi)
  2. kdyz se pripoji ESP, precte jeho nazev (Model ID) a podporovane hodnoty
     (clustery), zaregistruje ho v DB a zalozi tabulku dev_<nazev>
  3. kazde mereni z ESP ulozi jako jeden radek tabulky
  4. parovani (permit join) se zapina na omezenou dobu pres start_pairing()

Normalne ji spousti backend (backend/app.py). Samostatne pro ladeni:
    uv run python -m zigbee.zigbee_service          # ZIGBEE_PERMIT_S=120 = rovnou parovat
Promenne: ZIGBEE_PORT (/dev/ttyUSB0), ZIGPY_DB_PATH, HOMEOS_DB_PATH
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from typing import Callable

from bellows.zigbee.application import ControllerApplication
from dotenv import load_dotenv
from zigpy.config import CONF_DATABASE, CONF_DEVICE, CONF_DEVICE_PATH
from zigpy.zcl import AttributeReportedEvent, AttributeUpdatedEvent

from tools.db import Database
from zigbee.metrics import METRICS, Metric

load_dotenv()
logging.basicConfig(level=logging.INFO)

CONFIG = {
    CONF_DEVICE: {CONF_DEVICE_PATH: os.environ.get("ZIGBEE_PORT", "/dev/ttyUSB0")},
    # interni DB zigpy (klice site, sparovana zarizeni), NE databaze s merenimi
    CONF_DATABASE: os.environ.get("ZIGPY_DB_PATH", "/home/pi/zigbee.db"),
}

MAX_PAIRING_S = 254   # vic Zigbee standard nedovoli
FLUSH_DELAY_S = 2.0   # hodnoty, ktere ESP posle tesne po sobe, jdou do jednoho radku


class ZigbeeService:
    def __init__(self, app: ControllerApplication, db: Database):
        self.app = app
        self.db = db
        self.tables: dict[str, str] = {}        # ieee -> dev_<nazev>
        self._pending: dict[str, dict] = {}     # ieee -> hodnoty cekajici na zapis
        self._timers: dict[str, asyncio.TimerHandle] = {}
        self._subscribed: set = set()           # (ieee, ep, cluster)
        self._tasks: set = set()
        self.pairing_until = 0.0
        self.pairing_joined: list[dict] = []

    # --- zigpy listener (vola ho zigpy) ------------------------------------
    def device_joined(self, device):
        print(f"[JOIN] {device.ieee} se pripojuje, cekam na interview...")

    def raw_device_initialized(self, device):
        pass

    def device_initialized(self, device):
        """Interview hotovo: zname Model ID i clustery."""
        print(f"[INIT] {device.ieee} model={device.model!r}")
        self._spawn(self.setup_device(device))

    def device_left(self, device):
        print(f"[LEFT] {device.ieee} (tabulka v DB zustava)")

    # ----------------------------------------------------------------------
    def _spawn(self, coro):
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def setup_known_devices(self):
        """Po restartu Pi: ESP uz jsou sparovana, jen se znovu napojime."""
        for device in self.app.devices.values():
            if device.nwk != 0x0000 and device.is_initialized:
                self._spawn(self.setup_device(device))

    async def setup_device(self, device):
        ieee = str(device.ieee)
        found = []  # (cluster, metric)
        for ep_id, ep in device.endpoints.items():
            if ep_id == 0:
                continue   # ZDO
            for cluster_id, metric in METRICS.items():
                if cluster_id in ep.in_clusters:
                    found.append((ep.in_clusters[cluster_id], metric))

        if not found:
            print(f"[SKIP] {ieee}: nema zadnou podporovanou hodnotu")
            return

        columns = list(dict.fromkeys(m.column for _, m in found))
        table = self.db.register_device(ieee, device.model, device.manufacturer, columns)
        self.tables[ieee] = table

        for cluster, metric in found:
            key = (ieee, cluster.endpoint.endpoint_id, cluster.cluster_id)
            if key not in self._subscribed:
                self._subscribed.add(key)
                handler = self._make_handler(ieee, metric)
                cluster.on_event(AttributeReportedEvent.event_type, handler)
                cluster.on_event(AttributeUpdatedEvent.event_type, handler)
            try:
                # binding = ESP posila reporty na koordinator; interval si ridi ESP samo
                await cluster.bind()
            except Exception as e:  # noqa: BLE001 - ESP muze spat, neni to fatalni
                print(f"[WARN] {ieee} bind {metric.column} selhal: {e}")

        if self.pairing_active() and all(j["ieee"] != ieee for j in self.pairing_joined):
            self.pairing_joined.append(
                {"ieee": ieee, "name": table.removeprefix("dev_"), "table": table,
                 "columns": columns})
        print(f"[READY] {ieee} -> {table} ({', '.join(columns)})")

    # --- prijem dat ---------------------------------------------------------
    def _make_handler(self, ieee: str, metric: Metric):
        def handler(event):
            if event.attribute_id != metric.attr_id or event.value is None:
                return
            if event.value in metric.invalid:
                return
            self._collect(ieee, metric.column, metric.convert(event.value))
        return handler

    def _collect(self, ieee: str, column: str, value: float):
        """ESP posle teplotu a vlhkost jako 2 zpravy tesne po sobe -> 1 radek."""
        pending = self._pending.setdefault(ieee, {})
        if column in pending:          # stejna hodnota podruhe = uz je to dalsi mereni
            self._flush(ieee)
            pending = self._pending.setdefault(ieee, {})
        pending[column] = value
        if ieee not in self._timers:
            loop = asyncio.get_running_loop()
            self._timers[ieee] = loop.call_later(FLUSH_DELAY_S, self._flush, ieee)

    def _flush(self, ieee: str):
        timer = self._timers.pop(ieee, None)
        if timer:
            timer.cancel()
        values = self._pending.pop(ieee, None)
        table = self.tables.get(ieee)
        if values and table:
            print(f"[DATA] {table} {values}")
            self.db.insert(table, ieee, values)

    # --- parovani (web, pozdeji fyzicke tlacitko) ---------------------------------
    def pairing_active(self) -> bool:
        return time.time() < self.pairing_until

    async def start_pairing(self, seconds: int = 120):
        seconds = max(1, min(int(seconds), MAX_PAIRING_S))
        await self.app.permit(time_s=seconds)
        if not self.pairing_active():
            self.pairing_joined = []   # nove kolo parovani
        self.pairing_until = time.time() + seconds
        print(f"[PAIR] parovani otevreno na {seconds} s")

    async def stop_pairing(self):
        await self.app.permit(time_s=0)
        self.pairing_until = 0.0
        print("[PAIR] parovani zavreno")

    def pairing_state(self) -> dict:
        remaining = max(0, round(self.pairing_until - time.time()))
        return {"active": remaining > 0, "remaining_s": remaining,
                "joined": self.pairing_joined}

    async def stop(self):
        for ieee in list(self._pending):
            self._flush(ieee)
        await self.app.shutdown()


async def start_zigbee(db: Database | None = None) -> ZigbeeService:
    """Nastartuje Zigbee sit a vrati sluzbu."""
    app = ControllerApplication(CONFIG)
    await app.startup(auto_form=True)

    service = ZigbeeService(app, db or Database())
    app.add_listener(service)
    service.setup_known_devices()

    info = app.state.network_info
    print(f"[ZIGBEE] koordinator {app.state.node_info.ieee}, "
          f"PAN {info.pan_id}, kanal {info.channel}")
    return service


async def main():
    service = await start_zigbee()
    permit = int(os.environ.get("ZIGBEE_PERMIT_S", "1"))
    if permit:
        await service.start_pairing(permit)
    try:
        await asyncio.Event().wait()
    finally:
        await service.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
