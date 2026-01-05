import inspect
from typing import List, Optional, Collection

from dbus_fast.constants import PropertyAccess
from dbus_fast.service import dbus_property
from dbus_fast.aio.message_bus import MessageBus

from .base import HierarchicalServiceInterface
from .characteristic import characteristic
from ..uuid16 import UUID16, UUIDLike
from ..adapter import Adapter


class Service(HierarchicalServiceInterface):
    """Create a bluetooth service with the specified uuid.
    Represents an `org.bluez.GattService1 <https://raw.githubusercontent.com/bluez/bluez/refs/heads/master/doc/org.bluez.GattService.rst>`_ instance.

    Args:
        uuid: The UUID of this service. A full list of recognized values is provided by the `Bluetooth SIG Assigned Numbers <https://www.bluetooth.com/specifications/assigned-numbers/>`_
        primary: True if this service is a primary service (instead of a secondary service). False otherwise. Defaults to True.
        includes: Any services to include in this service.
            Services must be registered at the time Includes is read to be included.
    """

    _INTERFACE = "org.bluez.GattService1"
    _BUS_PREFIX = "service"

    def _populate(self) -> None:
        # Only interested in characteristic members.
        members = inspect.getmembers(
            type(self), lambda m: isinstance(m, characteristic)
        )

        for _, member in members:
            # Some characteristics will occur multiple times due to different decorators.
            if not member in self._children:
                self.add_child(member)

    def __init__(
        self,
        uuid: UUIDLike,
        primary: bool = True,
        includes: Optional[Collection["Service"]] = None,
    ):
        super().__init__()

        self._uuid = UUID16.parse_uuid(uuid)
        self._primary = primary
        self._path: Optional[str] = None
        if includes is None:
            includes = []
        self._includes = includes
        self._populate()
        self._collection: Optional[ServiceCollection] = None

    def add_child(self, child: HierarchicalServiceInterface) -> None:
        if not isinstance(child, characteristic):
            raise ValueError("service child must be characteristic")
        child.service = self
        super().add_child(child)

    def add_characteristic(self, char: characteristic) -> None:
        """
        Associated a characteristic with this service.
        """
        self.add_child(char)

    async def register(
        self,
        bus: MessageBus,
        *,
        path: Optional[str] = None,
        adapter: Optional[Adapter] = None,
    ) -> None:
        """Register this service as a standalone service.
        Using this multiple times will cause path conflicts.

        Args:
            bus: The bus to use when providing this service.
            path: The base dbus path to export this service to.
            adapter: The adapter that will provide this service or None to select the first adapter.
        """
        collection = ServiceCollection([self])
        await collection.register(bus, path=path, adapter=adapter)
        self._collection = collection

    async def unregister(self) -> None:
        """Unregister this service.
        You may only use this if the service was registered using :class:`Service.register()`
        """
        if self._collection is None:
            return

        await self._collection.unregister()
        self._collection = None

    @dbus_property(PropertyAccess.READ, "UUID")
    def _get_uuid(self) -> "s":  # type: ignore
        return str(self._uuid)

    @dbus_property(PropertyAccess.READ, "Primary")
    def _get_primary(self) -> "b":  # type: ignore
        return self._primary

    @dbus_property(PropertyAccess.READ, "Includes")
    def _get_includes(self) -> "ao":  # type: ignore
        paths = []

        for service in self._includes:
            if not service.export_path is None:
                paths.append(service.export_path)

        if not self.export_path is None:
            paths.append(self.export_path)
        return paths


class ServiceCollection(HierarchicalServiceInterface):
    """A collection of services that are registered with the bluez GATT manager as a group."""

    _INTERFACE = "org.spacecheese.ServiceCollection1"
    _DEFAULT_PATH_PREFIX = "/com/spacecheese/bluez_peripheral/service_collection"

    def __init__(self, services: Optional[List[Service]] = None):
        """Create a service collection populated with the specified list of services.

        Args:
            services: The services to provide.
        """
        super().__init__()
        if services is not None:
            for s in services:
                self.add_child(s)

        self._bus: Optional[MessageBus] = None
        self._adapter: Optional[Adapter] = None

    async def register(
        self,
        bus: MessageBus,
        *,
        path: Optional[str] = None,
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
        self._adapter = await Adapter.get_first(bus) if adapter is None else adapter

        self.export(bus, path=path)

        manager = self._adapter.get_gatt_manager()
        await manager.call_register_application(self.export_path, {})  # type: ignore

        self._bus = bus

    async def unregister(self) -> None:
        """Unregister this service using the bluez service manager."""
        if not self.is_exported:
            return
        assert self._bus is not None
        assert self._adapter is not None

        manager = self._adapter.get_gatt_manager()
        await manager.call_unregister_application(self.export_path)  # type: ignore

        self.unexport()

        self._adapter = None
        self._bus = None

    def export(
        self, bus: MessageBus, *, num: Optional[int] = None, path: Optional[str] = None
    ) -> None:
        """
        Export this ServiceCollection on the specified message bus.
        """
        if path is None:
            path = self._get_unique_export_path()

        super().export(bus, num=num, path=path)
