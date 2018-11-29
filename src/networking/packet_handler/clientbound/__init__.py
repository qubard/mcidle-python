from src.networking.packet_handler import PacketHandler
from src.networking.packets.serverbound import Handshake, LoginStart


class LoginHandler(PacketHandler):
    def handle(self):
        print(Handshake().read(self.read_packet_buffer()), flush=True)
        print(LoginStart().read(self.read_packet_buffer()), flush=True)