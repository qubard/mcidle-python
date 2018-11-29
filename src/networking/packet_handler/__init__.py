from zlib import decompress
from src.networking.types import VarInt
from src.networking.packets.packet_buffer import PacketBuffer


class PacketHandler:
    """ Generic packet handler responsible for processing incoming packets """
    def __init__(self, connection):
        self.connection = connection

    """ We can't receive or handle packets until we've done basic initialization """
    def initialize(self):
        pass

    """ Read the next packet into a packet buffer """
    def read_packet_buffer(self, write_length=False):
        packet_buffer = PacketBuffer()
        length = VarInt.read(self.connection.stream)

        data = self.connection.stream.read(length)

        # Decompress if needed
        if self.connection.threshold:
            compressed_buf = PacketBuffer()
            compressed_buf.write(data)
            compressed_buf.reset_cursor() # Need to reset to read off the compression byte(s)

            decompressed_length = VarInt.read(compressed_buf)
            is_compressed = decompressed_length > 0

            # Chop off the compression byte(s)
            data = compressed_buf.read()

            if is_compressed:
                # Read all the remaining bytes past the compression indicator into the packet buffer
                data = decompress(data)
                assert(len(data) == decompressed_length)

        if write_length:
            VarInt.write(length, packet_buffer)

        packet_buffer.write(data)
        packet_buffer.reset_cursor()

        return packet_buffer

    """ Default behaviour is to consume packets """
    def handle(self):
        pass