"""Negamax Q-learning. JSON checkpoints contain data, never executable pickle."""
from __future__ import annotations

import gzip
import json
import math
import os
from pathlib import Path
import random
import tempfile

FORMAT = "tic-tac-toe-q-v1"


def atomic_json(path, data, compressed=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    os.close(fd)
    try:
        opener = gzip.open if compressed else open
        with opener(name, "wt", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":"))
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _tuples(value):
    return tuple(_tuples(x) for x in value) if isinstance(value, list) else value


class QAgent:
    def __init__(self, variant="classic", seed=42):
        if variant not in ("classic", "infinite"):
            raise ValueError("Unknown variant")
        self.variant = variant
        self.seed = seed
        self.rng = random.Random(seed)
        self.q = {}
        self.episodes = 0
        self.steps = 0
        self.alpha = 0.25
        self.gamma = 0.97
        self.eps_start = 0.9
        self.eps_end = 0.05
        self.eps_decay = 40000 if variant == "classic" else 100000
        self.history = []
        self.outcomes = {"x": 0, "o": 0, "draw": 0}
        self.elapsed = 0.0

    @property
    def epsilon(self):
        fraction = min(1, self.episodes / self.eps_decay)
        return self.eps_start + fraction * (self.eps_end - self.eps_start)

    def values(self, env):
        if env.variant != self.variant:
            raise ValueError("Model and game rule sets differ")
        key, mapping = env.state()
        row = self.q.get(key, [0.0] * 9)
        return {a: row[mapping[a]] for a in env.empty_cells()}

    def choose(self, env, epsilon=0.0, rng=None):
        rng = rng or self.rng
        actions = env.legal_actions()
        if not actions:
            raise ValueError("No legal action")
        if rng.random() < epsilon:
            return rng.choice(actions)
        values = self.values(env)
        best = max(values[a] for a in actions)
        return rng.choice([a for a in actions if abs(values[a] - best) < 1e-12])

    def update(self, state, action, transition, next_env):
        key, mapping = state
        row = self.q.setdefault(key, [0.0] * 9)
        # Next player maximizes THEIR value, so our continuation is its negative.
        target = transition.reward
        if not transition.terminated:
            target -= self.gamma * max(self.values(next_env).values(), default=0.0)
        delta = target - row[mapping[action]]
        row[mapping[action]] += self.alpha * delta
        self.steps += 1
        return delta * delta

    def save(self, path):
        atomic_json(path, {
            "format": FORMAT, "variant": self.variant, "seed": self.seed,
            "q": self.q, "episodes": self.episodes, "steps": self.steps,
            "alpha": self.alpha, "gamma": self.gamma,
            "eps_start": self.eps_start, "eps_end": self.eps_end,
            "eps_decay": self.eps_decay, "history": self.history,
            "outcomes": self.outcomes, "elapsed": self.elapsed,
            "rng": self.rng.getstate(),
        }, compressed=True)

    @classmethod
    def load(cls, path, expected_variant=None):
        # Refuse unexpectedly large decompressed input before JSON parsing.
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            raw = stream.read(80_000_001)
        if len(raw) > 80_000_000:
            raise ValueError("Checkpoint is too large")
        data = json.loads(raw)
        if data.get("format") != FORMAT:
            raise ValueError("Unsupported checkpoint format")
        obj = cls(data["variant"], data["seed"])
        if expected_variant and obj.variant != expected_variant:
            raise ValueError("Model and selected rule sets differ")
        q = data["q"]
        if not isinstance(q, dict):
            raise ValueError("Invalid Q table")
        for key, row in q.items():
            if obj.variant == "classic":
                valid = len(key) == 9 and set(key) <= set("012")
            else:
                parts = key.split("|")
                valid = (len(parts) == 2 and all(len(p) <= 3 for p in parts)
                         and set("".join(parts)) <= set("012345678")
                         and len(set("".join(parts))) == len("".join(parts)))
            if not valid or not isinstance(row, list) or len(row) != 9:
                raise ValueError("Invalid Q state")
            if not all(type(v) in (float, int) and math.isfinite(v) and abs(v) <= 2
                       for v in row):
                raise ValueError("Invalid Q value")
        obj.q = q
        for attr in ("episodes", "steps", "eps_decay"):
            value = data[attr]
            if type(value) is not int or value < (1 if attr == "eps_decay" else 0):
                raise ValueError("Invalid model counter")
            setattr(obj, attr, value)
        for attr in ("alpha", "gamma", "eps_start", "eps_end"):
            value = data[attr]
            if type(value) not in (int, float) or not 0 < value <= 1:
                raise ValueError("Invalid learning parameter")
            setattr(obj, attr, value)
        obj.history = data["history"]
        obj.outcomes = data["outcomes"]
        obj.elapsed = float(data["elapsed"])
        if not math.isfinite(obj.elapsed) or obj.elapsed < 0:
            raise ValueError("Invalid elapsed time")
        if (not isinstance(obj.history, list) or
                set(obj.outcomes) != {"x", "o", "draw"} or
                any(type(v) is not int or v < 0 for v in obj.outcomes.values()) or
                sum(obj.outcomes.values()) != obj.episodes):
            raise ValueError("Invalid training statistics")
        required = {"episode", "td_mse", "epsilon", "length", "win_rate",
                    "draw_rate", "loss_rate", "elapsed_s", "states"}
        for row in obj.history:
            if (not isinstance(row, dict) or set(row) != required or
                    any(type(v) not in (int, float) or not math.isfinite(v)
                        for v in row.values())):
                raise ValueError("Invalid training history")
        obj.rng.setstate(_tuples(data["rng"]))
        return obj
