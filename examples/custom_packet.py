#!/usr/bin/env python
"""
Custom packet example (see TUTORIAL.md, "Custom packets").

Shows how to define a packet class that pyCraft does not implement yet.
Run it to inspect the class; to actually send the packet, instantiate
it, assign the fields from its ``definition`` and pass it to
``connection.write_packet``.
"""
import os
import sys

# Allow running this example straight from the repository checkout.
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))

from minecraft.networking.packets import Packet  # noqa: E402
from minecraft.networking.types import VarInt, String  # noqa: E402


class MyCustomPacket(Packet):
    id = 0x00                      # packet id
    packet_name = "my packet"      # packet name (used in logs)
    definition = [                 # field definitions: name -> type
        {'some_id': VarInt},
        {'some_text': String},
    ]


# If the packet id or layout differs between protocol versions, override
# ``get_id(context)`` / ``get_definition(context)`` and dispatch on
# ``context.protocol_version`` instead of using the class attributes.


def main():
    packet = MyCustomPacket()
    packet.some_id = 42
    packet.some_text = "hello"
    print("Defined packet: %s" % packet)
    print("Definition: %s" % (MyCustomPacket.definition,))


if __name__ == "__main__":
    main()
