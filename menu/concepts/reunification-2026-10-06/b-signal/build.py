#!/usr/bin/env python3
"""SIGNAL: one command renders everything.

    python build.py            # drives, screens, kit sheets, PNGs, index.html
    python build.py --only 04  # re-render screens whose name starts with 04 (and nothing else)

Headless Chromium through Playwright (no window), no network at render time. Deterministic: the drive PNGs come from the
committed generator's geometry (drives.py), the HTML from Python builders (ui.py, screens1.py, screens2.py, kitpage.py).
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import drives  # noqa: E402
import screens1, screens2, kitpage  # noqa: E402
from ui import page  # noqa: E402

OUT = HERE / "out"
SCR = HERE / "screens"
ALL = screens1.SCREENS1 + screens2.SCREENS2

TITLES = {
    "01-title": "Title", "02-main-menu": "Main menu", "03-solo": "Solo", "04-character-select": "Character select",
    "05-stage-select": "Stage select", "06-versus-rules": "Versus rules", "07-online-room": "Online room",
    "08-envoy-run-setup": "Envoy: run setup", "09-envoy-bag": "Envoy: the bag", "10-envoy-reward": "Envoy: reward",
    "11-envoy-hud": "In-match HUD (Envoy)", "12-pause": "Pause", "12b-payout": "End of stage: payout", "13-results": "Results",
    "14-settings-controls": "Settings: controls and remap", "14b-settings-video": "Settings: video", "14c-settings-audio": "Settings: audio",
    "15-mods": "Mods", "16-lab-pause": "The LAB pause menu", "17-launcher-play": "Launcher: Play",
}


def write_html():
    SCR.mkdir(exist_ok=True)
    for name, fn, has_wide in ALL:
        (SCR / (name + ".html")).write_text(fn(False) if not name.startswith("17") else fn(False), encoding="utf-8")
        if has_wide:
            (SCR / ("wide-" + name + ".html")).write_text(fn(True), encoding="utf-8")
    (HERE / "kit.html").write_text(kitpage.kit_html(), encoding="utf-8")


def jobs():
    """(html path, query zoom, viewport w, h, output png name, is_clip)"""
    J = []
    for name, fn, has_wide in ALL:
        if name.startswith("17"):
            J.append((SCR / (name + ".html"), 2, 2000, 1280, name + ".png"))
            continue
        J.append((SCR / (name + ".html"), 2, 1280, 960, name + ".png"))
        if has_wide:
            J.append((SCR / ("wide-" + name + ".html"), 2.25, 1920, 1080, "wide-" + name + ".png"))
        if name.startswith(("02", "09")):
            J.append((SCR / (name + ".html"), 1, 640, 480, "small-" + name + ".png"))
    return J


def render(only=None):
    from playwright.sync_api import sync_playwright
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        br = p.chromium.launch(args=["--force-color-profile=srgb", "--font-render-hinting=none"])
        for path, z, w, h, png in jobs():
            if only and not png.replace("wide-", "").replace("small-", "").startswith(only):
                continue
            pg = br.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
            pg.goto(path.as_uri() + "?z=%s" % z)
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(120)
            pg.screenshot(path=str(OUT / png), clip={"x": 0, "y": 0, "width": w, "height": h})
            pg.close()
            print("  ", png)
        if not only:
            kitpage.render_kit(br, HERE, OUT)
        br.close()


def index():
    pngs = []
    for name, fn, has_wide in ALL:
        t = TITLES.get(name, name)
        pngs.append((name, t, "out/" + name + ".png"))
    wide = [(n, TITLES[n], "out/wide-" + n + ".png") for n, _, w in ALL if w]
    small = [(n, TITLES[n], "out/small-" + n + ".png") for n, _, _ in ALL if n.startswith(("02", "09"))]
    kit = ["out/" + k for k in kitpage.KIT_PNGS]
    items = [("Screen " + t.split(" ")[0] if False else TITLES[n], p, "screen") for n, t, p in pngs]
    items += [("Wide 1920x1080: " + t, p, "wide") for n, t, p in wide]
    items += [("True 640x480: " + t, p, "small") for n, t, p in small]
    items += [("Kit: " + kitpage.KIT_TITLES[i], p, "kit") for i, p in enumerate(kit)]
    import json
    data = json.dumps([{"t": t, "p": p, "k": k} for t, p, k in items])
    html = INDEX.replace("__DATA__", data)
    (HERE / "index.html").write_text(html, encoding="utf-8")


INDEX = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>SIGNAL: menu mockups</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="tokens.css">
<style>
 body{margin:0;background:var(--ground);color:var(--bone);font-family:var(--f-body);font-weight:600}
 header{padding:28px 32px 8px;display:flex;gap:24px;align-items:baseline;flex-wrap:wrap}
 h1{font:800 56px/0.9 var(--f-display);text-transform:uppercase;margin:0;letter-spacing:-.004em}
 h1 span{color:var(--volt)}
 header p{margin:0;color:var(--mid);font-size:14px;max-width:560px}
 nav{padding:8px 32px 24px;display:flex;gap:22px;flex-wrap:wrap;font:700 20px var(--f-display);text-transform:uppercase;letter-spacing:.03em}
 nav a{color:var(--dim);cursor:pointer;padding-bottom:4px;border-bottom:3px solid transparent;text-decoration:none}
 nav a.on{color:var(--bone);border-bottom-color:var(--volt)}
 .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:28px 24px;padding:0 32px 64px}
 figure{margin:0;cursor:zoom-in}
 figure img{display:block;width:100%;height:auto;border:1px solid var(--line)}
 figure:hover img{border-color:var(--volt)}
 figcaption{font:500 12px var(--f-mono);letter-spacing:.06em;text-transform:uppercase;color:var(--mid);padding-top:8px}
 #lb{position:fixed;inset:0;background:rgba(8,9,11,.96);display:none;align-items:center;justify-content:center;z-index:9;flex-direction:column}
 #lb.on{display:flex}
 #lb img{max-width:96vw;max-height:88vh;border:1px solid var(--line)}
 #lb .cap{font:500 12px var(--f-mono);letter-spacing:.06em;text-transform:uppercase;color:var(--mid);padding:12px}
 #lb .cap b{color:var(--volt)}
</style></head><body>
<header><h1>Signal <span>/</span> menus</h1>
<p>Fast and minimal. Type does the work, one thing is in focus, everything else recedes. Click a picture to zoom; left and right move between pictures; Esc closes. The kit showcase is under Kit, or open <a href="kit.html" style="color:var(--volt)">kit.html</a>.</p></header>
<nav id="nav"></nav><div class="grid" id="g"></div>
<div id="lb"><img id="li" alt=""><div class="cap" id="lc"></div></div>
<script>
const D=__DATA__; const KINDS=[["all","All"],["screen","Screens"],["wide","Wide"],["small","Small"],["kit","Kit"]];
let kind="all", list=[], idx=0;
const g=document.getElementById("g"), lb=document.getElementById("lb");
function draw(){ list=D.filter(d=>kind=="all"||d.k==kind); g.innerHTML="";
 list.forEach((d,i)=>{const f=document.createElement("figure"); f.innerHTML='<img loading="lazy" src="'+d.p+'" alt=""><figcaption>'+d.t+'</figcaption>'; f.onclick=()=>open(i); g.appendChild(f);});
 document.getElementById("nav").innerHTML=KINDS.map(k=>'<a class="'+(k[0]==kind?"on":"")+'" data-k="'+k[0]+'">'+k[1]+'</a>').join("");
 document.querySelectorAll("nav a").forEach(a=>a.onclick=()=>{kind=a.dataset.k;draw();}); }
function open(i){ idx=(i+list.length)%list.length; document.getElementById("li").src=list[idx].p;
 document.getElementById("lc").innerHTML="<b>"+(idx+1)+" / "+list.length+"</b> &nbsp; "+list[idx].t; lb.classList.add("on"); }
lb.onclick=()=>lb.classList.remove("on");
addEventListener("keydown",e=>{ if(!lb.classList.contains("on")) return;
 if(e.key=="ArrowRight")open(idx+1); else if(e.key=="ArrowLeft")open(idx-1); else if(e.key=="Escape")lb.classList.remove("on"); });
draw();
</script></body></html>
"""


if __name__ == "__main__":
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]
    if only is None:
        print("drives:", len(drives.build(HERE / "assets" / "drives")), "png")
    write_html()
    render(only)
    if only is None:
        index()
    print("done")
