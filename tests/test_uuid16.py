from multiprocessing.sharedctypes import Value
import unittest

from bluez_peripheral.uuid16 import UUID16
from uuid import UUID, uuid1


class TestUUID16(unittest.TestCase):
    def test_from_hex(self):
        with self.assertRaises(ValueError):
            uuid = UUID16(hex="123")

        with self.assertRaises(ValueError):
            uuid = UUID16(hex="12345")

        uuid = UUID16(hex="1234")
        assert uuid.uuid == UUID("00001234-0000-1000-8000-00805F9B34FB")

        uuid = UUID16(hex="00001234-0000-1000-8000-00805F9B34FB")
        assert uuid.uuid == UUID("00001234-0000-1000-8000-00805F9B34FB")

    def test_from_bytes(self):
        with self.assertRaises(ValueError):
            uuid = UUID16(bytes=b"\x12")

        with self.assertRaises(ValueError):
            uuid = UUID16(bytes=b"\x12\x34\x56")

        uuid = UUID16(bytes=b"\x12\x34")
        assert uuid.uuid == UUID("00001234-0000-1000-8000-00805F9B34FB")

        uuid = UUID16(bytes=UUID("00001234-0000-1000-8000-00805F9B34FB").bytes)
        assert uuid.uuid == UUID("00001234-0000-1000-8000-00805F9B34FB")

    def test_from_int(self):
        with self.assertRaises(ValueError):
            uuid = UUID16(int=0x12345)

        uuid = UUID16(int=0x1234)
        assert uuid.uuid == UUID("00001234-0000-1000-8000-00805F9B34FB")

        uuid = UUID16(int=0x0000123400001000800000805F9B34FB)
        assert uuid.uuid == UUID("00001234-0000-1000-8000-00805F9B34FB")

    def test_parse_uuid(self):
        uuid = UUID("00001234-0000-1000-8000-00805F9B34FB")
        assert type(UUID16.parse_uuid(uuid)) is UUID16

        uuid = "00001234-0000-1000-8000-00805F9B34FB"
        assert type(UUID16.parse_uuid(uuid) is UUID16)

        uuid = b"\x00\x01\x12\x34\x00\x00\x10\x00\x80\x00\x00\x80\x5f\x9b\x34\xfb"
        assert type(UUID16.parse_uuid(uuid) is UUID16)

        uuid = 0x0000123400001000800000805F9B34FB
        assert type(UUID16.parse_uuid(uuid) is UUID16)

        uuid = UUID("00011234-0000-1000-8000-00805F9B34FB")
        assert type(UUID16.parse_uuid(uuid)) is UUID

        uuid = "00011234-0000-1000-8000-00805F9B34FB"
        assert type(UUID16.parse_uuid(uuid) is UUID)

        uuid = b"\x00\x00\x12\x34\x00\x00\x10\x00\x80\x00\x00\x80\x5f\x9b\x34\xfb"
        assert type(UUID16.parse_uuid(uuid) is UUID)

        uuid = 0x0001123400001000800000805F9B34FB
        assert type(UUID16.parse_uuid(uuid) is UUID)

        with self.assertRaises(ValueError):
            uuid = UUID16.parse_uuid(object())

    def test_from_uuid(self):
        with self.assertRaises(ValueError):
            uuid = UUID16(uuid=uuid1())

        uuid = UUID16(uuid=UUID("00001234-0000-1000-8000-00805F9B34FB"))
        assert uuid.uuid == UUID("00001234-0000-1000-8000-00805F9B34FB")

    def test_is_in_range(self):
        uuid = UUID("00001234-0000-1000-8000-00805F9B34FB")
        assert UUID16.is_in_range(uuid) == True

        uuid = UUID("00011234-0000-1000-8000-00805F9B34FB")
        assert UUID16.is_in_range(uuid) == False

        uuid = UUID("00001234-0000-1000-8000-00805F9B34FC")
        assert UUID16.is_in_range(uuid) == True

    def test_int(self):
        uuid = UUID16(uuid=UUID("00001234-0000-1000-8000-00805F9B34FB"))
        assert uuid.int == 0x1234

    def test_bytes(self):
        uuid = UUID16(uuid=UUID("00001234-0000-1000-8000-00805F9B34FB"))
        assert uuid.bytes == b"\x12\x34"

    def test_hex(self):
        uuid = UUID16(uuid=UUID("00001234-0000-1000-8000-00805F9B34FB"))
        assert uuid.hex == "1234"

    def test_init(self):
        with self.assertRaises(TypeError):
            uuid = UUID16()

    def test_eq(self):
        uuid_a = UUID("00001234-0000-1000-8000-00805F9B34FB")
        uuid16_a = UUID16(uuid=uuid_a)
       
        uuid_b = UUID("00001236-0000-1000-8000-00805F9B34FB")
        uuid16_b = UUID16(uuid=uuid_b)
        
        assert uuid16_a == uuid16_a
        assert uuid16_a != uuid16_b
        assert uuid16_b != uuid16_a
        assert uuid16_a == uuid_a
        assert uuid16_b == uuid_b
        assert uuid16_a != uuid_b
        assert not uuid16_a == object()
        assert uuid16_a != object()

    def test_hash(self):
        uuid_a = UUID16(uuid=UUID("00001234-0000-1000-8000-00805F9B34FB"))
        uuid_b = UUID16(uuid=UUID("00001234-0000-1000-8000-00805F9B34FB"))
        uuid_c = UUID16(uuid=UUID("00001236-0000-1000-8000-00805F9B34FB"))

        assert hash(uuid_a) == hash(uuid_b)
        assert hash(uuid_a) != hash(uuid_c)
