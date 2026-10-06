"""Gait generator for the Courier: contact / down / passing / up poses with a rolling foot, no sliding.

The body stays in place (the engine moves the fighter), so a planted sole point has to travel BACK relative to the
body at exactly the ground speed v (units / frame). The foot is built from that rule, not tuned by eye:

  stance   heel strike (heel pivots, toes up)  ->  foot flat (ankle moves at v)  ->  heel lift (ball pivots, toes down,
           the toe bone flexes so the tip stays on the ground).  The contact point moves at v in every stance phase.
  swing    one cubic Hermite from toe-off to the next heel strike, matching the stance velocities at both ends (so the
           foot does not jerk), with the ankle lifted over a bump and the foot pitch recovered on the way.
  hips     walk: highest over the supporting foot (passing), lowest in double support; run: lowest at mid-stance
           (the leg compresses), highest in flight; both are then lowered further by fit_hips where a leg cannot reach.
  arms     swing opposite the legs, the elbow closes as the arm comes forward; the trunk counter-rotates the pelvis, leans
           into the stride and bends toward the supporting foot; the head stays level and facing forward.

All angles in degrees (see anim_lib.py for the pose DSL); distances in model units (the heel sits 1.05 behind the ankle,
the ball 1.55 ahead of it, the sole 1.25 below it).
"""
import math
from anim_lib import P

HEEL_B, BALL_F, ANK_H = 1.05, 1.55, 1.25

def sm(u):
    u = 0.0 if u < 0 else 1.0 if u > 1 else u
    return u * u * (3 - 2 * u)

def herm(p0, p1, m0, m1, u):
    h00 = 2 * u ** 3 - 3 * u ** 2 + 1; h10 = u ** 3 - 2 * u ** 2 + u; h01 = -2 * u ** 3 + 3 * u ** 2; h11 = u ** 3 - u ** 2
    return h00 * p0 + h10 * m0 + h01 * p1 + h11 * m1

def rot(f, u, phi):
    c, s = math.cos(math.radians(phi)), math.sin(math.radians(phi))
    return f * c - u * s, f * s + u * c

class Foot:
    """One foot's ankle track over a gait cycle of N frames; phase 0 = heel strike. Returns (fwd, up, pitch, toe_flex)."""
    def __init__(self, N, duty, v, heel_t, toe_t, phi_h, phi_t, lift, xc, swing_skew=0.8):
        self.N, self.v = N, v
        self.S = duty * N; self.ta, self.tc = heel_t, toe_t; self.tb = self.S - toe_t
        self.phi_h, self.phi_t, self.lift, self.skew = phi_h, phi_t, lift, swing_skew
        mid = (self.ta + self.tb) / 2.0
        self.X0 = xc + v * (mid - self.ta)               # ankle x at the start of the flat phase
        self.W = N - self.S
        a0 = self.stance(0.0); a1 = self.stance(self.S)
        e = 0.01
        self.v0 = tuple((x - y) / e for x, y in zip(self.stance(e)[:3], a0[:3]))
        self.v1 = tuple((x - y) / e for x, y in zip(a1[:3], self.stance(self.S - e)[:3]))
        self.a0, self.a1 = a0, a1

    def stance(self, t):
        v, ta, tb, tc, S = self.v, self.ta, self.tb, self.tc, self.S
        if t < ta:                                              # heel strike: pivot about the heel
            u = t / ta if ta > 0 else 1.0
            phi = self.phi_h * (1 - (1 - (1 - u) ** 2))         # toes come down quickly then settle
            heel_x = self.X0 - HEEL_B + v * (ta - t)
            dx, dy = rot(HEEL_B, ANK_H, phi)
            return heel_x + dx, dy - ANK_H, phi, 0.0
        if t <= tb:                                             # foot flat
            return self.X0 - v * (t - ta), 0.0, 0.0, 0.0
        u = (t - tb) / tc if tc > 0 else 1.0                    # heel lift: pivot about the ball
        phi = self.phi_t * sm(u) ** 0.9
        ank_tb = self.X0 - v * (tb - ta)
        ball_x = ank_tb + BALL_F - v * (t - tb)
        dx, dy = rot(-BALL_F, 0.7, phi)                         # the foot turns about the toe joint; the toe bone stays flat on the ground
        return ball_x + dx, 0.55 + dy - ANK_H, phi, max(0.0, -phi)

    def at(self, ph):
        t = (ph % 1.0) * self.N
        if t < self.S: return self.stance(t)
        u = (t - self.S) / self.W
        W = self.W
        x0, z0, ph0 = self.a1[0], self.a1[1], self.a1[2]
        x1, z1, ph1 = self.a0[0] + self.N * 0.0, self.a0[1], self.a0[2]
        # next stance starts at a0 (ankle x there is the heel-strike position)
        fwd = herm(x0, x1, self.v1[0] * W, self.v0[0] * W, u)
        base = herm(z0, z1, self.v1[1] * W * 0.3, self.v0[1] * W * 0.3, u)
        bump = math.sin(math.pi * (u ** self.skew)) ** 1.3
        up = base + self.lift * bump
        pitch = ph0 + (ph1 - ph0) * sm(min(1.0, u * 1.2) if ph0 < ph1 else u)
        toe = max(0.0, -pitch)
        return fwd, up, pitch, toe

def gait(Nc, duty, v, arm, elbow0, elbow1, lean, dip, run=False, heel_t=2.0, toe_t=3.0, phi_h=18.0, phi_t=-34.0, lift=1.4,
         xc=0.2, out=0.35, twist=7.0, sway=0.35, arm_abd=12.0, flight=0.0, base=None, head_still=0.85, carry=None, lag_arm=0.05):
    """A function f -> Pose for a looping gait of Nc frames per full cycle (two steps)."""
    ft = Foot(Nc, duty, v, heel_t, toe_t, phi_h, phi_t, lift, xc)
    base = base or P(hd=(-2, 0, 0), cuL=1, cuR=1)
    def gen(f):
        ph = (f % Nc) / Nc
        fl, fr = ft.at(ph), ft.at(ph + 0.5)         # LEFT uses the reference track at phase ph (heel strike at ph=0)
        c = math.cos(2 * math.pi * ph); s = math.sin(2 * math.pi * ph)
        if run:
            th = 4 * math.pi * (ph - duty / 2.0)
            hz = flight * (1 - math.cos(th)) / 2.0 - dip
            lean_ = lean + 1.8 * math.cos(th)                        # leans harder into the stance
        else:
            th = 4 * math.pi * (ph - duty / 2.0)
            hz = -dip * (1 - math.cos(th)) / 2.0
            lean_ = lean + 0.6 * math.cos(th)
        sh = sway * math.cos(2 * math.pi * (ph - duty / 2.0))        # pelvis shifts over the supporting foot (left = +x)
        arm_ph = 2 * math.pi * (ph - lag_arm)
        ca = math.cos(arm_ph)
        swL, swR = -arm * ca, arm * ca
        eL = elbow0 + elbow1 * (1 + (-ca)) / 2.0                     # left arm forward when ca < 0
        eR = elbow0 + elbow1 * (1 + ca) / 2.0
        hy = -twist * c
        tw = twist * 0.8 * c
        pitchL, pitchR = fl[2], fr[2]
        p = base.copy(fl=(out, fl[0], fl[1], fl[2]), fr=(out, fr[0], fr[1], fr[2]), toL=fl[3], toR=fr[3],
                      tor=(lean_, -sway * 4.0 * math.cos(2 * math.pi * (ph - duty / 2.0)), tw), hy=hy,
                      aL=(swL, arm_abd, 0, eL, 0), aR=(swR, arm_abd, 0, eR, 0),
                      hp=(sh, 0, hz), hd=(-lean_ * 0.7, 0, -(hy + tw) * head_still))
        if carry: p = carry(p, ph)
        return p
    return gen
