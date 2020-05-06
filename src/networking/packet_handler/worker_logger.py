from src.networking.packets.serverbound import KeepAlive as KeepAliveServerbound, TeleportConfirm
from src.networking.packets.clientbound import ChunkData, UnloadChunk, SpawnEntity, \
    DestroyEntities, KeepAlive, ChatMessage, PlayerPositionAndLook, TimeUpdate, \
    HeldItemChange, GameState, SetSlot

import threading


class WorkerLogger(threading.Thread):
    def __init__(self, parent):
        threading.Thread.__init__(self)
        self.parent = parent

    def destroy_entities(self, packet):
        destroy_entities = DestroyEntities().read(packet.packet_buffer)
        for entity_id in destroy_entities.Entities:
            if entity_id in self.parent.log[SpawnEntity.id]:
                print("Removed entity ID: %s" % entity_id, self.parent.log[SpawnEntity.id].keys(),
                      flush=True)
                del self.parent.log[SpawnEntity.id][entity_id]  # Delete the entity

    def chunk_unload(self, packet):
        unload_chunk = UnloadChunk().read(packet.packet_buffer)
        chunk_key = (unload_chunk.ChunkX, unload_chunk.ChunkY)
        if chunk_key in self.parent.log[ChunkData.id]:
            del self.parent.log[ChunkData.id][chunk_key]
            print("UnloadChunk", unload_chunk.ChunkX, unload_chunk.ChunkY, flush=True)

    def chunk_load(self, packet):
        chunk_data = ChunkData().read(packet.packet_buffer)
        chunk_key = (chunk_data.ChunkX, chunk_data.ChunkY)
        if chunk_key not in self.parent.log[packet.id]:
            self.parent.log[packet.id][chunk_key] = packet
            print("ChunkData", chunk_data.ChunkX, chunk_data.ChunkY, flush=True)

    def spawn_entity(self, packet):
        spawn_entity = SpawnEntity().read(packet.packet_buffer)
        if spawn_entity.EntityID not in self.parent.log[SpawnEntity.id]:
            self.parent.log[SpawnEntity.id][spawn_entity.EntityID] = packet
            print("Added entity ID: %s" % spawn_entity.EntityID, self.parent.log[SpawnEntity.id].keys(),
              flush=True)

    def process_packet(self, packet):
        if packet.id in self.parent.connection.join_ids:
            self.parent.log[packet.id] = packet
        elif packet.id == ChunkData.id:  # ChunkData
            self.chunk_load(packet)
        elif packet.id == UnloadChunk.id:  # UnloadChunk
            self.chunk_unload(packet)
        elif packet.id in SpawnEntity.ids:
            self.spawn_entity(packet)
        elif packet.id == DestroyEntities.id:
            self.destroy_entities(packet)
        elif packet.id == KeepAlive.id and not self.parent.connection.client_connection: # KeepAlive Clientbound
            keep_alive = KeepAlive().read(packet.packet_buffer)
            print("Responded to KeepAlive", keep_alive, flush=True)
            self.parent.connection.send_packet(KeepAliveServerbound(KeepAliveID=keep_alive.KeepAliveID))
        elif packet.id == ChatMessage.id:
            chat_message = ChatMessage().read(packet.packet_buffer)
            print(chat_message, flush=True)
        elif packet.id == PlayerPositionAndLook.id:
            pos_packet = PlayerPositionAndLook().read(packet.packet_buffer)

            # Send back a teleport confirm
            self.parent.connection.send_packet(TeleportConfirm(TeleportID=pos_packet.TeleportID))

            # Log the packet
            self.parent.log[packet.id] = packet
        elif packet.id == TimeUpdate.id:
            self.parent.log[packet.id] = packet
        elif packet.id == HeldItemChange.id:
            self.parent.connection.held_item_slot = HeldItemChange().read(packet.packet_buffer).Slot
        elif packet.id == GameState.id:
            gamestate = GameState().read(packet.packet_buffer)
            self.parent.connection.gs_reason = gamestate.Reason
            self.parent.connection.gs_value = gamestate.Value
        elif packet.id == SetSlot.id:
            setslot = SetSlot().read(packet.packet_buffer)
            self.parent.connection.main_inventory[setslot.Slot] = packet

    def run(self):
        while True:
            if not self.parent.queue.empty():
                packet = self.parent.queue.get()
                self.process_packet(packet)
