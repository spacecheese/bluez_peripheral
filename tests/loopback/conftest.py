import pytest_asyncio

from dbus_fast.service import dbus_method

from bluez_peripheral.adapter import Adapter
from bluez_peripheral.agent import AgentCapability, BaseAgent


class TrivialAgent(BaseAgent):
    @dbus_method("Cancel")
    def _cancel(self):  # type: ignore
        return

    @dbus_method("Release")
    def _release(self):  # type: ignore
        return

    @dbus_method("RequestPinCode")
    def _request_pin_code(self, device: "o") -> "s":  # type: ignore
        return "0000"

    @dbus_method("DisplayPinCode")
    def _display_pin_code(self, device: "o", pincode: "s"):  # type: ignore
        return

    @dbus_method("RequestPasskey")
    def _request_passkey(self, device: "o") -> "u":  # type: ignore
        return 0

    @dbus_method("DisplayPasskey")
    def _display_passkey(self, device: "o", passkey: "u", entered: "q"):  # type: ignore
        return

    @dbus_method("RequestConfirmation")
    def _request_confirmation(self, device: "o", passkey: "u"):  # type: ignore
        return

    @dbus_method("RequestAuthorization")
    def _request_authorization(self, device: "o"):  # type: ignore
        return

    @dbus_method("AuthorizeService")
    def _authorize_service(self, device: "o", uuid: "s"):  # type: ignore
        return


@pytest_asyncio.fixture
async def unpaired_adapters(message_bus):
    adapters = await Adapter.get_all(message_bus)

    adapter0 = None
    adapter1 = None

    for adapter in adapters:
        addr = await adapter.get_address()
        if addr == "00:AA:01:00:00:00":
            adapter0 = adapter
        elif addr == "00:AA:01:01:00:01":
            adapter1 = adapter

    assert adapter0 is not None
    assert adapter1 is not None

    for adapter in [adapter0, adapter1]:
        for device in await adapter.get_devices():
            if await device.get_paired():
                await device.remove(adapters[1])

    yield adapter0, adapter1


@pytest_asyncio.fixture
async def paired_adapters(message_bus, unpaired_adapters):
    adapters = unpaired_adapters

    agent = TrivialAgent(AgentCapability.KEYBOARD_DISPLAY)
    await agent.register(message_bus)

    await adapters[0].set_powered(True)
    await adapters[0].set_discoverable(True)
    await adapters[0].set_pairable(True)

    await adapters[1].set_powered(True)
    await adapters[1].start_discovery()
    devices = await adapters[1].get_devices()
    assert len(devices) == 1
    devices[0].pair()

    yield adapters

    devices[0].remove()

    await agent.unregister()
