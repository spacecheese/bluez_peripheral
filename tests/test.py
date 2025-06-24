#!/usr/bin/env python3

import asyncio
from dbus_fast.aio import MessageBus
from dbus_fast.constants import BusType

from bluez_peripheral.advert import Advertisement
from bluez_peripheral.adapter import Adapter
from bluez_peripheral.util import get_message_bus
from bluez_peripheral.agent import TestAgent, AgentCapability

async def main():
    bus = await get_message_bus()

    adapters = await Adapter.get_all(bus)

    # Enable adapter settings
    await adapters[0].set_powered(True)
    await adapters[0].set_discoverable(True)
    await adapters[0].set_pairable(True)

    await adapters[1].set_powered(True)
    await adapters[1].set_discoverable(True)
    await adapters[1].set_pairable(True)

    print(f"Advertising on {await adapters[0].get_name()}")
    advert = Advertisement("Heart Monitor", ["180D", "1234"], 0x0340, 60 * 5, duration=5)
    await advert.register(bus, adapters[0])

    print(f"Starting scan on {await adapters[1].get_name()}")
    await adapters[1].start_discovery()

    agent = TestAgent(AgentCapability.KEYBOARD_DISPLAY)
    await agent.register(bus)

    devices = []
    print("Waiting for devices", end="")
    while len(devices) == 0:
        await asyncio.sleep(1)
        print(".", end="")
        devices = await adapters[1].get_devices()
    print("")

    for d in devices:
        print(f"Found '{await d.get_name()}'")
        if not await d.get_paired():
            print("   Pairing")
            await d.pair()

    print("Sleeping", end="")
    for _ in range(0,10):
        print(".", end="")
    print("")

    for d in devices:
        print(f"Device '{await d.get_name()}'")
        if await d.get_paired():
            print("   Removing")
            await adapters[1].remove_device(d)

asyncio.run(main())