from bluez_peripheral.gatt.descriptor import descriptor
from unittest import IsolatedAsyncioTestCase
from threading import Event
from ..util import *
import re

from bluez_peripheral.util import get_message_bus
from bluez_peripheral.gatt.characteristic import (
    CharacteristicFlags,
    CharacteristicWriteType,
    characteristic,
)
from bluez_peripheral.gatt.service import Service

last_opts = None
write_notify_char_val = None


class TestService(Service):
    def __init__(self):
        super().__init__("180A")

    @characteristic("2A37", CharacteristicFlags.READ)
    def read_only_char(self, opts):
        global last_opts
        last_opts = opts
        return bytes("Test Message", "utf-8")

    # Not testing other characteristic flags since their functionality is handled by bluez.
    @characteristic("2A38", CharacteristicFlags.NOTIFY | CharacteristicFlags.WRITE)
    def write_notify_char(self, _):
        pass

    @write_notify_char.setter
    def write_notify_char(self, val, opts):
        global last_opts
        last_opts = opts
        global write_notify_char_val
        write_notify_char_val = val


class TestCharacteristic(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self._client_bus = await get_message_bus()
        self._bus_manager = BusManager()
        self._path = "/com/spacecheese/bluez_peripheral/test_characteristic"

    async def asyncTearDown(self):
        self._client_bus.disconnect()
        self._bus_manager.close()

    async def test_structure(self):
        async def inspector(path):
            service = await get_attrib(
                self._client_bus, self._bus_manager.name, path, "180A"
            )

            child_names = [path.split("/")[-1] for path in service.child_paths]
            child_names = sorted(child_names)

            i = 0
            # Characteristic numbering can't have gaps.
            for name in child_names:
                assert re.match(r"^char0{0,3}" + str(i) + "$", name)
                i += 1

        service = TestService()
        adapter = MockAdapter(inspector)

        await service.register(self._bus_manager.bus, self._path, adapter)

    async def test_read(self):
        async def inspector(path):
            global last_opts
            opts = {
                "offset": Variant("q", 0),
                "mtu": Variant("q", 128),
                "device": Variant("s", "blablabla/.hmm"),
            }
            interface = (
                await get_attrib(
                    self._client_bus,
                    self._bus_manager.name,
                    path,
                    "180A",
                    char_uuid="2A37",
                )
            ).get_interface("org.bluez.GattCharacteristic1")
            resp = await interface.call_read_value(opts)
            cache = await interface.get_value()

            assert resp.decode("utf-8") == "Test Message"
            assert last_opts.offset == 0
            assert last_opts.mtu == 128
            assert last_opts.device == "blablabla/.hmm"
            assert cache == resp

        service = TestService()
        adapter = MockAdapter(inspector)

        await service.register(self._bus_manager.bus, self._path, adapter)

    async def test_write(self):
        async def inspector(path):
            global last_opts
            opts = {
                "offset": Variant("q", 10),
                "type": Variant("s", "request"),
                "mtu": Variant("q", 128),
                "device": Variant("s", "blablabla/.hmm"),
                "link": Variant("s", "yuyuyuy"),
                "prepare-authorize": Variant("b", False),
            }
            interface = (
                await get_attrib(
                    self._client_bus,
                    self._bus_manager.name,
                    path,
                    "180A",
                    char_uuid="2A38",
                )
            ).get_interface("org.bluez.GattCharacteristic1")
            await interface.call_write_value(bytes("Test Write Value", "utf-8"), opts)

            assert last_opts.offset == 10
            assert last_opts.type == CharacteristicWriteType.REQUEST
            assert last_opts.mtu == 128
            assert last_opts.device == "blablabla/.hmm"
            assert last_opts.link == "yuyuyuy"
            assert last_opts.prepare_authorize == False

            assert write_notify_char_val.decode("utf-8") == "Test Write Value"

        service = TestService()
        adapter = MockAdapter(inspector)

        await service.register(self._bus_manager.bus, self._path, adapter)

    async def test_notify_no_start(self):
        property_changed = Event()

        async def inspector(path):
            interface = (
                await get_attrib(
                    self._client_bus,
                    self._bus_manager.name,
                    path,
                    "180A",
                    char_uuid="2A38",
                )
            ).get_interface("org.freedesktop.DBus.Properties")

            def on_properties_changed(_0, _1, _2):
                property_changed.set()

            interface.on_properties_changed(on_properties_changed)

        service = TestService()
        adapter = MockAdapter(inspector)

        await service.register(self._bus_manager.bus, self._path, adapter)
        service.write_notify_char.changed(bytes("Test Notify Value", "utf-8"))

        # Expect a timeout since start notify has not been called.
        if property_changed.wait(timeout=0.1):
            raise Exception(
                "The characteristic signalled a notification before StartNotify() was called."
            )

    async def test_notify_start(self):
        property_changed = Event()

        async def inspector(path):
            proxy = await get_attrib(
                self._client_bus,
                self._bus_manager.name,
                path,
                "180A",
                char_uuid="2A38",
            )
            properties_interface = proxy.get_interface(
                "org.freedesktop.DBus.Properties"
            )
            char_interface = proxy.get_interface("org.bluez.GattCharacteristic1")

            def on_properties_changed(interface, values, invalid_props):
                assert interface == "org.bluez.GattCharacteristic1"
                assert len(values) == 1
                assert values["Value"].value.decode("utf-8") == "Test Notify Value"
                property_changed.set()
                

            properties_interface.on_properties_changed(on_properties_changed)
            await char_interface.call_start_notify()

        service = TestService()
        adapter = MockAdapter(inspector)

        await service.register(self._bus_manager.bus, self._path, adapter)
        service.write_notify_char.changed(bytes("Test Notify Value", "utf-8"))

        await asyncio.sleep(0.01)

        # Block until the properties changed notification propagates.
        if not property_changed.wait(timeout=0.1):
            raise TimeoutError(
                "The characteristic did not send a notification in time."
            )

    async def test_notify_stop(self):
        property_changed = Event()

        async def inspector(path):
            proxy = await get_attrib(
                self._client_bus,
                self._bus_manager.name,
                path,
                "180A",
                char_uuid="2A38",
            )
            property_interface = proxy.get_interface("org.freedesktop.DBus.Properties")
            char_interface = proxy.get_interface("org.bluez.GattCharacteristic1")

            def on_properties_changed(_0, _1, _2):
                property_changed.set()

            property_interface.on_properties_changed(on_properties_changed)

            await char_interface.call_start_notify()
            await char_interface.call_stop_notify()

        service = TestService()
        adapter = MockAdapter(inspector)

        await service.register(self._bus_manager.bus, self._path, adapter)
        service.write_notify_char.changed(bytes("Test Notify Value", "utf-8"))

        # Expect a timeout since start notify has not been called.
        if property_changed.wait(timeout=0.01):
            raise Exception(
                "The characteristic signalled a notification before after StopNotify() was called."
            )

    async def test_modify(self):
        service = TestService()

        @descriptor("2D56", service.write_notify_char)
        def some_desc(service, opts):
            return bytes("Some Test Value", "utf-8")

        global expect_descriptor
        expect_descriptor = True

        async def inspector(path):
            global expect_descriptor

            opts = {
                "offset": Variant("q", 0),
                "mtu": Variant("q", 128),
                "device": Variant("s", "blablabla/.hmm"),
            }

            if expect_descriptor:
                proxy = await get_attrib(
                    self._client_bus,
                    self._bus_manager.name,
                    path,
                    "180A",
                    "2A38",
                    "2D56",
                )
                desc = proxy.get_interface("org.bluez.GattDescriptor1")
                assert (await desc.call_read_value(opts)).decode(
                    "utf-8"
                ) == "Some Test Value"
            else:
                try:
                    await get_attrib(
                        self._client_bus,
                        self._bus_manager.name,
                        path,
                        "180A",
                        "2A38",
                        "2D56",
                    )
                except ValueError:
                    pass
                else:
                    self.fail("The descriptor was not properly removed.")

        adapter = MockAdapter(inspector)

        await service.register(self._bus_manager.bus, self._path, adapter=adapter)
        self.assertRaises(
            ValueError, service.write_notify_char.remove_descriptor, some_desc
        )

        await service.unregister()
        service.write_notify_char.remove_descriptor(some_desc)
        expect_descriptor = False

        await service.register(self._bus_manager.bus, self._path, adapter=adapter)
        self.assertRaises(
            ValueError, service.write_notify_char.add_descriptor, some_desc
        )
        await service.unregister()
        await service.register(self._bus_manager.bus, self._path, adapter=adapter)
