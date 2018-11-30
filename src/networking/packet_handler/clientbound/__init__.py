from src.networking.packet_handler import PacketHandler
from src.networking.packets.serverbound import Handshake, LoginStart, EncryptionResponse
from src.networking.packets.clientbound import EncryptionRequest, SetCompression, LoginSuccess

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15

class LoginHandler(PacketHandler):
    def set_mc_connection(self, mc_connection):
        self.mc_connection = mc_connection
        return self

    def handle(self):
        Handshake().read(self.read_packet_buffer())
        login_start = LoginStart().read(self.read_packet_buffer())

        # Generate a (pubkey, privkey) pair
        privkey = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
        pubkey = privkey.public_key().public_bytes(encoding=serialization.Encoding.DER, format=serialization.PublicFormat.SubjectPublicKeyInfo)

        self.connection.send(EncryptionRequest(ServerID='', PublicKey=pubkey, VerifyToken=self.mc_connection.VerifyToken))

        # The encryption response will be encrypted with the server's public key
        encryption_response = EncryptionResponse().read(self.read_packet_buffer())

        # Decrypt and verify the verify token
        verify_token = privkey.decrypt(encryption_response.VerifyToken, PKCS1v15())
        assert(verify_token == self.mc_connection.VerifyToken)

        # Decrypt the shared secret
        shared_secret = privkey.decrypt(encryption_response.SharedSecret, PKCS1v15())

        # Enable encryption using the shared secret
        self.connection.enable_encryption(shared_secret)

        # Enable compression and assign the threshold to the connection
        self.connection.send(SetCompression(Threshold=self.mc_connection.compression_threshold))
        self.connection.compression_threshold = self.mc_connection.compression_threshold

        self.connection.send(self.mc_connection.login_success)

