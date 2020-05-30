from mcidle.networking.packets.serverbound import KeepAlive as KeepAliveServerbound, TeleportConfirm, ClientStatus
from mcidle.networking.packets.clientbound import ChunkData, UnloadChunk, SpawnEntity, \
    DestroyEntities, KeepAlive, ChatMessage, PlayerPositionAndLook, TimeUpdate, \
    HeldItemChange, SetSlot, PlayerListItem, PlayerAbilities, Respawn, UpdateHealth, JoinGame

from mcidle.networking.packets.clientbound import GameState as GameStateP


class PacketProcessor:
    # A packet processor processes packets and mutates the game state
    def __init__(self, game_state):
        self.game_state = game_state

    # Processes a packet and returns a response packet if needed
    def process_packet(self, packet):
        return None


class ClientboundProcessor(PacketProcessor):
    def __init__(self, game_state):
        super().__init__(game_state)

    def destroy_entities(self, packet):
        destroy_entities = DestroyEntities().read(packet.packet_buffer)
        for entity_id in destroy_entities.Entities:
            if entity_id in self.game_state.entities:
                print("Removed entity ID: %s" % entity_id, flush=True)
                del self.game_state.entities[entity_id] # Delete the entity

    def player_list(self, packet):
        player_list_item = PlayerListItem().read(packet.packet_buffer)

        add_player = 0
        update_gamemode = 1
        remove_player = 4

        for player in player_list_item.Players:
            uuid = player[0]
            if uuid == self.game_state.client_uuid and player_list_item.Action == update_gamemode:
                self.game_state.gamemode = player[1]

            if player_list_item.Action == add_player:
                self.game_state.player_list[uuid] = packet
            elif player_list_item.Action == remove_player:
                if uuid in self.game_state.packet_log:
                    del self.game_state.player_list[uuid]

    def spawn_entity(self, packet):
        spawn_entity = SpawnEntity().read(packet.packet_buffer)
        if spawn_entity.EntityID not in self.game_state.entities:
            self.game_state.entities[spawn_entity.EntityID] = packet
            print("Added entity ID: %s" % spawn_entity.EntityID, flush=True)

    def chunk_unload(self, packet):
        unload_chunk = UnloadChunk().read(packet.packet_buffer)
        chunk_key = (unload_chunk.ChunkX, unload_chunk.ChunkZ)
        if chunk_key in self.game_state.chunks:
            del self.game_state.chunks[chunk_key]
            print("UnloadChunk", unload_chunk.ChunkX, unload_chunk.ChunkZ, flush=True)

    def chunk_load(self, packet):
        chunk_data = ChunkData().read(packet.packet_buffer)
        chunk_key = (chunk_data.ChunkX, chunk_data.ChunkZ)
        if chunk_key not in self.game_state.chunks:
            self.game_state.chunks[chunk_key] = packet
            print("ChunkData", chunk_data.ChunkX, chunk_data.ChunkZ, flush=True)

    def process_packet(self, packet):
        with self.game_state.state_lock:
            if packet.id == Respawn.id:
                # In case the gamemode is changed through a respawn packet
                respawn = Respawn().read(packet.packet_buffer)
                self.game_state.gamemode = respawn.Gamemode
                print("Set gamemode to", respawn.Gamemode, flush=True)
            if packet.id == JoinGame.id:
                join_game = JoinGame().read(packet.packet_buffer)
                self.game_state.gamemode = join_game.Gamemode & 3 # Bit 4 (0x8) is the hardcore flaga
                print("Set gamemode to", self.game_state.gamemode, "JoinGame", flush=True)

            if packet.id in self.game_state.join_ids:
                self.game_state.packet_log[packet.id] = packet
            elif packet.id == ChunkData.id:  # ChunkData
                self.chunk_load(packet)
            elif packet.id == UnloadChunk.id:  # UnloadChunk
                self.chunk_unload(packet)
            elif packet.id in SpawnEntity.ids:
                self.spawn_entity(packet)
            elif packet.id == DestroyEntities.id:
                self.destroy_entities(packet)
            elif packet.id == KeepAlive.id:  # KeepAlive Clientbound
                keep_alive = KeepAlive().read(packet.packet_buffer)
                print("Responded to KeepAlive", keep_alive, flush=True)
                return KeepAliveServerbound(KeepAliveID=keep_alive.KeepAliveID)
            elif packet.id == ChatMessage.id:
                chat_message = ChatMessage().read(packet.packet_buffer)
                print(chat_message, flush=True)
            elif packet.id == PlayerPositionAndLook.id:
                pos_packet = PlayerPositionAndLook().read(packet.packet_buffer)

                # Log the packet
                self.game_state.packet_log[packet.id] = packet
                self.game_state.received_position = True

                self.game_state.player_pos = (pos_packet.X, pos_packet.Y, pos_packet.Z)

                # Send back a teleport confirm
                return TeleportConfirm(TeleportID=pos_packet.TeleportID)
            elif packet.id == TimeUpdate.id:
                self.game_state.packet_log[packet.id] = packet
            elif packet.id == HeldItemChange.id:
                self.game_state.held_item_slot = HeldItemChange().read(packet.packet_buffer).Slot
            elif packet.id == GameStateP.id:
                game_state = GameStateP().read(packet.packet_buffer)
                if game_state.Reason == 3: # Change Gamemode
                    print("Set gamemode to ", game_state.Value, flush=True)
                    self.game_state.gamemode = game_state.Value
            elif packet.id == SetSlot.id:
                set_slot = SetSlot().read(packet.packet_buffer)
                self.game_state.main_inventory[set_slot.Slot] = packet
            elif packet.id == PlayerListItem.id:
                self.player_list(packet)
            elif packet.id == PlayerAbilities.id:
                self.game_state.abilities = PlayerAbilities().read(packet.packet_buffer)
            elif packet.id == UpdateHealth.id:
                update_health = UpdateHealth().read(packet.packet_buffer)
                self.game_state.update_health = update_health
                # Respawn the player if they're dead..
                print("Health: %s" % update_health.Health, flush=True)
                if update_health.Health == 0:
                    print("Client died, respawning", flush=True)
                    return ClientStatus(ActionID=0)


        return None
