from dbus_next.service import ServiceInterface, method
from dbus_next.aio import MessageBus
from dbus_next import DBusError

from typing import Awaitable, Callable
from enum import Enum

from .util import *


class AgentCapability(Enum):
    KEYBOARD_DISPLAY = 0
    """Device can use any pairing method.
    """
    DISPLAY_ONLY = 1
    """Device can display a pairing code.
    """
    DISPLAY_YES_NO = 2
    """Device can display and read the response to a yes/ no pairing prompt.
    """
    KEYBOARD_ONLY = 3
    """Device has no output but can be used to enter a pairing code.
    """
    NO_INPUT_NO_OUTPUT = 4
    """Device has no input/ output capabilities and therefore cannot support MITM protection.
    """


class BaseAgent(ServiceInterface):
    _INTERFACE = "org.bluez.Agent1"
    _MANAGER_INTERFACE = "org.bluez.AgentManager1"
    """The base agent for all bluez agents.
    """

    def __init__(
        self,
        capability: AgentCapability,
    ):
        """Instance a BaseAgent. You probably should only do this with a subclass.

        Args:
            capability (AgentCapability): The IO capabilities of the agent.
        """
        self._capability = capability

        self._path = None
        super().__init__(self._INTERFACE)

    @method()
    def Release(self):  # type: ignore
        pass

    @method()
    def Cancel(self):  # type: ignore
        pass

    def _get_capability(self):
        return _snake_to_pascal(self._capability.name)

    async def _get_manager_interface(self, bus: MessageBus):
        introspection = await bus.introspect("org.bluez", "/org/bluez")
        proxy = bus.get_proxy_object("org.bluez", "/org/bluez", introspection)
        return proxy.get_interface(self._MANAGER_INTERFACE)

    async def register(
        self, bus: MessageBus, default: bool = True, path: str = "/com/spacecheese/ble"
    ):
        """Expose this agent on the specified message bus and register it with the bluez agent manager.

        Args:
            bus (MessageBus): The message bus to expose the agent using.
            default (bool, optional): Whether or not the agent should be registered as default.
            Non-default agents will not be called to respond to incoming pairing requests.
            The caller requires superuser if this is true. Defaults to True.
            path (str, optional): The path to expose this message bus on. Defaults to "/com/spacecheese/ble".
        """
        self._path = path
        bus.export(path, self)

        interface = await self._get_manager_interface(bus)
        test = self._get_capability()
        await interface.call_register_agent(path, test)

        if default:
            await interface.call_request_default_agent(self._path)

    async def unregister(self, bus: MessageBus):
        interface = await self._get_manager_interface(bus)
        await interface.call_unregister_agent(self._path)

        bus.unexport(self._path, self._INTERFACE)


class TestAgent(BaseAgent):
    def __init__(self, capability: AgentCapability):
        """A testing agent that invokes the debugger whenever a method is called. Use this for debugging only.

        Args:
            capability (AgentCapability): The IO capability of the agent.
        """
        super().__init__(capability)

    @method()
    def Cancel():  # type: ignore
        breakpoint()
        pass

    @method()
    def Release():  # type: ignore
        breakpoint()
        pass

    @method()
    def RequestPinCode(self, device: "o") -> "s":  # type: ignore
        breakpoint()
        pass

    @method()
    def DisplayPinCode(self, device: "o", pincode: "s"):  # type: ignore
        breakpoint()
        pass

    @method()
    def RequestPasskey(self, device: "o") -> "u":  # type: ignore
        breakpoint()
        pass

    @method()
    def DisplayPasskey(self, device: "o", passkey: "u", entered: "q"):  # type: ignore
        breakpoint()
        pass

    @method()
    def RequestConfirmation(self, device: "o", passkey: "u"):  # type: ignore
        breakpoint()
        pass

    @method()
    def RequestAuthorization(self, device: "o"):  # type: ignore
        breakpoint()
        pass

    @method()
    def AuthorizeService(self, device: "o", uuid: "s"):  # type: ignore
        breakpoint()
        pass


class NoIoAgent(BaseAgent):
    def __init__(self):
        """An agent with no input or output capabilities. All incoming pairing requests from all devices will be accepted."""
        super().__init__(AgentCapability.NO_INPUT_NO_OUTPUT)

    @method()
    def RequestAuthorization(self, device: "o"):  # type: ignore
        pass

    @method()
    def AuthorizeService(self, device: "o", uuid: "s"):  # type: ignore
        pass


class YesNoAgent(BaseAgent):
    def __init__(
        self, request_confirmation: Callable[[int], Awaitable[bool]], cancel: Callable
    ):
        """An agent that uses a callback to display a yes/ no prompt in response to an incoming pairing request.

        Args:
            request_confirmation (Callable[[int], Awaitable[bool]]): The callback called when a pairing request is recived.
            This should return true if the user indicates that the supplied passcode is correct or false otherwise.
            cancel (Callable): The callback called when a pairing request is cancelled remotely.
        """
        self._request_confirmation = request_confirmation
        self._cancel = cancel

        super().__init__(AgentCapability.DISPLAY_YES_NO)

    @method()
    async def RequestConfirmation(self, device: "o", passkey: "u"):  # type: ignore
        if not await self._request_confirmation(passkey):
            raise DBusError(
                "org.bluez.Error.Rejected", "The supplied passkey was rejected."
            )

    @method()
    def Cancel(self):  # type: ignore
        self._cancel()
