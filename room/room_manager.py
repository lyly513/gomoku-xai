import random
import time
from game.game import Game


class Room:
    def __init__(self, room_id, player_black):
        self.room_id = room_id
        self.player_black = player_black
        self.player_white = None
        self.status = "waiting"
        self.game = Game()
        self.created_at = time.time()
        self.events = {"black": [], "white": []}


class RoomManager:
    def __init__(self):
        self.rooms = {}
        self.player_to_room = {}

    def generate_room_id(self):
        for _ in range(100):
            rid = str(random.randint(1000, 9999))
            if rid not in self.rooms:
                return rid
        return str(random.randint(1000, 9999))

    def create_room(self, player_id):
        rid = self.generate_room_id()
        self.rooms[rid] = Room(rid, player_id)
        self.player_to_room[player_id] = rid
        return rid

    def join_room(self, rid, player_id):
        room = self.rooms.get(rid)
        if not room:
            return None, "房间不存在"
        if room.status != "waiting":
            return None, "房间已满或游戏已开始"
        room.player_white = player_id
        room.status = "playing"
        self.player_to_room[player_id] = rid
        room.events["black"].append({"type": "opponent_joined"})
        return room, None

    def get_room_by_player(self, player_id):
        rid = self.player_to_room.get(player_id)
        if rid:
            return self.rooms.get(rid)
        return None

    def poll_events(self, room, color):
        evts = room.events[color]
        room.events[color] = []
        return evts

    def add_move_event(self, room, target_color, board, game_over, winner, current_player):
        room.events[target_color].append({
            "type": "opponent_moved",
            "board": board,
            "game_over": game_over,
            "winner": winner,
            "current_player": current_player,
        })

    def leave(self, player_id):
        rid = self.player_to_room.pop(player_id, None)
        if not rid:
            return None
        room = self.rooms.get(rid)
        if not room:
            return None

        if room.status == "waiting":
            del self.rooms[rid]
            self.player_to_room.pop(room.player_black, None)
            return None

        other_id = room.player_white if room.player_black == player_id else room.player_black
        other_color = "black" if room.player_black == other_id else "white"
        room.events[other_color].append({"type": "opponent_left"})
        del self.rooms[rid]
        self.player_to_room.pop(other_id, None)
        return other_id

    def cleanup_stale(self):
        now = time.time()
        stale = [rid for rid, room in self.rooms.items()
                 if room.status == "waiting" and now - room.created_at > 300]
        for rid in stale:
            room = self.rooms.pop(rid)
            self.player_to_room.pop(room.player_black, None)
