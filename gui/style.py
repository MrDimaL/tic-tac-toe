import tkinter as tk
from tkinter import ttk

BG = "#0c1018"
PANEL = "#151c29"
CARD = "#1d2738"
FG = "#edf2fc"
MUTED = "#a0aec4"
ACCENT = "#68dfc0"
RED = "#ff4d62"
BLUE = "#4c9bff"


def setup(root):
    root.configure(bg=BG)
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TFrame", background=BG)
    style.configure("Panel.TFrame", background=PANEL)
    style.configure("TLabel", background=BG, foreground=FG, font=("Arial", 11))
    style.configure("TButton", background=CARD, foreground=FG, borderwidth=0,
                    padding=(12, 9), font=("Arial", 11))
    style.map("TButton", background=[("active", "#30415b"), ("disabled", PANEL)],
              foreground=[("disabled", "#617087")])
    style.configure("Accent.TButton", background=ACCENT, foreground="#0b1c1a",
                    font=("Arial", 11, "bold"))
    style.map("Accent.TButton", background=[("active", "#91f4dc"), ("disabled", CARD)])
    style.configure("TCombobox", fieldbackground=CARD, background=CARD,
                    foreground=FG, arrowcolor=FG, padding=5)
    style.map("TCombobox", fieldbackground=[("readonly", CARD)],
              foreground=[("readonly", FG)], selectbackground=[("readonly", CARD)],
              selectforeground=[("readonly", FG)])
    style.configure("TEntry", fieldbackground=CARD, foreground=FG, padding=6)
    style.configure("Horizontal.TProgressbar", background=ACCENT, troughcolor=CARD)
    root.option_add("*TCombobox*Listbox.background", CARD)
    root.option_add("*TCombobox*Listbox.foreground", FG)
    root.option_add("*TCombobox*Listbox.selectBackground", "#30415b")


def label(parent, text="", size=11, color=FG, bold=False, bg=BG, **kw):
    return tk.Label(parent, text=text, bg=bg, fg=color,
                    font=("Arial", size, "bold" if bold else "normal"), **kw)


def button(parent, text, command, accent=False, **kw):
    return ttk.Button(parent, text=text, command=command,
                      style="Accent.TButton" if accent else "TButton", **kw)
