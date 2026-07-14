import uuid
from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit, join_room
from game.game import Game, BLACK
from room.room_manager import RoomManager

app = Flask(__name__, static_folder=".")
socketio = SocketIO(app, cors_allowed_origins="*")
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
    x, y = data["x"], data["y"]
    game, gid = get_game()
    result = game.human_move(x, y)
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


@socketio.on("connect")
def handle_connect():
    pass


@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid
    other_sid = room_manager.leave_room(sid)
    if other_sid:
        emit("room:opponent_left", to=other_sid)


@socketio.on("room:create")
def handle_create():
    sid = request.sid
    rid = room_manager.create_room(sid)
    emit("room:created", {"room_id": rid})


@socketio.on("room:join")
def handle_join(data):
    sid = request.sid
    rid = data.get("room_id", "").strip()
    if not rid:
        emit("game:error", {"message": "请输入房间号"})
        return
    room, error = room_manager.join_room(rid, sid)
    if error:
        emit("game:error", {"message": error})
        return

    join_room(rid, sid=room.player_black)
    join_room(rid, sid=room.player_white)

    board = room.game.board.to_list()
    emit("game:start", {
        "board": board,
        "color": "black",
        "current_player": "black"
    }, to=room.player_black)
    emit("game:start", {
        "board": board,
        "color": "white",
        "current_player": "black"
    }, to=room.player_white)


@socketio.on("game:move")
def handle_move(data):
    sid = request.sid
    room = room_manager.get_room_by_sid(sid)
    if not room:
        emit("game:error", {"message": "不在游戏中"})
        return

    from game.board import WHITE
    player = BLACK if sid == room.player_black else WHITE
    result = room.game.pvp_move(data["x"], data["y"], player)

    if not result["ok"]:
        emit("game:error", {"message": result["error"]})
        return

    rid = room.room_id
    emit("game:moved", {
        "x": data["x"],
        "y": data["y"],
        "stone": "black" if player == BLACK else "white",
        "board": result["board"],
        "game_over": result["game_over"],
        "winner": result["winner"],
        "current_player": result["current_player"],
        "message": result["message"],
    }, room=rid)


if __name__ == "__main__":
    socketio.run(app, debug=True, port=5000)
