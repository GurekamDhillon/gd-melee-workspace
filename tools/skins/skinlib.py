#!/usr/bin/env python3
"""Core of the skin tools: read costume DATs, write skin mod folders, lint them.

The format is specified in docs/superpowers/plans/2026-10-08-skins-registry.md section 2
(later docs/mods-packaging.md). This module never opens a disc image; callers hand it bytes.
make_test_skins.py is the one tool that reads an ISO, and only for a local, git-ignored pack.
"""

import json
import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "mex_port"))
import mex_hsd  # noqa: E402
from mex_hsd import Archive, Gcm  # noqa: E402,F401

DEFAULT_GAME = "E:/Projects/Melee Workspace/worktrees/skins255"

# (fighter_kind, target_name, pl_code, symbol_token), in FighterKind order.
RETAIL = [
    (0, "mario", "Mr", "Mario"),
    (1, "fox", "Fx", "Fox"),
    (2, "captain", "Ca", "Captain"),
    (3, "donkey", "Dk", "Donkey"),
    (4, "kirby", "Kb", "Kirby"),
    (5, "koopa", "Kp", "Koopa"),
    (6, "link", "Lk", "Link"),
    (7, "seak", "Sk", "Seak"),
    (8, "ness", "Ns", "Ness"),
    (9, "peach", "Pe", "Peach"),
    (10, "popo", "Pp", "Popo"),
    (11, "nana", "Nn", "Nana"),
    (12, "pikachu", "Pk", "Pikachu"),
    (13, "samus", "Ss", "Samus"),
    (14, "yoshi", "Ys", "Yoshi"),
    (15, "purin", "Pr", "Purin"),
    (16, "mewtwo", "Mt", "Mewtwo"),
    (17, "luigi", "Lg", "Luigi"),
    (18, "mars", "Ms", "Mars"),
    (19, "zelda", "Zd", "Zelda"),
    (20, "clink", "Cl", "Clink"),
    (21, "drmario", "Dr", "Drmario"),
    (22, "falco", "Fc", "Falco"),
    (23, "pichu", "Pc", "Pichu"),
    (24, "gamewatch", "Gw", "Gamewatch"),
    (25, "ganon", "Gn", "Ganon"),
    (26, "emblem", "Fe", "Emblem"),
]
RETAIL_BY_TOKEN = {tok.lower(): name for _, name, _, tok in RETAIL}
RETAIL_NAMES = frozenset(name for _, name, _, _ in RETAIL)
RETAIL_PL_FILES = frozenset(f"pl{code}.dat" for _, _, code, _ in RETAIL)  # lower case

COSTUME_SYMBOL = re.compile(r"^Ply(.+?)5K(.*?)_Share_joint$")
MOD_ID = re.compile(r"^[a-z0-9_-]+$")
NAME_MAX = 23
MAX_COSTUMES = 255
TEAMS = ("red", "blue", "green")
TARGET_KEYS = ("retail", "mex", "geno")
SKIN_KEYS = frozenset({"format", "target", "order", "costumes"})
COSTUME_KEYS = frozenset({"name", "file", "joint", "matanim", "team", "like", "kirby_hat",
                          "csp", "stock", "icon", "partner"})


# ----------------------------------------------------------------- reading DATs

def read_publics(raw):
    """Public symbol names of an HSD archive (bytes)."""
    try:
        arc = Archive(raw)
    except (ValueError, struct.error, IndexError) as e:
        raise ValueError(f"not an HSD archive: {e}") from None
    return [sym for sym, _ in arc.publics]


def costume_symbols(raw):
    """Find Ply<Token>5K<Colour>_Share_joint in a DAT, for any fighter (retail or not).

    Returns dict(token, colour, joint, matanim) with matanim None when absent.
    """
    pubs = read_publics(raw)
    for sym in pubs:
        m = COSTUME_SYMBOL.match(sym)
        if m:
            break
    else:
        shown = ", ".join(pubs[:8]) or "none"
        raise ValueError("not a costume DAT: no public symbol Ply<Fighter>5K<Colour>_Share_joint "
                         f"(publics: {shown})")
    token, colour = m.group(1), m.group(2)
    matanim = f"Ply{token}5K{colour}_Share_matanim_joint"
    return {"token": token, "colour": colour, "joint": sym,
            "matanim": matanim if matanim in pubs else None}


def classify_costume(raw):
    """Classify a retail costume DAT: dict(fighter, token, colour, joint, matanim)."""
    info = costume_symbols(raw)
    fighter = RETAIL_BY_TOKEN.get(info["token"].lower())
    if fighter is None:
        raise ValueError(f"costume is for {info['token']!r}, which is not a retail fighter "
                         "(for an m-ex or Geno costume pass --target mex:... or geno:...)")
    return dict(fighter=fighter, token=info["token"], colour=info["colour"],
                joint=info["joint"], matanim=info["matanim"])


# ------------------------------------------------------------------ art

def png_to_gxtex(png_path, out_path, fmt="rgb5a3", game_repo=None):
    """Convert a PNG with the game repo's pc/tools/png2gx.py (GW_MELEE selects the checkout)."""
    repo = game_repo or os.environ.get("GW_MELEE") or DEFAULT_GAME
    script = os.path.join(repo, "pc", "tools", "png2gx.py")
    if not os.path.isfile(script):
        raise FileNotFoundError(f"png2gx.py not found at {script} (set GW_MELEE)")
    # --allow-odd-size: skin art is 136x188 and 24x24, which png2gx refuses without it (format section 2).
    proc = subprocess.run([sys.executable, script, str(png_path), str(out_path), "--format", fmt,
                           "--allow-odd-size"], capture_output=True, text=True)
    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout).strip()
        raise RuntimeError(f"png2gx failed ({proc.returncode}) on {png_path}: {msg}")


# ------------------------------------------------------------------ writing

def _printable_ascii(s):
    return all(0x20 <= ord(c) <= 0x7E for c in s)


def costume_name(name):
    """A costume name as written: truncated to 23 characters, then checked."""
    if not isinstance(name, str):
        raise ValueError("costume name must be a string")
    name = name[:NAME_MAX]
    if not name or not _printable_ascii(name):
        raise ValueError(f"costume name {name!r} must be printable ASCII, 1..23 characters")
    return name


def place_file(src, dst):
    """Hard-link src to dst (no second copy on disk), else copy. Never writes through a link."""
    if os.path.lexists(dst):
        os.remove(dst)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copyfile(src, dst)


def write_skin_mod(mods_dir, mod_id, name, target, costumes, version="1.0.0", authors="", order=0):
    """Write mods_dir/<mod_id>/mod.json plus its files/skins/<mod_id>/ payload. Returns the dir."""
    if not isinstance(mod_id, str) or not MOD_ID.match(mod_id):
        raise ValueError(f"mod id {mod_id!r}: use lowercase letters, digits, '-' and '_' only")
    if not 1 <= len(costumes) <= MAX_COSTUMES:
        raise ValueError(f"a skin mod needs 1..{MAX_COSTUMES} costumes (got {len(costumes)})")
    mod_dir = os.path.join(mods_dir, mod_id)
    rel = f"skins/{mod_id}"
    files_dir = os.path.join(mod_dir, "files", "skins", mod_id)
    shutil.rmtree(files_dir, ignore_errors=True)
    os.makedirs(files_dir)

    entries = []
    for n, c in enumerate(costumes, 1):
        entry = {"name": costume_name(c["name"]), "file": f"{rel}/{n}.dat", "joint": c["joint"]}
        place_file(c["src_dat"], os.path.join(files_dir, f"{n}.dat"))
        if c.get("matanim"):
            entry["matanim"] = c["matanim"]
        if c.get("team") is not None:
            entry["team"] = c["team"]
        if c.get("like") is not None:
            entry["like"] = c["like"]
        if c.get("kirby_hat") is not None:
            entry["kirby_hat"] = c["kirby_hat"]
        if c.get("csp_png"):
            png_to_gxtex(c["csp_png"], os.path.join(files_dir, f"{n}_csp.gxtex"), "rgb5a3")
            entry["csp"] = f"{rel}/{n}_csp.gxtex"
        if c.get("stock_png"):
            png_to_gxtex(c["stock_png"], os.path.join(files_dir, f"{n}_stock.gxtex"), "rgb5a3")
            entry["stock"] = f"{rel}/{n}_stock.gxtex"
        entries.append(entry)

    skin = {"format": 1, "target": target}
    if order:
        skin["order"] = order
    skin["costumes"] = entries
    doc = {"id": mod_id, "name": name, "version": version, "kind": "skin",
           "authors": authors, "skin": skin}
    with open(os.path.join(mod_dir, "mod.json"), "w", encoding="utf-8", newline="\n") as fp:
        json.dump(doc, fp, indent=2, ensure_ascii=False)
        fp.write("\n")
    return mod_dir


# ------------------------------------------------------------------ linting

def _is_int(v, lo=None, hi=None):
    return type(v) is int and (lo is None or v >= lo) and (hi is None or v <= hi)


def _valid_name(v):
    return isinstance(v, str) and 1 <= len(v) <= NAME_MAX and _printable_ascii(v)


def _unsafe_rel(p):
    if not isinstance(p, str) or not p:
        return "must be a non-empty string"
    if p.startswith("/") or ":" in p or "\\" in p:
        return "must be a relative path with '/' separators"
    if any(seg in ("", ".", "..") for seg in p.split("/")):
        return "must not contain '..', '.' or empty segments"
    return None


def _lint_target(t):
    if not isinstance(t, dict):
        return ["skin.target must be an object"]
    if len(t) != 1:
        return [f"skin.target must have exactly one of {', '.join(TARGET_KEYS)} "
                f"(it has {len(t)} keys)"]
    (k, v), = t.items()
    if k not in TARGET_KEYS:
        return [f"skin.target: unknown key {k!r}"]
    if not isinstance(v, str) or not v:
        return [f"skin.target.{k} must be a non-empty string"]
    if k == "retail" and v not in RETAIL_NAMES and v.lower() not in RETAIL_PL_FILES:
        return [f"skin.target.retail {v!r} is not a retail fighter name or Pl code"]
    return []


def _lint_costume(c, files_dir):
    if not isinstance(c, dict):
        return ["must be an object"]
    p = [f"unknown key {k!r}" for k in c if k not in COSTUME_KEYS]
    if "file" not in c:
        p.append("file is required")
    else:
        err = _unsafe_rel(c["file"])
        if err:
            p.append(f"file {c['file']!r} {err}")
        elif not os.path.isfile(os.path.join(files_dir, *c["file"].split("/"))):
            p.append(f"file {c['file']!r} is not in files/")
    if not isinstance(c.get("joint"), str) or not c.get("joint"):
        p.append("joint must be a non-empty string")
    if "matanim" in c and (not isinstance(c["matanim"], str) or not c["matanim"]):
        p.append("matanim must be a non-empty string")
    if "name" in c and not _valid_name(c["name"]):
        p.append(f"name {c['name']!r} must be printable ASCII, 1..23 characters")
    if "team" in c and c["team"] not in TEAMS:
        p.append(f"team {c['team']!r} must be red, blue or green")
    if "like" in c and not _is_int(c["like"], 0, 254):
        p.append(f"like {c['like']!r} must be an integer 0..254")
    if "kirby_hat" in c and not _is_int(c["kirby_hat"], 0, 5):
        p.append(f"kirby_hat {c['kirby_hat']!r} must be an integer 0..5")
    for key in ("csp", "stock"):
        if key in c:
            err = _unsafe_rel(c[key])
            if err:
                p.append(f"{key} {c[key]!r} {err}")
            elif not os.path.isfile(os.path.join(files_dir, *c[key].split("/"))):
                p.append(f"{key} {c[key]!r} is not in files/")
    return p


def lint_skin_mod(mod_dir):
    """Problems with a skin mod folder, as strings. An empty list means clean."""
    path = os.path.join(mod_dir, "mod.json")
    try:
        with open(path, encoding="utf-8") as fp:
            doc = json.load(fp)
    except FileNotFoundError:
        return [f"no mod.json in {mod_dir}"]
    except (OSError, ValueError) as e:
        return [f"mod.json does not parse: {e}"]
    if not isinstance(doc, dict):
        return ["mod.json is not a JSON object"]

    problems = []
    if doc.get("kind") != "skin":
        problems.append(f'kind is {doc.get("kind")!r}, must be "skin"')
    skin = doc.get("skin")
    if not isinstance(skin, dict):
        problems.append('no "skin" object')
        return problems
    problems += [f"skin: unknown key {k!r}" for k in skin if k not in SKIN_KEYS]
    if not (type(skin.get("format")) is int and skin.get("format") == 1):
        problems.append(f"skin.format is {skin.get('format')!r}, must be 1")
    if "order" in skin and not _is_int(skin["order"]):
        problems.append("skin.order must be an integer")
    problems += _lint_target(skin.get("target"))

    costumes = skin.get("costumes")
    if not isinstance(costumes, list) or not costumes:
        problems.append("skin.costumes must be a non-empty list")
        return problems
    if len(costumes) > MAX_COSTUMES:
        problems.append(f"skin.costumes has {len(costumes)} entries; the cap is {MAX_COSTUMES}")
    files_dir = os.path.join(mod_dir, "files")
    for n, c in enumerate(costumes, 1):
        problems += [f"costume {n}: {p}" for p in _lint_costume(c, files_dir)]
    return problems
