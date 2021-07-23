from unittest import IsolatedAsyncioTestCase

from .util import *

from bluez_peripheral.util import get_message_bus
from bluez_peripheral.agent import AgentCapability, BaseAgent


class MockBus:
    async def introspect(self, name, path):
        return self

    def get_proxy_object(self, object, path, intro):
        return self

    def get_interface(self, int):
        return self

    def export(self, path, obj):
        self._path = path
        return self

    async def call_register_agent(self, path, capability):
        assert path == path
        self._capability = capability
        return self

    async def call_request_default_agent(self, path):
        assert path == path


class TestAgent(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self._bus_manager = BusManager()
        self._client_bus = await get_message_bus()

    async def asyncTearDown(self):
        self._client_bus.disconnect()
        self._bus_manager.close()

    async def test_base_agent_capability(self):
        agent = BaseAgent(AgentCapability.KEYBOARD_DISPLAY)
        bus = MockBus()
        await agent.register(bus)
        assert bus._capability == "KeyboardDisplay"

        agent = BaseAgent(AgentCapability.NO_INPUT_NO_OUTPUT)
        bus = MockBus()
        await agent.register(bus)
        assert bus._capability == "NoInputNoOutput"
