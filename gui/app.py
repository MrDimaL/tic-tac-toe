"""Desktop match UI. All moves go through TicTacToeEnv.step()."""
from __future__ import annotations

import json
from pathlib import Path
import random
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from localization import Translator
from src.agent import QAgent, atomic_json
from src.environment import TicTacToeEnv
from .style import BG, PANEL, CARD, FG, MUTED, ACCENT, RED, BLUE, setup, label, button
from .statistics import StatisticsWindow
from .training_window import TrainingWindow

ROOT = Path(__file__).resolve().parent.parent


class App:
    def __init__(self, root):
        self.root = root
        setup(root)
        root.geometry("1120x820")
        root.minsize(960, 700)
        self.settings = {}
        try:
            self.settings = json.loads((ROOT / "data" / "settings.json").read_text(encoding="utf-8"))
            if not isinstance(self.settings, dict):
                self.settings = {}
        except (OSError, ValueError):
            pass
        self.t = Translator(self.settings.get("language", "ru"))
        self.rule = self.settings.get("variant", "classic")
        if self.rule not in ("classic", "infinite"):
            self.rule = "classic"
        self.match = self.settings.get("mode", "hvm")
        if self.match not in ("hvm", "mvm", "hvh"):
            self.match = "hvm"
        self.human_side = self.settings.get("side", "X")
        if self.human_side not in ("X", "O"):
            self.human_side = "X"
        try:
            self.delay = min(2000, max(100, int(self.settings.get("delay", 650))))
        except (TypeError, ValueError):
            self.delay = 650
        self.score = {"x": 0, "o": 0, "draw": 0}
        self.models = {}
        self.startup_errors = []
        for variant in ("classic", "infinite"):
            try:
                agent = QAgent.load(ROOT / "models" / f"{variant}.ttq.gz", variant)
            except Exception as exc:
                agent = QAgent(variant)
                self.startup_errors.append(f"{variant}: {exc}")
            self.models[variant] = {1: agent, -1: agent}
        self.env = TicTacToeEnv(self.rule)
        self.paused = False
        self.rng = random.Random()
        self.last_machine_time = time.monotonic()
        self.hover = None
        self.animate_until = 0
        self.training = None
        self.stats_windows = []
        self.closing = False
        self.build()
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(30, self.tick)
        if self.startup_errors:
            root.after(200, lambda: messagebox.showerror(self.t("error"),
                "Bundled model could not be loaded. Using an untrained model.\n" +
                "\n".join(self.startup_errors), parent=root))

    @property
    def agents(self):
        return self.models[self.rule]

    def build(self):
        t = self.t
        self.root.title(t("app_title"))
        for child in self.root.winfo_children():
            # Keep independent training/statistics windows alive on locale change.
            if not isinstance(child, tk.Toplevel):
                child.destroy()
        outer = tk.Frame(self.root, bg=BG)
        outer.pack(fill="both", expand=True, padx=24, pady=22)
        header = tk.Frame(outer, bg=BG)
        header.pack(fill="x", pady=(0, 20))
        brand = tk.Frame(header, bg=BG)
        brand.pack(side="left")
        label(brand, t("brand"), 24, bold=True).pack(anchor="w")
        label(brand, t("subtitle"), color=MUTED).pack(anchor="w", pady=(5, 0))
        lang = tk.Frame(header, bg=BG)
        lang.pack(side="right")
        label(lang, t("language"), 9, color=MUTED).pack(anchor="e")
        self.language_var = tk.StringVar(value="Русский" if t.language == "ru" else "English")
        cb = ttk.Combobox(lang, textvariable=self.language_var,
                         values=["Русский", "English"], state="readonly", width=12)
        cb.pack(pady=(4, 0))
        cb.bind("<<ComboboxSelected>>", self.change_language)
        content = tk.Frame(outer, bg=BG)
        content.pack(fill="both", expand=True)
        side = tk.Frame(content, bg=PANEL, width=300)
        side.pack(side="left", fill="y", padx=(0, 24))
        side.pack_propagate(False)
        scroll = ttk.Scrollbar(side, orient="vertical")
        scroll.pack(side="right", fill="y")
        viewport = tk.Canvas(side, bg=PANEL, highlightthickness=0,
                             yscrollcommand=scroll.set)
        viewport.pack(side="left", fill="both", expand=True)
        scroll.config(command=viewport.yview)
        inner = tk.Frame(viewport, bg=PANEL)
        inner_id = viewport.create_window((16, 16), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda _: viewport.configure(
            scrollregion=(0, 0, viewport.winfo_width(), inner.winfo_reqheight() + 32)))
        viewport.bind("<Configure>", lambda e: viewport.itemconfigure(inner_id, width=max(1, e.width - 32)))
        label(inner, t("setup"), 10, color=ACCENT, bold=True, bg=PANEL).pack(anchor="w", pady=(0, 9))
        self.rule_var = tk.StringVar(value=t(self.rule))
        self.mode_var = tk.StringVar(value=t(self.match))
        self.side_var = tk.StringVar(value=self.human_side)
        for caption, variable, values in (
                ("rules", self.rule_var, [t("classic"), t("infinite")]),
                ("mode", self.mode_var, [t("hvm"), t("mvm"), t("hvh")]),
                ("side", self.side_var, ["X", "O"])):
            label(inner, t(caption), 10, color=MUTED, bg=PANEL).pack(anchor="w")
            combo = ttk.Combobox(inner, textvariable=variable, values=values, state="readonly")
            combo.pack(fill="x", pady=(4, 9))
            combo.bind("<<ComboboxSelected>>", lambda _: self.pending.config(text=t("pending")))
        self.delay_var = tk.IntVar(value=self.delay)
        label(inner, t("speed"), 10, color=MUTED, bg=PANEL).pack(anchor="w")
        scale = tk.Scale(inner, from_=100, to=2000, resolution=50, orient="horizontal",
                         variable=self.delay_var, bg=PANEL, fg=FG, troughcolor=CARD,
                         activebackground=ACCENT, highlightthickness=0,
                         command=lambda value: setattr(self, "delay", int(value)))
        scale.pack(fill="x", pady=(0, 5))
        button(inner, t("new_game"), self.new_game, True).pack(fill="x", pady=(0, 5))
        self.pending = label(inner, "", 8, color=MUTED, bg=PANEL, wraplength=260, anchor="w")
        self.pending.pack(fill="x", pady=(0, 8))
        label(inner, t("models"), 10, color=ACCENT, bold=True, bg=PANEL).pack(anchor="w", pady=(2, 8))
        self.model_labels = {}
        for symbol, side_id in (("X", 1), ("O", -1)):
            self.model_labels[side_id] = label(inner, "", 9, bg=PANEL, color=MUTED, anchor="w")
            self.model_labels[side_id].pack(fill="x", pady=(0, 5))
            row = tk.Frame(inner, bg=PANEL)
            row.pack(fill="x", pady=(0, 6))
            button(row, t("load_x" if side_id == 1 else "load_o"),
                   lambda s=side_id: self.load_model(s)).pack(side="left", fill="x", expand=True, padx=(0, 5))
            button(row, t("save_x" if side_id == 1 else "save_o"),
                   lambda s=side_id: self.save_model(s)).pack(side="right", fill="x", expand=True)
        button(inner, t("train"), self.open_training).pack(fill="x", pady=(5, 6))
        button(inner, t("stats"), self.open_statistics).pack(fill="x", pady=(0, 6))
        bottom = tk.Frame(inner, bg=PANEL)
        bottom.pack(fill="x", pady=(16, 0))
        label(bottom, t("score"), 9, color=MUTED, bg=PANEL).pack(anchor="w")
        self.score_label = label(bottom, "", 11, bold=True, bg=PANEL)
        self.score_label.pack(anchor="w", pady=(5, 6))
        button(bottom, t("clear_score"), self.clear_score).pack(fill="x")
        main = tk.Frame(content, bg=BG)
        main.pack(side="left", fill="both", expand=True)
        top = tk.Frame(main, bg=BG)
        top.pack(fill="x")
        self.turn_label = label(top, "", 24, bold=True)
        self.turn_label.pack(side="left")
        self.move_label = label(top, "", 10, color=MUTED)
        self.move_label.pack(side="right")
        self.active_label = label(main, "", 10, color=MUTED, anchor="w")
        self.active_label.pack(fill="x", pady=(6, 15))
        self.canvas = tk.Canvas(main, bg="#000000", highlightthickness=1,
                                highlightbackground="#283346", cursor="hand2")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _: self.draw())
        self.canvas.bind("<Button-1>", self.click)
        self.canvas.bind("<Motion>", self.motion)
        self.canvas.bind("<Leave>", lambda _: self.leave())
        self.hint_label = label(main, "", 10, color=MUTED, wraplength=660, justify="left", anchor="w")
        self.hint_label.pack(fill="x", pady=(12, 10))
        controls = tk.Frame(main, bg=BG)
        controls.pack(fill="x")
        button(controls, t("restart"), self.restart).pack(side="left", padx=(0, 8))
        self.pause_button = button(controls, t("pause"), self.toggle_pause)
        self.pause_button.pack(side="left", padx=(0, 8))
        button(controls, t("step"), self.single_step).pack(side="left")
        footer = tk.Frame(main, bg=BG)
        footer.pack(fill="x", pady=(8, 0))
        button(footer, t("help"), self.help).pack(side="left")
        button(footer, t("exit"), self.close).pack(side="right")
        self.refresh()

    def change_language(self, _=None):
        self.t.language = "ru" if self.language_var.get() == "Русский" else "en"
        self.build()
        for window in self.stats_windows:
            if window.window.winfo_exists():
                window.build()
        self.save_settings()

    def refresh(self):
        t, env = self.t, self.env
        if env.winner:
            text = t("win", side="X" if env.winner == 1 else "O")
        elif env.done:
            text = t("limit" if env.truncated else "draw")
        elif self.paused:
            text = t("paused")
        else:
            text = t("turn", side="X" if env.turn == 1 else "O")
        self.turn_label.config(text=text, fg=RED if env.winner == 1 else BLUE if env.winner == -1 else FG)
        self.move_label.config(text=t("move_number", n=env.plies))
        self.active_label.config(text=t("active_rules", rules=t(self.rule), mode=t(self.match)))
        self.score_label.config(text=t("score_value", **self.score))
        self.pause_button.config(text=t("resume" if self.paused else "pause"))
        self.hint_label.config(text=t("infinite_hint" if self.rule == "infinite" else "classic_hint"))
        for side_id in (1, -1):
            a = self.agents[side_id]
            self.model_labels[side_id].config(text=t("model_info", side="X" if side_id == 1 else "O",
                                                    episodes=a.episodes, states=len(a.q)))
        self.draw()

    def geometry(self):
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        size = max(0, min(width, height) - 48)
        return (width - size) / 2, (height - size) / 2, size / 3

    def cell_at(self, x, y):
        left, top, cell = self.geometry()
        if cell > 0 and left <= x < left + cell * 3 and top <= y < top + cell * 3:
            return int((y - top) / cell) * 3 + int((x - left) / cell)
        return None

    def draw(self):
        if not hasattr(self, "canvas"):
            return
        c, env = self.canvas, self.env
        c.delete("all")
        left, top, cell = self.geometry()
        if cell < 4:
            return
        for n in (1, 2):
            c.create_line(left + n * cell, top, left + n * cell, top + 3 * cell,
                          fill="#ffffff", width=3)
            c.create_line(left, top + n * cell, left + 3 * cell, top + n * cell,
                          fill="#ffffff", width=3)
        if self.hover in env.legal_actions() and self.is_human() and not self.paused:
            r, col = divmod(self.hover, 3)
            x, y = left + col * cell, top + r * cell
            c.create_rectangle(x + 8, y + 8, x + cell - 8, y + cell - 8,
                               outline="#354256", width=2)
        progress = max(0, min(1, 1 - (self.animate_until - time.monotonic()) / 0.18))
        for i, value in enumerate(env.board):
            if not value:
                continue
            row, col = divmod(i, 3)
            x, y = left + (col + 0.5) * cell, top + (row + 0.5) * cell
            scale = (0.65 + 0.35 * progress) if i == env.last_action else 1
            radius = cell * 0.27 * scale
            color = RED if value == 1 else BLUE
            stroke = max(5, int(cell * 0.055))
            if value == 1:
                c.create_line(x-radius, y-radius, x+radius, y+radius, fill=color, width=stroke, capstyle="round")
                c.create_line(x-radius, y+radius, x+radius, y-radius, fill=color, width=stroke, capstyle="round")
            else:
                c.create_oval(x-radius, y-radius, x+radius, y+radius, outline=color, width=stroke)
            if self.rule == "infinite":
                age = env.queues[value].index(i) + 1
                c.create_text(left + (col + 1)*cell - 17, top + (row + 1)*cell - 17,
                              text=str(age), fill=color, font=("Arial", 11, "bold"))
                if age == 1 and len(env.queues[value]) == 3:
                    c.create_oval(x-radius-12, y-radius-12, x+radius+12, y+radius+12,
                                  outline=color, dash=(3, 6), width=1)
        if env.winning_line:
            first, last = env.winning_line[0], env.winning_line[-1]
            r1, c1 = divmod(first, 3)
            r2, c2 = divmod(last, 3)
            c.create_line(left+(c1+.5)*cell, top+(r1+.5)*cell,
                          left+(c2+.5)*cell, top+(r2+.5)*cell,
                          fill=ACCENT, width=5, capstyle="round")

    def is_human(self):
        return self.match == "hvh" or (self.match == "hvm" and
                self.env.turn == (1 if self.human_side == "X" else -1))

    def motion(self, event):
        cell = self.cell_at(event.x, event.y)
        if cell != self.hover:
            self.hover = cell
            self.draw()

    def leave(self):
        self.hover = None
        self.draw()

    def click(self, event):
        action = self.cell_at(event.x, event.y)
        if self.is_human() and not self.paused and action in self.env.legal_actions():
            self.move(action)

    def move(self, action):
        self.env.step(action)
        self.animate_until = time.monotonic() + 0.18
        self.last_machine_time = time.monotonic()
        if self.env.done:
            self.score["x" if self.env.winner == 1 else "o" if self.env.winner == -1 else "draw"] += 1
        self.refresh()

    def new_game(self):
        self.rule = "infinite" if self.rule_var.get() == self.t("infinite") else "classic"
        self.match = next((k for k in ("hvm", "mvm", "hvh") if self.t(k) == self.mode_var.get()), "hvm")
        self.human_side = self.side_var.get()
        self.restart()
        self.save_settings()

    def restart(self):
        self.env = TicTacToeEnv(self.rule)
        self.paused = False
        self.hover = None
        self.last_machine_time = time.monotonic()
        self.pending.config(text="")
        self.refresh()

    def toggle_pause(self):
        self.paused = not self.paused
        self.last_machine_time = time.monotonic()
        self.refresh()

    def single_step(self):
        self.paused = True
        if not self.is_human() and not self.env.done:
            self.move(self.agents[self.env.turn].choose(self.env, rng=self.rng))
        self.refresh()

    def tick(self):
        if self.closing:
            return
        now = time.monotonic()
        if not self.paused and not self.env.done and not self.is_human():
            if (now - self.last_machine_time) * 1000 >= self.delay:
                self.move(self.agents[self.env.turn].choose(self.env, rng=self.rng))
        if now < self.animate_until + 0.04:
            self.draw()
        self.root.after(30, self.tick)

    def load_model(self, side_id):
        path = filedialog.askopenfilename(parent=self.root, title=self.t("load_model"),
                    filetypes=[(self.t("model_file"), "*.ttq.gz")])
        if not path:
            return
        try:
            self.agents[side_id] = QAgent.load(path, self.rule)
            self.refresh()
        except Exception as exc:
            messagebox.showerror(self.t("error"), self.t("model_error", variant=self.t(self.rule)) +
                                 "\n" + str(exc), parent=self.root)

    def save_model(self, side_id):
        a = self.agents[side_id]
        path = filedialog.asksaveasfilename(parent=self.root, title=self.t("save_model"),
                    initialfile=f"{a.variant}_{a.episodes}.ttq.gz", defaultextension=".ttq.gz",
                    filetypes=[(self.t("model_file"), "*.ttq.gz")])
        if path:
            self.safe_write(lambda: a.save(path), path)

    def safe_write(self, operation, path):
        try:
            operation()
            messagebox.showinfo(self.t("save_model"), self.t("saved", path=path), parent=self.root)
        except Exception as exc:
            messagebox.showerror(self.t("error"), str(exc), parent=self.root)

    def open_training(self):
        if self.training and not self.training.closed:
            self.training.window.lift()
            return
        self.paused = True
        self.refresh()
        def complete(agent):
            self.models[agent.variant] = {1: agent, -1: agent}
            self.refresh()
        self.training = TrainingWindow(self.root, self.agents[1], complete)

    def open_statistics(self):
        self.stats_windows = [s for s in self.stats_windows if s.window.winfo_exists()]
        self.stats_windows.append(StatisticsWindow(self))

    def clear_score(self):
        self.score = {"x": 0, "o": 0, "draw": 0}
        self.refresh()

    def help(self):
        messagebox.showinfo(self.t("help"), self.t("help_text"), parent=self.root)

    def save_settings(self):
        try:
            atomic_json(ROOT / "data" / "settings.json", dict(language=self.t.language,
                variant=self.rule, mode=self.match, side=self.human_side, delay=self.delay))
        except OSError as exc:
            messagebox.showerror(self.t("error"), str(exc), parent=self.root)

    def close(self):
        if self.closing:
            return
        self.save_settings()
        self.closing = True
        if self.training and not self.training.closed and self.training.running:
            self.training.close()
            self.wait_for_training()
        else:
            self.root.destroy()

    def wait_for_training(self):
        if self.training.running:
            self.root.after(100, self.wait_for_training)
        else:
            self.root.destroy()
