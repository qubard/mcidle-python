from mcidle.networking.encryption import encrypt_token_and_secret, generate_verification_hash, generate_shared_secret
from mcidle.networking.packets.serverbound import Handshake, LoginStart, EncryptionResponse
from mcidle.networking.packets.clientbound import EncryptionRequest, SetCompression, LoginSuccess
from mcidle.networking.packet_handler import PacketHandler
from mcidle.networking.packets.exceptions import InvalidPacketID

from .idle_handler import IdleHandler


class LoginHandler(PacketHandler):
    def on_setup(self):
        print("Switched to idling.", flush=True)
        self.nextHandler = IdleHandler(self.connection)

    """ Do all the authentication and logging in"""
    def setup(self):
        # Send a handshake and login start packet
        try:
            handshake = Handshake(ProtocolVersion=self.connection.protocol, ServerAddress=self.connection.address[0], \
                                  ServerPort=self.connection.address[1], NextState=2)
            login_start = LoginStart(Name=self.connection.username)

            print("Sending handshake", flush=True)
            self.connection.send_packet_raw(handshake)
            print("Done sending handshake", flush=True)
            self.connection.send_packet_raw(login_start)

            encryption_request = EncryptionRequest().read(self.read_packet_from_stream().packet_buffer)

            self.connection.VerifyToken = encryption_request.VerifyToken

            # Generate the encryption response to send over
            shared_secret = generate_shared_secret()
            (encrypted_token, encrypted_secret) = encrypt_token_and_secret(encryption_request.PublicKey,
                                                                           encryption_request.VerifyToken, shared_secret)
            encryption_response = EncryptionResponse(SharedSecret=encrypted_secret, VerifyToken=encrypted_token)

            # Generate an auth token, serverID is always empty
            server_id_hash = generate_verification_hash(encryption_request.ServerID, shared_secret,
                                                        encryption_request.PublicKey)

            # Client auth
            self.connection.auth.join(server_id_hash)

            # Send the encryption response
            self.connection.send_packet_raw(encryption_response)

            # Enable encryption using the shared secret
            self.connection.enable_encryption(shared_secret)

            print("Enabled encryption", flush=True)

            # Enable compression and set the threshold
            # We aren't sure if compression will be sent, or LoginSuccess immediately after
            unknown_packet = self.read_packet_from_stream().packet_buffer

            print("Unknown packet", unknown_packet, flush=True)
        except (EOFError, ValueError, AttributeError, \
                ConnectionResetError, ConnectionAbortedError, ConnectionRefusedError, ConnectionError):
            # Fail to join
            return False

        try:
            set_compression = SetCompression().read(unknown_packet)
            self.connection.compression_threshold = set_compression.Threshold
            print("Set compression threshold to %s" % self.connection.compression_threshold)

            login_success = LoginSuccess().read(self.read_packet_from_stream().packet_buffer)

            self.connection.game_state.client_uuid = login_success.UUID
            self.connection.game_state.client_username = login_success.Username

            print(login_success.UUID, login_success.Username, flush=True)
        except InvalidPacketID:
            print("Skipping compression..invalid compression packet")
            unknown_packet.reset_cursor()
            self.connection.compression_threshold = -1 # disabled

            self.connection.get_upstream().start()
            return False

        self.connection.upstream.start()
        # Start listening for a connection only if we've officially connected
        self.connection.start_server()

        return True


