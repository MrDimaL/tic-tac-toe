from __future__ import annotations

import copy
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from src.training import evaluate, export_csv
from .charts import Chart, fill_charts, export_svg
from .style import BG, MUTED, ACCENT, label, button


class StatisticsWindow:
    def __init__(self, app):
        self.app = app
        self.window = tk.Toplevel(app.root)
        self.window.geometry("1090x810")
        self.window.minsize(950, 720)
        self.results = None
        self.busy = False
        self.queue = queue.Queue()
        self.side = 1
        self.agent = copy.deepcopy(app.agents[1])
        self.build()
        self.window.after(100, self.poll)

    def build(self):
        t = self.app.t
        self.window.title(t("statistics"))
        self.window.configure(bg=BG)
        for child in self.window.winfo_children():
            child.destroy()
        body = tk.Frame(self.window, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=20)
        header = tk.Frame(body, bg=BG)
        header.pack(fill="x")
        label(header, t("statistics"), 22, bold=True).pack(side="left")
        self.side_var = tk.StringVar(value="X" if self.side == 1 else "O")
        selector = ttk.Combobox(header, values=["X", "O"], textvariable=self.side_var,
                                state="disabled" if self.busy else "readonly", width=5)
        self.selector = selector
        selector.pack(side="right")
        selector.bind("<<ComboboxSelected>>", self.change_side)
        a = self.agent
        label(body, t("training_numbers", side=self.side_var.get()) + " / " + t(a.variant), color=ACCENT).pack(anchor="w", pady=(12, 6))
        cells = tk.Frame(body, bg=BG)
        cells.pack(fill="x")
        metrics = [("episodes", f"{a.episodes:,}"), ("states", f"{len(a.q):,}"),
                   ("steps", f"{a.steps:,}"), ("epsilon", f"{a.epsilon:.4f}"),
                   ("seconds", f"{a.elapsed:.1f}"),
                   ("td_mse", f"{a.history[-1]['td_mse']:.6f}" if a.history else "-")]
        for i, (key, value) in enumerate(metrics):
            cell = tk.Frame(cells, bg=BG)
            cell.grid(row=0, column=i, sticky="w", padx=(0, 24))
            label(cell, value, 17, bold=True).pack(anchor="w")
            label(cell, t(key), 9, color=MUTED).pack(anchor="w", pady=(2, 8))
        label(body, t("eval_title", side=self.side_var.get()), color=ACCENT).pack(anchor="w", pady=(8, 4))
        self.eval_result = label(body, "", anchor="w", justify="left")
        self.eval_result.pack(fill="x")
        self.update_result()
        controls = ttk.Frame(body)
        controls.pack(fill="x", pady=(8, 12))
        self.eval_button = button(controls, t("evaluating" if self.busy else "evaluate"), self.evaluate, True)
        self.eval_button.pack(side="left", padx=(0, 8))
        if self.busy:
            self.eval_button.config(state="disabled")
        button(controls, t("refresh"), self.refresh).pack(side="left")
        grid = ttk.Frame(body)
        grid.pack(fill="both", expand=True)
        grid.rowconfigure((0, 1), weight=1)
        grid.columnconfigure((0, 1), weight=1)
        self.charts = []
        for i, (key, unit) in enumerate((("chart_td", "TD MSE"), ("chart_rates", t("axis_rate")),
                                         ("chart_epsilon", "Epsilon"), ("chart_length", t("axis_moves")))):
            c = Chart(grid, t(key), unit, t("axis_episode"), empty_text=t("no_history"), width=450, height=190)
            c.grid(row=i // 2, column=i % 2, sticky="nsew", padx=5, pady=5)
            self.charts.append(c)
        fill_charts(self.charts, a.history, t)
        footer = ttk.Frame(body)
        footer.pack(fill="x", pady=(12, 0))
        button(footer, t("export_csv"), self.csv).pack(side="left", padx=(0, 8))
        button(footer, t("export_graph"), self.svg).pack(side="left")
        button(footer, t("close"), self.window.destroy).pack(side="right")

    def update_result(self):
        t = self.app.t
        if self.results is None:
            self.eval_result.config(text=t("eval_empty"))
            return
        r = self.results
        self.eval_result.config(text=t("eval_result", **r) + "\n" +
            t("eval_rates", win=r["win_rate"], draw=r["draw_rate"],
              loss=r["loss_rate"], score=r["score_rate"]) + "\n" +
            t("eval_note", n=r["truncated"]))

    def refresh(self):
        if self.busy:
            return
        self.agent = copy.deepcopy(self.app.agents[self.side])
        self.results = None
        self.build()

    def change_side(self, _=None):
        if self.busy:
            return
        self.side = 1 if self.side_var.get() == "X" else -1
        self.refresh()

    def evaluate(self):
        self.busy = True
        self.selector.config(state="disabled")
        self.eval_button.config(text=self.app.t("evaluating"), state="disabled")
        agent = self.agent
        def worker():
            try:
                self.queue.put((True, evaluate(agent, 500)))
            except Exception as exc:
                self.queue.put((False, str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        if not self.window.winfo_exists():
            return
        try:
            ok, result = self.queue.get_nowait()
            self.busy = False
            self.selector.config(state="readonly")
            if ok:
                self.results = result
            else:
                messagebox.showerror(self.app.t("error"), result, parent=self.window)
            self.eval_button.config(text=self.app.t("evaluate"), state="normal")
            self.update_result()
        except queue.Empty:
            pass
        self.window.after(100, self.poll)

    def csv(self):
        path = filedialog.asksaveasfilename(parent=self.window, title=self.app.t("export_csv"),
                defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path:
            self.app.safe_write(lambda: export_csv(self.agent, path), path)

    def svg(self):
        path = filedialog.asksaveasfilename(parent=self.window, title=self.app.t("export_graph"),
                defaultextension=".svg", filetypes=[("SVG", "*.svg")])
        if path:
            self.app.safe_write(lambda: export_svg(self.charts, path), path)
