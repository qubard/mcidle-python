from src.networking.packet_handler import PacketHandler
from src.networking.packets.clientbound import PlayerListItem

import select


class IdleHandler(PacketHandler):

    # PlayerListItem has to be processed outside worker threads
    def player_list(self, packet):
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
        timeout = 0.05 # Always 50ms
        while self.connection.running:
            try:
                ready_to_read = select.select([self.connection.stream], [], [], timeout)[0]

                if ready_to_read:
                    packet = self.read_packet()

                    if packet.id != PlayerListItem.id:
                        self.connection.packet_logger.enqueue(packet)
                    else:
                        self.player_list(packet)

                    # Forward the packets if a client is connected
                    if self.connection.client_connection and self.connection.client_connection.connected:
                        try:
                            self.connection.client_connection.send_packet_buffer(packet.compressed_buffer)
                        except ConnectionAbortedError:
                            print("Something went wrong", flush=True)
                            pass
            except:
                print("Disconnected from server", flush=True)
                self.connection.running = False
                if self.connection.client_connection:
                    self.connection.client_connection.running = False
