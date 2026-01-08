from typing import Optional

from dbus_fast.aio.message_bus import MessageBus
from dbus_fast.service import ServiceInterface


class BaseServiceInterface(ServiceInterface):
    """
    Base class for bluez_peripheral ServiceInterface implementations.
    """

    _INTERFACE = ""
    """
    The dbus interface name implemented by this component.
    """

    _DEFAULT_PATH_PREFIX: Optional[str] = None
    """
    The default prefix to use when a bus path is not specified for this interface during export.
    """

    _default_path_count: int = 0

    _export_bus: Optional[MessageBus] = None
    _export_path: Optional[str] = None

    def __init__(self) -> None:
        super().__init__(name=self._INTERFACE)

    def _get_unique_export_path(self) -> str:
        if self._DEFAULT_PATH_PREFIX is None:
            raise NotImplementedError()

        res = self._DEFAULT_PATH_PREFIX + str(type(self)._default_path_count)
        type(self)._default_path_count += 1

        return res

    def export(self, bus: MessageBus, *, path: Optional[str] = None) -> None:
        """
        Export this service interface.
        If no path is provided a unique value is generated based on _DEFAULT_PATH_PREFIX and a type scoped export counter.
        """
        if self._INTERFACE is None:
            raise NotImplementedError()

        if path is None:
            path = self._get_unique_export_path()

        bus.export(path, self)
        self._export_path = path
        self._export_bus = bus

    def unexport(self) -> None:
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
        The dbus path on which this interface is currently exported.
        """
        return self._export_path

    @property
    def is_exported(self) -> bool:
        """
        Whether this service interface is exported and visible to dbus clients.
        """
        return self._export_bus is not None and self._export_path is not None
