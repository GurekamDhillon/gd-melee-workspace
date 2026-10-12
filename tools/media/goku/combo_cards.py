"""Atlas-style combo cards for Goku, generated from the combo data (ports/goku-xv2/combo/combo.json: combo.routes, combo.ki, meter).

    python tools/media/goku/combo_cards.py [--combo PATH] [--out _build/goku-media/cards] [--date 2026-10-12]

Writes card_1_ground.png .. card_4_ki.png (1920x1080 each) and cheat_sheet.png (one tall 1920 px image). Re-run after any change
to combo.json. Everything shown (inputs, on hit / always, active window in frames, ki costs) is read from the data; the only
hand-written text is DISPLAY (state ids to player-facing names) and the EXTRA_KI / NOTES lines, marked as such below.
Inputs: light = A, heavy = C-stick (or an A smash flick, in the air the C-stick), special = B, jump = X, blast = D-pad down.
Window [a, b] is action frames of the FROM move in which the cancel is open (b = 0: from frame a until the move ends).
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atlas_style import MEDIA, glyphs, html_page, render  # noqa: E402

DEFAULT_COMBO = Path('E:/Projects/Melee Workspace/worktrees/gokustage/ports/goku-xv2/combo/combo.json')

# player-facing names for the state ids in combo.json (hand-written map; unknown ids fall back to a spaced-out id)
DISPLAY = {
    'jab1': 'Jab 1', 'jab2': 'Jab 2', 'geno:Light3': 'Light 3', 'geno:Light4': 'Light 4', 'geno:Light5': 'Light 5',
    'geno:HeavyRush': 'Blowback', 'geno:HeavyFinish': 'Heavy finisher', 'geno:HeavyUp': 'Launcher', 'dsmash': 'Down smash',
    'special_s': 'Dragon Rush', 'geno:Rush': 'Dragon Rush', 'geno:RushCombo': 'Rush Combo', 'geno:KiVolley': 'Ki Volley',
    'jump_short': 'Short hop', 'uair': 'Up air', 'nair': 'Neutral air', 'fair': 'Forward air', 'dair': 'Down air',
    'geno:Homing': 'Dash kick', 'geno:KiBlast': 'Ki blast', 'geno:KiBlastAir': 'Air ki blast',
    'geno:FlightFair': 'Flight forward air', 'geno:FlightBair': 'Flight back air', 'geno:FlightUair': 'Flight up air',
    'geno:FlightDair': 'Flight down air', 'geno:FlightNair': 'Flight neutral air',
}
GROUPS = {   # a list of states in `from` shown as one source box
    'Flight': 'Flight (up B)', 'Shield': 'Shield held', 'GroundBlast': 'On the ground (standing, walking, running, crouching)',
    'AirBlast': 'In the air (jump, fall)',
}
EXTRA_KI = [   # not in combo.json routes: from KAMEHAMEHA.md and PICKS.md (hand-written, update with them)
    ('Super Kamehameha', 'spends all 100', 'needs a full bar and a full charge'),
    ('Ki charge (down B)', 'gains about 0.8 a frame', 'hold; about 2 seconds from empty to full'),
]
NOTES = {   # hand-written, from lua/goku.lua
    'barrage': 'Hold the ki blast input and it chains into alternating hands, 5 ki a shot.',
}

CSS = """
body{background:var(--ground)}
.card{position:absolute;inset:0;background:radial-gradient(ellipse at 15% 0%,var(--ground2),var(--ground) 70%)}
.card:before{content:"";position:absolute;left:0;top:0;bottom:0;width:14px;background:var(--ember)}
.hd{display:flex;align-items:baseline;gap:22px}
.hd .k{font-size:34px;color:var(--ember)}
.hd h1{font-size:84px;line-height:1.1}
.hd .alpha{font-size:30px}
.hd .sub{margin-left:auto;font-size:26px;color:var(--muted)}
.leg{display:flex;gap:18px;align-items:center;font-size:24px;color:var(--text2);font-weight:600}
.chip{display:inline-block;font-family:BC;font-weight:700;text-transform:uppercase;letter-spacing:.06em;border-radius:3px;padding:3px 12px 0;font-size:.8em;line-height:1.35}
.chip.hit{background:var(--jade);color:var(--ink)}.chip.any{background:var(--sun);color:var(--ink)}.chip.fr{background:var(--plate2);color:var(--ivory);border:1.5px solid var(--line2)}
.chip.ki{background:none;color:var(--sun);border:1.5px solid var(--sun)}.chip.auto{background:var(--plate2);color:var(--text2);border:1.5px solid var(--line2)}
.node{background:var(--plate);border-left:7px solid var(--ember);padding:12px 22px 8px;font-family:BC;font-weight:700;text-transform:uppercase;font-size:38px;line-height:1.1;display:flex;align-items:center}
.node.air{border-left-color:var(--p2)}.node.sm{font-size:30px}.node small{display:block;font-size:.5em;color:var(--muted);letter-spacing:.04em}
.rows{display:flex;flex-direction:column;gap:14px}
.row{display:grid;grid-template-columns:420px 1fr 420px;align-items:center;gap:0}
.arr{position:relative;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;padding:0 20px;min-height:84px}
.arr .in{font-size:36px}.arr .ch{display:flex;gap:10px;align-items:center;font-size:24px}
.arr .ln{position:absolute;left:8px;right:8px;top:50%;height:3px;background:var(--line2);z-index:0}
.arr .ln:after{content:"";position:absolute;right:-2px;top:-8px;border-left:16px solid var(--line2);border-top:9.5px solid transparent;border-bottom:9.5px solid transparent}
.arr .mid{position:relative;z-index:1;background:var(--ground);padding:4px 14px;display:flex;flex-direction:row;align-items:center;gap:18px}
.fl{display:grid;grid-template-columns:420px 1fr;gap:30px;align-items:center}.frows{display:flex;flex-direction:column;gap:6px}.frow{display:grid;grid-template-columns:430px 220px 380px;align-items:center;gap:20px}.frow .in{font-size:30px}.frow .ch{display:flex;gap:8px;font-size:22px}.frow .node{font-size:28px;padding:6px 18px 3px}.gh{font-family:BC;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--sun);font-size:30px;margin:6px 0 2px}
.mx{border-collapse:separate;border-spacing:8px}
.mx th{font-family:BC;font-weight:700;text-transform:uppercase;font-size:34px;text-align:center;padding:10px 8px 4px;background:var(--plate);border-bottom:4px solid var(--ember);width:230px}
.mx td.rh{background:var(--plate);border-left:7px solid var(--ember);padding:6px 18px;width:470px}.mx td.rh .w{display:flex;align-items:center;justify-content:space-between;gap:16px}
.mx td.rh .nm{font-family:BC;font-weight:700;text-transform:uppercase;font-size:34px;line-height:1.1}
.mx td.rh .in{font-size:26px}
.mx td.c{background:var(--plate);text-align:center;font-family:BC;font-weight:700;font-size:34px;color:var(--ivory);width:230px;height:58px}
.mx td.c.no{color:var(--line2)}
.chain{display:flex;align-items:stretch;gap:0}
.chain .node{min-width:190px;justify-content:center}
.chain .ar{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:0 10px;min-width:200px;position:relative}
.chain .ar .in{font-size:30px}.chain .ar .fr{font-size:22px;margin-top:6px}
.chain .ar:after{content:"";position:absolute;left:10px;right:10px;top:50%;height:3px;background:var(--line2);z-index:0}
.foot{position:absolute;left:96px;right:96px;bottom:34px;font-size:23px;color:var(--muted);font-weight:600;display:flex;gap:28px;align-items:center}
.bar{position:relative;height:62px;background:var(--plate);border:2px solid var(--line2);margin-top:6px}
.bar i{position:absolute;top:0;bottom:0;background:linear-gradient(90deg,#c9962f,var(--sun))}
.tick{position:absolute;top:74px;font-family:BC;font-weight:700;font-size:26px;color:var(--text2);transform:translateX(-50%);white-space:nowrap}
.tick:after{content:"";position:absolute;left:var(--a,50%);top:-14px;height:14px;width:3px;background:var(--ember)}
.kcols{display:grid;grid-template-columns:1fr 1fr;gap:34px}
.kt{width:100%;border-collapse:collapse;font-size:30px}
.kt td{padding:12px 14px;border-bottom:1px solid var(--line)}
.kt td:first-child{font-family:BC;font-weight:700;text-transform:uppercase;font-size:36px}
.kt td.v{font-family:BC;font-weight:700;font-size:38px;color:var(--sun);text-align:right;white-space:nowrap}
.kt td.n{color:var(--muted);font-size:23px;font-weight:600}
.page{position:absolute;left:96px;right:96px;top:56px;bottom:90px}
.sheet .sec{position:relative;width:1920px;height:1080px;overflow:hidden}
"""


def label(i):
    if isinstance(i, list):
        return label_group(i)
    return DISPLAY.get(i, i.replace('geno:', '').replace('_', ' '))


def label_group(lst):
    s = set(lst)
    if any(x.startswith('geno:Flight') for x in lst):
        return GROUPS['Flight']
    if s & {'motion:178', 'motion:179'}:
        return GROUPS['Shield']
    if any(x in s for x in ('motion:14', 'motion:15')):
        return GROUPS['GroundBlast']
    if any(x in s for x in ('motion:25', 'motion:26')):
        return GROUPS['AirBlast']
    return ' / '.join(label(x) for x in lst)


def window(w):
    if not w:
        return ''
    a, b = w[0], w[1] if len(w) > 1 else 0
    return 'f%d+' % a if not b else 'f%d\u2013%d' % (a, b)


def input_glyphs(r):
    i, d = r['input'], r.get('dir', '')
    d = {'forward': 'fwd'}.get(d, d)
    if i == 'light':
        return ['A'] + (['+', 'stick:' + d] if d in ('fwd', 'back', 'up', 'down') else [])
    if i == 'heavy':
        return ['C:' + d] if d in ('fwd', 'back', 'up', 'down') else ['C']
    if i == 'special':
        return ['stick:fwd', '+', 'B'] if d == 'side' else ['B']
    if i == 'jump':
        return ['X']
    if i == 'blast':
        return ['dpad:down']
    if i == 'shield':
        return ['R']
    return ['auto']


def chips(r):
    c = ['<span class="chip %s">%s</span>' % ('hit' if r['on'] == 'hit' else 'any', 'on hit' if r['on'] == 'hit' else 'always')]
    if r.get('window') and not (r['window'][0] <= 1 and not (r['window'][1:] or [0])[0]):
        c.append('<span class="chip fr">%s</span>' % window(r['window']))
    if r.get('ki_cost'):
        c.append('<span class="chip ki">%d ki</span>' % r['ki_cost'])
    if r.get('depth'):
        c.append('<span class="chip fr">up to %d times</span>' % (r['depth'] + 1))
    return ''.join(c)


def node(name, air=False, sm=False):
    return '<div class="node%s%s">%s</div>' % (' air' if air else '', ' sm' if sm else '', name)


def row(frm, to, r, air=False):
    return ('<div class="row">%s<div class="arr"><div class="ln"></div><div class="mid"><div class="in">%s</div><div class="ch">%s</div></div></div>%s</div>'
            % (node(frm, air, True), glyphs(input_glyphs(r)), chips(r), node(to, air, True)))


def head(title, kicker, date):
    return ('<div class="hd"><span class="k bc">%s</span><h1 class="bc">%s</h1><span class="alpha">ALPHA</span><span class="sub">Goku &middot; %s</span></div>'
            % (kicker, title, date))


LEGEND = ('<div class="leg"><span class="chip hit">on hit</span> the move before must connect '
          '<span class="chip any">always</span> works on hit, whiff or block '
          '<span class="chip fr">f15\u201336</span> the frames of that move where the cancel is open</div>')


def by(routes, name_prefix=None, **kw):
    out = []
    for r in routes:
        if name_prefix and not r['name'].startswith(name_prefix):
            continue
        if all(r.get(k) == v for k, v in kw.items()):
            out.append(r)
    return out


def card_ground(routes, date):
    chain = ['jab1', 'jab2', 'geno:Light3', 'geno:Light4', 'geno:Light5']
    links = {r['to'] if isinstance(r['to'], str) else None: r for r in routes if r['name'] in ('L1>L2', 'L2>L3', 'L3>L4', 'L4>L5')}
    parts = []
    for i, c in enumerate(chain):
        parts.append(node(label(c)))
        if i + 1 < len(chain):
            r = links[chain[i + 1]]
            parts.append('<div class="ar"><div class="in">%s</div><div class="fr">%s</div></div>' % (glyphs(['A']), chips(r)))
    dests = [('geno:HeavyUp', 'Launcher'), ('geno:HeavyRush', 'Blowback'), ('geno:HeavyFinish', 'Heavy finisher'), ('dsmash', 'Down smash'),
             ('special_s', 'Dragon Rush'), ('geno:KiVolley', 'Ki Volley')]
    th = ''.join('<th>%s</th>' % label(c) for c in chain)
    body = ''
    for d, nm in dests:
        rs = [r for r in routes if r['to'] == d and (r['from'] in chain or (isinstance(r['from'], list) and set(chain) <= set(r['from'])))]
        if not rs:
            continue
        ex = rs[0]
        cells = ''
        for c in chain:
            m = [r for r in rs if r['from'] == c or (isinstance(r['from'], list) and c in r['from'])]
            cells += '<td class="c">%s</td>' % window(m[0]['window']) if m else '<td class="c no">&ndash;</td>'
        body += '<tr><td class="rh"><div class="w"><div class="nm">%s</div><div class="in">%s</div></div></td>%s</tr>' % (nm, glyphs(input_glyphs(ex)), cells)
    return html_page(
        '<div class="card"></div><div class="page">%s<div style="margin:12px 0 4px">%s</div><div class="gh">The light string: tap A on each hit</div>'
        '<div class="chain">%s</div><div class="gh" style="margin-top:10px">Branch out of any hit</div>'
        '<table class="mx"><tr><th style="background:none;border:0;width:470px"></th>%s</tr>%s</table></div>'
        '<div class="foot">Every branch needs the hit to connect. Cells show the frames of the move you are in when the branch opens.</div>'
        % (head('Ground string', 'Combo card 1', date), LEGEND, ''.join(parts), th, body), CSS)


def card_air(routes, date):
    rs = [r for r in routes if r['name'] in ('Launcher>Jump', 'Uair>Nair', 'Nair>Nair', 'Nair>H fwd', 'Nair>H up', 'Nair>H down')]
    order = ['Launcher>Jump', 'Uair>Nair', 'Nair>Nair', 'Nair>H fwd', 'Nair>H up', 'Nair>H down']
    rs.sort(key=lambda r: order.index(r['name']))
    rows = ''
    for r in rs:
        air = r['where'] == 'air'
        rows += row(label(r['from']), label(r['to']), r, air)
    return html_page(
        '<div class="card"></div><div class="page">%s<div style="margin:18px 0 12px">%s</div><div class="gh">Launcher into the air string</div><div class="rows">%s</div></div>'
        '<div class="foot">Land the launcher, hop after it, then chain neutral airs and finish with a heavy aerial. Blue edge = in the air.</div>'
        % (head('Launcher to air string', 'Combo card 2', date), LEGEND, rows), CSS)


def merged_flight(routes):
    """Flight aerials: the A route and the C route to the same move become one row (A or C-stick)."""
    out = {}
    for r in routes:
        if r['name'].startswith('Fly>'):
            out.setdefault(r['to'], []).append(r)
    return out


def card_specials(routes, date):
    rows = ''
    for n in ('Rush>RushCombo', 'Guard>Homing', 'Blast>KiBlast', 'Blast>KiBlastAir'):
        r = next((x for x in routes if x['name'] == n), None)
        if r:
            rows += row(label(r['from']), label(r['to']), r, r['where'] == 'air')
    fl = ''
    src = None
    for to, rs in merged_flight(routes).items():
        a = next(r for r in rs if r['input'] == 'light')
        src = src or label(a['from'])
        d = {'forward': 'fwd'}.get(a.get('dir', ''), a.get('dir', ''))
        arrow = d in ('fwd', 'back', 'up', 'down')
        ig = ['A'] + (['+', 'stick:' + d] if arrow else []) + ['or', 'C' + (':' + d if arrow else '')]
        fl += ('<div class="frow"><div class="in">%s</div><div class="ch">%s</div>%s</div>' % (glyphs(ig), chips(a), node(label(to), True, True)))
    fl = '<div class="fl">%s<div class="frows">%s</div></div>' % (node(src, True, True), fl)
    return html_page(
        '<div class="card"></div><div class="page">%s<div style="margin:16px 0 4px">%s</div><div class="gh">Specials, shield and ki</div><div class="rows">%s</div>'
        '<div class="gh" style="margin-top:14px">Flight aerials (up B, then attack)</div>%s</div>'
        '<div class="foot">%s</div>' % (head('Specials and cancels', 'Combo card 3', date), LEGEND, rows, fl, NOTES['barrage']), CSS)


def card_ki(combo, routes, date):
    ki = combo['ki']
    mx = ki['max']
    costs = sorted({(r['name'], r['ki_cost']) for r in routes if r.get('ki_cost')}, key=lambda t: t[1])
    seen = {}
    for r in routes:
        if r.get('ki_cost'):
            seen.setdefault(r['ki_cost'], []).append(label(r['to']))
    ticks = ''.join('<div class="tick" style="left:%.1f%%;%s">%d%s</div>' % (
        100 * c / mx, '', c, ' ki') for c, n in sorted(seen.items()))
    ticks += '<div class="tick" style="left:100%%;transform:translateX(-100%%);--a:100%%">%d ki</div>' % mx
    gain = [('Landing a hit', '+%g' % ki['on_hit'], 'every hit that connects'),
            ('Taking a hit', '+%g' % ki['on_taken'], 'getting hit also feeds it'),
            ('Blocked hits', '+%g' % ki['on_block'], 'no gain when the hit is blocked')]
    spend = [(label(r['to']), '\u2212%d' % r['ki_cost'], 'to cancel into it') for r in routes if r.get('ki_cost')]
    seen_s, uniq = set(), []
    for s in spend:
        if s[0] not in seen_s:
            seen_s.add(s[0]); uniq.append(s)
    spend = uniq + [(a, b, c) for a, b, c in EXTRA_KI]
    tr = lambda rows: ''.join('<tr><td>%s</td><td class="v">%s</td><td class="n">%s</td></tr>' % t for t in rows)
    return html_page(
        '<div class="card"></div><div class="page">%s<div class="gh" style="margin-top:36px">The ki meter: 0 to %d, starts empty</div>'
        '<div style="position:relative;padding-top:14px;height:150px"><div class="bar"><i style="width:100%%;opacity:.28"></i></div>%s</div>'
        '<div class="kcols" style="margin-top:44px"><div><div class="gh">Fills with</div><table class="kt">%s</table></div>'
        '<div><div class="gh">Spends on</div><table class="kt">%s</table></div></div></div>'
        '<div class="foot">Hold down B to charge the bar back up, in the air too.</div>'
        % (head('Ki costs', 'Combo card 4', date), mx, ticks, tr(gain), tr(spend)), CSS)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--combo', default=str(DEFAULT_COMBO)); ap.add_argument('--out', default=str(MEDIA / 'cards'))
    ap.add_argument('--date', default='2026-10-12')
    a = ap.parse_args()
    combo = json.loads(Path(a.combo).read_text(encoding='utf-8'))
    routes = combo['combo']['routes']
    out = Path(a.out)
    cards = [('card_1_ground', card_ground(routes, a.date)), ('card_2_air', card_air(routes, a.date)),
             ('card_3_specials', card_specials(routes, a.date)), ('card_4_ki', card_ki(combo['combo'], routes, a.date))]
    errs = render([(h, out / (n + '.png')) for n, h in cards])
    # the tall cheat sheet: the same four pages stacked
    import re
    secs = ''.join('<div class="sec">%s</div>' % re.search(r'<body>(.*)</body>', h, re.S).group(1) for _, h in cards)
    sheet = html_page(secs, CSS + 'body{height:auto;overflow:visible}.sec{position:relative;width:1920px;height:1080px;overflow:hidden}')
    errs += render([(sheet, out / 'cheat_sheet.png')], h=1080 * 4, full_page=True)
    print('wrote 5 images to', out)
    if errs:
        print('FAIL:\n  ' + '\n  '.join(errs)); sys.exit(1)


if __name__ == '__main__':
    main()
