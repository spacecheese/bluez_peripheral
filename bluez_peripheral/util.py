import asyncio

from dbus_next import Variant, BusType
from dbus_next.aio import MessageBus
from dbus_next.aio.proxy_object import ProxyObject
from dbus_next.errors import DBusError

from typing import Any, Collection, Dict

from uuid import UUID


def getattr_variant(object: Dict[str, Variant], key: str, default: Any):
    if key in object:
        return object[key].value
    else:
        return default


def snake_to_kebab(s: str) -> str:
    return s.lower().replace("_", "-")


def kebab_to_shouting_snake(s: str) -> str:
    return s.upper().replace("-", "_")


def snake_to_pascal(s: str) -> str:
    split = s.split("_")

    pascal = ""
    for section in split:
        pascal += section.lower().capitalize()

    return pascal


async def get_message_bus() -> MessageBus:
    """Gets a system message bus to use for registering services and adverts."""
    return await MessageBus(bus_type=BusType.SYSTEM).connect()


async def is_bluez_available(bus: MessageBus) -> bool:
    """Checks if bluez is registered on the system dbus.

    Args:
        bus (MessageBus): The system dbus to use.

    Returns:
        bool: True if bluez is found. False otherwise.
    """
    try:
        await bus.introspect("org.bluez", "/org/bluez")
        return True
    except DBusError:
        return False

class Device:
    """A device discovered by an adapter.
    Warning: This interface is experimental.
    """

    _INTERFACE = "org.bluez.Device1"
    _device_interface = None

    def __init__(self, proxy: ProxyObject):
        self._proxy = proxy
        self._device_interface = proxy.get_interface(self._INTERFACE)
    
    async def pair(self):
        await self._device_interface.call_pair()

    async def connect(self):
        await self._device_interface.call_connect()

    async def disconnect(self):
        await self._device_interface.call_disconnect()

    async def set_trusted(self, val: bool):
        await self._device_interface.set_trusted(val)

    async def get_trusted(self) -> bool:
        return await self._device_interface.get_trusted()

    async def get_uuids(self) -> Collection[UUID]:
        return await self._device_interface.get()


class Adapter:
    """A bluetooth adapter."""

    _INTERFACE = "org.bluez.Adapter1"
    _adapter_interface = None

    def __init__(self, proxy: ProxyObject):
        self._proxy = proxy
        self._adapter_interface = proxy.get_interface(self._INTERFACE)

    def __eq__(self, other: "Adapter"):
        return self._proxy.path == other._proxy.path

    def __ne__(self, other: "Adapter"):
        return not (self == other)

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

    async def get_discoverable(self) -> bool:
        """Get the discoverablity of this adapter."""
        return await self._adapter_interface.get_discoverable()

    async def set_discoverable(self, val: bool):
        """Make this device visible (or invisible) to nearby devices."""
        return await self._adapter_interface.set_discoverable(val)

    async def get_discovering(self) -> bool:
        """Check if this adapter is searching for nearby devices."""
        return await self._adapter_interface.get_discovering()

    async def set_discovering(self, val: bool):
        """Set the adapter to search (or stop searching) for nearby devices."""
        if val:
            await self._adapter_interface.call_start_discovery()
        else:
            await self._adapter_interface.call_stop_discovery()

    async def get_pairable(self) -> bool:
        """Determine if this device is pairable."""
        return await self._adapter_interface.get_pairable()

    async def set_pairable(self, val: bool):
        """Enable or disable pairing with this device."""
        return await self._adapter_interface.set_pairable(val)

    async def get_devices(self) -> Collection[Device]:
        bus = self._proxy.bus
        device_nodes = (await bus.introspect("org.bluez", self._proxy.path)).nodes
        
        devices = []
        for node in device_nodes:
            introspection = await bus.introspect("org.bluez", self._proxy.path + "/" + node.name)
            proxy = bus.get_proxy_object(
                "org.bluez", "/org/bluez/" + node.name, introspection
            )
            devices.append(Device(proxy))

        return devices

    @classmethod
    async def get_all(cls, bus: MessageBus) -> Collection["Adapter"]:
        """Get a list of available Bluetooth adapters.

        Args:
            bus (MessageBus): The message bus used to query bluez.

        Returns:
            Collection[Adapter]: A list of available bluetooth adapters.
        """
        adapter_nodes = None
        try:
            adapter_nodes = (await bus.introspect("org.bluez", "/org/bluez", 1)).nodes
        except (asyncio.TimeoutError):
            # Bluez aparrently fails to respond to introspection requests when no bluetooth devices are active.
            return []

        adapters = []
        for node in adapter_nodes:
            introspection = await bus.introspect("org.bluez", "/org/bluez/" + node.name)
            proxy = bus.get_proxy_object(
                "org.bluez", "/org/bluez/" + node.name, introspection
            )
            adapters.append(cls(proxy))

        return adapters

    @classmethod
    async def get_first(cls, bus: MessageBus) -> "Adapter":
        """Gets the first adapter listed by bluez.

        Args:
            bus (MessageBus): The bus to use for adapter discovery.

        Raises:
            ValueError: Raised when no bluetooth adapters are available.

        Returns:
            Adapter: The resulting adapter.
        """
        adapters = await cls.get_all(bus)
        if len(adapters) > 0:
            return adapters[0]
        else:
            raise ValueError("No bluetooth adapters could be found.")
