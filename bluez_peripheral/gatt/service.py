from dbus_next.aio.proxy_object import ProxyObject
from dbus_next.constants import PropertyAccess
from dbus_next.service import ServiceInterface, dbus_property
from dbus_next.aio import MessageBus

from .characteristic import characteristic
from ..uuid import BTUUID as UUID
from ..util import *

from typing import Union
import inspect

# See https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/doc/gatt-api.txt
class Service(ServiceInterface):
    """Create a bluetooth service with the specified uuid.

    Args:
        uuid (Union[UUID, str]): The UUID of this service. A full list of recognised values is provided by the `Bluetooth SIG <https://btprodspecificationrefs.blob.core.windows.net/assigned-values/16-bit%20UUID%20Numbers%20Document.pdf>`_
        primary (bool, optional): True if this service is a primary service (instead of a secondary service). False otherwise. Defaults to True.
        includes (Collection[Service], optional): Any services to include in this service.
            Services must be registered at the time Includes is read to be included.
    """

    _INTERFACE = "org.bluez.GattService1"

    def _populate(self):
        # Only interested in characteristic members.
        members = inspect.getmembers(type(self), lambda m: type(m) is characteristic)

        for _, member in members:
            member._set_service(self)

            # Some characteristics will occur multiple times due to different decorators.
            if not member in self._characteristics:
                self.add_characteristic(member)

    def __init__(
        self,
        uuid: Union[UUID, str],
        primary: bool = True,
        includes: Collection["Service"] = [],
    ):
        # Make sure uuid is a uuid16.
        self._uuid = uuid if type(uuid) is UUID else UUID.from_uuid16(uuid)
        self._primary = primary
        self._characteristics = []
        self._path = None
        self._includes = includes
        self._populate()

        super().__init__(self._INTERFACE)

    def is_registered(self) -> bool:
        """Check if this service is registered with the bluez service manager.

        Returns:
            bool: True if the service is registered. False otherwise.
        """
        return not self._path is None

    def add_characteristic(self, char: characteristic):
        """Add the specified characteristic to this service declaration.

        Args:
            char (characteristic): The characteristic to add.

        Raises:
            ValueError: Raised when the service is registered with the bluez service manager and thus cannot be modified.
        """
        if self.is_registered():
            raise ValueError(
                "Registered services cannot be modified. Please unregister the containing application."
            )

        self._characteristics.append(char)

    def remove_characteristic(self, char: characteristic):
        """Remove the specified characteristic from this service declaration.

        Args:
            char (characteristic): The characteristic to remove.

        Raises:
            ValueError: Raised if the service is registered with the bluez service manager and thus cannot be modified.
        """
        if self.is_registered():
            raise ValueError(
                "Registered services cannot be modified. Please unregister the containing application."
            )

        self._characteristics.remove(char)

    def _export(self, bus: MessageBus, path: str):
        self._path = path

        # Export this and number each child characteristic.
        bus.export(path, self)
        i = 0
        for char in self._characteristics:
            char._export(bus, path, i)
            i += 1

    def _unexport(self, bus: MessageBus):
        # Unexport this and every child characteristic.
        bus.unexport(self._path, self._INTERFACE)
        for char in self._characteristics:
            char._unexport(bus)

        self._path = None

    async def register(
        self,
        bus: MessageBus,
        path: str = "/com/spacecheese/bluez_peripheral",
        adapter: Adapter = None,
    ):
        """Register this service as a standalone service.
        Using this multiple times will cause path conflicts.

        Args:
            bus (MessageBus): The bus to use when providing this service.
            path (str, optional): The base dbus path to export this service to.
            adapter (Adapter, optional): The adapter that will provide this service or None to select the first adapter.
        """
        self._collection = ServiceCollection([self])
        await self._collection.register(bus, path, adapter)

    async def unregister(self):
        """Unregister this service.
        You may only use this if the service was registered using :class:`Service.register()`
        """
        collection = getattr(self, "_collection", None)

        if collection is None:
            return

        await collection.unregister()

    @dbus_property(PropertyAccess.READ)
    def UUID(self) -> "s":  # type: ignore
        return str(self._uuid)

    @dbus_property(PropertyAccess.READ)
    def Primary(self) -> "b":  # type: ignore
        return self._primary

    @dbus_property(PropertyAccess.READ)
    def Includes(self) -> "ao":  # type: ignore
        paths = []

        for service in self._includes:
            if not service._path is None:
                paths.append(service._path)

        paths.append(self._path)
        return paths


class ServiceCollection:
    """A collection of services that are registered with the bluez GATT manager as a group."""

    _MANAGER_INTERFACE = "org.bluez.GattManager1"

    def _init(self, services: Collection[Service]):
        self._path = None
        self._adapter = None
        self._services = services

    def __init__(self, services: Collection[Service] = []):
        """Create a service collection populated with the specified list of services.

        Args:
            services (Collection[Service]): The services to provide.
        """
        self._path = None
        self._adapter = None
        self._services = services

    def add_service(self, service: Service):
        """Add the specified service to this service collection.

        Args:
            service (Service): The service to add.
        """
        if self.is_registered():
            raise ValueError(
                "You may not modify a registered service or service collection."
            )

        self._services.append(service)

    def remove_service(self, service: Service):
        """Remove the specified service from this collection.

        Args:
            service (Service): The service to remove.
        """
        if self.is_registered():
            raise ValueError(
                "You may not modify a registered service or service collection."
            )

        self._services.remove(service)

    async def _get_manager_interface(self):
        return self._adapter._proxy.get_interface(self._MANAGER_INTERFACE)

    def is_registered(self) -> bool:
        """Check if this service collection is registered with the bluez service manager.

        Returns:
            bool: True if the service is registered. False otherwise.
        """
        return not self._path is None

    async def register(
        self,
        bus: MessageBus,
        path: str = "/com/spacecheese/bluez_peripheral",
        adapter: Adapter = None,
    ):
        """Register this collection of services with the bluez service manager.
        Services and service collections that are registered may not be modified until they are unregistered.

        Args:
            bus (MessageBus): The bus to use for registration and management of this service.
            path (str, optional): The base dbus path to use when registering the collection.
                Each service will be an automatically numbered child of this base.
            adapter (ProxyObject, optional): The adapter that should be used to deliver the collection of services.
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
            service._export(bus, self._path + "/service{:d}".format(i))
            i += 1

        # Export an empty interface on the root path so that bluez has an object manager to find.
        bus.export(self._path, ServiceInterface(self._path.replace("/", ".")[1:]))
        await manager.call_register_application(self._path, {})

    async def unregister(self):
        """Unregister this service using the bluez service manager."""
        if not self.is_registered():
            return

        manager = await self._get_manager_interface()

        await manager.call_unregister_application(self._path)

        for service in self._services:
            service._unexport(self._bus)
        # Unexport the root object manager.
        self._bus.unexport(self._path)

        self._path = None
        self._adapter = None
        self._bus = None
