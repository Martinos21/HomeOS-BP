import asyncio
import logging
from bellows.zigbee.application import ControllerApplication
from zigpy.config import CONF_DEVICE, CONF_DEVICE_PATH

logging.basicConfig(level=logging.INFO)

config = {
    CONF_DEVICE: {
        CONF_DEVICE_PATH: "/dev/ttyUSB0"
    },
}

async def main():
    app = ControllerApplication(config)  # let it call its own SCHEMA internally
    await app.startup(auto_form=True)

    print("Coordinator IEEE:", app.state.node_info.ieee)

    await app.permit(time_s=60)
    print("Permit join open — put your device in pairing mode now")

    await asyncio.sleep(65)

    for device in app.devices.values():
        print(device.ieee, device.manufacturer, device.model)

    await app.shutdown()

asyncio.run(main())