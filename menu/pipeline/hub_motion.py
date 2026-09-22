"""Motion spec for the hub: selection, confirm, and screen transitions.

    python pipeline/hub_motion.py

Every motion is a set of keyframed channels at 60 fps, in the shape HSD
animation takes (per-key interpolation: con / lin / spl with a slope). The
preview is sampled from exactly these curves, so what you see is what the
tracks say. Writes, next to hub.py's output:

    out_hub/hub_motion.json          events -> HSD tracks, joint tree, sfx cues
    out_hub/preview/motion_1x.gif    the demo sequence (30 fps sample)
    out_hub/preview/motion_select_sheet_2x.png   one selection, frame by frame

Joint tree the tracks assume (one animjoint per joint, so channels that
could overlap in time live on different joints):

    tile_<id>          slide (screen transitions) + recoil      TRA_X/Y
      plate_<id>       stays at rest                            ALPHA
      lift_<id>        lift + scale, origin = face centre       TRA_X/Y, SCA_X/Y
        face / icon / label                                     DIFFUSE_RGB
"""
import base64
import io
import json
import math
import os
import sys

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hub as H                                           # noqa: E402
import hub_layout as L                                    # noqa: E402

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "out_hub")
FPS = 60
C = L.C
LIFT = L.STATES["sel"]["offset"]          # [-5, -5] at lift = 1
RECOIL_PX = 2.0
SLIDE_PX = 720
MIN_CONTRAST = 3.0                        # WCAG large text


# ------------------------------------------------------------ curves
def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def _lerp(a, b, u):
    if isinstance(a, tuple):
        return tuple(x + (y - x) * u for x, y in zip(a, b))
    return a + (b - a) * u


def evaluate(keys, t):
    """keys: [(frame, value, interp, slope)]; interp applies to the segment
    that starts at that key, as in HSD. slope is value/frame (spl only)."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (f0, v0, ip, s0), (f1, v1, _, s1) in zip(keys, keys[1:]):
        if t < f1:
            if ip == "con":
                return v0
            u = (t - f0) / (f1 - f0)
            if ip == "lin":
                return _lerp(v0, v1, u)
            d = f1 - f0
            h00, h10 = 2 * u**3 - 3 * u**2 + 1, u**3 - 2 * u**2 + u
            h01, h11 = -2 * u**3 + 3 * u**2, u**3 - u**2
            return h00 * v0 + h10 * d * s0 + h01 * v1 + h11 * d * s1
    return keys[-1][1]


class Channels:
    """Latest event wins per channel; an event's first key starts from the
    channel's current value, so an interrupted motion never pops."""
    def __init__(self):
        self.ch = {}                     # name -> [(start, keys)] in start order

    def value(self, name, f, default):
        live = [(s, k) for s, k in self.ch.get(name, []) if s <= f]
        if not live:
            return default
        start, keys = live[-1]
        return evaluate(keys, f - start)

    def start(self, name, f, keys, default):
        cur = self.value(name, f, default)
        k0 = keys[0]
        keys = [(k0[0], cur if k0[1] is None else k0[1], k0[2], k0[3])] + list(keys[1:])
        self.ch.setdefault(name, []).append((f, keys))


# ------------------------------------------------------------ events
# Values of None mean "from wherever the channel is now".
def ev_select():
    return {
        # lift overshoots to 1.3 (6.5px) then settles at 1 (5px). 1.4 + a 4%
        # pop put the hero's corner 0.6px outside title-safe
        "lift":  [(0, None, "spl", 0), (4, 1.3, "spl", 0), (9, 1.0, "spl", 0)],
        "scale": [(0, None, "spl", 0), (3, 1.03, "spl", 0), (10, 1.0, "spl", 0)],
        # face snaps to a bright flash on frame 1, then eases to gold: no
        # muddy mid-tone frame for the label to sit on
        "face":  [(0, None, "lin", 0), (1, hexrgb(C["gold_lt"]), "lin", 0),
                  (8, hexrgb(C["gold"]), "lin", 0)],
        # icons snap with the label: a tween goes grey for 4 frames
        "icon":  [(0, None, "con", 0), (1, hexrgb(C["gold_dk"]), "con", 0)],
        "plate": [(0, 1.0, "con", 0)],
    }


def ev_deselect():
    return {
        "lift":  [(0, None, "spl", 0), (5, 0.0, "spl", 0)],
        "scale": [(0, None, "spl", 0), (5, 1.0, "spl", 0)],
        "face":  [(0, None, "lin", 0), (2, hexrgb(C["cobalt"]), "lin", 0)],
        "icon":  [(0, None, "con", 0), (2, hexrgb(C["cobalt_hi"]), "con", 0)],
        # plate hides the frame the face lands on it
        "plate": [(0, 1.0, "con", 0), (5, 0.0, "con", 0)],
    }


def ev_recoil():
    return {"recoil": [(0, 0.0, "spl", 0), (3, 1.0, "spl", 0), (10, 0.0, "spl", 0)]}


def ev_confirm():
    return {
        # slam onto the plate, small bounce, settle down
        "lift":  [(0, None, "spl", 0), (3, 0.0, "spl", 0), (6, 0.35, "spl", 0),
                  (10, 0.0, "spl", 0)],
        "scale": [(0, None, "spl", 0), (3, 0.97, "spl", 0), (10, 1.0, "spl", 0)],
        "face":  [(0, None, "lin", 0), (3, hexrgb(C["bone"]), "lin", 0),
                  (12, hexrgb(C["gold"]), "lin", 0)],
    }


def ev_desc_in():
    return {"desc_a":  [(0, None, "lin", 0), (6, 1.0, "lin", 0)],
            "desc_dx": [(0, -12.0, "spl", 0), (6, 0.0, "spl", 0)]}


def ev_desc_out():
    return {"desc_a": [(0, None, "lin", 0), (3, 0.0, "lin", 0)]}


def ev_slide_out():
    # ease-in: leaves slowly, then fast (-120 px/frame at the end)
    return {"slide": [(0, 0.0, "spl", 0), (12, -SLIDE_PX, "spl", -120)]}


def ev_slide_in():
    # arrives fast from the right, overshoots 6px, settles
    return {"slide": [(0, SLIDE_PX, "spl", -120), (12, -6.0, "spl", 0),
                      (17, 0.0, "spl", 0)]}


def ev_bar(dy_from, dy_to, dur=10):
    return [(0, dy_from, "spl", 0), (dur, dy_to, "spl", 0)]


# ---------------------------------------------------------- contrast
def lum(rgb):
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# ------------------------------------------------------------ sequencer
class Hub:
    def __init__(self, layout):
        self.layout = layout
        self.ids = [t["id"] for t in layout["tiles"]]
        self.pivot = {}
        for t in layout["tiles"]:
            face = t["quads"][1]["verts"]
            self.pivot[t["id"]] = (sum(v[0] for v in face) / 4, sum(v[1] for v in face) / 4)
        self.ch = Channels()
        self.sel = None
        self.prev = None
        self.sfx = []
        self.transitions = []            # (f0, f1): intentionally off title-safe

    DEFAULTS = dict(lift=0.0, scale=1.0, plate=0.0, recoil=0.0, slide=0.0,
                    desc_a=0.0, desc_dx=0.0, dy=0.0)

    def default(self, tid, name):
        if name in self.DEFAULTS:
            return self.DEFAULTS[name]
        ng = L.STATES["ng"]
        return hexrgb({"face": ng["face"], "icon": ng["icon"], "label": ng["label"]}[name])

    def start(self, tid, f, event):
        for name, keys in event.items():
            self.ch.start("%s.%s" % (tid, name), f, keys, self.default(tid, name))

    def get(self, tid, name, f):
        return self.ch.value("%s.%s" % (tid, name), f, self.default(tid, name))

    def _label_switch(self, tid, f, to_ink):
        """Switch the label colour on the first frame where the new colour
        reads better against the face than the old one."""
        ink, bone = hexrgb(C["ink"]), hexrgb(C["bone"])
        new, old = (ink, bone) if to_ink else (bone, ink)
        for k in range(0, 16):
            face = self.get(tid, "face", f + k)
            if contrast(new, face) >= contrast(old, face):
                self.ch.start("%s.label" % tid, f, [(0, old, "con", 0), (k, new, "con", 0)],
                              old)
                return k
        raise RuntimeError("label never becomes legible for %s" % tid)

    def select(self, tid, f, initial=False):
        if initial:
            self.sel = tid
            st = L.STATES["sel"]
            self.start(tid, f, {"lift": [(0, 1.0, "con", 0)], "plate": [(0, 1.0, "con", 0)],
                                "face": [(0, hexrgb(st["face"]), "con", 0)],
                                "icon": [(0, hexrgb(st["icon"]), "con", 0)],
                                "label": [(0, hexrgb(st["label"]), "con", 0)],
                                "desc_a": [(0, 1.0, "con", 0)]})
            return
        old, self.prev, self.sel = self.sel, self.sel, tid
        self.sfx.append((f, "sfx_cursor_move"))
        self.start(old, f, ev_deselect())
        self._label_switch(old, f, to_ink=False)
        self.start(old, f, ev_desc_out())
        self.start(tid, f, ev_select())
        self._label_switch(tid, f, to_ink=True)
        self.start(tid, f, ev_desc_in())
        px, py = self.pivot[tid]
        for o in self.ids:
            if o in (tid, old):
                continue
            ox, oy = self.pivot[o]
            n = math.hypot(ox - px, oy - py)
            self.dirs = getattr(self, "dirs", {})
            self.dirs[o] = ((ox - px) / n, (oy - py) / n)
            self.start(o, f, ev_recoil())

    def confirm(self, f):
        self.sfx.append((f + 3, "sfx_confirm"))        # on impact, not on press
        self.start(self.sel, f, ev_confirm())

    def screen_out(self, f):
        self.sfx.append((f, "sfx_screen_whoosh"))
        order = [t for t in self.ids if t != self.sel] + [self.sel]   # chosen leaves last
        for i, tid in enumerate(order):
            self.start(tid, f + 2 * i, ev_slide_out())
        self.start("_bp", f, ev_slide_out())
        self.start("_hdr", f, {"dy": ev_bar(0.0, -60.0)})
        self.start("_ftr", f, {"dy": ev_bar(0.0, 60.0)})
        self.transitions.append((f, 10 ** 9))       # gone until the next screen

    def screen_in(self, f):
        self.sfx.append((f, "sfx_screen_whoosh"))
        order = sorted(self.ids, key=lambda t: next(
            x["rank"] for x in self.layout["tiles"] if x["id"] == t))
        stagger = [0, 3, 5, 7]
        # frames before a tile's stagger start must already be off-screen
        for tid, s in zip(order, stagger):
            self.ch.start("%s.slide" % tid, f, [(0, SLIDE_PX, "con", 0)], 0.0)
            self.ch.start("%s.slide" % tid, f + s, ev_slide_in()["slide"], 0.0)
        self.ch.start("_bp.slide", f, ev_slide_in()["slide"], 0.0)
        self.ch.start("_hdr.dy", f, ev_bar(-60.0, 0.0), 0.0)
        self.ch.start("_ftr.dy", f, ev_bar(60.0, 0.0), 0.0)
        self.transitions.append((f, f + stagger[-1] + 17))

    # ------------------------------------------------------- geometry
    def tile_state(self, tid, f):
        g = lambda n: self.get(tid, n, f)                   # noqa: E731
        dx, dy = getattr(self, "dirs", {}).get(tid, (0, 0))
        rc = g("recoil") * RECOIL_PX
        return dict(outer=(g("slide") + dx * rc, dy * rc), lift=g("lift"), scale=g("scale"),
                    face=g("face"), icon=g("icon"), label=g("label"), plate=g("plate"),
                    desc_a=g("desc_a"), desc_dx=g("desc_dx"))

    def frame_geometry(self, f):
        """-> list of (quad, verts, colour_rgb, opacity) in draw order."""
        out = []
        hdr = self.ch.value("_hdr.dy", f, 0.0)
        ftr = self.ch.value("_ftr.dy", f, 0.0)
        bp = self.ch.value("_bp.slide", f, 0.0)
        for q in self.layout["quads"]:
            if q["role"] == "decor":
                off = (0, 0)
            elif q["id"].startswith("header"):
                off = (0, hdr)
            elif q["id"].startswith("footer"):
                off = (0, ftr)
            else:
                off = (bp, 0)
            out.append((q, [(x + off[0], y + off[1]) for x, y in q["verts"]],
                        hexrgb(q["colour"]), 1.0))

        z = [t for t in self.ids if t not in (self.sel, self.prev)] + \
            [t for t in (self.prev, self.sel) if t]
        for tid in z:
            t = next(x for x in self.layout["tiles"] if x["id"] == tid)
            s = self.tile_state(tid, f)
            ox, oy = s["outer"]
            px, py = self.pivot[tid]
            lx, ly = LIFT[0] * s["lift"], LIFT[1] * s["lift"]
            sc = s["scale"]
            for q in t["quads"]:
                if q["role"] == "plate":
                    if s["plate"] > 0:
                        out.append((q, [(x + ox, y + oy) for x, y in q["verts"]],
                                    hexrgb(L.STATES["sel"]["plate"]), s["plate"]))
                    continue
                verts = [(px + sc * (x - px) + lx + ox, py + sc * (y - py) + ly + oy)
                         for x, y in q["verts"]]
                out.append((q, verts, s[q["role"]], 1.0))
        for t in self.layout["tiles"]:
            s = self.tile_state(t["id"], f)
            if s["desc_a"] > 0.01:
                q = t["desc"]
                out.append((q, [(x + s["desc_dx"], y + ftr) for x, y in q["verts"]],
                            hexrgb(q["colour"]), s["desc_a"]))
        return out


# ------------------------------------------------------------ render
def svg_frame(geo, b64, sizes, clear, scale):
    defs, body = [], []
    for i, (q, verts, rgb, a) in enumerate(geo):
        col = "#%02x%02x%02x" % tuple(max(0, min(255, round(c))) for c in rgb)
        pts = " ".join("%.3f,%.3f" % v for v in verts)
        op = ' opacity="%.3f"' % a if a < 1 else ""
        if q["kind"] != "textured":
            body.append('<polygon points="%s" fill="%s"%s/>' % (pts, col, op))
            continue
        a_, b_, c_, d_, e_, f_ = H._matrix(dict(q, verts=[list(v) for v in verts]),
                                          sizes[q["texture"]])
        W, Ht = sizes[q["texture"]]
        defs.append('<mask id="m%d" maskUnits="userSpaceOnUse" x="-800" y="-100" '
                    'width="2240" height="680"><image href="data:image/png;base64,%s" '
                    'width="%d" height="%d" preserveAspectRatio="none" '
                    'transform="matrix(%g %g %g %g %g %g)"/></mask>'
                    % (i, b64[q["texture"]], W, Ht, a_, b_, c_, d_, e_, f_))
        body.append('<polygon points="%s" fill="%s" mask="url(#m%d)"%s/>' % (pts, col, i, op))
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
            'viewBox="0 0 640 480"><defs>%s</defs><rect x="-10" y="-10" width="660" '
            'height="500" fill="%s"/>%s</svg>'
            % (640 * scale, 480 * scale, "".join(defs), clear, "".join(body)))


def render(page, svg, scale):
    page.set_viewport_size({"width": 640 * scale, "height": 480 * scale})
    page.set_content("<body style='margin:0'>%s</body>" % svg)
    return Image.open(io.BytesIO(page.locator("svg").screenshot(type="png"))).convert("RGB")


def build_assets(page):
    textures, metas = {}, {}
    jobs = [("lbl_title", "MAIN MENU", "title")]
    for b in L.BUCKETS:
        jobs.append(("lbl_" + b["id"], b["label"], "hero" if b["rank"] == 0 else "tile"))
        jobs.append(("desc_" + b["id"], b["desc"], "desc"))
    for name, text, style in jobs:
        img = H.whiten(H.text_texture(page, text, style))
        textures[name], metas[name] = img, H.meta(name, img, tight=True)
    for b in L.BUCKETS:
        name = "ico_" + b["id"]
        img = H.whiten(H.icon_texture(page, b["id"]))
        textures[name], metas[name] = img, H.meta(name, img, tight=False)
    b64, sizes = {}, {}
    for name, img in textures.items():
        buf = io.BytesIO()
        H.i4(img).save(buf, "PNG")
        b64[name] = base64.b64encode(buf.getvalue()).decode()
        sizes[name] = img.size
    return L.build(metas), b64, sizes


# ------------------------------------------------------------ export
DIFFUSE = ("DIFFUSE_R", "DIFFUSE_G", "DIFFUSE_B")


REST_NG = dict(lift=0.0, scale=1.0, face=hexrgb(C["cobalt"]), icon=hexrgb(C["cobalt_hi"]),
               label=hexrgb(C["bone"]), desc_a=0.0)
REST_SEL = dict(lift=1.0, scale=1.0, face=hexrgb(C["gold"]), icon=hexrgb(C["gold_dk"]),
                label=hexrgb(C["ink"]), desc_a=1.0)


def label_switch_frame(face_keys, start_face, new, old):
    keys = [(0, start_face, face_keys[0][2], 0)] + list(face_keys[1:])
    return next(k for k in range(16)
                if contrast(new, evaluate(keys, k)) >= contrast(old, evaluate(keys, k)))


def hsd_tracks(event, tid, rest):
    """Canonical event -> track list. A None start key is exported with
    from_current=true: the player replaces its value with the channel's
    current value when the event starts. 'value' holds the rest value of the
    state the event leaves, for a player that starts from rest."""
    tracks = []
    for name, keys in event.items():
        ks = [(f, rest[name] if v is None else v, ip, s) for f, v, ip, s in keys]
        fc = [v is None for _, v, _, _ in keys]

        def row(target, kind, channel, idx=None, scale=1.0):
            out = []
            for (f, v, ip, s), cur in zip(ks, fc):
                k = dict(frame=f, value=round((v[idx] / 255 if idx is not None else v) * scale, 5),
                         interp=ip.upper(), slope=round(s * scale, 5))
                if cur:
                    k["from_current"] = True
                out.append(k)
            return dict(target=target, kind=kind, channel=channel, keys=out)

        if name == "lift":
            tracks += [row("lift_" + tid, "joint", "TRA_X", scale=LIFT[0]),
                       row("lift_" + tid, "joint", "TRA_Y", scale=LIFT[1])]
        elif name == "scale":
            tracks += [row("lift_" + tid, "joint", "SCA_X"), row("lift_" + tid, "joint", "SCA_Y")]
        elif name in ("face", "icon", "label"):
            tracks += [row("%s_%s" % (name, tid), "material", ch, idx=i)
                       for i, ch in enumerate(DIFFUSE)]
        elif name == "plate":
            tracks.append(row("plate_" + tid, "material", "ALPHA"))
        elif name == "recoil":
            tracks.append(dict(target="tile_" + tid, kind="joint", channel="TRA_X/TRA_Y",
                               note="scale keys by the unit vector from the selected "
                                    "tile's centre * %g px" % RECOIL_PX,
                               keys=[dict(frame=f, value=v, interp=ip.upper(), slope=s)
                                     for f, v, ip, s in ks]))
        elif name == "slide":
            tracks.append(row("tile_" + tid, "joint", "TRA_X"))
        elif name == "desc_a":
            tracks.append(row("desc_" + tid, "material", "ALPHA"))
        elif name == "desc_dx":
            tracks.append(row("desc_" + tid, "joint", "TRA_X"))
    return tracks


# ------------------------------------------------------------ main
def main():
    os.makedirs(os.path.join(OUT, "preview"), exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb"])
        page = browser.new_page(device_scale_factor=1)
        layout, b64, sizes = build_assets(page)

        hub = Hub(layout)
        # demo: enter, walk the cursor, go back to the hero, confirm, leave
        hub.select("versus", 0, initial=True)
        hub.screen_in(0)
        script = [(40, "solo"), (74, "collection"), (108, "options"), (142, "versus")]
        for f, tid in script:
            hub.select(tid, f)
        hub.confirm(176)
        hub.screen_out(190)
        END = 224

        # ---- checks, sampled every frame
        errs, worst = [], (99, None)
        sx0, sy0, sx1, sy1 = layout["safe_area"]
        for f in range(END):
            geo = hub.frame_geometry(f)
            moving = any(a <= f <= b for a, b in hub.transitions)
            for q, verts, rgb, a in geo:
                if moving or q["role"] == "decor":
                    continue
                for x, y in verts:
                    if not (sx0 - 1e-6 <= x <= sx1 + 1e-6 and sy0 - 1e-6 <= y <= sy1 + 1e-6):
                        errs.append("frame %d: %s leaves title-safe at (%.1f,%.1f)"
                                    % (f, q["id"], x, y))
                        break
            for tid in hub.ids:
                s = hub.tile_state(tid, f)
                c = contrast(s["label"], s["face"])
                if c < worst[0]:
                    worst = (c, (f, tid))
                if c < MIN_CONTRAST:
                    errs.append("frame %d: %s label contrast %.2f < %.1f"
                                % (f, tid, c, MIN_CONTRAST))

        # ---- preview: 30 fps gif of the whole sequence
        frames = [render(page, svg_frame(hub.frame_geometry(f), b64, sizes,
                                         layout["clear_colour"], 1), 1)
                  for f in range(0, END, 2)]
        frames[0].save(os.path.join(OUT, "preview", "motion_1x.gif"), save_all=True,
                       append_images=frames[1:], duration=33, loop=0)

        # ---- contact sheet: versus -> solo, frames 0..11, cropped to the cluster
        crop = (300, 40, 640, 240)
        cw, chh = (crop[2] - crop[0]) * 2, (crop[3] - crop[1]) * 2
        sheet = Image.new("RGB", (cw * 4, chh * 3), (0, 0, 0))
        dr = ImageDraw.Draw(sheet)
        for k in range(12):
            img = render(page, svg_frame(hub.frame_geometry(40 + k), b64, sizes,
                                         layout["clear_colour"], 2), 2)
            img = img.crop(tuple(v * 2 for v in crop))
            x, y = (k % 4) * cw, (k // 4) * chh
            sheet.paste(img, (x, y))
            dr.rectangle((x, y, x + 58, y + 22), fill=(0, 0, 0))
            dr.text((x + 6, y + 5), "f%02d" % k, fill=(255, 215, 102))
        sheet.save(os.path.join(OUT, "preview", "motion_select_sheet_2x.png"))
        browser.close()

    # ---- export
    ink, bone = hexrgb(C["ink"]), hexrgb(C["bone"])
    k_sel = label_switch_frame(ev_select()["face"], REST_NG["face"], ink, bone)
    k_des = label_switch_frame(ev_deselect()["face"], REST_SEL["face"], bone, ink)
    sel_ev = dict(ev_select(), label=[(0, bone, "con", 0), (k_sel, ink, "con", 0)])
    des_ev = dict(ev_deselect(), label=[(0, ink, "con", 0), (k_des, bone, "con", 0)])
    events = {
        "select":    ("the newly selected tile", [(0, "sfx_cursor_move")], sel_ev, REST_NG),
        "deselect":  ("the previously selected tile", [], des_ev, REST_SEL),
        "recoil":    ("every other tile", [], ev_recoil(), REST_NG),
        "desc_in":   ("selected tile's description", [], ev_desc_in(), REST_NG),
        "desc_out":  ("previous tile's description", [], ev_desc_out(), REST_SEL),
        "confirm":   ("the selected tile", [(3, "sfx_confirm")], ev_confirm(), REST_SEL),
        "slide_out": ("each tile, stagger 2f, chosen tile last; backplate at 0",
                      [(0, "sfx_screen_whoosh")], ev_slide_out(), REST_SEL),
        "slide_in":  ("each tile by rank, stagger 0/3/5/7f; backplate with hero",
                      [(0, "sfx_screen_whoosh")], ev_slide_in(), REST_SEL),
    }
    out_events = {}
    for name, (targets, sfx, ev, rest) in events.items():
        length = max(k[0] for keys in ev.values() for k in keys)
        out_events[name] = dict(applies_to=targets, length_frames=length + 1,
                                sfx=[dict(frame=f, cue=c) for f, c in sfx],
                                tracks=hsd_tracks(ev, "<id>", rest))

    # joints in parent-before-child order; 'draws' are quad ids from
    # hub_layout.json. Quad verts there are screen positions at rest, so a
    # joint's transform is applied to them as an offset from rest.
    joints = [
        dict(name="header", parent=None, pivot=None, channels=["TRA_Y"],
             draws=[q["id"] for q in layout["quads"] if q["id"].startswith("header")]),
        dict(name="footer", parent=None, pivot=None, channels=["TRA_Y"],
             draws=[q["id"] for q in layout["quads"] if q["id"].startswith("footer")]),
        dict(name="cluster", parent=None, pivot=None, channels=["TRA_X"], draws=["backplate"]),
    ]
    for t in layout["tiles"]:
        tid = t["id"]
        px, py = hub.pivot[tid]
        joints += [
            dict(name="tile_" + tid, parent=None, pivot=None,
                 channels=["TRA_X", "RECOIL"], draws=[]),
            dict(name="plate_" + tid, parent="tile_" + tid, pivot=None,
                 channels=["ALPHA"], draws=["%s_plate" % tid]),
            dict(name="lift_" + tid, parent="tile_" + tid, pivot=[round(px, 3), round(py, 3)],
                 channels=["TRA_X", "TRA_Y", "SCA_X", "SCA_Y"],
                 draws=["%s_face" % tid, "%s_icon" % tid, "%s_label" % tid]),
            dict(name="desc_" + tid, parent="footer", pivot=None,
                 channels=["TRA_X", "ALPHA"], draws=["%s_desc" % tid]),
        ]
    materials = {}
    for t in layout["tiles"]:
        for role in ("face", "icon", "label"):
            materials["%s_%s" % (role, t["id"])] = "%s_%s" % (t["id"], role)

    spec = dict(
        fps=FPS,
        units="1x framebuffer pixels; colours and alpha 0..1; alpha = opacity",
        joints=joints,
        materials=dict(
            note="material target -> the quad id whose colour it drives",
            map=materials),
        transform=[
            "A joint's local transform maps a rest-space point p to "
            "pivot + S * (p - pivot) + T, with pivot = [0,0] where null and "
            "S = 1 where it has no SCA channel.",
            "World transform = parent's world transform applied after the "
            "child's local one. Tile quads: lift_<id>, then tile_<id>.",
            "RECOIL is a scalar r; tile_<id> adds r * %g * unit(pivot(tile) - "
            "pivot(selected)) to its translation. Pivots are lift_<id>.pivot."
            % RECOIL_PX,
            "Draw order: tiles by rank, then the previously selected tile, "
            "then the selected tile last (it is lifted over its neighbours).",
        ],
        interpolation=[
            "Keys are (frame, value, interp, slope); interp applies to the "
            "segment starting at that key. Before the first key: its value. "
            "After the last: the last value.",
            "CON: hold the key's value until the next key's frame.",
            "LIN: linear between the two values.",
            "SPL: cubic Hermite, u = (t - f0)/(f1 - f0), d = f1 - f0: "
            "v = h00*v0 + h10*d*s0 + h01*v1 + h11*d*s1, slopes in value/frame.",
            "from_current: when the event starts, replace that key's value "
            "with the channel's current value. This is what stops an "
            "interrupted motion from popping.",
            "A channel plays the most recently started event that covers it; "
            "events on other channels of the same joint keep playing.",
        ],
        events=out_events,
        sequences=dict(
            cursor_move=[
                dict(event="deselect", on="previous", at=0),
                dict(event="desc_out", on="previous", at=0),
                dict(event="select", on="new", at=0),
                dict(event="desc_in", on="new", at=0),
                dict(event="recoil", on="others", at=0),
            ],
            confirm=[
                dict(event="confirm", on="selected", at=0),
                dict(sequence="screen_out", at=14),
            ],
            screen_out=dict(
                cluster=dict(event="slide_out", at=0),
                header=dict(channel="TRA_Y", keys=[[0, 0, "SPL", 0], [10, -60, "SPL", 0]]),
                footer=dict(channel="TRA_Y", keys=[[0, 0, "SPL", 0], [10, 60, "SPL", 0]]),
                tiles=dict(event="slide_out", order="unselected by rank, then selected",
                           stagger_frames=2),
            ),
            screen_in=dict(
                cluster=dict(event="slide_in", at=0),
                header=dict(channel="TRA_Y", keys=[[0, -60, "SPL", 0], [10, 0, "SPL", 0]]),
                footer=dict(channel="TRA_Y", keys=[[0, 60, "SPL", 0], [10, 0, "SPL", 0]]),
                tiles=dict(event="slide_in", order="by rank", offsets=[0, 3, 5, 7],
                           before_start="hold TRA_X at %d (off-screen)" % SLIDE_PX),
                initial_state="the selected tile is already at its 'sel' rest values",
            ),
        ),
        notes=[
            "Label and icon colours switch instantly (CON) instead of "
            "tweening: a tween passes through a grey that reads on neither "
            "face. The label switch frame is the first frame where the new "
            "colour contrasts more with the face than the old one.",
            "Sound cues are frame markers only; no audio assets exist yet.",
        ],
        checks=dict(min_label_contrast=round(worst[0], 2), at=worst[1],
                    required=MIN_CONTRAST),
    )
    with open(os.path.join(OUT, "hub_motion.json"), "w", encoding="utf-8") as fh:
        json.dump(spec, fh, indent=2)

    print("motion: %d events, demo %d frames (%.1fs @ %dfps)"
          % (len(out_events), END, END / FPS, FPS))
    for name, e in out_events.items():
        print("   %-10s %2d frames  %2d tracks  sfx %s" % (
            name, e["length_frames"], len(e["tracks"]),
            ",".join("%s@%d" % (s["cue"], s["frame"]) for s in e["sfx"]) or "-"))
    print("   label switch: select f%d, deselect f%d" % (k_sel, k_des))
    print("   worst label contrast %.2f (frame %d, %s)" % (worst[0], *worst[1]))
    if errs:
        print("\nCHECKS FAILED (%d):" % len(errs))
        for e in errs[:20]:
            print("  - " + e)
        return 1
    print("\nchecks ok: title-safe every settled/selection frame incl. overshoot, "
          "label contrast >= %.1f every frame" % MIN_CONTRAST)
    return 0


if __name__ == "__main__":
    sys.exit(main())
