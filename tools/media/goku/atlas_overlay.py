"""Atlas-style overlay PNGs for the Goku alpha media: title card, per-clip lower-thirds, controls card, end card.

    python tools/media/goku/atlas_overlay.py [--shots tools/media/goku/shots.json] [--out _build/goku-media/overlays]
        [--date 2026-10-12] [--hero path.png] [--build "alpha build label"]

Lower-thirds and the corner mark are transparent 1920x1080 PNGs (composited by compose.py); cards are opaque. Text comes from
shots.json (one source of truth for the post, the lower-thirds and the controls card). Overflow in any .fit box fails the run.
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atlas_style import C, MEDIA, glyphs, html_page, render  # noqa: E402

HERE = Path(__file__).resolve().parent

CSS = """
.corner{position:absolute;right:56px;top:40px;display:flex;align-items:center;gap:14px;background:rgba(13,16,21,.78);padding:10px 18px 6px;border-left:4px solid var(--ember)}
.corner .t{font-size:30px;line-height:1}
.corner .alpha{font-size:22px}
.lt{position:absolute;right:72px;bottom:64px;display:flex;align-items:stretch;max-width:1000px}
.lt .bar{width:10px;background:var(--ember)}
.lt .box{background:rgba(26,31,41,.92);padding:16px 30px 14px 24px}
.lt .name{font-size:60px;line-height:1.12}
.lt .sub{margin-top:8px;font-size:26px;color:var(--text2);font-weight:600}
.lt .in{margin-top:12px;font-size:34px}
.lt .note{margin-top:8px;font-size:22px;color:var(--muted)}
.lt .idx{background:var(--sun);color:var(--ink);font-size:20px;padding:10px 12px 0;writing-mode:vertical-rl;transform:rotate(180deg);letter-spacing:.14em}
.card{position:absolute;inset:0;background:radial-gradient(ellipse at 20% 0%,var(--ground2),var(--ground) 70%)}
.card:before{content:"";position:absolute;left:0;top:0;bottom:0;width:14px;background:var(--ember)}
.slash{position:absolute;right:-120px;top:-100px;width:900px;height:1400px;background:linear-gradient(100deg,transparent 0 40%,rgba(255,122,61,.10) 40% 60%,transparent 60%);transform:skewX(-14deg)}
.glow{position:absolute;right:60px;top:60px;width:900px;height:1000px;background:radial-gradient(ellipse at 50% 55%,rgba(255,122,61,.38),rgba(255,122,61,.10) 45%,transparent 70%)}
.hero{position:absolute;right:-70px;top:-70px;height:1250px;filter:drop-shadow(0 0 40px rgba(255,122,61,.35))}
.title{position:absolute;left:120px;top:250px}
.title .big{font-size:300px;line-height:.82;letter-spacing:.01em}
.title .row{margin-top:30px;display:flex;align-items:center;gap:26px}
.title .alpha{font-size:76px;padding:6px 26px 0}
.title .date{font-size:44px;color:var(--text2);font-weight:600;font-family:BC}
.title .tag{margin-top:44px;font-size:34px;color:var(--text2);max-width:880px;line-height:1.35}
.hd{position:absolute;left:96px;top:60px;right:96px;display:flex;align-items:baseline;gap:24px}
.hd h1{font-size:92px;line-height:1}
.hd .alpha{font-size:34px}
.hd .sub{margin-left:auto;font-size:28px;color:var(--muted)}
.grid{position:absolute;left:96px;right:96px;top:200px;bottom:70px;display:grid;grid-template-columns:repeat(4,1fr);grid-auto-rows:1fr;gap:20px}
.cell{background:var(--plate);border-top:4px solid var(--ember);padding:20px 24px 16px;display:flex;flex-direction:column}
.cell h2{flex:none;font-size:42px;line-height:1.15}
.cell .in{margin:12px 0 8px;font-size:27px;min-height:48px}
.cell p{flex:none;font-size:22px;line-height:1.3;color:var(--text2);font-weight:600}
.cell.ki{border-top-color:var(--sun)}
.cs{position:absolute;left:96px;right:96px;top:190px}.cs .st{width:100%;display:block;border-top:4px solid var(--ember);image-rendering:auto}.crow{display:flex;gap:20px;margin-top:34px}.cc{flex:1;background:var(--plate);padding:18px 10px 14px;text-align:center;border-bottom:4px solid var(--ember)}.pp{height:376px;image-rendering:pixelated;display:block;margin:0 auto}.cn{margin-top:12px;font-family:BC;font-weight:700;text-transform:uppercase;font-size:44px;color:var(--ivory);display:flex;align-items:center;justify-content:center;gap:12px}.sk{width:48px;height:48px;image-rendering:pixelated}
.steps{position:absolute;left:120px;top:250px;width:1100px}
.steps li{list-style:none;display:flex;gap:26px;align-items:flex-start;margin-bottom:26px}
.steps .n{flex:none;width:68px;height:68px;border-radius:50%;background:var(--ember);color:var(--ink);font-family:BC;font-weight:700;font-size:44px;display:flex;align-items:center;justify-content:center;padding-top:4px}
.steps .tx{font-size:34px;line-height:1.25;font-weight:600}
.steps .tx small{display:block;font-size:24px;color:var(--muted);font-weight:400;margin-top:4px}
.side{position:absolute;right:96px;top:250px;width:560px;background:var(--plate);border-left:6px solid var(--sun);padding:30px 34px}
.side h3{font-size:40px;color:var(--sun)}
.side p{margin-top:14px;font-size:26px;line-height:1.35;color:var(--text2);font-weight:600}
"""

CORNER = '<div class="corner"><span class="bc t">Goku</span><span class="alpha">ALPHA</span></div>'


def lower_third(i, n, s):
    note = '<div class="note fit">%s</div>' % s['note'] if s.get('note') else ''
    return html_page(CORNER + (
        '<div class="lt"><div class="idx bc">%02d / %02d</div><div class="bar"></div><div class="box">'
        '<div class="name bc fit">%s</div><div class="in">%s</div>%s</div></div>') % (
        i, n, s['title'], glyphs(s['input']), note), CSS)


def title_card(date, hero, build):
    import base64
    img = '<img class="hero" src="data:image/png;base64,%s">' % base64.b64encode(Path(hero).read_bytes()).decode() if hero and Path(hero).exists() else ''
    return html_page(
        '<div class="card"><div class="slash"></div><div class="glow"></div>%s<div class="title"><div class="big bc">Goku</div>'
        '<div class="row"><span class="alpha">ALPHA</span><span class="date">TEST BUILD &middot; %s</span></div>'
        '<div class="tag">A hand-built Dragon Ball fighter for GD\'s Melee. Early and unbalanced: hitboxes are still being hand-authored, '
        'some animations are rough, and bug reports are the whole point.</div></div></div>' % (img, date), CSS)


def costumes_card(strip, names, date, pres=None):
    """The character-select strip on top; below it each costume's portrait and stock icon (art lead's presentation previews)."""
    import base64
    b64 = lambda p: base64.b64encode(Path(p).read_bytes()).decode()
    dirs = ['default', 'red', 'blue', 'green', 'navy']
    cells = ''
    for i, n in enumerate(names):
        d = Path(pres) / dirs[i] if pres and i < len(dirs) else None
        pic = '<img class="pp" src="data:image/png;base64,%s">' % b64(d / 'portrait.png') if d and (d / 'portrait.png').exists() else ''
        stk = '<img class="sk" src="data:image/png;base64,%s">' % b64(d / 'stock.png') if d and (d / 'stock.png').exists() else ''
        cells += '<div class="cc">%s<div class="cn">%s%s</div></div>' % (pic, stk, n)
    return html_page(
        '<div class="card"></div><div class="hd"><h1 class="bc">Costumes</h1><span class="alpha">ALPHA</span><span class="sub">Goku &middot; %s</span></div>'
        '<div class="cs"><img class="st" src="data:image/png;base64,%s"><div class="crow">%s</div></div>' % (date, b64(strip), cells), CSS)


def controls_card(cells, build):
    cs = ''.join('<div class="cell%s"><h2 class="bc fit">%s</h2><div class="in">%s</div><p class="fit">%s</p></div>' % (
        ' ki' if c.get('ki') else '', c['name'], glyphs(c['input']), c['text']) for c in cells)
    return html_page(
        '<div class="card"></div><div class="hd"><h1 class="bc">Controls</h1><span class="alpha">ALPHA</span>'
        '<span class="sub">Goku &middot; %s</span></div><div class="grid">%s</div>' % (build, cs), CSS)


def end_card(steps, report, date):
    li = ''.join('<li><span class="n">%d</span><div class="tx">%s<small>%s</small></div></li>' % (i + 1, a, b)
                 for i, (a, b) in enumerate(steps))
    return html_page(
        '<div class="card"></div><div class="hd"><h1 class="bc">Install</h1><span class="alpha">ALPHA</span>'
        '<span class="sub">Goku test build &middot; %s</span></div><ul class="steps">%s</ul>'
        '<div class="side"><h3 class="bc">Report bugs</h3><p class="fit">%s</p></div>' % (date, li, report), CSS)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--shots', default=str(HERE / 'shots.json'))
    ap.add_argument('--out', default=str(MEDIA / 'overlays'))
    ap.add_argument('--date', default=None); ap.add_argument('--hero'); ap.add_argument('--build', default='Alpha test build'); ap.add_argument('--costumes', help='the character-select strip (art lead css-goku-p1-panels.png)'); ap.add_argument('--presentation', help='art lead presentation/ dir with <costume>/portrait.png, stock.png')
    a = ap.parse_args()
    spec = json.loads(Path(a.shots).read_text(encoding='utf-8'))
    date = a.date or spec.get('date', '')
    out = Path(a.out)
    shots = [s for s in spec['shots'] if s.get('title')]
    pages = [(html_page(CORNER, CSS), out / 'corner.png')]
    for i, s in enumerate(shots, 1):
        pages.append((lower_third(i, len(shots), s), out / ('lt_%s.png' % s['id'])))
    errs = render(pages, transparent=True)
    cards = [(title_card(date, a.hero or spec.get('hero'), a.build), out / 'card_title.png'),
             (controls_card(spec['controls'], a.build), out / 'card_controls.png'),
             (end_card([tuple(x) for x in spec['install']], spec['report'], date), out / 'card_end.png')]
    if a.costumes and Path(a.costumes).exists():
        cards.append((costumes_card(a.costumes, spec.get('costume_names', []), date, a.presentation), out / 'card_costumes.png'))
    errs += render(cards)
    print('wrote %d overlays to %s' % (len(pages) + len(cards), out))
    if errs:
        print('FAIL:\n  ' + '\n  '.join(errs)); sys.exit(1)


if __name__ == '__main__':
    main()
