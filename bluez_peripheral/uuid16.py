import builtins

from uuid import UUID
from typing import Optional, Union


class UUID16:
    """A container for BLE uuid16 values.

    Args:
        hex (Optional[str]): A hexadecimal representation of a uuid16 or compatible uuid128.
        bytes (Optional[bytes]): A 16-bit or 128-bit value representing a uuid16 or compatible uuid128.
        int (Optional[int]): A numeric value representing a uuid16 (if < 2^16) or compatible uuid128.
        uuid (Optional[UUID]): A compatible uuid128.
    """

    # 0000****--0000-1000-8000-00805F9B34FB
    _FIELDS = (0x00000000, 0x0000, 0x1000, 0x80, 0x00, 0x00805F9B34FB)
    _uuid: UUID = None

    def __init__(
        self,
        hex: Optional[str] = None,
        bytes: Optional[bytes] = None,
        int: Optional[int] = None,
        uuid: Optional[UUID] = None,
    ):
        if [hex, bytes, int, uuid].count(None) != 3:
            raise TypeError("one of the hex, bytes or int arguments must be given")

        time_low = None

        if hex is not None:
            hex.strip("0x")
            if len(hex) == 4:
                time_low = builtins.int(hex, 16)
            else:
                uuid = UUID(hex)

        if bytes is not None:
            if len(bytes) == 2:
                time_low = builtins.int.from_bytes(bytes, byteorder="big")
            elif len(bytes) == 16:
                uuid = UUID(bytes=bytes)
            else:
                raise ValueError("bytes must be either 2 or 16-bytes long")

        if int is not None:
            if int < 2**16 and int >= 0:
                time_low = int
            else:
                uuid = UUID(int=int)
                

        if time_low is not None:
            fields = [f for f in self._FIELDS]
            fields[0] = time_low
            self._uuid = UUID(fields=fields)
        else:
            if UUID16.is_in_range(uuid):
                self._uuid = uuid
            else:
                raise ValueError(
                    "the supplied uuid128 was out of range"
                )

    @classmethod
    def is_in_range(cls, uuid: UUID) -> bool:
        """Determines if a supplied uuid128 is in the allowed uuid16 range.

        Returns:
            bool: True if the uuid is in range, False otherwise.
        """
        if uuid.fields[0] & 0xFFFF0000 != cls._FIELDS[0]:
            return False

        for i in range(1, 5):
            if uuid.fields[i] != cls._FIELDS[i]:
                return False

        return True

    @classmethod
    def parse_uuid(cls, uuid: Union[str, bytes, int, UUID]) -> Union[UUID, "UUID16"]:
        if type(uuid) is UUID:
            if cls.is_in_range(uuid):
                return UUID16(uuid=uuid)
            return uuid

        if type(uuid) is str:
            try:
                return UUID16(hex=uuid)
            except:
                return UUID(hex=uuid)

        if type(uuid) is bytes:
            try:
                return UUID16(bytes=uuid)
            except:
                return UUID(bytes=uuid)

        if type(uuid) is int:
            try:
                return UUID16(int=uuid)
            except:
                return UUID(int=uuid)

    @property
    def uuid(self) -> UUID:
        """Returns the full uuid128 corresponding to this uuid16.
        """
        return self._uuid

    @property
    def int(self) -> int:
        """Returns the 16-bit integer value corresponding to this uuid16.
        """
        return self._uuid.time_low & 0xFFFF

    @property
    def bytes(self) -> bytes:
        """Returns a two byte value corresponding to this uuid16.
        """
        return self.int.to_bytes(2, byteorder="big")

    @property
    def hex(self) -> str:
        """Returns a 4 character hex string representing this uuid16.
        """
        return self.bytes.hex()

    def __eq__(self, __o: object) -> bool:
        if type(__o) is UUID16:
            return self._uuid == __o._uuid
        elif type(__o) is UUID:
            return self._uuid == __o
        else:
            return False

    def __ne__(self, __o: object) -> bool:
        return not self.__eq__(__o)

    def __str__(self):
        return self.hex

    def __hash__(self):
        return hash(self.uuid)
