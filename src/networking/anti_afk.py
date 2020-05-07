import threading
import time

from src.networking.packets.serverbound import Animation


class AntiAFKThread(threading.Thread):
    def __init__(self, connection, rate=1):
        threading.Thread.__init__(self)
        self.connection = connection
        self.rate = rate
        self.running = True

    def stop(self):
        self.running = False

    def run(self):
        while self.running:
            if self.connection.client_upstream and not self.connection.client_upstream.connected():
                self.connection.send_packet(Animation(Hand=0))
            time.sleep(self.rate)
