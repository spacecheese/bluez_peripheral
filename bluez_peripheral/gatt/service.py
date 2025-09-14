import inspect
from typing import List, Optional, Collection

from dbus_fast.constants import PropertyAccess
from dbus_fast.service import dbus_property
from dbus_fast.aio.message_bus import MessageBus

from .base import HierarchicalServiceInterface
from .characteristic import characteristic
from ..uuid16 import UUID16, UUIDCompatible
from ..adapter import Adapter


# See https://github.com/bluez/bluez/blob/master/doc/org.bluez.GattService.rst
class Service(HierarchicalServiceInterface):
    """Create a bluetooth service with the specified uuid.

    Args:
        uuid: The UUID of this service. A full list of recognized values is provided by the `Bluetooth SIG Assigned Numbers <https://www.bluetooth.com/specifications/assigned-numbers/>`_
        primary: True if this service is a primary service (instead of a secondary service). False otherwise. Defaults to True.
        includes: Any services to include in this service.
            Services must be registered at the time Includes is read to be included.
    """

    BUS_INTERFACE = "org.bluez.GattService1"
    BUS_PREFIX = "service"

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
        uuid: UUIDCompatible,
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

        for service in self._includes:
            if not service.export_path is None:
                paths.append(service.export_path)

        if not self.export_path is None:
            paths.append(self.export_path)
        return paths


class ServiceCollection(HierarchicalServiceInterface):
    """A collection of services that are registered with the bluez GATT manager as a group."""

    BUS_INTERFACE = "org.spacecheese.ServiceCollection1"

    def __init__(self, services: Optional[List[Service]] = None):
        """Create a service collection populated with the specified list of services.

        Args:
            services: The services to provide.
        """
        super().__init__()
        if services is not None:
            for s in services:
                self.add_child(s)

        self._path: Optional[str] = None
        self._bus: Optional[MessageBus] = None
        self._adapter: Optional[Adapter] = None

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
        self._path = path
        self._bus = bus
        self._adapter = await Adapter.get_first(bus) if adapter is None else adapter

        self.export(self._bus, path=path)

        manager = self._adapter.get_gatt_manager()
        await manager.call_register_application(self._path, {})  # type: ignore

    async def unregister(self) -> None:
        """Unregister this service using the bluez service manager."""
        if not self.is_exported:
            return
        assert self._path is not None
        assert self._bus is not None
        assert self._adapter is not None

        manager = self._adapter.get_gatt_manager()

        await manager.call_unregister_application(self._path)  # type: ignore

        self.unexport(self._bus)

        self._path = None
        self._adapter = None
        self._bus = None
