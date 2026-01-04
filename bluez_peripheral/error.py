from dbus_fast import DBusError


class BluezNotAvailableError(RuntimeError):
    """
    Raised when org.bluez is not present on the dbus.
    This is normally because the bluetooth service is not running.
    """

    def __init__(self, message: str):
        super().__init__(message)


class FailedError(DBusError):
    """Raised when an operation failed."""

    def __init__(self, message: str):
        super().__init__("org.bluez.Error.Failed", message)


class InProgressError(DBusError):
    """Raised when an operation was already in progress but was requested again."""

    def __init__(self, message: str):
        super().__init__("org.bluez.Error.InProgress", message)


class NotPermittedError(DBusError):
    """Raised when a requested operation is not permitted."""

    def __init__(self, message: str):
        super().__init__("org.bluez.Error.NotPermitted", message)


class InvalidValueLengthError(DBusError):
    """Raised when a written value was an illegal length."""

    def __init__(self, message: str):
        super().__init__("org.bluez.Error.InvalidValueLength", message)


class InvalidOffsetError(DBusError):
    """Raised when an illegal offset is provided."""

    def __init__(self, message: str):
        super().__init__("org.bluez.Error.InvalidOffset", message)


class NotAuthorizedError(DBusError):
    """Raised when a requester is not authorized to perform the requested operation."""

    def __init__(self, message: str):
        super().__init__("org.bluez.Error.NotAuthorized", message)


class NotConnectedError(DBusError):
    """Raised when the operation could not be completed because the target is not connected."""

    def __init__(self, message: str):
        super().__init__("org.bluez.Error.NotConnected", message)


class NotSupportedError(DBusError):
    """Raised when the requested operation is not supported."""

    def __init__(self, message: str):
        super().__init__("org.bluez.Error.NotSupported", message)


class RejectedError(DBusError):
    """Raised when the pairing operation was rejected."""

    def __init__(self, message: str):
        super().__init__("org.bluez.Error.Rejected", message)
