import asyncio
import logging
from bellows.zigbee.application import ControllerApplication
from zigpy.config import CONF_DEVICE, CONF_DEVICE_PATH, CONF_DATABASE

logging.basicConfig(level=logging.INFO)

config = {
    CONF_DEVICE: {
        CONF_DEVICE_PATH: "/dev/ttyUSB0"
    },
    CONF_DATABASE: "/home/pi/zigbee.db",
}

async def main():
    app = ControllerApplication(config)
    await app.startup(auto_form=True)

    print("Coordinator IEEE:", app.state.node_info.ieee)
    print("PAN ID:", app.state.network_info.pan_id)
    print("Channel:", app.state.network_info.channel)

    await app.permit(time_s=120)
    print("Permit join open — put your device in pairing mode now")

    for _ in range(120):
        await asyncio.sleep(1)
        if len(app.devices) > 1:  # more than just the coordinator
            break

    for device in app.devices.values():
        print(device.ieee, device.manufacturer, device.model)

    await app.shutdown()

asyncio.run(main())