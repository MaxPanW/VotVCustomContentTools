#!/usr/bin/env python3
# VotV Poster Square Generator — transparent square PNG canvas utility
# Python 3.9+; Pillow is installed automatically by START_GENERATOR.bat if needed.

import os
import sys
import math
import hashlib
import random
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from votv_theme import apply_votv_theme, polish_votv_widgets

try:
    from PIL import Image, ImageTk
except ImportError:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        "Pillow is missing",
        "Pillow could not be loaded.\n\nClose the application and run START_GENERATOR.bat again."
    )
    raise

APP_TITLE = "VotV Poster Square Generator"
PREVIEW_SIZE = 320
IMAGE_TYPES = [
    ("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff *.gif"),
    ("PNG", "*.png"),
    ("All files", "*.*"),
]

POSITIONS = {
    "Center": (0.5, 0.5),
    "Top center": (0.5, 0.0),
    "Bottom center": (0.5, 1.0),
    "Center left": (0.0, 0.5),
    "Center right": (1.0, 0.5),
    "Top left": (0.0, 0.0),
    "Top right": (1.0, 0.0),
    "Bottom left": (0.0, 1.0),
    "Bottom right": (1.0, 1.0),
}


def default_votv_folder():
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        home = os.path.expanduser("~")
        local = os.path.join(home, "AppData", "Local")
    return os.path.join(local, "VotV", "Assets", "posters")


def output_side(image, resolution):
    if resolution == "Auto (long side)":
        return max(image.size)
    return int(resolution)


def stable_seed(path):
    """Return a stable per-source seed so decorations stay consistent across runs."""
    digest = hashlib.sha256(os.path.abspath(path).encode("utf-8", errors="replace")).digest()
    return int.from_bytes(digest[:8], "big")


def apply_crumple_texture(image, strength, seed):
    """Apply subtle procedural fold shading without changing transparent pixels."""
    from PIL import ImageChops, ImageDraw, ImageFilter

    strength = max(0, min(100, int(strength)))
    if strength <= 0:
        return image

    width, height = image.size
    small_scale = min(1.0, 320.0 / max(width, height))
    sw = max(40, int(round(width * small_scale)))
    sh = max(40, int(round(height * small_scale)))
    rng = random.Random(seed ^ 0x5A17C3)

    texture = Image.new("L", (sw, sh))
    texture.putdata([rng.randint(78, 178) for _ in range(sw * sh)])
    draw = ImageDraw.Draw(texture)
    fold_count = max(7, int(8 + strength * 0.20))
    for _ in range(fold_count):
        x0, y0 = rng.randrange(sw), rng.randrange(sh)
        x1 = max(0, min(sw - 1, x0 + rng.randint(-sw // 2, sw // 2)))
        y1 = max(0, min(sh - 1, y0 + rng.randint(-sh // 2, sh // 2)))
        points = [(x0, y0)]
        for part in (1, 2, 3):
            t = part / 4
            px = int(x0 + (x1 - x0) * t + rng.randint(-max(2, sw // 18), max(2, sw // 18)))
            py = int(y0 + (y1 - y0) * t + rng.randint(-max(2, sh // 18), max(2, sh // 18)))
            points.append((max(0, min(sw - 1, px)), max(0, min(sh - 1, py))))
        points.append((x1, y1))
        # A dark crease paired with a faint offset highlight produces paper-like relief.
        draw.line(points, fill=rng.randint(4, 24), width=rng.choice((1, 1, 2)))
        highlights = [(max(0, min(sw - 1, x + 1)), max(0, min(sh - 1, y + 1))) for x, y in points]
        draw.line(highlights, fill=rng.randint(226, 250), width=1)

    blur_radius = max(0.5, min(width, height) / 450.0)
    texture = texture.resize((width, height), Image.Resampling.BICUBIC).filter(
        ImageFilter.GaussianBlur(radius=blur_radius)
    )
    base_alpha = image.getchannel("A")
    dark_alpha = texture.point(lambda value: min(36, int(max(0, 130 - value) * strength * 0.68 / 130)))
    light_alpha = texture.point(lambda value: min(26, int(max(0, value - 126) * strength * 0.48 / 129)))
    dark_alpha = ImageChops.multiply(dark_alpha, base_alpha)
    light_alpha = ImageChops.multiply(light_alpha, base_alpha)

    shadow = Image.new("RGBA", image.size, (8, 7, 5, 0))
    shadow.putalpha(dark_alpha)
    highlight = Image.new("RGBA", image.size, (255, 250, 235, 0))
    highlight.putalpha(light_alpha)
    result = Image.alpha_composite(image, shadow)
    return Image.alpha_composite(result, highlight)


def make_tape_patch(length, thickness, style, rng):
    """Create a small translucent masking/clear-tape strip with subtle surface marks."""
    from PIL import ImageDraw

    if style == "Clear tape":
        base = (214, 229, 226, 92)
        edge = (245, 250, 246, 92)
        stripe = (255, 255, 255, 82)
    else:
        base = (223, 200, 151, 184)
        edge = (137, 113, 71, 100)
        stripe = (255, 240, 205, 78)

    patch = Image.new("RGBA", (length, thickness), base)
    draw = ImageDraw.Draw(patch)
    draw.rectangle((0, 0, length - 1, thickness - 1), outline=edge, width=max(1, thickness // 48))
    # Faint parallel fibres/highlights make the tape read as a material, not a flat bar.
    for _ in range(max(2, length // 24)):
        x = rng.randrange(max(1, length))
        draw.line((x, 2, x, max(2, thickness - 3)), fill=stripe, width=1)
    for _ in range(max(3, length // 10)):
        x = rng.randrange(max(1, length))
        y = rng.randrange(max(1, thickness))
        draw.point((x, y), fill=(255, 250, 230, 40) if style != "Clear tape" else (255, 255, 255, 45))
    return patch


def paste_center(destination, overlay, center_x, center_y):
    """Alpha-composite an overlay centred at a point; clip safely to the canvas."""
    left = int(round(center_x - overlay.width / 2))
    top = int(round(center_y - overlay.height / 2))
    src_left = max(0, -left)
    src_top = max(0, -top)
    src_right = min(overlay.width, destination.width - left)
    src_bottom = min(overlay.height, destination.height - top)
    if src_right <= src_left or src_bottom <= src_top:
        return
    piece = overlay.crop((src_left, src_top, src_right, src_bottom))
    destination.alpha_composite(piece, (max(0, left), max(0, top)))


def make_square(
    image_path, resolution, scale_percent, position, rotation_degrees=0,
    white_border=False, border_percent=4, crumple=False, crumple_strength=35,
    tape_mode="None", tape_style="Masking tape", sticker_paths=None,
    sticker_layout="Corners", sticker_size_percent=12,
):
    """Create a square RGBA poster with optional paper, tape, and PNG sticker effects."""
    from PIL import Image, ImageDraw

    with Image.open(image_path) as source:
        source.load()
        original = source.size
        rgba = source.convert("RGBA")

    side = max(1, int(output_side(rgba, resolution)))
    frac = max(1, int(round(side * float(scale_percent) / 100.0)))
    max_original = max(rgba.size)
    if white_border:
        estimated_border = max(1, int(round(frac * min(rgba.size) / max_original * float(border_percent) / 100.0)))
        content_limit = max(1, frac - 2 * estimated_border)
    else:
        content_limit = frac
    ratio = min(content_limit / max_original, 1.0) if resolution.startswith(("Auto", "Авто")) else content_limit / max_original
    new_w = max(1, int(round(rgba.width * ratio)))
    new_h = max(1, int(round(rgba.height * ratio)))
    if (new_w, new_h) != rgba.size:
        rgba = rgba.resize((new_w, new_h), Image.Resampling.LANCZOS)

    border_px = 0
    if white_border:
        border_px = max(1, int(round(min(rgba.size) * float(border_percent) / 100.0)))
        paper = Image.new("RGBA", (rgba.width + 2 * border_px, rgba.height + 2 * border_px), (255, 255, 255, 255))
        paper.alpha_composite(rgba, (border_px, border_px))
    else:
        paper = rgba.copy()

    seed = stable_seed(image_path)
    if crumple and int(crumple_strength) > 0:
        paper = apply_crumple_texture(paper, crumple_strength, seed)

    stickers = [p for p in (sticker_paths or []) if p and os.path.isfile(p)]
    tape_enabled = tape_mode != "None" and tape_mode != "Нет"
    sticker_target = max(1, int(round(min(paper.size) * float(sticker_size_percent) / 100.0))) if stickers else 0
    tape_length = max(16, int(round(min(paper.size) * 0.16))) if tape_enabled else 0
    padding = max(
        int(round(min(paper.size) * 0.095)) if tape_enabled else 0,
        int(round(sticker_target * 0.72)) if stickers else 0,
    )
    if padding:
        canvas = Image.new("RGBA", (paper.width + padding * 2, paper.height + padding * 2), (0, 0, 0, 0))
        canvas.alpha_composite(paper, (padding, padding))
    else:
        canvas = paper.copy()

    if tape_enabled:
        rng = random.Random(seed ^ 0x71A9E)
        corners = [
            ("Top left", padding, padding, -38),
            ("Top right", padding + paper.width, padding, 38),
            ("Bottom right", padding + paper.width, padding + paper.height, -38),
            ("Bottom left", padding, padding + paper.height, 38),
        ]
        if tape_mode == "Top corners":
            selected = corners[:2]
        elif tape_mode == "Four corners":
            selected = corners
        else:  # Random 2–4 corners
            selected = rng.sample(corners, rng.choice((2, 3, 4)))
        for _name, cx, cy, base_angle in selected:
            patch = make_tape_patch(tape_length, max(8, int(round(min(paper.size) * 0.055))), tape_style, rng)
            patch = patch.rotate(base_angle + rng.uniform(-12, 12), resample=Image.Resampling.BICUBIC, expand=True)
            paste_center(canvas, patch, cx, cy)

    if stickers:
        rng = random.Random(seed ^ 0xC0570)
        corner_points = [
            (padding + paper.width * 0.075, padding + paper.height * 0.075),
            (padding + paper.width * 0.925, padding + paper.height * 0.075),
            (padding + paper.width * 0.925, padding + paper.height * 0.925),
            (padding + paper.width * 0.075, padding + paper.height * 0.925),
        ]
        rng.shuffle(corner_points)
        for index, sticker_path in enumerate(stickers):
            try:
                with Image.open(sticker_path) as sticker_source:
                    sticker_source.load()
                    sticker = sticker_source.convert("RGBA")
            except Exception:
                continue
            sticker_ratio = sticker_target / max(sticker.size)
            sticker = sticker.resize(
                (max(1, int(round(sticker.width * sticker_ratio))), max(1, int(round(sticker.height * sticker_ratio)))),
                Image.Resampling.LANCZOS,
            )
            if sticker_layout == "Random edge positions":
                edge = rng.choice(("top", "right", "bottom", "left"))
                t = rng.uniform(0.18, 0.82)
                if edge == "top":
                    cx, cy = padding + paper.width * t, padding + paper.height * 0.07
                elif edge == "bottom":
                    cx, cy = padding + paper.width * t, padding + paper.height * 0.93
                elif edge == "left":
                    cx, cy = padding + paper.width * 0.07, padding + paper.height * t
                else:
                    cx, cy = padding + paper.width * 0.93, padding + paper.height * t
            else:
                cx, cy = corner_points[index % len(corner_points)]
            sticker = sticker.rotate(rng.uniform(-22, 22), resample=Image.Resampling.BICUBIC, expand=True)
            paste_center(canvas, sticker, cx, cy)

    angle = float(rotation_degrees) % 360.0
    if abs(angle) > 1e-6:
        canvas = canvas.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)

    if canvas.width > side or canvas.height > side:
        fit_ratio = min(side / canvas.width, side / canvas.height)
        canvas = canvas.resize(
            (max(1, int(round(canvas.width * fit_ratio))), max(1, int(round(canvas.height * fit_ratio)))),
            Image.Resampling.LANCZOS,
        )

    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    ax, ay = POSITIONS.get(position, (0.5, 0.5))
    x = int(round((side - canvas.width) * ax))
    y = int(round((side - canvas.height) * ay))
    square.alpha_composite(canvas, (x, y))
    return square, {
        "original": original,
        "output": (side, side),
        "content": canvas.size,
        "offset": (x, y),
        "rotation": float(rotation_degrees),
        "white_border": bool(white_border),
        "border_px": border_px,
        "crumple": bool(crumple and int(crumple_strength) > 0),
        "tape_mode": tape_mode,
        "sticker_count": len(stickers),
    }

class PosterGenerator(tk.Tk):
    def __init__(self):
        super().__init__()
        apply_votv_theme(self)
        self.title(APP_TITLE)
        self.geometry("1120x960")
        self.minsize(980, 870)
        self.files = []
        self.sticker_paths = []
        self.preview_photo = None
        self.preview_image_path = None
        self._build_ui()
        polish_votv_widgets(self)
        self._update_preview_placeholder()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self, padding=(16, 14, 16, 6))
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text="VotV Poster Square Generator", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(
            header,
            text="Places portrait or landscape images on a square 1:1 PNG canvas while preserving proportions and transparent margins.",
        ).pack(anchor="w", pady=(4, 0))

        body = ttk.Frame(self, padding=(16, 8, 16, 12))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        left = ttk.Frame(body)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)

        file_header = ttk.Frame(left)
        file_header.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ttk.Label(file_header, text="Images", font=("Segoe UI", 11, "bold")).pack(side="left")
        ttk.Button(file_header, text="＋ Add", command=self.add_files).pack(side="right")

        list_frame = ttk.Frame(left)
        list_frame.grid(row=1, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        self.file_list = tk.Listbox(list_frame, selectmode=tk.EXTENDED, activestyle="dotbox", font=("Segoe UI", 10), height=8)
        self.file_list.grid(row=0, column=0, sticky="nsew")
        self.file_list.bind("<<ListboxSelect>>", self.on_select)
        yscroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.file_list.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        self.file_list.configure(yscrollcommand=yscroll.set)
        list_buttons = ttk.Frame(left)
        list_buttons.grid(row=2, column=0, sticky="ew", pady=(6, 12))
        ttk.Button(list_buttons, text="Remove selected", command=self.remove_selected).pack(side="left")
        ttk.Button(list_buttons, text="Clear list", command=self.clear_files).pack(side="left", padx=(6, 0))

        settings = ttk.LabelFrame(left, text="Settings", padding=10)
        settings.grid(row=3, column=0, sticky="ew")
        settings.columnconfigure(1, weight=1)

        ttk.Label(settings, text="Canvas size:").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=4)
        self.resolution_var = tk.StringVar(value="Auto (long side)")
        resolution_box = ttk.Combobox(
            settings, textvariable=self.resolution_var, state="readonly", width=27,
            values=("Auto (long side)", "512", "1024", "2048", "4096")
        )
        resolution_box.grid(row=0, column=1, sticky="ew", pady=4)
        resolution_box.bind("<<ComboboxSelected>>", lambda _e: self.refresh_preview())

        ttk.Label(settings, text="Artwork size:").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(7, 0))
        scale_row = ttk.Frame(settings)
        scale_row.grid(row=1, column=1, sticky="ew", pady=(7, 0))
        scale_row.columnconfigure(0, weight=1)
        self.scale_var = tk.IntVar(value=100)
        self.scale_slider = ttk.Scale(scale_row, from_=30, to=100, variable=self.scale_var, command=self.on_scale)
        self.scale_slider.grid(row=0, column=0, sticky="ew")
        self.scale_label = ttk.Label(scale_row, text="100%", width=5, anchor="e")
        self.scale_label.grid(row=0, column=1, padx=(8, 0))

        ttk.Label(settings, text="Position on canvas:").grid(row=2, column=0, sticky="w", padx=(0, 10), pady=(8, 4))
        self.position_var = tk.StringVar(value="Center")
        position_box = ttk.Combobox(settings, textvariable=self.position_var, state="readonly", values=tuple(POSITIONS.keys()))
        position_box.grid(row=2, column=1, sticky="ew", pady=(8, 4))
        position_box.bind("<<ComboboxSelected>>", lambda _e: self.refresh_preview())

        ttk.Label(settings, text="Rotation:").grid(row=3, column=0, sticky="w", padx=(0, 10), pady=(8, 0))
        rotation_row = ttk.Frame(settings)
        rotation_row.grid(row=3, column=1, sticky="ew", pady=(8, 0))
        rotation_row.columnconfigure(0, weight=1)
        self.rotation_var = tk.DoubleVar(value=0.0)
        self.rotation_slider = ttk.Scale(
            rotation_row, from_=-45, to=45, variable=self.rotation_var, command=self.on_rotation
        )
        self.rotation_slider.grid(row=0, column=0, sticky="ew")
        self.rotation_label = ttk.Label(rotation_row, text="0°", width=6, anchor="e")
        self.rotation_label.grid(row=0, column=1, padx=(8, 0))

        ttk.Label(
            settings,
            text="Margins around the artwork will be fully transparent. Rotation is measured in degrees: negative values rotate clockwise, positive values counterclockwise. The artwork may be scaled down slightly after rotation to prevent clipping.",
            wraplength=490,
            foreground="#555555",
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(5, 0))

        output = ttk.LabelFrame(left, text="Output location", padding=10)
        output.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        output.columnconfigure(0, weight=1)
        self.output_var = tk.StringVar(value=default_votv_folder())
        self.output_entry = ttk.Entry(output, textvariable=self.output_var)
        self.output_entry.grid(row=0, column=0, sticky="ew")
        ttk.Button(output, text="Browse…", command=self.choose_output).grid(row=0, column=1, padx=(6, 0))
        ttk.Button(output, text="VotV folder", command=self.set_votv_output).grid(row=0, column=2, padx=(6, 0))

        self.convert_button = ttk.Button(left, text="CREATE SQUARE PNGS", command=self.convert_all, style="VotV.Primary.TButton")
        self.convert_button.grid(row=5, column=0, sticky="ew", pady=(12, 0), ipady=7)
        self.status_var = tk.StringVar(value="Add one or more images.")
        ttk.Label(left, textvariable=self.status_var, wraplength=600).grid(row=6, column=0, sticky="w", pady=(7, 0))

        right = ttk.LabelFrame(body, text="Output preview", padding=12)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        self.preview_canvas = tk.Canvas(right, width=PREVIEW_SIZE, height=PREVIEW_SIZE, highlightthickness=1, highlightbackground="#888888", bg="#cccccc")
        self.preview_canvas.grid(row=0, column=0, sticky="n", pady=(2, 10))
        self.preview_info = ttk.Label(right, text="Select an image to preview.", justify="left", wraplength=340)
        self.preview_info.grid(row=1, column=0, sticky="ew")
        ttk.Label(
            right,
            text="The checkerboard is preview-only. Margins in the exported PNG are transparent. Paper effects and stickers are applied to every selected image.",
            wraplength=340,
            foreground="#555555",
        ).grid(row=2, column=0, sticky="w", pady=(8, 0))

        effects = ttk.LabelFrame(right, text="Paper effects & decorations", padding=8)
        effects.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        effects.columnconfigure(1, weight=1)

        self.border_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(effects, text="White paper border", variable=self.border_var, command=self.refresh_preview).grid(row=0, column=0, sticky="w", pady=2)
        self.border_slider = ttk.Scale(effects, from_=1, to=10, command=self.on_border_width)
        self.border_slider.grid(row=0, column=1, sticky="ew", padx=(8, 4))
        self.border_label = ttk.Label(effects, text="4%", width=4, anchor="e")
        self.border_label.grid(row=0, column=2, sticky="e")
        self.border_slider.set(4)

        self.crumple_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(effects, text="Crumpled paper texture", variable=self.crumple_var, command=self.refresh_preview).grid(row=1, column=0, sticky="w", pady=2)
        self.crumple_slider = ttk.Scale(effects, from_=0, to=100, command=self.on_crumple_strength)
        self.crumple_slider.grid(row=1, column=1, sticky="ew", padx=(8, 4))
        self.crumple_label = ttk.Label(effects, text="35%", width=4, anchor="e")
        self.crumple_label.grid(row=1, column=2, sticky="e")
        self.crumple_slider.set(35)

        ttk.Label(effects, text="Tape corners:").grid(row=2, column=0, sticky="w", pady=2)
        self.tape_mode_var = tk.StringVar(value="None")
        tape_mode_box = ttk.Combobox(effects, textvariable=self.tape_mode_var, state="readonly", values=("None", "Top corners", "Four corners", "Random 2–4 corners"))
        tape_mode_box.grid(row=2, column=1, columnspan=2, sticky="ew", pady=2)
        tape_mode_box.bind("<<ComboboxSelected>>", lambda _e: self.refresh_preview())

        ttk.Label(effects, text="Tape material:").grid(row=3, column=0, sticky="w", pady=2)
        self.tape_style_var = tk.StringVar(value="Masking tape")
        tape_style_box = ttk.Combobox(effects, textvariable=self.tape_style_var, state="readonly", values=("Masking tape", "Clear tape"))
        tape_style_box.grid(row=3, column=1, columnspan=2, sticky="ew", pady=2)
        tape_style_box.bind("<<ComboboxSelected>>", lambda _e: self.refresh_preview())

        sticker_row = ttk.Frame(effects)
        sticker_row.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(4, 2))
        ttk.Button(sticker_row, text="＋ Add sticker PNGs", command=self.add_stickers).pack(side="left")
        ttk.Button(sticker_row, text="Clear", command=self.clear_stickers, style="VotV.Danger.TButton").pack(side="left", padx=(5, 8))
        self.sticker_count_var = tk.StringVar(value="No stickers")
        ttk.Label(sticker_row, textvariable=self.sticker_count_var, style="VotV.Muted.TLabel").pack(side="left")

        ttk.Label(effects, text="Sticker placement:").grid(row=5, column=0, sticky="w", pady=2)
        self.sticker_layout_var = tk.StringVar(value="Corners")
        sticker_layout_box = ttk.Combobox(effects, textvariable=self.sticker_layout_var, state="readonly", values=("Corners", "Random edge positions"))
        sticker_layout_box.grid(row=5, column=1, columnspan=2, sticky="ew", pady=2)
        sticker_layout_box.bind("<<ComboboxSelected>>", lambda _e: self.refresh_preview())

        ttk.Label(effects, text="Sticker size:").grid(row=6, column=0, sticky="w", pady=2)
        self.sticker_size_slider = ttk.Scale(effects, from_=5, to=22, command=self.on_sticker_size)
        self.sticker_size_slider.grid(row=6, column=1, sticky="ew", padx=(8, 4))
        self.sticker_size_label = ttk.Label(effects, text="12%", width=4, anchor="e")
        self.sticker_size_label.grid(row=6, column=2, sticky="e")
        self.sticker_size_slider.set(12)
        ttk.Label(effects, text="Effects are optional. Sticker PNGs with transparent backgrounds work best.", wraplength=340, style="VotV.Muted.TLabel").grid(row=7, column=0, columnspan=3, sticky="w", pady=(4, 0))

    def add_files(self):
        paths = filedialog.askopenfilenames(title="Select poster images", filetypes=IMAGE_TYPES)
        if not paths:
            return
        added = 0
        for p in paths:
            full = os.path.abspath(p)
            if full not in self.files:
                try:
                    with Image.open(full) as im:
                        im.verify()
                    self.files.append(full)
                    self.file_list.insert(tk.END, os.path.basename(full))
                    added += 1
                except Exception as exc:
                    messagebox.showwarning("Could not open image", f"{os.path.basename(full)}\n\n{exc}")
        if added and self.file_list.size() > 0:
            self.file_list.selection_clear(0, tk.END)
            self.file_list.selection_set(0)
            self.file_list.activate(0)
            self.preview_image_path = self.files[0]
        self.status_var.set(f"Images in list: {len(self.files)}.")
        self.refresh_preview()

    def remove_selected(self):
        indexes = list(self.file_list.curselection())
        for i in reversed(indexes):
            self.file_list.delete(i)
            del self.files[i]
        self.preview_image_path = self.files[0] if self.files else None
        self.status_var.set(f"Images in list: {len(self.files)}.")
        self.refresh_preview()

    def clear_files(self):
        self.files.clear()
        self.file_list.delete(0, tk.END)
        self.preview_image_path = None
        self.status_var.set("List cleared.")
        self.refresh_preview()

    def on_select(self, _event=None):
        selected = self.file_list.curselection()
        if selected:
            self.preview_image_path = self.files[selected[0]]
            self.refresh_preview()

    def on_scale(self, _value=None):
        self.scale_label.configure(text=f"{int(self.scale_var.get())}%")
        self.refresh_preview()

    def on_rotation(self, value=None):
        angle = int(round(float(self.rotation_var.get())))
        self.rotation_label.configure(text=f"{angle:+d}°" if angle else "0°")
        self.refresh_preview()

    def on_border_width(self, value=None):
        self.border_label.configure(text=f"{int(round(float(self.border_slider.get())))}%")
        self.refresh_preview()

    def on_crumple_strength(self, value=None):
        self.crumple_label.configure(text=f"{int(round(float(self.crumple_slider.get())))}%")
        self.refresh_preview()

    def on_sticker_size(self, value=None):
        self.sticker_size_label.configure(text=f"{int(round(float(self.sticker_size_slider.get())))}%")
        self.refresh_preview()

    def add_stickers(self):
        paths = filedialog.askopenfilenames(
            title="Select decorative sticker images (transparent PNG recommended)",
            filetypes=[("PNG sticker images", "*.png"), ("Images", "*.png *.webp *.tif *.tiff"), ("All files", "*.*")],
        )
        for path in paths:
            full = os.path.abspath(path)
            if full not in self.sticker_paths:
                try:
                    with Image.open(full) as image:
                        image.verify()
                    self.sticker_paths.append(full)
                except Exception as exc:
                    messagebox.showwarning("Could not open sticker", f"{os.path.basename(full)}\n\n{exc}")
        self.sticker_count_var.set(f"{len(self.sticker_paths)} sticker(s)" if self.sticker_paths else "No stickers")
        self.refresh_preview()

    def clear_stickers(self):
        self.sticker_paths.clear()
        self.sticker_count_var.set("No stickers")
        self.refresh_preview()

    def effect_options(self):
        return {
            "white_border": bool(self.border_var.get()),
            "border_percent": int(round(self.border_slider.get())),
            "crumple": bool(self.crumple_var.get()),
            "crumple_strength": int(round(self.crumple_slider.get())),
            "tape_mode": self.tape_mode_var.get(),
            "tape_style": self.tape_style_var.get(),
            "sticker_paths": list(self.sticker_paths),
            "sticker_layout": self.sticker_layout_var.get(),
            "sticker_size_percent": int(round(self.sticker_size_slider.get())),
        }

    def choose_output(self):
        selected = filedialog.askdirectory(title="Select a folder for the output PNG files", initialdir=self.output_var.get() if os.path.isdir(self.output_var.get()) else os.path.expanduser("~"))
        if selected:
            self.output_var.set(selected)

    def set_votv_output(self):
        self.output_var.set(default_votv_folder())

    def _update_preview_placeholder(self):
        self.preview_canvas.delete("all")
        cell = 18
        for y in range(0, PREVIEW_SIZE, cell):
            for x in range(0, PREVIEW_SIZE, cell):
                fill = "#eeeeee" if ((x // cell) + (y // cell)) % 2 == 0 else "#bbbbbb"
                self.preview_canvas.create_rectangle(x, y, x + cell, y + cell, fill=fill, outline=fill)
        self.preview_canvas.create_text(PREVIEW_SIZE / 2, PREVIEW_SIZE / 2, text="PREVIEW", fill="#555555", font=("Segoe UI", 11, "bold"))

    def refresh_preview(self):
        if not self.preview_image_path or not os.path.isfile(self.preview_image_path):
            self._update_preview_placeholder()
            self.preview_info.configure(text="Select an image to preview.")
            return
        try:
            result, meta = make_square(
                self.preview_image_path,
                self.resolution_var.get(),
                int(self.scale_var.get()),
                self.position_var.get(),
                int(round(self.rotation_var.get())),
                **self.effect_options(),
            )
            # Make a checkerboard at preview size, not full texture size (keeps slider responsive).
            display = result.copy()
            display.thumbnail((PREVIEW_SIZE, PREVIEW_SIZE), Image.Resampling.LANCZOS)
            check = Image.new("RGBA", display.size, (230, 230, 230, 255))
            from PIL import ImageDraw
            draw = ImageDraw.Draw(check)
            cell = max(8, PREVIEW_SIZE // 12)
            for y in range(0, display.height, cell):
                for x in range(0, display.width, cell):
                    if ((x // cell) + (y // cell)) % 2:
                        draw.rectangle((x, y, min(x + cell - 1, display.width - 1), min(y + cell - 1, display.height - 1)), fill=(185, 185, 185, 255))
            check.alpha_composite(display)
            display_rgb = check.convert("RGB")
            # Center in the preview canvas.
            canvas_img = Image.new("RGB", (PREVIEW_SIZE, PREVIEW_SIZE), (210, 210, 210))
            ox = (PREVIEW_SIZE - display_rgb.width) // 2
            oy = (PREVIEW_SIZE - display_rgb.height) // 2
            canvas_img.paste(display_rgb, (ox, oy))
            self.preview_photo = ImageTk.PhotoImage(canvas_img)
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(0, 0, image=self.preview_photo, anchor="nw")
            o_w, o_h = meta["original"]
            c_w, c_h = meta["content"]
            side = meta["output"][0]
            self.preview_info.configure(
                text=(f"File: {os.path.basename(self.preview_image_path)}\n"
                      f"Source: {o_w} × {o_h}\n"
                      f"Output: {side} × {side} PNG\n"
                      f"Artwork bounds: {c_w} × {c_h}\n"
                      f"Rotation: {int(round(meta['rotation']))}°\n"
                      f"Effects: {'border ' if meta['white_border'] else ''}{'crumple ' if meta['crumple'] else ''}{'tape ' if meta['tape_mode'] != 'None' else ''}{meta['sticker_count']} sticker(s)\n"
                      f"Transparent margins: yes"))
            self.status_var.set(f"Preview: {side} × {side}; the source file is unchanged.")
        except Exception as exc:
            self._update_preview_placeholder()
            self.preview_info.configure(text=f"Could not create preview:\n{exc}")

    def convert_all(self):
        if not self.files:
            messagebox.showinfo("No images selected", "Add one or more images first.")
            return
        out_dir = os.path.abspath(os.path.expandvars(os.path.expanduser(self.output_var.get().strip())))
        if not out_dir:
            messagebox.showerror("No output folder", "Select an output folder.")
            return
        resolutions = self.resolution_var.get()
        scale = int(self.scale_var.get())
        position = self.position_var.get()
        rotation = int(round(self.rotation_var.get()))

        planned = []
        for src in self.files:
            stem = os.path.splitext(os.path.basename(src))[0]
            if stem.lower().endswith("_votv"):
                output_name = stem + ".png"
            else:
                output_name = stem + "_votv.png"
            planned.append((src, os.path.join(out_dir, output_name)))

        exists = [dest for _, dest in planned if os.path.exists(dest)]
        if exists:
            sample = "\n".join(os.path.basename(p) for p in exists[:5])
            suffix = f"\n...and {len(exists) - 5} more" if len(exists) > 5 else ""
            if not messagebox.askyesno("Overwrite existing files?", f"These files already exist:\n{sample}{suffix}\n\nOverwrite them? The source files will not be changed."):
                return

        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception as exc:
            messagebox.showerror("Output folder error", f"Could not create folder:\n{out_dir}\n\n{exc}")
            return

        successes = []
        failures = []
        self.convert_button.configure(state="disabled")
        self.update_idletasks()
        try:
            for src, dest in planned:
                try:
                    image, _meta = make_square(src, resolutions, scale, position, rotation, **self.effect_options())
                    image.save(dest, format="PNG", optimize=True)
                    successes.append((src, dest, image.size))
                except Exception as exc:
                    failures.append((src, str(exc)))
        finally:
            self.convert_button.configure(state="normal")

        self.status_var.set(f"Done: {len(successes)}; errors: {len(failures)}.")
        if successes and not failures:
            message = f"Done! PNG files created: {len(successes)}\n\nFolder:\n{out_dir}"
            if os.path.normcase(out_dir) == os.path.normcase(default_votv_folder()):
                message += "\n\nRestart VotV or refresh the texture list if the posters do not appear."
            messagebox.showinfo("Conversion finished", message)
        else:
            detail = ""
            if failures:
                detail = "\n\nErrors:\n" + "\n".join(f"• {os.path.basename(p)}: {err}" for p, err in failures[:8])
            messagebox.showwarning("Conversion finished with warnings", f"Successful: {len(successes)}\nErrors: {len(failures)}\n\nFolder:\n{out_dir}{detail}")


def main():
    app = PosterGenerator()
    app.mainloop()


if __name__ == "__main__":
    main()
