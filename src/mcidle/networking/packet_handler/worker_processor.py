import threading

from multiprocessing import Queue


# Starts a worker processor thread to process packets
# and optionally write any responses in a thread-safe manner
class WorkerProcessor(threading.Thread):
    def __init__(self, connection, packet_processor):
        threading.Thread.__init__(self, daemon=True)
        self.connection = connection
        self.packet_processor = packet_processor
        self.queue = Queue()
        self.running = True

    def enqueue(self, packet):
        self.queue.put(packet)

    def stop(self):
        self.running = False

    def run(self):
        while self.running:
            if not self.queue.empty():
                packet = self.queue.get()
                response = self.packet_processor.process_packet(packet)

                if response:
                    self.connection.send_packet(response)
