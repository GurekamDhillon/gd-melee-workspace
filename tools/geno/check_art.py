#!/usr/bin/env python3
"""check_art.py - validate an authored fighter's art package before the converter runs (offline, no disc).

    python -m tools.geno.check_art ports/vanilla-original [--json]

The package is a folder with manifest.json (clips, motion_rows, bones, costumes), skeleton.json, hurtboxes.json and
out/courier.glb with out/tex/costume_<name>.png. Every problem is reported with the file and the field, then the exit
status is 1; warnings (stand-in rows, unmapped common parts) do not fail. This is the slice 4 "model/clip/hurtbox
manifest validated at check time" step; the converter is ports/ir/tools/authored_fighter.py (see build_courier.sh).
"""
import argparse
import json
import os
import struct
import sys
from pathlib import Path

ROLES_REQUIRED = ["root", "translation", "hips", "head", "hand", "foot", "item_socket", "grab_anchor", "victim_anchor",
                  "camera_focus", "shield_origin", "head_top"]
MAX_HURT = 15          # FighterHurtCapsule hurt_capsules[15]
MAX_BONES = 255        # MAX_FT_PARTS
MAX_ROWS = 351


def load(p, errs):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        errs.append("%s: cannot read (%s)" % (p, e))
        return None


def glb_json(path, errs):
    try:
        b = open(path, "rb").read()
        n = struct.unpack_from("<I", b, 12)[0]
        return json.loads(b[20:20 + n])
    except Exception as e:  # noqa: BLE001
        errs.append("%s: not a readable .glb (%s)" % (path, e))
        return None


def check(art):
    art = Path(art)
    errs, warns = [], []
    m = load(art / "manifest.json", errs)
    sk = load(art / "skeleton.json", errs)
    hb = load(art / "hurtboxes.json", errs)
    g = glb_json(art / "out" / "courier.glb", errs) if (art / "out" / "courier.glb").exists() else None
    if g is None and not (art / "out" / "courier.glb").exists():
        errs.append("out/courier.glb is missing: run ports/vanilla-original/build_all.sh (headless Blender)")
    if not m or not sk or not hb:
        return errs, warns, {}
    bones = {b["name"]: b for b in m["bones"]}
    if len(bones) > MAX_BONES:
        errs.append("manifest.json bones: %d bones, the engine's part limit is %d" % (len(bones), MAX_BONES))
    roles = {b["role"] for b in m["bones"]}
    for r in ROLES_REQUIRED:
        if r not in roles:
            errs.append("manifest.json bones: required role '%s' has no bone" % r)
    for b in m["bones"]:
        if b["parent"] is not None and b["parent"] not in bones:
            errs.append("manifest.json bones[%s].parent '%s' is not a bone" % (b["name"], b["parent"]))
    clips = {c["name"]: c for c in m["clips"]}
    rows = m["motion_rows"]
    if len(rows) != MAX_ROWS:
        errs.append("manifest.json motion_rows: %d rows, the engine has %d" % (len(rows), MAX_ROWS))
    counts = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
        if r["status"] != "no-animation" and r.get("clip") not in clips:
            errs.append("manifest.json motion_rows[%s] (%s) names clip '%s' which is not in clips" % (r["motion"], r["row"], r.get("clip")))
    for c in m["clips"]:
        if c["frames"] < 2:
            errs.append("manifest.json clips[%s].frames = %d (need at least 2)" % (c["name"], c["frames"]))
        if c["frames"] * 4 > 0x20000:
            errs.append("clip %s is longer than the animation buffer" % c["name"])
    if len(hb["hurtboxes"]) > MAX_HURT:
        errs.append("hurtboxes.json: %d capsules, at most %d" % (len(hb["hurtboxes"]), MAX_HURT))
    seen = set()
    for h in hb["hurtboxes"]:
        if h["id"] in seen:
            errs.append("hurtboxes.json: duplicate id %s" % h["id"])
        seen.add(h["id"])
        if h["bone"] not in bones:
            errs.append("hurtboxes.json[%s].bone '%s' is not a bone of the skeleton" % (h["id"], h["bone"]))
        if not h["radius"] > 0:
            errs.append("hurtboxes.json[%s].radius must be positive" % h["id"])
        if h["height"] not in ("high", "mid", "low"):
            errs.append("hurtboxes.json[%s].height '%s' is not high, mid or low" % (h["id"], h["height"]))
    e = hb.get("ecb", {})
    for k in ("standing", "crouch", "aerial"):
        s = e.get(k)
        if not s:
            errs.append("hurtboxes.json ecb.%s is missing" % k)
        elif not (s["top"] > s["bottom"] and s["left"] < s["right"]):
            errs.append("hurtboxes.json ecb.%s is inverted (top > bottom and left < right required)" % k)
    for c in m["costumes"]:
        t = art / "out" / "tex" / ("costume_%s.png" % c["name"])
        if not t.exists():
            errs.append("costume '%s': %s is missing (build_all.sh writes it)" % (c["name"], t.name))
    if g:
        sk0 = g["skins"][0]
        if len(sk0["joints"]) != len(bones):
            errs.append("courier.glb skin has %d joints, manifest.json lists %d bones" % (len(sk0["joints"]), len(bones)))
        if len(g["meshes"]) != 1 or len(g["meshes"][0]["primitives"]) != 1:
            errs.append("courier.glb must hold one mesh with one primitive (the palette path packs it into one piece)")
        if len(g["animations"]) != len(clips):
            errs.append("courier.glb has %d animations, manifest.json lists %d clips" % (len(g["animations"]), len(clips)))
    if counts.get("placeholder"):
        warns.append("%d motion rows play a placeholder alias clip (the art lane's list of stand-ins)" % counts["placeholder"])
    return errs, warns, {"rows": counts, "clips": len(clips), "bones": len(bones), "hurtboxes": len(hb["hurtboxes"]),
                         "costumes": len(m["costumes"])}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("art")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    errs, warns, info = check(a.art)
    if a.json:
        print(json.dumps({"errors": errs, "warnings": warns, "info": info}, indent=1))
    else:
        for e in errs:
            print("ERROR", e)
        for w in warns:
            print("WARNING", w)
        print(("FAILED: %d error(s)" % len(errs)) if errs else "OK: art package validated %s" % json.dumps(info))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
