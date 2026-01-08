import pytest
import pytest_asyncio

from .util import (
    BackgroundServiceManager,
    BackgroundBusManager,
    BackgroundAdvertManager,
)


@pytest_asyncio.fixture
async def background_bus_manager(bus_name):
    bus_manager = BackgroundBusManager()
    await bus_manager.start(bus_name)
    yield bus_manager
    await bus_manager.stop()


@pytest.fixture
def background_service(background_bus_manager):
    def _background_service(services, **kwargs):
        background_service = BackgroundServiceManager(background_bus_manager)
        background_service.register(services, **kwargs)
        return background_service

    return _background_service


@pytest.fixture
def background_advert(background_bus_manager):
    def _background_advert(advert, **kwargs):
        background_advert = BackgroundAdvertManager(background_bus_manager)
        background_advert.register(advert, **kwargs)
        return background_advert

    return _background_advert
