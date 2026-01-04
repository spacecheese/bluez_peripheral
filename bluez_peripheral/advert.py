from typing import Collection, Dict, Callable, Optional, Union, List, Tuple
import struct
from uuid import UUID

from dbus_fast import Variant
from dbus_fast.constants import PropertyAccess
from dbus_fast.service import method, dbus_property
from dbus_fast.aio.message_bus import MessageBus

from .uuid16 import UUID16, UUIDLike
from .util import _snake_to_kebab
from .adapter import Adapter
from .flags import AdvertisingIncludes
from .flags import AdvertisingPacketType
from .base import BaseServiceInterface


class Advertisement(BaseServiceInterface):
    """
    An advertisement for a particular service or collection of services that can be registered and broadcast to nearby devices.
    Represents an `org.bluez.LEAdvertisement1 <https://raw.githubusercontent.com/bluez/bluez/refs/heads/master/doc/org.bluez.LEAdvertisement.rst>`_ instance.

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
        release_callback: A function to call when the advert release function is called.
    """

    _INTERFACE = "org.bluez.LEAdvertisement1"
    _DEFAULT_PATH_PREFIX = "/com/spacecheese/bluez_peripheral/advert"

    def __init__(
        self,
        local_name: str,
        service_uuids: Collection[UUIDLike],
        *,
        appearance: Union[int, bytes],
        timeout: int = 0,
        discoverable: bool = True,
        packet_type: AdvertisingPacketType = AdvertisingPacketType.PERIPHERAL,
        manufacturer_data: Optional[Dict[int, bytes]] = None,
        solicit_uuids: Optional[Collection[UUIDLike]] = None,
        service_data: Optional[List[Tuple[UUIDLike, bytes]]] = None,
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

        self._adapter: Optional[Adapter] = None

        super().__init__()

    async def register(
        self,
        bus: MessageBus,
        *,
        path: Optional[str] = None,
        adapter: Optional[Adapter] = None,
    ) -> None:
        """Register this advert with bluez to start advertising.

        Args:
            bus: The message bus used to communicate with bluez.
            adapter: The adapter to use.
            path: The dbus path to use for registration.
        """

        self.export(bus, path=path)

        if adapter is None:
            adapter = await Adapter.get_first(bus)

        # Get the LEAdvertisingManager1 interface for the target adapter.
        interface = adapter.get_advertising_manager()
        await interface.call_register_advertisement(self.export_path, {})  # type: ignore

        self._adapter = adapter

    @method("Release")
    def _release(self):  # type: ignore
        self.unexport()

    async def unregister(self) -> None:
        """
        Unregister this advertisement from bluez to stop advertising.
        """
        if not self._adapter or not self.is_exported:
            raise ValueError("This advertisement is not registered")

        interface = self._adapter.get_advertising_manager()

        await interface.call_unregister_advertisement(self.export_path)  # type: ignore
        self._adapter = None
        self.unexport()

        if self._release_callback is not None:
            self._release_callback()

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
