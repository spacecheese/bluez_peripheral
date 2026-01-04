from typing import Awaitable, Callable, Optional
from enum import Enum

from dbus_fast.service import method
from dbus_fast.aio.message_bus import MessageBus
from dbus_fast.aio.proxy_object import ProxyInterface

from .util import _snake_to_pascal
from .error import RejectedError
from .base import BaseServiceInterface


class AgentCapability(Enum):
    """The IO Capabilities of the local device supported by the agent.
    See Tables 5.5 and 5.7 of the `Bluetooth Core Spec Part C. <https://www.bluetooth.org/docman/handlers/downloaddoc.ashx?doc_id=478726>`_
    """

    KEYBOARD_DISPLAY = 0
    """Any pairing method can be used.
    """
    DISPLAY_ONLY = 1
    """Device has no input but a 6 digit pairing code can be displayed.
    """
    DISPLAY_YES_NO = 2
    """Device can display a 6 digit pairing code and record the response to a yes/ no prompt.
    """
    KEYBOARD_ONLY = 3
    """Device has no output but can be used to input a pairing code.
    """
    NO_INPUT_NO_OUTPUT = 4
    """Device has no input/ output capabilities and therefore cannot support MITM protection.
    """


class BaseAgent(BaseServiceInterface):
    """The abstract base agent for all bluez agents. Subclass this if one of the existing agents does not meet your requirements.
    Alternatively bluez supports several built in agents which can be selected using the bluetoothctl cli.
    Represents an `org.bluez.Agent1 <https://raw.githubusercontent.com/bluez/bluez/refs/heads/master/doc/org.bluez.Agent.rst>`_ instance.

    Args:
        capability: The IO capabilities of the agent.
    """

    _INTERFACE = "org.bluez.Agent1"
    _MANAGER_INTERFACE = "org.bluez.AgentManager1"
    _DEFAULT_PATH_PREFIX = "/com/spacecheese/bluez_peripheral/agent"

    def __init__(
        self,
        capability: AgentCapability,
    ):
        self._capability: AgentCapability = capability

        super().__init__()

    @method("Release")
    def _release(self):  # type: ignore
        pass

    @method("Cancel")
    def _cancle(self):  # type: ignore
        pass

    def _get_capability(self) -> str:
        return _snake_to_pascal(self._capability.name)

    async def _get_manager_interface(self, bus: MessageBus) -> ProxyInterface:
        introspection = await bus.introspect("org.bluez", "/org/bluez")
        proxy = bus.get_proxy_object("org.bluez", "/org/bluez", introspection)
        return proxy.get_interface(self._MANAGER_INTERFACE)

    async def register(
        self, bus: MessageBus, *, path: Optional[str] = None, default: bool = True
    ) -> None:
        """Expose this agent on the specified message bus and register it with the bluez agent manager.

        Args:
            bus: The message bus to expose the agent using.
            default: Whether or not the agent should be registered as default.
                Non-default agents will not be called to respond to incoming pairing requests.
                The invoking process requires superuser if this is true.
            path: The path to expose this message bus on.
        """
        self.export(bus, path=path)

        interface = await self._get_manager_interface(bus)
        await interface.call_register_agent(path, self._get_capability())  # type: ignore

        if default:
            await interface.call_request_default_agent(self.export_path)  # type: ignore

    async def unregister(self) -> None:
        """Unregister this agent with bluez and remove it from the specified message bus.

        Args:
            bus: The message bus used to expose the agent.
        """
        if not self.is_exported:
            raise ValueError("agent has not been registered")
        assert self._export_bus is not None

        interface = await self._get_manager_interface(self._export_bus)
        await interface.call_unregister_agent(self.export_path)  # type: ignore

        self.unexport()


class TestAgent(BaseAgent):
    """A testing agent that invokes the debugger whenever a method is called. Use this for debugging only.

    Args:
        capability: The IO capability of the agent.
    """

    @method("Cancel")
    def _cancel(self):  # type: ignore
        breakpoint()  # pylint: disable=forgotten-debug-statement

    @method("Release")
    def _release(self):  # type: ignore
        breakpoint()  # pylint: disable=forgotten-debug-statement

    @method("RequestPinCode")
    def _request_pin_code(self, _device: "o") -> "s":  # type: ignore
        breakpoint()  # pylint: disable=forgotten-debug-statement

    @method("DisplayPinCode")
    def _display_pin_code(self, _device: "o", _pincode: "s"):  # type: ignore
        breakpoint()  # pylint: disable=forgotten-debug-statement

    @method("RequestPasskey")
    def _request_passkey(self, _device: "o") -> "u":  # type: ignore
        breakpoint()  # pylint: disable=forgotten-debug-statement

    @method("DisplayPasskey")
    def _display_passkey(self, _device: "o", _passkey: "u", _entered: "q"):  # type: ignore
        breakpoint()  # pylint: disable=forgotten-debug-statement

    @method("RequestConfirmation")
    def _request_confirmation(self, _device: "o", _passkey: "u"):  # type: ignore
        breakpoint()  # pylint: disable=forgotten-debug-statement

    @method("RequestAuthorization")
    def _request_authorization(self, _device: "o"):  # type: ignore
        breakpoint()  # pylint: disable=forgotten-debug-statement

    @method("AuthorizeService")
    def _authorize_service(self, _device: "o", _uuid: "s"):  # type: ignore
        breakpoint()  # pylint: disable=forgotten-debug-statement


class NoIoAgent(BaseAgent):
    """An agent with no input or output capabilities. All incoming pairing requests from all devices will be accepted unconditionally."""

    def __init__(self) -> None:
        super().__init__(AgentCapability.NO_INPUT_NO_OUTPUT)

    @method("RequestAuthorization")
    def _request_authorization(self, device: "o"):  # type: ignore
        pass

    @method("AuthorizeService")
    def _authorize_service(self, device: "o", uuid: "s"):  # type: ignore
        pass


class YesNoAgent(BaseAgent):
    """An agent that uses a callback to display a yes/ no prompt in response to an incoming pairing request.

    Args:
        request_confirmation: The callback called when a pairing request is received.
            This should return true if the user indicates that the supplied passcode is correct or false otherwise.
        cancel: The callback called when a pairing request is canceled remotely.
    """

    def __init__(
        self,
        request_confirmation: Callable[[int], Awaitable[bool]],
        cancel: Callable[[], None],
    ):
        self._request_confirmation_callback = request_confirmation
        self._cancel_callback = cancel

        super().__init__(AgentCapability.DISPLAY_YES_NO)

    @method("RequestConfirmation")
    async def _request_confirmation(self, _device: "o", passkey: "u"):  # type: ignore
        if not await self._request_confirmation_callback(passkey):
            raise RejectedError("The supplied passkey was rejected.")

    @method("Cancel")
    def _cancel(self):  # type: ignore
        self._cancel_callback()
