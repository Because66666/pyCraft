#!/usr/bin/env python
"""
Full chat-bot example: signs in with a Microsoft account (device-code
flow, no password needed), connects to a server, listens to every
clientbound packet type implemented by pyCraft, and sends chat lines
read from standard input.

Everything is configured by the constants below -- just edit them and
run:

    python examples/chat_bot.py

Chat commands:
    /respawn  respawn the player
    /quit     disconnect and exit
"""
import os
import sys

# Allow running this example straight from the repository checkout.
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))

from minecraft import authentication  # noqa: E402
from minecraft.exceptions import YggdrasilError  # noqa: E402
from minecraft.networking.connection import Connection  # noqa: E402
from minecraft.networking.packets import (  # noqa: E402
    Packet, clientbound, serverbound)

play = clientbound.play

# ---------------------------------------------------------------------------
# Configuration (hardcoded on purpose -- this is an example).
# ---------------------------------------------------------------------------

#: Microsoft account email. Only used to name the token cache files
#: and to print who is logging in; may be left empty.
USERNAME = "you@example.com"

#: Server to connect to.
ADDRESS = "localhost"
PORT = 25565

#: Directory for the Microsoft token cache; None means the default
#: (~/.minecraft/nmp-cache).
CACHE_DIR = None

# ---------------------------------------------------------------------------
# Authentication: Microsoft device-code flow. On the first run a
# verification URL and device code are printed; open the URL in a
# browser and enter the code. Afterwards cached tokens are reused.
# ---------------------------------------------------------------------------


def on_device_code(data):
    print(f"访问 {data['verification_uri']}?otc={data['user_code']} 以授权。")


auth_token = authentication.MicrosoftAuthenticationToken()
try:
    auth_token.authenticate(USERNAME, cache_dir=CACHE_DIR,
                            on_device_code=on_device_code)
except YggdrasilError as error:
    print(error)
    sys.exit(1)
print("Logged in as %s..." % auth_token.username)

connection = Connection(ADDRESS, PORT, auth_token=auth_token)

# ---------------------------------------------------------------------------
# Packet listeners. All listeners use the @connection.listener decorator.
# ---------------------------------------------------------------------------


def print_packet(category, packet):
    print("[%s] %s" % (category, packet))


def print_chat(packet):
    content = getattr(packet, "json_data", packet)
    print("[chat] %s" % content)


# --- login lifecycle ---

@connection.listener(play.JoinGamePacket)
def handle_join_game(packet):
    print_packet("event: joined the game", packet)


@connection.listener(play.RespawnPacket)
def handle_respawn(packet):
    print_packet("event: respawned", packet)


@connection.listener(play.DisconnectPacket)
def handle_disconnect(packet):
    print_packet("event: disconnected by server", packet.json_data)


@connection.listener(play.StartConfigurationPacket)
def handle_start_configuration(packet):
    print("[event] entering configuration state")


# --- chat (all variants across protocol versions) ---

@connection.listener(play.ChatMessagePacket)
def handle_chat_message(packet):
    print_chat(packet)


@connection.listener(play.PlayerChatPacket)
def handle_player_chat(packet):
    print_chat(packet)


@connection.listener(play.SystemChatPacket)
def handle_system_chat(packet):
    print_chat(packet)


@connection.listener(play.ProfilelessChatPacket)
def handle_profileless_chat(packet):
    print_chat(packet)


# --- world state ---

@connection.listener(play.KeepAlivePacket)
def handle_keep_alive(packet):
    print_packet("keep-alive", packet)


@connection.listener(play.TimeUpdatePacket)
def handle_time_update(packet):
    print_packet("time", packet)


@connection.listener(play.UpdateHealthPacket)
def handle_update_health(packet):
    print_packet("health", packet)


@connection.listener(play.ServerDifficultyPacket)
def handle_server_difficulty(packet):
    print_packet("difficulty", packet)


@connection.listener(play.BlockChangePacket)
def handle_block_change(packet):
    print_packet("block", packet)


@connection.listener(play.MultiBlockChangePacket)
def handle_multi_block_change(packet):
    print_packet("blocks", packet)


@connection.listener(play.ExplosionPacket)
def handle_explosion(packet):
    print_packet("explosion", packet)


@connection.listener(play.MapPacket)
def handle_map(packet):
    print_packet("map", packet)


@connection.listener(play.SoundEffectPacket)
def handle_sound_effect(packet):
    print_packet("sound", packet)


@connection.listener(play.NamedSoundEffectPacket)
def handle_named_sound_effect(packet):
    print_packet("sound", packet)


@connection.listener(play.ResourcePackSendPacket)
def handle_resource_pack(packet):
    print_packet("resource-pack", packet)


# --- entities and movement ---

@connection.listener(play.SpawnPlayerPacket)
def handle_spawn_player(packet):
    print_packet("spawn-player", packet)


@connection.listener(play.SpawnObjectPacket)
def handle_spawn_object(packet):
    print_packet("spawn-object", packet)


@connection.listener(play.EntityPositionDeltaPacket)
def handle_entity_position_delta(packet):
    print_packet("entity-move", packet)


@connection.listener(play.EntityLookPacket)
def handle_entity_look(packet):
    print_packet("entity-look", packet)


@connection.listener(play.EntityVelocityPacket)
def handle_entity_velocity(packet):
    print_packet("entity-velocity", packet)


@connection.listener(play.PlayerPositionAndLookPacket)
def handle_player_position_and_look(packet):
    print_packet("teleport", packet)


@connection.listener(play.FacePlayerPacket)
def handle_face_player(packet):
    print_packet("face-player", packet)


# --- combat ---

@connection.listener(play.CombatEventPacket)
def handle_combat_event(packet):
    print_packet("combat", packet)


@connection.listener(play.EnterCombatEventPacket)
def handle_enter_combat(packet):
    print_packet("combat", packet)


@connection.listener(play.EndCombatEventPacket)
def handle_end_combat(packet):
    print_packet("combat", packet)


@connection.listener(play.DeathCombatEventPacket)
def handle_death_combat(packet):
    print_packet("combat", packet)


# --- player list ---

@connection.listener(play.PlayerListItemPacket)
def handle_player_list_item(packet):
    print_packet("player-list", packet)


@connection.listener(play.PlayerRemovePacket)
def handle_player_remove(packet):
    print_packet("player-list", packet)


@connection.listener(play.PlayerListHeaderAndFooterPacket)
def handle_player_list_header_and_footer(packet):
    print_packet("player-list", packet)


# --- catch-all: any packet not handled above ---

#: Packet types that have a specific listener registered above.
HANDLED_TYPES = (
    play.JoinGamePacket, play.RespawnPacket, play.DisconnectPacket,
    play.StartConfigurationPacket, play.ChatMessagePacket,
    play.PlayerChatPacket, play.SystemChatPacket,
    play.ProfilelessChatPacket, play.KeepAlivePacket,
    play.TimeUpdatePacket, play.UpdateHealthPacket,
    play.ServerDifficultyPacket, play.BlockChangePacket,
    play.MultiBlockChangePacket, play.ExplosionPacket, play.MapPacket,
    play.SoundEffectPacket, play.NamedSoundEffectPacket,
    play.ResourcePackSendPacket, play.SpawnPlayerPacket,
    play.SpawnObjectPacket, play.EntityPositionDeltaPacket,
    play.EntityLookPacket, play.EntityVelocityPacket,
    play.PlayerPositionAndLookPacket, play.FacePlayerPacket,
    play.CombatEventPacket, play.EnterCombatEventPacket,
    play.EndCombatEventPacket, play.DeathCombatEventPacket,
    play.PlayerListItemPacket, play.PlayerRemovePacket,
    play.PlayerListHeaderAndFooterPacket,
)


@connection.listener(Packet, early=True)
def handle_any_packet(packet):
    if type(packet) is Packet or type(packet) not in HANDLED_TYPES:
        print_packet("packet", packet)


# ---------------------------------------------------------------------------
# Connect and run the chat loop.
# ---------------------------------------------------------------------------

connection.connect()

while True:
    try:
        text = input()
    except (EOFError, KeyboardInterrupt):
        print("Bye!")
        sys.exit()

    if text == "/respawn":
        packet = serverbound.play.ClientStatusPacket()
        packet.action_id = serverbound.play.ClientStatusPacket.RESPAWN
        connection.write_packet(packet)
        print("Respawning...")
    elif text == "/quit":
        print("Bye!")
        sys.exit()
    elif text:
        packet = serverbound.play.ChatPacket()
        packet.message = text
        connection.write_packet(packet)
