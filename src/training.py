"""Self-play training, independent random-opponent evaluation and CSV export."""
from __future__ import annotations

import csv
from pathlib import Path
import random
import time

from .environment import TicTacToeEnv

FIELDS = ("episode", "td_mse", "epsilon", "length", "win_rate", "draw_rate",
          "loss_rate", "elapsed_s", "states")


def evaluate(agent, games=200, seed=1042):
    if type(games) is not int or games < 1:
        raise ValueError("games must be positive")
    rng = random.Random(seed)
    wins = draws = losses = truncated = 0
    for i in range(games):
        env = TicTacToeEnv(agent.variant)
        side = 1 if i % 2 == 0 else -1
        while not env.done:
            action = (agent.choose(env, rng=rng) if env.turn == side
                      else rng.choice(env.legal_actions()))
            env.step(action)
        if env.winner == side:
            wins += 1
        elif env.winner == -side:
            losses += 1
        else:
            draws += 1
        truncated += int(env.truncated)
    return {"games": games, "wins": wins, "draws": draws, "losses": losses,
            "truncated": truncated, "win_rate": wins / games,
            "draw_rate": draws / games, "loss_rate": losses / games,
            "score_rate": (wins + draws * 0.5) / games, "seed": seed}


def export_csv(agent, path):
    with open(path, "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(agent.history)


def train(agent, episodes=10000, checkpoint=None, callback=None, stop=None,
          pause=None, log_every=500, eval_games=200):
    """Train ADDITIONAL episodes. Checkpoints are committed at episode boundaries.

    Stop saves completed episodes. RNG and epsilon progress survive resuming.
    Evaluation uses its own RNG, so logging frequency cannot change training.
    """
    if type(episodes) is not int or episodes < 1 or log_every < 1:
        raise ValueError("episodes and log_every must be positive")
    target = agent.episodes + episodes
    start = time.monotonic()
    elapsed_base = agent.elapsed
    paused_seconds = 0.0
    errors, lengths = [], []
    try:
        while agent.episodes < target:
            if stop and stop.is_set():
                break
            if pause and pause.is_set():
                before = time.monotonic()
                while pause.is_set() and not (stop and stop.is_set()):
                    time.sleep(0.05)
                paused_seconds += time.monotonic() - before
                continue
            env = TicTacToeEnv(agent.variant)
            epsilon = agent.epsilon
            while not env.done:
                state = env.state()
                action = agent.choose(env, epsilon)
                transition = env.step(action)
                errors.append(agent.update(state, action, transition, env))
            agent.episodes += 1
            agent.outcomes["x" if env.winner == 1 else "o" if env.winner == -1
                           else "draw"] += 1
            lengths.append(env.plies)
            if agent.episodes % log_every == 0 or agent.episodes == target:
                assessment = evaluate(agent, games=eval_games)
                agent.elapsed = elapsed_base + time.monotonic() - start - paused_seconds
                row = dict(episode=agent.episodes,
                           td_mse=sum(errors) / len(errors), epsilon=agent.epsilon,
                           length=sum(lengths) / len(lengths),
                           win_rate=assessment["win_rate"],
                           draw_rate=assessment["draw_rate"],
                           loss_rate=assessment["loss_rate"],
                           elapsed_s=agent.elapsed, states=len(agent.q))
                agent.history.append(row)
                errors.clear()
                lengths.clear()
                if checkpoint:
                    agent.save(checkpoint)
                if callback:
                    callback(dict(row))
    finally:
        agent.elapsed = elapsed_base + time.monotonic() - start - paused_seconds
        if checkpoint:
            agent.save(checkpoint)
            export_csv(agent, Path(checkpoint).with_suffix(".csv"))
    return agent
