import asyncio
from pathlib import Path

import pytest
import pytest_asyncio

from bluez_peripheral.util import get_message_bus, is_bluez_available
from bluez_peripheral.adapter import Adapter


def bluez_available():
    async def _bluez_available():
        bus = await get_message_bus()
        return await is_bluez_available(bus)

    return asyncio.run(_bluez_available())


requires_bluez = pytest.mark.skipif(
    not bluez_available(), reason="bluez is not available"
)


def adapter_available():
    async def _adapter_available():
        bus = await get_message_bus()
        if not await is_bluez_available(bus):
            return False

        adapters = await Adapter.get_all(bus)
        return len(adapters) > 0

    return asyncio.run(_adapter_available())


requires_adapter = pytest.mark.skipif(
    not adapter_available(), reason="no adapters are available"
)


def pytest_ignore_collect(collection_path: Path, config):
    if not bluez_available() and "loopback" in str(collection_path):
        return True
    return False


@pytest_asyncio.fixture
async def adapter(message_bus):
    return await Adapter.get_first(message_bus)


@pytest_asyncio.fixture
async def message_bus():
    bus = await get_message_bus()
    yield bus
    bus.disconnect()
