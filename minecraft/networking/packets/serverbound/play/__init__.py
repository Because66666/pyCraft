from minecraft.networking.packets import (
    Packet, AbstractKeepAlivePacket, AbstractPluginMessagePacket
)

from minecraft.networking.types import (
    Double, Float, Boolean, VarInt, Long, String, Byte, UnsignedByte, UUID,
    Position, Enum, RelativeHand, BlockFace, Vector, Direction,
    PositionAndLook, VarIntPrefixedByteArray, MutableRecord,
    multi_attribute_alias,
)

from .client_settings_packet import ClientSettingsPacket


# Formerly known as state_playing_serverbound.
def get_packets(context):
    packets = {
        KeepAlivePacket,
        ChatPacket,
        PositionAndLookPacket,
        AnimationPacket,
        ClientStatusPacket,
        ClientSettingsPacket,
        PluginMessagePacket,
        PlayerBlockPlacementPacket,
    }
    if context.protocol_later_eq(69):
        packets |= {
            UseItemPacket,
        }
    if context.protocol_later_eq(107):
        packets |= {
            TeleportConfirmPacket,
        }
    if context.protocol_later_eq(764):
        packets |= {
            ConfigurationAcknowledgedPacket,
        }
    if context.protocol_later_eq(766):
        packets |= {
            ChatCommandPacket,
        }
    return packets


class KeepAlivePacket(AbstractKeepAlivePacket):
    @staticmethod
    def get_id(context):
        return 0x1B if context.protocol_later_eq(771) else \
               0x1A if context.protocol_later_eq(768) else \
               0x18 if context.protocol_later_eq(766) else \
               0x15 if context.protocol_later_eq(765) else \
               0x14 if context.protocol_later_eq(764) else \
               0x12 if context.protocol_later_eq(762) else \
               0x11 if context.protocol_later_eq(761) else \
               0x12 if context.protocol_later_eq(760) else \
               0x11 if context.protocol_later_eq(759) else \
               0x0F if context.protocol_later_eq(755) else \
               0x10 if context.protocol_later_eq(712) else \
               0x0F if context.protocol_later_eq(471) else \
               0x10 if context.protocol_later_eq(464) else \
               0x0E if context.protocol_later_eq(389) else \
               0x0C if context.protocol_later_eq(386) else \
               0x0B if context.protocol_later_eq(345) else \
               0x0A if context.protocol_later_eq(343) else \
               0x0B if context.protocol_later_eq(336) else \
               0x0C if context.protocol_later_eq(318) else \
               0x0B if context.protocol_later_eq(107) else \
               0x00


class ChatPacket(Packet):
    @staticmethod
    def get_id(context):
        return 0x08 if context.protocol_later_eq(771) else \
               0x07 if context.protocol_later_eq(768) else \
               0x06 if context.protocol_later_eq(766) else \
               0x05 if context.protocol_later_eq(760) else \
               0x04 if context.protocol_later_eq(759) else \
               0x03 if context.protocol_later_eq(755) else \
               0x03 if context.protocol_later_eq(464) else \
               0x02 if context.protocol_later_eq(389) else \
               0x01 if context.protocol_later_eq(343) else \
               0x02 if context.protocol_later_eq(336) else \
               0x03 if context.protocol_later_eq(318) else \
               0x02 if context.protocol_later_eq(107) else \
               0x01

    @staticmethod
    def get_max_length(context):
        return 256 if context.protocol_later_eq(306) else \
               100

    @property
    def max_length(self):
        if self.context is not None:
            return self.get_max_length(self.context)

    packet_name = "chat"
    definition = [
        {'message': String}]

    # Default values of the fields introduced in protocol 759, so that an
    # unsigned chat message may be sent by setting only 'message'.
    timestamp = 0
    salt = 0
    signature = None
    signed_preview = False
    previous_messages = ()
    last_rejected_message = None
    offset = 0
    acknowledged = b'\x00\x00\x00'
    # The trailing checksum byte was added in protocol 770.
    checksum = 0

    class PreviousMessage(MutableRecord):
        __slots__ = 'message_sender', 'message_signature'

    def read(self, file_object):
        context = self.context
        self.message = String.read(file_object)
        if context.protocol_earlier(759):
            return
        self.timestamp = Long.read(file_object)
        self.salt = Long.read(file_object)
        if context.protocol_later_eq(761):
            if Boolean.read(file_object):
                self.signature = file_object.read(256)
            else:
                self.signature = None
            self.offset = VarInt.read(file_object)
            self.acknowledged = file_object.read(3)
            if context.protocol_later_eq(770):
                self.checksum = UnsignedByte.read(file_object)
            return
        self.signature = VarIntPrefixedByteArray.read(file_object)
        self.signed_preview = Boolean.read(file_object)
        if context.protocol_later_eq(760):
            self.previous_messages = []
            for i in range(VarInt.read(file_object)):
                self.previous_messages.append(ChatPacket.PreviousMessage(
                    message_sender=UUID.read(file_object),
                    message_signature=VarIntPrefixedByteArray.read(
                        file_object)))
            if Boolean.read(file_object):
                self.last_rejected_message = ChatPacket.PreviousMessage(
                    message_sender=UUID.read(file_object),
                    message_signature=VarIntPrefixedByteArray.read(
                        file_object))
            else:
                self.last_rejected_message = None

    def write_fields(self, packet_buffer):
        context = self.context
        String.send(self.message, packet_buffer)
        if context.protocol_earlier(759):
            return
        Long.send(self.timestamp, packet_buffer)
        Long.send(self.salt, packet_buffer)
        if context.protocol_later_eq(761):
            Boolean.send(self.signature is not None, packet_buffer)
            if self.signature is not None:
                packet_buffer.send(self.signature)
            VarInt.send(self.offset, packet_buffer)
            packet_buffer.send(self.acknowledged)
            if context.protocol_later_eq(770):
                UnsignedByte.send(self.checksum, packet_buffer)
            return
        signature = self.signature
        VarIntPrefixedByteArray.send(
            signature if signature is not None else b'', packet_buffer)
        Boolean.send(self.signed_preview, packet_buffer)
        if context.protocol_later_eq(760):
            VarInt.send(len(self.previous_messages), packet_buffer)
            for message in self.previous_messages:
                UUID.send(message.message_sender, packet_buffer)
                VarIntPrefixedByteArray.send(
                    message.message_signature, packet_buffer)
            Boolean.send(self.last_rejected_message is not None,
                         packet_buffer)
            if self.last_rejected_message is not None:
                UUID.send(
                    self.last_rejected_message.message_sender, packet_buffer)
                VarIntPrefixedByteArray.send(
                    self.last_rejected_message.message_signature,
                    packet_buffer)


class ChatCommandPacket(Packet):
    # Note: pyCraft supports this packet only in protocols 766 and later,
    # in which it carries no signature data.
    @staticmethod
    def get_id(context):
        return 0x06 if context.protocol_later_eq(771) else \
               0x05 if context.protocol_later_eq(768) else \
               0x04

    packet_name = "chat command"
    definition = [
        {'command': String}]


class ConfigurationAcknowledgedPacket(Packet):
    # Note: added in protocol 764; acknowledges the clientbound
    # 'start configuration' packet.
    @staticmethod
    def get_id(context):
        return 0x0F if context.protocol_later_eq(771) else \
               0x0E if context.protocol_later_eq(768) else \
               0x0C if context.protocol_later_eq(766) else \
               0x0B

    packet_name = "configuration acknowledged"
    definition = []


class PositionAndLookPacket(Packet):
    @staticmethod
    def get_id(context):
        return 0x1E if context.protocol_later_eq(771) else \
               0x1D if context.protocol_later_eq(768) else \
               0x1B if context.protocol_later_eq(766) else \
               0x18 if context.protocol_later_eq(765) else \
               0x17 if context.protocol_later_eq(764) else \
               0x15 if context.protocol_later_eq(762) else \
               0x14 if context.protocol_later_eq(761) else \
               0x15 if context.protocol_later_eq(760) else \
               0x14 if context.protocol_later_eq(759) else \
               0x12 if context.protocol_later_eq(755) else \
               0x13 if context.protocol_later_eq(712) else \
               0x12 if context.protocol_later_eq(471) else \
               0x13 if context.protocol_later_eq(464) else \
               0x11 if context.protocol_later_eq(389) else \
               0x0F if context.protocol_later_eq(386) else \
               0x0E if context.protocol_later_eq(345) else \
               0x0D if context.protocol_later_eq(343) else \
               0x0E if context.protocol_later_eq(336) else \
               0x0F if context.protocol_later_eq(332) else \
               0x0E if context.protocol_later_eq(318) else \
               0x0D if context.protocol_later_eq(107) else \
               0x06

    packet_name = "position and look"
    definition = [
        {'x': Double},
        {'feet_y': Double},
        {'z': Double},
        {'yaw': Float},
        {'pitch': Float},
        {'on_ground': Boolean}]

    # Access the 'x', 'feet_y', 'z' fields as a Vector tuple.
    position = multi_attribute_alias(Vector, 'x', 'feet_y', 'z')

    # Access the 'yaw', 'pitch' fields as a Direction tuple.
    look = multi_attribute_alias(Direction, 'yaw', 'pitch')

    # Access the 'x', 'feet_y', 'z', 'yaw', 'pitch' fields as a
    # PositionAndLook.
    # NOTE: modifying the object retrieved from this property will not change
    # the packet; it can only be changed by attribute or property assignment.
    position_and_look = multi_attribute_alias(
        PositionAndLook, 'x', 'feet_y', 'z', 'yaw', 'pitch')


class TeleportConfirmPacket(Packet):
    # Note: added between protocol versions 47 and 107.
    id = 0x00
    packet_name = "teleport confirm"
    definition = [
        {'teleport_id': VarInt}]


class AnimationPacket(Packet):
    @staticmethod
    def get_id(context):
        return 0x3C if context.protocol_later_eq(771) else \
               0x3B if context.protocol_later_eq(770) else \
               0x3A if context.protocol_later_eq(769) else \
               0x38 if context.protocol_later_eq(768) else \
               0x36 if context.protocol_later_eq(766) else \
               0x33 if context.protocol_later_eq(765) else \
               0x32 if context.protocol_later_eq(764) else \
               0x2F if context.protocol_later_eq(760) else \
               0x2E if context.protocol_later_eq(759) else \
               0x2C if context.protocol_later_eq(755) else \
               0x2C if context.protocol_later_eq(738) else \
               0x2B if context.protocol_later_eq(712) else \
               0x2A if context.protocol_later_eq(468) else \
               0x29 if context.protocol_later_eq(464) else \
               0x27 if context.protocol_later_eq(389) else \
               0x25 if context.protocol_later_eq(386) else \
               0x1D if context.protocol_later_eq(345) else \
               0x1C if context.protocol_later_eq(343) else \
               0x1D if context.protocol_later_eq(332) else \
               0x1C if context.protocol_later_eq(318) else \
               0x1A if context.protocol_later_eq(107) else \
               0x0A

    packet_name = "animation"
    get_definition = staticmethod(lambda context: [
        {'hand': VarInt} if context.protocol_later_eq(107) else {}])

    Hand = RelativeHand
    HAND_MAIN, HAND_OFF = Hand.MAIN, Hand.OFF  # For backward compatibility.


class ClientStatusPacket(Packet, Enum):
    @staticmethod
    def get_id(context):
        return 0x0B if context.protocol_later_eq(771) else \
               0x0A if context.protocol_later_eq(768) else \
               0x09 if context.protocol_later_eq(766) else \
               0x08 if context.protocol_later_eq(764) else \
               0x07 if context.protocol_later_eq(762) else \
               0x06 if context.protocol_later_eq(761) else \
               0x07 if context.protocol_later_eq(760) else \
               0x06 if context.protocol_later_eq(759) else \
               0x04 if context.protocol_later_eq(755) else \
               0x04 if context.protocol_later_eq(464) else \
               0x03 if context.protocol_later_eq(389) else \
               0x02 if context.protocol_later_eq(343) else \
               0x03 if context.protocol_later_eq(336) else \
               0x04 if context.protocol_later_eq(318) else \
               0x03 if context.protocol_later_eq(80) else \
               0x02 if context.protocol_later_eq(67) else \
               0x17 if context.protocol_later_eq(49) else \
               0x16

    packet_name = "client status"
    get_definition = staticmethod(lambda context: [
        {'action_id': VarInt}])
    field_enum = classmethod(
        lambda cls, field, context: cls if field == 'action_id' else None)

    RESPAWN = 0
    REQUEST_STATS = 1
    # Note: Open Inventory (id 2) was removed in protocol version 319
    OPEN_INVENTORY = 2


class PluginMessagePacket(AbstractPluginMessagePacket):
    @staticmethod
    def get_id(context):
        return 0x15 if context.protocol_later_eq(771) else \
               0x14 if context.protocol_later_eq(768) else \
               0x12 if context.protocol_later_eq(766) else \
               0x10 if context.protocol_later_eq(765) else \
               0x0F if context.protocol_later_eq(764) else \
               0x0D if context.protocol_later_eq(762) else \
               0x0C if context.protocol_later_eq(761) else \
               0x0D if context.protocol_later_eq(760) else \
               0x0C if context.protocol_later_eq(759) else \
               0x0A if context.protocol_later_eq(755) else \
               0x0B if context.protocol_later_eq(464) else \
               0x0A if context.protocol_later_eq(389) else \
               0x09 if context.protocol_later_eq(345) else \
               0x08 if context.protocol_later_eq(343) else \
               0x09 if context.protocol_later_eq(336) else \
               0x0A if context.protocol_later_eq(317) else \
               0x09 if context.protocol_later_eq(94) else \
               0x17


class PlayerBlockPlacementPacket(Packet):
    """Realizaton of http://wiki.vg/Protocol#Player_Block_Placement packet
    Usage:
        packet = PlayerBlockPlacementPacket()
        packet.location = Position(x=1200, y=65, z=-420)
        packet.face = packet.Face.TOP   # See networking.types.BlockFace.
        packet.hand = packet.Hand.MAIN  # See networking.types.RelativeHand.
    Next values are called in-block coordinates.
    They are calculated using raytracing. From 0 to 1 (from Minecraft 1.11)
    or integers from 0 to 15 or, in a special case, -1 (1.10.2 and earlier).
        packet.x = 0.725
        packet.y = 0.125
        packet.z = 0.555"""

    @staticmethod
    def get_id(context):
        return 0x3F if context.protocol_later_eq(771) else \
               0x3E if context.protocol_later_eq(770) else \
               0x3C if context.protocol_later_eq(769) else \
               0x3A if context.protocol_later_eq(768) else \
               0x38 if context.protocol_later_eq(766) else \
               0x35 if context.protocol_later_eq(765) else \
               0x34 if context.protocol_later_eq(764) else \
               0x31 if context.protocol_later_eq(760) else \
               0x30 if context.protocol_later_eq(759) else \
               0x2E if context.protocol_later_eq(755) else \
               0x2E if context.protocol_later_eq(738) else \
               0x2D if context.protocol_later_eq(712) else \
               0x2C if context.protocol_later_eq(468) else \
               0x2B if context.protocol_later_eq(464) else \
               0x29 if context.protocol_later_eq(389) else \
               0x27 if context.protocol_later_eq(386) else \
               0x1F if context.protocol_later_eq(345) else \
               0x1E if context.protocol_later_eq(343) else \
               0x1F if context.protocol_later_eq(332) else \
               0x1E if context.protocol_later_eq(318) else \
               0x1C if context.protocol_later_eq(94) else \
               0x08

    packet_name = 'player block placement'

    @staticmethod
    def get_definition(context):
        return [
            {'hand': VarInt} if context.protocol_later_eq(453) else {},
            {'location': Position},
            {'face': VarInt if context.protocol_later_eq(69) else Byte},
            {'hand': VarInt} if context.protocol_earlier(453) else {},
            {'x': Float if context.protocol_later_eq(309) else Byte},
            {'y': Float if context.protocol_later_eq(309) else Byte},
            {'z': Float if context.protocol_later_eq(309) else Byte},
            ({'inside_block': Boolean}
                if context.protocol_later_eq(453) else {}),
        ]

    # PlayerBlockPlacementPacket.Hand is an alias for RelativeHand.
    Hand = RelativeHand

    # PlayerBlockPlacementPacket.Face is an alias for BlockFace.
    Face = BlockFace


class UseItemPacket(Packet):
    @staticmethod
    def get_id(context):
        return 0x40 if context.protocol_later_eq(771) else \
               0x3F if context.protocol_later_eq(770) else \
               0x3D if context.protocol_later_eq(769) else \
               0x3B if context.protocol_later_eq(768) else \
               0x39 if context.protocol_later_eq(766) else \
               0x36 if context.protocol_later_eq(765) else \
               0x35 if context.protocol_later_eq(764) else \
               0x32 if context.protocol_later_eq(760) else \
               0x31 if context.protocol_later_eq(759) else \
               0x2F if context.protocol_later_eq(755) else \
               0x2F if context.protocol_later_eq(738) else \
               0x2E if context.protocol_later_eq(712) else \
               0x2D if context.protocol_later_eq(468) else \
               0x2C if context.protocol_later_eq(464) else \
               0x2A if context.protocol_later_eq(389) else \
               0x28 if context.protocol_later_eq(386) else \
               0x20 if context.protocol_later_eq(345) else \
               0x1F if context.protocol_later_eq(343) else \
               0x20 if context.protocol_later_eq(332) else \
               0x1F if context.protocol_later_eq(318) else \
               0x1D if context.protocol_later_eq(94) else \
               0x1A if context.protocol_later_eq(70) else \
               0x08

    packet_name = "use item"
    get_definition = staticmethod(lambda context: [
        {'hand': VarInt}])

    Hand = RelativeHand


class ResourcePackStatusPacket(Packet):
    @staticmethod
    def get_id(context):
        return 0x21
    packet_name = "resource pack status"
    definition = [
        {"result": VarInt}
    ]
