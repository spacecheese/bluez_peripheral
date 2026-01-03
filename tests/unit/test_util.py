import pytest

from bluez_peripheral.adapter import Adapter
from bluez_peripheral.util import get_message_bus
from ..unit.util import get_first_adapter_or_skip, bluez_available_or_skip


@pytest.mark.asyncio
async def test_get_first():
    bus = await get_message_bus()
    await bluez_available_or_skip(bus)

    if not len(await Adapter.get_all(bus)) > 0:
        with pytest.raises(ValueError):
            Adapter.get_first(bus)
    else:
        assert isinstance(await Adapter.get_first(bus), Adapter)

    bus.disconnect()


@pytest.mark.asyncio
async def test_alias_set():
    bus = await get_message_bus()
    await bluez_available_or_skip(bus)

    adapter = await get_first_adapter_or_skip(bus)

    await adapter.set_alias("Some test name")
    assert await adapter.get_alias() == "Some test name"

    bus.disconnect()


@pytest.mark.asyncio
async def test_alias_clear():
    bus = await get_message_bus()
    await bluez_available_or_skip(bus)

    adapter = await get_first_adapter_or_skip(bus)

    await adapter.set_alias("")
    assert await adapter.get_alias() == await adapter.get_name()

    bus.disconnect()


@pytest.mark.asyncio
async def test_powered():
    bus = await get_message_bus()
    await bluez_available_or_skip(bus)

    adapter = await get_first_adapter_or_skip(bus)

    initial_powered = await adapter.get_powered()

    await adapter.set_powered(False)
    assert not await adapter.get_powered()
    await adapter.set_powered(True)
    assert await adapter.get_powered()
    await adapter.set_powered(initial_powered)

    bus.disconnect()


@pytest.mark.asyncio
async def test_discoverable():
    bus = await get_message_bus()
    await bluez_available_or_skip(bus)

    adapter = await get_first_adapter_or_skip(bus)

    initial_discoverable = await adapter.get_discoverable()
    initial_powered = await adapter.get_powered()

    await adapter.set_powered(True)

    await adapter.set_discoverable(False)
    assert not await adapter.get_discoverable()
    await adapter.set_discoverable(True)
    assert await adapter.get_discoverable()
    await adapter.set_discoverable(initial_discoverable)
    await adapter.set_powered(initial_powered)

    bus.disconnect()


@pytest.mark.asyncio
async def test_pairable():
    bus = await get_message_bus()
    await bluez_available_or_skip(bus)

    adapter = await get_first_adapter_or_skip(bus)

    initial_pairable = await adapter.get_pairable()
    initial_powered = await adapter.get_powered()

    await adapter.set_pairable(False)
    assert not await adapter.get_pairable()
    await adapter.set_pairable(True)
    assert await adapter.get_pairable()
    await adapter.set_pairable(initial_pairable)
    await adapter.set_powered(initial_powered)

    bus.disconnect()


@pytest.mark.asyncio
async def test_pairable_timeout():
    bus = await get_message_bus()
    await bluez_available_or_skip(bus)

    adapter = await get_first_adapter_or_skip(bus)

    initial_pairable_timeout = await adapter.get_pairable_timeout()

    await adapter.set_pairable_timeout(30)
    assert await adapter.get_pairable_timeout() == 30
    await adapter.set_pairable_timeout(0)
    assert await adapter.get_pairable_timeout() == 0
    await adapter.set_pairable_timeout(initial_pairable_timeout)

    bus.disconnect()


@pytest.mark.asyncio
async def test_discoverable_timeout():
    bus = await get_message_bus()
    await bluez_available_or_skip(bus)

    adapter = await get_first_adapter_or_skip(bus)

    initial_discoverable_timeout = await adapter.get_discoverable_timeout()

    await adapter.set_discoverable_timeout(30)
    assert await adapter.get_discoverable_timeout() == 30
    await adapter.set_discoverable_timeout(0)
    assert await adapter.get_discoverable_timeout() == 0
    await adapter.set_discoverable_timeout(initial_discoverable_timeout)

    bus.disconnect()
