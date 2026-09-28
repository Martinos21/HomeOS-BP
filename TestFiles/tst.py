import asyncio
import logging
from dataclasses import dataclass
from typing import Callable, Optional

import zigpy.types as t
from bellows.zigbee.application import ControllerApplication
from zigpy.config import CONF_DEVICE, CONF_DEVICE_PATH, CONF_DATABASE

logging.basicConfig(level=logging.INFO)

config = {
    CONF_DEVICE: {CONF_DEVICE_PATH: "/dev/ttyUSB0"},
    CONF_DATABASE: "/home/pi/zigbee.db",
}


# --------------------------------------------------------------------------
# Sensor table: add a new measurement type = add one line here
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class SensorType:
    name: str
    unit: str
    attr_id: int
    convert: Callable          # raw ZCL value -> human value
    invalid: tuple             # raw values meaning "no measurement"
    min_interval: int
    max_interval: int
    change: float              # minimum change (raw units) to trigger a report


SENSORS = {
    # Temperature Measurement: int16, 0.01 °C
    0x0402: SensorType("temperature", "°C", 0x0000, lambda v: v / 100,
                       (-32768,), 10, 300, 10),
    # Relative Humidity: uint16, 0.01 %
    0x0405: SensorType("humidity", "%", 0x0000, lambda v: v / 100,
                       (0xFFFF,), 10, 300, 50),
    # CO2 Concentration Measurement: float, fraction (0.0004 = 400 ppm)
    0x040D: SensorType("co2", "ppm", 0x0000, lambda v: v * 1_000_000,
                       (), 30, 300, 0.00001),
}

ON_OFF_CLUSTER = 0x0006
ON_OFF_ATTR = 0x0000

# Latest known values: {(ieee, endpoint, name): value}
latest = {}


def on_reading(device, endpoint_id, name, value, unit):
    """Single place where all readings end up. Replace with MQTT/DB/etc."""
    latest[(str(device.ieee), endpoint_id, name)] = value
    print(f"[{device.ieee} ep{endpoint_id}] {name} = {value:.2f} {unit}".rstrip())


# --------------------------------------------------------------------------
# Cluster listeners
# --------------------------------------------------------------------------
class SensorListener:
    def __init__(self, device, endpoint_id, sensor: SensorType):
        self.device, self.endpoint_id, self.sensor = device, endpoint_id, sensor

    def attribute_updated(self, attribute_id, value, timestamp=None):
        s = self.sensor
        if attribute_id != s.attr_id or value is None or value in s.invalid:
            return
        on_reading(self.device, self.endpoint_id, s.name, s.convert(value), s.unit)

    def cluster_command(self, *a, **kw): pass
    def general_command(self, *a, **kw): pass


class RelayListener:
    def __init__(self, device, endpoint_id):
        self.device, self.endpoint_id = device, endpoint_id

    def attribute_updated(self, attribute_id, value, timestamp=None):
        if attribute_id == ON_OFF_ATTR and value is not None:
            print(f"[{self.device.ieee} ep{self.endpoint_id}] relay = "
                  f"{'ON' if value else 'OFF'}")
            latest[(str(self.device.ieee), self.endpoint_id, "relay")] = bool(value)

    def cluster_command(self, *a, **kw): pass
    def general_command(self, *a, **kw): pass


# --------------------------------------------------------------------------
# Application listener
# --------------------------------------------------------------------------
class MainListener:
    def __init__(self, application):
        self.application = application
        self._tasks = set()

    def _spawn(self, coro):
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def device_joined(self, device):
        print(f"[JOIN] {device.ieee}")

    def device_initialized(self, device):
        print(f"[INIT] {device.ieee} ({device.manufacturer} {device.model})")
        self._spawn(self.setup_device(device))

    def raw_device_initialized(self, device):
        pass

    def setup_known_devices(self):
        for device in self.application.devices.values():
            if device.ieee == self.application.state.node_info.ieee:
                continue
            if device.is_initialized:
                self._spawn(self.setup_device(device))

    async def setup_device(self, device):
        """Inspect every endpoint and set up whatever clusters are present."""
        for ep_id, ep in device.endpoints.items():
            if ep_id == 0:
                continue

            for cluster_id, sensor in SENSORS.items():
                if cluster_id in ep.in_clusters:
                    cluster = ep.in_clusters[cluster_id]
                    cluster.add_listener(SensorListener(device, ep_id, sensor))
                    await self._bind_and_report(
                        device, cluster, sensor.attr_id,
                        sensor.min_interval, sensor.max_interval, sensor.change,
                        label=sensor.name,
                    )

            if ON_OFF_CLUSTER in ep.in_clusters:
                cluster = ep.in_clusters[ON_OFF_CLUSTER]
                cluster.add_listener(RelayListener(device, ep_id))
                await self._bind_and_report(
                    device, cluster, ON_OFF_ATTR, 0, 300, 1, label="relay",
                )

    async def _bind_and_report(self, device, cluster, attr, mn, mx, change, label):
        try:
            await cluster.bind()
            await cluster.configure_reporting(
                attr, min_interval=mn, max_interval=mx, reportable_change=change
            )
            print(f"[SETUP] {device.ieee} {label}: OK")
        except Exception as e:
            # Sleepy battery devices often fail here; wake them by pressing
            # their button. Listener is already attached, so data may still come.
            print(f"[ERROR] {device.ieee} {label}: {e}")


# --------------------------------------------------------------------------
# Relay control
# --------------------------------------------------------------------------
async def set_relay(app, ieee: str, on: Optional[bool], endpoint: int = 1):
    """on=True -> ON, on=False -> OFF, on=None -> toggle."""
    device = app.get_device(ieee=t.EUI64.convert(ieee))
    cluster = device.endpoints[endpoint].in_clusters[ON_OFF_CLUSTER]
    if on is None:
        await cluster.toggle()
    elif on:
        await cluster.on()
    else:
        await cluster.off()


# --------------------------------------------------------------------------
async def main():
    app = ControllerApplication(config)
    await app.startup(auto_form=True)

    listener = MainListener(app)
    app.add_listener(listener)
    listener.setup_known_devices()

    await app.permit(time_s=120)
    print("Permit join open for 120 s")

    # Example: control a relay from anywhere in your code
    # await set_relay(app, "00:15:8d:00:01:23:45:67", True, endpoint=1)

    try:
        await asyncio.Event().wait()
    finally:
        await app.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass