#!/usr/bin/env python3
# One-click batch frontend for pmx2votv_optimized.py
# Python 3.8+, Pillow. Designed for Windows, but can be test-run on other OSes.
import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

# Make console/log output predictable on Windows, including non-ASCII file paths.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            pass
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
INPUT_DIR = BASE / "input"
LOG_DIR = BASE / "logs"
SETTINGS_PATH = BASE / "settings.json"
CSV_PATH = BASE / "models.csv"
CONVERTER = BASE / "pmx2votv_optimized.py"
MARKER = ".pmx2votv-managed"


def say(message, log_lines=None):
    print(message, flush=True)
    if log_lines is not None:
        log_lines.append(str(message))


def load_settings():
    defaults = {
        "output_mode": "game",
        "game_printer_dir": "%LOCALAPPDATA%\\VotV\\Assets\\meshes\\printer",
        "local_output_dir": "output",
        "default_height_cm": 0,
        "default_scale": 7.625,
        "collider": "box",
        "collider_width_cm": 32,
        "collider_depth_cm": 24,
        "max_texture_size": 1024,
        "drop_materials": "",
        "opaque_materials": "",
        "cfg_template": "",
        "replace_managed_output": True,
    }
    if SETTINGS_PATH.exists():
        try:
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            defaults.update(data)
        except Exception as exc:
            raise RuntimeError(f"Could not read settings.json: {exc}")
    return defaults


def expand_path(raw):
    value = os.path.expandvars(str(raw))
    # os.path.expandvars only expands %NAME% on Windows; also handle it in tests on other OSes.
    value = re.sub(r"%([^%]+)%", lambda m: os.environ.get(m.group(1), m.group(0)), value)
    return Path(value).expanduser().resolve()


def list_inputs(args_paths):
    found = []
    if args_paths:
        for raw in args_paths:
            p = Path(raw).expanduser()
            if not p.exists():
                print(f"[ERROR] Path does not exist: {p}")
                continue
            if p.is_dir():
                found.extend(x for x in p.rglob("*") if x.is_file() and x.suffix.lower() == ".pmx")
            elif p.is_file() and p.suffix.lower() == ".pmx":
                found.append(p)
            else:
                print(f"[SKIP] This is neither a PMX file nor a folder: {p}")
    else:
        INPUT_DIR.mkdir(parents=True, exist_ok=True)
        found.extend(x for x in INPUT_DIR.rglob("*") if x.is_file() and x.suffix.lower() == ".pmx")

    # Stable sort and de-duplicate (Windows paths are case-insensitive).
    unique = {}
    for p in found:
        try:
            full = p.resolve()
        except Exception:
            full = p.absolute()
        unique[str(full).casefold()] = full
    return sorted(unique.values(), key=lambda p: str(p).casefold())


def read_pmx_english_name(pmx_path):
    """Read only the PMX header and names; does not parse the full geometry."""
    try:
        import struct
        with open(pmx_path, "rb") as f:
            data = f.read(65536)
        if data[:4] != b"PMX ":
            return ""
        pos = 4 + 4
        gcount = data[pos]
        pos += 1
        globals_bytes = data[pos:pos + gcount]
        pos += gcount
        if not globals_bytes:
            return ""
        enc = globals_bytes[0]

        def read_text_at(pos):
            (n,) = struct.unpack_from("<i", data, pos)
            pos += 4
            raw = data[pos:pos + n]
            pos += n
            return raw.decode("utf-16-le" if enc == 0 else "utf-8", errors="replace"), pos

        _native, pos = read_text_at(pos)
        english, _ = read_text_at(pos)
        return english.strip()
    except Exception:
        return ""


def safe_slug(pmx_path):
    stem = pmx_path.stem
    # Prefer a meaningful ASCII filename. For Japanese/non-Latin names, use the PMX's English name.
    ascii_stem = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode("ascii")
    if not re.search(r"[A-Za-z]", ascii_stem):
        english = read_pmx_english_name(pmx_path)
        if english:
            ascii_stem = unicodedata.normalize("NFKD", english).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9]+", "-", ascii_stem.lower()).strip("-")
    if not slug:
        # Stable fallback for files whose names contain no Latin characters and no English PMX name.
        slug = "model-" + hashlib.sha1(str(pmx_path.resolve()).encode("utf-8", errors="replace")).hexdigest()[:8]
    if slug.upper() in {"CON", "PRN", "AUX", "NUL"} or re.fullmatch(r"COM[1-9]|LPT[1-9]", slug.upper()):
        slug = "model-" + slug
    return slug[:72].rstrip("-") or "model"


def read_model_overrides(input_dir):
    result = {}
    if not CSV_PATH.exists():
        return result
    try:
        with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
            useful = (line for line in f if line.strip() and not line.lstrip().startswith("#"))
            reader = csv.DictReader(useful)
            for row in reader:
                key = (row.get("pmx_file") or "").strip().replace("\\", "/").casefold()
                if key:
                    result[key] = {k: (v or "").strip() for k, v in row.items()}
    except Exception as exc:
        print(f"[WARNING] Could not read models.csv: {exc}")
    return result


def override_for(pmx_path, overrides):
    candidates = [pmx_path.name.casefold()]
    try:
        candidates.insert(0, pmx_path.resolve().relative_to(INPUT_DIR.resolve()).as_posix().casefold())
    except Exception:
        pass
    for key in candidates:
        if key in overrides:
            return overrides[key]
    return {}


def as_float(row, key, fallback):
    value = (row.get(key) or "").strip()
    if not value:
        return fallback
    try:
        return float(value)
    except ValueError:
        return fallback


def as_int(row, key, fallback):
    value = (row.get(key) or "").strip()
    if not value:
        return fallback
    try:
        return int(value)
    except ValueError:
        return fallback


def as_bool(value, default=True):
    if value is None or str(value).strip() == "":
        return default
    return str(value).strip().lower() not in {"0", "false", "no", "n", "off", "нет"}


def normalized_path(value):
    try:
        return os.path.normcase(os.path.abspath(str(value))).casefold()
    except Exception:
        return str(value).replace("\\", "/").casefold()


def is_managed_by_source(folder, source_path):
    marker = folder / MARKER
    if not marker.is_file():
        return False
    try:
        for line in marker.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("source="):
                return normalized_path(line[len("source="):]) == normalized_path(source_path)
    except Exception:
        return False
    return False


def choose_destination(base_dir, wanted_name, replace_managed, source_path):
    """Replace only this source's previous output; never overwrite a different model."""
    base_dir.mkdir(parents=True, exist_ok=True)
    candidate = base_dir / wanted_name
    if not candidate.exists():
        return candidate, False
    if replace_managed and candidate.is_dir() and is_managed_by_source(candidate, source_path):
        return candidate, True
    n = 2
    while True:
        alternate = base_dir / f"{wanted_name}-{n}"
        if not alternate.exists():
            return alternate, False
        if replace_managed and alternate.is_dir() and is_managed_by_source(alternate, source_path):
            return alternate, True
        n += 1


def make_output_base(settings, args):
    mode = args.output_mode or settings.get("output_mode", "game")
    if mode == "local":
        raw = args.output_dir or settings.get("local_output_dir", "output")
        path = Path(raw)
        if not path.is_absolute():
            path = BASE / path
        return path.resolve(), mode
    raw = args.output_dir or settings.get("game_printer_dir", "%LOCALAPPDATA%\\VotV\\Assets\\meshes\\printer")
    return expand_path(raw), mode


def build_command(pmx_path, staging_root, name, settings, override):
    cmd = [sys.executable, str(CONVERTER), str(pmx_path), "--name", name, "--out", str(staging_root)]
    height = as_float(override, "height_cm", float(settings.get("default_height_cm", 0) or 0))
    if height > 0:
        cmd.extend(["--height", str(height)])
    else:
        scale = as_float(override, "scale", float(settings.get("default_scale", 7.625)))
        if scale <= 0:
            scale = 7.625
        cmd.extend(["--scale", str(scale)])

    collider = (override.get("collider") or settings.get("collider", "box")).strip().lower()
    if collider not in {"box", "none"}:
        collider = "box"
    cmd.extend(["--collider", collider])
    width = as_float(override, "collider_width_cm", float(settings.get("collider_width_cm", 32)))
    depth = as_float(override, "collider_depth_cm", float(settings.get("collider_depth_cm", 24)))
    cmd.extend(["--collider-width", str(width), "--collider-depth", str(depth)])

    max_tex = as_int(override, "max_texture_size", int(settings.get("max_texture_size", 1024) or 0))
    if max_tex > 0:
        cmd.extend(["--max-tex", str(max_tex)])
    drop = override.get("drop_materials") or settings.get("drop_materials", "")
    if drop.strip():
        cmd.extend(["--drop", drop.strip()])
    opaque = override.get("opaque_materials") or settings.get("opaque_materials", "")
    if opaque.strip():
        cmd.extend(["--opaque", opaque.strip()])
    cfg = override.get("cfg_template") or settings.get("cfg_template", "")
    if cfg.strip():
        cfg_path = Path(cfg.strip())
        if not cfg_path.is_absolute():
            cfg_path = BASE / cfg_path
        if cfg_path.exists():
            cmd.extend(["--cfg", str(cfg_path.resolve())])
    return cmd


def main():
    parser = argparse.ArgumentParser(description="One-click batch PMX -> VOTV 3D Printer converter")
    parser.add_argument("paths", nargs="*", help="PMX files/folders; if omitted, scans ./input recursively")
    parser.add_argument("--output-mode", choices=("game", "local"), help="override destination from settings.json")
    parser.add_argument("--output-dir", help="override destination directory")
    args = parser.parse_args()

    log_lines = [f"VOTV PMX batch conversion — {datetime.now().isoformat(timespec='seconds')}"]
    try:
        settings = load_settings()
        if not CONVERTER.exists():
            raise RuntimeError(f"Converter script not found: {CONVERTER}")
        paths = list_inputs(args.paths)
        if not paths:
            say("No .pmx files were found in the input folder.", log_lines)
            say("Create a separate folder for each model and place the PMX file together with its source textures. Then run START_CONVERSION.bat again.", log_lines)
            return 2

        out_base, mode = make_output_base(settings, args)
        out_base.mkdir(parents=True, exist_ok=True)
        overrides = read_model_overrides(INPUT_DIR)
        say(f"PMX files found: {len(paths)}", log_lines)
        say(f"Output mode: {'VotV printer folder' if mode == 'game' else 'local folder'}", log_lines)
        say(f"Destination: {out_base}", log_lines)
        say("Default scale: " + (f"height {settings.get('default_height_cm')} cm" if float(settings.get('default_height_cm', 0) or 0) > 0 else f"factor {settings.get('default_scale', 7.625)}; final height depends on the source PMX scale"), log_lines)
        say("-" * 72, log_lines)

        succeeded = 0
        failed = 0
        for index, pmx in enumerate(paths, 1):
            override = override_for(pmx, overrides)
            if not as_bool(override.get("enabled"), True):
                say(f"[{index}/{len(paths)}] SKIP (enabled=0): {pmx}", log_lines)
                continue

            name = safe_slug(pmx)
            final_dir, replacing = choose_destination(out_base, name, bool(settings.get("replace_managed_output", True)), pmx)
            # Keep an individual staging tree so a failed conversion never damages an existing print.
            with tempfile.TemporaryDirectory(prefix="votv-pmx-stage-") as temp:
                stage_root = Path(temp)
                command = build_command(pmx, stage_root, final_dir.name, settings, override)
                say(f"[{index}/{len(paths)}] {pmx.name} -> {final_dir.name}", log_lines)
                try:
                    result = subprocess.run(
                        command, cwd=str(BASE), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, encoding="utf-8", errors="replace", env={**os.environ, "PYTHONUTF8": "1"}
                    )
                    if result.stdout:
                        out = result.stdout.rstrip()
                        print(out, flush=True)
                        log_lines.append(out)
                    generated_dir = stage_root / final_dir.name
                    obj_path = generated_dir / (final_dir.name + ".obj")
                    if result.returncode != 0 or not obj_path.is_file() or not (generated_dir / "properties.cfg").is_file():
                        failed += 1
                        say(f"[ERROR] Conversion failed for {pmx.name} (exit code {result.returncode}).", log_lines)
                        continue
                    if final_dir.exists():
                        if replacing and is_managed_by_source(final_dir, pmx):
                            shutil.rmtree(final_dir)
                        else:
                            failed += 1
                            say(f"[ERROR] The destination folder already exists or belongs to another model: {final_dir}. Overwriting was cancelled.", log_lines)
                            continue
                    shutil.copytree(generated_dir, final_dir)
                    (final_dir / MARKER).write_text(
                        "Generated by VotV_PMX_Converter.\nsource=" + str(pmx.resolve()) + "\n", encoding="utf-8"
                    )
                    missing = "texture not found" in (result.stdout or "").lower()
                    if missing:
                        say(f"[WARNING] {pmx.name}: some textures were not found; the model was installed without them.", log_lines)
                    say(f"[DONE] {final_dir}", log_lines)
                    succeeded += 1
                except Exception as exc:
                    failed += 1
                    say(f"[ERROR] {pmx.name}: {exc}", log_lines)
            say("-" * 72, log_lines)

        say(f"SUMMARY: {succeeded} successful, {failed} failed, {len(paths) - succeeded - failed} skipped", log_lines)
        if mode == "game":
            say("If VotV is already running, restart the game or refresh the printer to update the model list.", log_lines)
        return 0 if failed == 0 else 1
    finally:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        try:
            (LOG_DIR / f"conversion-{timestamp}.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
        except Exception:
            pass


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nCancelled by user.")
        raise SystemExit(130)
    except Exception as exc:
        print(f"Fatal error: {exc}")
        raise SystemExit(1)
