Creating a Service
==================
Attribute Flags
---------------
The behaviour of a particular attribute is described by a set of flags. These flags are implemented using the :py:class:`~bluez_peripheral.gatt.characteristic.CharacteristicFlags` and :py:class:`~bluez_peripheral.gatt.descriptor.DescriptorFlags` enums. A single attribute may have multiple flags, in python you can combine these flags using the ``|`` operator (eg. ``CharacteristicFlags.READ | CharacteristicFlags.WRITE``).

UUIDs
-----
.. hint:: 
    The Bluetooth SIG has reserved 16-bit UUIDs for `standardised services <https://www.bluetooth.com/specifications/assigned-numbers/>`_. 128-bit UUIDs should be preferred to avoid confusion.

BLE uses 128-bit Universally Unique Identifiers (UUIDs) to determine what each service, characteristic and descriptor refers to in addition to the type of every attribute. To minimise the amount of information that needs to be transmitted the Bluetooth SIG selected a base UUID of ``0000XXXX-0000-1000-8000-00805F9B34FB``. This allows a 16-bit number to be transmitted in place of the full 128-bit value in some cases. In bluez_peripheral 16-bit UUIDs are represented by the :py:class:`~bluez_peripheral.uuid16.UUID16` class whilst 128-bit values are represented by :py:class:`uuid.UUID`. In bluez_peripheral all user provided UUIDs are are parsed using :py:func:`UUID16.parse_uuid()<bluez_peripheral.uuid16.UUID16.parse_uuid>` meaning you can use these types interchangably, UUID16s will automatically be used where possible.

Adding Attributes
-----------------
The :py:class:`@characteristic<bluez_peripheral.gatt.characteristic.characteristic>` and :py:class:`@descriptor<bluez_peripheral.gatt.descriptor.descriptor>` decorators are designed to work identically to the built-in :py:class:`@property<property>` decorator. Attributes can be added to a service either manually or using decorators:

.. warning::
    Attributes exceeding 48 bytes in length may take place across multiple accesses, using the :ref:`options.offset<attribute-options>` parameter to select portions of the data. This is dependent upon the :ref:`options.mtu<attribute-options>`.

.. TODO: Code examples need automated testing.
.. tab:: Decorators

    .. code-block:: python

        from bluez_peripheral.gatt import Service
        from bluez_peripheral.gatt import characteristic, CharacteristicFlags as CharFlags
        from bluez_peripheral.gatt import descriptor, DescriptorFlags as DescFlags

        class MyService(Service):
            def __init__(self):
                # You must call the super class constructor to register any decorated attributes.
                super().__init__(uuid="BEED")

            @characteristic("BEEE", CharFlags.READ | CharFlags.WRITE)
            def my_characteristic(self, options):
                # This is the getter for my_characteristic.
                # All attribute functions must return bytes.
                return bytes("Hello World!", "utf-8")

            @my_characteristic.setter
            def my_characteristic(self, value, options):
                # This is the setter for my_characteristic.
                # Value consists of some bytes.
                self._my_char_value = value

            # Descriptors work exactly the same way.
            @descriptor("BEEF", my_characteristic, DescFlags.WRITE)
            def my_writeonly_descriptor(self, options):
                # This function is a manditory placeholder.
                # In Python 3.9+ you don't need this function (See PEP 614).
                pass

            my_writeonly_descriptor.setter
            def my_writeonly_descriptor(self, value, options):
                self._my_desc_value = value

.. tab:: Manually (Not Recommended)

    .. code-block:: python

        from bluez_peripheral.gatt import Service
        from bluez_peripheral.gatt import characteristic, CharacteristicFlags as CharFlags
        from bluez_peripheral.gatt import descriptor, DescriptorFlags as DescFlags

        # Create my_characteristic
        my_char_value = None
        def my_characteristic_getter(service, options):
            return bytes("Hello World!", "utf-8")
        def my_characteristic_setter(service, value, options):
            my_char_value = value
        # See characteristic.__call__()
        my_characteristic = characteristic("BEEE", CharFlags.READ | CharFlags.WRITE)(
            my_characteristic_getter, my_characteristic_setter
        )

        # Create my_descriptor
        my_desc_value = None
        def my_readonly_descriptor_setter(service, value, options):
            my_desc_value = value
        # See descriptor.__call__()
        my_descriptor = descriptor("BEEF", my_characteristic, DescFlags.WRITE)(
            None, my_readonly_descriptor_setter
        )

        # Register my_descriptor with its parent characteristic and my_characteristic 
        # with its parent service.
        my_service = Service()
        my_characteristic.add_descriptor(my_descriptor)
        my_service.add_characteristic(my_characteristic)

Error Handling
^^^^^^^^^^^^^^
Attribute getters/ setters may raise one of a set of :ref:`legal exceptions<legal-errors>` to signal specific conditions to bluez. Avoid thowing custom exceptions in attribute accessors, since these will not be presented to a user and bluez will not know how to interpret them. Aditionally any exceptions thrown **must** derive from :py:class:`dbus_next.DBusError`. 

.. _legal-errors:

Legal Errors
^^^^^^^^^^^^

+-------------------------------------------------------------+----------------------------------------------------------+----------------------------------------------------------+
| Error                                                       | Characteristic                                           | Descriptor                                               |
|                                                             +----------------------------+-----------------------------+----------------------------+-----------------------------+
|                                                             | :abbr:`Getter (ReadValue)` | :abbr:`Setter (WriteValue)` | :abbr:`Getter (ReadValue)` | :abbr:`Setter (WriteValue)` |
+=============================================================+============================+=============================+============================+=============================+
| :py:class:`~bluez_peripheral.error.FailedError`             | ✓                          | ✓                           | ✓                          | ✓                           |
+-------------------------------------------------------------+----------------------------+-----------------------------+----------------------------+-----------------------------+
| :py:class:`~bluez_peripheral.error.InProgressError`         | ✓                          | ✓                           | ✓                          | ✓                           |
+-------------------------------------------------------------+----------------------------+-----------------------------+----------------------------+-----------------------------+
| :py:class:`~bluez_peripheral.error.InvalidOffsetError`      | ✓                          |                             |                            |                             |
+-------------------------------------------------------------+----------------------------+-----------------------------+----------------------------+-----------------------------+
| :py:class:`~bluez_peripheral.error.InvalidValueLengthError` |                            | ✓                           |                            | ✓                           |
+-------------------------------------------------------------+----------------------------+-----------------------------+----------------------------+-----------------------------+
| :py:class:`~bluez_peripheral.error.NotAuthorizedError`      | ✓                          | ✓                           | ✓                          | ✓                           |
+-------------------------------------------------------------+----------------------------+-----------------------------+----------------------------+-----------------------------+
| :py:class:`~bluez_peripheral.error.NotPermittedError`       | ✓                          | ✓                           | ✓                          | ✓                           |
+-------------------------------------------------------------+----------------------------+-----------------------------+----------------------------+-----------------------------+
| :py:class:`~bluez_peripheral.error.NotSupportedError`       | ✓                          | ✓                           | ✓                          | ✓                           |
+-------------------------------------------------------------+----------------------------+-----------------------------+----------------------------+-----------------------------+

Registering a Service
-----------------------
.. warning:: 
    Ensure that the thread used to register your service yeilds regularly. Client requests will not be served otherwise.

.. hint:: 
    The "message bus" referred to here is a :py:class:`dbus_next.aio.MessageBus`.

Services can either be registered individually using a :py:class:`~bluez_peripheral.gatt.service.Service` or as part of a :py:class:`~bluez_peripheral.gatt.service.ServiceCollection`. For example following on from the earlier code:

.. tab:: Service

    .. code-block:: python

        from bluez_peripheral import get_message_bus

        my_service = Service()

        bus = await get_message_bus()
        # Register the service for bluez to access.
        await my_service.register(bus)

        # Yeild so that the service can handle requests.
        await bus.wait_for_disconnect()

.. tab:: ServiceCollection

    .. code-block:: python

        from bluez_peripheral import get_message_bus
        from bluez_peripheral.gatt import ServiceCollection

        my_service_collection = ServiceCollection()
        my_service_collection.add_service(my_service)
        #my_service_collection.add_service(my_other_service)

        bus = await get_message_bus()
        # Register the service for bluez to access.
        await my_service_collection.register(bus)

        # Yeild so that the services can handle requests.
        await bus.wait_for_disconnect()

Notification
^^^^^^^^^^^^
Characteristics with the :py:attr:`~bluez_peripheral.gatt.characteristic.CharacteristicFlags.NOTIFY` or :py:attr:`~bluez_peripheral.gatt.characteristic.CharacteristicFlags.INDICATE` flags can update clients when their value changes. Indicate requires acknowledgement from the client whilst notify does not. For this to work the client must first call subscribe to the notification. The client can then be notified by calling :py:func:`characteristic.changed()<bluez_peripheral.gatt.characteristic.characteristic.changed>`.

.. warning:: 
    The :py:func:`characteristic.changed()<bluez_peripheral.gatt.characteristic.characteristic.changed>` function may only be called in the same thread that registered the service.

.. code-block:: python

    from bluez_peripheral import get_message_bus
    from bluez_peripheral.gatt import Service
    from bluez_peripheral.gatt import characteristic, CharacteristicFlags as CharFlags

    class MyService(Service):
            def __init__(self):
                super().__init__(uuid="DEED")

            @characteristic("DEEE", CharFlags.NOTIFY)
            def my_notify_characteristic(self, options):
                pass

    my_service = MyService()

    bus = await get_message_bus()
    await my_service.register(bus)

    # Signal that the value of the characteristic has changed.
    service.my_notify_characteristic.changed(bytes("My new value", "utf-8"))

    # Yeild so that the service can handle requests and signal the change.
    await bus.wait_for_disconnect()


.. seealso:: 

    Bluez Documentation
        `GATT API <https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/doc/gatt-api.txt>`_

    .. _attribute-options:

    Attribute Access Options
        :py:class:`~bluez_peripheral.gatt.characteristic.CharacteristicReadOptions`
        :py:class:`~bluez_peripheral.gatt.characteristic.CharacteristicWriteOptions`
        :py:class:`~bluez_peripheral.gatt.descriptor.DescriptorReadOptions`
        :py:class:`~bluez_peripheral.gatt.descriptor.DescriptorWriteOptions`

