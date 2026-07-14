import uuid
from flask import Flask, request, jsonify, send_from_directory
from game.game import Game

app = Flask(__name__, static_folder=".")

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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
