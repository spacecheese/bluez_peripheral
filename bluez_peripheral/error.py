from dbus_next import DBusError

class FailedError(DBusError):
	def __init__(message):
		super.__init__("org.bluez.Error.Failed", message)

class InProgressError(DBusError):
	def __init__(message):
		super.__init__("org.bluez.Error.InProgress", message)

class NotPermittedError(DBusError):
	def __init__(message):
		super.__init__("org.bluez.Error.NotPermitted", message)

class InvalidValueLengthError(DBusError):
	def __init__(message):
		super.__init__("org.bluez.Error.InvalidValueLength", message)

class InvalidOffsetError(DBusError):
	def __init__(message):
		super.__init__("org.bluez.Error.InvalidOffset", message)

class NotAuthorizedError(DBusError):
	def __init__(message):
		super.__init__("org.bluez.Error.NotAuthorized", message)

class NotConnectedError(DBusError):
	def __init__(message):
		super.__init__("org.bluez.Error.NotConnected", message)

class NotSupportedError(DBusError):
	def __init__(message):
		super.__init__("org.bluez.Error.NotSupported", message)

class RejectedError(DBusError):
    def __init__(message):
        super.__init__("org.bluez.Error.Rejected", message)

