import pytest_asyncio

from .util import BackgroundServiceManager


@pytest_asyncio.fixture
async def background_service(services, bus_name, bus_path):
    manager = BackgroundServiceManager()
    await manager.start(bus_name)
    manager.register(services, bus_path)

    yield manager

    manager.unregister()
    await manager.stop()
