"""The COMBOS section of Goku's fidelity ledger, generated from combo.json (the single source of the routes and their provenance).

    python ports/goku-xv2/combo/fidelity.py    -> combo/FIDELITY-COMBOS.md, combo/fidelity-combos.json
If ports/goku-xv2/FIDELITY.md exists (the Goku lane's ledger), a COMBOS section pointing here is appended once; its rows are not
touched. Every route is classified: "xv2" (a BCM node and the source BAC cancel window), "xv2+deviation" (traced, with the change
and the reason), or "design" (the owner-approved control design, 2026-10-08, with no XV2 equivalent in the BCM tree).
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = json.loads((HERE / 'combo.json').read_text(encoding='utf-8'))
bad = []
REF = {'Lx>Dragon Rush': 'Ryu/Ken special-cancel of a normal on hit (RYU-KEN-NOTES row 2; AI cancel column)',
       'Lx>Ki Volley': 'Ryu/Ken special-cancel of a normal on hit (RYU-KEN-NOTES row 2); XV2 Blast input',
       'Launcher>Jump': 'Ultimate-style jump-cancel of a launcher on hit; always a short hop (owner 2026-10-09)'}


def intent_for(r, kind):
    """One line saying what the route is meant to do and what it traces to, plus the checks that fail the generator: an xv2 route
    must name its BCM node and BAC entry, a design route must say which control design or Ryu/Ken reference it implements, every route
    is on-hit (cancels only on hit), and a string route's window must open at or before it closes."""
    src, probs = r.get('source', ''), []
    win = r.get('window', [1, 0])
    if r.get('on', 'hit') != 'hit':
        probs.append('not on hit (approved: cancels only on hit)')
    if win[1] and win[0] > win[1]:
        probs.append('window opens after it closes')
    if kind.startswith('xv2') and not ('BCM' in src and 'BAC' in src):
        probs.append('xv2 route without a BCM node and a BAC cancel window in its source')
    if kind == 'design' and not src.startswith('design'):
        probs.append('design route without a design note')
    m = re.search(r'cancel f(\d+)\+(\d+)', src)
    if m and kind == 'xv2' and 'opens at' not in src and win[0] < int(m[1]) + 1:
        probs.append(f'window opens at {win[0]}, before the BAC cancel start f{m[1]}')
    if kind.startswith('xv2'):
        text = f"on hit, {r['input']} (BCM) -> {r['to']}; window {win} from the BAC cancel record"
    else:
        text = REF.get(r['name']) or ('Melee air string / ender after the launcher (owner-approved design)' if r['name'].startswith(('Uair', 'Nair'))
                                      else 'owner-approved heavy-direction ender: ' + src.replace('design: ', '').replace('design', '').strip('; '))
    return text, probs


rows = []
for r in spec['combo']['routes']:
    src = r.get('source', '')
    kind = 'design' if src.startswith('design') else ('xv2+deviation' if ('dropped' in src or 'shifted' in src or 'here' in src) else 'xv2')
    intent, problems = intent_for(r, kind)
    if problems:
        bad.extend(f"{r['name']}: {p}" for p in problems)
    rows.append({'route': r['name'], 'intent': intent, 'from': r['from'], 'to': r['to'], 'input': r['input'], 'dir': r.get('dir', 'any'),
                 'on': r.get('on', 'hit'), 'window': r.get('window', [1, 0]), 'class': kind, 'source': src})
states = [{'state': s['name'], 'clip': s['clip'], 'bac': s['bac'], 'bcm': s['bcm'], 'script': s['script']} for s in spec['states']]
deviations = [
    ('All string hits', 'XV2 tracking / homing / lock-on', 'dropped (approved: no auto-tracking); replaced by the BAC Movement records\' timing as forward steps (FWD_VEL; speeds are design values, the record speeds are not decoded), held 4 frames past the hit'),
    ('L2>L3 window', 'BAC 301 cancel f11', 'opens at f7: the Goku lane moved jab2\'s hit from BAC f9 to f4 (move review); the window keeps XV2\'s 2 frames after the hit'),
    ('L2>L3 ... L4>L5 condition', 'BCM OnAttackHit | AttackBlocked', 'hit only (approved: cancels only on hit, never on shield)'),
    ('jab1/jab2 (L1/L2) in the combo package', 'BAC 300/301 reactions (BDM, not decoded)', 'HBSTUN +10/+14 and set knockback fkb 10 kbg 60: the XV2 rhythm (hit, cancel, next startup) is longer than Melee jab hitstun'),
    ('Light3-5', 'BAC 302-304 reactions', 'set knockback fkb 10 kbg 60 + HBSTUN 12/12/10 (Ultimate-style string hits, RYU-KEN-NOTES.md)'),
    ('Heavy at L1-L4', 'BAC 320 and its charge entry 322 (BacEntryCharge)', '320 built (HeavyRush); the charge variant is not built'),
    ('Heavy at L5', 'BAC 310 > 311 > 312 > 480 (a rush chain with teleports and homing)', '310 built (HeavyFinish); 311/312/480 dropped (homing, camera, targeting assistance)'),
    ('Heavy up / down enders', 'none in the BCM light tree (XV2 heavies are not directional there)', 'approved design: up = launcher HeavyUp (BAC 342, clip ATC_004, at its BAC hit f14 and cancel window 16+8), down = the Goku lane dsmash'),
    ('Launcher > jump', 'BCM Jump children under every light/heavy node (BAC 410 step)', 'approved design: the launcher (HeavyUp) jump-cancels on hit into a SHORT HOP (route target jump_short; geno.md 25.5c) so the air string meets the victim; Rush > RushCombo (Dragon Rush strike into its flurry) is a design route requested by the Goku lane'),
    ('Blocked moves', 'BCM conditions OnAttackHit | AttackBlocked', 'every route is on hit only: on a shield only Melee-native follow-ups apply; the SHIELD suite asserts no route fires on block, no closed loop (<= 2 consecutive blocked moves without an actionable defender frame) and no shield break within 8 blocked hits'),
    ('Air string', 'BCM 0/35/0/1: light in the air continues the ground light chain', 'approved design: Melee aerials (nair x3, heavy aerial enders)'),
    ('BCM conditions CloseToTarget / FarFromTarget / InTransformedState / Idle / Unk*', 'distance-to-target, transformation, flags', 'not mapped (xv2_bcm_combo.py lists them as unmapped)'),
]
data = {'routes': rows, 'states': states, 'deviations': [dict(zip(('what', 'xv2', 'melee'), d)) for d in deviations],
        'max_links': spec['combo']['max_links'], 'ki': spec['combo']['ki']}
(HERE / 'fidelity-combos.json').write_text(json.dumps(data, indent=1) + '\n', encoding='utf-8')
md = ['# Goku fidelity ledger: COMBOS (generated by combo/fidelity.py from combo.json)', '',
      'Every combo route and state, the XV2 source it traces to (BCM node of chara/GOK/GOK_PLAYER.bcm, BAC entry of GOK_PLAYER.bac and its',
      'cancel window, frames as the exporter\'s static 60 fps convention, not observed in XV2), or the owner-approved design it implements.',
      'Evidence of behaviour in the game: RESULTS.md (the combo test tables).', '', '## States', '',
      '| state | clip | BAC | BCM | script |', '|---|---|---|---|---|']
md += [f"| {s['state']} | {s['clip']} | {s['bac']} | {s['bcm']} | {s['script']} |" for s in states]
md += ['', '## Routes', '', '| route | from | to | input | on | window | class | intent | source |', '|---|---|---|---|---|---|---|---|---|']
md += [f"| {r['route']} | {r['from']} | {r['to']} | {r['input']}/{r['dir']} | {r['on']} | {r['window']} | {r['class']} | {r['intent']} | {r['source']} |" for r in rows]
md += ['', '## Deviations', '', '| what | XV2 | in Melee, and why |', '|---|---|---|']
md += [f'| {a} | {b} | {c} |' for a, b, c in deviations]
(HERE / 'FIDELITY-COMBOS.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
ledger = HERE.parent / 'FIDELITY.md'
if ledger.exists() and '## COMBOS' not in ledger.read_text(encoding='utf-8'):
    with ledger.open('a', encoding='utf-8') as f:
        f.write('\n## COMBOS\n\nThe combo routes, states and deviations: [combo/FIDELITY-COMBOS.md](combo/FIDELITY-COMBOS.md) '
                '(generated from combo/combo.json; machine-readable: combo/fidelity-combos.json). Test evidence: combo/RESULTS.md.\n')
if bad:
    print('INTENT ASSERTIONS FAILED:')
    print('  ' + chr(10).join(bad))
    sys.exit(1)
print(f'{len(rows)} routes, {len(states)} states -> {HERE / "FIDELITY-COMBOS.md"}')
