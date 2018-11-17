from src.networking.packets.packet import Packet
from src.networking.types import String, Long, UnsignedShort, VarInt

"""
 Note: not using an OrderedDict for `definition` will break
 in anything older than Python 3.7.1 (the keys will not be in order)
"""

# Useful for mapping packet IDs to their respective classes
def get_packets():
    return {
        p.id: p for p in [KeepAlive, EncryptionRequest, LoginStart, Handshake]
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


class EncryptionRequest(Packet):
    id = 0x01
    definition = {
        "ServerId": String,
        "PubKey": String,
        "Token": String
    }


class LoginStart(Packet):
    id = 0x00
    definition = {
        "Name": String
    }