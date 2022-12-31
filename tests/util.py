from typing import Tuple
import asyncio
from threading import Thread, Event
from unittest.case import SkipTest

from dbus_next.introspection import Node

from bluez_peripheral.util import *
from bluez_peripheral.uuid16 import UUID16


class BusManager:
    def __init__(self, name="com.spacecheese.test"):
        bus_ready = Event()
        self.name = name

        async def operate_bus_async():
            # Setup the bus.
            self.bus = await get_message_bus()
            await self.bus.request_name(name)

            bus_ready.set()

            await self.bus.wait_for_disconnect()

        def operate_bus():
            asyncio.run(operate_bus_async())

        self._thread = Thread(target=operate_bus)
        self._thread.start()

        bus_ready.wait()

    def close(self):
        self.bus.disconnect()


async def get_first_adapter_or_skip(bus: MessageBus) -> Adapter:
    adapters = await Adapter.get_all(bus)
    if not len(adapters) > 0:
        raise SkipTest("No adapters detected for testing.")
    else:
        return adapters[0]


async def bluez_available_or_skip(bus: MessageBus):
    if await is_bluez_available(bus):
        return
    else:
        raise SkipTest("bluez is not available for testing.")


class MockAdapter(Adapter):
    def __init__(self, inspector):
        self._inspector = inspector
        self._proxy = self

    def get_interface(self, name):
        return self

    async def call_register_advertisement(self, path, obj):
        await self._inspector(path)

    async def call_register_application(self, path, obj):
        await self._inspector(path)

    async def call_unregister_application(self, path):
        pass


async def find_attrib(bus, bus_name, path, nodes, target_uuid) -> Tuple[Node, str]:
    for node in nodes:
        node_path = path + "/" + node.name

        introspection = await bus.introspect(bus_name, node_path)
        proxy = bus.get_proxy_object(bus_name, node_path, introspection)

        uuid = None
        interface_names = [interface.name for interface in introspection.interfaces]
        if "org.bluez.GattService1" in interface_names:
            uuid = await proxy.get_interface("org.bluez.GattService1").get_uuid()
        elif "org.bluez.GattCharacteristic1" in interface_names:
            uuid = await proxy.get_interface("org.bluez.GattCharacteristic1").get_uuid()
        elif "org.bluez.GattDescriptor1" in interface_names:
            uuid = await proxy.get_interface("org.bluez.GattDescriptor1").get_uuid()

        if UUID16(uuid) == UUID16(target_uuid):
            return introspection, node_path

    raise ValueError(
        "The attribute with uuid '" + str(target_uuid) + "' could not be found."
    )


async def get_attrib(bus, bus_name, path, service_uuid, char_uuid=None, desc_uuid=None):
    introspection = await bus.introspect(bus_name, path)

    nodes = introspection.nodes
    introspection, path = await find_attrib(bus, bus_name, path, nodes, service_uuid)

    if char_uuid is None:
        return bus.get_proxy_object(bus_name, path, introspection)

    nodes = introspection.nodes
    introspection, path = await find_attrib(bus, bus_name, path, nodes, char_uuid)

    if desc_uuid is None:
        return bus.get_proxy_object(bus_name, path, introspection)

    nodes = introspection.nodes
    introspection, path = await find_attrib(bus, bus_name, path, nodes, desc_uuid)

    return bus.get_proxy_object(bus_name, path, introspection)
