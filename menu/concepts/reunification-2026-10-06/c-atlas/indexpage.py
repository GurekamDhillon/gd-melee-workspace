"""index.html: a local gallery of every ATLAS preview. Opens from the file system (no server, no network)."""
import html
import json


def make(screens, wide, small, kit_jobs):
    items = []   # (group, title, file)
    for name, fn, title in screens:
        items.append(("Screens (1280x960)", "%s  %s" % (name.split("-")[0], title), "out/%s.png" % name))
    for name, fn, title in screens:
        if name in wide:
            items.append(("Wide (1920x1080)", "%s  %s, wide" % (name.split("-")[0], title), "out/wide-%s.png" % name))
    for name, fn, title in screens:
        if name in small:
            items.append(("Legibility: true 640x480", "%s  %s, 1:1" % (name.split("-")[0], title), "out/small-%s.png" % name))
    for html_, sel, png, scale, width in kit_jobs:
        items.append(("Kit showcase", png.replace(".png", "").replace("kit-", "").replace("-", " "), "out/" + png))
    groups = []
    for g, t, f in items:
        if not groups or groups[-1][0] != g:
            groups.append((g, []))
        groups[-1][1].append((t, f))
    secs = []
    n = 0
    for g, lst in groups:
        cards = []
        for t, f in lst:
            cards.append('<a class="card" href="%s" data-i="%d"><img loading="lazy" src="%s" alt="%s"><span>%s</span></a>' % (f, n, f, html.escape(t), html.escape(t)))
            n += 1
        secs.append('<h2>%s</h2><div class="grid">%s</div>' % (html.escape(g), "".join(cards)))
    data = json.dumps([{"t": t, "f": f} for g, l in groups for t, f in l])
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>ATLAS menu mockups</title><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<link rel="stylesheet" href="tokens.css"><style>'
            'body{margin:0;background:var(--ground);color:var(--ivory);font-family:var(--f-ui);font-weight:600}'
            'header{padding:28px 32px 8px;display:flex;align-items:baseline;gap:18px;flex-wrap:wrap}'
            'h1{margin:0;font-family:var(--f-cap);font-weight:700;font-size:44px;letter-spacing:.08em;text-transform:uppercase}'
            'h1 i{font-style:normal;color:var(--ember)}header p{margin:0;color:var(--muted);font-size:15px;max-width:640px}'
            'header a{color:var(--ink);background:var(--ember);padding:6px 14px;text-decoration:none;font-family:var(--f-cap);font-weight:600;letter-spacing:.12em;text-transform:uppercase;font-size:16px}'
            'h2{font-family:var(--f-cap);font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);font-size:18px;margin:26px 32px 10px;border-bottom:1px solid var(--line);padding-bottom:6px}'
            '.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px;padding:0 32px}'
            '.card{display:block;background:var(--plate);border-bottom:3px solid var(--edge);text-decoration:none;color:var(--ivory);position:relative}'
            '.card:hover,.card:focus{background:var(--lift);border-bottom-color:var(--ember);outline:none}'
            '.card img{display:block;width:100%;height:auto;background:#000}.card span{display:block;padding:8px 10px;font-size:14px}'
            '#z{position:fixed;inset:0;background:rgba(5,7,10,.94);display:none;flex-direction:column;align-items:center;justify-content:center;z-index:9}'
            '#z.on{display:flex}#z img{max-width:96vw;max-height:88vh;display:block}#z .cap{margin-top:10px;color:var(--muted);font-size:15px;font-family:var(--f-ui)}'
            '#z button{position:absolute;top:14px;right:18px;background:none;border:0;color:var(--ivory);font-size:30px;cursor:pointer}'
            'footer{padding:28px 32px 40px;color:var(--dim);font-size:13px}'
            '</style></head><body><header><h1>Atlas<i>.</i></h1><p>Rich and layered, kept calm: one primary pane, one explainer, a trail that says where you are. Click an image to zoom; use the left and right arrow keys to move between them; Esc closes.</p><a href="kit.html">Kit showcase (live page)</a></header>'
            '@@SECS@@<footer>Original work. Disc art is always a labelled placeholder. Drive models are drawn from the committed generator geometry (envoy_drives). Fonts: Source Sans 3, Hasklug, Barlow Condensed (SIL OFL).</footer>'
            '<div id="z"><button aria-label="close">&times;</button><img alt=""><div class="cap"></div></div>'
            '<script>var D=@@DATA@@,cur=0,z=document.getElementById("z"),im=z.querySelector("img"),cp=z.querySelector(".cap");'
            'function show(i){cur=(i+D.length)%D.length;im.src=D[cur].f;cp.textContent=D[cur].t+"  ("+(cur+1)+" / "+D.length+")";z.className="on"}'
            'document.querySelectorAll(".card").forEach(function(a){a.addEventListener("click",function(e){e.preventDefault();show(+a.dataset.i)})});'
            'z.addEventListener("click",function(e){if(e.target!==im)z.className=""});'
            'document.addEventListener("keydown",function(e){if(!z.classList.contains("on"))return;if(e.key=="ArrowRight")show(cur+1);else if(e.key=="ArrowLeft")show(cur-1);else if(e.key=="Escape")z.className=""});'
            '</script></body></html>').replace("@@SECS@@", "".join(secs)).replace("@@DATA@@", data)
