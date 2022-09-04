from bluez_peripheral.util import *
from typing import Tuple
import subprocess
import atexit

BTVIRT_CMD = "btvirt"
BTMON_CMD = "btmon"

async def get_test_adapters(bus: MessageBus) -> Tuple[Adapter, Adapter]:
    old_adapters = await Adapter.get_all(bus)
    proc = subprocess.Popen([BTVIRT_CMD, "-l2"], stdout=subprocess.PIPE)
    
    adapters = []
    while len(adapters) < 2:
        new_adapters = await Adapter.get_all(bus)
        adapters = [i for i in new_adapters if i not in old_adapters]

    server = adapters[0]
    client = adapters[1]

    await server.set_powered(True)
    await client.set_powered(True)

    # Make sure the virtual adapter process get cleaned up.
    def cleanup():
        proc.terminate()
        proc.wait()
    atexit.register(cleanup)

    return (server, client)

async def disconnect_test_adapters(server: Adapter, client: Adapter):
    server_dev = None
    for d in await client.get_devices():
        if await d.get_address() == await server.get_address():
            server_dev = d
            break
    if await server_dev.get_connected():
        await server_dev.disconnect()

async def pair_test_adapters(server: Adapter, client: Adapter):
    # Prepare adapters for pairing.
    await server.set_pairable(True)
    await client.set_pairable(True)
    await server.set_discoverable(True)
    await client.set_discovering(True)

    server_dev = None
    for d in await client.get_devices():
        if await d.get_address() == await server.get_address():
            server_dev = d
            break

    if not await server_dev.get_paired():
        print(await server_dev.get_paired())
        await server_dev.pair()

    if not await server_dev.get_trusted():
        await server_dev.set_trusted(True)
    

class BTMonitor:
    _proc : subprocess.Popen = None

    def start(self):
        self._proc = subprocess.Popen([BTMON_CMD], stdout=subprocess.PIPE)

    def stop(self):
        self._proc.terminate()

    def check(self):
        # TODO: Detect errors.
        self._proc

#########################################################################
import asyncio
from bluez_peripheral.advert import Advertisement

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
    bus = await get_message_bus()
    await bus.request_name("com.spacecheese.test")

    server, client = await get_test_adapters(bus)
    await pair_test_adapters(server, client)

    service = HeartRateService()
    await service.register(bus)

    #advert = Advertisement("Heart Monitor", ["180D"], 0x0340, 60)
    #await advert.register(bus, ad[0])

    await bus.wait_for_disconnect()


if __name__ == "__main__":
    asyncio.run(main())