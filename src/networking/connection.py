import socket
import threading

from .auth import Auth
from .types import VarInt

from .packets.serverbound import Handshake, LoginStart
from .packets.packet_buffer import PacketBuffer
from .packets.clientbound import EncryptionRequest


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
    def read_packet_buffer(self):
        packet_buffer = PacketBuffer()
        length = VarInt.read(self.connection.stream)
        data = self.connection.stream.read(length)
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

        self.connection.socket.send(handshake.write().buffer.get_bytes())
        self.connection.socket.send(login_start.write().buffer.get_bytes())

    def handle(self, packet_buffer):
        encryption_request = EncryptionRequest().read(packet_buffer)
        print(encryption_request)


class IdleHandler(PacketHandler):
    """ Idling occurs when we've disconnected our client or have yet to connect """
    def __init__(self):
        super().__init__(self)


class Connection:
    def __init__(self, username, ip, protocol, port=25565, access_token=None):
        self.socket = socket.socket()
        self.stream = self.socket.makefile('rb')
        self.username = username
        self.address = (ip, port)
        self.encrypted = False
        self.compression = None
        self.protocol = protocol

        self.auth = Auth(username, access_token)

        self.connection_thread = ConnectionThread(self)

    """ Connect to the socket and start a connection thread """
    def connect(self):
        self.socket.connect(self.address)
        self.connection_thread.start()
