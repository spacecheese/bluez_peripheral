import pytest
import pytest_asyncio

from bluez_peripheral.adapter import Adapter
from bluez_peripheral.util import get_message_bus
from ..conftest import bluez_available, adapter_available


@pytest.mark.asyncio
@pytest.mark.skipif(not bluez_available())
async def test_get_first(message_bus):
    if not len(await Adapter.get_all(message_bus)) > 0:
        with pytest.raises(ValueError):
            await Adapter.get_first(message_bus)
    else:
        assert isinstance(await Adapter.get_first(message_bus), Adapter)


@pytest.mark.asyncio
@pytest.mark.skipif(not adapter_available())
async def test_alias_set(adapter):
    await adapter.set_alias("Some test name")
    assert await adapter.get_alias() == "Some test name"


@pytest.mark.asyncio
@pytest.mark.skipif(not adapter_available())
async def test_alias_clear(adapter):
    await adapter.set_alias("")
    assert await adapter.get_alias() == await adapter.get_name()


@pytest.mark.asyncio
@pytest.mark.skipif(not adapter_available())
async def test_powered(adapter):
    initial_powered = await adapter.get_powered()

    await adapter.set_powered(False)
    assert not await adapter.get_powered()
    await adapter.set_powered(True)
    assert await adapter.get_powered()
    await adapter.set_powered(initial_powered)


@pytest.mark.asyncio
async def test_discoverable(adapter):
    initial_discoverable = await adapter.get_discoverable()
    initial_powered = await adapter.get_powered()

    await adapter.set_powered(True)

    await adapter.set_discoverable(False)
    assert not await adapter.get_discoverable()
    await adapter.set_discoverable(True)
    assert await adapter.get_discoverable()
    await adapter.set_discoverable(initial_discoverable)
    await adapter.set_powered(initial_powered)


@pytest.mark.asyncio
async def test_pairable(adapter):
    initial_pairable = await adapter.get_pairable()
    initial_powered = await adapter.get_powered()

    await adapter.set_pairable(False)
    assert not await adapter.get_pairable()
    await adapter.set_pairable(True)
    assert await adapter.get_pairable()
    await adapter.set_pairable(initial_pairable)
    await adapter.set_powered(initial_powered)


@pytest.mark.asyncio
async def test_pairable_timeout(adapter):
    initial_pairable_timeout = await adapter.get_pairable_timeout()

    await adapter.set_pairable_timeout(30)
    assert await adapter.get_pairable_timeout() == 30
    await adapter.set_pairable_timeout(0)
    assert await adapter.get_pairable_timeout() == 0
    await adapter.set_pairable_timeout(initial_pairable_timeout)


@pytest.mark.asyncio
async def test_discoverable_timeout(adapter):
    initial_discoverable_timeout = await adapter.get_discoverable_timeout()

    await adapter.set_discoverable_timeout(30)
    assert await adapter.get_discoverable_timeout() == 30
    await adapter.set_discoverable_timeout(0)
    assert await adapter.get_discoverable_timeout() == 0
    await adapter.set_discoverable_timeout(initial_discoverable_timeout)
