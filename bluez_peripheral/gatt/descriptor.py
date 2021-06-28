from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface, method, dbus_property
from dbus_next.constants import PropertyAccess

from enum import Flag, auto
from typing import Union, Callable
from ..uuid import BTUUID as UUID
from ..util import *


class DescriptorReadOptions:
    """Options supplied to descriptor read functions.
    Generally you can ignore these unless you have a long descriptor (eg > 100 bytes) or you have some specific authorization requirements.
    Documentation on these feilds can be found in the `bluez docs <https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/doc/gatt-api.txt>`_.
    """

    def __init__(self, options):
        self.offset = _getattr_variant(options, "offset", 0)
        self.link = _getattr_variant(options, "link", None)
        self.device = _getattr_variant(options, "device", None)


class DescriptorWriteOptions:
    """Options supplied to descriptor write functions.
    Generally you can ignore these unless you have a long characteristic (eg > 100 bytes) or you have some specific authorization requirements.
    Documentation on these feilds can be found in the `bluez docs <https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/doc/gatt-api.txt>`_.
    """

    def __init__(self, options):
        self.offset = _getattr_variant(options, "offset", 0)
        self.device = _getattr_variant(options, "device", None)
        self.link = _getattr_variant(options, "link", None)
        self.prepare_authorize = _getattr_variant(options, "prepare-authorize", False)


class DescriptorFlags(Flag):
    """Flags to use when specifying the read/ write routines that can be used when accessing the descriptor.
    These are converted to `bluez flags <https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/doc/gatt-api.txt>`_ some of which are not clearly documented.
    """

    INVALID = 0
    READ = auto()
    """Descriptor may be read.
    """
    WRITE = auto()
    """Descriptor may be written to.
    """
    ENCRYPT_READ = auto()
    """"""
    ENCRYPT_WRITE = auto()
    """"""
    ENCRYPT_AUTHENTICATED_READ = auto()
    """"""
    ENCRYPT_AUTHENTICATED_WRITE = auto()
    """"""
    SECURE_READ = auto()
    """"""
    SECURE_WRITE = auto()
    """"""
    AUTHORIZE = auto()
    """"""


# Decorator for descriptor getters/ setters.
class descriptor(ServiceInterface):
    """Create a new descriptor with a specified UUID and flags associated with the specified parent characteristic.

    Args:
        uuid (Union[UUID, str]): The UUID of this GATT descriptor. A list of standard ids is provided by the `Bluetooth SIG <https://btprodspecificationrefs.blob.core.windows.net/assigned-values/16-bit%20UUID%20Numbers%20Document.pdf>`_
        characteristic (characteristic): The parent characteristic to associate this descriptor with.
        flags (DescriptorFlags, optional): Flags defining the possible read/ write behaviour of the attribute.
    """

    # TODO: Add reference to detailed characteristic documentation.

    _INTERFACE = "org.bluez.GattDescriptor1"

    def __init__(
        self,
        uuid: Union[UUID, str],
        characteristic: "characteristic",  # type: ignore
        flags: DescriptorFlags = DescriptorFlags.READ,
    ):
        if uuid is str:
            uuid = UUID.from_uuid16(uuid)
        self.uuid = uuid
        self.getter_func = None
        self.setter_func = None
        self.characteristic = characteristic
        self.flags = flags
        self._service = None

        self._characteristic_path = None
        super().__init__(self._INTERFACE)

        characteristic.add_descriptor(self)

    # Decorators
    def setter(
        self, setter_func: Callable[[bytes, DescriptorWriteOptions], None]
    ) -> "descriptor":
        """A decorator for descriptor value setters. You must define a getter first."""
        self.setter_func = setter_func
        return setter_func

    def __call__(
        self,
        func: Callable[[DescriptorReadOptions], bytes],
    ):
        """A decorator for descriptor value getters."""
        self.getter_func = func
        return self

    def _set_service(self, service):
        self._service = service

    # DBus
    def _get_path(self) -> str:
        return self._characteristic_path + "/descriptor{:d}".format(self._num)

    def _export(self, bus: MessageBus, characteristic_path: str, num: int):
        self._characteristic_path = characteristic_path
        self._num = num
        bus.export(self._get_path(), self)

    def _unexport(self, bus: MessageBus):
        bus.unexport(self._get_path(), self._INTERFACE)
        self._characteristic_path = None

    @method()
    def ReadValue(self, options: "a{sv}") -> "ay":  # type: ignore
        return self.getter_func(self._service, DescriptorReadOptions(options))

    @method()
    def WriteValue(self, data: "ay", options: "a{sv}"):  # type: ignore
        self.setter_func(self._service, data, DescriptorWriteOptions(options))

    @dbus_property(PropertyAccess.READ)
    def UUID(self) -> "s":  # type: ignore
        return str(self.uuid)

    @dbus_property(PropertyAccess.READ)
    def Characteristic(self) -> "o":  # type: ignore
        return self._characteristic_path

    @dbus_property(PropertyAccess.READ)
    def Flags(self) -> "as":  # type: ignore
        # Return a list of string flag names.
        return [
            _snake_to_kebab(flag.name) for flag in DescriptorFlags if self.flags & flag
        ]
