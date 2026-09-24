"""anim/vis_events.json: Meta Knight's Brawl visibility events for every converted clip, in Melee ModelVis terms.

Model-part visibility of the MK costume files (model/tools/mkbuild, ftData x8 table written by install_mk.py):
  model 0 = cape switch  (Brawl BoneSwitch2):  0 closed cape (MantM, DObj 10)   1 wings (WingM, DObjs 11-12)
                                               2 merged cape article (DObj 13; Brawl: no cape bone + the article)
  model 1 = body switch  (Brawl BoneSwitch1):  0 body (DObjs 0-6)               1 mantle ball (DObj 9)
  the sword (DObjs 7-8) is in no list and always drawn (a model's states may not share DObjs in Melee's table).
  Brawl group -> Melee state: 0 body+sword -> 0, 1 ball only -> 1, 2 body+sword+ball -> 0 (ball dropped),
  3 body without sword -> 0 (sword stays).
Brawl PSA 'Model Changer 2 {Switch 2, Group g}' == Melee ModelVis(0, g) and 'Model Changer 1 {Switch 1, Group g}'
-> ModelVis(1, BODY_STATE[g]) (Melee script command 0x7C: (31 << 26) | (index << 19) | value).
Model 0 is the cape on purpose: Kirby's clone code (OnDeath: both models -> 0, the multi-jump puff ModelVis(0, 1))
then gives MK his closed cape at spawn and his wings on multi-jumps - exactly Brawl's JumpAerialF* state.

The cape article: Brawl shows it with Generate Article / Article Visibility and anchors its clip to the fighter's
(Set Anchored Article SubAction); here its bones are animated inside the MK clip (mk_anim.ARTICLE) and it is shown
by ModelVis(0, 2). 'Article Visibility false' / 'Remove Article' while the cape switch is on group 2 means Brawl shows
NO cape (group 2 has no bones); model 0 has no empty state, so those frames are only reported (article_hidden_frames)
and the article cape stays visible.
'Visibility {false/true}' (the whole fighter vanishes, Dimensional Cape teleport, ThrowB) has no ModelVis
equivalent: listed as body_invisible_frames for the script translator.
"""
import os, sys, json
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__)); ANIM = os.path.dirname(HERE); MK = os.path.dirname(ANIM)
sys.path.insert(0, HERE)
import mk_anim

BODY_STATE = {0: 0, 1: 1, 2: 0, 3: 0}
VIS = ('Model Changer 1', 'Model Changer 2', 'Generate Article', 'Remove Article', 'Article Visibility', 'Visibility',
       'Set Anchored Article SubAction', 'Item Visibility')


def main():
    B = json.load(open(os.path.join(MK, 'analysis', 'brawl_metaknight.json')))
    subs = defaultdict(list)
    for s in B['subactions']['list']:
        if s['anim']: subs[s['anim']].append(s)
    mr = json.load(open(os.path.join(ANIM, 'out', 'motion_rows.json')))
    out = {'legend': __doc__.strip(), 'clips': []}
    for c in mr['clips'] + mr['extras']:
        names = c['brawl_clip'].split('+')
        if names[0].startswith('pose:'): continue
        off = 0; ev = []; sugg = []; hidden = []; invis = []; seq = []
        for cn in names:
            seen = set()
            for s in subs.get(cn, []):
                if s['name'] in seen: continue
                seen.add(s['name'])
                for ch in ('main_timeline', 'gfx', 'sfx', 'other'):
                    for e in s.get(ch) or []:
                        if e[1] not in VIS: continue
                        f = int(e[0]) + off; a = e[2]
                        rec = {'frame': f, 'event': e[1], 'args': a, 'subaction': s['name']}
                        if e[1] == 'Model Changer 2' and a.get('Switch Index') == 2:
                            g = a.get('Bone Group Index'); rec['meaning'] = ['closed cape', 'wings', 'cape article'][g]
                            sugg.append({'frame': f, 'cmd': 'ModelVis', 'index': 0, 'value': g, 'why': rec['meaning']})
                            seq.append((f, 'mc2', g))
                        elif e[1] == 'Model Changer 1' and a.get('Switch Index') == 1:
                            g = a.get('Bone Group Index'); rec['meaning'] = ['body + sword', 'mantle ball only', 'body + sword + ball', 'body, no sword'][g]
                            sugg.append({'frame': f, 'cmd': 'ModelVis', 'index': 1, 'value': BODY_STATE[g], 'why': rec['meaning']})
                        elif e[1] in ('Article Visibility', 'Remove Article') and not a.get('Visibility', False):
                            hidden.append(f); seq.append((f, 'art', False))
                        elif e[1] == 'Article Visibility' and a.get('Visibility'):
                            seq.append((f, 'art', True))
                        elif e[1] == 'Visibility':
                            invis.append({'frame': f, 'visible': a.get('Visibility')})
                        ev.append(rec)
            off += mk_anim.mk_clip(cn)['frames']
        # the cape article hidden while the cape switch shows it (group 2) = no cape at all: model 0 state 3 (empty)
        sw, art = None, True
        for f, k, v in sorted(seq, key=lambda x: x[0]):
            if k == 'mc2': sw = v
            else: art = v
            if sw == 2 and k == 'art':
                sugg.append({'frame': f, 'cmd': 'ModelVis', 'index': 0, 'value': 2 if art else 3,
                             'why': 'cape article shown again' if art else 'cape article hidden (no cape)'})
            elif k == 'mc2' and v == 2 and not art:
                sugg.append({'frame': f, 'cmd': 'ModelVis', 'index': 0, 'value': 3, 'why': 'cape switch on the article while it is hidden (no cape)'})
        uniq = {};
        for s in sugg: uniq[(s['frame'], s['index'])] = s
        sugg = [uniq[k] for k in sorted(uniq)]
        keys = set(); ue = []
        for e in ev:
            k = (e['frame'], e['event'], json.dumps(e['args'], sort_keys=True))
            if k not in keys: keys.add(k); ue.append(e)
        out['clips'].append({'brawl_clip': c['brawl_clip'], 'symbol': c['symbol'], 'rows': c['rows'], 'frames': c['frames'],
                             'article_clip': c.get('article_clip'), 'melee_modelvis_suggested': sugg, 'melee_modelvis_vanilla': [],
                             'article_hidden_frames': sorted(set(hidden)), 'body_invisible_frames': invis, 'brawl_events': ue})
    dr = os.path.join(ANIM, 'out', 'demo_rows.json')
    out['demo'] = []
    if os.path.exists(dr):
        prev_end = {0: 0, 1: 0}
        for r in json.load(open(dr))['rows']:
            c = next((x for x in out['clips'] if x['brawl_clip'] == r['brawl_clip']), None)
            ev = sorted({(e['frame'], e['index'], e['value']) for e in (c['melee_modelvis_suggested'] if c else [])})
            if c is None:
                seq = []; sw, art = None, True
                for s_ in subs.get(r['brawl_clip'], [])[:1]:
                    for ch in ('main_timeline', 'gfx', 'sfx', 'other'):
                        for e in s_.get(ch) or []:
                            f = int(e[0]); a = e[2]
                            if e[1] == 'Model Changer 2' and a.get('Switch Index') == 2: seq.append((f, 0, 'mc2', a['Bone Group Index']))
                            elif e[1] == 'Model Changer 1' and a.get('Switch Index') == 1: seq.append((f, 1, 'mc1', BODY_STATE[a['Bone Group Index']]))
                            elif e[1] in ('Article Visibility', 'Remove Article'): seq.append((f, 0, 'art', bool(a.get('Visibility', False))))
                d = {}
                for f, i, k, v in seq:
                    if k == 'mc2': sw = v; d[(f, 0)] = 3 if (v == 2 and not art) else v
                    elif k == 'mc1': d[(f, 1)] = v
                    else:
                        art = v
                        if sw == 2: d[(f, 0)] = 2 if v else 3
                        elif v: d[(f, 0)] = 2      # Brawl shows the article next to the closed cape (Win1): Melee's cape
                                                   # model shows one of them - the article, the moving part of the pose
                ev = sorted((f, i, v) for (f, i), v in d.items())
            wait = r['name'].endswith('Wait') and not r['name'].startswith('Selected')
            start = dict(prev_end) if wait else {0: 0, 1: 0}
            for f, i, v in ev:
                if f == 0: start[i] = v
            evs = [(0, 0, start[0]), (0, 1, start[1])] + [(f, i, v) for f, i, v in ev if f > 0]
            end = dict(start)
            for f, i, v in evs: end[i] = v
            prev_end = end
            out['demo'].append({'index': r['index'], 'name': r['name'], 'brawl_clip': r['brawl_clip'], 'frames': r['frames'],
                                'melee_modelvis': [{'frame': f, 'index': i, 'value': v} for f, i, v in evs]})
    json.dump(out, open(os.path.join(ANIM, 'vis_events.json'), 'w'), indent=1)
    n = sum(1 for c in out['clips'] if c['melee_modelvis_suggested'])
    print(len(out['clips']), 'clips,', n, 'with ModelVis suggestions')
    for c in out['clips']:
        if any(s['value'] for s in c['melee_modelvis_suggested']) or c['article_clip']:
            print('%-22s rows=%-12s %s hidden=%s invis=%s' % (c['brawl_clip'][:22], str(c['rows'])[:12],
                  [(s['frame'], s['index'], s['value']) for s in c['melee_modelvis_suggested']], c['article_hidden_frames'], c['body_invisible_frames']))


if __name__ == '__main__':
    main()
