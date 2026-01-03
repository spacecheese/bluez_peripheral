import pytest_asyncio

from bluez_peripheral.util import get_message_bus, MessageBus


@pytest_asyncio.fixture
async def message_bus():
    bus = await get_message_bus()
    yield bus
    bus.disconnect()