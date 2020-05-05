from src.networking.packet_handler import WorkerLogger
from src.networking.packets.clientbound import ChunkData, UnloadChunk, PlayerListItem, SpawnEntity

from multiprocessing import Manager, Queue


class PacketLogger:

    def __init__(self, connection, thread_count=32):
        self.connection = connection
        self.manager = Manager()
        self.queue = Queue()
        self.log = self.manager.dict()
        self.thread_count = thread_count

        # Initialize logging dicts (doing this in worker threads leads to race conditions)
        self.initialize_dicts()

    # TODO: Better way of doing this is having a separate class for storage
    # Also, shouldn't this be a linked list/queue? (yes)
    # I guess I wanted O(1) removal for deletion
    def initialize_dicts(self):
        self.log[ChunkData.id] = self.manager.dict()
        self.log[UnloadChunk.id] = self.manager.dict()
        self.log[PlayerListItem.id] = self.manager.dict()
        self.log[SpawnEntity.id] = self.manager.dict()

    def start_worker_threads(self):
        for _ in range(0, self.thread_count):
            WorkerLogger(self).start()
            print("Started thread", flush=True)

    def enqueue(self, packet):
        self.queue.put(packet)

