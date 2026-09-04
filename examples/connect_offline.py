#!/usr/bin/env python
"""
Offline-mode connection example (see TUTORIAL.md, "Connecting to a
server (offline mode)").

Connects to an offline-mode server without any authentication:

    python examples/connect_offline.py
"""
import os
import sys
import time

# Allow running this example straight from the repository checkout.
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))

from minecraft.networking.connection import Connection  # noqa: E402


def main():
    connection = Connection(
        "localhost", 25565,      # server address and port
        username="MyBot",        # in-game player name
    )
    connection.connect()
    print("Connected in offline mode as 'MyBot'. Press Ctrl+C to quit.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Bye!")


if __name__ == "__main__":
    main()
