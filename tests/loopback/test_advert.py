import pytest

from bluez_peripheral.advert import Advertisement
from bluez_peripheral.uuid16 import UUID16


@pytest.mark.asyncio
async def test_advertisement(message_bus, unpaired_adapters):
    adapters = unpaired_adapters

    await adapters[0].set_powered(True)
    await adapters[0].set_discoverable(True)
    await adapters[0].set_pairable(True)

    await adapters[1].set_powered(True)

    advert = Advertisement(
        "Heart Monitor",
        ["180D", "1234"],
        appearance=0x0340,
        timeout=300,
        duration=5,
    )
    await advert.register(message_bus, adapter=adapters[0])
    loopback_device = None
    async for device in adapters[1].discover_devices(duration=5.0):
        loopback_device = device

    assert loopback_device is not None
    assert await loopback_device.get_alias() == "Heart Monitor"
    assert await loopback_device.get_appearance() == 0x0340
    uuids = set(await loopback_device.get_uuids())
    assert uuids == set([UUID16("180D"), UUID16("1234")])


@pytest.mark.asyncio
async def test_advanced_data(message_bus, unpaired_adapters):
    adapters = unpaired_adapters

    await adapters[0].set_powered(True)
    await adapters[0].set_discoverable(True)

    advert = Advertisement(
        "Testing Device Name",
        ["180A", "180D"],
        appearance=0x0340,
        timeout=2,
        solicit_uuids=["180F"],
        service_data={"180A": b"\0x01\0x02"},
    )
    await advert.register(message_bus, adapter=adapters[0])


@pytest.mark.asyncio
async def test_manufacturer_data(message_bus, unpaired_adapters):
    adapters = unpaired_adapters

    await adapters[0].set_powered(True)
    await adapters[0].set_discoverable(True)

    advert = Advertisement(
        "Testing Device Name",
        ["180A", "180D"],
        appearance=0x0340,
        timeout=2,
        solicit_uuids=["180F"],
        manufacturer_data={
            0: b"\0x0\0x1\0x2",
        },
    )
    await advert.register(message_bus, adapter=adapters[0])
