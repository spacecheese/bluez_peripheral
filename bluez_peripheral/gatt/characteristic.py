from dbus_next import DBusError
from dbus_next.constants import PropertyAccess
from dbus_next.service import ServiceInterface, method, dbus_property
from dbus_next.aio import MessageBus

import inspect
from uuid import UUID
from enum import Enum, Flag, auto
from typing import Callable, Optional, Union, Awaitable

from .descriptor import descriptor, DescriptorFlags
from ..uuid16 import UUID16
from ..util import *


class CharacteristicReadOptions:
    """Options supplied to characteristic read functions.
    Generally you can ignore these unless you have a long characteristic (eg > 48 bytes) or you have some specific authorization requirements.
    """

    def __init__(self):
        self.__init__({})

    def __init__(self, options):
        self._offset = int(getattr_variant(options, "offset", 0))
        self._mtu = int(getattr_variant(options, "mtu", 0))
        self._device = getattr_variant(options, "device", None)

    @property
    def offset(self) -> int:
        """A byte offset to read the characteristic from until the end."""
        return self._offset

    @property
    def mtu(self) -> Optional[int]:
        """The exchanged Maximum Transfer Unit of the connection with the remote device or 0."""
        return self._mtu

    @property
    def device(self):
        """The path of the remote device on the system dbus or None."""
        return self._device


class CharacteristicWriteType(Enum):
    """Possible value of the :class:`CharacteristicWriteOptions`.type field"""

    COMMAND = 0
    """Write without response
    """
    REQUEST = 1
    """Write with response
    """
    RELIABLE = 2
    """Reliable Write
    """


class CharacteristicWriteOptions:
    """Options supplied to characteristic write functions.
    Generally you can ignore these unless you have a long characteristic (eg > 48 bytes) or you have some specific authorization requirements.
    """

    def __init__(self):
        self.__init__({})

    def __init__(self, options):
        self._offset = int(getattr_variant(options, "offset", 0))
        type = getattr_variant(options, "type", None)
        if not type is None:
            type = CharacteristicWriteType[type.upper()]
        self._type = type
        self._mtu = int(getattr_variant(options, "mtu", 0))
        self._device = getattr_variant(options, "device", None)
        self._link = getattr_variant(options, "link", None)
        self._prepare_authorize = getattr_variant(options, "prepare-authorize", False)

    @property
    def offset(self):
        """A byte offset to use when writing to this characteristic."""
        return self._offset

    @property
    def type(self):
        """The type of write operation requested or None."""
        return self._type

    @property
    def mtu(self):
        """The exchanged Maximum Transfer Unit of the connection with the remote device or 0."""
        return self._mtu

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


class CharacteristicFlags(Flag):
    """Flags to use when specifying the read/ write routines that can be used when accessing the characteristic.
    These are converted to `bluez flags <https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/doc/gatt-api.txt>`_ some of which are not clearly documented.
    """

    INVALID = 0
    BROADCAST = auto()
    """Characteristic value may be broadcast as a part of advertisements.
    """
    READ = auto()
    """Characteristic value may be read.
    """
    WRITE_WITHOUT_RESPONSE = auto()
    """Characteristic value may be written to with no confirmation required.
    """
    WRITE = auto()
    """Characteristic value may be written to and confirmation is required.
    """
    NOTIFY = auto()
    """Characteristic may be subscribed to in order to provide notification when its value changes.
    Notification does not require acknowledgment.
    """
    INDICATE = auto()
    """Characteristic may be subscribed to in order to provide indication when its value changes.
    Indication requires acknowledgment.
    """
    AUTHENTICATED_SIGNED_WRITES = auto()
    """Characteristic requires secure bonding. Values are authenticated using a client signature.
    """
    EXTENDED_PROPERTIES = auto()
    """The Characteristic Extended Properties Descriptor exists and contains the values of any extended properties.
    Do not manually set this flag or attempt to define the Characteristic Extended Properties Descriptor. These are automatically 
    handled when a :class:`CharacteristicFlags.RELIABLE_WRITE` or :class:`CharacteristicFlags.WRITABLE_AUXILIARIES` flag is used.
    """
    RELIABLE_WRITE = auto()
    """The value to be written to the characteristic is verified by transmission back to the client before writing occurs.
    """
    WRITABLE_AUXILIARIES = auto()
    """The Characteristic User Description Descriptor exists and is writable by the client.
    """
    ENCRYPT_READ = auto()
    """The communicating devices have to be paired for the client to be able to read the characteristic.
    After pairing the devices share a bond and the communication is encrypted.
    """
    ENCRYPT_WRITE = auto()
    """The communicating devices have to be paired for the client to be able to write the characteristic.
    After pairing the devices share a bond and the communication is encrypted.
    """
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


class characteristic(ServiceInterface):
    """Create a new characteristic with a specified UUID and flags.

    Args:
        uuid: The UUID of the GATT characteristic. A list of standard ids is provided by the `Bluetooth SIG <https://btprodspecificationrefs.blob.core.windows.net/assigned-values/16-bit%20UUID%20Numbers%20Document.pdf>`_
        flags: Flags defining the possible read/ write behavior of the attribute.

    See Also:
        :ref:`quickstart`

        :ref:`characteristics_descriptors`
    """

    _INTERFACE = "org.bluez.GattCharacteristic1"

    def __init__(
        self,
        uuid: Union[str, bytes, UUID, UUID16, int],
        flags: CharacteristicFlags = CharacteristicFlags.READ,
    ):
        self.uuid = UUID16.parse_uuid(uuid)
        self.getter_func = None
        self.setter_func = None
        self.flags = flags

        self._notify = False
        self._service_path = None
        self._descriptors = []
        self._service = None
        self._value = bytearray()

        super().__init__(self._INTERFACE)

    def changed(self, new_value: bytes):
        """Call this function when the value of a notifiable or indicatable property changes to alert any subscribers.

        Args:
            new_value: The new value of the property to send to any subscribers.
        """
        if self._notify:
            self.emit_properties_changed({"Value": new_value}, [])

    # Decorators
    def setter(
        self,
        setter_func: Union[
            Callable[["Service", bytes, CharacteristicWriteOptions], None],
            Callable[["Service", bytes, CharacteristicWriteOptions], Awaitable[None]]],
    ) -> "characteristic":
        """A decorator for characteristic value setters."""
        self.setter_func = setter_func
        return self

    def __call__(
        self,
        getter_func: Union[
            Callable[["Service", CharacteristicReadOptions], bytes],
            Callable[["Service", CharacteristicReadOptions], Awaitable[bytes]]
        ] = None,
        setter_func: Union[
            Callable[["Service", bytes, CharacteristicWriteOptions], None],
            Callable[["Service", bytes, CharacteristicWriteOptions], Awaitable[None]]
        ] = None,
    ) -> "characteristic":
        """A decorator for characteristic value getters.

        Args:
            get: The getter function for this characteristic.
            set: The setter function for this characteristic.

        Returns:
            This characteristic.
        """
        self.getter_func = getter_func
        self.setter_func = setter_func
        return self

    def descriptor(
        self, uuid: Union[str, bytes, UUID, UUID16, int], flags: DescriptorFlags = DescriptorFlags.READ
    ) -> "descriptor":
        """Create a new descriptor with the specified UUID and Flags.

        Args:
            uuid: The UUID of the descriptor.
            flags: Any descriptor access flags to use.
        """
        # Use as a decorator for descriptors that need a getter.
        return descriptor(uuid, self, flags)

    def _is_registered(self):
        return not self._service_path is None

    def _set_service(self, service: "Service"):
        self._service = service

        for desc in self._descriptors:
            desc._set_service(service)

    def add_descriptor(self, desc: "descriptor"):
        """Associate the specified descriptor with this characteristic.

        Args:
            desc: The descriptor to associate.

        Raises:
            ValueError: Raised when the containing service is currently registered and thus cannot be modified.
        """
        if self._is_registered():
            raise ValueError(
                "Registered characteristics cannot be modified. Please unregister the containing application."
            )

        self._descriptors.append(desc)
        # Make sure that any descriptors have the correct service set at all times.
        desc._set_service(self._service)

    def remove_descriptor(self, desc: "descriptor"):
        """Remove the specified descriptor from this characteristic.

        Args:
            desc: The descriptor to remove.

        Raises:
            ValueError: Raised when the containing service is currently registered and thus cannot be modified.
        """
        if self._is_registered():
            raise ValueError(
                "Registered characteristics cannot be modified. Please unregister the containing application."
            )

        self._descriptors.remove(desc)
        # Clear the parent service from any old descriptors.
        desc._set_service(None)

    def _get_path(self) -> str:
        return self._service_path + "/char{:d}".format(self._num)

    def _export(self, bus: MessageBus, service_path: str, num: int):
        self._service_path = service_path
        self._num = num
        bus.export(self._get_path(), self)

        # Export and number each of the child descriptors.
        i = 0
        for desc in self._descriptors:
            desc._export(bus, self._get_path(), i)
            i += 1

    def _unexport(self, bus: MessageBus):
        # Unexport this and each of the child descriptors.
        bus.unexport(self._get_path(), self._INTERFACE)
        for desc in self._descriptors:
            desc._unexport(bus)

        self._service_path = None

    @method()
    async def ReadValue(self, options: "a{sv}") -> "ay":  # type: ignore
        try:
            res = []
            if inspect.iscoroutinefunction(self.getter_func):
                res = await self.getter_func(self._service, CharacteristicReadOptions(options))
            else:
                res = self.getter_func(self._service, CharacteristicReadOptions(options))

            self._value = bytearray(res)
            return bytes(self._value)
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
        opts = CharacteristicWriteOptions(options)
        try:
            if inspect.iscoroutinefunction(self.setter_func):
                await self.setter_func(self._service, data, opts)
            else:
                self.setter_func(self._service, data, opts)
        except DBusError as e:
            raise e
        except Exception as e:
            print(
                "Unrecognised exception type when writing descriptor value: \n" + str(e)
            )
            raise e
        self._value[opts.offset : opts.offset + len(data)] = bytearray(data)

    @method()
    def StartNotify(self):
        if not self.flags | CharacteristicFlags.NOTIFY:
            raise DBusError(
                "org.bluez.Error.NotSupported",
                "The characteristic does not support notification.",
            )

        self._notify = True

    @method()
    def StopNotify(self):
        if not self.flags | CharacteristicFlags.NOTIFY:
            raise DBusError(
                "org.bluez.Error.NotSupported",
                "The characteristic does not support notification.",
            )

        self._notify = False

    @dbus_property(PropertyAccess.READ)
    def UUID(self) -> "s":  # type: ignore
        return str(self.uuid)

    @dbus_property(PropertyAccess.READ)
    def Service(self) -> "o":  # type: ignore
        return self._service_path

    @dbus_property(PropertyAccess.READ)
    def Flags(self) -> "as":  # type: ignore
        # Clear the extended properties flag (bluez doesn't seem to like this flag even though its in the docs).
        self.flags &= ~CharacteristicFlags.EXTENDED_PROPERTIES

        # Return a list of set string flag names.
        return [
            snake_to_kebab(flag.name)
            for flag in CharacteristicFlags
            if self.flags & flag
        ]

    @dbus_property(PropertyAccess.READ)
    def Value(self) -> "ay":  # type: ignore
        return bytes(self._value)
