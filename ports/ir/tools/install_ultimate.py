#!/usr/bin/env python3
"""install_ultimate.py - an Ultimate fighter as an m-ex slot mod on its OWN skeleton (Kirby-clone host).

    python ports/ir/tools/install_ultimate.py kirby [--name "Ultimate Kirby"] [--pl PlUk.dat]
            [--dst-k 52 --dst-e 51] [--out _build/tmp/ultimate-mods/ultimate-kirby-slot]

The generic counterpart of Halberd's install_mk.py, driven by the IR tools instead of hand tables:

 1. slot files (Halberd's mk_slot_files.py, parameterised): MxDt row dst-k/dst-e becomes a clone of
    Kirby (internal/external 4) named --name with pl file --pl; PlCo / MnSlChr / IfAll to match.
    Row 52/51 is the one Meta Knight uses (it replaces ACE's duplicate "Wolf SSBU"): every added
    fighter displaces an ACE fighter while the port has 31 m-ex slots, so this mod and
    metaknight-slot are mounted one at a time.
 2. <pl> = the ACE disc's PlKb.dat: Kirby's fighter data and scripts are the host behaviour.
 3. costume: export_ultimate_mesh.py + fighterbuild (every costume row -> the c00 model).
 4. animations: convert_ultimate_anim.py per clip into <pl stem>AJ.dat; every motion row that has
    a clip is pointed at the Ultimate clip of the same action name (Melee 'AttackS4S' = Ultimate
    'c03attacks4s'); rows with no match play the fallback (wait1) and are listed.
 5. ftData joint fields from plan_parts.py: part bytes, centre, coin spheres, ECB, GFX, IK; the
    host's hurtboxes moved onto the fighter's joints by role; x20 / x5C joint trees; x1C part
    anims parked on a mesh-less joint (as install_mk.py does for Meta Knight).
 6. script bones: Kirby's scripts name Kirby PART SLOTS; each goes to the fighter's joint with the
    same common part, else to the nearest joint by rest position (uniform scale fitted on the
    common parts). Hurtbox-state bones go to the nearest hurtbox bone up the chain.
 7. PlCo parts table for dst-k from the plan; placeholder slots [5] -> NULL.
 8. expressions: Ultimate shows and hides whole meshes (faces, eyes) through each animation's
    Visibility group over a base layer (a00defaulteyelid). Every distinct visible set becomes a
    state of ModelVis model 0; each row starts in its clip's frame-0 state (a ModelVis command
    prepended to the row's script). Changes later in a clip and the base layer's blinks are not
    carried yet; the report counts the rows that have them.

Nothing here is Kirby-specific except the host (Kirby's fighter data and scripts), which is what a
Kirby-clone m-ex slot runs. Output is disc-derived and goes under _build/tmp (git-ignored).
"""
import argparse
import glob
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys

import numpy as np
from scipy.spatial.transform import Rotation

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import convert_ultimate_anim as CA  # noqa: E402
import export_ultimate_mesh as EM  # noqa: E402
import figatree as F  # noqa: E402
import plan_parts  # noqa: E402

ROOT = CA.ROOT
sys.path.insert(0, os.path.join(ROOT, "tools", "mex_port"))
import mex_hsd  # noqa: E402

ISO_ACE = "C:/iso/SSBM ACE Build v2.0.0.iso"   # mk_slot_files.py reads this path too
HALBERD = os.path.join(ROOT, "ports", "halberd")
KIRBY_INTERNAL = 4
FLOW_LEN = [1, 1, 1, 1, 1, 2, 1, 2, 1, 1]
OP_LEN = [5, 5, 1, 1, 1, 1, 1, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 1, 1, 1, 7, 4, 1, 1, 1, 1,
          1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 3, 2, 1, 4]   # ftaction.c ftAction_803C0870, ops 10..58


class Writer:
    """Append-only HSD archive editor (install_mk.py's): data grows at the end, relocations rebuilt."""
    def __init__(self, raw):
        self.ar = mex_hsd.Archive(raw); self.data = bytearray(self.ar.data); self.relocs = set(self.ar.reloc_offsets)
    def u32(self, o): return struct.unpack(">I", self.data[o:o + 4])[0]
    def put(self, o, v): self.data[o:o + 4] = struct.pack(">I", v & 0xFFFFFFFF)
    def ptr(self, o, target):
        if target: self.put(o, target); self.relocs.add(o)
        else: self.put(o, 0); self.relocs.discard(o)
    def alloc(self, b, align=4):
        while len(self.data) % align: self.data.append(0)
        at = len(self.data); self.data.extend(b); return at
    def cstr(self, s): return self.alloc(s.encode() + b"\0", 4)
    def str_at(self, o): return self.data[o:self.data.index(b"\0", o)].decode("latin1")
    def save(self, path):
        while len(self.data) % 4: self.data.append(0)
        rel = sorted(self.relocs); tail = self.ar.raw[self.ar.o_public:]
        body = bytes(self.data) + b"".join(struct.pack(">I", r) for r in rel) + tail
        hdr = struct.pack(">5I", 0x20 + len(body), len(self.data), len(rel), self.ar.nb_public, self.ar.nb_extern) + self.ar.raw[0x14:0x20]
        open(path, "wb").write(hdr + body)


# ------------------------------------------------------------------ fighter model: joints and positions
def fighter_joints(plan, rest):
    """Plan joints with rest SRT (synthesized: identity) and rest world positions."""
    out, world = [], []
    for j in plan["joints"]:
        if j["synthesized"]:
            t, e, s = np.zeros(3), np.zeros(3), np.ones(3); m = np.eye(4)
        else:
            t, r, s, e = rest[j["name"]]
            m = np.eye(4); m[:3, :3] = r.as_matrix() @ np.diag(s); m[:3, 3] = t
        w = world[j["parent"]] @ m if j["parent"] is not None else m
        world.append(w)
        out.append({"name": j["name"], "parent": j["parent"], "trans": list(map(float, t)),
                    "rot": list(map(float, e)), "scale": list(map(float, s)), "pos": w[:3, 3]})
    return out


def joint_tree(w, J):
    """HSD_Joint tree (0x40 per joint, depth-first = plan order), rest SRT, classical scale."""
    offs = [w.alloc(bytes(0x40), 4) for _ in J]
    kids = {i: [k for k, j in enumerate(J) if j["parent"] == i] for i in range(len(J))}
    for i, j in enumerate(J):
        o = offs[i]
        w.put(o + 4, 1 << 3)
        if kids[i]: w.ptr(o + 8, offs[kids[i][0]])
        sib = kids[j["parent"]] if j["parent"] is not None else [i]
        k = sib.index(i)
        if k + 1 < len(sib): w.ptr(o + 0xC, offs[sib[k + 1]])
        w.data[o + 0x14:o + 0x38] = struct.pack(">9f", *j["rot"], *j["scale"], *j["trans"])
    return offs[0]


# ------------------------------------------------------------------ host (Melee Kirby) joint spaces
def host_slot_map(fj, plan):
    """Kirby part slot -> fighter joint: same common part, else nearest by rest position."""
    host = json.load(open(os.path.join(CA.INSTANCES, "kirby.melee.ir.json"), encoding="utf-8"))["assets"]["skeletons"][0]
    hw = []
    for j in host["joints"]:
        r = j["rest"]; m = np.eye(4)
        m[:3, :3] = Rotation.from_euler("xyz", r["rotation_euler_rad"]).as_matrix() @ np.diag(r["scale"])
        m[:3, 3] = r["translation"]
        hw.append(hw[j["parent"]] @ m if j["parent"] is not None else m)
    hpos = [m[:3, 3] for m in hw]
    slots = host["engine"]["melee.gc"]["part_slots"]
    joint_of = {}
    for ci, c in enumerate(plan_parts.COMMON):
        p2j = plan["parts"]["part_to_joint"][ci]
        if p2j != 255:
            joint_of[c] = p2j
    pairs = [(hpos[s["joint"]], fj[joint_of[s["common_part"]]]["pos"]) for s in slots
             if s["common_part"] in joint_of and not plan["joints"][joint_of[s["common_part"]]]["synthesized"]]
    P = np.array([a for a, _ in pairs]); Q = np.array([b for _, b in pairs])
    scale = float((P * Q).sum() / (Q * Q).sum())          # host units per fighter unit
    fpos = np.array([j["pos"] for j in fj]) * scale
    real = [i for i, j in enumerate(plan["joints"]) if not j["synthesized"]]
    slot_to_joint, how = {}, {"by_role": 0, "by_position": 0}
    for s in slots:
        c = s["common_part"]
        if c in joint_of:
            slot_to_joint[s["part_slot"]] = joint_of[c]; how["by_role"] += 1
        else:
            d = np.linalg.norm(fpos[real] - hpos[s["joint"]], axis=1)
            slot_to_joint[s["part_slot"]] = real[int(np.argmin(d))]; how["by_position"] += 1
    return slot_to_joint, scale, how


# ------------------------------------------------------------------ Kirby-host script bones
def remap_scripts(w, fd, slot_to_joint, hurt_bones, J):
    def to_hurt(j):
        while j is not None and j not in hurt_bones: j = J[j]["parent"]
        return j if j is not None else min(hurt_bones)
    mt = w.u32(fd + 0xC)
    starts = [w.u32(mt + r * 0x18 + 0xC) for r in range(479) if (mt + r * 0x18 + 0xC) in w.relocs]
    done = set(); st = {"hitbox": 0, "gfx": 0, "hurt_state": 0, "wind": 0, "texanim_dropped": 0, "unmapped": 0}
    def walk(o):
        while o not in done and o + 4 <= len(w.data):
            done.add(o); word = w.u32(o); op = word >> 26
            if op < 10:
                if op in (0, 6): return
                if op in (5, 7):
                    t = w.u32(o + 4) if (o + 4) in w.relocs else 0
                    if t: walk(t)
                    if op == 7: return
                o += 4 * FLOW_LEN[op]; continue
            if op - 10 >= len(OP_LEN): return
            def sub(shift, key, conv=lambda j: j):
                b = (word >> shift) & 0xFF
                nb = slot_to_joint.get(b)
                if nb is None: st["unmapped"] += 1; nb = 0
                w.put(o, (word & ~(0xFF << shift)) | (conv(nb) << shift)); st[key] += 1
            if op == 11 and not (word >> 10) & 1: sub(11, "hitbox")
            elif op == 10 and not (word >> 17) & 1 and not (word >> 15) & 1: sub(18, "gfx")
            elif op == 28: sub(18, "hurt_state", to_hurt)
            elif op == 58: sub(0, "wind")
            elif op == 31:
                # the host's ModelVis names the host model's groups (Kirby's); the ported model's
                # model 0 is the expression states, set from the clips' Visibility (merge_vis)
                w.put(o, 1 << 26); st["modelvis_dropped"] = st.get("modelvis_dropped", 0) + 1
            elif op == 40:
                # SetTexAnim drives the host's costume texture anims (Kirby's Melee eyes). The ported
                # model has none (its expressions are meshes, ModelVis), and with no costume TObjs
                # the command asserts "texture no exist" (ftAnim_80070458): a SyncWait 0 instead.
                w.put(o, 1 << 26); st["texanim_dropped"] += 1
            o += 4 * OP_LEN[op - 10]
    for s_ in starts: walk(s_)
    st["commands_seen"] = len(done)
    return st


# ------------------------------------------------------------------ Melee motion row -> Ultimate clip
# Melee common motion -> Ultimate action, where the names differ outright (Melee's common motion names
# are shared by every fighter, so this table is not Kirby's). Choices, not facts: 'Landing' is the
# normal landing, which Ultimate plays as landingheavy after a full fall.
ALIAS = {"landing": "landingheavy", "attack100loop": "attack100", "attack100end": "attack100",
         # charge-start specials whose Ultimate clip carries 'start' (Kirby's inhale); only used when
         # the fighter has no clip of the exact name (Mario's SpecialN is his own 'specialn')
         "specialn": "specialnstart", "specialairn": "specialairnstart",
         "eat": "specialneat"}
COPY_ROW = re.compile(r"^(Mr|Lk|Ss|Ys|Fx|Pk|Lg|Ca|Ns|Kp|Pe|Pp|Dk|Zd|Sk|Pr|Ms|Mt|Gw|Dr|Cl|Fc|Pc|Gn|Fe|Gk|Sd)Special|^T[A-Z]")


def match_clip(act, by_key):
    """The Ultimate clip playing Melee motion `act`. Ultimate names clips '<group letter><2 digits>
    <action>' in lower case; the rules below cover the naming differences seen on Kirby, in order,
    and every non-exact pick is reported. Copy-ability and thrown-victim rows are not guessed."""
    if not act:
        return None, None
    k = act.lower()
    if k in by_key:
        return by_key[k], "exact"
    if COPY_ROW.match(act):
        return None, None
    if k in ALIAS and ALIAS[k] in by_key:
        return by_key[ALIAS[k]], "alias"
    bases = [("", k)] + ([("metal row, ", re.sub(r"met$", "", k))] if k.endswith("met") else [])
    if re.search(r"(quick|slow)\d?$", k):         # CliffAttackQuick / CliffJumpSlow1: Melee splits by damage
        bases.append(("quick/slow merged, ", re.sub(r"(quick|slow)(\d?)$", r"\2", k)))
    for pre, b in bases:                          # JumpAerialF2Met -> jumpaerialf2, F1Met -> jumpaerialf
        for how_, t in (("same name", b), ("no trailing 1", re.sub(r"1$", "", b)),   # SquatWait1 -> squatwait
                        ("left variant", b + "l"),                                  # RunBrake -> runbrakel
                        ("no trailing digit", re.sub(r"\d+$", "", b))):
            if t in by_key:
                return by_key[t], pre + how_
    import difflib
    close = difflib.get_close_matches(k, list(by_key), n=1, cutoff=0.9)   # 0.85 took SpecialN -> specials
    return (by_key[close[0]], "closest name") if close else (None, None)


# ------------------------------------------------------------------ visibility -> ModelVis
def merge_vis(w, src, events, frames, rep):
    """A copy of script `src` with ModelVis(0, state) at each event frame: Halberd's apply_vis
    (install_mk.py), which splits timers so a command lands on its frame. Frames after a loop,
    subroutine or animation-rate command are placed approximately (reported); events after a Goto
    are dropped (counted). A row with no script gets one made of the events alone."""
    MV = lambda i, v: (31 << 26) | ((i & 0x7F) << 19) | (v & 0x7FFFF)
    if src is None:
        ws, fr = [], 0
        for f, v in events:
            if f > fr: ws.append((2 << 26) | f); fr = f
            ws.append(MV(0, v))
        return w.alloc(b"".join(struct.pack(">I", x) for x in ws + [0]))
    words, pend, frame, approx, o, seen = [], list(events), 0, False, src, 0
    def emit_until(f_lim, timer_async):
        nonlocal frame
        while pend and pend[0][0] < f_lim:
            f, v = pend.pop(0)
            if f > frame:
                words.append((((2 << 26) | f) if timer_async else ((1 << 26) | (f - frame)), False)); frame = f
            words.append((MV(0, v), False))
    while seen < 4000:
        seen += 1
        word = w.u32(o); op = word >> 26
        while pend and pend[0][0] <= frame:
            f, v = pend.pop(0); words.append((MV(0, v), False))
        if op == 0:
            emit_until(frames, True); words.append((word, False)); break
        if op == 1:
            n = word & 0x3FFFFFF; start = frame
            emit_until(start + n, False)
            if frame < start + n: words.append(((1 << 26) | (start + n - frame), False))
            frame = start + n; o += 4; continue
        if op == 2:
            n = word & 0x3FFFFFF
            emit_until(n, True); words.append((word, False)); frame = max(frame, n); o += 4; continue
        if op == 7:
            rep["dropped_after_goto"] += len(pend); pend = []
            words.append((word, False)); words.append((w.u32(o + 4), (o + 4) in w.relocs)); break
        if op in (3, 4, 5, 8): approx = True
        ln = FLOW_LEN[op] if op < 10 else (OP_LEN[op - 10] if op - 10 < len(OP_LEN) else 1)
        for k in range(ln): words.append((w.u32(o + 4 * k), (o + 4 * k) in w.relocs))
        o += 4 * ln
    at = w.alloc(bytes(4 * len(words)))
    for k, (v, isp) in enumerate(words):
        if isp: w.ptr(at + 4 * k, v)
        else: w.put(at + 4 * k, v)
    if approx: rep["approx_rows"].append(src)
    return at


def vis_frames(anim, base):
    g = [g for g in anim["groups"] if g["group_type"] == "Visibility"]
    tr = {}
    if g:
        for n in g[0]["nodes"]:
            v = n["tracks"][0]["values"]; tr[n["name"]] = next(iter(v.values())) if isinstance(v, dict) else v
    n = int(round(anim["final_frame_index"])) + 1
    out = []
    for f in range(n):
        vis = dict(base)
        for k, v in tr.items(): vis[k] = v[min(f, len(v) - 1)]
        out.append(frozenset(k for k, on in vis.items() if on))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fighter")
    ap.add_argument("--name", default=None)
    ap.add_argument("--pl", default="PlUk.dat")
    ap.add_argument("--dst-k", type=int, default=52); ap.add_argument("--dst-e", type=int, default=51)
    ap.add_argument("--out", default=None)
    ap.add_argument("--fallback", default="a00wait1")
    a = ap.parse_args()
    name = a.name or f"Ultimate {a.fighter.capitalize()}"
    stem = a.pl[:-4]
    out = a.out or os.path.join(ROOT, "_build", "tmp", "ultimate-mods", f"ultimate-{a.fighter}-slot")
    files = os.path.join(out, "files"); os.makedirs(files, exist_ok=True)
    rep = {"fighter": a.fighter, "name": name, "pl": a.pl, "row": {"internal": a.dst_k, "external": a.dst_e}}

    ir = json.load(open(os.path.join(CA.INSTANCES, f"{a.fighter}.ultimate-body.ir.json"), encoding="utf-8"))
    plan = plan_parts.plan(ir); rest = CA.rest_of(ir); J = fighter_joints(plan, rest)
    if plan["unresolved"]: sys.exit(f"plan has unresolved roles: {plan['unresolved']}")

    # 1-2. slot files + host fighter data
    log = subprocess.run([sys.executable, os.path.join(HALBERD, "tools", "mk_slot_files.py"), "--out", files,
                          "--base", os.path.join(out, "_nobase"), "--pl", a.pl, "--name", name,
                          "--dst-k", str(a.dst_k), "--dst-e", str(a.dst_e)], capture_output=True, text=True)
    if log.returncode: sys.exit("mk_slot_files failed: " + log.stderr[-1500:])
    rep["slot_files"] = json.loads(log.stdout)
    g = mex_hsd.Gcm(ISO_ACE)
    open(os.path.join(files, a.pl), "wb").write(g.read("PlKb.dat"))

    # 3. costume
    mesh = EM.export(a.fighter, "c00")
    mpath = os.path.join(out, "_work", "mesh_c00.json"); os.makedirs(os.path.dirname(mpath), exist_ok=True)
    json.dump(mesh, open(mpath, "w"))
    tmpl = os.path.join(out, "_work", "PlKbNr.dat"); open(tmpl, "wb").write(g.read("PlKbNr.dat"))
    fb = glob.glob(os.path.join(HERE, "fighterbuild", "bin", "**", "fighterbuild.exe"), recursive=True)
    if not fb: sys.exit("build ports/ir/tools/fighterbuild first (dotnet build -c Release)")
    jsym, msym = "Ply%s5K_Share_joint" % name.replace(" ", ""), "Ply%s5K_Share_matanim_joint" % name.replace(" ", "")
    costume = f"{stem}Nr.dat"
    r = subprocess.run([fb[0], "build", mpath, tmpl, os.path.join(files, costume), jsym, msym,
                        os.path.join(out, "_work", "costume_report.json")], capture_output=True, text=True)
    if r.returncode: sys.exit("fighterbuild failed: " + r.stdout[-800:] + r.stderr[-800:])
    rep["costume"] = r.stdout.strip()
    dobj_group = [d["group"] for d in mesh["dobjs"]]

    # 4. animations + visibility
    motion = os.path.join(CA.FIGHTERS, a.fighter, "motion", "body", "c00")
    clips = sorted(n[:-7] for n in os.listdir(motion) if n.endswith(".nuanmb"))
    base_anim = CA.decode(os.path.join(motion, "a00defaulteyelid.nuanmb")) if "a00defaulteyelid" in clips else None
    base = {}
    if base_anim:
        for n in [g_ for g_ in base_anim["groups"] if g_["group_type"] == "Visibility"][0]["nodes"]:
            v = n["tracks"][0]["values"]; v = next(iter(v.values())) if isinstance(v, dict) else v
            base[n["name"]] = v[0]
    key = lambda c: re.sub(r"^[a-z]\d\d", "", c)
    by_key = {}
    for c in clips: by_key.setdefault(key(c), c)
    w = Writer(open(os.path.join(files, a.pl), "rb").read())
    fd = w.ar.public([s for s, _ in w.ar.publics if s.startswith("ftData")][0])
    mt = w.u32(fd + 0xC)
    rows, foreign = {}, {}
    for r_ in range(479):
        o = mt + r_ * 0x18
        if o in w.relocs and w.u32(o + 8):
            if w.u32(o + 0x10) & 0x3F != KIRBY_INTERNAL:
                # authored for another skeleton (0x21: the generic thrown skeleton - ThrownF/B/Hi/Lw,
                # the star-spit and Yoshi-egg victims). These play on the VICTIM, so they keep the
                # host's own clip; pointing them at the fighter's clips crashed the victim of a throw.
                foreign[r_] = (w.u32(o + 4), w.u32(o + 8))
                continue
            m = re.search(r"_ACTION_(\w+?)_figatree", w.str_at(w.u32(o)))
            rows[r_] = m.group(1) if m else None
    wanted, unmatched, fuzzy = {}, [], {}
    # The decomp's row name first (the figatree name repeats for ground and air rows: Kirby's 320
    # 'SpecialAirN' plays a figatree named SpecialN), then the figatree's.
    host_names = {s["index"]["value"]: s["name"] for s in json.load(open(os.path.join(
        CA.INSTANCES, "kirby.melee.ir.json"), encoding="utf-8"))["behavior"]["subactions"]}
    for r_, act in rows.items():
        c, how_ = match_clip(host_names.get(r_), by_key)
        if c is None:
            c, how_ = match_clip(act, by_key)
        if c is None: unmatched.append(act); c = a.fallback
        elif how_ != "exact": fuzzy[act] = f"{c} ({how_})"
        wanted.setdefault(c, []).append(r_)
    aj = bytearray(); clip_at = {}; vis_of = {}; worst = 0.0; conv = []
    for c in sorted(wanted):
        anim = CA.decode(os.path.join(motion, c + ".nuanmb"))
        sym = f"Ply{name.replace(' ', '')}5K_Share_ACTION_{c}_figatree"
        arc, cr, poses = CA.convert_clip(anim, plan, rest, sym)
        chk = CA.check(arc, plan, rest, poses, cr["frames"], False)
        worst = max(worst, chk["world"])
        if len(arc) > 0x20000: sys.exit(f"{c}: {len(arc)} bytes, over FT_ANIM_BUF_SIZE")
        while len(aj) % 0x20: aj.append(0)
        clip_at[c] = (len(aj), len(arc), sym); aj += arc
        vis_of[c] = vis_frames(anim, base)
        conv.append({"clip": c, "rows": wanted[c], "bytes": len(arc), "world_err": round(chk["world"], 4)})
    host_aj = g.read("PlKbAJ.dat")
    kept = {}
    for r_, (off, size) in sorted(foreign.items()):
        if (off, size) not in kept:
            while len(aj) % 0x20: aj.append(0)
            kept[(off, size)] = len(aj); aj += host_aj[off:off + size]
        w.put(mt + r_ * 0x18 + 4, kept[(off, size)])
    open(os.path.join(files, f"{stem}AJ.dat"), "wb").write(aj)
    sym_str = {}
    for c, rs in wanted.items():
        off, size, sym = clip_at[c]
        if sym not in sym_str: sym_str[sym] = w.cstr(sym)
        for r_ in rs:
            o = mt + r_ * 0x18
            w.ptr(o, sym_str[sym]); w.put(o + 4, off); w.put(o + 8, size)
    rep["animations"] = {"file": f"{stem}AJ.dat", "bytes": len(aj), "clips": len(clip_at), "rows": len(rows),
                         "unmatched_rows_played_as_fallback": sorted({u for u in unmatched if u}),
                         "matched_by_rule": fuzzy,
                         "host_clips_kept_for_other_skeletons": sorted(foreign),
                         "worst_world_error": round(worst, 4)}

    # 5. ftData joint fields
    ftd = plan["ftdata"]
    jn = lambda e: e["joint"]
    # x8: ModelVis model 0 = every distinct visible set (states); part bytes item/shield/head/feet
    all_sets = sorted({s for v in vis_of.values() for s in v}, key=lambda s: sorted(s))
    default = vis_of.get(a.fallback, [frozenset()])[0]
    if default in all_sets: all_sets.remove(default)
    states = [default] + all_sets
    controlled = sorted({g_ for s in states for g_ in s} | set(base))
    lists = [[i for i, gname in enumerate(dobj_group) if gname in s and gname in controlled] for s in states]
    st_at = w.alloc(bytes(8 * len(states)))
    for k, dl in enumerate(lists):
        lst = w.alloc(bytes(dl) + bytes((-len(dl)) % 4))
        w.put(st_at + 8 * k, len(dl)); w.ptr(st_at + 8 * k + 4, lst)
    model = w.alloc(bytes(8)); w.put(model, len(states)); w.ptr(model + 4, st_at)
    NROWS = 8
    vt = w.alloc(bytes(16 * NROWS))
    w.ptr(vt, model); w.ptr(vt + 4, model); w.ptr(vt + 12, model)
    tl = w.alloc(struct.pack(">HH", 0, 0)); tt = w.alloc(bytes(4 * NROWS)); w.ptr(tt, tl)
    x8 = w.alloc(bytes(0x18))
    # no costume TObjs: ftAnim_80070200 asserts "can't find fighter texture anim" for any TObj
    # listed here without a texanim, and the model's expressions are meshes, not texanims
    w.put(x8, 1); w.ptr(x8 + 4, vt); w.put(x8 + 8, 0); w.ptr(x8 + 0xC, tt)
    w.data[x8 + 0x10:x8 + 0x15] = bytes(jn(e) for e in ftd["x8_part_bytes"])
    w.ptr(fd + 8, x8)
    # x1C: part anims parked on the head-top joint with still AnimJoints (install_mk.py's approach)
    park = jn(ftd["x8_part_bytes"][2])
    still = []
    for _ in range(4):
        aobj = w.alloc(struct.pack(">IfII", 0, 1.0, 0, 0)); aj_ = w.alloc(bytes(0x14)); w.ptr(aj_ + 8, aobj); still.append(aj_)
    x1c = w.alloc(bytes(12))
    for e in range(3):
        lst = w.alloc(bytes([park, 0, 0, 0])); an = w.alloc(bytes(16))
        for k in range(4): w.ptr(an + 4 * k, still[k])
        ent = w.alloc(struct.pack(">HH", park, 1) + bytes(8)); w.ptr(ent + 4, lst); w.ptr(ent + 8, an); w.ptr(x1c + 4 * e, ent)
    w.ptr(fd + 0x1C, x1c)
    # x20 shield pose, x5C metal / parts model: the fighter's tree at rest
    x20 = w.alloc(bytes(8)); w.ptr(x20, joint_tree(w, J)); w.ptr(fd + 0x20, x20)
    w.ptr(fd + 0x5C, joint_tree(w, J))
    # host slot map (scripts, hurtboxes)
    slot_to_joint, scale, how = host_slot_map(J, plan)
    # x30 hurtboxes: the host's capsules on the fighter's joints (offsets in fighter units)
    x30 = w.u32(fd + 0x30); n = w.u32(x30); arr = w.u32(x30 + 4)
    hurt_bones, hb = set(), []
    for i in range(n):
        o = arr + 0x28 * i
        b = struct.unpack(">i", w.data[o:o + 4])[0]; nb = slot_to_joint.get(b, 0)
        w.data[o:o + 4] = struct.pack(">i", nb); hurt_bones.add(nb)
        vals = struct.unpack(">7f", w.data[o + 0xC:o + 0x28])
        w.data[o + 0xC:o + 0x28] = struct.pack(">7f", *[v / scale for v in vals])
        hb.append({"host_slot": b, "joint": J[nb]["name"]})
    # in-place joint fields
    w.put(w.u32(fd + 0x34), jn(ftd["x34_centre"][0]))
    x38 = w.u32(fd + 0x38); w.put(x38, jn(ftd["x38_coin"][0])); w.put(x38 + 4, jn(ftd["x38_coin"][1]))
    x44 = w.u32(fd + 0x44); w.data[x44:x44 + 12] = struct.pack(">6h", *[jn(e) for e in ftd["x44_ecb"]])
    x54 = w.u32(fd + 0x54); w.data[x54:x54 + 20] = struct.pack(">5i", *[jn(e) for e in ftd["x54_gfx"]])
    x58 = w.u32(fd + 0x58)
    for o, (rr, ll) in zip((0, 8, 0x10, 0x1C, 0x24), ftd["x58_ik"]):
        w.data[x58 + o] = jn(rr); w.data[x58 + o + 1] = jn(ll)
    rep["ftdata"] = {"modelvis_states": len(states), "controlled_meshes": controlled, "hurtboxes": hb,
                     "host_units_per_fighter_unit": round(scale, 4), "host_slot_map": how}

    # demo motions (x14): the port counts an m-ex fighter's demo motions up to the first entry with
    # no script (ftdata.c); Kirby's entry 4 has none, so the results screen asserted "Demo Status
    # error". The holes get an End-only script (install_mk.py's fix for Meta Knight).
    x14 = w.u32(fd + 0x14); end = None; holes = []
    for i in range(18):
        o = x14 + i * 0x18 + 0xC
        if o not in w.relocs:
            if end is None: end = w.alloc(bytes(4))
            w.ptr(o, end); holes.append(i)
    rep["demo_holes_given_end_script"] = holes

    # 6. scripts + frame-0 ModelVis
    rep["scripts"] = remap_scripts(w, fd, slot_to_joint, hurt_bones, J)
    idx_of = {s: k for k, s in enumerate(states)}
    cache = {}; mv = {"rows": 0, "events": 0, "approx_rows": [], "dropped_after_goto": 0}
    for c, rs in wanted.items():
        seq = [idx_of[s] for s in vis_of[c]]
        events = [(f, st) for f, st in enumerate(seq) if f == 0 or st != seq[f - 1]]
        for r_ in rs:
            po = mt + r_ * 0x18 + 0xC
            src = w.u32(po) if po in w.relocs else None
            key_ = (src, tuple(events))
            if key_ not in cache:
                cache[key_] = merge_vis(w, src, events, len(seq), mv)
            w.ptr(po, cache[key_])
            mv["rows"] += 1; mv["events"] += len(events)
    rep["modelvis"] = mv
    w.save(os.path.join(files, a.pl))

    # 7. PlCo parts table
    pc = Writer(open(os.path.join(files, "PlCo.dat"), "rb").read())
    r0 = pc.ar.public("ftLoadCommonData"); t4 = pc.u32(r0 + 16); t5 = pc.u32(r0 + 20)
    j2p = plan["parts"]["joint_to_part"]; p2j = plan["parts"]["part_to_joint"]
    a_j2p = pc.alloc(bytes(j2p) + bytes((-len(j2p)) % 4)); a_p2j = pc.alloc(bytes(p2j) + b"\xff" * (64 - len(p2j)))
    ent = pc.alloc(bytes(12)); pc.ptr(ent, a_j2p); pc.ptr(ent + 4, a_p2j); pc.put(ent + 8, len(J))
    pc.ptr(t4 + 4 * a.dst_k, ent); pc.ptr(t5 + 4 * a.dst_k, 0)
    pc.save(os.path.join(files, "PlCo.dat"))
    rep["PlCo.dat"] = {"parts_num": len(J), "placeholder_slots": None}

    # MxDt: anim file + every costume row -> the c00 model
    mx = os.path.join(files, "MxDt.dat")
    raw = open(mx, "rb").read()
    class _Gcm:
        def __init__(self, iso): pass
        def read(self, nm): return raw if nm == "MxDt.dat" else mex_hsd.Gcm(ISO_ACE).read(nm)
    real = mex_hsd.Gcm; mex_hsd.Gcm = _Gcm
    argv = sys.argv
    sys.argv = ["mxdt_clone.py", "--out", mx, "--pl", a.pl, "--name", name, "--aj", f"{stem}AJ.dat",
                "--src-k", str(a.dst_k), "--src-e", str(a.dst_e), "--dst-k", str(a.dst_k), "--dst-e", str(a.dst_e)]
    for c in range(6): sys.argv += ["--costume", f"{c}:{costume}:{jsym}:{msym}"]
    import contextlib, io, runpy
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            runpy.run_path(os.path.join(ROOT, "experiment", "brawl-kirby", "tools", "mxdt_clone.py"), run_name="__main__")
    finally:
        sys.argv = argv; mex_hsd.Gcm = real

    json.dump({"id": f"ultimate-{a.fighter}-slot", "name": f"{name.upper()} (Ultimate, own skeleton)", "version": "0.1.0",
               "kind": "fighter", "requires": [], "conflicts": ["metaknight-slot"],
               "description": f"{name} from Smash Ultimate on its own skeleton, as an m-ex fighter replacing ACE's row "
                              f"{a.dst_k}/{a.dst_e} (the row metaknight-slot uses). Kirby's fighter data and scripts are the "
                              f"host behaviour. Built by ports/ir/tools/install_ultimate.py."},
              open(os.path.join(out, "mod.json"), "w"), indent=1)
    rep["conversion"] = conv
    json.dump(rep, open(os.path.join(out, "INSTALL.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k not in ("conversion", "slot_files")}, indent=1)[:4000])
    print(f"-> {out}  (scene token p1={name.replace(' ', '').lower()})")


if __name__ == "__main__":
    sys.exit(main())
