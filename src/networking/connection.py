import socket
import threading

from .auth import Auth
from src.networking.encryption import *
from src.networking.packet_handler.serverbound import LoginHandler as ServerboundLoginHandler
from src.networking.packet_handler.clientbound import LoginHandler as ClientboundLoginHandler

from multiprocessing import Manager


class Connection(threading.Thread):
    def __init__(self, ip=None, port=None):
        threading.Thread.__init__(self)
        self.threshold = None
        self.address = (ip, port)
        self.packet_handler = None
        self.running = False

        self.socket = None
        self.stream = None

        self.compression_threshold = None

        self.initialize_socket(socket.socket())

    def initialize_socket(self, sock):
        self.socket = sock
        """ Create a read only blocking file interface (stream) for the socket """
        self.stream = self.socket.makefile('rb')

    def reset_socket(self):
        self.socket.shutdown(2)
        self.socket.close()
        self.socket = None
        self.stream = None

    @property
    def connected(self):
        return self.socket and self.stream

    def enable_encryption(self, shared_secret):
        cipher = create_AES_cipher(shared_secret)
        # Generate the encrypted endpoints
        encryptor = cipher.encryptor()
        decryptor = cipher.decryptor()

        # Replace the socket used with an encrypted socket
        self.socket = EncryptedSocketWrapper(self.socket, encryptor, decryptor)
        self.stream = EncryptedFileObjectWrapper(self.stream, decryptor)

    def initialize_connection(self):
        pass

    def send_packet(self, packet):
        self.socket.send(packet.write(self.compression_threshold).bytes)

    def send_packet_buffer(self, packet_buffer):
        self.socket.send(packet_buffer.bytes)

    def run(self):
        self.running = True
        self.initialize_connection()
        if self.packet_handler is not None:
            self.packet_handler.handle()


class MinecraftConnection(Connection):
    def __init__(self, username, ip, protocol, port=25565, server_port=1001, profile=None):
        super().__init__(ip, port)

        self.username = username
        self.protocol = protocol
        self.server = None
        self.server_port = server_port

        self.held_item_slot = 0
        self.last_pos_packet = None
        self.last_yaw = 0
        self.last_pitch = 0

        self.client_connection = None

        self.auth = Auth(username, profile)

        # Make sure the access token we are using is still valid
        self.auth.validate()

        self.packet_handler = ServerboundLoginHandler(self)

        """ JoinGame, ServerDifficulty, SpawnPosition, PlayerAbilities, Respawn """
        self.join_ids = [0x23, 0x0D, 0x46, 0x2C, 0x35]
        self.manager = Manager()
        self.packet_log = self.manager.dict()

    """ Connect to the socket and start a connection thread """
    def connect(self):
        self.socket.connect(self.address)
        print("Connected", flush=True)

    def initialize_connection(self):
        self.connect()
        self.start_server()

    def start_server(self):
        self.server = MinecraftServer(self.server_port, self)
        self.server.start()

    """ Connect to the socket and start a connection thread """
    def connect(self):
        self.socket.connect(self.address)
        print("Connected", flush=True)


class MinecraftServer(Connection):
    """ Used for listening on a port for a connection """
    def __init__(self, port=25565, mc_connection=None):
        super().__init__('localhost', port)
        self.packet_handler = ClientboundLoginHandler(self, mc_connection)
        self.teleport_id = 2

    """ Bind to a socket and wait for a client to connect """
    def initialize_connection(self):
        self.socket.bind(self.address)
        self.socket.listen(1) # Listen for 1 incoming connection

        print("Waiting for client", flush=True)

        (connection, address) = self.socket.accept()

        # Replace the server socket with the client's socket
        self.initialize_socket(connection)
