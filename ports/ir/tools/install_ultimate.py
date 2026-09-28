#!/usr/bin/env python3
"""install_ultimate.py - an Ultimate fighter as an m-ex slot mod on its OWN skeleton (Kirby-clone host).

    python ports/ir/tools/install_ultimate.py kirby [--name "Ultimate Kirby"] [--pl PlUk.dat]
            [--dst-k 52 --dst-e 51] [--out _build/tmp/ultimate-mods/ultimate-kirby-slot]

The generic counterpart of Halberd's install_mk.py, driven by the IR tools instead of hand tables:

 1. slot files (Halberd's mk_slot_files.py, parameterised): MxDt row dst-k/dst-e becomes a clone of
    Kirby (internal/external 4) named --name with pl file --pl; PlCo / MnSlChr / IfAll to match.
    When the fighter's extracted Ultimate UI BNTX files exist, the copied CSS icon, CSPs and
    stock icons are replaced with converted art in this mod's own entries.
    Row 52/51 is the one Meta Knight uses (it replaces ACE's duplicate "Wolf SSBU"): every added
    fighter displaces an ACE fighter while the port has 31 m-ex slots, so this mod and
    metaknight-slot are mounted one at a time.
 2. <pl> = the ACE disc's host fighter file (--host kirby: PlKb.dat, marth: PlMs.dat): its fighter data and scripts are the host behaviour.
 3. costumes: export_ultimate_mesh.py + fighterbuild for each available c00..c07 body,
    one Melee costume file per m-ex row. --c00-only selects just the first costume.
 4. animations: convert_ultimate_anim.py per clip into <pl stem>AJ.dat; every motion row that has
    a clip is pointed at the Ultimate clip of the same action name (Melee 'AttackS4S' = Ultimate
    'c03attacks4s'); rows with no match play the fallback (wait1) and are listed.
 5. ftData joint fields from plan_parts.py: part bytes, centre, coin spheres, ECB, GFX, IK; the
    hurtboxes fitted to the fighter's own mesh (plan_hurtboxes.py; --host-hurtboxes: the host's moved by role); x20 guard-frame / x5C rest joint trees; x1C part
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
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys

import numpy as np
from scipy.spatial.transform import Rotation

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acmd_parse as AP  # noqa: E402
import convert_ultimate_anim as CA  # noqa: E402
import export_ultimate_mesh as EM  # noqa: E402
import figatree as F  # noqa: E402
import plan_parts  # noqa: E402
import ultimate_ui as UI  # noqa: E402
from walkloop import rewrite_host_loop, validate_geno_overlays, validate_script  # noqa: E402
from acmd_loss import write_losses, verify_acmd_source  # noqa: E402

ROOT = CA.ROOT
sys.path.insert(0, os.path.join(ROOT, "tools", "mex_port"))
import mex_hsd  # noqa: E402

ISO_ACE = os.environ.get("GW_ISO_ACE", "")   # mk_slot_files.py reads this path too
HALBERD = os.path.join(ROOT, "ports", "halberd")
# Host fighters: the Melee fighter whose data, scripts and m-ex row the slot clones.
# internal = FighterKind (also the low 6 bits of a motion row authored for its skeleton),
# external = the m-ex CSS id, icon = the CSS icon joint (ACE MxDt/MnSlChr), code = file letters.
HOSTS = {"kirby": {"internal": 4, "external": 4, "icon": 20, "code": "Kb"},
         "marth": {"internal": 18, "external": 9, "icon": 47, "code": "Ms"}}
HOST = HOSTS["kirby"]   # set from --host in main()
COMMON_ROWS = 295   # motion rows 0..294 are the common actions (ftCo); 295 on are the fighter's own
COSTUME_COLORS = ("Nr", "Ye", "Bu", "Re", "Gr", "Wh", "Bk", "Or")
FLOW_LEN = [1, 1, 1, 1, 1, 2, 1, 2, 1, 1]
OP_LEN = [5, 5, 1, 1, 1, 1, 1, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 1, 1, 1, 7, 4, 1, 1, 1, 1,
          1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 3, 2, 1, 4]   # ftaction.c ftAction_803C0870, ops 10..58


def acmd_converter_digest():
    return hashlib.sha256(b"".join((Path(HERE) / file).read_bytes() for file in
                                   ("acmd_to_ftcmd.py", "acmd_loss.py", "acmd_allowlist.json"))).hexdigest()


def verify_moveset_audit(document, source_bytes):
    audit = document.get("audit") or {}
    if audit.get("version") != 1:
        raise ValueError("unaudited moveset: regenerate with current acmd_to_ftcmd.py")
    if audit.get("source_sha256") != hashlib.sha256(source_bytes).hexdigest():
        raise ValueError("stale moveset: ACMD source changed; regenerate the moveset")
    if audit.get("converter_sha256") != acmd_converter_digest():
        raise ValueError("stale moveset: converter or allowlist changed; regenerate the moveset")


def cmd_len(word):
    """Words in the ftcmd starting with `word`: flow ops 0-9, retail 10-58 (ftAction_803C0870), and
    Geno's 59 whose word0 [19:16] is its own length (melee docs/geno.md 15; 0 reads as 1)."""
    op = word >> 26
    if op < 10:
        return FLOW_LEN[op]
    if op == 59:
        return max(1, (word >> 16) & 0xF)
    return OP_LEN[op - 10] if op - 10 < len(OP_LEN) else 1


def admit_empty_motion_rows(rows, foreign, host_names, moveset, clips):
    """Add empty host rows only when the translated moveset supplies a clip and script.

    The caller's animation and script passes then fill the whole motion record. Rows
    supplied by --row-clips have no script here and remain Geno overlay territory.
    """
    admitted = {}
    for r_, move in moveset.items():
        if r_ in rows or r_ in foreign or r_ not in host_names:
            continue
        if not move.get("clip") or not move.get("script") or not move.get("words"):
            continue
        clip = move["clip"]
        if clip not in clips:
            raise ValueError(f"moveset row {r_}: no clip {clip}")
        rows[r_] = host_names[r_]
        admitted[r_] = clip
    return admitted


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


def discover_costumes(body_dir, c00_only=False):
    """Select the contiguous Ultimate costume prefix represented by the eight UI/ftData rows."""
    body_dir = Path(body_dir)
    selected = []
    for index, color in enumerate(COSTUME_COLORS):
        costume = f"c{index:02}"
        folder = body_dir / costume
        complete = (all((folder / name).is_file() for name in
                        ("model.numshb", "model.numdlb", "model.numatb"))
                    and any(folder.glob("*.nutexb")))
        if complete:
            if len(selected) != index:
                raise ValueError(f"{costume}: preceding costume c{len(selected):02} is missing or incomplete")
            selected.append((costume, color))
        if c00_only:
            break
    if not selected:
        raise ValueError(f"c00 model/textures missing from {body_dir}")
    return selected


def costume_workdir(out):
    work = Path(out, "_work")
    work.mkdir(parents=True, exist_ok=True)
    return work


def write_costume_rows(w, internal, external, files, joint_sym, mat_sym):
    """Replace the m-ex costume_file table and external costume_info count."""
    if not 1 <= len(files) <= len(COSTUME_COLORS):
        raise ValueError(f"m-ex costume rows must contain 1..{len(COSTUME_COLORS)} files")
    fighter = w.u32(w.ar.public("mexData") + 8)
    info = w.u32(fighter + 0x10) + external * 4
    table_ptr = w.u32(fighter + 0x14) + internal * 4
    table = w.alloc(bytes(16 * len(files)))
    joint = w.cstr(joint_sym)
    mat = w.cstr(mat_sym)
    for index, filename in enumerate(files):
        row = table + index * 16
        w.ptr(row, w.cstr(filename))
        w.ptr(row + 4, joint)
        w.ptr(row + 8, mat)
        # The fourth word selects this costume's ftData x8 visibility lookup row.
        w.put(row + 12, index)
    w.ptr(table_ptr, table)
    w.data[info] = len(files)
    for team in range(1, 4):
        if w.data[info + team] >= len(files):
            w.data[info + team] = 0


def write_costume_modelvis(w, states, costume_groups, controlled):
    """Build one ftData x8 model-visibility lookup per costume's DObj order."""
    table = w.alloc(bytes(16 * len(COSTUME_COLORS)))
    first = None
    for index, groups in enumerate(costume_groups):
        state_table = w.alloc(bytes(8 * len(states)))
        for state_index, state in enumerate(states):
            dobjs = [i for i, group in enumerate(groups) if group in state and group in controlled]
            entries = w.alloc(bytes(dobjs) + bytes((-len(dobjs)) % 4))
            row = state_table + state_index * 8
            w.put(row, len(dobjs))
            w.ptr(row + 4, entries)
        model = w.alloc(bytes(8))
        w.put(model, len(states))
        w.ptr(model + 4, state_table)
        if first is None:
            first = model
        w.ptr(table + index * 16, model)
        w.ptr(table + index * 16 + 4, model)
        w.ptr(table + index * 16 + 12, model)
    for index in range(len(costume_groups), len(COSTUME_COLORS)):
        w.ptr(table + index * 16, first)
        w.ptr(table + index * 16 + 4, first)
        w.ptr(table + index * 16 + 12, first)
    return table


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


def guard_pose_joints(anim, plan, rest, joints, orient):
    """Sample Ultimate's b00guard at frame 0 in the costume/figatree joint order."""
    CA.bake_helpers(anim, plan, rest, orient)
    nodes = {n["name"]: n for g in anim["groups"] if g["group_type"] == "Transform" for n in g["nodes"]}
    pose = []
    for planned, joint in zip(plan["joints"], joints):
        copied = dict(joint)
        node = nodes.get(planned["name"]) if not planned["synthesized"] else None
        if node is not None:
            track = node["tracks"][0]
            frame = track["values"]["Transform"][0]
            copied["rot"] = list(map(float, CA.euler_track(
                [[frame["rotation"][axis] for axis in "xyzw"]], rest[planned["name"]][3])[0]))
            copied["scale"] = [float(frame["scale"][axis]) for axis in "xyz"]
            if not track["transform_flags"]["override_translation"]:
                copied["trans"] = [float(frame["translation"][axis]) for axis in "xyz"]
        pose.append(copied)
    return pose


def count_joint_tree(w, root):
    """Count an HSD_Joint tree, rejecting invalid links and cycles."""
    seen, pending = set(), [root]
    while pending:
        at = pending.pop()
        if not at or at in seen or at + 0x40 > len(w.data):
            raise ValueError(f"invalid HSD_Joint at 0x{at:X}")
        seen.add(at)
        for field in (at + 8, at + 0xC):
            child = w.u32(field)
            if child:
                if field not in w.relocs:
                    raise ValueError(f"HSD_Joint link at 0x{field:X} lacks relocation")
                pending.append(child)
    return len(seen)


def validate_ftdata_pose_trees(w, fd, joint_count):
    """The only HSD_Joint fields in ftData are x20->x0 and x5C."""
    x20 = w.u32(fd + 0x20)
    if fd + 0x20 not in w.relocs or not x20 or x20 + 8 > len(w.data):
        raise ValueError("ftData x20 pose descriptor is invalid")
    shield_root = w.u32(x20)
    if x20 not in w.relocs or not shield_root:
        raise ValueError("ftData x20->x0 pose root is invalid")
    trees = (("x20->x0", shield_root, joint_count),
             ("x20->x0[2]", w.u32(shield_root + 8), joint_count - 1),
             ("x5C", w.u32(fd + 0x5C), joint_count))
    if fd + 0x5C not in w.relocs:
        raise ValueError("ftData x5C pose root lacks relocation")
    for name, root, expected in trees:
        found = count_joint_tree(w, root)
        if found != expected:
            raise ValueError(f"ftData {name}: {found} joints, expected {expected}")


def install_ftdata_pose_trees(w, fd, joints, guard_pose):
    # x0 is itself an HSD_Joint root: words [0] and [1] are its null name
    # and 0x8 CLASSICAL_SCALING flag. Word [2] is the child tree copied by guard.
    x20 = w.alloc(bytes(8))
    w.ptr(x20, joint_tree(w, guard_pose))
    w.ptr(fd + 0x20, x20)
    w.ptr(fd + 0x5C, joint_tree(w, joints))
    validate_ftdata_pose_trees(w, fd, len(joints))


# ------------------------------------------------------------------ host (Melee Kirby) joint spaces
def host_ir():
    return json.load(open(os.path.join(CA.INSTANCES, f"{HOST['name']}.melee.ir.json"), encoding="utf-8"))


def host_slot_map(fj, plan):
    """Kirby part slot -> fighter joint: same common part, else nearest by rest position."""
    host = host_ir()["assets"]["skeletons"][0]
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
    starts = [w.u32(mt + r * 0x18 + 0xC) for r in range(HOST["rows"]) if (mt + r * 0x18 + 0xC) in w.relocs]
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
            if op == 59: o += 4 * cmd_len(word); continue
            if op - 10 >= len(OP_LEN): return
            def sub(shift, key, conv=lambda j: j):
                b = (word >> shift) & 0xFF
                nb = slot_to_joint.get(b)
                if nb is None:
                    raise ValueError(f"host script joint slot {b} is unmapped at 0x{o:X} (opcode {op})")
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
    subroutine or animation-rate command are placed approximately (reported). A row with no
    script gets one made of the events alone. Ambiguous Goto placement fails."""
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
            if pend:
                rep["dropped_after_goto"] += len(pend)
                rep.setdefault("goto_losses", []).append({"script_offset": f"0x{o:X}",
                                                          "events": list(pend)})
            words.append((word, False)); words.append((w.u32(o + 4), (o + 4) in w.relocs)); break
        if op in (3, 4, 5, 8): approx = True
        ln = cmd_len(word)
        for k in range(ln): words.append((w.u32(o + 4 * k), (o + 4 * k) in w.relocs))
        o += 4 * ln
    else:
        raise ValueError(f"ModelVis script at 0x{src:X} has no End within 4000 commands")
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


# ------------------------------------------------------------------ clip conversion: parallel + cached
_CTX = {}


def _convert_one(job):
    """One clip: decode, strip the root (non-driven rows), bake helpers, convert, self-check.
    Cached on disk by (source clip bytes, options, converter sources), so a reinstall that only
    changes scripts reuses every clip."""
    import hashlib, pickle
    fighter, c, driven, root, helpers, sym, base = job
    src = os.path.join(CA.FIGHTERS, fighter, "motion", "body", "c00", c + ".nuanmb")
    h = hashlib.sha1(open(src, "rb").read())
    import inspect
    for f in ("convert_ultimate_anim.py", "figatree.py", "plan_parts.py"):
        h.update(open(os.path.join(HERE, f), "rb").read())
    h.update(inspect.getsource(vis_frames).encode())
    h.update(repr((root, helpers, sym, sorted(base.items()))).encode())
    cache_root = os.environ.get("GW_ULTIMATE_ANIM_CACHE", os.path.join(ROOT, "_build", "tmp", "ultimate-anim-cache"))
    cache = os.path.join(cache_root, fighter, f"{c}{'_drv' if driven else ''}_{h.hexdigest()[:16]}.pkl")
    if os.path.exists(cache):
        return pickle.load(open(cache, "rb"))
    if fighter not in _CTX:
        ir = json.load(open(os.path.join(CA.INSTANCES, f"{fighter}.ultimate-body.ir.json"), encoding="utf-8"))
        _CTX[fighter] = (plan_parts.plan(ir), CA.rest_of(ir), CA.helper_constraints(fighter)[0])
    plan, rest, orient = _CTX[fighter]
    anim = CA.decode(src)
    stripped = CA.strip_root(anim, root) if root else None
    if helpers:
        CA.bake_helpers(anim, plan, rest, orient)
    arc, cr, poses = CA.convert_clip(anim, plan, rest, sym)
    chk = CA.check(arc, plan, rest, poses, cr["frames"], False)
    out = (arc, chk["world"], vis_frames(anim, base), stripped, sym)
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    pickle.dump(out, open(cache + ".tmp", "wb")); os.replace(cache + ".tmp", cache)
    return out


def convert_all(jobs, workers):
    if workers <= 1:
        return [_convert_one(j) for j in jobs]
    # Each worker loads numpy/scipy (~0.3 GB of commit). When the machine's commit limit is reached
    # (other games running: "paging file too small") the pool dies; finished clips are cached, so the
    # rest runs with half the workers, down to serial.
    from concurrent.futures import ProcessPoolExecutor
    from concurrent.futures.process import BrokenProcessPool
    try:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            return list(ex.map(_convert_one, jobs, chunksize=2))
    except (BrokenProcessPool, MemoryError, OSError) as e:
        print(f"conversion pool of {workers} failed ({type(e).__name__}); retrying with {workers // 2}", file=sys.stderr)
        return convert_all(jobs, workers // 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fighter")
    ap.add_argument("--name", default=None)
    ap.add_argument("--pl", default="PlUk.dat")
    ap.add_argument("--dst-k", type=int, default=52); ap.add_argument("--dst-e", type=int, default=51)
    ap.add_argument("--out", default=None)
    ap.add_argument("--ir-root", help="directory with the generated fighter IR files (default: this workspace's _build/tmp/ir)")
    ap.add_argument("--c00-only", action="store_true",
                    help="build and expose only Ultimate costume c00 (one selectable m-ex costume)")
    ap.add_argument("--ui-art", choices=("auto", "off", "required"), default="auto",
                    help="convert Ultimate CSS/CSP/stock art when all BNTX sources exist (default: auto; "
                         "off keeps host placeholders; required fails if art is missing)")
    ap.add_argument("--ui-root", default=UI.UI_ROOT, help="extracted ui/replace_patch/chara folder")
    ap.add_argument("--ui-label", help="text in the CSS icon's name band (trail defaults to SORA)")
    ap.add_argument("--fallback", default="a00wait1")
    ap.add_argument("--jobs", type=int, default=min(4, max(1, (os.cpu_count() or 2) - 2)),
                    help="clip conversion processes (default: min(4, cores - 2), halved on a memory failure; each holds a decoded clip, ~0.5 GB peak); converted clips are cached "
                         "under --out/_work/anim-cache when --out is set, else _build/tmp/ultimate-anim-cache")
    ap.add_argument("--row-clips", help="clips.json {subaction_clips: {row: clip}} (trail_specials_geno.py)")
    ap.add_argument("--extra-files", help="a folder whose files are added to the mod's files/ (article models)")
    ap.add_argument("--geno", help="geno.json to ship (default: a minimal profile attached to --pl)")
    ap.add_argument("--host", choices=sorted(HOSTS), default="kirby", help="the Melee fighter whose data, "
                    "scripts and m-ex row the slot clones (its IR: build_melee_fighter.py <host>)")
    ap.add_argument("--clip-list", help="ship only these clips (one per line, see convert_ultimate_anim."
                    "read_clip_list); rows matched to any other clip play --fallback and are listed")
    ap.add_argument("--write-clip-list", help="write the clips the host's rows match (the used set, with "
                    "the rows each plays and whether they are common actions) and continue")
    ap.add_argument("--common-only", action="store_true", help="ship only the clips common-action rows "
                    "(host rows < %d) use; the fighter's specials play --fallback" % COMMON_ROWS)
    ap.add_argument("--moveset", help="acmd_to_ftcmd.py output (<fighter>.moveset.json): its rows get the "
                    "translated scripts (not remapped: their bones are already the fighter's joints) and "
                    "the named clips; the ModelVis merge still runs on top")
    ap.add_argument("--acmd", help="ACMD JSON used to produce --moveset (default: _build/tmp/ir/<fighter>.acmd.json)")
    ap.add_argument("--joint-probe", help="optional LAB joint-probe log for the final position check")
    ap.add_argument("--skip-acmd-audit", action="store_true",
                    help="LOUD OVERRIDE: skip no-drop provenance and installed hitbox position gate")
    ap.add_argument("--lod", choices=("high", "low"), default="high", help="which body to keep where the "
                    "model ships two levels of detail")
    ap.add_argument("--tex-format", choices=("auto",), help="opt in to smaller CMPR/RGB5A3 costume textures")
    ap.add_argument("--host-hurtboxes", action="store_true", help="the host's capsules moved onto the "
                    "fighter's joints instead of plan_hurtboxes.py's fitted to the fighter's mesh")
    ap.add_argument("--fold-helpers", action="store_true", help="fold helper-bone (H_*) weights into their "
                    "nearest non-helper ancestor instead of baking model.nuhlpb into the clips (saves "
                    "~25%% of animation bytes on Sora; skin error up to ~5%% of body height at the feet)")
    ap.add_argument("--pc-palette", type=int, choices=(64,), help="build the costume's envelope POBJs as PC "
                    "matrix palette POBJs (geno_pal_pobj_v1, up to 64 envelopes a piece; needs an exe with engine "
                    "pobj_palette 1, which mod.json then requires)")
    a = ap.parse_args()
    if a.ir_root:
        os.environ["GW_ULTIMATE_IR_ROOT"] = os.path.abspath(a.ir_root)
        CA.INSTANCES = EM.INSTANCES = os.environ["GW_ULTIMATE_IR_ROOT"]
    acmd_path = a.acmd or os.path.join(CA.INSTANCES, f"{a.fighter}.acmd.json")
    moveset_doc = None
    geno_audit = None
    geno_sources = None
    if a.skip_acmd_audit:
        print("WARNING: ACMD LOSS AND HITBOX POSITION AUDITS DISABLED BY --skip-acmd-audit", file=sys.stderr)
    else:
        if not a.moveset:
            sys.exit("ACMD audit requires --moveset; use --skip-acmd-audit only for a deliberate unaudited install")
        if not os.path.isfile(acmd_path):
            sys.exit(f"ACMD audit source missing: {acmd_path}")
        try:
            source_bytes = verify_acmd_source(acmd_path)
        except ValueError as exc:
            sys.exit(str(exc))
        moveset_doc = json.load(open(a.moveset, encoding="utf-8"))
        try:
            verify_moveset_audit(moveset_doc, source_bytes)
        except ValueError as exc:
            sys.exit(str(exc))
        if a.geno:
            provenance = Path(a.geno).with_name("conversion_losses.json")
            geno_sources = Path(a.geno).with_name("overlay_sources.json")
            if not provenance.is_file() or not geno_sources.is_file():
                sys.exit("Geno ACMD profile needs conversion_losses.json and overlay_sources.json beside --geno")
            geno_audit = json.loads(provenance.read_text(encoding="utf-8"))
            profile_audit = geno_audit.get("audit", {})
            if profile_audit.get("source_sha256") != hashlib.sha256(Path(acmd_path).read_bytes()).hexdigest():
                sys.exit("Geno ACMD audit is missing or stale for this source")
            generator_hashes = {hashlib.sha256((Path(HERE) / name).read_bytes()).hexdigest()
                                for name in ("trail_specials_geno.py", "trail_magic_geno.py")}
            if (profile_audit.get("generator_sha256") not in generator_hashes or
                    profile_audit.get("profile_sha256") != hashlib.sha256(Path(a.geno).read_bytes()).hexdigest() or
                    profile_audit.get("manifest_sha256") != hashlib.sha256(geno_sources.read_bytes()).hexdigest()):
                sys.exit("Geno ACMD profile, generator, or source mapping changed; regenerate the profile")
    global HOST
    HOST = dict(HOSTS[a.host], name=a.host)
    HOST["rows"] = len(host_ir()["behavior"]["subactions"])
    name = a.name or f"Ultimate {a.fighter.capitalize()}"
    ui_label = a.ui_label or ("SORA" if a.fighter == "trail" else name.removeprefix("Ultimate ").upper())
    stem = a.pl[:-4]
    out = a.out or os.path.join(ROOT, "_build", "tmp", "ultimate-mods", f"ultimate-{a.fighter}-slot")
    if a.out:
        os.environ["GW_ULTIMATE_ANIM_CACHE"] = os.path.join(out, "_work", "anim-cache")
    files = os.path.join(out, "files"); os.makedirs(files, exist_ok=True)
    for audit_file in ("conversion_losses.json", "hitbox_positions.json"):
        Path(out, audit_file).write_text(json.dumps({"version": 1, "status": "pending"}) + "\n",
                                         encoding="utf-8")
    rep = {"fighter": a.fighter, "name": name, "pl": a.pl, "row": {"internal": a.dst_k, "external": a.dst_e}}

    ir = json.load(open(os.path.join(CA.INSTANCES, f"{a.fighter}.ultimate-body.ir.json"), encoding="utf-8"))
    plan = plan_parts.plan(ir); rest = CA.rest_of(ir); J = fighter_joints(plan, rest)
    if plan["unresolved"]: sys.exit(f"plan has unresolved roles: {plan['unresolved']}")
    body_dir = Path(CA.FIGHTERS, a.fighter, "model", "body")
    try:
        costumes = discover_costumes(body_dir, a.c00_only)
    except ValueError as exc:
        sys.exit(str(exc))
    missing_ui = UI.missing_sources(a.ui_root, a.fighter) if a.ui_art != "off" else []
    if missing_ui and a.ui_art == "required":
        sys.exit(f"Ultimate UI art required, but {len(missing_ui)} BNTX files are missing; first: {missing_ui[0]}")

    # 1-2. slot files + host fighter data
    log = subprocess.run([sys.executable, os.path.join(HALBERD, "tools", "mk_slot_files.py"), "--out", files,
                          "--base", os.path.join(out, "_nobase"), "--pl", a.pl, "--name", name,
                          "--dst-k", str(a.dst_k), "--dst-e", str(a.dst_e),
                          "--src-k", str(HOST["internal"]), "--src-e", str(HOST["external"]),
                          "--src-icon-joint", str(HOST["icon"])], capture_output=True, text=True)
    if log.returncode: sys.exit("mk_slot_files failed: " + log.stderr[-1500:])
    rep["slot_files"] = json.loads(log.stdout)
    if a.ui_art == "off":
        rep["ui_art"] = {"status": "host placeholders (--ui-art off)"}
    elif missing_ui:
        warning = (f"Ultimate UI art unavailable ({len(missing_ui)} BNTX files missing, first: "
                   f"{missing_ui[0]}); keeping {a.host}'s CSS icon, CSP and stock art")
        print("warning: " + warning, file=sys.stderr)
        rep["ui_art"] = {"status": "host placeholders", "warning": warning}
    else:
        rep["ui_art"] = UI.install(files, a.fighter, a.dst_k, a.dst_e, ui_label, a.ui_root, ISO_ACE)
    g = mex_hsd.Gcm(ISO_ACE)
    open(os.path.join(files, a.pl), "wb").write(g.read(f"Pl{HOST['code']}.dat"))

    # 3. costumes: all share the plan's skeleton, but their DObj layouts can differ.
    work = costume_workdir(out)
    tmpl = work / "template_Nr.dat"; tmpl.write_bytes(g.read(f"Pl{HOST['code']}Nr.dat"))
    fb = glob.glob(os.path.join(HERE, "fighterbuild", "bin", "**", "fighterbuild.exe"), recursive=True)
    if not fb: sys.exit("build ports/ir/tools/fighterbuild first (dotnet build -c Release)")
    jsym, msym = "Ply%s5K_Share_joint" % name.replace(" ", ""), "Ply%s5K_Share_matanim_joint" % name.replace(" ", "")
    mesh = None
    costume_groups = []
    costume_files = []
    rep["costumes"] = []
    for source, color in costumes:
        converted = EM.export(a.fighter, source, fold_helpers=a.fold_helpers, lod=a.lod,
                              tex_format=a.tex_format)
        if mesh is not None and converted["joints"] != mesh["joints"]:
            sys.exit(f"{source}: costume skeleton differs from c00")
        if mesh is None:
            mesh = converted
        costume_groups.append([d["group"] for d in converted["dobjs"]])
        mpath = work / f"mesh_{source}.json"
        with open(mpath, "w", encoding="utf-8") as fh:
            json.dump(converted, fh)
        filename = f"{stem}{color}.dat"
        build_report = work / f"costume_report_{source}.json"
        r = subprocess.run([fb[0], "build", str(mpath), str(tmpl), os.path.join(files, filename), jsym, msym,
                            str(build_report)] + (["--pc-palette", str(a.pc_palette)] if a.pc_palette else [])
                           + (["--tex-format", a.tex_format] if a.tex_format else []),
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit(f"fighterbuild {source} failed: " + r.stdout[-800:] + r.stderr[-800:])
        costume_files.append(filename)
        rep["costumes"].append({"source": source, "file": filename, "build": r.stdout.strip(),
                                 "dobjs": len(converted["dobjs"])})
    rep["costume"] = rep["costumes"][0]["build"]

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
    for r_ in range(HOST["rows"]):
        o = mt + r_ * 0x18
        if o in w.relocs and w.u32(o + 8):
            if w.u32(o + 0x10) & 0x3F != HOST["internal"]:
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
    host_names = {s["index"]["value"]: s["name"] for s in host_ir()["behavior"]["subactions"]}
    host_doc = host_ir()
    host_subactions = {s["index"]["value"]: s for s in host_doc["behavior"]["subactions"]}
    host_clip_frames = {c["id"]: c["frames"] for c in host_doc["assets"]["animations"]["clips"]}
    allowed = set(CA.read_clip_list(a.clip_list)) | {a.fallback} if a.clip_list else None
    moveset = {int(k): v for k, v in (moveset_doc or json.load(open(a.moveset)))["rows"].items()} if a.moveset else {}
    # --row-clips (trail_specials_geno.py clips.json): rows whose Geno overlay supplies the script
    # and only need the fighter's clip
    for k, c in (json.load(open(a.row_clips))["subaction_clips"].items() if a.row_clips else []):
        moveset.setdefault(int(k), {"name": f"row {k}", "script": None, "words": None, "clip": c})
    try:
        admit_empty_motion_rows(rows, foreign, host_names, moveset, clips)
    except ValueError as exc:
        sys.exit(str(exc))
    if allowed is not None:
        allowed |= {m["clip"] for m in moveset.values()}
    matched, not_shipped = {}, {}
    for r_, act in rows.items():
        c, how_ = match_clip(host_names.get(r_), by_key)
        if r_ in moveset:
            c, how_ = moveset[r_]["clip"], "exact"
            if c not in clips: sys.exit(f"moveset row {r_}: no clip {c}")
        if c is None:
            c, how_ = match_clip(act, by_key)
        if c is not None:
            matched.setdefault(c, []).append(r_)
        if c is not None and ((allowed is not None and c not in allowed) or (a.common_only and r_ >= COMMON_ROWS and r_ not in moveset)):
            not_shipped.setdefault(c, []).append(host_names.get(r_) or act); c = a.fallback
        elif c is None: unmatched.append(act); c = a.fallback
        elif how_ != "exact": fuzzy[act] = f"{c} ({how_})"
        wanted.setdefault(c, []).append(r_)
    if a.write_clip_list:
        with open(a.write_clip_list, "w", encoding="utf-8") as fh:
            fh.write(f"# clips {a.fighter}'s rows use on the {name} host (install_ultimate.py --write-clip-list)\n"
                     f"# 'common' = played by a common-action row (< {COMMON_ROWS}); edit and pass back with --clip-list\n")
            for c in sorted(set(matched) | {a.fallback}):
                rs = matched.get(c, [])
                tag = "common" if any(r_ < COMMON_ROWS for r_ in rs) else "special"
                fh.write(f"{c:28} # {tag}: {', '.join(sorted({host_names.get(r_, str(r_)) for r_ in rs}))[:150]}\n")
    orient, aim = ({}, []) if a.fold_helpers else CA.helper_constraints(a.fighter)
    if aim: sys.exit(f"{len(aim)} aim constraints: not baked yet, rerun with --fold-helpers")
    # Root motion: a row the host drives from the animation (flag 0x80000000, the host IR's subaction
    # flags) keeps the root's travel; every other row gets the clip with it held at frame 0
    # (convert_ultimate_anim.strip_root). A clip used both ways is converted twice.
    # Ultimate's motion_list marks the motions whose clip moves the fighter (`move`); on a common
    # ground row whose physics reads the extracted TransN (ground friction / attack physics,
    # ft_80085030) those become animation-driven too, and the row gets 0x80000000. Walk, run,
    # turn, jumps, falls, air, ledge, down and wall rows keep Melee's physics (their clips carry
    # `move` for Ultimate's own locomotion); special rows are Geno states with their own physics.
    host_flags = {s["index"]["value"]: int(s["flags"]["raw"], 16) for s in host_ir()["behavior"]["subactions"]}
    ml = AP.motion_list(a.fighter)
    move_clips = {v["clip"] for v in ml.values() if v["clip"] and v["move"]} -                  {v["clip"] for v in ml.values() if v["clip"] and not v["move"]}
    physics_rows = re.compile(r"^(Wait|Walk|Turn|Run|Dash$|Kneebend|Jump|Fall|Squat|Landing|Guard|Escape|"
                              r"AttackAir|Damage|Down|Passive|Cliff|Ceil|Wall|Stop|Swim|Ladder|Pass|Ottotto|Entry|Dead|Rebound)")
    move_rows = {}
    for c, rs in wanted.items():
        if c in move_clips:
            for r_ in rs:
                if r_ < COMMON_ROWS and not host_flags.get(r_, 0) & 0x80000000 and                    not physics_rows.match(host_names.get(r_) or ""):
                    host_flags[r_] = host_flags.get(r_, 0) | 0x80000000
                    move_rows[r_] = (host_names.get(r_), c)
    root = CA.root_joint(plan)
    variants = {}
    for c, rs in wanted.items():
        for r_ in rs:
            variants.setdefault((c, bool(host_flags.get(r_, 0) & 0x80000000)), []).append(r_)
    wanted = variants
    root_report = {}
    aj = bytearray(); clip_at = {}; vis_of = {}; worst = 0.0; conv = []
    jobs = [(a.fighter, c, driven, root if not driven else None, not a.fold_helpers,
             f"Ply{name.replace(' ', '')}5K_Share_ACTION_{c}{'_drv' if driven else ''}_figatree", base)
            for c, driven in sorted(wanted)]
    for key_c, (arc, world, vis, stripped, sym) in zip(sorted(wanted), convert_all(jobs, a.jobs)):
        c, driven = key_c
        if stripped is not None:
            root_report[c] = stripped
        worst = max(worst, world)
        if len(arc) > 0x20000: sys.exit(f"{c}: {len(arc)} bytes, over FT_ANIM_BUF_SIZE")
        while len(aj) % 0x20: aj.append(0)
        clip_at[key_c] = (len(aj), len(arc), sym); aj += arc
        vis_of[key_c] = vis
        conv.append({"clip": c, "anim_driven": driven, "rows": wanted[key_c], "bytes": len(arc), "world_err": round(world, 4),
                     "common": any(r_ < COMMON_ROWS for r_ in wanted[key_c])})
    host_aj = g.read(f"Pl{HOST['code']}AJ.dat")
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
            if r_ in move_rows: w.put(o + 0x10, w.u32(o + 0x10) | 0x80000000)
    rep["animations"] = {"file": f"{stem}AJ.dat", "bytes": len(aj), "clips": len(clip_at), "rows": len(rows),
                         "unmatched_rows_played_as_fallback": sorted({u for u in unmatched if u}),
                         "matched_by_rule": fuzzy,
                         "host_clips_kept_for_other_skeletons": sorted(foreign),
                         "worst_world_error": round(worst, 4),
                         "bytes_common_clips": sum(x["bytes"] for x in conv if x["common"]),
                         "helpers": "folded" if a.fold_helpers else f"{len(orient)} orient constraints baked",
                         "anim_driven_by_move_flag": {str(k): v for k, v in sorted(move_rows.items())},
                         "root_travel_stripped": {"joint": root, "per_clip": root_report,
                                                  "max_per_axis": {ax: max([v[ax] for v in root_report.values()] or [0]) for ax in "xyz"},
                                                  "anim_driven_clips": sorted({c for c, d in wanted if d})},
                         "clips_not_shipped": {c: sorted(set(v)) for c, v in not_shipped.items()}}

    # 5. ftData joint fields
    ftd = plan["ftdata"]
    jn = lambda e: e["joint"]
    # x8: ModelVis model 0 = every distinct visible set (states); part bytes item/shield/head/feet
    all_sets = sorted({s for v in vis_of.values() for s in v}, key=lambda s: sorted(s))
    default = (vis_of.get((a.fallback, False)) or vis_of.get((a.fallback, True)) or [frozenset()])[0]
    if default in all_sets: all_sets.remove(default)
    states = [default] + all_sets
    controlled = sorted({g_ for s in states for g_ in s} | set(base))
    NROWS = 8
    vt = write_costume_modelvis(w, states, costume_groups, controlled)
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
    # x20 shield pose samples b00guard; x5C metal / parts model stays at rest.
    guard_anim = CA.decode(os.path.join(motion, "b00guard.nuanmb"))
    guard_pose = guard_pose_joints(guard_anim, plan, rest, J, orient)
    install_ftdata_pose_trees(w, fd, J, guard_pose)
    # host slot map (scripts, hurtboxes)
    slot_to_joint, scale, how = host_slot_map(J, plan)
    # x30 hurtboxes: capsules fitted to the fighter's own mesh (plan_hurtboxes.py), or with
    # --host-hurtboxes the host's capsules moved onto the fighter's joints (offsets in fighter units)
    x30 = w.u32(fd + 0x30); n = w.u32(x30); arr = w.u32(x30 + 4)
    hurt_bones, hb = set(), []
    if not a.host_hurtboxes:
        import plan_hurtboxes as PH
        hres, _ = PH.plan(a.fighter, a.fallback, mesh)
        caps = hres["capsules"]
        if not 0 < len(caps) <= 15: sys.exit(f"{len(caps)} hurtboxes (the engine holds 15)")
        arr = w.alloc(bytes(0x28 * len(caps)))
        for i, c in enumerate(caps):
            w.data[arr + 0x28 * i:arr + 0x28 * (i + 1)] = struct.pack(">3i7f", c["joint"], c["height"], c["grabbable"],
                                                                      *c["a"], *c["b"], c["radius"])
            hurt_bones.add(c["joint"])
            hb.append({"segment": c["segment"], "joint": c["joint_name"], "radius": round(c["radius"], 3)})
        w.put(x30, len(caps)); w.ptr(x30 + 4, arr); n = 0
    for i in range(n):
        o = arr + 0x28 * i
        b = struct.unpack(">i", w.data[o:o + 4])[0]; nb = slot_to_joint.get(b, 0)
        w.data[o:o + 4] = struct.pack(">i", nb); hurt_bones.add(nb)
        vals = struct.unpack(">7f", w.data[o + 0xC:o + 0x28])
        w.data[o + 0xC:o + 0x28] = struct.pack(">7f", *[v / scale for v in vals])
        hb.append({"host_slot": b, "joint": J[nb]["name"]})
    # x2C bone dynamics (Marth's cape and hair chains): the host's chains name ITS part slots; the
    # ported model's own swinging bones are animated by its clips, so the host's chains are cut
    x2c = w.u32(fd + 0x2C)
    rep["host_bone_dynamics_dropped"] = w.u32(x2c) if x2c else 0
    if x2c: w.put(x2c, 0)
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
    # vis_of includes both frame 0 and the final frame; the FigaTree length
    # used by ftcmd is the final frame index (50 for Sora's WalkMiddle).
    row_clips = {r_: (c, len(vis_of[(c, driven)]) - 1)
                 for (c, driven), rs in wanted.items() for r_ in rs}
    rewritten_loops = {}
    for r_ in sorted(rows):
        if r_ in moveset:  # translated scripts replace the host script below
            continue
        po = mt + r_ * 0x18 + 0xC
        if po not in w.relocs:
            continue
        src = w.u32(po)
        try:
            if not validate_script(w, src):
                continue
            host_clip = host_subactions[r_].get("clip")
            host_frames = host_clip_frames.get(host_clip)
            clip, new_frames = row_clips[r_]
            rewritten, detail = rewrite_host_loop(w, src, host_frames or 0, new_frames)
        except (ValueError, KeyError) as exc:
            sys.exit(f"host script row {r_} ({host_names.get(r_)}): {exc}")
        w.ptr(po, rewritten)
        rewritten_loops[r_] = {"motion": host_names.get(r_), "clip": clip,
                               "host_frames": host_frames, "new_frames": new_frames,
                               **detail}
    rep["host_loop_rewrites"] = rewritten_loops
    for r_, m in sorted(moveset.items()):
        words = m["words"]
        if words is None:
            continue
        if not words or words[-1] >> 26 != 0: sys.exit(f"moveset row {r_}: script does not end in End")
        w.ptr(mt + r_ * 0x18 + 0xC, w.alloc(b"".join(struct.pack(">I", x) for x in words)))
    rep["moveset_rows"] = {r_: f"{m['name']} {m['script']} -> {m['clip']} ({len(m['words'] or [])} words)" for r_, m in sorted(moveset.items())}
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
                try:
                    cache[key_] = merge_vis(w, src, events, len(seq), mv)
                except ValueError as exc:
                    raise ValueError(f"{c} row {r_} ({host_names.get(r_)}), events {events!r}: {exc}") from exc
            w.ptr(po, cache[key_])
            mv["rows"] += 1; mv["events"] += len(events)
    rep["modelvis"] = mv
    script_findings = []
    rows_checked = 0
    for r_ in range(HOST["rows"]):
        po = mt + r_ * 0x18 + 0xC
        if po not in w.relocs:
            continue
        rows_checked += 1
        try:
            script_findings.extend({"row": r_, "motion": host_names.get(r_), **finding}
                                   for finding in validate_script(w, w.u32(po)))
        except ValueError as exc:
            sys.exit(f"script loop validation row {r_} ({host_names.get(r_)}): {exc}")
    rep["script_loop_validation"] = {"rows_checked": rows_checked, "findings": script_findings}
    if script_findings:
        sys.exit(f"unsafe script loops in installed moveset: {script_findings[:8]}")
    validate_ftdata_pose_trees(w, fd, len(J))
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

    # MxDt: clone the animation filename, then replace the costume table and count.
    mx = os.path.join(files, "MxDt.dat")
    raw = open(mx, "rb").read()
    class _Gcm:
        def __init__(self, iso): pass
        def read(self, nm): return raw if nm == "MxDt.dat" else mex_hsd.Gcm(ISO_ACE).read(nm)
    real = mex_hsd.Gcm; mex_hsd.Gcm = _Gcm
    argv = sys.argv
    sys.argv = ["mxdt_clone.py", "--out", mx, "--pl", a.pl, "--name", name, "--aj", f"{stem}AJ.dat",
                "--src-k", str(a.dst_k), "--src-e", str(a.dst_e), "--dst-k", str(a.dst_k), "--dst-e", str(a.dst_e)]
    import contextlib, io, runpy
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            runpy.run_path(os.path.join(ROOT, "experiment", "brawl-kirby", "tools", "mxdt_clone.py"), run_name="__main__")
    finally:
        sys.argv = argv; mex_hsd.Gcm = real
    costume_row = Writer(open(mx, "rb").read())
    write_costume_rows(costume_row, a.dst_k, a.dst_e, costume_files, jsym, msym)
    costume_row.save(mx)
    rep["costume_count"] = len(costume_files)

    json.dump({"id": f"ultimate-{a.fighter}-slot", "name": f"{name.upper()} (Ultimate, own skeleton)", "version": "0.1.0",
               "kind": "fighter", "requires": [], "conflicts": ["metaknight-slot"],
               **({"engine": {"pobj_palette": 1}} if a.pc_palette else {}),
               "description": f"{name} from Smash Ultimate on its own skeleton, as an m-ex fighter replacing ACE's row "
                              f"{a.dst_k}/{a.dst_e} (the row metaknight-slot uses). {a.host.capitalize()}'s fighter data and scripts are the "
                              f"host behaviour. Built by ports/ir/tools/install_ultimate.py."},
              open(os.path.join(out, "mod.json"), "w"), indent=1)
    # Geno profile: the translated scripts' PUTs (ANIM_RATE for FT_MOTION_RATE) run only for a fighter
    # with one. --geno copies a full profile (specials, magic); else a minimal one attaches to the slot.
    if a.geno:
        shutil.copy(a.geno, os.path.join(out, "geno.json"))
        if geno_sources:
            shutil.copy(geno_sources, os.path.join(out, "overlay_sources.json"))
        gdir = os.path.join(os.path.dirname(a.geno), "geno")      # the profile's overlay scripts
        if os.path.isdir(gdir):
            shutil.copytree(gdir, os.path.join(out, "geno"), dirs_exist_ok=True)
    else:
        json.dump({"geno": 1, "fighters": [{"attach": a.pl, "name": name}]},
                  open(os.path.join(out, "geno.json"), "w"), indent=1)
    try:
        overlay_findings = validate_geno_overlays(os.path.join(out, "geno.json"))
    except ValueError as exc:
        sys.exit(f"Geno script loop validation: {exc}")
    rep["script_loop_validation"]["geno_overlay_findings"] = overlay_findings
    if overlay_findings:
        sys.exit(f"unsafe Geno overlay loops: {overlay_findings[:8]}")
    if a.extra_files:
        for f in os.listdir(a.extra_files):
            shutil.copy(os.path.join(a.extra_files, f), os.path.join(files, f))
    rep["conversion"] = conv
    json.dump(rep, open(os.path.join(out, "INSTALL.json"), "w"), indent=1)
    if a.skip_acmd_audit:
        marker = {"version": 1, "audit_skipped": True, "flag": "--skip-acmd-audit"}
        Path(out, "conversion_losses.json").write_text(json.dumps(marker, indent=2) + "\n", encoding="utf-8")
        Path(out, "hitbox_positions.json").write_text(json.dumps(marker, indent=2) + "\n", encoding="utf-8")
        rep["acmd_audit"] = marker
        json.dump(rep, open(os.path.join(out, "INSTALL.json"), "w"), indent=1)
    else:
        audited = []
        seen_scripts = set()
        for move in moveset.values():
            script = move.get("script")
            if not script or script in seen_scripts:
                continue
            seen_scripts.add(script)
            detail = moveset_doc.get("report", {}).get(move["name"])
            if detail is None:
                sys.exit(f"moveset script {script}: missing conversion report")
            audited.append(detail)
        host_losses = []
        for key in ("modelvis_dropped", "texanim_dropped"):
            count = rep["scripts"].get(key, 0)
            if count:
                host_losses.append({"move": f"{a.host} host scripts", "frame": 0,
                                    "what": f"{count} {key} commands", "why": "host model feature replaced by converted body"})
        if rep.get("host_bone_dynamics_dropped"):
            host_losses.append({"move": f"{a.host} host fighter", "frame": 0,
                                "what": "host bone dynamics", "why": "ported skeleton supplies its own animation"})
        if mv["approx_rows"]:
            host_losses.append({"move": f"{a.host} host scripts", "frame": 0,
                                "what": f"approximate ModelVis timing in {len(mv['approx_rows'])} rows",
                                "why": "host script contains non-linear timing"})
        for loss in mv.get("goto_losses", []):
            for frame, state in loss["events"]:
                host_losses.append({"move": f"{a.host} host ModelVis script {loss['script_offset']}",
                                    "frame": frame, "what": f"visibility state {state} after Goto",
                                    "why": "host item script jumps before this cosmetic visibility frame"})
        for clip, names in rep["animations"]["clips_not_shipped"].items():
            host_losses.append({"move": ", ".join(names), "frame": 0,
                                "what": f"Ultimate animation clip {clip} replaced by {a.fallback}",
                                "why": "install clip selection excludes this clip"})
        for name in rep["animations"]["unmatched_rows_played_as_fallback"]:
            host_losses.append({"move": name, "frame": 0,
                                "what": f"unmatched Ultimate animation replaced by {a.fallback}",
                                "why": "no matching Ultimate clip for host motion row"})
        for clip, travel in rep["animations"]["root_travel_stripped"]["per_clip"].items():
            if any(value for value in travel.values()):
                host_losses.append({"move": clip, "frame": 0,
                                    "what": f"animation root travel {travel}",
                                    "why": "host physics drives the root on these rows"})
        audited.append({"losses": host_losses})
        audited.append({"losses": moveset_doc.get("omissions", [])})
        if geno_audit is not None:
            audited.append(geno_audit)
        reported_losses = write_losses(os.path.join(out, "conversion_losses.json"), *audited)
        from check_hitbox_positions import check_install
        try:
            position_report = check_install(a.fighter, out, acmd_path, a.moveset,
                                            joint_probe=a.joint_probe,
                                            overlay_sources=(os.path.join(out, "overlay_sources.json")
                                                             if geno_sources else None))
        except ValueError as exc:
            sys.exit(f"installed hitbox position audit failed: {exc}")
        rep["hitbox_position_check"] = position_report
        rep["acmd_audit"] = {"status": "passed", "loss_count": len(reported_losses)}
        json.dump(rep, open(os.path.join(out, "INSTALL.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k not in ("conversion", "slot_files")}, indent=1)[:4000])
    print(f"-> {out}  (scene token p1={rep['name'].replace(' ', '').lower()})")


if __name__ == "__main__":
    sys.exit(main())
