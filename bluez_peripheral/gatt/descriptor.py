from dbus_next import DBusError
from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface, method, dbus_property
from dbus_next.constants import PropertyAccess

from enum import Flag, auto
from typing import Union, Callable
from ..uuid import BTUUID as UUID
from ..util import *


class DescriptorReadOptions:
    """Options supplied to descriptor read functions.
    Generally you can ignore these unless you have a long descriptor (eg > 48 bytes) or you have some specific authorization requirements.
    """

    def __init__(self, options):
        self._offset = getattr_variant(options, "offset", 0)
        self._link = getattr_variant(options, "link", None)
        self._device = getattr_variant(options, "device", None)

    @property
    def offset(self):
        """A byte offset to use when writing to this descriptor."""
        return self._offset

    @property
    def link(self):
        """The link type."""
        return self._link

    @property
    def device(self):
        """The path of the remote device on the system dbus or None."""
        return self._device


class DescriptorWriteOptions:
    """Options supplied to descriptor write functions.
    Generally you can ignore these unless you have a long descriptor (eg > 48 bytes) or you have some specific authorization requirements.
    """

    def __init__(self, options):
        self._offset = getattr_variant(options, "offset", 0)
        self._device = getattr_variant(options, "device", None)
        self._link = getattr_variant(options, "link", None)
        self._prepare_authorize = getattr_variant(options, "prepare-authorize", False)

    @property
    def offset(self):
        """A byte offset to use when writing to this descriptor."""
        return self._offset

    @property
    def device(self):
        """The path of the remote device on the system dbus or None."""
        return self._device

    @property
    def link(self):
        """The link type."""
        return self._link

    @property
    def prepare_authorize(self):
        """True if prepare authorization request. False otherwise."""
        return self._prepare_authorize


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

    See Also:
        :ref:`quickstart`

        :ref:`characteristics_descriptors`
    """

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
        self,
        setter_func: Callable[[bytes, DescriptorWriteOptions], None],
    ) -> "descriptor":
        """A decorator for descriptor value setters."""
        self.setter_func = setter_func
        return setter_func

    def __call__(
        self,
        getter_func: Callable[["Service", DescriptorReadOptions], bytes] = None,
        setter_func: Callable[["Service", bytes, DescriptorWriteOptions], None] = None,
    ) -> "descriptor":
        """A decorator for characteristic value getters.

        Args:
            getter_func (Callable[[Service, DescriptorReadOptions], bytes], optional): The getter function for this descriptor.
            setter_func (Callable[[Service, bytes, DescriptorWriteOptions], None], optional): The setter function for this descriptor. Defaults to None.

        Returns:
            descriptor: This descriptor
        """
        self.getter_func = getter_func
        self.setter_func = setter_func
        return self

    def _set_service(self, service):
        self._service = service

    # DBus
    def _get_path(self) -> str:
        return self._characteristic_path + "/desc{:d}".format(self._num)

    def _export(self, bus: MessageBus, characteristic_path: str, num: int):
        self._characteristic_path = characteristic_path
        self._num = num
        bus.export(self._get_path(), self)

    def _unexport(self, bus: MessageBus):
        bus.unexport(self._get_path(), self._INTERFACE)
        self._characteristic_path = None

    @method()
    def ReadValue(self, options: "a{sv}") -> "ay":  # type: ignore
        try:
            return self.getter_func(self._service, DescriptorReadOptions(options))
        except DBusError as e:
            # Allow DBusErrors to bubble up normally.
            raise e
        except Exception as e:
            # Report any other exception types.
            print(
                "Unrecognised exception type when reading descriptor value: \n" + str(e)
            )
            raise e

    @method()
    def WriteValue(self, data: "ay", options: "a{sv}"):  # type: ignore
        try:
            self.setter_func(self._service, data, DescriptorWriteOptions(options))
        except DBusError as e:
            raise e
        except Exception as e:
            print(
                "Unrecognised exception type when writing descriptor value: \n" + str(e)
            )
            raise e

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
            snake_to_kebab(flag.name) for flag in DescriptorFlags if self.flags & flag
        ]
