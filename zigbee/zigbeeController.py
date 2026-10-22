#!/usr/bin/env python3
"""
Zigbee koordinator pro HomeOS (bezi na Raspberry Pi s USB donglem).

- kazde pripojene ESP se zaregistruje v DB podle IEEE adresy a Model ID
- automaticky se vytvori tabulka dev_<nazev> a ukladaji se do ni hodnoty
- podporovane clustery: teplota (0x0402) a vlhkost (0x0405), ostatni se preskoci

Spusteni:  python zigbee/zigbee_service.py
Promenne:  ZIGBEE_PORT (default /dev/ttyUSB0), HOMEOS_DB_PATH, ZIGPY_DB_PATH
Parovani:  POST http://127.0.0.1:8081/pairing (viz control_api.py)
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Callable

import zigpy.types as t
from bellows.zigbee.application import ControllerApplication
from dotenv import load_dotenv
from zigpy.config import CONF_DATABASE, CONF_DEVICE, CONF_DEVICE_PATH
from zigpy.zcl import AttributeReportedEvent, AttributeUpdatedEvent

from control_api import Pairing, start_api
from tools.db import Database

load_dotenv()
logging.basicConfig(level=logging.INFO)

config = {
    CONF_DEVICE: {CONF_DEVICE_PATH: os.environ.get("ZIGBEE_PORT", "/dev/ttyUSB0")},
    # interni DB zigpy (sit, klice, sparovana zarizeni) - neni to DB s merenimi
    CONF_DATABASE: os.environ.get("ZIGPY_DB_PATH", "/home/pi/zigbee.db"),
}


# --------------------------------------------------------------------------
# Co umime cist: novy typ mereni = jeden radek
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Measurement:
    metric: str
    attr_id: int
    convert: Callable
    invalid: tuple
    min_interval: int
    max_interval: int
    change: float

MEASUREMENTS = {
    # Temperature Measurement: int16, 0.01 °C
    0x0402: Measurement("temperature", 0x0000, lambda v: v / 100,
                        (-32768,), 10, 300, 10),
    # Relative Humidity: uint16, 0.01 %
    0x0405: Measurement("humidity", 0x0000, lambda v: v / 100,
                        (0xFFFF,), 10, 300, 50),
}


# --------------------------------------------------------------------------
class ZigbeeService:
    def __init__(self, app: ControllerApplication, db: Database):
        self.app = app
        self.db = db
        self._tasks = set()
        self._subscribed = set()  # (ieee, ep, cluster) - at se neodebira 2x
        self.pairing = Pairing()

    # --- zigpy listener callbacky -----------------------------------------
    def device_joined(self, device):
        print(f"[JOIN] {device.ieee}")

    def raw_device_initialized(self, device):
        pass

    def device_initialized(self, device):
        print(f"[INIT] {device.ieee} ({device.manufacturer} {device.model})")
        self._spawn(self.setup_device(device))

    def device_left(self, device):
        print(f"[LEFT] {device.ieee}")

    # ----------------------------------------------------------------------
    def _spawn(self, coro):
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def setup_known_devices(self):
        """Po restartu Pi: zarizeni uz jsou sparovana, jen se znovu napojime."""
        for device in self.app.devices.values():
            if device.ieee == self.app.state.node_info.ieee:
                continue
            if device.is_initialized:
                self._spawn(self.setup_device(device))

    async def setup_device(self, device):
        ieee = str(device.ieee)
        found = []  # (ep_id, cluster, measurement)
        for ep_id, ep in device.endpoints.items():
            if ep_id == 0:
                continue
            for cluster_id, m in MEASUREMENTS.items():
                if cluster_id in ep.in_clusters:
                    found.append((ep_id, ep.in_clusters[cluster_id], m))

        if not found:
            print(f"[SKIP] {ieee}: zadny podporovany cluster")
            return

        table = self.db.register_device(ieee, device.model, device.manufacturer, "sensor")

        for ep_id, cluster, m in found:
            key = (ieee, ep_id, cluster.cluster_id)
            if key not in self._subscribed:
                self._subscribed.add(key)
                handler = self._make_handler(ieee, ep_id, m)
                # zigpy posle Updated (hodnota se zmenila) NEBO Reported (stejna)
                cluster.on_event(AttributeReportedEvent.event_type, handler)
                cluster.on_event(AttributeUpdatedEvent.event_type, handler)
            await self._bind_and_report(ieee, cluster, m)

        if self.pairing.remaining > 0 and all(j["ieee"] != ieee for j in self.pairing.joined):
            name = table.removeprefix("dev_")
            self.pairing.joined.append({"ieee": ieee, "name": name, "table": table})
        print(f"[READY] {ieee} -> {table} ({', '.join(m.metric for _, _, m in found)})")

    def _make_handler(self, ieee, ep_id, m: Measurement):
        multi_ep = None  # vice stejnych senzoru na jednom ESP -> metric_ep

        def handler(event):
            if event.attribute_id != m.attr_id or event.value is None:
                return
            if event.value in m.invalid:
                return
            nonlocal multi_ep
            if multi_ep is None:
                device = self.app.get_device(ieee=t.EUI64.convert(ieee))
                multi_ep = sum(
                    1 for e_id, e in device.endpoints.items()
                    if e_id != 0 and event.cluster_id in e.in_clusters
                ) > 1
            metric = f"{m.metric}_{ep_id}" if multi_ep else m.metric
            value = m.convert(event.value)
            print(f"[DATA] {ieee} {metric} = {value}")
            self.db.insert(ieee, metric, value)

        return handler

    async def _bind_and_report(self, ieee, cluster, m: Measurement):
        try:
            await cluster.bind()
            await cluster.configure_reporting(
                m.attr_id, min_interval=m.min_interval,
                max_interval=m.max_interval, reportable_change=m.change,
            )
            print(f"[SETUP] {ieee} {m.metric}: OK")
        except Exception as e:
            # ESP stejne reportuje samo (reportTemperature() atd.), takze to
            # neni fatalni - handler uz je napojeny
            print(f"[WARN] {ieee} {m.metric}: bind/reporting selhal: {e}")


# --------------------------------------------------------------------------
async def main():
    db = Database()
    app = ControllerApplication(config)
    await app.startup(auto_form=True)

    service = ZigbeeService(app, db)
    app.add_listener(service)
    service.setup_known_devices()

    print("Coordinator IEEE:", app.state.node_info.ieee)
    print("PAN ID:", app.state.network_info.pan_id,
          "Channel:", app.state.network_info.channel)

    api = await start_api(service)

    # parovani se normalne spousti pres API; tohle je jen pro ladeni
    permit = min(int(os.environ.get("ZIGBEE_PERMIT_S", "0")), 254)
    if permit:
        await app.permit(time_s=permit)
        print(f"Parovani otevreno na {permit} s")

    try:
        await asyncio.Event().wait()
    finally:
        await api.cleanup()
        await app.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
