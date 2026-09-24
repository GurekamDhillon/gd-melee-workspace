"""GX texture codecs for MK's menu art: CI8 / CI4 (RGB5A3 TLUT), I4 encode + decode (decode = verification).

The RGB5A3 word rules are pc/tools/png2gx.py's (imported, not copied), so texels round the same way the port's
own art pipeline rounds them. Quantisation to a 256/16-entry palette happens on RGB5A3-quantised colours (the
palette can only hold those), with fully transparent texels folded to one entry."""
import os, struct, sys
from PIL import Image
sys.path.insert(0, os.path.join(r"C:/Users/Gurek/Desktop/GD's Melee", "melee", "pc", "tools"))
from png2gx import rgb5a3_encode, rgb5a3_decode

GX_TF_I4, GX_TF_I8, GX_TF_IA4, GX_TF_IA8, GX_TF_RGB565, GX_TF_RGB5A3, GX_TF_RGBA8, GX_TF_C4, GX_TF_C8 = 0, 1, 2, 3, 4, 5, 6, 8, 9
GX_TL_RGB5A3 = 2
TILE = {GX_TF_I4: (8, 8), GX_TF_C4: (8, 8), GX_TF_C8: (8, 4), GX_TF_I8: (8, 4), GX_TF_IA4: (8, 4), GX_TF_RGB5A3: (4, 4)}
BPP = {GX_TF_I4: 4, GX_TF_C4: 4, GX_TF_C8: 8, GX_TF_I8: 8, GX_TF_IA4: 8, GX_TF_RGB5A3: 16}


def size_of(fmt, w, h):
    tw, th = TILE[fmt]
    return ((w + tw - 1) // tw * tw) * ((h + th - 1) // th * th) * BPP[fmt] // 8


def _tiles(w, h, tw, th):
    for ty in range(0, h, th):
        for tx in range(0, w, tw):
            yield tx, ty


def _q(c):
    """RGB5A3 round trip of one RGBA texel; alpha 0 -> one canonical transparent colour."""
    if c[3] < 16:
        return (0, 0, 0, 0)
    return rgb5a3_decode(rgb5a3_encode(*c))


W = (3.0, 4.0, 2.0, 6.0)          # perceptual-ish channel weights (R G B A) for palette distances


def _kmeans(px, pal, ncolors, iters=12):
    """Refine an octree palette with weighted k-means over the (non-transparent) texels; entry 0 stays transparent.
    Every entry is snapped to an exact RGB5A3 value."""
    import numpy as np
    X = np.array([c for c in px if c[3] > 0], dtype=np.float64)
    if len(X) == 0: return pal
    U, cnt = np.unique(X, axis=0, return_counts=True)
    w = np.sqrt(np.array(W))
    C = np.array([c for c in pal if c[3] > 0] or [U[0]], dtype=np.float64)
    k = ncolors - 1
    while len(C) < k and len(C) < len(U):                    # seed missing centres with the worst-fit colours
        d = (((U[:, None, :] - C[None]) * w) ** 2).sum(-1).min(1) * cnt
        C = np.vstack([C, U[d.argmax()]])
    for _ in range(iters):
        d = (((U[:, None, :] - C[None]) * w) ** 2).sum(-1); lab = d.argmin(1)
        for j in range(len(C)):
            m = lab == j
            if m.any(): C[j] = (U[m] * cnt[m, None]).sum(0) / cnt[m].sum()
    snapped = sorted(set(_q(tuple(int(round(v)) for v in c)) for c in C) - {(0, 0, 0, 0)})
    return [(0, 0, 0, 0)] + snapped[:k]


def quantize(img, ncolors):
    """RGBA image -> (indices row-major, palette [RGBA]) with at most ncolors entries, each an exact RGB5A3 value."""
    img = img.convert("RGBA")
    w, h = img.size
    px = [_q(c) for c in img.getdata()]
    uniq = sorted(set(px))
    if len(uniq) <= ncolors:
        pal = uniq
    else:
        tmp = Image.new("RGBA", (w, h)); tmp.putdata(px)
        qi = tmp.quantize(colors=ncolors - 1, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
        raw = qi.getpalette(rawmode="RGBA")[:4 * (ncolors - 1)]
        pal = [(0, 0, 0, 0)] + sorted(set(_q(tuple(raw[i:i + 4])) for i in range(0, len(raw), 4)) - {(0, 0, 0, 0)})
        pal = _kmeans(px, pal[:ncolors], ncolors)
    best = {}
    def nearest(c):
        if c not in best:
            if c[3] == 0:
                best[c] = pal.index((0, 0, 0, 0)) if (0, 0, 0, 0) in pal else min(range(len(pal)), key=lambda i: pal[i][3])
            else:
                best[c] = min(range(len(pal)), key=lambda i: sum((pal[i][k] - c[k]) ** 2 * W[k] for k in range(4)))
        return best[c]
    return [nearest(c) for c in px], pal


def quantize_joint(imgs, ncolors, iters=15, seed=1):
    """Several same-size images that are recolours of one picture (costumes) -> ONE index map + one palette per image
    (the m-ex / ACE CSP layout: a fighter's costumes share a pixel buffer and differ only by TLUT). Each texel is the
    tuple of its colours in every image; weighted k-means over the tuples; index 0 = transparent in every image."""
    import numpy as np
    w, h = imgs[0].size
    P = np.stack([np.array([_q(c) for c in im.convert("RGBA").getdata()], dtype=np.float64) for im in imgs], 1)  # N x K x 4
    N, K = P.shape[0], P.shape[1]
    clear = (P[:, :, 3] == 0).all(1)
    X = P[~clear].reshape(-1, K * 4)
    U, inv, cnt = np.unique(X, axis=0, return_inverse=True, return_counts=True)
    wv = np.tile(np.sqrt(np.array(W)), K)
    k = min(ncolors - 1, len(U))
    rng = np.random.default_rng(seed)
    C = U[rng.choice(len(U), size=k, replace=False, p=cnt / cnt.sum())].copy()
    def assign(C):
        lab = np.empty(len(U), dtype=np.int64)
        for s in range(0, len(U), 4096):
            d = (((U[s:s+4096, None, :] - C[None]) * wv) ** 2).sum(-1); lab[s:s+4096] = d.argmin(1)
        return lab
    for _ in range(iters):
        lab = assign(C)
        for j in range(k):
            m = lab == j
            if m.any(): C[j] = (U[m] * cnt[m, None]).sum(0) / cnt[m].sum()
    pals = []
    for i in range(K):                                       # snap every centre to RGB5A3, per image
        pals.append([(0, 0, 0, 0)] + [_q(tuple(int(round(v)) for v in C[j, 4*i:4*i+4])) for j in range(k)])
    Cq = np.array([[v for i in range(K) for v in pals[i][j + 1]] for j in range(k)], dtype=np.float64)
    lab = assign(Cq)                                         # final assignment against the snapped palettes
    idx = np.zeros(N, dtype=np.int64); idx[~clear] = lab[inv.reshape(-1)] + 1
    for i in range(K): pals[i] += [(0, 0, 0, 0)] * (ncolors - len(pals[i]))
    return idx.tolist(), pals


def encode_ci_joint(imgs, fmt):
    """-> (one image bytes, [tlut bytes per image], n entries) - see quantize_joint"""
    n = 256 if fmt == GX_TF_C8 else 16
    w, h = imgs[0].size
    idx, pals = quantize_joint(imgs, n)
    return _tile_ci(idx, w, h, fmt), [b"".join(struct.pack(">H", rgb5a3_encode(*p[i])) for i in range(n)) for p in pals], n


def _tile_ci(idx, w, h, fmt):
    tw, th = TILE[fmt]
    out = bytearray()
    for tx, ty in _tiles(w, h, tw, th):
        for y in range(ty, ty + th):
            row = [idx[y * w + x] if (x < w and y < h) else 0 for x in range(tx, tx + tw)]
            if fmt == GX_TF_C8:
                out += bytes(row)
            else:
                for i in range(0, tw, 2): out.append((row[i] << 4) | row[i + 1])
    return bytes(out)


def encode_ci(img, fmt):
    """-> (image bytes, tlut bytes, n tlut entries) for GX_TF_C8 (256) or GX_TF_C4 (16), TLUT GX_TL_RGB5A3."""
    n = 256 if fmt == GX_TF_C8 else 16
    w, h = img.size
    idx, pal = quantize(img, n)
    tw, th = TILE[fmt]
    out = bytearray()
    for tx, ty in _tiles(w, h, tw, th):
        for y in range(ty, ty + th):
            row = [idx[y * w + x] if (x < w and y < h) else 0 for x in range(tx, tx + tw)]
            if fmt == GX_TF_C8:
                out += bytes(row)
            else:
                for i in range(0, tw, 2): out.append((row[i] << 4) | row[i + 1])
    tlut = b"".join(struct.pack(">H", rgb5a3_encode(*pal[i]) if i < len(pal) else 0) for i in range(n))
    return bytes(out), tlut, n


def encode_i4(img):
    """Greyscale (luma of RGB, times alpha) -> GX_TF_I4."""
    img = img.convert("RGBA"); w, h = img.size; px = img.load()
    out = bytearray()
    def lv(x, y):
        if x >= w or y >= h: return 0
        r, g, b, a = px[x, y]
        return (((r * 299 + g * 587 + b * 114) // 1000) * a // 255 * 15 + 127) // 255
    for tx, ty in _tiles(w, h, 8, 8):
        for y in range(ty, ty + 8):
            for x in range(tx, tx + 8, 2):
                out.append((lv(x, y) << 4) | lv(x + 1, y))
    return bytes(out)


def decode(buf, fmt, w, h, tlut=None):
    """GX texture bytes -> PIL RGBA (tlut: RGB5A3 words bytes for C4/C8)."""
    im = Image.new("RGBA", (w, h)); px = im.load()
    pal = [rgb5a3_decode(struct.unpack(">H", tlut[i:i + 2])[0]) for i in range(0, len(tlut), 2)] if tlut else None
    tw, th = TILE[fmt]; p = 0
    for tx, ty in _tiles(w, h, tw, th):
        for y in range(ty, ty + th):
            for x in range(tx, tx + tw, 1 if BPP[fmt] >= 8 else 2):
                if BPP[fmt] == 16:
                    v = [rgb5a3_decode(struct.unpack(">H", buf[p:p + 2])[0])]; p += 2
                elif BPP[fmt] == 8:
                    b = buf[p]; p += 1
                    v = [pal[b] if fmt == GX_TF_C8 else ((b & 15) * 17,) * 3 + ((b >> 4) * 17,)]
                else:
                    b = buf[p]; p += 1
                    v = [(b >> 4), (b & 15)]
                    v = [pal[i] for i in v] if fmt == GX_TF_C4 else [(i * 17,) * 3 + (255,) for i in v]
                for k, c in enumerate(v):
                    if x + k < w and y < h: px[x + k, y] = c
    return im
