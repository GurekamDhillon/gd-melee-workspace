"""The character select's hands and coins (the "puck"), as tintable masks.

    python pipeline/css_tokens.py   -> out_kit/{2x,1x}/css_*.png
                                       out_kit/css_tokens_layout.json   (png2gx --layout reads it)
                                       out_kit/preview/css_tokens_2x.png

Original art. The reference for *character* is a cartoon glove pointing at a roster
(the silhouette idea every fighting-game select screen shares): a chunky gloved hand,
index finger out, thumb cocked, curled knuckles, a turned-back cuff. Nothing is traced or
sampled; every shape below is a rounded rectangle or a circle typed in by hand.

Every texture is a white mask (I4) the engine tints per port, so P1..P6, CPU and teams
cost no extra textures. A hand is drawn as stacked layers:

    shadow (ink, soft, offset)   ink (outline)   fill (glove: bone mixed with the port)
    shade (ink, low alpha)       hi (white, low alpha)   cuff (port colour)
    detail (ink creases)         badge (port colour disc; the number comes from the font)

Two poses: `point` (index finger out; the hotspot is the fingertip) and `grab` (index and
thumb pinched; the hotspot is the pinch, where a held coin sits).

A coin is a poker-chip token: ink edge, a port-coloured rim with six bone inlays, a
port-coloured face with an engraved ring, a top-left highlight and a bottom-right shade;
"P1" etc. is drawn over it from the font. Carried and placed are the same textures at a
different scale and shadow (the engine's draw; see `states` in the layout).
"""
import io
import json
import math
import os
import sys

from PIL import Image
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kit                                                 # noqa: E402
from build import downscale_half, save_png               # noqa: E402

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "out_kit")
U = 64          # authoring units per texture side
PX2 = 128       # texels per side @2x (64 px at 1x)

# ---------------------------------------------------------------- the glove ----
# Authored upright (finger up) in a 64 grid, then posed by POSE_T.

def _capsule(x0, y0, x1, y1, w):
    """a rounded bar from (x0,y0) to (x1,y1), w wide: a rotated rect"""
    ln = math.hypot(x1 - x0, y1 - y0)
    a = math.degrees(math.atan2(y1 - y0, x1 - x0))
    return ('<rect x="%g" y="%g" width="%g" height="%g" rx="%g" transform="rotate(%g %g %g)"/>'
            % (x0 - w / 2, y0 - w / 2, ln + w, w, w / 2, a, x0, y0))


PALM = '<rect x="16.5" y="24" width="34" height="27" rx="11"/>'
KNUCKLES = ('<circle cx="36" cy="26.5" r="7"/><circle cx="44" cy="29" r="6.4"/>'
            '<circle cx="48.5" cy="36" r="4.8"/>')
CUFF = '<rect x="14.5" y="46.5" width="37" height="12.5" rx="5"/>'

POSES = {
    # index finger straight out, thumb cocked against it
    "point": dict(
        parts=['<rect x="18.5" y="2.5" width="14" height="34" rx="7"/>',
               PALM, KNUCKLES, _capsule(21.5, 41.5, 10, 31, 12)],
        creases=['<path d="M39.6 24.5 v6.5"/>', '<path d="M45.8 30 v4.5"/>',
                 '<path d="M21.5 30.5 h8"/>', '<path d="M15.5 34.5 l4 4"/>'],
        hot=(25.5, 3.3),
        badge=(36.5, 38.5)),
    # index hooked down onto the thumb: a pinch (a held coin sits at the hotspot)
    "grab": dict(
        parts=['<rect x="15.5" y="13" width="14.5" height="21" rx="7.25"/>',
               PALM, KNUCKLES, _capsule(21.5, 41.5, 12, 24, 12)],
        creases=['<path d="M39.6 24.5 v6.5"/>', '<path d="M45.8 30 v4.5"/>',
                 '<path d="M19 22.5 h8"/>', '<path d="M16.5 32 l3.5 3.5"/>'],
        hot=(15.0, 21.0),
        badge=(36.5, 38.5)),
}
# the pose: lean the hand so the finger points up-left, shrink it to leave room for the shadow
POSE_SCALE, POSE_ROT, POSE_PIVOT, POSE_AT = 0.86, -32.0, (32.0, 36.0), (33.0, 34.0)
POSE_T = ("translate(%g %g) scale(%g) rotate(%g) translate(%g %g)"
          % (POSE_AT[0], POSE_AT[1], POSE_SCALE, POSE_ROT, -POSE_PIVOT[0], -POSE_PIVOT[1]))


def posed(x, y):
    """a point in the upright grid -> the texture's 64 grid, the same maths as POSE_T"""
    x, y = x - POSE_PIVOT[0], y - POSE_PIVOT[1]
    a = math.radians(POSE_ROT)
    x, y = x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)
    return POSE_AT[0] + x * POSE_SCALE, POSE_AT[1] + y * POSE_SCALE


def hand_layers(pose):
    d = POSES[pose]
    sil = "".join(d["parts"]) + CUFF
    g = '<g transform="%s">%%s</g>' % POSE_T
    defs = ('<defs><g id="sil">%s</g>'
            '<filter id="soft" x="-20%%" y="-20%%" width="140%%" height="140%%">'
            '<feGaussianBlur stdDeviation="1.9"/></filter>'
            '<filter id="feather" x="-10%%" y="-10%%" width="120%%" height="120%%">'
            '<feGaussianBlur stdDeviation="0.45"/></filter>'
            '<mask id="shade" maskUnits="userSpaceOnUse" x="0" y="0" width="64" height="64">'
            '<use href="#sil" fill="#fff"/><use href="#sil" fill="#000" transform="translate(-3.2 -3.2)"/></mask>'
            '<mask id="hi" maskUnits="userSpaceOnUse" x="0" y="0" width="64" height="64">'
            '<use href="#sil" fill="#fff"/><use href="#sil" fill="#000" transform="translate(1.7 1.9)"/></mask>'
            '</defs>') % (g % sil)
    bx, by = posed(*d["badge"])
    return {
        "shadow": defs + '<g filter="url(#soft)"><use href="#sil" fill="#fff"/></g>',
        "ink": defs + '<use href="#sil" fill="#fff" stroke="#fff" stroke-width="4.2" stroke-linejoin="round"/>',
        "fill": defs + '<use href="#sil" fill="#fff"/>',
        "shade": defs + '<g mask="url(#shade)"><rect width="64" height="64" fill="#fff"/></g>',
        "hi": defs + '<g filter="url(#feather)"><g mask="url(#hi)"><rect width="64" height="64" fill="#fff"/></g></g>',
        "cuff": defs + (g % ('<g fill="#fff">%s</g>' % CUFF)),
        "detail": defs + (g % ('<g stroke="#fff" stroke-width="1.7" stroke-linecap="round" fill="none">%s'
                               '<path d="M18 50.2 H48"/></g>' % "".join(d["creases"]))),
        "badge": defs + '<circle cx="%.2f" cy="%.2f" r="6.6" fill="#fff"/>' % (bx, by),
    }


# ---------------------------------------------------------------- the coin ----
def coin_layers():
    c, r_out, r_face = 32, 28.0, 21.0
    inlays = []
    for i in range(6):                     # six bone inlays on the rim, a poker chip's stripes
        a0 = math.radians(i * 60 - 12 - 90)
        a1 = math.radians(i * 60 + 12 - 90)
        ro, ri = r_out - 1.2, r_face + 1.4
        pts = [(c + ro * math.cos(a0), c + ro * math.sin(a0)), (c + ro * math.cos(a1), c + ro * math.sin(a1)),
               (c + ri * math.cos(a1), c + ri * math.sin(a1)), (c + ri * math.cos(a0), c + ri * math.sin(a0))]
        inlays.append('<path d="M%.2f %.2f A%g %g 0 0 1 %.2f %.2f L%.2f %.2f A%g %g 0 0 0 %.2f %.2f Z"/>'
                      % (pts[0][0], pts[0][1], ro, ro, pts[1][0], pts[1][1], pts[2][0], pts[2][1], ri, ri,
                         pts[3][0], pts[3][1]))
    defs = ('<defs><filter id="soft" x="-20%%" y="-20%%" width="140%%" height="140%%"><feGaussianBlur stdDeviation="2.2"/></filter>'
            '<filter id="feather"><feGaussianBlur stdDeviation="0.5"/></filter>'
            '<mask id="hi" maskUnits="userSpaceOnUse" x="0" y="0" width="64" height="64">'
            '<circle cx="32" cy="32" r="%g" fill="#fff"/><circle cx="35.2" cy="35.8" r="%g" fill="#000"/></mask>'
            '<mask id="shade" maskUnits="userSpaceOnUse" x="0" y="0" width="64" height="64">'
            '<circle cx="32" cy="32" r="%g" fill="#fff"/><circle cx="29.4" cy="28.8" r="%g" fill="#000"/></mask>'
            '</defs>') % (r_out, r_out, r_out, r_out)
    return {
        "shadow": defs + '<circle cx="32" cy="32" r="27" fill="#fff" filter="url(#soft)"/>',
        "ink": '<circle cx="32" cy="32" r="30.6" fill="#fff"/>',
        "rim": '<circle cx="32" cy="32" r="%g" fill="#fff"/>' % r_out,
        "inlay": '<g fill="#fff">%s</g>' % "".join(inlays),
        "face": '<circle cx="32" cy="32" r="%g" fill="#fff"/>' % r_face,
        "ring": ('<circle cx="32" cy="32" r="%g" fill="none" stroke="#fff" stroke-width="1.6"/>'
                 '<circle cx="32" cy="32" r="%g" fill="none" stroke="#fff" stroke-width="1.1"/>') % (r_face + 0.2, r_face - 3.4),
        "hi": defs + ('<g filter="url(#feather)"><g mask="url(#hi)"><rect width="64" height="64" fill="#fff"/></g>'
                      '<ellipse cx="22.5" cy="19.5" rx="5.2" ry="2.4" transform="rotate(-42 22.5 19.5)" fill="#fff"/></g>'),
        "shade": defs + '<g mask="url(#shade)"><rect width="64" height="64" fill="#fff"/></g>',
    }


# How the engine stacks them: (layer, colour, alpha). "port" is the port's colour,
# "port_dark" the port's colour x 0.62, "glove" bone mixed 22% toward the port.
HAND_STACK = [("shadow", "ink", 0.45), ("ink", "ink", 1.0), ("fill", "glove", 1.0), ("cuff", "port", 1.0),
              ("shade", "ink", 0.28), ("hi", "white", 0.55), ("detail", "ink", 0.85),
              ("badge", "port", 1.0)]
COIN_STACK = [("shadow", "ink", 0.5), ("ink", "ink", 1.0), ("rim", "port_dark", 1.0), ("inlay", "bone", 1.0),
              ("face", "port", 1.0), ("ring", "ink", 0.35), ("shade", "ink", 0.25), ("hi", "white", 0.6)]


def page(w, h, body):
    return ('<!doctype html><html><head><style>html,body{margin:0;background:transparent}</style></head>'
            '<body><svg id="s" xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">%s</svg>'
            '</body></html>' % (w, h, U, U, body))


def shot(pg, body):
    pg.set_viewport_size({"width": PX2, "height": PX2})
    pg.set_content(page(PX2, PX2, body))
    png = pg.locator("#s").screenshot(omit_background=True, type="png")
    img = Image.open(io.BytesIO(png)).convert("RGBA")
    out = Image.new("RGBA", img.size, (255, 255, 255, 0))
    out.putalpha(img.getchannel("A"))
    return out


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def tint_of(name, port):
    pc = hexrgb(port)
    bone = hexrgb(kit.PALETTE["bone"])
    return {"ink": hexrgb(kit.PALETTE["ink"]), "white": (255, 255, 255), "bone": bone, "port": pc,
            "port_dark": tuple(int(v * 0.62) for v in pc),
            "glove": tuple(int(b * 0.78 + p * 0.22) for b, p in zip(bone, pc))}[name]


def compose(imgs, prefix, stack, port, size, offset=(0, 0), shadow_off=(0, 0)):
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for layer, col, a in stack:
        m = imgs[prefix + layer].resize((size, size), Image.LANCZOS)
        al = m.getchannel("A").point(lambda v, a=a: int(v * a))
        sol = Image.new("RGBA", (size, size), tint_of(col, port) + (0,))
        sol.putalpha(al)
        o = shadow_off if layer == "shadow" else (0, 0)
        tmp = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        tmp.alpha_composite(sol, o)
        out.alpha_composite(tmp)
    return out


def main():
    for sub in ("2x", "1x", "preview"):
        os.makedirs(os.path.join(OUT, sub), exist_ok=True)
    jobs = {}
    for pose in POSES:
        for k, body in hand_layers(pose).items():
            jobs["css_hand_%s_%s" % (pose, k)] = body
    for k, body in coin_layers().items():
        jobs["css_coin_%s" % k] = body
    imgs, errs = {}, []
    with sync_playwright() as p:
        br = p.chromium.launch(args=["--force-color-profile=srgb"])
        pg = br.new_page(device_scale_factor=1)
        for name, body in jobs.items():
            imgs[name] = shot(pg, body)
        br.close()
    rows = []
    for name, img in imgs.items():
        if img.getchannel("A").getbbox() is None:
            errs.append("%s is empty" % name)
        save_png(img, os.path.join(OUT, "2x", name + ".png"))
        save_png(downscale_half(img), os.path.join(OUT, "1x", name + ".png"))
        rows.append(dict(name=name, file_2x="out_kit/2x/%s.png" % name, file_1x="out_kit/1x/%s.png" % name,
                         size_2x=[PX2, PX2], size_1x=[PX2 // 2, PX2 // 2], format="I4",
                         why="white mask, tinted per port by the engine"))
    # nothing may touch the texture's border (a clipped shadow shows as a hard line)
    for name, img in imgs.items():
        a = img.getchannel("A")
        edge = max(max(a.crop((0, 0, PX2, 1)).get_flattened_data()), max(a.crop((0, PX2 - 1, PX2, PX2)).get_flattened_data()),
                   max(a.crop((0, 0, 1, PX2)).get_flattened_data()), max(a.crop((PX2 - 1, 0, PX2, PX2)).get_flattened_data()))
        if edge > 24:
            errs.append("%s touches its border (alpha %d)" % (name, edge))
    hot = {pose: [round(v, 2) for v in posed(*POSES[pose]["hot"])] for pose in POSES}
    badge = {pose: [round(v, 2) for v in posed(*POSES[pose]["badge"])] for pose in POSES}
    layout = dict(
        screen="css_tokens",
        note="Hands and coins of the character select. Units: the 64 grid of each texture (= 1x pixels at "
             "the authored size); the engine scales the whole stack.",
        hand=dict(grid=U, hotspot=hot, badge_centre=badge, badge_r=6.6, stack=HAND_STACK,
                  states=dict(rest="point, shadow (+2,+3)", hover="point, lowered: shadow (+1,+1.5), 0.94 scale",
                              carry="grab with the coin under the pinch", drag="grab on the slider knob")),
        coin=dict(grid=U, centre=[32, 32], r_face=21.0, r_out=28.0, stack=COIN_STACK,
                  states=dict(placed="scale 1, shadow (+1,+1.5)", carried="scale 1.15, shadow (+4,+6)",
                              drop="160 ms from carried to placed with a 6% undershoot")),
        textures=sorted(rows, key=lambda r: r["name"]))
    with open(os.path.join(OUT, "css_tokens_layout.json"), "w", encoding="utf-8") as fh:
        json.dump(layout, fh, indent=2)
    # preview: P1..P4 + CPU hands (both poses) and coins, on the CSS ground, at 2x and 1x
    ground = hexrgb("#131820")
    sheet = Image.new("RGB", (5 * 150 + 20, 460), ground)
    ports = [kit.PORTS[k] for k in ("p1", "p2", "p3", "p4", "cpu")]
    for i, pc in enumerate(ports):
        x = 10 + i * 150
        sheet.paste(compose(imgs, "css_hand_point_", HAND_STACK, pc, 128, shadow_off=(4, 6)), (x, 10),
                    compose(imgs, "css_hand_point_", HAND_STACK, pc, 128, shadow_off=(4, 6)))
        cn = compose(imgs, "css_coin_", COIN_STACK, pc, 64, shadow_off=(3, 4))
        sheet.paste(cn, (x + 10, 170), cn)
        gr = compose(imgs, "css_hand_grab_", HAND_STACK, pc, 128, shadow_off=(4, 6))
        sheet.paste(gr, (x, 150), gr)
        small = compose(imgs, "css_hand_point_", HAND_STACK, pc, 40, shadow_off=(1, 2))
        sheet.paste(small, (x, 300), small)
        cs = compose(imgs, "css_coin_", COIN_STACK, pc, 22, shadow_off=(1, 1))
        sheet.paste(cs, (x + 50, 310), cs)
        cs = compose(imgs, "css_coin_", COIN_STACK, pc, 32, shadow_off=(1, 1))
        sheet.paste(cs, (x + 80, 305), cs)
    sheet.save(os.path.join(OUT, "preview", "css_tokens_2x.png"))
    print("css_tokens: %d masks (%d hand, %d coin), hotspots %s" % (len(imgs), sum(1 for n in imgs if "hand" in n),
                                                                     sum(1 for n in imgs if "coin" in n), hot))
    if errs:
        print("CHECKS FAILED:")
        for e in errs:
            print("  - " + e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
