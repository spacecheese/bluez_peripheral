import asyncio
import re

import pytest

from dbus_fast import Variant

from bluez_peripheral.gatt.characteristic import (
    CharacteristicFlags,
    CharacteristicWriteType,
    characteristic,
)
from bluez_peripheral.gatt.descriptor import descriptor
from bluez_peripheral.gatt.service import Service, ServiceCollection

from ..util import ServiceNode
from ...conftest import requires_adapter


class MockService(Service):
    def __init__(self):
        super().__init__("180A")

    @characteristic("2A37", CharacteristicFlags.READ)
    def read_only_char(self, opts):
        self.last_opts = opts
        return bytes("Test Message", "utf-8")

    @characteristic("3A37", CharacteristicFlags.READ)
    async def async_read_only_char(self, opts):
        self.last_opts = opts
        return bytes("Test Message", "utf-8")

    # Not testing other characteristic flags since their functionality is handled by bluez.
    @characteristic("2A38", CharacteristicFlags.NOTIFY | CharacteristicFlags.WRITE)
    def write_notify_char(self, _):
        raise NotImplementedError()

    @write_notify_char.setter
    def write_notify_char(self, val, opts):
        self.last_opts = opts
        self.val = val

    @characteristic("3A38", CharacteristicFlags.WRITE)
    async def aysnc_write_only_char(self, _):
        raise NotImplementedError()

    @aysnc_write_only_char.setter
    async def aysnc_write_only_char(self, val, opts):
        self.last_opts = opts
        self.val = val

    @characteristic("3A33", CharacteristicFlags.WRITE | CharacteristicFlags.READ)
    def read_write_char(self, opts):
        self.last_opts = opts
        return self.val

    @read_write_char.setter
    def read_write_char(self, val, opts):
        self.last_opts = opts
        self.val = val


@pytest.fixture
def service():
    return MockService()


@pytest.fixture
def services(service):
    return ServiceCollection([service])


@pytest.fixture
def bus_name():
    return "com.spacecheese.test"


@pytest.fixture
def bus_path():
    return "/com/spacecheese/bluez_peripheral/test"


@pytest.mark.asyncio
async def test_structure(message_bus, background_service, bus_name, bus_path):
    service_collection = await ServiceNode.from_service_collection(
        message_bus, bus_name, bus_path
    )
    service = await service_collection.get_child("180A")
    char = await service.get_children()

    child_names = [c.bus_path.split("/")[-1] for c in char.values()]
    child_names.sort()

    assert len(child_names) == 5

    i = 0
    # Numbering may not have gaps.
    for name in child_names:
        assert re.match(r"^char0{0,3}" + str(i) + "$", name)
        i += 1


@pytest.mark.asyncio
async def test_read(message_bus, service, background_service, bus_name, bus_path):
    opts = {
        "offset": Variant("q", 0),
        "mtu": Variant("q", 128),
        "device": Variant("s", "blablabla/.hmm"),
    }

    service_collection = await ServiceNode.from_service_collection(
        message_bus, bus_name, bus_path
    )
    char = await service_collection.get_child("180A", "2A37")
    resp = await char.attr_interface.call_read_value(opts)
    cache = await char.attr_interface.get_value()

    assert resp.decode("utf-8") == "Test Message"
    assert service.last_opts.offset == 0
    assert service.last_opts.mtu == 128
    assert service.last_opts.device == "blablabla/.hmm"
    assert cache == resp

    char = await service_collection.get_child("180A", "3A37")
    resp = await char.attr_interface.call_read_value(opts)
    cache = await char.attr_interface.get_value()

    assert resp.decode("utf-8") == "Test Message"
    assert cache == resp


@pytest.mark.asyncio
async def test_write(message_bus, service, background_service, bus_name, bus_path):
    opts = {
        "offset": Variant("q", 10),
        "type": Variant("s", "request"),
        "mtu": Variant("q", 128),
        "device": Variant("s", "blablabla/.hmm"),
        "link": Variant("s", "yuyuyuy"),
        "prepare-authorize": Variant("b", False),
    }

    service_collection = await ServiceNode.from_service_collection(
        message_bus, bus_name, bus_path
    )
    char = await service_collection.get_child("180A", "2A38")
    await char.attr_interface.call_write_value(bytes("Test Write Value", "utf-8"), opts)

    assert service.last_opts.offset == 10
    assert service.last_opts.type == CharacteristicWriteType.REQUEST
    assert service.last_opts.mtu == 128
    assert service.last_opts.device == "blablabla/.hmm"
    assert service.last_opts.link == "yuyuyuy"
    assert not service.last_opts.prepare_authorize

    assert service.val.decode("utf-8") == "Test Write Value"

    char = await service_collection.get_child("180A", "3A38")
    await char.attr_interface.call_write_value(bytes("Test Write Value", "utf-8"), opts)

    assert service.val.decode("utf-8") == "Test Write Value"


@pytest.mark.asyncio
async def test_notify_no_start(
    message_bus, service, background_service, bus_name, bus_path
):
    service_collection = await ServiceNode.from_service_collection(
        message_bus, bus_name, bus_path
    )
    char = await service_collection.get_child("180A", "2A38")
    prop_interface = char.proxy.get_interface("org.freedesktop.DBus.Properties")

    foreground_loop = asyncio.get_running_loop()
    properties_changed = foreground_loop.create_future()

    def on_properties_changed(_0, _1, _2):
        properties_changed.set()

    prop_interface.on_properties_changed(on_properties_changed)
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(properties_changed, timeout=0.1)


@pytest.mark.asyncio
async def test_notify_start_stop(
    message_bus, service, background_service, bus_name, bus_path
):
    service_collection = await ServiceNode.from_service_collection(
        message_bus, bus_name, bus_path
    )
    char = await service_collection.get_child("180A", "2A38")
    properties_interface = char.proxy.get_interface("org.freedesktop.DBus.Properties")

    foreground_loop = asyncio.get_running_loop()
    properties_changed = foreground_loop.create_future()

    def _good_on_properties_changed(interface, values, invalid_props):
        assert interface == "org.bluez.GattCharacteristic1"
        assert len(values) == 1
        assert values["Value"].value.decode("utf-8") == "Test Notify Value"
        foreground_loop.call_soon_threadsafe(properties_changed.set_result, ())

    properties_interface.on_properties_changed(_good_on_properties_changed)
    await char.attr_interface.call_start_notify()

    service.write_notify_char.changed(bytes("Test Notify Value", "utf-8"))
    await asyncio.wait_for(properties_changed, timeout=0.1)

    properties_changed = foreground_loop.create_future()

    def _bad_on_properties_changed(interface, values, invalid_props):
        ex = AssertionError(
            "on_properties_changed triggered after call_stop_notify called"
        )
        foreground_loop.call_soon_threadsafe(properties_changed.set_exception, (ex))

    properties_interface.on_properties_changed(_bad_on_properties_changed)
    await char.attr_interface.call_stop_notify()

    service.write_notify_char.changed(bytes("Test Notify Value", "utf-8"))
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(properties_changed, timeout=0.1)


@pytest.mark.asyncio
async def test_modify(
    message_bus, service, services, background_service, bus_name, bus_path
):
    opts = {
        "offset": Variant("q", 0),
        "mtu": Variant("q", 128),
        "device": Variant("s", "blablabla/.hmm"),
    }

    service_collection = await ServiceNode.from_service_collection(
        message_bus, bus_name, bus_path
    )

    with pytest.raises(KeyError):
        await service_collection.get_child("180A", "2A38", "2D56")

    background_service.unregister()

    @descriptor("2D56", service.write_notify_char)
    def some_desc(service, opts):
        return bytes("Some Test Value", "utf-8")

    background_service.register(services, bus_path)
    desc = await service_collection.get_child("180A", "2A38", "2D56")
    resp = await desc.attr_interface.call_read_value(opts)
    assert resp.decode("utf-8") == "Some Test Value"

    background_service.unregister()
    service.write_notify_char.remove_child(some_desc)

    background_service.register(services, bus_path)
    with pytest.raises(KeyError):
        await service_collection.get_child("180A", "2A38", "2D56")


@pytest.mark.asyncio
@requires_adapter
async def test_bluez(message_bus, adapter, services):
    initial_powered = await adapter.get_powered()
    initial_discoverable = await adapter.get_discoverable()

    await adapter.set_powered(True)
    await adapter.set_discoverable(True)

    try:
        await services.register(message_bus, adapter=adapter)
    finally:
        await services.unregister()

        await adapter.set_discoverable(initial_discoverable)
        await adapter.set_powered(initial_powered)
