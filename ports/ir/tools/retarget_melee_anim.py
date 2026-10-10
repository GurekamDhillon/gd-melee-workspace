#!/usr/bin/env python3
"""retarget_melee_anim.py - bring a retail Melee fighter's animation (and its hitbox events) onto any other skeleton, by bone role.

    python ports/ir/tools/retarget_melee_anim.py luigi AttackAirB --dst-fighter _build/goku-xv2/author-source/fighter.json \\
        --out _build/retarget/luigi-AttackAirB            # clip npz + hitboxes.json + report.json (all local, disc-derived)
    python ports/ir/tools/retarget_melee_anim.py luigi AttackAirB --dst-fighter F.json --inject-glb in.glb out.glb --name AttackAirB

SOURCE  a retail Melee fighter on GW_ISO_VANILLA: Pl<Code>Nr.dat (the joint tree and rest pose), PlCo.dat (the parts table, which names each
        joint's common part and therefore its role), Pl<Code>.dat (the 0x18-byte action rows: figatree name, AJ offset/size, script) and
        Pl<Code>AJ.dat (the FigaTree). The row is found by action name (`..._ACTION_<Name>_figatree`), so any fighter and any action works.
TARGET  a Geno artist `fighter.json` (glb + `roles`: bone name -> artist role), or any Rig built in code. Roles are the artist roles
        (docs/geno-artist-spec.md 4): translation, hips, spine, chest, neck, head, shoulder/upper_arm/lower_arm/hand, upper_leg/lower_leg/foot/toe.

SOLVER  per matched role, in world space (so the source's XRotN/YRotN/TransN carriers and a different rest posture are handled):
        - delta   R_dst = D * R_dst_rest, D = R_src(t) * R_src_rest^-1                         (hips, spine, chest, neck, head, hands, feet)
        - limb    the bone's direction follows the source's (T-pose against A-pose rests are reconciled): swing = shortest arc from the
                  destination rest direction to D * (source rest direction), twist = D's twist about the source bone axis, re-applied about the
                  destination axis.
        - a source with fewer torso bones than the destination (Melee has WaistN only; XV2 has Spine1/Spine2/Chest) drives `spine` with half
          the delta and `chest` with all of it.
        - hips translation = destination rest + size_ratio * (source hips world position - its rest position).
        Local rotations are then recovered against the destination parent's solved world rotation, so unmatched bones (helpers, knees,
        armor) keep their rest locals and follow. Non-hip translation, scale tracks and the source's unnamed joints are NOT carried; the
        report says how large they were.

HITBOXES  `decode_script` reads the row's ftcmd script (tools/geno/script.py words); `retarget_hitbox` re-expresses a sphere on a source joint
        on the destination joint of the same role: the offset along the bone (as a fraction of the child distance) and the offset across it
        are rebuilt in the destination bone's frame, scaled by the size ratio; size is scaled by the same ratio.

Everything read from the disc stays under _build (git-ignored). The unit tests (test_retarget_melee_anim.py) use synthetic rigs only.
"""
import argparse
import json
import math
import os
import struct
import sys

import numpy as np
from scipy.spatial.transform import Rotation as R

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import figatree as F  # noqa: E402

# Melee common part (PlCo parts table order, see build_melee_fighter.COMMON) -> artist role (docs/geno-artist-spec.md 4)
PART_ROLE = {"TransN": "translation", "HipN": "hips", "WaistN": "spine", "BustN": "chest", "NeckN": "neck", "HeadN": "head",
             "ThrowN": "grab_anchor"}
for _s, _n in (("L", "L"), ("R", "R")):
    PART_ROLE.update({f"{_s}ShoulderN": f"shoulder.{_n}", f"{_s}ShoulderJ": f"upper_arm.{_n}", f"{_s}ArmJ": f"lower_arm.{_n}",
                      f"{_s}HandN": f"hand.{_n}", f"{_s}LegJ": f"upper_leg.{_n}", f"{_s}KneeJ": f"lower_leg.{_n}",
                      f"{_s}FootJ": f"foot.{_n}", f"{_s}HaveN": f"item_socket.{_n}"})
# the role the direction of a limb bone is measured toward
CHILD_ROLE = {}
for _n in "LR":
    CHILD_ROLE.update({f"upper_arm.{_n}": f"lower_arm.{_n}", f"lower_arm.{_n}": f"hand.{_n}", f"upper_leg.{_n}": f"lower_leg.{_n}",
                       f"lower_leg.{_n}": f"foot.{_n}", f"foot.{_n}": f"toe.{_n}"})
CHILD_ROLE["neck"] = "head"
# solve order does not matter (each bone is absolute); this is the report order
ROLES_SOLVED = ["hips", "spine", "chest", "neck", "head"] + [f"{p}.{n}" for n in "LR" for p in
                ("shoulder", "upper_arm", "lower_arm", "hand", "upper_leg", "lower_leg", "foot", "toe")]
# retail fighters: name -> (internal FighterKind, file code)
RETAIL = {"mario": (0, "Mr"), "fox": (1, "Fx"), "captain": (2, "Ca"), "falcon": (2, "Ca"), "donkey": (3, "Dk"), "kirby": (4, "Kb"),
          "koopa": (5, "Kp"), "link": (6, "Lk"), "seak": (7, "Sk"), "ness": (8, "Ns"), "peach": (9, "Pe"), "popo": (10, "Pp"),
          "pikachu": (12, "Pk"), "samus": (13, "Ss"), "yoshi": (14, "Ys"), "purin": (15, "Pr"), "mewtwo": (16, "Mt"),
          "luigi": (17, "Lg"), "mars": (18, "Ms"), "marth": (18, "Ms"), "zelda": (19, "Zd"), "clink": (20, "Cl"),
          "drmario": (21, "Dr"), "falco": (22, "Fc"), "pichu": (23, "Pc"), "gamewatch": (24, "Gw"), "ganon": (25, "Gn"),
          "emblem": (26, "Fe"), "roy": (26, "Fe")}


# ------------------------------------------------------------------------------------------------ rigs
class Rig:
    """A skeleton: parents (-1 root), rest local TRS, and role -> joint index. Joints are listed parents first."""

    def __init__(self, names, parents, t, q, s=None, roles=None):
        self.names = list(names)
        self.parents = [int(p) for p in parents]
        self.t = np.asarray(t, float).reshape(-1, 3)
        self.q = np.asarray(q, float).reshape(-1, 4)
        self.s = np.ones_like(self.t) if s is None else np.asarray(s, float).reshape(-1, 3)
        self.roles = dict(roles or {})            # role -> joint index
        for i, p in enumerate(self.parents):
            if p >= i:
                raise ValueError("rig joints must list parents first (joint %d has parent %d)" % (i, p))

    def __len__(self):
        return len(self.names)

    def children(self, i):
        return [j for j, p in enumerate(self.parents) if p == i]

    def role_of(self, i):
        return next((r for r, j in self.roles.items() if j == i), None)

    def world(self, t=None, q=None, s=None):
        """World matrices (..., N, 4, 4) for local arrays shaped (..., N, 3|4|3); defaults to the rest pose."""
        t = self.t if t is None else t
        q = self.q if q is None else q
        s = self.s if s is None else s
        lead = np.shape(t)[:-2]
        n = len(self)
        rot = R.from_quat(np.reshape(q, (-1, 4))).as_matrix().reshape(lead + (n, 3, 3))
        loc = np.zeros(lead + (n, 4, 4))
        loc[..., :3, :3] = rot * np.asarray(s)[..., None, :]
        loc[..., :3, 3] = t
        loc[..., 3, 3] = 1
        out = np.empty_like(loc)
        for i in range(n):
            p = self.parents[i]
            out[..., i, :, :] = loc[..., i, :, :] if p < 0 else out[..., p, :, :] @ loc[..., i, :, :]
        return out

    def rest_world(self):
        return self.world()


def world_rotations(w):
    """Rotation matrices of world matrices with the scale removed (columns normalised)."""
    m = w[..., :3, :3]
    return m / np.maximum(np.linalg.norm(m, axis=-2, keepdims=True), 1e-12)


def hsd_euler(e):
    """HSD JObj rotation (radians x,y,z) -> Rotation. HSD builds Rz*Ry*Rx, i.e. scipy's extrinsic 'xyz'."""
    return R.from_euler("xyz", np.reshape(e, (-1, 3)))


def rig_from_glb(path, roles):
    """A Geno artist glb (nodes with TRS; the first skin's joints) + {bone name: role} -> Rig."""
    raw = open(path, "rb").read()
    jlen = struct.unpack_from("<I", raw, 12)[0]
    doc = json.loads(raw[20:20 + jlen])
    nodes = doc["nodes"]
    keep = doc["skins"][0]["joints"] if doc.get("skins") else list(range(len(nodes)))
    keep = sorted(set(keep))
    parent = {}
    for i, nd in enumerate(nodes):
        for c in nd.get("children", []):
            parent[c] = i
    # extra non-skin nodes that are joints' parents would break the parents-first order; glb joint lists already include them
    index = {n: k for k, n in enumerate(keep)}
    names, par, t, q, s = [], [], [], [], []
    for n in keep:
        nd = nodes[n]
        names.append(nd["name"])
        par.append(index.get(parent.get(n), -1))
        t.append(nd.get("translation", [0, 0, 0]))
        q.append(nd.get("rotation", [0, 0, 0, 1]))
        s.append(nd.get("scale", [1, 1, 1]))
    rig = Rig(names, par, t, q, s)
    rig.roles = {role: names.index(bone) for bone, role in roles.items() if bone in names}
    return rig


def rig_from_fighter_json(path):
    cfg = json.load(open(path, encoding="utf-8"))
    glb = os.path.join(os.path.dirname(os.path.abspath(path)), cfg["art"]["glb"])
    return rig_from_glb(glb, cfg["roles"])


# ------------------------------------------------------------------------------------------------ retail Melee source
def read_plco_parts(co, kind):
    """(joint_to_part table, holes) for a fighter kind, from PlCo's ftLoadCommonData."""
    r = co.public("ftLoadCommonData")
    table = co.u32(co.u32(r + 16) + 4 * kind)
    j2p, count = co.u32(table), co.u32(table + 8)
    holes = set()
    if r + 20 in co.reloc_set:
        entry_ptr = co.u32(r + 20) + 4 * kind
        if entry_ptr in co.reloc_set:
            entry = co.u32(entry_ptr)
            arr, n = co.u32(entry), co.u32(entry + 4)
            holes = {co.data[arr + 4 * i] for i in range(n)}
    return list(co.data[j2p:j2p + count]), holes, count


def read_jobj_tree(nr):
    """Depth-first JObj walk (the order the ftParts walk and the figatrees use) -> list of dicts."""
    joints = []

    def ptr(off):
        return nr.u32(off) if off in nr.reloc_set else None

    def f32s(off, n):
        return list(struct.unpack(">%df" % n, bytes(nr.data[off:off + 4 * n])))

    def walk(off, parent):
        while off is not None:
            flags = nr.u32(off + 4)
            j = {"index": len(joints), "parent": parent, "flags": flags, "rot": f32s(off + 0x14, 3),
                 "scale": f32s(off + 0x20, 3), "trans": f32s(off + 0x2C, 3)}
            joints.append(j)
            child = ptr(off + 8)
            if child is not None and not flags & (1 << 12):
                walk(child, j["index"])
            off = ptr(off + 0xC)

    root = nr.public(next(s for s, _ in nr.publics if s.endswith("_Share_joint")))
    walk(root, -1)
    return joints


def melee_rig(nr, co, kind):
    """Rig of a retail fighter's neutral model, with roles from the PlCo parts table."""
    from build_melee_fighter import COMMON
    joints = read_jobj_tree(nr)
    j2p, holes, count = read_plco_parts(co, kind)
    slot, part = [], 0
    for _ in joints:
        while part in holes:
            part += 1
        slot.append(part)
        part += 1
    if part != count:
        raise ValueError("part walk ends at %d, the parts table says %d" % (part, count))
    names, roles = [], {}
    for j, s in zip(joints, slot):
        common = j2p[s]
        cname = COMMON[common] if common < len(COMMON) else None
        names.append(cname or "joint%d" % j["index"])
        role = PART_ROLE.get(cname)
        if role:
            roles[role] = j["index"]
    rig = Rig(names, [j["parent"] for j in joints], [j["trans"] for j in joints],
              hsd_euler([j["rot"] for j in joints]).as_quat(), [j["scale"] for j in joints], roles)
    rig.common_slots = slot
    rig.rest_euler = np.array([j["rot"] for j in joints], float)
    return rig


class FigaClip:
    """A decoded FigaTree: per joint, a dict channel -> (start, keys). Sampled against a Rig's rest pose."""

    def __init__(self, tree, symbol=""):
        self.symbol = symbol
        self.frames = float(tree["frames"])        # last frame index; the clip has frames + 1 samples
        self.joints = []
        for tracks in tree["joints"]:
            self.joints.append({F.TT[t["type"]]: (t["start"], t["keys"]) for t in tracks if t["type"] in F.TT})

    def value(self, joint, channel, frame):
        got = self.joints[joint].get(channel) if joint < len(self.joints) else None
        if got is None:
            return None
        start, keys = got
        return F.evaluate(keys, max(0.0, frame - start))

    def sample(self, rig, frames):
        """Local t (F,N,3), q (F,N,4), s (F,N,3) at `frames`; channels without a track keep the rig's rest value (Euler per axis)."""
        n, nf = len(rig), len(frames)
        t = np.tile(rig.t, (nf, 1, 1))
        s = np.tile(rig.s, (nf, 1, 1))
        rest_e = getattr(rig, "rest_euler", None)
        rest_e = R.from_quat(rig.q).as_euler("xyz") if rest_e is None else rest_e   # raw JObj euler keeps untracked axes exact
        e = np.tile(rest_e, (nf, 1, 1))
        rotated = np.zeros(n, bool)
        for j, chans in enumerate(self.joints):
            if j >= n:
                break
            for ci, ch in enumerate("XYZ"):
                if "ROT" + ch in chans:
                    e[:, j, ci] = [self.value(j, "ROT" + ch, f) for f in frames]
                    rotated[j] = True
                if "TRA" + ch in chans:
                    t[:, j, ci] = [self.value(j, "TRA" + ch, f) for f in frames]
                if "SCA" + ch in chans:
                    s[:, j, ci] = [self.value(j, "SCA" + ch, f) for f in frames]
        q = np.tile(rig.q, (nf, 1, 1))
        for j in np.flatnonzero(rotated):
            q[:, j] = hsd_euler(e[:, j]).as_quat()
        return t, q, s


# ------------------------------------------------------------------------------------------------ size ratio
def _chain_length(rig, roles):
    w = rig.rest_world()
    pts = [w[rig.roles[r], :3, 3] for r in roles if r in rig.roles]
    return sum(np.linalg.norm(b - a) for a, b in zip(pts, pts[1:])) if len(pts) == len(roles) else None


def size_ratio(src, dst):
    """destination / source size: mean of the leg and arm chain lengths both rigs have. Returns (mean, per-chain dict)."""
    per = {}
    for side in "LR":
        for name, chain in (("leg", ("upper_leg", "lower_leg", "foot")), ("arm", ("upper_arm", "lower_arm", "hand"))):
            roles = [f"{c}.{side}" for c in chain]
            a, b = _chain_length(src, roles), _chain_length(dst, roles)
            if a and b:
                per[f"{name}.{side}"] = b / a
    if not per:
        raise ValueError("no limb chain exists in both rigs; pass ratio= explicitly")
    legs = [v for k, v in per.items() if k.startswith("leg")]
    return float(np.mean(list(per.values()))), per, float(np.mean(legs)) if legs else float(np.mean(list(per.values())))


# ------------------------------------------------------------------------------------------------ the solver
def _arc(a, b):
    """Shortest rotation taking unit vectors a -> b (F,3) as Rotation."""
    a = a / np.linalg.norm(a, axis=-1, keepdims=True)
    b = b / np.linalg.norm(b, axis=-1, keepdims=True)
    cross = np.cross(a, b)
    dot = np.einsum("...i,...i->...", a, b)
    q = np.concatenate([cross, (1 + dot)[..., None]], axis=-1)
    anti = (1 + dot) < 1e-9                                         # opposite vectors: any perpendicular axis
    if np.any(anti):
        perp = np.cross(a, np.array([1.0, 0, 0]))
        small = np.linalg.norm(perp, axis=-1) < 1e-6
        perp = np.where(small[..., None], np.cross(a, np.array([0, 1.0, 0])), perp)
        perp = perp / np.linalg.norm(perp, axis=-1, keepdims=True)
        q = np.where(anti[..., None], np.concatenate([perp, np.zeros_like(dot)[..., None]], axis=-1), q)
    return R.from_quat(q / np.linalg.norm(q, axis=-1, keepdims=True))


def _twist_angle(d, axis):
    """Twist angle of rotation d about a unit `axis` (swing * twist decomposition, twist applied first)."""
    qv = d.as_quat()
    proj = qv[:, :3] @ axis
    return 2 * np.arctan2(proj, qv[:, 3])


class Retargeted:
    """The solved clip: local rotations per destination joint (F,N,4), pelvis translation, report."""

    def __init__(self, dst, frames, q, hips_t, report):
        self.dst, self.frames, self.q, self.hips_t, self.report = dst, frames, q, hips_t, report

    @property
    def rotations(self):
        return {name: self.q[:, i] for i, name in enumerate(self.dst.names)}

    def save(self, path):
        np.savez_compressed(path, names=np.array(self.dst.names), q=self.q, hips_t=self.hips_t, frames=self.frames)

    @staticmethod
    def load(path):
        z = np.load(path, allow_pickle=False)
        return {"names": list(z["names"]), "q": z["q"], "hips_t": z["hips_t"], "frames": int(z["frames"])}


def retarget(src, src_t, src_q, src_s, dst, ratio=None, leg_ratio=None, fixed_roles=()):
    """Solve a destination clip. src_t/q/s are the source's local TRS per frame (F,N,*). Returns Retargeted."""
    nf = src_q.shape[0]
    if ratio is None:
        ratio, per, leg_ratio = size_ratio(src, dst)
    else:
        per = {}
        leg_ratio = leg_ratio or ratio
    ws0 = world_rotations(src.rest_world())
    wsp = src.world(src_t, src_q, src_s)
    ws = world_rotations(wsp)
    wd0m = dst.rest_world()
    wd0 = world_rotations(wd0m)
    src_pos0 = src.rest_world()[:, :3, 3]
    dst_pos0 = wd0m[:, :3, 3]
    n = len(dst)

    def delta(role):
        js = src.roles[role]
        return R.from_matrix(ws[:, js]) * R.from_matrix(ws0[js]).inv()

    target = {}                                                       # dst joint -> Rotation (F)
    report = {"ratio": ratio, "per_chain": per, "leg_ratio": leg_ratio, "roles": {}, "unmatched_dst_roles": [], "unmatched_src_roles": []}
    for role, jd in dst.roles.items():
        if role in ("translation", "grab_anchor") or role.startswith("item_socket"):
            continue
        drv = role
        weight = 1.0
        if drv not in src.roles:
            if role == "chest" and "spine" in src.roles:
                drv = "spine"
            elif role == "toe.L" or role == "toe.R":
                drv = "foot." + role[-1] if ("foot." + role[-1]) in src.roles else None
            else:
                drv = None
        if drv is None:
            report["unmatched_dst_roles"].append(role)
            continue
        if role == "spine" and "chest" not in src.roles and "chest" in dst.roles:
            weight = 0.5                                              # the source has one torso bone: split it over spine and chest
        d = delta(drv)
        if weight != 1.0:
            d = _partial(d, weight)
        mode = "delta"
        child = CHILD_ROLE.get(role)
        if child and child in src.roles and child in dst.roles and drv == role and role not in fixed_roles:
            js, jc = src.roles[role], src.roles[child]
            jdc = dst.roles[child]
            a_s = src_pos0[jc] - src_pos0[js]
            a_d = dst_pos0[jdc] - dst_pos0[jd]
            if np.linalg.norm(a_s) > 1e-9 and np.linalg.norm(a_d) > 1e-9:
                a_s, a_d = a_s / np.linalg.norm(a_s), a_d / np.linalg.norm(a_d)
                want = d.apply(np.tile(a_s, (nf, 1)))
                swing = _arc(np.tile(a_d, (nf, 1)), want)
                theta = _twist_angle(d, a_s)
                twist = R.from_rotvec(theta[:, None] * a_d)
                target[jd] = swing * twist * R.from_matrix(wd0[jd])
                mode = "limb"
        if jd not in target:
            target[jd] = d * R.from_matrix(wd0[jd])
        report["roles"][role] = {"driven_by": drv, "mode": mode, "weight": weight}
    report["unmatched_src_roles"] = sorted(r for r in src.roles if r not in dst.roles and r in ROLES_SOLVED)
    # local rotations against the destination parent's solved world rotation (unmatched joints keep their rest local)
    wd = np.empty((nf, n, 3, 3))
    q = np.empty((nf, n, 4))
    for i in range(n):
        p = dst.parents[i]
        parent_w = R.from_matrix(wd[:, p]) if p >= 0 else None
        if i in target:
            loc = (parent_w.inv() * target[i]) if parent_w is not None else target[i]
        else:
            loc = R.from_quat(np.tile(dst.q[i], (nf, 1)))
        q[:, i] = loc.as_quat()
        wd[:, i] = ((parent_w * loc) if parent_w is not None else loc).as_matrix()
    # pelvis translation: destination rest + ratio * the source hips' world displacement
    hips = np.tile(dst.t[dst.roles["hips"]], (nf, 1)) if "hips" in dst.roles else np.zeros((nf, 3))
    if "hips" in src.roles and "hips" in dst.roles:
        disp = wsp[:, src.roles["hips"], :3, 3] - src_pos0[src.roles["hips"]]
        hips = hips + leg_ratio * disp
    return Retargeted(dst, nf, q, hips, report)


def _partial(d, w):
    """Rotation d scaled toward identity by weight w (rotation-vector scaling, per frame)."""
    return R.from_rotvec(d.as_rotvec() * w)


def solved_world(res):
    """Destination world matrices of a Retargeted clip (hips translation applied) for error measures."""
    dst = res.dst
    t = np.tile(dst.t, (res.frames, 1, 1))
    if "hips" in dst.roles:
        t[:, dst.roles["hips"]] = res.hips_t
    return dst.world(t, res.q, np.tile(dst.s, (res.frames, 1, 1)))


def pose_error(src, src_t, src_q, src_s, res, ratio, leg_ratio=None):
    """Per-role end-effector error: destination joint world position vs the source's scaled about the hips. Returns {role: (max, mean)}
    in destination units, plus the destination limb length for scale."""
    ws = src.world(src_t, src_q, src_s)
    wd = solved_world(res)
    dst = res.dst
    hs = src.roles.get("hips")
    hd = dst.roles.get("hips")
    out = {}
    for role, jd in dst.roles.items():
        if role not in src.roles or role in ("translation", "hips", "grab_anchor") or role.startswith("item_socket"):
            continue
        js = src.roles[role]
        ps = ws[:, js, :3, 3] - ws[:, hs, :3, 3]
        pd = wd[:, jd, :3, 3] - wd[:, hd, :3, 3]
        err = np.linalg.norm(pd - ratio * ps, axis=1)
        out[role] = (float(err.max()), float(err.mean()))
    return out


# ------------------------------------------------------------------------------------------------ hitboxes
def decode_hitbox(ws):
    """One ftcmd Create Hitbox (opcode 11, 5 words) -> dict. Offsets are bone-local (x along w1 low, y/z in w2); the raw words are kept so
    bits the Geno `hitbox` command does not name (sound kind/level) can be carried."""
    w0, w1, w2, w3, w4 = ws
    signed = lambda n: (n if n < 32768 else n - 65536) / 256
    return {"slot": w0 >> 23 & 7, "joint": w0 >> 11 & 255, "damage": w0 & 1023, "size": (w1 >> 16) / 256, "x": signed(w1 & 65535),
            "y": signed(w2 >> 16), "z": signed(w2 & 65535), "angle": w3 >> 23, "kbg": w3 >> 14 & 511, "fkb": w3 >> 5 & 511,
            "bkb": w4 >> 23, "element": w4 >> 18 & 31, "shield": (w4 >> 10 & 255) if (w4 >> 10 & 255) < 128 else (w4 >> 10 & 255) - 256,
            "ground": w4 >> 1 & 1, "air": w4 & 1, "raw": [int(w) for w in ws]}


def decode_script(words):
    """ftcmd words -> timeline of events [{frame, kind, ...}] for the commands that matter to a port: waits (frame accounting), hitbox,
    clear, cmd_var (landing-lag/auto-cancel flag), sfx, iasa, end. `frame` is the game frame the command runs on."""
    from tools.geno import script
    events, frame = [], 0
    for off, ws in script.commands(words):
        op = ws[0] >> 26
        text = script.friendly(ws).split(" ", 1)[0] if op != 11 else "hitbox"
        if op == 11:
            events.append(dict(frame=frame, kind="hitbox", **decode_hitbox(ws)))
        elif text in ("wait", "wait_until", "frame"):
            line = script.friendly(ws)
            n = int(float(line.split()[1].split("=")[-1])) if len(line.split()) > 1 else 0
            frame = n if text in ("wait_until", "frame") else frame + n
        else:
            events.append(dict(frame=frame, kind=text, text=script.friendly(ws), words=[int(w) for w in ws]))
    return events


def bone_frame(rig, joint):
    """(child_direction_local unit, child_distance) of a joint: toward its first child with a nonzero offset (else the +X axis, 1)."""
    for c in rig.children(joint):
        v = rig.t[c] * rig.s[joint]
        d = np.linalg.norm(v)
        if d > 1e-9:
            return v / d, d
    return np.array([1.0, 0, 0]), 1.0


def retarget_hitbox(hb, src, dst, src_joint, dst_joint, ratio):
    """Re-express a sphere centre given in `src_joint`'s frame in `dst_joint`'s frame. The part along the bone keeps its fraction of the
    bone length; the part across it is rotated with the bone axis and scaled by `ratio`. Returns a new dict (size scaled by ratio)."""
    ds, ls = bone_frame(src, src_joint)
    dd, ld = bone_frame(dst, dst_joint)
    c = np.array([hb["x"], hb["y"], hb["z"]])
    along = float(c @ ds)
    across = c - along * ds
    align = _arc(ds[None], dd[None])
    centre = dd * (along / ls * ld) + ratio * align.apply(across[None])[0]
    out = dict(hb)
    out.update(x=float(centre[0]), y=float(centre[1]), z=float(centre[2]), size=hb["size"] * ratio, joint=dst_joint)
    return out


def hitbox_words(hb, joint=None, scale=1.0):
    """Re-encode a decoded hitbox into five ftcmd words with a new joint and size/offset scale, keeping the unnamed bits."""
    w = list(hb["raw"])
    q16 = lambda v: int(round(v * 256)) & 0xFFFF
    if joint is not None:
        w[0] = (w[0] & ~(255 << 11)) | (int(joint) << 11)
    size = int(round(hb["size"] * scale * 256))
    if not 0 <= size <= 0xFFFF:
        raise ValueError("scaled hitbox size out of range")
    for v in (hb["x"], hb["y"], hb["z"]):
        if not -128 <= v * scale <= 127.99:
            raise ValueError("scaled hitbox offset out of range")
    w[1] = (size << 16) | q16(hb["x"] * scale)
    w[2] = (q16(hb["y"] * scale) << 16) | q16(hb["z"] * scale)
    return w


# ------------------------------------------------------------------------------------------------ disc access
def load_retail(fighter, action, iso=None):
    """Read a retail fighter's action from the vanilla disc -> dict(rig, clip, words, row, symbol). Needs GW_ISO_VANILLA."""
    from tools.mex_port import mex_hsd
    key = fighter.lower()
    if key not in RETAIL:
        raise ValueError("unknown retail fighter %r (%s)" % (fighter, ", ".join(sorted(RETAIL))))
    kind, code = RETAIL[key]
    iso = iso or os.environ.get("GW_ISO_VANILLA")
    if not iso:
        raise ValueError("GW_ISO_VANILLA is not set (source .env)")
    disc = mex_hsd.Gcm(iso)
    co = mex_hsd.Archive(disc.read("PlCo.dat"))
    pl = mex_hsd.Archive(disc.read("Pl%s.dat" % code))
    nr = mex_hsd.Archive(disc.read("Pl%sNr.dat" % code))
    aj = disc.read("Pl%sAJ.dat" % code)
    rig = melee_rig(nr, co, kind)
    root = pl.public(next(s for s, _ in pl.publics if s.startswith("ftData")))
    table = pl.u32(root + 0xC)
    suffix = "_ACTION_%s_figatree" % action
    rows = (len(pl.data) - table) // 0x18
    for row in range(min(rows, 400)):
        o = table + row * 0x18
        if o not in pl.reloc_set:
            continue
        name = pl.cstr(pl.u32(o))
        if name.endswith(suffix):
            off, size, script_ptr = pl.u32(o + 4), pl.u32(o + 8), pl.u32(o + 0xC) if o + 0xC in pl.reloc_set else None
            sym, tree = F.parse_archive(aj[off:off + size])
            from tools.geno import export
            words = export.read_script(pl, script_ptr) if script_ptr is not None else []
            return {"rig": rig, "clip": FigaClip(tree, sym), "words": words, "row": row, "symbol": sym, "fighter": key, "action": action}
    raise ValueError("%s has no action %s" % (fighter, action))


def sample_frames(clip):
    return np.arange(int(round(clip.frames)) + 1, dtype=float)


# ------------------------------------------------------------------------------------------------ glb injection
def inject_glb_animation(glb_in, glb_out, name, res, fps=60.0):
    """Append the clip to a glb as one animation: rotation channels for every joint, translation for the pelvis."""
    raw = open(glb_in, "rb").read()
    jlen = struct.unpack_from("<I", raw, 12)[0]
    doc = json.loads(raw[20:20 + jlen])
    pos = 20 + jlen
    blen = struct.unpack_from("<I", raw, pos)[0]
    blob = bytearray(raw[pos + 8:pos + 8 + blen])
    names = [n["name"] for n in doc["nodes"]]

    def add(arr, typ, bounds=False):
        arr = np.ascontiguousarray(arr, "<f4")
        while len(blob) % 4:
            blob.append(0)
        view = {"buffer": 0, "byteOffset": len(blob), "byteLength": arr.nbytes}
        blob.extend(arr.tobytes())
        doc["bufferViews"].append(view)
        acc = {"bufferView": len(doc["bufferViews"]) - 1, "componentType": 5126, "count": int(arr.shape[0]), "type": typ}
        if bounds:
            acc.update(min=[float(arr.min())], max=[float(arr.max())])
        doc["accessors"].append(acc)
        return len(doc["accessors"]) - 1

    times = add(np.arange(res.frames) / fps, "SCALAR", True)
    an = {"name": name, "samplers": [], "channels": []}

    def channel(bone, path, values, typ):
        an["samplers"].append({"input": times, "output": add(values, typ), "interpolation": "LINEAR"})
        an["channels"].append({"sampler": len(an["samplers"]) - 1, "target": {"node": names.index(bone), "path": path}})

    for i, bone in enumerate(res.dst.names):
        channel(bone, "rotation", res.q[:, i], "VEC4")
    if "hips" in res.dst.roles:
        channel(res.dst.names[res.dst.roles["hips"]], "translation", res.hips_t, "VEC3")
    doc.setdefault("animations", [])
    doc["animations"] = [a for a in doc["animations"] if a.get("name") != name] + [an]
    doc["buffers"][0]["byteLength"] = len(blob)
    js = json.dumps(doc, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    while len(blob) % 4:
        blob.append(0)
    out = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(blob))
    out += struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(blob), 0x004E4942) + bytes(blob)
    open(glb_out, "wb").write(out)


# ------------------------------------------------------------------------------------------------ CLI
def run(fighter, action, dst_json, out_dir, ratio=None, iso=None):
    got = load_retail(fighter, action, iso)
    src, clip = got["rig"], got["clip"]
    dst = rig_from_fighter_json(dst_json)
    frames = sample_frames(clip)
    t, q, s = clip.sample(src, frames)
    mean, per, leg = size_ratio(src, dst)
    use = ratio or mean
    res = retarget(src, t, q, s, dst, ratio=use, leg_ratio=leg if ratio is None else ratio)
    err = pose_error(src, t, q, s, res, use)
    os.makedirs(out_dir, exist_ok=True)
    res.save(os.path.join(out_dir, "clip.npz"))
    events = decode_script(got["words"])
    carried = {"scale_tracks": sorted({j for j, c in enumerate(clip.joints) if any(k.startswith("SCA") for k in c)}),
               "translation_tracks": sorted({j for j, c in enumerate(clip.joints) if any(k.startswith("TRA") for k in c)}),
               "rotation_tracks_unmapped": sorted({j for j, c in enumerate(clip.joints) if any(k.startswith("ROT") for k in c)
                                                   and src.names[j].startswith("joint")})}
    report = {"source": {"fighter": fighter, "action": action, "row": got["row"], "symbol": got["symbol"], "frames": clip.frames,
                         "samples": len(frames)},
              "destination": os.path.abspath(dst_json), "ratio": use, "size_ratios": per, "leg_ratio": leg, "solver": res.report,
              "end_effector_error": {k: {"max": v[0], "mean": v[1]} for k, v in err.items()}, "not_carried": carried,
              "src_joint_roles": src.roles, "dst_joint_roles": dst.roles}
    json.dump(report, open(os.path.join(out_dir, "report.json"), "w"), indent=2)
    json.dump({"events": events, "src_roles": {str(v): k for k, v in src.roles.items()}, "src_names": src.names,
               "src_rest_t": src.t.tolist(), "src_parents": src.parents},
              open(os.path.join(out_dir, "script.json"), "w"), indent=1)
    return res, report, events, got


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fighter")
    ap.add_argument("action", help="action name as in the figatree symbol, e.g. AttackAirB")
    ap.add_argument("--dst-fighter", required=True, help="Geno artist fighter.json (glb + roles)")
    ap.add_argument("--out", required=True, help="output directory (disc-derived: keep it under _build)")
    ap.add_argument("--ratio", type=float, help="override the size ratio")
    ap.add_argument("--inject-glb", nargs=2, metavar=("IN", "OUT"))
    ap.add_argument("--name", help="animation name for --inject-glb (default: the action)")
    args = ap.parse_args()
    res, report, events, got = run(args.fighter, args.action, args.dst_fighter, args.out, args.ratio)
    if args.inject_glb:
        inject_glb_animation(args.inject_glb[0], args.inject_glb[1], args.name or args.action, res)
    worst = max((v["max"] for v in report["end_effector_error"].values()), default=0)
    print("%s %s -> %d frames, ratio %.3f, worst end-effector error %.3f units, %d script events"
          % (args.fighter, args.action, res.frames, report["ratio"], worst, len(events)))


if __name__ == "__main__":
    main()
