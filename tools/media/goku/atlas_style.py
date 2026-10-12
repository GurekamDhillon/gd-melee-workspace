"""Atlas look for the Goku media: tokens, fonts, controller glyphs and a headless-Chromium PNG renderer.

Shared by atlas_overlay.py (title / lower-third / controls / end cards) and combo_cards.py (route cards). Colours come from
menu/atlas/tokens.json, fonts are Barlow Condensed (display) and Source Sans 3 (body) from menu/, the renderer is the same
Playwright Chromium the README and announcement charts use (menu/pipeline/readme.py, announce_chart.py).
"""
import base64, json, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MEDIA = Path(os.environ.get('GW_ROOT') or 'E:/Projects/Melee Workspace') / '_build/goku-media'   # git-ignored outputs
MENU = ROOT / 'menu'
TOK = json.loads((MENU / 'atlas/tokens.json').read_text(encoding='utf-8'))['colours']


def C(name):
    return '#%06x' % (TOK[name] >> 8)


def font_css():
    def b64(p):
        return base64.b64encode((MENU / p).read_bytes()).decode()
    return ('@font-face{font-family:BC;font-weight:700;src:url(data:font/ttf;base64,%s)}'
            '@font-face{font-family:BC;font-weight:600;src:url(data:font/ttf;base64,%s)}'
            '@font-face{font-family:SS;font-weight:400 600;src:url(data:font/otf;base64,%s)}'
            '@font-face{font-family:SS;font-weight:700;src:url(data:font/otf;base64,%s)}') % (
        b64('Barlow/BarlowCondensed-Bold.ttf'), b64('Barlow/BarlowCondensed-SemiBold.ttf'),
        b64('SourceSans3/SourceSans3-Semibold.otf'), b64('SourceSans3/SourceSans3-Bold.otf'))


BASE_CSS = """
:root{--ground:%(ground)s;--ground2:%(ground2)s;--plate:%(plate)s;--plate2:%(plate2)s;--ink:%(ink)s;--ivory:%(ivory)s;--text2:%(text2)s;
--muted:%(muted)s;--sun:%(sun)s;--ember:%(ember)s;--emberd:%(ember-d)s;--jade:%(jade)s;--rose:%(rose)s;--line:%(line)s;--line2:%(line2)s;
--pa:%(pad-a)s;--pb:%(pad-b)s;--px:%(pad-x)s;--pz:%(pad-z)s;--p2:%(p2)s}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:transparent;overflow:hidden}
body{font-family:SS,sans-serif;color:var(--ivory);width:1920px;height:1080px;position:relative;overflow:hidden;-webkit-font-smoothing:antialiased}
.bc{font-family:BC,sans-serif;font-weight:700;text-transform:uppercase;letter-spacing:.02em}
.solid{background:var(--ground)}
.alpha{display:inline-block;font-family:BC;font-weight:700;letter-spacing:.12em;background:var(--sun);color:var(--ink);padding:2px 12px 0;border-radius:3px}
.g{display:inline-flex;align-items:center;justify-content:center;vertical-align:middle;font-family:BC;font-weight:700;color:var(--ink);line-height:1}
.g.btn{width:1.5em;height:1.5em;border-radius:50%%;font-size:1em}
.g.A{background:var(--pa)}.g.B{background:var(--pb);color:var(--ivory)}.g.XY{background:var(--px)}.g.Z{background:var(--pz);color:var(--ivory);border-radius:.3em;width:1.7em;height:1.2em}
.g.R,.g.L{background:var(--px);border-radius:.5em .5em .2em .2em;width:1.8em;height:1.2em}
.g.C{background:var(--sun);width:1.5em;height:1.5em;border-radius:50%%;font-size:1em}
.g.kw{background:var(--plate2);color:var(--ivory);border:1.5px solid var(--line2);border-radius:.35em;padding:0 .55em;height:1.4em;font-size:.82em;letter-spacing:.06em;text-transform:uppercase}
.g.dir{background:var(--plate2);color:var(--sun);border:1.5px solid var(--line2);border-radius:.35em;width:1.4em;height:1.4em;font-size:1em}
.g.dpad{background:none;width:2em;height:2em;position:relative}
.glyphs{display:inline-flex;align-items:center;gap:.28em;flex-wrap:wrap}
.pl{display:inline-block;color:var(--muted);font-family:BC;font-weight:700;padding:0 .08em}
""" % {k: C(k) for k in ('ground', 'ground2', 'plate', 'plate2', 'ink', 'ivory', 'text2', 'muted', 'sun', 'ember', 'ember-d',
                         'jade', 'rose', 'line', 'line2', 'pad-a', 'pad-b', 'pad-x', 'pad-z', 'p2')}

ARROW = {'up': '&uarr;', 'down': '&darr;', 'left': '&larr;', 'right': '&rarr;', 'fwd': '&rarr;', 'back': '&larr;', 'neutral': '&middot;'}


def dpad(direction):
    """A D-pad cross with one arm lit."""
    arms = {'up': (11, 0), 'down': (11, 19), 'left': (0, 11), 'right': (19, 11)}
    parts = ['<rect x="11" y="0" width="10" height="32" rx="2" fill="%s"/>' % C('plate2'),
             '<rect x="0" y="11" width="32" height="10" rx="2" fill="%s"/>' % C('plate2')]
    x, y = arms[direction]
    w, h = (10, 13) if direction in ('up', 'down') else (13, 10)
    parts.append('<rect x="%d" y="%d" width="%d" height="%d" rx="2" fill="%s"/>' % (x, y, w, h, C('sun')))
    return '<span class="g dpad"><svg viewBox="0 0 32 32" width="100%%" height="100%%">%s</svg></span>' % ''.join(parts)


def glyph(tok):
    """One input token to HTML. Tokens: A B X Y Z L R C(c-stick) | stick:up|down|left|right|fwd|back | dpad:down ... |
    '+' (and) '>' (then) | any other string is a small keyword chip (hold, tap, on hit, shield...)."""
    t = tok.strip()
    if t in ('+', '>', 'then'):
        return '<span class="pl">%s</span>' % ('+' if t == '+' else '&rsaquo;')
    if t in ('A', 'B'):
        return '<span class="g btn %s">%s</span>' % (t, t)
    if t in ('X', 'Y'):
        return '<span class="g btn XY">%s</span>' % t
    if t == 'Z':
        return '<span class="g Z">Z</span>'
    if t in ('L', 'R'):
        return '<span class="g %s">%s</span>' % (t, t)
    if t == 'C' or t.startswith('C:'):
        d = t.split(':')[1] if ':' in t else None
        return '<span class="g C">C</span>' + ('<span class="g dir">%s</span>' % ARROW[d] if d else '')
    if t.startswith('stick:'):
        return '<span class="g dir">%s</span>' % ARROW[t.split(':')[1]]
    if t.startswith('dpad:'):
        return dpad(t.split(':')[1])
    return '<span class="g kw">%s</span>' % t


def glyphs(toks):
    return '<span class="glyphs">%s</span>' % ''.join(glyph(t) for t in toks)


def html_page(body, css=''):
    return '<!doctype html><meta charset="utf-8"><style>%s%s%s</style><body>%s</body>' % (font_css(), BASE_CSS, css, body)


def render(pages, w=1920, h=1080, transparent=False, full_page=False):
    """pages: [(html, out_path)] -> PNGs. Raises if text overflows an element marked .fit."""
    from playwright.sync_api import sync_playwright
    errs = []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=['--force-color-profile=srgb'])
        for html, out in pages:
            pg = browser.new_page(viewport={'width': w, 'height': h})
            pg.set_content(html)
            pg.evaluate('document.fonts.ready')
            bad = pg.evaluate("""() => [...document.querySelectorAll('.fit')]
                .filter(e => e.scrollWidth > e.clientWidth + 1 || e.scrollHeight > e.clientHeight + 10)
                .map(e => e.textContent.trim().slice(0, 40))""")
            errs += ['overflow in %s: %s' % (Path(out).name, b) for b in bad]
            if not full_page and pg.evaluate('document.documentElement.scrollHeight') > h + 2:
                errs.append('page taller than %d: %s' % (h, Path(out).name))
            Path(out).parent.mkdir(parents=True, exist_ok=True)
            pg.screenshot(path=str(out), omit_background=transparent, full_page=full_page)
            pg.close()
        browser.close()
    return errs
