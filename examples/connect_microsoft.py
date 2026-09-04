#!/usr/bin/env python
"""
Microsoft account (online-mode) connection example (see TUTORIAL.md,
"Connecting to a server (authenticated)").

Signs in with a Microsoft account via the OAuth 2.0 device-code flow --
no password is involved. On first run a verification URL and device
code are printed; open the URL in a browser and enter the code. The
tokens are cached (by default in ``~/.minecraft/nmp-cache/``) and reused
on later runs.

    python examples/connect_microsoft.py
"""
import os
import sys
import time

# Allow running this example straight from the repository checkout.
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))

from minecraft import authentication  # noqa: E402
from minecraft.exceptions import YggdrasilError  # noqa: E402
from minecraft.networking.connection import Connection  # noqa: E402


def on_device_code(data):
    """Called when the user must authorize the device code."""
    print("To sign in, open {0} and enter the code: {1}".format(
        data["verification_uri"], data["user_code"]))


def main():
    auth_token = authentication.MicrosoftAuthenticationToken()
    try:
        # The username (Microsoft account email) is only used to name
        # the cache files; it may be omitted.
        auth_token.authenticate("you@example.com",
                                on_device_code=on_device_code)
    except YggdrasilError as error:
        print("Authentication failed:", error)
        raise SystemExit(1)

    print("Logged in as: %s" % auth_token.username)

    connection = Connection("localhost", 25565, auth_token=auth_token)
    connection.connect()
    print("Connected. Press Ctrl+C to quit.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Bye!")


if __name__ == "__main__":
    main()
