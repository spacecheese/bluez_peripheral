from dbus_fast import Variant, BusType
from dbus_fast.aio import MessageBus
from dbus_fast.errors import DBusError

from typing import Any, Dict

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
        bus: The system dbus to use.

    Returns:
        True if bluez is found. False otherwise.
    """
    try:
        await bus.introspect("org.bluez", "/org/bluez")
        return True
    except DBusError:
        return False
