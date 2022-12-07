from bluez_peripheral.util import *
import subprocess
    
class BTMonitor:
    _proc : subprocess.Popen = None

    def start(self):
        self._proc = subprocess.Popen(["btmon"], stdout=subprocess.PIPE)

    def stop(self):
        self._proc.terminate()

    def check(self):
        # TODO: Detect errors.
        self._proc

#########################################################################
import asyncio
from bluez_peripheral.advert import Advertisement
from bluez_peripheral.agent import *

from bluez_peripheral.gatt.service import Service
from bluez_peripheral.gatt.characteristic import characteristic, CharacteristicFlags as CharFlags

import struct

class HeartRateService(Service):
    def __init__(self):
        # Base 16 service UUID, This should be a primary service.
        super().__init__("180D", True)

    @characteristic("2A37", CharFlags.NOTIFY)
    def heart_rate_measurement(self, options):
        # This function is called when the characteristic is read.
        # Since this characteristic is notify only this function is a placeholder.
        # You don't need this function Python 3.9+ (See PEP 614).
        # You can generally ignore the options argument 
        # (see Advanced Characteristics and Descriptors Documentation).
        pass

    def update_heart_rate(self, new_rate):
        # Call this when you get a new heartrate reading.
        # Note that notification is asynchronous (you must await something at some point after calling this).
        flags = 0

        # Bluetooth data is little endian.
        rate = struct.pack("<BB", flags, new_rate)
        self.heart_rate_measurement.changed(rate)

async def main():
    # TODO: Need a better solution than this.
    #   Modalias property of adapter positivly identifies it as virtual (ie usb:v1D6Bp0246d0540 uniquely identifies the vendor and product id)

    subprocess.Popen(["btvirt", "-l2"], stdout=subprocess.PIPE)

    bus = await get_message_bus()
    await bus.request_name("com.spacecheese.test")

    # Need a better way of doing this
    # Advertising manager takes a while to show up on new adapters
    await asyncio.sleep(2)
    
    adapters = []
    while len(adapters) < 2:
        adapters = await Adapter.get_all(bus)

    server = adapters[0]
    client = adapters[1]

    service = HeartRateService()
    await service.register(bus, adapter = server)

    async def agent_request(key):
        print("Vaccuous Approval")
        return True
    def agent_cancel():
        pass

    agent = YesNoAgent(agent_request, agent_cancel)
    await agent.register(bus, True)

    advert = Advertisement("Heart Monitor", ["180D"], 0x0340, 60)
    await advert.register(bus, server)

    await server.set_powered(True)
    await client.set_powered(True)

    try:
        await server.set_pairable(True)
        await client.set_pairable(True)
        await server.set_discoverable(True)
        await client.set_discovering(True)

        server_dev = None
        while server_dev is None:
            for d in await client.get_devices():
                if await d.get_address() == await server.get_address():
                    server_dev = d
                    break

        if not await server_dev.get_paired():
            await server_dev.pair()

        while not await server_dev.get_paired():
            pass

        await server_dev.set_trusted(True)

    except Exception as ex:
        print("Encountered the following exception:")
        print(ex)
    finally:
        print(f"Client Address = {await client.get_address()}, Server Address = {await server.get_address()}")
        print("Sleeping")
        while(1):
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())