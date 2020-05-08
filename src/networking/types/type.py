"""Contains definitions for minecraft's different data types
Each type has a method which is used to read and write it.
These definitions and methods are used by the packet definitions
"""
from __future__ import division
import struct
import uuid

from .utility import Vector


class Type:
    __slots__ = ()

    @staticmethod
    def read(stream):
        raise NotImplementedError("Base data type not de-serializable")

    @staticmethod
    def write(value, stream):
        raise NotImplementedError("Base data type not serializable")


class Boolean(Type):
    @staticmethod
    def read(stream):
        return struct.unpack('?', stream.read(1))[0]

    @staticmethod
    def write(value, stream):
        return stream.write(struct.pack('?', value))


class UnsignedByte(Type):
    @staticmethod
    def read(stream):
        return struct.unpack('>B', stream.read(1))[0]

    @staticmethod
    def write(value, stream):
        return stream.write(struct.pack('>B', value))


class Byte(Type):
    @staticmethod
    def read(stream):
        return struct.unpack('>b', stream.read(1))[0]

    @staticmethod
    def write(value, stream):
        return stream.write(struct.pack('>b', value))


class Short(Type):
    @staticmethod
    def read(stream):
        return struct.unpack('>h', stream.read(2))[0]

    @staticmethod
    def write(value, stream):
        return stream.write(struct.pack('>h', value))


class UnsignedShort(Type):
    @staticmethod
    def read(stream):
        return struct.unpack('>H', stream.read(2))[0]

    @staticmethod
    def write(value, stream):
        return stream.write(struct.pack('>H', value))


class Integer(Type):
    @staticmethod
    def read(stream):
        return struct.unpack('>i', stream.read(4))[0]

    @staticmethod
    def write(value, stream):
        return stream.write(struct.pack('>i', value))


class FixedPointInteger(Type):
    @staticmethod
    def read(stream):
        return Integer.read(stream) / 32

    @staticmethod
    def write(value, stream):
        return Integer.write(int(value * 32), stream)


class VarInt(Type):
    @staticmethod
    def read(stream):
        number = 0
        # Limit of 5 bytes, otherwise its possible to cause
        # a DOS attack by sending VarInts that just keep
        # going
        bytes_encountered = 0
        while True:
            byte = stream.read(1)
            if len(byte) < 1:
                raise EOFError("Unexpected end of message.")

            byte = ord(byte)
            number |= (byte & 0x7F) << 7 * bytes_encountered
            if not byte & 0x80:
                break

            bytes_encountered += 1
            if bytes_encountered > 5:
                raise ValueError("Tried to read too long of a VarInt")
        return number

    @staticmethod
    def write(value, stream):
        out = bytes()
        while True:
            byte = value & 0x7F
            value >>= 7
            out += struct.pack("B", byte | (0x80 if value > 0 else 0))
            if value == 0:
                break
        return stream.write(out)

    @staticmethod
    def size(value):
        for max_value, size in VARINT_SIZE_TABLE.items():
            if value < max_value:
                return size
        raise ValueError("Integer too large")


# Maps (maximum integer value -> size of VarInt in bytes)
VARINT_SIZE_TABLE = {
    2 ** 7: 1,
    2 ** 14: 2,
    2 ** 21: 3,
    2 ** 28: 4,
    2 ** 35: 5,
    2 ** 42: 6,
    2 ** 49: 7,
    2 ** 56: 8,
    2 ** 63: 9,
    2 ** 70: 10,
    2 ** 77: 11,
    2 ** 84: 12
}


class Long(Type):
    @staticmethod
    def read(stream):
        return struct.unpack('>q', stream.read(8))[0]

    @staticmethod
    def write(value, stream):
        return stream.write(struct.pack('>q', value))


class UnsignedLong(Type):
    @staticmethod
    def read(stream):
        return struct.unpack('>Q', stream.read(8))[0]

    @staticmethod
    def write(value, stream):
        return stream.write(struct.pack('>Q', value))


class Float(Type):
    @staticmethod
    def read(stream):
        return struct.unpack('>f', stream.read(4))[0]

    @staticmethod
    def write(value, stream):
        return stream.write(struct.pack('>f', value))


class Double(Type):
    @staticmethod
    def read(stream):
        return struct.unpack('>d', stream.read(8))[0]

    @staticmethod
    def write(value, stream):
        return stream.write(struct.pack('>d', value))


class VarIntArray(Type):
    @staticmethod
    def read(stream):
        count = VarInt.read(stream)
        arr = []
        for _ in range(0, count):
            arr.append(VarInt.read(stream))
        return arr

    @staticmethod
    def write(values, stream):
        size = 0
        for value in values:
            size += VarInt.write(value, stream)
        return size


class ShortPrefixedByteArray(Type):
    @staticmethod
    def read(stream):
        length = Short.read(stream)
        return struct.unpack(str(length) + "s", stream.read(length))[0]

    @staticmethod
    def write(value, stream):
        return Short.write(len(value), stream) + stream.write(value)


class ByteArray(Type):
    @staticmethod
    def read(stream, length):
        return struct.unpack(str(length) + "s", stream.read(length))[0]


class VarIntPrefixedByteArray(Type):
    @staticmethod
    def read(stream):
        length = VarInt.read(stream)
        return struct.unpack(str(length) + "s", stream.read(length))[0]

    @staticmethod
    def write(value, stream):
        return VarInt.write(len(value), stream) + stream.write(struct.pack(str(len(value)) + "s", value))


class TrailingByteArray(Type):
    """ A byte array consisting of all remaining data. If present in a packet
        definition, this should only be the type of the last field. """

    @staticmethod
    def read(stream):
        return stream.read()

    @staticmethod
    def write(value, stream):
        return stream.write(value)


class String(Type):
    @staticmethod
    def read(stream):
        length = VarInt.read(stream)
        return stream.read(length).decode("utf-8")

    @staticmethod
    def write(value, stream):
        value = value.encode('utf-8')
        return VarInt.write(len(value), stream) + stream.write(value)


class UUID(Type):
    @staticmethod
    def read(stream):
        return str(uuid.UUID(bytes=stream.read(16)))

    @staticmethod
    def write(value, stream):
        return stream.write(uuid.UUID(value).bytes)


class ChunkSection(Type):

    @staticmethod
    def read(stream):
        # In the latest protocol we have to read a short here (block count)
        # block_count = Short.read(stream)
        bits_per_block = UnsignedByte.read(stream)

        palette_len = VarInt.read(stream)
        if bits_per_block < 4:
            # Indirect palette
            bits_per_block = 4
            # palette = [((p & 0xF0) >> 4, p & 0x0F) for p in palette]
            #print("palette", palette, flush=True)
        if bits_per_block > 8:
            # Direct palette, ignore
            bits_per_block = 13

        if palette_len > 0:
            while palette_len > 0:
                VarInt.read(stream)
                palette_len -= 1

        mask = (1 << bits_per_block) - 1

        data_len = VarInt.read(stream)
        data = []
        num_read = 0
        while num_read < data_len:
            data.append(UnsignedLong.read(stream))
            num_read = num_read + 1

        SECTION_HEIGHT = 16
        SECTION_WIDTH = 16

        for y in range(0, SECTION_HEIGHT):
            for z in range(0, SECTION_WIDTH):
                for x in range(0, SECTION_WIDTH):
                    block_number = ((y * SECTION_HEIGHT) + z) * SECTION_WIDTH + x
                    start_long = (block_number * bits_per_block) // 64
                    start_offset = (block_number * bits_per_block) % 64
                    end_long = ((block_number + 1) * bits_per_block - 1) // 64

                    val = 0
                    if start_long == end_long:
                        val = data[start_long] >> start_offset
                    else:
                        end_offset = 64 - start_offset
                        val = (data[start_long] >> start_offset) | (data[end_long] << end_offset)
                    val &= mask


                    #if palette:
                    #    print(x,y,z, "Type", (palette[val] & 0xF0) >> 4, "Meta", (palette[val] & 0x0F), flush=True)

        block_light = ByteArray.read(stream, 4096 // 2)

        # If there's still data we have sky light
        # Assumes our stream is a packet buffer, not sure if I like this
        sky_light = ByteArray.read(stream, 4096 // 2)


class Position(Type, Vector):
    """3D position vectors with a specific, compact network representation."""
    __slots__ = ()

    @staticmethod
    def read(stream):
        location = UnsignedLong.read(stream)
        x = int(location >> 38)
        y = int((location >> 26) & 0xFFF)
        z = int(location & 0x3FFFFFF)

        if x >= pow(2, 25):
            x -= pow(2, 26)

        if y >= pow(2, 11):
            y -= pow(2, 12)

        if z >= pow(2, 25):
            z -= pow(2, 26)

        return Position(x=x, y=y, z=z)

    @staticmethod
    def write(position, stream):
        # 'position' can be either a tuple or Position object.
        x, y, z = position
        value = ((x & 0x3FFFFFF) << 38) | ((y & 0xFFF) << 26) | (z & 0x3FFFFFF)
        return UnsignedLong.write(value, stream)