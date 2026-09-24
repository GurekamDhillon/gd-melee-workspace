"""Meta Knight Phase 2: Brawl CHR0 -> Melee figatrees on MK's OWN joint tree (model/tools/skeleton.py), 1:1.

No retarget: joint i of the Melee tree IS Brawl bone i (0..76), the merged cape article bones are 77..103 (their
tracks come from the article clip that Brawl plays alongside the fighter clip, e.g. WpnMetaknightMantleB00Guard
with Guard), and 104 TransN2 is never keyed. A Brawl channel becomes one Melee track (rotation deg -> rad,
translation / scale 1:1), keys transplanted as HSD SPL keys, re-emitted densely where the sparse keys miss
BrawlLib's baked per-frame values (same encoder and checks as the Brawl Kirby port: brawl-kirby/tools/anim).

Motion rows: the clone's motion table is Kirby's (Phase 1 slot = Kirby clone), so every Kirby row that has an
animation gets an MK clip here - common rows from the Brawl-Kirby row map (same Brawl clip names), Kirby's special
rows from MK's specials, every other row (copy abilities, inhale, Kirby-only item rows) from a fallback clip. None
may keep a vanilla Kirby offset: the file is a NEW PlBmAJ.dat with MK clips only, and a 46-joint Kirby figatree on
a 105-joint model would pose the wrong joints anyway. Each sub-archive's public symbol is the row's figatree name
(the engine looks the tree up by that string); MK clips with no Kirby row are appended as extras.

TransN (root motion): anim/transn_policy.json, 'auto' per axis vs vanilla Melee Kirby's clip for the same motion
(exactly the Brawl Kirby rule), plus one MK rule: rows whose Melee flags have 0x80000000 (animation-driven: the
engine turns TransN into movement) keep Brawl's TransN on every axis. Every decision -> anim/transn_report.json.
Ledge get-ups (policy 'ledge_floor'): TransN.y's -0.003 rest on top of the ledge snaps to 0, or Melee never lands them.

usage: python mk_anim.py            -> anim/out/PlBmAJ.dat, anim/out/motion_rows.json, anim/transn_report.json
       (then mk_vis.py -> anim/vis_events.json; model/tools/report.py -> model/converter_report.json)
"""
import os, sys, json, math, struct
from collections import defaultdict, Counter
HERE = os.path.dirname(os.path.abspath(__file__)); ANIM = os.path.dirname(HERE); MK = os.path.dirname(ANIM)
EXP = os.path.join(os.path.dirname(os.path.dirname(MK)), "experiment"); BK = os.path.join(EXP, 'brawl-kirby')
sys.path.insert(0, os.path.join(BK, 'tools', 'anim'))
import figatree as F
import anim_convert as KAC            # Brawl Kirby encoder helpers (read-only use): _track_points, _dense_points, _check

OUT = os.path.join(ANIM, 'out')
KSYM = 'PlyKirby5K_Share_ACTION_%s_figatree'
ARR2TYPE = {0: 8, 1: 9, 2: 10, 3: 1, 4: 2, 5: 3, 6: 5, 7: 6, 8: 7}
TYPE2ARR = {v: k for k, v in ARR2TYPE.items()}
GROUP_OF = {0: 'scale', 1: 'scale', 2: 'scale', 3: 'rot', 4: 'rot', 5: 'rot', 6: 'trans', 7: 'trans', 8: 'trans'}
TOL = {'rot': 2e-3, 'trans': 2e-3, 'scale': 1e-3}
ORDER = [3, 4, 5, 6, 7, 8, 0, 1, 2]
AXES = {'x': 6, 'y': 7, 'z': 8}
ARTICLE = {  # MK clip -> the cape article clip Brawl anchors with it (Set Anchored Article SubAction)
    'Wait3': 'WpnMetaknightMantleA00Wait3', 'GuardOn': 'WpnMetaknightMantleB00GuardOn', 'Guard': 'WpnMetaknightMantleB00Guard',
    'GuardOff': 'WpnMetaknightMantleB00GuardOff', 'GuardDamage': 'WpnMetaknightMantleB01GuardDamage',
    'EscapeN': 'WpnMetaknightMantleB02EscapeN', 'EscapeF': 'WpnMetaknightMantleB02EscapeF', 'EscapeB': 'WpnMetaknightMantleB02EscapeB',
    'SpecialLwStart': 'WpnMetaknightMantleD03SpecialLwStart', 'SpecialAirLwStart': 'WpnMetaknightMantleD03SpecialAirLwStart',
    'SpecialLw': 'WpnMetaknightMantleD03SpecialLw', 'SpecialAirLw': 'WpnMetaknightMantleD03SpecialAirLw',
    'SpecialLwF': 'WpnMetaknightMantleD03SpecialLwF', 'SpecialAirLwF': 'WpnMetaknightMantleD03SpecialAirLwF',
    'SpecialLwB': 'WpnMetaknightMantleD03SpecialLwB', 'SpecialAirLwB': 'WpnMetaknightMantleD03SpecialAirLwB',
    'SpecialLwEnd': 'WpnMetaknightMantleD03SpecialLwEnd', 'SpecialAirLwEnd': 'WpnMetaknightMantleD03SpecialAirLwEnd',
    'AppealHi': 'WpnMetaknightMantleJ01AppealU',
    # results screen (FitMetaknightResult.pac: Win1 / Win2 anchor article 1 = the cape article with these clips)
    'Win1': 'WpnMetaknightMantleJ02Win1', 'Win2': 'WpnMetaknightMantleJ02Win2',
}
# Melee's demo motion table (ftData x14, Kirby's layout): index -> (Kirby demo name, MK clip). The results screen plays
# 0/2/5 for winners (pad L / R / Z or random, then the Wait loop) and 9 for losers (gm_1798.c); 7/8 are the 1P
# 'Selected' poses MK has none of (Wait1); 4 is Kirby's script-only hole; 10-17 (intro / ending / vi) live in other files.
DEMO = [(0, 'Win1', 'Win1'), (1, 'Win1Wait', 'Win1Wait'), (2, 'Win2', 'Win2'), (3, 'Win2Wait', 'Win2Wait'),
        (5, 'Win3', 'Win3'), (6, 'Win3Wait', 'Win3Wait'), (7, 'Selected', 'Wait1'), (8, 'SelectedWait', 'Wait1'), (9, 'Lose', 'Lose')]
DEMO_FILE, DEMO_SYM = 'GmRstMBm.dat', 'ftDemoResultMotionFileMetaknightBm'
SMASH = "Brawl Start + attack clips joined; the Melee script's SmashCharge frame must equal the Start length (%d) or the charge pose freezes mid-swing"

# ------------------------------------------------------------------ row table
# Kirby row -> MK clip where the Brawl-Kirby row map (brawl-kirby/phase2/motion_rows.json) names a clip MK lacks.
SUBST = {
    46: ('Attack100Start', 'MK has no single jab (Brawl slots 0x48-0x4A empty): Attack11 plays the rapid-jab start'),
    47: ('Attack100Start', 'no Attack12 either: rapid-jab start'),
    53: ('AttackS3S', 'MK has no angled forward tilt: AttackS3Hi = AttackS3S'),
    57: ('AttackS3S', 'MK has no angled forward tilt: AttackS3Lw = AttackS3S'),
    60: (['AttackS4Start', 'AttackS4S'], 'no angled forward smash: AttackS4Hi = AttackS4S. ' + SMASH % 21),
    64: (['AttackS4Start', 'AttackS4S'], 'no angled forward smash: AttackS4Lw = AttackS4S. ' + SMASH % 21),
    62: (['AttackS4Start', 'AttackS4S'], SMASH % 21),
    66: (['AttackHi4Start', 'AttackHi4'], SMASH % 4),
    67: (['AttackLw4Start', 'AttackLw4'], SMASH % 1),
    32: ('SquatWait', 'no SquatWait2: SquatWait'),
    239: ('AppealLw', 'Melee taunt = Brawl down taunt (as the Brawl Kirby port)'),
    240: ('AppealLw', 'Melee taunt = Brawl down taunt (as the Brawl Kirby port)'),
    # Kirby's special rows -> MK's specials (Phase 1 builds MK's specials on Kirby's special states)
    305: ('SpecialNStart', 'N-B start (Mach Tornado)'), 320: ('SpecialAirNStart', 'air N-B start'),
    306: ('SpecialNSpin', 'Mach Tornado spin loop'), 308: ('SpecialNSpin', 'Mach Tornado spin loop (capture row)'),
    321: ('SpecialNSpin', 'Mach Tornado spin loop (air)'), 307: ('SpecialNEnd', 'Mach Tornado end'),
    322: ('SpecialSStart', 'S-B start (Drill Rush); SpecialSDrill / SpecialSEnd are extras'),
    323: ('SpecialAirSStart', 'air S-B start; SpecialAirSEnd is an extra'),
    324: ('SpecialHi', 'Shuttle Loop (ground)'), 325: ('SpecialHiLoop', 'Shuttle Loop loop'),
    326: ('SpecialHiEnd', 'Shuttle Loop end'), 327: ('SpecialHiEnd', 'Shuttle Loop end'),
    328: ('SpecialAirHiStart', 'Shuttle Loop (air start)'), 329: ('SpecialHiLoop', 'Shuttle Loop loop (air)'),
    330: ('SpecialHiEnd', 'Shuttle Loop end (air)'), 331: ('SpecialHiEnd', 'Shuttle Loop end (air)'),
    332: ('SpecialLwStart', 'Dimensional Cape start'), 333: ('SpecialLw', 'Dimensional Cape (neutral)'),
    334: ('SpecialLwEnd', 'Dimensional Cape end'),
    335: ('SpecialAirLwStart', 'Dimensional Cape start (air)'), 336: ('SpecialAirLw', 'Dimensional Cape (air)'),
    337: ('SpecialAirLwEnd', 'Dimensional Cape end (air)'),
    # Kirby-thrown / swallowed victim poses provided by this fighter's file
    262: ('ThrownF', 'TKirbyThrowF: victim pose this fighter provides (remapped by parts table) - MK ThrownF'),
    263: ('ThrownB', 'TKirbyThrowB -> MK ThrownB'), 264: ('ThrownHi', 'TKirbyThrowHi -> MK ThrownHi'),
    265: ('ThrownLw', 'TKirbyThrowLw -> MK ThrownLw'),
    284: ('Swallowed', 'TKirbySpecialNDrink -> MK Swallowed'), 285: ('Swallowed', 'TKirbySpecialNSpit -> MK Swallowed'),
    294: ('Swallowed', 'TYoshiSpecialN -> MK Swallowed'),
    238: ('Wait1', 'Melee Entry is a 10f code-driven stub; MK EntryL/R (121f warp entrance) is an extra'),
    145: ('ItemScrew', 'no air screw clip: ItemScrew'), 146: ('ItemScrewFall', 'ItemScrewDamage -> ItemScrewFall'),
    147: ('ItemScrewFall', 'ItemScrewDamage -> ItemScrewFall'),
    134: ('Fall', 'no parasol in Brawl: Fall'), 135: ('Fall', 'no parasol in Brawl: Fall'), 136: ('Fall', 'no parasol in Brawl: Fall'),
    148: ('FuraFura', 'ItemBlind (no Brawl clip): FuraFura'),
}
KEEP_EXTRA = {'StepPose', 'LandingLight'}
EXTRA_NOTE = {
    'GlideStart': 'glide (Geno v2 state)', 'GlideDirection': 'glide', 'GlideWing': 'glide', 'GlideAttack': 'glide attack',
    'GlideEnd': 'glide end', 'GlideLanding': 'glide landing',
    'AttackS3S2': 'forward tilt hit 2', 'AttackS3S3': 'forward tilt hit 3',
    'SpecialSDrill': 'Drill Rush loop', 'SpecialSEnd': 'Drill Rush end', 'SpecialAirSEnd': 'Drill Rush end (air)',
    'SpecialAirNEnd': 'Mach Tornado end (air)',
    'SpecialLwF': 'Dimensional Cape forward', 'SpecialLwB': 'Dimensional Cape back',
    'SpecialAirLwF': 'Dimensional Cape forward (air)', 'SpecialAirLwB': 'Dimensional Cape back (air)',
    'Wait3': 'idle 3 (cape article)', 'AppealHi': 'up taunt', 'AppealS': 'side taunt',
    'EntryL': 'entrance', 'EntryR': 'entrance', 'Win1': 'victory', 'Win2': 'victory', 'Win3': 'victory',
    'Win1Wait': 'victory loop', 'Win2Wait': 'victory loop', 'Win3Wait': 'victory loop', 'Lose': 'clapping',
    'LandingLight': 'light landing', 'StepPose': 'footstool', 'Swing4Bat': 'bat smash',
}


def load_json(p):
    return json.load(open(p)) if os.path.exists(p) else None


def mk_clip(name):
    return load_json(os.path.join(ANIM, 'brawl', 'chr0', name + '.json'))


def article_clip(name):
    return load_json(os.path.join(ANIM, 'brawl_mantle', 'chr0', name + '.json')) or         load_json(os.path.join(ANIM, 'brawl_mantle_result', 'chr0', name + '.json'))


def clip_index():
    return json.load(open(os.path.join(ANIM, 'brawl', 'chr0_index.json')))


def joints():
    return json.load(open(os.path.join(MK, 'model', 'work', 'skeleton.json')))['joints']


def merged(names):
    """MK clip(s) played back to back, with the anchored cape article's bones merged in (prefix Mt, TopN dropped)."""
    if isinstance(names, str): names = [names]
    if len(names) == 1 and names[0].startswith('pose:'):
        # a still 2-frame pose (frame 0 of an MK clip): the fallback for rows MK can't reach (copy abilities, ...)
        src = mk_clip(names[0][5:]); bones = {}
        for bn, bd in src['bones'].items():
            b0 = bd['baked'][0]; keyed = sorted({k[0] for k in bd['keys']})
            bones[bn] = {'keys': [[a, 0, b0[a], 0.0] for a in keyed], 'baked': [b0, b0]}
        return {'name': names[0], 'frames': 2, 'loop': False, 'bones': bones}
    cs = []
    for n in names:
        c = mk_clip(n)
        if c is None: raise KeyError('no MK clip ' + n)
        c = {'name': c['name'], 'frames': c['frames'], 'loop': c['loop'], 'bones': dict(c['bones'])}
        an = ARTICLE.get(n)
        if an:
            a = article_clip(an); c['article'] = an; c['article_frames'] = a['frames']
            for bn, bd in a['bones'].items():
                if bn == 'TopN': continue
                bk = bd['baked']
                if len(bk) < c['frames']: bk = bk + [bk[-1]] * (c['frames'] - len(bk))    # article shorter: hold
                keys = [k for k in bd['keys'] if k[1] < c['frames']]
                c['bones']['Mt' + bn] = {'keys': keys, 'baked': bk[:c['frames']]}
        cs.append(c)
    if len(cs) == 1: return cs[0]
    out = {'name': '+'.join(names), 'frames': sum(c['frames'] for c in cs), 'loop': False, 'bones': {},
           'article': [c.get('article') for c in cs]}
    allb = set().union(*[c['bones'] for c in cs])
    for bn in allb:
        keys = []; baked = []; off = 0
        for c in cs:
            bd = c['bones'].get(bn)
            if bd is None:
                baked += [baked[-1] if baked else None] * c['frames']
            else:
                keys += [[k[0], k[1] + off, k[2], k[3]] for k in bd['keys']]; baked += bd['baked']
            off += c['frames']
        rest = REST().get(bn)
        first = rest if rest is not None else next(b for b in baked if b is not None)
        baked = [b if b is not None else first for b in baked]
        out['bones'][bn] = {'keys': keys, 'baked': baked}
    return out


_REST = None
def REST():
    """Brawl bind (= Melee rest) per joint name as a baked row [sx,sy,sz, rx,ry,rz (deg), tx,ty,tz]."""
    global _REST
    if _REST is None: _REST = {j['name']: list(j['scale']) + list(j['rot_deg']) + list(j['trans']) for j in joints()}
    return _REST


def closed_loop(c):
    return all(max(abs(x - y) for x, y in zip(b['baked'][0], b['baked'][-1])) < 1e-3 for b in c['bones'].values())


# ------------------------------------------------------------------ TransN policy
_TP = None; _MAJ = None; _MROWS = None


def melee_rows():
    global _MROWS
    if _MROWS is None: _MROWS = json.load(open(os.path.join(BK, 'analysis', 'melee_kirby.json')))['motion_table']
    return _MROWS


def melee_transn(mname):
    """Vanilla Melee Kirby TransN per axis for figatree mname: {axis: (min, max, first, last)} or None."""
    global _MAJ
    if _MAJ is None:
        raw = open(os.path.join(BK, 'disc', 'PlKbAJ.dat'), 'rb').read(); _MAJ = {}
        for o, s in F.walk_aj(raw):
            sym, t = F.parse_archive(raw[o:o + s]); _MAJ[sym] = t
    t = _MAJ.get(KSYM % mname)
    if t is None: t = demo_kirby().get(KSYM % mname)
    if t is None: return None
    tr = {x['type']: x for x in t['joints'][1]}; fr = int(t['frames']); out = {}
    for ax, a in AXES.items():
        x = tr.get(ARR2TYPE[a])
        v = [F.evaluate(x['keys'], f) for f in range(fr + 1)] if x else [0.0]
        out[ax] = (min(v), max(v), v[0], v[-1])
    return out


_MDEMO = None
def demo_kirby():
    """Vanilla Kirby's results-screen figatrees (GmRstMKb.dat, ACE disc) by symbol: the TransN base of the demo clips."""
    global _MDEMO
    if _MDEMO is None:
        sys.path.insert(0, r"C:/Users/Gurek/Desktop/GD's Melee/tools/mex_port"); import mex_hsd
        a = mex_hsd.Archive(mex_hsd.Gcm("C:/iso/SSBM ACE Build v2.0.0.iso").read('GmRstMKb.dat')); raw = bytes(a.data); _MDEMO = {}
        for o, sz in F.walk_aj(raw):
            sym, t = F.parse_archive(raw[o:o + sz]); _MDEMO[sym] = t
    return _MDEMO


def apply_transn_policy(c, mname, rows):
    global _TP
    if _TP is None: _TP = json.load(open(os.path.join(ANIM, 'transn_policy.json')))
    eps = _TP.get('eps', 0.05)
    mr = {r['index']: r for r in melee_rows()}
    anim_driven = [r for r in rows if int(mr[r]['flags'], 16) & 0x80000000]
    ov = _TP['overrides'].get(c['name'], _TP['overrides'].get(mname))
    rule_src = 'override' if ov is not None else ('anim_driven_rows' if anim_driven else 'default')
    if ov is None and not rows: ov = _TP.get('extras', 'keep'); rule_src = 'extras'
    if ov is None: ov = _TP['anim_driven_rows'] if anim_driven else _TP['default']
    if isinstance(ov, str): ov = {ax: ov for ax in AXES}
    scale = ov.get('scale', {})
    mel = melee_transn(mname) if mname else None
    rec = {'clip': c['name'], 'melee_base': (KSYM % mname) if mname else None, 'melee_base_found': mel is not None,
           'rows': rows, 'rows_anim_driven_0x80000000': anim_driven, 'rule_source': rule_src, 'axes': {}}
    bd = c['bones'].get('TransN')
    for ax, a in AXES.items():
        col = [r[a] for r in bd['baked']] if bd else [0.0]
        b_rng = max(col) - min(col)
        m = mel[ax] if mel else None
        m_has = bool(m) and (m[1] - m[0] > eps or max(abs(m[0]), abs(m[1])) > eps)
        rule = ov.get(ax, 'auto')
        why = rule
        if rule == 'auto': rule = 'keep' if m_has else 'strip'; why = 'auto: Melee base %s' % ('moves/offsets on this axis' if m_has else ('still on this axis' if m else 'missing'))
        d = {'brawl_min': round(min(col), 3), 'brawl_max': round(max(col), 3), 'brawl_net': round(col[-1] - col[0], 3),
             'melee_min': round(m[0], 3) if m else None, 'melee_max': round(m[1], 3) if m else None,
             'melee_net': round(m[3] - m[2], 3) if m else None, 'melee_has': m_has, 'rule': why}
        if b_rng <= 1e-4:
            d['decision'] = 'none'
        elif rule == 'strip':
            v0 = col[0]
            bd['baked'] = [r[:a] + [v0] + r[a + 1:] for r in bd['baked']]
            bd['keys'] = [k for k in bd['keys'] if k[0] != a] + [[a, 0, v0, 0.0]]
            d['decision'] = 'strip'; d['held_at'] = round(v0, 4)
        else:
            s = scale.get(ax, 1.0); d['decision'] = 'keep'
            if s != 1.0:
                v0 = col[0]
                bd['baked'] = [r[:a] + [v0 + (r[a] - v0) * s] + r[a + 1:] for r in bd['baked']]
                bd['keys'] = [k if k[0] != a else [k[0], k[1], v0 + (k[2] - v0) * s, k[3] * s] for k in bd['keys']]
                d['scale'] = s
        rec['axes'][ax] = d
    # Ledge get-ups (CliffClimb / CliffAttack / CliffEscape): Melee's ftCo_CliffClimb_Phys puts the hanging fighter at
    # ledge + TransN and only lands him once TransN.z >= 0 AND TransN.y >= 0 on the same frame. Brawl's clips settle at
    # y = -0.003 (CHR0 noise; Melee Kirby's end at exactly 0), so MK never landed: the stage wall held him at the ledge x
    # and he fell and regrabbed when the clip ended. Snap the near-zero negatives on the top of the climb to 0.
    lf = _TP.get('ledge_floor', {})
    if bd and c['name'] in lf.get('clips', []):
        a = AXES['y']; within = lf.get('within', 0.05); n = 0
        for r in bd['baked']:
            if -within <= r[a] < 0: r[a] = 0.0; n += 1
        for k in bd['keys']:
            if k[0] == a and -within <= k[2] < 0: k[2] = 0.0; n += 1
        rec['ledge_floor'] = {'axis': 'y', 'within': within, 'snapped': n}
    return rec


# ------------------------------------------------------------------ convert
def track_points(bd, a, frames, loop):
    """Brawl Kirby's _track_points, except the tail after the last Brawl key: Kirby's helper closes a non-loop clip
    with a flat point at baked[last key], but BrawlLib keeps interpolating past the last key (the article clips end
    3-4 frames after it), which forced whole tracks dense. Here the tail frames are keyed from the baked values."""
    pts, baked = KAC._track_points(bd, a, frames, loop)
    if pts is None or loop or len(pts) < 3: return pts, baked
    last = pts[-2][0]
    if pts[-1][0] == frames and last < frames - 1 and len(baked) >= frames:
        tail = []
        for f in range(last + 1, frames + 1):
            v = baked[min(f, len(baked) - 1)]
            vp = baked[min(f - 1, len(baked) - 1)]; vn = baked[min(f + 1, len(baked) - 1)]
            tail.append((f, v, (vn - vp) / 2))
        pts = pts[:-1] + tail
    return pts, baked


def convert(clip, sym, mname, rows, frames=None):
    c = merged(clip)
    transn = apply_transn_policy(c, mname, rows)
    frames = frames or c['frames']; loop = c['loop']
    J = joints()
    tracks = []; rep = {'clip': c['name'], 'article': c.get('article'), 'brawl_frames': c['frames'], 'frames': frames,
                        'tracks': 0, 'dense_tracks': 0, 'f32_tracks': 0, 'max_err': {'rot': 0.0, 'trans': 0.0, 'scale': 0.0},
                        'transn': transn, 'unkeyed_off_rest': []}
    for j in J:
        bd = c['bones'].get(j['name']); tr = []
        if bd:
            rest = REST().get(j['name'])
            for a in ORDER:
                pts, baked = KAC._track_points(bd, a, frames, loop)
                if pts is None:
                    # An unkeyed channel of a bone the clip DOES animate is not "use the bind value": a CHR0 entry
                    # defines the whole SRT, so BrawlLib bakes the entry's fixed value (0 for a translation the
                    # entry leaves out). With no Melee track the joint would fall back to its rest pose instead -
                    # e.g. SquatWait / AttackLw3 key only XRotN's scale, Brawl holds XRotN.y at 0 but the rest pose
                    # is 4.6, which lifted MK ~4.1 units off the floor while crouching and during down tilt.
                    col = [r[a] for r in bd['baked']]
                    if rest is None or max(abs(v - rest[a]) for v in col) <= 1e-4: continue
                    pts = KAC._dense_points(baked, frames, loop)
                    if max(col) - min(col) <= 1e-6: pts = [(0, baked[0], 0.0), (frames, baked[0], 0.0)]
                    rep['unkeyed_off_rest'].append([j['name'], a, round(col[0], 4), round(rest[a], 4)])
                g = GROUP_OF[a]
                best = None
                # cheapest encoding within tolerance: Brawl keys s16 -> f32 -> Brawl keys + keyed tail -> dense
                cands = [pts]
                tp, _ = track_points(bd, a, frames, loop)
                if tp != pts: cands.append(tp)
                for cp in cands:
                    for fr in ((None, None), (0x00, 0x00)):
                        body, fv, fs, keys = F.encode_spline(cp, *fr)
                        err = KAC._check(keys, baked, frames)
                        if err <= TOL[g]: best = (body, fv, fs, keys, err); break
                    if best: break
                if best is None:
                    dp = KAC._dense_points(baked, frames, loop)
                    body, fv, fs, keys = F.encode_spline(dp)
                    err = KAC._check(keys, baked, frames)
                    if err > TOL[g]:
                        body, fv, fs, keys = F.encode_spline(dp, 0x00, 0x00)
                        err = KAC._check(keys, baked, frames)
                    best = (body, fv, fs, keys, err); rep['dense_tracks'] += 1
                body, fv, fs, keys, err = best
                rep['max_err'][g] = max(rep['max_err'][g], err)
                tr.append((ARR2TYPE[a], body, fv, fs))
        tracks.append(tr); rep['tracks'] += len(tr)
    unused = sorted(set(c['bones']) - {j['name'] for j in J})
    rep['brawl_bones_not_in_tree'] = unused
    arc = F.build_tree_archive(sym, frames, tracks)
    rep['size'] = len(arc); rep['symbol'] = sym
    return arc, rep, c


def validate(arc, c, frames):
    """Independent re-parse (figatree.parse_archive + evaluate vs the Brawl baked values, per joint name) and
    Shadow's figa.py key walker (overrun check)."""
    sym, t = F.parse_archive(arc)
    J = joints(); worst = {'rot': 0.0, 'trans': 0.0, 'scale': 0.0}
    assert len(t['joints']) == len(J), (len(t['joints']), len(J))
    R = REST(); worst['untracked'] = 0.0
    for ji, tr in enumerate(t['joints']):
        bd = c['bones'].get(J[ji]['name'])
        if bd is not None:      # a channel with no track plays the rest pose: Brawl's baked value must equal it
            have = {TYPE2ARR[x['type']] for x in tr}
            for a in range(9):
                if a in have: continue
                worst['untracked'] = max(worst['untracked'], max(abs(r[a] - R[J[ji]['name']][a]) for r in bd['baked'][:frames]))
        bk = bd['baked'] if tr else None
        for x in tr:
            a = TYPE2ARR[x['type']]; g = GROUP_OF[a]
            for f in range(min(len(bk), frames)):
                v = math.radians(bk[f][a]) if 3 <= a <= 5 else bk[f][a]
                worst[g] = max(worst[g], abs(F.evaluate(x['keys'], f) - v))
    sys.path.insert(0, os.path.join(EXP, 'Shadow', 'analysis', '02_assets_scripts'))
    sys.path.insert(0, r"C:/Users/Gurek/Desktop/GD's Melee/tools/mex_port")
    import figa, mex_hsd
    a = mex_hsd.Archive(arc).relocate(0)
    r = figa.figatree(a, a.publics[0][1])
    return {'reparse_max_err': {k: round(v, 5) for k, v in worst.items()}, 'figa_py_overruns': r['bad'], 'nodes': len(t['joints'])}


# ------------------------------------------------------------------ table
def build_table():
    idx = clip_index()
    rows = melee_rows()
    kmap = json.load(open(os.path.join(BK, 'phase2', 'motion_rows.json')))['clips']
    row_clip = {}; notes = {}
    for e in kmap:
        names = e['brawl_clip'].split('+')
        for r in e['rows']:
            if all(n in idx for n in names):
                row_clip[r] = names if len(names) > 1 else names[0]; notes[r] = e.get('note', '')
    for r, (cl, note) in SUBST.items():
        row_clip[r] = cl; notes[r] = note
    # every other row with an animation: fallback by kind
    for r in rows:
        if r['index'] in row_clip or int(r['anim_size'], 16) == 0: continue
        n = r['name']; fig = (r['figatree'] or '')[len('PlyKirby5K_Share_ACTION_'):-len('_figatree')]
        if fig in idx: row_clip[r['index']] = fig; notes[r['index']] = 'same-name MK clip'; continue
        air = 'Air' in n or 'Jump' in n or 'Fall' in n
        row_clip[r['index']] = 'pose:Fall' if air else 'pose:Wait1'
        notes[r['index']] = 'FALLBACK (%s row, no MK clip): still pose, frame 0 of %s' % (r['category'], 'Fall' if air else 'Wait1')
    return row_clip, notes


def build_demo():
    """anim/out/GmRstMBm.dat: MK's results-screen motions (DEMO), one figatree sub-archive per entry, in an HSD archive
    whose one public (DEMO_SYM) is the blob, as vanilla GmRstMKb.dat (no relocations). The sub-archive symbols are
    Kirby's demo names (the x14 rows keep their name strings). TransN: the same policy, Kirby's result clip as the base.
    Writes anim/out/demo_rows.json (index, clip, offset, size, frames) for install_mk.py."""
    blob = bytearray(); rows = []
    for idx, kname, clip in DEMO:
        sym = KSYM % kname
        c0 = merged(clip)
        frames = c0['frames'] - 1 if c0['loop'] and closed_loop(c0) and c0['frames'] > 2 else c0['frames']
        arc, rep, c = convert(clip, sym, kname, [], frames)
        v = validate(arc, c, frames)
        while len(blob) % 0x20: blob.append(0xFF)
        off = len(blob); blob.extend(arc)
        rows.append({'index': idx, 'name': kname, 'symbol': sym, 'brawl_clip': clip, 'article_clip': c.get('article'),
                     'offset': off, 'size': len(arc), 'frames': frames, 'brawl_frames': c['frames'], 'loop': c['loop'],
                     'max_err': {k: round(x, 5) for k, x in rep['max_err'].items()}, 'validate': v, 'transn': rep['transn']})
    while len(blob) % 0x20: blob.append(0)
    strtab = DEMO_SYM.encode() + bytes(1)
    body = bytes(blob) + struct.pack('>2I', 0, 0) + strtab
    hdr = struct.pack('>5I', 0x20 + len(body), len(blob), 0, 1, 0) + bytes(12)
    open(os.path.join(OUT, DEMO_FILE), 'wb').write(hdr + body)
    json.dump({'file': DEMO_FILE, 'symbol': DEMO_SYM, 'bytes': 0x20 + len(body), 'rows': rows}, open(os.path.join(OUT, 'demo_rows.json'), 'w'), indent=1)
    print('demo', DEMO_FILE, 0x20 + len(body), 'bytes:', ', '.join('%d %s %df' % (r['index'], r['brawl_clip'], r['frames']) for r in rows))
    return rows


def main():
    os.makedirs(OUT, exist_ok=True)
    idx = clip_index(); rows = {r['index']: r for r in melee_rows()}
    row_clip, notes = build_table()
    # one sub-archive per distinct clip (and TransN base / anim-driven flag, which change the TransN decision).
    # Its symbol is the first row's figatree name; the other rows of the group are RENAMED at install (their name
    # pointer -> this symbol), so e.g. 6 Swing1 rows or 140 copy-ability fallback rows share one tree.
    groups = defaultdict(list)
    for r, cl in sorted(row_clip.items()):
        fig = rows[r]['figatree'][len('PlyKirby5K_Share_ACTION_'):-len('_figatree')]
        base = fig if not (isinstance(cl, str) and cl.startswith('pose:')) else None
        drv = bool(int(rows[r]['flags'], 16) & 0x80000000)
        if isinstance(cl, str) and cl.startswith('pose:'): drv = False
        groups[(json.dumps(cl), base if (isinstance(cl, str) and not cl.startswith('pose:')) or not isinstance(cl, str) else None, drv)].append(r)
    aj = bytearray(); clips_out = []; report = {'clips': [], 'failed': [], 'sizes_over_0x8000': [], 'sizes_over_0x10000': []}
    transn = []
    def add(cl, sym, mname, rs, note, category):
        c0 = merged(cl); frames = c0['frames'] - 1 if isinstance(cl, str) and c0['loop'] is not None and closed_loop(c0) and c0['frames'] > 2 else c0['frames']
        try:
            arc, rep, c = convert(cl, sym, mname, rs, frames)
            v = validate(arc, c, frames)
        except Exception as ex:
            report['failed'].append({'clip': cl, 'symbol': sym, 'rows': rs, 'error': repr(ex)}); return
        while len(aj) % 0x20: aj.append(0xFF)
        off = len(aj); aj.extend(arc)
        ent = {'brawl_clip': c['name'], 'melee_name': mname, 'symbol': sym, 'rows': rs, 'category': category,
               'offset': off, 'size': len(arc), 'offset_hex': '0x%X' % off, 'size_hex': '0x%X' % len(arc),
               'frames': frames, 'brawl_frames': c['frames'], 'closed_loop_n_minus_1': frames != c['frames'],
               'vanilla_frames': rows[rs[0]]['anim_frames'] if rs else None, 'note': note, 'article_clip': c.get('article'),
               'tracks': rep['tracks'], 'dense_tracks': rep['dense_tracks'], 'max_err': {k: round(x, 5) for k, x in rep['max_err'].items()},
               'validate': v, 'transn': rep['transn'], 'unkeyed_off_rest': rep['unkeyed_off_rest']}
        clips_out.append(ent)
        if len(arc) > 0x8000: report['sizes_over_0x8000'].append((c['name'], len(arc)))
        if len(arc) > 0x10000: report['sizes_over_0x10000'].append((c['name'], len(arc)))
    for (clj, base, drv), rs in sorted(groups.items(), key=lambda x: x[1][0]):
        cl = json.loads(clj)
        if isinstance(cl, str) and cl.startswith('pose:'):
            sym = KSYM % ('MkPose' + cl[5:]); mname = None
        else:
            sym = rows[rs[0]]['figatree']; mname = base
        cat = Counter(rows[r]['category'] for r in rs).most_common(1)[0][0]
        add(cl, sym, mname, rs, '; '.join(sorted({notes[r] for r in rs if notes.get(r)})), cat)
        clips_out[-1]['rename_rows'] = [r for r in rs if rows[r]['figatree'] != sym] if clips_out and clips_out[-1]['symbol'] == sym else []
    used = set()
    for cl in row_clip.values(): used.update([cl] if isinstance(cl, str) else cl)
    extras = []
    for n in sorted(idx):
        if n in used: continue
        if n.startswith(('Ladder', 'Swim', 'Final', 'Item', 'Heavy', 'Light', 'Smash', 'Slip', 'Ottotto', 'Step', 'Gekikara', 'Win', 'Lose', 'Entry', 'Thrown')) \
                and n not in KEEP_EXTRA:
            extras.append({'clip': n, 'converted': False, 'why': 'no Melee state (ladder/swim/Final Smash/Brawl-only item, tripping, footstool, '
                                                                 'result screen / entrance: those use the fighter demo files, not this AJ)'})
            continue
        add(n, KSYM % n, None, [], EXTRA_NOTE.get(n, 'MK clip with no Kirby motion row (extra, not pointed to)'), 'extra')
        extras.append({'clip': n, 'converted': True})
    while len(aj) % 0x20: aj.append(0xFF)
    open(os.path.join(OUT, 'PlBmAJ.dat'), 'wb').write(aj)
    mr = {'aj_file': 'PlBmAJ.dat', 'aj_size': len(aj), 'joint_count': len(joints()),
          'row_fields': 'motion table = ftData+0xC, 0x18-byte rows {name*, u32 AJ offset, u32 size, script*, flags, ...}; '
                        'the install script writes offset/size of the entry whose symbol equals the row name',
          'clips': [c for c in clips_out if c['rows']], 'extras': [c for c in clips_out if not c['rows']],
          'rows_without_animation': sorted(r for r in rows if int(rows[r]['anim_size'], 16) == 0),
          'failed': report['failed'], 'skipped_brawl_clips': [e for e in extras if not e['converted']]}
    json.dump(mr, open(os.path.join(OUT, 'motion_rows.json'), 'w'), indent=1)
    tr = [dict(c['transn'], brawl_clip=c['brawl_clip'], extra=not c['rows']) for c in clips_out
          if any(d['decision'] != 'none' for d in c['transn']['axes'].values())]
    json.dump({'policy': 'anim/transn_policy.json', 'clips': tr}, open(os.path.join(ANIM, 'transn_report.json'), 'w'), indent=1)
    nrows = sum(len(c['rows']) for c in clips_out)
    print('sub-archives', len(clips_out), 'rows pointed', nrows, 'extras', len(mr['extras']), 'failed', len(report['failed']),
          'AJ bytes', len(aj), '>0x8000', len(report['sizes_over_0x8000']), '>0x10000', report['sizes_over_0x10000'])
    build_demo()
    for c in clips_out:
        flag = '' if max(c['max_err'].values()) < 2e-3 and not c['validate']['figa_py_overruns'] and c['validate']['reparse_max_err']['untracked'] < 2e-3 else '  <-- check'
        print('%-30s %-40s rows=%-16s f=%3d/%-5s size=%6d dense=%3d err=%s%s' % (c['brawl_clip'][:30], c['symbol'][24:-9][:40], str(c['rows'])[:16], c['frames'],
              c['vanilla_frames'], c['size'], c['dense_tracks'], max(c['max_err'].values()), flag))
    return mr


if __name__ == '__main__':
    main()
