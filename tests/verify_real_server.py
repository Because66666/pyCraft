"""End-to-end verification of pyCraft against a real Minecraft server.

This is NOT part of the automated test suite (it requires a locally
installed official server jar). Run it manually, e.g.:

    python tests/verify_real_server.py path/to/server/dir 1.20.1

The server directory must contain a server jar named
'<version>-server.jar' (or pass --jar), an 'eula.txt' with 'eula=true'
and a 'server.properties' with 'online-mode=false'.

The script starts the server, waits for it to load, connects a pyCraft
client, checks login, join game, position sync, keep-alive and chat,
then disconnects and stops the server. Exit status 0 means success.
"""

from __future__ import print_function

import argparse
import os
import subprocess
import sys
import threading
import time

from minecraft.networking.connection import Connection
from minecraft.networking.packets import clientbound, serverbound


class ServerProcess(object):
    """Runs a Minecraft server jar as a subprocess."""

    def __init__(self, server_dir, jar, java='java'):
        self.server_dir = server_dir
        self.lines = []
        self.ready = threading.Event()
        self.failed = threading.Event()
        self.process = subprocess.Popen(
            [java, '-Xmx2G', '-jar', jar, 'nogui'],
            cwd=server_dir, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
        self.reader = threading.Thread(target=self._read_output)
        self.reader.daemon = True
        self.reader.start()

    def _read_output(self):
        for raw in iter(self.process.stdout.readline, b''):
            line = raw.decode('utf-8', 'replace').rstrip()
            self.lines.append(line)
            print('[server] %s' % line)
            if 'Done (' in line:
                self.ready.set()
            if 'Negotiation cannot continue' in line:
                self.failed.set()

    def wait_ready(self, timeout):
        return self.ready.wait(timeout)

    def stop(self, timeout=120):
        if self.process.poll() is not None:
            return
        try:
            self.process.stdin.write(b'stop\n')
            self.process.stdin.flush()
        except (IOError, ValueError):
            pass
        try:
            self.process.wait(timeout)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        self.reader.join(5)

    def tail(self, count=20):
        return '\n'.join(self.lines[-count:])


def verify(server, mc_version, port):
    """Connect to a running server and check basic play-state behaviour."""
    events = dict.fromkeys(
        ['joined', 'positioned', 'keep_alive', 'disconnected'])
    reasons = []

    connection = Connection('127.0.0.1', port, username='pyCraftTest',
                            allowed_versions={mc_version})

    def set_event(name):
        def listener(packet):
            events[name] = packet
        return listener

    def on_disconnect(packet):
        events['disconnected'] = packet
        reasons.append(getattr(packet, 'json_data', '<no reason>'))

    connection.register_packet_listener(
        set_event('joined'), clientbound.play.JoinGamePacket)
    connection.register_packet_listener(
        set_event('positioned'),
        clientbound.play.PlayerPositionAndLookPacket)
    connection.register_packet_listener(
        set_event('keep_alive'), clientbound.play.KeepAlivePacket)
    connection.register_packet_listener(
        on_disconnect, clientbound.play.DisconnectPacket)

    connection.connect()

    def check(condition, message):
        if not condition:
            raise AssertionError(message)
        print('[check] OK: %s' % message)

    joined = _wait_for(events, 'joined', 60)
    check(joined, 'received join game packet (login succeeded)')

    positioned = _wait_for(events, 'positioned', 60)
    check(positioned, 'received player position and look packet')

    keep_alive = _wait_for(events, 'keep_alive', 40)
    check(keep_alive, 'received and answered keep alive (still connected)')

    chat = serverbound.play.ChatPacket()
    chat.message = 'Hello from pyCraft!'
    connection.write_packet(chat)
    print('[check] sent chat message: %r' % chat.message)
    time.sleep(5)
    check(events['disconnected'] is None and connection.connected,
          'still connected 5s after sending chat (reasons: %s)' % reasons)

    connection.disconnect()
    return True


def _wait_for(events, name, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if events[name] is not None:
            return events[name]
        time.sleep(0.05)
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('server_dir', help='directory of the server')
    parser.add_argument('mc_version', help="Minecraft version, e.g. '1.20.1'")
    parser.add_argument('--java', default='java', help='java executable')
    parser.add_argument('--jar', default=None,
                        help='server jar file name (default: '
                             '<mc_version>-server.jar)')
    parser.add_argument('--port', type=int, default=25565)
    parser.add_argument('--ready-timeout', type=int, default=300,
                        help='seconds to wait for the server to load')
    args = parser.parse_args(argv)

    jar = args.jar or ('%s-server.jar' % args.mc_version)
    if not os.path.isfile(os.path.join(args.server_dir, jar)):
        print('FAIL: server jar not found: %s' % jar)
        return 2

    server = ServerProcess(args.server_dir, jar, java=args.java)
    try:
        print('Waiting for the server to load (up to %ds)...'
              % args.ready_timeout)
        if not server.wait_ready(args.ready_timeout):
            print('FAIL: server did not become ready.\nLast server output:')
            print(server.tail())
            return 1

        try:
            verify(server, args.mc_version, args.port)
        except Exception as exc:
            print('FAIL: %s: %s' % (type(exc).__name__, exc))
            print('Last server output:')
            print(server.tail())
            return 1

        print('PASS: %s (protocol verification succeeded)'
              % args.mc_version)
        return 0
    finally:
        server.stop()


if __name__ == '__main__':
    sys.exit(main())
