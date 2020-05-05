import threading

from multiprocessing import Queue


class UpstreamThread(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.queue = Queue()
        self.socket = None
        self.lock = threading.Lock()
        self.running = False

    def set_socket(self, socket):
        with self.lock:
            self.socket = socket

    def put(self, b):
        self.queue.put(b)

    def start(self):
        self.running = True
        super().start()

    def started(self):
        return self.running

    def stop(self):
        self.running = False

    def run(self):
        while self.running:
            if not self.queue.empty():
                with self.lock:
                    if self.socket:
                        while not self.queue.empty():
                            pkt = self.queue.get()
                            try:
                                self.socket.send(pkt)
                            except Exception as _:
                                pass # Keep on throwing exceptions until we get a new socket
