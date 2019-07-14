from zlib import decompress
from src.networking.types import VarInt
from src.networking.packets.packet_buffer import PacketBuffer
from src.networking.packets.packet import Packet


class PacketHandler:
    """ Generic packet handler responsible for processing incoming packets """
    def __init__(self, connection):
        self.connection = connection

    """ Read the next packet from the stream """
    def read_packet(self):
        packet_buffer = PacketBuffer()

        length = VarInt.read(self.connection.stream)

        data = self.connection.stream.read(length)

        id_buffer = PacketBuffer()

        # Decompress if needed
        threshold = self.connection.compression_threshold

        if threshold is not None and threshold >= 0:
            tmp_buf = PacketBuffer()
            tmp_buf.write(data)
            tmp_buf.reset_cursor() # Need to reset to read off the compression byte(s)

            decompressed_length = VarInt.read(tmp_buf)
            is_compressed = decompressed_length > 0

            if is_compressed:
                # Read all the remaining bytes past the compression indicator into the packet buffer
                decompressed_data = decompress(tmp_buf.read())
                assert(len(decompressed_data) == decompressed_length)
                id_buffer.write(decompressed_data[:5])  # Only need the first 5 bytes for an ID
                packet_buffer.write(decompressed_data)
            else:
                id_buffer.write(data[1:6]) # Ignore the compression=0 byte
                packet_buffer.write(data[1:])
        else:
            id_buffer.write(data[:5])
            packet_buffer.write(data)

        id_buffer.reset_cursor()
        id_ = VarInt.read(id_buffer)

        # Write a compressed buffer with its length and compression indicator
        compressed_buffer = PacketBuffer()
        VarInt.write(length, compressed_buffer)
        compressed_buffer.write(data)
        compressed_buffer.reset_cursor()

        packet_buffer.reset_cursor()

        return Packet(packet_buffer_=packet_buffer, compressed_buffer=compressed_buffer, id=id_)

    """ Default behaviour is to consume packets """
    def handle(self):
        pass
