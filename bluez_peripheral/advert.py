from typing import Collection, Dict, Callable, Optional, Union, List, Tuple
import struct
from uuid import UUID

from dbus_fast import Variant
from dbus_fast.constants import PropertyAccess
from dbus_fast.service import ServiceInterface, method, dbus_property
from dbus_fast.aio.message_bus import MessageBus

from .uuid16 import UUID16, UUIDCompatible
from .util import _snake_to_kebab
from .adapter import Adapter
from .types import AdvertisingIncludes
from .types import AdvertisingPacketType


class Advertisement(ServiceInterface):
    """
    An advertisement for a particular service or collection of services that can be registered and broadcast to nearby devices.

    Args:
        localName: The device name to advertise.
        serviceUUIDs: A list of service UUIDs advertise.
        appearance: The appearance value to advertise.
            See the `Bluetooth SIG Assigned Numbers <https://www.bluetooth.com/specifications/assigned-numbers/>`_ (Search for "Appearance Values")
        timeout: The time from registration until this advert is removed (defaults to zero meaning never timeout).
        discoverable: Whether or not the device this advert should be generally discoverable.
        packetType: The type of advertising packet requested.
        manufacturerData: Any manufacturer specific data to include in the advert.
        solicitUUIDs: Array of service UUIDs to attempt to solicit (not widely used).
        serviceData: Any service data elements to include.
        includes: Fields that can be optionally included in the advertising packet.
            Only the :class:`bluez_peripheral.flags.AdvertisingIncludes.TX_POWER` flag seems to work correctly with bluez.
        duration: Duration of the advert when multiple adverts are ongoing.
        releaseCallback: A function to call when the advert release function is called.
    """

    _INTERFACE = "org.bluez.LEAdvertisement1"
    _MANAGER_INTERFACE = "org.bluez.LEAdvertisingManager1"

    _defaultPathAdvertCount = 0

    def __init__(
        self,
        local_name: str,
        service_uuids: Collection[UUIDCompatible],
        *,
        appearance: Union[int, bytes],
        timeout: int = 0,
        discoverable: bool = True,
        packet_type: AdvertisingPacketType = AdvertisingPacketType.PERIPHERAL,
        manufacturer_data: Optional[Dict[int, bytes]] = None,
        solicit_uuids: Optional[Collection[UUIDCompatible]] = None,
        service_data: Optional[List[Tuple[UUIDCompatible, bytes]]] = None,
        includes: AdvertisingIncludes = AdvertisingIncludes.NONE,
        duration: int = 2,
        release_callback: Optional[Callable[[], None]] = None,
    ):
        self._type = packet_type
        # Convert any string uuids to uuid16.
        self._service_uuids = [UUID16.parse_uuid(uuid) for uuid in service_uuids]
        self._local_name = local_name
        # Convert the appearance to a uint16 if it isn't already an int.
        if isinstance(appearance, bytes):
            self._appearance = struct.unpack("H", appearance)[0]
        else:
            self._appearance = appearance
        self._timeout = timeout

        if manufacturer_data is None:
            manufacturer_data = {}
        self._manufacturer_data = {}
        for key, value in manufacturer_data.items():
            self._manufacturer_data[key] = Variant("ay", value)

        if solicit_uuids is None:
            solicit_uuids = []
        self._solicit_uuids = [UUID16.parse_uuid(uuid) for uuid in solicit_uuids]

        if service_data is None:
            service_data = []
        self._service_data: List[Tuple[UUID16 | UUID, Variant]] = []
        for i, dat in service_data:
            self._service_data.append((UUID16.parse_uuid(i), Variant("ay", dat)))

        self._discoverable = discoverable
        self._includes = includes
        self._duration = duration
        self._release_callback = release_callback

        self._export_bus: Optional[MessageBus] = None
        self._export_path: Optional[str] = None

        self._exportBus: Optional[MessageBus] = None
        self._exportPath: Optional[str] = None
        self._adapter: Optional[Adapter] = None

        super().__init__(self._INTERFACE)

    async def register(
        self,
        bus: MessageBus,
        adapter: Optional[Adapter] = None,
        path: Optional[str] = None,
    ) -> None:
        """Register this advert with bluez to start advertising.

        Args:
            bus: The message bus used to communicate with bluez.
            adapter: The adapter to use.
            path: The dbus path to use for registration.
        """
        # Generate a unique path name for this advert if one isn't already given.
        if path is None:
            path = "/com/spacecheese/bluez_peripheral/advert" + str(
                Advertisement._defaultPathAdvertCount
            )
            Advertisement._defaultPathAdvertCount += 1

        self._export_bus = bus
        self._export_path = path

        # Export this advert to the dbus.
        bus.export(path, self)

        if adapter is None:
            adapter = await Adapter.get_first(bus)

        self._adapter = adapter

        # Get the LEAdvertisingManager1 interface for the target adapter.
        interface = adapter._proxy.get_interface(self._MANAGER_INTERFACE)
        await interface.call_register_advertisement(path, {})  # type: ignore

    @method("Release")
    def _release(self):  # type: ignore
        assert self._export_bus is not None
        assert self._export_path is not None
        self._export_bus.unexport(self._export_path, self._INTERFACE)

    async def unregister(self):
        """
        Unregister this advertisement from bluez to stop advertising.
        """
        if not self._exportBus or not self._adapter or not self._exportPath:
            return

        interface = self._adapter._proxy.get_interface(self._MANAGER_INTERFACE)

        await interface.call_unregister_advertisement(self._exportPath)
        self._exportBus = None
        self._adapter = None
        self._exportPath = None

        if self.releaseCallback is not None:
            self.releaseCallback()

    @dbus_property(PropertyAccess.READ, "Type")
    def _get_type(self) -> "s":  # type: ignore
        return self._type.name.lower()

    @dbus_property(PropertyAccess.READ, "ServiceUUIDs")
    def _get_service_uuids(self) -> "as":  # type: ignore
        return [str(id) for id in self._service_uuids]

    @dbus_property(PropertyAccess.READ, "LocalName")
    def _get_local_name(self) -> "s":  # type: ignore
        return self._local_name

    @dbus_property(PropertyAccess.READ, "Appearance")
    def _get_appearance(self) -> "q":  # type: ignore
        return self._appearance

    @dbus_property(PropertyAccess.READ, "Timeout")
    def _get_timeout(self) -> "q":  # type: ignore
        return self._timeout

    @dbus_property(PropertyAccess.READ, "ManufacturerData")
    def _get_manufacturer_data(self) -> "a{qv}":  # type: ignore
        return self._manufacturer_data

    @dbus_property(PropertyAccess.READ, "SolicitUUIDs")
    def _get_solicit_uuids(self) -> "as":  # type: ignore
        return [str(key) for key in self._solicit_uuids]

    @dbus_property(PropertyAccess.READ, "ServiceData")
    def _get_service_data(self) -> "a{sv}":  # type: ignore
        return dict((str(key), val) for key, val in self._service_data)

    @dbus_property(PropertyAccess.READ, "Discoverable")
    def _get_discoverable(self) -> "b":  # type: ignore
        return self._discoverable

    @dbus_property(PropertyAccess.READ, "Includes")
    def _get_includes(self) -> "as":  # type: ignore
        return [
            _snake_to_kebab(inc.name)
            for inc in AdvertisingIncludes
            if self._includes & inc and inc.name is not None
        ]

    @dbus_property(PropertyAccess.READ, "Duration")
    def _get_duration(self) -> "q":  # type: ignore
        return self._duration
