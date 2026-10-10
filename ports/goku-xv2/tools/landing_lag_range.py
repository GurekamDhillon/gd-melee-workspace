"""Landing-lag range of Melee's retail fighters (item #12). Reads each PlXx.dat ftCo_DatAttrs from GW_ISO_VANILLA
(local only, nothing derived is committed) and writes _build/goku-xv2/landing-lag-range.md. L-cancel halves the value (Melee rounds down)."""
import os, re, struct, sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'ports/ir/tools')); sys.path.insert(0, str(ROOT/'tools/mex_port'))
import mex_hsd
from attr_apply import attr_layout
for l in (ROOT/'.env').read_text().splitlines():
    m = re.match(r'\s*(?:export\s+)?(GW_ISO_VANILLA)=["\']?(.*?)["\']?\s*$', l)
    if m: os.environ.setdefault(m.group(1), m.group(2))
AIR = [('nair', 'landingairn_lag'), ('fair', 'landingairf_lag'), ('bair', 'landingairb_lag'), ('uair', 'landingairhi_lag'), ('dair', 'landingairlw_lag')]
NAMES = {'Ca':'Captain Falcon','Cl':'Young Link','Dk':'Donkey Kong','Dr':'Dr. Mario','Fc':'Falco','Fx':'Fox','Gn':'Ganondorf','Gw':'Mr. Game & Watch','Kb':'Kirby','Kp':'Bowser','Lg':'Luigi','Lk':'Link','Mr':'Mario','Ms':'Marth','Mt':'Mewtwo','Ns':'Ness','Pc':'Pichu','Pe':'Peach','Pk':'Pikachu','Pr':'Jigglypuff','Ic':'Ice Climbers','Ss':'Samus','Sk':'Sheik','Ys':'Yoshi','Zd':'Zelda','Fe':'Roy','Pp':'Popo','Nn':'Nana','Sm':'Sheik?','Gk':'Giga Bowser'}
def read_attrs(disc, code):
    pl = mex_hsd.Archive(disc.read(f'Pl{code}.dat'))
    root = pl.public(next(s for s, _ in pl.publics if s.startswith('ftData')))
    blk = struct.unpack_from('>I', pl.data, root)[0]
    L = attr_layout(); out = {}
    for _, k in AIR + [('normal', 'normal_landing_lag')]:
        off, is_int = L[k]; out[k] = struct.unpack_from('>i' if is_int else '>f', pl.data, blk+off)[0]
    return out
def _find(o, key):
    if isinstance(o, dict):
        if key in o: yield key, o
        for v in o.values(): yield from _find(v, key)
    elif isinstance(o, list):
        for v in o: yield from _find(v, key)
def lc(x): return max(int(x / 2), 1)   # ftCo_LandingAir_EnterWithLag: lag / xE8 (2), truncated, at least 1
def write_md(rows, play, ga):
    assert len(play) == 26 and all(c in rows for c in play)
    out = ['# Aerial landing lag: retail range vs Goku', '',
           'Source: `ftCo_DatAttrs` of the 26 playable retail fighters in the vanilla disc (`landingair{n,f,b,hi,lw}_lag`), read by `ports/goku-xv2/tools/landing_lag_range.py`. Local only.',
           'Frames = the attribute (the animation is rate-scaled to it). L-cancel = `int(lag / 2)`, min 1 (`ftCo_LandingAir_EnterWithLag`). A frame trace in game reads attr+1 (Goku bair attr 18 shows `Landing:19`).', '',
           '| aerial | min | min fighter | max | max fighter | Goku | in range | Goku L-cancel | L-cancel range | in range |', '|---|---|---|---|---|---|---|---|---|---|']
    res = {}
    for nm, k in AIR:
        v = {c: int(rows[c][k]) for c in play}
        mn, mx = min(v.values()), max(v.values()); lmn, lmx = min(map(lc, v.values())), max(map(lc, v.values()))
        g = int(ga[k]); out.append(f"| {nm} | {mn} | {', '.join(NAMES[c] for c in play if v[c] == mn)} | {mx} | {', '.join(NAMES[c] for c in play if v[c] == mx)} | {g} | {'yes' if mn <= g <= mx else 'NO'} | {lc(g)} | {lmn}-{lmx} | {'yes' if lmn <= lc(g) <= lmx else 'NO'} |")
        res[nm] = (g, mn, mx)
    out += ['', '## Per fighter (attribute frames: nair/fair/bair/uair/dair)', '']
    for c in play: out.append(f"- {NAMES[c]}: " + '/'.join(str(int(rows[c][k])) for _, k in AIR))
    (ROOT/'_build/goku-xv2/landing-lag-range.md').write_text(chr(10).join(out) + chr(10), encoding='utf-8')
    print(chr(10).join(out[6:11]))
def main():
    disc = mex_hsd.Gcm(os.environ['GW_ISO_VANILLA'])
    rows = {}
    for f in sorted(disc.files):
        m = re.fullmatch(r'Pl([A-Z][a-z])\.dat', f.rsplit('/', 1)[-1])
        if not m or m.group(1) in ('Co',): continue
        try: rows[m.group(1)] = read_attrs(disc, m.group(1))
        except Exception as e: print('skip', m.group(1), e, file=sys.stderr)
    PLAYABLE = ['Ca','Cl','Dk','Dr','Fc','Fe','Fx','Gn','Gw','Kb','Kp','Lg','Lk','Mr','Ms','Mt','Ns','Pc','Pe','Pk','Pp','Pr','Ss','Sk','Ys','Zd']  # 26 (Ice Climbers = Pp; Nana/Sandbag/wireframes/Giga Bowser/hands excluded)
    goku = json.loads((ROOT/'_build/goku-xv2/author-source/package/mods/goku-xv2/geno.json').read_text())
    ga = next(v for k, v in _find(goku, 'landingairn_lag'))
    write_md(rows, PLAYABLE, ga)
    json.dump(rows, open(ROOT/'_build/goku-xv2/landing-lag-raw.json', 'w'), indent=1)
    print(len(rows), 'fighters'); return rows
if __name__ == '__main__': main()
