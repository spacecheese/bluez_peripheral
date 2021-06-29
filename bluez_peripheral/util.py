from dbus_next import Variant, BusType
from dbus_next.aio import MessageBus

from typing import Any, Collection, Dict

from dbus_next.aio.proxy_object import ProxyObject


def _getattr_variant(object: Dict[str, Variant], key: str, default: Any):
    if key in object:
        return object[key].value
    else:
        return default


def _snake_to_kebab(s: str) -> str:
    return s.lower().replace("_", "-")


def _snake_to_pascal(s: str) -> str:
    split = s.split("_")

    pascal = ""
    for section in split:
        pascal += section.lower().capitalize()

    return pascal

async def get_message_bus() -> MessageBus:
    return await MessageBus(bus_type=BusType.SYSTEM).connect()


class Adapter(ProxyObject):
    @classmethod
    async def get_all(cls, bus: MessageBus) -> Collection["Adapter"]:
        """Get a list of available Bluetooth adapters.

        Args:
            bus (MessageBus): The message bus used to query bluez.

        Returns:
            Collection[Adapter]: A list of available bluetooth adapters.
        """
        # TODO: Test.
        adapter_nodes = (await bus.introspect("org.bluez", "/org/bluez")).nodes

        adapters = []
        for node in adapter_nodes:
            introspection = await bus.introspect("org.bluez", "/org/bluez/" + node.name)
            proxy = bus.get_proxy_object(
                "org.bluez", "/org/bluez/" + node.name, introspection
            )
            adapters.append(cls(proxy))

        return adapters
