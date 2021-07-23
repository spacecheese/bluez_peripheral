from tests.util import BusManager, MockAdapter, get_attrib

import re
from typing import Collection
from unittest import IsolatedAsyncioTestCase

from bluez_peripheral.util import get_message_bus
from bluez_peripheral.gatt.service import Service, ServiceCollection


class TestService1(Service):
    def __init__(self, includes: Collection[Service]):
        super().__init__("180A", primary=False, includes=includes)


class TestService2(Service):
    def __init__(self):
        super().__init__("180B")


class TestService3(Service):
    def __init__(self):
        super().__init__("180C")


class TestService(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self._client_bus = await get_message_bus()
        self._bus_manager = BusManager()
        self._path = "/com/spacecheese/bluez_peripheral/test_service"

    async def asyncTearDown(self):
        self._client_bus.disconnect()
        self._bus_manager.close()

    async def test_structure(self):
        async def inspector(path):
            introspection = await self._client_bus.introspect(
                self._bus_manager.name, path
            )

            child_names = [node.name for node in introspection.nodes]
            child_names = sorted(child_names)

            i = 0
            for name in child_names:
                assert re.match(r"^service0?" + str(i) + "$", name)
                i += 1

        service1 = TestService1([])
        service2 = TestService2()
        service3 = TestService3()
        collection = ServiceCollection([service1, service2, service3])

        adapter = MockAdapter(inspector)

        await collection.register(self._bus_manager.bus, self._path, adapter)
        await collection.unregister()

    async def test_include_modify(self):
        service3 = TestService3()
        service2 = TestService2()
        service1 = TestService1([service2, service3])
        collection = ServiceCollection([service1, service2])

        expect_service3 = False

        async def inspector(path):
            service1 = await get_attrib(
                self._client_bus, self._bus_manager.name, path, "180A"
            )
            service = service1.get_interface("org.bluez.GattService1")
            includes = await service.get_includes()

            service2 = await get_attrib(
                self._client_bus, self._bus_manager.name, path, "180B"
            )
            # Services must include themselves.
            assert service1.path in includes
            assert service2.path in includes

            if expect_service3:
                service3 = await get_attrib(
                    self._client_bus, self._bus_manager.name, path, "180C"
                )
                assert service3.path in includes

        adapter = MockAdapter(inspector)
        await collection.register(self._bus_manager.bus, self._path, adapter=adapter)
        await collection.unregister()

        collection.add_service(service3)
        expect_service3 = True
        await collection.register(self._bus_manager.bus, self._path, adapter=adapter)
        await collection.unregister()

        collection.remove_service(service3)
        expect_service3 = False
        await collection.register(self._bus_manager.bus, self._path, adapter=adapter)

