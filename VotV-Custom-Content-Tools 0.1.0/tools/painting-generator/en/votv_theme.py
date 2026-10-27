"""Shared VotV-inspired Tk/ttk theme for the custom content tools.

Uses only Tkinter's bundled ttk themes; no third-party GUI package is required.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, font as tkfont

BG = "#050505"
PANEL = "#090909"
PANEL_ALT = "#101010"
BORDER = "#DCDC00"
YELLOW = "#F0F000"
GREEN = "#00D92F"
CYAN = "#00DDE8"
RED = "#F02020"
MAGENTA = "#EC00E8"
WHITE = "#F1F1F1"
MUTED = "#8A8A8A"
DARK_GREEN = "#003D0D"
DARK_YELLOW = "#383800"


def _font_family(root: tk.Misc) -> str:
    """Prefer an installed pixel font; use a readable mono fallback otherwise."""
    try:
        available = set(tkfont.families(root))
    except tk.TclError:
        available = set()
    for candidate in (
        "Pixel Operator", "Pixeloid Sans", "VT323", "Fixedsys",
        "Terminal", "Cascadia Mono", "Consolas", "Courier New",
        "Press Start 2P",
    ):
        if candidate in available:
            return candidate
    return "TkFixedFont"


def apply_votv_theme(root: tk.Tk) -> None:
    """Apply the shared palette and classic VotV-style rectangular controls."""
    family = _font_family(root)
    root._votv_font_family = family
    root.configure(background=BG)

    # Default options for classic Tk widgets, which are still used for lists/logs.
    root.option_add("*Font", (family, 10))
    root.option_add("*Listbox.background", BG)
    root.option_add("*Listbox.foreground", WHITE)
    root.option_add("*Listbox.selectBackground", DARK_GREEN)
    root.option_add("*Listbox.selectForeground", GREEN)
    root.option_add("*Listbox.highlightBackground", BORDER)
    root.option_add("*Text.background", BG)
    root.option_add("*Text.foreground", WHITE)
    root.option_add("*Text.insertBackground", YELLOW)
    root.option_add("*Entry.background", BG)
    root.option_add("*Entry.foreground", WHITE)
    root.option_add("*Entry.insertBackground", YELLOW)

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(".", background=BG, foreground=WHITE, font=(family, 10))
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=WHITE, font=(family, 10))
    style.configure(
        "VotV.Title.TLabel", background=BG, foreground=YELLOW,
        font=(family, 16, "bold"), padding=(0, 0, 0, 2),
    )
    style.configure(
        "VotV.Section.TLabel", background=BG, foreground=YELLOW,
        font=(family, 11, "bold"),
    )
    style.configure(
        "VotV.Muted.TLabel", background=BG, foreground=MUTED,
        font=(family, 9),
    )
    style.configure(
        "VotV.Cyan.TLabel", background=BG, foreground=CYAN,
        font=(family, 10, "bold"),
    )
    style.configure(
        "VotV.Warning.TLabel", background=BG, foreground=YELLOW,
        font=(family, 9),
    )

    style.configure(
        "TLabelframe", background=BG, foreground=YELLOW,
        bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER,
        relief="solid", borderwidth=1, padding=7,
    )
    style.configure(
        "TLabelframe.Label", background=BG, foreground=YELLOW,
        font=(family, 10, "bold"), padding=(4, 0),
    )

    style.configure(
        "TButton", background=BG, foreground=YELLOW,
        bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER,
        relief="solid", borderwidth=1, focusthickness=1,
        focuscolor=CYAN, padding=(9, 5), font=(family, 9, "bold"),
    )
    style.map(
        "TButton",
        background=[("disabled", PANEL), ("pressed", GREEN), ("active", YELLOW)],
        foreground=[("disabled", MUTED), ("pressed", BG), ("active", BG)],
        bordercolor=[("focus", CYAN), ("active", YELLOW)],
    )
    style.configure(
        "VotV.Primary.TButton", background=YELLOW, foreground=BG,
        bordercolor=YELLOW, lightcolor=YELLOW, darkcolor=YELLOW,
        relief="solid", borderwidth=1, padding=(10, 8),
        font=(family, 10, "bold"),
    )
    style.map(
        "VotV.Primary.TButton",
        background=[("disabled", PANEL), ("pressed", GREEN), ("active", GREEN)],
        foreground=[("disabled", MUTED), ("pressed", BG), ("active", BG)],
        bordercolor=[("active", GREEN), ("focus", CYAN)],
    )
    style.configure(
        "VotV.Danger.TButton", background=BG, foreground=RED,
        bordercolor=RED, lightcolor=RED, darkcolor=RED,
        relief="solid", borderwidth=1, padding=(8, 4),
        font=(family, 9, "bold"),
    )
    style.map(
        "VotV.Danger.TButton",
        background=[("pressed", RED), ("active", "#440000")],
        foreground=[("pressed", BG), ("active", "#FF7777")],
        bordercolor=[("active", RED), ("focus", CYAN)],
    )

    style.configure(
        "TEntry", fieldbackground=PANEL, foreground=WHITE,
        insertcolor=YELLOW, bordercolor=BORDER, lightcolor=BORDER,
        darkcolor=BORDER, padding=(5, 5), relief="solid",
    )
    style.map(
        "TEntry",
        fieldbackground=[("disabled", PANEL_ALT), ("focus", "#0D0D00")],
        foreground=[("disabled", MUTED)],
        bordercolor=[("focus", CYAN)],
    )

    style.configure(
        "TCombobox", fieldbackground=PANEL, foreground=YELLOW,
        background=BG, arrowcolor=YELLOW, bordercolor=BORDER,
        lightcolor=BORDER, darkcolor=BORDER, padding=(5, 4),
        selectbackground=DARK_GREEN, selectforeground=GREEN,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", PANEL), ("focus", PANEL)],
        foreground=[("readonly", YELLOW), ("disabled", MUTED)],
        background=[("active", YELLOW), ("pressed", GREEN)],
        arrowcolor=[("active", BG)],
        bordercolor=[("focus", CYAN), ("active", YELLOW)],
    )

    style.configure(
        "TCheckbutton", background=BG, foreground=WHITE,
        indicatorcolor=BG, padding=(2, 3), font=(family, 9),
    )
    style.map(
        "TCheckbutton",
        background=[("active", BG), ("selected", BG)],
        foreground=[("disabled", MUTED), ("selected", GREEN), ("active", YELLOW)],
        indicatorcolor=[("selected", GREEN), ("active", YELLOW)],
    )

    style.configure(
        "TScale", background=BG, troughcolor=DARK_YELLOW,
        bordercolor=BORDER, lightcolor=YELLOW, darkcolor=YELLOW,
        sliderlength=17, relief="flat",
    )
    style.map("TScale", background=[("active", GREEN), ("disabled", PANEL)])

    style.configure(
        "TScrollbar", background="#777700", troughcolor=BG,
        bordercolor=BORDER, arrowcolor=YELLOW, lightcolor=BORDER,
        darkcolor=BORDER, relief="flat", arrowsize=12,
    )
    style.map("TScrollbar", background=[("active", YELLOW), ("pressed", GREEN)])

    style.configure("TSeparator", background="#505050")
    style.configure(
        "TNotebook", background=BG, bordercolor=BORDER, tabmargins=(2, 3, 2, 0),
    )
    style.configure(
        "TNotebook.Tab", background=BG, foreground=YELLOW,
        bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER,
        padding=(10, 5), font=(family, 9, "bold"),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", YELLOW), ("active", "#333300")],
        foreground=[("selected", BG), ("active", WHITE)],
    )
    style.configure(
        "Treeview", background=BG, foreground=WHITE,
        fieldbackground=BG, bordercolor=BORDER, rowheight=25,
        font=(family, 9),
    )
    style.map(
        "Treeview",
        background=[("selected", DARK_GREEN)],
        foreground=[("selected", GREEN)],
    )
    style.configure(
        "Treeview.Heading", background=BG, foreground=YELLOW,
        bordercolor=BORDER, font=(family, 9, "bold"),
    )
    style.configure(
        "TProgressbar", background=GREEN, troughcolor=DARK_YELLOW,
        bordercolor=BORDER, lightcolor=GREEN, darkcolor=GREEN,
    )
    style.configure(
        "Vertical.TScrollbar", background="#777700", troughcolor=BG,
        bordercolor=BORDER, arrowcolor=YELLOW,
    )
    style.configure(
        "Horizontal.TScrollbar", background="#777700", troughcolor=BG,
        bordercolor=BORDER, arrowcolor=YELLOW,
    )


def polish_votv_widgets(root: tk.Misc) -> None:
    """Retheme legacy widgets and select accent styles based on the control role."""
    family = getattr(root, "_votv_font_family", _font_family(root))

    def visit(parent: tk.Misc) -> None:
        for widget in parent.winfo_children():
            try:
                cls = widget.winfo_class()
                if isinstance(widget, tk.Listbox):
                    widget.configure(
                        background=BG, foreground=WHITE,
                        selectbackground=DARK_GREEN, selectforeground=GREEN,
                        highlightbackground=BORDER, highlightcolor=CYAN,
                        highlightthickness=1, borderwidth=1, relief="solid",
                        activestyle="none", font=(family, 10),
                    )
                elif isinstance(widget, tk.Text):
                    widget.configure(
                        background=BG, foreground=WHITE,
                        insertbackground=YELLOW, selectbackground=DARK_GREEN,
                        selectforeground=GREEN, highlightbackground=BORDER,
                        highlightcolor=CYAN, highlightthickness=1,
                        borderwidth=1, relief="solid", font=(family, 9),
                    )
                elif isinstance(widget, tk.Entry):
                    widget.configure(
                        background=PANEL, foreground=WHITE,
                        insertbackground=YELLOW, selectbackground=DARK_GREEN,
                        selectforeground=GREEN, highlightbackground=BORDER,
                        highlightcolor=CYAN, highlightthickness=1,
                        borderwidth=1, relief="solid", font=(family, 10),
                    )
                elif isinstance(widget, tk.Canvas):
                    # Keep canvas content (e.g. checkerboard preview), but use the
                    # thin VotV-style border around it.
                    widget.configure(highlightbackground=BORDER, highlightcolor=CYAN)
                elif isinstance(widget, ttk.Button):
                    label = str(widget.cget("text") or "").strip().lower()
                    if any(token in label for token in ("конвертировать", "создать квадрат", "подготовить картины", "convert models", "create square pngs", "prepare paintings", "start conversion", "convert all")):
                        widget.configure(style="VotV.Primary.TButton")
                    elif any(token in label for token in ("удалить", "убрать выбран", "очистить", "clear list", "remove selected", "clear all", "remove")):
                        widget.configure(style="VotV.Danger.TButton")
                elif isinstance(widget, ttk.Label):
                    label = str(widget.cget("text") or "").strip()
                    low = label.lower()
                    if label in {
                        "VotV PMX Converter", "VotV Poster Square Generator",
                        "VotV Painting Generator", "VotV Poster Generator",
                    }:
                        widget.configure(style="VotV.Title.TLabel")
                    elif any(token in low for token in (
                        "исходные модели", "изображения", "предпросмотр",
                        "source models", "images", "preview", "output preview",
                        "conversion settings", "advanced options", "format & processing",
                        "output folder", "settings", "log", "model conversion",
                    )):
                        widget.configure(style="VotV.Section.TLabel")
                    else:
                        fg = str(widget.cget("foreground") or "").lower()
                        if fg in {"#555", "#555555", "#666", "#666666", "gray", "grey"}:
                            widget.configure(style="VotV.Muted.TLabel", foreground=MUTED)
                        elif fg in {"#9a4a00", "#aa5500", "orange"}:
                            widget.configure(style="VotV.Warning.TLabel", foreground=YELLOW)
                        elif fg in {"#00d9e6", "#00dde8", "#00ffff"}:
                            widget.configure(style="VotV.Cyan.TLabel", foreground=CYAN)
                elif isinstance(widget, tk.Button):
                    label = str(widget.cget("text") or "").strip().lower()
                    danger = any(token in label for token in ("удалить", "очистить", "remove", "clear"))
                    widget.configure(
                        background=BG, foreground=RED if danger else YELLOW,
                        activebackground=RED if danger else YELLOW,
                        activeforeground=BG, borderwidth=1,
                        relief="solid", highlightbackground=RED if danger else BORDER,
                        font=(family, 9, "bold"), padx=8, pady=4,
                    )
            except tk.TclError:
                pass
            visit(widget)

    visit(root)
