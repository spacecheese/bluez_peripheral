from dbus_next import Variant, BusType
from dbus_next.aio import MessageBus

from typing import Any, Collection, Dict

from dbus_next.aio.proxy_object import ProxyObject
from dbus_next.errors import DBusError


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

    @classmethod
    async def get_all(cls, bus: MessageBus) -> Collection["Adapter"]:
        """Get a list of available Bluetooth adapters.

        Args:
            bus (MessageBus): The message bus used to query bluez.

        Returns:
            Collection[Adapter]: A list of available bluetooth adapters.
        """
        adapter_nodes = (await bus.introspect("org.bluez", "/org/bluez")).nodes

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
