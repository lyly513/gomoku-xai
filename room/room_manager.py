import random
import time
from game.game import Game


class Room:
    def __init__(self, room_id, player_black_sid):
        self.room_id = room_id
        self.player_black = player_black_sid
        self.player_white = None
        self.status = "waiting"
        self.game = Game()
        self.created_at = time.time()


class RoomManager:
    def __init__(self):
        self.rooms = {}
        self.sid_to_room = {}

    def generate_room_id(self):
        for _ in range(100):
            rid = str(random.randint(1000, 9999))
            if rid not in self.rooms:
                return rid
        return str(random.randint(1000, 9999))

    def create_room(self, sid):
        rid = self.generate_room_id()
        self.rooms[rid] = Room(rid, sid)
        self.sid_to_room[sid] = rid
        return rid

    def join_room(self, rid, sid):
        room = self.rooms.get(rid)
        if not room:
            return None, "房间不存在"
        if room.status != "waiting":
            return None, "房间已满或游戏已开始"
        room.player_white = sid
        room.status = "playing"
        self.sid_to_room[sid] = rid
        return room, None

    def get_room_by_sid(self, sid):
        rid = self.sid_to_room.get(sid)
        if rid:
            return self.rooms.get(rid)
        return None

    def leave_room(self, sid):
        rid = self.sid_to_room.pop(sid, None)
        if not rid:
            return None
        room = self.rooms.get(rid)
        if not room:
            return None

        if room.status == "waiting":
            del self.rooms[rid]
            return None

        room.status = "finished"
        other_sid = room.player_black if room.player_white == sid else room.player_white
        del self.rooms[rid]
        return other_sid

    def cleanup_stale(self):
        now = time.time()
        stale = [rid for rid, room in self.rooms.items()
                 if room.status == "waiting" and now - room.created_at > 300]
        for rid in stale:
            room = self.rooms.pop(rid)
            self.sid_to_room.pop(room.player_black, None)
