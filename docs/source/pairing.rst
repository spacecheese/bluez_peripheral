Pairing
=======

Pairing requires that the host and client exchange encryption keys in order to communicate securely. 

Agents
------

.. TODO: Investigate OOB pairing.

.. hint:: 
    Some devices use "out of band" data (for example communicated using NFC) to verify pairing. This approach is currently **unsupported** by bluez_peripheral agents.

.. warning:: 
    By default bluez_peripheral agents are registered as default (see the :py:func:`~bluez_peripheral.agent.BaseAgent.register` function ``default`` argument). This generally requires superuser permission. If an agent is not registered as default it will not be called in response to inbound pairing requests (only those outbound from the source program).

An agent is a program used to authorize and secure a pairing. Each agent has associated Input/ Output capabilities (see :py:class:`~bluez_peripheral.agent.AgentCapability`) which are exchanged at the start of the pairing process. Devices with limited IO capabilities cannot support authentication which prevents access to attributes with certain flags (see :ref:`pairing-io`).

Using an Agent
--------------

.. hint:: 
    The "message bus" referred to here is a :py:class:`dbus_next.aio.MessageBus`.

There are three potential sources of agents:

.. tab:: bluez

    Bluez supports a number of built in agents. You can select an agent with given capability by using the following command in your terminal:

    .. code-block:: shell

        bluetoothctl agent <capability>

    These agents are unreliable but the simplest to set up.

.. tab:: bluez_peripheral

    bluez_peripheral includes built in :py:class:`~bluez_peripheral.agent.NoIoAgent` and :py:class:`~bluez_peripheral.agent.YesNoAgent` agents which can be used as below:

    .. code-block:: python

        from bluez_peripheral import get_message_bus
        from bluez_peripheral.agent import NoIoAgent

        bus = await get_message_bus()

        agent = NoIoAgent()
        # By default agents are registered as default.
        await agent.register(bus, default=True)

        # OR

        def accept_pairing(code: int) -> bool:
            # TODO: Show the user the code and ask if it's correct.
            # if (correct):
            #   return True
            # else:
            #   return False

            return True

        def cancel_pairing():
            # TODO: Notify the user that pairing was cancelled by the other device.
            pass

        agent = YesNoAgent(accept_pairing, cancel_pairing)
        await agent.register(bus)

.. tab:: Custom Agents (Recommended)

    Support for custom agents in bluez_peripheral is limited. The recommended approach is to inherit the :class:`bluez_peripheral.agent.BaseAgent` in the same way as the built in agents. The :class:`bluez_peripheral.agent.TestAgent` can be instanced as shown for testing:

    .. code-block:: python

        from bluez_peripheral import get_message_bus
        from bluez_peripheral.agent import TestAgent

        bus = await get_message_bus()

        agent = TestAgent()
        await agent.register(bus)

    The test agent will then fire :py:func:`breakpoints<breakpoint>` when each of the interfaces functions is called during the pairing process. Note that when extending this class the type hints as used are important (see :doc:`dbus_next services<dbus_next:high-level-service/index>`).

Debugging
---------
Pairing can be quite difficult to debug. In between testing attempts ensure that the peripheral has been unpaired from the host **and** vice versa. Using linux you can list paired devices using ``bluetoothctl list`` then remove any unwanted devices using ``bluetoothctl remove <device id>``. Additionally the linux bluetooth daemon stores persistent adapter metadata in the ``/var/lib/bluetooth/`` (see the bluetoothd manpages).

.. _pairing-io:

Pairing Security
----------------

+---------------------+-------------------------------------------------------------------------------------------------------------+
|                     | Initiator                                                                                                   |
|                     +---------------------+---------------------+---------------------+---------------------+---------------------+
| Responder           | Display Only        | Display YesNo       | Keyboard Only       | NoInput NoOutput    | Keyboard Display    |
+=====================+=====================+=====================+=====================+=====================+=====================+
| Display Only        | Just Works          | Just Works          | Passkey Entry       | Just Works          | Passkey Entry       |
+---------------------+---------------------+---------------------+---------------------+---------------------+---------------------+
| Display YesNo       | Just Works          | Numeric Comparison  | Passkey Entry       | Just Works          | Numeric Comparison  |
|                     |                     | (*Just Works\**)    |                     |                     | (*Passkey Entry\**) |
+---------------------+---------------------+---------------------+---------------------+---------------------+---------------------+
| Keyboard Only       | Passkey Entry       | Passkey Entry       | Passkey Entry       | Just Works          | Passkey Entry       |
+---------------------+---------------------+---------------------+---------------------+---------------------+---------------------+
| NoInput NoOutput    | Just Works          | Just Works          | Just Works          | Just Works          | Just Works          |
+---------------------+---------------------+---------------------+---------------------+---------------------+---------------------+
| Keyboard Display    | Passkey Entry       | Numeric Comparison  | Passkey Entry       | Just Works          | Numeric Comparison  |
|                     |                     | (*Passkey Entry\**) |                     |                     | (*Passkey Entry\**) |
+---------------------+---------------------+---------------------+---------------------+---------------------+---------------------+

| *\* Types apply to LE Legacy Pairing only (used when the initiator or responder do not support "LE Secure Connection" pairing).*
|

For completeness these pairing models are described below:

* Just Works - Devices may pair with no user interaction (eg a phone connecting to a headset without a display). Since this has no MITM protection, connections established using this model **may not perform authentication** (ie. access authenticated attributes).
* Numeric Comparison - The user verifies 6 digit codes displayed by each device match each other.
* Passkey Entry - The user is shown a 6 digit code on one device and inputs that code on the other.
* Out of Band - A MITM resistant channel is established between the two devices using a different protocol (eg NFC).

Note that IO Capability is not the only factor in selecting a pairing algorithm. Specifically:

* Where neither device requests Man-In-The-Middle (MITM) protection, Just Works pairing will be used. 
* Where both devices request it, OOB pairing will be used. 

.. seealso:: 

    Bluetooth SIG Pairing Overview
        `Part 1 <https://www.bluetooth.com/blog/bluetooth-pairing-part-1-pairing-feature-exchange/>`_
        `Part 2 <https://www.bluetooth.com/blog/bluetooth-pairing-part-2-key-generation-methods/>`_
        `Part 3 <https://www.bluetooth.com/blog/bluetooth-pairing-passkey-entry/>`_

    `Bluetooth Core Spec v5.2 <https://www.bluetooth.org/docman/handlers/downloaddoc.ashx?doc_id=478726>`_
        Vol 3, Part H, Table 2.8 (source of :ref:`pairing-io`)

    Bluez Documentation
        `Agent API <https://github.com/bluez/bluez/blob/master/doc/org.bluez.Agent.rst>`_
