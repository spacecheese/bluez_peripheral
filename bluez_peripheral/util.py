from typing import Any, Dict

from dbus_fast import Variant, DBusError
from dbus_fast.constants import BusType
from dbus_fast.aio.message_bus import MessageBus


def _getattr_variant(obj: Dict[str, Variant], key: str, default: Any) -> Any:
    if key in obj:
        return obj[key].value

    return default


def _snake_to_kebab(s: str) -> str:
    return s.lower().replace("_", "-")


def _kebab_to_shouting_snake(s: str) -> str:
    return s.upper().replace("-", "_")


def _snake_to_pascal(s: str) -> str:
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
