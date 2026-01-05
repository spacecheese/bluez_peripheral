import pytest

from dbus_fast.errors import DBusError

from bluez_peripheral.error import bluez_error_wrapper, AlreadyExistsError, FailedError


@pytest.mark.asyncio
async def test_wrapper():
    with pytest.raises(AlreadyExistsError) as e:
        async with bluez_error_wrapper():
            raise DBusError("org.bluez.Error.AlreadyExists", "test1")

    assert e.value.text == "test1"

    with pytest.raises(FailedError) as e:
        async with bluez_error_wrapper():
            raise DBusError("org.bluez.Error.Failed", "test2")

    assert e.value.text == "test2"
