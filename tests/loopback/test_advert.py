import asyncio
import pytest
import pytest_asyncio

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
    await advert.register(message_bus, adapters[0])

    await adapters[1].start_discovery()
    devices = await adapters[1].get_devices()
    
    assert len(devices) == 1
    assert await devices[0].get_alias() == "Heart Monitor"
    assert await devices[0].get_appearance() == 0x0340
    uuids = set(await devices[0].get_uuids())
    assert uuids == set([UUID16("180D"), UUID16("1234")])

    await adapters[1].stop_discovery()
