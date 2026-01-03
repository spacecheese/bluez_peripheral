import asyncio
from typing import Dict, Union, Optional
from unittest.mock import MagicMock, AsyncMock, create_autospec
from uuid import UUID
import threading

import pytest

from dbus_fast.introspection import Node
from dbus_fast.aio.proxy_object import ProxyInterface, ProxyObject

from bluez_peripheral.util import (
    get_message_bus,
    is_bluez_available,
    MessageBus,
)
from bluez_peripheral.gatt.service import ServiceCollection
from bluez_peripheral.adapter import Adapter
from bluez_peripheral.uuid16 import UUID16, UUIDLike
from bluez_peripheral.advert import Advertisement


def make_adapter_mock() -> MagicMock:
    adapter = MagicMock()

    advertising_manager = MagicMock()
    advertising_manager.call_register_advertisement = AsyncMock()
    advertising_manager.call_unregister_advertisement = AsyncMock()
    adapter.get_advertising_manager.return_value = advertising_manager

    gatt_manager = MagicMock()
    gatt_manager.call_register_application = AsyncMock()
    gatt_manager.call_unregister_application = AsyncMock()
    adapter.get_gatt_manager.return_value = gatt_manager

    return adapter


def make_message_bus_mock() -> MagicMock:
    bus = create_autospec(MessageBus, instance=True)

    proxy = create_autospec(ProxyObject, instance=True)
    interface = MagicMock()

    interface.call_register_agent = AsyncMock()
    interface.call_request_default_agent = AsyncMock()
    interface.call_unregister_agent = AsyncMock()

    proxy.get_interface.return_value = interface
    bus.get_proxy_object.return_value = proxy

    return bus


class BackgroundLoopWrapper:
    event_loop: asyncio.AbstractEventLoop
    thread: threading.Thread

    def __init__(self):
        self.event_loop = asyncio.new_event_loop()

        def _func():
            self.event_loop.run_forever()
            self.event_loop.close()

        self.thread = threading.Thread(
            target=_func,
            daemon=True
        )

    @property
    def running(self):
        return self.thread.is_alive()

    def start(self):
        self.thread.start()

    def stop(self):
        if self.thread is None or not self.thread.is_alive():
            return

        def _func():
            if self.event_loop is not None and self.event_loop.is_running():
                self.event_loop.stop()

        self.event_loop.call_soon_threadsafe(_func)
        self.thread.join()


async def get_first_adapter_or_skip(bus: MessageBus) -> Adapter:
    adapters = await Adapter.get_all(bus)
    if not len(adapters) > 0:
        pytest.skip("No adapters detected for testing.")
    else:
        return adapters[0]


async def bluez_available_or_skip(bus: MessageBus):
    if await is_bluez_available(bus):
        return
    else:
        pytest.skip("bluez is not available for testing.")


class ServiceNode:
    bus_name: str
    bus_path: str
    attr_interface: Optional[ProxyInterface]
    attr_type: Optional[str]

    _intf_hierarchy = [
        None,
        "org.bluez.GattService1",
        "org.bluez.GattCharacteristic1",
        "org.bluez.GattDescriptor1",
    ]

    def __init__(
        self,
        node: Node,
        *,
        bus: MessageBus,
        bus_name: str,
        bus_path: str,
        proxy: Optional[ProxyObject] = None,
        attr_interface: Optional[ProxyInterface] = None,
        attr_type: Optional[str] = None,
    ):
        self.node = node
        self.bus = bus
        self.bus_name = bus_name
        self.bus_path = bus_path
        self.proxy = proxy
        self.attr_interface = attr_interface
        self.attr_type = attr_type

    @staticmethod
    async def from_service_collection(
        bus: MessageBus, bus_name: str, bus_path: str
    ) -> "ServiceNode":
        node = await bus.introspect(bus_name, bus_path)
        return ServiceNode(node, bus=bus, bus_name=bus_name, bus_path=bus_path)

    @staticmethod
    def _node_has_intf(node: Node, intf: str):
        return any(i.name == intf for i in node.interfaces)

    async def get_children(self) -> Dict[Union[UUID16, UUID], "ServiceNode"]:
        children = []
        for node in self.node.nodes:
            assert node.name is not None
            path = self.bus_path + "/" + node.name

            attr_idx = self._intf_hierarchy.index(self.attr_type)
            attr_type = self._intf_hierarchy[attr_idx + 1]

            expanded_node = await self.bus.introspect(self.bus_name, path)

            proxy = None
            attr_interface = None
            if attr_type is not None and self._node_has_intf(expanded_node, attr_type):
                proxy = self.bus.get_proxy_object(self.bus_name, path, expanded_node)
                attr_interface = proxy.get_interface(attr_type)

            children.append(
                ServiceNode(
                    expanded_node,
                    bus=self.bus,
                    bus_name=self.bus_name,
                    bus_path=path,
                    proxy=proxy,
                    attr_type=attr_type,
                    attr_interface=attr_interface,
                )
            )

        res = {}
        for c in children:
            uuid = UUID16.parse_uuid(await c.attr_interface.get_uuid())
            res[uuid] = c
        return res

    async def get_child(self, *uuid: UUIDLike):
        child = self
        for u in uuid:
            children = await child.get_children()
            child = children[UUID16.parse_uuid(u)]

        return child


class BackgroundBusManager:
    _background_bus: Optional[MessageBus]

    def __init__(self):
        self._background_wrapper = BackgroundLoopWrapper()
        self._foreground_loop = None

    @property
    def foreground_loop(self):
        return self._foreground_loop

    @property
    def background_loop(self):
        return self._background_wrapper.event_loop

    async def start(self, bus_name: str):
        self._foreground_loop = asyncio.get_running_loop()

        async def _serve():
            await self._background_bus.wait_for_disconnect()

        self._background_wrapper.start()
        
        async def _start():
            self._background_bus = await get_message_bus()
            await self._background_bus.request_name(bus_name)
        
        asyncio.run_coroutine_threadsafe(_start(), self.background_loop).result()
        self._idle_task = asyncio.run_coroutine_threadsafe(
            _serve(), self.background_loop
        )

    async def stop(self):
        async def _stop():  
            self._background_bus.disconnect()

        asyncio.run_coroutine_threadsafe(_stop(), self.background_loop).result()
        self._idle_task.result()
        self._background_wrapper.stop()

    @property
    def background_bus(self):
        return self._background_bus

class BackgroundServiceManager(BackgroundBusManager):
    def __init__(self):
        self.adapter = make_adapter_mock()
        super().__init__()

    def register(self, services: ServiceCollection, bus_path: str):
        self._services = services
        asyncio.run_coroutine_threadsafe(
            services.register(self.background_bus, path=bus_path, adapter=self.adapter), 
            self.background_loop
        ).result()

    def unregister(self):
        asyncio.run_coroutine_threadsafe(
            self._services.unregister(), 
            self.background_loop
        ).result()
        self._services = None

    
class BackgroundAdvertManager(BackgroundBusManager):
    def __init__(self):
        self.adapter = make_adapter_mock()
        super().__init__()

    def register(self, advert: Advertisement, bus_path: str):
        self._advert = advert
        asyncio.run_coroutine_threadsafe(
            advert.register(self.background_bus, path=bus_path, adapter=self.adapter), 
            self.background_loop
        ).result()

    def unregister(self):
        asyncio.run_coroutine_threadsafe(
            self._advert.unregister(), 
            self.background_loop
        ).result()
        self._advert = None