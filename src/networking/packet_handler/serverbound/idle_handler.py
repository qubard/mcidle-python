from src.networking.packet_handler import PacketHandler
from src.networking.packets.clientbound import PlayerListItem

import select


class IdleHandler(PacketHandler):

    # PlayerListItem has to be processed outside worker threads
    def parse_player_list(self, packet):
        player_list_item = PlayerListItem().read(packet.packet_buffer)

        add_player = 0
        remove_player = 4

        if player_list_item.Action == add_player or player_list_item.Action == remove_player:
            for player in player_list_item.Players:
                uuid = player[0]
                if player_list_item.Action == add_player:
                    self.connection.packet_logger.log[packet.id][uuid] = packet
                elif player_list_item.Action == remove_player:
                    if uuid in self.connection.packet_logger.log[packet.id]:
                        del self.connection.packet_logger.log[packet.id][uuid]

    """ Idling occurs when we've disconnected our client or have yet to connect """
    def handle(self):
        while self.connection.running:
            try:
                ready_to_read = select.select([self.connection.stream], [], [], self._timeout)[0]

                if ready_to_read:
                    packet = self.read_packet_from_stream()

                    if packet:
                        if packet.id != PlayerListItem.id:
                            self.connection.packet_logger.enqueue(packet)
                        else:
                            self.parse_player_list(packet)

                        # Bottleneck around here, we relay packets WAY too slowly apparently
                        # We can try making packet reading multithreaded but essentially send_packet_buffer
                        # takes too long and it'd be nice to chunk as many packets as we could in 50ms to the player
                        # in one buffer

                        # We can try just recv'ing a chunk of bytes instead and pushing it to a queue to be processed
                        # in another thread.m

                        # Forward the packets if a client is connected
                        if self.connection.client_connection:
                            try:
                                self.connection.client_connection.send_packet_buffer(packet.compressed_buffer)
                            except (ConnectionAbortedError, BrokenPipeError, AttributeError):
                                pass
                    else:
                        raise EOFError()
            except EOFError:
                print("Disconnected from server, closing", flush=True)

                # Panic and exit, TODO: try reconnecting at a regular interval
                self.connection.running = False
                if self.connection.client_connection:
                    self.connection.client_connection.on_disconnect()
