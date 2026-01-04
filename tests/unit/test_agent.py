import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from bluez_peripheral.agent import AgentCapability, BaseAgent

from .util import make_message_bus_mock


@pytest.mark.asyncio
async def test_base_agent_capability():
    mock_bus = make_message_bus_mock()
    mock_proxy = mock_bus.get_proxy_object.return_value
    mock_interface = mock_proxy.get_interface.return_value
    bus_path = "/com/spacecheese/bluez_peripheral/agent0"

    agent = BaseAgent(AgentCapability.KEYBOARD_DISPLAY)

    await agent.register(mock_bus, path=bus_path)
    mock_interface.call_register_agent.assert_awaited_once_with(
        bus_path, "KeyboardDisplay"
    )
    await agent.unregister()

    mock_bus.reset_mock()
    agent = BaseAgent(AgentCapability.NO_INPUT_NO_OUTPUT)

    await agent.register(mock_bus, path=bus_path, default=True)
    mock_interface.call_register_agent.assert_awaited_once_with(
        bus_path, "NoInputNoOutput"
    )
    mock_interface.call_request_default_agent.assert_awaited_once_with(bus_path)
    await agent.unregister()

    mock_interface.call_unregister_agent.assert_awaited_once_with(bus_path)
