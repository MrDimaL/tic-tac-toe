"""Optional desktop integration test: TTT_GUI_TESTS=1 python -m unittest tests.test_gui -v"""
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.environ.get("TTT_GUI_TESTS") == "1", "Requires a graphical desktop")
class DesktopTests(unittest.TestCase):
    def test_match_localization_statistics_and_training(self):
        import tkinter as tk
        from gui.app import App
        from src.agent import QAgent
        errors = []
        with tempfile.TemporaryDirectory() as tmp, \
                patch("gui.app.ROOT", Path(tmp)), \
                patch("gui.training_window.ROOT", Path(tmp)), \
                patch("gui.app.messagebox.showerror", side_effect=lambda *a, **k: errors.append(a)), \
                patch("gui.app.messagebox.showinfo"), \
                patch("gui.training_window.messagebox.showerror", side_effect=lambda *a, **k: errors.append(a)):
            # Models are loaded from the distribution, preferences go into temp.
            project = Path(__file__).resolve().parent.parent
            root = tk.Tk()
            root.withdraw()
            root.report_callback_exception = lambda *exc: errors.append(exc)
            # Avoid startup fallback notices by copying bundled data into temp.
            import shutil
            shutil.copytree(project / "models", Path(tmp) / "models")
            app = App(root)
            root.update_idletasks()
            try:
                self.assertGreater(app.canvas.winfo_width(), 400)
                app.mode_var.set(app.t("hvh"))
                app.new_game()
                for action in (0, 3, 1, 4, 2):
                    app.move(action)
                self.assertEqual(app.env.winner, 1)
                self.assertEqual(app.score["x"], 1)
                app.restart()
                self.assertFalse(app.env.done)
                app.rule_var.set(app.t("infinite"))
                app.mode_var.set(app.t("mvm"))
                app.new_game()
                app.single_step()
                self.assertEqual(app.env.plies, 1)
                self.assertTrue(app.paused)
                before = list(app.env.board)
                app.language_var.set("English")
                app.change_language()
                root.update_idletasks()
                self.assertEqual(app.env.board, before)
                self.assertEqual(app.t.language, "en")
                app.rule_var.set(app.t("classic"))
                app.mode_var.set(app.t("hvm"))
                app.side_var.set("O")
                app.new_game()
                self.assertFalse(app.is_human())
                app.single_step()
                self.assertTrue(app.is_human())
                self.assertEqual(app.env.plies, 1)
                app.open_statistics()
                stats = app.stats_windows[-1]
                stats.evaluate()
                self.pump(root, lambda: not stats.busy)
                self.assertEqual(stats.results["games"], 500)
                stats.side_var.set("O")
                stats.change_side()
                self.assertEqual(stats.side, -1)
                self.assertIsNone(stats.results)
                app.open_training()
                training = app.training
                training.variant.set("classic")
                training.seed.set("9")
                training.new_model()
                training.episodes.set("1000")
                training.start()
                self.pump(root, lambda: not training.running)
                self.assertEqual(training.agent.episodes, 1000)
                self.assertEqual(app.agents[1].episodes, 1000)
                self.assertTrue(training.output.exists())
                restored = QAgent.load(training.output)
                self.assertEqual(restored.q, training.agent.q)
                csv_path = Path(tmp) / "training.csv"
                svg_path = Path(tmp) / "charts.svg"
                with patch("gui.training_window.filedialog.asksaveasfilename", return_value=str(csv_path)):
                    training.csv()
                with patch("gui.training_window.filedialog.asksaveasfilename", return_value=str(svg_path)):
                    training.svg()
                self.assertIn("td_mse", csv_path.read_text())
                import xml.etree.ElementTree as ET
                self.assertTrue(ET.parse(svg_path).getroot().tag.endswith("svg"))
                with patch("gui.app.filedialog.askopenfilename", return_value=str(training.output)):
                    app.load_model(-1)
                self.assertEqual(app.agents[-1].episodes, 1000)
                training.episodes.set("1000000")
                training.start()
                training.pause()
                self.pump(root, lambda: training.pause_event.is_set())
                training.stop()
                self.pump(root, lambda: not training.running)
                self.assertLess(training.agent.episodes, 1001000)
                training.close()
                self.assertTrue(training.closed)
                self.assertEqual(errors, [])
            finally:
                if app.training and app.training.running:
                    app.training.stop()
                    self.pump(root, lambda: not app.training.running)
                root.destroy()

    def pump(self, root, predicate, timeout=20):
        deadline = time.monotonic() + timeout
        while not predicate() and time.monotonic() < deadline:
            root.update()
            time.sleep(0.01)
        root.update()
        self.assertTrue(predicate(), "Timed out waiting for a GUI operation")
