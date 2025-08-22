import inspect
from typing import Callable, Optional, Union, Awaitable, List, cast, TYPE_CHECKING

from dbus_fast.errors import DBusError
from dbus_fast.constants import PropertyAccess
from dbus_fast.service import ServiceInterface, method, dbus_property
from dbus_fast.aio import MessageBus

from ..types import CharacteristicFlags, CharacteristicReadOptions, CharacteristicWriteOptions
from .descriptor import descriptor as Descriptor, DescriptorFlags
from ..uuid16 import UUID16, UUIDCompatible
from ..util import _snake_to_kebab
from ..error import NotSupportedError, FailedError

if TYPE_CHECKING:
    from .service import Service


GetterType = Union[
    Callable[["Service", CharacteristicReadOptions], bytes],
    Callable[["Service", CharacteristicReadOptions], Awaitable[bytes]],
]
SetterType = Union[
    Callable[["Service", bytes, CharacteristicWriteOptions], None],
    Callable[["Service", bytes, CharacteristicWriteOptions], Awaitable[None]],
]


class characteristic(ServiceInterface):  # pylint: disable=invalid-name
    """Create a new characteristic with a specified UUID and flags.

    Args:
        uuid: The UUID of the GATT characteristic. A list of standard ids is provided by the `Bluetooth SIG <https://www.bluetooth.com/specifications/assigned-numbers/>`_
        flags: Flags defining the possible read/ write behavior of the attribute.

    See Also:
        :ref:`services`
    """

    _INTERFACE = "org.bluez.GattCharacteristic1"

    def __init__(
        self,
        uuid: UUIDCompatible,
        flags: CharacteristicFlags = CharacteristicFlags.READ,
    ):
        self.uuid = UUID16.parse_uuid(uuid)
        self.getter_func: Optional[GetterType] = None
        self.setter_func: Optional[SetterType] = None
        self.flags = flags

        self._notify = False
        self._service_path: Optional[str] = None
        self._descriptors: List[Descriptor] = []
        self._service: Optional["Service"] = None
        self._value = bytearray()
        self._num: Optional[int] = None

        super().__init__(self._INTERFACE)

    def changed(self, new_value: bytes) -> None:
        """Call this function when the value of a notifiable or indicatable property changes to alert any subscribers.

        Args:
            new_value: The new value of the property to send to any subscribers.
        """
        if self._notify:
            self.emit_properties_changed({"Value": new_value}, [])

    # Decorators
    def setter(self, setter_func: SetterType) -> "characteristic":
        """A decorator for characteristic value setters."""
        self.setter_func = setter_func
        return self

    def __call__(
        self,
        getter_func: Optional[GetterType] = None,
        setter_func: Optional[SetterType] = None,
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
        self,
        uuid: UUIDCompatible,
        flags: DescriptorFlags = DescriptorFlags.READ,
    ) -> Descriptor:
        """Create a new descriptor with the specified UUID and Flags.

        Args:
            uuid: The UUID of the descriptor.
            flags: Any descriptor access flags to use.
        """
        # Use as a decorator for descriptors that need a getter.
        return Descriptor(uuid, self, flags)

    def _is_registered(self) -> bool:
        return not self._service_path is None

    def set_service(self, service: Optional["Service"]) -> None:
        """Attaches this characteristic to the specified service.

        Warnings:
            Do not call this directly. Subclasses of the Service class will handle this automatically.
        """
        self._service = service

        for desc in self._descriptors:
            desc.set_service(service)

    def add_descriptor(self, desc: Descriptor) -> None:
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
        desc.set_service(self._service)

    def remove_descriptor(self, desc: Descriptor) -> None:
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
        desc.set_service(None)

    def _get_path(self) -> str:
        if self._service_path is None:
            raise ValueError()

        return f"{self._service_path}/char{self._num}"

    def _export(self, bus: MessageBus, service_path: str, num: int) -> None:
        self._service_path = service_path
        self._num = num
        bus.export(self._get_path(), self)

        # Export and number each of the child descriptors.
        i = 0
        for desc in self._descriptors:
            desc._export(bus, self._get_path(), i)
            i += 1

    def _unexport(self, bus: MessageBus) -> None:
        # Unexport this and each of the child descriptors.
        bus.unexport(self._get_path(), self._INTERFACE)
        for desc in self._descriptors:
            desc._unexport(bus)

        self._service_path = None

    @method("ReadValue")
    async def _read_value(self, options: "a{sv}") -> "ay":  # type: ignore
        if self.getter_func is None:
            raise FailedError("No getter implemented")

        if self._service is None:
            raise ValueError()

        try:
            res: bytes
            if inspect.iscoroutinefunction(self.getter_func):
                res = await self.getter_func(
                    self._service, CharacteristicReadOptions(options)
                )
            else:
                res = cast(
                    bytes,
                    self.getter_func(self._service, CharacteristicReadOptions(options)),
                )

            self._value = bytearray(res)
            return res
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
        return str(self.uuid)

    @dbus_property(PropertyAccess.READ, "Service")
    def _get_service(self) -> "o":  # type: ignore
        return self._service_path

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

    @dbus_property(PropertyAccess.READ, "Value")
    def _get_value(self) -> "ay":  # type: ignore
        return bytes(self._value)
