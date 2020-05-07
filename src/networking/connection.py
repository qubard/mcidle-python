import socket
import threading

from .auth import Auth
from src.networking.encryption import *
from src.networking.packet_handler.serverbound import LoginHandler as ServerboundLoginHandler
from src.networking.packet_handler.clientbound import LoginHandler as ClientboundLoginHandler

from src.networking.packet_handler import WorkerProcessor, ClientboundProcessor

from src.networking.upstream import UpstreamThread
from src.networking.anti_afk import AntiAFKThread
from src.networking.game_state import GameState


class Connection(threading.Thread):
    def __init__(self, ip=None, port=None, upstream=None):
        threading.Thread.__init__(self)
        self.threshold = None
        self.address = (ip, port)
        self.packet_handler = None

        self.socket = None
        self.stream = None

        if upstream is None:
            self.upstream = UpstreamThread()
        else:
            self.upstream = upstream

        self.compression_threshold = None

        self.initialize_socket(socket.socket())

    def initialize_socket(self, sock):
        self.socket = sock
        """ Create a read only blocking file interface (stream) for the socket """
        self.stream = self.socket.makefile('rb')
        self.upstream.set_socket(self.socket)

    def destroy_socket(self):
        try:
            self.socket.close()
            self.socket = None
            self.stream = None
            self.upstream.set_socket(None)
            print("Socket shutdown and closed.", flush=True)
        except OSError:
            print("Failed to reset socket", flush=True)
            pass

    def enable_encryption(self, shared_secret):
        cipher = create_AES_cipher(shared_secret)
        # Generate the encrypted endpoints
        encryptor = cipher.encryptor()
        decryptor = cipher.decryptor()

        # Replace the socket used with an encrypted socket
        self.socket = EncryptedSocketWrapper(self.socket, encryptor, decryptor)
        print("Set upstream socket", flush=True)
        self.upstream.set_socket(self.socket)
        self.stream = EncryptedFileObjectWrapper(self.stream, decryptor)

    def initialize_connection(self):
        pass

    # We need this to stop reading packets from the dead stream
    # which halts the wait thread
    def on_disconnect(self):
        self.destroy_socket()

    def send_packet_buffer_raw(self, packet_buffer):
        self.socket.send(packet_buffer.bytes)

    def send_packet_raw(self, packet):
        self.socket.send(packet.write(self.compression_threshold).bytes)

    def send_packet(self, packet):
        self.upstream.put(packet.write(self.compression_threshold).bytes)

    def send_packet_buffer(self, packet_buffer):
        self.upstream.put(packet_buffer.bytes)

    def send_packet_dict(self, id_, m):
        if id_ in m:
            packet_dict = m[id_]
            for packet in packet_dict.values():
                self.send_packet_buffer_raw(packet.compressed_buffer)

    def send_single_packet_dict(self, m):
        for packet in m.values():
            self.send_packet_buffer_raw(packet.compressed_buffer)

    def run(self):
        self.initialize_connection()
        if self.packet_handler is not None:
            if self.packet_handler.setup():
                self.packet_handler.on_setup() # Could possibly change the packet handler
                
                if self.packet_handler.next_handler() is not None \
                        and self.packet_handler.next_handler() != self.packet_handler:
                    self.packet_handler = self.packet_handler.next_handler()
                
                self.packet_handler.handle()

# Assume that a MinecraftConnection has to stay active at all times
class MinecraftConnection(Connection):
    def __init__(self, username, ip, protocol, port=25565, server_port=1001, profile=None):
        super().__init__(ip, port)

        self.username = username
        self.protocol = protocol
        self.server = None
        self.server_port = server_port

        # JoinGame, ServerDifficulty, SpawnPosition, Respawn
        join_ids = [0x23, 0x0D, 0x46, 0x35]
        self.game_state = GameState(join_ids)

        self.packet_processor = ClientboundProcessor(self.game_state)

        self.client_connection = None

        self.local_client_upstream = None
        self.client_upstream_lock = RLock()

        self.auth = Auth(username, profile)

        # Make sure the access token we are using is still valid
        self.auth.validate()

        self.packet_handler = ServerboundLoginHandler(self)

        # Process packets in another thread
        self.worker_processor = WorkerProcessor(self, self.packet_processor)
        self.worker_processor.start()

    @property
    def client_upstream(self):
        return self.local_client_upstream

    def set_client_upstream(self, upstream):
        with self.client_upstream_lock:
            self.local_client_upstream = upstream

    # Guarantees upstream is not set to None while putting
    def put_upstream(self, packet):
        with self.client_upstream_lock:
            if self.client_upstream:
                self.client_upstream.put(packet.compressed_buffer.bytes)

    """ Connect to the socket and start a connection thread """
    def connect(self):
        self.socket.connect(self.address)
        print("Connected MinecraftConnection", flush=True)
        
    def on_disconnect(self):
        print("Called MinecraftConnection::on_disconnect()...", flush=True)
        super().on_disconnect()

        # Terminate all existing threads
        self.packet_handler.stop()
        self.worker_processor.stop()

        if self.server is not None:
            self.server.upstream.stop()
            self.server.packet_handler.stop()

    def initialize_connection(self):
        self.connect()
        # Should we wait here or is this blocking?
        self.start_server()

    def start_server(self):
        # Override the old server interface
        # And stop the old thread
        if self.server is not None:
            self.server.upstream.stop()

        self.server = MinecraftServer(self, self.server_port)
        self.server.start() # Start main thread
        

class MinecraftServer(Connection):
    """ Used for listening on a port for a connection """
    def __init__(self, mc_connection, port=25565, upstream=None):
        super().__init__('localhost', port, upstream)
        self.mc_connection = mc_connection
        self.packet_handler = ClientboundLoginHandler(self, mc_connection)

        # Every second send an animation swing to prevent AFK kicks while client_upstream is DCed
        self.anti_afk = AntiAFKThread(self.upstream, self.mc_connection)
        self.anti_afk.start()

    def on_disconnect(self):
        print("Called MinecraftServer::on_disconnect()...", flush=True)
        super().on_disconnect()
        if self.mc_connection:
            # Start listening for a client again
            self.mc_connection.start_server()
            
    """ Bind to a socket and wait for a client to connect """
    def initialize_connection(self):
        try:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(self.address)
            print("Waiting for client", flush=True)
            self.socket.listen(1) # Listen for 1 incoming connection

            (connection, address) = self.socket.accept()

            self.initialize_socket(connection)
        except OSError:
            print("Failed to bind socket (race condition?), it's already on", flush=True)
