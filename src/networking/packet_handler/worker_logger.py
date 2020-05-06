import threading


class WorkerLogger(threading.Thread):
    def __init__(self, parent):
        threading.Thread.__init__(self)
        self.parent = parent

    def run(self):
        while True:
            if not self.parent.queue.empty():
                packet = self.parent.queue.get()
                response = self.parent.connection.packet_processor.process_packet(packet)

                if response:
                    self.parent.connection.send_packet(response)
