from minecraft import PRE
from minecraft.networking.packets import Packet
from minecraft.networking.types import (
    VarInt, String, Float, Byte, Type, Integer, Long, Vector, Enum,
    PrefixedOptional,
)

__all__ = 'SoundEffectPacket', 'NamedSoundEffectPacket'


class SoundEffectPacket(Packet):
    @staticmethod
    def get_id(context):
        return 0x75 if context.protocol_later_eq(775) else \
               0x73 if context.protocol_later_eq(773) else \
               0x6E if context.protocol_later_eq(770) else \
               0x6F if context.protocol_later_eq(768) else \
               0x68 if context.protocol_later_eq(766) else \
               0x66 if context.protocol_later_eq(765) else \
               0x64 if context.protocol_later_eq(764) else \
               0x62 if context.protocol_later_eq(762) else \
               0x5E if context.protocol_later_eq(761) else \
               0x60 if context.protocol_later_eq(760) else \
               0x5D if context.protocol_later_eq(757) else \
               0x5D if context.protocol_later_eq(PRE | 48) else \
               0x5C if context.protocol_later_eq(755) else \
               0x51 if context.protocol_later_eq(721) else \
               0x52 if context.protocol_later_eq(550) else \
               0x51 if context.protocol_later_eq(471) else \
               0x4D if context.protocol_later_eq(461) else \
               0x4E if context.protocol_later_eq(451) else \
               0x4D if context.protocol_later_eq(389) else \
               0x4C if context.protocol_later_eq(352) else \
               0x4B if context.protocol_later_eq(345) else \
               0x4A if context.protocol_later_eq(343) else \
               0x49 if context.protocol_later_eq(336) else \
               0x48 if context.protocol_later_eq(318) else \
               0x46 if context.protocol_later_eq(110) else \
               0x47

    packet_name = 'sound effect'

    def read(self, file_object):
        if self.context.protocol_earlier(761):
            return super(SoundEffectPacket, self).read(file_object)
        # Protocols 761 and later: the sound is given as a "holder", i.e.
        # a registry ID, with an inline definition present only when the
        # ID is zero. From protocol 766, the wire stores the registry ID
        # plus one (zero indicates an inline definition).
        self.sound_id = VarInt.read(file_object)
        if self.context.protocol_later_eq(766) and self.sound_id > 0:
            self.sound_id -= 1
        if self.sound_id == 0:
            self.sound_name = String.read(file_object)
            self.fixed_range = PrefixedOptional(Float).read(file_object)
        self.sound_category = VarInt.read(file_object)
        self.effect_position = SoundEffectPacket.EffectPosition.read(
            file_object)
        self.volume = Float.read(file_object)
        self.pitch = SoundEffectPacket.Pitch.read_with_context(
            file_object, self.context)
        self.seed = Long.read(file_object)

    def write_fields(self, packet_buffer):
        if self.context.protocol_earlier(761):
            return super(SoundEffectPacket, self).write_fields(packet_buffer)
        sound_id = self.sound_id
        if self.context.protocol_later_eq(766) and sound_id != 0:
            sound_id += 1
        VarInt.send(sound_id, packet_buffer)
        if self.sound_id == 0:
            String.send(self.sound_name, packet_buffer)
            PrefixedOptional(Float).send(self.fixed_range, packet_buffer)
        VarInt.send(self.sound_category, packet_buffer)
        SoundEffectPacket.EffectPosition.send(
            self.effect_position, packet_buffer)
        Float.send(self.volume, packet_buffer)
        SoundEffectPacket.Pitch.send_with_context(
            self.pitch, packet_buffer, self.context)
        Long.send(self.seed, packet_buffer)

    @staticmethod
    def get_definition(context):
        return [
            ({'sound_category': VarInt}
                if context.protocol_later_eq(321)
                and context.protocol_earlier(326) else {}),
            {'sound_id': VarInt},
            ({'sound_category': VarInt}
                if context.protocol_later_eq(95)
                and context.protocol_earlier(321)
                or context.protocol_later_eq(326) else {}),
            ({'parroted_entity_type': String}
                if context.protocol_later_eq(321)
                and context.protocol_earlier(326) else {}),
            {'effect_position': SoundEffectPacket.EffectPosition},
            {'volume': Float},
            {'pitch': SoundEffectPacket.Pitch},
            {'seed': Long} if context.protocol_later_eq(759) else {},
        ]

    class SoundCategory(Enum):
        MASTER = 0
        MUSIC = 1
        RECORDS = 2
        WEATHER = 3
        BLOCKS = 4
        HOSTILE = 5
        NEUTRAL = 6
        PLAYERS = 7
        AMBIENT = 8
        VOICE = 9

    class EffectPosition(Type):
        @classmethod
        def read(cls, file_object):
            return Vector(*(Integer.read(file_object) / 8.0 for i in range(3)))

        @classmethod
        def send(cls, value, socket):
            for coordinate in value:
                Integer.send(int(coordinate * 8), socket)

    class Pitch(Type):
        @staticmethod
        def read_with_context(file_object, context):
            if context.protocol_later_eq(201):
                value = Float.read(file_object)
            else:
                value = Byte.read(file_object)
            if context.protocol_earlier(204):
                value /= 63.5
            return value

        @staticmethod
        def send_with_context(value, socket, context):
            if context.protocol_earlier(204):
                value *= 63.5
            if context.protocol_later_eq(201):
                Float.send(value, socket)
            else:
                Byte.send(int(value), socket)


class NamedSoundEffectPacket(Packet):
    # Note: added in protocol 107 and removed in protocol 761.
    @staticmethod
    def get_id(context):
        return 0x17 if context.protocol_later_eq(760) else \
               0x16 if context.protocol_later_eq(759) else \
               0x19 if context.protocol_later_eq(755) else \
               0x18 if context.protocol_later_eq(751) else \
               0x19 if context.protocol_later_eq(735) else \
               0x1A if context.protocol_later_eq(573) else \
               0x19 if context.protocol_later_eq(477) else \
               0x1A if context.protocol_later_eq(393) else \
               0x19

    packet_name = 'named sound effect'
    get_definition = staticmethod(lambda context: [
        {'sound_name': String},
        {'sound_category': VarInt},
        {'effect_position': SoundEffectPacket.EffectPosition},
        {'volume': Float},
        {'pitch': SoundEffectPacket.Pitch},
        {'seed': Long} if context.protocol_later_eq(759) else {},
    ])

    SoundCategory = SoundEffectPacket.SoundCategory
