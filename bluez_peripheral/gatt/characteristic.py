from enum import Enum, Flag, auto
from typing import Optional, cast, Dict, TYPE_CHECKING

from dbus_fast import Variant
from dbus_fast.constants import PropertyAccess
from dbus_fast.service import method, dbus_property

from .base import HierarchicalServiceInterface, ServiceAttribute
from ..uuid16 import UUIDLike, UUID16
from ..util import _snake_to_kebab, _getattr_variant
from ..error import NotSupportedError
from .descriptor import DescriptorFlags, descriptor

if TYPE_CHECKING:
    from .service import Service


class CharacteristicReadOptions:
    """Options supplied to characteristic read functions.
    Generally you can ignore these unless you have a long characteristic (eg > 48 bytes) or you have some specific authorization requirements.
    """

    def __init__(self, options: Dict[str, Variant]):
        self._offset = cast(int, _getattr_variant(options, "offset", 0))
        self._mtu = cast(int, _getattr_variant(options, "mtu", None))
        self._device = cast(str, _getattr_variant(options, "device", None))

    @property
    def offset(self) -> int:
        """A byte offset to read the characteristic from until the end."""
        return self._offset

    @property
    def mtu(self) -> Optional[int]:
        """The exchanged Maximum Transfer Unit of the connection with the remote device or 0."""
        return self._mtu

    @property
    def device(self) -> Optional[str]:
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

    def __init__(self, options: Dict[str, Variant]):
        t = _getattr_variant(options, "type", None)
        self._type: Optional[CharacteristicWriteType] = None
        if not t is None:
            self._type = CharacteristicWriteType[t.upper()]

        self._offset = cast(int, _getattr_variant(options, "offset", 0))
        self._mtu = cast(int, _getattr_variant(options, "mtu", 0))
        self._device = cast(str, _getattr_variant(options, "device", None))
        self._link = cast(str, _getattr_variant(options, "link", None))
        self._prepare_authorize = cast(
            bool, _getattr_variant(options, "prepare-authorize", False)
        )

    @property
    def offset(self) -> int:
        """A byte offset to use when writing to this characteristic."""
        return self._offset

    @property
    def type(self) -> Optional[CharacteristicWriteType]:
        """The type of write operation requested or None."""
        return self._type

    @property
    def mtu(self) -> int:
        """The exchanged Maximum Transfer Unit of the connection with the remote device or 0."""
        return self._mtu

    @property
    def device(self) -> str:
        """The path of the remote device on the system dbus or None."""
        return self._device

    @property
    def link(self) -> str:
        """The link type."""
        return self._link

    @property
    def prepare_authorize(self) -> bool:
        """True if prepare authorization request. False otherwise."""
        return self._prepare_authorize


class CharacteristicFlags(Flag):
    """Flags to use when specifying the read/ write routines that can be used when accessing the characteristic.
    These are converted to `bluez flags <https://raw.githubusercontent.com/bluez/bluez/refs/heads/master/doc/org.bluez.GattCharacteristic.rst>`_.
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


class characteristic(
    ServiceAttribute[CharacteristicReadOptions, CharacteristicWriteOptions],
    HierarchicalServiceInterface,
):  # pylint: disable=invalid-name
    """Create a new characteristic with a specified UUID and flags.
    Represents an `org.bluez.GattCharacteristic1 <https://raw.githubusercontent.com/bluez/bluez/refs/heads/master/doc/org.bluez.GattCharacteristic.rst>`_ instance.

    Args:
        uuid: The UUID of the GATT characteristic. A list of standard ids is provided by the `Bluetooth SIG <https://www.bluetooth.com/specifications/assigned-numbers/>`_
        flags: Flags defining the possible read/ write behavior of the attribute.

    See Also:
        :ref:`services`
    """

    _INTERFACE = "org.bluez.GattCharacteristic1"
    _BUS_PREFIX = "char"

    def __init__(
        self,
        uuid: UUIDLike,
        flags: CharacteristicFlags = CharacteristicFlags.READ,
    ):
        super().__init__()

        self.flags = flags
        self._uuid = UUID16.parse_uuid(uuid)
        self._notify = False
        self._value = bytearray()

    @staticmethod
    def _parse_read_options(
        options: Dict[str, Variant],
    ) -> CharacteristicReadOptions:
        return CharacteristicReadOptions(options)

    @staticmethod
    def _parse_write_options(
        options: Dict[str, Variant],
    ) -> CharacteristicWriteOptions:
        return CharacteristicWriteOptions(options)

    def add_child(self, child: HierarchicalServiceInterface) -> None:
        if not isinstance(child, descriptor):
            raise ValueError("characteristic child must be descriptor")
        child.service = self.service
        super().add_child(child)

    def add_descriptor(self, desc: "descriptor") -> None:
        """
        Associated a descriptor with this characteristic.
        """
        self.add_child(desc)

    @ServiceAttribute.service.setter  # type: ignore[attr-defined, untyped-decorator]
    def service(self, service: Optional["Service"]) -> None:
        ServiceAttribute.service.fset(self, service)  # type: ignore[attr-defined]  # pylint: disable=no-member
        for c in self._children:
            assert isinstance(c, descriptor)
            c.service = self.service

    def changed(self, new_value: bytes) -> None:
        """Call this function when the value of a notifiable or indicatable property changes to alert any subscribers.

        Args:
            new_value: The new value of the property to send to any subscribers.
        """
        self._value = bytearray(new_value)
        if self._notify:
            self.emit_properties_changed({"Value": new_value}, [])

    def descriptor(
        self,
        uuid: UUIDLike,
        flags: DescriptorFlags = DescriptorFlags.READ,
    ) -> descriptor:
        """Create a new descriptor with the specified UUID and Flags.

        Args:
            uuid: The UUID of the descriptor.
            flags: Any descriptor access flags to use.
        """
        # Use as a decorator for descriptors that need a getter.
        return descriptor(uuid, self, flags)

    @method("StartNotify")
    def _start_notify(self) -> None:
        if not self.flags | CharacteristicFlags.NOTIFY:
            raise NotSupportedError("The characteristic does not support notification.")

        self._notify = True

    @method("StopNotify")
    def _stop_notify(self) -> None:
        if not self.flags | CharacteristicFlags.NOTIFY:
            raise NotSupportedError("The characteristic does not support notification.")

        self._notify = False

    @dbus_property(PropertyAccess.READ, "UUID")
    def _get_uuid(self) -> "s":  # type: ignore
        return str(self._uuid)

    @dbus_property(PropertyAccess.READ, "Service")
    def _get_service(self) -> "o":  # type: ignore
        assert self._service is not None

        return self._service.export_path

    @dbus_property(PropertyAccess.READ, "Flags")
    def _get_flags(self) -> "as":  # type: ignore
        # Clear the extended properties flag (bluez doesn't seem to like this flag even though its in the docs).
        self.flags &= ~CharacteristicFlags.EXTENDED_PROPERTIES

        # Return a list of set string flag names.
        return [
            _snake_to_kebab(flag.name)
            for flag in CharacteristicFlags
            if self.flags & flag and flag.name is not None
        ]
