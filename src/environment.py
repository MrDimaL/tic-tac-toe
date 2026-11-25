"""Rules shared by the GUI, training and evaluation. No GUI imports."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

LINES = ((0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6),
         (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6))


def _symmetries():
    maps = []
    for mirror in (False, True):
        for rotations in range(4):
            result = []
            for cell in range(9):
                r, c = divmod(cell, 3)
                if mirror:
                    c = 2 - c
                for _ in range(rotations):
                    r, c = c, 2 - r
                result.append(r * 3 + c)
            maps.append(tuple(result))
    return tuple(maps)


SYMMETRIES = _symmetries()


@lru_cache(maxsize=65536)
def canonical(raw: str, variant: str):
    """Return a D4-canonical state and the physical -> canonical action map."""
    candidates = []
    for mapping in SYMMETRIES:
        if variant == "classic":
            cells = ["0"] * 9
            for i, value in enumerate(raw):
                cells[mapping[i]] = value
            key = "".join(cells)
        else:
            own, other = raw.split("|")
            key = "".join(str(mapping[int(c)]) for c in own) + "|"
            key += "".join(str(mapping[int(c)]) for c in other)
        candidates.append((key, mapping))
    return min(candidates, key=lambda item: item[0])


@dataclass(frozen=True)
class Transition:
    reward: float
    terminated: bool
    truncated: bool
    winner: int
    removed: int | None


class TicTacToeEnv:
    """X=1, O=-1. Infinite places on an empty cell, then removes the oldest.

    A win is checked AFTER removal. The old cell is occupied while selecting
    the move. At the time limit the GUI declares a draw, but RL bootstraps:
    this is truncation of a continuing game, not an absorbing terminal state.
    """
    def __init__(self, variant="classic", max_plies=120):
        if variant not in ("classic", "infinite"):
            raise ValueError("Unknown rule set")
        if type(max_plies) is not int or max_plies < 9:
            raise ValueError("max_plies must be an integer >= 9")
        self.variant = variant
        self.max_plies = max_plies
        self.reset()

    def reset(self):
        self.board = [0] * 9
        self.queues = {1: [], -1: []}
        self.turn = 1
        self.plies = 0
        self.winner = 0
        self.terminated = False
        self.truncated = False
        self.winning_line = ()
        self.last_action = None
        return self.state()

    @property
    def done(self):
        return self.terminated or self.truncated

    def legal_actions(self):
        return [] if self.done else self.empty_cells()

    def empty_cells(self):
        return [i for i, value in enumerate(self.board) if value == 0]

    def state(self):
        """Player-relative state; FIFO order is essential in Infinite mode."""
        if self.variant == "classic":
            raw = "".join("0" if v == 0 else "1" if v == self.turn else "2"
                          for v in self.board)
        else:
            raw = "".join(map(str, self.queues[self.turn])) + "|"
            raw += "".join(map(str, self.queues[-self.turn]))
        return canonical(raw, self.variant)

    def step(self, action):
        if self.done:
            raise ValueError("The game has ended")
        if type(action) is not int or action not in range(9) or self.board[action]:
            raise ValueError("Choose an empty cell in 0..8")
        player = self.turn
        removed = None
        self.board[action] = player
        self.queues[player].append(action)
        if self.variant == "infinite" and len(self.queues[player]) > 3:
            removed = self.queues[player].pop(0)
            self.board[removed] = 0
        self.plies += 1
        self.last_action = action
        for line in LINES:
            if all(self.board[i] == player for i in line):
                self.terminated = True
                self.winner = player
                self.winning_line = line
                break
        if not self.terminated and not self.empty_cells():
            self.terminated = True
        if not self.terminated and self.plies >= self.max_plies:
            self.truncated = True
        self.turn = -player
        return Transition(1.0 if self.winner else 0.0, self.terminated,
                          self.truncated, self.winner, removed)
