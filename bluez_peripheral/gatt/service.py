import inspect
from typing import List, Optional, Collection

from dbus_fast.constants import PropertyAccess
from dbus_fast.service import ServiceInterface, dbus_property
from dbus_fast.aio.message_bus import MessageBus
from dbus_fast.aio.proxy_object import ProxyInterface

from .characteristic import characteristic
from ..uuid16 import UUID16, UUIDCompatible
from ..adapter import Adapter


# See https://github.com/bluez/bluez/blob/master/doc/org.bluez.GattService.rst
class Service(ServiceInterface):
    """Create a bluetooth service with the specified uuid.

    Args:
        uuid: The UUID of this service. A full list of recognized values is provided by the `Bluetooth SIG Assigned Numbers <https://www.bluetooth.com/specifications/assigned-numbers/>`_
        primary: True if this service is a primary service (instead of a secondary service). False otherwise. Defaults to True.
        includes: Any services to include in this service.
            Services must be registered at the time Includes is read to be included.
    """

    _INTERFACE = "org.bluez.GattService1"

    def _populate(self) -> None:
        # Only interested in characteristic members.
        members = inspect.getmembers(
            type(self), lambda m: isinstance(m, characteristic)
        )

        for _, member in members:
            member.set_service(self)

            # Some characteristics will occur multiple times due to different decorators.
            if not member in self._characteristics:
                self.add_characteristic(member)

    def __init__(
        self,
        uuid: UUIDCompatible,
        primary: bool = True,
        includes: Optional[Collection["Service"]] = None,
    ):
        # Make sure uuid is a uuid16.
        self._uuid = UUID16.parse_uuid(uuid)
        self._primary = primary
        self._characteristics: List[characteristic] = []
        self._path: Optional[str] = None
        if includes is None:
            includes = []
        self._includes = includes
        self._populate()
        self._collection: Optional[ServiceCollection] = None

        super().__init__(self._INTERFACE)

    def is_registered(self) -> bool:
        """Check if this service is registered with the bluez service manager.

        Returns:
            bool: True if the service is registered. False otherwise.
        """
        return not self._path is None

    def add_characteristic(self, char: characteristic) -> None:
        """Add the specified characteristic to this service declaration.

        Args:
            char: The characteristic to add.

        Raises:
            ValueError: Raised when the service is registered with the bluez service manager and thus cannot be modified.
        """
        if self.is_registered():
            raise ValueError(
                "Registered services cannot be modified. Please unregister the containing application."
            )

        self._characteristics.append(char)

    def remove_characteristic(self, char: characteristic) -> None:
        """Remove the specified characteristic from this service declaration.

        Args:
            char: The characteristic to remove.

        Raises:
            ValueError: Raised if the service is registered with the bluez service manager and thus cannot be modified.
        """
        if self.is_registered():
            raise ValueError(
                "Registered services cannot be modified. Please unregister the containing application."
            )

        self._characteristics.remove(char)

    def _export(self, bus: MessageBus, path: str) -> None:
        self._path = path

        # Export this and number each child characteristic.
        bus.export(path, self)
        i = 0
        for char in self._characteristics:
            char._export(bus, path, i)
            i += 1

    def _unexport(self, bus: MessageBus) -> None:
        if self._path is None:
            return

        # Unexport this and every child characteristic.
        bus.unexport(self._path, self._INTERFACE)
        for char in self._characteristics:
            char._unexport(bus)

        self._path = None

    async def register(
        self,
        bus: MessageBus,
        path: str = "/com/spacecheese/bluez_peripheral",
        adapter: Optional[Adapter] = None,
    ) -> None:
        """Register this service as a standalone service.
        Using this multiple times will cause path conflicts.

        Args:
            bus: The bus to use when providing this service.
            path: The base dbus path to export this service to.
            adapter: The adapter that will provide this service or None to select the first adapter.
        """
        self._collection = ServiceCollection([self])
        await self._collection.register(bus, path, adapter)

    async def unregister(self) -> None:
        """Unregister this service.
        You may only use this if the service was registered using :class:`Service.register()`
        """
        if self._collection is None:
            return

        await self._collection.unregister()

    @dbus_property(PropertyAccess.READ, "UUID")
    def _get_uuid(self) -> "s":  # type: ignore
        return str(self._uuid)

    @dbus_property(PropertyAccess.READ, "Primary")
    def _get_primary(self) -> "b":  # type: ignore
        return self._primary

    @dbus_property(PropertyAccess.READ, "Includes")
    def _get_includes(self) -> "ao":  # type: ignore
        paths = []

        # Shouldn't be possible to call this before export.
        if self._path is None:
            raise ValueError()

        for service in self._includes:
            if not service._path is None:
                paths.append(service._path)

        paths.append(self._path)
        return paths


class ServiceCollection:
    """A collection of services that are registered with the bluez GATT manager as a group."""

    _MANAGER_INTERFACE = "org.bluez.GattManager1"

    def __init__(self, services: Optional[List[Service]] = None):
        """Create a service collection populated with the specified list of services.

        Args:
            services: The services to provide.
        """
        self._bus: Optional[MessageBus]
        self._path: Optional[str] = None
        self._adapter: Optional[Adapter] = None
        if services is None:
            services = []
        self._services = services

    def add_service(self, service: Service) -> None:
        """Add the specified service to this service collection.

        Args:
            service: The service to add.
        """
        if self.is_registered():
            raise ValueError(
                "You may not modify a registered service or service collection."
            )

        self._services.append(service)

    def remove_service(self, service: Service) -> None:
        """Remove the specified service from this collection.

        Args:
            service: The service to remove.
        """
        if self.is_registered():
            raise ValueError(
                "You may not modify a registered service or service collection."
            )

        self._services.remove(service)

    async def _get_manager_interface(self) -> ProxyInterface:
        if not self.is_registered():
            raise ValueError("Service is not registered to an adapter.")
        assert self._adapter is not None

        return self._adapter._proxy.get_interface(self._MANAGER_INTERFACE)

    def is_registered(self) -> bool:
        """Check if this service collection is registered with the bluez service manager.

        Returns:
            True if the service is registered. False otherwise.
        """
        return not self._path is None

    async def register(
        self,
        bus: MessageBus,
        path: str = "/com/spacecheese/bluez_peripheral",
        adapter: Optional[Adapter] = None,
    ) -> None:
        """Register this collection of services with the bluez service manager.
        Services and service collections that are registered may not be modified until they are unregistered.

        Args:
            bus: The bus to use for registration and management of this service.
            path: The base dbus path to use when registering the collection.
                Each service will be an automatically numbered child of this base.
            adapter: The adapter that should be used to deliver the collection of services.
        """
        if self.is_registered():
            return

        self._bus = bus
        self._path = path
        self._adapter = await Adapter.get_first(bus) if adapter is None else adapter

        manager = await self._get_manager_interface()

        # Number and export each service.
        i = 0
        for service in self._services:
            service._export(bus, f"{self._path}/service{i}")
            i += 1

        class _EmptyServiceInterface(ServiceInterface):
            pass

        # Export an empty interface on the root path so that bluez has an object manager to find.
        bus.export(self._path, _EmptyServiceInterface(self._path.replace("/", ".")[1:]))
        await manager.call_register_application(self._path, {})  # type: ignore

    async def unregister(self) -> None:
        """Unregister this service using the bluez service manager."""
        if not self.is_registered():
            return
        assert self._bus is not None
        assert self._path is not None

        manager = await self._get_manager_interface()

        await manager.call_unregister_application(self._path)  # type: ignore

        for service in self._services:
            service._unexport(self._bus)
        # Unexport the root object manager.
        self._bus.unexport(self._path)

        self._path = None
        self._adapter = None
        self._bus = None
