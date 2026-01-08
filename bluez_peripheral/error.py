from contextlib import AbstractAsyncContextManager
from typing import Optional, Type, Any

from dbus_fast import DBusError


class BluezNotAvailableError(RuntimeError):
    """
    Raised when org.bluez is not present on the dbus.
    This is normally because the bluetooth service is not running.
    """

    def __init__(self, message: str):
        super().__init__(message)


class BluezDBusErrorBase(DBusError):
    """
    Base class for typed bluez dbus errors.
    Subclasses must define ERROR_TYPE.
    """

    ERROR_TYPE: str

    def __init__(
        self,
        text: Optional[str] = None,
        *,
        error: Optional[DBusError] = None,
    ):
        if error is not None:
            super().__init__(error.type, error.text, error.reply)
        else:
            assert text is not None
            super().__init__(self.ERROR_TYPE, text)


class FailedError(BluezDBusErrorBase):
    """Raised when an operation failed."""

    ERROR_TYPE = "org.bluez.Error.Failed"


class InProgressError(BluezDBusErrorBase):
    """Raised when an operation is already in progress."""

    ERROR_TYPE = "org.bluez.Error.InProgress"


class NotPermittedError(BluezDBusErrorBase):
    """Raised when a requested operation is not permitted."""

    ERROR_TYPE = "org.bluez.Error.NotPermitted"


class InvalidValueLengthError(BluezDBusErrorBase):
    """Raised when a written value was an illegal length."""

    ERROR_TYPE = "org.bluez.Error.InvalidValueLength"


class InvalidOffsetError(BluezDBusErrorBase):
    """Raised when an illegal offset is provided."""

    ERROR_TYPE = "org.bluez.Error.InvalidOffset"


class NotAuthorizedError(BluezDBusErrorBase):
    """Raised when the requester is not authorized for the operation."""

    ERROR_TYPE = "org.bluez.Error.NotAuthorized"


class NotConnectedError(BluezDBusErrorBase):
    """Raised when the target device is not connected."""

    ERROR_TYPE = "org.bluez.Error.NotConnected"


class NotSupportedError(BluezDBusErrorBase):
    """Raised when the requested operation is not supported."""

    ERROR_TYPE = "org.bluez.Error.NotSupported"


class RejectedError(BluezDBusErrorBase):
    """Raised when the pairing or operation was rejected."""

    ERROR_TYPE = "org.bluez.Error.Rejected"


class AlreadyExistsError(BluezDBusErrorBase):
    """Raised when the object already exists."""

    ERROR_TYPE = "org.bluez.Error.AlreadyExists"


class DoesNotExistError(BluezDBusErrorBase):
    """Raised when the object does not exist."""

    ERROR_TYPE = "org.bluez.Error.DoesNotExist"


class NotAvailableError(BluezDBusErrorBase):
    """Raised when the requested resource is not available."""

    ERROR_TYPE = "org.bluez.Error.NotAvailable"


class NotReadyError(BluezDBusErrorBase):
    """Raised when the adapter or device is not ready."""

    ERROR_TYPE = "org.bluez.Error.NotReady"


class InvalidArgumentsError(BluezDBusErrorBase):
    """Indicates that an object has invalid or conflicting properties."""

    ERROR_TYPE = "org.bluez.Error.InvalidArguments"


_SUPPORTED_ERRORS = {
    e.ERROR_TYPE: e
    for e in [
        FailedError,
        InProgressError,
        NotPermittedError,
        InvalidValueLengthError,
        InvalidOffsetError,
        NotAuthorizedError,
        NotConnectedError,
        NotSupportedError,
        RejectedError,
        AlreadyExistsError,
        DoesNotExistError,
        NotAvailableError,
        NotReadyError,
        InvalidArgumentsError,
    ]
}


def translate_bluez_error(err: DBusError) -> DBusError:
    """
    Translate a raw DBusError into a typed error class if supported.
    Returns the original error if no mapping exists.
    """
    cls = _SUPPORTED_ERRORS.get(err.type)
    if cls is not None:
        return cls(error=err)
    return err


class bluez_error_wrapper(
    AbstractAsyncContextManager[None]
):  # pylint: disable=invalid-name
    """
    Translates DBusErrors into typed error classes (where supported)

    Usage:
        async with bluez_error_handler():
            await adapter.start_discovery()
    """

    async def __aenter__(self) -> None:
        return None

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Any,
    ) -> bool:
        if isinstance(exc, DBusError):
            raise translate_bluez_error(exc) from exc

        return False
