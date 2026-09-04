# -*- coding: utf-8 -*-
"""Tests for 'minecraft.networking.chat_signing'.

The expected signable byte strings were generated with the reference
implementation (node-minecraft-protocol's 'concat' over protodef types),
so these tests pin byte-level compatibility with vanilla servers.
"""
import hashlib
import unittest

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from minecraft.networking.chat_signing import (
    ProfileKey, ChatSigner, ChatSession, LastSeenMessages760,
    LastSeenMessages761, compute_checksum, signable_759, body_digest_760,
    signable_760, signable_761,
)
from minecraft.networking.connection import ConnectionContext
from minecraft.networking.packets import serverbound

SENDER = '12345678-1234-5678-1234-567812345678'
SESSION = '87654321-4321-8765-4321-876543218765'
SALT = 0x1122334455667788
TIMESTAMP_MS = 1693478000123
MESSAGE = 'hello world'
ACK_1 = bytes([0xAA]) * 256
ACK_2 = bytes([0xBB]) * 256

# Reference outputs produced by node-minecraft-protocol's primitives.
S761_HEX = (
    '00000001'                              # signature version
    '12345678123456781234567812345678'      # sender UUID
    '87654321432187654321876543218765'      # session UUID
    '00000000'                              # message index
    '1122334455667788'                      # salt
    '0000000064f06c70'                      # timestamp, seconds
    '0000000b'                              # message length (i32)
    '68656c6c6f20776f726c64'                # "hello world"
    '00000000')                             # no acknowledgements
B760_DIGEST_HEX = \
    'aa9845de5128007d033fdd268554f82d17c25b1308a12d77474f58d205b305df'
S759_HEX = (
    '1122334455667788'                      # salt
    '12345678123456781234567812345678'      # sender UUID
    '0000000064f06c70'                      # timestamp, seconds
    '7b2274657874223a2268656c6c6f20776f726c64227d')  # {"text":...}


def make_profile_key(expires_at='2999-08-25T14:20:21.8213516Z'):
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()).decode('ascii')
    public_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo).decode('ascii')
    certificates = {
        'keyPair': {'privateKey': private_pem, 'publicKey': public_pem},
        'publicKeySignature': 'AAECAw==',
        'publicKeySignatureV2': 'BQYHCA==',
        'expiresAt': expires_at,
        'refreshedAfter': '2023-08-25T14:20:21.8213516Z',
    }
    return ProfileKey.from_certificates(certificates)


def make_signer(context, expires_at='2999-08-25T14:20:21.8213516Z'):
    signer = ChatSigner(make_profile_key(expires_at), SENDER)
    signer.begin_play(context)
    return signer


class ProfileKeyTest(unittest.TestCase):
    def test_from_certificates(self):
        profile_key = make_profile_key()
        self.assertEqual(profile_key.signature_v1, b'\x00\x01\x02\x03')
        self.assertEqual(profile_key.signature_v2, b'\x05\x06\x07\x08')
        self.assertFalse(profile_key.is_expired())

        # The public key must round-trip through its DER encoding.
        public_key = serialization.load_der_public_key(
            profile_key.public_key_der)
        self.assertEqual(
            public_key.public_numbers(),
            profile_key.private_key.public_key().public_numbers())

    def test_expiry_parsing(self):
        profile_key = make_profile_key('2023-08-25T14:20:21.8213516Z')
        self.assertEqual(profile_key.expires_at_ms, 1692973221821)
        self.assertTrue(profile_key.is_expired())

        # Timestamps without a fractional part are also accepted.
        profile_key = make_profile_key('2023-08-25T14:20:21Z')
        self.assertEqual(profile_key.expires_at_ms, 1692973221000)

    def test_sign_and_verify(self):
        profile_key = make_profile_key()
        signature = profile_key.sign(b'data')
        self.assertEqual(len(signature), 256)
        serialization.load_der_public_key(profile_key.public_key_der) \
            .verify(signature, b'data', padding.PKCS1v15(), hashes.SHA256())


class SignableVectorTest(unittest.TestCase):
    def test_759(self):
        self.assertEqual(
            signable_759(SENDER, MESSAGE, TIMESTAMP_MS, SALT).hex(),
            S759_HEX)

    def test_760_body_digest(self):
        digest = body_digest_760(MESSAGE, TIMESTAMP_MS, SALT, [])
        self.assertEqual(digest.hex(), B760_DIGEST_HEX)

    def test_760_body_digest_with_previous_messages(self):
        previous = [('aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
                     bytes([0xCC]) * 256)]
        digest = body_digest_760(MESSAGE, TIMESTAMP_MS, SALT, previous)
        expected_input = bytes.fromhex(
            '1122334455667788' '0000000064f06c70'
            '68656c6c6f20776f726c64' '46'
            '46' 'aaaaaaaabbbbccccddddeeeeeeeeeeee'
            + 'cc' * 256)
        self.assertEqual(digest, hashlib.sha256(expected_input).digest())

    def test_760_signable(self):
        digest = bytes.fromhex(B760_DIGEST_HEX)
        self.assertEqual(
            signable_760(SENDER, digest).hex(),
            '12345678123456781234567812345678' + B760_DIGEST_HEX)
        previous_signature = bytes([0xDD]) * 256
        self.assertEqual(
            signable_760(SENDER, digest, previous_signature),
            previous_signature + bytes.fromhex(
                '12345678123456781234567812345678' + B760_DIGEST_HEX))

    def test_761(self):
        self.assertEqual(
            signable_761(SENDER, SESSION, 0, MESSAGE, TIMESTAMP_MS, SALT,
                         []).hex(),
            S761_HEX)

    def test_761_with_acknowledgements(self):
        signable = signable_761(SENDER, SESSION, 3, MESSAGE, TIMESTAMP_MS,
                                SALT, [ACK_1, ACK_2])
        self.assertTrue(signable.startswith(bytes.fromhex(
            S761_HEX.replace('00000000', '00000003', 1)
            [:8 + 32 + 32 + 8])))
        self.assertTrue(signable.endswith(bytes.fromhex('00000002')
                                          + ACK_1 + ACK_2))

    def test_checksum(self):
        self.assertEqual(compute_checksum([]), 1)
        self.assertEqual(compute_checksum([ACK_1, ACK_2]), 225)


class LastSeenMessages760Test(unittest.TestCase):
    def test_newest_first_and_per_sender_dedup(self):
        tracker = LastSeenMessages760()
        self.assertFalse(tracker.push('a', None))   # unsigned: not tracked
        self.assertFalse(tracker.push('a', b''))
        tracker.push('a', b'1')
        tracker.push('b', b'2')
        tracker.push('a', b'3')  # replaces the earlier entry from 'a'
        self.assertEqual(tracker.entries, [('a', b'3'), ('b', b'2')])

    def test_capacity(self):
        tracker = LastSeenMessages760()
        for i in range(10):
            tracker.push(str(i), bytes([i]))
        self.assertEqual(len(tracker.entries), 5)
        self.assertEqual(tracker.entries[0], ('9', bytes([9])))


class LastSeenMessages761Test(unittest.TestCase):
    def test_acknowledge_bitset_and_order(self):
        tracker = LastSeenMessages761()
        self.assertFalse(tracker.push(None))
        tracker.push(ACK_1)
        tracker.push(ACK_2)
        self.assertEqual(tracker.pending, 2)
        bitset, signatures = tracker.acknowledge()
        # The window ends at the newest message: bit 19 is the most
        # recently seen message.
        self.assertEqual(bitset, b'\x00\x00\x0c')
        self.assertEqual(signatures, [ACK_1, ACK_2])  # oldest first

    def test_ring_wraparound(self):
        tracker = LastSeenMessages761()
        for i in range(21):
            tracker.push(bytes([i + 1]))
        # The first signature was evicted; the window starts at slot 1.
        bitset, signatures = tracker.acknowledge()
        self.assertEqual(len(signatures), 20)
        self.assertEqual(signatures[0], bytes([2]))
        self.assertEqual(bitset, b'\xff\xff\x0f')
        # The checksum follows the ring's slot order, matching
        # node-minecraft-protocol.
        self.assertEqual(tracker.checksum(), compute_checksum(
            [bytes([21])] + [bytes([i + 1]) for i in range(1, 20)]))


class ChatSignerTest(unittest.TestCase):
    def verify(self, profile_key, signature, data):
        serialization.load_der_public_key(profile_key.public_key_der) \
            .verify(signature, data, padding.PKCS1v15(), hashes.SHA256())

    def make_packet(self, context):
        packet = serverbound.play.ChatPacket(context)
        packet.message = MESSAGE
        packet.timestamp = TIMESTAMP_MS
        packet.salt = SALT
        return packet

    def test_759(self):
        context = ConnectionContext(protocol_version=759)
        signer = make_signer(context)
        packet = self.make_packet(context)
        signer.sign_chat_packet(context, packet)
        self.verify(signer.profile_key, packet.signature, signable_759(
            SENDER, MESSAGE, TIMESTAMP_MS, SALT))

    def test_760_chains_own_messages(self):
        context = ConnectionContext(protocol_version=760)
        signer = make_signer(context)

        packet = self.make_packet(context)
        signer.sign_chat_packet(context, packet)
        digest = body_digest_760(MESSAGE, TIMESTAMP_MS, SALT, [])
        self.verify(signer.profile_key, packet.signature,
                    signable_760(SENDER, digest))
        self.assertEqual(packet.previous_messages, [])

        # The second message chains onto the signature of the first.
        packet2 = self.make_packet(context)
        signer.sign_chat_packet(context, packet2)
        self.verify(signer.profile_key, packet2.signature,
                    signable_760(SENDER, digest, packet.signature))

    def test_760_includes_last_seen(self):
        context = ConnectionContext(protocol_version=760)
        signer = make_signer(context)
        other = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
        signer.observe_player_chat(other, ACK_1)
        packet = self.make_packet(context)
        signer.sign_chat_packet(context, packet)
        digest = body_digest_760(MESSAGE, TIMESTAMP_MS, SALT,
                                 [(other, ACK_1)])
        self.verify(signer.profile_key, packet.signature,
                    signable_760(SENDER, digest))
        self.assertEqual(len(packet.previous_messages), 1)
        self.assertEqual(packet.previous_messages[0].message_sender, other)
        self.assertEqual(
            packet.previous_messages[0].message_signature, ACK_1)

    def test_761(self):
        context = ConnectionContext(protocol_version=770)
        signer = make_signer(context)
        self.assertIsInstance(signer.last_seen_761, LastSeenMessages761)
        self.assertIsNone(signer.last_seen_760)

        # Without a session, chat stays unsigned.
        packet = self.make_packet(context)
        signer.sign_chat_packet(context, packet)
        self.assertIsNone(packet.signature)

        session = signer.start_session()
        self.assertIsInstance(session, ChatSession)
        signer.observe_player_chat('ignored', ACK_1)
        signer.observe_player_chat('ignored', ACK_2)

        packet = self.make_packet(context)
        signer.sign_chat_packet(context, packet)
        self.assertEqual(len(packet.signature), 256)
        self.assertEqual(packet.offset, 2)
        self.assertEqual(packet.acknowledged, b'\x00\x00\x0c')
        self.assertEqual(packet.checksum, 225)
        self.assertEqual(signer.last_seen_761.pending, 0)
        self.assertEqual(session.index, 1)
        self.verify(signer.profile_key, packet.signature, signable_761(
            SENDER, session.uuid, 0, MESSAGE, TIMESTAMP_MS, SALT,
            [ACK_1, ACK_2]))

    def test_761_acknowledgement_backlog(self):
        context = ConnectionContext(protocol_version=761)
        signer = make_signer(context)
        for i in range(64):
            self.assertIsNone(
                signer.observe_player_chat('a', bytes([i + 1])))
        self.assertEqual(signer.observe_player_chat('a', bytes([65])), 65)
        self.assertEqual(signer.last_seen_761.pending, 0)

    def test_no_resign(self):
        context = ConnectionContext(protocol_version=770)
        signer = make_signer(context)
        signer.start_session()
        packet = self.make_packet(context)
        packet.signature = b'already signed'
        signer.sign_chat_packet(context, packet)
        self.assertEqual(packet.signature, b'already signed')

    def test_expired_key_not_used(self):
        context = ConnectionContext(protocol_version=770)
        signer = make_signer(context, expires_at='2023-08-25T14:20:21Z')
        signer.start_session()
        packet = self.make_packet(context)
        signer.sign_chat_packet(context, packet)
        self.assertIsNone(packet.signature)

    def test_old_protocols_not_signed(self):
        context = ConnectionContext(protocol_version=758)
        signer = make_signer(context)
        packet = self.make_packet(context)
        signer.sign_chat_packet(context, packet)
        self.assertIsNone(packet.signature)


class SigningPacketTest(unittest.TestCase):
    def test_player_session_packet_round_trip(self):
        for protocol_version, packet_id in ((761, 0x20), (762, 0x06),
                                            (766, 0x07), (768, 0x08),
                                            (771, 0x09)):
            context = ConnectionContext(protocol_version=protocol_version)
            self.assertIn(serverbound.play.PlayerSessionPacket,
                          serverbound.play.get_packets(context))
            packet = serverbound.play.PlayerSessionPacket(context)
            self.assertEqual(packet.id, packet_id)

    def test_chat_acknowledgement_packet_ids(self):
        for protocol_version, packet_id in ((761, 0x03), (768, 0x04),
                                            (771, 0x05)):
            context = ConnectionContext(protocol_version=protocol_version)
            self.assertIn(serverbound.play.ChatAcknowledgementPacket,
                          serverbound.play.get_packets(context))
            packet = serverbound.play.ChatAcknowledgementPacket(context)
            self.assertEqual(packet.id, packet_id)

    def test_login_start_with_profile_key(self):
        from minecraft.networking.packets import PacketBuffer
        from minecraft.networking.types import VarInt

        profile_key = make_profile_key()
        for protocol_version, expect_v1 in ((759, True), (760, False)):
            context = ConnectionContext(protocol_version=protocol_version)
            packet = serverbound.login.LoginStartPacket(context)
            packet.name = 'Steve'
            packet.profile_key = profile_key
            if protocol_version >= 760:
                packet.player_uuid = SENDER

            buffer = PacketBuffer()
            packet.write(buffer)
            buffer.reset_cursor()
            VarInt.read(buffer)  # length
            VarInt.read(buffer)  # packet id

            read = serverbound.login.LoginStartPacket(context)
            read.read(buffer)
            self.assertEqual(read.name, 'Steve')
            self.assertEqual(read.signature_timestamp,
                             profile_key.expires_at_ms)
            self.assertEqual(read.signature_public_key,
                             profile_key.public_key_der)
            self.assertEqual(read.signature,
                             profile_key.signature_v1 if expect_v1
                             else profile_key.signature_v2)

    def test_login_start_without_profile_key(self):
        from minecraft.networking.packets import PacketBuffer
        from minecraft.networking.types import VarInt

        for protocol_version in (759, 760):
            context = ConnectionContext(protocol_version=protocol_version)
            packet = serverbound.login.LoginStartPacket(context)
            packet.name = 'Steve'
            if protocol_version >= 760:
                packet.player_uuid = SENDER

            buffer = PacketBuffer()
            packet.write(buffer)
            buffer.reset_cursor()
            VarInt.read(buffer)  # length
            VarInt.read(buffer)  # packet id

            read = serverbound.login.LoginStartPacket(context)
            read.read(buffer)
            self.assertEqual(read.name, 'Steve')
            self.assertIsNone(read.signature)


class ChatCommandPacketTest(unittest.TestCase):
    def roundtrip(self, context, packet):
        from minecraft.networking.packets import PacketBuffer
        from minecraft.networking.types import VarInt

        buffer = PacketBuffer()
        packet.write(buffer)
        buffer.reset_cursor()
        VarInt.read(buffer)  # length
        VarInt.read(buffer)  # packet id
        read = serverbound.play.ChatCommandPacket(context)
        read.read(buffer)
        return read

    def test_ids_and_registration(self):
        cases = ((759, 0x03), (760, 0x04), (765, 0x04), (766, 0x04),
                 (768, 0x05), (771, 0x06))
        for protocol_version, packet_id in cases:
            context = ConnectionContext(protocol_version=protocol_version)
            self.assertIn(serverbound.play.ChatCommandPacket,
                          serverbound.play.get_packets(context))
            packet = serverbound.play.ChatCommandPacket(context)
            self.assertEqual(packet.id, packet_id)

        context = ConnectionContext(protocol_version=758)
        self.assertNotIn(serverbound.play.ChatCommandPacket,
                         serverbound.play.get_packets(context))

    def test_round_trip_all_eras(self):
        for protocol_version in (759, 760, 761, 765, 766):
            context = ConnectionContext(protocol_version=protocol_version)
            packet = serverbound.play.ChatCommandPacket(context)
            packet.command = 'help'
            packet.timestamp = TIMESTAMP_MS
            packet.salt = SALT
            read = self.roundtrip(context, packet)
            self.assertEqual(read.command, 'help')
            if protocol_version < 766:
                self.assertEqual(read.timestamp, TIMESTAMP_MS)
                self.assertEqual(read.salt, SALT)
                self.assertEqual(read.argument_signatures, [])

    def test_prepare_command_packet_761(self):
        context = ConnectionContext(protocol_version=761)
        signer = make_signer(context)
        signer.observe_player_chat(SENDER, ACK_1)
        signer.observe_player_chat(SENDER, ACK_2)

        packet = serverbound.play.ChatCommandPacket(context)
        packet.command = 'help'
        packet.timestamp = TIMESTAMP_MS
        packet.salt = SALT
        signer.prepare_command_packet(context, packet)
        self.assertEqual(packet.offset, 2)
        self.assertEqual(packet.acknowledged, b'\x00\x00\x0c')
        self.assertEqual(signer.last_seen_761.pending, 0)

        read = self.roundtrip(context, packet)
        self.assertEqual(read.offset, 2)
        self.assertEqual(read.acknowledged, b'\x00\x00\x0c')

    def test_prepare_command_packet_760(self):
        context = ConnectionContext(protocol_version=760)
        signer = make_signer(context)
        signer.observe_player_chat(SENDER, ACK_1)

        packet = serverbound.play.ChatCommandPacket(context)
        packet.command = 'msg Steve hello'
        packet.timestamp = TIMESTAMP_MS
        packet.salt = SALT
        signer.prepare_command_packet(context, packet)
        self.assertEqual(len(packet.previous_messages), 1)

        read = self.roundtrip(context, packet)
        self.assertEqual(len(read.previous_messages), 1)
        self.assertEqual(
            read.previous_messages[0].message_signature, ACK_1)
        self.assertFalse(read.signed_preview)
        self.assertIsNone(read.last_rejected_message)

    def test_prepare_command_packet_759(self):
        context = ConnectionContext(protocol_version=759)
        signer = make_signer(context)
        packet = serverbound.play.ChatCommandPacket(context)
        packet.command = 'help'
        signer.prepare_command_packet(context, packet)
        self.assertNotEqual(packet.timestamp, 0)
        self.assertNotEqual(packet.salt, 0)

    def test_prepare_command_packet_untouched_eras(self):
        # Protocol 766 and later carry no signing fields at all.
        context = ConnectionContext(protocol_version=766)
        signer = make_signer(context)
        packet = serverbound.play.ChatCommandPacket(context)
        packet.command = 'help'
        signer.prepare_command_packet(context, packet)
        self.assertEqual(packet.timestamp, 0)
        self.assertEqual(packet.salt, 0)
