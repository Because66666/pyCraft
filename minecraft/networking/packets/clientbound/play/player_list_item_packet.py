from minecraft.networking.packets import Packet

from minecraft.networking.types import (
    String, Boolean, UnsignedByte, Long, UUID, VarInt, NBT,
    VarIntPrefixedByteArray, PrefixedOptional, PrefixedArray, MutableRecord,
)


# Player Info
class PlayerListItemPacket(Packet):
    @staticmethod
    def get_id(context):
        return 0x44 if context.protocol_later_eq(773) else \
               0x3F if context.protocol_later_eq(770) else \
               0x40 if context.protocol_later_eq(768) else \
               0x3E if context.protocol_later_eq(766) else \
               0x3C if context.protocol_later_eq(764) else \
               0x3A if context.protocol_later_eq(762) else \
               0x36 if context.protocol_later_eq(761) else \
               0x37 if context.protocol_later_eq(760) else \
               0x34 if context.protocol_later_eq(759) else \
               0x36 if context.protocol_later_eq(755) else \
               0x32 if context.protocol_later_eq(741) else \
               0x33 if context.protocol_later_eq(721) else \
               0x34 if context.protocol_later_eq(550) else \
               0x33 if context.protocol_later_eq(471) else \
               0x31 if context.protocol_later_eq(451) else \
               0x30 if context.protocol_later_eq(389) else \
               0x2F if context.protocol_later_eq(345) else \
               0x2E if context.protocol_later_eq(336) else \
               0x2D if context.protocol_later_eq(332) else \
               0x2E if context.protocol_later_eq(318) else \
               0x2D if context.protocol_later_eq(107) else \
               0x38

    packet_name = "player list item"

    fields = 'action_type', 'actions'

    def field_string(self, field):
        if field == 'action_type':
            # 'action_type' is None when a bitmask-style packet (protocols
            # 761 and later) carries no actions, e.g. an empty entry list.
            return self.action_type.__name__ \
                if self.action_type is not None else 'None'
        return super(PlayerListItemPacket, self).field_string(field)

    class PlayerList(object):
        __slots__ = 'players_by_uuid'

        def __init__(self, *items):
            self.players_by_uuid = {item.uuid: item for item in items}

    class PlayerListItem(MutableRecord):
        __slots__ = (
            'uuid', 'name', 'properties', 'gamemode', 'ping', 'display_name')

    class PlayerProperty(MutableRecord):
        __slots__ = 'name', 'value', 'signature'

        def read(self, file_object):
            self.name = String.read(file_object)
            self.value = String.read(file_object)
            is_signed = Boolean.read(file_object)
            if is_signed:
                self.signature = String.read(file_object)
            else:
                self.signature = None

        def send(self, packet_buffer):
            String.send(self.name, packet_buffer)
            String.send(self.value, packet_buffer)
            if self.signature is not None:
                Boolean.send(True, packet_buffer)
                String.send(self.signature, packet_buffer)
            else:
                Boolean.send(False, packet_buffer)

    class Action(MutableRecord):
        __slots__ = 'uuid',

        # The bits of the action bitmask (used in place of the 'action' enum
        # in protocols 761 and later) that this action type carries when
        # written, or None if it has no such representation.
        action_bit = None

        def read(self, file_object, context=None):
            self.uuid = UUID.read(file_object)
            self._read(file_object, context)

        def send(self, packet_buffer, context=None):
            UUID.send(self.uuid, packet_buffer)
            self._send(packet_buffer, context)

        def _read(self, file_object, context=None):
            raise NotImplementedError(
                'This abstract method must be overridden in a subclass.')

        def _send(self, packet_buffer, context=None):
            raise NotImplementedError(
                'This abstract method must be overridden in a subclass.')

        @classmethod
        def type_from_id(cls, action_id):
            for subcls in cls.__subclasses__():
                if getattr(subcls, 'action_id', None) == action_id:
                    return subcls
            raise ValueError("Unknown player list action ID: %s." % action_id)

    class AddPlayerAction(Action):
        __slots__ = ('name', 'properties', 'gamemode', 'ping', 'display_name',
                     'crypto_timestamp', 'crypto_public_key',
                     'crypto_signature')
        action_id = 0
        # In protocols 761 and later, adding a player also carries the
        # game mode, latency and display name of the player.
        action_bit = 0x01 | 0x04 | 0x10 | 0x20

        def _read(self, file_object, context=None):
            self.name = String.read(file_object)
            prop_count = VarInt.read(file_object)
            self.properties = []
            for i in range(prop_count):
                property = PlayerListItemPacket.PlayerProperty()
                property.read(file_object)
                self.properties.append(property)
            self.gamemode = VarInt.read(file_object)
            self.ping = VarInt.read(file_object)
            has_display_name = Boolean.read(file_object)
            if has_display_name:
                self.display_name = String.read(file_object)
            else:
                self.display_name = None
            if context is not None and context.protocol_in_range(759, 761):
                # Profile public-key signature data, sent in protocols 759
                # and 760 only.
                if Boolean.read(file_object):
                    self.crypto_timestamp = Long.read(file_object)
                    self.crypto_public_key = \
                        VarIntPrefixedByteArray.read(file_object)
                    self.crypto_signature = \
                        VarIntPrefixedByteArray.read(file_object)
                else:
                    self.crypto_timestamp = None
                    self.crypto_public_key = None
                    self.crypto_signature = None

        def _send(self, packet_buffer, context=None):
            String.send(self.name, packet_buffer)
            VarInt.send(len(self.properties), packet_buffer)
            for property in self.properties:
                property.send(packet_buffer)
            VarInt.send(self.gamemode, packet_buffer)
            VarInt.send(self.ping, packet_buffer)
            if self.display_name is not None:
                Boolean.send(True, packet_buffer)
                String.send(self.display_name, packet_buffer)
            else:
                Boolean.send(False, packet_buffer)
            if context is not None and context.protocol_in_range(759, 761):
                has_crypto = getattr(self, 'crypto_timestamp', None) \
                    is not None
                Boolean.send(has_crypto, packet_buffer)
                if has_crypto:
                    Long.send(self.crypto_timestamp, packet_buffer)
                    VarIntPrefixedByteArray.send(
                        self.crypto_public_key, packet_buffer)
                    VarIntPrefixedByteArray.send(
                        self.crypto_signature, packet_buffer)

        def apply(self, player_list):
            player = PlayerListItemPacket.PlayerListItem(
                uuid=self.uuid,
                name=self.name,
                properties=self.properties,
                gamemode=self.gamemode,
                ping=self.ping,
                display_name=self.display_name)
            player_list.players_by_uuid[self.uuid] = player

    class ChatSession(MutableRecord):
        # The chat session data of 'InitializeChatAction' (protocols 761
        # and later).
        __slots__ = 'uuid', 'expire_time', 'public_key', 'key_signature'

    class InitializeChatAction(Action):
        # Note: this action exists only in protocols 761 and later.
        __slots__ = 'chat_session',
        action_bit = 0x02

        def apply(self, player_list):
            # The 'PlayerList' model does not track chat sessions.
            pass

    class UpdateGameModeAction(Action):
        __slots__ = 'gamemode'
        action_id = 1
        action_bit = 0x04

        def _read(self, file_object, context=None):
            self.gamemode = VarInt.read(file_object)

        def _send(self, packet_buffer, context=None):
            VarInt.send(self.gamemode, packet_buffer)

        def apply(self, player_list):
            player = player_list.players_by_uuid.get(self.uuid)
            if player:
                player.gamemode = self.gamemode

    class UpdateListedAction(Action):
        # Note: this action exists only in protocols 761 and later.
        __slots__ = 'listed',
        action_bit = 0x08

        def apply(self, player_list):
            # The 'PlayerList' model does not track listed status.
            pass

    class UpdateLatencyAction(Action):
        __slots__ = 'ping'
        action_id = 2
        action_bit = 0x10

        def _read(self, file_object, context=None):
            self.ping = VarInt.read(file_object)

        def _send(self, packet_buffer, context=None):
            VarInt.send(self.ping, packet_buffer)

        def apply(self, player_list):
            player = player_list.players_by_uuid.get(self.uuid)
            if player:
                player.ping = self.ping

    class UpdateDisplayNameAction(Action):
        __slots__ = 'display_name'
        action_id = 3
        action_bit = 0x20

        def _read(self, file_object, context=None):
            has_display_name = Boolean.read(file_object)
            if has_display_name:
                self.display_name = String.read(file_object)
            else:
                self.display_name = None

        def _send(self, packet_buffer, context=None):
            if self.display_name is not None:
                Boolean.send(True, packet_buffer)
                String.send(self.display_name, packet_buffer)
            else:
                Boolean.send(False, packet_buffer)

        def apply(self, player_list):
            player = player_list.players_by_uuid.get(self.uuid)
            if player:
                player.display_name = self.display_name

    class RemovePlayerAction(Action):
        action_id = 4
        # In protocols 761 and later, this action no longer exists in the
        # vanilla packet (in protocols 764 and later, removal is handled by
        # the separate PlayerRemovePacket). pyCraft retains it for backward
        # compatibility, representing it with an otherwise-unused bit of the
        # action bitmask of protocols 761 to 767; it has no representation
        # in protocols 768 and later.
        action_bit = 0x40

        def _read(self, file_object, context=None):
            pass

        def _send(self, packet_buffer, context=None):
            pass

        def apply(self, player_list):
            if self.uuid in player_list.players_by_uuid:
                del player_list.players_by_uuid[self.uuid]

    class UpdateListOrderAction(Action):
        # Note: this action exists only in protocols 768 and later.
        __slots__ = 'list_priority',
        action_bit = None  # Depends on the protocol version; see below.

        def _read(self, file_object, context=None):
            self.list_priority = VarInt.read(file_object)

        def _send(self, packet_buffer, context=None):
            VarInt.send(self.list_priority, packet_buffer)

        def apply(self, player_list):
            # The 'PlayerList' model does not track list order.
            pass

    class UpdateHatAction(Action):
        # Note: this action exists only in protocols 769 and later.
        __slots__ = 'show_hat',
        action_bit = None  # Depends on the protocol version; see below.

        def _read(self, file_object, context=None):
            self.show_hat = Boolean.read(file_object)

        def _send(self, packet_buffer, context=None):
            Boolean.send(self.show_hat, packet_buffer)

        def apply(self, player_list):
            # The 'PlayerList' model does not track hat visibility.
            pass

    def read(self, file_object):
        if self.context is not None and self.context.protocol_later_eq(761):
            return self._read_bitmask(file_object)
        action_id = VarInt.read(file_object)
        self.action_type = PlayerListItemPacket.Action.type_from_id(action_id)
        action_count = VarInt.read(file_object)
        self.actions = []
        for i in range(action_count):
            action = self.action_type()
            action.read(file_object, self.context)
            self.actions.append(action)

    def _read_bitmask(self, file_object):
        # In protocols 761 and later, the packet begins with a bitmask of
        # the actions applied to every entry, and each entry carries the
        # fields of every action given in the bitmask.
        mask = UnsignedByte.read(file_object)
        self.actions = []
        for i in range(VarInt.read(file_object)):
            uuid = UUID.read(file_object)
            fields = {}
            if mask & 0x01:  # add_player
                fields['name'] = String.read(file_object)
                fields['properties'] = []
                for j in range(VarInt.read(file_object)):
                    property = PlayerListItemPacket.PlayerProperty()
                    property.read(file_object)
                    fields['properties'].append(property)
            if mask & 0x02:  # initialize_chat
                if Boolean.read(file_object):
                    fields['chat_session'] = \
                        PlayerListItemPacket.ChatSession(
                            uuid=UUID.read(file_object),
                            expire_time=Long.read(file_object),
                            public_key=VarIntPrefixedByteArray.read(
                                file_object),
                            key_signature=VarIntPrefixedByteArray.read(
                                file_object))
                else:
                    fields['chat_session'] = None
            if mask & 0x04:  # update_game_mode
                fields['gamemode'] = VarInt.read(file_object)
            if mask & 0x08:  # update_listed
                fields['listed'] = Boolean.read(file_object)
            if mask & 0x10:  # update_latency
                fields['ping'] = VarInt.read(file_object)
            if mask & 0x20:  # update_display_name
                # In protocol 765 and later, the display name is an NBT
                # chat component rather than a JSON string.
                fields['display_name'] = PrefixedOptional(NBT) \
                    .read_with_context(file_object, self.context) \
                    if self.context.protocol_later_eq(765) else \
                    PrefixedOptional(String).read(file_object)
            if self.context.protocol_later_eq(768) and \
                    mask & self._list_order_bit():  # update_list_order
                fields['list_priority'] = VarInt.read(file_object)
            if self.context.protocol_later_eq(769) and \
                    mask & 0x40:  # update_hat
                fields['show_hat'] = Boolean.read(file_object)

            # Emit one action per set bit, so that no field of the entry is
            # lost when the mask combines several actions. An 'add_player'
            # action also absorbs the game mode, latency and display name,
            # as it did in protocols before 761.
            PLI = PlayerListItemPacket
            if mask & 0x40 and self.context.protocol_earlier(768):
                # remove_player (pyCraft extension; see the comment on
                # 'RemovePlayerAction')
                self.actions.append(PLI.RemovePlayerAction(uuid=uuid))
            if mask & 0x01:  # add_player
                self.actions.append(PLI.AddPlayerAction(
                    uuid=uuid,
                    name=fields.get('name'),
                    properties=fields.get('properties', []),
                    gamemode=fields.get('gamemode'),
                    ping=fields.get('ping'),
                    display_name=fields.get('display_name')))
            if mask & 0x02:  # initialize_chat
                self.actions.append(PLI.InitializeChatAction(
                    uuid=uuid, chat_session=fields.get('chat_session')))
            if mask & 0x04 and not mask & 0x01:  # update_game_mode
                self.actions.append(PLI.UpdateGameModeAction(
                    uuid=uuid, gamemode=fields.get('gamemode')))
            if mask & 0x08:  # update_listed
                self.actions.append(PLI.UpdateListedAction(
                    uuid=uuid, listed=fields.get('listed')))
            if mask & 0x10 and not mask & 0x01:  # update_latency
                self.actions.append(PLI.UpdateLatencyAction(
                    uuid=uuid, ping=fields.get('ping')))
            if mask & 0x20 and not mask & 0x01:  # update_display_name
                self.actions.append(PLI.UpdateDisplayNameAction(
                    uuid=uuid, display_name=fields.get('display_name')))
            if self.context.protocol_later_eq(768) and \
                    mask & self._list_order_bit():  # update_list_order
                self.actions.append(PLI.UpdateListOrderAction(
                    uuid=uuid, list_priority=fields.get('list_priority')))
            if self.context.protocol_later_eq(769) and \
                    mask & 0x40:  # update_hat
                self.actions.append(PLI.UpdateHatAction(
                    uuid=uuid, show_hat=fields.get('show_hat')))
        self.action_type = type(self.actions[0]) if self.actions else None

    def _list_order_bit(self):
        # The bit of the action bitmask representing 'update_list_order';
        # in protocols 769 and later, the 0x40 bit is 'update_hat' instead.
        return 0x80 if self.context.protocol_later_eq(769) else 0x40

    def write_fields(self, packet_buffer):
        if self.context is not None and self.context.protocol_later_eq(761):
            return self._write_bitmask(packet_buffer)
        VarInt.send(self.action_type.action_id, packet_buffer)
        VarInt.send(len(self.actions), packet_buffer)
        for action in self.actions:
            action.send(packet_buffer, self.context)

    def _write_bitmask(self, packet_buffer):
        PLI = PlayerListItemPacket
        mask = 0
        for action in self.actions:
            bit = type(action).action_bit
            if isinstance(action, PLI.UpdateListOrderAction):
                bit = self._list_order_bit()
            elif isinstance(action, PLI.UpdateHatAction):
                bit = 0x40
            elif isinstance(action, PLI.RemovePlayerAction) and \
                    self.context.protocol_later_eq(768):
                raise ValueError(
                    'RemovePlayerAction has no representation in protocols '
                    '768 and later; use PlayerRemovePacket instead.')
            mask |= bit or 0
        UnsignedByte.send(mask, packet_buffer)
        VarInt.send(len(self.actions), packet_buffer)
        for action in self.actions:
            UUID.send(action.uuid, packet_buffer)
            if mask & 0x01:  # add_player
                String.send(getattr(action, 'name', ''), packet_buffer)
                properties = getattr(action, 'properties', ())
                VarInt.send(len(properties), packet_buffer)
                for property in properties:
                    property.send(packet_buffer)
            if mask & 0x02:  # initialize_chat
                session = getattr(action, 'chat_session', None)
                Boolean.send(session is not None, packet_buffer)
                if session is not None:
                    UUID.send(session.uuid, packet_buffer)
                    Long.send(session.expire_time, packet_buffer)
                    VarIntPrefixedByteArray.send(
                        session.public_key, packet_buffer)
                    VarIntPrefixedByteArray.send(
                        session.key_signature, packet_buffer)
            if mask & 0x04:  # update_game_mode
                VarInt.send(getattr(action, 'gamemode', 0), packet_buffer)
            if mask & 0x08:  # update_listed
                Boolean.send(getattr(action, 'listed', True), packet_buffer)
            if mask & 0x10:  # update_latency
                VarInt.send(getattr(action, 'ping', 0), packet_buffer)
            if mask & 0x20:  # update_display_name
                display_name = getattr(action, 'display_name', None)
                if self.context.protocol_later_eq(765):
                    PrefixedOptional(NBT).send_with_context(
                        display_name, packet_buffer, self.context)
                else:
                    PrefixedOptional(String).send(display_name, packet_buffer)
            if self.context.protocol_later_eq(768) and \
                    mask & self._list_order_bit():  # update_list_order
                VarInt.send(getattr(action, 'list_priority', 0),
                            packet_buffer)
            if self.context.protocol_later_eq(769) and \
                    mask & 0x40:  # update_hat
                Boolean.send(getattr(action, 'show_hat', True),
                             packet_buffer)

    def apply(self, player_list):
        for action in self.actions:
            action.apply(player_list)


class PlayerRemovePacket(Packet):
    """ The 'player info remove' packet, split off from the player info
        (PlayerListItemPacket) packet in protocol 764. """
    @staticmethod
    def get_id(context):
        return 0x43 if context.protocol_later_eq(773) else \
               0x3E if context.protocol_later_eq(770) else \
               0x3F if context.protocol_later_eq(768) else \
               0x3D if context.protocol_later_eq(766) else \
               0x3B

    packet_name = "player remove"
    definition = [
        {'uuids': PrefixedArray(VarInt, UUID)}]

    def apply(self, player_list):
        for uuid in self.uuids:
            if uuid in player_list.players_by_uuid:
                del player_list.players_by_uuid[uuid]
