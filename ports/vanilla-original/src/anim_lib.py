"""Pose DSL, forward kinematics, analytic leg IK and clip sampling for the Courier rig (Blender Python).

Authoring conventions (all angles in degrees; authoring space is Z-up, the character faces -Y, left = +X):

  P(hp, tp, tor, hy, hd, aL, aR, lL, lR, fl, fr, cuL, cuR, shL, shR, toL, toR)

  hp   hips offset (left, forward, up) in units from the rest pelvis (up<0 crouches)
  tp   trans offset (left, forward, up): ROOT MOTION. Only a few clips use it (see manifest root_motion)
  tor  (lean forward, side bend toward the character's left, twist toward the left) shared by hips/spine/chest
  hy   extra hips yaw (twist to the left)
  fp   whole-body pitch about the hips (forward positive): somersaults, lying poses
  hd   (nod down, tilt left, turn left) shared by neck/head
  aL/aR   arm (fwd swing, abduction from vertical hanging, twist, elbow flex, wrist flex); rest A-pose is abduction 38
  lL/lR   FK leg (thigh lift forward, thigh abduct, knee flex, ankle toes-up). Ignored when fl/fr is set
  fl/fr   IK foot: (out, forward, up, toes-up pitch): ankle target relative to the rest ankle, in WORLD space (planted
          while the hips move; moves with `tp`); None switches the leg to FK
  cuL/cuR fist curl 0 (open) .. 1 (fist)
  shL/shR shoulder (shrug up, protract forward)
  toL/toR toe flex (toes up)
Rotations are composed as R = Rx(swing) * Ry(abduct) * Rz(twist) (Euler 'ZYX') and converted to each bone's
local basis quaternion with q = Rb^-1 d Rb (Rb = bone rest orientation). No bone is ever scaled.
"""
import bpy, math, sys, os
from mathutils import Matrix, Vector, Quaternion, Euler
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

ORDER = [b["name"] for b in C.BONES]
REST_HEAD = {b["name"]: Vector(b["head"]) for b in C.BONES}
PARENT = {b["name"]: b["parent"] for b in C.BONES}
REST_R = {}       # bone -> 3x3 rest orientation in armature space (filled by init_rig)
ANIMATED = [b["name"] for b in C.BONES if b["deform"]] + ["trans"]
ARM_REST_ABD = 38.0
LEG1 = {s: (REST_HEAD[f"thigh_{s}"], REST_HEAD[f"shin_{s}"], REST_HEAD[f"foot_{s}"]) for s in "LR"}

def init_rig(arm_ob):
    for b in arm_ob.data.bones:
        REST_R[b.name] = b.matrix_local.to_3x3()

# ------------------------------------------------------------------ pose object
DEFAULTS = dict(hp=(0, 0, 0), tp=(0, 0, 0), tor=(0, 0, 0), hy=0.0, fp=0.0, hd=(0, 0, 0),
                aL=(0, 12, 0, 14, 0), aR=(0, 12, 0, 14, 0),
                lL=(0, 0, 0, 0), lR=(0, 0, 0, 0), fl=(0, 0, 0, 0), fr=(0, 0, 0, 0),
                cuL=1.0, cuR=1.0, shL=(0, 0), shR=(0, 0), toL=0.0, toR=0.0)

class Pose:
    def __init__(self, **kw):
        self.v = dict(DEFAULTS)
        for k, x in kw.items():
            if k not in DEFAULTS: raise KeyError(k)
            self.v[k] = x
    def copy(self, **kw):
        p = Pose(); p.v = dict(self.v)
        for k, x in kw.items():
            if k not in DEFAULTS: raise KeyError(k)
            p.v[k] = x
        return p
    def add(self, **kw):
        """Offset tuple/scalar params additively."""
        p = self.copy()
        for k, x in kw.items():
            a = p.v[k]
            if isinstance(a, tuple): p.v[k] = tuple(ai + xi for ai, xi in zip(a, x))
            elif a is None: p.v[k] = x
            else: p.v[k] = a + x
        return p
    def mirror(self):
        v = self.v
        def mt(t): return (-t[0], t[1], t[2]) if t is not None else None
        out = Pose()
        out.v = dict(v)
        out.v["hp"] = (-v["hp"][0], v["hp"][1], v["hp"][2]); out.v["tp"] = (-v["tp"][0], v["tp"][1], v["tp"][2])
        out.v["tor"] = (v["tor"][0], -v["tor"][1], -v["tor"][2]); out.v["hy"] = -v["hy"]
        out.v["hd"] = (v["hd"][0], -v["hd"][1], -v["hd"][2])
        for a, b in (("aL", "aR"), ("lL", "lR"), ("fl", "fr"), ("cuL", "cuR"), ("shL", "shR"), ("toL", "toR")):
            out.v[a], out.v[b] = v[b], v[a]
        return out

def P(**kw): return Pose(**kw)

def lerp_val(a, b, u):
    if a is None or b is None: return b if u >= 1 else a if (a is not None) else b
    if isinstance(a, tuple): return tuple(x + (y - x) * u for x, y in zip(a, b))
    return a + (b - a) * u

def lerp_pose(a, b, u):
    p = Pose()
    for k in DEFAULTS:
        p.v[k] = lerp_val(a.v[k], b.v[k], u)
    return p

EASES = {
    "lin": lambda u: u,
    "smooth": lambda u: u * u * (3 - 2 * u),
    "in": lambda u: u * u,
    "out": lambda u: 1 - (1 - u) * (1 - u),
    "fast": lambda u: 1 - (1 - u) ** 3,
    "hold": lambda u: 0.0 if u < 1 else 1.0,
}

class Clip:
    def __init__(self, name, n, loop=False, serves="", status="full", wind=6.0, root_motion=False, keys=None,
                 gen=None, ref=None, notes="", hit=None, category="common", fit=True):
        self.name, self.n, self.loop, self.serves, self.status = name, n, loop, serves, status
        self.wind, self.root_motion = wind, root_motion
        self.keys = keys or []
        self.gen = gen            # optional generator: f(frame_float) -> Pose (used instead of keys)
        self.ref = ref or {}      # extra manifest data (stride, speeds)
        self.notes = notes
        self.hit = hit            # list of hit frames (for the move clips), documentation + validation
        self.category = category
        self.fit = fit
    def key(self, frame, pose, ease="smooth"):
        self.keys.append((float(frame), pose, ease)); return self
    def sample(self, f):
        if self.gen: return self.gen(f)
        ks = self.keys
        if self.loop:
            # cyclic: wrap the key list
            ks = ks + [(ks[0][0] + self.n, ks[0][1], ks[0][2])]
            f = f % self.n
            if f < ks[0][0]: f += self.n
        if f <= ks[0][0]: return ks[0][1]
        for (f0, p0, _), (f1, p1, e1) in zip(ks, ks[1:]):
            if f0 <= f <= f1:
                u = 0 if f1 == f0 else (f - f0) / (f1 - f0)
                return lerp_pose(p0, p1, EASES[e1](u))
        return ks[-1][1]

# ------------------------------------------------------------------ FK / IK
def _rot(sx_rx_ry_rz):
    rx, ry, rz = (math.radians(a) for a in sx_rx_ry_rz)
    return Euler((rx, ry, rz), "ZYX").to_matrix()

def dsl_to_d(bone, rx, ry, rz):
    s = C.SIGNS[bone]
    return _rot((s[0] * rx, s[1] * ry, s[2] * rz))

def arc(a, b):
    a = a.normalized(); b = b.normalized()
    q = a.rotation_difference(b)
    return q.to_matrix()

def solve_leg(side, H, T, A_hips, forward_pole=Vector((0, -1, 0))):
    """Two-bone IK. H hip joint, T ankle target. Returns (A_thigh, A_shin, ankle_pos, knee_pos)."""
    hh, kh, ah = LEG1[side]
    l1 = (kh - hh).length; l2 = (ah - kh).length
    d = T - H
    dist = d.length
    dist = max(min(dist, (l1 + l2) * 0.9995), abs(l1 - l2) + 1e-3)
    dirv = d.normalized()
    a = (l1 * l1 - l2 * l2 + dist * dist) / (2 * dist)
    h = math.sqrt(max(l1 * l1 - a * a, 0.0))
    pole = forward_pole - dirv * forward_pole.dot(dirv)
    if pole.length < 1e-4: pole = Vector((0, -1, 0))
    pole.normalize()
    K = H + dirv * a + pole * h
    ank = H + dirv * dist
    A_thigh = arc(kh - hh, K - H)
    A_shin = arc(A_thigh @ (ah - kh), ank - K) @ A_thigh
    return A_thigh, A_shin, ank, K

def eval_pose(pose, with_world=False):
    """Returns {bone: (quat, loc)} (loc only for trans/hips) and, optionally, world head positions."""
    v = pose.v
    hp = v["hp"]; tp = v["tp"]
    d = {b: Matrix.Identity(3) for b in ORDER}
    # torso distribution
    lean, side, twist = v["tor"]
    d["hips"] = dsl_to_d("hips", lean * 0.12 + v["fp"], side * 0.1, v["hy"])
    d["spine"] = dsl_to_d("spine", lean * 0.38, side * 0.4, twist * 0.4)
    d["chest"] = dsl_to_d("chest", lean * 0.5, side * 0.5, twist * 0.6)
    nod, tilt, turn = v["hd"]
    d["neck"] = dsl_to_d("neck", nod * 0.4, tilt * 0.4, turn * 0.4)
    d["head"] = dsl_to_d("head", nod * 0.6, tilt * 0.6, turn * 0.6)
    for sd, ak, lk, ck, sk, tk in (("L", "aL", "lL", "cuL", "shL", "toL"), ("R", "aR", "lR", "cuR", "shR", "toR")):
        f, o, t, e, w = v[ak]
        d[f"upperarm_{sd}"] = dsl_to_d(f"upperarm_{sd}", f, o - ARM_REST_ABD, t)
        d[f"forearm_{sd}"] = dsl_to_d(f"forearm_{sd}", e, 0, 0)
        d[f"hand_{sd}"] = dsl_to_d(f"hand_{sd}", w, 0, 0)
        c = v[ck]
        d[f"fingers_{sd}"] = dsl_to_d(f"fingers_{sd}", 70 * (1 - c), 0, 0)
        d[f"thumb_{sd}"] = dsl_to_d(f"thumb_{sd}", 40 * (1 - c), 30 * (1 - c), 0)
        su, sp_ = v[sk]
        d[f"clavicle_{sd}"] = dsl_to_d(f"clavicle_{sd}", 0, su, sp_)
        tf, to, tk_, ta = v[lk]
        d[f"thigh_{sd}"] = dsl_to_d(f"thigh_{sd}", tf, to, 0)
        d[f"shin_{sd}"] = dsl_to_d(f"shin_{sd}", tk_, 0, 0)
        d[f"foot_{sd}"] = dsl_to_d(f"foot_{sd}", ta, 0, 0)
        d[f"toe_{sd}"] = dsl_to_d(f"toe_{sd}", v[tk], 0, 0)
    A, Pw = {}, {}
    out = {}
    for b in ORDER:
        p = PARENT[b]
        Ap = A[p] if p else Matrix.Identity(3)
        if b == "root":
            A[b] = Matrix.Identity(3); Pw[b] = REST_HEAD[b].copy(); continue
        if p:
            Pw[b] = Pw[p] + Ap @ (REST_HEAD[b] - REST_HEAD[p])
        if b == "trans":
            Pw[b] = REST_HEAD[b] + Vector((tp[0], -tp[1], tp[2]))   # left=+X, forward=-Y
        if b == "hips":
            Pw[b] = Pw[b] + Vector((hp[0], -hp[1], hp[2]))
        # IK legs
        if b in ("thigh_L", "thigh_R"):
            sd = b[-1]
            ik = v["fl" if sd == "L" else "fr"]
            if ik is not None:
                out_, fwd, up, pitch = ik
                sx = 1 if sd == "L" else -1
                rest_ank = REST_HEAD[f"foot_{sd}"]
                T = rest_ank + Vector((sx * out_, -fwd, up)) + Vector((tp[0], -tp[1], tp[2]))
                At, As, ank, K = solve_leg(sd, Pw[b], T, Ap)
                A[b] = At
                d[b] = Ap.inverted() @ At
                A[f"shin_{sd}"] = As
                d[f"shin_{sd}"] = At.inverted() @ As
                Afoot = Matrix.Rotation(0, 3, "Z") @ _rot((-pitch * (1 if True else 1), 0, 0))
                d[f"foot_{sd}"] = As.inverted() @ Afoot
                A[f"foot_{sd}"] = Afoot
                Pw[f"shin_{sd}"] = K; Pw[f"foot_{sd}"] = ank
                # the thigh itself
                continue
        if b in ("shin_L", "shin_R") and v["fl" if b[-1] == "L" else "fr"] is not None:
            continue                          # already done with the thigh
        if b in ("foot_L", "foot_R") and v["fl" if b[-1] == "L" else "fr"] is not None:
            continue
        A[b] = Ap @ d[b]
    # IK path set A/Pw for shin/foot out of order: finish children of the foot (toes) positions
    for b in ORDER:
        if b in ("toe_L", "toe_R"):
            p = PARENT[b]
            Pw[b] = Pw[p] + A[p] @ (REST_HEAD[b] - REST_HEAD[p])
            A[b] = A[p] @ d[b]
    for b in ANIMATED:
        Rb = REST_R[b]
        q = (Rb.inverted() @ d[b] @ Rb).to_quaternion()
        loc = None
        if b == "trans":
            loc = Rb.inverted() @ Vector((tp[0], -tp[1], tp[2]))
        elif b == "hips":
            loc = Rb.inverted() @ Vector((hp[0], -hp[1], hp[2]))
        out[b] = (q, loc)
    return (out, Pw, A) if with_world else out

# ------------------------------------------------------------------ hips fitting and procedural helpers
def fit_hips(pose, margin=0.955, min_drop=0.0):
    """Lower the hips just enough that both IK legs can reach their targets with slightly bent knees."""
    v = pose.v
    hp = v["hp"]; tp = v["tp"]
    rest_h = REST_HEAD["hips"]
    best = 0.0
    need = None
    for sd, key in (("L", "fl"), ("R", "fr")):
        ik = v[key]
        if ik is None: continue
        out_, fwd, up, _ = ik
        sx = 1 if sd == "L" else -1
        hh, kh, ah = LEG1[sd]
        L = ((kh - hh).length + (ah - kh).length) * margin
        # hip joint (at hips pose) vs ankle target; approximate the hip joint as hips + (thigh_head - hips_head)
        ox = (REST_HEAD[f"thigh_{sd}"].x + hp[0]) - (REST_HEAD[f"foot_{sd}"].x + sx * out_ + tp[0] * 0)
        oy = (-hp[1]) - (-fwd)
        horiz2 = ox * ox + oy * oy
        if horiz2 >= L * L: hz_max = 0
        else: hz_max = math.sqrt(L * L - horiz2)
        ank_z = REST_HEAD[f"foot_{sd}"].z + up + tp[2]
        hip_joint_z_max = ank_z + hz_max
        need = hip_joint_z_max if need is None else min(need, hip_joint_z_max)
    if need is None: return pose
    z = min(hp[2], need - REST_HEAD["thigh_L"].z)
    return pose.copy(hp=(hp[0], hp[1], z))

def scarf_channels(clip, poses, wind):
    """Procedural follow-through: returns per-frame [(rx1,rz1),...(rx4,rz4)] for the 4 scarf bones (DSL degrees)."""
    n = len(poses)
    reps = 3 if clip.loop else 1
    seq = poses * reps if clip.loop else poses
    lean = [p.v["tor"][0] + p.v["hd"][0] * 0.3 for p in seq]
    hz = [p.v["hp"][2] + p.v["tp"][2] for p in seq]
    twist = [p.v["tor"][2] + p.v["hy"] for p in seq]
    fwd = [p.v["tp"][1] for p in seq]
    # target lift angle: wind, lean forward lifts the tail, and vertical acceleration whips it
    tgt = []
    for i in range(len(seq)):
        vz = hz[i] - hz[i - 1] if i > 0 else 0.0
        vy = fwd[i] - fwd[i - 1] if i > 0 else 0.0
        tgt.append(wind + 0.7 * lean[i] + 18.0 * vz + 14.0 * vy)
    tw = [0.0] + [twist[i] - twist[i - 1] for i in range(1, len(seq))]
    out = []
    state = [[wind, 0.0, 0.0] for _ in range(4)]    # angle, velocity, lateral
    lag = [0.45, 0.33, 0.25, 0.18]
    for i in range(len(seq)):
        row = []
        prev = tgt[i]
        for k in range(4):
            a, vv, lat = state[k]
            # first-order lag toward the previous segment's value (chain follow-through)
            a += (prev - a) * lag[k]
            lat += ((-tw[i] * 0.8) - lat) * lag[k]
            state[k] = [a, vv, lat]
            prev = a
            flutter = 2.2 * math.sin(2 * math.pi * (i % n) / max(n, 1) * (1 if clip.loop else 1) + k * 0.9) if clip.loop else 0.0
            row.append((a * (0.55 + 0.15 * k) + flutter, lat * (1 + 0.3 * k)))
        out.append(row)
    return out[-n:] if clip.loop else out

def bake_clip(clip):
    """Sample every frame; returns list of (frame, {bone: (quat, loc)}) with scarf follow-through, and the poses."""
    poses = []
    for f in range(clip.n):
        p = clip.sample(float(f))
        if p.v["fl"] is not None or p.v["fr"] is not None:
            p = fit_hips(p) if clip.fit else p
        poses.append(p)
    frames = []
    sc = scarf_channels(clip, poses, clip.wind)
    for f, p in enumerate(poses):
        res = eval_pose(p)
        for k in range(4):
            rx, rz = sc[f][k]
            d = dsl_to_d(f"scarf{k + 1}", rx, 0, rz)
            Rb = REST_R[f"scarf{k + 1}"]
            res[f"scarf{k + 1}"] = ((Rb.inverted() @ d @ Rb).to_quaternion(), None)
        frames.append((f, res))
    return frames, poses

NO_FIT = set()

def continuity_fix(frames):
    """Make quaternions in a channel continuous (flip sign to the shortest path)."""
    last = {}
    for f, res in frames:
        for b, (q, loc) in res.items():
            if b in last and last[b].dot(q) < 0: q = -q; res[b] = (q, loc)
            last[b] = q
    return frames
