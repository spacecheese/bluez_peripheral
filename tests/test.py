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

    advert = Advertisement("Heart Monitor", ["180D"], 0x0340, 60)
    await advert.register(bus, adapters[0])

    await adapters[1].start_discovery()

    await asyncio.sleep(5)

    agent = TestAgent(AgentCapability.KEYBOARD_DISPLAY)
    await agent.register(bus)

    devices = await adapters[1].get_devices(bus)
    for d in devices:
        if not await d.get_paired():
            await d.pair()

    while 1:
        await asyncio.sleep(5)

asyncio.run(main())