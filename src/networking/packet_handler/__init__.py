from zlib import decompress
from src.networking.types import VarInt
from src.networking.packets.packet_buffer import PacketBuffer
from src.networking.packets.packet import Packet


class PacketHandler:
    """ Generic packet handler responsible for processing incoming packets """
    def __init__(self, connection):
        self.connection = connection

    """ Read the next packet from the stream """
    def read_packet(self, write_length=False):
        packet_buffer = PacketBuffer()
        length = VarInt.read(self.connection.stream)

        data = self.connection.stream.read(length)
        decompressed_data = None

        # Decompress if needed
        if self.connection.compression_threshold:
            compressed_buf = PacketBuffer()
            compressed_buf.write(data)
            compressed_buf.reset_cursor() # Need to reset to read off the compression byte(s)

            decompressed_length = VarInt.read(compressed_buf)
            is_compressed = decompressed_length > 0

            # Chop off the compression byte(s)
            data = compressed_buf.read()

            if is_compressed:
                # Read all the remaining bytes past the compression indicator into the packet buffer
                decompressed_data = decompress(data)
                assert(len(decompressed_data) == decompressed_length)

        id_buffer = PacketBuffer()
        if decompressed_data:
            id_buffer.write(decompressed_data[:5]) # Only need the first 5 bytes for an ID
        else:
            id_buffer.write(data[:5])
        id_buffer.reset_cursor()
        id_ = VarInt.read(id_buffer)

        if write_length:
            VarInt.write(length, packet_buffer)

        if decompressed_data:
            packet_buffer.write(decompressed_data)
        else:
            packet_buffer.write(data)

        packet_buffer.reset_cursor()

        return Packet(packet_buffer_=packet_buffer, compressed_buffer=data, id=id_)

    """ Default behaviour is to consume packets """
    def handle(self):
        pass