from util import *
from gatt.characteristic import *

from dbus_next import BusType
from dbus_next.aio import MessageBus

import asyncio


async def main():
    test = CharacteristicReadOptions()

    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    adapters = await Adapter.get_all()

    await bus.wait_for_disconnect()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
