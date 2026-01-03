from uuid import UUID

import asyncio
import pytest

from bluez_peripheral.advert import Advertisement, AdvertisingIncludes
from bluez_peripheral.flags import AdvertisingPacketType

from .util import get_first_adapter_or_skip, bluez_available_or_skip, make_adapter_mock, BackgroundAdvertManager


@pytest.fixture
def bus_name():
    return "com.spacecheese.test"


@pytest.fixture
def bus_path():
    return "/com/spacecheese/bluez_peripheral/test"


@pytest.mark.asyncio
async def test_basic(message_bus, bus_name, bus_path):
    advert = Advertisement(
        "Testing Device Name",
        ["180A", "180D"],
        appearance=0x0340,
        timeout=2,
        packet_type=AdvertisingPacketType.PERIPHERAL,
        includes=AdvertisingIncludes.TX_POWER,
    )
    manager = BackgroundAdvertManager()
    await manager.start(bus_name)
    manager.register(advert, bus_path)

    introspection = await message_bus.introspect(bus_name, bus_path)
    proxy_object = message_bus.get_proxy_object(bus_name, bus_path, introspection)
    interface = proxy_object.get_interface("org.bluez.LEAdvertisement1")

    assert await interface.get_type() == "peripheral"
    # Case of UUIDs is not important.
    assert [id.lower() for id in await interface.get_service_uui_ds()] == [
        "180a",
        "180d",
    ]
    assert await interface.get_local_name() == "Testing Device Name"
    assert await interface.get_appearance() == 0x0340
    assert await interface.get_timeout() == 2
    assert await interface.get_includes() == ["tx-power"]

    manager.unregister()
    await manager.stop()


@pytest.mark.asyncio
async def test_includes_empty(message_bus, bus_name, bus_path):
    advert = Advertisement(
        "Testing Device Name",
        ["180A", "180D"],
        appearance=0x0340,
        timeout=2,
        packet_type=AdvertisingPacketType.PERIPHERAL,
        includes=AdvertisingIncludes.NONE,
    )
    manager = BackgroundAdvertManager()
    await manager.start(bus_name)
    manager.register(advert, bus_path)

    introspection = await message_bus.introspect(bus_name, bus_path)
    proxy_object = message_bus.get_proxy_object(
        bus_name, bus_path, introspection
    )
    interface = proxy_object.get_interface("org.bluez.LEAdvertisement1")
    assert await interface.get_includes() == []

    manager.unregister()
    await manager.stop()

@pytest.mark.asyncio
async def test_uuid128(message_bus, bus_name, bus_path):
    advert = Advertisement(
        "Improv Test",
        [UUID("00467768-6228-2272-4663-277478268000")],
        appearance=0x0340,
        timeout=2,
    )
    manager = BackgroundAdvertManager()
    await manager.start(bus_name)
    manager.register(advert, bus_path)

    introspection = await message_bus.introspect(bus_name, bus_path)
    proxy_object = message_bus.get_proxy_object(
        bus_name, bus_path, introspection
    )
    interface = proxy_object.get_interface("org.bluez.LEAdvertisement1")
    assert [
        id.lower() for id in await interface.get_service_uui_ds()
    ] == [
        "00467768-6228-2272-4663-277478268000",
    ]

    manager.unregister()
    await manager.stop()


@pytest.mark.asyncio
async def test_real(message_bus):
    await bluez_available_or_skip(message_bus)
    adapter = await get_first_adapter_or_skip(message_bus)

    initial_powered = await adapter.get_powered()
    initial_discoverable = await adapter.get_discoverable()

    await adapter.set_powered(True)
    await adapter.set_discoverable(True)

    advert = Advertisement(
        "Testing Device Name",
        ["180A", "180D"],
        appearance=0x0340,
        timeout=2,
    )

    try:
        await advert.register(message_bus, adapter=adapter)
    finally:
        await advert.unregister()

        await adapter.set_discoverable(initial_discoverable)
        await adapter.set_powered(initial_powered)
