import threading
import time

from src.networking.packets.serverbound import Animation


class AntiAFKThread(threading.Thread):
    def __init__(self, connection, rate=5):
        threading.Thread.__init__(self, daemon=True)
        self.connection = connection
        self.rate = rate
        self.running = True

    def stop(self):
        self.running = False

    def run(self):
        while self.running:
            if self.connection.game_state.received_position \
                    and not (self.connection.client_upstream and self.connection.client_upstream.connected()):
                print("Sent AntiAFK packet", flush=True)
                self.connection.send_packet(Animation(Hand=0))
            time.sleep(self.rate)
