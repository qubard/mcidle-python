from src.networking.packets.packet import Packet
from src.networking.types import String, VarIntPrefixedByteArray, VarInt

"""
 Note: not using an OrderedDict for `definition` will break
 in anything older than Python 3.7.1 (the keys will not be in order)
"""


# Useful for mapping packet IDs to their respective classes
def get_packets():
    return {
        packet.id: packet for packet in [EncryptionRequest, LoginSuccess, SetCompression]
    }


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