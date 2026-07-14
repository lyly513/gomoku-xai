import uuid
from flask import Flask, request, jsonify, send_from_directory
from game.game import Game, BLACK, WHITE
from room.room_manager import RoomManager

app = Flask(__name__, static_folder=".")
room_manager = RoomManager()

games = {}


def get_game():
    gid = request.cookies.get("game_id")
    if gid and gid in games:
        return games[gid], gid
    gid = uuid.uuid4().hex
    games[gid] = Game()
    return games[gid], gid


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/api/state", methods=["GET"])
def state():
    game, gid = get_game()
    resp = jsonify(game.get_state())
    resp.set_cookie("game_id", gid)
    return resp


@app.route("/api/new-game", methods=["POST"])
def new_game():
    game, gid = get_game()
    game.reset()
    return jsonify(game.get_state())


@app.route("/api/move", methods=["POST"])
def move():
    data = request.get_json()
    game, gid = get_game()
    result = game.human_move(data["x"], data["y"])
    resp = jsonify(result)
    resp.set_cookie("game_id", gid)
    return resp


@app.route("/api/undo", methods=["POST"])
def undo():
    game, gid = get_game()
    result = game.undo()
    resp = jsonify(result)
    resp.set_cookie("game_id", gid)
    return resp


@app.route("/api/pvp/create", methods=["POST"])
def pvp_create():
    player_id = uuid.uuid4().hex
    rid = room_manager.create_room(player_id)
    return jsonify({"ok": True, "player_id": player_id, "room_id": rid, "color": "black"})


@app.route("/api/pvp/join", methods=["POST"])
def pvp_join():
    data = request.get_json()
    rid = data.get("room_id", "").strip()
    if not rid or len(rid) != 4:
        return jsonify({"ok": False, "error": "房间号格式错误"})
    player_id = uuid.uuid4().hex
    room, error = room_manager.join_room(rid, player_id)
    if error:
        return jsonify({"ok": False, "error": error})
    return jsonify({
        "ok": True,
        "player_id": player_id,
        "color": "white",
        "board": room.game.board.to_list(),
        "current_player": "black",
        "game_over": False,
        "winner": None,
    })


@app.route("/api/pvp/state", methods=["GET"])
def pvp_state():
    player_id = request.args.get("player_id")
    if not player_id:
        return jsonify({"ok": False, "error": "参数缺失"})
    room = room_manager.get_room_by_player(player_id)
    if not room:
        return jsonify({"ok": False, "inactive": True, "error": "房间不存在或游戏已结束"})
    color = "black" if room.player_black == player_id else "white"
    events = room_manager.poll_events(room, color)
    return jsonify({
        "ok": True,
        "color": color,
        "board": room.game.board.to_list(),
        "current_player": "black" if room.game.current_player == BLACK else "white",
        "game_over": room.game.game_over,
        "winner": room.game.winner,
        "status": room.status,
        "events": events,
    })


@app.route("/api/pvp/move", methods=["POST"])
def pvp_move():
    data = request.get_json()
    player_id = data.get("player_id")
    room = room_manager.get_room_by_player(player_id)
    if not room:
        return jsonify({"ok": False, "error": "房间不存在"})

    player = BLACK if room.player_black == player_id else WHITE
    result = room.game.pvp_move(data["x"], data["y"], player)
    if not result["ok"]:
        return jsonify(result)

    target_color = "white" if player == BLACK else "black"
    room_manager.add_move_event(room, target_color,
                                result["board"], result["game_over"],
                                result["winner"], result["current_player"])
    return jsonify({"ok": True})


@app.route("/api/pvp/leave", methods=["GET", "POST"])
def pvp_leave():
    if request.method == "GET":
        player_id = request.args.get("player_id")
    else:
        data = request.get_json()
        player_id = data.get("player_id") if data else None
    if not player_id:
        return jsonify({"ok": False, "error": "参数缺失"})
    room_manager.leave(player_id)
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, port=5000, threaded=True)
