"""The Striker's move set as clips (frame counts and hit frames from vanilla-striker/moves/*.genoasm).

Timing contract: a clip is authored at logic rate 1.0 (60 fps) with the hit pose on the first hit frame of the
move script (script frame N = clip frame N); the total length is the script's iasa/last wait, plus a short tail
where the script is silent. The Striker's ANIM_RATE overlays (1.2-1.45) were tuned for the donor's longer clips:
with these clips set the rate to 1.0.
"""
from anim_lib import P, Pose, Clip, lerp_pose, extrap_pose

# ---------------------------------------------------------------- shared poses
GL = (55, 18, 0, 105, 0)       # lead (left) fist guard
GR = (35, 10, 0, 118, 0)       # rear (right) fist guard
STAND = P(tor=(8, 0, -14), hy=-8, hd=(-3, 0, 6), aL=GL, aR=GR, fl=(0.75, 0.9, 0, 0), fr=(0.75, -0.7, 0, 0))

def spin(deg, lean=0.0, side=0.0):
    return dict(hy=deg * 0.40, tor=(lean, side, deg * 0.60))

def S(**kw):
    return STAND.copy(**kw)

CLIPS = []

def polish(keys, hit, n, over=1.07):
    """Animation principles added to a keyed strike without moving its hit frame or its length:
    anticipation (a small counter-move before the first real key), the strike overshoots on the hit frame and settles two frames
    later (follow-through), and the recovery passes through a small dip and overshoot past the rest pose before it settles."""
    ks = sorted([(float(f), p, e) for (f, p, e) in keys], key=lambda k: k[0])
    h = float(hit)
    idx = [i for i, k in enumerate(ks) if k[0] == h]
    # 1. overshoot on the hit frame, settle after it
    if idx and idx[0] > 0 and idx[0] + 1 < len(ks) and ks[idx[0] + 1][0] >= h + 3:
        i = idx[0]
        prev, cur = ks[i - 1][1], ks[i][1]
        settle = (h + 2.0, cur, "out")
        ks[i] = (h, extrap_pose(prev, cur, over), ks[i][2] if ks[i][2] != "smooth" else "fast")
        ks.insert(i + 1, settle)
    # 2. anticipation: a counter-move in the frame before the first real key when there is room for it
    if len(ks) > 2 and ks[1][0] >= 3 and ks[1][0] < h:
        fa = min(ks[1][0] - 1.0, 2.0)
        ks.insert(1, (fa, extrap_pose(ks[0][1], ks[1][1], -0.14), "out"))
    # 3. recovery: dip and overshoot on the way back to the final pose
    last = ks[-1]
    j = len(ks) - 2
    while j > 0 and ks[j][0] > last[0] - 5: j -= 1
    hold = ks[j]
    gap = last[0] - hold[0]
    if hold[0] > h and gap >= 6:
        dip = lerp_pose(hold[1], last[1], 0.7).add(hp=(0, 0, -0.25))
        ks.insert(j + 1, (hold[0] + 0.5 * gap, dip, "smooth"))
        ks.insert(j + 2, (hold[0] + 0.83 * gap, extrap_pose(hold[1], last[1], 1.05), "smooth"))
    return ks

def add(name, n, keys=None, **kw):
    kw.setdefault("category", "move")
    keys = [(float(f), p, e) for (f, p, e) in (keys or [])]
    if keys and kw.get("hit") and not kw.get("loop") and kw.pop("polish", True):
        keys = polish(keys, kw["hit"][0], n)
    kw.pop("polish", None)
    c = Clip(name, n, keys=keys, **kw)
    CLIPS.append(c)
    return c

def K(*items):
    out = []
    for it in items:
        f, p = it[0], it[1]
        e = it[2] if len(it) > 2 else "smooth"
        out.append((f, p, e))
    return out

def register():
    CLIPS.clear()
    # ------------------------------------------------------------ jabs
    j1 = S(aL=(90, 6, 0, 6, 0), tor=(12, 0, -32), hy=-20, fl=(0.75, 1.5, 0, 0), hp=(0, 0.6, -0.1), hd=(-3, 0, 14))
    add("Attack11", 13, K((0, S()), (1, S(aL=(48, 20, 0, 118, 0), tor=(8, 0, -8), hy=-2), "in"), (3, j1, "fast"), (6, j1, "lin"), (13, S(), "smooth")),
        serves="Attack11 (jab 1)", hit=[3])
    j2 = S(aR=(90, 6, 0, 6, 0), tor=(12, 0, 30), hy=18, fl=(0.75, 1.2, 0, 0), fr=(0.75, -0.2, 0, 0), hp=(0, 0.7, -0.15), hd=(-3, 0, -10))
    add("Attack12", 14, K((0, S()), (1, S(aR=(32, 8, 0, 130, 0), tor=(8, 0, -22), hy=-14), "in"), (3, j2, "fast"), (6, j2, "lin"), (14, S(), "smooth")),
        serves="Attack12 (jab 2)", hit=[3])
    j3 = S(aR=(125, 14, 0, 55, -25), aL=(25, 20, 0, 110, 0), tor=(-6, 0, 28), hy=20, fl=(0.75, 2.0, 0, 0), fr=(0.8, -0.8, 0, 0), hp=(0, 0.9, 0.2), hd=(-8, 0, -8))
    add("Attack13", 20, K((0, S()), (3, S(aR=(10, 12, 0, 120, 0), tor=(20, 0, -26), hy=-18, hp=(0, 0, -0.9)), "in"), (5, j3, "fast"), (9, j3, "lin"), (20, S(), "smooth")),
        serves="Attack13 (jab 3, rising hook)", hit=[5])
    # rapid jab (loop) as a placeholder built from jab 1/2
    rl = S(aL=(80, 8, 0, 20, 0), tor=(12, 0, -26), hy=-14)
    rr = S(aR=(80, 8, 0, 20, 0), tor=(12, 0, 22), hy=12)
    add("Attack100Loop", 8, K((0, rl, "fast"), (4, rr, "fast")), loop=True, serves="Attack100Loop (rapid jab; placeholder cycle)", status="placeholder")
    add("Attack100Start", 6, K((0, S()), (5, rl, "out")), serves="Attack100Start (placeholder)", status="placeholder")
    add("Attack100End", 10, K((0, rl), (9, S(), "smooth")), serves="Attack100End (placeholder)", status="placeholder")
    # ------------------------------------------------------------ dash attack: shoulder lunge, slide 10-22
    da = S(tor=(32, 0, -14), hy=-8, aL=(78, 10, 0, 20, 0), aR=(-70, 28, 0, 50, 0), fl=(0.9, 2.8, 0, 0), fr=(0.9, -3.2, 0.6, 35),
           hp=(0, 1.4, -1.1), hd=(-20, 0, 14))
    da2 = da.copy(fr=(0.9, -3.4, 1.4, 40))
    add("AttackDash", 30, K((0, S(tor=(30, 0, -20), aL=(-30, 20, 0, 80, 0), aR=(-40, 25, 0, 80, 0)), "smooth"), (4, S(tor=(20, 0, -10), hp=(0, 0, -0.6)), "in"),
                            (6, da, "fast"), (10, da, "lin"), (16, da2, "lin"), (22, da2, "lin"), (30, S(), "smooth")),
        serves="AttackDash (shoulder lunge)", hit=[6, 10], root_motion=False)
    # ------------------------------------------------------------ forward tilts: front kick, three heights
    def ftilt(h, name):
        kick = S(fr=None, lR=(h, 0, 6, -12), aL=(30, 28, 0, 70, 0), aR=(-25, 40, 0, 40, 0), tor=(-14, 0, 12), hy=6, hp=(0, -0.3, 0), hd=(-3, 0, 0))
        add(name, 17, K((0, S()), (3, S(fr=None, lR=(h * 0.3, 0, 90, 0), tor=(-6, 0, 4)), "in"), (6, kick, "fast"), (9, kick, "lin"), (17, S(), "smooth")),
            serves=f"{name} (forward tilt)", hit=[6])
    ftilt(100, "AttackS3Hi"); ftilt(78, "AttackS3S"); ftilt(52, "AttackS3Lw")
    # ------------------------------------------------------------ up tilt: double-arm overhead sweep, rehit 5-17
    ut_low = S(aL=(20, 30, 0, 60, 0), aR=(-30, 20, 0, 30, 0), tor=(22, 0, -20), hy=-10, hp=(0, 0, -0.9))
    ut_hi = S(aL=(-30, 40, 0, 30, 0), aR=(150, 10, 0, 10, 0), tor=(-16, 0, 14), hy=8, hd=(10, 0, -8), hp=(0, 0, 0.1))
    ut_hi2 = ut_hi.copy(aR=(172, 30, 0, 10, 0), tor=(-22, 0, 20))
    add("AttackHi3", 23, K((0, S()), (2, ut_low, "in"), (5, ut_hi, "fast"), (11, ut_hi2, "smooth"), (17, ut_hi2, "lin"), (23, S(), "smooth")),
        serves="AttackHi3 (up tilt)", hit=[5, 17])
    # ------------------------------------------------------------ down tilt: low sweeping kick
    dt = S(fr=None, lR=(68, 0, 2, -30), hp=(0, -0.1, -1.5), tor=(18, 0, 10), aL=(-40, 60, 0, 30, 0), aR=(20, 70, 0, 30, 0), hd=(-12, 0, 0), fl=(1.0, 0.4, 0, 0))
    add("AttackLw3", 23, K((0, S()), (3, S(hp=(0, 0, -1.6), tor=(18, 0, -8), fr=None, lR=(10, 0, 70, 0)), "in"), (6, dt, "fast"), (10, dt, "lin"), (23, S(), "smooth")),
        serves="AttackLw3 (down tilt)", hit=[6])
    # ------------------------------------------------------------ smashes
    wind = S(aR=(-70, 24, 0, 100, 0), aL=(70, 10, 0, 40, 0), tor=(14, 0, -48), hy=-30, hp=(0, -0.4, -0.7), hd=(-5, 0, 22), fl=(0.9, 1.0, 0, 0), fr=(0.9, -1.0, 0, 0))
    def fsmash(name, arm, lean, kneel, hy_):
        hitp = S(aR=(arm, 4, 0, 4, 0), aL=(-30, 30, 0, 60, 0), tor=(lean, 0, 44), hy=hy_, hp=(0, 1.8, -kneel), hd=(-6, 0, -18),
                 fl=(0.9, 3.0, 0, 0), fr=(0.9, -1.4, 0.3, 15))
        add(name, 38, K((0, S()), (2, S(tor=(12, 0, -30), hy=-18, aR=(0, 20, 0, 120, 0)), "in"), (5, wind, "smooth"), (8, wind, "lin"), (12, wind.copy(tor=(16, 0, -54), hp=(0, 0.2, -0.9)), "in"),
                        (13, hitp, "fast"), (18, hitp, "lin"), (27, hitp.copy(aR=(arm - 20, 14, 0, 30, 0), tor=(lean * 0.7, 0, 30)), "smooth"), (38, S(), "smooth")),
            serves=f"{name} (forward smash; charge pose = frame 5)", hit=[13])
    fsmash("AttackS4S", 92, 26, 1.1, 26); fsmash("AttackS4Hi", 135, 6, 0.5, 20); fsmash("AttackS4Lw", 52, 38, 1.9, 30)
    # up smash: crouch-charge then a leaping double-handed uppercut, second hit at 20
    us_c = S(hp=(0, 0, -2.0), tor=(30, 0, 0), hy=0, aL=(-25, 30, 0, 30, 0), aR=(-25, 30, 0, 30, 0), hd=(-10, 0, 0), fl=(1.3, 0.2, 0, 0), fr=(1.3, -0.2, 0, 0))
    us_1 = S(hp=(0, 0, 0.9), tor=(-12, 0, 0), hy=0, aL=(138, 26, 0, 6, 0), aR=(150, 14, 0, 6, 0), hd=(14, 0, 0), fl=(0.9, 0.2, 1.6, -35), fr=(0.9, -0.2, 1.6, -35))
    us_2 = us_1.copy(aL=(150, 70, 0, 6, 0), aR=(170, 40, 0, 6, 0), hp=(0, 0, 1.1), tor=(-18, 0, 0), fl=(0.9, 0.2, 2.0, -40), fr=(0.9, -0.2, 2.0, -40))
    add("AttackHi4", 38, K((0, S()), (3, S(hp=(0, 0, -0.9), tor=(20, 0, 0)), "smooth"), (7, us_c, "smooth"), (9, us_c, "in"), (10, us_1, "fast"), (20, us_2, "smooth"), (24, us_2, "lin"), (38, S(), "smooth")),
        serves="AttackHi4 (up smash; charge pose = frame 7)", hit=[10, 20])
    # down smash: low sweep kick front (6) then spin to a rear kick (15)
    ds_c = S(hp=(0, 0, -1.8), tor=(26, 0, -10), aL=(40, 40, 0, 60, 0), aR=(30, 50, 0, 70, 0), fl=(1.3, 0.8, 0, 0), fr=(1.3, -0.8, 0, 0))
    ds_1 = S(fr=None, lR=(72, 0, 2, -35), hp=(0, 0.0, -1.7), tor=(22, 0, 12), aL=(-30, 70, 0, 30, 0), aR=(20, 76, 0, 30, 0), fl=(1.3, 0.5, 0, 0), hd=(-12, 0, -6))
    ds_2 = S(fl=None, lL=(-62, 0, 4, 40), fr=(1.3, -0.1, 0, 0), hp=(0, 0, -1.9), tor=(36, 0, -102), hy=-68, aL=(40, 60, 0, 40, 0), aR=(40, 60, 0, 40, 0), hd=(-6, 0, 0))
    add("AttackLw4", 34, K((0, S()), (3, ds_c, "smooth"), (4, ds_c, "in"), (6, ds_1, "fast"), (10, ds_1, "lin"), (12, ds_1.copy(tor=(30, 0, -90), lR=(40, 0, 30, -10)), "smooth"), (15, ds_2, "fast"), (20, ds_2, "lin"), (34, S(), "smooth")),
        serves="AttackLw4 (down smash: front then back)", hit=[6, 15])
    # ------------------------------------------------------------ aerials (FK legs, no planted feet)
    A0 = P(hp=(0, 0, 0), tor=(8, 0, -10), hd=(-3, 0, 4), aL=(35, 25, 0, 90, 0), aR=(35, 25, 0, 90, 0), lL=(40, 8, 60, 20), lR=(10, 8, 40, 20), fl=None, fr=None)
    def aadd(name, n, keys, **kw):
        return add(name, n, keys, **kw)
    nair = A0.copy(lL=(78, 20, 8, 10), lR=(-52, 20, 8, 20), aL=(30, 62, 0, 20, 0), aR=(100, 40, 0, 20, 0), tor=(-4, 0, 0), hy=0)
    aadd("AttackAirN", 40, K((0, A0), (2, A0.copy(lL=(70, 5, 100, 0), lR=(70, 5, 100, 0)), "in"), (4, nair, "fast"), (8, nair, "lin"), (30, nair.copy(lL=(30, 40, 30, 10), lR=(30, 40, 30, 10)), "smooth"), (40, A0, "smooth")),
         serves="AttackAirN (split-kick spin pose)", hit=[4, 8], category="air", fit=False)
    f_wind = A0.copy(aL=(175, 30, 0, 40, 0), aR=(175, 30, 0, 40, 0), tor=(-24, 0, 0), hd=(8, 0, 0), lL=(10, 5, 50, 10), lR=(10, 5, 50, 10))
    f_hit = A0.copy(aL=(95, 14, 0, 6, 0), aR=(95, 8, 0, 6, 0), tor=(40, 0, 0), hd=(-18, 0, 0), lL=(50, 5, 60, 10), lR=(40, 5, 70, 10), hp=(0, 0.4, 0))
    aadd("AttackAirF", 52, K((0, A0), (8, f_wind, "smooth"), (17, f_wind, "lin"), (19, f_hit, "fast"), (25, f_hit, "lin"), (38, f_hit.copy(tor=(20, 0, 0), aL=(60, 20, 0, 40, 0), aR=(60, 20, 0, 40, 0)), "smooth"), (52, A0, "smooth")),
         serves="AttackAirF (overhead double smash)", hit=[19], category="air", fit=False)
    b_hit = A0.copy(fr=None, lR=(-78, 4, 5, 30), lL=(30, 8, 90, 20), tor=(48, 0, 0), hd=(-30, 0, 12), aL=(70, 40, 0, 40, 0), aR=(70, 40, 0, 40, 0), hp=(0, -0.2, 0))
    aadd("AttackAirB", 28, K((0, A0), (4, A0.copy(tor=(26, 0, 0), lR=(-20, 4, 100, 30), hd=(-12, 0, 6)), "in"), (7, b_hit, "fast"), (14, b_hit.copy(lL=(-78, 4, 5, 30), lR=(30, 8, 90, 20)), "fast"), (28, A0, "smooth")),
         serves="AttackAirB (double back kick)", hit=[7, 14], category="air", fit=False)
    h_hit = A0.copy(lR=(126, 6, 4, -20), lL=(100, 6, 70, 10), tor=(-46, 0, 0), hd=(18, 0, 0), aL=(-10, 55, 0, 30, 0), aR=(-10, 55, 0, 30, 0))
    aadd("AttackAirHi", 25, K((0, A0), (2, A0.copy(lR=(60, 4, 100, 10), tor=(-12, 0, 0)), "in"), (5, h_hit, "fast"), (13, h_hit, "lin"), (25, A0, "smooth")),
         serves="AttackAirHi (scorpion kick)", hit=[5], category="air", fit=False)
    dr = A0.copy(lL=(-6, 4, 2, -40), lR=(-6, 4, 2, -40), aL=(80, 14, 0, 14, 0), aR=(80, 14, 0, 14, 0), tor=(14, 0, 0), hd=(-14, 0, 0))
    aadd("AttackAirLw", 42, K((0, A0), (4, A0.copy(lL=(70, 4, 120, 0), lR=(70, 4, 120, 0), tor=(20, 0, 0)), "in"), (11, dr, "fast"), (25, dr, "lin"), (29, dr, "lin"), (42, A0, "smooth")),
         serves="AttackAirLw (drill)", hit=[11, 25], category="air", fit=False)
    # ------------------------------------------------------------ grabs
    g_reach = S(aR=(92, 8, 0, 4, 0), cuR=0.0, aL=(30, 30, 0, 90, 0), tor=(14, 0, 24), hy=14, hp=(0, 0.8, -0.3), fl=(0.75, 1.5, 0, 0), fr=(0.75, -0.6, 0, 0), hd=(-4, 0, -10))
    add("Catch", 30, K((0, S()), (3, S(aR=(30, 8, 0, 110, 0), cuR=0.0, tor=(10, 0, -10)), "in"), (6, g_reach, "fast"), (9, g_reach, "lin"), (14, g_reach, "lin"), (30, S(), "smooth")),
        serves="Catch / CatchPull (grab whiff)", hit=[6])
    g_dash = g_reach.copy(tor=(30, 0, 24), hp=(0, 1.6, -0.6), fl=(0.9, 2.4, 0, 0), fr=(0.9, -2.0, 0.2, 18), aL=(-20, 30, 0, 70, 0))
    add("CatchDash", 36, K((0, S(tor=(22, 0, 0))), (6, S(tor=(26, 0, -10), aR=(10, 10, 0, 100, 0), cuR=0.0), "in"), (9, g_dash, "fast"), (13, g_dash, "lin"), (36, S(), "smooth")),
        serves="CatchDash (dash grab)", hit=[9])
    hold = S(aL=(80, 14, 0, 40, 0), aR=(80, 14, 0, 40, 0), cuL=0.1, cuR=0.1, tor=(8, 0, 0), hy=0, hd=(-4, 0, 0), fl=(0.8, 0.6, 0, 0), fr=(0.8, -0.6, 0, 0))
    add("CatchWait", 40, K((0, hold), (20, hold.add(hp=(0, 0, 0.1), tor=(1, 0, 0)), "smooth")), loop=True, serves="CatchWait (holding a victim: grab_anchor in front of the chest)")
    add("CatchAttack", 15, K((0, hold), (5, hold.copy(hd=(-22, 0, 0), tor=(2, 0, 0)), "in"), (14, hold.copy(hd=(32, 0, 0), tor=(16, 0, 0), hp=(0, 0.4, -0.1)), "fast"), (15, hold, "smooth")),
        serves="CatchAttack (pummel, a headbutt)", hit=[14])
    add("CatchCut", 22, K((0, hold), (6, hold.copy(aL=(60, 40, 0, 70, 0), aR=(60, 40, 0, 70, 0), cuL=0.0, cuR=0.0, tor=(-8, 0, 0), hp=(0, -0.6, 0)), "smooth"), (22, S(), "smooth")), serves="CatchCut (victim breaks free)")
    # throws
    tF_w = hold.copy(tor=(-6, 0, 0), aL=(40, 20, 0, 60, 0), aR=(40, 20, 0, 60, 0), hp=(0, -0.5, 0))
    tF = hold.copy(aL=(95, 6, 0, 4, 0), aR=(95, 6, 0, 4, 0), tor=(24, 0, 0), hp=(0, 1.2, -0.3), cuL=0.0, cuR=0.0, fl=(0.8, 1.6, 0, 0))
    add("ThrowF", 26, K((0, hold), (7, tF_w, "smooth"), (12, tF_w, "in"), (13, tF, "fast"), (26, S(), "smooth")), serves="ThrowF (forward throw; release 13)", hit=[13])
    tB1 = hold.copy(tor=(10, 0, -90), hy=-0, aL=(60, 20, 0, 40, 0), aR=(60, 20, 0, 40, 0), hp=(0, 0, -0.5))
    tB2 = hold.copy(tor=(10, 0, -114), hy=-76, aL=(95, 6, 0, 4, 0), aR=(95, 6, 0, 4, 0), cuL=0.0, cuR=0.0, hp=(0, 0, -0.2), hd=(-6, 0, 0))
    add("ThrowB", 60, K((0, hold), (14, tB1, "smooth"), (28, tB1.copy(tor=(10, 0, -112), hy=-38), "smooth"), (45, tB2, "fast"), (60, S(tor=(8, 0, -14)), "smooth")), serves="ThrowB (back throw; spin, release 45)", hit=[45])
    tU_w = hold.copy(hp=(0, 0, -1.0), aL=(30, 24, 0, 60, 0), aR=(30, 24, 0, 60, 0), tor=(16, 0, 0))
    tU = hold.copy(aL=(172, 18, 0, 4, 0), aR=(172, 18, 0, 4, 0), cuL=0.0, cuR=0.0, tor=(-16, 0, 0), hp=(0, 0, 0.2), hd=(8, 0, 0), fl=(0.8, 0.4, 0.4, -20), fr=(0.8, -0.4, 0.4, -20))
    add("ThrowHi", 34, K((0, hold), (9, tU_w, "smooth"), (18, tU_w, "in"), (19, tU, "fast"), (34, S(), "smooth")), serves="ThrowHi (up throw; release 19)", hit=[19])
    tD_w = hold.copy(aL=(165, 20, 0, 20, 0), aR=(165, 20, 0, 20, 0), tor=(-16, 0, 0), hd=(8, 0, 0))
    tD = hold.copy(aL=(80, 8, 0, 2, 0), aR=(80, 8, 0, 2, 0), cuL=0.0, cuR=0.0, tor=(46, 0, 0), hp=(0, 0.6, -1.7), hd=(-24, 0, 0), fl=(1.0, 0.8, 0, 0), fr=(1.0, -0.8, 0, 0))
    add("ThrowLw", 34, K((0, hold), (8, tD_w, "smooth"), (18, tD_w, "in"), (19, tD, "fast"), (34, S(), "smooth")), serves="ThrowLw (down throw: slam; release 19)", hit=[19])
    # ------------------------------------------------------------ specials
    ch = S(hp=(0, 0, -1.4), tor=(30, 0, -26), hy=-14, aR=(-45, 28, 0, 110, 0), aL=(60, 14, 0, 90, 0), hd=(-14, 0, 16), fl=(1.2, 1.0, 0, 0), fr=(1.2, -1.0, 0, 0))
    ch_b = ch.add(hp=(0, 0, 0.12), tor=(2, 0, -3), aR=(-8, 0, 0, 0, 0))
    add("NCharge", 12, K((0, ch, "lin"), (3, ch_b, "lin"), (6, ch, "lin"), (9, ch_b, "lin")), loop=True, serves="NCharge (hold B: coiled stance, 2-frame script loop)", wind=14)
    nr = S(tor=(36, 0, 30), hy=18, aR=(110, 0, 0, 4, 0), aL=(-60, 30, 0, 40, 0), hp=(0, 2.0, -1.0), fl=(1.0, 3.2, 0, 0), fr=(1.0, -3.0, 0.5, 35), hd=(-18, 0, -10))
    add("NRelease", 20, K((0, ch, "fast"), (3, nr, "fast"), (11, nr, "lin"), (20, S(), "smooth")), serves="NRelease (dash strike; hit 3-11)", hit=[3], wind=40)
    sl = S(tor=(32, 0, -22), hy=-10, aL=(104, 2, 0, 4, 0), cuL=0.0, aR=(-60, 30, 0, 40, 0), hp=(0, 1.8, -1.1), fl=(1.2, 3.4, 0, 0), fr=(1.2, -3.0, 0.4, 30), hd=(-12, 0, 12))
    add("SLunge", 28, K((0, S()), (2, S(hp=(0, 0, -1.0), tor=(18, 0, 10), aL=(40, 30, 0, 120, 0)), "in"), (4, sl, "fast"), (12, sl, "lin"), (28, S(), "smooth")), serves="SLunge (side special lunge; hit 4-12)", hit=[4], wind=30)
    ri = P(hp=(0, 0, 0), tor=(-4, 0, 0), aL=(172, 12, 0, 5, 0), aR=(172, 12, 0, 5, 0), hd=(6, 0, 0), lL=(-4, 3, 6, -50), lR=(-4, 3, 6, -50), fl=None, fr=None, cuL=1, cuR=1)
    def ri_gen(f, n=24):
        a = 360.0 * (f % n) / n
        return ri.copy(hy=a, tor=(-4, 0, 0))             # the hips carry the whole turn, so 360 degrees is exactly one full revolution (the loop closes)
    c = add("Rise", 24, serves="Rise (up special: a steerable corkscrew; the clip loops)", hit=[1], wind=70, category="air", fit=False, loop=True)
    c.gen = lambda f: ri_gen(f)
    cb1 = S(hp=(0, 0, -1.2), tor=(16, 0, 0), hy=0, aL=(78, 38, 0, 120, 0), aR=(78, 38, 0, 120, 0), cuL=1, cuR=1, hd=(-8, 0, 0), fl=(1.3, 0.3, 0, 0), fr=(1.3, -0.3, 0, 0))
    cb1x = cb1.copy(aL=(92, 6, -40, 118, 0), aR=(92, 6, 40, 118, 0))
    add("Counter", 30, K((0, S()), (3, cb1, "fast"), (4, cb1x, "fast"), (24, cb1x, "lin"), (30, S(), "smooth")), serves="Counter (guard cross; counter window 4-24)")
    cs = S(tor=(30, 0, 40), hy=24, aR=(100, 2, 0, 4, 0), aL=(-40, 30, 0, 50, 0), hp=(0, 1.6, -1.0), fl=(1.0, 3.0, 0, 0), fr=(1.0, -1.6, 0.3, 15), hd=(-12, 0, -12))
    add("CounterStrike", 21, K((0, cb1x, "fast"), (2, cs, "fast"), (7, cs, "lin"), (21, S(), "smooth")), serves="CounterStrike (answering strike; hit 2-7)", hit=[2], wind=30)
    return CLIPS
