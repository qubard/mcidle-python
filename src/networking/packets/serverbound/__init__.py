from src.networking.packets.packet import Packet
from src.networking.types import String, Long, UnsignedShort, VarInt, VarIntPrefixedByteArray

"""
 Note: not using an OrderedDict for `definition` will break
 in anything older than Python 3.7.1 (the keys will not be in order)
"""


# Useful for mapping packet IDs to their respective classes
def get_packets():
    return {
        packet.id: packet for packet in [KeepAlive, Handshake, LoginStart, EncryptionResponse]
    }


class KeepAlive(Packet):
    id = 0x0E
    definition = {
        "ID": Long
    }


class Handshake(Packet):
    id = 0x00
    definition = {
        "ProtocolVersion": VarInt,
        "ServerAddress": String,
        "ServerPort": UnsignedShort,
        "NextState":  VarInt
    }


class LoginStart(Packet):
    id = 0x00
    definition = {
        "Name": String
    }


class EncryptionResponse(Packet):
    id = 0x01
    definition = {
        "SharedSecret": VarIntPrefixedByteArray,
        "VerifyToken": VarIntPrefixedByteArray
    }