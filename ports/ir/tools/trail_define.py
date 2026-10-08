#!/usr/bin/env python3
"""trail_define.py - an installed Ultimate port (Sora) -> a Geno `define` package (base "none", geno 9).

    python ports/ir/tools/trail_define.py --install <mods>/ultimate-trail-slot --moveset staged-moveset.json \
        --row-clips staged-specials/clips.json --out _build/geno-slice8/ultimate-sora-define

The slice 8 migration step (docs/superpowers/plans/2026-10-08-geno-slice8-migrations.md). It does not rebuild the port: it reads
what install_ultimate.py wrote (the m-ex slot's fighter data file `PlUs.dat`, the costume models, the clip bank, the Geno
`attach` profile, the effect packages) and writes the same fighter as a define:

    geno.json          define header + fighter block (plan, bank, costumes, own rows) + attributes + states + specials +
                       overlays + articles + sounds-free fx_bindings, every row number of the host's stand-in rows remapped
    plan.json -> files/plan.json   joints, Melee parts table, ftData joint fields, 14-15 hurtbox capsules, bank, row clips
    files/GnSora_<c>.dat           the installed costume models (renamed; the symbols inside keep their names)
    files/GnSoraAJ.dat             the installed clip bank, unchanged
    files/GnTrail*.dat             the article models
    moves/*.words                  the translated moves and the specials, one overlay file each
    fx/                            the Geno effect packages and the remapped fx_bindings.json

Nothing here is committed: the output is built from Ultimate data (and the host's thrown-victim clips that the installer
copies into the bank) and goes under _build/ like every install. The package needs no m-ex slot, no ACE disc and no PowerPC.

What is NOT carried (reported in define_report.json): ModelVis expressions, the host's unnamed ftCo_DatAttrs fields,
ECB and IK floats (the donor template's), the CSS/CSP/stock art of the m-ex slot.
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
sys.path.insert(0, os.path.join(ROOT, "tools", "mex_port"))
import mex_hsd  # noqa: E402
import figatree as F  # noqa: E402
import plan_parts  # noqa: E402
import attr_apply  # noqa: E402

WAIT_MOTION = 14                    # ftCo_MS_Wait
MARIO_ROWS = 303                    # a define's donor rows
COMMON_ROWS = 295
HIJACK = range(149, 163)            # Marth's ItemScope rows the Geno magic states used as stand-ins
COLOR_TEAM = {"Re": "red", "Bu": "blue", "Gr": "green"}
COLOR_NAME = {"Nr": "Normal", "Ye": "Yellow", "Bu": "Blue", "Re": "Red", "Gr": "Green", "Wh": "White", "Bk": "Black", "Or": "Orange"}


def game_dir():
    return os.environ.get("GW_MELEE") or os.path.join(ROOT, "melee")


def geno_attr_names():
    """[(name, is_int)] of the engine's common attribute table (geno_game.c geno_attrs[]), in table order."""
    src = open(os.path.join(game_dir(), "pc", "geno", "geno_game.c"), encoding="utf-8", errors="replace").read()
    i = src.index("geno_attrs[] = {")
    blk = src[i:src.index("};", i)]
    return [(n, int(k)) for n, k in re.findall(r"GENO_ATTR\((\w+),\s*(\d)\)", blk)]


def f32(x):
    """shortest decimal that reads back as the same float32"""
    import numpy as np
    return float(np.format_float_positional(np.float32(x), unique=True, trim="-"))


def read_slot(install, host_rows, pl_name):
    """The fighter data file's row table, attribute block and hurtboxes: {rows, attrs, hurt}."""
    raw = open(os.path.join(install, "files", pl_name), "rb").read()
    ar = mex_hsd.Archive(raw)
    fd = ar.public([s for s, _ in ar.publics if s.startswith("ftData")][0])
    mt = ar.u32(fd + 0xC)
    bt = ar.u32(fd + 0x10)          # the per-row blend bytes (ftData x10)
    rows = {}
    for r in range(host_rows):
        o = mt + r * 0x18
        if o in ar.reloc_set and ar.u32(o + 8):
            rows[r] = {"symbol": ar.cstr(ar.u32(o)), "offset": ar.u32(o + 4), "size": ar.u32(o + 8), "flags": ar.u32(o + 0x10),
                        "blend": [ar.data[bt + 2 * r], ar.data[bt + 2 * r + 1]]}
    layout = attr_apply.attr_layout(os.path.join(game_dir(), "src", "melee", "ft", "types.h"))
    block = ar.u32(fd)
    attrs = {}
    for name, (off, is_int) in layout.items():
        attrs[name] = struct.unpack_from(">i" if is_int else ">f", ar.data, block + off)[0]
    x30 = ar.u32(fd + 0x30); n = ar.u32(x30); arr = ar.u32(x30 + 4)
    hurt = []
    for i in range(n):
        o = arr + 0x28 * i
        j, h, g = struct.unpack_from(">3i", ar.data, o)
        v = struct.unpack_from(">7f", ar.data, o + 0xC)
        hurt.append({"joint": j, "height": ("low", "mid", "high")[max(0, min(2, h))], "grabbable": bool(g),
                     "a": [round(x, 5) for x in v[0:3]], "b": [round(x, 5) for x in v[3:6]], "radius": round(v[6], 5)})
    return rows, attrs, hurt


def clip_key(symbol, taken):
    m = re.search(r"_ACTION_(.+)_figatree$", symbol or "")
    base = m.group(1) if m else re.sub(r"\W", "_", symbol or "clip")
    if len(base) > 30:
        base = base[:30]
    key, k = base, 1
    while key in taken and taken[key] != symbol:
        k += 1
        key = "%s~%d" % (base[:26], k)
    return key


def write_words(path, words, header):
    lines = ["# " + header]
    for i in range(0, len(words), 8):
        lines.append(" ".join("0x%08X" % (w & 0xFFFFFFFF) for w in words[i:i + 8]))
    open(path, "w", newline="\n").write("\n".join(lines) + "\n")


def parse_words_file(path):
    ws = []
    for line in open(path, encoding="utf-8"):
        line = line.split("#")[0]
        ws += [int(t, 0) for t in line.split()]
    return ws


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--install", required=True, help="the installed slot folder (mod.json, geno.json, files/, fx/, geno/)")
    ap.add_argument("--moveset", required=True, help="acmd_to_ftcmd.py output the install used (staged-moveset.json)")
    ap.add_argument("--row-clips", required=True, help="trail_specials_geno.py clips.json")
    ap.add_argument("--ir-root", default=os.path.join(ROOT, "_build", "tmp", "ir"))
    ap.add_argument("--fighter", default="trail")
    ap.add_argument("--host", default="marth")
    ap.add_argument("--key", default="ultimate-sora")
    ap.add_argument("--name", default="Ultimate Sora")
    ap.add_argument("--prefix", default="GnSora")
    ap.add_argument("--hide-models", action="store_true", help="keep the old look: an article with an effect package hides its model (default: show_model, so the magic spheres are drawn beside their particles)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out, files = a.out, os.path.join(a.out, "files")
    if os.path.exists(out):
        shutil.rmtree(out)
    for d in (out, files, os.path.join(out, "moves")):
        os.makedirs(d)

    inst = json.load(open(os.path.join(a.install, "INSTALL.json"), encoding="utf-8"))
    old = json.load(open(os.path.join(a.install, "geno.json"), encoding="utf-8"))
    oldmod = json.load(open(os.path.join(a.install, "mod.json"), encoding="utf-8"))
    ent = old["fighters"][0]
    moveset = json.load(open(a.moveset, encoding="utf-8"))["rows"]
    clipdoc = json.load(open(a.row_clips, encoding="utf-8"))
    host_ir = json.load(open(os.path.join(a.ir_root, "%s.melee.ir.json" % a.host), encoding="utf-8"))
    host_rows = len(host_ir["behavior"]["subactions"])
    pl_name = inst["pl"]
    ir = json.load(open(os.path.join(a.ir_root, "%s.ultimate-body.ir.json" % a.fighter), encoding="utf-8"))
    plan = plan_parts.plan(ir)
    assert not plan["unresolved"], plan["unresolved"]

    rows, attrs, hurt = read_slot(a.install, host_rows, pl_name)
    report = {"rows_in_slot": len(rows), "not_carried": []}

    # ---- the clip bank: the installed AJ file, every distinct (symbol, offset, size) a clip
    aj = open(os.path.join(a.install, "files", pl_name[:-4] + "AJ.dat"), "rb").read()
    shutil.copyfile(os.path.join(a.install, "files", pl_name[:-4] + "AJ.dat"), os.path.join(files, a.prefix + "AJ.dat"))
    keys, bank = {}, {}
    for r in sorted(rows):
        s = rows[r]
        k = (s["symbol"], s["offset"], s["size"])
        if k in keys:
            continue
        key = clip_key(s["symbol"], {n: b["symbol"] for n, b in bank.items()})
        keys[k] = key
        frames = F.parse_archive(aj[s["offset"]:s["offset"] + s["size"]])[1]["frames"] + 1
        bank[key] = {"symbol": s["symbol"], "offset": s["offset"], "bytes": s["size"], "frames": frames}
    row_key = {r: keys[(s["symbol"], s["offset"], s["size"])] for r, s in rows.items()}

    # ---- own rows: the host's stand-in rows and everything past the common rows, in numeric order
    sub_clips = {int(k): v for k, v in clipdoc["subaction_clips"].items()}
    state_rows = {s["subaction"] for s in ent["states"]}
    remap_src = sorted(r for r in (set(sub_clips) | state_rows | {ma["subaction"] for ma in ent.get("motion_anims", [])})
                       if r >= COMMON_ROWS or r in HIJACK)
    remap = {r: MARIO_ROWS + i for i, r in enumerate(remap_src)}
    own_clips = []
    for r in remap_src:
        if r not in row_key:
            sys.exit("own row %d (host row) has no clip in the installed table" % r)
        own_clips.append(row_key[r])
    report["own_rows"] = {str(remap[r]): {"host_row": r, "clip": row_key[r]} for r in remap_src}

    # ---- plan.json
    nrow = MARIO_ROWS + len(remap_src)
    row_clips = [None] * COMMON_ROWS
    for r in range(COMMON_ROWS):
        if r in rows and r not in HIJACK:
            row_clips[r] = row_key[r]
    row_flags = [None] * nrow
    for r in range(COMMON_ROWS):
        if r in rows and r not in HIJACK:
            row_flags[r] = rows[r]["flags"] & ~0x3F
    for r in remap_src:
        row_flags[remap[r]] = rows[r]["flags"] & ~0x3F
    row_blend = [None] * nrow
    for r in range(COMMON_ROWS):
        if r in rows and r not in HIJACK:
            row_blend[r] = rows[r]["blend"]
    for r in remap_src:
        row_blend[remap[r]] = rows[r]["blend"]
    plan_json = {
        "scale": 1.0, "joint_count": plan["joint_count"],
        "joints": [{"index": j["index"], "name": j["name"], "parent": j["parent"], "synth": j["synthesized"]} for j in plan["joints"]],
        "parts": plan["parts"], "ftdata": plan["ftdata"],
        "hurtboxes": hurt,
        "bank": {"file": a.prefix + "AJ.dat", "bytes": len(aj), "clips": bank},
        "motion_rows": [{"motion": WAIT_MOTION, "row": "Wait", "clip": row_key[2], "status": "own"}],
        "row_clips": row_clips, "row_flags": row_flags, "row_blend": row_blend,
    }
    json.dump(plan_json, open(os.path.join(files, "plan.json"), "w"), indent=1)

    # ---- costumes
    costumes = []
    for c in inst["costumes"]:
        src = c["file"]                                    # PlUsNr.dat
        color = src[len(pl_name) - 4:-4]
        dst = "%s_%s.dat" % (a.prefix, color)
        shutil.copyfile(os.path.join(a.install, "files", src), os.path.join(files, dst))
        ar = mex_hsd.Archive(open(os.path.join(files, dst), "rb").read())
        syms = [s for s, _ in ar.publics]
        joint = next(s for s in syms if s.endswith("_joint") and "matanim" not in s)
        mat = next((s for s in syms if "matanim" in s), None)
        e = {"file": dst, "joint": joint, "name": COLOR_NAME.get(color, color)}
        if mat:
            e["matanim"] = mat
        if color in COLOR_TEAM:
            e["team"] = COLOR_TEAM[color]
        costumes.append(e)
    for f in os.listdir(os.path.join(a.install, "files")):
        if f.startswith("GnTrail") and f.endswith(".dat"):
            shutil.copyfile(os.path.join(a.install, "files", f), os.path.join(files, f))

    # ---- attributes: every field the engine's table names, read from the installed block (the host's, calibrated)
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
    report["not_carried"].append("%d ftCo_DatAttrs fields have no name in Geno's table (the donor's value stays): %s" % (len(unnamed), ", ".join(unnamed[:12]) + (" ..." if len(unnamed) > 12 else "")))

    # ---- scripts: the translated moveset rows (kept on their common row numbers)
    subs = []
    nwords = 0
    for r in sorted(int(k) for k in moveset):
        m = moveset[str(r)]
        words = [int(w) for w in m["words"]]
        if not words:
            continue
        fn = "moves/%03d_%s.words" % (r, m["name"].lower())
        write_words(os.path.join(out, fn), words, "%s row %d (%s), translated ACMD %s" % (a.fighter, r, m["name"], m["script"]))
        subs.append({"index": r, "file": fn})
        nwords += len(words)
    # ---- the Geno profile's overlays, on their remapped rows
    for s in ent["subactions"]:
        r = s["index"]
        if "words" in s:
            words = [int(w, 0) if isinstance(w, str) else int(w) for w in s["words"]]
        else:
            words = parse_words_file(os.path.join(a.install, s["file"]))
        nr = remap.get(r, r)
        ORIG = 0xED310000   # Geno sub 0x13: continue with the row's original script
        if ORIG in words:
            # the old install's original is the translated moveset row; a define's original is the donor's, so the two are one overlay here
            base = moveset.get(str(r))
            assert base and words[-1] == ORIG and words.count(ORIG) == 1, "ORIG overlay on row %d without a moveset base" % r
            words = words[:-1] + [int(w) for w in base["words"]]
            subs[:] = [x for x in subs if x["index"] != r]
            report.setdefault("merged_orig", []).append(r)
        fn = "moves/%03d_sp.words" % nr
        write_words(os.path.join(out, fn), words, "Geno overlay of host row %d, define row %d" % (r, nr))
        e = {"index": nr, "file": fn}
        if "move_tag" in s:
            e["move_tag"] = s["move_tag"]
        subs.append(e)
        nwords += len(words)
    report["overlays"] = {"count": len(subs), "words": nwords}

    states = []
    for s in ent["states"]:
        s = dict(s)
        s["subaction"] = remap.get(s["subaction"], s["subaction"])
        states.append(s)
    motion_anims = [{"motion": m["motion"], "subaction": remap.get(m["subaction"], m["subaction"])} for m in ent.get("motion_anims", [])]

    # ---- effect packages and the remapped bindings
    shutil.copytree(os.path.join(a.install, "fx"), os.path.join(out, "fx"))
    fxb_path = os.path.join(out, "fx", "fx_bindings.json")
    fxb = json.load(open(fxb_path, encoding="utf-8"))
    for st in fxb["states"]:
        st["subaction"] = remap.get(st["subaction"], st["subaction"])
    json.dump(fxb, open(fxb_path, "w"), indent=1)

    entry = {
        "define": {"key": a.key, "name": a.name, "base": "none", "common": "melee.common.v1", "resources": "mod:files"},
        "fighter": {"plan": "plan.json", "animation": a.prefix + "AJ.dat", "costumes": costumes, "rows": own_clips},
        "attributes": attributes,
        "states": states, "specials": ent["specials"], "subactions": subs,
    }
    if motion_anims:
        entry["motion_anims"] = motion_anims
    arts = json.loads(json.dumps(ent["articles"]))
    for art in arts:
        if art.get("model") and art.get("fx") and not a.hide_models:
            art["show_model"] = True            # geno 5.7: the model stays drawn beside its fx package
        for hb in art.get("hitboxes", []):
            hb.pop("source_id", None)           # a generator note the engine ignores and `check` rejects
    entry["articles"] = arts
    entry["fx_bindings"] = ent["fx_bindings"]
    json.dump({"geno": 9, "fighters": [entry]}, open(os.path.join(out, "geno.json"), "w"), indent=1)

    mod = {"id": a.key + "-define", "name": a.name + " (define)", "version": oldmod.get("version", "0.1.0"), "kind": "fighter",
           "requires": [], "conflicts": [],
           "description": "%s as a Geno define (base none). Local build, not shipped." % a.name}
    if oldmod.get("engine"):
        mod["engine"] = oldmod["engine"]
    json.dump(mod, open(os.path.join(out, "mod.json"), "w"), indent=1)

    report["not_carried"] += ["ModelVis expressions (%s states): the model shows every mesh the costume has" % inst["ftdata"].get("modelvis_states"),
                              "the host's ECB, IK and ledge floats (the donor template's)",
                              "CSS icon, CSP and stock art (presentation .gxtex not generated)"]
    json.dump(report, open(os.path.join(out, "define_report.json"), "w"), indent=1)
    print("trail_define: %d joints, %d clips, %d own rows, %d overlays (%d words), %d states, %d attributes -> %s" %
          (plan["joint_count"], len(bank), len(remap_src), len(subs), nwords, len(states), len(attributes), out))


if __name__ == "__main__":
    main()
