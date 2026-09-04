import pynbt

from minecraft.networking.packets import Packet
from minecraft.networking.types import (
    Type, NBT, Integer, Boolean, UnsignedByte, String, Byte, Long, VarInt,
    Position, PrefixedArray, PrefixedOptional, MutableRecord, Difficulty,
    GameMode, Dimension,
)


def nbt_to_snbt(tag):
    '''Convert a pyNBT tag to SNBT ("stringified NBT") format.'''
    scalars = {
        pynbt.TAG_Byte: 'b',
        pynbt.TAG_Short: 's',
        pynbt.TAG_Int: '',
        pynbt.TAG_Long: 'l',
        pynbt.TAG_Float: 'f',
        pynbt.TAG_Double: 'd',
    }
    if type(tag) in scalars:
        return repr(tag.value) + scalars[type(tag)]

    arrays = {
        pynbt.TAG_Byte_Array: 'B',
        pynbt.TAG_Int_Array: 'I',
        pynbt.TAG_Long_Array: 'L',
    }
    if type(tag) in arrays:
        return '[' + arrays[type(tag)] + ';' + \
               ','.join(map(repr, tag.value)) + ']'

    if isinstance(tag, pynbt.TAG_String):
        return repr(tag.value)

    if isinstance(tag, pynbt.TAG_List):
        return '[' + ','.join(map(nbt_to_snbt, tag.value)) + ']'

    if isinstance(tag, pynbt.TAG_Compound):
        return '{' + ','.join(n + ':' + nbt_to_snbt(v)
                              for (n, v) in tag.items()) + '}'

    raise TypeError('Unknown NBT tag type: %r' % type(tag))


class DeathLocation(MutableRecord, Type):
    """ The 'death' compound of JoinGamePacket and RespawnPacket (protocols
        759 and later), wrapped in a 'PrefixedOptional' in the packet
        definitions. """
    __slots__ = 'dimension_name', 'location'

    @classmethod
    def read_with_context(cls, file_object, context):
        return cls(dimension_name=String.read(file_object),
                   location=Position.read_with_context(file_object, context))

    @classmethod
    def send_with_context(cls, record, socket, context):
        String.send(record.dimension_name, socket)
        Position.send_with_context(record.location, socket, context)


class SpawnInfo(MutableRecord, Type):
    """ The 'world_state' compound of JoinGamePacket and RespawnPacket
        (protocols 766 and later). """
    __slots__ = ('dimension', 'world_name', 'hashed_seed', 'game_mode',
                 'previous_game_mode', 'is_debug', 'is_flat', 'death',
                 'portal_cooldown', 'sea_level')

    def __init__(self, **kwds):
        self.dimension = 0
        self.world_name = 'minecraft:overworld'
        self.hashed_seed = 0
        self.game_mode = 0
        self.previous_game_mode = 255  # As an unsigned byte, -1 (none).
        self.is_debug = False
        self.is_flat = False
        self.death = None
        self.portal_cooldown = 0
        self.sea_level = 63
        super(SpawnInfo, self).__init__(**kwds)

    @classmethod
    def read_with_context(cls, file_object, context):
        record = cls(
            dimension=VarInt.read(file_object),
            world_name=String.read(file_object),
            hashed_seed=Long.read(file_object),
            game_mode=Byte.read(file_object),
            previous_game_mode=UnsignedByte.read(file_object),
            is_debug=Boolean.read(file_object),
            is_flat=Boolean.read(file_object),
            death=PrefixedOptional(DeathLocation).read_with_context(
                file_object, context),
            portal_cooldown=VarInt.read(file_object))
        if context.protocol_later_eq(768):
            record.sea_level = VarInt.read(file_object)
        return record

    @classmethod
    def send_with_context(cls, record, socket, context):
        VarInt.send(record.dimension, socket)
        String.send(record.world_name, socket)
        Long.send(record.hashed_seed, socket)
        Byte.send(record.game_mode, socket)
        UnsignedByte.send(record.previous_game_mode, socket)
        Boolean.send(record.is_debug, socket)
        Boolean.send(record.is_flat, socket)
        PrefixedOptional(DeathLocation).send_with_context(
            record.death, socket, context)
        VarInt.send(record.portal_cooldown, socket)
        if context.protocol_later_eq(768):
            VarInt.send(record.sea_level, socket)


def _world_state_alias(attr, default=None):
    """ Create a property giving access to a field that, in protocols 766
        and later, resides in the 'world_state' SpawnInfo record of the
        packet, and in earlier protocols is a direct field of the packet.
        The property may be set when 'context' is undefined; the value is
        then stored in both locations. """
    private_attr = '_' + attr

    def getter(self):
        # pylint: disable=protected-access
        if self.context is not None and self.context.protocol_later_eq(766):
            world_state = self.world_state
            if world_state is not None:
                return getattr(world_state, attr)
            return default
        return getattr(self, private_attr, default)

    def setter(self, value):
        setattr(self, private_attr, value)
        if self.world_state is None:
            self.world_state = SpawnInfo()
        setattr(self.world_state, attr, value)

    def deleter(self):
        # pylint: disable=protected-access
        if hasattr(self, private_attr):
            delattr(self, private_attr)
        world_state = self.world_state
        if world_state is not None and hasattr(world_state, attr):
            delattr(world_state, attr)

    return property(getter, setter, deleter)


class AbstractDimensionPacket(Packet):
    ''' The abstract superclass of JoinGamePacket and RespawnPacket, containing
        common definitions relating to their 'dimension' field.
    '''

    # The 'world_state' SpawnInfo record of protocols 766 and later; None
    # until set. The following properties provide version-independent
    # access to the fields it contains (see '_world_state_alias').
    world_state = None

    dimension = _world_state_alias('dimension')
    world_name = _world_state_alias('world_name')
    hashed_seed = _world_state_alias('hashed_seed')
    previous_game_mode = _world_state_alias('previous_game_mode')
    is_debug = _world_state_alias('is_debug')
    is_flat = _world_state_alias('is_flat')
    death = _world_state_alias('death')
    portal_cooldown = _world_state_alias('portal_cooldown', 0)
    sea_level = _world_state_alias('sea_level')

    def field_string(self, field):
        # pylint: disable=no-member
        if self.context.protocol_in_range(748, 759) and field == 'dimension':
            return nbt_to_snbt(self.dimension)
        elif self.context.protocol_earlier(718) and field == 'dimension':
            return Dimension.name_from_value(self.dimension)
        return super(AbstractDimensionPacket, self).field_string(field)


class JoinGamePacket(AbstractDimensionPacket):
    @staticmethod
    def get_id(context):
        return 0x30 if context.protocol_later_eq(773) else \
               0x2B if context.protocol_later_eq(770) else \
               0x2C if context.protocol_later_eq(768) else \
               0x2B if context.protocol_later_eq(766) else \
               0x29 if context.protocol_later_eq(764) else \
               0x28 if context.protocol_later_eq(762) else \
               0x24 if context.protocol_later_eq(761) else \
               0x25 if context.protocol_later_eq(760) else \
               0x23 if context.protocol_later_eq(759) else \
               0x26 if context.protocol_later_eq(755) else \
               0x24 if context.protocol_later_eq(741) else \
               0x25 if context.protocol_later_eq(721) else \
               0x26 if context.protocol_later_eq(550) else \
               0x25 if context.protocol_later_eq(389) else \
               0x24 if context.protocol_later_eq(345) else \
               0x23 if context.protocol_later_eq(332) else \
               0x24 if context.protocol_later_eq(318) else \
               0x23 if context.protocol_later_eq(107) else \
               0x01

    packet_name = "join game"

    @staticmethod
    def get_definition(context):
        if context.protocol_later_eq(766):
            # In protocols 766 and later, the world-related fields are
            # grouped into the 'world_state' SpawnInfo record.
            return [
                {'entity_id': Integer},
                {'is_hardcore': Boolean},
                {'world_names': PrefixedArray(VarInt, String)},
                {'max_players': VarInt},
                {'render_distance': VarInt},
                {'simulation_distance': VarInt},
                {'reduced_debug_info': Boolean},
                {'respawn_screen': Boolean},
                {'do_limited_crafting': Boolean},
                {'world_state': SpawnInfo},
                {'enforces_secure_chat': Boolean},
            ]
        if context.protocol_later_eq(764):
            # In protocols 764 and 765, the 'dimension_codec' and 'dimension'
            # NBT fields are replaced by a dimension type ID string, and the
            # field order differs from that of earlier protocols.
            return [
                {'entity_id': Integer},
                {'is_hardcore': Boolean},
                {'world_names': PrefixedArray(VarInt, String)},
                {'max_players': VarInt},
                {'render_distance': VarInt},
                {'simulation_distance': VarInt},
                {'reduced_debug_info': Boolean},
                {'respawn_screen': Boolean},
                {'do_limited_crafting': Boolean},
                {'dimension': String},
                {'world_name': String},
                {'hashed_seed': Long},
                {'game_mode': UnsignedByte},
                {'previous_game_mode': Byte},
                {'is_debug': Boolean},
                {'is_flat': Boolean},
                {'death': PrefixedOptional(DeathLocation)},
                {'portal_cooldown': VarInt},
            ]
        return [
            {'entity_id': Integer},
            {'is_hardcore': Boolean} if context.protocol_later_eq(738) else {},
            {'game_mode': UnsignedByte},
            {'previous_game_mode': UnsignedByte}
            if context.protocol_later_eq(730) else {},
            {'world_names': PrefixedArray(VarInt, String)}
            if context.protocol_later_eq(722) else {},
            {'dimension_codec': NBT}
            if context.protocol_later_eq(718) else {},
            {'dimension':
             String if context.protocol_later_eq(759) else
             NBT if context.protocol_later_eq(748) else
             String if context.protocol_later_eq(718) else
             Integer if context.protocol_later_eq(108) else
             Byte},
            {'world_name': String} if context.protocol_later_eq(722) else {},
            {'hashed_seed': Long} if context.protocol_later_eq(552) else {},
            {'difficulty': UnsignedByte}
            if context.protocol_earlier(464) else {},
            {'max_players':
                VarInt if context.protocol_later_eq(749) else UnsignedByte},
            {'level_type': String} if context.protocol_earlier(716) else {},
            {'render_distance': VarInt}
            if context.protocol_later_eq(468) else {},
            {'simulation_distance': VarInt}
            if context.protocol_later_eq(757) else {},
            {'reduced_debug_info': Boolean},
            {'respawn_screen': Boolean}
            if context.protocol_later_eq(571) else {},
            {'is_debug': Boolean} if context.protocol_later_eq(716) else {},
            {'is_flat': Boolean} if context.protocol_later_eq(716) else {},
            {'death': PrefixedOptional(DeathLocation)}
            if context.protocol_later_eq(759) else {},
            {'portal_cooldown': VarInt}
            if context.protocol_later_eq(763) else {},
        ]

    do_limited_crafting = False
    enforces_secure_chat = False

    # These aliases declare the Enum type corresponding to each field:
    Difficulty = Difficulty
    GameMode = GameMode

    # Accesses the 'game_mode' field appropriately depending on the protocol.
    # Can be set or deleted when 'context' is undefined.
    @property
    def game_mode(self):
        if self.context.protocol_later_eq(766):
            world_state = self.world_state
            if world_state is not None:
                return world_state.game_mode
            return None
        elif self.context.protocol_later_eq(738):
            return self._game_mode_738
        else:
            return self._game_mode_0

    @game_mode.setter
    def game_mode(self, value):
        self._game_mode_738 = value
        self._game_mode_0 = value
        if self.world_state is None:
            self.world_state = SpawnInfo()
        self.world_state.game_mode = value

    @game_mode.deleter
    def game_mode(self):
        del self._game_mode_738
        del self._game_mode_0
        if self.world_state is not None and \
                hasattr(self.world_state, 'game_mode'):
            del self.world_state.game_mode

    # Accesses the 'is_hardcore' field, or its equivalent in older protocols.
    # Can be set or deleted when 'context' is undefined.
    @property
    def is_hardcore(self):
        if self.context.protocol_later_eq(738):
            return self._is_hardcore
        else:
            return bool(self._game_mode_0 & GameMode.HARDCORE)

    @is_hardcore.setter
    def is_hardcore(self, value):
        self._is_hardcore = value
        self._game_mode_0 = \
            getattr(self, '_game_mode_0', 0) | GameMode.HARDCORE \
            if value else \
            getattr(self, '_game_mode_0', 0) & ~GameMode.HARDCORE

    @is_hardcore.deleter
    def is_hardcore(self):
        if hasattr(self, '_is_hardcore'):
            del self._is_hardcore
        if hasattr(self, '_game_mode_0'):
            self._game_mode_0 &= ~GameMode.HARDCORE

    # Accesses the component of the 'game_mode' field without any hardcore bit,
    # version-independently. Can be set or deleted when 'context' is undefined.
    @property
    def pure_game_mode(self):
        if self.context.protocol_later_eq(766):
            world_state = self.world_state
            if world_state is not None:
                return world_state.game_mode
            return None
        elif self.context.protocol_later_eq(738):
            return self._game_mode_738
        else:
            return self._game_mode_0 & ~GameMode.HARDCORE

    @pure_game_mode.setter
    def pure_game_mode(self, value):
        self._game_mode_738 = value
        self._game_mode_0 = \
            value & ~GameMode.HARDCORE | \
            getattr(self, '_game_mode_0', 0) & GameMode.HARDCORE
        if self.world_state is None:
            self.world_state = SpawnInfo()
        self.world_state.game_mode = value & ~GameMode.HARDCORE

    def field_string(self, field):
        if field == 'dimension_codec':
            # pylint: disable=no-member
            return nbt_to_snbt(self.dimension_codec)
        return super(JoinGamePacket, self).field_string(field)


class RespawnPacket(AbstractDimensionPacket):
    @staticmethod
    def get_id(context):
        return 0x50 if context.protocol_later_eq(773) else \
               0x4B if context.protocol_later_eq(770) else \
               0x4C if context.protocol_later_eq(768) else \
               0x47 if context.protocol_later_eq(766) else \
               0x45 if context.protocol_later_eq(765) else \
               0x43 if context.protocol_later_eq(764) else \
               0x41 if context.protocol_later_eq(762) else \
               0x3D if context.protocol_later_eq(761) else \
               0x3E if context.protocol_later_eq(760) else \
               0x3B if context.protocol_later_eq(759) else \
               0x3D if context.protocol_later_eq(755) else \
               0x39 if context.protocol_later_eq(741) else \
               0x3A if context.protocol_later_eq(721) else \
               0x3B if context.protocol_later_eq(550) else \
               0x3A if context.protocol_later_eq(471) else \
               0x38 if context.protocol_later_eq(461) else \
               0x39 if context.protocol_later_eq(451) else \
               0x38 if context.protocol_later_eq(389) else \
               0x37 if context.protocol_later_eq(352) else \
               0x36 if context.protocol_later_eq(345) else \
               0x35 if context.protocol_later_eq(336) else \
               0x34 if context.protocol_later_eq(332) else \
               0x35 if context.protocol_later_eq(318) else \
               0x33 if context.protocol_later_eq(70) else \
               0x07

    packet_name = 'respawn'

    @staticmethod
    def get_definition(context):
        if context.protocol_later_eq(766):
            # In protocols 766 and later, the world-related fields are
            # grouped into the 'world_state' SpawnInfo record, and
            # 'copy_metadata' is a byte of flags rather than a Boolean.
            return [
                {'world_state': SpawnInfo},
                {'copy_metadata': UnsignedByte},
            ]
        if context.protocol_later_eq(764):
            # In protocols 764 and 765, 'copy_metadata' is moved to the end
            # of the packet.
            return [
                {'dimension': String},
                {'world_name': String},
                {'hashed_seed': Long},
                {'game_mode': Byte},
                {'previous_game_mode': UnsignedByte},
                {'is_debug': Boolean},
                {'is_flat': Boolean},
                {'death': PrefixedOptional(DeathLocation)},
                {'portal_cooldown': VarInt},
                {'copy_metadata': Boolean},
            ]
        return [
            {'dimension':
             String if context.protocol_later_eq(759) else
             NBT if context.protocol_later_eq(748) else
             String if context.protocol_later_eq(718) else
             Integer},
            {'world_name': String} if context.protocol_later_eq(719) else {},
            {'difficulty': UnsignedByte}
            if context.protocol_earlier(464) else {},
            {'hashed_seed': Long} if context.protocol_later_eq(552) else {},
            {'game_mode':
             Byte if context.protocol_later_eq(760) else UnsignedByte},
            {'previous_game_mode': UnsignedByte}
            if context.protocol_later_eq(730) else {},
            {'level_type': String} if context.protocol_earlier(716) else {},
            {'is_debug': Boolean} if context.protocol_later_eq(716) else {},
            {'is_flat': Boolean} if context.protocol_later_eq(716) else {},
            {'copy_metadata': Boolean}
            if context.protocol_later_eq(714) else {},
            {'death': PrefixedOptional(DeathLocation)}
            if context.protocol_later_eq(759) else {},
            {'portal_cooldown': VarInt}
            if context.protocol_later_eq(763) else {},
        ]

    copy_metadata = 0

    # These aliases declare the Enum type corresponding to each field:
    Difficulty = Difficulty
    GameMode = GameMode

    # Accesses the 'game_mode' field, which in protocols 766 and later
    # resides in the 'world_state' SpawnInfo record.
    game_mode = _world_state_alias('game_mode')
