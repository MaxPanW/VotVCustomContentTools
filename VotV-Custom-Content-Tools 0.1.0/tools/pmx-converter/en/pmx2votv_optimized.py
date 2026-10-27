#!/usr/bin/env python3
"""PMX to VotV Printer converter.

Converts a static PMX model into an OBJ/MTL asset folder with diffuse textures,
icon.png and properties.cfg. Blender and MMD Tools are not required.

Requirements: Python 3.9+ and Pillow.

Examples:
  python pmx2votv_optimized.py model.pmx --name model --height 156
  python pmx2votv_optimized.py model.pmx --out ./output --collider box
  python pmx2votv_optimized.py model.pmx --max-tex 1024 --collider-width 32 --collider-depth 24

The converter removes fully duplicated material layers, offsets overlapping layers
slightly, maps common material names to printer-friendly names and generates
properties.cfg. It can also add a simple UCX box collider.
"""
import argparse
import os
import re
import shutil
import struct
import sys

# Use UTF-8 for logs and tolerate characters unsupported by legacy Windows code pages.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            pass

# Avoid UnicodeEncodeError in Windows consoles using legacy code pages.
# GUI callers read subprocess output as UTF-8; interactive consoles keep their own encoding.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _encoding = "utf-8" if not _stream.isatty() else _stream.encoding
            _stream.reconfigure(encoding=_encoding, errors="replace")
        except (OSError, ValueError):
            pass
try:
    from PIL import Image
except ImportError:
    Image = None


# ---------------------------------------------------------------- PMX reader
class Reader:
    def __init__(self, data):
        self.d = data
        self.p = 0

    def unpack(self, fmt):
        size = struct.calcsize(fmt)
        v = struct.unpack_from("<" + fmt, self.d, self.p)
        self.p += size
        return v

    def skip(self, n):
        self.p += n

    def idx(self, size, signed=True):
        fmt = {1: "b" if signed else "B", 2: "h" if signed else "H", 4: "i"}[size]
        return self.unpack(fmt)[0]

    def text(self, enc):
        (n,) = self.unpack("i")
        raw = self.d[self.p:self.p + n]
        self.p += n
        return raw.decode("utf-16-le" if enc == 0 else "utf-8", errors="replace")


def read_pmx(path):
    with open(path, "rb") as f:
        r = Reader(f.read())

    if r.d[:4] != b"PMX ":
        raise SystemExit("This is not a PMX file (legacy PMD format is not supported).")
    r.skip(4)
    (version,) = r.unpack("f")
    (gcount,) = r.unpack("B")
    g = list(r.unpack("%dB" % gcount))
    enc, add_uv, vsz, tsz, msz, bsz = g[0], g[1], g[2], g[3], g[4], g[5]

    name = r.text(enc)
    name_en = r.text(enc)
    r.text(enc)
    r.text(enc)

    # vertices
    (vcount,) = r.unpack("i")
    verts, normals, uvs = [], [], []
    for _ in range(vcount):
        verts.append(r.unpack("3f"))
        normals.append(r.unpack("3f"))
        uvs.append(r.unpack("2f"))
        r.skip(16 * add_uv)
        (wt,) = r.unpack("B")
        if wt == 0:
            r.skip(bsz)
        elif wt == 1:
            r.skip(bsz * 2 + 4)
        elif wt in (2, 4):
            r.skip(bsz * 4 + 16)
        elif wt == 3:
            r.skip(bsz * 2 + 4 + 36)
        else:
            raise SystemExit("Unknown vertex weight type: %d" % wt)
        r.skip(4)  # edge scale

    # faces
    (icount,) = r.unpack("i")
    faces = [r.idx(vsz, signed=False) if vsz != 4 else r.idx(4) for _ in range(icount)]

    # textures
    (tcount,) = r.unpack("i")
    textures = [r.text(enc).replace("\\", "/") for _ in range(tcount)]

    # materials
    (mcount,) = r.unpack("i")
    mats = []
    for i in range(mcount):
        mname = r.text(enc)
        mname_en = r.text(enc)
        diffuse = r.unpack("4f")
        r.skip(12 + 4 + 12)  # specular, strength, ambient
        (flags,) = r.unpack("B")
        r.skip(16 + 4)  # edge color, edge size
        tex = r.idx(tsz)
        r.idx(tsz)  # sphere
        r.skip(1)  # sphere mode
        (toon_shared,) = r.unpack("B")
        if toon_shared:
            r.skip(1)
        else:
            r.idx(tsz)
        r.text(enc)  # memo
        (surf,) = r.unpack("i")
        mats.append({
            "name": mname, "name_en": mname_en, "diffuse": diffuse,
            "flags": flags, "tex": tex, "count": surf,
        })

    return {"name": name or name_en, "verts": verts, "normals": normals,
            "uvs": uvs, "faces": faces, "textures": textures, "mats": mats,
            "version": version}


# ---------------------------------------------------------------- helpers
def is_ascii_ident(s):
    return bool(s) and re.fullmatch(r"[A-Za-z0-9_\-]+", s) is not None


def obj_bbox(path):
    mn = [1e30] * 3
    mx = [-1e30] * 3
    with open(path, "r", errors="ignore") as f:
        for line in f:
            if line.startswith("v "):
                x = list(map(float, line.split()[1:4]))
                for i in range(3):
                    mn[i] = min(mn[i], x[i])
                    mx[i] = max(mx[i], x[i])
    return mn, mx


def find_texture(base_dir, rel):
    """Find a texture by its PMX-relative path, then recursively by filename."""
    rel = rel.replace("\\", "/")
    cand = os.path.join(base_dir, *rel.split("/"))
    if os.path.isfile(cand):
        return cand

    # Windows paths stored in PMX may use different casing from actual folder names.
    want_path = rel.replace("/", os.sep).lower()
    for root, dirs, files in os.walk(base_dir):
        # Do not enter system or utility directories.
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__"}]
        for fn in files:
            full = os.path.join(root, fn)
            rel_full = os.path.relpath(full, base_dir).lower()
            if rel_full == want_path or fn.lower() == os.path.basename(rel).lower():
                return full
    return None



# ---------------------------------------------------------------- v2 logic
RULES = [("bdy", "body"), ("body", "body"), ("eye", "eyes"), ("mayu", "mayu"),
         ("brow", "mayu"), ("cheek", "cheek"), ("mouth", "mouth"),
         ("face", "face"), ("hair", "hair"), ("tail", "tail")]

DEFAULT_CFG_TAIL = """physical_material=0
emissive_strength=0
is_lamp=0
lamp_color=(R=1,G=1,B=1)
lamp_offset=(X=0,Y=0,Z=0)
lamp_intensity=5000
lamp_attenuation=2500
lamp_shadows=0"""


def guess_name(*cands):
    for c in cands:
        lc = (c or "").lower()
        for k, v in RULES:
            if k in lc:
                return v
    return None


def tri_key(verts, t):
    return tuple(sorted(tuple(round(c, 3) for c in verts[v]) for v in t))


def norm3(n):
    l = (n[0] ** 2 + n[1] ** 2 + n[2] ** 2) ** 0.5 or 1.0
    return (n[0] / l, n[1] / l, n[2] / l)


def append_box_collider(obj_path, name, scale, flip, y_min, y_max,
                        center_x, center_z, width, depth, vertex_offset):
    """Append a separate low-polygon UCX box to the OBJ.

    Width, depth, and height are measured in VotV printer units (centimetres).
    Center the collider on the main body material rather than the full bounds of
    loose hair and tail. Y is the vertical axis in this converter format.
    """
    if width <= 0 or depth <= 0:
        raise SystemExit("Collider width and depth must be greater than zero.")

    cx = center_x * scale
    cz = center_z * scale * (-1.0 if flip else 1.0)
    ymin, ymax = y_min * scale, y_max * scale
    hx, hz = width / 2.0, depth / 2.0
    corners = [
        (cx-hx, ymin, cz-hz), (cx+hx, ymin, cz-hz),
        (cx+hx, ymax, cz-hz), (cx-hx, ymax, cz-hz),
        (cx-hx, ymin, cz+hz), (cx+hx, ymin, cz+hz),
        (cx+hx, ymax, cz+hz), (cx-hx, ymax, cz+hz),
    ]
    # At most four vertices per face; the importer triangulates each quad.
    faces = [
        (1, 4, 3, 2), (5, 6, 7, 8),
        (1, 2, 6, 5), (2, 3, 7, 6),
        (3, 4, 8, 7), (4, 1, 5, 8),
    ]
    with open(obj_path, "a", encoding="utf-8", newline="\n") as o:
        o.write("\n# Simple custom collision; intentionally separate from the visible mesh\n")
        o.write("o UCX_%s_00\n" % name)
        for x, y, z in corners:
            o.write("v %.5f %.5f %.5f\n" % (x, y, z))
        for face in faces:
            o.write("f %s\n" % " ".join(str(vertex_offset + i) for i in face))


def main():
    ap = argparse.ArgumentParser(description="PMX -> VotV 3D printer folder")
    ap.add_argument("pmx")
    ap.add_argument("--name", help="output folder/model name (ASCII, no spaces)")
    ap.add_argument("--out", default=".", help="output parent folder (current folder by default)")
    ap.add_argument("--scale", type=float, default=None,
                    help="scale factor for PMX units (default 8.0 = PMX to centimetres)")
    ap.add_argument("--height", type=float, default=None,
                    help="set the model height to N output units (e.g. 170)")
    ap.add_argument("--match", help="path to a reference OBJ; match its height")
    ap.add_argument("--cfg", help="properties.cfg from a reference model (template for the config tail)")
    ap.add_argument("--icon", help="icon.png (if omitted, an icon is generated from a texture)")
    ap.add_argument("--no-flip", action="store_true",
                    help="do not flip the Z axis (use if the model appears mirrored)")
    ap.add_argument("--drop", default="", help="comma-separated material names to omit")
    ap.add_argument("--push", type=float, default=0.15,
                    help="offset for overlapping layers in output units (default 0.15)")
    ap.add_argument("--max-tex", type=int, default=0,
                    help="downscale textures so their longest side is at most N pixels (e.g. 1024)")
    ap.add_argument("--opaque", default="",
                    help="comma-separated materials whose textures should be made opaque (e.g. body,face,hair,tail)")
    ap.add_argument("--dup-threshold", type=float, default=0.95,
                    help="overlap ratio used to detect duplicate material layers")
    ap.add_argument("--collider", choices=("box", "none"), default="box",
                    help="add a simple UCX box collider (default) or disable it")
    ap.add_argument("--collider-width", type=float, default=32.0,
                    help="UCX box width in VotV units (cm; default 32)")
    ap.add_argument("--collider-depth", type=float, default=24.0,
                    help="UCX box depth in VotV units (cm; default 24)")
    args = ap.parse_args()

    if Image is None:
        raise SystemExit("Pillow is required: pip install pillow")

    m = read_pmx(args.pmx)
    verts, normals, uvs = m["verts"], m["normals"], m["uvs"]
    pmx_dir = os.path.dirname(os.path.abspath(args.pmx))
    base = os.path.splitext(os.path.basename(args.pmx))[0]
    name = args.name or (base if is_ascii_ident(base) else "model")
    name = re.sub(r"[^A-Za-z0-9_\-]", "_", name).lower()
    out = os.path.join(args.out, name)
    os.makedirs(out, exist_ok=True)

    total_tris = len(m["faces"]) // 3
    print("Model: %s | vertices: %d | triangles: %d | materials: %d" % (
        m["name"], len(verts), total_tris, len(m["mats"])))

    # ---- scaling
    ys = [v[1] for v in verts]
    pmx_height = max(ys) - min(ys)
    if args.match:
        mn, mx = obj_bbox(args.match)
        scale = (mx[1] - mn[1]) / pmx_height
        print("Reference height: %.2f -> scale %.3f" % (mx[1] - mn[1], scale))
    elif args.height:
        scale = args.height / pmx_height
    elif args.scale:
        scale = args.scale
    else:
        scale = 8.0
    print("PMX height: %.2f, output height: %.2f (scale=%.3f)" % (
        pmx_height, pmx_height * scale, scale))

    drop = {s.strip() for s in args.drop.split(",") if s.strip()}
    opaque = {s.strip() for s in args.opaque.split(",") if s.strip()}

    # ---- split faces by material and detect duplicate/overlapping layers
    pos = 0
    seen = set()
    kept = []
    for i, mt in enumerate(m["mats"]):
        f = m["faces"][pos:pos + mt["count"]]
        pos += mt["count"]
        tris = [tuple(f[k:k + 3]) for k in range(0, len(f), 3)]
        tris = [t for t in tris if len(set(t)) == 3]
        label = mt["name_en"] if is_ascii_ident(mt["name_en"]) else mt["name"]
        if mt["name"] in drop or label in drop:
            print("  - omitted by --drop: %s" % label)
            continue
        if mt["diffuse"][3] <= 0.001 or not tris:
            print("  - skipped transparent/empty material #%d (%s)" % (i, label))
            continue
        keys = [tri_key(verts, t) for t in tris]
        kset = set(keys)
        # A duplicate must match one previously kept material in both directions.
        dup_of = None
        for k in kept:
            common = len(kset & k["kset"])
            if common / len(kset) >= args.dup_threshold and common / len(k["kset"]) >= 0.9:
                dup_of = k
                break
        if dup_of:
            print("  - material #%d (%s): duplicate of layer #%d, skipped (-%d triangles)" % (
                i, label, dup_of["i"], len(tris)))
            continue
        ov = sum(1 for kk in keys if kk in seen)
        push = ov > 0
        if push:
            print("  ~ material #%d (%s): %d of %d triangles overlap another layer; offsetting it" % (
                i, label, ov, len(tris)))
        seen.update(keys)
        kept.append({"i": i, "mt": mt, "label": label, "tris": tris, "push": push, "kset": kset})

    # ---- in-game material names
    used = set()
    for n, k in enumerate(kept):
        nm = guess_name(k["label"], k["mt"]["name"])
        if not nm:
            nm = "mat%02d" % k["i"]
        base_nm, c = nm, 2
        while nm in used:
            nm = "%s%d" % (base_nm, c)
            c += 1
        used.add(nm)
        k["name"] = nm

    # ---- textures: each material gets its own diffuse_<name>.png
    cache = {}
    for k in kept:
        ti = k["mt"]["tex"]
        k["tex"] = None
        if ti < 0 or ti >= len(m["textures"]):
            continue
        src = find_texture(pmx_dir, m["textures"][ti])
        if not src:
            print("  ! texture not found: %s (check that source textures are next to the PMX file or in its subfolders)" % m["textures"][ti])
            continue
        try:
            if src not in cache:
                cache[src] = Image.open(src).convert("RGBA")
            fn = "diffuse_%s.png" % k["name"]
            im = cache[src]
            w0, h0 = im.size
            if args.max_tex and max(im.size) > args.max_tex:
                r = args.max_tex / max(im.size)
                im = im.resize((max(1, round(im.width * r)), max(1, round(im.height * r))), Image.LANCZOS)
            if k["name"] in opaque:
                bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
                bg.alpha_composite(im)
                im = bg
            im.save(os.path.join(out, fn))
            k["tex"] = fn
            k["texinfo"] = "%dx%d%s" % (w0, h0, " -> %dx%d" % im.size if im.size != (w0, h0) else "")
        except Exception as e:
            print("  ! could not convert %s: %s" % (src, e))

    # ---- OBJ / MTL (each material has its own vertex set)
    flip = not args.no_flip
    obj_path = os.path.join(out, name + ".obj")
    nv = 0
    ntris = 0
    with open(obj_path, "w") as o:
        o.write("# generated by pmx2votv.py v2\nmtllib %s.mtl\no %s\n" % (name, name))
        for k in kept:
            used_v = sorted({v for t in k["tris"] for v in t})
            remap = {v: n + 1 + nv for n, v in enumerate(used_v)}
            for v in used_v:
                x, y, z = verts[v]
                nx, ny, nz = norm3(normals[v])
                if flip:
                    z, nz = -z, -nz
                px, py, pz = x * scale, y * scale, z * scale
                if k["push"]:
                    px += nx * args.push
                    py += ny * args.push
                    pz += nz * args.push
                o.write("v %.5f %.5f %.5f\n" % (px, py, pz))
            for v in used_v:
                o.write("vt %.5f %.5f\n" % (uvs[v][0], 1.0 - uvs[v][1]))
            for v in used_v:
                n = normals[v]
                o.write("vn %.4f %.4f %.4f\n" % (n[0], n[1], -n[2] if flip else n[2]))
            o.write("g %s\nusemtl %s\n" % (k["name"], k["name"]))
            for a, b, c in k["tris"]:
                if flip:
                    b, c = c, b
                a, b, c = remap[a], remap[b], remap[c]
                o.write("f %d/%d/%d %d/%d/%d %d/%d/%d\n" % (a, a, a, b, b, b, c, c, c))
            nv += len(used_v)
            ntris += len(k["tris"])

    with open(os.path.join(out, name + ".mtl"), "w") as f:
        for k in kept:
            f.write("newmtl %s\nKa 1.0 1.0 1.0\nKd 1.0 1.0 1.0\nKs 0.0 0.0 0.0\nd 1.0\nillum 1\n" % k["name"])
            if k["tex"]:
                f.write("map_Kd %s\n" % k["tex"])
            f.write("\n")

    # ---- separate simple collider so VotV does not build a convex hull around hair
    if args.collider == "box":
        # Use the first body material to find the body center, not the full model bounds:
        # otherwise, hair and tail would make the hitbox too wide.
        body_mat = next((k for k in kept if k["name"].startswith("body")), None)
        if body_mat:
            body_vids = {v for tri in body_mat["tris"] for v in tri}
        else:
            body_vids = set(range(len(verts)))
        if body_vids:
            center_x = (min(verts[v][0] for v in body_vids) + max(verts[v][0] for v in body_vids)) / 2.0
            center_z = (min(verts[v][2] for v in body_vids) + max(verts[v][2] for v in body_vids)) / 2.0
        else:
            center_x = center_z = 0.0
        append_box_collider(obj_path, name, scale, flip, min(ys), max(ys),
                            center_x, center_z, args.collider_width, args.collider_depth, nv)
        print("Collider: UCX_%s_00, %.1f x %.1f x %.1f units (W x D x H)" % (
            name, args.collider_width, args.collider_depth, pmx_height * scale))

    # ---- icon
    icon_path = os.path.join(out, "icon.png")
    if args.icon:
        shutil.copy(args.icon, icon_path)
    else:
        pick = next((k["tex"] for k in kept if k["name"] == "face" and k["tex"]), None) or \
               next((k["tex"] for k in kept if k["tex"]), None)
        if pick:
            im = Image.open(os.path.join(out, pick)).convert("RGBA")
            im.thumbnail((128, 128))
            im.save(icon_path)

    # ---- properties.cfg: generate filters for exported materials and retain the template tail
    tail = DEFAULT_CFG_TAIL
    if args.cfg:
        with open(args.cfg, encoding="utf-8", errors="ignore") as f:
            lines = [l.rstrip("\r\n") for l in f if l.strip() and not l.startswith("filter_")]
        if lines:
            tail = "\n".join(lines)
    cfg = []
    for k in kept:
        for kind in ("diffuse", "pbr", "normal", "emissive"):
            cfg.append("filter_%s_%s=0" % (kind, k["name"]))
    with open(os.path.join(out, "properties.cfg"), "w", newline="\n") as f:
        f.write("\n".join(cfg) + "\n" + tail + "\n")

    print("\nResult: %d -> %d visual-mesh triangles, %d visual-mesh vertices%s, %d materials" % (
        total_tris, ntris, nv, " (+8 UCX collider vertices)" if args.collider == "box" else "", len(kept)))
    print("UE/VotV estimate: about %d rendered vertex references from visual triangles (3 per triangle; this is not the polygon count)." % (ntris * 3))
    print("Materials (PMX -> in-game name):")
    for k in kept:
        print("  #%d %-26s -> %-8s %6d triangles  %s%s" % (k["i"], k["label"], k["name"], len(k["tris"]),
              (k["tex"] + " " + k.get("texinfo", "")) if k["tex"] else "(no texture)",
              "  [offset]" if k["push"] else ""))
    print("OBJ model height: %.1f units (use --height or --match if needed)"
          % (pmx_height * scale))
    print("\nDone: %s" % os.path.abspath(out))


if __name__ == "__main__":
    main()