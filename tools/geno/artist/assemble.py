"""assemble.py - the define folder around the built files: moves retargeted by ROLE, geno.json, mod.json, files/.

A base "none" fighter needs a move set. The default is the Striker's 32 move scripts (the game repo's pc/geno/mods/vanilla-striker, written
against Mario's skeleton): every `joint=N` becomes the joint that plays the same ROLE on this character (data/mario_joint_roles.json,
with a fallback chain for roles the skeleton lacks), sizes and offsets scale with the character's height, and the animation rate is set
to 1.0 (clips are authored for rate 1.0). `moves.hitboxes` / `moves.delay` in fighter.json override per hitbox, by joint NAME,
exactly like the Courier's retarget.json.
"""
import json
import os
import re
import shutil
import subprocess
import sys

from . import spec
from .model import ArtistError

FALLBACK = {"fingers.L": ["hand.L", "lower_arm.L"], "fingers.R": ["hand.R", "lower_arm.R"], "thumb.L": ["hand.L", "lower_arm.L"],
            "thumb.R": ["hand.R", "lower_arm.R"], "hand.L": ["lower_arm.L"], "hand.R": ["lower_arm.R"], "toe.L": ["foot.L"],
            "toe.R": ["foot.R"], "shoulder.L": ["chest", "spine"], "shoulder.R": ["chest", "spine"], "neck": ["chest", "spine", "head"],
            "chest": ["spine", "hips"], "spine": ["hips"], "foot.L": ["lower_leg.L"], "foot.R": ["lower_leg.R"]}


def joint_map(plan):
    """Mario/Striker joint index -> this character's plan joint index, by role."""
    names = {j["name"]: j["index"] for j in plan["joints"]}
    roles = {k: v[0] for k, v in plan["roles"].items()}
    out, notes = {}, []
    for idx, role in spec.mario_joint_roles().items():
        if role in ("TopN", "XRotN", "YRotN"):
            out[idx] = names[role]
            continue
        cand = [role] + FALLBACK.get(role, [])
        for c in cand:
            if c in roles:
                out[idx] = roles[c]
                if c != role:
                    notes.append("role %s is missing: hitboxes on it use %s" % (role, c))
                break
        else:
            out[idx] = names["TopN"]
            notes.append("role %s is missing: its hitboxes sit on TopN" % role)
    return out, sorted(set(notes))


def _apply_delay(text, n):
    if n <= 0:
        return text
    lines = text.split("\n")
    first = next((i for i, l in enumerate(lines) if l.startswith("hitbox slot=")), None)
    if first is None:
        return text
    pre = next((i for i in range(first - 1, -1, -1) if re.match(r"wait \d+$", lines[i])), None)
    last = first
    while last + 1 < len(lines) and lines[last + 1].startswith("hitbox slot="):
        last += 1
    post = next((i for i in range(last + 1, len(lines)) if re.match(r"wait \d+$", lines[i])), None)
    if pre is None or post is None:
        return text
    lines[pre] = "wait %d" % (int(lines[pre].split()[1]) + n)
    lines[post] = "wait %d" % max(1, int(lines[post].split()[1]) - n)
    return "\n".join(lines)


def _fmt(x):
    return ("%.3f" % x).rstrip("0").rstrip(".") or "0"


def retarget_script(text, jm, move, ov_all, delay, scale, names):
    ov = ov_all.get(move, {})
    state = {"n": -1}

    def line(m):
        txt = m.group(0)
        state["n"] += 1
        o = ov.get(str(state["n"]))
        jn = re.search(r"joint=(\d+)", txt)
        if jn is None:
            return txt
        n = int(jn.group(1))
        if n in jm:
            txt = txt.replace(jn.group(0), "joint=%d" % jm[n], 1)
        for k in ("size", "x", "y", "z"):
            mm = re.search(r" %s=(-?[0-9.]+)" % k, txt)
            if mm:
                txt = txt.replace(mm.group(0), " %s=%s" % (k, _fmt(float(mm.group(1)) * scale)), 1)
        if o:
            if "joint" in o:
                if o["joint"] not in names:
                    raise ArtistError("fighter.json moves.hitboxes: joint '%s' is not in the skeleton" % o["joint"])
                txt = re.sub(r"joint=\d+", "joint=%d" % names[o["joint"]], txt, count=1)
            for k in ("x", "y", "z", "size"):
                if k in o:
                    if re.search(r" %s=" % k, txt):
                        txt = re.sub(r" %s=-?[0-9.]+" % k, " %s=%s" % (k, o[k]), txt, count=1)
                    else:
                        txt = txt.replace(" angle=", " %s=%s angle=" % (k, o[k]), 1)
        return txt

    text = re.sub(r"(?m)^hitbox slot=.*$", line, text)
    text = _apply_delay(text, int(delay.get(move, 0)))
    return re.sub(r"(?m)^PUT ANIM_RATE\s+[0-9.]+", "PUT ANIM_RATE 1.0", text)


def assemble(f, build_dir, mod_dir, hitbox_scale, ref_speeds, log=print):
    """Write mod_dir (mod.json, geno.json, moves/, files/) from the files built into build_dir."""
    plan = json.load(open(os.path.join(build_dir, "plan.json"), encoding="utf-8"))
    striker = os.path.join(spec.game_dir(), "pc", "geno", "mods", "vanilla-striker")
    if not os.path.isdir(os.path.join(striker, "moves")):
        raise ArtistError("the Striker move set was not found at %s (set GW_MELEE to the game checkout)" % striker)
    jm, notes = joint_map(plan)
    names = {j["name"]: j["index"] for j in plan["joints"]}
    mv = f.cfg.get("moves", {})
    if os.path.isdir(mod_dir):
        shutil.rmtree(mod_dir)
    os.makedirs(os.path.join(mod_dir, "moves"))
    os.makedirs(os.path.join(mod_dir, "files"))
    root = spec.workspace_root()
    n = 0
    for fn in sorted(os.listdir(os.path.join(striker, "moves"))):
        if not fn.endswith(".genoasm"):
            continue
        src = open(os.path.join(striker, "moves", fn), encoding="utf-8").read()
        dst = os.path.join(mod_dir, "moves", fn)
        open(dst, "w", encoding="utf-8", newline="\n").write(
            retarget_script(src, jm, fn[:-8], mv.get("hitboxes", {}), mv.get("delay", {}), hitbox_scale, names))
        r = subprocess.run([sys.executable, "-m", "tools.geno.asm", dst, "-o", dst[:-8] + ".words", "--words"], cwd=root, capture_output=True, text=True)
        if r.returncode:
            raise ArtistError("move %s does not assemble: %s" % (fn, (r.stdout + r.stderr).strip()[-300:]))
        n += 1
    sj = json.load(open(os.path.join(striker, "geno.json"), encoding="utf-8"))["fighters"][0]
    dflt = json.load(open(os.path.join(spec.DATA, "default_attributes.json"), encoding="utf-8"))
    attrs = dict(dflt["attributes"])
    attrs["model_scaling"] = 1.0
    ws, wm, wf, run = (ref_speeds.get(k) for k in ("WalkSlow", "WalkMiddle", "WalkFast", "Run"))
    mid = wm or ws or wf
    if mid:
        attrs["slow_walk_max"] = round(ws or mid * 0.58, 3)
        attrs["mid_walk_point"] = round(mid, 3)
        attrs["fast_walk_min"] = round(wf or mid * 1.44, 3)
    if run:
        attrs["run_animation_scaling"] = round(run, 3)
    attrs.update(f.cfg.get("attributes", {}))
    low = f.token.lower()
    costumes = []
    for c in f.costumes:
        e = {"file": "Gn%s_%s.dat" % (f.token, c["name"]), "joint": low + "_joint", "matanim": low + "_matanim", "name": c["label"]}
        if c["team"]:
            e["team"] = c["team"]
        costumes.append(e)
    fighter = {"define": {"key": f.key, "name": f.name, "base": "none", "common": "melee.common.v1", "resources": "mod:files"},
               "fighter": {"plan": "plan.json", "animation": "Gn%sAJ.dat" % f.token, "costumes": costumes},
               "ai": dflt["ai"], "kirby_copy": dflt["kirby_copy"], "attributes": attrs, "jumps": dflt["jumps"],
               "special_attributes": dflt["special_attributes"]}
    for k in ("states", "specials", "subactions"):
        fighter[k] = sj[k]
    if f.cfg.get("jumps"):
        fighter["jumps"] = f.cfg["jumps"]
    json.dump({"geno": 10, "fighters": [fighter]}, open(os.path.join(mod_dir, "geno.json"), "w", encoding="utf-8", newline="\n"), indent=2)
    open(os.path.join(mod_dir, "geno.json"), "a").write("\n")
    json.dump({"id": f.key, "name": f.name, "version": "0.1.0", "kind": "fighter", "engine": {"pobj_palette": 1}},
              open(os.path.join(mod_dir, "mod.json"), "w", encoding="utf-8", newline="\n"), indent=2)
    for fn in os.listdir(build_dir):
        if re.match(r"Gn%s(_.*\.dat|AJ\.dat)$" % re.escape(f.token), fn) or fn == "plan.json":
            shutil.copy2(os.path.join(build_dir, fn), os.path.join(mod_dir, "files", fn))
    return n, notes
