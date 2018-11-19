import socket
import threading

from .auth import Auth
from .types import VarInt

from .packets.serverbound import Handshake, LoginStart, EncryptionResponse
from .packets.packet_buffer import PacketBuffer
from .packets.clientbound import EncryptionRequest
from .encryption import *


class ConnectionThread(threading.Thread):
    def __init__(self, connection):
        threading.Thread.__init__(self)
        self.packet_handler = LoginHandler(connection)

    def set_packet_handler(self, packet_handler):
        self.packet_handler = packet_handler

    def run(self):
        if self.packet_handler is not None:
            self.packet_handler.initialize()
            self.packet_handler.handle(self.packet_handler.read_packet_buffer())


class PacketHandler:
    """ Generic packet handler """
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
    def handle(self, packet_buffer):
        encryption_request = EncryptionRequest().read(packet_buffer)

        # Generate the encryption response to send over
        shared_secret = generate_shared_secret()
        (encrypted_token, encrypted_secret) = encrypt_token_and_secret(encryption_request.PublicKey, encryption_request.VerifyToken, shared_secret)
        encryption_response = EncryptionResponse(SharedSecret=encrypted_secret, VerifyToken=encrypted_token)

        # Send the encryption response
        self.connection.socket.send(encryption_response.write().bytes)

        # Enable encryption over the socket
        cipher = create_AES_cipher(shared_secret)
        encryptor = cipher.encryptor()
        decryptor = cipher.decryptor()

        self.connection.socket = EncryptedSocketWrapper(self.connection.socket, encryptor, decryptor)
        self.connection.stream = EncryptedFileObjectWrapper(self.connection.stream, decryptor)

        # Generate an auth token
        self.connection.auth.authenticate()

        if self.connection.auth.validate():
            server_id_hash = generate_verification_hash(encryption_request.ServerID, shared_secret, encryption_request.PublicKey)
            self.connection.auth.join(server_id_hash)

            # Now packets are encrypted, so we can switch states after reading the decrypted login success
            packet_buffer = self.read_packet_buffer()
            login_start = LoginStart().read(packet_buffer)
            print(login_start)


class IdleHandler(PacketHandler):
    """ Idling occurs when we've disconnected our client or have yet to connect """
    def __init__(self):
        super().__init__(self)


class Connection:
    def __init__(self, username, ip, protocol, port=25565, access_token=None, client_token=None):
        self.socket = socket.socket()
        """ Create a readable only file interface (stream) for the socket """
        self.stream = self.socket.makefile('rb')
        self.username = username
        self.address = (ip, port)
        self.compression = None
        self.protocol = protocol

        self.auth = Auth(username, access_token, client_token)

        self.connection_thread = ConnectionThread(self)

    """ Connect to the socket and start a connection thread """
    def connect(self):
        self.socket.connect(self.address)
        self.connection_thread.start()
