from src.networking.packet_handler import PacketHandler
from src.networking.packets.serverbound import Handshake, LoginStart, EncryptionResponse
from src.networking.packets.clientbound import EncryptionRequest, SetCompression

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15


class LoginHandler(PacketHandler):
    def __init__(self, connection, mc_connection):
        super().__init__(connection)
        self.mc_connection = mc_connection

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

        for id_ in self.mc_connection.join_ids:
            if id_ in self.mc_connection.packet_log:
                packet = self.mc_connection.packet_log[id_]
                self.connection.send_packet_buffer(packet.compressed_buffer)

        chunk_dict = self.mc_connection.packet_log[0x20]

        for packet in chunk_dict.values():
            self.connection.send_packet_buffer(packet.compressed_buffer)