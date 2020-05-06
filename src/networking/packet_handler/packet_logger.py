from src.networking.packet_handler import WorkerLogger
from src.networking.packets.clientbound import ChunkData, UnloadChunk, PlayerListItem, SpawnEntity, GameState

from multiprocessing import Queue


class PacketLogger:

    def __init__(self, connection):
        self.connection = connection
        self.queue = Queue()
        self.log = {}

        # Initialize logging dicts (doing this in worker threads leads to race conditions)
        self.initialize_dicts()

    # TODO: Better way of doing this is having a separate class for storage
    # Also, shouldn't this be a linked list/queue? (yes)
    # I guess I wanted O(1) removal for deletion
    def initialize_dicts(self):
        self.log[ChunkData.id] = {}
        self.log[UnloadChunk.id] = {}
        self.log[PlayerListItem.id] = {}
        self.log[SpawnEntity.id] = {}
        self.log[GameState.id] = {}

    def start_worker_thread(self):
        WorkerLogger(self).start()
        print("Started thread", flush=True)

    def enqueue(self, packet):
        self.queue.put(packet)

