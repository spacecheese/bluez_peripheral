from unittest import IsolatedAsyncioTestCase

from .util import *

from bluez_peripheral.util import *


class TestUtil(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._bus = await get_message_bus()
        await bluez_available_or_skip(self._bus)

        self._adapter = await get_first_adapter_or_skip(self._bus)

    async def asyncTearDown(self) -> None:
        self._bus.disconnect()

    async def test_get_first(self):
        if not len(await Adapter.get_all(self._bus)) > 0:
            with self.assertRaises(ValueError):
                Adapter.get_first(self._bus)
        else:
            assert type(await Adapter.get_first(self._bus)) == Adapter

    async def test_alias_set(self):
        await self._adapter.set_alias("Some test name")
        assert await self._adapter.get_alias() == "Some test name"

    async def test_alias_clear(self):
        await self._adapter.set_alias("")
        assert await self._adapter.get_alias() == await self._adapter.get_name()

    async def test_powered(self):
        initial_powered = await self._adapter.get_powered()

        await self._adapter.set_powered(False)
        assert await self._adapter.get_powered() == False
        await self._adapter.set_powered(True)
        assert await self._adapter.get_powered() == True
        await self._adapter.set_powered(initial_powered)
