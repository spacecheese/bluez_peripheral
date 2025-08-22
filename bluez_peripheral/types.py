from enum import Enum, Flag, auto
from typing import Optional, cast, Dict

from dbus_fast import Variant

from .util import _getattr_variant


class AdvertisingPacketType(Enum):
    """Represents the type of packet used to perform a service."""

    BROADCAST = 0
    """The relevant service(s) will be broadcast and do not require pairing.
    """
    PERIPHERAL = 1
    """The relevant service(s) are associated with a peripheral role.
    """


class AdvertisingIncludes(Flag):
    """The fields to include in advertisements."""

    NONE = 0
    TX_POWER = auto()
    """Transmission power should be included.
    """
    APPEARANCE = auto()
    """Device appearance number should be included.
    """
    LOCAL_NAME = auto()
    """The local name of this device should be included.
    """


class CharacteristicReadOptions:
    """Options supplied to characteristic read functions.
    Generally you can ignore these unless you have a long characteristic (eg > 48 bytes) or you have some specific authorization requirements.
    """

    def __init__(self, options: Optional[Dict[str, Variant]] = None):
        if options is None:
            return

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

    def __init__(self, options: Optional[Dict[str, Variant]] = None):
        if options is None:
            return

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
    These are converted to `bluez flags <https://github.com/bluez/bluez/blob/master/doc/org.bluez.GattCharacteristic.rst>`_.
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
    def offset(self) -> int:
        """A byte offset to use when writing to this descriptor."""
        return cast(int, self._offset)

    @property
    def link(self) -> str:
        """The link type."""
        return cast(str, self._link)

    @property
    def device(self) -> str:
        """The path of the remote device on the system dbus or None."""
        return cast(str, self._device)


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
    def offset(self) -> int:
        """A byte offset to use when writing to this descriptor."""
        return cast(int, self._offset)

    @property
    def device(self) -> str:
        """The path of the remote device on the system dbus or None."""
        return cast(str, self._device)

    @property
    def link(self) -> str:
        """The link type."""
        return cast(str, self._link)

    @property
    def prepare_authorize(self) -> bool:
        """True if prepare authorization request. False otherwise."""
        return cast(bool, self._prepare_authorize)


class DescriptorFlags(Flag):
    """Flags to use when specifying the read/ write routines that can be used when accessing the descriptor.
    These are converted to `bluez flags <https://github.com/bluez/bluez/blob/master/doc/org.bluez.GattDescriptor.rst>`_.
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
