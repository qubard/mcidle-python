import socket
import threading

from .auth import Auth
from .packet_handler import *


class MinecraftConnection(threading.Thread):
    def __init__(self, username, ip, protocol, port=25565, profile=None):
        threading.Thread.__init__(self)
        self.socket = socket.socket()
        """ Create a readable only file interface (stream) for the socket """
        self.stream = self.socket.makefile('rb')
        self.username = username
        self.address = (ip, port)
        self.threshold = None
        self.protocol = protocol

        self.auth = Auth(username, profile)

        # Make sure the access token we are using is still valid
        self.auth.validate()

        self.packet_handler = LoginHandler(self)

    def run(self):
        self.connect()
        if self.packet_handler is not None:
            self.packet_handler.initialize()
            self.packet_handler.handle()

    """ Connect to the socket and start a connection thread """
    def connect(self):
        self.socket.connect(self.address)
        print("Connected", flush=True)


class MinecraftServer(threading.Thread):
    """ Used for listening on a port for a connection """
    def __init__(self, port=25565):
        threading.Thread.__init__(self)
        self.socket = socket.socket()
        self.address = ('localhost', port)
        self.port = port

    def run(self):
        self.socket.bind(self.address)
        self.socket.listen(1) # Listen for 1 incoming connection

        print("Waiting for client", flush=True)

        (connection, address) = self.socket.accept()

        print("Got client", connection, address, flush=True)
