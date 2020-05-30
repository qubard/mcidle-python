import threading
import time

from mcidle.networking.packets.serverbound import Animation, ChatMessage, PlayerLook, PlayerPosition

from random import randint, uniform


class AntiAFKThread(threading.Thread):
    def __init__(self, connection, rate=30):
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

                if self.connection.game_state.player_pos:
                    # Move 3 blocks ahead and back
                    for off in range(0, 30):
                        pos = self.connection.game_state.player_pos
                        self.connection.send_packet(PlayerPosition(X=pos[0] + 0.1 * off, \
                                                                   Y=pos[1] + 0.1, Z=pos[2], OnGround=True))
                        time.sleep(0.1)

                    for off in range(30, 0, -1):
                        pos = self.connection.game_state.player_pos
                        self.connection.send_packet(PlayerPosition(X=pos[0] + 0.1 * off, \
                                                                   Y=pos[1] + 0.1, Z=pos[2], OnGround=True))
                        time.sleep(0.1)

                print(self.connection.game_state.player_pos, flush=True)

                # Look around
                self.connection.send_packet(PlayerLook(Yaw=uniform(0, 360), Pitch=uniform(0, 360), OnGround=True))
            time.sleep(self.rate)


