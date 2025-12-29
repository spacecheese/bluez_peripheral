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
from dbus_fast.service import method, ServiceInterface, dbus_property
from dbus_fast.aio.message_bus import MessageBus

from ..error import FailedError, NotSupportedError

if TYPE_CHECKING:
    from .service import Service


class HierarchicalServiceInterface(ServiceInterface):
    """
    Base class for a member of a hierarchy of ServiceInterfaces which should be exported and unexported as a group.
    """

    BUS_PREFIX = ""
    """
        The prefix used by default when exporting this ServiceInterface as a child of another component.
    """

    BUS_INTERFACE = ""
    """
        The dbus interface name implemented by this component.
    """

    def __init__(self) -> None:
        super().__init__(name=self.BUS_INTERFACE)

        self._export_path: Optional[str] = None
        self._parent: Optional["HierarchicalServiceInterface"] = None
        self._children: list["HierarchicalServiceInterface"] = []

    def add_child(self, child: "HierarchicalServiceInterface") -> None:
        """
        Adds a child service interface.
        """
        if self.is_exported:
            raise ValueError("Registered components cannot be modified")

        self._children.append(child)
        child._parent = self  # pylint: disable=protected-access

    def remove_child(self, child: "HierarchicalServiceInterface") -> None:
        """
        Removes a child service interface.
        """
        if self.is_exported:
            raise ValueError("Registered components cannot be modified")

        self._children.remove(child)
        child._parent = None  # pylint: disable=protected-access

    @property
    def export_path(self) -> Optional[str]:
        """
        The path on which this service is exported (or None).
        """
        return self._export_path

    @property
    def is_exported(self) -> bool:
        """
        Indicates whether this service is exported or not.
        """
        return self._export_path is not None

    def export(
        self, bus: MessageBus, *, num: Optional[int] = 0, path: Optional[str] = None
    ) -> None:
        """
        Attempts to export this component and all registered children. Either ``num`` or ``path`` must be provided.

        Args:
            bus: The message bus to export this and all children on.
            num: An optional index of this component within it's parent.
            path: An optional absolute path indicating where this component should be exported.
                If no ``path`` is specified then this component must have been registered using another components :class:`HierarchicalServiceInterface.add_child()` method.
        """
        if self.is_exported:
            raise ValueError("Cannot export an already exported component")

        if path is None:
            if self._parent is not None:
                path = f"{self._parent.export_path}/{self.BUS_PREFIX}{num}"
            else:
                raise ValueError("path or parent must be specified")

        bus.export(path, self)
        self._export_path = path

        for i, c in enumerate(self._children):
            c.export(bus, num=i)

    def unexport(self, bus: MessageBus) -> None:
        """
        Attempts to unexport this component and all registered children from the specified message bus.
        """
        if not self.is_exported:
            raise ValueError("Cannot unexport a component which is not exported")
        assert self._export_path is not None

        for c in self._children:
            c.unexport(bus)

        bus.unexport(self._export_path, self.BUS_INTERFACE)
        self._export_path = None


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
