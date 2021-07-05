.. _characteristics_descriptors:

Characteristics/ Descriptors
============================

You should read the :doc:`quickstart guide <index>` before reading this. 
If you were looking for a characteristic reference you can find it :doc:`here <ref/gatt/characteristic>`. 
**Characteristics are designed to work the same way as the built-in property class.**
A list of Bluetooth SIG recognised characteristics, services and descriptors is 
`available on their website <https://btprodspecificationrefs.blob.core.windows.net/assigned-values/16-bit%20UUID%20Numbers%20Document.pdf>`_.

Characteristic and descriptor function are assumed to be members of a service class by type hints.
Though it is possible manually invoke the characteristic and descriptor decorators on a function that is not a member of a service it is not recomended.
**If you do this with a method your** :class:`self` **argument will be the associated service or None.**

Exceptions
----------

Internally bluez_peripheral uses `dbus_next <https://github.com/altdesktop/python-dbus-next/tree/master/dbus_next>`_ to communicate with bluez.
If you find that a characteristic or descriptor read or write access is invalid or not permitted for some reason you shoud raise a :class:`dbus_next.DBusError` with a type string recognised by bluez.
The `bluez docs <https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/doc/gatt-api.txt>`_ include specific lists 
of each access operation (the characteristic getters and setters map to ReadValue/ WriteValue calls) however in general you may use the following types::
    
    org.bluez.Error.Failed
    org.bluez.Error.InProgress
    org.bluez.Error.NotPermitted
    org.bluez.Error.InvalidValueLength
    org.bluez.Error.NotAuthorized
    org.bluez.Error.NotSupported

Exceptions that are not a :class:`dbus_next.DBusError` will still be returned to the caller but will result in a warning being printed to the terminal to aid in debugging.

Read/ Write Options
-------------------

bluez_peripheral does not check the validity of these options and only assigns them default values for convenience.
Normally you can ignore these options hoever one notable exeption to this is when the size of you characteristic exceeds the negotated mtu of your connection with the remote device.
In this case bluez will read your characteristic in bits by using the offset option.
The Bluetooth specification requires that all devices support, at least, an MTU of 48 bytes.
A default of 672 bytes is also specified, though in my testing with the Raspberry Pi 128 bytes seems a more typical number.

You may also choose to use these options to enforce authentication/ authorization.
Within this library this behaviour is untested and I'm not entirely sure if you need to manually implement this or whether simply setting the relevant flags ensures security. 
If you happen to experiment with this a github issue with your findings would be greatly appreciated.

Undocumented Flags
------------------

Some operation mode flags are currently undocumented in the reference.
The behaviour of these flags is not clearly defined by bluez and the terminology used differs slightly from that in the Bluetooth Core Spec.
If you have any insight into the functionality of these flags a Github issue would be greatly appreciated.