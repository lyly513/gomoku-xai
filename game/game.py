from .board import Board, EMPTY, BLACK, WHITE, SIZE
from .ai import ai_move

DIRECTIONS = [(1, 0), (0, 1), (1, 1), (1, -1)]


class Game:
    def __init__(self):
        self.board = Board()
        self.current_player = BLACK
        self.history = []
        self.game_over = False
        self.winner = None

    def reset(self):
        self.board.reset()
        self.current_player = BLACK
        self.history = []
        self.game_over = False
        self.winner = None

    def _check_win(self, x, y, player):
        for dx, dy in DIRECTIONS:
            count = 1
            for d in (1, -1):
                cx, cy = x + dx * d, y + dy * d
                while 0 <= cx < SIZE and 0 <= cy < SIZE and self.board.get(cx, cy) == player:
                    count += 1
                    cx += dx * d
                    cy += dy * d
            if count >= 5:
                return True
        return False

    def human_move(self, x, y):
        if self.game_over or self.current_player != BLACK:
            return {"ok": False, "error": "当前不是你的回合"}
        if not self.board.is_valid(x, y):
            return {"ok": False, "error": "该位置无效或已有棋子"}

        self.board.set(x, y, BLACK)
        self.history.append({"x": x, "y": y, "stone": "black"})

        if self._check_win(x, y, BLACK):
            self.game_over = True
            self.winner = "black"
            return self._state("黑棋（你）获胜！")

        if self.board.is_full():
            self.game_over = True
            return self._state("平局！")

        self.current_player = WHITE

        move = ai_move(self.board)
        if move is None:
            self.game_over = True
            return self._state("平局！")

        ax, ay = move
        self.board.set(ax, ay, WHITE)
        self.history.append({"x": ax, "y": ay, "stone": "white"})

        if self._check_win(ax, ay, WHITE):
            self.game_over = True
            self.winner = "white"
            return self._state("白棋（AI）获胜！")

        if self.board.is_full():
            self.game_over = True
            return self._state("平局！")

        self.current_player = BLACK
        return self._state("")

    def undo(self):
        if self.game_over or not self.history:
            return {"ok": False, "error": "没有可以悔棋的步骤"}

        moves_to_undo = min(2, len(self.history))
        for _ in range(moves_to_undo):
            m = self.history.pop()
            self.board.set(m["x"], m["y"], EMPTY)

        self.current_player = BLACK
        return self._state("")

    def _state(self, message):
        return {
            "ok": True,
            "message": message,
            "board": self.board.to_list(),
            "current_player": "black" if self.current_player == BLACK else "white",
            "game_over": self.game_over,
            "winner": self.winner,
            "move_count": len(self.history),
        }

    def get_state(self):
        return self._state("")
