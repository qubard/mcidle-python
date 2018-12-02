from src.networking.packet_handler import PacketHandler
from src.networking.packets.serverbound import Handshake, LoginStart, EncryptionResponse, ClientStatus, \
    PlayerPositionAndLook, TeleportConfirm
from src.networking.packets.clientbound import EncryptionRequest, SetCompression, SpawnEntity, ChunkData, \
    PlayerListItem
from src.networking.packets.clientbound import PlayerPositionAndLook as PlayerPositionAndLookClientbound

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15

import select


class LoginHandler(PacketHandler):
    def __init__(self, connection, mc_connection):
        super().__init__(connection)
        self.mc_connection = mc_connection
        self.teleport_id = 1

    def handle_position_packet(self, packet):
        if packet.id != PlayerPositionAndLook.id:
            return

        pos_packet = PlayerPositionAndLook().read(packet.packet_buffer)
        self.mc_connection.last_yaw = pos_packet.Yaw
        self.mc_connection.last_pitch = pos_packet.Pitch
        self.mc_connection.last_pos_packet = pos_packet

        # Replace the currently logged PlayerPositionAndLookClientbound packet
        self.mc_connection.last_pos_packet = pos_packet

    def join_world(self):
        # Send the player all the packets that lets them join the world
        for id_ in self.mc_connection.join_ids:
            if id_ in self.mc_connection.packet_log:
                packet = self.mc_connection.packet_log[id_]
                self.connection.send_packet_buffer(packet.compressed_buffer)

        # Send them their last position/look if it exists
        if PlayerPositionAndLookClientbound.id in self.mc_connection.packet_log:
            if self.mc_connection and self.mc_connection.last_pos_packet:
                last_packet = self.mc_connection.last_pos_packet

                pos_packet = PlayerPositionAndLookClientbound( \
                    X=last_packet.X, Y=last_packet.Y, Z=last_packet.Z, \
                    Yaw=self.mc_connection.last_yaw, Pitch=self.mc_connection.last_pitch, Flags=0, TeleportID=self.teleport_id)
                self.teleport_id += 1
                self.connection.send_packet(pos_packet)
            else:
                self.connection.send_packet_buffer(
                    self.mc_connection.packet_log[PlayerPositionAndLookClientbound.id] \
                        .compressed_buffer)  # Send the last packet that we got

        # Send the player list items (to see other players)
        if PlayerListItem.id in self.mc_connection.packet_log:
            player_lists = self.mc_connection.packet_log[PlayerListItem.id]
            for packet in player_lists:
                self.connection.send_packet_buffer(packet.compressed_buffer)

        # Send the player all the currently loaded entities
        if SpawnEntity.id in self.mc_connection.packet_log:
            entity_dict = self.mc_connection.packet_log[SpawnEntity.id]
            for packet in entity_dict.values():
                self.connection.send_packet_buffer(packet.compressed_buffer)

        if ChunkData.id in self.mc_connection.packet_log:
            # Send the player all the currently loaded chunks
            chunk_dict = self.mc_connection.packet_log[ChunkData.id]
            print("Sending %s chunks" % len(chunk_dict.values()), flush=True)
            for packet in chunk_dict.values():
                self.connection.send_packet_buffer(packet.compressed_buffer)

        # Player sends ClientStatus, this is important for respawning if died
        self.mc_connection.send_packet(ClientStatus(ActionID=0))

    def handle(self):
        Handshake().read(self.read_packet().packet_buffer)
        LoginStart().read(self.read_packet().packet_buffer)

        # Generate a (pubkey, privkey) pair
        privkey = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
        pubkey = privkey.public_key().public_bytes(encoding=serialization.Encoding.DER, format=serialization.PublicFormat.SubjectPublicKeyInfo)

        self.connection.send_packet(EncryptionRequest(ServerID='', PublicKey=pubkey, VerifyToken=self.mc_connection.VerifyToken))

        # The encryption response will be encrypted with the server's public key
        encryption_response = EncryptionResponse().read(self.read_packet().packet_buffer)

        # Decrypt and verify the verify token
        verify_token = privkey.decrypt(encryption_response.VerifyToken, PKCS1v15())
        assert(verify_token == self.mc_connection.VerifyToken)

        # Decrypt the shared secret
        shared_secret = privkey.decrypt(encryption_response.SharedSecret, PKCS1v15())

        # Enable encryption using the shared secret
        self.connection.enable_encryption(shared_secret)

        # Enable compression and assign the threshold to the connection
        self.connection.send_packet(SetCompression(Threshold=self.mc_connection.compression_threshold))
        self.connection.compression_threshold = self.mc_connection.compression_threshold

        self.connection.send_packet(self.mc_connection.login_success)

        self.join_world()

        # Let the real connection know about our client
        self.mc_connection.client_connection = self.connection

        timeout = 0.05 # Always 50ms
        while self.connection.running:
            try:
                if self.connection.connected:
                    ready_to_read = select.select([self.connection.stream], [], [], timeout)[0]

                    if ready_to_read:
                        packet = self.read_packet()
                        if packet.id != TeleportConfirm.id: # Sending these will crash us
                            self.handle_position_packet(packet)
                            self.mc_connection.send_packet_buffer(packet.compressed_buffer)
            except:
                self.mc_connection.client_connection = None
                self.connection.reset_socket()
                self.mc_connection.start_server() # Start the server again
