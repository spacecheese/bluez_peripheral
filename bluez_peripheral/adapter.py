from dbus_fast.aio import MessageBus
from dbus_fast.errors import InvalidIntrospectionError
from dbus_fast.aio.proxy_object import ProxyObject

from typing import Collection

class Device:
    """A bluetooth device discovered by an adapter."""

    _INTERFACE = "org.bluez.Device1"
    _device_interface = None

    def __init__(self, proxy: ProxyObject):
        self._proxy = proxy
        self._device_interface = proxy.get_interface(self._INTERFACE)

    async def get_paired(self):
        return await self._device_interface.get_paired()

    async def pair(self):
        await self._device_interface.call_pair()


class Adapter:
    """A bluetooth adapter."""

    _INTERFACE = "org.bluez.Adapter1"
    _adapter_interface = None

    def __init__(self, proxy: ProxyObject):
        self._proxy = proxy
        self._adapter_interface = proxy.get_interface(self._INTERFACE)

    async def get_address(self) -> str:
        """Read the bluetooth address of this device."""
        return await self._adapter_interface.get_address()

    async def get_name(self) -> str:
        """Read the bluetooth hostname of this system."""
        return await self._adapter_interface.get_name()

    async def get_alias(self) -> str:
        """The user friendly name of the device."""
        return await self._adapter_interface.get_alias()

    async def set_alias(self, val: str):
        """Set the user friendly name for this device.
        Changing the device hostname directly is preferred.
        Writing an empty string will result in the alias resetting to the device hostname.
        """
        await self._adapter_interface.set_alias(val)

    async def get_powered(self) -> bool:
        """Indicates if the adapter is on or off."""
        return await self._adapter_interface.get_powered()

    async def set_powered(self, val: bool):
        """Turn this adapter on or off."""
        await self._adapter_interface.set_powered(val)

    async def get_pairable(self) -> bool:
        """Indicates if the adapter is in pairable state or not."""
        return await self._adapter_interface.get_pairable()

    async def set_pairable(self, val: bool):
        """Switch an adapter to pairable or non-pairable."""
        await self._adapter_interface.set_pairable(val)

    async def get_pairable_timeout(self) -> int:
        """Get the current pairable timeout"""
        return await self._adapter_interface.get_pairable_timeout()

    async def set_pairable_timeout(self, val: int):
        """Set the pairable timeout in seconds. A value of zero means that the
        timeout is disabled and it will stay in pairable mode forever."""
        await self._adapter_interface.set_pairable_timeout(val)

    async def get_discoverable(self) -> bool:
        """Indicates if the adapter is discoverable."""
        return await self._adapter_interface.get_discoverable()

    async def set_discoverable(self, val: bool):
        """Switch an adapter to discoverable or non-discoverable to either make it
        visible or hide it."""
        await self._adapter_interface.set_discoverable(val)

    async def get_discoverable_timeout(self) -> int:
        """Get the current discoverable timeout"""
        return await self._adapter_interface.get_discoverable_timeout()

    async def set_discoverable_timeout(self, val: int):
        """Set the discoverable timeout in seconds. A value of zero means that the
        timeout is disabled and it will stay in discoverable mode forever."""
        await self._adapter_interface.set_discoverable_timeout(val)

    async def start_discovery(self):
        """Start searching for other bluetooth devices."""
        await self._adapter_interface.call_start_discovery()

    async def stop_discovery(self):
        """Stop searching for other blutooth devices."""
        await self._adapter_interface.call_stop_discovery()

    async def get_devices(self) -> Collection[Device]:
        path = self._adapter_interface.path
        bus = self._adapter_interface.bus
        device_nodes = (await bus.introspect("org.bluez", path)).nodes

        devices = []
        for node in device_nodes:
            try:
                introspection = await bus.introspect("org.bluez", path + "/" + node.name)
                proxy = bus.get_proxy_object(
                    "org.bluez", path + "/" + node.name, introspection
                )
                devices.append(Device(proxy))
            except InvalidIntrospectionError:
                pass

        return devices
    
    async def remove_device(self, device: Device):
        path = device._device_interface.path
        await self._adapter_interface.call_remove_device(path)

    @classmethod
    async def get_all(cls, bus: MessageBus) -> Collection["Adapter"]:
        """Get a list of available Bluetooth adapters.

        Args:
            bus: The message bus used to query bluez.

        Returns:
            A list of available bluetooth adapters.
        """
        adapter_nodes = (await bus.introspect("org.bluez", "/org/bluez")).nodes

        adapters = []
        for node in adapter_nodes:
            try:
                introspection = await bus.introspect("org.bluez", "/org/bluez/" + node.name)
                proxy = bus.get_proxy_object(
                    "org.bluez", "/org/bluez/" + node.name, introspection
                )
                adapters.append(cls(proxy))
            except InvalidIntrospectionError:
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
            return adapters[0]
        else:
            raise ValueError("No bluetooth adapters could be found.")