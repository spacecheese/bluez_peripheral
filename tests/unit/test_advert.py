from uuid import UUID
import asyncio
import pytest

from dbus_fast import Variant

from bluez_peripheral.advert import Advertisement, AdvertisingIncludes
from bluez_peripheral.flags import AdvertisingPacketType


@pytest.fixture
def bus_name():
    return "com.spacecheese.test"


@pytest.fixture
def bus_path():
    return "/com/spacecheese/bluez_peripheral/test"


@pytest.mark.asyncio
async def test_basic(bus_name, bus_path, message_bus, background_advert):
    advert = Advertisement(
        "Testing Device Name",
        ["180A", "180D"],
        appearance=0x0340,
        timeout=2,
        packet_type=AdvertisingPacketType.PERIPHERAL,
        includes=AdvertisingIncludes.TX_POWER,
    )
    background_advert(advert, path=bus_path)

    introspection = await message_bus.introspect(bus_name, bus_path)
    proxy_object = message_bus.get_proxy_object(bus_name, bus_path, introspection)
    interface = proxy_object.get_interface("org.bluez.LEAdvertisement1")

    assert await interface.get_type() == "peripheral"
    # Case of UUIDs is not important.
    assert [i.lower() for i in await interface.get_service_uui_ds()] == [
        "180a",
        "180d",
    ]
    assert await interface.get_local_name() == "Testing Device Name"
    assert await interface.get_appearance() == 0x0340
    assert await interface.get_timeout() == 2
    assert await interface.get_includes() == ["tx-power"]


@pytest.mark.asyncio
async def test_includes_empty(bus_name, bus_path, message_bus, background_advert):
    advert = Advertisement(
        "Testing Device Name",
        ["180A", "180D"],
        appearance=bytes([0x03, 0x40]),
        timeout=2,
        packet_type=AdvertisingPacketType.PERIPHERAL,
        includes=AdvertisingIncludes.NONE,
    )
    background_advert(advert, path=bus_path)

    introspection = await message_bus.introspect(bus_name, bus_path)
    proxy_object = message_bus.get_proxy_object(bus_name, bus_path, introspection)
    interface = proxy_object.get_interface("org.bluez.LEAdvertisement1")
    assert await interface.get_includes() == []


@pytest.mark.asyncio
async def test_uuid128(bus_name, bus_path, message_bus, background_advert):
    advert = Advertisement(
        "Improv Test",
        [UUID("00467768-6228-2272-4663-277478268000")],
        appearance=0x0340,
        timeout=2,
    )
    background_advert(advert, path=bus_path)

    introspection = await message_bus.introspect(bus_name, bus_path)
    proxy_object = message_bus.get_proxy_object(bus_name, bus_path, introspection)
    interface = proxy_object.get_interface("org.bluez.LEAdvertisement1")
    assert [id.lower() for id in await interface.get_service_uui_ds()] == [
        "00467768-6228-2272-4663-277478268000",
    ]


@pytest.mark.asyncio
async def test_illegal_unregister():
    advert = Advertisement(
        "Improv Test",
        [UUID("00467768-6228-2272-4663-277478268000")],
        appearance=0x0340,
        timeout=2,
    )
    with pytest.raises(ValueError):
        await advert.unregister()


@pytest.mark.asyncio
async def test_default_release(message_bus, bus_name, bus_path, background_advert):
    advert = Advertisement(
        "Attribs Test", ["180A", "180D"], appearance=0x0340, timeout=2
    )
    background_advert(advert, path=bus_path)

    introspection = await message_bus.introspect(bus_name, bus_path)
    proxy_object = message_bus.get_proxy_object(bus_name, bus_path, introspection)
    interface = proxy_object.get_interface("org.bluez.LEAdvertisement1")
    await interface.call_release()

    assert not advert.is_exported


@pytest.mark.asyncio
async def test_custom_sync_release(message_bus, bus_name, bus_path, background_advert):
    foreground_loop = asyncio.get_running_loop()
    released = foreground_loop.create_future()

    def _release_callback():
        foreground_loop.call_soon_threadsafe(released.set_result, ())

    advert = Advertisement(
        "Attribs Test",
        ["180A", "180D"],
        appearance=0x0340,
        timeout=2,
        release_callback=_release_callback,
    )
    background_advert(advert, path=bus_path)

    introspection = await message_bus.introspect(bus_name, bus_path)
    proxy_object = message_bus.get_proxy_object(bus_name, bus_path, introspection)
    interface = proxy_object.get_interface("org.bluez.LEAdvertisement1")
    await interface.call_release()
    await asyncio.wait_for(released, timeout=0.1)

    assert advert.is_exported


@pytest.mark.asyncio
async def test_custom_async_release(message_bus, bus_name, bus_path, background_advert):
    foreground_loop = asyncio.get_running_loop()
    released = foreground_loop.create_future()

    async def _release_callback():
        foreground_loop.call_soon_threadsafe(released.set_result, ())

    advert = Advertisement(
        "Attribs Test",
        ["180A", "180D"],
        appearance=0x0340,
        timeout=2,
        release_callback=_release_callback,
    )
    background_advert(advert, path=bus_path)

    introspection = await message_bus.introspect(bus_name, bus_path)
    proxy_object = message_bus.get_proxy_object(bus_name, bus_path, introspection)
    interface = proxy_object.get_interface("org.bluez.LEAdvertisement1")
    await interface.call_release()
    await asyncio.wait_for(released, timeout=0.1)

    assert advert.is_exported


@pytest.mark.asyncio
async def test_args(message_bus, bus_name, bus_path, background_advert):
    advert = Advertisement(
        "Attribs Test",
        ["180A", "180D"],
        appearance=0x0340,
        timeout=2,
        solicit_uuids=["180F"],
        manufacturer_data={
            0: b"\0x0\0x1\0x2",
        },
    )
    background_advert(advert, path=bus_path)

    introspection = await message_bus.introspect(bus_name, bus_path)
    proxy_object = message_bus.get_proxy_object(bus_name, bus_path, introspection)
    interface = proxy_object.get_interface("org.bluez.LEAdvertisement1")
    assert [i.lower() for i in await interface.get_solicit_uui_ds()] == ["180f"]
    assert await interface.get_manufacturer_data() == {
        0: Variant("ay", b"\0x0\0x1\0x2")
    }


@pytest.mark.asyncio
async def test_args_service_data(message_bus, bus_name, bus_path, background_advert):
    advert = Advertisement(
        "Attribs Test",
        ["180A", "180D"],
        appearance=0x0340,
        timeout=2,
        service_data={"180A": b"\0x01\0x02"},
    )
    background_advert(advert, path=bus_path)

    introspection = await message_bus.introspect(bus_name, bus_path)
    proxy_object = message_bus.get_proxy_object(bus_name, bus_path, introspection)
    interface = proxy_object.get_interface("org.bluez.LEAdvertisement1")
    data = await interface.get_service_data()
    assert {k.lower(): v for k, v in data.items()} == {
        "180a": Variant("ay", b"\0x01\0x02")
    }


@pytest.mark.asyncio
async def test_default_path(message_bus, bus_name, background_advert):
    advert0 = Advertisement(
        "Attribs Test1",
        ["180A", "180D"],
        appearance=0x0340,
    )
    background_advert(advert0)

    advert1 = Advertisement(
        "Attribs Test2",
        ["180A", "180D"],
        appearance=0x0340,
    )
    background_advert(advert1)

    advert2 = Advertisement(
        "Attribs Test3",
        ["180A", "180D"],
        appearance=0x0340,
    )
    background_advert(advert2)

    # Make sure that adverts do not clash with each other and all interfaces are visible.
    assert advert0.export_path != advert1.export_path
    assert advert0.export_path != advert2.export_path
    assert advert1.export_path != advert2.export_path

    introspection = await message_bus.introspect(bus_name, advert0.export_path)
    proxy_object = message_bus.get_proxy_object(
        bus_name, advert0.export_path, introspection
    )
    _ = proxy_object.get_interface("org.bluez.LEAdvertisement1")

    introspection = await message_bus.introspect(bus_name, advert1.export_path)
    proxy_object = message_bus.get_proxy_object(
        bus_name, advert1.export_path, introspection
    )
    _ = proxy_object.get_interface("org.bluez.LEAdvertisement1")

    introspection = await message_bus.introspect(bus_name, advert2.export_path)
    proxy_object = message_bus.get_proxy_object(
        bus_name, advert2.export_path, introspection
    )
    _ = proxy_object.get_interface("org.bluez.LEAdvertisement1")
