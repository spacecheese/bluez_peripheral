from typing import Sequence

from dbus_fast.aio import MessageBus, ProxyInterface
from dbus_fast.aio.proxy_object import ProxyObject
from dbus_fast import InvalidIntrospectionError, InterfaceNotFoundError

from .util import _kebab_to_shouting_snake
from .flags import AdvertisingIncludes


class Device:
    """A bluetooth device discovered by an adapter."""

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

    async def get_name(self) -> str:
        """Returns the display name of this device."""
        return await self._device_interface.get_name()  # type: ignore

    async def remove(self, adapter: "Adapter") -> None:
        """Disconnects and unpairs from this device."""
        interface = adapter.get_adapter_interface()
        await interface.call_remove_device(self._device_interface._path)  # type: ignore  # pylint: disable=protected-access


class Adapter:
    """A bluetooth adapter."""

    BUS_INTERFACE = "org.bluez.Adapter1"
    _GATT_MANAGER_INTERFACE = "org.bluez.GattManager1"
    _ADVERTISING_MANAGER_INTERFACE = "org.bluez.LEAdvertisingManager1"
    _proxy: ProxyObject
    _adapter_interface: ProxyInterface

    def __init__(self, proxy: ProxyObject):
        self._proxy = proxy
        self._adapter_interface = proxy.get_interface(self.BUS_INTERFACE)

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

    async def start_discovery(self) -> None:
        """Start searching for other bluetooth devices."""
        await self._adapter_interface.call_start_discovery()  # type: ignore

    async def stop_discovery(self) -> None:
        """Stop searching for other bluetooth devices."""
        await self._adapter_interface.call_stop_discovery()  # type: ignore

    async def get_devices(self) -> Sequence[Device]:
        """Returns a sequence of devices which have been discovered by this adapter."""
        assert self._adapter_interface is not None

        path = self._adapter_interface.path
        bus = self._adapter_interface.bus

        device_nodes = (await bus.introspect("org.bluez", path)).nodes

        devices = []
        for node in device_nodes:
            if node.name is None:
                continue
            try:
                introspection = await bus.introspect(
                    "org.bluez", path + "/" + node.name
                )
                proxy = bus.get_proxy_object(
                    "org.bluez", path + "/" + node.name, introspection
                )
                devices.append(Device(proxy))
            except InvalidIntrospectionError:
                pass

        return devices

    @classmethod
    async def get_all(cls, bus: MessageBus) -> Sequence["Adapter"]:
        """Get a list of available Bluetooth adapters.

        Args:
            bus: The message bus used to query bluez.

        Returns:
            A list of available bluetooth adapters.
        """
        adapter_nodes = (await bus.introspect("org.bluez", "/org/bluez")).nodes

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
