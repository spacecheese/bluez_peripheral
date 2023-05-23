from dbus_next import DBusError, Variant
from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface, method, dbus_property
from dbus_next.constants import PropertyAccess

import inspect
from uuid import UUID
from enum import Flag, auto
from typing import Callable, Union, Awaitable, Optional, Dict, TYPE_CHECKING, cast

if TYPE_CHECKING:
    from .service import Service

from ..uuid16 import UUID16
from ..util import _snake_to_kebab, _getattr_variant
from ..error import FailedError


class DescriptorReadOptions:
    """Options supplied to descriptor read functions.
    Generally you can ignore these unless you have a long descriptor (eg > 48 bytes) or you have some specific authorization requirements.
    """

    def __init__(self, options: Optional[Dict[str, Variant]] = None):
        if options is None:
            return

        self._offset = _getattr_variant(options, "offset", 0)
        self._link = _getattr_variant(options, "link", None)
        self._device = _getattr_variant(options, "device", None)

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

    def __init__(self, options: Optional[Dict[str, Variant]] = None):
        if options is None:
            return

        self._offset = _getattr_variant(options, "offset", 0)
        self._device = _getattr_variant(options, "device", None)
        self._link = _getattr_variant(options, "link", None)
        self._prepare_authorize = _getattr_variant(options, "prepare-authorize", False)

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


GetterType = Union[
    Callable[["Service", DescriptorReadOptions], bytes],
    Callable[["Service", DescriptorReadOptions], Awaitable[bytes]],
]
SetterType = Union[
    Callable[["Service", bytes, DescriptorWriteOptions], None],
    Callable[["Service", bytes, DescriptorWriteOptions], Awaitable[None]],
]


# Decorator for descriptor getters/ setters.
class descriptor(ServiceInterface):
    """Create a new descriptor with a specified UUID and flags associated with the specified parent characteristic.

    Args:
        uuid: The UUID of this GATT descriptor. A list of standard ids is provided by the `Bluetooth SIG Assigned Numbers <https://www.bluetooth.com/specifications/assigned-numbers/>`_
        characteristic: The parent characteristic to associate this descriptor with.
        flags: Flags defining the possible read/ write behavior of the attribute.

    See Also:
        :ref:`services`
    """

    _INTERFACE = "org.bluez.GattDescriptor1"

    def __init__(
        self,
        uuid: Union[str, bytes, UUID, UUID16, int],
        characteristic: "characteristic",  # type: ignore
        flags: DescriptorFlags = DescriptorFlags.READ,
    ):
        self.uuid = UUID16.parse_uuid(uuid)
        self.getter_func: Optional[GetterType] = None
        self.setter_func: Optional[SetterType] = None
        self.characteristic = characteristic
        self.flags = flags
        self._service = None

        self._characteristic_path: Optional[str] = None
        super().__init__(self._INTERFACE)

        characteristic.add_descriptor(self)

    # Decorators
    def setter(
        self,
        setter_func: SetterType,
    ) -> "descriptor":
        """A decorator for descriptor value setters."""
        self.setter_func = setter_func
        return self

    def __call__(
        self,
        getter_func: Optional[GetterType] = None,
        setter_func: Optional[SetterType] = None,
    ) -> "descriptor":
        """A decorator for characteristic value getters.

        Args:
            getter_func: The getter function for this descriptor.
            setter_func: The setter function for this descriptor.

        Returns:
            This descriptor
        """
        self.getter_func = getter_func
        self.setter_func = setter_func
        return self

    def _set_service(self, service):
        self._service = service

    # DBus
    def _get_path(self) -> str:
        if self._characteristic_path is None:
            raise ValueError()

        return self._characteristic_path + "/desc{:d}".format(self._num)

    def _export(self, bus: MessageBus, characteristic_path: str, num: int):
        self._characteristic_path = characteristic_path
        self._num = num
        bus.export(self._get_path(), self)

    def _unexport(self, bus: MessageBus):
        if self._characteristic_path is None:
            return

        bus.unexport(self._get_path(), self._INTERFACE)
        self._characteristic_path = None

    @method()
    async def ReadValue(self, options: "a{sv}") -> "ay":  # type: ignore
        if self.getter_func is None:
            raise FailedError("No getter implemented")

        if self._service is None:
            raise ValueError()

        try:
            if inspect.iscoroutinefunction(self.getter_func):
                return await self.getter_func(
                    self._service, DescriptorReadOptions(options)
                )
            else:
                return cast(
                    bytes,
                    self.getter_func(self._service, DescriptorReadOptions(options)),
                )
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
    async def WriteValue(self, data: "ay", options: "a{sv}"):  # type: ignore
        if self.setter_func is None:
            raise FailedError("No setter implemented")

        if self._service is None:
            raise ValueError()

        try:
            if inspect.iscoroutinefunction(self.setter_func):
                await self.setter_func(
                    self._service, data, DescriptorWriteOptions(options)
                )
            else:
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
            _snake_to_kebab(flag.name)
            for flag in DescriptorFlags
            if self.flags & flag and flag.name is not None
        ]
