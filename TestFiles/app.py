import asyncio
import logging
from bellows.zigbee.application import ControllerApplication
from zigpy.config import CONF_DEVICE, CONF_DEVICE_PATH, CONF_DATABASE
from zigpy.zcl import AttributeReportedEvent, AttributeUpdatedEvent

logging.basicConfig(level=logging.INFO)

config = {
    CONF_DEVICE: {
        CONF_DEVICE_PATH: "/dev/ttyUSB0"
    },
    CONF_DATABASE: "/home/pi/zigbee.db",
}

TEMP_CLUSTER = 0x0402
TEMP_ATTR_MEASURED_VALUE = 0x0000


class MainListener:
    def __init__(self, application):
        self.application = application

    def device_joined(self, device):
        print(f"[JOIN] Zarizeni se pripojilo: {device.ieee}")

    def device_initialized(self, device):
        print(f"[INIT] Zarizeni inicializovano: {device.ieee} "
              f"({device.manufacturer} {device.model})")
        asyncio.create_task(self.bind_configure_and_listen(device))

    async def bind_configure_and_listen(self, device):
        for ep_id, ep in device.endpoints.items():
            if ep_id == 0:
                continue
            if TEMP_CLUSTER in ep.in_clusters:
                cluster = ep.in_clusters[TEMP_CLUSTER]
                try:
                    bind_result = await cluster.bind()
                    print(f"[BIND] Vysledek: {bind_result}")

                    cfg_result = await cluster.configure_reporting(
                        TEMP_ATTR_MEASURED_VALUE,
                        min_interval=1,
                        max_interval=60,
                        reportable_change=10,
                    )
                    print(f"[CONFIG] Vysledek: {cfg_result}")

                    # KLICOVA CAST - napojeni na novy event system zigpy
                    cluster.on_event(AttributeReportedEvent.event_type, self.on_attribute_report)
                    cluster.on_event(AttributeUpdatedEvent.event_type, self.on_attribute_report)
                    print(f"[LISTEN] Napojeno na eventy pro {device.ieee}")

                except Exception as e:
                    print(f"[ERROR] Bind/configure/listen selhal pro {device.ieee}: {e}")

    def on_attribute_report(self, event):
        # event je instance AttributeReportedEvent nebo AttributeUpdatedEvent
        print(f"[MSG] attr={event.attribute_id} hodnota={event.value}")
        if event.attribute_id == TEMP_ATTR_MEASURED_VALUE:
            print(f"temp:{event.value / 100}")

    def raw_device_initialized(self, device):
        pass


async def main():
    app = ControllerApplication(config)
    await app.startup(auto_form=True)

    app.add_listener(MainListener(app))

    print("Coordinator IEEE:", app.state.node_info.ieee)
    print("PAN ID:", app.state.network_info.pan_id)
    print("Channel:", app.state.network_info.channel)

    await app.permit(time_s=120)
    print("Permit join open — put your device in pairing mode now")

    for _ in range(300):
        await asyncio.sleep(1)

    print("\nPripojena zarizeni:")
    for device in app.devices.values():
        print(device.ieee, device.manufacturer, device.model)

    await app.shutdown()

asyncio.run(main())