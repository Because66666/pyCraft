from minecraft.networking.packets import Packet

from minecraft.networking.types import (
    VarInt, Boolean, Long, String, UUID, VarIntPrefixedByteArray,
    TrailingByteArray
)

import hashlib
import uuid


# Formerly known as state_login_serverbound.
def get_packets(context):
    packets = {
        LoginStartPacket,
        EncryptionResponsePacket
    }
    if context.protocol_later_eq(385):
        packets |= {
            PluginResponsePacket
        }
    if context.protocol_later_eq(764):
        packets |= {
            LoginAcknowledgedPacket
        }
    return packets


def offline_player_uuid(name):
    """ Derive the offline-mode player UUID from a username, in the same
        way as Java's 'UUID.nameUUIDFromBytes' applied to the string
        "OfflinePlayer:<name>": a version-3 (MD5) UUID with the version
        and variant bits set accordingly. """
    digest = bytearray(hashlib.md5(
        ('OfflinePlayer:%s' % name).encode('utf-8')).digest())
    digest[6] = digest[6] & 0x0F | 0x30  # Version 3 (MD5).
    digest[8] = digest[8] & 0x3F | 0x80  # IETF variant.
    return str(uuid.UUID(bytes=bytes(digest)))


class LoginStartPacket(Packet):
    @staticmethod
    def get_id(context):
        return 0x00 if context.protocol_later_eq(391) else \
               0x01 if context.protocol_later_eq(385) else \
               0x00

    packet_name = "login start"
    definition = [
        {'name': String}]

    def read(self, file_object):
        self.name = String.read(file_object)
        if self.context.protocol_in_range(759, 761):
            # Profile public-key signature data, removed in protocol 761.
            if Boolean.read(file_object):
                self.signature_timestamp = Long.read(file_object)
                self.signature_public_key = \
                    VarIntPrefixedByteArray.read(file_object)
                self.signature = VarIntPrefixedByteArray.read(file_object)
            else:
                self.signature = None
        if self.context.protocol_later_eq(764):
            # In protocol 764 and later, the player UUID is mandatory.
            self.player_uuid = UUID.read(file_object)
        elif self.context.protocol_later_eq(760):
            if Boolean.read(file_object):
                self.player_uuid = UUID.read(file_object)
            else:
                self.player_uuid = None

    def write_fields(self, packet_buffer):
        String.send(self.name, packet_buffer)
        if self.context.protocol_in_range(759, 761):
            # Profile public-key signature data, sent when chat signing
            # is available (see 'minecraft.networking.chat_signing').
            profile_key = getattr(self, 'profile_key', None)
            Boolean.send(profile_key is not None, packet_buffer)
            if profile_key is not None:
                Long.send(profile_key.expires_at_ms, packet_buffer)
                VarIntPrefixedByteArray.send(
                    profile_key.public_key_der, packet_buffer)
                # Protocol 760 covers both 1.19.1 (which expects the V1
                # signature) and 1.19.2 (V2); the two cannot be told apart
                # by protocol number, and 1.19.2 is by far the more common.
                if self.context.protocol_earlier(760):
                    signature = profile_key.signature_v1
                else:
                    signature = profile_key.signature_v2
                VarIntPrefixedByteArray.send(signature, packet_buffer)
        if self.context.protocol_later_eq(764):
            # In protocol 764 and later, the player UUID is mandatory.
            player_uuid = getattr(self, 'player_uuid', None)
            if player_uuid is None and self.name is not None:
                player_uuid = offline_player_uuid(self.name)
            if player_uuid is None:
                player_uuid = str(uuid.UUID(int=0))
            UUID.send(player_uuid, packet_buffer)
        elif self.context.protocol_later_eq(760):
            # pyCraft never sends a player UUID in the login start packet.
            Boolean.send(False, packet_buffer)


class LoginAcknowledgedPacket(Packet):
    # Note: added in protocol 764; acknowledges the 'login success' packet
    # and transitions the connection to the configuration state.
    id = 0x03

    packet_name = "login acknowledged"
    definition = []


class EncryptionResponsePacket(Packet):
    @staticmethod
    def get_id(context):
        return 0x01 if context.protocol_later_eq(391) else \
               0x02 if context.protocol_later_eq(385) else \
               0x01

    packet_name = "encryption response"
    definition = [
        {'shared_secret': VarIntPrefixedByteArray},
        {'verify_token': VarIntPrefixedByteArray}]

    def read(self, file_object):
        self.shared_secret = VarIntPrefixedByteArray.read(file_object)
        if self.context.protocol_in_range(759, 761):
            if Boolean.read(file_object):
                self.verify_token = VarIntPrefixedByteArray.read(file_object)
            else:
                self.verify_token = None
                self.salt = Long.read(file_object)
                self.message_signature = \
                    VarIntPrefixedByteArray.read(file_object)
        else:
            self.verify_token = VarIntPrefixedByteArray.read(file_object)

    def write_fields(self, packet_buffer):
        VarIntPrefixedByteArray.send(self.shared_secret, packet_buffer)
        if self.context.protocol_in_range(759, 761):
            has_verify_token = self.verify_token is not None
            Boolean.send(has_verify_token, packet_buffer)
            if not has_verify_token:
                Long.send(getattr(self, 'salt', 0), packet_buffer)
                VarIntPrefixedByteArray.send(
                    getattr(self, 'message_signature', b''), packet_buffer)
                return
        VarIntPrefixedByteArray.send(self.verify_token, packet_buffer)


class PluginResponsePacket(Packet):
    """ NOTE: see comments on 'clientbound.login.PluginRequestPacket' for
        important information on the usage of this packet.
    """

    @staticmethod
    def get_id(context):
        return 0x02 if context.protocol_later_eq(391) else \
               0x00

    packet_name = 'login plugin response'
    fields = (
        'message_id',  # str
        'successful',  # bool
        'data',        # bytes, or None if 'successful' is False
    )

    def read(self, file_object):
        self.message_id = VarInt.read(file_object)
        self.successful = Boolean.read(file_object)
        if self.successful:
            self.data = TrailingByteArray.read(file_object)
        else:
            self.data = None

    def write_fields(self, packet_buffer):
        VarInt.send(self.message_id, packet_buffer)
        successful = getattr(self, 'data', None) is not None
        successful = getattr(self, 'successful', successful)
        Boolean.send(successful, packet_buffer)
        if successful:
            TrailingByteArray.send(self.data, packet_buffer)
