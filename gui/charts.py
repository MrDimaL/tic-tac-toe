"""Responsive native canvas charts and portable vector export, no packages."""
from __future__ import annotations

from html import escape
from pathlib import Path
import tkinter as tk

from .style import PANEL, FG, MUTED, ACCENT, BLUE, RED


class Chart(tk.Canvas):
    def __init__(self, parent, title, ylabel="", xlabel="Episode", empty_text="No training history yet", **kw):
        super().__init__(parent, bg=PANEL, highlightthickness=0, **kw)
        self.title, self.ylabel, self.xlabel = title, ylabel, xlabel
        self.empty_text = empty_text
        self.series = []
        self.bind("<Configure>", lambda _: self.redraw())

    def set_data(self, series):
        # series: (legend, color, [(x, y), ...]); keep every logged point.
        self.series = series
        self.redraw()

    def primitives(self, width, height):
        out = []
        def text(x, y, value, color=MUTED, size=10, anchor="middle"):
            out.append(("text", (x, y), value, color, size, anchor))
        def line(points, color, stroke=1):
            out.append(("line", points, color, stroke))
        text(18, 23, self.title, FG, 12, "start")
        text(18, 43, self.ylabel, MUTED, 9, "start")
        left, top, right, bottom = 56, 65, width - 24, height - 58
        if right <= left or bottom <= top:
            return out
        points = [p for _, _, values in self.series for p in values]
        if not points:
            text(width / 2, height / 2, self.empty_text, MUTED, 11)
            return out
        xmin, xmax = min(p[0] for p in points), max(p[0] for p in points)
        ymin, ymax = min(0, min(p[1] for p in points)), max(p[1] for p in points)
        xmax = max(xmax, xmin + 1)
        ymax = max(ymax * 1.08, 0.01)
        for i in range(5):
            frac = i / 4
            y = bottom - frac * (bottom - top)
            line([left, y, right, y], "#2a3547")
            value = ymin + frac * (ymax - ymin)
            text(left - 8, y + 3, f"{value:.2g}", anchor="end", size=9)
            x = left + frac * (right - left)
            text(x, bottom + 17, f"{xmin + frac * (xmax - xmin):.0f}", size=9)
        text(width / 2, height - 9, self.xlabel, size=9)
        for index, (name, color, values) in enumerate(self.series):
            # Bound canvas item count while preserving the underlying data/export.
            xy = []
            for x, y in values:
                xy.extend((left + (x - xmin) / (xmax - xmin) * (right - left),
                           bottom - (y - ymin) / (ymax - ymin) * (bottom - top)))
            if len(xy) >= 4:
                line(xy, color, 2)
            elif xy:
                line([xy[0] - 2, xy[1], xy[0] + 2, xy[1]], color, 4)
            text(left + index * 85, height - 28, name, color, 9, "start")
        return out

    def redraw(self):
        self.delete("all")
        for primitive in self.primitives(self.winfo_width(), self.winfo_height()):
            if primitive[0] == "line":
                _, coords, color, width = primitive
                self.create_line(*coords, fill=color, width=width)
            else:
                _, (x, y), value, color, size, anchor = primitive
                self.create_text(x, y, text=value, fill=color, font=("Arial", size),
                                 anchor={"start": "w", "end": "e", "middle": "center"}[anchor])


def fill_charts(charts, history, tr=None):
    t = tr or (lambda key: {"legend_win": "Win", "legend_draw": "Draw",
                           "legend_loss": "Loss"}.get(key, key))
    def series(key):
        return [(row["episode"], row[key]) for row in history]
    charts[0].set_data([("TD MSE", ACCENT, series("td_mse"))])
    charts[1].set_data([(t("legend_win"), ACCENT, series("win_rate")),
                        (t("legend_draw"), BLUE, series("draw_rate")),
                        (t("legend_loss"), RED, series("loss_rate"))])
    charts[2].set_data([("Epsilon", BLUE, series("epsilon"))])
    charts[3].set_data([((tr("axis_moves") if tr else "Moves"), ACCENT, series("length"))])


def export_svg(charts, path):
    width, height = 1100, 720
    pieces = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
              f'<rect width="100%" height="100%" fill="{PANEL}"/>']
    for index, chart in enumerate(charts):
        ox, oy = (index % 2) * 550, (index // 2) * 360
        pieces.append(f'<g transform="translate({ox},{oy})">')
        for item in chart.primitives(550, 360):
            if item[0] == "line":
                _, coords, color, stroke = item
                pts = " ".join(f"{coords[i]:.2f},{coords[i+1]:.2f}" for i in range(0, len(coords), 2))
                pieces.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{stroke}"/>')
            else:
                _, (x, y), value, color, size, anchor = item
                pieces.append(f'<text x="{x}" y="{y}" fill="{color}" font-family="Arial,sans-serif" font-size="{size*1.3}" text-anchor="{anchor}" dominant-baseline="middle">{escape(str(value))}</text>')
        pieces.append('</g>')
    pieces.append('</svg>')
    Path(path).write_text("\n".join(pieces), encoding="utf-8")
