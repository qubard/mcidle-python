from src.networking.packets.packet import Packet
from src.networking.types import String, Long, UnsignedShort, VarInt, VarIntPrefixedByteArray, \
    Double, Float, Boolean, UnsignedByte, Short, Byte

"""
 Note: not using an OrderedDict for `definition` will break
 in anything older than Python 3.7.1 (the keys will not be in order)
"""


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


class ClientStatus(Packet):
    id = 0x03
    definition = {
        "ActionID": VarInt
    }


class KeepAlive(Packet):
    id = 0x0B
    definition = {
        "KeepAliveID": Long
    }


class PlayerPosition(Packet):
    id = 0x0D
    definition = {
        "X": Double,
        "Y": Double,
        "Z": Double,
        "OnGround": Boolean
    }


class PlayerPositionAndLook(Packet):
    id = 0x0E
    definition = {
        "X": Double,
        "Y": Double,
        "Z": Double,
        "Yaw": Float,
        "Pitch": Float,
        "OnGround": Boolean
    }


class ClickWindow(Packet):
    id = 0x07
    definition = {
        "WindowID": UnsignedByte,
        "Slot": Short,
        "Button": Byte,
        "ActionNumber": Short,
        "Mode": VarInt,
        "ClickedSlot": VarInt
    }