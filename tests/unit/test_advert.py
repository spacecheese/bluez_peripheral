from uuid import UUID
import pytest

from dbus_fast import Variant

from bluez_peripheral.advert import Advertisement, AdvertisingIncludes
from bluez_peripheral.flags import AdvertisingPacketType


def test_intervals_validation_partial_kwarg() -> None:
    with pytest.raises(ValueError, match="both be set"):
        Advertisement(
            "x",
            [],
            min_advertising_interval_ms=100,
        )


def test_intervals_validation_min_gt_max() -> None:
    with pytest.raises(ValueError, match="<="):
        Advertisement(
            "x",
            [],
            min_advertising_interval_ms=200,
            max_advertising_interval_ms=100,
        )


def test_intervals_validation_slot_too_small() -> None:
    # Min slot 0x20 <=> 20 ms; 19 ms is the largest integer ms with int(ms/0.625) < 0x20.
    with pytest.raises(ValueError, match="out of range"):
        Advertisement(
            "x",
            [],
            min_advertising_interval_ms=20 - 1,
            max_advertising_interval_ms=20,
        )


def test_intervals_validation_slot_too_large() -> None:
    # Max slot 0xFFFFFF; 10485759 is last integer max_ms still in range, 10485760 is first over.
    with pytest.raises(ValueError, match="out of range"):
        Advertisement(
            "x",
            [],
            min_advertising_interval_ms=20,
            max_advertising_interval_ms=10485759 + 1,
        )


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

    with pytest.raises(AttributeError):
        await interface.get_includes()


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
async def test_release(message_bus, bus_name, bus_path, background_advert):
    advert = Advertisement(
        "Attribs Test", ["180A", "180D"], appearance=0x0340, timeout=2
    )
    background_manager = background_advert(advert, path=bus_path)
    mock_advertising_manager = (
        background_manager.adapter.get_advertising_manager.return_value
    )

    mock_advertising_manager.reset_mock()

    introspection = await message_bus.introspect(bus_name, bus_path)
    proxy_object = message_bus.get_proxy_object(bus_name, bus_path, introspection)
    interface = proxy_object.get_interface("org.bluez.LEAdvertisement1")
    await interface.call_release()

    assert mock_advertising_manager.call_register_advertisement.await_count == 0
    assert mock_advertising_manager.call_unregister_advertisement.await_count == 0

    introspection = await message_bus.introspect(bus_name, bus_path)
    assert "org.bluez.LEAdvertisement1" not in introspection.interfaces


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
async def test_intervals_optional_omitted(
    bus_name, bus_path, message_bus, background_advert
):
    advert = Advertisement(
        "Testing Device Name",
        ["180A", "180D"],
        appearance=0x0340,
        timeout=2,
        packet_type=AdvertisingPacketType.PERIPHERAL,
    )
    background_advert(advert, path=bus_path)

    introspection = await message_bus.introspect(bus_name, bus_path)
    le_iface = next(
        i for i in introspection.interfaces if i.name == "org.bluez.LEAdvertisement1"
    )
    prop_names = {p.name for p in le_iface.properties}
    assert "MinInterval" not in prop_names
    assert "MaxInterval" not in prop_names


@pytest.mark.asyncio
async def test_intervals_exposed(bus_name, bus_path, message_bus, background_advert):
    advert = Advertisement(
        "Testing Device Name",
        ["180A", "180D"],
        appearance=0x0340,
        timeout=2,
        packet_type=AdvertisingPacketType.PERIPHERAL,
        min_advertising_interval_ms=100,
        max_advertising_interval_ms=150,
    )
    background_advert(advert, path=bus_path)

    introspection = await message_bus.introspect(bus_name, bus_path)
    le_iface = next(
        i for i in introspection.interfaces if i.name == "org.bluez.LEAdvertisement1"
    )
    prop_names = {p.name for p in le_iface.properties}
    assert "MinInterval" in prop_names
    assert "MaxInterval" in prop_names
    proxy_object = message_bus.get_proxy_object(bus_name, bus_path, introspection)
    interface = proxy_object.get_interface("org.bluez.LEAdvertisement1")
    assert await interface.get_min_interval() == 100
    assert await interface.get_max_interval() == 150


@pytest.mark.asyncio
async def test_default_path(message_bus, bus_name, background_advert):
    adverts = [
        Advertisement(
            f"Attribs Test{i}",
            ["180A", "180D"],
            appearance=0x0340,
        )
        for i in range(0, 11)
    ]
    for a in adverts:
        background_advert(a)

    # Make sure that adverts do not clash with each other and all interfaces are visible.
    paths = {a.export_path for a in adverts}
    assert len(paths) == len(adverts)

    for a in adverts:
        assert a.export_path is not None

        introspection = await message_bus.introspect(bus_name, a.export_path)
        proxy_object = message_bus.get_proxy_object(
            bus_name, a.export_path, introspection
        )
        _ = proxy_object.get_interface("org.bluez.LEAdvertisement1")
