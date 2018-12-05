from src.networking.packet_handler import PacketHandler
from src.networking.packets.serverbound import KeepAlive as KeepAliveServerbound, TeleportConfirm
from src.networking.packets.clientbound import ChunkData, UnloadChunk, SpawnEntity, Disconnect, \
    DestroyEntities, KeepAlive, ChatMessage, PlayerListItem, PlayerPositionAndLook, TimeUpdate

import select


class IdleHandler(PacketHandler):

    def handle_destroyed_entities(self, packet):
        destroy_entities = DestroyEntities().read(packet.packet_buffer)
        if SpawnEntity.id in self.connection.packet_log:
            for entity_id in destroy_entities.Entities:
                print("Removed entity ID: %s" % entity_id, self.connection.packet_log[SpawnEntity.id].keys(),
                      flush=True)
                if entity_id in self.connection.packet_log[SpawnEntity.id]:
                    del self.connection.packet_log[SpawnEntity.id][entity_id]  # Delete the entity

    def handle_player_list(self, packet):
        player_list_item = PlayerListItem().read(packet.packet_buffer)

        if packet.id not in self.connection.packet_log:
            self.connection.packet_log[packet.id] = {}

        add_player = 0
        remove_player = 4

        if player_list_item.Action == add_player or player_list_item.Action == remove_player:
            for player in player_list_item.Players:
                uuid = player[0]
                if player_list_item.Action == add_player:
                    if uuid not in self.connection.packet_log[packet.id]:
                        print("Added", player, flush=True)
                        self.connection.packet_log[packet.id][uuid] = packet
                elif player_list_item.Action == remove_player:
                    if uuid in self.connection.packet_log[packet.id]:
                        print("Removed", player, flush=True)
                        del self.connection.packet_log[packet.id][uuid]

    def handle_chunk_unloading(self, packet):
        unload_chunk = UnloadChunk().read(packet.packet_buffer)
        if ChunkData.id in self.connection.packet_log:
            chunk_key = (unload_chunk.ChunkX, unload_chunk.ChunkY)
            if chunk_key in self.connection.packet_log[ChunkData.id]:
                del self.connection.packet_log[ChunkData.id][chunk_key]
                print("UnloadChunk", unload_chunk.ChunkX, unload_chunk.ChunkY)

    def handle_chunk_loading(self, packet):
        chunk_data = ChunkData().read(packet.packet_buffer)
        if packet.id not in self.connection.packet_log:
            self.connection.packet_log[packet.id] = {}
        self.connection.packet_log[packet.id][(chunk_data.ChunkX, chunk_data.ChunkY)] = packet
        print("ChunkData", chunk_data.ChunkX, chunk_data.ChunkY)

    def handle_spawn_entity(self, packet):
        spawn_entity = SpawnEntity().read(packet.packet_buffer)
        if SpawnEntity.id not in self.connection.packet_log:
            self.connection.packet_log[SpawnEntity.id] = {}
        if spawn_entity.EntityID not in self.connection.packet_log[SpawnEntity.id]:
            self.connection.packet_log[SpawnEntity.id][spawn_entity.EntityID] = packet
        print("Added entity ID: %s" % spawn_entity.EntityID, self.connection.packet_log[SpawnEntity.id].keys(),
              flush=True)

    """ Idling occurs when we've disconnected our client or have yet to connect """
    def handle(self):
        timeout = 0.05 # Always 50ms
        while self.connection.running:
            try:
                ready_to_read = select.select([self.connection.stream], [], [], timeout)[0]

                if ready_to_read:
                    packet = self.read_packet()

                    if packet.id in self.connection.join_ids:
                        self.connection.packet_log[packet.id] = packet
                    elif packet.id == ChunkData.id: # ChunkData
                        self.handle_chunk_loading(packet)
                    elif packet.id == UnloadChunk.id: # UnloadChunk
                        self.handle_chunk_unloading(packet)
                    elif packet.id in SpawnEntity.ids:
                        self.handle_spawn_entity(packet)
                    elif packet.id == DestroyEntities.id:
                        self.handle_destroyed_entities(packet)
                    elif packet.id == KeepAlive.id and not self.connection.client_connection: # KeepAlive Clientbound
                        keep_alive = KeepAlive().read(packet.packet_buffer)
                        print("Responded to KeepAlive", keep_alive, flush=True)
                        self.connection.send_packet(KeepAliveServerbound(KeepAliveID=keep_alive.KeepAliveID))
                    elif packet.id == PlayerListItem.id: # PlayerListItem
                        self.handle_player_list(packet)
                    elif packet.id == ChatMessage.id:
                        chat_message = ChatMessage().read(packet.packet_buffer)
                        print(chat_message, flush=True)
                    elif packet.id == PlayerPositionAndLook.id:
                        pos_packet = PlayerPositionAndLook().read(packet.packet_buffer)

                        # Send back a teleport confirm
                        self.connection.send_packet(TeleportConfirm(TeleportID=pos_packet.TeleportID))

                        self.connection.packet_log[packet.id] = packet
                    elif packet.id == Disconnect.id:
                        print(Disconnect.read(packet.packet_buffer), flush=True)
                    elif packet.id == TimeUpdate.id:
                        self.connection.packet_log[packet.id] = packet

                    # Forward the packets if a client is connected
                    if self.connection.client_connection and self.connection.client_connection.connected:
                        try:
                            self.connection.client_connection.send_packet_buffer(packet.compressed_buffer)
                        except ConnectionAbortedError:
                            print("Something went wrong", flush=True)
                            pass
            except:
                print("Disconnected from server", flush=True)
                self.connection.running = False
                if self.connection.client_connection:
                    self.connection.client_connection.running = False