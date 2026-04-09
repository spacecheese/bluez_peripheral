import inspect
from abc import ABC, abstractmethod
from typing import (
    Any,
    Optional,
    TypeVar,
    Generic,
    Union,
    Callable,
    Awaitable,
    Dict,
    cast,
    TYPE_CHECKING,
)

from dbus_fast import Variant, DBusError
from dbus_fast.constants import PropertyAccess
from dbus_fast.service import method, dbus_property

from ..error import FailedError, NotSupportedError

if TYPE_CHECKING:
    from .service import Service


ReadOptionsT = TypeVar("ReadOptionsT")
"""
The type of options supplied by a dbus ReadValue access.
"""
WriteOptionsT = TypeVar("WriteOptionsT")
"""
The type of options supplied by a dbus WriteValue access.
"""
GetterType = Union[
    Callable[[Any, ReadOptionsT], bytes],
    Callable[[Any, ReadOptionsT], Awaitable[bytes]],
]
SetterType = Union[
    Callable[[Any, bytes, WriteOptionsT], None],
    Callable[[Any, bytes, WriteOptionsT], Awaitable[None]],
]


class ServiceAttribute(Generic[ReadOptionsT, WriteOptionsT], ABC):
    """
    Base class for service components with a ReadValue and WriteValue dbus interface.
    """

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

        self._value = bytearray()
        self._service: Optional["Service"] = None

        self._getter_func: Optional[GetterType[ReadOptionsT]] = None
        self._setter_func: Optional[SetterType[WriteOptionsT]] = None

    @staticmethod
    @abstractmethod
    def _parse_read_options(options: Dict[str, Variant]) -> ReadOptionsT:
        pass

    @staticmethod
    @abstractmethod
    def _parse_write_options(options: Dict[str, Variant]) -> WriteOptionsT:
        pass

    @property
    def service(self) -> Optional["Service"]:
        """
        Gets the service that this attribute is a child of.
        """
        return self._service

    @service.setter
    def service(self, service: Optional["Service"]) -> None:
        """
        Sets the service that this attribute is a child of (do no call directly).
        """
        self._service = service

    # Decorators
    def setter(
        self, setter_func: SetterType[WriteOptionsT]
    ) -> "ServiceAttribute[ReadOptionsT, WriteOptionsT]":
        """
        Decorator for specifying a setter to be called by the ReadValue interface.
        """
        self._setter_func = setter_func
        return self

    def __call__(
        self,
        getter_func: Optional[GetterType[ReadOptionsT]] = None,
        setter_func: Optional[SetterType[WriteOptionsT]] = None,
    ) -> Any:
        """
        Decorator for specifying a getter and setter pair to be called by the ReadValue and WriteValue interfaces.
        """
        self._getter_func = getter_func
        self._setter_func = setter_func

        return self

    # dbus Interface
    @method("ReadValue")
    async def _read_value(self, options: "a{sv}") -> "ay":  # type: ignore
        if self._getter_func is None:
            raise NotSupportedError("No getter implemented")

        if self._service is None:
            raise FailedError("No service provided")

        options = self._parse_read_options(options)
        try:
            if inspect.iscoroutinefunction(self._getter_func):
                res = await self._getter_func(self._service, options)
            else:
                res = self._getter_func(self._service, options)
                res = cast(bytes, res)

            self._value[options.offset :] = bytearray(res)
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
        if self._setter_func is None:
            raise NotSupportedError("No setter implemented")

        if self._service is None:
            raise FailedError("No service provided")

        options = self._parse_write_options(options)
        try:
            if inspect.iscoroutinefunction(self._setter_func):
                await self._setter_func(self._service, data, options)
            else:
                self._setter_func(self._service, data, options)
        except DBusError as e:
            raise e
        except Exception as e:
            print(
                "Unrecognised exception type when writing descriptor value: \n" + str(e)
            )
            raise e
        self._value[options.offset :] = bytearray(data)

    @dbus_property(PropertyAccess.READ, "Value")
    def _get_value(self) -> "ay":  # type: ignore
        return bytes(self._value)
