.. _quickstart:

bluez-peripheral Quickstart
===========================

This documentation assumes that you are vaguely familiar with the structure of a BLE GATT service (See the `README <https://github.com/spacecheese/bluez_peripheral>`_).
In bluez-peripheral classes are used to define services. 
Your services should contain methods decorated with the characteristic and descriptor classes.
These classes behave in much the same way as the built-in `property class <https://docs.python.org/library/functions.html#property>`_.

.. code-block:: python

   from bluez_peripheral.gatt.service import Service
   from bluez_peripheral.gatt.characteristic import characteristic, CharacteristicFlags as CharFlags
   from bluez_peripheral.gatt.descriptor import descriptor, DescriptorFlags as DescFlags

   # Define a service like so.
   class MyService(Service):
      def __init__(self):
         self._some_value = None
         # Call the super constructor to set the UUID.
         super().__init__("BEEF", True)

      # Use the characteristic decorator to define your own characteristics.
      # Set the allowed access methods using the characteristic flags.
      @characteristic("BEF0", CharFlags.READ)
      def my_readonly_characteristic(self, options):
         # Characteristics need to return bytes.
         return bytes("Hello World!", "utf-8")

      # This is a write only characteristic.
      @characteristic("BEF1", CharFlags.WRITE)
      def my_writeonly_characteristic(self, options):
         # This function is a placeholder.
         # In Python 3.9+ you don't need this function (See PEP 614)
         pass

      # In Python 3.9+:
      # @characteristic("BEF1", CharFlags.WRITE).setter
      # Define a characteristic writing function like so.
      @my_readonly_characteristic.setter
      def my_writeonly_characteristic(self, value, options):
         # Your characteristics will need to handle bytes.
         self._some_value = value

      # Associate a descriptor with your characteristic like so.
      # Descriptors have largely the same flags available as characteristics.
      @descriptor("BEF2", my_readonly_characteristic, DescFlags.READ)
      # Alternatively you could write this:
      # @my_writeonly_characteristic.descriptor("BEF2", DescFlags.READ)
      def my_readonly_descriptors(self, options):
         # Descriptors also need to handle bytes.
         return bytes("This characteristic is completely pointless!", "utf-8")

Once you've defined your service you need to add it to a service collection which can then be registed with bluez.

.. code-block:: python

   from bluez_peripheral.gatt.service import ServiceCollection
   from ble.util import *

   # This needs running in an awaitable context.
   bus = await get_message_bus()

   # Instance and register your service.
   service = MyService()
   await service.register(bus)

At this point your service would work but without anything knowing it exists you can't test it.
You need to advertise your service to allow other devices to connect to it.

.. code-block:: python

   from bluez_peripheral.advert import Advertisment

   my_service_ids = ["BEEF"] # The services that we're advertising.
   my_appearance = 0 # The appearance of my service. 
   # See https://specificationrefs.bluetooth.com/assigned-values/Appearance%20Values.pdf
   my_timeout = 60 # Advert should last 60 seconds before ending (assuming other local 
   # services aren't being advertised).
   advert = Advertisment("My Device Name", my_service_ids, my_appearance, my_timeout)


At this point you'll be be able to connect to your device using a bluetooth tester 
and see your service (`nRF Connect for Mobile <https://www.nordicsemi.com/Products/Development-tools/nrf-connect-for-mobile>`_ is good for basic testing).


.. toctree::
   :maxdepth: 1
   :caption: Contents:

   characteristics_descriptors
   pairing

.. toctree::
   :maxdepth: 4
   :caption: Reference:

   ref/bluez_peripheral



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
