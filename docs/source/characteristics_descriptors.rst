.. _characteristics_descriptors:

Characteristics/ Descriptors
============================

You should read the :doc:`quickstart guide <index>` before reading this. 
If you were looking for a characteristic reference you can find it :doc:`here <ref/gatt/characteristic>`. 

Characteristics are designed to work the same way as the built-in property class.
A list of Bluetooth SIG recognized characteristics, services and descriptors is 
`available on their website <https://btprodspecificationrefs.blob.core.windows.net/assigned-values/16-bit%20UUID%20Numbers%20Document.pdf>`_.
These are recommended over creating a custom characteristic where possible since other devices may already support them.

Exceptions
----------

Internally bluez_peripheral uses `dbus_next <https://github.com/altdesktop/python-dbus-next/tree/master/dbus_next>`_ to communicate with bluez.
If you find that a characteristic or descriptor read or write access is invalid or not permitted for some reason you should raise a :py:class:`dbus_next.DBusError` with a type string recognized by bluez.
The `bluez docs <https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/doc/gatt-api.txt>`_ include specific lists 
of each access operation (the characteristic getters and setters map to ReadValue/ WriteValue calls) however in general you may use the following types::
    
    org.bluez.Error.Failed
    org.bluez.Error.InProgress
    org.bluez.Error.NotPermitted
    org.bluez.Error.InvalidValueLength
    org.bluez.Error.NotAuthorized
    org.bluez.Error.NotSupported

Exceptions that are not a :py:class:`dbus_next.DBusError` will still be returned to the caller but will result in a warning being printed to the terminal to aid in debugging.

Read/ Write Options
-------------------

bluez_peripheral does not check the validity of these options and only assigns them default values for convenience.
Normally you can ignore these options however one notable exception to this is when the size of you characteristic exceeds the negotiated Minimum Transfer Unit (MTU) of your connection with the remote device.
In this case bluez will read your characteristic multiple times (using the offset option to break it up).
This can be a problem if your characteristic exceeds 48 bytes in length (this is the minimum allowed by the Bluetooth specification) although in general 
most devices have a larger default MTU (on the Raspberry Pi this appears to be 128 bytes).

You may also choose to use these options to enforce authentication/ authorization.
The behavior of these options is untested so if you experiment with these or have experience working with them a GitHub issue would be greatly appreciated.

Undocumented Flags
------------------

Some operation mode flags are currently undocumented in the reference.
The behavior of these flags is not clearly defined by the bluez documentation and the terminology used differs slightly from that in the Bluetooth Specifications.
If you have any insight into the functionality of these flags a GitHub issue would be greatly appreciated.