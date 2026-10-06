"""Common-state clips: everything a fighter needs besides its attacks (locomotion, jumps, shield, damage,
down/tech, ledge, grab victim, items, taunts, results). Named after the engine's motion rows
(tools/geno/report.py lists the 351 rows); rows without their own clip are mapped in ALIASES with a status.
"""
import math
from anim_lib import P, Pose, Clip, lerp_pose, extrap_pose, EASES
from clips_moves import STAND, GL, GR, spin, polish

CLIPS = []
ALIASES = {}

def add(name, n, keys=None, **kw):
    kw.setdefault("category", "common")
    keys = [(float(k[0]), k[1], k[2] if len(k) > 2 else "smooth") for k in (keys or [])]
    if keys and kw.get("hit") and not kw.get("loop") and kw.pop("polish", True):
        keys = polish(keys, kw["hit"][0], n)
    kw.pop("polish", None)
    c = Clip(name, n, keys=keys, **kw)
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

# ------------------------------------------------------------------ locomotion (see loco.py)
import loco

def add_gait(name, N, cycles, duty, v, serves="", wind=14, **kw):
    """A looping gait of N clip frames made of `cycles` full cycles. v = the ground speed (units / frame) it is slide-free at."""
    Nc = N / cycles
    base = kw.pop("clip_base", None)
    g = loco.gait(Nc, duty, v, base=base, **kw)
    c = add(name, N, loop=True, gen=g, serves=serves, wind=wind, lagk=0.0, head_follow=0.0,
            ref=dict(stride_per_cycle_units=round(v * duty * Nc * 2, 3), stance_duty=duty, ground_ref_speed=round(v, 4), gait_cycles_in_clip=cycles,
                     note="slide-free body speed in units/frame at animation rate 1.0 (contact point speed = body speed in every stance phase); the engine scales the rate"))
    c.locomotion = True
    return c

def register():
    CLIPS.clear(); ALIASES.clear()
    # ============================================================ stance and locomotion
    def wait_gen(f):
        s = math.sin(2 * math.pi * f / 80.0)
        return STAND.copy(hp=(0, 0, 0.0), tor=(8 + 1.6 * s, 0.6 * s, -14), aL=(55 + 3 * s, 18 + 1.2 * s, 0, 105 - 3 * s, 0), aR=(35 + 2 * s, 10, 0, 118 + 2 * s, 0), hd=(-3 - s, 0, 6))
    add("Wait", 80, loop=True, gen=wait_gen, serves="Wait (ready stance, breathing)", wind=5)
    # Two gait cycles per clip for the walks (the clip lengths are fixed by the engine contract: 44 / 34 / 26 frames) so the
    # cadence stays human; the Run is one cycle of 16 frames with a flight phase.
    add_gait("WalkSlow", 44, 2, 0.60, 0.29, arm=16, elbow0=14, elbow1=10, lean=3, dip=0.45, heel_t=3.0, toe_t=4.0, phi_h=18, phi_t=-30, lift=0.55, xc=0.15, out=0.3, twist=5, sway=0.45,
             serves="WalkSlow", wind=10)
    add_gait("WalkMiddle", 34, 2, 0.57, 0.50, arm=24, elbow0=18, elbow1=18, lean=5, dip=0.6, heel_t=2.5, toe_t=3.0, phi_h=20, phi_t=-34, lift=0.8, xc=0.2, out=0.3, twist=6, sway=0.4,
             serves="WalkMiddle", wind=16)
    add_gait("WalkFast", 26, 2, 0.53, 0.72, arm=32, elbow0=28, elbow1=26, lean=8, dip=0.7, heel_t=2.0, toe_t=2.4, phi_h=16, phi_t=-38, lift=1.1, xc=0.15, out=0.28, twist=8, sway=0.35,
             serves="WalkFast", wind=26)
    add_gait("Run", 16, 1, 0.27, 1.32, arm=42, elbow0=84, elbow1=18, lean=17, dip=0.55, run=True, flight=0.9, heel_t=0.8, toe_t=1.6, phi_h=8, phi_t=-42, lift=1.7, xc=0.1, out=0.25, twist=9, sway=0.2,
             arm_abd=10, serves="Run / RunDirect", wind=58)
    rg = loco.gait(16.0, 0.27, 1.32, 44, 86, 16, 19, 0.6, run=True, flight=1.0, heel_t=0.8, toe_t=1.5, phi_h=6, phi_t=-42, lift=1.8, xc=0.1, out=0.25, twist=9, sway=0.2, arm_abd=10)
    def dash_gen(f):
        u = min(1.0, f / 6.0)
        run = rg(f + 3)
        crouch = run.copy(tor=(30, 0, 0), hd=(-18, 0, 0), aL=(-34, 16, 0, 70, 0), aR=(-48, 16, 0, 80, 0))
        # drive out of a low start: the trunk comes up from 32 degrees of lean, the arms pump
        p = lerp_pose(crouch, run, sm(u))
        lean = 31 - 13 * sm(f / 12.0)
        return p.copy(tor=(lean, p.v["tor"][1], p.v["tor"][2]), hd=(-lean * 0.7, 0, p.v["hd"][2]))
    c = add("Dash", 16, gen=dash_gen, serves="Dash (burst into the run cycle; loops to Run)", wind=64, lagk=0.0, head_follow=0.0,
            ref=dict(ground_ref_speed=1.32, note="the dash runs the Run gait at 1.32 units/frame from a low drive start; the engine scales the rate"))
    brk0 = P(tor=(-6, 0, 6), hy=4, aL=(40, 46, 0, 50, 0), aR=(26, 52, 0, 56, 0), fl=(0.7, 2.0, 0, 8), fr=(0.7, -1.0, 0, 0), hd=(2, 0, 0), hp=(0, -0.3, -0.6))
    brk1 = brk0.copy(tor=(-18, 0, 8), hp=(0, -0.6, -0.9), fl=(0.8, 2.5, 0, 14), fr=(0.8, -1.1, 0.2, 0), aL=(52, 58, 0, 40, 0), aR=(40, 62, 0, 44, 0), hd=(8, 0, 0))
    brk2 = S(hp=(0, 0, -0.9), tor=(14, 0, -8), aL=(40, 30, 0, 80, 0), aR=(30, 30, 0, 90, 0))
    add("RunBrake", 16, [(0, brk0), (4, brk1, "out"), (9, brk1, "lin"), (12, brk2, "smooth"), (15, S(), "smooth")], serves="RunBrake (skid)", wind=36)
    # turn: the engine flips facing between frames 4 and 5 (absolute orientation continuous: +70 before, -70 after).
    # The head leads (eyes first), the pivot foot digs in, the arms counter-swing, then the trunk overshoots and settles.
    t0 = S()
    t_ant = S(tor=(9, 0, -22), hy=-12, hd=(-2, 0, -8), aL=(60, 18, 0, 100, 0), aR=(30, 14, 0, 120, 0))
    t1 = S(tor=(10, 0, 70), hy=40, hd=(0, 0, 58), aL=(30, 52, 0, 60, 0), aR=(52, 36, 0, 70, 0), fl=(1.0, 0.4, 0, 0), fr=(1.0, -0.4, 0, 0), hp=(0, 0, -0.5))
    t2 = t1.copy(tor=(10, 0, -70), hy=-40, hd=(0, 0, -30))
    t3 = S(tor=(10, 0, -34), hy=-18, hd=(-2, 0, -16), aL=(50, 40, 0, 80, 0), aR=(26, 22, 0, 100, 0))
    add("Turn", 10, [(0, t0), (1, t_ant, "out"), (4, t1, "fast"), (5, t2, "hold"), (7, t3, "out"), (9, S(), "smooth")], serves="Turn (engine flips facing between frames 4 and 5)", wind=10, head_follow=0.0, lagk=0.6)
    tr1 = t1.copy(tor=(26, 0, 70), hp=(0, 0, -0.8), fl=(1.4, 1.0, 0, 0), fr=(1.0, -1.2, 0, 0), aL=(10, 70, 0, 50, 0), aR=(40, 60, 0, 60, 0))
    tr2 = tr1.copy(tor=(26, 0, -70), hy=-40, hd=(0, 0, -30))
    add("TurnRun", 12, [(0, S(tor=(24, 0, 0), hp=(0, 0, -0.3))), (1, S(tor=(26, 0, -16), hy=-8, hp=(0, 0, -0.5), aL=(60, 30, 0, 90, 0)), "out"), (5, tr1, "fast"), (6, tr2, "hold"),
                       (8, S(tor=(22, 0, -34), hy=-18, hp=(0, 0, -0.5), aL=(40, 50, 0, 80, 0), aR=(20, 40, 0, 90, 0)), "out"), (11, S(tor=(18, 0, -14)), "smooth")],
        serves="TurnRun (engine flips facing between frames 5 and 6)", wind=30, head_follow=0.0, lagk=0.6)
    # jump squat / jumps: squash (crouch, arms swept back), then stretch (legs driven straight, toes pointed, arms up), then tuck
    kb1 = S(hp=(0, 0, -0.9), tor=(16, 0, -10), aL=(10, 26, 0, 70, 0), aR=(10, 26, 0, 70, 0), fl=(0.9, 0.5, 0, 0), fr=(0.9, -0.5, 0, 0), hd=(-6, 0, 0))
    ksq = S(hp=(0, 0, -2.0), tor=(30, 0, -6), aL=(-50, 30, 0, 36, 0), aR=(-50, 30, 0, 36, 0), fl=(1.0, 0.2, 0, 0), fr=(1.0, -0.2, 0, 0), hd=(-14, 0, 0))
    add("KneeBend", 5, [(0, S()), (2, kb1, "in"), (4, ksq, "out")], serves="KneeBend (jump squat)", wind=2, lagk=0.7)
    push = AIR.copy(lL=(-10, 4, 4, -50), lR=(-10, 4, 4, -50), aL=(160, 28, 0, 14, 0), aR=(160, 28, 0, 14, 0), tor=(-8, 0, 0), hd=(8, 0, 0), hp=(0, 0, 0.6))
    mid1 = AIR.copy(lL=(36, 6, 60, 0), lR=(10, 6, 50, 0), aL=(120, 34, 0, 30, 0), aR=(120, 34, 0, 30, 0), tor=(4, 0, -4))
    add("JumpF", 40, [(0, push, "out"), (4, push.copy(lL=(0, 4, 18, -40), lR=(0, 4, 18, -40), hp=(0, 0, 0.3)), "smooth"), (10, AIR.copy(lL=(78, 6, 100, 10), lR=(58, 6, 86, 10), aL=(88, 42, 0, 56, 0), aR=(88, 42, 0, 56, 0), tor=(16, 0, -4)), "smooth"),
                      (24, AIR.copy(lL=(46, 6, 74, 12), lR=(22, 6, 54, 12), tor=(10, 0, -4)), "smooth"), (39, AIR, "smooth")], serves="JumpF (full hop forward)", category="air", fit=False, wind=-18)
    add("JumpB", 40, [(0, push.copy(tor=(-14, 0, 0)), "out"), (4, push.copy(lL=(0, 4, 18, -40), lR=(0, 4, 18, -40), tor=(-16, 0, 0)), "smooth"),
                      (10, AIR.copy(lL=(58, 6, 94, 10), lR=(74, 6, 94, 10), aL=(104, 30, 0, 42, 0), aR=(104, 30, 0, 42, 0), tor=(-14, 0, 6)), "smooth"),
                      (24, AIR.copy(lL=(30, 6, 62, 10), lR=(40, 6, 72, 10), tor=(-9, 0, 4)), "smooth"), (39, AIR.copy(tor=(-4, 0, 0)), "smooth")], serves="JumpB (full hop back)", category="air", fit=False, wind=-18)
    def djump(sign):
        def g(f):
            if f < 3:                                              # kick off: a quick crouch in the air, arms swept down and back
                u = f / 3.0
                return lerp_pose(AIR, AIR.copy(lL=(60, 6, 100, 0), lR=(60, 6, 100, 0), aL=(-30, 30, 0, 40, 0), aR=(-30, 30, 0, 40, 0), tor=(14, 0, 0)), sm(u)).copy(hp=(0, 0, -0.5 * u))
            u = min(1.0, (f - 3) / 22.0)
            ease = u * u * (3 - 2 * u)
            ease = ease * 0.85 + u * 0.15                              # a little more even mid-flip
            tuck = math.sin(math.pi * min(1.0, u)) ** 0.7
            p = lerp_pose(AIR.copy(aL=(150, 30, 0, 20, 0), aR=(150, 30, 0, 20, 0)), TUCK, tuck)
            if f > 25:                                             # open out: legs reach for the ground, arms spread
                w = sm((f - 25) / 8.0)
                p = lerp_pose(p, AIR.copy(aL=(40, 62, 0, 30, 0), aR=(40, 62, 0, 30, 0), lL=(40, 8, 40, 10), lR=(24, 8, 40, 10)), w)
            return p.copy(fp=sign * 360 * ease, hp=(0, 0, 0.9 * math.sin(math.pi * u)))
        return g
    add("JumpAerialF", 34, gen=djump(1), serves="JumpAerialF (double jump: forward flip)", category="air", fit=False, wind=0)
    add("JumpAerialB", 34, gen=djump(-1), serves="JumpAerialB (double jump: back flip)", category="air", fit=False, wind=0)
    def fall_gen(f):
        a = 2 * math.pi * f / 20.0
        s, s2 = math.sin(a), math.sin(a - 0.9)
        return AIR.copy(lL=(32 + 7 * s, 6, 58 - 10 * s, 15), lR=(10 - 7 * s, 6, 40 + 10 * s, 15), aL=(40 + 10 * s2, 42 + 4 * s, 0, 40 + 6 * s2, 0), aR=(40 - 10 * s2, 42 - 4 * s, 0, 40 - 6 * s2, 0),
                        tor=(8 + 1.2 * math.sin(2 * a), 0.8 * s, -8), hd=(-2 - 1.5 * s2, 1.2 * s, 4))
    add("Fall", 20, loop=True, gen=fall_gen, serves="Fall / FallAerial", category="air", fit=False, wind=26)
    add("FallAerial", 20, loop=True, gen=fall_gen, serves="FallAerial", category="air", fit=False, wind=26)
    add("FastFall", 8, [(0, P(lL=(6, 3, 6, -30), lR=(6, 3, 6, -30), aL=(-22, 12, 0, 20, 0), aR=(-22, 12, 0, 20, 0), tor=(12, 0, 0), hd=(-6, 0, 0), fl=None, fr=None, cuL=1, cuR=1)),
                         (4, P(lL=(12, 3, 4, -30), lR=(0, 3, 10, -30), aL=(-30, 14, 0, 14, 0), aR=(-26, 14, 0, 20, 0), tor=(15, 0, 0), hd=(-7, 0, 0), fl=None, fr=None), "smooth")],
        loop=True, serves="FastFall (tight dive; engine may bind to FallAerial rows)", category="air", fit=False, wind=40)
    help_ = P(aL=(60, 78, 0, 20, 0), aR=(60, 78, 0, 20, 0), lL=(20, 14, 40, 20), lR=(16, 12, 36, 20), tor=(6, 0, 0), hd=(8, 0, 0), fl=None, fr=None, cuL=0, cuR=0)
    def help_gen(f):
        a = 2 * math.pi * f / 24.0
        s = math.sin(a); s2 = math.sin(a - 1.0)
        return help_.copy(tor=(6 + 3 * s, 4 * s, 0), aL=(60 + 8 * s2, 78 + 6 * s, 0, 20 + 6 * s2, 8 * s2), aR=(60 - 8 * s2, 78 - 6 * s, 0, 20 - 6 * s2, -8 * s2), hd=(8 - 3 * s, 0, 6 * s2),
                          lL=(20 + 5 * s, 14, 40 - 6 * s, 20), lR=(16 - 5 * s, 12, 36 + 6 * s, 20))
    add("FallSpecial", 24, loop=True, gen=help_gen, serves="FallSpecial (helpless fall, arms out)", category="air", fit=False, wind=30)
    def dfall(f):
        a = 2 * math.pi * f / 18.0
        s, s2 = math.sin(a), math.sin(a - 1.1)
        return P(fp=22 * s, aL=(90 + 34 * s2, 70, 0, 30 + 10 * s2, 6 * s), aR=(90 - 34 * s2, 70, 0, 30 - 10 * s2, -6 * s), lL=(40 + 8 * s, 12, 60 - 6 * s, 10), lR=(30 - 8 * s, 12, 70 + 6 * s, 10),
                 hd=(-6 - 3 * s2, 0, 14 * s2), tor=(4 * s, 3 * s2, 0), fl=None, fr=None, cuL=0, cuR=0)
    add("DamageFall", 18, loop=True, gen=dfall, serves="DamageFall (tumbling fall after hitstun)", category="air", fit=False, wind=40)
    # landings (squash on contact, recovery with a small rebound) and crouch
    def landing(name, n, depth, lean, serves):
        imp = S(hp=(0, 0, -depth * 0.45), tor=(lean * 0.5, 0, -8), aL=(55, 52, 0, 40, 0), aR=(55, 52, 0, 40, 0), fl=(1.1, 0.3, 0, 0), fr=(1.1, -0.3, 0, 0), hd=(-3, 0, 0))
        low = S(hp=(0, 0, -depth), tor=(lean, 0, -8), aL=(14, 36, 0, 70, 0), aR=(14, 36, 0, 70, 0), fl=(1.3, 0.3, 0, 0), fr=(1.3, -0.3, 0, 0), hd=(-10, 0, 0))
        reb = S(hp=(0, 0, 0.12), tor=(2, 0, -14), aL=(50, 20, 0, 100, 0), aR=(36, 14, 0, 116, 0))
        t_low = max(1, n // 4)
        add(name, n, [(0, imp, "out"), (t_low, low, "out"), (int(n * 0.62), reb, "smooth"), (n - 1, S(), "smooth")], serves=serves, wind=-6, lagk=0.8)
    landing("Landing", 8, 1.0, 14, "Landing")
    landing("LandingAirN", 8, 1.3, 16, "LandingAirN"); landing("LandingAirF", 10, 1.5, 22, "LandingAirF")
    landing("LandingAirB", 9, 1.4, 18, "LandingAirB"); landing("LandingAirHi", 8, 1.3, 10, "LandingAirHi"); landing("LandingAirLw", 14, 2.1, 30, "LandingAirLw")
    landing("LandingFallSpecial", 24, 2.2, 30, "LandingFallSpecial (helpless landing)")
    sq = S(hp=(0, 0, -2.5), tor=(32, 0, -10), hy=-4, aL=(30, 26, 0, 60, 0), aR=(24, 26, 0, 60, 0), fl=(1.4, 0.4, 0, 0), fr=(1.4, -0.5, 0, 0), hd=(-18, 0, 0))
    add("Squat", 8, [(0, S()), (3, S(hp=(0, 0, -1.2), tor=(18, 0, -10), aL=(40, 26, 0, 80, 0), aR=(30, 26, 0, 80, 0), fl=(1.2, 0.5, 0, 0), fr=(1.2, -0.5, 0, 0)), "in"), (7, sq, "back")], serves="Squat (crouch in)", wind=2)
    add("SquatWait", 40, loop=True, gen=lambda f: sq.copy(hp=(0, 0, -2.5 + 0.08 * math.sin(2 * math.pi * f / 40)), tor=(32 + 1.5 * math.sin(2 * math.pi * f / 40), 0, -10)), serves="SquatWait (crouch hold)", wind=4)
    add("SquatRv", 8, [(0, sq), (3, S(hp=(0, 0, -1.2), tor=(18, 0, -10), aL=(40, 26, 0, 80, 0), aR=(30, 26, 0, 80, 0), fl=(1.2, 0.5, 0, 0), fr=(1.2, -0.5, 0, 0)), "out"), (7, S(), "smooth")], serves="SquatRv (crouch out)", wind=2)
    # ============================================================ shield, dodges
    gd = S(hp=(0, 0, -0.9), tor=(20, 0, -6), hy=-4, aL=(86, 24, 0, 132, 0), aR=(80, 18, 0, 138, 0), hd=(-18, 0, 0), fl=(1.0, 0.6, 0, 0), fr=(1.0, -0.6, 0, 0))
    gd_mid = S(hp=(0, 0, -0.5), tor=(12, 0, -10), aL=(60, 26, 0, 110, 0), aR=(52, 20, 0, 120, 0), hd=(-8, 0, 0), fl=(0.9, 0.6, 0, 0), fr=(0.9, -0.6, 0, 0))
    add("GuardOn", 8, [(0, S()), (3, gd_mid, "in"), (6, extrap_pose(gd_mid, gd, 1.15), "fast"), (7, gd, "out")], serves="GuardOn", wind=4)
    add("Guard", 24, loop=True, gen=lambda f: gd.copy(tor=(20 + 1.0 * math.sin(2 * math.pi * f / 24), 0, -6), hp=(0, 0, -0.9 + 0.05 * math.sin(2 * math.pi * f / 24))), serves="Guard (shield hold)", wind=4)
    add("GuardOff", 10, [(0, gd), (2, extrap_pose(gd, S(), -0.12), "out"), (6, S(hp=(0, 0, 0.1), tor=(5, 0, -14)), "smooth"), (9, S(), "smooth")], serves="GuardOff", wind=4)
    add("GuardSetOff", 12, [(0, gd), (2, gd.copy(hp=(0, -0.9, -0.5), tor=(8, 0, -6), hd=(-4, 0, 0), aL=(80, 30, 0, 120, 0)), "fast"), (5, gd.copy(hp=(0, -0.5, -0.6), tor=(12, 0, -6)), "out"), (11, gd, "smooth")], serves="GuardSetOff (shield hit flinch)", wind=8)
    # a ground roll: crouch (anticipation), then a tight somersault along the ground in which the distance travelled is proportional to
    # the angle turned (no slipping: 360 degrees at a radius of about 2.6 units is the 16 unit root motion), then stand up
    def roll_gen(sign, n=30, dist=16.0, start=None):
        crouch = S(hp=(0, 0, -1.7), tor=(34, 0, 0), hy=0, aL=(-30, 30, 0, 80, 0), aR=(-30, 30, 0, 80, 0), fl=(1.1, 0.5, 0, 0), fr=(1.1, -0.5, 0, 0), hd=(-14, 0, 0))
        tuck = TUCK.copy(hp=(0, 0, -2.6), lL=(120, 4, 135, 10), lR=(120, 4, 135, 10), tor=(40, 0, 0), aL=(75, 18, 0, 118, 0), aR=(75, 18, 0, 118, 0), hd=(-22, 0, 0))
        wide = crouch.copy(hp=(0, 0, -1.2), tor=(24, 0, 0))
        a0, a1 = 0.16, 0.86
        def g(f):
            u = min(1.0, f / (n - 1.0))
            first = start if start is not None else S()
            if u < a0:
                w = u / a0
                return lerp_pose(first, crouch, sm(w) ** 0.8).copy(tp=(0, 0, 0))
            if u <= a1:
                w = (u - a0) / (a1 - a0)
                r = w * w * (3 - 2 * w)
                tk = sm(min(1.0, w / 0.22)) * (1 - sm(max(0.0, (w - 0.78) / 0.22)))
                p = lerp_pose(crouch, tuck, tk)
                return p.copy(fp=sign * 360 * r, tp=(0, sign * dist * r, 0))
            w = (u - a1) / (1 - a1)
            p = lerp_pose(wide.copy(hp=(0, 0, -1.9)), S(), sm(w) ** 1.0)
            return p.copy(tp=(0, sign * dist, 0))
        return g
    add("EscapeF", 30, gen=roll_gen(1), serves="EscapeF (forward roll)", root_motion=True, category="roll", fit=False, wind=20, notes="root motion on `trans`: 16 units forward")
    add("EscapeB", 30, gen=roll_gen(-1), serves="EscapeB (back roll)", root_motion=True, category="roll", fit=False, wind=20, notes="root motion on `trans`: 16 units backward")
    sd0 = S(hp=(0, 0, -0.7), tor=(14, 0, 8), hy=4, aL=(50, 24, 0, 110, 0), aR=(40, 20, 0, 120, 0), hd=(-6, 0, 0), fl=(1.0, 0.7, 0, 0), fr=(1.0, -0.7, 0, 0))
    sd = S(hp=(0, 0, -1.4), tor=(24, 0, -52), hy=-32, aL=(62, 30, 0, 120, 0), aR=(72, 30, 0, 120, 0), hd=(-12, 0, 34), fl=(1.2, 0.6, 0, 0), fr=(1.2, -0.6, 0, 0))
    add("EscapeN", 24, [(0, S()), (2, sd0, "in"), (6, extrap_pose(sd0, sd, 1.1), "fast"), (9, sd, "out"), (16, sd.copy(tor=(26, 0, -56), hy=-34, hd=(-12, 0, 38)), "smooth"), (20, S(hp=(0, 0, -0.5), tor=(12, 0, -4)), "smooth"), (23, S(), "smooth")], serves="EscapeN (spot dodge)", wind=6)
    ad = TUCK.copy(tor=(30, 0, 0))
    def air_dodge(f):
        if f < 4:                                                   # squash into the tuck
            return lerp_pose(AIR, AIR.copy(lL=(70, 6, 100, 0), lR=(70, 6, 100, 0), tor=(16, 0, 0), aL=(70, 24, 0, 90, 0), aR=(70, 24, 0, 90, 0)), sm(f / 4.0))
        w = min(1.0, (f - 4) / 16.0)
        spin = 360 * (w * w * (3 - 2 * w))
        tk = sm(min(1.0, (f - 3) / 5.0)) * (1 - sm(max(0.0, (f - 17) / 8.0)))
        p = lerp_pose(AIR, ad, tk)
        if f > 20: p = lerp_pose(p, AIR.copy(aL=(60, 56, 0, 30, 0), aR=(60, 56, 0, 30, 0)), sm((f - 20) / 7.0))
        return p.copy(fp=spin, hp=(0, 0, 0))
    add("EscapeAir", 28, gen=air_dodge, serves="EscapeAir (air dodge)", category="air", fit=False, wind=8)
    # ============================================================ damage (ground, light -> heavy), air, fly
    # a hit throws the body away from the blow (the head and trunk first, the arms flare after), overshoots, rocks back past the
    # rest pose and settles; heavier hits go further, hold longer and bend the legs more
    def hit(name, n, kind, s, air=False):
        base = P(fl=None, fr=None, lL=(30, 6, 60, 15), lR=(10, 6, 40, 15), cuL=0, cuR=0) if air else STAND
        flare = 50 + 8 * s
        if kind == "Hi":                                           # struck high: the head snaps back, the chest follows, the knees give a little
            pk = base.copy(tor=(-20 * s, 0, 10 * s), hd=(-28 * s, 0, -12 * s), hp=(0, -0.5 * s, 0.2 - 0.25 * s), aL=(60, flare + 10, 0, 40, 0), aR=(50, flare + 10, 0, 50, 0))
        elif kind == "N":                                          # struck mid: the trunk folds around the blow, then rocks back
            pk = base.copy(tor=(-24 * s, 0, 12 * s), hd=(-8 * s, 0, 4 * s), hp=(0, -0.8 * s, -0.2 * s), aL=(40, flare, 0, 60, 0), aR=(40, flare, 0, 60, 0))
        else:                                                      # struck low: doubled over, the head dropping forward
            pk = base.copy(tor=(34 * s, 0, 8 * s), hd=(14 * s, 0, 0), hp=(0, 0.4 * s, -0.7 * s), aL=(20, flare - 5, 0, 40, 0), aR=(20, flare - 5, 0, 40, 0))
        if air: pk = pk.copy(lL=(30 + 20 * s, 8, 50, 10), lR=(10 + 25 * s, 8, 30, 10))
        end = base if not air else AIR
        over = extrap_pose(base, pk, 1.25)
        rock = extrap_pose(pk, end, 1.18)
        add(name, n, [(0, base), (2, over, "fast"), (4, pk, "out"), (int(n * 0.55), pk.add(tor=(-1.5 * s, 0, 0), hd=(1.0 * s, 0, 0)), "smooth"), (int(n * 0.8), rock, "smooth"), (n - 1, end, "smooth")],
            serves=name, category="air" if air else "common", fit=not air, wind=12)
    for kind in ("Hi", "N", "Lw"):
        for i, (n, s) in enumerate(((14, 0.9), (20, 1.4), (28, 2.0)), 1):
            hit(f"Damage{kind}{i}", n, kind, s)
    for i, (n, s) in enumerate(((14, 0.9), (20, 1.4), (28, 2.0)), 1):
        hit(f"DamageAir{i}", n, "N", s, air=True)
    # launched: the body holds the line of the launch, the limbs trail it and flail with a delay (a travelling wave from the hips out),
    # the head lolls on its follower. The tumble (Roll) spins about the hips with the arms flung by the spin and the legs trailing.
    def fly(name, fp, spinning=False, serves=""):
        n = 20 if spinning else 16
        def g(f):
            a = 2 * math.pi * f / n
            s = math.sin(a)
            if spinning:
                ang = 360.0 * f / n
                return P(fp=ang, aL=(82 + 18 * math.sin(a - 0.7), 84, 0, 16 + 10 * math.sin(a - 1.4), 0), aR=(82 - 18 * math.sin(a - 0.7), 84, 0, 16 - 10 * math.sin(a - 1.4), 0),
                         lL=(46 + 14 * math.sin(a - 1.0), 14, 54 - 14 * math.sin(a - 1.0), 6), lR=(34 - 14 * math.sin(a - 1.0), 14, 64 + 14 * math.sin(a - 1.0), 6), hd=(-12, 0, 10 * math.sin(a - 1.6)),
                         tor=(10 + 4 * math.sin(2 * a), 0, 0), fl=None, fr=None, cuL=0, cuR=0, hp=(0, 0, 0))
            return P(fp=fp + 7 * s, aL=(78 + 22 * math.sin(a - 0.6), 70 + 12 * math.sin(a - 1.2), 0, 22 + 14 * math.sin(a - 1.4), 12 * math.sin(a - 2.0)),
                     aR=(78 - 22 * math.sin(a - 0.6), 70 - 12 * math.sin(a - 1.2), 0, 22 - 14 * math.sin(a - 1.4), -12 * math.sin(a - 2.0)),
                     lL=(38 + 12 * math.sin(a - 0.8), 12, 60 - 14 * math.sin(a - 0.8), 10 + 10 * math.sin(a - 1.8)), lR=(26 - 12 * math.sin(a - 0.8), 12, 70 + 14 * math.sin(a - 0.8), 10 - 10 * math.sin(a - 1.8)),
                     hd=(-10 - 5 * math.sin(a - 1.0), 0, 8 * math.sin(a - 1.6)), tor=(-6 * math.sin(a - 0.4), 3 * s, 0), fl=None, fr=None, cuL=0, cuR=0, hp=(0, 0, 0))
        add(name, n, loop=True, gen=g, serves=serves or name, category="air", fit=False, wind=44)
    fly("DamageFlyHi", -55, serves="DamageFlyHi (launched, head high)"); fly("DamageFlyN", -25, serves="DamageFlyN")
    fly("DamageFlyLw", 35, serves="DamageFlyLw"); fly("DamageFlyTop", -140, serves="DamageFlyTop (launched upward)")
    fly("DamageFlyRoll", 0, spinning=True, serves="DamageFlyRoll (tumble spin)")
    # ============================================================ lying, down, tech
    def lying(sign, name, n=30):
        base = LAY(sign)
        add(name, n, loop=True, gen=lambda f: base.copy(hp=(0, 0, -4.1 + 0.05 * math.sin(2 * math.pi * f / n)), tor=(0, 0, 0), hd=(0, 0, 3 * math.sin(2 * math.pi * f / n))), serves=name, category="down", fit=False, wind=2)
    lying(-1, "DownWaitU"); lying(1, "DownWaitD")
    for sign, sfx in ((-1, "U"), (1, "D")):
        lay = LAY(sign)
        air = lay.copy(fp=sign * 40, hp=(0, 0, -2.0), lL=(40, 6, 60, 0), lR=(40, 6, 60, 0), aL=(60, 50, 0, 30, 0), aR=(60, 50, 0, 30, 0))
        flop = lay.copy(hp=(0, 0, -4.1), aL=(sign * -40, 40, 0, 14, 0), aR=(sign * -40, 40, 0, 14, 0), lL=(sign * 14, 12, 8, 0), lR=(sign * 14, 12, 8, 0), hd=(sign * 10, 0, 0))
        add(f"DownBound{sfx}", 22, [(0, air, "in"), (4, flop, "fast"), (8, lay.copy(fp=sign * 52, hp=(0, 0, -3.0), aL=(sign * 30, 60, 0, 30, 0), aR=(sign * 30, 60, 0, 30, 0)), "out"), (12, flop, "in"), (15, lay.copy(hp=(0, 0, -4.2)), "out"), (21, lay, "smooth")],
            serves=f"DownBound{sfx}", category="down", fit=False, wind=18)
        add(f"DownDamage{sfx}", 16, [(0, lay), (2, lay.copy(tor=(sign * -14, 0, 0), fp=sign * 82, hp=(0, 0, -3.8), hd=(sign * -14, 0, 0), aL=(sign * 30, 50, 0, 40, 0), aR=(sign * 30, 50, 0, 40, 0), lL=(sign * 12, 8, 16, 0)), "fast"),
                                     (5, lay.copy(fp=sign * 79, hp=(0, 0, -3.9), hd=(sign * -6, 0, 0)), "out"), (15, lay, "smooth")], serves=f"DownDamage{sfx}", category="down", fit=False, wind=6)
        sit0 = lay.copy(fp=sign * 62, hp=(0, 0, -3.4), lL=(sign * 50, 6, 70, 0), lR=(sign * 50, 6, 70, 0), aL=(sign * 30, 30, 0, 80, 0), aR=(sign * 30, 30, 0, 80, 0), hd=(sign * 14, 0, 0))
        sit = lay.copy(fp=sign * 35, hp=(0, 0, -2.6), lL=(sign * 40, 6, 60, 0), lR=(sign * 40, 6, 60, 0), aL=(40, 30, 0, 50, 0), aR=(40, 30, 0, 50, 0))
        crouch = S(hp=(0, 0, -2.0), tor=(26, 0, 0), fl=(1.3, 0.2, 0, 0), fr=(1.3, -0.2, 0, 0))
        rise = S(hp=(0, 0, 0.12), tor=(2, 0, -14))
        add(f"DownStand{sfx}", 30, [(0, lay), (5, sit0, "in"), (11, sit, "smooth"), (17, extrap_pose(sit, crouch, 1.15), "smooth"), (23, crouch.copy(hp=(0, 0, -1.2), tor=(14, 0, -6)), "smooth"), (26, rise, "out"), (29, S(), "smooth")],
            serves=f"DownStand{sfx} (getup in place)", category="down", fit=False, wind=10)
        add(f"DownSpot{sfx}", 28, [(0, lay), (4, sit0, "in"), (9, sit.copy(fp=sign * 55), "smooth"), (14, crouch.copy(hp=(0, 0, -1.4)), "smooth"), (24, rise, "out"), (27, S(), "smooth")], serves=f"DownSpot{sfx}", category="down", fit=False, wind=10)
        # getup attack: sit up, sweep kick forward then back, stand
        k1 = crouch.copy(hp=(0, 0, -2.6), fl=(1.3, 0.4, 0, 0), fr=None, lR=(62, 0, 6, -30), tor=(30, 0, 14))
        k2 = crouch.copy(hp=(0, 0, -2.6), fr=(1.3, 0.2, 0, 0), fl=None, lL=(-60, 0, 6, 30), tor=(36, 0, -80), hy=-40)
        add(f"DownAttack{sfx}", 45, [(0, lay), (5, sit0, "in"), (10, sit, "smooth"), (14, crouch, "smooth"), (16, crouch.copy(tor=(34, 0, -10), hp=(0, 0, -2.4), aL=(-30, 30, 0, 60, 0), aR=(-30, 30, 0, 60, 0)), "in"),
                                    (18, k1, "fast"), (24, k1, "lin"), (30, k2, "fast"), (36, k2, "lin"), (41, S(hp=(0, 0, -0.6), tor=(14, 0, -6)), "smooth"), (44, S(), "smooth")], serves=f"DownAttack{sfx} (getup attack)", category="down", fit=False, wind=14)
        for dirn, dn in ((1, "Forward"), (-1, "Back")):
            g = roll_gen(dirn, 35, 14.0, start=lay)
            add(f"Down{dn}{sfx}", 35, gen=g, serves=f"Down{dn}{sfx} (getup roll)", category="down", fit=False, root_motion=True, wind=16, notes="root motion on `trans`: 14 units")
    add("Passive", 24, [(0, LAY(-1).copy(fp=-35, hp=(0, 0, -2.6))), (3, S(hp=(0, 0, -1.2), tor=(14, 0, 0), aL=(40, 60, 0, 40, 0), aR=(40, 60, 0, 40, 0)), "fast"),
                        (6, S(hp=(0, 0, -1.8), tor=(24, 0, 0), aL=(30, 70, 0, 30, 0), aR=(30, 70, 0, 30, 0)), "out"), (14, S(hp=(0, 0, -1.0), tor=(18, 0, -6)), "smooth"), (23, S(), "smooth")], serves="Passive (tech in place)", category="down", fit=False, wind=10)
    for sign, nm in ((1, "PassiveStandF"), (-1, "PassiveStandB")):
        add(nm, 30, gen=roll_gen(sign, 30, 14.0, start=S(hp=(0, 0, -1.4), tor=(16, 0, 0), aL=(40, 60, 0, 40, 0), aR=(40, 60, 0, 40, 0))), serves=f"{nm} (tech roll)", root_motion=True, category="roll", fit=False, wind=20, notes="root motion on `trans`: 14 units")
    # wall / ceiling tech: arrive on the surface (feet / hands), absorb with a crouch, push off
    wallp = P(fp=-20, hp=(0, 0, -0.5), aL=(130, 60, 0, 30, 0), aR=(130, 60, 0, 30, 0), lL=(-30, 6, 80, 30), lR=(60, 6, 40, 30), tor=(-8, 0, 0), fl=None, fr=None, cuL=0, cuR=0)
    wall_abs = wallp.copy(fp=-8, hp=(0, 0, -1.8), lL=(60, 6, 110, 20), lR=(70, 6, 100, 20), aL=(60, 40, 0, 70, 0), aR=(60, 40, 0, 70, 0), tor=(10, 0, 0), hd=(-6, 0, 0))
    add("PassiveWall", 24, [(0, AIR), (3, extrap_pose(AIR, wallp, 1.15), "fast"), (5, wallp, "out"), (9, wall_abs, "smooth"), (23, wall_abs.copy(aL=(80, 40, 0, 60, 0), aR=(80, 40, 0, 60, 0)), "smooth")], serves="PassiveWall (wall tech)", category="air", fit=False, wind=10)
    add("PassiveWallJump", 30, [(0, wall_abs), (3, wall_abs.copy(hp=(0, 0, -2.0), tor=(14, 0, 0)), "in"), (6, AIR.copy(lL=(-10, 4, 4, -50), lR=(-10, 4, 4, -50), aL=(160, 28, 0, 14, 0), aR=(160, 28, 0, 14, 0), tor=(-6, 0, 0)), "fast"), (14, AIR.copy(lL=(60, 6, 90, 10), lR=(40, 6, 70, 10)), "smooth"), (29, AIR, "smooth")], serves="PassiveWallJump", category="air", fit=False, wind=12)
    ceil_p = P(fp=180, aL=(70, 50, 0, 40, 0), aR=(70, 50, 0, 40, 0), lL=(30, 6, 70, 10), lR=(30, 6, 70, 10), fl=None, fr=None, cuL=0, cuR=0)
    ceil_abs = ceil_p.copy(fp=172, hp=(0, 0, -1.6), aL=(90, 40, 0, 90, 0), aR=(90, 40, 0, 90, 0), lL=(70, 6, 110, 10), lR=(70, 6, 110, 10))
    add("PassiveCeil", 22, [(0, AIR), (3, extrap_pose(AIR, ceil_p, 1.1), "fast"), (5, ceil_p, "out"), (9, ceil_abs, "smooth"), (15, ceil_abs.copy(fp=178), "smooth"), (21, AIR, "smooth")], serves="PassiveCeil", category="air", fit=False, wind=10)
    # ============================================================ shield break, dizzy
    def sbf(f):
        a = 2 * math.pi * f / 16
        return P(fp=-30 + 10 * math.sin(a), aL=(100 + 18 * math.sin(a - 0.8), 80, 0, 20 + 8 * math.sin(a - 1.4), 0), aR=(100 - 18 * math.sin(a - 0.8), 80, 0, 20 - 8 * math.sin(a - 1.4), 0),
                 lL=(30 + 8 * math.sin(a - 1), 12, 50, 10), lR=(20 - 8 * math.sin(a - 1), 12, 60, 10), fl=None, fr=None, cuL=0, cuR=0, hd=(-14 - 4 * math.sin(a - 1.2), 0, 6 * math.sin(a - 1.8)))
    add("ShieldBreakFly", 16, loop=True, gen=sbf, serves="ShieldBreakFly", category="air", fit=False, wind=50)
    add("ShieldBreakFall", 20, loop=True, gen=lambda f: P(fp=-10, tor=(10, 0, 0), aL=(40 + 12 * math.sin(2 * math.pi * f / 20 - 0.7), 70, 0, 20, 0), aR=(40 - 12 * math.sin(2 * math.pi * f / 20 - 0.7), 70, 0, 20, 0),
                                                         lL=(30, 10, 50, 10), lR=(20, 10, 60, 10), fl=None, fr=None, cuL=0, cuR=0, hd=(-20, 0, 10 * math.sin(2 * math.pi * f / 20 - 1.0))), serves="ShieldBreakFall", category="air", fit=False, wind=24)
    for sign, sfx in ((-1, "U"), (1, "D")):
        lay = LAY(sign)
        add(f"ShieldBreakDown{sfx}", 22, [(0, lay.copy(fp=sign * 35, hp=(0, 0, -2.2)), "in"), (5, lay.copy(aL=(sign * -30, 50, 0, 20, 0), aR=(sign * -30, 50, 0, 20, 0)), "fast"), (8, lay, "out"), (21, lay.copy(hd=(0, 0, 14)), "smooth")], serves=f"ShieldBreakDown{sfx}", category="down", fit=False, wind=10)
        add(f"ShieldBreakStand{sfx}", 40, [(0, lay), (14, lay.copy(fp=sign * 50, hp=(0, 0, -2.8), aL=(sign * 30, 30, 0, 80, 0), aR=(sign * 30, 30, 0, 80, 0)), "smooth"), (28, S(hp=(0, 0, -1.6), tor=(26, 0, 0), hd=(-14, 0, 10)), "smooth"), (34, S(hp=(0, 0, 0.1), tor=(4, 0, -14)), "out"), (39, S(), "smooth")], serves=f"ShieldBreakStand{sfx}", category="down", fit=False, wind=10)
    add("Furafura", 40, loop=True, gen=lambda f: S(tor=(10, 10 * math.sin(2 * math.pi * f / 40), 8 * math.sin(2 * math.pi * f / 40 + 1)), aL=(5 + 6 * math.sin(2 * math.pi * f / 40 + 0.6), 25, 0, 20, 0), aR=(5 - 6 * math.sin(2 * math.pi * f / 40 + 0.6), 25, 0, 20, 0), hd=(-12, 14 * math.sin(2 * math.pi * f / 40 + 2), 20 * math.sin(2 * math.pi * f / 40)), hp=(0.4 * math.sin(2 * math.pi * f / 40), 0, -0.4)), serves="Furafura (dizzy sway)", wind=8)
    # ============================================================ grabs: hold and throw handled in clips_moves; victim clips here
    # The victim: yanked into the hold (trunk first, limbs trailing), a struggle that pushes and twists, a pummel that snaps the head
    # and rings out (damped), a break-out shove, a hop out; dangling holds swing like pendulums; throws fling the body with the limbs behind.
    VB = P(fl=None, fr=None, lL=(20, 6, 20, 0), lR=(20, 6, 20, 0), aL=(40, 40, 0, 50, 0), aR=(40, 40, 0, 50, 0), hd=(-8, 0, 0), cuL=0, cuR=0)
    def captured_pose(low, **kw):
        return VB.copy(hp=(0, 0, -0.6 if low else 0), tor=(20 if low else 4, 0, 0), **kw)
    def pulled(name, low):
        end = captured_pose(low)
        start = VB.copy(tor=(-10, 0, 0), aL=(80, 60, 0, 20, 0), aR=(80, 60, 0, 20, 0), hd=(8, 0, 0), lL=(30, 8, 30, 10), lR=(10, 8, 40, 10), hp=(0, -0.8, 0.2))
        mid = end.copy(tor=(end.v["tor"][0] + 14, 0, 0), aL=(-24, 36, 0, 60, 0), aR=(-24, 36, 0, 60, 0), hd=(-18, 0, 0), hp=(0, 0.8, -0.9 if low else -0.4), lL=(40, 6, 40, 0), lR=(30, 6, 40, 0))
        add(name, 16, [(0, start), (5, mid, "fast"), (8, extrap_pose(start, mid, 1.12), "smooth"), (11, end.copy(tor=(end.v["tor"][0] - 3, 0, 0)), "smooth"), (15, end, "smooth")], serves=name + " (victim yanked into the hold)", category="victim", fit=False, wind=10)
    pulled("CapturePulledHi", False); pulled("CapturePulledLw", True)
    def wait_struggle(name, low, n=30):
        base = captured_pose(low)
        def g(f):
            a = 2 * math.pi * f / n * 2.0
            s, s2 = math.sin(a), math.sin(a - 0.9)
            return base.copy(tor=(base.v["tor"][0] + 5 * s, 3 * s2, 6 * s), hp=(0.3 * s2, 0, base.v["hp"][2] + 0.15 * abs(s)),
                             aL=(40 + 28 * s2, 40 + 10 * s, 0, 50 - 10 * s2, 0), aR=(40 - 28 * s2, 40 - 10 * s, 0, 50 + 10 * s2, 0),
                             lL=(20 + 8 * s2, 6, 20 - 8 * s2, 0), lR=(20 - 8 * s2, 6, 20 + 8 * s2, 0), hd=(-8 + 3 * s2, 5 * s, 6 * s2))
        add(name, n, loop=True, gen=g, serves=name + (" (victim struggle)" if not low else ""), category="victim", fit=False, wind=10)
    wait_struggle("CaptureWaitHi", False); wait_struggle("CaptureWaitLw", True)
    def cap_dmg(name, low):
        base = captured_pose(low)
        def g(f):
            d = math.exp(-f / 3.0); s = math.sin(f * 1.5)
            return base.copy(tor=(base.v["tor"][0] - 16 * d * (1 if f < 3 else s), 0, 4 * d * s), hd=(-8 - 22 * d * (1 if f < 3 else s), 0, 8 * d * s), hp=(0, -0.5 * d, base.v["hp"][2]),
                             aL=(40 + 30 * d, 50, 0, 50, 0), aR=(40 + 30 * d, 50, 0, 50, 0))
        add(name, 10, gen=g, serves=name + (" (pummeled)" if not low else ""), category="victim", fit=False, wind=10)
    cap_dmg("CaptureDamageHi", False); cap_dmg("CaptureDamageLw", True)
    add("CaptureCut", 18, [(0, captured_pose(False)), (3, AIR.copy(tor=(-18, 0, 0), aL=(80, 60, 0, 30, 0), aR=(80, 60, 0, 30, 0), hp=(0, -1.4, 0.3), hd=(8, 0, 0)), "fast"),
                           (8, AIR.copy(tor=(-10, 0, 0), lL=(60, 6, 40, 10), lR=(50, 6, 40, 10), hp=(0, -1.0, 0.5)), "out"), (12, S(hp=(0, 0, -0.9), tor=(16, 0, 0), aL=(50, 50, 0, 80, 0), aR=(40, 50, 0, 80, 0)), "smooth"), (17, S(), "smooth")],
        serves="CaptureCut (breaks out of the hold)", category="victim", fit=False, wind=10)
    add("CaptureJump", 20, [(0, AIR), (3, AIR.copy(lL=(80, 4, 110, 0), lR=(80, 4, 110, 0), hp=(0, 0, -0.5), tor=(18, 0, 0), aL=(-20, 30, 0, 60, 0), aR=(-20, 30, 0, 60, 0)), "in"),
                            (7, AIR.copy(lL=(0, 4, 8, -40), lR=(0, 4, 8, -40), hp=(0, 0, 1.2), tor=(-8, 0, 0), aL=(140, 30, 0, 20, 0), aR=(140, 30, 0, 20, 0)), "fast"), (19, AIR, "smooth")],
        serves="CaptureJump (hops out)", category="victim", fit=False, wind=10)
    def neck_g(f):
        a = 2 * math.pi * f / 24.0
        s, s2 = math.sin(a), math.sin(a - 1.0)
        return P(fp=-10 + 5 * s, aL=(70 + 10 * s2, 60 + 8 * s, 0, 40 + 10 * s2, 0), aR=(70 - 10 * s2, 60 - 8 * s, 0, 40 - 10 * s2, 0), lL=(10 + 6 * s2, 4, 10, 0), lR=(10 - 6 * s2, 4, 10, 0),
                 fl=None, fr=None, hd=(-18 + 3 * s2, 8 * s, 4 * s2), hp=(0, 0, 0.6 * s), tor=(2 * s2, 2 * s, 0))
    add("CaptureNeck", 24, loop=True, gen=neck_g, serves="CaptureNeck (dangling hold)", category="victim", fit=False)
    def foot_g(f):
        a = 2 * math.pi * f / 24.0
        s, s2 = math.sin(a), math.sin(a - 1.1)
        return P(fp=180 + 6 * s, aL=(60 + 14 * s2, 50 + 10 * s, 0, 30, 0), aR=(60 - 14 * s2, 50 - 10 * s, 0, 30, 0), lL=(10, 4, 10, 0), lR=(10, 4, 10, 0), fl=None, fr=None, hd=(0, 4 * s2, 8 * s2))
    add("CaptureFoot", 24, loop=True, gen=foot_g, serves="CaptureFoot (hung by the feet)", category="victim", fit=False)
    # thrown: the trunk takes the launch line first; the arms and legs stream behind (flail with a delay) and the body keeps turning
    for nm, fp in (("ThrownF", -40), ("ThrownB", 40), ("ThrownHi", -150), ("ThrownLw", 60)):
        t0 = P(fp=fp * 0.15, aL=(70, 60, 0, 30, 0), aR=(70, 60, 0, 30, 0), lL=(30, 8, 40, 10), lR=(20, 8, 50, 10), fl=None, fr=None, cuL=0, cuR=0, tor=(-6 * (1 if fp < 0 else -1), 0, 0))
        t1 = P(fp=fp * 1.18, aL=(110, 82, 0, 14, 0), aR=(110, 82, 0, 14, 0), lL=(10, 12, 20, 0), lR=(6, 12, 24, 0), fl=None, fr=None, cuL=0, cuR=0, hd=(-14, 0, 0))
        t2 = P(fp=fp * 1.02, aL=(90, 75, 0, 24, 0), aR=(90, 75, 0, 24, 0), lL=(44, 12, 64, 10), lR=(30, 12, 74, 10), fl=None, fr=None, cuL=0, cuR=0, hd=(-12, 0, 0))
        add(nm, 24, [(0, t0), (3, t1, "fast"), (8, t2, "out"), (23, t2.copy(fp=fp * 1.1, aL=(80, 78, 0, 30, 0), aR=(80, 78, 0, 30, 0)), "smooth")], serves=f"{nm} (flung by a throw)", category="victim", fit=False, wind=44)
    # ============================================================ misc reactions
    rb1 = S(tor=(-16, 0, 8), hp=(0, -1.0, -0.2), hd=(-14, 0, 0), aL=(70, 70, 0, 30, 0), aR=(70, 70, 0, 30, 0))
    add("Rebound", 24, [(0, S()), (2, extrap_pose(S(), rb1, 1.25), "fast"), (4, rb1, "out"), (10, rb1.copy(tor=(-14, 0, 6), aL=(60, 66, 0, 40, 0), aR=(60, 66, 0, 40, 0)), "smooth"), (17, S(hp=(0, 0, -0.5), tor=(14, 0, -10)), "smooth"), (23, S(), "smooth")], serves="Rebound (staggered by a clank)", wind=14)
    add("Pass", 18, [(0, S()), (3, S(hp=(0, 0, -0.5), tor=(10, 0, -10)), "in"), (6, S(hp=(0, 0, -1.8), tor=(22, 0, 0), aL=(30, 30, 0, 80, 0), aR=(30, 30, 0, 80, 0)), "smooth"), (12, S(hp=(0, 0, -0.9), tor=(14, 0, 0)), "smooth"), (17, S(hp=(0, 0, -0.4)), "smooth")], serves="Pass (drop through platform)", wind=8)
    def ott(f):
        a = 2 * math.pi * f / 15.0
        s, s2 = math.sin(a), math.sin(a - 1.2)
        return S(tor=(-14 + 3 * math.sin(2 * a - 0.6), 0, 0), hp=(0, -0.3, 0), aL=(100 + 40 * s, 60 + 8 * s2, 0, 20, 0), aR=(100 - 40 * s, 60 - 8 * s2, 0, 20, 0), hd=(-6 + 2 * s2, 0, 0), fl=(0.9, 1.6, 0, 20), fr=(0.9, -0.2, 0, 0))
    add("Ottotto", 30, loop=True, gen=ott, serves="Ottotto (teetering at an edge)", wind=18)
    # bounce off / stick to a wall or ceiling: spread-eagled impact (squash), then the rebound (reflect) or a slow sag (stop)
    wl = P(fp=-85, hp=(0, 0, -0.8), aL=(120, 80, 0, 10, 0), aR=(120, 80, 0, 10, 0), lL=(50, 20, 20, 0), lR=(50, 20, 20, 0), fl=None, fr=None, cuL=0, cuR=0)
    for nm in ("FlyReflectWall", "FlyReflectCeil", "StopWall", "StopCeil"):
        wall = "Wall" in nm
        stop = nm.startswith("Stop")
        f_imp = -85 if wall else 175
        imp = wl.copy(fp=f_imp, hp=(0, 0, -1.8), aL=(100, 95, 0, 8, 0), aR=(100, 95, 0, 8, 0), lL=(40, 28, 10, 0), lR=(40, 28, 10, 0), hd=(0, 0, 0))
        sq = wl.copy(fp=f_imp + (4 if wall else -4), hp=(0, 0, -1.2), aL=(110, 86, 0, 12, 0), aR=(110, 86, 0, 12, 0), lL=(50, 22, 22, 0), lR=(50, 22, 22, 0))
        if stop:
            end = wl.copy(fp=-60 if wall else 150, hp=(0, 0, -1.4))
            keys = [(0, AIR), (2, imp, "fast"), (4, sq, "out"), (9, wl.copy(fp=f_imp, hp=(0, 0, -1.5)), "smooth"), (19, end, "smooth")]
        else:
            out_ = AIR.copy(fp=(-20 if wall else 160), lL=(40, 8, 50, 10), lR=(30, 8, 60, 10), aL=(70, 60, 0, 40, 0), aR=(70, 60, 0, 40, 0))
            keys = [(0, AIR), (2, imp, "fast"), (4, sq, "out"), (7, extrap_pose(sq, out_, 0.45), "in"), (12, out_, "smooth"), (19, out_.copy(fp=(-35 if wall else 148)), "smooth")]
        add(nm, 20, keys, serves=f"{nm} (bounce / stick on a surface)", category="air", fit=False, wind=20)
    add("MissFoot", 20, [(0, AIR.copy(lL=(60, 6, 40, 10), lR=(60, 6, 40, 10))), (3, S(hp=(0, 0, -1.4), tor=(24, 0, 0), aL=(80, 60, 0, 30, 0), aR=(80, 60, 0, 30, 0)), "fast"),
                         (5, S(hp=(0, 0, -2.2), tor=(34, 0, 0), aL=(60, 60, 0, 30, 0), aR=(60, 60, 0, 30, 0)), "out"), (12, S(hp=(0, 0, -1.2), tor=(16, 0, 0)), "smooth"), (19, S(), "smooth")], serves="MissFoot (stumbling landing)", wind=10)
    # ============================================================ ledge (hands above the head; body hangs; root motion on climbs)
    hang = P(hp=(0, 0, 0.0), aL=(176, 14, 0, 8, 0), aR=(176, 14, 0, 8, 0), lL=(6, 6, 22, 0), lR=(-4, 6, 30, 0), tor=(-6, 0, 0), hd=(8, 0, 0), fl=None, fr=None, cuL=1, cuR=1)
    # catch: the body arrives with momentum, the hands take the ledge first, the hips and legs swing in and then rock back to rest
    add("CliffCatch", 14, [(0, AIR.copy(aL=(130, 30, 0, 30, 0), aR=(130, 30, 0, 30, 0), hd=(6, 0, 0))), (3, hang.copy(hp=(0, 0, -0.9), lL=(40, 6, 70, 0), lR=(30, 6, 60, 0), tor=(10, 0, 0)), "fast"),
                           (6, hang.copy(hp=(0, 0, -0.2), lL=(-8, 6, 10, 0), lR=(-16, 6, 14, 0), tor=(-12, 0, 0)), "out"), (9, hang.copy(hp=(0, 0, -0.35), lL=(14, 6, 30, 0), lR=(6, 6, 34, 0), tor=(-3, 0, 0)), "smooth"), (13, hang, "smooth")],
        serves="CliffCatch", category="ledge", fit=False, wind=6)
    def sway(f):
        a = 2 * math.pi * f / 60.0
        s, s2 = math.sin(a), math.sin(a - 0.9)
        return hang.copy(tor=(-6 + 1.4 * s, 1.2 * s2, 0), hp=(0, 0, 0.05 * math.sin(2 * a)), lL=(6 + 4 * s2, 6, 22 + 3 * s, 0), lR=(-4 - 4 * s2, 6, 30 - 3 * s, 0), hd=(8 + 1.5 * s2, 0, 2 * s))
    add("CliffWait", 60, loop=True, gen=sway, serves="CliffWait (hang)", category="ledge", fit=False, wind=6)
    def ledge_clip(name, n, keys, tpf, serves, wind=14):
        base = Clip(name, n, keys=[(float(k[0]), k[1], k[2] if len(k) > 2 else "smooth") for k in keys], fit=False)
        c = add(name, n, gen=lambda f: base.sample(f).copy(tp=tpf(f / (n - 1.0))), serves=serves, category="ledge", fit=False, root_motion=True, wind=wind)
        return c
    def cl(x): return 0.0 if x < 0 else 1.0 if x > 1 else x
    pull = hang.copy(aL=(150, 30, 0, 100, 0), aR=(150, 30, 0, 100, 0), tor=(10, 0, 0), hp=(0, 0, 0.5), lL=(30, 6, 60, 0), lR=(20, 6, 60, 0))
    over = P(hp=(0, 0, -1.2), aL=(40, 40, 0, 70, 0), aR=(40, 40, 0, 70, 0), tor=(34, 0, 0), lL=(95, 6, 120, 0), lR=(40, 6, 90, 0), fl=None, fr=None, hd=(-14, 0, 0))
    stand_c = S(hp=(0, 0, -1.6), tor=(26, 0, 0), fl=(1.2, 0.2, 0, 0), fr=(1.2, -0.2, 0, 0))
    def climb(name, n, up, fwd):
        keys = [(0, hang), (int(n * 0.12), hang.copy(hp=(0, 0, -0.7), lL=(-14, 6, 40, 0), lR=(-20, 6, 44, 0), tor=(-10, 0, 0)), "in"), (int(n * 0.38), pull, "smooth"), (int(n * 0.55), over, "smooth"),
                (int(n * 0.74), extrap_pose(over, stand_c, 1.1), "smooth"), (int(n * 0.88), S(hp=(0, 0, -0.4), tor=(12, 0, -8)), "smooth"), (n - 1, S(), "smooth")]
        ledge_clip(name, n, keys, lambda u: (0, fwd * sm(cl((u - 0.42) / 0.36)), up * sm(cl((u - 0.10) / 0.45))),
                   f"{name} (root motion: +{up} up, +{fwd} forward over the clip)")
    climb("CliffClimbSlow", 60, 9.0, 4.5); climb("CliffClimbQuick", 40, 9.0, 4.5)
    def cliff_attack(name, n):
        strike = S(tor=(30, 0, 44), hy=26, aR=(96, 4, 0, 4, 0), aL=(-30, 30, 0, 60, 0), hp=(0, 1.2, -1.2), fl=(1.0, 2.6, 0, 0), fr=(1.0, -1.4, 0.3, 15))
        wnd = S(tor=(26, 0, -30), hy=-16, aR=(-40, 30, 0, 100, 0), aL=(60, 20, 0, 80, 0), hp=(0, 0, -1.7), fl=(1.3, 0.4, 0, 0), fr=(1.3, -0.4, 0, 0))
        keys = [(0, hang), (int(n * 0.12), hang.copy(hp=(0, 0, -0.7), lL=(-14, 6, 40, 0), lR=(-20, 6, 44, 0), tor=(-10, 0, 0)), "in"), (int(n * 0.32), pull, "smooth"), (int(n * 0.5), stand_c, "smooth"),
                (int(n * 0.58), wnd, "smooth"), (int(n * 0.65), extrap_pose(wnd, strike, 1.06), "fast"), (int(n * 0.69), strike, "out"), (int(n * 0.8), strike, "lin"), (int(n * 0.9), S(hp=(0, 0, -0.5), tor=(12, 0, -6)), "smooth"), (n - 1, S(), "smooth")]
        ledge_clip(name, n, keys, lambda u: (0, 6.0 * sm(cl((u - 0.30) / 0.25)), 9.0 * sm(cl((u - 0.10) / 0.32))), f"{name} (ledge attack; root motion +9 up, +6 forward)")
    cliff_attack("CliffAttackSlow", 70); cliff_attack("CliffAttackQuick", 50)
    def cliff_roll(name, n):
        rg_ = roll_gen(1, n, 14.0, start=pull)
        def g(f, n=n):
            u = f / (n - 1.0)
            if u < 0.25:
                w = u / 0.25
                q = lerp_pose(hang, hang.copy(hp=(0, 0, -0.7), lL=(-14, 6, 40, 0), lR=(-20, 6, 44, 0), tor=(-10, 0, 0)), sm(min(1.0, w * 3.0))) if w < 0.34 else lerp_pose(hang.copy(hp=(0, 0, -0.7), lL=(-14, 6, 40, 0), lR=(-20, 6, 44, 0), tor=(-10, 0, 0)), pull, sm((w - 0.34) / 0.66))
                return q.copy(tp=(0, 0, 9.0 * sm(cl((u - 0.05) / 0.2)) * 0.9))
            q = rg_((u - 0.25) / 0.75 * (n - 1))
            tpq = q.v["tp"]
            return q.copy(tp=(0, tpq[1], 9.0 * sm(cl((u - 0.05) / 0.2)) * 0.9 + 0.1 * 9.0 * sm(cl((u - 0.25) / 0.1))))
        add(name, n, gen=g, serves=f"{name} (ledge roll onto the stage; root motion +9 up, +14 forward)", category="ledge", fit=False, root_motion=True, wind=20)
    cliff_roll("CliffEscapeSlow", 70); cliff_roll("CliffEscapeQuick", 50)
    for nm, n, extra in (("CliffJumpSlow1", 30, 0), ("CliffJumpQuick1", 22, 0)):
        add(nm, n, [(0, hang), (int(n * 0.2), hang.copy(hp=(0, 0, -0.9), lL=(-14, 6, 40, 0), lR=(-20, 6, 44, 0), tor=(-8, 0, 0)), "in"), (int(n * 0.45), hang.copy(hp=(0, 0, -1.8), aL=(60, 30, 0, 100, 0), aR=(60, 30, 0, 100, 0), tor=(26, 0, 0), lL=(60, 6, 100, 0), lR=(60, 6, 100, 0)), "smooth"),
                    (n - 1, AIR.copy(lL=(-10, 4, 4, -50), lR=(-10, 4, 4, -50), aL=(160, 28, 0, 14, 0), aR=(160, 28, 0, 14, 0)), "fast")], serves=nm, category="ledge", fit=False, wind=14)
    for nm, n in (("CliffJumpSlow2", 36), ("CliffJumpQuick2", 30)):
        add(nm, n, [(0, AIR.copy(lL=(-10, 4, 4, -50), lR=(-10, 4, 4, -50), aL=(160, 28, 0, 14, 0), aR=(160, 28, 0, 14, 0))), (12, AIR.copy(lL=(70, 6, 90, 10), lR=(55, 6, 80, 10)), "smooth"), (n - 1, AIR, "smooth")], serves=nm + " (air part of the ledge jump)", category="air", fit=False, wind=-10)
    # ============================================================ items (right hand socket)
    hold_i = S(aR=(70, 14, 0, 90, 0), cuR=0.9)
    # pick up a light item: lean down on the planted front foot, the free arm back for balance, the fist closes on the item
    # (frame 8), then the whole body straightens with the item
    lg_reach = S(hp=(0, 0, -2.0), tor=(44, 0, 0), aR=(46, 14, 0, 12, 0), aL=(-34, 30, 0, 40, 0), cuR=0.0, fl=(1.3, 1.0, 0, 0), fr=(1.3, -0.9, 0.2, 0), hd=(-12, 0, 6))
    add("LightGet", 14, [(0, S()), (3, S(hp=(0, 0, -1.0), tor=(24, 0, 0), aR=(30, 14, 0, 50, 0), aL=(-10, 30, 0, 70, 0), cuR=0.0, fl=(1.1, 0.6, 0, 0), fr=(1.1, -0.6, 0, 0)), "in"), (6, lg_reach, "out"),
                         (8, lg_reach.copy(cuR=1.0), "lin"), (11, S(hp=(0, 0, -0.8), tor=(22, 0, 0), aR=(50, 18, 0, 60, 0), cuR=1.0), "smooth"), (13, hold_i, "smooth")], serves="LightGet (pick up a light item)", wind=4)
    hv_low = S(hp=(0, 0, -2.5), tor=(46, 0, 0), aL=(60, 20, 0, 20, 0), aR=(60, 20, 0, 20, 0), cuL=0, cuR=0, fl=(1.4, 0.8, 0, 0), fr=(1.4, -0.8, 0, 0), hd=(-12, 0, 0))
    add("HeavyGet", 24, [(0, S()), (3, S(hp=(0, 0, -1.2), tor=(26, 0, 0), aL=(40, 24, 0, 80, 0), aR=(40, 24, 0, 80, 0), fl=(1.2, 0.6, 0, 0), fr=(1.2, -0.6, 0, 0)), "in"), (7, hv_low, "out"), (11, hv_low.copy(cuL=1, cuR=1, aL=(56, 20, 0, 36, 0), aR=(56, 20, 0, 36, 0)), "lin"),
                         (17, S(hp=(0, 0, -1.4), tor=(26, 0, 0), aL=(70, 24, 0, 70, 0), aR=(70, 24, 0, 70, 0), cuL=1, cuR=1), "smooth"), (21, S(hp=(0, 0, 0.1), tor=(-6, 0, 0), aL=(110, 24, 0, 80, 0), aR=(110, 24, 0, 80, 0), cuL=1, cuR=1), "out"), (23, S(aL=(100, 24, 0, 80, 0), aR=(100, 24, 0, 80, 0), cuL=1, cuR=1), "smooth")],
        serves="HeavyGet (lift a heavy item)", wind=4)
    def throw(name, n, wind_pose, rel_pose, rel, serves):
        add(name, n, [(0, hold_i), (rel - 4, wind_pose, "smooth"), (rel, rel_pose, "fast"), (n - 1, S(), "smooth")], serves=serves, hit=[rel], wind=14)
    throw("LightThrowF", 24, S(aR=(-40, 24, 0, 120, 0), tor=(10, 0, -46), hy=-24), S(aR=(120, 6, 0, 6, 0), tor=(20, 0, 40), hy=24, cuR=0, hp=(0, 1.0, -0.4), fl=(0.9, 2.2, 0, 0)), 9, "LightThrowF")
    throw("LightThrowB", 26, S(aR=(60, 20, 0, 60, 0), tor=(8, 0, 20)), S(aR=(100, 0, 0, 6, 0), tor=(10, 0, -102), hy=-68, cuR=0), 12, "LightThrowB")
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
    add("ItemSwingDash", 30, [(0, S(tor=(26, 0, 0), aR=(-30, 20, 0, 80, 0))), (7, S(aR=(110, 8, 0, 8, 0), tor=(34, 0, 30), hp=(0, 1.2, -0.6), fl=(1.0, 2.0, 0, 0), fr=(1.0, -1.7, 0.3, 20)), "fast"), (13, S(aR=(110, 8, 0, 8, 0), tor=(34, 0, 30), hp=(0, 1.2, -0.6), fl=(1.0, 2.0, 0, 0), fr=(1.0, -1.7, 0.3, 20)), "lin"), (29, S(), "smooth")], serves="ItemSwingDash", hit=[7], wind=40)
    shoot = S(aR=(95, 6, 0, 6, 0), tor=(8, 0, 20), hy=10, cuR=0.8)
    add("ItemShoot", 22, [(0, hold_i), (3, shoot, "fast"), (5, shoot.copy(hp=(0, -0.5, 0), aR=(105, 6, 0, 10, 0)), "out"), (21, hold_i, "smooth")], serves="ItemShoot (ray gun / flower style shot; also the scope rows)", hit=[3], wind=8)
    # carrying a heavy item overhead: a steady strain (tiny tremor in the arms, the legs taking the weight, a slow counter-sway of the trunk)
    def liftw(f):
        a = 2 * math.pi * f / 40.0
        tr = math.sin(2 * math.pi * f / 6.7)
        return S(aL=(176 + 0.6 * tr, 24, 0, 6, 0), aR=(176 - 0.6 * tr, 24, 0, 6, 0), tor=(-4 + math.sin(a), 0.8 * math.sin(a + 0.8), 0), cuL=0.1, cuR=0.1, hp=(0.1 * math.sin(a + 0.8), 0, -0.45 + 0.08 * math.sin(a)), hd=(4 + 0.6 * math.sin(a - 0.8), 0, 0))
    add("LiftWait", 40, loop=True, gen=liftw, serves="LiftWait (carrying a heavy item overhead)", wind=5)
    lw_arms = lambda p, ph: p.copy(aL=(176, 24, 0, 6, 0), aR=(176, 24, 0, 6, 0), cuL=0.1, cuR=0.1)
    add_gait("LiftWalk", 28, 2, 0.60, 0.38, arm=0, elbow0=6, elbow1=0, lean=-3, dip=0.4, heel_t=2.5, toe_t=3.0, phi_h=14, phi_t=-28, lift=0.6, xc=0.1, out=0.35, twist=3, sway=0.35,
             carry=lw_arms, serves="LiftWalk", wind=8)
    # ============================================================ presentation: entry, taunts, wins (a courier: satchel and scarf)
    # poses: the satchel hangs at the right hip (back of the body), so "tapping the satchel" is the right hand dropping behind the hip;
    # a salute is a hand to the helmet; a delivery is the arm thrust out like handing over a parcel
    tap = S(aR=(-24, 26, 0, 74, 0), tor=(10, 0, -24), hy=-14, hd=(6, 0, -14))
    salute = S(aR=(140, 58, 0, 128, 0), tor=(-4, 0, -22), hy=-12, hd=(2, 0, 10), cuR=0.0)
    deliver = S(aR=(100, 4, 0, 6, 0), cuR=0.0, tor=(16, 0, 28), hy=14, hp=(0, 1.0, -0.8), fl=(1.0, 1.8, 0, 0), fr=(1.0, -1.0, 0.2, 10), hd=(-6, 0, -8))
    crouchE = S(hp=(0, 0, -2.4), tor=(40, 0, 0), aL=(-40, 30, 0, 40, 0), aR=(-40, 30, 0, 40, 0), hd=(-20, 0, 0), fl=(1.2, 0.4, 0, 0), fr=(1.2, -0.4, 0, 0))
    # entry: coiled low, a spring (stretch) with a hop, a skid landing, the courier salutes
    spring = S(hp=(0, 0, 0.5), aL=(170, 40, 0, 10, 0), aR=(170, 40, 0, 10, 0), tor=(-12, 0, 0), hd=(8, 0, 0), fl=(0.8, 0.1, 1.2, -45), fr=(0.8, -0.1, 1.2, -45))
    add("EntryStart", 60, [(0, crouchE), (12, crouchE.copy(hp=(0, 0, -2.6), tor=(42, 0, 0)), "smooth"), (19, crouchE.copy(hp=(0, 0, -2.9), tor=(44, 0, 0), aL=(-55, 30, 0, 30, 0), aR=(-55, 30, 0, 30, 0)), "in"),
                           (24, spring, "fast"), (28, spring.copy(hp=(0, 0, 1.2), fl=(0.8, 0.1, 2.0, -45), fr=(0.8, -0.1, 2.0, -45)), "out"), (34, S(hp=(0, 0, -1.8), tor=(28, 0, -8), aL=(40, 60, 0, 40, 0), aR=(40, 60, 0, 40, 0)), "in"),
                           (38, S(hp=(0, 0, -2.0), tor=(30, 0, -8), aL=(40, 60, 0, 40, 0), aR=(40, 60, 0, 40, 0)), "out"), (46, salute, "smooth"), (53, salute, "lin"), (59, S(), "smooth")],
        serves="EntryStart / Entry (spawn pose: crouch, spring, point)", wind=12)
    def rebirth(f):
        a = 2 * math.pi * f / 40.0
        s, s2 = math.sin(a), math.sin(a - 1.0)
        return S(aL=(10 + 6 * s2, 70 + 4 * s, 0, 10, 0), aR=(10 + 6 * s2, 70 - 4 * s, 0, 10, 0), tor=(0, 1.0 * s, 0), hy=0, hd=(-2 + 2 * s2, 0, 5 * math.sin(a * 0.5)), hp=(0, 0, 0.3 * math.sin(a)))
    add("Rebirth", 40, loop=True, gen=rebirth, serves="Rebirth / RebirthWait (standing on the revival platform)", wind=6)
    # AppealSR: pat the satchel twice (checking the parcel), then hand it over with a flourish and hold
    add("AppealSR", 70, [(0, S()), (6, S(hp=(0, 0, -0.5), tor=(14, 0, -10)), "in"), (11, tap, "fast"), (14, tap.copy(aR=(-14, 26, 0, 80, 0)), "smooth"), (17, tap, "smooth"), (20, tap.copy(aR=(-14, 26, 0, 80, 0)), "smooth"), (23, tap, "smooth"),
                         (30, S(hp=(0, 0, -1.0), tor=(24, 0, -34), hy=-16, aR=(-50, 40, 0, 90, 0)), "in"), (35, extrap_pose(S(tor=(14, 0, -10)), deliver, 1.12), "fast"), (38, deliver, "out"), (52, deliver.copy(aR=(104, 4, 0, 6, 0), hd=(-8, 0, -10)), "smooth"),
                         (60, S(hp=(0, 0, -0.4), tor=(12, 0, -8)), "smooth"), (69, S(), "smooth")], serves="AppealSR (taunt: check the satchel, hand over the parcel)", wind=10)
    # AppealSL: a full spin that throws the scarf out, then a salute (a taunt that shows off the scarf)
    spin_w = S(hp=(0, 0, -1.2), tor=(18, 0, 18), hy=10, aL=(30, 40, 0, 80, 0), aR=(30, 40, 0, 80, 0))
    whip = S(hp=(0, 0, -0.5), tor=(10, 0, -100), hy=-70, aL=(30, 70, 0, 40, 0), aR=(30, 70, 0, 40, 0), hd=(0, 0, -30))
    add("AppealSL", 70, [(0, S()), (7, spin_w, "in"), (22, extrap_pose(spin_w, whip, 1.08), "fast"), (27, whip, "out"), (34, whip.copy(tor=(8, 0, -92), hy=-62, hd=(0, 0, -34)), "smooth"),
                         (42, extrap_pose(S(), salute, 1.1), "smooth"), (47, salute, "out"), (58, salute, "lin"), (64, S(hp=(0, 0, -0.3)), "smooth"), (69, S(), "smooth")], serves="AppealSL (taunt: whip turn flares the scarf, salute)", wind=10)
    # results: cheers with hops (win 1), a confident lean with a satchel pat (win 2), a back flip into a point (win 3), a slump (lose)
    up = S(aL=(176, 30, 0, 8, 0), aR=(176, 30, 0, 8, 0), tor=(-14, 0, 0), hd=(10, 0, 0))
    hop1 = up.copy(hp=(0, 0, 1.4), fl=(0.9, 0.2, 1.8, -40), fr=(0.9, -0.2, 1.8, -40))
    sq1 = S(hp=(0, 0, -1.9), tor=(30, 0, 0), aL=(-40, 30, 0, 60, 0), aR=(-40, 30, 0, 60, 0), hd=(-6, 0, 0))
    add("Win1", 90, [(0, S()), (10, sq1.copy(hp=(0, 0, -1.2)), "in"), (14, sq1, "out"), (21, hop1, "fast"), (27, up.copy(hp=(0, 0, 0.1)), "in"), (33, sq1.copy(hp=(0, 0, -1.2), aL=(120, 30, 0, 40, 0), aR=(120, 30, 0, 40, 0)), "out"), (40, hop1, "fast"),
                     (47, up.copy(hp=(0, 0, 0.1)), "in"), (53, up, "smooth"), (70, up.copy(tor=(-10, 0, -8), hd=(8, 0, 8)), "smooth"), (89, up, "smooth")], serves="Win1 (results: both fists up, two hops)", category="results", wind=10)
    cross = S(tor=(-6, 0, 0), hy=0, aL=(70, 6, -50, 118, 0), aR=(70, 6, 50, 118, 0), hd=(0, 0, 14), fl=(0.9, 0.2, 0, 0), fr=(0.9, -0.2, 0, 0))
    add("Win2", 90, [(0, S()), (14, S(tor=(4, 0, 0), hy=0, aL=(60, 20, 0, 130, 0), aR=(60, 20, 0, 130, 0), hd=(-4, 0, -20), fl=(0.9, 0.2, 0, 0), fr=(0.9, -0.2, 0, 0)), "in"), (30, extrap_pose(S(), cross, 1.08), "smooth"), (36, cross, "out"),
                     (52, cross.copy(hd=(-2, 0, -10), tor=(-4, 0, 6), hp=(0.6, 0, -0.1)), "smooth"), (66, cross.copy(hd=(2, 0, 16), hp=(-0.4, 0, 0)), "smooth"), (89, cross, "smooth")], serves="Win2 (results: arms crossed, a confident sway)", category="results", wind=8)
    def win3(f):
        if f < 8:
            u = f / 8.0
            return S(hp=(0, 0, -2.4 * sm(u)), tor=(34 * sm(u), 0, 0), aL=(-45 * sm(u), 30, 0, 40, 0), aR=(-45 * sm(u), 30, 0, 40, 0))
        if f < 32:
            t = (f - 8) / 24.0
            tk = math.sin(math.pi * t) ** 0.6
            e = t * t * (3 - 2 * t) * 0.85 + t * 0.15
            return lerp_pose(AIR.copy(aL=(150, 30, 0, 20, 0), aR=(150, 30, 0, 20, 0)), TUCK, tk).copy(fp=-360 * e, hp=(0, 0, 4.5 * math.sin(math.pi * t)))
        if f < 36: return lerp_pose(S(hp=(0, 0, -2.2), tor=(30, 0, 0)), S(hp=(0, 0, -1.0), tor=(18, 0, 0)), sm((f - 32) / 4.0))
        if f < 44: return lerp_pose(S(hp=(0, 0, -1.0), tor=(18, 0, 0)), S(hp=(0, 0, 0.1), tor=(-4, 0, -10)), sm((f - 36) / 8.0))
        pt = S(tor=(2, 0, -30), hy=-16, aR=(176, 18, 0, 8, 0), aL=(35, 20, 0, 100, 0), hd=(2, 0, 10))
        if f < 56: return lerp_pose(S(hp=(0, 0, 0.1), tor=(-4, 0, -10)), extrap_pose(S(), pt, 1.08), sm((f - 44) / 12.0))
        return lerp_pose(extrap_pose(S(), pt, 1.08), pt, sm((f - 56) / 6.0)) if f < 62 else pt
    add("Win3", 90, gen=win3, serves="Win3 (results: backflip into a point)", category="results", fit=True, wind=10)
    def lose(f):
        a = 2 * math.pi * f / 60.0
        s = math.sin(a); s2 = math.sin(a - 0.8)
        return S(hp=(0, 0, -0.9 - 0.12 * s), tor=(30 + 3 * s, 0, 0), hd=(-34 + 4 * s2, 0, 9 * math.sin(a * 2)), aL=(18 + 4 * s2, 14, 0, 14, 0), aR=(18 - 4 * s2, 14, 0, 14, 0),
                 fl=(0.9, 0.2, 0, 0), fr=(0.9, -0.2, 0, 0), cuL=0.4, cuR=0.4)
    add("Lose", 60, loop=True, gen=lose, serves="Lose (results: slumped, a long sigh)", category="results", wind=3)
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
