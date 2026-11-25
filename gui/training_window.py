"""English-only training dashboard, safe worker lifecycle and checkpoints."""
from __future__ import annotations

import copy
from datetime import datetime
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from src.agent import QAgent
from src.training import train, export_csv
from .charts import Chart, fill_charts, export_svg
from .style import BG, FG, MUTED, ACCENT, label, button

ROOT = Path(__file__).resolve().parent.parent


class TrainingWindow:
    def __init__(self, parent, agent=None, on_complete=None, standalone=False):
        self.window = parent if standalone else tk.Toplevel(parent)
        self.window.title("RL Training | Tic-Tac-Toe")
        self.window.configure(bg=BG)
        self.window.geometry("1100x820")
        self.window.minsize(960, 720)
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.on_complete = on_complete
        self.agent = copy.deepcopy(agent) if agent else QAgent()
        self.running = False
        self.closed = False
        self.close_when_done = False
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.events = queue.Queue()
        self.output = None
        self.variant = tk.StringVar(value=self.agent.variant)
        self.episodes = tk.StringVar(value="10000")
        self.seed = tk.StringVar(value=str(self.agent.seed))
        outer = tk.Frame(self.window, bg=BG)
        outer.pack(fill="both", expand=True, padx=24, pady=20)
        label(outer, "SELF-PLAY / TRAINING LAB", 23, bold=True).pack(anchor="w")
        label(outer, "Negamax Q-learning  /  CPU  /  English charts", color=MUTED).pack(anchor="w", pady=(4, 16))
        settings = ttk.Frame(outer)
        settings.pack(fill="x")
        self.editable = []
        for i, (caption, var, values) in enumerate((
                ("Rules", self.variant, ["classic", "infinite"]),
                ("Additional episodes", self.episodes, None),
                ("Seed for NEW model", self.seed, None))):
            label(settings, caption, color=MUTED).grid(row=0, column=i, sticky="w", padx=(0, 16))
            widget = (ttk.Combobox(settings, textvariable=var, values=values,
                                   state="readonly", width=20) if values else
                      ttk.Entry(settings, textvariable=var, width=22))
            widget.grid(row=1, column=i, sticky="ew", padx=(0, 16), pady=(5, 12))
            self.editable.append(widget)
        controls = ttk.Frame(outer)
        controls.pack(fill="x")
        self.new_button = button(controls, "New model", self.new_model)
        self.load_button = button(controls, "Load checkpoint", self.load)
        self.start_button = button(controls, "Start / continue", self.start, True)
        self.pause_button = button(controls, "Pause", self.pause, state="disabled")
        self.stop_button = button(controls, "Stop & save", self.stop, state="disabled")
        for w in (self.new_button, self.load_button, self.start_button,
                  self.pause_button, self.stop_button):
            w.pack(side="left", padx=(0, 8))
        self.status = label(outer, "Ready. New model resets learning; Start adds episodes.", color=ACCENT, anchor="w")
        self.status.pack(fill="x", pady=(12, 4))
        self.numbers = label(outer, "", color=MUTED, anchor="w")
        self.numbers.pack(fill="x", pady=(0, 10))
        self.progress = ttk.Progressbar(outer, mode="determinate")
        self.progress.pack(fill="x", pady=(0, 12))
        grid = ttk.Frame(outer)
        grid.pack(fill="both", expand=True)
        grid.rowconfigure((0, 1), weight=1)
        grid.columnconfigure((0, 1), weight=1)
        self.charts = []
        for i, (title, unit) in enumerate((("Squared TD error", "TD MSE"),
                ("Evaluation vs random (200 games, seed 1042)", "Rate"),
                ("Exploration schedule", "Epsilon"), ("Mean game length", "Moves"))):
            chart = Chart(grid, title, unit, width=450, height=220)
            chart.grid(row=i // 2, column=i % 2, sticky="nsew", padx=5, pady=5)
            self.charts.append(chart)
        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=(12, 0))
        self.save_button = button(footer, "Save model as...", self.save)
        self.csv_button = button(footer, "Export CSV", self.csv)
        self.svg_button = button(footer, "Export charts (SVG)", self.svg)
        for w in (self.save_button, self.csv_button, self.svg_button):
            w.pack(side="left", padx=(0, 8))
        button(footer, "Close", self.close).pack(side="right")
        self.refresh()
        self.window.after(100, self.poll)

    def refresh(self):
        a = self.agent
        td = a.history[-1]["td_mse"] if a.history else 0
        self.numbers.config(text=f"{a.variant.upper()} | Episodes {a.episodes:,} | States {len(a.q):,} | Steps {a.steps:,} | Epsilon {a.epsilon:.4f} | TD MSE {td:.6f}")
        fill_charts(self.charts, a.history)

    def new_model(self):
        try:
            self.agent = QAgent(self.variant.get(), int(self.seed.get()))
            self.output = None
            self.refresh()
            self.status.config(text="New untrained model. Press Start to learn.")
        except Exception as exc:
            messagebox.showerror("Training error", str(exc), parent=self.window)

    def load(self):
        path = filedialog.askopenfilename(parent=self.window, title="Load checkpoint",
                                          filetypes=[("Q-learning model", "*.ttq.gz")])
        if not path:
            return
        try:
            agent = QAgent.load(path)
            self.agent = agent
            self.variant.set(agent.variant)
            self.seed.set(str(agent.seed))
            self.output = None
            self.refresh()
            self.status.config(text="Checkpoint loaded. Start will continue this model.")
        except Exception as exc:
            messagebox.showerror("Invalid checkpoint", str(exc), parent=self.window)

    def start(self):
        try:
            count = int(self.episodes.get())
            if not 1 <= count <= 10_000_000:
                raise ValueError("Additional episodes must be between 1 and 10,000,000")
            if self.variant.get() != self.agent.variant:
                raise ValueError("Press New model to change the rule set")
            if self.output is None:
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                self.output = ROOT / "data" / "models" / f"{self.agent.variant}_{stamp}.ttq.gz"
                self.output.parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            messagebox.showerror("Training error", str(exc), parent=self.window)
            return
        self.stop_event.clear()
        self.pause_event.clear()
        self.pause_button.config(text="Pause")
        self.start_episode = self.agent.episodes
        self.target_episode = self.agent.episodes + count
        self.progress.config(maximum=count, value=0)
        self.set_running(True)
        self.status.config(text="Training... checkpoints every 500 episodes. Stop saves progress.")

        def worker():
            try:
                train(self.agent, count, self.output,
                      callback=lambda row: self.events.put(("progress", row)),
                      stop=self.stop_event, pause=self.pause_event)
                self.events.put(("done", None))
            except Exception as exc:
                self.events.put(("error", str(exc)))
        threading.Thread(target=worker, daemon=False).start()

    def pause(self):
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.pause_button.config(text="Pause")
            self.status.config(text="Training resumed.")
        else:
            self.pause_event.set()
            self.pause_button.config(text="Resume")
            self.status.config(text="Pausing at the next episode boundary...")

    def stop(self):
        self.stop_event.set()
        self.pause_event.clear()
        self.status.config(text="Stopping and saving the completed episodes...")
        self.stop_button.config(state="disabled")

    def poll(self):
        if self.closed:
            return
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "progress":
                    # Worker owns the agent while running. UI reads only messages.
                    history = getattr(self, "live_history", None)
                    if history is None:
                        history = list(self.initial_history)
                    history.append(payload)
                    self.live_history = history
                    fill_charts(self.charts, history)
                    self.progress.config(value=payload["episode"] - self.start_episode)
                    self.numbers.config(text=f"{self.variant.get().upper()} | Episodes {payload['episode']:,} | States {payload['states']:,} | Epsilon {payload['epsilon']:.4f} | TD MSE {payload['td_mse']:.6f}")
                else:
                    self.set_running(False)
                    self.live_history = None
                    self.refresh()
                    if kind == "done":
                        self.progress.config(value=self.agent.episodes - self.start_episode)
                        self.status.config(text=f"Saved {self.output.name}. Game models updated." if self.on_complete else f"Saved {self.output.name}.")
                        if self.on_complete:
                            self.on_complete(copy.deepcopy(self.agent))
                    else:
                        self.status.config(text="Training stopped due to an error.")
                        messagebox.showerror("Training error", payload, parent=self.window)
                    if self.close_when_done:
                        self.close()
                        return
        except queue.Empty:
            pass
        self.window.after(100, self.poll)

    def save(self):
        path = filedialog.asksaveasfilename(parent=self.window, title="Save model",
                    initialfile=f"{self.agent.variant}_{self.agent.episodes}.ttq.gz",
                    defaultextension=".ttq.gz", filetypes=[("Q-learning model", "*.ttq.gz")])
        if path:
            self.write(lambda: self.agent.save(path), path)

    def csv(self):
        path = filedialog.asksaveasfilename(parent=self.window, title="Export training CSV",
                    defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path:
            self.write(lambda: export_csv(self.agent, path), path)

    def svg(self):
        path = filedialog.asksaveasfilename(parent=self.window, title="Export charts",
                    defaultextension=".svg", filetypes=[("SVG", "*.svg")])
        if path:
            self.write(lambda: export_svg(self.charts, path), path)

    def write(self, operation, path):
        try:
            operation()
            self.status.config(text=f"Saved: {path}")
        except Exception as exc:
            messagebox.showerror("Write error", str(exc), parent=self.window)

    def close(self):
        if self.running:
            self.close_when_done = True
            self.stop()
            return
        self.closed = True
        self.window.destroy()

    @property
    def initial_history(self):
        # Capture history BEFORE starting a worker; never traverse its live table.
        return self._initial_history

    def set_running(self, value):
        if value:
            self._initial_history = list(self.agent.history)
            self.live_history = None
        self.running = value
        for w in (self.new_button, self.load_button, self.start_button,
                  self.save_button, self.csv_button, self.svg_button):
            w.config(state="disabled" if value else "normal")
        for w in self.editable:
            w.config(state="disabled" if value else
                     "readonly" if isinstance(w, ttk.Combobox) else "normal")
        for w in (self.pause_button, self.stop_button):
            w.config(state="normal" if value else "disabled")
