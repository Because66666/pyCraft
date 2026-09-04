from minecraft.networking.packets import (
    Packet, AbstractKeepAlivePacket, AbstractPluginMessagePacket
)

from minecraft.networking.types import (
    Type, Integer, String, NBT, VarInt, PrefixedArray, MutableRecord,
)


# The configuration state exists in protocol 764 (Minecraft 1.20.2) and
# later only.
def get_packets(context):
    packets = {
        PluginMessagePacket,
        DisconnectPacket,
        FinishConfigurationPacket,
        KeepAlivePacket,
        PingPacket,
    }
    if context.protocol_later_eq(766):
        packets |= {
            SelectKnownPacksPacket,
        }
    return packets


class PluginMessagePacket(AbstractPluginMessagePacket):
    @staticmethod
    def get_id(context):
        return 0x01 if context.protocol_later_eq(766) else \
               0x00

    packet_name = "plugin message"


class DisconnectPacket(Packet):
    @staticmethod
    def get_id(context):
        return 0x02 if context.protocol_later_eq(766) else \
               0x01

    packet_name = "disconnect"

    get_definition = staticmethod(lambda context: [
        {'json_data': NBT if context.protocol_later_eq(765) else String},
    ])


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


class PingPacket(Packet):
    @staticmethod
    def get_id(context):
        return 0x05 if context.protocol_later_eq(766) else \
               0x04

    packet_name = "ping"

    # NOTE: the wire field is named 'id'; it is named 'ping_id' here, as
    # 'id' clashes with the packet ID attribute of 'Packet'.
    definition = [
        {'ping_id': Integer}]


class SelectKnownPacksPacket(Packet):
    # Note: added in protocol 766.
    id = 0x0E

    packet_name = "select known packs"

    class KnownPack(MutableRecord, Type):
        """ A single entry of the 'packs' array of the 'select known packs'
            packets (protocols 766 and later). """
        __slots__ = 'namespace', 'id', 'version'

        @classmethod
        def read(cls, file_object):
            return cls(namespace=String.read(file_object),
                       id=String.read(file_object),
                       version=String.read(file_object))

        @classmethod
        def send(cls, record, socket):
            String.send(record.namespace, socket)
            String.send(record.id, socket)
            String.send(record.version, socket)

    definition = [
        {'packs': PrefixedArray(VarInt, KnownPack)}]
