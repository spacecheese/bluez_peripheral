Advertising Services
====================

In BLE advertising is required for other devices to discover services that surrounding peripherals offer. To allow multiple adverts to operate simultaneously advertising is time-division multiplexed.

.. hint:: 
    The "message bus" referred to here is a :py:class:`dbus_next.aio.MessageBus`.

A minimal :py:class:`advert<bluez_peripheral.advert.Advertisement>` requires:

* A name for the device transmitting the advert (the ``localName``).
* A collection of service UUIDs.
* An appearance  describing how the device should appear to a user (see `Bluetooth SIG Assigned Numbers <https://www.bluetooth.com/specifications/assigned-numbers/>`_).
* A timeout specifying roughly how long the advert should be broadcast for (roughly since this is complicated by advert multiplexing).
* A reference to a specific bluetooth :py:class:`adapter<bluez_peripheral.util.Adapter>` (since unlike with services, adverts are per-adapter).

.. code-block:: python

    from bluez_peripheral import get_message_bus, Advertisement
    from bluez_peripheral.util import Adapter

    adapter = await Adapter.get_first(bus)

    # "Heart Monitor" is the name the user will be shown for this device.
    # "180D"          is the uuid16 for a heart rate service.
    # 0x0340          is the appearance code for a generic heart rate sensor.
    # 60              is the time (in seconds) until the advert stops.
    advert = Advertisement("Heart Monitor", ["180D"], 0x0340, 60)
    await advert.register(bus, adapter)

.. TODO: Advertising includes
.. TODO: Advertisable characteristics

.. seealso:: 

    Bluez Documentation
        `Advertising API <https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/doc/advertising-api.txt>`_
