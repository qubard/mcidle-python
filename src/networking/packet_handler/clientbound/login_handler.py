from src.networking.packet_handler import PacketHandler
from src.networking.packets.serverbound import Handshake, LoginStart, EncryptionResponse, ClientStatus
from src.networking.packets.clientbound import EncryptionRequest, SetCompression

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15

import select


class LoginHandler(PacketHandler):
    def __init__(self, connection, mc_connection):
        super().__init__(connection)
        self.mc_connection = mc_connection

    def join_world(self):
        # Send the player all the packets that lets them join the world
        for id_ in self.mc_connection.join_ids:
            if id_ in self.mc_connection.packet_log:
                packet = self.mc_connection.packet_log[id_]
                self.connection.send_packet_buffer(packet.compressed_buffer)

        # Send the player list items (to see other players)
        if 0x2E in self.mc_connection.packet_log:
            player_lists = self.mc_connection.packet_log[0x2E]
            for packet in player_lists:
                self.connection.send_packet_buffer(packet.compressed_buffer)

        # Send the player all the currently loaded entities
        if 0x03 in self.mc_connection.packet_log:
            entity_dict = self.mc_connection.packet_log[0x03]
            for packet in entity_dict.values():
                self.connection.send_packet_buffer(packet.compressed_buffer)

        if 0x20 in self.mc_connection.packet_log:
            # Send the player all the currently loaded chunks
            chunk_dict = self.mc_connection.packet_log[0x20]
            for packet in chunk_dict.values():
                self.connection.send_packet_buffer(packet.compressed_buffer)

        # Player sends ClientStatus, this is important for respawning if died
        self.mc_connection.send_packet(ClientStatus(ActionID=0))

    def handle(self):
        Handshake().read(self.read_packet().packet_buffer)
        LoginStart().read(self.read_packet().packet_buffer)

        # Generate a (pubkey, privkey) pair
        privkey = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
        pubkey = privkey.public_key().public_bytes(encoding=serialization.Encoding.DER, format=serialization.PublicFormat.SubjectPublicKeyInfo)

        self.connection.send_packet(EncryptionRequest(ServerID='', PublicKey=pubkey, VerifyToken=self.mc_connection.VerifyToken))

        # The encryption response will be encrypted with the server's public key
        encryption_response = EncryptionResponse().read(self.read_packet().packet_buffer)

        # Decrypt and verify the verify token
        verify_token = privkey.decrypt(encryption_response.VerifyToken, PKCS1v15())
        assert(verify_token == self.mc_connection.VerifyToken)

        # Decrypt the shared secret
        shared_secret = privkey.decrypt(encryption_response.SharedSecret, PKCS1v15())

        # Enable encryption using the shared secret
        self.connection.enable_encryption(shared_secret)

        # Enable compression and assign the threshold to the connection
        self.connection.send_packet(SetCompression(Threshold=self.mc_connection.compression_threshold))
        self.connection.compression_threshold = self.mc_connection.compression_threshold

        self.connection.send_packet(self.mc_connection.login_success)

        self.join_world()

        # Let the real connection know about our client
        self.mc_connection.client_connection = self.connection

        timeout = 0.05 # Always 50ms
        while True:
            try:
                if self.connection.connected:
                    ready_to_read = select.select([self.connection.stream], [], [], timeout)[0]

                    if ready_to_read:
                        packet = self.read_packet()
                        if packet:
                            self.mc_connection.send_packet_buffer(packet.compressed_buffer)
            except:
                self.connection.reset_socket()
                self.mc_connection.start_server() # Start the server again