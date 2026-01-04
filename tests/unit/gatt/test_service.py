import re
from typing import Collection

import pytest

from bluez_peripheral.gatt.service import Service, ServiceCollection

from ..util import ServiceNode


class MockService1(Service):
    def __init__(self, includes: Collection[Service]):
        super().__init__("180A", primary=False, includes=includes)


class MockService2(Service):
    def __init__(self):
        super().__init__("180B")


class MockService3(Service):
    def __init__(self):
        super().__init__("180C")


@pytest.fixture
def service1(service2, service3):
    return MockService1([service2, service3])


@pytest.fixture
def service2():
    return MockService2()


@pytest.fixture
def service3():
    return MockService3()


@pytest.fixture
def services(service1, service2, service3):
    return ServiceCollection([service1, service2, service3])


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

    children = await service_collection.get_children()
    child_names = [c.bus_path.split("/")[-1] for c in children.values()]
    child_names = sorted(child_names)

    assert len(child_names) == 3

    # Numbering may not have gaps.
    i = 0
    for name in child_names:
        assert re.match(r"^service0?" + str(i) + "$", name)
        i += 1


@pytest.mark.asyncio
async def test_include_modify(
    message_bus,
    service3,
    services,
    bus_name,
    bus_path,
    background_service,
):
    service_collection = await ServiceNode.from_service_collection(
        message_bus, bus_name, bus_path
    )
    service1_node = await service_collection.get_child("180A")
    service2_node = await service_collection.get_child("180B")
    service3_node = await service_collection.get_child("180C")

    includes = await service1_node.attr_interface.get_includes()
    assert set(includes) == set(
        [service1_node.bus_path, service2_node.bus_path, service3_node.bus_path]
    )

    background_service.unregister()
    services.remove_child(service3)
    background_service.register(services, bus_path)

    service_collection = await ServiceNode.from_service_collection(
        message_bus, bus_name, bus_path
    )
    service1_node = await service_collection.get_child("180A")
    service2_node = await service_collection.get_child("180B")

    includes = await service1_node.attr_interface.get_includes()
    assert set(includes) == set([service1_node.bus_path, service2_node.bus_path])

    with pytest.raises(KeyError):
        await service_collection.get_child("180C")

    background_service.unregister()
    services.add_child(service3)
    background_service.register(services, bus_path)

    service_collection = await ServiceNode.from_service_collection(
        message_bus, bus_name, bus_path
    )
    service1_node = await service_collection.get_child("180A")
    service2_node = await service_collection.get_child("180B")
    service3_node = await service_collection.get_child("180C")

    includes = await service1_node.attr_interface.get_includes()
    assert set(includes) == set(
        [service1_node.bus_path, service2_node.bus_path, service3_node.bus_path]
    )
