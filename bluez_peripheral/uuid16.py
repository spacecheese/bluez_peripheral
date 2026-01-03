import builtins
from typing import Union, Optional
from uuid import UUID

UUIDLike = Union[str, bytes, UUID, "UUID16", int]


class UUID16:
    """A container for BLE uuid16 values.

    Args:
        hex: A hexadecimal representation of a uuid16 or compatible uuid128.
        bytes: A 16-bit or 128-bit value representing a uuid16 or compatible uuid128.
        int: A numeric value representing a uuid16 (if < 2^16) or compatible uuid128.
        uuid: A compatible uuid128.
    """

    # 0000****--0000-1000-8000-00805F9B34FB
    _FIELDS = (0x00000000, 0x0000, 0x1000, 0x80, 0x00, 0x00805F9B34FB)
    _uuid: UUID

    def __init__(
        self,
        hex: Optional[str] = None,
        bytes: Optional[bytes] = None,
        int: Optional[int] = None,
        uuid: Optional[UUID] = None,
    ):  # pylint: disable=redefined-builtin
        if [hex, bytes, int, uuid].count(None) != 3:
            raise TypeError(
                "exactly one of the hex, bytes or int arguments must be given"
            )

        time_low = None

        if hex is not None:
            hex.strip("0x")
            if len(hex) == 4:
                time_low = builtins.int(hex, 16)
            else:
                uuid = UUID(hex)
        elif bytes is not None:
            if len(bytes) == 2:
                time_low = builtins.int.from_bytes(bytes, byteorder="big")
            elif len(bytes) == 16:
                uuid = UUID(bytes=bytes)
            else:
                raise ValueError("uuid bytes must be exactly either 2 or 16 bytes long")
        elif int is not None:
            if 0 <= int < 2**16:
                time_low = int
            else:
                uuid = UUID(int=int)

        if time_low is not None:
            self._uuid = UUID(fields=(time_low,) + self._FIELDS[1:])
        else:
            assert uuid is not None
            if UUID16.is_in_range(uuid):
                self._uuid = uuid
            else:
                raise ValueError("the supplied uuid128 was out of range")

    @classmethod
    def is_in_range(cls, uuid: UUID) -> bool:
        """Determines if a supplied uuid128 is in the allowed uuid16 range.

        Returns:
            True if the uuid is in range, False otherwise.
        """
        if uuid.fields[0] & 0xFFFF0000 != cls._FIELDS[0]:
            return False

        return uuid.fields[1:5] == cls._FIELDS[1:5]

    @classmethod
    def parse_uuid(cls, uuid: UUIDLike) -> Union[UUID, "UUID16"]:
        """Attempts to parse a supplied UUID representation to a UUID16.
        If the resulting value is out of range a UUID128 will be returned instead."""
        if isinstance(uuid, UUID16):
            return uuid
        if isinstance(uuid, UUID):
            if cls.is_in_range(uuid):
                return UUID16(uuid=uuid)
            return uuid
        if isinstance(uuid, str):
            try:
                return UUID16(hex=uuid)
            except ValueError:
                return UUID(hex=uuid)
        if isinstance(uuid, builtins.bytes):
            try:
                return UUID16(bytes=uuid)
            except ValueError:
                return UUID(bytes=uuid)
        if isinstance(uuid, builtins.int):
            try:
                return UUID16(int=uuid)
            except ValueError:
                return UUID(int=uuid)

        raise ValueError("uuid is not a supported type")

    @property
    def uuid(self) -> UUID:
        """Returns the full uuid128 corresponding to this uuid16."""
        return self._uuid

    @property
    def int(self) -> builtins.int:
        """Returns the 16-bit integer value corresponding to this uuid16."""
        return self._uuid.time_low & 0xFFFF

    @property
    def bytes(self) -> bytes:
        """Returns a two byte value corresponding to this uuid16."""
        return self.int.to_bytes(2, byteorder="big")

    @property
    def hex(self) -> str:
        """Returns a 4 character hex string representing this uuid16."""
        return self.bytes.hex()

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, UUID16):
            return self._uuid == __o._uuid
        if isinstance(__o, UUID):
            return self._uuid == __o

        return False

    def __ne__(self, __o: object) -> bool:
        return not self.__eq__(__o)

    def __str__(self) -> str:
        return self.hex

    def __hash__(self) -> builtins.int:
        return hash(self.uuid)
