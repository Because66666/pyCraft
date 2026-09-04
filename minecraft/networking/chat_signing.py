"""Chat message signing for Minecraft 1.19 and later (protocols 759+).

Implements the client side of the 'secure chat' system: a profile public
key obtained from the Minecraft services API ('player/certificates') is
registered with the server during login, and outgoing chat messages are
signed with the associated RSA private key so that servers running with
'enforce-secure-chat=true' accept them.

The wire-level schemes are ported from node-minecraft-protocol
('src/client/chat.js'), whose behavior is verified against vanilla
servers; the byte-level layouts here mirror it exactly.
"""
import calendar
import hashlib
import json
import secrets
import struct
import time
import uuid as uuid_module
from base64 import b64decode
from datetime import datetime

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

__all__ = [
    'ProfileKey', 'ChatSession', 'ChatSigner', 'LastSeenMessages760',
    'LastSeenMessages761', 'compute_checksum', 'signable_759',
    'body_digest_760', 'signable_760', 'signable_761',
]


class ProfileKey(object):
    """ A player's chat-signing key pair and its Mojang-issued signatures,
        as returned by the 'player/certificates' Minecraft services
        endpoint. """

    def __init__(self, private_key, public_key_der, expires_at_ms,
                 signature_v1, signature_v2):
        self.private_key = private_key      # cryptography RSA private key
        self.public_key_der = public_key_der  # X.509 SubjectPublicKeyInfo
        self.expires_at_ms = expires_at_ms
        # 'signature_v1' signs the public key only; 'signature_v2' signs
        # the expiry timestamp together with the public key (1.19.2+).
        self.signature_v1 = signature_v1
        self.signature_v2 = signature_v2

    @classmethod
    def from_certificates(cls, certificates):
        """ Builds a 'ProfileKey' from the dict returned by the Minecraft
            services API (see 'MicrosoftAuthenticationToken.authenticate'
            with 'fetch_certificates=True'). """
        private_key = serialization.load_pem_private_key(
            certificates['keyPair']['privateKey'].encode('utf-8'),
            password=None)
        public_key = serialization.load_pem_public_key(
            certificates['keyPair']['publicKey'].encode('utf-8'))
        public_key_der = public_key.public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo)
        return cls(
            private_key=private_key,
            public_key_der=public_key_der,
            expires_at_ms=_iso8601_to_epoch_ms(certificates['expiresAt']),
            signature_v1=b64decode(certificates['publicKeySignature']),
            signature_v2=b64decode(certificates['publicKeySignatureV2']))

    def is_expired(self, now_ms=None):
        """ True if the key has passed its Mojang-issued expiry time. """
        if now_ms is None:
            now_ms = int(time.time() * 1000)
        return now_ms >= self.expires_at_ms

    def sign(self, data):
        """ Signs 'data' with the profile key (RSA with SHA-256). """
        return self.private_key.sign(
            data, padding.PKCS1v15(), hashes.SHA256())


class ChatSession(object):
    """ A chat session as used by protocols 761 and later (1.19.3+): a
        random UUID identifying the session, and the index of the next
        signed message within it. """

    def __init__(self):
        self.uuid = uuid_module.uuid4()
        self.index = 0


class LastSeenMessages760(object):
    """ Tracks the last seen signed player chat messages for protocol 760
        (1.19.1/2): at most five entries from distinct senders, newest
        first. Mirrors node-minecraft-protocol's 'LastSeenMessages'. """
    capacity = 5

    def __init__(self):
        # A list of (sender_uuid, signature) tuples, newest first.
        self.entries = []

    def push(self, sender_uuid, signature):
        """ Records a message; unsigned messages are not tracked. Only the
            newest message of each sender is kept. """
        if not signature:
            return False
        entries = [(sender_uuid, signature)]
        for entry in self.entries:
            if entry[0] != sender_uuid:
                entries.append(entry)
        self.entries = entries[:self.capacity]
        return True


class LastSeenMessages761(object):
    """ Tracks the last seen signed player chat messages for protocols 761
        and later (1.19.3+): a ring buffer of at most twenty signatures,
        plus the number of messages not yet acknowledged to the server.
        Mirrors node-minecraft-protocol's
        'LastSeenMessagesWithInvalidation'. """
    capacity = 20

    def __init__(self):
        self.slots = [None] * self.capacity
        self.offset = 0
        self.pending = 0

    def push(self, signature):
        """ Records a message signature; unsigned messages are not
            tracked. """
        if not signature:
            return False
        self.slots[self.offset] = signature
        self.offset = (self.offset + 1) % self.capacity
        self.pending += 1
        return True

    def acknowledge(self):
        """ Returns '(bitset, signatures)': the 3-byte bitset sent in the
            'acknowledged' field of outgoing chat, and the corresponding
            signature list (oldest first) included in the signed data. """
        bits = 0
        signatures = []
        for i in range(self.capacity):
            signature = self.slots[(self.offset + i) % self.capacity]
            if signature is not None:
                bits |= 1 << i
                signatures.append(signature)
        return bits.to_bytes(3, 'little'), signatures

    def checksum(self):
        """ The trailing checksum byte of chat messages in protocols 770
            and later. """
        return compute_checksum(
            [signature for signature in self.slots if signature is not None])


def compute_checksum(signatures):
    """ Computes Java's 'Arrays.hashCode' over a list of signature byte
        strings, reduced to a single byte (protocols 770+). """
    result = 1
    for signature in signatures:
        signature_hash = 1
        for byte in bytearray(signature):
            signature_hash = (31 * signature_hash + byte) & 0xFFFFFFFF
        result = (31 * result + signature_hash) & 0xFFFFFFFF
    result &= 0xFF
    return result or 1


class ChatSigner(object):
    """ Per-connection state and logic for signing outgoing chat messages
        and acknowledging incoming ones. """

    def __init__(self, profile_key, player_uuid):
        self.profile_key = profile_key
        self.player_uuid = uuid_module.UUID(player_uuid)
        self.session = None            # ChatSession for protocols 761+.
        self.last_seen_760 = None      # LastSeenMessages760, protocol 760.
        self.last_seen_761 = None      # LastSeenMessages761, protocols 761+.
        self._last_own_signature = None  # Message chain for protocol 760.

    def begin_play(self, context):
        """ (Re)initialises per-play-state tracking for the given protocol
            version. """
        self.last_seen_761 = LastSeenMessages761() \
            if context.protocol_later_eq(761) else None
        self.last_seen_760 = LastSeenMessages760() \
            if context.protocol_in_range(760, 761) else None
        self._last_own_signature = None

    def start_session(self):
        """ Starts a new chat session (protocols 761+). """
        self.session = ChatSession()
        return self.session

    def observe_player_chat(self, sender_uuid, signature):
        """ Tracks an incoming signed player chat message. Returns the
            number of pending acknowledgements if an acknowledgement
            packet should be sent now, and None otherwise. """
        if self.last_seen_760 is not None:
            self.last_seen_760.push(sender_uuid, signature)
        elif self.last_seen_761 is not None:
            tracker = self.last_seen_761
            if tracker.push(signature) and tracker.pending > 64:
                pending = tracker.pending
                tracker.pending = 0
                return pending
        return None

    def prepare_command_packet(self, context, packet):
        """ Fills in the timestamp, salt and acknowledgement fields of a
            serverbound 'ChatCommandPacket' (protocols 759-765; protocol
            766 and later carry none of these fields). Commands themselves
            are never signed by pyCraft. """
        if context.protocol_earlier(759) or context.protocol_later_eq(766):
            return
        if packet.timestamp == 0:
            packet.timestamp = int(time.time() * 1000)
        if packet.salt == 0:
            packet.salt = _random_salt()
        if context.protocol_earlier(761):  # Protocol 760.
            if self.last_seen_760 is not None:
                packet.previous_messages = [
                    packet.PreviousMessage(
                        message_sender=sender, message_signature=signature)
                    for sender, signature in self.last_seen_760.entries]
        elif self.last_seen_761 is not None:  # Protocols 761-765.
            tracker = self.last_seen_761
            acknowledged, _signatures = tracker.acknowledge()
            packet.offset = tracker.pending
            packet.acknowledged = acknowledged
            tracker.pending = 0

    def sign_chat_packet(self, context, packet):
        """ Fills in the timestamp, salt, signature and acknowledgement
            fields of a serverbound 'ChatPacket'. Does nothing when the
            packet is already signed, the profile key has expired, or
            (in protocols 761+) no chat session has been started yet. """
        if context.protocol_earlier(759):
            return
        if packet.signature is not None or self.profile_key.is_expired():
            return
        if packet.timestamp == 0:
            packet.timestamp = int(time.time() * 1000)
        if packet.salt == 0:
            packet.salt = _random_salt()
        timestamp, salt = packet.timestamp, packet.salt

        if context.protocol_earlier(760):  # Protocol 759 (1.19).
            packet.signature = self.profile_key.sign(signable_759(
                self.player_uuid, packet.message, timestamp, salt))
        elif context.protocol_earlier(761):  # Protocol 760 (1.19.1/2).
            last_seen = self.last_seen_760.entries \
                if self.last_seen_760 is not None else []
            digest = body_digest_760(packet.message, timestamp, salt,
                                     last_seen)
            packet.signature = self.profile_key.sign(signable_760(
                self.player_uuid, digest, self._last_own_signature))
            self._last_own_signature = packet.signature
            packet.previous_messages = [
                packet.PreviousMessage(
                    message_sender=sender, message_signature=signature)
                for sender, signature in last_seen]
        else:  # Protocols 761 and later (1.19.3+).
            if self.session is None or self.last_seen_761 is None:
                return
            tracker = self.last_seen_761
            acknowledged, signatures = tracker.acknowledge()
            packet.signature = self.profile_key.sign(signable_761(
                self.player_uuid, self.session.uuid, self.session.index,
                packet.message, timestamp, salt, signatures))
            self.session.index += 1
            packet.offset = tracker.pending
            packet.acknowledged = acknowledged
            if context.protocol_later_eq(770):
                packet.checksum = tracker.checksum()
            tracker.pending = 0


def signable_759(sender_uuid, message, timestamp_ms, salt):
    """ The bytes signed by chat messages in protocol 759 (1.19). """
    json_data = json.dumps({'text': message},
                           separators=(',', ':'), ensure_ascii=False)
    return b''.join((
        _i64(salt), _uuid_bytes(sender_uuid), _i64(timestamp_ms // 1000),
        json_data.encode('utf-8')))


def body_digest_760(message, timestamp_ms, salt, last_seen, preview=None):
    """ The SHA-256 body digest of a chat message in protocol 760
        (1.19.1/2). 'last_seen' is a list of (sender_uuid, signature)
        tuples, newest first. """
    digest = hashlib.sha256()
    digest.update(_i64(salt))
    digest.update(_i64(timestamp_ms // 1000))
    digest.update(message.encode('utf-8'))
    digest.update(b'\x46')
    if preview is not None:
        digest.update(preview.encode('utf-8'))
    for sender_uuid, signature in last_seen:
        digest.update(b'\x46')
        digest.update(_uuid_bytes(sender_uuid))
        digest.update(signature)
    return digest.digest()


def signable_760(sender_uuid, digest, previous_own_signature=None):
    """ The bytes signed by chat messages in protocol 760 (1.19.1/2):
        the signature of the sender's own previous message (if any), the
        sender's UUID, and the body digest. """
    return (previous_own_signature or b'') \
        + _uuid_bytes(sender_uuid) + digest


def signable_761(sender_uuid, session_uuid, index, message, timestamp_ms,
                 salt, acknowledgements):
    """ The bytes signed by chat messages in protocols 761 and later
        (1.19.3+). 'acknowledgements' is a list of signature byte strings
        of recently seen messages, oldest first. """
    encoded = message.encode('utf-8')
    return b''.join(
        (_i32(1), _uuid_bytes(sender_uuid), _uuid_bytes(session_uuid),
         _i32(index), _i64(salt), _i64(timestamp_ms // 1000),
         _i32(len(encoded)), encoded,
         _i32(len(acknowledgements))) + tuple(acknowledgements))


def _uuid_bytes(value):
    return value.bytes if isinstance(value, uuid_module.UUID) \
        else uuid_module.UUID(value).bytes


def _i32(value):
    return struct.pack('>i', value)


def _i64(value):
    return struct.pack('>q', value)


def _random_salt():
    return int.from_bytes(secrets.token_bytes(8), 'big', signed=True)


def _iso8601_to_epoch_ms(text):
    """ Parses the ISO-8601 timestamps returned by the Minecraft services
        API (e.g. '2023-08-25T14:20:21.8213516Z') into epoch
        milliseconds. """
    text = text.rstrip('Z')
    if '.' in text:
        main, fraction = text.split('.')
        stamp = '%s.%s' % (main, (fraction + '000000')[:6])
        parsed = datetime.strptime(stamp, '%Y-%m-%dT%H:%M:%S.%f')
    else:
        parsed = datetime.strptime(text, '%Y-%m-%dT%H:%M:%S')
    return calendar.timegm(parsed.timetuple()) * 1000 \
        + parsed.microsecond // 1000
