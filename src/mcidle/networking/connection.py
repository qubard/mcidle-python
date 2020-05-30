import socket
import threading

from .auth import Auth

from .encryption import (
    EncryptedFileObjectWrapper, EncryptedSocketWrapper, create_AES_cipher
)

from .packet_handler.serverbound import LoginHandler as ServerboundLoginHandler
from .packet_handler.clientbound import LoginHandler as ClientboundLoginHandler
from .packets.clientbound import Respawn, JoinGame

from .packet_handler import WorkerProcessor, ClientboundProcessor

from .upstream import UpstreamThread
from .anti_afk import AntiAFKThread
from .game_state import GameState


class Connection(threading.Thread):
    def __init__(self, ip=None, port=None, upstream=None):
        threading.Thread.__init__(self, daemon=True)
        self.threshold = None
        self.address = (ip, port)
        self.packet_handler = None

        self.socket = None
        self.stream = None

        self.upstream_lock = threading.RLock()
        self.upstream = upstream

        self.compression_threshold = None

        # By default we generate a new socket for our upstream
        # But this is replaced in MinecraftServer with the client
        self.initialize_socket_upstream(socket.socket())

    def stop(self):
        if self.packet_handler:
            self.packet_handler.stop()

        with self.upstream_lock:
            if self.upstream:
                self.upstream.stop()

    def initialize_socket_upstream(self, sock):
        self.initialize_socket(sock)
        with self.upstream_lock:
            if self.upstream:
                self.upstream.set_socket(self.socket)

    def initialize_socket(self, sock):
        self.socket = sock
        self.stream = self.socket.makefile('rb')

    def destroy_socket(self):
        try:
            if self.socket:
                self.socket.close()
            self.socket = None
            self.stream = None
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
        with self.upstream_lock:
            if self.upstream:
                self.upstream.set_socket(self.socket)
        self.stream = EncryptedFileObjectWrapper(self.stream, decryptor)

    def initialize_connection(self):
        return True

    # We need this to stop reading packets from the dead stream
    # which halts the wait thread
    def on_disconnect(self):
        self.stop()
        self.destroy_socket()

    def send_packet_buffer_raw(self, packet_buffer):
        self.socket.send(packet_buffer.bytes)

    def send_packet_raw(self, packet):
        self.socket.send(packet.write(self.compression_threshold).bytes)

    def send_packet(self, packet):
        with self.upstream_lock:
            if self.upstream:
                self.upstream.put(packet.write(self.compression_threshold).bytes)

    def send_packet_buffer(self, packet_buffer):
        with self.upstream_lock:
            if self.upstream:
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
            else:
                # Clean up if we can't even setup the handler
                self.on_disconnect()

    def run(self):
        self.run_handler()


# Assume that a MinecraftConnection has to stay active at all times
class MinecraftConnection(Connection):
    def __init__(self, username, ip, protocol, port=25565, server_port=1001, profile=None, listen_thread=None):
        super().__init__(ip, port, UpstreamThread())

        self.username = username
        self.protocol = protocol
        self.server = None
        self.server_port = server_port
        self.listen_thread = listen_thread

        # JoinGame, ServerDifficulty, SpawnPosition, Respawn, Experience
        join_ids = [JoinGame.id, 0x0D, 0x46, Respawn.id, 0x40]
        self.game_state = GameState(join_ids)

        self.packet_processor = ClientboundProcessor(self.game_state)

        self.client_connection = None

        self.local_client_upstream = None
        self.client_upstream_lock = threading.RLock()

        # Keeping the child server's upstream alive as long as possible prevents the BrokenPipeError bug
        # So pass it in as a construction argument instead of something it spawns itself
        # Then we can just redirect its socket if need be
        self.server_upstream = UpstreamThread()
        self.server_upstream.start()

        self.auth = Auth(username, profile)

        # Make sure the access token we are using is still valid
        self.auth.validate()

        self.packet_handler = ServerboundLoginHandler(self)

        # Every second send an animation swing to prevent AFK kicks while client_upstream is DCed
        self.anti_afk = AntiAFKThread(self)
        self.anti_afk.start()

        # Process packets in another thread
        self.worker_processor = WorkerProcessor(self, self.packet_processor)

    @property
    def client_upstream(self):
        with self.client_upstream_lock:
            return self.local_client_upstream

    def set_client_upstream(self, upstream):
        with self.client_upstream_lock:
            self.local_client_upstream = upstream

    # Sends to the client through its upstream if we have one
    # Guarantees upstream is not set to None while putting
    def send_to_client(self, packet):
        with self.client_upstream_lock:
            if self.local_client_upstream:
                self.local_client_upstream.put(packet.compressed_buffer.bytes)

    """ Connect to the socket and start a connection thread """
    def connect(self):
        try:
            self.socket.connect(self.address)
            self.worker_processor.start()
            print("Connected MinecraftConnection", flush=True)
            return True
        except ConnectionRefusedError:
            print("Cannot connect to target server, connection refused!", flush=True)
            return False

    def stop(self):
        super().stop()
        self.anti_afk.stop()
        with self.client_upstream_lock:
            self.server_upstream.stop()
        self.worker_processor.stop()

    def on_disconnect(self):
        print("Called MinecraftConnection::on_disconnect()...", flush=True)
        super().on_disconnect()

        # Terminate all existing threads
        self.stop()

        # Terminate the server threads if there is one
        if self.server:
            self.server.stop()
            self.server.destroy_socket()

    def initialize_connection(self):
        return self.connect()

    def start_server(self):
        self.server = MinecraftServer(self, self.server_port, self.listen_thread, self.server_upstream)


class MinecraftServer(Connection):
    """ Used for listening on a port for a connection """
    def __init__(self, mc_connection, port=25565, listen_thread=None, upstream=None):
        super().__init__('localhost', port, upstream)
        self.mc_connection = mc_connection
        self.packet_handler = ClientboundLoginHandler(self, mc_connection)

        self.start_lock = threading.Lock()

        self.client_socket = None

        self.listen_thread = listen_thread.set_server(self)

    def finalize_socket_upstream(self):
        self.initialize_socket_upstream(self.client_socket)

    # Note that when mcidle terminates first MinecraftConnection does
    def on_disconnect(self):
        # Sometimes on_disconnect() is called and then in the middle of executing
        # we call start_with_socket which causes a weird bug so we need the lock here
        # to make sure they are separate events
        with self.start_lock:
            print("Called MinecraftServer::on_disconnect()...", flush=True)
            self.stop()
            # Only re-create the server if we're still connected to our target server
            if self.mc_connection and self.mc_connection.upstream.connected():
                self.destroy_socket()
                self.mc_connection.set_client_upstream(None) # Client is no longer connected
                # Replace our server object to restart the MinecraftServer state easily
                # To be honest this is a bad pattern and it's better to just never kill MinecraftServer
                # but then we'd have to overhaul how the packet handlers work since start() calls run()
                # which calls packet handler logic
                # The overhaul would just be to construct the handlers in start_with_socket
                self.mc_connection.start_server()

    def start_with_socket(self, sock):
        with self.start_lock:
            if self.mc_connection.upstream.connected():
                if not self.client_socket:
                    print("Starting MinecraftServer!", flush=True)
                    self.initialize_socket(sock)
                    self.client_socket = sock
                    super().start()
                else:
                    print("Rejected client start_with_socket, client already connected", flush=True)
                    sock.close()

    def stop(self):
        # Bugfix: Makes sure listen_thread does not have a server
        # So it accepts a new client forcefully
        self.listen_thread.set_server(None)
        self.upstream.set_socket(None)

        if self.packet_handler:
            self.packet_handler.stop()

