import asyncio
from typing import Collection, Dict, Tuple, List, AsyncIterator

from dbus_fast import Variant
from dbus_fast.aio import MessageBus, ProxyInterface
from dbus_fast.aio.proxy_object import ProxyObject
from dbus_fast import InvalidIntrospectionError, InterfaceNotFoundError
from dbus_fast.errors import DBusError

from .util import _kebab_to_shouting_snake
from .flags import AdvertisingIncludes
from .uuid16 import UUID16, UUIDLike
from .error import BluezNotAvailableError


class Device:
    """A bluetooth device discovered by an adapter.
    Represents an `org.bluez.Device1 <https://raw.githubusercontent.com/bluez/bluez/refs/heads/master/doc/org.bluez.Device.rst>`_ instance.
    """

    _INTERFACE = "org.bluez.Device1"
    _device_interface: ProxyInterface

    def __init__(self, proxy: ProxyObject):
        self._proxy = proxy
        self._device_interface = proxy.get_interface(self._INTERFACE)

    async def get_paired(self) -> bool:
        """Returns true if the parent adapter is paired with this device. False otherwise."""
        return await self._device_interface.get_paired()  # type: ignore

    async def pair(self) -> None:
        """Attempts to pair the parent adapter with this device."""
        await self._device_interface.call_pair()  # type: ignore

    async def remove(self, adapter: "Adapter") -> None:
        """Disconnects and unpairs from this device."""
        interface = adapter.get_adapter_interface()
        await interface.call_remove_device(self._device_interface._path)  # type: ignore  # pylint: disable=protected-access

    async def get_name(self) -> str:
        """Returns the display name of this device (use alias instead to get the display name)."""
        return await self._device_interface.get_name()  # type: ignore

    async def get_alias(self) -> str:
        """Returns the alias of this device."""
        return await self._device_interface.get_alias()  # type: ignore

    async def get_appearance(self) -> int:
        """Returns the appearance of the device."""
        return await self._device_interface.get_appearance()  # type: ignore

    async def get_uuids(self) -> Collection[UUIDLike]:
        """Returns the collection of UUIDs representing the services available on this device."""
        ids = await self._device_interface.get_uui_ds()  # type: ignore
        return [UUID16.parse_uuid(i) for i in ids]

    async def get_manufacturer_data(self) -> Dict[int, bytes]:
        """Returns the manufacturer data."""
        return await self._device_interface.get_manufacturer_data()  # type: ignore

    async def get_service_data(self) -> List[Tuple[UUIDLike, bytes]]:
        """Returns the service data."""
        data = await self._device_interface.get_service_data()  # type: ignore
        return [(UUID16.parse_uuid(u), d) for u, d in data]


class Adapter:
    """A bluetooth adapter.
    Represents an `org.bluez.Adapter1 <https://raw.githubusercontent.com/bluez/bluez/refs/heads/master/doc/org.bluez.Adapter.rst>`_ instance.
    """

    _INTERFACE = "org.bluez.Adapter1"
    _GATT_MANAGER_INTERFACE = "org.bluez.GattManager1"
    _ADVERTISING_MANAGER_INTERFACE = "org.bluez.LEAdvertisingManager1"
    _proxy: ProxyObject
    _adapter_interface: ProxyInterface

    def __init__(self, proxy: ProxyObject):
        self._proxy = proxy
        self._adapter_interface = proxy.get_interface(self._INTERFACE)
        self._discovery_stopped = asyncio.Event()

    def get_adapter_interface(self) -> ProxyInterface:
        """Returns the org.bluez.Adapter associated with this adapter."""
        return self._adapter_interface

    def get_gatt_manager(self) -> ProxyInterface:
        """Returns the org.bluez.GattManager1 interface associated with this adapter."""
        return self._proxy.get_interface(self._GATT_MANAGER_INTERFACE)

    def get_advertising_manager(self) -> ProxyInterface:
        """Returns the org.bluez.LEAdvertisingManager1 interface associated with this adapter."""
        return self._proxy.get_interface(self._ADVERTISING_MANAGER_INTERFACE)

    async def get_address(self) -> str:
        """Read the bluetooth address of this device."""
        return await self._adapter_interface.get_address()  # type: ignore

    async def get_name(self) -> str:
        """Read the bluetooth hostname of this system."""
        return await self._adapter_interface.get_name()  # type: ignore

    async def get_alias(self) -> str:
        """The user friendly name of the device."""
        return await self._adapter_interface.get_alias()  # type: ignore

    async def set_alias(self, val: str) -> None:
        """Set the user friendly name for this device.
        Changing the device hostname directly is preferred.
        Writing an empty string will result in the alias resetting to the device hostname.
        """
        await self._adapter_interface.set_alias(val)  # type: ignore

    async def get_powered(self) -> bool:
        """Indicates if the adapter is on or off."""
        return await self._adapter_interface.get_powered()  # type: ignore

    async def set_powered(self, val: bool) -> None:
        """Turn this adapter on or off."""
        await self._adapter_interface.set_powered(val)  # type: ignore

    async def get_pairable(self) -> bool:
        """Indicates if the adapter is in pairable state or not."""
        return await self._adapter_interface.get_pairable()  # type: ignore

    async def set_pairable(self, val: bool) -> None:
        """Switch an adapter to pairable or non-pairable."""
        await self._adapter_interface.set_pairable(val)  # type: ignore

    async def get_pairable_timeout(self) -> int:
        """Get the current pairable timeout"""
        return await self._adapter_interface.get_pairable_timeout()  # type: ignore

    async def set_pairable_timeout(self, val: int) -> None:
        """Set the pairable timeout in seconds. A value of zero means that the
        timeout is disabled and it will stay in pairable mode forever."""
        await self._adapter_interface.set_pairable_timeout(val)  # type: ignore

    async def get_discoverable(self) -> bool:
        """Indicates if the adapter is discoverable."""
        return await self._adapter_interface.get_discoverable()  # type: ignore

    async def set_discoverable(self, val: bool) -> None:
        """Switch an adapter to discoverable or non-discoverable to either make it
        visible or hide it."""
        await self._adapter_interface.set_discoverable(val)  # type: ignore

    async def get_discoverable_timeout(self) -> int:
        """Get the current discoverable timeout"""
        return await self._adapter_interface.get_discoverable_timeout()  # type: ignore

    async def set_discoverable_timeout(self, val: int) -> None:
        """Set the discoverable timeout in seconds. A value of zero means that the
        timeout is disabled and it will stay in discoverable mode forever."""
        await self._adapter_interface.set_discoverable_timeout(val)  # type: ignore

    async def get_supported_advertising_includes(self) -> AdvertisingIncludes:
        """Returns a flag set of the advertising includes supported by this adapter."""
        interface = self.get_advertising_manager()
        includes = await interface.get_supported_includes()  # type: ignore
        flags = AdvertisingIncludes.NONE
        for inc in includes:
            inc = AdvertisingIncludes[_kebab_to_shouting_snake(inc)]
            # Combine all the included flags.
            flags |= inc
        return flags

    async def get_discovering(self) -> bool:
        """Returns true if the adapter is discovering. False otherwise."""
        return await self._adapter_interface.get_discovering()  # type: ignore

    async def start_discovery(self) -> None:
        """Start searching for other bluetooth devices."""
        await self._adapter_interface.call_start_discovery()  # type: ignore
        self._discovery_stopped.clear()

    async def stop_discovery(self) -> None:
        """Stop searching for other bluetooth devices."""
        await self._adapter_interface.call_stop_discovery()  # type: ignore
        self._discovery_stopped.set()

    async def _get_device(self, path: str) -> Device:
        bus = self._adapter_interface.bus

        introspection = await bus.introspect("org.bluez", path)
        proxy = bus.get_proxy_object("org.bluez", path, introspection)
        proxy.get_interface("org.bluez.Device1")
        return Device(proxy)

    async def discover_devices(self, duration: float = 10.0) -> AsyncIterator[Device]:
        """
        Asynchronously search for other bluetooth devices.

        Args:
            duration: The number of seconds to perform the discovery scan. Defaults to 10.0 seconds.
        """
        queue: asyncio.Queue[Tuple[str, Dict[str, Dict[str, Variant]]]] = (
            asyncio.Queue()
        )

        def _interface_added(path: str, intfs_and_props: Dict[str, Dict[str, Variant]]):  # type: ignore
            queue.put_nowait((path, intfs_and_props))

        object_manager_interface = self._proxy.get_interface(
            "org.freedesktop.DBus.ObjectManager"
        )
        object_manager_interface.on_interfaces_added(_interface_added)  # type: ignore

        yielded_paths = set()

        async def _stop_discovery() -> None:
            await asyncio.sleep(duration)
            await self.stop_discovery()

        await self.start_discovery()
        stop_task = None
        if duration > 0:
            stop_task = asyncio.create_task(_stop_discovery())

        while not self._discovery_stopped.is_set():
            if stop_task is not None:
                queue_task = asyncio.create_task(queue.get())

                done, _ = await asyncio.wait(
                    [queue_task, stop_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )

                if stop_task in done and queue_task not in done:
                    queue_task.cancel()
                    try:
                        await queue_task
                    except asyncio.CancelledError:
                        pass
                    break

                path, intfs_and_props = queue_task.result()
            else:
                path, intfs_and_props = await queue.get()

            if path in yielded_paths or "org.bluez.Device1" not in intfs_and_props:
                continue

            yield await self._get_device(path)
            yielded_paths.add(path)

        if stop_task is not None and stop_task.done():
            stop_task.cancel()
            try:
                await stop_task
            except asyncio.CancelledError:
                pass

        object_manager_interface.off_interfaces_added(_interface_added)  # type: ignore
        return

    async def get_devices(self) -> List[Device]:
        """Returns a list of devices which have been discovered by this adapter."""
        assert self._adapter_interface is not None

        path = self._adapter_interface.path
        bus = self._adapter_interface.bus

        device_nodes = (await bus.introspect("org.bluez", path)).nodes

        devices = []
        for node in device_nodes:
            if node.name is None:
                continue

            devices.append(await self._get_device(path + "/" + node.name))
        return devices

    @classmethod
    async def get_all(cls, bus: MessageBus) -> List["Adapter"]:
        """Get a list of available Bluetooth adapters.

        Args:
            bus: The message bus used to query bluez.

        Returns:
            A list of available bluetooth adapters.
        """
        try:
            adapter_nodes = (await bus.introspect("org.bluez", "/org/bluez")).nodes
        except DBusError as e:
            raise BluezNotAvailableError("org.bluez could not be introspected") from e

        adapters = []
        for node in adapter_nodes:
            if node.name is None:
                continue
            try:
                introspection = await bus.introspect(
                    "org.bluez", "/org/bluez/" + node.name
                )
                proxy = bus.get_proxy_object(
                    "org.bluez", "/org/bluez/" + node.name, introspection
                )
                adapters.append(cls(proxy))
            except (InvalidIntrospectionError, InterfaceNotFoundError):
                pass

        return adapters

    @classmethod
    async def get_first(cls, bus: MessageBus) -> "Adapter":
        """Gets the first adapter listed by bluez.

        Args:
            bus: The bus to use for adapter discovery.

        Raises:
            ValueError: Raised when no bluetooth adapters are available.

        Returns:
            The resulting adapter.
        """
        adapters = await cls.get_all(bus)
        if len(adapters) > 0:
            return next(iter(adapters))
        raise ValueError("No bluetooth adapters could be found.")
