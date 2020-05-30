from mcidle.networking.packet_handler import PacketHandler
from mcidle.networking.packets.clientbound import KeepAlive

import select


class IdleHandler(PacketHandler):
    # Idling occurs when we've disconnected our client or have yet to connect
    def handle(self):
        while self.running:
            try:
                # Read a packet from the target server
                ready_to_read = select.select([self.connection.stream], [], [], self._timeout)[0]
                if ready_to_read:
                    packet = self.read_packet_from_stream()
                    if packet:
                        # Entirely thread safe (worker processor only read, not destroyed)
                        self.connection.worker_processor.enqueue(packet)

                        # Forward the packets if a client is connected
                        # Ignore KeepAlive's because those are processed by worker threads
                        # This is thread safe because the old connection is only reassigned never deleted
                        # so while we have a reference it can't be None
                        # Since client_upstream is set in another thread it is wrapped in an RLock
                        if packet.id != KeepAlive.id:
                            self.connection.send_to_client(packet)
                    else:
                        raise EOFError()
            except EOFError:
                print("Disconnected from server, closing", flush=True)
                self.connection.on_disconnect()
                break
