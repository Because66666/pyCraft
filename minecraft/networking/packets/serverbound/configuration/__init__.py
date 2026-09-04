from minecraft.networking.packets import (
    Packet, AbstractKeepAlivePacket, AbstractPluginMessagePacket
)

from minecraft.networking.types import Integer, VarInt, PrefixedArray

from ..play.client_settings_packet import ClientSettingsPacket
from ...clientbound.configuration import SelectKnownPacksPacket \
    as ClientboundSelectKnownPacksPacket


# The configuration state exists in protocol 764 (Minecraft 1.20.2) and
# later only.
def get_packets(context):
    packets = {
        ClientInformationPacket,
        PluginMessagePacket,
        FinishConfigurationPacket,
        KeepAlivePacket,
        PongPacket,
    }
    if context.protocol_later_eq(766):
        packets |= {
            SelectKnownPacksPacket,
        }
    return packets


class ClientInformationPacket(ClientSettingsPacket):
    # The 'client information' packet of the configuration state has the
    # same fields as the 'client settings' packet of the play state.
    @staticmethod
    def get_id(context):
        return 0x00

    packet_name = 'client information'


class PluginMessagePacket(AbstractPluginMessagePacket):
    @staticmethod
    def get_id(context):
        return 0x02 if context.protocol_later_eq(766) else \
               0x01

    packet_name = "plugin message"


class FinishConfigurationPacket(Packet):
    @staticmethod
    def get_id(context):
        return 0x03 if context.protocol_later_eq(766) else \
               0x02

    packet_name = "finish configuration"
    definition = []


class KeepAlivePacket(AbstractKeepAlivePacket):
    @staticmethod
    def get_id(context):
        return 0x04 if context.protocol_later_eq(766) else \
               0x03


class PongPacket(Packet):
    @staticmethod
    def get_id(context):
        return 0x05 if context.protocol_later_eq(766) else \
               0x04

    packet_name = "pong"

    # NOTE: the wire field is named 'id'; it is named 'ping_id' here, as
    # 'id' clashes with the packet ID attribute of 'Packet'.
    definition = [
        {'ping_id': Integer}]


class SelectKnownPacksPacket(Packet):
    # Note: added in protocol 766.
    id = 0x07

    packet_name = "select known packs"

    # The record type of the 'packs' array is shared with the clientbound
    # 'select known packs' packet.
    KnownPack = ClientboundSelectKnownPacksPacket.KnownPack

    definition = [
        {'packs': PrefixedArray(VarInt, KnownPack)}]
