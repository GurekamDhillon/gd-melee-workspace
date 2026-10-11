"""Apply the REMAKE picks to the animation row specs (called by xv2_to_artist.row_specs).

Inputs (all committed, clip names and frame numbers only):
  remake-picks.json   the LAB REMAKE picker's file: {"picks": [{"n": slot, "clip": "xGOK_ATC_002", "in": null, "out": null, ...}]}
  remake-rows.json    slot n -> the Melee rows it drives; per row "pick" (the slot's pick), a fixed companion clip, or a dict with timing
A row whose current clip already is the pick keeps its tuned crop ("keep"); a row on another clip is re-specified from the dict timing, else from the
pick (in/out) and the clip's own length ("remake"), at the clip's own speed. A slot with no pick (GAP / KEEP) changes nothing.
The applied table is returned (and written by the caller) so the ledger can say, per slot, what each row uses.
"""
import json
from pathlib import Path

PORT = Path(__file__).resolve().parents[1]
PICKS = PORT / 'remake-picks.json'
ROWS = PORT / 'remake-rows.json'
MAX_CLIP = 180   # the engine's per-clip buffer (xv2_to_artist cuts the library there too)


def load_picks(path=PICKS):
    d = json.loads(Path(path).read_text(encoding='utf-8'))
    return {p['n']: p for p in d.get('picks', [])}


def strip_x(name):
    return name[1:] if name.startswith('x') else name


def apply(out, source, byname, ean_file, aliases=None, picks=None, rows=None):
    """Mutate `out` (row -> spec). byname(name) -> clip id. Returns a list of {slot, n, row, clip, action, why}."""
    picks = load_picks() if picks is None else picks
    spec_rows = json.loads(ROWS.read_text(encoding='utf-8'))['slots'] if rows is None else rows
    report, changed = [], set()
    for key, slot in sorted(spec_rows.items(), key=lambda kv: int(kv[0])):
        n = int(key)
        pick = picks.get(n)
        for row, rspec in slot.get('rows', {}).items():
            if isinstance(rspec, str):
                rspec = {'use': rspec}
            use = rspec['use']
            if use == 'pick':
                if not pick:
                    report.append(dict(slot=slot['slot'], n=n, row=row, clip=None, action='no pick (row unchanged)', why=''))
                    continue
                clip = strip_x(pick['clip'])
            else:
                clip = use
            cid = byname(clip)
            if cid is None:
                raise SystemExit('remake: slot %d row %s: no source clip named %s' % (n, row, clip))
            cur = out.get(row)
            curname = source.clips[cur['clip']]['name'] if cur and cur.get('clip') in source.clips else None
            if cur is not None and curname == clip and not rspec.get('force'):
                report.append(dict(slot=slot['slot'], n=n, row=row, clip=clip, action='keep', why='row already plays this clip; its tuned crop stays'))
                continue
            c = source.clips[cid]
            src_frames = c['frames']
            start = rspec.get('start')
            if start is None:
                start = max(0, (pick.get('in') or 1) - 1) if (use == 'pick' and pick) else 0
            frames = rspec.get('frames')
            if frames is None:
                last = (pick.get('out') or src_frames) if (use == 'pick' and pick) else src_frames
                frames = min(MAX_CLIP, max(2, int(last - start)))
            new = {'clip': cid, 'loop': bool(rspec.get('loop', False)), 'frames': frames, 'start': start,
                   'status': 'REMAKE slot %d (%s): source %s from f%d, %d frames%s%s' % (
                       n, slot['slot'], c['name'], start, frames, (' x%g' % rspec['tf']) if rspec.get('tf') else '',
                       (' - ' + rspec['note']) if rspec.get('note') else '')}
            if rspec.get('tf'):
                new['time_factor'] = rspec['tf']
            if rspec.get('hold') is not None:
                new['hold_source'] = rspec['hold']
            if rspec.get('yaw'):
                new['yaw'] = rspec['yaw']
            if c['file'] != 'file:' + ean_file:
                new['library'] = True      # CMN / skill clips may scale bones; tolerated as in the library
            if cur is not None:            # keep the row's other settings that are not about which clip plays (move links, active_end)
                for k in ('move', 'active_end'):
                    if k in cur:
                        new[k] = cur[k]
            out[row] = new
            changed.add(row)
            report.append(dict(slot=slot['slot'], n=n, row=row, clip=clip, action='remake', why='was %s' % curname))
    # rows that were declared safe aliases of a base row follow the base
    for row, base in (aliases or {}).items():
        if base in changed and row in out and row not in changed:
            out[row] = {**out[base], 'status': 'safe alias of %s (the same pose is final art)' % base}
            report.append(dict(slot='(alias)', n=0, row=row, clip=None, action='alias of ' + base, why=''))
    return report
