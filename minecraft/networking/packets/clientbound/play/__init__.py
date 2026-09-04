from minecraft import PRE
from minecraft.networking.packets import (
    Packet, AbstractKeepAlivePacket, AbstractPluginMessagePacket
)

from minecraft.networking.types import (
    FixedPoint, Integer, Angle, UnsignedByte, Byte, Boolean, UUID, Short,
    VarInt, Double, Float, String, Enum, Difficulty, Long, Vector, Direction,
    PositionAndLook, multi_attribute_alias, attribute_transform,
    VarIntPrefixedByteArray, PrefixedOptional, MutableRecord, NBT, LpVec3,
)

from .combat_event_packet import (
    CombatEventPacket, EnterCombatEventPacket, EndCombatEventPacket,
    DeathCombatEventPacket,
)
from .map_packet import MapPacket
from .player_list_item_packet import PlayerListItemPacket, PlayerRemovePacket
from .player_position_and_look_packet import PlayerPositionAndLookPacket
from .spawn_object_packet import SpawnObjectPacket
from .block_change_packet import BlockChangePacket, MultiBlockChangePacket
from .explosion_packet import ExplosionPacket
from .sound_effect_packet import SoundEffectPacket, NamedSoundEffectPacket
from .face_player_packet import FacePlayerPacket
from .join_game_and_respawn_packets import JoinGamePacket, RespawnPacket


# Formerly known as state_playing_clientbound.
def get_packets(context):
    packets = {
        KeepAlivePacket,
        JoinGamePacket,
        ServerDifficultyPacket,
        PlayerPositionAndLookPacket,
        PlayerListItemPacket,
        DisconnectPacket,
        EntityVelocityPacket,
        EntityPositionDeltaPacket,
        TimeUpdatePacket,
        UpdateHealthPacket,
        BlockChangePacket,
        MultiBlockChangePacket,
        RespawnPacket,
        PluginMessagePacket,
        PlayerListHeaderAndFooterPacket,
        EntityLookPacket,
    }

    # The 'chat message' packet was removed in protocol 759, being replaced
    # by 'system chat message' and 'player chat message' (and, in protocol
    # 761, 'profileless chat message').
    if context.protocol_earlier(759):
        packets |= {
            ChatMessagePacket,
        }
    else:
        packets |= {
            SystemChatPacket,
        }
        if context.protocol_earlier(767):
            # In protocol 767, the 'type' field of the 'player chat message'
            # packet became a registry entry holder, which pyCraft does not
            # currently support; the packet is not registered for protocols
            # 767 and later.
            packets |= {
                PlayerChatPacket,
            }
        if context.protocol_in_range(761, 767):
            # In protocol 767, the 'type' field of the 'profileless chat
            # message' packet became a registry entry holder, which pyCraft
            # does not currently support.
            packets |= {
                ProfilelessChatPacket,
            }

    # The 'spawn player' packet was removed in protocol 764; in this and
    # later protocols, players are spawned with the 'spawn entity' packet.
    if context.protocol_earlier(764):
        packets |= {
            SpawnPlayerPacket,
        }

    # The 'explosion' packet gained particle and sound fields in protocol
    # 765, which pyCraft does not currently support.
    if context.protocol_earlier(765):
        packets |= {
            ExplosionPacket,
        }

    # The 'spawn object' packet changed its velocity encoding in protocol
    # 773, which pyCraft does not currently support.
    if context.protocol_earlier(773):
        packets |= {
            SpawnObjectPacket,
        }

    # In protocol 765, the 'displayName' of map icons changed from a chat
    # JSON string to NBT, which pyCraft does not currently support.
    if context.protocol_earlier(765):
        packets |= {
            MapPacket,
        }

    # The 'resource pack send' packet was replaced by 'add resource pack'
    # in protocol 765.
    if context.protocol_earlier(765):
        packets |= {
            ResourcePackSendPacket,
        }

    if context.protocol_later_eq(764):
        packets |= {
            StartConfigurationPacket,
            PlayerRemovePacket,
        }

    # The 'named sound effect' packet was added in protocol 107 and removed
    # in protocol 761.
    if context.protocol_later_eq(107) and context.protocol_earlier(761):
        packets |= {
            NamedSoundEffectPacket,
        }

    if context.protocol_earlier_eq(47):
        packets |= {
            SetCompressionPacket,
        }

    if context.protocol_earlier(PRE | 15):
        packets |= {
            CombatEventPacket,
        }
    else:
        packets |= {
            EnterCombatEventPacket,
            EndCombatEventPacket,
            DeathCombatEventPacket,
        }

    if context.protocol_later_eq(94):
        packets |= {
            SoundEffectPacket,
        }

    if context.protocol_later_eq(352):
        packets |= {
            FacePlayerPacket
        }

    return packets


class KeepAlivePacket(AbstractKeepAlivePacket):
    @staticmethod
    def get_id(context):
        return 0x2B if context.protocol_later_eq(773) else \
               0x26 if context.protocol_later_eq(770) else \
               0x27 if context.protocol_later_eq(768) else \
               0x26 if context.protocol_later_eq(766) else \
               0x24 if context.protocol_later_eq(764) else \
               0x23 if context.protocol_later_eq(762) else \
               0x1F if context.protocol_later_eq(761) else \
               0x20 if context.protocol_later_eq(760) else \
               0x1E if context.protocol_later_eq(759) else \
               0x21 if context.protocol_later_eq(755) else \
               0x1F if context.protocol_later_eq(741) else \
               0x20 if context.protocol_later_eq(721) else \
               0x21 if context.protocol_later_eq(550) else \
               0x20 if context.protocol_later_eq(471) else \
               0x21 if context.protocol_later_eq(389) else \
               0x20 if context.protocol_later_eq(345) else \
               0x1F if context.protocol_later_eq(332) else \
               0x20 if context.protocol_later_eq(318) else \
               0x1F if context.protocol_later_eq(107) else \
               0x00


class ServerDifficultyPacket(Packet):
    @staticmethod
    def get_id(context):
        return 0x0A if context.protocol_later_eq(770) else \
               0x0B if context.protocol_later_eq(764) else \
               0x0C if context.protocol_later_eq(762) else \
               0x0B if context.protocol_later_eq(759) else \
               0x0E if context.protocol_later_eq(755) else \
               0x0D if context.protocol_later_eq(721) else \
               0x0E if context.protocol_later_eq(550) else \
               0x0D if context.protocol_later_eq(332) else \
               0x0E if context.protocol_later_eq(318) else \
               0x0D if context.protocol_later_eq(70) else \
               0x41

    packet_name = 'server difficulty'
    get_definition = staticmethod(lambda context: [
        {'difficulty': UnsignedByte},
        {'is_locked': Boolean} if context.protocol_later_eq(464) else {},
    ])

    # These aliases declare the Enum type corresponding to each field:
    Difficulty = Difficulty


class ChatMessagePacket(Packet):
    @staticmethod
    def get_id(context):
        return 0x0F if context.protocol_later_eq(755) else \
               0x0E if context.protocol_later_eq(721) else \
               0x0F if context.protocol_later_eq(550) else \
               0x0E if context.protocol_later_eq(343) else \
               0x0F if context.protocol_later_eq(332) else \
               0x10 if context.protocol_later_eq(317) else \
               0x0F if context.protocol_later_eq(107) else \
               0x02

    packet_name = "chat message"
    get_definition = staticmethod(lambda context: [
        {'json_data': String},
        {'position': Byte},
        {'sender': UUID} if context.protocol_later_eq(718) else {},
    ])

    class Position(Enum):
        CHAT = 0       # A player-initiated chat message.
        SYSTEM = 1     # The result of running a command.
        GAME_INFO = 2  # Displayed above the hotbar in vanilla clients.


class SystemChatPacket(Packet):
    # Note: added in protocol 759, replacing 'ChatMessagePacket'.
    @staticmethod
    def get_id(context):
        return 0x77 if context.protocol_later_eq(773) else \
               0x72 if context.protocol_later_eq(770) else \
               0x73 if context.protocol_later_eq(768) else \
               0x6C if context.protocol_later_eq(766) else \
               0x69 if context.protocol_later_eq(765) else \
               0x67 if context.protocol_later_eq(764) else \
               0x64 if context.protocol_later_eq(762) else \
               0x60 if context.protocol_later_eq(761) else \
               0x62 if context.protocol_later_eq(760) else \
               0x5F

    packet_name = "system chat message"
    get_definition = staticmethod(lambda context: [
        # In protocol 765 and later, the content is an NBT chat component
        # rather than a JSON string.
        {'content': NBT if context.protocol_later_eq(765) else String},
        {'type': VarInt} if context.protocol_earlier(760)
        else {'is_action_bar': Boolean},
    ])


class PlayerChatPacket(Packet):
    # Note: added in protocol 759, replacing 'ChatMessagePacket'. In
    # protocol 767, the 'type' field became a registry entry holder, which
    # pyCraft does not currently support, so this packet is not registered
    # for protocols 767 and later (see 'get_packets').
    @staticmethod
    def get_id(context):
        return 0x39 if context.protocol_later_eq(766) else \
               0x37 if context.protocol_later_eq(764) else \
               0x35 if context.protocol_later_eq(762) else \
               0x31 if context.protocol_later_eq(761) else \
               0x33 if context.protocol_later_eq(760) else \
               0x30

    packet_name = "player chat message"

    @property
    def fields(self):
        context = self.context
        if context.protocol_earlier(760):
            return ('signed_content', 'unsigned_content', 'type',
                    'sender_uuid', 'sender_name', 'sender_team',
                    'timestamp', 'salt', 'signature')
        if context.protocol_earlier(761):
            return ('previous_signature', 'sender_uuid', 'signature',
                    'plain_message', 'formatted_message', 'timestamp',
                    'salt', 'previous_messages', 'unsigned_content',
                    'filter_type', 'filter_type_mask', 'type',
                    'network_name', 'network_target_name')
        return ('sender_uuid', 'index', 'signature', 'plain_message',
                'timestamp', 'salt', 'previous_messages', 'unsigned_content',
                'filter_type', 'filter_type_mask', 'type', 'network_name',
                'network_target_name')

    class PreviousMessage(MutableRecord):
        # An entry of the 'previous_messages' array in protocol 760.
        __slots__ = 'message_sender', 'message_signature'

    class LastSeenMessage(MutableRecord):
        # An entry of the 'previous_messages' array in protocols 761 and
        # later; the 'signature' is present only when 'id' is zero.
        __slots__ = 'id', 'signature'

    def read(self, file_object):
        context = self.context
        if context.protocol_earlier(760):  # Protocol 759.
            self.signed_content = String.read(file_object)
            self.unsigned_content = PrefixedOptional(String).read(file_object)
            self.type = VarInt.read(file_object)
            self.sender_uuid = UUID.read(file_object)
            self.sender_name = String.read(file_object)
            self.sender_team = PrefixedOptional(String).read(file_object)
            self.timestamp = Long.read(file_object)
            self.salt = Long.read(file_object)
            self.signature = VarIntPrefixedByteArray.read(file_object)
            return

        if context.protocol_earlier(761):  # Protocol 760.
            self.previous_signature = \
                PrefixedOptional(VarIntPrefixedByteArray).read(file_object)
            self.sender_uuid = UUID.read(file_object)
            self.signature = VarIntPrefixedByteArray.read(file_object)
            self.plain_message = String.read(file_object)
            self.formatted_message = \
                PrefixedOptional(String).read(file_object)
        else:  # Protocols 761 and later.
            self.sender_uuid = UUID.read(file_object)
            self.index = VarInt.read(file_object)
            if Boolean.read(file_object):
                self.signature = file_object.read(256)
            else:
                self.signature = None
            self.plain_message = String.read(file_object)

        self.timestamp = Long.read(file_object)
        self.salt = Long.read(file_object)
        self.previous_messages = []
        for i in range(VarInt.read(file_object)):
            if context.protocol_earlier(761):
                message = PlayerChatPacket.PreviousMessage(
                    message_sender=UUID.read(file_object),
                    message_signature=VarIntPrefixedByteArray.read(
                        file_object))
            else:
                message = PlayerChatPacket.LastSeenMessage(
                    id=VarInt.read(file_object))
                message.signature = file_object.read(256) \
                    if message.id == 0 else None
            self.previous_messages.append(message)

        if context.protocol_later_eq(765):
            # In protocol 765 and later, chat components are NBT rather
            # than JSON strings.
            self.unsigned_content = PrefixedOptional(NBT) \
                .read_with_context(file_object, context)
        else:
            self.unsigned_content = PrefixedOptional(String).read(file_object)
        self.filter_type = VarInt.read(file_object)
        if self.filter_type == 2:
            self.filter_type_mask = [
                Long.read(file_object)
                for i in range(VarInt.read(file_object))]
        else:
            self.filter_type_mask = None
        self.type = VarInt.read(file_object)
        if context.protocol_later_eq(765):
            self.network_name = NBT.read_with_context(file_object, context)
            self.network_target_name = PrefixedOptional(NBT) \
                .read_with_context(file_object, context)
        else:
            self.network_name = String.read(file_object)
            self.network_target_name = \
                PrefixedOptional(String).read(file_object)

    def write_fields(self, packet_buffer):
        context = self.context
        if context.protocol_earlier(760):  # Protocol 759.
            String.send(self.signed_content, packet_buffer)
            PrefixedOptional(String).send(
                self.unsigned_content, packet_buffer)
            VarInt.send(self.type, packet_buffer)
            UUID.send(self.sender_uuid, packet_buffer)
            String.send(self.sender_name, packet_buffer)
            PrefixedOptional(String).send(self.sender_team, packet_buffer)
            Long.send(self.timestamp, packet_buffer)
            Long.send(self.salt, packet_buffer)
            VarIntPrefixedByteArray.send(self.signature, packet_buffer)
            return

        if context.protocol_earlier(761):  # Protocol 760.
            PrefixedOptional(VarIntPrefixedByteArray).send(
                self.previous_signature, packet_buffer)
            UUID.send(self.sender_uuid, packet_buffer)
            VarIntPrefixedByteArray.send(self.signature, packet_buffer)
            String.send(self.plain_message, packet_buffer)
            PrefixedOptional(String).send(
                self.formatted_message, packet_buffer)
        else:  # Protocols 761 and later.
            UUID.send(self.sender_uuid, packet_buffer)
            VarInt.send(self.index, packet_buffer)
            Boolean.send(self.signature is not None, packet_buffer)
            if self.signature is not None:
                packet_buffer.send(self.signature)
            String.send(self.plain_message, packet_buffer)

        Long.send(self.timestamp, packet_buffer)
        Long.send(self.salt, packet_buffer)
        VarInt.send(len(self.previous_messages), packet_buffer)
        for message in self.previous_messages:
            if context.protocol_earlier(761):
                UUID.send(message.message_sender, packet_buffer)
                VarIntPrefixedByteArray.send(
                    message.message_signature, packet_buffer)
            else:
                VarInt.send(message.id, packet_buffer)
                if message.id == 0:
                    packet_buffer.send(message.signature)

        if context.protocol_later_eq(765):
            PrefixedOptional(NBT).send_with_context(
                self.unsigned_content, packet_buffer, context)
        else:
            PrefixedOptional(String).send(
                self.unsigned_content, packet_buffer)
        VarInt.send(self.filter_type, packet_buffer)
        if self.filter_type == 2:
            VarInt.send(len(self.filter_type_mask), packet_buffer)
            for value in self.filter_type_mask:
                Long.send(value, packet_buffer)
        VarInt.send(self.type, packet_buffer)
        if context.protocol_later_eq(765):
            NBT.send_with_context(self.network_name, packet_buffer, context)
            PrefixedOptional(NBT).send_with_context(
                self.network_target_name, packet_buffer, context)
        else:
            String.send(self.network_name, packet_buffer)
            PrefixedOptional(String).send(
                self.network_target_name, packet_buffer)


class ProfilelessChatPacket(Packet):
    # Note: added in protocol 761.
    @staticmethod
    def get_id(context):
        return 0x21 if context.protocol_later_eq(773) else \
               0x1D if context.protocol_later_eq(770) else \
               0x1E if context.protocol_later_eq(766) else \
               0x1C if context.protocol_later_eq(764) else \
               0x1B if context.protocol_later_eq(762) else \
               0x18

    packet_name = "profileless chat message"
    get_definition = staticmethod(lambda context: [
        # In protocol 765 and later, chat components are NBT rather than
        # JSON strings.
        {'message': NBT if context.protocol_later_eq(765) else String},
        {'type': VarInt},
        {'name': NBT if context.protocol_later_eq(765) else String},
        {'target': PrefixedOptional(NBT) if context.protocol_later_eq(765)
         else PrefixedOptional(String)},
    ])


class DisconnectPacket(Packet):
    @staticmethod
    def get_id(context):
        return 0x20 if context.protocol_later_eq(773) else \
               0x1C if context.protocol_later_eq(770) else \
               0x1D if context.protocol_later_eq(766) else \
               0x1B if context.protocol_later_eq(764) else \
               0x1A if context.protocol_later_eq(762) else \
               0x17 if context.protocol_later_eq(761) else \
               0x19 if context.protocol_later_eq(760) else \
               0x17 if context.protocol_later_eq(759) else \
               0x1A if context.protocol_later_eq(755) else \
               0x19 if context.protocol_later_eq(741) else \
               0x1A if context.protocol_later_eq(721) else \
               0x1B if context.protocol_later_eq(550) else \
               0x1A if context.protocol_later_eq(471) else \
               0x1B if context.protocol_later_eq(345) else \
               0x1A if context.protocol_later_eq(332) else \
               0x1B if context.protocol_later_eq(318) else \
               0x1A if context.protocol_later_eq(107) else \
               0x40

    packet_name = "disconnect"

    get_definition = staticmethod(lambda context: [
        # In protocol 765 and later, the reason is an NBT chat component
        # rather than a JSON string.
        {'json_data': NBT if context.protocol_later_eq(765) else String},
    ])


class SetCompressionPacket(Packet):
    # Note: removed between protocol versions 47 and 107.
    @staticmethod
    def get_id(context):
        return 0x03 if context.protocol_later_eq(755) else \
               0x46

    packet_name = "set compression"
    definition = [
        {'threshold': VarInt}]


class SpawnPlayerPacket(Packet):
    @staticmethod
    def get_id(context):
        return 0x03 if context.protocol_later_eq(762) else \
               0x02 if context.protocol_later_eq(759) else \
               0x04 if context.protocol_later_eq(721) else \
               0x05 if context.protocol_later_eq(67) else \
               0x0C

    packet_name = 'spawn player'
    get_definition = staticmethod(lambda context: [
        {'entity_id': VarInt},
        {'player_UUID': UUID},
        {'x': Double} if context.protocol_later_eq(100)
        else {'x': FixedPoint(Integer)},
        {'y': Double} if context.protocol_later_eq(100)
        else {'y': FixedPoint(Integer)},
        {'z': Double} if context.protocol_later_eq(100)
        else {'z': FixedPoint(Integer)},
        {'yaw': Angle},
        {'pitch': Angle},
        {'current_item': Short} if context.protocol_earlier_eq(49) else {},
        # TODO: read entity metadata (protocol < 550)
    ])

    # Access the 'x', 'y', 'z' fields as a Vector tuple.
    position = multi_attribute_alias(Vector, 'x', 'y', 'z')

    # Access the 'yaw', 'pitch' fields as a Direction tuple.
    look = multi_attribute_alias(Direction, 'yaw', 'pitch')

    # Access the 'x', 'y', 'z', 'yaw', 'pitch' fields as a PositionAndLook.
    # NOTE: modifying the object retrieved from this property will not change
    # the packet; it can only be changed by attribute or property assignment.
    position_and_look = multi_attribute_alias(
        PositionAndLook, 'x', 'y', 'z', 'yaw', 'pitch')


class EntityVelocityPacket(Packet):
    @staticmethod
    def get_id(context):
        return 0x63 if context.protocol_later_eq(773) else \
               0x5E if context.protocol_later_eq(770) else \
               0x5F if context.protocol_later_eq(768) else \
               0x5A if context.protocol_later_eq(766) else \
               0x58 if context.protocol_later_eq(765) else \
               0x56 if context.protocol_later_eq(764) else \
               0x54 if context.protocol_later_eq(762) else \
               0x50 if context.protocol_later_eq(761) else \
               0x52 if context.protocol_later_eq(760) else \
               0x4F if context.protocol_later_eq(755) else \
               0x46 if context.protocol_later_eq(721) else \
               0x47 if context.protocol_later_eq(707) else \
               0x46 if context.protocol_later_eq(550) else \
               0x45 if context.protocol_later_eq(471) else \
               0x41 if context.protocol_later_eq(461) else \
               0x42 if context.protocol_later_eq(451) else \
               0x41 if context.protocol_later_eq(389) else \
               0x40 if context.protocol_later_eq(352) else \
               0x3F if context.protocol_later_eq(345) else \
               0x3E if context.protocol_later_eq(336) else \
               0x3D if context.protocol_later_eq(332) else \
               0x3B if context.protocol_later_eq(86) else \
               0x3C if context.protocol_later_eq(77) else \
               0x3B if context.protocol_later_eq(67) else \
               0x12

    packet_name = 'entity velocity'
    get_definition = staticmethod(lambda context: [
        {'entity_id': VarInt},
        # In protocols 773 and later, the velocity is a single packed
        # vector (LpVec3) instead of three Shorts.
        {'velocity': LpVec3} if context.protocol_later_eq(773) else {},
        {'velocity_x': Short} if context.protocol_earlier(773) else {},
        {'velocity_y': Short} if context.protocol_earlier(773) else {},
        {'velocity_z': Short} if context.protocol_earlier(773) else {},
    ])


class EntityPositionDeltaPacket(Packet):
    @staticmethod
    def get_id(context):
        return 0x33 if context.protocol_later_eq(773) else \
               0x2E if context.protocol_later_eq(770) else \
               0x2F if context.protocol_later_eq(768) else \
               0x2E if context.protocol_later_eq(766) else \
               0x2C if context.protocol_later_eq(764) else \
               0x2B if context.protocol_later_eq(762) else \
               0x27 if context.protocol_later_eq(761) else \
               0x28 if context.protocol_later_eq(760) else \
               0x26 if context.protocol_later_eq(759) else \
               0x29 if context.protocol_later_eq(755) else \
               0x27 if context.protocol_later_eq(741) else \
               0x28 if context.protocol_later_eq(721) else \
               0x29 if context.protocol_later_eq(550) else \
               0x28 if context.protocol_later_eq(389) else \
               0x27 if context.protocol_later_eq(345) else \
               0x26 if context.protocol_later_eq(318) else \
               0x25 if context.protocol_later_eq(94) else \
               0x26 if context.protocol_later_eq(70) else \
               0x15

    packet_name = "entity position delta"

    @staticmethod
    def get_definition(context):
        delta_type = FixedPoint(Short, 12) \
                     if context.protocol_later_eq(106) else \
                     FixedPoint(Byte)
        return [
            {'entity_id': VarInt},
            {'delta_x_float': delta_type},
            {'delta_y_float': delta_type},
            {'delta_z_float': delta_type},
            {'on_ground': Boolean},
        ]

    # The following transforms are retained for backward compatibility;
    # they represent the delta values as fixed-point integers with 12 bits
    # of fractional part, regardless of the protocol version.
    delta_x = attribute_transform(
                'delta_x_float', lambda x: int(x * 4096), lambda x: x / 4096)
    delta_y = attribute_transform(
                'delta_y_float', lambda y: int(y * 4096), lambda y: y / 4096)
    delta_z = attribute_transform(
                'delta_z_float', lambda z: int(z * 4096), lambda z: z / 4096)


class TimeUpdatePacket(Packet):
    @staticmethod
    def get_id(context):
        return 0x6F if context.protocol_later_eq(773) else \
               0x6A if context.protocol_later_eq(770) else \
               0x6B if context.protocol_later_eq(768) else \
               0x64 if context.protocol_later_eq(766) else \
               0x62 if context.protocol_later_eq(765) else \
               0x60 if context.protocol_later_eq(764) else \
               0x59 if context.protocol_later_eq(PRE | 48) else \
               0x58 if context.protocol_later_eq(755) else \
               0x4E if context.protocol_later_eq(721) else \
               0x4F if context.protocol_later_eq(550) else \
               0x4E if context.protocol_later_eq(471) else \
               0x4A if context.protocol_later_eq(461) else \
               0x4B if context.protocol_later_eq(451) else \
               0x4A if context.protocol_later_eq(389) else \
               0x49 if context.protocol_later_eq(352) else \
               0x48 if context.protocol_later_eq(345) else \
               0x47 if context.protocol_later_eq(336) else \
               0x46 if context.protocol_later_eq(318) else \
               0x44 if context.protocol_later_eq(94) else \
               0x43 if context.protocol_later_eq(70) else \
               0x03

    packet_name = "time update"
    get_definition = staticmethod(lambda context: [
        {'world_age': Long},
        {'time_of_day': Long},
        {'tick_day_time': Boolean}
        if context.protocol_later_eq(768) else {},
    ])

    # The 'tick_day_time' field was added in protocol 768.
    tick_day_time = True


class UpdateHealthPacket(Packet):
    @staticmethod
    def get_id(context):
        return 0x66 if context.protocol_later_eq(773) else \
               0x61 if context.protocol_later_eq(770) else \
               0x62 if context.protocol_later_eq(768) else \
               0x5D if context.protocol_later_eq(766) else \
               0x5B if context.protocol_later_eq(765) else \
               0x59 if context.protocol_later_eq(764) else \
               0x57 if context.protocol_later_eq(762) else \
               0x53 if context.protocol_later_eq(761) else \
               0x55 if context.protocol_later_eq(760) else \
               0x52 if context.protocol_later_eq(755) else \
               0x49 if context.protocol_later_eq(721) else \
               0x4A if context.protocol_later_eq(707) else \
               0x49 if context.protocol_later_eq(550) else \
               0x48 if context.protocol_later_eq(471) else \
               0x44 if context.protocol_later_eq(461) else \
               0x45 if context.protocol_later_eq(451) else \
               0x44 if context.protocol_later_eq(389) else \
               0x43 if context.protocol_later_eq(352) else \
               0x42 if context.protocol_later_eq(345) else \
               0x41 if context.protocol_later_eq(336) else \
               0x40 if context.protocol_later_eq(318) else \
               0x3E if context.protocol_later_eq(86) else \
               0x3F if context.protocol_later_eq(77) else \
               0x3E if context.protocol_later_eq(67) else \
               0x06

    packet_name = 'update health'
    get_definition = staticmethod(lambda context: [
        {'health': Float},
        {'food': VarInt},
        {'food_saturation': Float}
    ])


class PluginMessagePacket(AbstractPluginMessagePacket):
    @staticmethod
    def get_id(context):
        return 0x18 if context.protocol_later_eq(770) else \
               0x19 if context.protocol_later_eq(766) else \
               0x18 if context.protocol_later_eq(764) else \
               0x17 if context.protocol_later_eq(762) else \
               0x15 if context.protocol_later_eq(761) else \
               0x16 if context.protocol_later_eq(760) else \
               0x15 if context.protocol_later_eq(759) else \
               0x18 if context.protocol_later_eq(755) else \
               0x17 if context.protocol_later_eq(741) else \
               0x18 if context.protocol_later_eq(721) else \
               0x19 if context.protocol_later_eq(550) else \
               0x18 if context.protocol_later_eq(471) else \
               0x19 if context.protocol_later_eq(345) else \
               0x18 if context.protocol_later_eq(332) else \
               0x19 if context.protocol_later_eq(318) else \
               0x18 if context.protocol_later_eq(70) else \
               0x3F


class PlayerListHeaderAndFooterPacket(Packet):
    @staticmethod
    def get_id(context):
        return 0x78 if context.protocol_later_eq(773) else \
               0x73 if context.protocol_later_eq(770) else \
               0x74 if context.protocol_later_eq(768) else \
               0x6D if context.protocol_later_eq(766) else \
               0x6A if context.protocol_later_eq(765) else \
               0x68 if context.protocol_later_eq(764) else \
               0x65 if context.protocol_later_eq(762) else \
               0x61 if context.protocol_later_eq(761) else \
               0x63 if context.protocol_later_eq(760) else \
               0x60 if context.protocol_later_eq(759) else \
               0x5F if context.protocol_later_eq(PRE | 48) else \
               0x5E if context.protocol_later_eq(755) else \
               0x53 if context.protocol_later_eq(721) else \
               0x54 if context.protocol_later_eq(550) else \
               0x53 if context.protocol_later_eq(471) else \
               0x5F if context.protocol_later_eq(461) else \
               0x50 if context.protocol_later_eq(451) else \
               0x4F if context.protocol_later_eq(441) else \
               0x4E if context.protocol_later_eq(393) else \
               0x4A if context.protocol_later_eq(338) else \
               0x49 if context.protocol_later_eq(335) else \
               0x47 if context.protocol_later_eq(110) else \
               0x48 if context.protocol_later_eq(107) else \
               0x47

    packet_name = 'player list header and footer'
    get_definition = staticmethod(lambda context: [
        # In protocol 765 and later, the header and footer are NBT chat
        # components rather than JSON strings.
        {'header': NBT if context.protocol_later_eq(765) else String},
        {'footer': NBT if context.protocol_later_eq(765) else String},
    ])


class EntityLookPacket(Packet):
    @staticmethod
    def get_id(context):
        return 0x36 if context.protocol_later_eq(773) else \
               0x31 if context.protocol_later_eq(770) else \
               0x32 if context.protocol_later_eq(768) else \
               0x30 if context.protocol_later_eq(766) else \
               0x2E if context.protocol_later_eq(764) else \
               0x2D if context.protocol_later_eq(762) else \
               0x29 if context.protocol_later_eq(761) else \
               0x2A if context.protocol_later_eq(760) else \
               0x28 if context.protocol_later_eq(759) else \
               0x2B if context.protocol_later_eq(755) else \
               0x29 if context.protocol_later_eq(741) else \
               0x2A if context.protocol_later_eq(721) else \
               0x2B if context.protocol_later_eq(550) else \
               0x2A if context.protocol_later_eq(389) else \
               0x29 if context.protocol_later_eq(345) else \
               0x28 if context.protocol_later_eq(318) else \
               0x27 if context.protocol_later_eq(94) else \
               0x28 if context.protocol_later_eq(70) else \
               0x16

    packet_name = 'entity look'
    definition = [
        {'entity_id': VarInt},
        {'yaw': Angle},
        {'pitch': Angle},
        {'on_ground': Boolean}
    ]


class ResourcePackSendPacket(Packet):
    # Note: this packet was replaced by 'add resource pack' in protocol 765.
    @staticmethod
    def get_id(context):
        return 0x42 if context.protocol_later_eq(764) else \
               0x40 if context.protocol_later_eq(762) else \
               0x3C if context.protocol_later_eq(761) else \
               0x3D if context.protocol_later_eq(760) else \
               0x3A if context.protocol_later_eq(759) else \
               0x3C if context.protocol_later_eq(PRE | 15) else \
               0x39 if context.protocol_later_eq(PRE | 8) else \
               0x38 if context.protocol_later_eq(741) else \
               0x39 if context.protocol_later_eq(721) else \
               0x3A if context.protocol_later_eq(550) else \
               0x39 if context.protocol_later_eq(471) else \
               0x37 if context.protocol_later_eq(461) else \
               0x38 if context.protocol_later_eq(451) else \
               0x37 if context.protocol_later_eq(389) else \
               0x36 if context.protocol_later_eq(352) else \
               0x35 if context.protocol_later_eq(345) else \
               0x34 if context.protocol_later_eq(336) else \
               0x33 if context.protocol_later_eq(332) else \
               0x34 if context.protocol_later_eq(318) else \
               0x32 if context.protocol_later_eq(70) else \
               0x48

    packet_name = "resource pack send"

    @staticmethod
    def get_definition(context):
        return [
            {"url": String},
            {"hash": String},
            {"forced": Boolean} if context.protocol_later_eq(PRE | 5) else {},
            {"forced_message": String}
            if context.protocol_later_eq(PRE | 15) else {},
        ]


class StartConfigurationPacket(Packet):
    # Note: added in protocol 764, this packet switches the connection back
    # to the configuration state.
    @staticmethod
    def get_id(context):
        return 0x74 if context.protocol_later_eq(773) else \
               0x6F if context.protocol_later_eq(770) else \
               0x70 if context.protocol_later_eq(768) else \
               0x69 if context.protocol_later_eq(766) else \
               0x67 if context.protocol_later_eq(765) else \
               0x65

    packet_name = "start configuration"
    definition = []
