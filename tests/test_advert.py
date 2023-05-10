from unittest import IsolatedAsyncioTestCase
from unittest.case import SkipTest

from tests.util import *
from bluez_peripheral.util import get_message_bus
from bluez_peripheral.advert import Advertisement, PacketType, AdvertisingIncludes

from uuid import UUID


class TestAdvert(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self._bus_manager = BusManager()
        self._client_bus = await get_message_bus()

    async def asyncTearDown(self):
        self._client_bus.disconnect()
        self._bus_manager.close()

    async def test_basic(self):
        advert = Advertisement(
            "Testing Device Name",
            ["180A", "180D"],
            0x0340,
            2,
            packetType=PacketType.PERIPHERAL,
            includes=AdvertisingIncludes.TX_POWER,
        )

        async def inspector(path):
            introspection = await self._client_bus.introspect(
                self._bus_manager.name, path
            )
            proxy_object = self._client_bus.get_proxy_object(
                self._bus_manager.name, path, introspection
            )
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

        path = "/com/spacecheese/bluez_peripheral/test_advert/advert0"
        adapter = MockAdapter(inspector)
        await advert.register(self._bus_manager.bus, adapter, path)

    async def test_includes_empty(self):
        advert = Advertisement(
            "Testing Device Name",
            ["180A", "180D"],
            0x0340,
            2,
            packetType=PacketType.PERIPHERAL,
            includes=AdvertisingIncludes.NONE,
        )

        async def inspector(path):
            introspection = await self._client_bus.introspect(
                self._bus_manager.name, path
            )
            proxy_object = self._client_bus.get_proxy_object(
                self._bus_manager.name, path, introspection
            )
            interface = proxy_object.get_interface("org.bluez.LEAdvertisement1")

            assert await interface.get_includes() == []

        adapter = MockAdapter(inspector)
        await advert.register(self._bus_manager.bus, adapter)

    async def test_uuid128(self):
        advert = Advertisement(
            "Improv Test",
            [UUID("00467768-6228-2272-4663-277478268000")],
            0x0340,
            2,
        )

        async def inspector(path):
            introspection = await self._client_bus.introspect(
                self._bus_manager.name, path
            )
            proxy_object = self._client_bus.get_proxy_object(
                self._bus_manager.name, path, introspection
            )
            interface = proxy_object.get_interface("org.bluez.LEAdvertisement1")

            assert [id.lower() for id in await interface.get_service_uui_ds()] == [
                "00467768-6228-2272-4663-277478268000",
            ]
            print(await interface.get_service_uui_ds())

        adapter = MockAdapter(inspector)
        await advert.register(self._bus_manager.bus, adapter)

    async def test_real(self):
        await bluez_available_or_skip(self._client_bus)
        adapter = await get_first_adapter_or_skip(self._client_bus)

        advert = Advertisement(
            "Testing Device Name",
            ["180A", "180D"],
            0x0340,
            2,
        )

        await advert.register(self._client_bus, adapter)
