SIZE = 15

EMPTY = 0
BLACK = 1
WHITE = 2


class Board:
    def __init__(self):
        self.reset()

    def reset(self):
        self.grid = [[EMPTY] * SIZE for _ in range(SIZE)]

    def get(self, x, y):
        return self.grid[y][x]

    def set(self, x, y, player):
        self.grid[y][x] = player

    def is_valid(self, x, y):
        return 0 <= x < SIZE and 0 <= y < SIZE and self.grid[y][x] == EMPTY

    def is_full(self):
        return all(self.grid[y][x] != EMPTY for y in range(SIZE) for x in range(SIZE))

    def to_list(self):
        return [row[:] for row in self.grid]
