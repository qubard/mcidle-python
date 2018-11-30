from src.networking.packets.serverbound import Handshake, LoginStart, EncryptionResponse
from src.networking.packets.clientbound import EncryptionRequest, SetCompression, LoginSuccess
from src.networking.encryption import *
from src.networking.packet_handler import PacketHandler


class LoginHandler(PacketHandler):
    def handle(self):
        self.login()

    """ Do all the authentication and logging in"""
    def login(self):
        # Send a handshake and login start packet
        handshake = Handshake(ProtocolVersion=self.connection.protocol, ServerAddress=self.connection.address[0], \
                              ServerPort=self.connection.address[1], NextState=2)
        login_start = LoginStart(Name=self.connection.username)

        self.connection.send(handshake)
        self.connection.send(login_start)

        encryption_request = EncryptionRequest().read(self.read_packet_buffer())
        self.connection.VerifyToken = encryption_request.VerifyToken

        # Generate the encryption response to send over
        shared_secret = generate_shared_secret()
        (encrypted_token, encrypted_secret) = encrypt_token_and_secret(encryption_request.PublicKey,
                                                                       encryption_request.VerifyToken, shared_secret)
        encryption_response = EncryptionResponse(SharedSecret=encrypted_secret, VerifyToken=encrypted_token)

        # Generate an auth token, serverID is always empty
        server_id_hash = generate_verification_hash(encryption_request.ServerID, shared_secret,
                                                    encryption_request.PublicKey)

        # Client auth
        self.connection.auth.join(server_id_hash)

        # Send the encryption response
        self.connection.send(encryption_response)

        # Enable encryption using the shared secret
        self.connection.enable_encryption(shared_secret)

        # Enable compression and set the threshold
        set_compression = SetCompression().read(self.read_packet_buffer())
        self.connection.compression_threshold = set_compression.Threshold

        # Now packets are encrypted, so we can switch states after reading the decrypted login success
        self.connection.login_success = LoginSuccess().read(self.read_packet_buffer())


class IdleHandler(PacketHandler):
    """ Idling occurs when we've disconnected our client or have yet to connect """
    def __init__(self):
        super().__init__(self)