"""Review sheets for the animation pass (system Python + Pillow; Blender runs headless through render_review.py).
    python src/review.py <round> film <clip> [step] [first] [last]      before / after filmstrip, fixed frame step
    python src/review.py <round> sil  <name> <clip:frame> ...           flat-black silhouette sheet (before above, after below)
    python src/review.py <round> side <clip> [frames]                    side-view strip with ground line and sole-contact markers
    python src/review.py <round> arcs <name> <clip> [bones]              hand / foot paths (onion skin), before and after
    python src/review.py <round> small <name> <clip:frame> ...           ~120 px tall poses, before and after
BEFORE is the first lane's source (_build/audit-20261003/geno-art2/before_src), AFTER is this src. Output goes to
_build/audit-20261003/geno-art2/renders/<round>/ (each PNG <= 1024 px wide).
"""
import sys, os, json, subprocess
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
ROOT = os.path.normpath(os.path.join(PKG, "..", ".."))
G2 = os.path.join(ROOT, "_build", "audit-20261003", "geno-art2")
BEFORE = os.path.join(G2, "before_src")
BLEND = os.path.join(PKG, "out", "stage1_model.blend")
BG = (205, 208, 214)

def p(x): return x.replace("\\", "/")

def blender(spec, tag):
    os.makedirs(os.path.join(G2, "raw"), exist_ok=True)
    jf = os.path.join(G2, "raw", f"jobs_{tag}.json")
    json.dump(spec, open(jf, "w"))
    r = subprocess.run(["C:/Program Files/Git/usr/bin/bash.exe", p(os.path.join(G2, "bl.sh")), p(os.path.join(HERE, "render_review.py")), p(BLEND), p(jf)], capture_output=True, text=True)
    if "RENDERED" not in r.stdout and not spec.get("dump"):
        print(r.stdout[-1500:], r.stderr[-800:]); raise SystemExit("render failed: " + tag)
    return r.stdout

def jobs_for(clip_frames, tag, src, view="left", res=(128, 170), scale=17.0, target=(0, -1.0, 6.0), sil=False, dump=False):
    rawd = os.path.join(G2, "raw", tag); os.makedirs(rawd, exist_ok=True)
    jobs = []
    for i, (c, f) in enumerate(clip_frames):
        jobs.append(dict(out=p(os.path.join(rawd, f"{i:03d}_{c}_{f}.png")), clip=c, frame=int(f), view=view, res=list(res), scale=scale, target=list(target), sil=sil))
    spec = dict(jobs=jobs)
    if src: spec["src"] = p(src)
    return spec, [j["out"] for j in jobs]

def render(clip_frames, tag, src, **kw):
    spec, outs = jobs_for(clip_frames, tag, src, **kw)
    blender(spec, tag)
    return outs

def sheet(rows, labels, out, cell, cols, pad=3, label_h=12, title=None, maxw=1024):
    """rows: list of (row_label, [png paths], [cell labels])"""
    cw, ch = cell
    n = sum((len(r[1]) + cols - 1) // cols for r in rows)
    W = cols * (cw + pad) + pad + 40
    H = n * (ch + label_h + pad) + pad + (14 if title else 0)
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    if title: d.text((4, 1), title, fill=(10, 10, 30))
    y = pad + (14 if title else 0)
    for rl, files, labs in rows:
        for k in range(0, len(files), cols):
            if k == 0: d.text((2, y + label_h + ch // 2 - 6), rl, fill=(150, 30, 30) if rl.startswith("B") else (20, 100, 40))
            for i, f in enumerate(files[k:k + cols]):
                a = Image.open(f).convert("RGB")
                if a.size != (cw, ch): a = a.resize((cw, ch), Image.LANCZOS)
                x = 40 + pad + i * (cw + pad)
                im.paste(a, (x, y + label_h))
                d.text((x + 2, y), str(labs[k + i]) if labs else "", fill=(20, 20, 30))
            y += ch + label_h + pad
    if W > maxw: im = im.resize((maxw, int(H * maxw / W)), Image.LANCZOS)
    im.save(out, optimize=True)
    print("WROTE", out, im.size)

def outdir(rnd):
    d = os.path.join(G2, "renders", rnd); os.makedirs(d, exist_ok=True); return d

def film(rnd, clip, step=None, first=0, last=None, n_cells=8, before=True, view="left", name=None, frames=None):
    if frames is None:
        step = step or 1
        frames = list(range(first, (last if last is not None else first + step * (n_cells - 1)) + 1, step))[:n_cells]
    rows = []
    cell = (128, 170)
    if before:
        o = render([(clip, f) for f in frames], f"film_b_{clip}", BEFORE, view=view)
        rows.append(("BEFORE", o, frames))
    o = render([(clip, f) for f in frames], f"film_a_{clip}", None, view=view)
    rows.append(("AFTER", o, frames))
    sheet(rows, None, os.path.join(outdir(rnd), f"film_{name or clip}.png"), cell, len(frames), title=f"{clip}  frames {frames[0]}..{frames[-1]} step {frames[1]-frames[0] if len(frames) > 1 else 1}")

def sil(rnd, name, items, before=True, small=False):
    cf = [(c.split(":")[0], int(c.split(":")[1])) for c in items]
    res = (96, 128) if not small else (80, 106)
    cols = min(len(cf), 10)
    rows = []
    if before:
        rows.append(("BEFORE", render(cf, f"sil_b_{name}", BEFORE, sil=True, res=res, scale=17.0, target=(0, -0.8, 6.0)), [f"{c} {f}" for c, f in cf]))
    rows.append(("AFTER", render(cf, f"sil_a_{name}", None, sil=True, res=res, scale=17.0, target=(0, -0.8, 6.0)), [f"{c} {f}" for c, f in cf]))
    sheet(rows, None, os.path.join(outdir(rnd), f"sil_{name}.png"), res, cols, title=f"silhouettes: {name}")

def small(rnd, name, items, before=True):
    cf = [(c.split(":")[0], int(c.split(":")[1])) for c in items]
    res = (120, 120)
    cols = min(len(cf), 8)
    rows = []
    # the match size: about 120 px tall for the 12-unit fighter -> scale ~ 15 units in a 120 px frame
    if before: rows.append(("BEFORE", render(cf, f"sm_b_{name}", BEFORE, res=res, scale=15.0, target=(0, -0.8, 5.8)), [f"{c} {f}" for c, f in cf]))
    rows.append(("AFTER", render(cf, f"sm_a_{name}", None, res=res, scale=15.0, target=(0, -0.8, 5.8)), [f"{c} {f}" for c, f in cf]))
    sheet(rows, None, os.path.join(outdir(rnd), f"small_{name}.png"), res, cols, title=f"~120 px: {name}")

def side(rnd, clip, nfr=12, speed=None, before=True):
    """Side-view strip over one cycle: ground line, scrolling ground ticks at the body speed, sole contact markers (z < 0.15)."""
    out_rows = []
    for tag, src in ((("B", BEFORE),) if before else ()) + (("A", None),):
        dumpf = os.path.join(G2, "raw", f"dump_{tag}_{clip}.json")
        spec = dict(jobs=[], dump=[clip], dump_out=p(dumpf))
        if src: spec["src"] = p(src)
        blender(spec, f"dump_{tag}_{clip}")
        D = json.load(open(dumpf))[clip]
        n = len(D)
        frames = [int(i * n / nfr) for i in range(nfr)]
        o = render([(clip, f) for f in frames], f"side_{tag}_{clip}", src, res=(150, 150), scale=14.0, target=(0, 0.0, 5.4), view="left")
        # ground speed: from the manifest ref (after) or the old manifest (before)
        out_rows.append((tag, o, frames, D))
    cell = (150, 150)
    pad = 3
    H = len(out_rows) * (cell[1] + 14 + pad) + pad + 14
    W = nfr * (cell[0] + pad) + pad + 40
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    d.text((4, 1), f"{clip}: ground line, scrolling ticks at the reference ground speed; red = sole point on the ground", fill=(10, 10, 30))
    refs = json.load(open(os.path.join(G2, "before_manifest.json"))) if before else None
    mref = json.load(open(os.path.join(PKG, "manifest.json")))
    sp_after = [c for c in mref["clips"] if c["name"] == clip][0]["ref"].get("ground_ref_speed", 0.0)
    sp_before = [c for c in refs["clips"] if c["name"] == clip][0]["ref"].get("ground_ref_speed", 0.0) if before else 0.0
    y = 14
    for tag, files, frames, D in out_rows:
        sp = sp_before if tag == "B" else sp_after
        d.text((2, y + 70), "BEFORE" if tag == "B" else "AFTER", fill=(150, 30, 30) if tag == "B" else (20, 100, 40))
        for i, (fpath, f) in enumerate(zip(files, frames)):
            x0 = 40 + pad + i * (cell[0] + pad)
            im.paste(Image.open(fpath).convert("RGB"), (x0, y + 14))
            sc = cell[1] / 14.0
            gy = y + 14 + cell[1] / 2 + 5.4 * sc            # z = 0
            d.line([(x0, gy), (x0 + cell[0], gy)], fill=(30, 30, 30), width=1)
            # ticks every 1 unit, scrolling backwards at the ground speed (image right = behind the character)
            for k in range(-20, 21):
                tx = x0 + cell[0] / 2 + (k * 1.0 - sp * f) * sc
                if x0 <= tx <= x0 + cell[0]: d.line([(tx, gy), (tx, gy + 4)], fill=(30, 30, 30))
            row = D[f]
            for nm in ("heel_L", "ball_L", "tip_L", "heel_R", "ball_R", "tip_R"):
                yy, zz = row[nm][1], row[nm][2]
                if zz < 0.15:
                    px = x0 + cell[0] / 2 + (yy - 0.0) * sc
                    d.ellipse([px - 2.5, gy - 2.5, px + 2.5, gy + 2.5], fill=(220, 30, 30))
            d.text((x0 + 2, y), f"f{f}", fill=(20, 20, 30))
        y += cell[1] + 14 + pad
    if W > 1024: im = im.resize((1024, int(H * 1024 / W)), Image.LANCZOS)
    path = os.path.join(outdir(rnd), f"side_{clip}.png"); im.save(path, optimize=True); print("WROTE", path, im.size)

def arcs(rnd, name, clip, bones=("hand_L", "hand_R", "foot_L", "foot_R"), before=True, view="side"):
    cols = {"hand_L": (220, 60, 40), "hand_R": (230, 140, 20), "foot_L": (40, 90, 200), "foot_R": (30, 160, 130), "head": (120, 60, 160)}
    panels = []
    for tag, src in ((("BEFORE", BEFORE),) if before else ()) + (("AFTER", None),):
        dumpf = os.path.join(G2, "raw", f"dumpa_{tag}_{clip}.json")
        spec = dict(jobs=[], dump=[clip], dump_out=p(dumpf))
        if src: spec["src"] = p(src)
        blender(spec, f"dumpa_{tag}_{clip}")
        D = json.load(open(dumpf))[clip]
        n = len(D)
        W, H, sc = 360, 330, 24.0
        im = Image.new("RGB", (W, H), (236, 238, 242)); d = ImageDraw.Draw(im)
        def pt(row, k):
            tp = row["tp"]
            return (W / 2 + (row[k][1] + tp[1]) * sc * -1 * -1 if False else W / 2 + (row[k][1] + tp[1] * 1.0) * sc * 1.0, H - 20 - (row[k][2]) * sc * 1.0)
        # facing -Y is image left: x = W/2 + y*sc
        def P2(row, k): return (W / 2 + (row[k][1]) * sc, H - 20 - row[k][2] * sc)
        d.line([(0, H - 20), (W, H - 20)], fill=(60, 60, 60))
        for fi in range(0, n, max(1, n // 6)):          # onion-skin stick figures
            row = D[fi]
            a = 40 + int(120 * fi / max(1, n - 1))
            segs = [("hips", "chest"), ("chest", "head"), ("hips", "shin_L"), ("shin_L", "foot_L"), ("hips", "shin_R"), ("shin_R", "foot_R"), ("chest", "forearm_L"), ("forearm_L", "hand_L"), ("chest", "forearm_R"), ("forearm_R", "hand_R")]
            for s0, s1 in segs: d.line([P2(row, s0), P2(row, s1)], fill=(a + 60, a + 60, a + 70), width=2)
        for b in bones:
            if b not in cols: continue
            ptsb = [P2(D[i], b) for i in range(n)]
            d.line(ptsb, fill=cols[b], width=2)
            for i, q in enumerate(ptsb):
                r = 2 if i % 4 else 3
                d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], outline=cols[b])
        d.text((4, 2), f"{tag}  {clip}  (side view, character faces left; paths of {', '.join(bones)})", fill=(10, 10, 30))
        panels.append(im)
    W = sum(i.size[0] for i in panels) + 4 * (len(panels) - 1)
    out = Image.new("RGB", (W, panels[0].size[1]), BG)
    x = 0
    for im in panels: out.paste(im, (x, 0)); x += im.size[0] + 4
    path = os.path.join(outdir(rnd), f"arcs_{name}.png"); out.save(path, optimize=True); print("WROTE", path, out.size)

if __name__ == "__main__":
    a = sys.argv[1:]
    rnd, kind = a[0], a[1]
    if kind == "film":
        film(rnd, a[2], int(a[3]) if len(a) > 3 else None, int(a[4]) if len(a) > 4 else 0, int(a[5]) if len(a) > 5 else None)
    elif kind == "sil": sil(rnd, a[2], a[3:])
    elif kind == "small": small(rnd, a[2], a[3:])
    elif kind == "side": side(rnd, a[2], int(a[3]) if len(a) > 3 else 12)
    elif kind == "arcs": arcs(rnd, a[2], a[3], tuple(a[4].split(",")) if len(a) > 4 else ("hand_L", "hand_R", "foot_L", "foot_R"))
