from zlib import decompress
from .types import VarInt

from .packets.serverbound import Handshake, LoginStart, EncryptionResponse
from .packets.packet_buffer import PacketBuffer
from .packets.clientbound import EncryptionRequest, SetCompression, LoginSuccess
from .encryption import *


class PacketHandler:
    """ Generic packet handler responsible for processing incoming packets """
    def __init__(self, connection):
        self.connection = connection

    """ We can't receive or handle packets until we've done basic initialization """
    def initialize(self):
        pass

    """ Read the next packet into a packet buffer """
    def read_packet_buffer(self, write_length=False):
        packet_buffer = PacketBuffer()
        length = VarInt.read(self.connection.stream)

        data = self.connection.stream.read(length)

        # Decompress if needed
        if self.connection.threshold:
            compressed_buf = PacketBuffer()
            compressed_buf.write(data)
            compressed_buf.reset_cursor() # Need to reset to read off the compression byte(s)

            decompressed_length = VarInt.read(compressed_buf)
            is_compressed = decompressed_length > 0

            # Chop off the compression byte(s)
            data = compressed_buf.read()

            if is_compressed:
                # Read all the remaining bytes past the compression indicator into the packet buffer
                data = decompress(data)
                assert(len(data) == decompressed_length)

        if write_length:
            VarInt.write(length, packet_buffer)

        packet_buffer.write(data)
        packet_buffer.reset_cursor()

        return packet_buffer

    """ Default behaviour is to consume packets """
    def handle(self, packet_buffer):
        pass


class LoginHandler(PacketHandler):
    """ Handles logging in and establishing encryption (if needed) """
    def __init__(self, connection):
        super().__init__(connection)

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