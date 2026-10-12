"""HB-SAMPLE hitboxes for the Goku remake (phase 2): labelled starting points the owner edits in the Workbench, never final.

    python ports/goku-xv2/tools/remake_samples.py plan     # dry run: per move the XV2 hit entry used, the limb, the spheres (no file changes)
    python ports/goku-xv2/tools/remake_samples.py write    # rewrite the HB-NONE move scripts with hitbox lines and mark them HB-SAMPLE

Needs a built package (build.py) for the pose bank and the mesh; run `build.py --gameplay-only` afterwards (its audit fails a sphere whose centre is farther
than its radius from the limb bone segment). What is derived from what (REMAKE-SAMPLES.md has the tables):

* WHEN: the XV2 BAC Hitbox events that play while the row's clip plays (frame, duration) mapped through the row's crop and speed.
* HOW MUCH: XV2 damage through an anchor table to Melee damage (capped per move class); the BDM reaction (DamageType, strength Y up / Z forward, duration)
  to angle, KBG, BKB. Weak Standard reactions are string hits (angle 361, fixed knockback) like the existing light string.
* WHERE: the limb that leads at the window (largest reach from the chest in the built animation bank) gets 3 spheres along its bone chain (tip,
  middle, inner), centres on the bone axis of the mesh cloud of each bone, radius = mesh limb thickness x LIMB_FAT. Tip slot 0 strongest, inner slots weaker.
"""
import json
import math
import re
import sys
from pathlib import Path

import os
import numpy as np

HERE = Path(__file__).resolve().parent
PORT = HERE.parent
ROOT = PORT.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'ports/ir/tools'))
import strip_gameplay as SG  # noqa: E402
import build as G  # noqa: E402
import audit_gameplay as AU  # noqa: E402
import check_hitbox_positions as HP  # noqa: E402
import figatree  # noqa: E402
from plan_hurtboxes import seg_dist  # noqa: E402
from tools.geno import report, script  # noqa: E402

AUTHOR = ROOT / '_build/goku-xv2/author-source'
PKG = AUTHOR / 'package/mods/goku-xv2'
ART = AUTHOR / 'package/build'
BDM_DIR = Path('E:/Torrents/Dragon.Ball.Xenoverse.2.Future.Saga.Chapter.4-RUNE/modding/exports/goku-base-shallow-v0.1/decoded/chara')

LIMB_FAT = 2.4        # hitbox radius = mesh limb thickness x this (Melee spheres are fatter than the limb they ride on)
MIN_RADIUS = 2.0
MAX_RADIUS = 3.6
HB_GROW = 2.0          # owner 2026-10-11: "all hitboxes 2x the size, except back air": every sample sphere's radius x this (centres stay on the limb bones)
GROW_EXCLUDE = ('bair',)
CARRY = ('bair', 'grab', 'dash_grab')   # scripts not regenerated: bair (Luigi) and the grabs (Falcon) are cross-ports (tools/cross_port.py)   # moves kept at the unscaled size (bair is also 'carry': its script is not regenerated)
# XV2 damage -> Melee damage (anchors from Marth: jab 3, tilts 8, fair 10, smashes 15-22); linear between anchors
ANCHORS = [(0, 0), (3, 2), (5, 3), (10, 8), (15, 10), (20, 12), (30, 15), (40, 20)]
CAP = {'jab': 7, 'tilt': 12, 'smash': 22, 'aerial': 14, 'special': 16, 'grab': 0}
INNER_SCALE = (1.0, 0.85, 0.7)       # tip, middle, inner damage
INNER_BKB = (0, -3, -6)
CHAINS = {  # effector role -> bones from the tip inwards (mesh owners; the hand is part of the lower arm cloud)
    'hand.R': ['lower_arm.R', 'upper_arm.R'], 'hand.L': ['lower_arm.L', 'upper_arm.L'],
    'foot.R': ['foot.R', 'lower_leg.R', 'upper_leg.R'], 'foot.L': ['foot.L', 'lower_leg.L', 'upper_leg.L'],
}
TOKEN = {'lower_arm.R': 'ARM_R', 'upper_arm.R': 'UPARM_R', 'lower_arm.L': 'ARM_L', 'upper_arm.L': 'UPARM_L', 'foot.R': 'FOOT_R', 'foot.L': 'FOOT_L',
         'lower_leg.R': 'LEG_R', 'lower_leg.L': 'LEG_L', 'upper_leg.R': 'UPLEG_R', 'upper_leg.L': 'UPLEG_L'}
# the owner's descriptions of the clips (CLIP-NOTES.md / the picker): a kick leads with a foot, a punch with a hand; undescribed clips use the motion metric alone
CLIP_LIMB = {'GOK_ATC_002': 'hand', 'GOK_ATC_003': 'hand', 'GOK_ATC_004': 'hand', 'GOK_ATC_006': 'hand', 'GOK_ATC_007': 'foot', 'GOK_ATC_008': 'foot',
             'GOK_ATC_011': 'foot', 'GOK_ATC_012': 'foot', 'GOK_ATC_017': 'foot', 'GOK_ATC_020_S': 'foot', 'GOK_ATC_025': 'foot', 'GOK_ATC_028': 'foot',
             'GOK_NAG_TSUKAMI': 'hand'}
# moves whose limb the reach rule (leading_limb, 2026-10-11) would flip but the owner has not been asked about: they keep the limb they had. dtilt is deliberately NOT here (the fix).
# Reported flips: dash_attack foot.R -> foot.L, utilt hand.L -> hand.R, RushCombo hand.R -> foot.L, Light5 hand.L -> foot.R. owner 2026-10-11: current limbs confirmed in game.
# owner 2026-10-11 (goku-stage playtest): utilt's hand.L lock is lifted (the hitboxes were on the wrong hand; the reach rule picks the striking hand, as for dtilt).
# owner 2026-10-11: RushCombo is the left-leg kick (reverses the earlier hand.R lock).
LIMB_LOCK = {'dash_attack': 'foot.R', 'RushCombo': 'foot.L', 'Light5': 'hand.L'}
# owner 2026-10-11 playtest: first active frame. utilt starts at 8 (the second punch, hand.R, is out from frame 9); ftilt at 5 (hand.R extension peaks at frame 5, 7.2 vs 6.7 at frame 4).
# (a, b) in row frames; the XV2-derived window is replaced, the limb and everything else still come from the plan.
WINDOW_OVERRIDE = {'utilt': (8, 12), 'ftilt': (5, 9)}
SKIP_SAMPLE = {'pummel', 'fthrow', 'bthrow', 'uthrow', 'dthrow', 'rapid_start', 'rapid_end', 'ITEnd', 'Recovery', 'KameCharge'}


def anchor_damage(x):
    for (a, ya), (b, yb) in zip(ANCHORS, ANCHORS[1:]):
        if x <= b:
            return ya + (yb - ya) * (x - a) / (b - a)
    return ANCHORS[-1][1]


def load_bdm():
    cmn = json.loads((BDM_DIR / 'CMN/CMN.bdm.json').read_text(encoding='utf-8'))['BDM_Entries']
    gok = json.loads((BDM_DIR / 'GOK/GOK_PLAYER.bdm.json').read_text(encoding='utf-8'))['BDM_Entries']

    def look(scope, v):
        for e in (cmn if scope == 'Common' else gok):
            if int(e['Index']) == v:
                x = e['Type0Entries'][0]
                return {'type': x['DamageType']['label'], 'up': x['KnockbackStrengthY'], 'fwd': x['KnockbackStrengthZ'], 'dur': x['KnockbackDuration']}
        return {'type': 'Standard', 'up': 0.1, 'fwd': 0.04, 'dur': 30}
    return look


def reaction_to_melee(bdm, dmg, cls, string_hit):
    """BDM reaction -> (angle, kbg, fkb, bkb). Table in REMAKE-SAMPLES.md."""
    if string_hit:   # a hit that feeds the next link of a string: Melee jab convention, the same push at every percent
        return 361, 60, 10, 0
    t = bdm['type']
    if t == 'Standard' or t.startswith('Stumble'):
        return 361, 50, 0, int(round(6 + 0.8 * dmg))
    ang = math.degrees(math.atan2(bdm['up'], max(bdm['fwd'], 1e-6)))
    if ang <= -45:
        angle = 270                          # spike / meteor
    elif ang >= 55:
        angle = 80 if ang < 80 else 85       # launcher
    elif ang >= 25:
        angle = 55
    else:
        angle = 45 if cls in ('smash', 'special') else 40   # horizontal blowback
    d = bdm['dur']
    kbg = int(min(100, max(50, 60 + 0.5 * (d - 30))))
    bkb = int(round(20 + 1.5 * dmg))
    return angle, kbg, 0, bkb


def limb_clouds(plan, points, weights, worlds):
    """role -> {joint, a (proximal), b (distal), radius}: the mesh cloud of every limb bone in its joint-local frame (PCA axis, 3-97 percentile extent, 92nd percentile thickness)."""
    roles = plan['roles']
    parents = {j['index']: j['parent'] for j in plan['joints']}
    segs = {}
    for role in sum(CHAINS.values(), []):
        segs[roles[role][0]] = role
    owners = []
    for w in weights:
        joint = max(w, key=lambda x: x[1])[0]
        while joint not in segs and parents.get(joint) is not None:
            joint = parents[joint]
        owners.append(joint if joint in segs else -1)
    owners = np.array(owners)
    out = {}
    for joint, role in segs.items():
        sel = points[owners == joint]
        if len(sel) < 8:
            continue
        inv = np.linalg.inv(worlds[joint])
        local = (inv[:3, :3] @ sel.T).T + inv[:3, 3]
        centre = local.mean(0)
        axis = np.linalg.svd(local - centre, full_matrices=False)[2][0]
        proj = (local - centre) @ axis
        low, high = np.percentile(proj, [3, 97])
        a, b = centre + axis * low, centre + axis * high
        if np.linalg.norm(a) > np.linalg.norm(b):
            a, b = b, a
        radius = float(np.percentile(seg_dist(local, a, b), 92))
        out[role] = {'joint': joint, 'a': a, 'b': b, 'radius': max(radius, 0.15)}
    return out


class Rig:
    """The built pose bank + mesh of the package (what audit_gameplay reads)."""

    def __init__(self):
        self.plan = G.load(PKG / 'files/plan.json')
        self.mesh = G.load(next(ART.glob('mesh_*.json')))
        self.rest, self.native, self.worlds = AU.rest_context(self.mesh, self.plan)
        self.bank = (PKG / 'files' / self.plan['bank']['file']).read_bytes()
        self.cfg = G.load(SG.path())
        self.scale = G.load(AUTHOR / 'art-report.json')['geometry']['height'] / self.cfg['geometry_reference_height']
        self.roles = self.plan['roles']
        self.points, self.weights = AU.mesh_points(self.mesh)
        self.clouds = self._clouds()
        self._trees = {}

    def _clouds(self):
        return limb_clouds(self.plan, self.points, self.weights, self.worlds)

    def tree(self, clip):
        if clip not in self._trees:
            rec = self.plan['bank']['clips'][clip]
            self._trees[clip] = figatree.parse_archive(self.bank[rec['offset']:rec['offset'] + rec['bytes']])[1]
        return self._trees[clip]

    def pose(self, row, frame):
        tree = self.tree(row)
        return HP.pose_matrices(tree, self.native, self.rest, min(frame, tree['frames']))

    def leading_limb(self, clip, f0, f1, kind=None):
        """The effector thrown farthest from the chest inside the window (the striking limb). Owner 2026-10-11 (dtilt): the old score was raw displacement from five frames before,
        which picked the planted foot of a kick whose other foot swung out; reach from the chest picks the limb that is actually out there."""
        best, score = None, -1.0
        for eff in CHAINS:
            if kind and not eff.startswith(kind):
                continue
            tot = max(self.extension(clip, eff, f) for f in range(max(f0 - 2, 0), f1 + 1))
            if tot > score:
                best, score = eff, tot
        return best

    def extension(self, clip, eff, f):
        """Distance of the effector from the chest at frame f (how far the limb is thrown out)."""
        p = self.pose(clip, f)
        return float(np.linalg.norm(p[self.roles[eff][0]][:3, 3] - p[self.roles['chest'][0]][:3, 3]))

    def refine(self, clip, eff, a, b, frames, reach=6):
        """Centre the XV2 window on the frame where the limb is farthest out (BAC event frames run on the BAC's own clock, which can differ from the clip's)."""
        if not eff or clip not in self.plan['bank']['clips']:
            return a, b
        lo, hi = max(1, a - reach), min(frames - 2, b + reach)
        best, fbest = -1.0, a
        for f in range(lo, hi + 1):
            e = self.extension(clip, eff, f)
            if e > best + 1e-6:
                best, fbest = e, f
        width = max(3, b - a)
        na = max(1, fbest - width // 2)
        return na, na + width

    def spheres(self, eff, n=3, grow=1.0):
        """Up to n spheres along the chain, tip first: (token, x, y, z, radius) in script units."""
        out = []
        for i, bone in enumerate(CHAINS[eff][:n]):
            c = self.clouds.get(bone)
            if not c:
                continue
            t = 0.78 if i == 0 else 0.5                 # the tip sits near the distal end of its cloud, the others mid-bone
            if bone.startswith('lower_arm') and i == 0:
                t = 0.85                                # the hand end of the forearm cloud
            if bone.startswith('lower_arm') and len(CHAINS[eff]) == 2 and n >= 3:
                pass
            ctr = c['a'] + (c['b'] - c['a']) * t
            r = min(MAX_RADIUS, max(MIN_RADIUS, c['radius'] * LIMB_FAT))
            out.append((TOKEN[bone], *(ctr / self.scale).tolist(), r * grow / self.scale))
        if eff.startswith('hand') and len(out) == 2:       # arms: add a mid-forearm sphere between the hand end and the upper arm
            c = self.clouds.get(CHAINS[eff][0])
            if c:
                ctr = c['a'] + (c['b'] - c['a']) * 0.4
                out.insert(1, (TOKEN[CHAINS[eff][0]], *(ctr / self.scale).tolist(), min(MAX_RADIUS, max(MIN_RADIUS, c['radius'] * LIMB_FAT)) * grow / self.scale))
        return out[:n]


def source_hits(source):
    """BAC entry id -> [(frame, duration, hitbox dict, scope, reaction)] and the clip segments it plays: [(frame, clip name, start, end, speed)]."""
    bacs = {}
    for sid, sub in source.subs.items():
        m = re.search(r'GOK_PLAYER\.bac/(\d+)$', sid)
        if not m:
            continue
        sc = source.scripts.get(sub['scripts']['main'])
        if not sc:
            continue
        segs, hits = [], []
        for e in sc['events']:
            if e['op'] == 'engine.animation':
                b = e['args'].get('binding') or {}
                if b.get('clip') and b['clip'] in source.clips and '.fce.' not in b['clip']:
                    segs.append((e['frame'], source.clips[b['clip']]['name'], b['start_frame'], b['end_frame'], b['speed']))
            elif e['op'] == 'hitbox.create' and e.get('hitbox'):
                h = e['hitbox']
                hits.append((e['frame'], e['args']['engine']['xv2.pc']['duration_frames'], h, h['engine']['xv2.pc']['reaction_scope'],
                             h['engine']['xv2.pc']['reaction']['value']))
        bacs[int(m.group(1))] = (sorted(segs), hits)
    return bacs


def row_windows(bacs, clip, start, tf, frames, hint):
    """Hits of the best BAC entry that plays `clip` at the hit frame, as row-frame windows [(a, b, hit)]."""
    best = None
    for n, (segs, hits) in sorted(bacs.items()):
        wins = []
        for fr, dur, h, scope, rv in hits:
            seg = [s for s in segs if s[0] <= fr]
            seg = seg[-1] if seg else None
            if not seg or seg[1] != clip:
                continue
            cf = seg[2] + (fr - seg[0]) * seg[4]
            a = (cf - start) / tf
            b = (cf + max(dur, 1) - start) / tf
            if b < 1 or a >= frames:
                continue
            wins.append((max(1, int(round(a))), min(frames - 1, max(int(round(b)), int(round(a)) + 2)), h, scope, rv))
        if wins and (best is None or n == hint):
            best = (n, wins)
            if n == hint:
                break
    return best


def class_of(move):
    tag = move.get('tag') or move.get('move_tag') or ''
    n = move['name']
    if n in ('jab1', 'jab2', 'jab3', 'rapid_jab') or n.startswith('Light'):
        return 'jab'
    if n.endswith('smash') or n.startswith('Heavy'):
        return 'smash'
    if n in ('nair', 'fair', 'bair', 'uair', 'dair'):
        return 'aerial'
    if n in ('grab', 'dash_grab'):
        return 'grab'
    if n in ('ftilt', 'utilt', 'dtilt', 'dash_attack'):
        return 'tilt'
    return 'special'


def fmt(v):
    return ('%.4g' % v)


IASA_AT = {'Rush': 40}


SMASH_CHARGE = {'fsmash', 'usmash', 'dsmash'}   # Melee's smash charge (ftcmd smash_charge: hold A to charge up to 60 frames, damage x1.3671) 2 frames before the first active frame
CHARGE_LINE = 'smash_charge charge_frames=60 charge_rate=350 color_anim=119'


def build_script(old_text, blocks, header, iasa=None, extra=None):
    """Timeline-merge: the old script's non-hitbox commands plus the new hitbox blocks [(frame, [lines], end_frame)]."""
    ev, t = [], 0
    for ln in old_text.splitlines():
        s = ln.strip()
        if not s or s.startswith('#'):
            continue
        w = s.split(None, 1)
        op = w[0].lower()
        if op == 'wait_until':
            t = int(float(w[1]))
        elif op == 'wait':
            t += int(float(w[1]))
        elif op in ('hitbox', 'clear_hitbox', 'clear_hitboxes', 'hitboxes_clear', 'hbstun', 'hbflags', 'hbdmg', 'rehit'):
            continue
        elif op == 'smash_charge':
            continue   # re-added below at the right frame
        elif op == 'iasa' and iasa:
            ev.append((iasa, 3, s))
        else:
            ev.append((t, 0, s))
    for a, lines, b in blocks:
        for k, l in enumerate(lines):
            ev.append((a, 1, l))
        ev.append((b, 2, 'clear_hitboxes'))
    for a, line in (extra or []):
        ev.append((a, 0, line))
    ev.sort(key=lambda e: (e[0], e[1]))
    out = header.rstrip('\n').split('\n')
    cur = 0
    for t, _, line in ev:
        if t != cur and t > 0:
            out.append('wait_until %d' % t)
            cur = t
        out.append(line)
    # a trailing iasa must stay last in time order: it is an ordinary event above
    return '\n'.join(out) + '\n'


OLD_REV = '93231f5'   # the last commit with the earlier generated scripts (timing fallbacks, HBSTUN carry-over)
OVERRIDES = {   # move -> forced fields; design intent from the owner brief, recorded in REMAKE-SAMPLES.md
}
# owner 2026-10-11: smash knockback is Melee's. (angle, KBG, BKB) of the tip slot, the inner slots follow INNER_BKB. Retail reference (hit data read from the vanilla disc, damage / angle / KBG / BKB):
#   fsmash Marth 14-20 / 361 / 70 / 60-80, Fox 15 / 361 / 105 / 10, Mewtwo 12-20 / 361 / 75-80 / 21-30, Falcon (S4Hi) 21 / 361 / 100 / 24
#   usmash Marth 15-18 / 90 / 80 / 30-60, Falcon 13-14 / 90 / 105-128 / 30, Fox 18 / 80 / 112 / 30, Mewtwo 10 / 90 / 118 / 40
#   dsmash Marth 11-16 / 70-75 / 72-100 / 70, Falcon 16-18 / 361 / 100 / 20-30, Fox 12-15 / 361-25 / 65-100 / 2-20, Mewtwo 15 / 361 / 103 / 20
SMASH_KB = {'fsmash': (361, 100, 28), 'usmash': (88, 105, 32), 'dsmash': (361, 100, 28)}
# and the tip damage: XV2's 15 / 15 / 10 mapped through the anchor table gave 10 / 10 / 8, far under retail's 14-21, which no growth value makes up for. Knockback-formula KO estimate at the
# stage centre on Mario (weight 100, no DI, tip slot, KB = ((p/10 + p*d/20) * 200/(w+100) * 1.4 + 18) * KBG/100 + BKB, launch speed 0.03 KB, 0.051 decay, blast zone 224 out / 188 up):
#   fsmash Marth tip 42, Falcon 52, Fox 90, Mewtwo tip 89;  usmash Marth 46, Falcon 69, Fox 44, Mewtwo 76;  dsmash Marth tip 41, Falcon 62, Fox 151, Mewtwo 84  (percent before the hit, uncharged)
#   Goku with 15/100/28: fsmash 81, usmash (14/105/32) 67, dsmash (13/100/28) about 95; fully charged (x1.4 damage) 50 / 41 / about 60.
BODY_SPHERE = {'usmash': ('HIPS', 3.2)}   # token, script-unit radius (5.5 in game)
SMASH_DMG = {'fsmash': 15, 'usmash': 14, 'dsmash': 13}
# owner 2026-10-11: the forward and down air spikes are small sweetspots on the fist / foot tip for a few frames; everywhere else the move is a sourspot at a normal angle.
# Marth's dair tipper is the size reference (sphere 3.5, active 4 frames, 290, KBG 70, BKB 40; his other spheres 361 / 80 with BKB 20-40); Mario's fair is a 5-frame 280 meteor (KBG 70, BKB 30).
# radius is in script units (the build multiplies by 1.4286 and the engine by 1.2: 2.3 -> 3.9, 2.1 -> 3.6 in game, no HB_GROW); frames = the spike's active frames, centred in the XV2 window.
SPIKES = {'dair': {'radius': 2.1, 'frames': 3, 'angle': 290, 'kbg': 70, 'bkb': 40}}
# owner 2026-10-11: Goku's fair is built on retail Mario's AttackAirF (read from the vanilla disc, numbers only): hitbox 0 (hand, size 3.125) and hitbox 1 (forearm, size 3.906, 3.125 along it)
# both created at script frame 18, damage 15, angle 280 (meteor), KBG 70, fixed 0, BKB 30, cleared 5 frames later; IASA 60. The retail script has NO sourspot: both spheres spike for the whole
# window. Here: the same two-sphere, 5-frame window centred on the clip's peak extension, on the arm chain (tip + forearm), the owner's 2x sizes.
MARIO_FAIR = {'spheres': 2, 'frames': 5, 'damage': 15, 'angle': 280, 'kbg': 70, 'bkb': 30}
SOURCE_NOTE = {'fair': 'Mario AttackAirF (retail): 2 spheres, 5 frames, damage 15, angle 280, KBG 70, BKB 30, no sourspot',
               'dair': 'spike sweetspot 2.1 script units (3.6 in game) for 3 frames, sourspot elsewhere; Marth dair tipper 3.5 / 4 frames / 290 / KBG 70 / BKB 40 is the reference'}
SOUR = {'angle': 40, 'kbg': 70, 'bkb': 20, 'dmg_scale': 0.7, 'late_frames': 3}   # the sourspot: diagonal forward, low knockback, 70% damage, held 3 frames past the window


def old_script(rel):
    import subprocess
    r = subprocess.run(['git', 'show', '%s:ports/goku-xv2/%s' % (OLD_REV, rel)], cwd=ROOT, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ''


def old_windows(text):
    """[(start, end)] of the hitbox windows of an earlier script (timeline replay), for clips with no XV2 hit entry."""
    t, start, wins = 0, None, []
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith('#'):
            continue
        w = s.split(None, 1)
        op = w[0].lower()
        if op == 'wait_until':
            t = int(float(w[1]))
        elif op == 'wait':
            t += int(float(w[1]))
        elif op == 'hitbox' and start is None:
            start = t
        elif op in ('clear_hitboxes', 'hitboxes_clear') and start is not None:
            wins.append((max(1, start), max(start + 2, t)))
            start = None
    return wins


def old_hbstun(text):
    m = re.search(r'^HBSTUN\s+\d+\s+(\d+)', text, re.M)
    return int(m.group(1)) if m else 0


def targets(cfg, combo):
    t = []
    for m in cfg['moves']:
        t.append(dict(name=m['name'], kind='move', motion=m['motions'][0], script=m['script'], hint=(m.get('pick') or {}).get('bac'), chain=False, entry=m))
    for m in cfg['special_adaptations']:
        if m['name'] in ('Rush', 'RushCombo', 'Homing'):
            t.append(dict(name=m['name'], kind='special', row=m['name'], script=m['script'], hint={'Rush': 419, 'RushCombo': 427, 'Homing': 476}[m['name']],
                          chain=m['name'] in ('Rush', 'Homing'), entry=m))
    for s in combo['states']:
        if s['name'] in ('Light3', 'Light4', 'Light5', 'HeavyRush', 'HeavyFinish', 'HeavyUp'):
            t.append(dict(name=s['name'], kind='combo', clip=s['clip'], script='combo/' + s['script'], hint=s.get('bac'), chain=False, entry=s))
    return [x for x in t if x['name'] not in SKIP_SAMPLE]


def source_clip_frames(source, name):
    for c in source.clips.values():
        if c['name'] == name:
            return c['frames']
    return 40


def plan_targets(rig, source, anim_rows, combo):
    bacs = source_hits(source)
    by_motion = {r['motion']: r for r in anim_rows if r.get('source')}
    art = json.loads((AUTHOR / 'art-report.json').read_text(encoding='utf-8'))['animations']
    routes = combo['combo']['routes']
    sources = set()
    for r in routes:
        for f in (r['from'] if isinstance(r['from'], list) else [r['from']]):
            sources.add(f.split(':', 1)[1] if f.startswith('geno:') else f)
    bdm = load_bdm()
    result = []
    for t in targets(rig.cfg, combo):
        name = t['name']
        if name in CARRY:
            result.append(dict(t, status='carry'))
            continue
        if t['kind'] == 'combo':
            clipname = t['clip'][1:] if t['clip'].startswith('x') else t['clip']
            bank_clip = t['clip']
            row = {'source_name': clipname, 'start': 0, 'time_factor': 1.0, 'frames': min(180, source_clip_frames(source, clipname))}
        else:
            bank_clip = by_motion[t['motion']]['clip'] if t['kind'] == 'move' else t['row']
            row = art.get(bank_clip)
            if not row:
                result.append(dict(t, status='no row'))
                continue
            clipname = row['source_name']
        start, tf, frames = row.get('start') or 0, row.get('time_factor') or 1.0, row.get('frames') or 0
        if t['chain']:
            n = t['hint']
            segs, hits = bacs[n]
            found = (n, [(max(1, fr), min(frames - 1, fr + max(d, 1)), h, sc, rv) for fr, d, h, sc, rv in hits if fr < frames])
        else:
            pk = (t['entry'].get('pick') or {}) if t['kind'] == 'move' else {}
            hint = t['hint'] if (t['kind'] != 'move' or str(pk.get('clip', '')).endswith(clipname)) else None
            found = row_windows(bacs, clipname, start, tf, frames, hint)
        note = 'XV2 hit entry %s' % (found[0] if found else '-')
        if not found or not found[1]:
            ow = old_windows(old_script(t['script']))
            if not ow:
                result.append(dict(t, status='no XV2 hit and no earlier window'))
                continue
            found = (None, [(a, b, None, 'Common', None) for a, b in ow])
            note = 'windows from the earlier design (no XV2 hit entry for this clip)'
        cls = class_of(t['entry'])
        string = (name in sources) and cls in ('jab', 'special', 'aerial', 'tilt')
        wl = []
        for a, b, h, sc, rv in found[1]:
            b_ = bdm(sc, rv) if h else {'type': 'Standard', 'up': 0.1, 'fwd': 0.04, 'dur': 30}
            xdmg = h['damage'] if h else 8
            dmg = min(CAP[cls], max(1, int(round(anchor_damage(xdmg))))) if cls != 'grab' else 0
            eff = LIMB_LOCK.get(name) or (rig.leading_limb(bank_clip, a, b, CLIP_LIMB.get(clipname)) if bank_clip in rig.plan['bank']['clips'] else None)
            a0, b0 = a, b
            if h is not None and not t['chain'] and len(found[1]) == 1:
                a, b = rig.refine(bank_clip, eff, a, b, frames)
            if name in WINDOW_OVERRIDE and len(found[1]) == 1:
                a, b = WINDOW_OVERRIDE[name]
            wl.append(dict(a0=a0, b0=b0, a=a, b=b, xdmg=xdmg, bdm=b_, dmg=dmg, limb=eff, rv=rv))
        result.append(dict(t, status='ok', bac=found[0], note=note, cls=cls, string=string, wins=wl, frames=frames, bank_clip=bank_clip))
    return result


def render(rig, tg):
    """The hitbox blocks [(a, lines, b)] of a planned target."""
    blocks = []
    ov = OVERRIDES.get(tg['name'], {})
    stun = old_hbstun(old_script(tg['script']))
    last = len(tg['wins']) - 1
    for i, w in enumerate(tg['wins']):
        sph = rig.spheres(w['limb'], 3, 1.0 if tg['name'] in GROW_EXCLUDE else HB_GROW) if w['limb'] else []
        if not sph:
            continue
        is_string = (tg['string'] and w['bdm']['type'] == 'Standard') or tg['name'] == 'Rush'
        angle, kbg, fkb, bkb = reaction_to_melee(w['bdm'], w['dmg'], tg['cls'], is_string)
        if tg['name'].startswith('rapid') or tg['name'] == 'nair':
            angle, kbg, fkb, bkb = (361, 30, 0, 10) if i < last else (angle if angle != 361 else 45, 60, 0, 25)
        if 'angle' in ov:
            angle, kbg, fkb, bkb = ov['angle'], 80, 0, 20 + 2 * w['dmg']
        if tg['cls'] == 'grab':
            angle, kbg, fkb, bkb = 361, 100, 0, 0
        if tg['name'] in SMASH_KB:
            w['dmg'] = SMASH_DMG[tg['name']]
            a0, kbg, bkb = SMASH_KB[tg['name']]
            angle, fkb = a0, 0
        w['final'] = dict(angle=angle, kbg=kbg, fkb=fkb, bkb=bkb)
        lines = []
        if tg['name'] == 'fair' and i == 0 and len(sph) >= 2:
            m = MARIO_FAIR
            c = (w['a'] + w['b']) // 2
            a_ = max(1, c - m['frames'] // 2)
            lines = []
            for k in range(m['spheres']):
                tok, x, y, z, r = sph[k]
                lines.append('hitbox slot=%d joint=@%s@ damage=%d size=%s x=%s y=%s z=%s angle=%d kbg=%d fkb=0 bkb=%d' % (k, tok, m['damage'], fmt(r), fmt(x), fmt(y), fmt(z), m['angle'], m['kbg'], m['bkb']))
            w['final'] = dict(angle=m['angle'], kbg=m['kbg'], fkb=0, bkb=m['bkb'], window=[a_, a_ + m['frames']])
            blocks.append((a_, lines, a_ + m['frames']))
            continue
        if tg['name'] in SPIKES and i == 0 and len(sph) >= 3:
            sp = SPIKES[tg['name']]
            a_, b_ = w['a'], w['b']
            p = a_ + max(0, (b_ - a_ - sp['frames'] + 1) // 2)
            tip, mid, inner = sph[0], sph[1], sph[2]
            tip_dmg = max(1, int(round(w['dmg'])))
            sour_dmg = max(1, int(round(w['dmg'] * SOUR['dmg_scale'])))
            def hb(slot, tok_xyzr, dmg, ang, kg, bk, size=None):
                tok, x, y, z, r = tok_xyzr
                return 'hitbox slot=%d joint=@%s@ damage=%d size=%s x=%s y=%s z=%s angle=%d kbg=%d fkb=0 bkb=%d' % (slot, tok, dmg, fmt(size if size else r), fmt(x), fmt(y), fmt(z), ang, kg, bk)
            lines = [hb(1, mid, sour_dmg, SOUR['angle'], SOUR['kbg'], SOUR['bkb']), hb(2, inner, sour_dmg, SOUR['angle'], SOUR['kbg'], SOUR['bkb']),
                     'wait_until %d' % p,
                     hb(0, tip, tip_dmg, sp['angle'], sp['kbg'], sp['bkb'], size=sp['radius']),
                     'wait_until %d' % (p + sp['frames']),
                     'clear_hitbox hit_idx=0',
                     hb(3, tip, sour_dmg, SOUR['angle'], SOUR['kbg'], SOUR['bkb'])]
            w['final'] = dict(angle=sp['angle'], kbg=sp['kbg'], fkb=0, bkb=sp['bkb'], spike_frames=[p, p + sp['frames']], spike_radius=sp['radius'])
            blocks.append((a_, lines, b_ + SOUR['late_frames']))
            continue
        slot0 = 0
        if tg['name'] in BODY_SPHERE and tg['cls'] != 'grab':
            # owner 2026-10-11 (usmash phantom hits): the arm spheres of an uppercut sit above Goku's head, higher than a Mario-sized fighter beside him, so the hit only grazed the top of
            # the hurtbox (damage, no knockback: a phantom hit). Falcon's usmash puts its hits on the body line (joint 4 = HipN, size 5.5); the same here: a sphere centred on the hips. It is
            # SLOT 0 with the full damage and knockback: when several of a move's hitboxes touch a victim the lowest slot is the one that counts, so a grazing arm sphere must not come first.
            tok_b, r_b = BODY_SPHERE[tg['name']]
            lines.append('hitbox slot=0 joint=@%s@ damage=%d size=%s x=0 y=0 z=0 angle=%d kbg=%d fkb=0 bkb=%d' % (tok_b, w['dmg'], fmt(r_b), angle, kbg, bkb))
            slot0 = 1
        for k, (tok, x, y, z, r) in enumerate(sph):
            d = max(1, int(round(w['dmg'] * INNER_SCALE[k]))) if tg['cls'] != 'grab' else 0
            kb = max(0, bkb + INNER_BKB[k]) if bkb else 0
            extra = ''
            if tg['cls'] == 'grab':
                extra = ' element=8 item_hit=1 clank=1 sfx_kind=2'
                angle, kbg, fkb, kb = 361, 100, 0, 0
            lines.append('hitbox slot=%d joint=@%s@ damage=%d size=%s x=%s y=%s z=%s angle=%d kbg=%d fkb=%d bkb=%d%s' % (
                k + slot0, tok, d, fmt(r), fmt(x), fmt(y), fmt(z), angle, kbg, fkb, kb, extra))
        if stun and tg['string'] and i == 0:
            lines.append('HBSTUN %d %d' % ((1 << len(sph)) - 1, stun))
        blocks.append((w['a'], lines, w['b']))
    return blocks


def main(argv):
    mode = argv[0] if argv else 'plan'
    rig = Rig()
    from xv2_to_artist import Source
    source = Source(PORT / 'ir/goku.xv2.ir.json')
    anim_rows = json.loads((PORT / 'ANIM-ROWS.json').read_text(encoding='utf-8'))['rows']
    combo = json.loads((PORT / 'combo/combo.json').read_text(encoding='utf-8'))
    plans = plan_targets(rig, source, anim_rows, combo)
    only = [x for x in os.environ.get('SAMPLES_ONLY', '').split(',') if x]   # write/plan only these moves (keeps hand-edited scripts such as Rush untouched)
    if only:
        plans = [p for p in plans if p['name'] in only]
    for tg in plans:
        if tg['status'] != 'ok':
            print('%-12s %s' % (tg['name'], tg['status']))
            continue
        blocks = render(rig, tg)
        print('%-12s bac=%s %s limb=%s' % (tg['name'], tg['bac'], tg['cls'], ','.join(sorted({str(w['limb']) for w in tg['wins']}))))
        for w, b in zip(tg['wins'], blocks):
            print('    f%d-%d xdmg=%s -> %s %s | %s' % (w['a'], w['b'], w['xdmg'], w['dmg'], w.get('final'), w['bdm']['type']))
        tg['blocks'] = blocks
    if mode == 'write':
        write_all(rig, plans, combo)
    return 0


HB_HEADER = ('# HB-SAMPLE (remake phase 2, 2026-10-11): a generated STARTING POINT, not an authored hitbox. Spheres ride the leading limb chain (tip, middle, inner),\n'
             '# sized from the mesh; timing, damage and reaction are derived from the XV2 hit entry (tools/remake_samples.py, REMAKE-SAMPLES.md). Edit it in the Workbench.\n')


def windows_of(rig, text):
    words = script.assemble(G.bind(text, rig.plan, rig.scale), rig.cfg['states'])
    return [[b['start'], b['end'] - b['start']] for b in report.frames(words)['hitboxes']]


def write_all(rig, plans, combo):
    g = json.loads(SG.FULL.read_text(encoding='utf-8'))
    n = 0
    for tg in plans:
        if tg['status'] == 'carry' and tg['name'] != 'bair':
            continue   # the grabs are Falcon cross-ports (tools/cross_port.py): their scripts are never regenerated or restored here
        if tg['status'] == 'carry':   # bair: the cross-port back air; its spheres were hand-authored earlier (owner: looks and works as intended)
            old = old_script(tg['script'])
            if old and 'hitbox' in old:
                (PORT / tg['script']).write_text('# HB-SAMPLE (remake phase 2): carried unchanged from the earlier hand-authored cross-port bair spheres (owner: looks and works as intended).\n' + old, encoding='utf-8', newline='\n')
                for m in g['moves']:
                    if m['name'] == 'bair':
                        m['hb'] = 'HB-SAMPLE'
                        m.pop('why_hb', None)
                        m['strike'] = [[6, 18]]
                        m['windows'] = windows_of(rig, old)
            continue
        if tg['status'] != 'ok' or not tg.get('blocks'):
            continue
        path = PORT / tg['script']
        old = path.read_text(encoding='utf-8')
        header = HB_HEADER + '# ' + tg['note'] + ('; limb %s' % ','.join(sorted({str(w['limb']) for w in tg['wins']}))) + '\n' + ('# SOURCE: ' + SOURCE_NOTE[tg['name']] + '\n' if tg['name'] in SOURCE_NOTE else '')
        path.write_text(build_script(old, tg['blocks'], header, IASA_AT.get(tg['name']),
                                                [(max(1, tg['wins'][0]['a'] - 2), CHARGE_LINE)] if tg['name'] in SMASH_CHARGE else None), encoding='utf-8', newline='\n')
        n += 1
        w0 = tg['wins'][0]
        fin = w0.get('final') or {}
        if tg['kind'] == 'combo':
            for s in combo['states']:
                if s['name'] == tg['name']:
                    s['hb'] = 'HB-SAMPLE'
                    s.pop('why_hb', None)
                    s['strike'] = [[w['a'], w['b']] for w in tg['wins']]
        else:
            for sec in ('moves', 'special_adaptations'):
                for m in g[sec]:
                    if m['name'] == tg['name']:
                        m['hb'] = 'HB-SAMPLE'
                        m.pop('why_hb', None)
                        d = m.setdefault('design', {})
                        d.update(damage=w0['dmg'], angle=fin.get('angle'), kbg=fin.get('kbg'), bkb=fin.get('bkb'))
                        m['sample'] = {'limb': sorted({str(w['limb']) for w in tg['wins']}), 'from': tg['note'], 'xv2_damage': [w['xdmg'] for w in tg['wins']],
                                       'reaction': sorted({w['bdm']['type'] for w in tg['wins']})}
                        m['strike'] = [[w['a'], w['b']] for w in tg['wins']]
                        m['windows'] = windows_of(rig, (PORT / tg['script']).read_text(encoding='utf-8'))
    SG.save(g)
    (PORT / 'combo/combo.json').write_text(json.dumps(combo, indent=2) + '\n', encoding='utf-8')
    print('wrote', n, 'scripts')


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
