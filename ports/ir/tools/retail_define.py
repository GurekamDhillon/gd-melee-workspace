#!/usr/bin/env python3
"""retail_define.py - a RETAIL Melee fighter, read from the user's own disc -> a Geno `define` package (base "none", template <fighter>).

    python ports/ir/tools/retail_define.py captain --disc-dir _build/falcon-geno/disc --out _build/falcon-geno/geno-falcon

The sibling of trail_define.py (which converts an installed Ultimate port) for the case where the source is the game's own fighter files:
PlCa.dat (ftData: attributes, the 318 animation rows and their ftcmd scripts, hurtboxes, joint fields), PlCo.dat (the parts table),
PlCa<colour>.dat (the costume models), PlCaAJ.dat (the animation bank). It writes the same package shape the engine loads for Sora and
the Courier, plus `define.template` so the native code the fighter runs on (his specials, the state table, the callbacks) is the retail
fighter's own, not Mario's:

    geno.json          define header (template), fighter block (plan, bank, costumes), the named attributes, special_attributes,
                       one `subactions` overlay per script row, ai.like and kirby_copy
    files/plan.json    joints, parts table, ftData joint fields, hurtboxes, the bank, a clip and flags and blend bytes for EVERY row
    files/Gn<Name>_<c>.dat   the costume models (renamed copies; the symbols inside keep their names)
    files/Gn<Name>AJ.dat     the animation bank (a renamed copy)
    moves/<row>_<clip>.words the scripts; Subroutine/Goto operands are word indices inside the overlay (geno.md 22.10)

Everything here is disc-derived: the output goes under _build/ (git-ignored), never into a repository. What is NOT carried is listed in
define_report.json (the effect file, the sound bank, the results/intro demo clips, the select art).

Wired: `captain`, `fox` (FIGHTERS below); another retail fighter needs its template in the engine first (geno.md 22.10, 22.13: the checklist).
"""
import argparse
import json
import os
import re
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
from tools.mex_port import mex_hsd  # noqa: E402
import figatree as F  # noqa: E402
import attr_apply  # noqa: E402

# name -> everything that is specific to the fighter
FIGHTERS = {
    "captain": {
        "kind": 2, "code": "Ca", "data": "ftDataCaptain", "rows": 318, "prefix": "GnFalcon", "key": "geno-falcon", "name": "Geno Falcon",
        "motions": 364, "dir": "ftCaptain", "attrs_struct": "ftCaptain_DatAttrs",
        # costume order is the game's (ftCa_Init_CostumeStrings): file code, label, team colour
        "costumes": [("Nr", "Navy", None), ("Gy", "Gray", None), ("Re", "Red", "red"), ("Wh", "White", None), ("Gr", "Green", "green"), ("Bu", "Blue", "blue")],
        "ai": "captain", "kirby": "retail:captain",
    },
    "fox": {
        "kind": 1, "code": "Fx", "data": "ftDataFox", "rows": 327, "prefix": "GnFox", "key": "geno-fox", "name": "Geno Fox",
        "motions": 376, "dir": "ftFox", "attrs_struct": "ftFox_DatAttrs",
        # ftFx_Init_CostumeStrings: Nr, Or, La, Gr (team: red = Or, blue = La, green = Gr)
        "costumes": [("Nr", "Default", None), ("Or", "Orange", "red"), ("La", "Lavender", "blue"), ("Gr", "Green", "green")],
        "ai": "fox", "kirby": "retail:fox",
    },
}
WAIT_MOTION = 14   # ftCo_MS_Wait


def game_dir():
    return os.environ.get("GW_MELEE") or os.path.join(ROOT, "melee")


def f32(x):
    """shortest decimal that reads back as the same float32"""
    import numpy as np
    return float(np.format_float_positional(np.float32(x), unique=True, trim="-"))


def be_f32(ar, off):
    return struct.unpack_from(">f", ar.data, off)[0]


def geno_attr_names():
    src = open(os.path.join(game_dir(), "pc", "geno", "geno_game.c"), encoding="utf-8", errors="replace").read()
    i = src.index("geno_attrs[] = {")
    blk = src[i:src.index("};", i)]
    return [(n, int(k)) for n, k in re.findall(r"GENO_ATTR\((\w+),\s*(\d)\)", blk)]


# structs embedded in a special-attribute block: [(byte offset inside, is_int)]
NESTED = {"ReflectDesc": [(0, True), (4, True), (8, False), (12, False), (16, False), (0x14, False), (0x18, False), (0x1C, False), (0x20, True)]}   # lb/types.h, 0x24 bytes


def ext_layout(struct_name, types_h):
    """[(byte offset, is_int)] of a fighter's special-attribute struct, from the decomp header (every 32-bit field in order). Two comment styles
    exist: `/* +OFF */ type name;` (Captain) and `type xOFF_NAME;` (Fox); an embedded struct listed in NESTED is expanded."""
    src = open(types_h, encoding="utf-8").read()
    i = src.index("struct %s {" % struct_name)
    blk = src[i:src.index("\n};", i)]
    out = []
    pat = re.compile(r"(?:/\*\s*\+(?P<o1>[0-9A-Fa-f]+)\s*\*/\s*(?P<t1>\w+)\s+\w+|\b(?P<t2>[A-Za-z_]\w*)\s+x(?P<o2>[0-9A-F]+)_\w+)\s*;")
    for m in pat.finditer(blk):
        off, ty = (int(m.group("o1"), 16), m.group("t1")) if m.group("o1") else (int(m.group("o2"), 16), m.group("t2"))
        if ty in NESTED:
            out += [(off + o, is_int) for o, is_int in NESTED[ty]]
        elif ty in ("float", "f32"):
            out.append((off, False))
        elif ty in ("s32", "u32", "int", "ItemKind"):
            out.append((off, True))
    return out


# ---- reading PlCa.dat ----------------------------------------------------------------------------------------------

def read_ftdata(ar, spec):
    fd = ar.public(spec["data"])
    n = spec["rows"]
    mt, bt = ar.u32(fd + 0xC), ar.u32(fd + 0x10)
    rows = []
    for r in range(n):
        o = mt + r * 0x18
        row = {"row": r, "flags": ar.u32(o + 0x10), "blend": [ar.data[bt + 2 * r], ar.data[bt + 2 * r + 1]], "symbol": None, "script": None}
        if o in ar.reloc_set and ar.u32(o + 8):
            row.update(symbol=ar.cstr(ar.u32(o)), offset=ar.u32(o + 4), size=ar.u32(o + 8))
        if (o + 0xC) in ar.reloc_set:
            row["script"] = ar.u32(o + 0xC)
        rows.append(row)
    # ftData joint fields
    x8 = ar.u32(fd + 0x8)
    f = {"x8_part_bytes": list(ar.data[x8 + 0x10:x8 + 0x15])}
    x34 = ar.u32(fd + 0x34)
    f["x34_centre"] = [ar.u32(x34)]
    f["x34_scale"] = be_f32(ar, x34 + 4)
    x38 = ar.u32(fd + 0x38)
    f["x38_coin"] = [ar.u32(x38), ar.u32(x38 + 0x14)]
    x44 = ar.u32(fd + 0x44)
    f["x44_ecb"] = list(struct.unpack_from(">6h", ar.data, x44))
    x54 = ar.u32(fd + 0x54)
    f["x54_gfx"] = list(struct.unpack_from(">5i", ar.data, x54))
    x58 = ar.u32(fd + 0x58)
    d = ar.data
    f["x58_ik"] = [d[x58], d[x58 + 1], d[x58 + 8], d[x58 + 9], d[x58 + 0x10], d[x58 + 0x11], 0, 0, 0, 0]   # the plan holds 10; the loader reads the first six
    # hurtboxes
    x30 = ar.u32(fd + 0x30)
    cnt, arr = ar.u32(x30), ar.u32(x30 + 4)
    hurt = []
    for i in range(cnt):
        o = arr + 0x28 * i
        j, h, g = struct.unpack_from(">3i", ar.data, o)
        v = struct.unpack_from(">7f", ar.data, o + 0xC)
        hurt.append({"joint": j, "height": ("low", "mid", "high")[h], "grabbable": g == 1,
                     "a": [f32(x) for x in v[0:3]], "b": [f32(x) for x in v[3:6]], "radius": f32(v[6])})
        assert h in (0, 1, 2) and g in (0, 1), ("hurtbox %d: height %d grabbable %d" % (i, h, g))
    # the attribute blocks
    layout = attr_apply.attr_layout(os.path.join(game_dir(), "src", "melee", "ft", "types.h"))
    block = ar.u32(fd)
    attrs = {}
    for name, (off, is_int) in layout.items():
        attrs[name] = struct.unpack_from(">i" if is_int else ">f", ar.data, block + off)[0]
    ext = ar.u32(fd + 4)
    ftypes = ext_layout(spec["attrs_struct"], os.path.join(game_dir(), "src", "melee", "ft", "kinds", spec["dir"], "types.h"))
    special = []
    for off, is_int in ftypes:
        if is_int:
            special.append({"index": off // 4, "int": struct.unpack_from(">i", ar.data, ext + off)[0]})
        else:
            special.append({"index": off // 4, "float": f32(struct.unpack_from(">f", ar.data, ext + off)[0])})
    return rows, f, hurt, attrs, special


def read_parts(co, kind):
    r = co.public("ftLoadCommonData")
    table = co.u32(co.u32(r + 16) + 4 * kind)
    j2p_at, p2j_at, count = co.u32(table), co.u32(table + 4), co.u32(table + 8)
    j2p = list(co.data[j2p_at:j2p_at + count])
    # the part -> joint array is as long as the highest joint-to-part slot the table names, plus the ones the fighter lacks (255); the
    # game's parts enum has 54 slots (Fighter_Part)
    p2j = list(co.data[p2j_at:p2j_at + 54])
    return j2p, p2j, count


def joint_count(model):
    n = 0

    def walk(off):
        nonlocal n
        while off is not None:
            n += 1
            flags = model.u32(off + 4)
            c = model.u32(off + 8) if (off + 8) in model.reloc_set else None
            if c is not None and not flags & (1 << 12):
                walk(c)
            off = model.u32(off + 0xC) if (off + 0xC) in model.reloc_set else None
    root = model.public([s for s, _ in model.publics if s.endswith("_joint")][0])
    walk(root)
    return n


# ---- scripts -----------------------------------------------------------------------------------------------------

def cmd_len(w0):
    from tools.geno import script
    op = w0 >> 26
    if op == 59:
        return max(1, (w0 >> 16) & 15)
    return script.LENGTHS[op]


def read_overlay(ar, start):
    """The words of one row's script and everything it can reach, as one overlay: the main run first, then every other run (a
    shared subroutine, a goto target) in order of discovery. Subroutine and Goto operands become word indices inside the overlay."""
    seen = {}           # address -> (op, words)
    runs = []           # [first address, ...] of every discovered run, in order
    work = [start]
    while work:
        p = work.pop(0)
        if p in seen:
            continue
        run_first = p
        while p not in seen:
            w0 = ar.u32(p)
            op = w0 >> 26
            if op > 59:
                raise ValueError("unsupported opcode %d at 0x%X" % (op, p))
            n = cmd_len(w0)
            seen[p] = (op, [ar.u32(p + 4 * i) for i in range(n)])
            if op == 5:
                work.append(ar.u32(p + 4))
            if op == 7:
                work.append(ar.u32(p + 4))
                break
            if op in (0, 6):
                break
            p += 4 * n
        runs.append(run_first)
    # lay the runs out
    index, words = {}, []
    for first in runs:
        p = first
        while True:
            op, w = seen[p]
            index[p] = len(words)
            words.extend(w)
            if op in (0, 6, 7):
                break
            p += 4 * len(w)
            if p not in seen:
                raise ValueError("a script falls off its reachable commands at 0x%X" % p)
            if p in index:    # ran into a command another run already laid out: a run must not fall through into one
                raise ValueError("a run falls into an already laid-out command at 0x%X" % p)
    for addr, (op, w) in seen.items():
        if op in (5, 7):
            words[index[addr] + 1] = index[ar.u32(addr + 4)]
    return words


def write_words(path, words, header):
    lines = ["# " + header]
    for i in range(0, len(words), 8):
        lines.append(" ".join("0x%08X" % (w & 0xFFFFFFFF) for w in words[i:i + 8]))
    open(path, "w", newline="\n").write("\n".join(lines) + "\n")


def clip_keys(rows):
    """a unique short key (<= 31 chars) per distinct (symbol, offset, size)"""
    keys, used = {}, {}
    for r in rows:
        if r["symbol"] is None:
            continue
        k = (r["symbol"], r["offset"], r["size"])
        if k in keys:
            continue
        m = re.search(r"_ACTION_(.+)_figatree$", r["symbol"])
        base = (m.group(1) if m else re.sub(r"\W", "_", r["symbol"]))[:26]
        key, n = base, 1
        while key in used:
            n += 1
            key = "%s~%d" % (base, n)
        used[key] = k
        keys[k] = key
    return keys


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fighter", choices=sorted(FIGHTERS))
    ap.add_argument("--disc-dir", required=True, help="a folder holding the fighter's Pl*.dat files and PlCo.dat (tools/gc_extract.py --only PlCa / PlCo)")
    ap.add_argument("--out", required=True, help="fresh output folder (under a git-ignored _build/)")
    ap.add_argument("--key", help="define key (default: the fighter's)")
    ap.add_argument("--name", help="display name")
    ap.add_argument("--red-file", default="usd", choices=("usd", "dat"), help="the red costume of Captain Falcon exists as PlCaRe.usd (English) and PlCaRe.dat (Japanese)")
    ap.add_argument("--no-scripts", action="store_true", help="do not write script overlays (the template's scripts run)")
    a = ap.parse_args()
    spec = FIGHTERS[a.fighter]
    out = os.path.abspath(a.out)
    if "_build" not in out.replace("\\", "/").split("/"):
        ap.error("the output holds disc-derived data and must be below a _build/ folder")
    if os.path.exists(out) and os.listdir(out):
        ap.error("output folder is not empty")
    files = os.path.join(out, "files")
    os.makedirs(files, exist_ok=True)
    os.makedirs(os.path.join(out, "moves"), exist_ok=True)
    code, prefix = spec["code"], spec["prefix"]
    d = a.disc_dir

    pl = mex_hsd.Archive(open(os.path.join(d, "Pl%s.dat" % code), "rb").read())
    co = mex_hsd.Archive(open(os.path.join(d, "PlCo.dat"), "rb").read())
    rows, jf, hurt, attrs, special = read_ftdata(pl, spec)
    j2p, p2j, nparts_j = read_parts(co, spec["kind"])
    report = {"not_carried": []}

    # ---- costumes
    costumes, first_model = [], None
    for color, label, team in spec["costumes"]:
        src = "Pl%s%s.%s" % (code, color, a.red_file if color == "Re" else "dat")
        dst = "%s_%s.dat" % (prefix, color)
        shutil.copyfile(os.path.join(d, src), os.path.join(files, dst))
        model = mex_hsd.Archive(open(os.path.join(files, dst), "rb").read())
        syms = [s for s, _ in model.publics]
        joint = next(s for s in syms if s.endswith("_joint") and "matanim" not in s)
        e = {"file": dst, "joint": joint, "name": label}
        mat = next((s for s in syms if "matanim" in s), None)
        if mat:
            e["matanim"] = mat
        if team:
            e["team"] = team
        costumes.append(e)
        first_model = first_model or model
    nj = joint_count(first_model)
    if nj != nparts_j:
        sys.exit("the model has %d joints, the parts table says %d" % (nj, nparts_j))

    # ---- the bank
    aj_name = "Pl%sAJ.dat" % code
    aj = open(os.path.join(d, aj_name), "rb").read()
    shutil.copyfile(os.path.join(d, aj_name), os.path.join(files, prefix + "AJ.dat"))
    keys = clip_keys(rows)
    bank = {}
    for (sym, off, size), key in keys.items():
        frames = F.parse_archive(aj[off:off + size])[1]["frames"] + 1
        bank[key] = {"symbol": sym, "offset": off, "bytes": size, "frames": frames}
    row_key = {r["row"]: keys[(r["symbol"], r["offset"], r["size"])] for r in rows if r["symbol"] is not None}

    # ---- plan.json
    wait_row = next(r for r in rows if r["row"] == 2)   # placeholder, replaced below by the motion table's Wait row
    plan = {
        "scale": 1.0, "joint_count": nj,
        "joints": [{"index": i, "name": "j%d" % i, "parent": None, "synth": False} for i in range(nj)],
        "parts": {"parts_num": nj, "joint_to_part": j2p, "part_to_joint": p2j},
        "ftdata": {k: [{"joint": v} for v in jf[k]] for k in ("x8_part_bytes", "x34_centre", "x38_coin", "x44_ecb", "x54_gfx", "x58_ik")},
        "hurtboxes": hurt,
        "bank": {"file": prefix + "AJ.dat", "bytes": len(aj), "clips": bank},
        "motion_rows": [],     # filled below: the Wait motion's clip
        "row_clips": [row_key.get(r["row"]) for r in rows],
        "row_flags": [(r["flags"] & ~0x3F) if r["symbol"] is not None else None for r in rows],
        "row_blend": [r["blend"] if r["symbol"] is not None else None for r in rows],
    }
    json.dump(plan, open(os.path.join(files, "plan.json"), "w"), indent=1)

    # ---- attributes
    named = geno_attr_names()
    attributes, missing = {}, []
    for n, is_int in named:
        if n not in attrs:
            missing.append(n)
            continue
        attributes[n] = int(attrs[n]) if is_int else f32(attrs[n])
    report["attributes"] = {"carried": len(attributes), "table": len(named), "not_in_struct": missing}
    unnamed = sorted(set(attrs) - {n for n, _ in named})
    report["attributes_not_carried"] = unnamed

    # ---- scripts
    subs, nwords, skipped = [], 0, []
    if not a.no_scripts:
        for r in rows:
            if r["script"] is None:
                continue
            try:
                words = read_overlay(pl, r["script"])
            except ValueError as e:
                skipped.append({"row": r["row"], "why": str(e)})
                continue
            nm = (re.search(r"_ACTION_(.+)_figatree$", r["symbol"] or "") or [None, "row"])[1] if r["symbol"] else "row"
            fn = "moves/%03d_%s.words" % (r["row"], re.sub(r"\W", "_", nm).lower())
            write_words(os.path.join(out, fn), words, "%s row %d (%s): the retail script, branches as word indices" % (a.fighter, r["row"], nm))
            subs.append({"index": r["row"], "file": fn})
            nwords += len(words)
    report["overlays"] = {"count": len(subs), "words": nwords, "skipped": skipped}

    entry = {
        "define": {"key": a.key or spec["key"], "name": a.name or spec["name"], "base": "none", "common": "melee.common.v1", "resources": "mod:files",
                   "template": a.fighter},
        "fighter": {"plan": "plan.json", "animation": prefix + "AJ.dat", "costumes": costumes},
        "attributes": attributes,
        "special_attributes": special,
        "subactions": subs,
        "ai": {"like": spec["ai"]},
        "kirby_copy": spec["kirby"],
    }
    json.dump({"geno": 10, "fighters": [entry]}, open(os.path.join(out, "geno.json"), "w"), indent=1)
    mod = {"id": (a.key or spec["key"]), "name": a.name or spec["name"], "version": "0.1.0", "kind": "fighter", "requires": [], "conflicts": [],
           "description": "%s: a retail fighter as a standalone Geno define, built from your own disc. Local only." % spec["name"]}
    json.dump(mod, open(os.path.join(out, "mod.json"), "w"), indent=1)
    report["not_carried"] += [
        "the fighter's effect file (EfCa*.dat) and sound bank: scripts name them by id; the engine cannot mount a mod's copy",
        "the results/intro demo clips (the define's demo rows pose with its Wait clip)",
        "the select icon, portrait and stock art (the letters fallback)",
    ]
    json.dump(report, open(os.path.join(out, "define_report.json"), "w"), indent=1)
    print("retail_define %s: %d joints, %d hurtboxes, %d clips, %d overlays (%d words, %d skipped), %d attributes, %d special words -> %s" %
          (a.fighter, nj, len(hurt), len(bank), len(subs), nwords, len(skipped), len(attributes), len(special), out))


if __name__ == "__main__":
    main()
