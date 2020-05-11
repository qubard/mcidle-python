import socket
import threading


class ListenThread(threading.Thread):
    def __init__(self, address):
        self.address = address
        threading.Thread.__init__(self, daemon=True)
        self.socket = socket.socket()
        self.server = None
        self.server_lock = threading.RLock()
        self.running = True

    def set_server(self, server):
        with self.server_lock:
            self.server = server
            return self

    def run(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.address)
        self.socket.listen(1)  # Listen for 1 incoming connection

        while self.running:
            try:
                (connection, address) = self.socket.accept()

                with self.server_lock:
                    if self.server:
                        print("Client connected", flush=True)
                        self.server.start_with_socket(connection)
            except OSError:
                print("Failed to bind socket (race condition?), it's already on", flush=True)
