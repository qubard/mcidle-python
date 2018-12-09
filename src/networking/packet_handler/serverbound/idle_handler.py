from src.networking.packet_handler import PacketHandler

import select


class IdleHandler(PacketHandler):

    """ Idling occurs when we've disconnected our client or have yet to connect """
    def handle(self):
        timeout = 0.05 # Always 50ms
        while self.connection.running:
            try:
                ready_to_read = select.select([self.connection.stream], [], [], timeout)[0]

                if ready_to_read:
                    packet = self.read_packet()

                    self.connection.packet_logger.enqueue(packet)

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
