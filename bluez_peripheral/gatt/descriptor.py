import inspect
from typing import Callable, Union, Awaitable, Optional, Dict, TYPE_CHECKING, cast

from dbus_fast.errors import DBusError
from dbus_fast.aio.message_bus import MessageBus
from dbus_fast.service import ServiceInterface, method, dbus_property
from dbus_fast.constants import PropertyAccess

from ..types import DescriptorFlags, DescriptorReadOptions, DescriptorWriteOptions
from ..uuid16 import UUID16, UUIDCompatible
from ..util import _snake_to_kebab
from ..error import FailedError

if TYPE_CHECKING:
    from .service import Service


GetterType = Union[
    Callable[["Service", DescriptorReadOptions], bytes],
    Callable[["Service", DescriptorReadOptions], Awaitable[bytes]],
]
SetterType = Union[
    Callable[["Service", bytes, DescriptorWriteOptions], None],
    Callable[["Service", bytes, DescriptorWriteOptions], Awaitable[None]],
]


# Decorator for descriptor getters/ setters.
class descriptor(ServiceInterface):  # pylint: disable=invalid-name
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
        uuid: UUIDCompatible,
        characteristic: "characteristic",  # type: ignore
        flags: DescriptorFlags = DescriptorFlags.READ,
    ):
        self.uuid = UUID16.parse_uuid(uuid)
        self.getter_func: Optional[GetterType] = None
        self.setter_func: Optional[SetterType] = None
        self.characteristic = characteristic
        self.flags = flags
        self._service: Optional[Service] = None
        self._num: Optional[int] = None

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

    def set_service(self, service: Optional["Service"]) -> None:
        """Attaches this descriptor to the specified service.

        Warnings:
            Do not call this directly. Subclasses of the Service class will handle this automatically.
        """
        self._service = service

    # DBus
    def _get_path(self) -> str:
        if self._characteristic_path is None:
            raise ValueError()

        return f"{self._characteristic_path}/desc{self._num}"

    def _export(self, bus: MessageBus, characteristic_path: str, num: int) -> None:
        self._characteristic_path = characteristic_path
        self._num = num
        bus.export(self._get_path(), self)

    def _unexport(self, bus: MessageBus) -> None:
        if self._characteristic_path is None:
            return

        bus.unexport(self._get_path(), self._INTERFACE)
        self._characteristic_path = None

    @method("ReadValue")
    async def _read_value(self, options: "a{sv}") -> "ay":  # type: ignore
        if self.getter_func is None:
            raise FailedError("No getter implemented")

        if self._service is None:
            raise ValueError()

        try:
            if inspect.iscoroutinefunction(self.getter_func):
                return await self.getter_func(
                    self._service, DescriptorReadOptions(options)
                )

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

    @method("WriteValue")
    async def _write_value(self, data: "ay", options: "a{sv}"):  # type: ignore
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

    @dbus_property(PropertyAccess.READ, "UUID")
    def _get_uuid(self) -> "s":  # type: ignore
        return str(self.uuid)

    @dbus_property(PropertyAccess.READ, "Characteristic")
    def _get_characteristic(self) -> "o":  # type: ignore
        return self._characteristic_path

    @dbus_property(PropertyAccess.READ, "Flags")
    def _get_flags(self) -> "as":  # type: ignore
        # Return a list of string flag names.
        return [
            _snake_to_kebab(flag.name)
            for flag in DescriptorFlags
            if self.flags & flag and flag.name is not None
        ]
