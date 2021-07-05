import re

from uuid import UUID
from typing import Union


class BTUUID(UUID):
    """An extension of the built-in UUID class with some utility functions for converting Bluetooth UUID16s to and from UUID128s."""

    _UUID16_UUID128_FMT = "0000{0}-0000-1000-8000-00805F9B34FB"
    _UUID16_UUID128_RE = re.compile(
        "^0000([0-9A-F]{4})-0000-1000-8000-00805F9B34FB$", re.IGNORECASE
    )
    _UUID16_RE = re.compile("^(?:0x)?([0-9A-F]{4})$", re.IGNORECASE)

    @classmethod
    def from_uuid16(cls, id: Union[str, int]) -> "BTUUID":
        """Converts an integer or 4 digit hex string to a Bluetooth compatible UUID16.

        Args:
            id (Union[str, int]): The UUID representation to convert.

        Raises:
            ValueError: Raised if the supplied UUID16 is not valid.

        Returns:
            BTUUID: The resulting UUID.
        """
        hex = "0000"

        if type(id) is str:
            match = cls._UUID16_RE.search(id)

            if not match:
                raise ValueError("id is not a valid UUID16")

            hex = match.group(1)

        elif type(id) is int:
            if id > 65535 or id < 0:
                raise ValueError("id is out of range")

            hex = "{:04X}".format(id)

        return cls(cls._UUID16_UUID128_FMT.format(hex))

    @classmethod
    def from_uuid16_128(cls, id: str) -> "BTUUID":
        """Converts a 4 or 32 digit hex string to a bluetooth compatible UUID16.

        Raises:
            ValueError: Raised if the supplied string is not a valid UUID.

        Returns:
            BTUUID: The resulting UUID.
        """
        if len(id) == 4:
            return cls.from_uuid16(id)
        else:
            uuid = cls(id)

            try:
                # If the result wont convert to a uuid16 then it must be invalid.
                _ = uuid.uuid16
            except ValueError:
                raise ValueError("id is not a valid uuid16")

            return uuid

    @property
    def uuid16(self) -> str:
        """Converts the UUID16 to a 4 digit string representation.

        Raises:
            ValueError: Raised if this UUID is not a valid UUID16.

        Returns:
            str: The UUID representation.
        """
        match = self._UUID16_UUID128_RE.search(str(self))

        if not match:
            raise ValueError("self is not a uuid16")

        return match.group(1)
