import threading
import time

from src.networking.packets.serverbound import Animation, ChatMessage, PlayerLook

from random import randint, uniform


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
                # Try spamming /help
                self.connection.send_packet(ChatMessage(Message="/help"))
                # Swing arm randomly
                self.connection.send_packet(Animation(Hand=randint(0, 1)))

                # Look around
                self.connection.send_packet(PlayerLook(Yaw=uniform(0, 360), Pitch=uniform(0, 360), OnGround=True))
            time.sleep(self.rate)
