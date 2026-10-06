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
    if (a.v["fl"] is None) != (b.v["fl"] is None) or (a.v["fr"] is None) != (b.v["fr"] is None):
        a, b = harmonize(a, b, True)
    p = Pose()
    for k in DEFAULTS:
        p.v[k] = lerp_val(a.v[k], b.v[k], u)
    return p

def extrap_pose(a, b, k):
    """a + (b - a) * k for numeric parameters (k > 1 overshoots, k < 0 anticipates); None parameters follow b."""
    p = Pose()
    for n in DEFAULTS:
        x, y = a.v[n], b.v[n]
        p.v[n] = y if (x is None or y is None) else lerp_val(x, y, k)
    return p

def _back(c1):
    c3 = c1 + 1.0
    return lambda u: 1 + c3 * (u - 1) ** 3 + c1 * (u - 1) ** 2

EASES = {
    "lin": lambda u: u,
    "smooth": lambda u: u * u * (3 - 2 * u),     # only used as a fallback: keyed 'smooth' segments are splined (see Clip.sample)
    "in": lambda u: u * u,
    "out": lambda u: 1 - (1 - u) * (1 - u),
    "fast": lambda u: 1 - (1 - u) ** 3,
    "back": _back(1.1),                           # fast arrival with a small overshoot, then settle onto the key (follow-through)
    "backs": _back(0.6),
    "hold": lambda u: 0.0 if u < 1 else 1.0,
}
# (start slope, end slope) of each ease, for the Hermite segments that follow a flowing key
def _flat_tangent(a, b, c, ta, tb):
    """Monotone (Fritsch-Carlson style) tangent at the middle of three samples a, b, c spaced ta, tb apart: 0 at an extremum."""
    d0 = (b - a) / ta; d1 = (c - b) / tb
    if d0 * d1 <= 0: return 0.0
    w1 = 2 * tb + ta; w2 = tb + 2 * ta
    return (w1 + w2) / (w1 / d0 + w2 / d1)

class Clip:
    def __init__(self, name, n, loop=False, serves="", status="full", wind=6.0, root_motion=False, keys=None,
                 gen=None, ref=None, notes="", hit=None, category="common", fit=True, lagk=1.0, life=1.0, head_follow=1.0, speed=None):
        self.name, self.n, self.loop, self.serves, self.status = name, n, loop, serves, status
        self.wind, self.root_motion = wind, root_motion
        self.keys = keys or []
        self.gen = gen            # optional generator: f(frame_float) -> Pose (used instead of keys)
        self.ref = ref or {}      # extra manifest data (stride, speeds)
        self.notes = notes
        self.hit = hit            # list of hit frames (for the move clips), documentation + validation
        self.category = category
        self.fit = fit
        self.lagk = lagk          # scale of the extremity lag (overlapping action); 0 disables
        self.life = life          # scale of the breathing added to still moments; 0 disables
        self.head_follow = head_follow
        self.speed = speed        # ground speed in units/frame the scarf should stream against (None: from ref / wind)
        self.locomotion = False   # set by the walk/run builder: validated for foot contact speed
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
        for i in range(len(ks) - 1):
            f0, p0, _ = ks[i]; f1, p1, e1 = ks[i + 1]
            if f0 <= f <= f1:
                u = 0 if f1 == f0 else (f - f0) / (f1 - f0)
                if (p0.v["fl"] is None) != (p1.v["fl"] is None) or (p0.v["fr"] is None) != (p1.v["fr"] is None):
                    p0, p1 = harmonize(p0, p1, self.fit)            # an IK leg meeting an FK leg: convert, so the legs do not pop
                    if e1 == "smooth":
                        return lerp_pose(p0, p1, EASES["smooth"](u))
                if e1 == "smooth":
                    return self._spline(ks, i, u)
                return lerp_pose(p0, p1, EASES[e1](u))
        return ks[-1][1]
    def _spline(self, ks, i, u):
        """'smooth' segment: monotone cubic Hermite through the keys, so a pose does not stop at every key (flow);
        a key next to a non-smooth segment, or the end of a clip, still eases to rest (zero tangent)."""
        f0, p0, _ = ks[i]; f1, p1, _ = ks[i + 1]
        dt = f1 - f0
        pm = ks[i - 1] if i > 0 else None                     # the key before f0
        pn = ks[i + 2] if i + 2 < len(ks) else None           # the key after f1
        flow0 = pm is not None and ks[i][2] == "smooth" and pm[0] < f0
        flow1 = pn is not None and ks[i + 2][2] == "smooth" and pn[0] > f1
        if self.loop and len(ks) > 2:
            n0 = len(ks) - 1                                  # last real key index (ks[-1] duplicates ks[0])
            if i == 0 and ks[1][2] == "smooth" and ks[0][2] == "smooth": pm, flow0 = (ks[n0 - 1][0] - self.n, ks[n0 - 1][1], ks[n0 - 1][2]), True
            if i + 1 == n0 and len(ks) > 2: pn, flow1 = (ks[1][0] + self.n, ks[1][1], ks[1][2]), True
        out = Pose()
        h00 = 2 * u ** 3 - 3 * u ** 2 + 1; h10 = u ** 3 - 2 * u ** 2 + u; h01 = -2 * u ** 3 + 3 * u ** 2; h11 = u ** 3 - u ** 2
        for k in DEFAULTS:
            a, b = p0.v[k], p1.v[k]
            if a is None or b is None:
                out.v[k] = b if u >= 1 else a if a is not None else b
                continue
            tup = isinstance(a, tuple)
            av, bv = (a, b) if tup else ((a,), (b,))
            res = []
            for j in range(len(av)):
                m0 = m1 = 0.0
                if flow0 and pm[1].v[k] is not None:
                    q = pm[1].v[k]; q = q[j] if tup else q
                    m0 = _flat_tangent(q, av[j], bv[j], f0 - pm[0], dt)
                if flow1 and pn[1].v[k] is not None:
                    q = pn[1].v[k]; q = q[j] if tup else q
                    m1 = _flat_tangent(av[j], bv[j], q, dt, pn[0] - f1)
                res.append(h00 * av[j] + h10 * dt * m0 + h01 * bv[j] + h11 * dt * m1)
            out.v[k] = tuple(res) if tup else res[0]
        return out

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
                # an ankle only turns so far: when the shin leans too much for the foot to stay at the requested pitch, the foot follows the shin
                rq = (As.inverted() @ Afoot).to_quaternion()
                lim_ = math.radians(C.JOINT_LIMITS["foot"] - 3.0)
                if rq.angle > lim_:
                    rq = Quaternion((1, 0, 0, 0)).slerp(rq, lim_ / rq.angle)
                    Afoot = As @ rq.to_matrix()
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

_FK_CACHE = {}
def ik_to_fk(pose, fit=True):
    """The same posture with both IK legs expressed as FK angles (thigh lift / abduct, knee, ankle), so a pose can blend into an
    FK-legged one (rolls, jumps, tumbles) without the foot popping. Twist of the thigh is dropped (small error)."""
    key = (id(pose), fit)
    if key in _FK_CACHE and _FK_CACHE[key][0] is pose: return _FK_CACHE[key][1]
    q = fit_hips(pose) if fit else pose
    res, Pw, A = eval_pose(q, True)
    v = q.v
    kw = {}
    for sd, ik, lk in (("L", "fl", "lL"), ("R", "fr", "lR")):
        if v[ik] is None: continue
        Ah = A["hips"]; At = A[f"thigh_{sd}"]; As = A[f"shin_{sd}"]; Af = A[f"foot_{sd}"]
        e = (Ah.inverted() @ At).to_euler("ZYX")
        sg = C.SIGNS[f"thigh_{sd}"]
        tf, to = math.degrees(e.x) / sg[0], math.degrees(e.y) / sg[1]
        es = (At.inverted() @ As).to_euler("ZYX")
        knee = math.degrees(es.x) / C.SIGNS[f"shin_{sd}"][0]
        ef = (As.inverted() @ Af).to_euler("ZYX")
        ank = math.degrees(ef.x) / C.SIGNS[f"foot_{sd}"][0]
        kw[lk] = (tf, to, knee, ank); kw[ik] = None
    out = q.copy(**kw)
    out.v["toL"] = v["toL"]; out.v["toR"] = v["toR"]
    _FK_CACHE[key] = (pose, out)
    return out

def harmonize(a, b, fit=True):
    """Make the two poses use the same kind of leg (IK or FK) per side by converting the IK one to FK."""
    ka = [(a.v[k] is None) for k in ("fl", "fr")]; kb = [(b.v[k] is None) for k in ("fl", "fr")]
    if ka == kb: return a, b
    if any(kb[i] and not ka[i] for i in range(2)):
        a = ik_to_fk(a, fit)
        ka = [(a.v[k] is None) for k in ("fl", "fr")]
    if any(ka[i] and not kb[i] for i in range(2)):
        b = ik_to_fk(b, fit)
    # if both sides are now FK where either had FK, make the remaining IK side of the other FK too
    ka = [(a.v[k] is None) for k in ("fl", "fr")]; kb = [(b.v[k] is None) for k in ("fl", "fr")]
    if ka != kb:
        if not all(ka): a = ik_to_fk(a, fit)
        if not all(kb): b = ik_to_fk(b, fit)
    return a, b

# ------------------------------------------------------------------ secondary motion: lag, head follower, breathing
LAGS = (0.6, 1.2, 2.0)           # frames: shoulder / hip, elbow / knee / head / fist, wrist / ankle / toe
LAGS_MOVE = (0.0, 0.4, 1.2)      # the Striker's strikes keep their hit frame: only the elbow and wrist trail a little
ARM_LAG = (0, 0, 1, 1, 2)        # which lag class each component of an arm (swing, abduct, twist, elbow, wrist) uses
LEG_LAG = (0, 0, 1, 2)

def _tclamp(clip, f):
    if clip.loop: return f % clip.n
    return min(max(f, 0.0), clip.n - 1.0)

def lagged_poses(clip):
    """Raw poses per frame with the extremities trailing the body (successive breaking of joints): the shoulder arrives a
    frame after the hips, then the elbow, then the wrist, with the fists last. Time shifts of the same keys, never new data."""
    lags = LAGS_MOVE if clip.category == "move" or (clip.category == "air" and clip.hit) else LAGS
    lags = tuple(l * clip.lagk for l in lags)
    out = []
    for f in range(clip.n):
        base = clip.sample(float(f))
        if clip.lagk <= 0:
            out.append(base); continue
        sm_ = [base if l == 0 else clip.sample(_tclamp(clip, f - l)) for l in lags]
        p = base.copy()
        for sd, ak, lk, ik in (("L", "aL", "lL", "fl"), ("R", "aR", "lR", "fr")):
            p.v[ak] = tuple(sm_[ARM_LAG[j]].v[ak][j] for j in range(5))
            if base.v[ik] is None and sm_[0].v[ik] is None:
                p.v[lk] = tuple(sm_[LEG_LAG[j]].v[lk][j] for j in range(4))
        for nm in ("cuL", "cuR", "toL", "toR"): p.v[nm] = sm_[1].v[nm]
        p.v["shL"] = sm_[0].v["shL"]; p.v["shR"] = sm_[0].v["shR"]
        out.append(p)
    return out

def head_follow(clip, poses):
    """The head (and neck) follows the body with a damped spring: it trails a motion and settles after it."""
    k = clip.head_follow
    if k <= 0 or not poses: return poses
    w, z = 2 * math.pi / 10.0, 0.55
    seq = poses * 3 if clip.loop else [poses[0]] * 12 + poses
    x = list(seq[0].v["hd"]); v = [0.0, 0.0, 0.0]
    res = []
    for p in seq:
        t = p.v["hd"]
        for j in range(3):
            v[j] += w * w * (t[j] - x[j]) - 2 * z * w * v[j]
            x[j] += v[j]
        res.append(tuple(x))
    res = res[-len(poses):] if clip.loop else res[12:]
    out = []
    for p, h in zip(poses, res):
        t = p.v["hd"]
        out.append(p.copy(hd=tuple(t[j] + (h[j] - t[j]) * k for j in range(3))))
    return out

def breathing(clip, poses):
    """Life in holds: a slow breath (chest, head, elbows, hips) and a tiny weight shift, faded in wherever the pose is nearly still."""
    if clip.life <= 0 or len(poses) < 4: return poses
    n = len(poses)
    def vec(p):
        v = p.v; o = []
        for k in ("hp", "tor", "hd", "aL", "aR"):
            o += list(v[k])
        o.append(v["hy"] * 1.0); o.append(v["fp"] * 1.0)
        for k in ("fl", "fr"):
            o += [x * 4.0 for x in v[k][:3]] if v[k] is not None else [0, 0, 0]
        return o
    vs = [vec(p) for p in poses]
    sp = []
    for i in range(n):
        a = vs[(i - 1) % n] if clip.loop else vs[max(0, i - 1)]
        b = vs[(i + 1) % n] if clip.loop else vs[min(n - 1, i + 1)]
        sp.append(sum(abs(x - y) for x, y in zip(a, b)) / 2.0)
    st = [max(0.0, min(1.0, 1.0 - s / 3.0)) for s in sp]
    sm2 = []
    for i in range(n):
        acc = 0.0; wsum = 0.0
        for d in range(-3, 4):
            j = (i + d) % n if clip.loop else min(max(i + d, 0), n - 1)
            w = 4 - abs(d); acc += st[j] * w; wsum += w
        sm2.append(acc / wsum)
    per = n / max(1, round(n / 80.0)) if clip.loop else 84.0
    out = []
    for i, p in enumerate(poses):
        s = sm2[i] * clip.life
        if s < 0.02: out.append(p); continue
        b = math.sin(2 * math.pi * i / per)
        b2 = math.sin(2 * math.pi * i / (per * 2.0) + 0.7) if clip.loop and per * 2.0 > n else math.sin(2 * math.pi * i / per + 0.7)
        v = p.v
        q = p.copy(hp=(v["hp"][0] + 0.05 * b2 * s, v["hp"][1], v["hp"][2] + 0.035 * b * s),
                   tor=(v["tor"][0] + 0.9 * b * s, v["tor"][1] + 0.5 * b2 * s, v["tor"][2]),
                   hd=(v["hd"][0] - 0.6 * b * s, v["hd"][1] + 0.4 * b2 * s, v["hd"][2]),
                   aL=(v["aL"][0] + 0.8 * b * s, v["aL"][1] + 0.4 * b * s, v["aL"][2], v["aL"][3] - 1.4 * b * s, v["aL"][4]),
                   aR=(v["aR"][0] + 0.8 * b * s, v["aR"][1] + 0.4 * b * s, v["aR"][2], v["aR"][3] - 1.4 * b * s, v["aR"][4]))
        out.append(q)
    return out

# ------------------------------------------------------------------ scarf: a damped chain run over the finished motion
SC_REST = [REST_HEAD[f"scarf{k}"] for k in range(1, 5)]
SC_TAIL = [Vector(C.BONE[f"scarf{k}"]["tail"]) for k in range(1, 5)]
SC_LEN = [(SC_TAIL[k] - SC_REST[k]).length for k in range(4)]
SC_DIR = [(SC_TAIL[k] - SC_REST[k]).normalized() for k in range(4)]
TORSO_R = 1.45          # scarf points keep this far from the torso axis (hips head -> neck head); the validator checks 1.3

def _capsule_push(p, a, b, r):
    ab = b - a; t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    c = a + ab * t; d = p - c; dl = d.length
    if dl < r:
        if dl < 1e-5: d = Vector((0, 1, 0)); dl = 1.0
        return c + d * (r / dl)
    return p

def scarf_sim(clip, worlds, speed):
    """worlds: per frame (Pw, A) from eval_pose. A Verlet chain of 4 segments hanging from the neck: gravity, air drag
    against the ground speed, a little bending stiffness toward the torso-rigid direction, torso capsule clearance.
    Returns, per frame, the 5 chain points (the scarf motion is derived from the body's motion, nothing is keyed)."""
    n = len(worlds)
    PRE = 24
    seq = worlds * 3 if clip.loop else [worlds[0]] * PRE + worlds
    p0 = seq[0][0]["scarf1"]
    pts = [p0.copy()]
    for k in range(4): pts.append(pts[-1] + (seq[0][1]["neck"] @ SC_DIR[k]) * SC_LEN[k])
    prev = [q.copy() for q in pts]
    air = Vector((0, speed, 0))
    out = []
    SUB = 6
    g, kd, damp, ks = 0.085, 0.32, 0.90, 0.09
    anchor_prev = p0.copy()
    for fi, (Pw, A) in enumerate(seq):
        a1 = Pw["scarf1"]
        for s_ in range(SUB):
            anchor = anchor_prev + (a1 - anchor_prev) * ((s_ + 1) / SUB)
            pts[0] = anchor
            for k in range(1, 5):
                vel = (pts[k] - prev[k]) * (damp ** (1.0 / SUB))
                rel = air - vel * SUB
                acc = Vector((0, 0, -g)) + rel * (kd / SUB) * 0.6
                want = (A["neck"] @ SC_DIR[k - 1]) * 0.5 + Vector((0, 0.3, -1.0)).normalized() * 0.5
                tgt = pts[k - 1] + want.normalized() * SC_LEN[k - 1]
                acc += (tgt - pts[k]) * (ks / SUB)
                prev[k] = pts[k].copy()
                pts[k] = pts[k] + vel + acc / SUB
            for _ in range(4):
                pts[0] = anchor
                for k in range(1, 5):
                    d = pts[k] - pts[k - 1]; dl = max(d.length, 1e-6)
                    pts[k] = pts[k - 1] + d * (SC_LEN[k - 1] / dl)
                ta, tb = Pw["hips"], Pw["neck"]
                for k in range(2, 5):
                    pts[k] = _capsule_push(pts[k], ta, tb, TORSO_R)
                pts[1] = _capsule_push(pts[1], ta, tb, TORSO_R - 0.1)
        anchor_prev = a1.copy()
        out.append([q.copy() for q in pts])
    return out[-n:] if clip.loop else out[PRE:]

def scarf_bones(pts_seq, worlds):
    """Chain points -> quaternions for scarf1..4 (parent chain starting at the neck)."""
    res = []
    for pts, (Pw, A) in zip(pts_seq, worlds):
        row = []
        Ap = A["neck"]
        for k in range(4):
            dvec = (pts[k + 1] - pts[k]).normalized()
            Ak = arc(Ap @ SC_DIR[k], dvec) @ Ap
            d = Ap.inverted() @ Ak
            Rb = REST_R[f"scarf{k + 1}"]
            row.append((Rb.inverted() @ d @ Rb).to_quaternion())
            Ap = Ak
        res.append(row)
    return res

# ------------------------------------------------------------------ foot contact helpers (sole points) and joint angles
HEEL = Vector((0, 1.05, -1.25)); BALL = Vector((0, -1.55, -1.25))
def sole_points(Pw, A, sd):
    """World heel, ball and toe-tip points of a boot (the sole sits 1.25 below the ankle in rest; the toe bone carries the tip)."""
    f = f"foot_{sd}"; t = f"toe_{sd}"
    heel = Pw[f] + A[f] @ HEEL
    ball = Pw[t] + A[t] @ Vector((0, 0, -0.55))     # bottom of the toe joint (equals the forefoot sole when the foot is flat)
    tip = Pw[t] + A[t] @ Vector((0, -1.12, -0.55))
    return heel, ball, tip

def joint_angle(A, b):
    p = PARENT[b]
    if p is None or p not in A or b not in A: return 0.0
    d = A[p].inverted() @ A[b]
    c = (d[0][0] + d[1][1] + d[2][2] - 1.0) / 2.0
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))

LIMIT_BONES = tuple(f"{b}_{s}" for s in "LR" for b in ("upperarm", "forearm", "hand", "thigh", "shin", "foot", "clavicle", "toe")) + ("neck", "head", "spine", "chest")
JOINT_LIMITS = C.JOINT_LIMITS
KEY_PTS = ("hand_L", "hand_R", "foot_L", "foot_R", "head", "chest", "hips", "neck", "scarf1")

def final_poses(clip):
    poses = lagged_poses(clip)
    poses = head_follow(clip, poses)
    poses = [(fit_hips(p) if (clip.fit and (p.v["fl"] is not None or p.v["fr"] is not None)) else p) for p in poses]
    poses = breathing(clip, poses)
    return poses

def clip_speed(clip):
    if clip.speed is not None: return clip.speed
    r = clip.ref.get("ground_ref_speed") if clip.ref else None
    w = max(0.0, clip.wind) / 60.0
    return max(r * 0.85 if r else 0.0, w)

def bake_clip(clip):
    """Sample every frame; returns list of (frame, {bone: (quat, loc)}) with the derived scarf chain, and the poses.
    clip.metrics holds the world-space data the validators use (sole points, scarf clearance, joint angles, key points)."""
    poses = final_poses(clip)
    worlds, results = [], []
    for p in poses:
        res, Pw, A = eval_pose(p, True)
        results.append(res); worlds.append((Pw, A))
    pts_seq = scarf_sim(clip, worlds, clip_speed(clip))
    sc = scarf_bones(pts_seq, worlds)
    frames = []
    mx = {b: 0.0 for b in LIMIT_BONES}
    pts_out, soles, clear = [], [], 1e9
    for f, res in enumerate(results):
        for k in range(4):
            res[f"scarf{k + 1}"] = (sc[f][k], None)
        frames.append((f, res))
        Pw, A = worlds[f]
        for b in LIMIT_BONES:
            mx[b] = max(mx[b], joint_angle(A, b))
        pts_out.append({k: [round(Pw[k].x, 4), round(Pw[k].y, 4), round(Pw[k].z, 4)] for k in KEY_PTS})
        row = {}
        for sd in "LR":
            h, b_, t = sole_points(Pw, A, sd)
            row[sd] = [[round(q.x, 4), round(q.y, 4), round(q.z, 4)] for q in (h, b_, t)]
        soles.append(row)
        ta, tb = Pw["hips"], Pw["neck"]
        ab = tb - ta
        for k in range(2, 5):
            q = pts_seq[f][k]
            t_ = max(0.0, min(1.0, (q - ta).dot(ab) / ab.length_squared))
            clear = min(clear, (q - (ta + ab * t_)).length)
    clip.metrics = dict(pts=pts_out, soles=soles, scarf_clearance=round(clear, 4), max_angle={k: round(v, 1) for k, v in mx.items()},
                        scarf=[[[round(c, 3) for c in q] for q in pts] for pts in pts_seq])
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
