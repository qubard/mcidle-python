from zlib import decompress
from mcidle.networking.types import VarInt
from mcidle.networking.packets.packet_buffer import PacketBuffer
from mcidle.networking.packets.packet import Packet


class PacketHandler:
    _timeout = 0.05

    """ Generic packet handler responsible for processing incoming packets """
    def __init__(self, connection):
        self.connection = connection
        self.running = True
        self.nextHandler = None

    """ Setup the packet handler
        Return whether or not setup succeeded
     """
    def setup(self):
        raise NotImplementedError("setup() is not implemented!")

    """ Called when setup() succeeds """
    def on_setup(self):
        pass

    """ Default behaviour is to consume packets """
    def handle(self):
        pass

    def stop(self):
        self.running = False

    def is_running(self):
        return self.running

    def next_handler(self):
        return self.nextHandler

    # TODO: Maybe put this in a separate class, like PacketStreamReader that takes a connection?
    """ Read the next packet from the stream """
    def read_packet_from_stream(self):
        packet_buffer = PacketBuffer()

        try:
            length = VarInt.read(self.connection.stream)
            data = self.connection.stream.read(length)
        except (ConnectionAbortedError, ConnectionResetError, EOFError, AttributeError) as e:
            print("Exception", e)
            return None

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
        # This packet may or may not actually be compressed
        # Storing the compressed buffer helps w/ performance since we don't have to re-compress it
        compressed_buffer = PacketBuffer()
        VarInt.write(length, compressed_buffer)
        compressed_buffer.write(data)
        compressed_buffer.reset_cursor()

        packet_buffer.reset_cursor()

        return Packet(packet_buffer_=packet_buffer, compressed_buffer=compressed_buffer, id=id_)
