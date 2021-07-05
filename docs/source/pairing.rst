Pairing
=======
Before pairing devices will exchange their input/ output capabilities in order to select a pairing approach.
In some situations **out of band (OOB)** data (using alternative communication channels like NFC) may also be used in pairing though this is currently **unsupported**.

Pairing can be quite difficult to debug.
In between attempts you should make sure to fully remove both the peripheral from the host and the host from the peripheral.
Using bluez you can list paired devices using ``bluetoothctl list`` then remove any unwanted devices using ``bluetoothctl remove <device id>``.

Agents
------

An agent is a program that bluez uses to interface with the user during pairing.
bluez uses agents to determine what pairing mode should be used based on their indicated input/ output capabilites.

Selecting an Agent
------------------

There are three sources of potential agents:

* Use a :ref:`bluez built in agent <bluez agent>` (Not recomended)
* Use a :ref:`bluez_peripheral built in agent <bluez_peripheral agent>` (NoInputNoOutput or YesNoInput only)
* Use a :ref:`custom agent <custom agent>`

.. _bluez agent:

bluez Agents
------------

bluez supports a number of built in agents.
You can select an agent with given capability by using the following command in your terminal::

    bluetoothctl agent <capability>

This approach is not recomended since the bluez agents seem to be slightly unreliable.

.. _bluez_peripheral agent:

bluez_peripheral Agents
-----------------------

Using a bluez_peripheral agent is the preferred approach where possible. The README makes use of a bluez agent using the following code:

.. code-block:: python

    from bluez_peripheral.agent import NoIoAgent

    agent = NoIoAgent()
    await agent.register(bus)

Note that if using a bluez_peripheral or custom agent your program must be run with root permissions.
Without root permission you do not have permission to set the default agent which is required to intercept incoming pairing requests.

.. _custom agent:

Custom Agents
-------------

You can write a custom agent by subclassing the :class:`bluez_peripheral.agent.BaseAgent` in the same way as the built in agents.
The recomended approach is first to instance and register the :class:`bluez_peripheral.agent.TestAgent` with your chosen capability setting.

.. code-block:: python

    from bluez_peripheral.agent import TestAgent

    agent = TestAgent()
    await agent.register(bus)

Once you've registered this agent, assuming that you are broadcasting a valid advertisment, you may connect to your peripheral from another device.
During the pairing process the test agent will encounter breakpoints whenever one of its methods is called.
To implement your agent you should check which methods are called during the pairing process then implement them as required using the test agent as a template.
