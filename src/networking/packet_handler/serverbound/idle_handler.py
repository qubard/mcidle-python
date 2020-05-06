from src.networking.packet_handler import PacketHandler
from src.networking.packets.clientbound import PlayerListItem, KeepAlive, ChunkData

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
                # Read a packet from the target server
                ready_to_read = select.select([self.connection.stream], [], [], self._timeout)[0]
                if ready_to_read:
                    packet = self.read_packet_from_stream()
                    if packet:
                        if packet.id != PlayerListItem.id:
                            self.connection.packet_logger.enqueue(packet)
                        else:
                            self.parse_player_list(packet)

                        # Forward the packets if a client is connected
                        # Ignore KeepAlive's because those are processed by worker threads
                        if packet.id != KeepAlive.id and self.connection.client_upstream:
                            self.connection.client_upstream.put(packet.compressed_buffer.bytes)
                    else:
                        print("Received invalid packet", flush=True)
            except EOFError:
                print("Disconnected from server, closing", flush=True)
                break
