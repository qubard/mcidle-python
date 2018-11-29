from src.networking.packets.serverbound import Handshake, LoginStart, EncryptionResponse
from src.networking.packets.clientbound import EncryptionRequest, SetCompression, LoginSuccess
from src.networking.encryption import *
from src.networking.packet_handler import PacketHandler


class LoginHandler(PacketHandler):
    """ Handles logging in and establishing encryption (if needed) """
    def initialize(self):
        handshake = Handshake(ProtocolVersion=self.connection.protocol, ServerAddress=self.connection.address[0], ServerPort=self.connection.address[1],
                              NextState=2)
        login_start = LoginStart(Name=self.connection.username)

        self.connection.socket.send(handshake.write().bytes)
        self.connection.socket.send(login_start.write().bytes)

    """ Do all the authentication and logging in"""
    def handle(self):
        encryption_request = EncryptionRequest().read(self.read_packet_buffer())

        # Generate the encryption response to send over
        shared_secret = generate_shared_secret()
        (encrypted_token, encrypted_secret) = encrypt_token_and_secret(encryption_request.PublicKey, encryption_request.VerifyToken, shared_secret)
        encryption_response = EncryptionResponse(SharedSecret=encrypted_secret, VerifyToken=encrypted_token)

        # Generate an auth token, serverID is always empty
        server_id_hash = generate_verification_hash(encryption_request.ServerID, shared_secret,
                                                    encryption_request.PublicKey)

        # Client auth
        self.connection.auth.join(server_id_hash)

        # Send the encryption response
        self.connection.socket.send(encryption_response.write().bytes)

        # Enable encryption over the socket
        cipher = create_AES_cipher(shared_secret)
        encryptor = cipher.encryptor()
        decryptor = cipher.decryptor()

        # Replace the socket used with an encrypted socket
        self.connection.socket = EncryptedSocketWrapper(self.connection.socket, encryptor, decryptor)
        self.connection.stream = EncryptedFileObjectWrapper(self.connection.stream, decryptor)

        # Now packets are encrypted, so we can switch states after reading the decrypted login success
        self.connection.threshold = SetCompression().read(self.read_packet_buffer()).Threshold

        login_success = LoginSuccess().read(self.read_packet_buffer())
        print(login_success, flush=True)


class IdleHandler(PacketHandler):
    """ Idling occurs when we've disconnected our client or have yet to connect """
    def __init__(self):
        super().__init__(self)