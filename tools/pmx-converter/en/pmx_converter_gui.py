#!/usr/bin/env python3
"""Graphical front-end for pmx2votv_optimized.py."""
from __future__ import annotations
import os
import queue
import re
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from votv_theme import apply_votv_theme, polish_votv_widgets

APP_TITLE = "VotV PMX Converter"
ROOT = Path(__file__).resolve().parent
CONVERTER = ROOT / "pmx2votv_optimized.py"


def printer_dir() -> Path:
    local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(local) / "VotV" / "Assets" / "meshes" / "printer"


def safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_\-]", "_", value).strip("_").lower()
    value = re.sub(r"_+", "_", value)
    return value or "model"


def unused_name(root: Path, base: str) -> str:
    name = safe_name(base)
    candidate = name
    index = 2
    while (root / candidate).exists():
        candidate = f"{name}-{index}"
        index += 1
    return candidate


class ConverterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        apply_votv_theme(self)
        self.title(APP_TITLE)
        self.geometry("1180x900")
        self.minsize(1000, 800)
        self.files: list[str] = []
        self.events: queue.Queue = queue.Queue()
        self.worker: threading.Thread | None = None
        self._build_ui()
        polish_votv_widgets(self)
        self.after(100, self._process_events)

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        header = ttk.Frame(self, padding=(18, 14, 18, 8))
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text=APP_TITLE, font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(header, text="Convert PMX models to OBJ/MTL for the Voices of the Void 3D printer",
                  font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 0))

        body = ttk.Frame(self, padding=(18, 6, 18, 12))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        left = ttk.Frame(body)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)
        files_bar = ttk.Frame(left)
        files_bar.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ttk.Label(files_bar, text="Source models", font=("Segoe UI", 11, "bold")).pack(side="left")
        ttk.Button(files_bar, text="Add PMX files…", command=self.add_files).pack(side="right")
        list_frame = ttk.Frame(left)
        list_frame.grid(row=1, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        self.file_list = tk.Listbox(list_frame, selectmode=tk.EXTENDED, height=7, font=("Consolas", 10))
        self.file_list.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.file_list.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.file_list.configure(yscrollcommand=scroll.set)
        file_actions = ttk.Frame(left)
        file_actions.grid(row=2, column=0, sticky="ew", pady=(6, 10))
        ttk.Button(file_actions, text="Remove selected", command=self.remove_selected).pack(side="left")
        ttk.Button(file_actions, text="Clear list", command=self.clear_files).pack(side="left", padx=(6, 0))

        opts = ttk.LabelFrame(left, text="Conversion settings", padding=10)
        opts.grid(row=3, column=0, sticky="ew")
        opts.columnconfigure(1, weight=1)
        self.name_var = tk.StringVar()
        self.scale_var = tk.StringVar(value="7.625")
        self.height_var = tk.StringVar()
        self.tex_var = tk.StringVar(value="1024")
        self.collider_var = tk.BooleanVar(value=True)
        self.width_var = tk.StringVar(value="32")
        self.depth_var = tk.StringVar(value="24")
        self.flip_var = tk.BooleanVar(value=False)
        self.opaque_var = tk.StringVar()
        self.drop_var = tk.StringVar()

        ttk.Label(opts, text="Model name (optional):").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=4)
        ttk.Entry(opts, textvariable=self.name_var).grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Label(opts, text="Target height, cm (blank = use scale):").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=4)
        ttk.Entry(opts, textvariable=self.height_var, width=12).grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Label(opts, text="Scale factor:").grid(row=2, column=0, sticky="w", padx=(0, 10), pady=4)
        ttk.Entry(opts, textvariable=self.scale_var).grid(row=2, column=1, sticky="ew", pady=4)
        ttk.Label(opts, text="Max texture size:").grid(row=3, column=0, sticky="w", padx=(0, 10), pady=4)
        ttk.Combobox(opts, textvariable=self.tex_var, state="readonly", values=("1024", "2048", "4096", "No downscaling")).grid(row=3, column=1, sticky="ew", pady=4)

        collider = ttk.Frame(opts)
        collider.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(5, 3))
        ttk.Checkbutton(collider, text="Create a simple box collider (UCX)", variable=self.collider_var).pack(side="left")
        dims = ttk.Frame(opts)
        dims.grid(row=5, column=0, columnspan=2, sticky="ew", pady=3)
        ttk.Label(dims, text="Width, cm:").pack(side="left")
        ttk.Entry(dims, textvariable=self.width_var, width=7).pack(side="left", padx=(5, 12))
        ttk.Label(dims, text="Depth, cm:").pack(side="left")
        ttk.Entry(dims, textvariable=self.depth_var, width=7).pack(side="left", padx=(5, 0))

        advanced = ttk.LabelFrame(left, text="Advanced options (optional)", padding=8)
        advanced.grid(row=4, column=0, sticky="ew", pady=(9, 0))
        advanced.columnconfigure(1, weight=1)
        ttk.Label(advanced, text="Drop materials:").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=3)
        ttk.Entry(advanced, textvariable=self.drop_var).grid(row=0, column=1, sticky="ew", pady=3)
        ttk.Label(advanced, text="Make materials opaque:").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=3)
        ttk.Entry(advanced, textvariable=self.opaque_var).grid(row=1, column=1, sticky="ew", pady=3)
        ttk.Checkbutton(advanced, text="Do not flip the Z axis", variable=self.flip_var).grid(row=2, column=0, columnspan=2, sticky="w", pady=(3, 0))

        outbox = ttk.LabelFrame(left, text="Output folder", padding=8)
        outbox.grid(row=5, column=0, sticky="ew", pady=(9, 0))
        outbox.columnconfigure(0, weight=1)
        self.out_var = tk.StringVar(value=str(ROOT / "output"))
        ttk.Entry(outbox, textvariable=self.out_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(outbox, text="Browse…", command=self.choose_output).grid(row=0, column=1, padx=(6, 0))
        ttk.Button(outbox, text="VotV folder", command=lambda: self.out_var.set(str(printer_dir()))).grid(row=0, column=2, padx=(6, 0))
        self.run_button = ttk.Button(left, text="CONVERT MODELS", command=self.start_conversion)
        self.run_button.grid(row=6, column=0, sticky="ew", pady=(10, 0), ipady=7)
        ttk.Label(left, text="When processing multiple files, source filenames are used.\nExisting folders are not overwritten; a suffix is added if a name is already taken.",
                  wraplength=620, foreground="#555555").grid(row=7, column=0, sticky="w", pady=(7, 0))

        right = ttk.LabelFrame(body, text="Log", padding=10)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)
        self.log = tk.Text(right, wrap="word", font=("Consolas", 9), state="disabled", background="#f4f5f7")
        self.log.grid(row=0, column=0, sticky="nsew")
        logscroll = ttk.Scrollbar(right, orient="vertical", command=self.log.yview)
        logscroll.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=logscroll.set)
        self.status = tk.StringVar(value="Add one or more PMX files to process.")
        ttk.Label(right, textvariable=self.status, wraplength=330).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Label(right, text="The GUI requires Python 3.9+ and Pillow. Blender and MMD Tools are not required.", wraplength=330,
                  foreground="#555555").grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def _log(self, text: str):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def add_files(self):
        paths = filedialog.askopenfilenames(title="Select PMX files", filetypes=(("PMX models", "*.pmx"), ("All files", "*.*")))
        for path in paths:
            path = os.path.abspath(path)
            if path not in self.files:
                self.files.append(path)
                self.file_list.insert("end", path)
        self.status.set(f"Files selected: {len(self.files)}")

    def remove_selected(self):
        for i in reversed(self.file_list.curselection()):
            self.file_list.delete(i)
            del self.files[i]
        self.status.set(f"Files selected: {len(self.files)}")

    def clear_files(self):
        self.files.clear()
        self.file_list.delete(0, "end")
        self.status.set("File list cleared.")

    def choose_output(self):
        path = filedialog.askdirectory(title="Select an output folder", initialdir=self.out_var.get() or str(ROOT))
        if path:
            self.out_var.set(path)

    def start_conversion(self):
        if self.worker and self.worker.is_alive():
            return
        if not self.files:
            messagebox.showinfo(APP_TITLE, "Add at least one PMX file before starting.")
            return
        if not CONVERTER.is_file():
            messagebox.showerror(APP_TITLE, f"Converter script not found:\n{CONVERTER}")
            return
        try:
            scale = float(self.scale_var.get().strip())
            if scale <= 0:
                raise ValueError
            height_text = self.height_var.get().strip()
            height = float(height_text) if height_text else None
            if height is not None and height <= 0:
                raise ValueError
            width = float(self.width_var.get().strip())
            depth = float(self.depth_var.get().strip())
            if self.collider_var.get() and (width <= 0 or depth <= 0):
                raise ValueError
        except ValueError:
            messagebox.showerror(APP_TITLE, "Check the scale, target height, and collider dimensions. All numeric values must be greater than zero.")
            return
        output_text = self.out_var.get().strip()
        if not output_text:
            messagebox.showerror(APP_TITLE, "Specify an output folder.")
            return
        output = Path(output_text).expanduser()
        try:
            output.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror(APP_TITLE, f"Could not create the output folder:\n{exc}")
            return

        opts = {
            "files": list(self.files), "output": str(output), "scale": scale, "height": height,
            "width": width, "depth": depth, "collider": self.collider_var.get(),
            "tex": self.tex_var.get(), "flip": self.flip_var.get(), "drop": self.drop_var.get().strip(),
            "opaque": self.opaque_var.get().strip(), "custom_name": self.name_var.get().strip(),
        }
        self.run_button.configure(state="disabled")
        self.status.set("Converting…")
        self._log("=" * 48)
        self._log("Conversion started")
        self.worker = threading.Thread(target=self._worker, args=(opts,), daemon=True)
        self.worker.start()

    def _worker(self, opts):
        ok = 0
        failed = 0
        out_root = Path(opts["output"])
        for index, src in enumerate(opts["files"], start=1):
            p = Path(src)
            base_name = opts["custom_name"] if len(opts["files"]) == 1 and opts["custom_name"] else p.stem
            name = unused_name(out_root, base_name)
            cmd = [sys.executable, "-u", str(CONVERTER), str(p), "--name", name, "--out", str(out_root),
                   "--scale", str(opts["scale"]), "--max-tex", "0" if opts["tex"] == "No downscaling" else opts["tex"]]
            if opts["height"] is not None:
                cmd += ["--height", str(opts["height"])]
            if opts["collider"]:
                cmd += ["--collider", "box", "--collider-width", str(opts["width"]), "--collider-depth", str(opts["depth"])]
            else:
                cmd += ["--collider", "none"]
            if opts["flip"]:
                cmd.append("--no-flip")
            if opts["drop"]:
                cmd += ["--drop", opts["drop"]]
            if opts["opaque"]:
                cmd += ["--opaque", opts["opaque"]]
            self.events.put(("line", f"\n[{index}/{len(opts['files'])}] {p.name}"))
            self.events.put(("line", "Command: " + subprocess.list2cmdline(cmd)))
            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
                assert proc.stdout is not None
                for line in proc.stdout:
                    self.events.put(("line", line.rstrip()))
                code = proc.wait()
                if code == 0:
                    ok += 1
                else:
                    failed += 1
                    self.events.put(("line", f"Error: exit code {code}"))
            except Exception as exc:
                failed += 1
                self.events.put(("line", f"Could not start converter: {exc}"))
        self.events.put(("done", ok, failed, str(out_root)))

    def _process_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "line":
                    self._log(event[1])
                elif event[0] == "done":
                    _, ok, failed, output = event
                    self.run_button.configure(state="normal")
                    self.status.set(f"Done: {ok}; errors: {failed}")
                    self._log(f"\nFinished. Successful: {ok}; errors: {failed}.\nOutput: {output}")
                    messagebox.showinfo(APP_TITLE, f"Conversion complete.\n\nSuccessful: {ok}\nErrors: {failed}\n\nOutput folder:\n{output}")
        except queue.Empty:
            pass
        self.after(100, self._process_events)


if __name__ == "__main__":
    if not CONVERTER.is_file():
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(APP_TITLE, f"{CONVERTER.name} was not found. Place the GUI script next to the converter script.")
        raise SystemExit(1)
    ConverterApp().mainloop()
