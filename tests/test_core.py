import copy
import gzip
import json
from pathlib import Path
import random
import tempfile
import threading
import unittest

from localization import Translator
from src.agent import QAgent
from src.environment import LINES, SYMMETRIES, TicTacToeEnv, Transition
from src.training import evaluate, train, export_csv


class RulesTests(unittest.TestCase):
    def test_every_winning_line_for_both_players(self):
        for variant in ("classic", "infinite"):
            for side in (1, -1):
                for line in LINES:
                    e = TicTacToeEnv(variant)
                    e.turn = side
                    e.board[line[0]] = e.board[line[1]] = side
                    e.queues[side] = list(line[:2])
                    result = e.step(line[2])
                    self.assertEqual(result.reward, 1)
                    self.assertEqual(e.winner, side)
                    self.assertEqual(e.winning_line, line)

    def test_classic_draw_and_no_move_after_done(self):
        e = TicTacToeEnv()
        for a in (0, 1, 2, 4, 3, 5, 7, 6, 8):
            e.step(a)
        self.assertTrue(e.terminated)
        self.assertEqual(e.winner, 0)
        self.assertEqual(e.legal_actions(), [])
        with self.assertRaises(ValueError):
            e.step(0)

    def test_illegal_moves_are_atomic(self):
        e = TicTacToeEnv()
        e.step(4)
        snapshot = copy.deepcopy(e.__dict__)
        for action in (4, -1, 9, True, "3", None, 1.5):
            with self.assertRaises(ValueError):
                e.step(action)
            self.assertEqual(e.__dict__, snapshot)

    def test_infinite_removes_oldest_then_checks_win(self):
        e = TicTacToeEnv("infinite")
        for a in (0, 3, 1, 4, 6, 8):
            e.step(a)
        with self.assertRaises(ValueError):
            e.step(0)
        r = e.step(2)  # 0,1,2 would win BEFORE removing 0, but must not win.
        self.assertEqual(r.removed, 0)
        self.assertEqual(e.board[0], 0)
        self.assertFalse(e.done)
        self.assertEqual(e.queues[1], [1, 6, 2])
        self.assertEqual(len(e.queues[-1]), 3)

    def test_infinite_can_win_with_fourth_placement(self):
        e = TicTacToeEnv("infinite")
        for a in (0, 1, 2, 3, 4, 5, 6):
            e.step(a)
        self.assertEqual(e.winner, 1)
        self.assertEqual(e.board[0], 0)
        self.assertEqual(e.queues[1], [2, 4, 6])

    def test_infinite_cap_and_fifo_invariants(self):
        e = TicTacToeEnv("infinite")
        rng = random.Random(51)
        while not e.done:
            candidates = []
            for a in e.legal_actions():
                child = copy.deepcopy(e)
                child.step(a)
                if not child.terminated:
                    candidates.append(a)
            self.assertTrue(candidates)
            e.step(rng.choice(candidates))
            self.assertLessEqual(len(e.queues[1]), 3)
            self.assertLessEqual(len(e.queues[-1]), 3)
            for side in (1, -1):
                self.assertEqual(set(e.queues[side]), {i for i, x in enumerate(e.board) if x == side})
        self.assertTrue(e.truncated)
        self.assertFalse(e.terminated)
        self.assertEqual(e.plies, 120)

    def test_order_is_part_of_infinite_state(self):
        e = TicTacToeEnv("infinite")
        for a in (0, 2, 1, 5, 4, 6):
            e.step(a)
        key = e.state()[0]
        e.queues[1] = [1, 0, 4]
        self.assertNotEqual(key, e.state()[0])

    def test_symmetry_preserves_state_and_actions(self):
        for variant in ("classic", "infinite"):
            e = TicTacToeEnv(variant)
            for a in (0, 4, 1, 8):
                e.step(a)
            key, mapping = e.state()
            for symmetry in SYMMETRIES:
                rotated = TicTacToeEnv(variant)
                for a in (0, 4, 1, 8):
                    rotated.step(symmetry[a])
                self.assertEqual(key, rotated.state()[0])
                self.assertEqual(mapping[2], rotated.state()[1][symmetry[2]])


class LearningTests(unittest.TestCase):
    def test_negamax_target_and_illegal_mask(self):
        a = QAgent()
        e = TicTacToeEnv()
        state = e.state()
        transition = e.step(0)
        key, mapping = e.state()
        a.q[key] = [0.5] * 9
        a.q[key][mapping[0]] = 1.8  # Illegal value must never enter target.
        a.update(state, 0, transition, e)
        self.assertAlmostEqual(a.q[state[0]][state[1][0]], -0.25 * 0.97 * 0.5)

    def test_terminal_has_no_bootstrap(self):
        a = QAgent()
        e = TicTacToeEnv()
        state = e.state()
        a.update(state, 0, Transition(1, True, False, 1, None), e)
        self.assertEqual(a.q[state[0]][state[1][0]], 0.25)

    def test_truncation_keeps_bootstrap(self):
        a = QAgent("infinite")
        e = TicTacToeEnv("infinite")
        state = e.state()
        transition = e.step(0)
        e.truncated = True
        key, _ = e.state()
        a.q[key] = [0.5] * 9
        a.update(state, 0, Transition(0, False, True, 0, None), e)
        self.assertAlmostEqual(a.q[state[0]][state[1][0]], -0.25 * 0.97 * 0.5)

    def test_resume_restores_exact_learning_trajectory(self):
        for variant in ("classic", "infinite"):
            direct = QAgent(variant, 22)
            train(direct, 200, log_every=50, eval_games=10)
            split = QAgent(variant, 22)
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "resume.ttq.gz"
                train(split, 100, path, log_every=50, eval_games=10)
                split = QAgent.load(path, variant)
                train(split, 100, log_every=50, eval_games=10)
            self.assertEqual(direct.q, split.q)
            self.assertEqual(direct.rng.getstate(), split.rng.getstate())
            self.assertEqual(direct.episodes, split.episodes)
            self.assertEqual(direct.outcomes, split.outcomes)
            self.assertEqual(direct.steps, split.steps)

    def test_stop_produces_valid_checkpoint_and_csv(self):
        stop = threading.Event()
        a = QAgent()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stop.ttq.gz"
            train(a, 1000, path, callback=lambda _: stop.set(), stop=stop,
                  log_every=50, eval_games=10)
            restored = QAgent.load(path)
            self.assertEqual(restored.episodes, 50)
            self.assertTrue(path.with_suffix('.csv').exists())

    def test_eval_does_not_change_model_rng_or_q(self):
        a = QAgent()
        state = a.rng.getstate()
        self.assertEqual(evaluate(a, 20), evaluate(a, 20))
        self.assertEqual(a.rng.getstate(), state)
        self.assertEqual(a.q, {})

    def test_wrong_variant_and_corrupt_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "a.ttq.gz"
            QAgent().save(p)
            with self.assertRaises(ValueError):
                QAgent.load(p, "infinite")
            p.write_bytes(b"bad gzip data")
            with self.assertRaises((OSError, ValueError)):
                QAgent.load(p)

    def test_bundled_models_are_legal_and_beat_random(self):
        root = Path(__file__).resolve().parent.parent
        for variant in ("classic", "infinite"):
            a = QAgent.load(root / "models" / (variant + ".ttq.gz"))
            result = evaluate(a, 300)
            self.assertGreater(result["win_rate"], 0.7)
            self.assertLess(result["loss_rate"], 0.05)

    def test_localization_keys_and_no_long_dashes(self):
        t = Translator()
        self.assertEqual(t.tables["ru"].keys(), t.tables["en"].keys())
        for code in ("ru", "en"):
            for value in t.tables[code].values():
                self.assertNotIn(chr(0x2014), value)
                self.assertNotIn(chr(0x2013), value)


if __name__ == "__main__":
    unittest.main()
