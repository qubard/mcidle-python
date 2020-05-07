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
    def __init__(self, ip=None, port=None):
        threading.Thread.__init__(self)
        self.threshold = None
        self.address = (ip, port)
        self.packet_handler = None

        self.socket = None
        self.stream = None

        self.upstream = UpstreamThread()

        self.compression_threshold = None

        self.initialize_socket(socket.socket())

    def stop(self):
        if self.packet_handler:
            self.packet_handler.stop()
        self.upstream.stop()

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
        return True

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

    def run_handler(self):
        if not self.initialize_connection():
            print("Failed to run_handler!", flush=True)
            return

        if self.packet_handler is not None:
            if self.packet_handler.setup():
                self.packet_handler.on_setup()  # Could possibly change the packet handler

                if self.packet_handler.next_handler() is not None \
                        and self.packet_handler.next_handler() != self.packet_handler:
                    self.packet_handler = self.packet_handler.next_handler()

                self.packet_handler.handle()

    def run(self):
        self.run_handler()


# Assume that a MinecraftConnection has to stay active at all times
class MinecraftConnection(Connection):
    def __init__(self, username, ip, protocol, port=25565, server_port=1001, profile=None, listen_thread=None):
        super().__init__(ip, port)

        self.username = username
        self.protocol = protocol
        self.server = None
        self.server_port = server_port
        self.listen_thread = listen_thread

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
        try:
            self.socket.connect(self.address)
            self.worker_processor.start()
            print("Connected MinecraftConnection", flush=True)
            return True
        except ConnectionRefusedError:
            return False

    def stop(self):
        super().stop()
        self.worker_processor.stop()

    def on_disconnect(self):
        print("Called MinecraftConnection::on_disconnect()...", flush=True)
        super().on_disconnect()

        # Terminate all existing threads
        self.stop()

        # Terminate the server threads if there is one
        if self.server is not None:
            self.server.stop()

    def initialize_connection(self):
        if self.connect():
            self.start_server()
            return True
        return False

    def start_server(self):
        self.server = MinecraftServer(self, self.server_port, self.listen_thread)


class MinecraftServer(Connection):
    """ Used for listening on a port for a connection """
    def __init__(self, mc_connection, port=25565, listen_thread=None):
        super().__init__('localhost', port)
        self.mc_connection = mc_connection
        self.packet_handler = ClientboundLoginHandler(self, mc_connection)

        self.running = True
        self.start_lock = RLock()

        # Every second send an animation swing to prevent AFK kicks while client_upstream is DCed
        self.anti_afk = AntiAFKThread(self.mc_connection)
        self.anti_afk.start()

        self.listen_thread = listen_thread.set_server(self)

    # Note that when mcidle terminates first MinecraftConnection does
    def on_disconnect(self):
        print("Called MinecraftServer::on_disconnect()...", flush=True)
        self.stop()
        # Only re-create the server if we're still connected to our target server
        if self.mc_connection and self.mc_connection.upstream.connected():
            super().on_disconnect()
            # Replace our server object to restart the MinecraftServer state easily
            self.mc_connection.start_server()

    def start(self, connection):
        with self.start_lock:
            if self.mc_connection.upstream.connected():
                print("Starting MinecraftServer!", flush=True)
                # Sets our upstream to the client connection
                self.initialize_socket(connection)
                # Runs initialize_connection and the main packet handler in a separate thread
                super().start()

    def stop(self):
        self.running = False
        # Bugfix: Makes sure listen_thread does not have a server
        # So it accepts a new client forcefully
        self.listen_thread.set_server(None)
        super().stop()
        self.anti_afk.stop()
