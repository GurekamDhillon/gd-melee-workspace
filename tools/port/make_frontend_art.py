#!/usr/bin/env python3
"""Generate the frontend's HD artwork and convert it to .gxtex (pc/tools/png2gx.py).

    python tools/port/make_frontend_art.py        # writes _build/ui/*.png and *.gxtex

Everything is drawn procedurally so the art is reproducible and carries no third-party assets:

  fe_backdrop  512x512  the screen's background: a deep-navy vertical gradient, two soft light
                        blooms, a fine diagonal line pattern, a vignette, and a little noise so
                        the gradients do not band. Drawn full screen behind every frontend page.
  fe_btn_a     64x64    the GameCube A button (green) with its letter, for the footer hints.
  fe_btn_b     64x64    the B button (red).

All three convert as RGBA8 (lossless): the backdrop's gradients would band in RGB5A3's five bits,
and the buttons need their soft edges' alpha.
"""
import math
import os
import random
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "_build", "ui")
PNG2GX = os.path.join(ROOT, "melee", "pc", "tools", "png2gx.py")
FONT = r"C:\Windows\Fonts\arialbd.ttf"


def lerp(a, b, t):
    return a + (b - a) * t


def backdrop(w=512, h=512):
    # GX textures here are power-of-two: drawn at 512x512 and stretched to the 4:3 screen, so
    # vertical distances are pre-squashed by 3/4 to keep the blooms round on screen.
    img = Image.new("RGB", (w, h))
    px = img.load()
    top, bottom = (26, 34, 64), (5, 6, 12)
    blooms = [  # (cx, cy, radius, colour, strength)
        (0.78 * w, 0.18 * h, 0.55 * w, (70, 110, 230), 0.55),
        (0.12 * w, 0.92 * h, 0.45 * w, (120, 60, 170), 0.28),
    ]
    rnd = random.Random(1)
    for y in range(h):
        t = y / (h - 1)
        base = [lerp(top[i], bottom[i], t) for i in range(3)]
        for x in range(w):
            c = list(base)
            for cx, cy, r, col, s in blooms:
                d = math.hypot(x - cx, (y - cy) * 0.75) / r
                if d < 1.0:
                    k = s * (1.0 - d) ** 2
                    c = [c[i] + (col[i] - c[i]) * k for i in range(3)]
            if (x + y) % 12 == 0:  # the fine diagonal pattern
                c = [ci + 5 for ci in c]
            vx, vy = (x / w - 0.5) * 2, (y / h - 0.5) * 2  # vignette
            v = 1.0 - 0.35 * min(1.0, (vx * vx + vy * vy) * 0.5)
            n = rnd.uniform(-1.5, 1.5)  # dither against banding
            px[x, y] = tuple(max(0, min(255, int(ci * v + n))) for ci in c)
    return img.convert("RGBA")


def button(letter, fill, rim, size=64):
    s = size * 4  # supersample for smooth edges
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    shadow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse((s * 0.10, s * 0.14, s * 0.94, s * 0.98), fill=(0, 0, 0, 150))
    img = Image.alpha_composite(img, shadow.filter(ImageFilter.GaussianBlur(s * 0.03)))
    d = ImageDraw.Draw(img)
    d.ellipse((s * 0.06, s * 0.06, s * 0.90, s * 0.90), fill=rim)
    d.ellipse((s * 0.10, s * 0.10, s * 0.86, s * 0.86), fill=fill)
    hi = Image.new("RGBA", (s, s), (0, 0, 0, 0))  # a soft top highlight
    ImageDraw.Draw(hi).ellipse((s * 0.20, s * 0.14, s * 0.76, s * 0.46), fill=(255, 255, 255, 70))
    img = Image.alpha_composite(img, hi.filter(ImageFilter.GaussianBlur(s * 0.04)))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT, int(s * 0.50))
    box = d.textbbox((0, 0), letter, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    d.text((s * 0.48 - tw / 2 - box[0], s * 0.48 - th / 2 - box[1]), letter, font=font,
           fill=(255, 255, 255, 255))
    return img.resize((size, size), Image.LANCZOS)


def convert(name):
    png = os.path.join(OUT, name + ".png")
    gx = os.path.join(OUT, name + ".gxtex")
    subprocess.check_call([sys.executable, PNG2GX, png, gx, "--format", "rgba8"])


def main():
    os.makedirs(OUT, exist_ok=True)
    backdrop().save(os.path.join(OUT, "fe_backdrop.png"))
    button("A", (40, 190, 110, 255), (18, 110, 60, 255)).save(os.path.join(OUT, "fe_btn_a.png"))
    button("B", (220, 60, 60, 255), (130, 25, 25, 255)).save(os.path.join(OUT, "fe_btn_b.png"))
    for name in ("fe_backdrop", "fe_btn_a", "fe_btn_b"):
        convert(name)
    print("frontend art ->", OUT)


if __name__ == "__main__":
    main()
