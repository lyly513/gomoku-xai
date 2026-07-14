import random
from .board import SIZE, EMPTY, BLACK, WHITE

DIRECTIONS = [(1, 0), (0, 1), (1, 1), (1, -1)]


def _score_position(x, y, player, board):
    total = 0
    for dx, dy in DIRECTIONS:
        count = 1
        open_ends = 0

        cx, cy = x + dx, y + dy
        while 0 <= cx < SIZE and 0 <= cy < SIZE and board.get(cx, cy) == player:
            count += 1
            cx += dx
            cy += dy
        if 0 <= cx < SIZE and 0 <= cy < SIZE and board.get(cx, cy) == EMPTY:
            open_ends += 1

        cx, cy = x - dx, y - dy
        while 0 <= cx < SIZE and 0 <= cy < SIZE and board.get(cx, cy) == player:
            count += 1
            cx -= dx
            cy -= dy
        if 0 <= cx < SIZE and 0 <= cy < SIZE and board.get(cx, cy) == EMPTY:
            open_ends += 1

        if count >= 5:
            total += 100000
        elif count == 4:
            if open_ends == 2:
                total += 50000
            elif open_ends == 1:
                total += 5000
        elif count == 3:
            if open_ends == 2:
                total += 5000
            elif open_ends == 1:
                total += 500
        elif count == 2:
            if open_ends == 2:
                total += 500
            elif open_ends == 1:
                total += 50
    return total


def evaluate_position(x, y, board):
    ai_score = _score_position(x, y, WHITE, board)
    human_score = _score_position(x, y, BLACK, board)
    if ai_score >= 100000:
        return ai_score * 10
    return ai_score + human_score * 1.1


def ai_move(board):
    best_score = -1
    best_moves = []

    for y in range(SIZE):
        for x in range(SIZE):
            if board.get(x, y) != EMPTY:
                continue
            score = evaluate_position(x, y, board)
            if score > best_score:
                best_score = score
                best_moves = [(x, y)]
            elif score == best_score:
                best_moves.append((x, y))

    if not best_moves:
        return None
    return random.choice(best_moves)
