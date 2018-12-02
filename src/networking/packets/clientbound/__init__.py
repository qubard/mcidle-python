from src.networking.packets.packet import Packet
from src.networking.types import String, VarIntPrefixedByteArray, VarInt, Integer, VarIntArray, \
    Long, Byte, Double, Float, Boolean, UUID

"""
 Note: not using an OrderedDict for `definition` will break
 in anything older than Python 3.7.1 (the keys will not be in order)
"""


class EncryptionRequest(Packet):
    id = 0x01
    definition = {
        "ServerID": String,
        "PublicKey": VarIntPrefixedByteArray,
        "VerifyToken": VarIntPrefixedByteArray
    }


class LoginSuccess(Packet):
    id = 0x02
    definition = {
        "UUID": String,
        "Username": String
    }


class SetCompression(Packet):
    id = 0x03
    definition = {
        "Threshold": VarInt
    }


class ChunkData(Packet):
    id = 0x20
    definition =  {
        "ChunkX": Integer,
        "ChunkY": Integer
    }


class UnloadChunk(Packet):
    id = 0x1D
    definition =  {
        "ChunkX": Integer,
        "ChunkY": Integer
    }


class SpawnEntity(Packet):
    id = 0x03
    ids = [0x00, 0x01, 0x03, 0x04, 0x05, 0x25]
    definition = {
        "EntityID": VarInt
    }


class DestroyEntities(Packet):
    id = 0x32
    definition = {
        "Entities": VarIntArray
    }


class KeepAlive(Packet):
    id = 0x1F
    definition = {
        "KeepAliveID": Long
    }


class ChatMessage(Packet):
    id = 0x0F
    definition = {
        "Chat": String,
        "Position": Byte
    }


class PlayerPositionAndLook(Packet):
    id = 0x2F
    definition = {
        "X": Double,
        "Y": Double,
        "Z": Double,
        "Yaw": Float,
        "Pitch": Float,
        "Flags": Byte,
        "TeleportID": VarInt
    }


class PlayerListItem(Packet):
    id = 0x2E
    definition = {
        "Action": None,
        "NumberOfPlayers": None,
        "Players": None
    }

    def read_fields(self, packet_buffer):
        self.Action = VarInt.read(packet_buffer)
        self.NumberOfPlayers = VarInt.read(packet_buffer)
        self.Players = []

        for _ in range(0, self.NumberOfPlayers):
            uuid = UUID.read(packet_buffer)
            player = [uuid]
            if self.Action == 0: # Add Player
                name = String.read(packet_buffer)
                number_of_properties = VarInt.read(packet_buffer)
                properties = []
                for _ in range(0, number_of_properties):
                    name = String.read(packet_buffer)
                    value = String.read(packet_buffer)
                    signature = None
                    if Boolean.read(packet_buffer): # has signature
                        signature = String.read(packet_buffer)
                    properties.append((name, value, signature))

                gamemode = VarInt.read(packet_buffer)
                ping = VarInt.read(packet_buffer)

                display_name = None
                if Boolean.read(packet_buffer): # has display name
                    display_name = String.read(packet_buffer)

                player.append((name, properties, gamemode, ping, display_name))
            elif self.Action == 1: # Update Gamemode
                player.append(VarInt.read(packet_buffer))
            elif self.Action == 2: # Update Latency
                player.append(VarInt.read(packet_buffer))
            elif self.Action == 3: # Update Display Name
                has_display_name = Boolean.read(packet_buffer)
                if has_display_name:
                    player.append(String.read(packet_buffer))
            self.Players.append(player)
