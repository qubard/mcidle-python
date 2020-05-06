from src.networking.packet_handler import PacketHandler
from src.networking.packets.clientbound import PlayerListItem, KeepAlive, ChunkData

import select


class IdleHandler(PacketHandler):

    """ Idling occurs when we've disconnected our client or have yet to connect """
    def handle(self):
        while self.connection.running:
            try:
                # Read a packet from the target server
                ready_to_read = select.select([self.connection.stream], [], [], self._timeout)[0]
                if ready_to_read:
                    packet = self.read_packet_from_stream()
                    if packet:
                        self.connection.packet_logger.enqueue(packet)

                        # Forward the packets if a client is connected
                        # Ignore KeepAlive's because those are processed by worker threads
                        if packet.id != KeepAlive.id and self.connection.client_upstream:
                            self.connection.client_upstream.put(packet.compressed_buffer.bytes)
                    else:
                        print("Received invalid packet", flush=True)
            except EOFError:
                print("Disconnected from server, closing", flush=True)
                break
