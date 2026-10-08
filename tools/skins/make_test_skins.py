#!/usr/bin/env python3
"""Write a synthetic pack of skin mods for local testing. Output is never committed.

    make_test_skins.py --out DIR [--iso PATH] [--fighters mario:40,fox:30,...]
                       [--mex PlWf.dat=PlWfNr.dat:20 ...] [--geno KEY=SRC.dat:5 ...]
                       [--art-every 5] [--seed 1]

The model files are copies (hard links where the filesystem allows) of the player's own retail
costume DATs, read from their disc at run time into OUT/_src. The art is generated here: a
number on a hue gradient, so there is no third-party artwork in the pack. OUT gets a .gitignore
of `*`. --out may not sit inside tools/, docs/ or pc/ of this repo (exit 2).

--seed is accepted for reproducibility; the output does not depend on it.
"""

import argparse
import colorsys
import json
import os
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import skinlib  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

ROOT = skinlib.ROOT
FORBIDDEN = [ROOT / "tools", ROOT / "docs", ROOT / "pc"]
# The name the default list uses for Marth; the retail table calls him mars (Pl code Ms).
ALIASES = {"marth": "mars"}
DEFAULT_FIGHTERS = "mario:40,fox:30,falco:20,marth:20,captain:10,link:10"
RETAIL_BY_NAME = {name: (code, tok) for _, name, code, tok in skinlib.RETAIL}


def refused_location(out):
    out = Path(out).resolve()
    for sub in FORBIDDEN:
        s = sub.resolve()
        if out == s or s in out.parents:
            return sub
    return None


def parse_count(rest):
    m = re.match(r"^(.*):(\d+)$", rest)
    if m:
        return m.group(1), int(m.group(2))
    return rest, 1


def parse_fighters(text):
    out = []
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        name, _, count = item.partition(":")
        name = ALIASES.get(name.strip().lower(), name.strip().lower())
        if name not in RETAIL_BY_NAME:
            raise SystemExit(f"make_test_skins: unknown retail fighter {name!r}")
        out.append((name, int(count) if count else 1))
    return out


def find_default_costume(gcm, code):
    """The fighter's default costume file on the disc: Pl<code>Nr.dat, else the first Pl<code>??.dat."""
    pat = re.compile(rf"Pl{code}[A-Za-z0-9]{{2}}\.dat", re.IGNORECASE)
    names = sorted({k.rsplit("/", 1)[-1] for k in gcm.files if pat.fullmatch(k.rsplit("/", 1)[-1])})
    if not names:
        raise SystemExit(f"make_test_skins: no Pl{code}??.dat costume on the disc")
    for n in names:
        if n.lower() == f"pl{code}nr.dat".lower():
            return n
    return names[0]


def load_font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow without FreeType
        return ImageFont.load_default()


def gradient(w, h, hue_deg):
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(h - 1, 1)
        r, g, b = colorsys.hsv_to_rgb((hue_deg % 360) / 360.0, 0.55, 1.0 - 0.45 * t)
        draw.line([(0, y), (w - 1, y)], fill=(round(r * 255), round(g * 255), round(b * 255)))
    return img


def numbered(i, w, h, hue_deg, size):
    img = gradient(w, h, hue_deg)
    draw = ImageDraw.Draw(img)
    font = load_font(size)
    text = str(i)
    l, t, r, b = draw.textbbox((0, 0), text, font=font)
    x = int((w - (r - l)) / 2 - l)
    y = int((h - (b - t)) / 2 - t)
    draw.text((x, y), text, fill=(255, 255, 255), font=font)
    return img


def write_bytes(path, data):
    if os.path.lexists(path):
        os.remove(path)
    with open(path, "wb") as fp:
        fp.write(data)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Synthetic skin test pack (never commit the output).")
    ap.add_argument("--out", required=True, help="output folder (git-ignored by its own .gitignore)")
    ap.add_argument("--iso", help="disc image (default $GW_ISO_VANILLA, else $GW_ISO_ACE)")
    ap.add_argument("--fighters", default=DEFAULT_FIGHTERS, help="name:count,... (retail fighters)")
    ap.add_argument("--mex", action="append", default=[], metavar="PlWf.dat=SRC:N",
                    help="m-ex target; SRC is a file on the disc (repeatable)")
    ap.add_argument("--geno", action="append", default=[], metavar="KEY=SRC.dat:N",
                    help="Geno define key; SRC is a loose file (repeatable)")
    ap.add_argument("--art-every", type=int, default=5, help="every Nth skin gets art (0: none)")
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args(argv)

    bad = refused_location(args.out)
    if bad is not None:
        print(f"make_test_skins: refusing --out inside {bad}: generated skins never go in the repo tree",
              file=sys.stderr)
        return 2

    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / ".gitignore").write_text("*\n", encoding="utf-8")
    src_dir = out / "_src"
    art_dir = out / "_art"
    src_dir.mkdir(exist_ok=True)
    art_dir.mkdir(exist_ok=True)

    try:
        return build_pack(args, out, src_dir, art_dir)
    except KeyError as e:
        print(f"make_test_skins: {e.args[0]}", file=sys.stderr)
        return 2


def build_pack(args, out, src_dir, art_dir):
    fighters = parse_fighters(args.fighters)
    mex_specs = []
    for item in args.mex:
        dest, _, rest = item.partition("=")
        if not dest or not rest or not dest.lower().endswith(".dat"):
            raise SystemExit(f"make_test_skins: --mex wants PlWf.dat=SRC.dat:N, got {item!r}")
        src, count = parse_count(rest)
        mex_specs.append((dest, src, count))
    geno_specs = []
    for item in args.geno:
        key, _, rest = item.partition("=")
        if not key or not rest:
            raise SystemExit(f"make_test_skins: --geno wants KEY=SRC.dat:N, got {item!r}")
        src, count = parse_count(rest)
        geno_specs.append((key, src, count))

    iso = args.iso or os.environ.get("GW_ISO_VANILLA") or os.environ.get("GW_ISO_ACE")
    gcm = None
    if fighters or mex_specs:
        if not iso:
            print("make_test_skins: no disc: pass --iso or set GW_ISO_VANILLA / GW_ISO_ACE", file=sys.stderr)
            return 2
        gcm = skinlib.Gcm(iso)

    # Sources: (key, label, target, dat path in _src, joint, matanim, count, first_retail)
    sources = []
    for name, count in fighters:
        code, _tok = RETAIL_BY_NAME[name]
        base = find_default_costume(gcm, code)
        dat = src_dir / f"{name}.dat"
        raw = gcm.read(base)
        info = skinlib.classify_costume(raw)
        write_bytes(dat, raw)
        sources.append((name, name.title(), {"retail": name}, dat, info["joint"], info["matanim"], count))

    for dest, src, count in mex_specs:
        raw = gcm.read(src)
        info = skinlib.costume_symbols(raw)
        stem = dest[:-4].lower()
        dat = src_dir / f"mex-{stem}.dat"
        write_bytes(dat, raw)
        sources.append((stem, dest[:-4], {"mex": dest}, dat, info["joint"], info["matanim"], count))

    for key, src, count in geno_specs:
        with open(src, "rb") as fp:
            raw = fp.read()
        info = skinlib.costume_symbols(raw)
        label = re.sub(r"[^a-z0-9_-]+", "-", key.lower()).strip("-")
        if not label:
            raise SystemExit(f"make_test_skins: --geno key {key!r} has no usable characters")
        dat = src_dir / f"geno-{label}.dat"
        write_bytes(dat, raw)
        sources.append((label, key, {"geno": key}, dat, info["joint"], info["matanim"], count))

    mods = []
    per_fighter = {}
    total = 0
    for idx, (key, label, target, dat, joint, matanim, count) in enumerate(sources):
        per_fighter[key] = count
        for i in range(1, count + 1):
            mod_id = f"tsk-{key}-{i:03d}"
            mod_name = f"Test {label} {i}"[:skinlib.NAME_MAX]
            art = args.art_every > 0 and i % args.art_every == 0
            costume = {"name": mod_name, "src_dat": str(dat), "joint": joint, "matanim": matanim}
            if i == 3:
                costume["like"] = 0
            if idx == 0 and i <= 3:
                costume["team"] = ("red", "blue", "green")[i - 1]
            if art:
                hue = (i * 37) % 360
                csp_path = art_dir / f"{mod_id}_csp.png"
                stock_path = art_dir / f"{mod_id}_stock.png"
                numbered(i, 136, 188, hue, 96).save(csp_path, "PNG")
                numbered(i, 24, 24, hue, 16).save(stock_path, "PNG")
                costume["csp_png"] = str(csp_path)
                costume["stock_png"] = str(stock_path)
            skinlib.write_skin_mod(str(out), mod_id, mod_name, target, [costume])
            mods.append({"id": mod_id, "target": target, "costumes": 1, "art": art})
            total += 1

    shutil.rmtree(art_dir, ignore_errors=True)
    manifest = {"mods": mods, "per_fighter": per_fighter, "total_mods": total}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"made {total} skin mods ({total} costumes) in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
