from enum import Flag, auto
from typing import Callable, Union, Awaitable, Optional, Dict, TYPE_CHECKING, cast

from dbus_fast import Variant
from dbus_fast.service import dbus_property
from dbus_fast.constants import PropertyAccess

from .base import HierarchicalServiceInterface, ServiceAttribute
from ..uuid16 import UUID16, UUIDCompatible
from ..util import _snake_to_kebab, _getattr_variant

if TYPE_CHECKING:
    from .service import Service
    from .characteristic import characteristic


class DescriptorReadOptions:
    """Options supplied to descriptor read functions.
    Generally you can ignore these unless you have a long descriptor (eg > 48 bytes) or you have some specific authorization requirements.
    """

    def __init__(self, options: Dict[str, Variant]):
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


GetterType = Union[
    Callable[["Service", DescriptorReadOptions], bytes],
    Callable[["Service", DescriptorReadOptions], Awaitable[bytes]],
]
SetterType = Union[
    Callable[["Service", bytes, DescriptorWriteOptions], None],
    Callable[["Service", bytes, DescriptorWriteOptions], Awaitable[None]],
]


# Decorator for descriptor getters/ setters.
class descriptor(
    ServiceAttribute[DescriptorReadOptions, DescriptorWriteOptions],
    HierarchicalServiceInterface,
):  # pylint: disable=invalid-name
    """Create a new descriptor with a specified UUID and flags associated with the specified parent characteristic.

    Args:
        uuid: The UUID of this GATT descriptor. A list of standard ids is provided by the `Bluetooth SIG Assigned Numbers <https://www.bluetooth.com/specifications/assigned-numbers/>`_
        characteristic: The parent characteristic to associate this descriptor with.
        flags: Flags defining the possible read/ write behavior of the attribute.

    See Also:
        :ref:`services`
    """

    BUS_PREFIX = "desc"
    BUS_INTERFACE = "org.bluez.GattDescriptor1"

    def __init__(
        self,
        uuid: UUIDCompatible,
        characteristic: "characteristic",
        flags: DescriptorFlags = DescriptorFlags.READ,
    ):
        super().__init__()

        self.flags = flags
        self._uuid = UUID16.parse_uuid(uuid)
        self._characteristic = characteristic

        characteristic.add_child(self)

    @staticmethod
    def _parse_read_options(
        options: Dict[str, Variant],
    ) -> DescriptorReadOptions:
        return DescriptorReadOptions(options)

    @staticmethod
    def _parse_write_options(
        options: Dict[str, Variant],
    ) -> DescriptorWriteOptions:
        return DescriptorWriteOptions(options)

    @dbus_property(PropertyAccess.READ, "UUID")
    def _get_uuid(self) -> "s":  # type: ignore
        return str(self._uuid)

    @dbus_property(PropertyAccess.READ, "Characteristic")
    def _get_characteristic(self) -> "o":  # type: ignore
        return self._characteristic.export_path

    @dbus_property(PropertyAccess.READ, "Flags")
    def _get_flags(self) -> "as":  # type: ignore
        # Return a list of string flag names.
        return [
            _snake_to_kebab(flag.name)
            for flag in DescriptorFlags
            if self.flags & flag and flag.name is not None
        ]
