from src.networking.packet_handler import WorkerLogger

from multiprocessing import Queue


class PacketLogger:

    def __init__(self, connection):
        self.connection = connection
        self.queue = Queue()

    def start_worker_thread(self):
        WorkerLogger(self).start()
        print("Started thread", flush=True)

    def enqueue(self, packet):
        self.queue.put(packet)

