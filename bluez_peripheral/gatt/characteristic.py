from dbus_next import DBusError
from dbus_next.constants import PropertyAccess
from dbus_next.service import ServiceInterface, method, dbus_property
from dbus_next.aio import MessageBus

from enum import Flag, auto
from typing import Callable, Union

from .descriptor import descriptor, DescriptorFlags
from ..uuid import BTUUID
from ..util import *


class CharacteristicReadOptions:
    """Options supplied to characteristic read functions.
    Generally you can ignore these unless you have a long characteristic (eg > 100 bytes) or you have some specific authorization requirements.
    Documentation on these feilds can be found in the `bluez docs <https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/doc/gatt-api.txt>`_.
    """

    def __init__(self):
        self.__init__({})

    def __init__(self, options):
        self.offset = _getattr_variant(options, "offset", 0)
        self.mtu = _getattr_variant(options, "mtu", None)
        self.device = _getattr_variant(options, "device", None)


class CharacteristicWriteOptions:
    """Options supplied to characteristic write functions.
    Generally you can ignore these unless you have a long characteristic (eg > 100 bytes) or you have some specific authorization requirements.
    Documentation on these feilds can be found in the `bluez docs <https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/doc/gatt-api.txt>`_.
    """

    def __init__(self):
        self.__init__({})

    def __init__(self, options):
        self.offset = _getattr_variant(options, "offset", 0)
        self.type = _getattr_variant(options, "type", None)
        self.mtu = _getattr_variant(options, "mtu", None)
        self.device = _getattr_variant(options, "device", None)
        self.link = _getattr_variant(options, "link", None)
        self.prepare_authorize = _getattr_variant(options, "prepare-authorize", False)


class CharacteristicFlags(Flag):
    """Flags to use when specifying the read/ write routines that can be used when accessing the characteristic.
    These are converted to `bluez flags <https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/doc/gatt-api.txt>`_ some of which are not clearly documented.
    """

    INVALID = 0
    BROADCAST = auto()
    """Characteristic value may be broadcast as a part of advertisments.
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
    Notification does not require acknowledgement.
    """
    INDICATE = auto()
    """Characteristic may be subscribed to in order to provide indication when its value changes.
    Indication requires acknowledgement.
    """
    AUTHENTICATED_SIGNED_WRITES = auto()
    """Characteristic requires bonding. Values are authenticated using a client signature.
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
    """"""
    ENCRPYT_WRITE = auto()
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


class characteristic(ServiceInterface):
    """Create a new characteristic with a specified UUID and flags.

    Args:
        uuid (Union[BTUUID, str]): The UUID of the GATT characteristic. A list of standard ids is provided by the `Bluetooth SIG <https://btprodspecificationrefs.blob.core.windows.net/assigned-values/16-bit%20UUID%20Numbers%20Document.pdf>`_
        flags (CharacteristicFlags, optional): Flags defining the possible read/ write behaviour of the attribute.
    """

    # TODO: Add reference to detailed characteristic documentation.

    _INTERFACE = "org.bluez.GattCharacteristic1"

    def __init__(
        self,
        uuid: Union[BTUUID, str],
        flags: CharacteristicFlags = CharacteristicFlags.READ,
    ):
        if uuid is str:
            uuid = BTUUID.from_uuid16(uuid)
        self.uuid = uuid
        self.getter_func = None
        self.setter_func = None
        self.flags = flags

        self._notify = False
        self._service_path = None
        self._descriptors = []
        self._service = None
        self._value = bytes()

        super().__init__(self._INTERFACE)

    def changed(self, new_value: bytes):
        """Call this function when the value of a notifiable or indicatable property changes to alert any subscribers.

        Args:
            new_value (bytes): The new value of the property to send to any subscribers.
        """
        if self._notify:
            self.emit_properties_changed({"Value": new_value})

    # Decorators
    def setter(
        self,
        setter_func: Callable[["Service", bytes, CharacteristicWriteOptions], None],
    ) -> "characteristic":
        """A decorator for characteristic value setters. You must define a getter using :class:`characteristic.__init__()()` first."""
        self.setter_func = setter_func
        return self

    def __call__(
        self,
        func: Callable[["Service", CharacteristicReadOptions], bytes],
    ):
        """A decorator for characteristic value getters. You should use this by chaining with :class:`characteristic.__init__()`."""
        self.getter_func = func
        return self

    def descriptor(
        self, uuid: Union[BTUUID, str], flags: DescriptorFlags = DescriptorFlags.READ
    ) -> "descriptor":
        """Create a new descriptor with the specified UUID and Flags.

        Args:
            uuid (Union[BTUUID, str]): The UUID of the descriptor.
            flags (DescriptorFlags, optional): Any descriptor access flags to use.
        """
        # Use as a decorator for descriptors that need a getter.
        return descriptor(uuid, self, flags)

    def _is_registered(self):
        return not self._service_path is None

    def _set_service(self, service: "Service"):
        self._service = service

        for desc in self._descriptors:
            desc._set_service(service)

    def add_descriptor(self, desc: descriptor):
        """Associate the specified descriptor with this characteristic.

        Args:
            desc (descriptor): The descriptor to associate.

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

    def remove_descriptor(self, desc: descriptor):
        """Remove the specified descriptor from this characteristic.

        Args:
            desc (descriptor): The descriptor to remove.

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
    def ReadValue(self, options: "a{sv}") -> "ay":  # type: ignore
        self._value = self.getter_func(
            self._service, CharacteristicReadOptions(options)
        )
        return self._value

    @method()
    def WriteValue(self, data: "ay", options: "a{sv}"):  # type: ignore
        opts = CharacteristicWriteOptions(options)
        self.setter_func(self._service, data, opts)
        self._value[opts.offset : opts.offset + len(data)] = data

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
        if (
            self.flags | CharacteristicFlags.RELIABLE_WRITE
            or self.flags | CharacteristicFlags.WRITABLE_AUXILIARIES
        ):
            # Add the extended properties flag if required.
            self.flags |= CharacteristicFlags.EXTENDED_PROPERTIES
        else:
            # Clear the extended properties flag if it is otherwise set.
            self.flags &= ~CharacteristicFlags.EXTENDED_PROPERTIES

        # Return a list of set string flag names.
        return [
            _snake_to_kebab(flag.name)
            for flag in CharacteristicFlags
            if self.flags & flag
        ]

    @dbus_property(PropertyAccess.READ)
    def Value(self) -> "ay":  # type: ignore
        return self._value
