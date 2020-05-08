from src.networking.packets.packet import Packet
from src.networking.types import String, VarIntPrefixedByteArray, VarInt, Integer, VarIntArray, \
    Long, Byte, Double, Float, Boolean, UUID, Short, ChunkSection, UnsignedByte, ByteArray

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


class TimeUpdate(Packet):
    id = 0x47
    definition =  {
        "WorldAge": Long,
        "TimeOfDay": Long
    }


class HeldItemChange(Packet):
    id = 0x3A
    definition = {
        "Slot": Byte
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


class SetSlot(Packet):
    id = 0x16
    definition = {
        "WindowID": None,
        "Slot": None,
        "SlotData": None,
    }

    # This packet changes a lot depending on the current protocol
    # But only SlotData changes
    # See https://wiki.vg/index.php?title=Slot_Data&oldid=7835 (1.12.2)
    def read_fields(self, packet_buffer):
        self.WindowID = Byte.read(packet_buffer)
        self.Slot = Short.read(packet_buffer)

        # The rest of the packet is SlotData which we don't need to parse

class MultiBlockChange(Packet):
    id = 0x10
    definition = {
        "ChunkX": Integer,
        "ChunkZ": Integer,
        "RecordCount": VarInt,
        "Records": [],
    }

    def read_fields(self, packet_buffer):
        self.ChunkX = Integer.read(packet_buffer)
        self.ChunkZ = Integer.read(packet_buffer)
        self.RecordCount = VarInt.read(packet_buffer)

        count = self.RecordCount
        self.Records = []
        while count > 0:
            pos = UnsignedByte.read(packet_buffer)
            pos_x = (pos & 0xF0) >> 4
            pos_z = pos & 0x0F

            y_coord = UnsignedByte.read(packet_buffer)

            id = VarInt.read(packet_buffer)
            block_type = id >> 4
            block_meta = id & 15

            coords = (self.ChunkX * 16 + pos_x, y_coord, self.ChunkZ * 16 + pos_z)

            self.Records.append((coords, block_type, block_meta))
            print("Coords", coords, "Type", block_type, "Meta", block_meta, flush=True)
            count = count - 1


class ChunkData(Packet):
    id = 0x20
    definition = {
        "ChunkX": Integer,
        "ChunkZ": Integer,
        "NumSections": Integer,
    }

    def read_fields(self, packet_buffer):
        self.ChunkX = Integer.read(packet_buffer)
        self.ChunkZ = Integer.read(packet_buffer)
        self.GroundUpContinuous = Boolean.read(packet_buffer)
        self.PrimaryBitMask = VarInt.read(packet_buffer)
        mask = self.PrimaryBitMask

        #self.NumSections = 0

        # Count the # of bits set
        #while mask > 0:
        #    self.NumSections += mask & 1
        #    mask >>= 1

        #self.Data = VarIntPrefixedByteArray.read(packet_buffer)

        #self.DataLen = VarInt.read(packet_buffer)
        # Read the data array
        # Ref: https://wiki.vg/index.php?title=Chunk_Format&oldid=14135#Data_structure
        sections = []
        #readSections = 0
        #while readSections < self.NumSections:
        #    ChunkSection.read(packet_buffer)
        #    readSections = readSections + 1

        #if self.GroundUpContinuous:
        #    biomes = ByteArray.read(packet_buffer, 256)

        #self.NumBlockEnts = VarInt.read(packet_buffer)


class UnloadChunk(Packet):
    id = 0x1D
    definition =  {
        "ChunkX": Integer,
        "ChunkZ": Integer
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


class GameState(Packet):
    id = 0x1E
    definition = {
        "Reason": Byte,
        "Value": Float,
    }


class Disconnect(Packet):
    id = 0x1A
    definition = {
        "Reason": String
    }


class PlayerAbilities(Packet):
    id = 0x2C
    definition = {
        "Flags": Byte,
        "FlyingSpeed": Float,
        "FOV": Float,
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
