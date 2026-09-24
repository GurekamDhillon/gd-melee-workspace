"""Meta Knight's eye animation: Brawl's 111 SRT0 clips on the eye material (medama) -> Melee eye texture states.

Brawl animates the texture matrix (scale + translation, Maya mode) of the two eye layers of 'medama' continuously:
Texture0 (TexCoord0, the eye on +x) and Texture1 (TexCoord1, the eye on -x). Melee's fighters set their eye texture
anim to a FRAME from the subaction script (SetTexAnim, ftAction_800726F4: tobj idx [+ idx2], frame 0..1023) and the
engine resets it to frame 0 at every motion change (fighter.c: ftAnim_80070654). So here:
  - every Brawl frame's pair of texture matrices is converted to HSD TObj SRT (tobj.c MakeTextureMtx:
        uv' = (repeat / scale) * (uv - translate)
    Brawl Maya (NW4R TexSrtMaya, rotation 0 on every MK key):  u' = sx * (u - tx),   v' = sy * (v + ty) + 1 - sy
    ->  HSD scale = 1 / s,  translate.u = tx,  translate.v = -ty - (1 - sy) / sy)
    (check: Brawl's 0.6667-scale keys then zoom about the eye texture's centre (0.5, 0.5), the fixed point of both maps)
  - the pairs are quantised into STATES (greedy, first-seen order, state 0 = identity = open eyes, the reset state):
    a frame joins a state when both eye maps agree within TOL in uv over the eye's opaque texture region
  - each clip becomes a list of (frame, state) change events: the script pass (tools/build_mk_visuals.py) inserts
    SetTexAnim(0, state, idx2 = 1) at those frames; the costume matanim (model/tools/mkbuild) holds, per eye TObj, a
    constant-key SCAU/SCAV/TRAU/TRAV track whose value at frame k is state k.

usage: python mk_eyes.py   -> anim/out/eye_states.json
"""
import os, json, math
HERE = os.path.dirname(os.path.abspath(__file__)); ANIM = os.path.dirname(HERE)
SRT = os.path.join(ANIM, 'brawl_srt0', 'srt0.json')
OUT = os.path.join(ANIM, 'out', 'eye_states.json')
TOL = 0.008                   # uv: 2 texels across (256 wide), 1 texel down (128 high) on metaknight_eye
EYE_U, EYE_V = (0.30, 0.70), (0.44, 0.60)     # the eye texture's opaque region (alpha > 0: u 0.32-0.69, v 0.46-0.58)
MAX_STATES = 1023             # SetTexAnim's frame field is s32:11


def aff(s):
    """Brawl (sx, sy, rot, tx, ty) -> the uv map (au, bu, av, bv): u' = au u + bu, v' = av v + bv."""
    sx, sy, r, tx, ty = s
    assert abs(r) < 1e-6, 'MK eye SRT0 has a rotation'
    return (sx, -sx * tx, sy, sy * ty + 1 - sy)


def hsd(s):
    """Brawl (sx, sy, rot, tx, ty) -> HSD TObj (scale.x, scale.y, translate.x, translate.y) giving the same map."""
    sx, sy, r, tx, ty = s
    return (1.0 / sx, 1.0 / sy, tx, -ty - (1.0 - sy) / sy)


def hsd_map(h):
    """HSD (SX, SY, TX, TY) -> (au, bu, av, bv), repeat 1, rotation 0, no mirror (tobj.c MakeTextureMtx)."""
    SX, SY, TX, TY = h
    return (1 / SX, -TX / SX, 1 / SY, -TY / SY)


def err(a, b):
    e = 0.0
    for k, rng in ((0, EYE_U), (2, EYE_V)):
        for x in rng:
            e = max(e, abs((a[k] - b[k]) * x + (a[k + 1] - b[k + 1])))
    return e


def main():
    d = json.load(open(SRT))
    I = (1.0, 1.0, 0.0, 0.0, 0.0)
    states = [(I, I)]; maps = [(aff(I), aff(I))]
    clips = {}; worst = 0.0; worst_conv = 0.0; nframes = 0
    for name, a in d.items():
        m = a['materials'].get('medama')
        if not m: continue
        t0, t1 = m['Texture0']['baked'], m['Texture1']['baked']
        seq = []
        for x, y in zip(t0, t1):
            x = tuple(x); y = tuple(y); ax, ay = aff(x), aff(y)
            worst_conv = max(worst_conv, err(ax, hsd_map(hsd(x))), err(ay, hsd_map(hsd(y))))
            best, be = None, 1e9
            for i, (mx, my) in enumerate(maps):
                e = max(err(ax, mx), err(ay, my))
                if e < be: best, be = i, e
                if e == 0: break
            if be > TOL:
                states.append((x, y)); maps.append((ax, ay)); best, be = len(states) - 1, 0.0
            worst = max(worst, be); seq.append(best); nframes += 1
        ev = [[f, s] for f, s in enumerate(seq) if f == 0 or s != seq[f - 1]]
        if ev and ev[0] == [0, 0]: ev = ev[1:]            # frame 0 at state 0 is the engine's reset: no command
        clips[name] = {'frames': a['frames'], 'loop': a['loop'], 'events': ev, 'states_used': sorted(set(seq))}
    if len(states) > MAX_STATES: raise SystemExit('%d eye states > %d (SetTexAnim frame field)' % (len(states), MAX_STATES))
    out = {'source': 'anim/brawl_srt0/srt0.json (FitMetaknightMotionEtc.pac AnmTexSrt, material medama)',
           'tolerance_uv': TOL, 'worst_quantisation_uv': round(worst, 5), 'worst_brawl_to_hsd_uv': worst_conv,
           'frames': nframes, 'n_states': len(states),
           'tobj_order': 'state = [Texture0 (TexCoord0, eye on +x): SX, SY, TX, TY, Texture1 (TexCoord1, eye on -x): SX, SY, TX, TY] in HSD TObj terms',
           'states': [list(hsd(x)) + list(hsd(y)) for x, y in states],
           'states_brawl': [[list(x), list(y)] for x, y in states],
           'clips': clips}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, 'w'), indent=0)
    nev = sum(len(c['events']) for c in clips.values())
    print('eye clips', len(clips), 'frames', nframes, 'states', len(states), 'events', nev, 'worst quantisation uv', round(worst, 5),
          'brawl->hsd map err', worst_conv)


if __name__ == '__main__':
    main()
