import socket
import threading

from .auth import Auth
from .types import VarInt

from .packets.serverbound import Handshake, LoginStart
from .packets.packet_buffer import PacketBuffer

""" 
By far the best architecture is to assign a single thread to 
each connection and have these threads handle the already
connected socket's behaviour 

This is basically the "adapter" design pattern and makes for
extensibility to separate various connection states.
"""


class ConnectionThread(threading.Thread):
    def __init__(self, connection):
        threading.Thread.__init__(self)
        self.packet_handler = LoginHandler(connection)

    def set_packet_handler(self, packet_handler):
        self.packet_handler = packet_handler

    def run(self):
        if self.packet_handler is not None:
            self.packet_handler.initialize()
            self.packet_handler.handle()


class PacketHandler:
    """ Generic packet handler """
    def __init__(self, connection):
        self.connection = connection

    """ We can't receive or handle packets until we've done basic initialization """
    def initialize(self):
        pass

    """ Read an entire packet into a packet buffer """
    def read_packet(self):
        packet_buffer = PacketBuffer()
        length = VarInt.read(self.connection.stream)
        data = self.connection.stream.read(length)
        VarInt.write(length, packet_buffer)
        packet_buffer.write(self.connection.stream.read(length))
        print("Read length", length, "data", data, "buffer", packet_buffer)
        return packet_buffer

    """ Default behaviour is to consume packets """
    def handle(self):
        pass


class LoginHandler(PacketHandler):
    """ Handles logging in and establishing encryption (if needed) """
    def __init__(self, connection):
        super().__init__(connection)

    def initialize(self):
        handshake = Handshake(ProtocolVersion=self.connection.protocol, ServerAddress="localhost", ServerPort=25565,
                              NextState=2)
        login_start = LoginStart(Name="leddit")

        self.connection.socket.send(handshake.write().buffer.get_bytes())
        self.connection.socket.send(login_start.write().buffer.get_bytes())

    def handle(self):
        self.read_packet()


class IdleHandler(PacketHandler):
    """ Idling occurs when we've disconnected our client or have yet to connect """
    def __init__(self):
        super().__init__(self)


class Connection:
    def __init__(self, username, ip, protocol, port=25565, access_token=None):
        self.socket = socket.socket()
        self.stream = self.socket.makefile('rb')
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
