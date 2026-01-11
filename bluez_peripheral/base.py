from typing import Optional, Any

from dbus_fast.aio.message_bus import MessageBus
from dbus_fast.service import ServiceInterface


class UniquePathMixin:
    """
    Mixin which calculates the default path for exported components with a _get_default_path.
    """

    _DEFAULT_PATH_PREFIX: Optional[str] = None
    """
    The default prefix to use when a bus path is not specified for this interface during export.
    """

    _default_path_count: int = 0

    def _get_default_path(self, **_: Any) -> str:
        if self._DEFAULT_PATH_PREFIX is None:
            raise NotImplementedError()

        res = self._DEFAULT_PATH_PREFIX + str(type(self)._default_path_count)
        type(self)._default_path_count += 1

        return res


class BaseServiceInterface(ServiceInterface):
    """
    Base class for bluez_peripheral ServiceInterface implementations.
    """

    _INTERFACE = ""
    """
    The dbus interface name implemented by this component.
    """

    _export_bus: Optional[MessageBus] = None
    _export_path: Optional[str] = None

    def __init__(self) -> None:
        super().__init__(name=self._INTERFACE)

    def _get_default_path(self, **_: Any) -> str:
        raise NotImplementedError()

    def _export(self, bus: MessageBus, *, path: Optional[str] = None) -> None:
        """
        Export this service interface.
        If no path is provided a unique value is generated based on _DEFAULT_PATH_PREFIX and a type scoped export counter.
        """
        if self._INTERFACE is None:
            raise NotImplementedError()

        if path is None:
            path = self._get_default_path()

        bus.export(path, self)
        self._export_path = path
        self._export_bus = bus

    def _unexport(self) -> None:
        """
        Unexport this service interface.
        """
        if self._INTERFACE is None:
            raise NotImplementedError()

        if self._export_bus is None or self._export_path is None:
            raise ValueError("This service interface is not exported")

        self._export_bus.unexport(self._export_path, self._INTERFACE)
        self._export_path = None
        self._export_bus = None

    @property
    def export_path(self) -> Optional[str]:
        """
        Returns the message bus path that the ServiceInterface is exported on or None.
        """
        return self._export_path


class HierarchicalServiceInterface(BaseServiceInterface):
    """
    Base class for a member of a hierarchy of ServiceInterfaces which should be exported and unexported as a group.
    """

    _BUS_PREFIX = ""
    """
    The prefix used by default when exporting this ServiceInterface as a child of another component.
    """

    def __init__(self) -> None:
        super().__init__()

        self._parent: Optional["HierarchicalServiceInterface"] = None
        self._children: list["HierarchicalServiceInterface"] = []

    def _get_default_path(self, **kwargs: Any) -> str:
        num = kwargs.get("num")

        if self._parent is not None and num is not None:
            return f"{self._parent.export_path}/{self._BUS_PREFIX}{num}"

        raise ValueError("path or parent must be specified")

    def add_child(self, child: "HierarchicalServiceInterface") -> None:
        """
        Adds a child service interface.
        """
        if not self.export_path is None:
            raise ValueError("Registered components cannot be modified")

        self._children.append(child)
        child._parent = self  # pylint: disable=protected-access

    def remove_child(self, child: "HierarchicalServiceInterface") -> None:
        """
        Removes a child service interface.
        """
        if not self.export_path is None:
            raise ValueError("Registered components cannot be modified")

        self._children.remove(child)
        child._parent = None  # pylint: disable=protected-access

    def _export(
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
        if path is None:
            path = self._get_default_path(num=num)

        super()._export(bus, path=path)
        for i, c in enumerate(self._children):
            c._export(bus, num=i)

    def _unexport(self) -> None:
        """
        Attempts to unexport this component and all registered children from the specified message bus.
        """
        for c in self._children:
            c._unexport()

        super()._unexport()
