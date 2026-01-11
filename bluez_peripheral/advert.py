from typing import Collection, Dict, Optional, Union, Any
import struct

from dbus_fast import Variant
from dbus_fast.constants import PropertyAccess
from dbus_fast.service import method, dbus_property
from dbus_fast.aio.message_bus import MessageBus

from .uuid16 import UUID16, UUIDLike
from .util import _snake_to_kebab
from .adapter import Adapter
from .flags import AdvertisingIncludes
from .flags import AdvertisingPacketType
from .base import BaseServiceInterface, UniquePathMixin
from .error import bluez_error_wrapper


class Advertisement(UniquePathMixin):
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
        release_callback: A function to call when the advert release function is called. The default release callback will unexport the advert.
    """

    _DEFAULT_PATH_PREFIX = "/com/spacecheese/bluez_peripheral/advert"

    def _advert_service_factory(self) -> "BaseServiceInterface":
        advert = self

        class _AdvertService(BaseServiceInterface):
            _INTERFACE = "org.bluez.LEAdvertisement1"

            def _get_default_path(self, **_: Any) -> str:
                raise NotImplementedError()

            @method("Release")
            async def _release(self):  # type: ignore
                await advert._release()

            @dbus_property(PropertyAccess.READ, "Type")
            def _get_type(self) -> "s":  # type: ignore
                return advert._type.name.lower()

            @dbus_property(
                PropertyAccess.READ,
                "ServiceUUIDs",
                disabled=(advert._service_uuids is None),
            )
            def _get_service_uuids(self) -> "as":  # type: ignore
                if advert._service_uuids is None:
                    raise NotImplementedError()

                return [str(id) for id in advert._service_uuids]

            @dbus_property(
                PropertyAccess.READ, "LocalName", disabled=(advert._local_name is None)
            )
            def _get_local_name(self) -> "s":  # type: ignore
                return advert._local_name

            @dbus_property(
                PropertyAccess.READ, "Appearance", disabled=(advert._appearance is None)
            )
            def _get_appearance(self) -> "q":  # type: ignore
                return advert._appearance

            @dbus_property(
                PropertyAccess.READ, "Timeout", disabled=(advert._timeout is None)
            )
            def _get_timeout(self) -> "q":  # type: ignore
                return advert._timeout

            @dbus_property(
                PropertyAccess.READ,
                "ManufacturerData",
                disabled=(advert._manufacturer_data is None),
            )
            def _get_manufacturer_data(self) -> "a{qv}":  # type: ignore
                return advert._manufacturer_data

            @dbus_property(
                PropertyAccess.READ,
                "SolicitUUIDs",
                disabled=(advert._solicit_uuids is None),
            )
            def _get_solicit_uuids(self) -> "as":  # type: ignore
                if advert._solicit_uuids is None:
                    raise NotImplementedError()

                return [str(key) for key in advert._solicit_uuids]

            @dbus_property(
                PropertyAccess.READ,
                "ServiceData",
                disabled=(advert._service_data is None),
            )
            def _get_service_data(self) -> "a{sv}":  # type: ignore
                if advert._service_data is None:
                    raise NotImplementedError()

                return {str(key): val for key, val in advert._service_data.items()}

            @dbus_property(
                PropertyAccess.READ,
                "Discoverable",
                disabled=(advert._discoverable is None),
            )
            def _get_discoverable(self) -> "b":  # type: ignore
                return advert._discoverable

            @dbus_property(
                PropertyAccess.READ,
                "Includes",
                disabled=(advert._includes == AdvertisingIncludes.NONE),
            )
            def _get_includes(self) -> "as":  # type: ignore
                return [
                    _snake_to_kebab(inc.name)
                    for inc in AdvertisingIncludes
                    if advert._includes & inc and inc.name is not None
                ]

            @dbus_property(
                PropertyAccess.READ, "Duration", disabled=(advert._duration is None)
            )
            def _get_duration(self) -> "q":  # type: ignore
                return advert._duration

        return _AdvertService()

    def __init__(
        self,
        local_name: Optional[str] = None,
        service_uuids: Optional[Collection[UUIDLike]] = None,
        *,
        appearance: Optional[Union[int, bytes]] = None,
        timeout: Optional[int] = None,
        discoverable: Optional[bool] = None,
        packet_type: AdvertisingPacketType = AdvertisingPacketType.PERIPHERAL,
        manufacturer_data: Optional[Dict[int, bytes]] = None,
        solicit_uuids: Optional[Collection[UUIDLike]] = None,
        service_data: Optional[Dict[UUIDLike, bytes]] = None,
        includes: AdvertisingIncludes = AdvertisingIncludes.NONE,
        duration: Optional[int] = 2,
    ):
        self._type = packet_type
        # Convert any string uuids to uuid16.
        self._service_uuids = None
        if service_uuids is not None:
            self._service_uuids = [UUID16.parse_uuid(uuid) for uuid in service_uuids]
        self._local_name = local_name
        # Convert the appearance to a uint16 if it isn't already an int.
        if isinstance(appearance, bytes):
            self._appearance = struct.unpack("H", appearance)[0]
        else:
            self._appearance = appearance
        self._timeout = timeout

        self._manufacturer_data = None
        if manufacturer_data is not None:
            self._manufacturer_data = {
                k: Variant("ay", v) for k, v in manufacturer_data.items()
            }

        self._solicit_uuids = None
        if solicit_uuids is not None:
            self._solicit_uuids = [UUID16.parse_uuid(uuid) for uuid in solicit_uuids]

        self._service_data = None
        if service_data is not None:
            self._service_data = {
                UUID16.parse_uuid(k): Variant("ay", v) for k, v in service_data.items()
            }

        self._discoverable = discoverable
        self._includes = includes
        self._duration = duration

        self._adapter: Optional[Adapter] = None
        self._service = self._advert_service_factory()

    async def _release(self) -> None:
        self._adapter = None
        self._service._unexport()

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
        if path is None:
            path = self._get_default_path()
        self._service._export(bus, path=path)

        if adapter is None:
            adapter = await Adapter.get_first(bus)

        # Get the LEAdvertisingManager1 interface for the target adapter.
        interface = adapter.get_advertising_manager()
        async with bluez_error_wrapper():
            await interface.call_register_advertisement(self._service.export_path, {})  # type: ignore
        self._adapter = adapter

    async def unregister(self) -> None:
        """
        Unregister this advertisement from bluez to stop advertising.
        """
        if self._adapter is None:
            raise ValueError("This advertisement is not registered")

        interface = self._adapter.get_advertising_manager()

        async with bluez_error_wrapper():
            await interface.call_unregister_advertisement(self._service.export_path)  # type: ignore
        self._adapter = None

        self._service._unexport()

    @property
    def export_path(self) -> Optional[str]:
        """
        Returns the message bus path that the advert is exported on or None.
        """
        return self._service.export_path
