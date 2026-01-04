from enum import Enum, Flag, auto


class AdvertisingPacketType(Enum):
    """Represents the type of packet used to perform a service."""

    BROADCAST = 0
    """The relevant service(s) will be broadcast and do not require pairing.
    """
    PERIPHERAL = 1
    """The relevant service(s) are associated with a peripheral role.
    """


class AdvertisingIncludes(Flag):
    """The fields to include in advertisements."""

    NONE = 0
    TX_POWER = auto()
    """Transmission power should be included.
    """
    APPEARANCE = auto()
    """Device appearance number should be included.
    """
    LOCAL_NAME = auto()
    """The local name of this device should be included.
    """
