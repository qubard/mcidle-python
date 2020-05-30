import threading

from multiprocessing import Queue


class UpstreamThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self, daemon=True)
        self.queue = Queue()
        self.socket = None
        self.socket_lock = threading.RLock()
        self.running = True

    def set_socket(self, socket):
        self.clear()
        with self.socket_lock:
            self.socket = socket

    def connected(self):
        with self.socket_lock:
            return self.socket is not None

    def put(self, b):
        self.queue.put(b)

    def clear(self):
        while not self.queue.empty():
            self.queue.get()

    def stop(self):
        self.set_socket(None)
        self.running = False

    def run(self):
        while self.running:
            if not self.queue.empty():
                # Acquire the lock since socket can be None when set in another thread
                with self.socket_lock:
                    if self.socket:
                        while not self.queue.empty():
                            pkt = self.queue.get()
                            try:
                                self.socket.send(pkt)
                            except Exception as _:
                                pass # Keep on throwing exceptions until we get a new socket
