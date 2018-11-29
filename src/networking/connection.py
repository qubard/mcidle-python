import socket
import threading

from .auth import Auth
from src.networking.packet_handler.serverbound import LoginHandler as ServerboundLoginHandler
from src.networking.packet_handler.clientbound import LoginHandler as ClientboundLoginHandler


class Connection(threading.Thread):
    def __init__(self, ip=None, port=None):
        threading.Thread.__init__(self)
        self.socket = socket.socket()
        self.address = (ip, port)
        self.packet_handler = None

    def initialize_connection(self):
        pass

    def run(self):
        self.initialize_connection()
        if self.packet_handler is not None:
            self.packet_handler.initialize()
            self.packet_handler.handle()


class MinecraftConnection(Connection):
    def __init__(self, username, ip, protocol, port=25565, profile=None):
        super().__init__(ip, port)

        """ Create a readable only file interface (stream) for the socket """
        self.stream = self.socket.makefile('rb')
        self.username = username
        self.threshold = None
        self.protocol = protocol

        self.auth = Auth(username, profile)

        # Make sure the access token we are using is still valid
        self.auth.validate()

        self.packet_handler = ServerboundLoginHandler(self)

    """ Connect to the socket and start a connection thread """
    def connect(self):
        self.socket.connect(self.address)
        print("Connected", flush=True)

    def initialize_connection(self):
        self.connect()

    """ Connect to the socket and start a connection thread """
    def connect(self):
        self.socket.connect(self.address)
        print("Connected", flush=True)


class MinecraftServer(Connection):
    """ Used for listening on a port for a connection """
    def __init__(self, port=25565):
        super().__init__('localhost', port)
        self.packet_handler = ClientboundLoginHandler(self)

    """ Bind to a socket and wait for a client to connect """
    def initialize_connection(self):
        self.socket.bind(self.address)
        self.socket.listen(1) # Listen for 1 incoming connection

        print("Waiting for client", flush=True)

        (connection, address) = self.socket.accept()

        print("Got client", connection, address, flush=True)
