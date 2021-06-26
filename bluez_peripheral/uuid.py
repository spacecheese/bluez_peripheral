import re

from uuid import UUID
from typing import Union


class BTUUID(UUID):
    _UUID16_FMT = "0000{0}-0000-1000-8000-00805F9B34FB"
    _UUID16_RE = re.compile(
        "^0000([0-9a-fA-F]{4})-0000-1000-8000-00805F9B34FB", re.IGNORECASE
    )

    @classmethod
    def from_uuid16(cls, id: Union[str, int]) -> "BTUUID":
        """Converts an integer or 4 digit hex string to a Bluetooth compatible UUID16.

        Args:
            id (Union[str, int]): The UUID representation to convert.

        Returns:
            BTUUID: The resulting UUID.
        """
        hex = "0000"

        if type(id) is str:
            if id.lower().startswith("0x"):
                hex = id[2:]
            else:
                hex = id
        elif type(id) is int:
            hex = "{:04X}".format(id)

        return cls(cls._UUID16_FMT.format(hex))

    @property
    def uuid16(self) -> str:
        """Converts the UUID16 to a 4 digit string representation.

        Raises:
            ValueError: Raised if this UUID is not a UUID16.

        Returns:
            str: The UUID representation.
        """
        match = self._UUID16_RE.search(str(self))

        if not match:
            raise ValueError("self is not a uuid16")
        else:
            return match.group(1)
