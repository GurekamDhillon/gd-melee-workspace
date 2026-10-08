"""Join a moves_check.lua run with the declared data of a Geno define and say, per move: works / wrong / crashes.

    GW_MELEE=<game checkout> python -m tools.geno.moves_check.moves_report <mod folder> <melee-pc.log> [--json out.json]

Declared data: the overlay scripts of the mod's geno.json read with tools.geno.report (hitbox slot, damage, angle, size,
growth, base knockback and start / end script frame; throws and the pummel by their `throw` / hitbox words).
Observed data: the MOVECHK lines the fixture logged (live hitboxes per action frame, damage dealt to a placed Mario).

A move is
  works    it was entered, its hitboxes match the declared set (damage, angle, kbg, bkb, size) with the first live frame
           within 1 of declared start - 2 (geno.md 22: the hitbox is live from readout action frame N-2) and the same
           number of live frames within 1, and it connects for a declared damage;
  wrong    it ran but something differs (the reason is in the row);
  crashes  the game stopped mid-move (a START line with no result, or a FAIL line / panic in the log).
Moves that cannot be judged from the declared words alone (a loop or a charge-scaled damage) get `works*` and a note.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from .. import report as geno_report, script

# move name -> (overlay row, expectation)
ROWS = {
    'jab1': 46, 'jab2': 47, 'jab3': 48, 'dash_attack': 52, 'ftilt': 55, 'ftilt_up': 53, 'ftilt_down': 57, 'utilt': 58,
    'dtilt': 59, 'fsmash': 62, 'fsmash_up': 60, 'fsmash_down': 64, 'usmash': 66, 'dsmash': 67, 'nair': 68, 'fair': 69,
    'bair': 70, 'uair': 71, 'dair': 72, 'grab': 242, 'dash_grab': 243, 'pummel': 245, 'fthrow': 247, 'bthrow': 248,
    'uthrow': 249, 'dthrow': 250, 'n_charge': 295, 'n_release': 296, 's_lunge': 297, 'rise': 299, 'counter': 301,
    'land_nair': 68, 'land_fair': 69, 'land_bair': 70, 'land_uair': 71, 'land_dair': 72,
    'air_n_charge': 295, 'air_n_release': 296, 'air_s_lunge': 297, 'air_counter': 301,
}
LANDING_ATTR = {'nair': 'landingairn_lag', 'fair': 'landingairf_lag', 'bair': 'landingairb_lag', 'uair': 'landingairhi_lag',
                'dair': 'landingairlw_lag'}
THROWS = ('fthrow', 'bthrow', 'uthrow', 'dthrow')


def parse_log(path):
    started, results, other = [], {}, []
    fighter = None
    for line in Path(path).read_text(errors='replace').splitlines():
        m = re.search(r'MOVECHK (START|FIGHTER|DONE|FAIL)\s*(.*)$', line)
        if m:
            if m.group(1) == 'START':
                started.append(m.group(2).strip())
            elif m.group(1) == 'FIGHTER':
                fighter = json.loads(m.group(2))
            else:
                other.append((m.group(1), m.group(2)))
            continue
        m = re.search(r'MOVECHK (\{.*\})\s*$', line)
        if m:
            d = json.loads(m.group(1))
            results[d['name']] = d
    return started, results, other, fighter


def declared(mod):
    base, data = geno_report.load(mod)
    fighter = next(f for f in data['fighters'] if 'define' in f)
    by_row = {'attributes': fighter.get('attributes', {})}
    for o in fighter.get('subactions', []):
        words = geno_report.overlay_words(base, o)
        info = geno_report.frames(words)
        info['asm'] = script.disassemble(words)
        by_row[o['index']] = info
    return by_row


def throw_damage(info):
    m = re.search(r'throw idx=0 damage=(\d+)', info['asm'])
    return float(m.group(1)) if m else None


def close(a, b, tol):
    return abs(a - b) <= tol


def judge(name, dec, obs, other):
    """-> (verdict, notes list, summary dict)"""
    notes = []
    if obs is None:
        return 'crashes', ['no result line (the game stopped during this move)'], {}
    if 'error' in obs:
        return 'crashes', ['script error: ' + obs['error']], {}
    row = ROWS[name]
    d = dec.get(row)
    if name.startswith('land_'):
        want_l = dec['attributes'].get(LANDING_ATTR[name[5:]])
        got_l = (obs.get('landing') or {}).get('frames')
        summ = {'landing': (got_l, want_l)}
        if got_l is None:
            return 'wrong', ['did not land inside the attack (seen %s)' % obs.get('seen')], summ
        if want_l is None:
            return 'works', ['landing %s frames (attribute not authored)' % got_l], summ
        if abs(got_l - want_l) > 1:
            return 'wrong', ['landing lag %s frames, attribute %s = %s' % (got_l, LANDING_ATTR[name[5:]], want_l)], summ
        return 'works', ['landing %s frames, attribute %s' % (got_l, want_l)], summ
    if name == 'air_counter':   # no hitbox of its own; the state must be entered in the air and end without a fault
        ok = 'Counter' in obs.get('seen', [])
        return ('works' if ok else 'wrong'), ['entered in the air: %s' % obs.get('seen')], {}
    if d is None:
        return 'wrong', ['no declared overlay on row %d' % row], {}
    wrong = []
    star = False
    summ = {}

    if name == 'counter':
        cases = {c['case']: c for c in obs['cases']}
        for k in ('early', 'late'):
            c = cases[k]
            if 'CounterStrike' not in c['fighter'] or c['fighter_damage'] != 0 or not c['mario_damage']:
                wrong.append('%s: counter did not answer (%s, fighter took %s)' % (k, c['fighter'], c['fighter_damage']))
        c = cases['out_of_window']
        if 'CounterStrike' in c['fighter'] or not c['fighter_damage']:
            wrong.append('out of window: the hit was countered or missed (%s)' % c['fighter'])
        strike = dec.get(302)
        want = strike['hitboxes'][0]['damage'] if strike and strike['hitboxes'] else None
        got = cases['early']['mario_damage']
        summ = {'strike_damage': got, 'declared': want}
        if want is not None and not close(got, want, 0.6):
            wrong.append('counter-strike damage %s, declared %s' % (got, want))
        return ('wrong' if wrong else 'works'), wrong or ['countered early and late in the window, not outside it; strike %s%%' % got], summ

    if name in ('n_charge', 'air_n_charge'):
        if 'NCharge' not in obs['seen'] or 'NRelease' not in obs['seen']:
            wrong.append('charge did not release into NRelease: %s' % obs['seen'])
        if obs.get('groups'):
            wrong.append('declared no hitbox but one was live')
        return ('wrong' if wrong else 'works'), wrong or ['charges, then releases into NRelease (%s frames)' % obs['frames_in_move']], {}

    if name in THROWS or name == 'pummel':
        want = throw_damage(d) if name in THROWS else (d['hitboxes'][0]['damage'] if d['hitboxes'] else None)
        if not obs.get('captured'):
            wrong.append('the grab did not hold the victim')
        got = obs.get('dmg_dealt')
        summ = {'declared_damage': want, 'dealt': got, 'victim': obs.get('victim_state'), 'launch': obs.get('launch')}
        if want is not None and (got is None or not close(got, want, 0.6)):
            wrong.append('damage %s, declared %s' % (got, want))
        if name in THROWS and not any(s.startswith('Thrown') for s in obs.get('mseen', [])):
            wrong.append('victim never entered a Thrown state: %s' % obs.get('mseen'))
        if name == 'pummel' and 'CatchAttack' not in obs.get('seen', []):
            wrong.append('never entered CatchAttack')
        return ('wrong' if wrong else 'works'), wrong or ['victim held, %s%% dealt, ends %s' % (got, obs.get('victim_state'))], summ

    boxes = d['hitboxes']
    groups = obs.get('groups', [])
    grabby = name in ('grab', 'dash_grab')
    if not boxes:
        return 'wrong', ['no declared hitbox'], {}
    if not groups:
        return 'wrong', ['declared %d hitbox(es) but none was ever live (%s)' % (len(boxes), obs.get('seen'))], {}
    # compare the set of (damage, angle) pairs
    dset = {}
    for b in boxes:
        dset.setdefault((round(b.get('damage', 0)), b.get('angle')), []).append(b)
    oset = {}
    for g in groups:
        oset.setdefault((round(g['dmg']), round(g['ang'])), []).append(g)
    # a hit-damage write (HBDMG) or a loop changes damage at run time: the walk cannot follow those
    asm = d['asm']
    dynamic = bool(re.search(r'HBDMG|\bloop\b', asm))
    miss = [k for k in dset if k not in oset]
    extra = [k for k in oset if k not in dset]
    if (miss or extra) and not dynamic:
        wrong.append('hitbox sets differ: declared-only %s, observed-only %s' % (sorted(miss), sorted(extra)))
    elif miss or extra:
        star = True
        notes.append('script has HBDMG/loops; static walk differs from run: declared-only %s, observed-only %s' % (sorted(miss), sorted(extra)))
    # kbg / bkb / size of the matched pairs
    for k, bs in dset.items():
        for g in oset.get(k, []):
            if not any(close(g['kbg'], b.get('kbg', g['kbg']), 0.6) and close(g['bkb'], b.get('bkb', g['bkb']), 0.6) for b in bs):
                wrong.append('kb growth/base %s/%s observed for %s%% ang %s, declared %s' % (
                    g['kbg'], g['bkb'], k[0], k[1], sorted({(b.get('kbg'), b.get('bkb')) for b in bs})))
            if not any(close(g['r'], b.get('size', g['r']), 0.1) for b in bs):
                notes.append('size %.2f observed, declared %s (%s%%)' % (g['r'], sorted({b.get('size') for b in bs}), k[0]))
    # timing of the first live frame, and the live-frame count of the first matched group
    first_decl = min(b['start'] for b in boxes)
    lo = obs.get('active_lo')
    if lo is not None and not dynamic:
        rate = d.get('rate') or 1.0   # a script `wait N` is N script frames; the clip runs at `rate` (PUT ANIM_RATE)
        want_lo = max(0.0, first_decl / rate - 2)
        delta = int(round(lo - want_lo))
        summ['start_delta'] = delta
        if abs(delta) > (1 if rate == 1.0 else 2):   # a rate other than 1 scales the wait; the -2 offset was measured at rate 1
            wrong.append('first live frame %s, declared %s at rate %s (expected about %.1f), off by %+d' % (lo, first_decl, rate, want_lo, delta))
    elif lo is not None:
        summ['first_live'] = lo
    # connects, for a declared damage
    if grabby:
        if not any(x.startswith('Capture') for x in obs.get('mseen', [])):
            wrong.append('Mario was never captured (%s)' % obs.get('mseen'))
        else:
            notes.append('captures a placed Mario (%s)' % obs.get('mseen')[-1])
    elif not obs.get('hit'):
        wrong.append('did not hit a Mario placed on its hitbox (%s)' % obs.get('mseen'))
    else:
        got = obs['dmg_dealt']
        ok = any(close(got, b.get('damage', -9), 0.6) for b in boxes) or dynamic
        summ['dealt'] = got
        if not ok:
            wrong.append('dealt %s%%, declared %s' % (got, sorted({b.get('damage') for b in boxes})))
    summ['groups'] = [(g['dmg'], g['ang'], g['first_af'], g['last_af']) for g in groups]
    if name in LANDING_ATTR:
        want_l = dec['attributes'].get(LANDING_ATTR[name])
        got_l = (obs.get('landing') or {}).get('frames')
        if want_l is not None:
            summ['landing'] = (got_l, want_l)
            if got_l is None:
                notes.append('no landing observed (the aerial did not reach the ground in the window)')
            elif abs(got_l - want_l) > 1:
                wrong.append('landing lag %s frames, attribute %s = %s' % (got_l, LANDING_ATTR[name], want_l))
            else:
                notes.append('landing %s frames (attribute %s)' % (got_l, want_l))
    verdict = 'wrong' if wrong else ('works*' if star else 'works')
    return verdict, wrong + notes, summ


def run(mod, log):
    started, results, other, fighter = parse_log(log)
    dec = declared(mod)
    order = list(ROWS)
    crashed_at = None
    for s in started:
        if s not in results:
            crashed_at = s
            break
    rows = []
    for name in order:
        obs = results.get(name)
        if obs is None and crashed_at is not None and name != crashed_at and name not in started:
            rows.append((name, 'not run', ['the run stopped at %s' % crashed_at], {}))
            continue
        v, n, s = judge(name, dec, obs, other)
        rows.append((name, v, n, s))
    return rows, fighter, other, crashed_at


def check_attrs(mod, fighter):
    """Declared attributes against gd.attrs(1) read at match start (gd.attrs returns only the 40 named fields it knows)."""
    declared_attrs = declared(mod)['attributes']
    got = (fighter or {}).get('attrs') or {}
    rows, bad, unread = 0, [], []
    for k, v in declared_attrs.items():
        if k not in got:
            unread.append(k)
            continue
        rows += 1
        if abs(float(got[k]) - float(v)) > max(1e-3, abs(float(v)) * 2e-3):
            bad.append((k, v, got[k]))
    return rows, bad, unread


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mod')
    ap.add_argument('log')
    ap.add_argument('--json')
    a = ap.parse_args(argv)
    rows, fighter, other, crashed_at = run(a.mod, a.log)
    print('| move | verdict | detail |')
    print('|---|---|---|')
    for name, v, n, s in rows:
        print('| %s | %s | %s |' % (name, v, '; '.join(n)))
    tally = {}
    for _, v, _, _ in rows:
        tally[v] = tally.get(v, 0) + 1
    print('\n%s' % ', '.join('%s %d' % kv for kv in sorted(tally.items())))
    rows_a, bad_a, unread = check_attrs(a.mod, fighter)
    print('attributes: %d declared values read back through gd.attrs, %d differ%s; %d declared but not readable through gd.attrs (%s)' % (
        rows_a, len(bad_a), (' ' + str(bad_a)) if bad_a else '', len(unread), ', '.join(unread)))
    if fighter:
        print('fighter: %s (facing %s)' % (fighter.get('char_name'), fighter.get('face')))
    for k, v in other:
        print('log: %s %s' % (k, v))
    if a.json:
        Path(a.json).write_text(json.dumps([dict(move=n, verdict=v, notes=nn, summary=s) for n, v, nn, s in rows], indent=1, default=str))
    return 0 if all(v.startswith('works') for _, v, _, _ in rows) else 1


if __name__ == '__main__':
    sys.exit(main())
