"""Common-state clips: everything a fighter needs besides its attacks (locomotion, jumps, shield, damage,
down/tech, ledge, grab victim, items, taunts, results). Named after the engine's motion rows
(tools/geno/report.py lists the 351 rows); rows without their own clip are mapped in ALIASES with a status.
"""
import math
from anim_lib import P, Pose, Clip, lerp_pose, EASES
from clips_moves import STAND, GL, GR, spin

CLIPS = []
ALIASES = {}

def add(name, n, keys=None, **kw):
    kw.setdefault("category", "common")
    c = Clip(name, n, keys=[(float(k[0]), k[1], k[2] if len(k) > 2 else "smooth") for k in (keys or [])], **kw)
    CLIPS.append(c)
    return c

def alias(rows, clip, status="alias", note=""):
    for r in rows.split():
        ALIASES[r] = dict(clip=clip, status=status, note=note)

def sm(u): return u * u * (3 - 2 * u)
def S(**kw): return STAND.copy(**kw)

# ------------------------------------------------------------------ air poses (FK legs)
AIR = P(tor=(8, 0, -8), hd=(-2, 0, 4), aL=(30, 40, 0, 40, 0), aR=(30, 40, 0, 40, 0), lL=(30, 6, 60, 15), lR=(8, 6, 40, 15), fl=None, fr=None)
TUCK = AIR.copy(lL=(105, 6, 125, 10), lR=(105, 6, 125, 10), tor=(24, 0, 0), aL=(60, 30, 0, 110, 0), aR=(60, 30, 0, 110, 0), hd=(-6, 0, 0))
LAY = lambda sign, **kw: P(fp=90 * sign, hp=(0, 0, -4.1), tor=(0, 0, 0), aL=(0, 14, 0, 6, 0), aR=(0, 14, 0, 6, 0), lL=(0, 4, 2, 0), lR=(0, 4, 2, 0), fl=None, fr=None, hd=(0, 0, 0), **kw)

# ------------------------------------------------------------------ locomotion generator
def loco(N, E, duty, lift, lean, arm, elbow, bob=0.0, out=0.6, twist=7.0, base=None, blend_in=0):
    base = base or P(hd=(-2, 0, 0), cuL=1, cuR=1)
    def foot(p):
        p %= 1.0
        if p < duty:
            s = p / duty
            fwd = E / 2 - E * s
            up = 0.0
            pitch = 16 * (1 - s / 0.28) if s < 0.28 else (0 if s < 0.62 else -34 * ((s - 0.62) / 0.38) ** 2)
        else:
            s = (p - duty) / (1 - duty)
            es = sm(s)
            fwd = -E / 2 + E * es
            up = lift * math.sin(math.pi * s) ** 0.8
            pitch = -28 * (1 - s) ** 2 + 14 * s ** 3
        # keep the sole off the ground while pitched (heel / toe clearance)
        pr = math.radians(abs(pitch))
        up += (0.95 * math.sin(pr) if pitch > 0 else 1.9 * math.sin(pr))
        return (out, fwd, up, pitch)
    def gen(f):
        ph = (f % N) / N
        c = math.cos(2 * math.pi * ph); sn = math.sin(2 * math.pi * ph)
        fl, fr = foot(ph), foot(ph + 0.5)
        # flight bounce for runs: both feet off the ground
        fb = 0.0
        if bob:
            for q in (ph, ph + 0.5):
                q %= 1.0
                if duty <= q < 0.5 + 1e-6 or (0.5 + duty <= q):
                    pass
            a = (ph % 0.5) / 0.5
            fb = bob * max(0.0, math.sin(math.pi * (a - duty * 2) / (1 - duty * 2))) if a > duty * 2 else 0.0
        p = base.copy(fl=fl, fr=fr, tor=(lean, 2.0 * sn, twist * 0.8 * c), hy=-twist * c,
                      aL=(-arm * c, 14, 0, elbow, 0), aR=(arm * c, 14, 0, elbow, 0), hp=(0, 0, fb), hd=(-lean * 0.5, 0, -twist * 0.5 * c))
        return p
    return gen

def add_loco(name, N, E, duty, lift, lean, arm, elbow, bob=0.0, out=0.6, serves="", wind=14, loop=True, base=None):
    g = loco(N, E, duty, lift, lean, arm, elbow, bob, out, base=base)
    return add(name, N, loop=loop, gen=g, serves=serves, wind=wind,
               ref=dict(stride_per_cycle_units=E, stance_duty=duty, ground_ref_speed=round(E / (duty * N), 4),
                        note="slide-free body speed in units/frame at animation rate 1.0; the engine scales the rate"))

def register():
    CLIPS.clear(); ALIASES.clear()
    # ============================================================ stance and locomotion
    def wait_gen(f):
        s = math.sin(2 * math.pi * f / 80.0)
        return STAND.copy(hp=(0, 0, 0.0), tor=(8 + 1.6 * s, 0.6 * s, -14), aL=(55 + 3 * s, 18 + 1.2 * s, 0, 105 - 3 * s, 0), aR=(35 + 2 * s, 10, 0, 118 + 2 * s, 0), hd=(-3 - s, 0, 6))
    add("Wait", 80, loop=True, gen=wait_gen, serves="Wait (ready stance, breathing)", wind=5)
    add_loco("WalkSlow", 44, 2.8, 0.66, 0.8, 4, 12, 22, serves="WalkSlow", wind=10, base=P(tor=(4, 0, 0), hd=(-2, 0, 0)))
    add_loco("WalkMiddle", 34, 3.5, 0.60, 1.0, 6, 28, 36, serves="WalkMiddle", wind=16)
    add_loco("WalkFast", 26, 4.3, 0.55, 1.3, 11, 38, 55, serves="WalkFast", wind=26)
    add_loco("Run", 16, 5.8, 0.38, 2.3, 28, 72, 100, bob=0.6, serves="Run / RunDirect", wind=58, out=0.55)
    rg = loco(16, 6.2, 0.38, 2.4, 32, 74, 104, 0.6, 0.55)
    def dash_gen(f):
        u = min(1.0, f / 5.0)
        return lerp_pose(S(tor=(14, 0, -10), aL=(-20, 20, 0, 80, 0), aR=(-30, 22, 0, 90, 0), hp=(0, 0, -0.5)), rg(f + 4), sm(u))
    add("Dash", 16, gen=dash_gen, serves="Dash (burst into the run cycle; loops to Run)", wind=64)
    def brake_gen(f):
        u = f / 15.0
        a = P(tor=(-12, 0, 8), hy=4, aL=(30, 50, 0, 40, 0), aR=(20, 55, 0, 40, 0), fl=(0.8, 3.0, 0, 8), fr=(0.8, 0.2, 0, 0), hd=(6, 0, 0), hp=(0, -0.6, -0.5))
        return lerp_pose(a, STAND, EASES["smooth"](max(0, (u - 0.4) / 0.6)))
    add("RunBrake", 16, gen=brake_gen, serves="RunBrake (skid)", wind=36)
    # turn: the engine flips facing between frames 4 and 5 (absolute orientation continuous: +90 before, -90 after)
    t0 = S(); t1 = S(tor=(10, 0, 70), hy=40, hd=(0, 0, 40), aL=(40, 30, 0, 70, 0), aR=(40, 30, 0, 70, 0), fl=(1.0, 0.4, 0, 0), fr=(1.0, -0.4, 0, 0))
    t2 = t1.copy(tor=(10, 0, -70), hy=-40, hd=(0, 0, -40))
    add("Turn", 10, [(0, t0), (4, t1, "fast"), (5, t2, "hold"), (9, S(), "smooth")], serves="Turn (engine flips facing between frames 4 and 5)", wind=10)
    add("TurnRun", 12, [(0, S(tor=(24, 0, 0))), (5, t1.copy(tor=(24, 0, 70), hp=(0, 0, -0.5), fl=(1.4, 1.0, 0, 0)), "fast"), (6, t2.copy(tor=(24, 0, -70), hp=(0, 0, -0.5), fl=(1.4, 1.0, 0, 0)), "hold"), (11, S(tor=(24, 0, -14)), "smooth")],
        serves="TurnRun (engine flips facing between frames 5 and 6)", wind=30)
    # jump squat / jumps
    ksq = S(hp=(0, 0, -1.7), tor=(26, 0, -6), aL=(-35, 25, 0, 40, 0), aR=(-35, 25, 0, 40, 0), fl=(1.0, 0.2, 0, 0), fr=(1.0, -0.2, 0, 0), hd=(-12, 0, 0))
    add("KneeBend", 5, [(0, S()), (4, ksq, "out")], serves="KneeBend (jump squat)", wind=2)
    push = AIR.copy(lL=(-8, 4, 4, -45), lR=(-8, 4, 4, -45), aL=(150, 25, 0, 20, 0), aR=(150, 25, 0, 20, 0), tor=(-4, 0, 0), hd=(4, 0, 0))
    add("JumpF", 40, [(0, push, "out"), (10, AIR.copy(lL=(70, 6, 90, 10), lR=(55, 6, 80, 10), aL=(90, 40, 0, 50, 0), aR=(90, 40, 0, 50, 0), tor=(14, 0, -4)), "smooth"),
                      (24, AIR.copy(lL=(45, 6, 70, 10), lR=(20, 6, 50, 10), tor=(10, 0, -4)), "smooth"), (39, AIR, "smooth")], serves="JumpF (full hop forward)", category="air", fit=False, wind=-18)
    add("JumpB", 40, [(0, push.copy(tor=(-10, 0, 0)), "out"), (10, AIR.copy(lL=(55, 6, 90, 10), lR=(70, 6, 90, 10), aL=(100, 30, 0, 40, 0), aR=(100, 30, 0, 40, 0), tor=(-12, 0, 6)), "smooth"),
                      (24, AIR.copy(lL=(30, 6, 60, 10), lR=(40, 6, 70, 10), tor=(-8, 0, 4)), "smooth"), (39, AIR.copy(tor=(-4, 0, 0)), "smooth")], serves="JumpB (full hop back)", category="air", fit=False, wind=-18)
    def djump(sign):
        def g(f):
            u = min(1.0, max(0.0, (f - 2) / 22.0))
            tuck = math.sin(math.pi * min(1.0, u * 1.0)) ** 0.6
            p = lerp_pose(AIR, TUCK, tuck)
            return p.copy(fp=sign * 360 * sm(u), hp=(0, 0, 0.9 * math.sin(math.pi * u)))
        return g
    add("JumpAerialF", 34, gen=djump(1), serves="JumpAerialF (double jump: forward flip)", category="air", fit=False, wind=0)
    add("JumpAerialB", 34, gen=djump(-1), serves="JumpAerialB (double jump: back flip)", category="air", fit=False, wind=0)
    def fall_gen(f):
        s = math.sin(2 * math.pi * f / 20.0)
        return AIR.copy(lL=(32 + 6 * s, 6, 58 - 8 * s, 15), lR=(10 - 6 * s, 6, 40 + 8 * s, 15), aL=(40 + 8 * s, 42, 0, 40, 0), aR=(40 - 8 * s, 42, 0, 40, 0))
    add("Fall", 20, loop=True, gen=fall_gen, serves="Fall / FallAerial", category="air", fit=False, wind=26)
    add("FallAerial", 20, loop=True, gen=fall_gen, serves="FallAerial", category="air", fit=False, wind=26)
    add("FastFall", 8, [(0, P(lL=(6, 3, 6, -30), lR=(6, 3, 6, -30), aL=(-20, 12, 0, 20, 0), aR=(-20, 12, 0, 20, 0), tor=(12, 0, 0), hd=(-6, 0, 0), fl=None, fr=None, cuL=1, cuR=1)),
                         (4, P(lL=(10, 3, 4, -30), lR=(2, 3, 8, -30), aL=(-26, 14, 0, 16, 0), aR=(-26, 14, 0, 16, 0), tor=(14, 0, 0), hd=(-6, 0, 0), fl=None, fr=None), "smooth")],
        loop=True, serves="FastFall (tight dive; engine may bind to FallAerial rows)", category="air", fit=False, wind=40)
    help_ = P(aL=(60, 78, 0, 20, 0), aR=(60, 78, 0, 20, 0), lL=(20, 14, 40, 20), lR=(16, 12, 36, 20), tor=(6, 0, 0), hd=(8, 0, 0), fl=None, fr=None, cuL=0, cuR=0)
    def help_gen(f):
        s = math.sin(2 * math.pi * f / 24.0)
        return help_.copy(tor=(6 + 3 * s, 4 * s, 0), aL=(60 + 6 * s, 78, 0, 20, 0), aR=(60 - 6 * s, 78, 0, 20, 0), hd=(8 - 3 * s, 0, 6 * s))
    add("FallSpecial", 24, loop=True, gen=help_gen, serves="FallSpecial (helpless fall, arms out)", category="air", fit=False, wind=30)
    add("DamageFall", 18, loop=True, gen=lambda f: P(fp=18 * math.sin(2 * math.pi * f / 18), aL=(90 + 30 * math.sin(2 * math.pi * f / 18), 70, 0, 30, 0), aR=(90 - 30 * math.sin(2 * math.pi * f / 18), 70, 0, 30, 0),
                                                       lL=(40, 12, 60, 10), lR=(30, 12, 70, 10), hd=(-6, 0, 12 * math.sin(2 * math.pi * f / 18)), fl=None, fr=None, cuL=0, cuR=0),
        serves="DamageFall (tumbling fall after hitstun)", category="air", fit=False, wind=40)
    # landings and crouch
    def landing(name, n, depth, lean, serves):
        low = S(hp=(0, 0, -depth), tor=(lean, 0, -8), aL=(20, 28, 0, 70, 0), aR=(20, 28, 0, 70, 0), fl=(1.1, 0.3, 0, 0), fr=(1.1, -0.3, 0, 0), hd=(-8, 0, 0))
        add(name, n, [(0, low.copy(hp=(0, 0, -depth * 0.4)), "out"), (max(1, n // 4), low, "smooth"), (n - 1, S(), "smooth")], serves=serves, wind=-6)
    landing("Landing", 8, 1.0, 14, "Landing")
    landing("LandingAirN", 8, 1.3, 16, "LandingAirN"); landing("LandingAirF", 10, 1.5, 22, "LandingAirF")
    landing("LandingAirB", 9, 1.4, 18, "LandingAirB"); landing("LandingAirHi", 8, 1.3, 10, "LandingAirHi"); landing("LandingAirLw", 14, 2.1, 30, "LandingAirLw")
    landing("LandingFallSpecial", 24, 2.2, 30, "LandingFallSpecial (helpless landing)")
    sq = S(hp=(0, 0, -2.5), tor=(32, 0, -10), hy=-4, aL=(30, 26, 0, 60, 0), aR=(24, 26, 0, 60, 0), fl=(1.4, 0.4, 0, 0), fr=(1.4, -0.5, 0, 0), hd=(-18, 0, 0))
    add("Squat", 8, [(0, S()), (7, sq, "out")], serves="Squat (crouch in)", wind=2)
    add("SquatWait", 40, loop=True, gen=lambda f: sq.copy(hp=(0, 0, -2.5 + 0.08 * math.sin(2 * math.pi * f / 40)), tor=(32 + 1.5 * math.sin(2 * math.pi * f / 40), 0, -10)), serves="SquatWait (crouch hold)", wind=4)
    add("SquatRv", 8, [(0, sq), (7, S(), "out")], serves="SquatRv (crouch out)", wind=2)
    # ============================================================ shield, dodges
    gd = S(hp=(0, 0, -0.9), tor=(20, 0, -6), hy=-4, aL=(86, 24, 0, 132, 0), aR=(80, 18, 0, 138, 0), hd=(-18, 0, 0), fl=(1.0, 0.6, 0, 0), fr=(1.0, -0.6, 0, 0))
    add("GuardOn", 8, [(0, S()), (6, gd, "out")], serves="GuardOn", wind=4)
    add("Guard", 24, loop=True, gen=lambda f: gd.copy(tor=(20 + 1.2 * math.sin(2 * math.pi * f / 24), 0, -6), hp=(0, 0, -0.9 + 0.05 * math.sin(2 * math.pi * f / 24))), serves="Guard (shield hold)", wind=4)
    add("GuardOff", 10, [(0, gd), (9, S(), "smooth")], serves="GuardOff", wind=4)
    add("GuardSetOff", 12, [(0, gd), (2, gd.copy(hp=(0, -0.7, -0.5), tor=(10, 0, -6), hd=(-6, 0, 0)), "out"), (11, gd, "smooth")], serves="GuardSetOff (shield hit flinch)", wind=8)
    def roll_gen(sign, n=30, dist=16.0):
        def g(f):
            u = min(1.0, f / (n - 1.0))
            crouch = math.sin(math.pi * min(1.0, u * 1.0)) ** 0.5
            tuck = lerp_pose(S(), TUCK.copy(hp=(0, 0, -2.0)), 0)
            # a somersault along the ground, low
            base = TUCK.copy(hp=(0, 0, -2.4), lL=(110, 4, 130, 10), lR=(110, 4, 130, 10), tor=(36, 0, 0), aL=(70, 20, 0, 115, 0), aR=(70, 20, 0, 115, 0))
            p = lerp_pose(S(hp=(0, 0, -1.0), tor=(24, 0, 0), fl=None, fr=None, lL=(30, 4, 70, 0), lR=(30, 4, 70, 0)), base, sm(min(1.0, u / 0.25) if u < 0.8 else max(0.0, (1 - u) / 0.2)))
            fp = sign * 360 * sm(min(1.0, max(0.0, (u - 0.15) / 0.7)))
            q = p.copy(fp=fp, tp=(0, sign * dist * sm(min(1.0, max(0.0, (u - 0.1) / 0.8))), 0), fl=None, fr=None)
            if u > 0.88:
                q = lerp_pose(q, S(tp=(0, sign * dist, 0)), (u - 0.88) / 0.12)
                q = q.copy(fl=(0.75, 0.9, 0, 0), fr=(0.75, -0.7, 0, 0), fp=0) if u > 0.97 else q
            return q
        return g
    add("EscapeF", 30, gen=roll_gen(1), serves="EscapeF (forward roll)", root_motion=True, category="roll", fit=False, wind=20, notes="root motion on `trans`: 16 units forward")
    add("EscapeB", 30, gen=roll_gen(-1), serves="EscapeB (back roll)", root_motion=True, category="roll", fit=False, wind=20, notes="root motion on `trans`: 16 units backward")
    sd = S(hp=(0, 0, -1.2), tor=(22, 0, -50), hy=-30, aL=(60, 30, 0, 120, 0), aR=(70, 30, 0, 120, 0), hd=(-10, 0, 30), fl=(1.2, 0.6, 0, 0), fr=(1.2, -0.6, 0, 0))
    add("EscapeN", 24, [(0, S()), (4, sd, "out"), (16, sd, "lin"), (23, S(), "smooth")], serves="EscapeN (spot dodge)", wind=6)
    ad = TUCK.copy(tor=(30, 0, 0))
    add("EscapeAir", 28, gen=lambda f: lerp_pose(AIR, ad, sm(min(1.0, f / 5.0)) * (1 - sm(max(0.0, (f - 20) / 7.0)))).copy(fp=360 * sm(min(1.0, max(0.0, (f - 3) / 14.0))), hp=(0, 0, 0)),
        serves="EscapeAir (air dodge)", category="air", fit=False, wind=8)
    # ============================================================ damage (ground, light -> heavy), air, fly
    def hit(name, n, kind, s, air=False):
        base = P(fl=None, fr=None, lL=(30, 6, 60, 15), lR=(10, 6, 40, 15), cuL=0, cuR=0) if air else STAND
        if kind == "Hi":
            pk = base.copy(tor=(-22 * s, 0, 10 * s), hd=(-26 * s, 0, -12 * s), hp=(0, -0.5 * s, 0.2), aL=(60, 60, 0, 40, 0), aR=(50, 60, 0, 50, 0))
        elif kind == "N":
            pk = base.copy(tor=(-26 * s, 0, 12 * s), hd=(-8 * s, 0, 4 * s), hp=(0, -0.8 * s, -0.2 * s), aL=(40, 55, 0, 60, 0), aR=(40, 55, 0, 60, 0))
        else:
            pk = base.copy(tor=(34 * s, 0, 8 * s), hd=(10 * s, 0, 0), hp=(0, 0.4 * s, -0.5 * s), aL=(20, 50, 0, 40, 0), aR=(20, 50, 0, 40, 0))
        if air: pk = pk.copy(lL=(30 + 20 * s, 8, 50, 10), lR=(10 + 25 * s, 8, 30, 10))
        add(name, n, [(0, base), (2, pk, "fast"), (max(4, n // 2), pk.add(tor=(-2, 0, 0)), "lin"), (n - 1, base if not air else AIR, "smooth")],
            serves=name, category="air" if air else "common", fit=not air, wind=12)
    for kind in ("Hi", "N", "Lw"):
        for i, (n, s) in enumerate(((14, 0.9), (20, 1.4), (28, 2.0)), 1):
            hit(f"Damage{kind}{i}", n, kind, s)
    for i, (n, s) in enumerate(((14, 0.9), (20, 1.4), (28, 2.0)), 1):
        hit(f"DamageAir{i}", n, "N", s, air=True)
    def fly(name, fp, spinning=False, serves=""):
        def g(f):
            a = 2 * math.pi * f / 16.0
            ang = (360.0 * f / 20.0) if spinning else fp + 6 * math.sin(a)
            return P(fp=ang, aL=(80 + 15 * math.sin(a), 75, 0, 20, 0), aR=(80 - 15 * math.sin(a), 75, 0, 20, 0), lL=(40, 12, 60, 10), lR=(28, 12, 70, 10),
                     hd=(-10, 0, 0), fl=None, fr=None, cuL=0, cuR=0, hp=(0, 0, 0))
        add(name, 20 if spinning else 16, loop=True, gen=g, serves=serves or name, category="air", fit=False, wind=44)
    fly("DamageFlyHi", -55, serves="DamageFlyHi (launched, head high)"); fly("DamageFlyN", -25, serves="DamageFlyN")
    fly("DamageFlyLw", 35, serves="DamageFlyLw"); fly("DamageFlyTop", -140, serves="DamageFlyTop (launched upward)")
    fly("DamageFlyRoll", 0, spinning=True, serves="DamageFlyRoll (tumble spin)")
    # ============================================================ lying, down, tech
    def lying(sign, name, n=30):
        base = LAY(sign)
        add(name, n, loop=True, gen=lambda f: base.copy(hp=(0, 0, -4.1 + 0.05 * math.sin(2 * math.pi * f / n)), tor=(0, 0, 0)), serves=name, category="down", fit=False, wind=2)
    lying(-1, "DownWaitU"); lying(1, "DownWaitD")
    for sign, sfx in ((-1, "U"), (1, "D")):
        lay = LAY(sign)
        air = lay.copy(fp=sign * 40, hp=(0, 0, -2.0), lL=(40, 6, 60, 0), lR=(40, 6, 60, 0))
        add(f"DownBound{sfx}", 22, [(0, air, "in"), (5, lay, "out"), (9, lay.copy(fp=sign * 70, hp=(0, 0, -3.3)), "smooth"), (14, lay, "in"), (21, lay, "smooth")], serves=f"DownBound{sfx}", category="down", fit=False, wind=18)
        add(f"DownDamage{sfx}", 16, [(0, lay), (2, lay.copy(tor=(0, 0, 0), fp=sign * 78, hp=(0, 0, -3.8), hd=(sign * -10, 0, 0)), "out"), (15, lay, "smooth")], serves=f"DownDamage{sfx}", category="down", fit=False, wind=6)
        sit = lay.copy(fp=sign * 35, hp=(0, 0, -2.6), lL=(sign * 40, 6, 60, 0), lR=(sign * 40, 6, 60, 0), aL=(40, 30, 0, 50, 0), aR=(40, 30, 0, 50, 0))
        crouch = S(hp=(0, 0, -2.0), tor=(26, 0, 0), fl=(1.3, 0.2, 0, 0), fr=(1.3, -0.2, 0, 0))
        add(f"DownStand{sfx}", 30, [(0, lay), (8, sit, "smooth"), (16, crouch, "smooth"), (29, S(), "smooth")], serves=f"DownStand{sfx} (getup in place)", category="down", fit=False, wind=10)
        add(f"DownSpot{sfx}", 28, [(0, lay), (6, sit.copy(fp=sign * 55), "smooth"), (14, crouch.copy(hp=(0, 0, -1.4)), "smooth"), (27, S(), "smooth")], serves=f"DownSpot{sfx}", category="down", fit=False, wind=10)
        # getup attack: sit up, sweep kick forward then back, stand
        k1 = crouch.copy(hp=(0, 0, -2.6), fl=(1.3, 0.4, 0, 0), fr=None, lR=(62, 0, 6, -30), tor=(30, 0, 14))
        k2 = crouch.copy(hp=(0, 0, -2.6), fr=(1.3, 0.2, 0, 0), fl=None, lL=(-60, 0, 6, 30), tor=(36, 0, -120))
        add(f"DownAttack{sfx}", 45, [(0, lay), (8, sit, "smooth"), (14, crouch, "smooth"), (18, k1, "fast"), (24, k1, "lin"), (30, k2, "fast"), (36, k2, "lin"), (44, S(), "smooth")], serves=f"DownAttack{sfx} (getup attack)", category="down", fit=False, wind=14)
        for dirn, dn in ((1, "Forward"), (-1, "Back")):
            def g(f, sign=sign, dirn=dirn, n=35):
                u = f / (n - 1.0)
                if u < 0.3:
                    return lerp_pose(LAY(sign), LAY(sign).copy(fp=sign * 35, hp=(0, 0, -2.6), lL=(sign * 40, 6, 60, 0), lR=(sign * 40, 6, 60, 0)), sm(u / 0.3))
                if u < 0.85:
                    v = (u - 0.3) / 0.55
                    r = roll_gen(dirn, 100, 14.0)(0.25 * 99 + v * 0.6 * 99)
                    return r.copy(tp=(0, dirn * 14.0 * sm(v), 0))
                return lerp_pose(S(tp=(0, dirn * 14.0, 0), hp=(0, 0, -1.0), fl=None, fr=None, lL=(30, 4, 70, 0), lR=(30, 4, 70, 0)), S(tp=(0, dirn * 14.0, 0)), sm((u - 0.85) / 0.15))
            add(f"Down{dn}{sfx}", 35, gen=g, serves=f"Down{dn}{sfx} (getup roll)", category="down", fit=False, root_motion=True, wind=16, notes="root motion on `trans`: 14 units")
    add("Passive", 24, [(0, LAY(-1).copy(fp=-35, hp=(0, 0, -2.6))), (4, S(hp=(0, 0, -1.8), tor=(24, 0, 0), aL=(30, 70, 0, 30, 0), aR=(30, 70, 0, 30, 0)), "out"), (23, S(), "smooth")], serves="Passive (tech in place)", category="down", fit=False, wind=10)
    for sign, nm in ((1, "PassiveStandF"), (-1, "PassiveStandB")):
        add(nm, 30, gen=roll_gen(sign, 30, 14.0), serves=f"{nm} (tech roll)", root_motion=True, category="roll", fit=False, wind=20, notes="root motion on `trans`: 14 units")
    wallp = P(fp=-20, hp=(0, 0, -0.5), aL=(130, 60, 0, 30, 0), aR=(130, 60, 0, 30, 0), lL=(-30, 6, 80, 30), lR=(60, 6, 40, 30), tor=(-8, 0, 0), fl=None, fr=None, cuL=0, cuR=0)
    add("PassiveWall", 24, [(0, AIR), (4, wallp, "out"), (23, wallp.copy(aL=(80, 40, 0, 40, 0)), "smooth")], serves="PassiveWall (wall tech)", category="air", fit=False, wind=10)
    add("PassiveWallJump", 30, [(0, wallp), (6, AIR.copy(lL=(-8, 4, 4, -45), lR=(-8, 4, 4, -45), aL=(150, 25, 0, 20, 0), aR=(150, 25, 0, 20, 0)), "out"), (29, AIR, "smooth")], serves="PassiveWallJump", category="air", fit=False, wind=12)
    add("PassiveCeil", 22, [(0, AIR), (4, P(fp=180, aL=(70, 50, 0, 40, 0), aR=(70, 50, 0, 40, 0), lL=(30, 6, 70, 10), lR=(30, 6, 70, 10), fl=None, fr=None, cuL=0, cuR=0), "out"), (21, AIR, "smooth")], serves="PassiveCeil", category="air", fit=False, wind=10)
    # ============================================================ shield break, dizzy
    add("ShieldBreakFly", 16, loop=True, gen=lambda f: P(fp=-30 + 10 * math.sin(2 * math.pi * f / 16), aL=(100, 80, 0, 20, 0), aR=(100, 80, 0, 20, 0), lL=(30, 12, 50, 10), lR=(20, 12, 60, 10), fl=None, fr=None, cuL=0, cuR=0, hd=(-14, 0, 0)), serves="ShieldBreakFly", category="air", fit=False, wind=50)
    add("ShieldBreakFall", 20, loop=True, gen=lambda f: P(fp=-10, tor=(10, 0, 0), aL=(40 + 10 * math.sin(2 * math.pi * f / 20), 70, 0, 20, 0), aR=(40 - 10 * math.sin(2 * math.pi * f / 20), 70, 0, 20, 0), lL=(30, 10, 50, 10), lR=(20, 10, 60, 10), fl=None, fr=None, cuL=0, cuR=0, hd=(-20, 0, 10 * math.sin(2 * math.pi * f / 20))), serves="ShieldBreakFall", category="air", fit=False, wind=24)
    for sign, sfx in ((-1, "U"), (1, "D")):
        lay = LAY(sign)
        add(f"ShieldBreakDown{sfx}", 22, [(0, lay.copy(fp=sign * 35, hp=(0, 0, -2.2)), "in"), (6, lay, "out"), (21, lay.copy(hd=(0, 0, 14)), "smooth")], serves=f"ShieldBreakDown{sfx}", category="down", fit=False, wind=10)
        add(f"ShieldBreakStand{sfx}", 40, [(0, lay), (14, lay.copy(fp=sign * 50, hp=(0, 0, -2.8)), "smooth"), (28, S(hp=(0, 0, -1.6), tor=(26, 0, 0), hd=(-14, 0, 10)), "smooth"), (39, S(), "smooth")], serves=f"ShieldBreakStand{sfx}", category="down", fit=False, wind=10)
    add("Furafura", 40, loop=True, gen=lambda f: S(tor=(10, 10 * math.sin(2 * math.pi * f / 40), 8 * math.sin(2 * math.pi * f / 40 + 1)), aL=(5, 25, 0, 20, 0), aR=(5, 25, 0, 20, 0), hd=(-12, 14 * math.sin(2 * math.pi * f / 40 + 2), 20 * math.sin(2 * math.pi * f / 40)), hp=(0.4 * math.sin(2 * math.pi * f / 40), 0, -0.4)), serves="Furafura (dizzy sway)", wind=8)
    # ============================================================ grabs: hold and throw handled in clips_moves; victim clips here
    def captured(name, n, hold_low, loop=True, wob=1.0, serves=""):
        base = P(fl=None, fr=None, lL=(20, 6, 20, 0), lR=(20, 6, 20, 0), hp=(0, 0, -0.6 if hold_low else 0), tor=(20 if hold_low else 4, 0, 0), aL=(40, 40, 0, 50, 0), aR=(40, 40, 0, 50, 0), hd=(-8, 0, 0), cuL=0, cuR=0)
        def g(f):
            s = math.sin(2 * math.pi * f / n * (2 if loop else 1))
            return base.copy(tor=(base.v["tor"][0] + 5 * s * wob, 3 * s * wob, 4 * s * wob), aL=(40 + 25 * s * wob, 40, 0, 50, 0), aR=(40 - 25 * s * wob, 40, 0, 50, 0), hd=(-8, 4 * s * wob, 0))
        add(name, n, loop=loop, gen=g, serves=serves or name, category="victim", fit=False, wind=10)
    captured("CapturePulledHi", 16, False, loop=False, serves="CapturePulledHi (victim yanked into the hold)")
    captured("CapturePulledLw", 16, True, loop=False, serves="CapturePulledLw")
    captured("CaptureWaitHi", 30, False, serves="CaptureWaitHi (victim struggle)"); captured("CaptureWaitLw", 30, True, serves="CaptureWaitLw")
    captured("CaptureDamageHi", 10, False, loop=False, wob=2.5, serves="CaptureDamageHi (pummeled)"); captured("CaptureDamageLw", 10, True, loop=False, wob=2.5, serves="CaptureDamageLw")
    add("CaptureCut", 18, [(0, AIR.copy(tor=(-16, 0, 0))), (8, AIR.copy(tor=(-10, 0, 0), lL=(60, 6, 40, 10), lR=(50, 6, 40, 10), hp=(0, -1.0, 0.5)), "out"), (17, S(), "smooth")], serves="CaptureCut (breaks out of the hold)", category="victim", fit=False, wind=10)
    add("CaptureJump", 20, [(0, AIR), (6, AIR.copy(lL=(70, 4, 90, 0), lR=(70, 4, 90, 0), hp=(0, 0, 1.2)), "out"), (19, AIR, "smooth")], serves="CaptureJump (hops out)", category="victim", fit=False, wind=10)
    add("CaptureNeck", 24, loop=True, gen=lambda f: P(fp=-10, aL=(70, 60, 0, 40, 0), aR=(70, 60, 0, 40, 0), lL=(10, 4, 10, 0), lR=(10, 4, 10, 0), fl=None, fr=None, hd=(-18, 8 * math.sin(2 * math.pi * f / 24), 0), hp=(0, 0, 0.6 * math.sin(2 * math.pi * f / 24))), serves="CaptureNeck (dangling hold)", category="victim", fit=False)
    add("CaptureFoot", 24, loop=True, gen=lambda f: P(fp=180, aL=(60, 50, 0, 30, 0), aR=(60, 50, 0, 30, 0), lL=(10, 4, 10, 0), lR=(10, 4, 10, 0), fl=None, fr=None, hd=(0, 0, 8 * math.sin(2 * math.pi * f / 24))), serves="CaptureFoot (hung by the feet)", category="victim", fit=False)
    for nm, fp in (("ThrownF", -40), ("ThrownB", 40), ("ThrownHi", -150), ("ThrownLw", 60)):
        add(nm, 24, [(0, P(fp=fp * 0.2, aL=(70, 60, 0, 30, 0), aR=(70, 60, 0, 30, 0), lL=(30, 8, 40, 10), lR=(20, 8, 50, 10), fl=None, fr=None, cuL=0, cuR=0)),
                     (6, P(fp=fp, aL=(100, 80, 0, 20, 0), aR=(100, 80, 0, 20, 0), lL=(40, 12, 60, 10), lR=(28, 12, 70, 10), fl=None, fr=None, cuL=0, cuR=0, hd=(-12, 0, 0)), "out"),
                     (23, P(fp=fp * 1.1, aL=(90, 75, 0, 20, 0), aR=(90, 75, 0, 20, 0), lL=(40, 12, 60, 10), lR=(28, 12, 70, 10), fl=None, fr=None, cuL=0, cuR=0, hd=(-12, 0, 0)), "smooth")],
            serves=f"{nm} (flung by a throw)", category="victim", fit=False, wind=44)
    # ============================================================ misc reactions
    add("Rebound", 24, [(0, S()), (3, S(tor=(-16, 0, 8), hp=(0, -1.0, -0.2), hd=(-14, 0, 0), aL=(70, 70, 0, 30, 0), aR=(70, 70, 0, 30, 0)), "out"), (23, S(), "smooth")], serves="Rebound (staggered by a clank)", wind=14)
    add("Pass", 18, [(0, S()), (5, S(hp=(0, 0, -1.4), tor=(18, 0, 0)), "smooth"), (17, S(hp=(0, 0, -0.4)), "smooth")], serves="Pass (drop through platform)", wind=8)
    add("Ottotto", 30, loop=True, gen=lambda f: S(tor=(-14, 0, 0), hp=(0, -0.3, 0), aL=(100 + 40 * math.sin(2 * math.pi * f / 15), 60, 0, 20, 0), aR=(100 - 40 * math.sin(2 * math.pi * f / 15), 60, 0, 20, 0), hd=(-6, 0, 0), fl=(0.9, 1.6, 0, 20), fr=(0.9, -0.2, 0, 0)), serves="Ottotto (teetering at an edge)", wind=18)
    wl = P(fp=-85, hp=(0, 0, -0.8), aL=(120, 80, 0, 10, 0), aR=(120, 80, 0, 10, 0), lL=(50, 20, 20, 0), lR=(50, 20, 20, 0), fl=None, fr=None, cuL=0, cuR=0)
    for nm in ("FlyReflectWall", "FlyReflectCeil", "StopWall", "StopCeil"):
        add(nm, 20, [(0, AIR), (3, wl.copy(fp=-85 if "Wall" in nm else 175), "out"), (19, wl.copy(fp=-60 if "Wall" in nm else 150, hp=(0, 0, -1.4)), "smooth")], serves=f"{nm} (bounce / stick on a surface)", category="air", fit=False, wind=20)
    add("MissFoot", 20, [(0, AIR.copy(lL=(60, 6, 40, 10), lR=(60, 6, 40, 10))), (4, S(hp=(0, 0, -2.2), tor=(34, 0, 0), aL=(60, 60, 0, 30, 0), aR=(60, 60, 0, 30, 0)), "out"), (19, S(), "smooth")], serves="MissFoot (stumbling landing)", wind=10)
    # ============================================================ ledge (hands above the head; body hangs; root motion on climbs)
    hang = P(hp=(0, 0, 0.0), aL=(176, 14, 0, 8, 0), aR=(176, 14, 0, 8, 0), lL=(6, 6, 22, 0), lR=(-4, 6, 30, 0), tor=(-6, 0, 0), hd=(8, 0, 0), fl=None, fr=None, cuL=1, cuR=1)
    add("CliffCatch", 14, [(0, AIR.copy(aL=(120, 30, 0, 40, 0), aR=(120, 30, 0, 40, 0))), (3, hang.copy(hp=(0, 0, -0.6)), "out"), (13, hang, "smooth")], serves="CliffCatch", category="ledge", fit=False, wind=6)
    add("CliffWait", 60, loop=True, gen=lambda f: hang.copy(tor=(-6 + 1.2 * math.sin(2 * math.pi * f / 60), 1.2 * math.sin(2 * math.pi * f / 60), 0), lL=(6 + 3 * math.sin(2 * math.pi * f / 60), 6, 22, 0), lR=(-4 - 3 * math.sin(2 * math.pi * f / 60), 6, 30, 0)), serves="CliffWait (hang)", category="ledge", fit=False, wind=6)
    def climb(name, n, up, fwd, pace):
        pull = hang.copy(aL=(150, 30, 0, 100, 0), aR=(150, 30, 0, 100, 0), tor=(10, 0, 0), hp=(0, 0, 0.5), lL=(30, 6, 60, 0), lR=(20, 6, 60, 0))
        over = P(hp=(0, 0, -1.2), aL=(40, 40, 0, 70, 0), aR=(40, 40, 0, 70, 0), tor=(34, 0, 0), lL=(95, 6, 120, 0), lR=(40, 6, 90, 0), fl=None, fr=None, hd=(-14, 0, 0))
        add(name, n, [(0, hang), (int(n * 0.3 * pace), pull, "smooth"), (int(n * 0.6), over, "smooth"), (int(n * 0.8), S(hp=(0, 0, -1.6), tor=(26, 0, 0), fl=(1.2, 0.2, 0, 0), fr=(1.2, -0.2, 0, 0)), "smooth"), (n - 1, S(), "smooth")], serves=f"{name} (root motion: +{up} up, +{fwd} forward over the clip)", category="ledge", fit=False, root_motion=True, wind=14)
        c = CLIPS[-1]
        orig = c.keys
        def g(f, c=c, n=n):
            q = Clip.sample(Clip(c.name, c.n, keys=orig), f)
            u = sm(min(1.0, f / (n * 0.85)))
            return q.copy(tp=(0, fwd * u, up * u), fl=q.v["fl"], fr=q.v["fr"])
        c.keys = []; c.gen = g
    climb("CliffClimbSlow", 60, 9.0, 4.5, 1.0); climb("CliffClimbQuick", 40, 9.0, 4.5, 1.0)
    def cliff_attack(name, n):
        add(name, n, [(0, hang), (int(n * 0.3), hang.copy(aL=(150, 30, 0, 100, 0), aR=(150, 30, 0, 100, 0), tor=(10, 0, 0), hp=(0, 0, 0.5)), "smooth"), (int(n * 0.5), S(hp=(0, 0, -1.6), tor=(26, 0, 0), fl=(1.3, 0.4, 0, 0), fr=(1.3, -0.4, 0, 0)), "smooth"), (int(n * 0.62), S(tor=(30, 0, 44), hy=26, aR=(96, 4, 0, 4, 0), aL=(-30, 30, 0, 60, 0), hp=(0, 1.2, -1.2), fl=(1.0, 2.6, 0, 0), fr=(1.0, -1.4, 0.3, 15)), "fast"), (int(n * 0.78), S(tor=(30, 0, 44), hy=26, aR=(96, 4, 0, 4, 0), aL=(-30, 30, 0, 60, 0), hp=(0, 1.2, -1.2), fl=(1.0, 2.6, 0, 0), fr=(1.0, -1.4, 0.3, 15)), "lin"), (n - 1, S(), "smooth")],
            serves=f"{name} (ledge attack; root motion +9 up, +6 forward)", category="ledge", fit=False, root_motion=True, wind=14)
        c = CLIPS[-1]; orig = c.keys
        def g(f, c=c, n=n, orig=orig):
            q = Clip.sample(Clip(c.name, c.n, keys=orig), f)
            u = sm(min(1.0, f / (n * 0.5)))
            return q.copy(tp=(0, 6.0 * u, 9.0 * u))
        c.keys = []; c.gen = g
    cliff_attack("CliffAttackSlow", 70); cliff_attack("CliffAttackQuick", 50)
    def cliff_roll(name, n):
        add(name, n, gen=None, serves=f"{name} (ledge roll onto the stage; root motion +9 up, +14 forward)", category="ledge", fit=False, root_motion=True, wind=20)
        c = CLIPS[-1]
        rg_ = roll_gen(1, n, 14.0)
        def g(f, n=n):
            u = f / (n - 1.0)
            if u < 0.25:
                return lerp_pose(hang, hang.copy(aL=(150, 30, 0, 100, 0), aR=(150, 30, 0, 100, 0), tor=(10, 0, 0), hp=(0, 0, 0.5)), sm(u / 0.25))
            q = rg_((u - 0.25) / 0.75 * (n - 1))
            return q.copy(tp=(0, 14.0 * sm(min(1.0, (u - 0.25) / 0.7)), 9.0 * sm(min(1.0, (u - 0.25) / 0.2))))
        c.gen = g
    cliff_roll("CliffEscapeSlow", 70); cliff_roll("CliffEscapeQuick", 50)
    for nm, n, extra in (("CliffJumpSlow1", 30, 0), ("CliffJumpQuick1", 22, 0)):
        add(nm, n, [(0, hang), (int(n * 0.4), hang.copy(hp=(0, 0, -1.8), aL=(60, 30, 0, 100, 0), aR=(60, 30, 0, 100, 0), tor=(26, 0, 0), lL=(60, 6, 100, 0), lR=(60, 6, 100, 0)), "smooth"), (n - 1, AIR.copy(lL=(-8, 4, 4, -45), lR=(-8, 4, 4, -45), aL=(150, 25, 0, 20, 0), aR=(150, 25, 0, 20, 0)), "out")], serves=nm, category="ledge", fit=False, wind=14)
    for nm, n in (("CliffJumpSlow2", 36), ("CliffJumpQuick2", 30)):
        add(nm, n, [(0, AIR.copy(lL=(-8, 4, 4, -45), lR=(-8, 4, 4, -45), aL=(150, 25, 0, 20, 0), aR=(150, 25, 0, 20, 0))), (12, AIR.copy(lL=(70, 6, 90, 10), lR=(55, 6, 80, 10)), "smooth"), (n - 1, AIR, "smooth")], serves=nm + " (air part of the ledge jump)", category="air", fit=False, wind=-10)
    # ============================================================ items (right hand socket)
    hold_i = S(aR=(70, 14, 0, 90, 0), cuR=0.9)
    add("LightGet", 14, [(0, S()), (4, S(hp=(0, 0, -2.0), tor=(40, 0, 0), aR=(40, 20, 0, 20, 0), cuR=0.0, fl=(1.2, 0.6, 0, 0), fr=(1.2, -0.6, 0, 0)), "out"), (9, S(hp=(0, 0, -1.5), tor=(30, 0, 0), aR=(40, 20, 0, 20, 0), cuR=1.0, fl=(1.2, 0.6, 0, 0), fr=(1.2, -0.6, 0, 0)), "smooth"), (13, hold_i, "smooth")], serves="LightGet (pick up a light item)", wind=4)
    add("HeavyGet", 24, [(0, S()), (6, S(hp=(0, 0, -2.4), tor=(44, 0, 0), aL=(50, 20, 0, 20, 0), aR=(50, 20, 0, 20, 0), cuL=0, cuR=0), "out"), (14, S(hp=(0, 0, -2.2), tor=(34, 0, 0), aL=(50, 20, 0, 40, 0), aR=(50, 20, 0, 40, 0), cuL=1, cuR=1), "smooth"), (23, S(aL=(100, 24, 0, 80, 0), aR=(100, 24, 0, 80, 0)), "smooth")], serves="HeavyGet (lift a heavy item)", wind=4)
    def throw(name, n, wind_pose, rel_pose, rel, serves):
        add(name, n, [(0, hold_i), (rel - 4, wind_pose, "smooth"), (rel, rel_pose, "fast"), (n - 1, S(), "smooth")], serves=serves, hit=[rel], wind=14)
    throw("LightThrowF", 24, S(aR=(-40, 24, 0, 120, 0), tor=(10, 0, -46), hy=-24), S(aR=(120, 6, 0, 6, 0), tor=(20, 0, 40), hy=24, cuR=0, hp=(0, 1.0, -0.4), fl=(0.9, 2.2, 0, 0)), 9, "LightThrowF")
    throw("LightThrowB", 26, S(aR=(60, 20, 0, 60, 0), tor=(8, 0, 20)), S(aR=(100, 0, 0, 6, 0), tor=(10, 0, -170), cuR=0), 12, "LightThrowB")
    throw("LightThrowHi", 24, S(aR=(20, 24, 0, 110, 0), hp=(0, 0, -1.0), tor=(18, 0, 0)), S(aR=(172, 14, 0, 6, 0), tor=(-14, 0, 0), cuR=0, hp=(0, 0, 0.2)), 9, "LightThrowHi")
    throw("LightThrowLw", 24, S(aR=(100, 24, 0, 60, 0), tor=(-10, 0, 0)), S(aR=(40, 10, 0, 6, 0), tor=(40, 0, 0), hp=(0, 0.4, -1.6), cuR=0), 9, "LightThrowLw")
    throw("LightThrowDash", 24, S(aR=(-40, 24, 0, 120, 0), tor=(30, 0, -30), hy=-16), S(aR=(120, 6, 0, 6, 0), tor=(36, 0, 30), hy=18, cuR=0, hp=(0, 1.6, -0.8), fl=(0.9, 2.8, 0, 0)), 9, "LightThrowDash")
    throw("LightThrowDrop", 14, S(aR=(60, 20, 0, 40, 0), cuR=0.6), S(aR=(30, 24, 0, 40, 0), cuR=0), 5, "LightThrowDrop")
    # item swings (family: Sword, Bat, Parasol, Harisen, StarRod, Lipstick all alias these)
    sw1 = S(aR=(100, 30, 0, 10, 0), tor=(10, 0, 50), hy=24, hp=(0, 0.8, -0.2), fl=(0.9, 1.8, 0, 0))
    add("ItemSwing1", 24, [(0, hold_i), (3, S(aR=(60, 100, 0, 70, 0), tor=(10, 0, -40), hy=-20), "in"), (6, sw1, "fast"), (10, sw1, "lin"), (23, S(), "smooth")], serves="ItemSwing1 (item swing; family clip for the 24 Sword/Bat/Parasol/Harisen/StarRod/Lipstick rows)", hit=[6], wind=14)
    sw3 = S(aR=(110, 8, 0, 8, 0), tor=(34, 0, 14), hp=(0, 0.8, -1.0), fl=(1.0, 1.6, 0, 0))
    add("ItemSwing3", 28, [(0, hold_i), (5, S(aR=(176, 22, 0, 60, 0), tor=(-18, 0, 0)), "smooth"), (8, S(aR=(176, 22, 0, 60, 0), tor=(-18, 0, 0)), "in"), (10, sw3, "fast"), (16, sw3, "lin"), (27, S(), "smooth")], serves="ItemSwing3 (overhead swing)", hit=[10], wind=14)
    add("ItemSwing4", 40, [(0, hold_i), (8, S(aR=(-70, 40, 0, 100, 0), tor=(14, 0, -48), hy=-30, hp=(0, -0.3, -0.8)), "smooth"), (12, S(aR=(-70, 40, 0, 100, 0), tor=(14, 0, -48), hy=-30, hp=(0, -0.3, -0.8)), "in"), (14, sw1.copy(aR=(95, 4, 0, 4, 0), tor=(26, 0, 44), hp=(0, 1.6, -1.0), fl=(1.0, 2.8, 0, 0)), "fast"), (22, sw1.copy(aR=(95, 4, 0, 4, 0), tor=(26, 0, 44), hp=(0, 1.6, -1.0), fl=(1.0, 2.8, 0, 0)), "lin"), (39, S(), "smooth")], serves="ItemSwing4 (smash swing)", hit=[14], wind=14)
    add("ItemSwingDash", 30, [(0, S(tor=(26, 0, 0), aR=(-30, 20, 0, 80, 0))), (7, S(aR=(110, 8, 0, 8, 0), tor=(36, 0, 30), hp=(0, 1.6, -1.0), fl=(1.0, 2.6, 0, 0), fr=(1.0, -2.4, 0.3, 20)), "fast"), (13, S(aR=(110, 8, 0, 8, 0), tor=(36, 0, 30), hp=(0, 1.6, -1.0), fl=(1.0, 2.6, 0, 0), fr=(1.0, -2.4, 0.3, 20)), "lin"), (29, S(), "smooth")], serves="ItemSwingDash", hit=[7], wind=40)
    shoot = S(aR=(95, 6, 0, 6, 0), tor=(8, 0, 20), hy=10, cuR=0.8)
    add("ItemShoot", 22, [(0, hold_i), (3, shoot, "fast"), (5, shoot.copy(hp=(0, -0.5, 0), aR=(105, 6, 0, 10, 0)), "out"), (21, hold_i, "smooth")], serves="ItemShoot (ray gun / flower style shot; also the scope rows)", hit=[3], wind=8)
    add("LiftWait", 40, loop=True, gen=lambda f: S(aL=(176, 24, 0, 6, 0), aR=(176, 24, 0, 6, 0), tor=(-4 + math.sin(2 * math.pi * f / 40), 0, 0), cuL=0.1, cuR=0.1), serves="LiftWait (carrying a heavy item overhead)", wind=5)
    gl = loco(28, 2.8, 0.62, 0.8, 0, 0, 0, base=S(aL=(176, 24, 0, 6, 0), aR=(176, 24, 0, 6, 0), cuL=0.1, cuR=0.1))
    add("LiftWalk", 28, loop=True, gen=lambda f: gl(f).copy(aL=(176, 24, 0, 6, 0), aR=(176, 24, 0, 6, 0), tor=(-4, 0, 0)), serves="LiftWalk", wind=8,
        ref=dict(stride_per_cycle_units=2.8, stance_duty=0.62, ground_ref_speed=round(2.8 / (0.62 * 28), 4)))
    # ============================================================ presentation: entry, taunts, wins
    add("EntryStart", 60, [(0, S(hp=(0, 0, -2.4), tor=(40, 0, 0), aL=(-40, 30, 0, 40, 0), aR=(-40, 30, 0, 40, 0), hd=(-20, 0, 0), fl=(1.2, 0.4, 0, 0), fr=(1.2, -0.4, 0, 0))),
                           (20, S(hp=(0, 0, -2.4), tor=(40, 0, 0), aL=(-40, 30, 0, 40, 0), aR=(-40, 30, 0, 40, 0), hd=(-20, 0, 0), fl=(1.2, 0.4, 0, 0), fr=(1.2, -0.4, 0, 0)), "lin"),
                           (30, S(hp=(0, 0, 0.1), aL=(170, 40, 0, 10, 0), aR=(170, 40, 0, 10, 0), tor=(-12, 0, 0), hd=(8, 0, 0), fl=(0.8, 0.1, 0.0, 0), fr=(0.8, -0.1, 0.0, 0)), "fast"),
                           (45, S(tor=(4, 0, -30), hy=-18, aR=(90, 8, 0, 8, 0), aL=(35, 20, 0, 100, 0)), "smooth"), (59, S(), "smooth")], serves="EntryStart / Entry (spawn pose: crouch, spring, point)", wind=12)
    add("Rebirth", 40, loop=True, gen=lambda f: S(aL=(10, 70, 0, 10, 0), aR=(10, 70, 0, 10, 0), tor=(0, 0, 0), hy=0, hd=(0, 0, 0), hp=(0, 0, 0.3 * math.sin(2 * math.pi * f / 40))), serves="Rebirth / RebirthWait (standing on the revival platform)", wind=6)
    add("AppealSR", 70, [(0, S()), (8, S(hp=(0, 0, -1.2), tor=(24, 0, 0), aR=(-40, 30, 0, 90, 0), aL=(-30, 30, 0, 80, 0)), "smooth"), (18, S(aR=(176, 24, 0, 8, 0), tor=(-14, 0, 0), hp=(0, 0, 0.2), hd=(8, 0, 12)), "fast"), (30, S(aR=(176, 24, 0, 8, 0), tor=(-14, 0, 0), hd=(8, 0, -12)), "smooth"), (44, S(aR=(176, 24, 0, 8, 0), tor=(-14, 0, 0), hd=(8, 0, 12)), "smooth"), (69, S(), "smooth")], serves="AppealSR (taunt: fist raised)", wind=10)
    add("AppealSL", 70, [(0, S()), (10, S(tor=(-6, 0, -50), hy=-30, aL=(100, 40, 0, 50, 0), aR=(100, 40, 0, 50, 0)), "smooth"), (30, S(tor=(-6, 0, 120), hy=60, aL=(100, 40, 0, 50, 0), aR=(100, 40, 0, 50, 0), hd=(0, 0, 20)), "smooth"), (48, S(tor=(10, 0, 0), hy=0, aL=(20, 40, 0, 60, 0), aR=(20, 40, 0, 60, 0)), "smooth"), (69, S(), "smooth")], serves="AppealSL (taunt: spin and settle)", wind=10)
    add("Win1", 90, [(0, S()), (14, S(hp=(0, 0, -1.8), tor=(30, 0, 0), aL=(-40, 30, 0, 60, 0), aR=(-40, 30, 0, 60, 0)), "smooth"), (24, S(hp=(0, 0, 0.2), aL=(176, 30, 0, 8, 0), aR=(176, 30, 0, 8, 0), tor=(-14, 0, 0), hd=(10, 0, 0), fl=(0.9, 0.2, 0.6, -30), fr=(0.9, -0.2, 0.6, -30)), "fast"), (50, S(aL=(176, 30, 0, 8, 0), aR=(176, 30, 0, 8, 0), tor=(-14, 0, 0), hd=(10, 0, 0)), "lin"), (89, S(aL=(176, 30, 0, 8, 0), aR=(176, 30, 0, 8, 0), tor=(-14, 0, 0), hd=(10, 0, 0)), "smooth")], serves="Win1 (results: both fists up)", category="results", wind=10)
    add("Win2", 90, [(0, S()), (16, S(tor=(4, 0, 0), hy=0, aL=(60, 20, 0, 130, 0), aR=(60, 20, 0, 130, 0), hd=(-4, 0, -20), fl=(0.9, 0.2, 0, 0), fr=(0.9, -0.2, 0, 0)), "smooth"), (40, S(tor=(-6, 0, 0), hy=0, aL=(70, 6, -50, 118, 0), aR=(70, 6, 50, 118, 0), hd=(0, 0, 14), fl=(0.9, 0.2, 0, 0), fr=(0.9, -0.2, 0, 0)), "smooth"), (89, S(tor=(-6, 0, 0), hy=0, aL=(70, 6, -50, 118, 0), aR=(70, 6, 50, 118, 0), hd=(0, 0, 14), fl=(0.9, 0.2, 0, 0), fr=(0.9, -0.2, 0, 0)), "smooth")], serves="Win2 (results: arms crossed)", category="results", wind=8)
    def win3(f):
        u = min(1.0, f / 30.0)
        fl_ = sm(min(1.0, max(0.0, (f - 6) / 22.0)))
        p = lerp_pose(S(hp=(0, 0, -2.0), tor=(30, 0, 0)), AIR.copy(), 0)
        if f < 6: return S(hp=(0, 0, -2.0 * f / 6), tor=(30 * f / 6, 0, 0))
        if f < 30:
            t = (f - 6) / 24.0
            tk = math.sin(math.pi * t) ** 0.6
            return lerp_pose(AIR.copy(aL=(150, 30, 0, 20, 0), aR=(150, 30, 0, 20, 0)), TUCK, tk).copy(fp=-360 * sm(t), hp=(0, 0, 4.5 * math.sin(math.pi * t)))
        if f < 40: return lerp_pose(S(hp=(0, 0, -1.6), tor=(24, 0, 0)), S(), sm((f - 30) / 10.0))
        return S(tor=(2, 0, -30), hy=-16, aR=(176, 18, 0, 8, 0), aL=(35, 20, 0, 100, 0)) if f > 54 else lerp_pose(S(), S(tor=(2, 0, -30), hy=-16, aR=(176, 18, 0, 8, 0), aL=(35, 20, 0, 100, 0)), sm((f - 40) / 14.0))
    add("Win3", 90, gen=win3, serves="Win3 (results: backflip into a point)", category="results", fit=True, wind=10)
    add("Lose", 60, loop=True, gen=lambda f: S(hp=(0, 0, -0.9), tor=(26, 0, 0), hd=(-30, 0, 6 * math.sin(2 * math.pi * f / 60)), aL=(5, 14, 0, 14, 0), aR=(5, 14, 0, 14, 0), fl=(0.9, 0.2, 0, 0), fr=(0.9, -0.2, 0, 0)), serves="Lose (results: slumped)", category="results", wind=3)
    # ============================================================ aliases (rows with no clip of their own)
    alias("CatchPull", "Catch", "alias", "the grab row's pull-in plays the same clip")
    alias("CatchDashPull", "CatchDash")
    alias("GuardReflect", "GuardOn", "alias", "reflect shield pose shares the shield raise")
    alias("Entry EntryEnd EntryStart", "EntryStart", "alias")
    alias("RebirthWait", "Rebirth")
    alias("RunDirect", "Run"); alias("FallF FallB", "Fall"); alias("FallAerialF FallAerialB", "FallAerial")
    alias("FallSpecialF FallSpecialB", "FallSpecial")
    alias("AttackS3HiS", "AttackS3Hi"); alias("AttackS3LwS", "AttackS3Lw"); alias("AttackS4HiS", "AttackS4Hi"); alias("AttackS4LwS", "AttackS4Lw")
    alias("SpecialN SpecialAirN", "NCharge", "alias", "Geno states NCharge/NRelease replace the Mario special rows"); alias("SpecialS SpecialAirS", "SLunge")
    alias("SpecialHi SpecialAirHi", "Rise"); alias("SpecialLw SpecialAirLw", "Counter")
    alias("LightThrowAirF LightThrowAirB LightThrowAirHi LightThrowAirLw", "LightThrowF", "placeholder", "air item throws reuse the ground clips")
    alias("LightThrowF4 LightThrowB4 LightThrowHi4 LightThrowLw4 LightThrowAirF4 LightThrowAirB4 LightThrowAirHi4 LightThrowAirLw4", "LightThrowF", "placeholder")
    alias("HeavyThrowF HeavyThrowB HeavyThrowHi HeavyThrowLw HeavyThrowF4 HeavyThrowB4 HeavyThrowHi4 HeavyThrowLw4", "LightThrowF", "placeholder", "heavy throws reuse the light throw")
    for fam in ("Sword", "Bat", "Parasol", "Harisen", "StarRod", "Lipstick"):
        alias(f"{fam}Swing1", "ItemSwing1", "placeholder", "one swing family for all item types")
        alias(f"{fam}Swing3", "ItemSwing3", "placeholder"); alias(f"{fam}Swing4", "ItemSwing4", "placeholder"); alias(f"{fam}SwingDash", "ItemSwingDash", "placeholder")
    alias("ItemParasolOpen ItemParasolFall ItemParasolFallSpecial ItemParasolDamageFall", "Fall", "placeholder", "parasol float has no own pose")
    alias("LGunShoot LGunShootAir LGunShootEmpty LGunShootAirEmpty FireFlowerShoot FireFlowerShootAir", "ItemShoot", "placeholder")
    alias("ItemScrew ItemScrewAir DamageScrew DamageScrewAir", "DamageFlyRoll", "placeholder", "screw attack spin")
    alias("ItemScopeStart ItemScopeRapid ItemScopeFire ItemScopeEnd ItemScopeAirStart ItemScopeAirRapid ItemScopeAirFire ItemScopeAirEnd ItemScopeStartEmpty ItemScopeRapidEmpty ItemScopeFireEmpty ItemScopeEndEmpty ItemScopeAirStartEmpty ItemScopeAirRapidEmpty ItemScopeAirFireEmpty ItemScopeAirEndEmpty", "ItemShoot", "placeholder")
    alias("LiftTurn", "Turn", "placeholder")
    alias("LiftWalk1 LiftWalk2", "LiftWalk")
    alias("DownBoundU DownBoundD", "DownBoundU", "alias")  # exact names exist; harmless
    ALIASES.pop("DownBoundU", None); ALIASES.pop("DownBoundD", None)
    alias("ShoulderedWait", "Wait", "placeholder", "shouldered carry is not part of this fighter")
    alias("ShoulderedWalkSlow", "WalkSlow", "placeholder"); alias("ShoulderedWalkMiddle", "WalkMiddle", "placeholder")
    alias("ShoulderedWalkFast", "WalkFast", "placeholder"); alias("ShoulderedTurn", "Turn", "placeholder")
    alias("ThrownFF ThrownFB ThrownFHi ThrownFLw", "ThrownF", "placeholder", "throws by other fighters use the generic flung clip")
    alias("ThrownlwWomen", "ThrownLw", "placeholder")
    alias("CaptureCaptain CaptureYoshi CaptureKoopa CaptureKoopaAir CaptureKirby CaptureKirbyYoshi CaptureMewtwo CaptureMewtwoAir CaptureMasterHand CaptureCrazyHand CaptureLeadead CaptureLikelike", "CaptureWaitHi", "placeholder", "special-grab holds reuse the generic struggle")
    alias("CaptureWaitKoopa CaptureWaitKoopaAir CaptureWaitKirby CaptureWaitMasterHand CaptureWaitCrazyHand CaptureDamageKoopa CaptureDamageKoopaAir CaptureDamageMasterHand CaptureDamageCrazyHand", "CaptureWaitHi", "placeholder")
    alias("ThrownKoopaF ThrownKoopaB ThrownKoopaAirF ThrownKoopaAirB ThrownKirbyStar ThrownCopyStar ThrownKirby ThrownMewtwo ThrownMewtwoAir ThrownMasterHand ThrownCrazyHand", "ThrownF", "placeholder")
    alias("YoshiEgg KirbyYoshiEgg", "DamageIce", "placeholder", "egg trap shows the frozen pose")
    alias("DeadUpStar DeadUpFall DeadUpFallHitCamera DeadUpFallHitCameraFlat", "DamageFlyRoll", "placeholder", "star KO spin")
    alias("DamageSong DamageSongWait DamageSongRv DamageBind", "Furafura", "placeholder", "sleep / bind poses reuse the dizzy sway")
    alias("WarpStarJump", "JumpAerialF", "placeholder"); alias("WarpStarFall", "Fall", "placeholder")
    alias("HammerWait", "Wait", "placeholder"); alias("HammerWalk HammerTurn", "WalkMiddle", "placeholder"); alias("HammerKneeBend", "KneeBend", "placeholder")
    alias("HammerFall HammerJump", "Fall", "placeholder"); alias("HammerLanding", "Landing", "placeholder")
    alias("KinokoGiantStart KinokoGiantStartAir KinokoGiantEnd KinokoGiantEndAir KinokoSmallStart KinokoSmallStartAir KinokoSmallEnd KinokoSmallEndAir", "Wait", "placeholder", "mushroom size change: the engine scales the model; no bone is scaled by clips")
    alias("BuryJump", "KneeBend", "placeholder"); alias("Bury BuryWait", "SquatWait", "placeholder")
    alias("BarrelWait Barrel", "Wait", "placeholder")
    alias("Sleep", "Wait", "placeholder")
    alias("DownFowardU", "DownForwardU", "alias", "the engine spells this row DownFoward"); alias("DownFowardD", "DownForwardD", "alias")
    alias("DownReflect", "FlyReflectWall", "placeholder"); alias("OttottoWait", "Ottotto", "alias"); alias("ReboundStop", "Rebound", "alias")
    alias("Attack100Start Attack100Loop Attack100End", "Attack100Loop", "alias")
    for k in ("Attack100Start", "Attack100Loop", "Attack100End"): ALIASES.pop(k, None)
    alias("AppealSRx", "AppealSR"); ALIASES.pop("AppealSRx", None)
    add("DamageIce", 4, [(0, P(hp=(0, 0, 0), tor=(-8, 0, 6), aL=(60, 50, 0, 40, 0), aR=(60, 50, 0, 40, 0), hd=(-8, 0, 10), fl=(0.9, 0.5, 0, 0), fr=(0.9, -0.5, 0, 0))), (3, P(hp=(0, 0, 0), tor=(-8, 0, 6), aL=(60, 50, 0, 40, 0), aR=(60, 50, 0, 40, 0), hd=(-8, 0, 10), fl=(0.9, 0.5, 0, 0), fr=(0.9, -0.5, 0, 0)), "lin")], serves="DamageIce (frozen: one rigid pose)", wind=0)
    add("DamageIceJump", 20, [(0, AIR), (10, AIR.copy(lL=(60, 6, 80, 0), lR=(60, 6, 80, 0)), "smooth"), (19, AIR, "smooth")], serves="DamageIceJump (frozen hop)", category="air", fit=False, wind=10)
    return CLIPS
