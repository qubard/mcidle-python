from threading import RLock


class GameState:
    def __init__(self, join_ids=[]):
        self.held_item_slot = 0
        self.last_pos_packet = None
        self.last_yaw = 0
        self.last_pitch = 0
        self.teleport_id = 0

        self.gamemode = None

        self.client_uuid = None
        self.client_username = None

        self.abilities = None

        self.player_pos = None

        self.state_lock = RLock()

        self.received_position = False
        self.update_health = None

        # Every other packet goes here
        self.packet_log = {}

        self.main_inventory = {}
        self.chunks = {}
        self.player_list = {}
        self.entities = {}

        self.join_ids = join_ids

    def acquire(self):
        self.state_lock.acquire()

    def release(self):
        self.state_lock.release()
