from src.networking.packets.packet import Packet
from src.networking.types import String, VarIntPrefixedByteArray, VarInt, Integer, VarIntArray, Long, Byte

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
    ids = [0x0, 0x01, 0x03, 0x04, 0x05, 0x25]
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