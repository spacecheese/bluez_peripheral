import asyncio
import re

import pytest
import pytest_asyncio

from dbus_fast import Variant

from bluez_peripheral.gatt.characteristic import (
    CharacteristicFlags,
    characteristic,
)
from bluez_peripheral.gatt.descriptor import descriptor, DescriptorFlags
from bluez_peripheral.gatt.service import Service, ServiceCollection

from ..util import ServiceNode


class MockService(Service):
    def __init__(self):
        super().__init__("180A")

    read_write_val = b"\x05"

    @characteristic("2A37", CharacteristicFlags.RELIABLE_WRITE)
    def some_char(self, _):
        return bytes("Some Other Test Message", "utf-8")

    @some_char.descriptor("2A38")
    def read_only_desc(self, opts):
        self.last_opts = opts
        return bytes("Test Message", "utf-8")

    @some_char.descriptor("3A38")
    async def async_read_only_desc(self, opts):
        self.last_opts = opts
        await asyncio.sleep(0.05)
        return bytes("Test Message", "utf-8")

    @descriptor("2A39", some_char, DescriptorFlags.WRITE)
    def write_desc(self, _):
        return bytes()

    @write_desc.setter
    def write_desc_set(self, val, opts):
        self.last_opts = opts
        self.write_desc_val = val

    @descriptor("3A39", some_char, DescriptorFlags.WRITE)
    async def async_write_desc(self, _):
        return bytes()

    @async_write_desc.setter
    async def async_write_desc_set(self, val, opts):
        self.last_opts = opts
        await asyncio.sleep(0.05)
        self.async_write_desc_val = val

    @descriptor("3A33", some_char, DescriptorFlags.WRITE | DescriptorFlags.READ)
    def read_write_desc(self, opts):
        return self.read_write_val

    @read_write_desc.setter
    def read_write_desc(self, val, opts):
        self.read_write_val = val


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
    char = await service.get_child("2A37")
    descs = await char.get_children()

    child_names = [c.bus_path.split("/")[-1] for c in descs.values()]
    child_names.sort()

    assert len(child_names) == 5

    i = 0
    # Numbering may not have gaps.
    for name in child_names:
        assert re.match(r"^desc0{0,2}" + str(i) + "$", name)
        i += 1


@pytest.mark.asyncio
async def test_read(
    message_bus, service, background_service, bus_name, bus_path
):
    opts = {
        "offset": Variant("q", 0),
        "link": Variant("s", "dododo"),
        "device": Variant("s", "bebealbl/.afal"),
    }

    service_collection = await ServiceNode.from_service_collection(
        message_bus, bus_name, bus_path
    )
    desc = await service_collection.get_child("180A", "2A37", "2A38")
    resp = await desc.attr_interface.call_read_value(opts)

    assert resp.decode("utf-8") == "Test Message"
    assert service.last_opts.offset == 0
    assert service.last_opts.link == "dododo"
    assert service.last_opts.device == "bebealbl/.afal"

    desc = await service_collection.get_child("180A", "2A37", "3A38")
    resp = await desc.attr_interface.call_read_value(opts)

    assert resp.decode("utf-8") == "Test Message"


@pytest.mark.asyncio
async def test_write(
    message_bus, service, background_service, bus_name, bus_path
):
    opts = {
        "offset": Variant("q", 1),
        "device": Variant("s", "bebealbl/.afal"),
        "link": Variant("s", "gogog"),
        "prepare-authorize": Variant("b", True),
    }

    service_collection = await ServiceNode.from_service_collection(
        message_bus, bus_name, bus_path
    )
    desc = await service_collection.get_child("180A", "2A37", "2A39")
    await desc.attr_interface.call_write_value(bytes("Test Write Value", "utf-8"), opts)

    assert service.last_opts.offset == 1
    assert service.last_opts.device == "bebealbl/.afal"
    assert service.last_opts.link == "gogog"
    assert service.last_opts.prepare_authorize == True

    assert service.write_desc_val.decode("utf-8") == "Test Write Value"

    desc = await service_collection.get_child("180A", "2A37", "3A39")
    await desc.attr_interface.call_write_value(bytes("Test Write Value", "utf-8"), opts)

    assert service.async_write_desc_val.decode("utf-8") == "Test Write Value"


@pytest.mark.asyncio
async def test_empty_opts(
    message_bus, service, background_service, bus_name, bus_path
):
    service_collection = await ServiceNode.from_service_collection(
        message_bus, bus_name, bus_path
    )
    desc = await service_collection.get_child("180A", "2A37", "3A33")
    resp = await desc.attr_interface.call_read_value({})
    assert resp == b"\x05"
    await desc.attr_interface.call_write_value(bytes("Test Write Value", "utf-8"), {})
    resp = await desc.attr_interface.call_read_value({})
    assert resp == bytes("Test Write Value", "utf-8")
