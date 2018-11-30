from src.networking.packets.serverbound import Handshake, LoginStart, EncryptionResponse
from src.networking.packets.clientbound import EncryptionRequest, SetCompression, LoginSuccess, ChunkData, \
    UnloadChunk, SpawnEntity, DestroyEntities, KeepAlive
from src.networking.encryption import *
from src.networking.packet_handler import PacketHandler

from src.networking.packets.serverbound import KeepAlive as KeepAliveServerbound

import select


class LoginHandler(PacketHandler):
    def handle(self):
        self.login()

    """ Do all the authentication and logging in"""
    def login(self):
        # Send a handshake and login start packet
        handshake = Handshake(ProtocolVersion=self.connection.protocol, ServerAddress=self.connection.address[0], \
                              ServerPort=self.connection.address[1], NextState=2)
        login_start = LoginStart(Name=self.connection.username)

        self.connection.send_packet(handshake)
        self.connection.send_packet(login_start)

        encryption_request = EncryptionRequest().read(self.read_packet().packet_buffer)
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
        self.connection.send_packet(encryption_response)

        # Enable encryption using the shared secret
        self.connection.enable_encryption(shared_secret)

        # Enable compression and set the threshold
        set_compression = SetCompression().read(self.read_packet().packet_buffer)
        self.connection.compression_threshold = set_compression.Threshold

        # Now packets are encrypted, so we can switch states after reading the decrypted login success
        self.connection.login_success = LoginSuccess().read(self.read_packet().packet_buffer)

        # Switch to idling
        self.connection.packet_handler = IdleHandler(self.connection)
        self.connection.packet_handler.handle()


class IdleHandler(PacketHandler):
    """ Idling occurs when we've disconnected our client or have yet to connect """
    def handle(self):
        timeout = 0.05 # Always 50ms
        while True:
            ready_to_read = select.select([self.connection.stream], [], [], timeout)[0]

            if ready_to_read:
                packet = self.read_packet()

                if packet:
                    if packet.id in self.connection.join_ids:
                        self.connection.packet_log[packet.id] = packet
                    elif packet.id == 0x20: # ChunkData
                        chunk_data = ChunkData().read(packet.packet_buffer)
                        if packet.id not in self.connection.packet_log:
                            self.connection.packet_log[packet.id] = {}
                        self.connection.packet_log[packet.id][(chunk_data.ChunkX, chunk_data.ChunkY)] = packet
                        print("ChunkData", chunk_data.ChunkX, chunk_data.ChunkY)
                    elif packet.id == 0x1D: # UnloadChunk
                        unload_chunk = UnloadChunk().read(packet.packet_buffer)
                        if 0x20 in self.connection.packet_log:
                            del self.connection.packet_log[0x20][(unload_chunk.ChunkX, unload_chunk.ChunkY)]
                            print("UnloadChunk", unload_chunk.ChunkX, unload_chunk.ChunkY)
                    elif packet.id in SpawnEntity.ids:
                        spawn_entity = SpawnEntity().read(packet.packet_buffer)
                        if 0x03 not in self.connection.packet_log:
                            self.connection.packet_log[0x03] = {}
                        self.connection.packet_log[0x03][spawn_entity.EntityID] = packet
                        print("Added entity ID: %s" % spawn_entity.EntityID, self.connection.packet_log[0x03].keys(), flush=True)
                    elif packet.id == 0x32:
                        destroy_entities = DestroyEntities().read(packet.packet_buffer)
                        if 0x03 in self.connection.packet_log:
                            for entity_id in destroy_entities.Entities:
                                print("Removed entity ID: %s" % entity_id, self.connection.packet_log[0x03].keys(), flush=True)
                                del self.connection.packet_log[0x03][entity_id] # Delete the entity
                    elif packet.id == 0x1F: # Keep Alive Clientbound
                        keep_alive = KeepAlive().read(packet.packet_buffer)
                        print("Responded to KeepAlive", keep_alive, flush=True)
                        self.connection.send_packet(KeepAliveServerbound(KeepAliveID=keep_alive.KeepAliveID))
                    elif packet.id == 0x2E:
                        if 0x2E not in self.connection.packet_log:
                            self.connection.packet_log[0x2E] = []
                        self.connection.packet_log[0x2E].append(packet)

                    # Forward the packets if a client is connected, don't send KeepAlive
                    if self.connection.client_connection and self.connection.client_connection.connected and packet.id != 0x1F:
                        try:
                            self.connection.client_connection.send_packet_buffer(packet.compressed_buffer)
                        except ConnectionAbortedError:
                            pass