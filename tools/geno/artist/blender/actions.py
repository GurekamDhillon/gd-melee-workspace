"""actions.py - example actions for the starter, written against ROLES, not bone names, so they pose any skeleton the starter builds.

Pose language (per role, degrees; applied hierarchically, in the rest-pose armature axes so "forward" means forward):
    f   swing forward   (limbs hanging down swing forward, a spine/neck/head tips forward; sign handled per bone direction)
    o   swing outward   (away from the centre line; sign handled per side and bone direction)
    t   twist about the bone's own axis
    rx, ry, rz   raw rotation about the armature axes (X side, Y depth, Z up; right-hand rule), applied after f/o
    hips only: dx, dy, dz  translation in armature units (x side, y depth with -y forward, z up)
The poses are samples of a plain function per clip: read them, copy one, change the numbers. Every clip keys EVERY animated bone on
EVERY frame at 60 fps with linear interpolation (what the importer wants, spec section 10).
"""
import json
import math

import bpy
from bpy_extras import anim_utils
from mathutils import Matrix, Vector

S = math.sin
C = math.cos
PI = math.pi


class Rig:
    def __init__(self, arm, bones, prop):
        self.arm, self.bones, self.p = arm, bones, prop
        self.by_role = {b["role"]: b for b in bones}
        self.rest = {}
        self.dirs = {}
        for b in bones:
            pb = arm.pose.bones[b["name"]]
            self.rest[b["role"]] = pb.bone.matrix_local.to_3x3()
            d = Vector(b["tail"]) - Vector(b["head"])
            self.dirs[b["role"]] = d.normalized() if d.length > 1e-6 else Vector((0, 0, 1))
        self.keyed = [b["role"] for b in bones if b["deform"]]

    def basis(self, role, spec):
        d = self.dirs[role]
        side = 1 if role.endswith(".L") else (-1 if role.endswith(".R") else 0)
        f = spec.get("f", 0)
        # forward swing: tip moves toward -Y. Rx(theta) takes +Z toward -Y, so up-pointing bones use +theta, down-pointing bones -theta.
        rx = spec.get("rx", 0) + (f if d.z >= 0 else -f)
        o = spec.get("o", 0)
        # outward: Ry(phi) moves an up-pointing tip toward +X for phi>0 and a down-pointing tip toward -X.
        ry = spec.get("ry", 0) + (o * side * (1 if d.z >= 0 else -1))
        rz = spec.get("rz", 0)
        D = Matrix.Rotation(math.radians(rz), 3, "Z") @ Matrix.Rotation(math.radians(ry), 3, "Y") @ Matrix.Rotation(math.radians(rx), 3, "X")
        t = spec.get("t", 0)
        if t:
            D = D @ Matrix.Rotation(math.radians(t), 3, d)
        R = self.rest[role]
        return (R.inverted() @ D @ R).to_quaternion()

    def loc(self, v):
        R = self.rest["hips"]
        return R.inverted() @ Vector(v)


def make_action(rig, name, frames, fn, loop=False, hit=None, root_motion=False):
    arm = rig.arm
    arm.animation_data_create()
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    slot = act.slots.new(id_type="OBJECT", name=arm.name)
    arm.animation_data.action = act
    arm.animation_data.action_slot = slot
    cb = anim_utils.action_ensure_channelbag_for_slot(act, slot)
    for b in rig.bones:
        arm.pose.bones[b["name"]].rotation_mode = "QUATERNION"
    data = {}
    for i in range(frames):
        pose = fn(i, frames, rig.p)
        for role in rig.keyed:
            q = rig.basis(role, pose.get(role, {}))
            data.setdefault(role, []).append((q, rig.loc((pose.get("hips", {}).get("dx", 0), pose.get("hips", {}).get("dy", 0), pose.get("hips", {}).get("dz", 0))) if role == "hips" else None))
    for role in rig.keyed:
        bname = rig.by_role[role]["name"]
        for k in range(4):
            fc = cb.fcurves.new('pose.bones["%s"].rotation_quaternion' % bname, index=k, group_name=bname)
            fc.keyframe_points.add(frames)
            co = []
            for i in range(frames):
                co += [float(i), float(data[role][i][0][k])]
            fc.keyframe_points.foreach_set("co", co)
            fc.keyframe_points.foreach_set("interpolation", [1] * frames)
            fc.update()
        if role == "hips":
            for k in range(3):
                fc = cb.fcurves.new('pose.bones["%s"].location' % bname, index=k, group_name=bname)
                fc.keyframe_points.add(frames)
                co = []
                for i in range(frames):
                    co += [float(i), float(data[role][i][1][k])]
                fc.keyframe_points.foreach_set("co", co)
                fc.keyframe_points.foreach_set("interpolation", [1] * frames)
                fc.update()
    act["geno_loop"] = bool(loop)
    if hit:
        act["geno_hit_frames"] = json.dumps(list(hit))
        try:
            for h in hit:
                m = act.pose_markers.new("hit")
                m.frame = int(h)
        except Exception:  # noqa: BLE001
            pass
    if root_motion:
        act["geno_root_motion"] = True
    return act


# ---- clips ----------------------------------------------------------------------------------------------------------
def _ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def wait(i, n, P):
    ph = 2 * PI * i / n
    return {"chest": {"f": 1.5 * S(ph)}, "spine": {"f": 1.0 * S(ph)}, "head": {"f": -1.0 * S(ph)},
            "hips": {"dz": -0.06 * (0.5 - 0.5 * C(ph))},
            "upper_arm.L": {"f": 2 * S(ph), "o": 2 * S(ph)}, "upper_arm.R": {"f": 2 * S(ph), "o": 2 * S(ph)},
            "lower_arm.L": {"f": 8}, "lower_arm.R": {"f": 8}}


def _gait(amp, knee, arm, lean, bob, elbow):
    def fn(i, n, P):
        ph = 2 * PI * i / n
        out = {"hips": {"dz": -bob * abs(C(ph)) + 0.0, "dy": -0.0}, "spine": {"f": lean}, "chest": {"f": lean * 0.5, "rz": 6 * S(ph)}}
        for s, sg in (("L", 1), ("R", -1)):
            a = ph if s == "L" else ph + PI
            out["upper_leg." + s] = {"f": amp * S(a)}
            out["lower_leg." + s] = {"f": -(knee * max(0.0, C(a + 0.6)) + 6)}
            out["foot." + s] = {"rx": 10 * C(a)}
            out["upper_arm." + s] = {"f": -arm * S(a), "o": 4}
            out["lower_arm." + s] = {"f": elbow + 0.3 * elbow * max(0.0, -S(a))}
        return out
    return fn


walk = _gait(32, 40, 24, 4, 0.14, 18)
run = _gait(48, 95, 45, 14, 0.28, 80)


def jump_f(i, n, P):
    x = i / (n - 1)
    crouch = S(PI * min(1.0, x / 0.45)) if x < 0.45 else 0.0
    stretch = _ease((x - 0.35) / 0.5)
    out = {"hips": {"dz": -0.9 * crouch + 0.3 * stretch}, "spine": {"f": 12 * crouch - 6 * stretch}}
    for s in "LR":
        out["upper_leg." + s] = {"f": 40 * crouch - 8 * stretch}
        out["lower_leg." + s] = {"f": -75 * crouch}
        out["upper_arm." + s] = {"f": -30 * crouch + 150 * stretch, "o": 10 + 15 * stretch}
        out["lower_arm." + s] = {"f": 10}
    return out


def jump_aerial(i, n, P):
    x = i / (n - 1)
    tuck = S(PI * x)
    out = {"spine": {"f": 8 * tuck}, "hips": {"dz": 0.0}}
    for s in "LR":
        out["upper_leg." + s] = {"f": 60 * tuck + 8, "o": 6}
        out["lower_leg." + s] = {"f": -100 * tuck}
        out["upper_arm." + s] = {"f": 60 + 30 * tuck, "o": 40}
        out["lower_arm." + s] = {"f": 25}
    return out


def fall(i, n, P):
    ph = 2 * PI * i / n
    out = {"spine": {"f": 3}}
    for s, sg in (("L", 1), ("R", -1)):
        out["upper_leg." + s] = {"f": 12 + 5 * S(ph * sg), "o": 8}
        out["lower_leg." + s] = {"f": -30 - 6 * S(ph)}
        out["upper_arm." + s] = {"f": 50 + 6 * S(ph), "o": 55}
        out["lower_arm." + s] = {"f": 20}
    return out


def landing(i, n, P):
    x = i / (n - 1)
    c = S(PI * x)
    out = {"hips": {"dz": -0.9 * c}, "spine": {"f": 14 * c}}
    for s in "LR":
        out["upper_leg." + s] = {"f": 45 * c}
        out["lower_leg." + s] = {"f": -85 * c}
        out["upper_arm." + s] = {"f": 25 * c}
    return out


def _guard_pose(k):
    out = {"hips": {"dz": -0.3 * k}, "spine": {"f": 10 * k}, "head": {"f": 6 * k}}
    for s in "LR":
        out["upper_leg." + s] = {"f": 14 * k}
        out["lower_leg." + s] = {"f": -28 * k}
        out["upper_arm." + s] = {"f": 62 * k, "o": -22 * k + 38 * (1 - k)}
        out["lower_arm." + s] = {"f": 95 * k}
    return out


def guard(i, n, P):
    return _guard_pose(1.0 + 0.04 * S(2 * PI * i / n))


def guard_on(i, n, P):
    return _guard_pose(_ease(i / (n - 1)))


def attack11(i, n, P):
    # left jab, strike pose on frame 3 (the Striker's jab1 hitbox starts at script frame 3), recover by frame 12
    if i <= 3:
        k = _ease(i / 3.0)
    elif i <= 6:
        k = 1.0
    else:
        k = 1.0 - _ease((i - 6) / float(n - 1 - 6))
    out = {"spine": {"f": 6 * k}, "chest": {"rz": -18 * k}, "hips": {"dz": -0.1 * k},
           "upper_leg.L": {"f": 10 * k}, "upper_leg.R": {"f": -14 * k},
           "lower_leg.L": {"f": -14 * k}, "lower_leg.R": {"f": -8 * k},
           "upper_arm.L": {"f": 82 * k, "o": -34 * k}, "lower_arm.L": {"f": 6 * k + 10 * (1 - k)},
           "upper_arm.R": {"f": -12 * k, "o": 8 * k}, "lower_arm.R": {"f": 80 * k + 10 * (1 - k)}}
    return out


def _reach(k):
    out = {"spine": {"f": 8 * k}}
    for s in "LR":
        out["upper_arm." + s] = {"f": 84 * k, "o": -30 * k + 38 * (1 - k)}
        out["lower_arm." + s] = {"f": 8}
        out["upper_leg." + s] = {"f": 8 * k}
        out["lower_leg." + s] = {"f": -16 * k}
    return out


def catch(i, n, P):
    return _reach(_ease(i / 5.0) if i < 6 else 1.0)


def catch_wait(i, n, P):
    out = _reach(1.0)
    out["spine"]["f"] = 8 + 1.5 * S(2 * PI * i / n)
    return out


def throw_f(i, n, P):
    x = i / (n - 1)
    k = _ease(x / 0.8)
    out = {"spine": {"f": 8 + 24 * k - (10 * _ease((x - 0.85) / 0.15))}, "chest": {"rz": 0}, "hips": {"dz": -0.2 * k}}
    for s in "LR":
        out["upper_arm." + s] = {"f": 84 - 20 * k, "o": -30}
        out["lower_arm." + s] = {"f": 8 + 40 * k * (1 - x)}
        out["upper_leg." + s] = {"f": 8 + 20 * k * (1 if s == "L" else 0)}
        out["lower_leg." + s] = {"f": -16 - 10 * k}
    return out


# name, frames, function, loop, hit frames
CLIPS = {
    "Wait": (48, wait, True, None),
    "WalkMiddle": (28, walk, True, None),
    "Run": (20, run, True, None),
    "JumpF": (14, jump_f, False, None),
    "JumpAerialF": (24, jump_aerial, False, None),
    "Fall": (16, fall, True, None),
    "Landing": (8, landing, False, None),
    "Guard": (12, guard, True, None),
    "GuardOn": (7, guard_on, False, None),
    "Attack11": (13, attack11, False, [3]),
    "Catch": (10, catch, False, [6]),
    "CatchWait": (24, catch_wait, True, None),
    "ThrowF": (14, throw_f, False, [13]),
}
DEFAULT = ["Wait", "WalkMiddle", "Run", "JumpF", "JumpAerialF", "Fall", "Landing", "Guard", "GuardOn", "Attack11", "Catch", "CatchWait", "ThrowF"]


def make_actions(arm, bones, prop, names=None):
    rig = Rig(arm, bones, prop)
    for n in (names or DEFAULT):
        frames, fn, loop, hit = CLIPS[n]
        make_action(rig, n, frames, fn, loop, hit)
    arm.animation_data.action = bpy.data.actions.get("Wait")
    for b in rig.bones:
        pb = arm.pose.bones[b["name"]]
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
