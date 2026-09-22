#!/usr/bin/env python3
"""Dump vanilla Melee's menu/UI archives and index what they contain.

    python tools/mex_port/dump_menu_assets.py                 # everything, default locations
    python tools/mex_port/dump_menu_assets.py --only MnMaAll.usd,IfAll.usd --no-raw
    python tools/mex_port/dump_menu_assets.py --iso "C:/iso/Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso"

WHAT IT WRITES (all outside the repo; nothing this tool writes is ever committed):

  <raw-out>/                  the 75 archives, byte for byte, flat, .dat and .usd side by side
  <tex-out>/<archive>/*.png   every texture, decoded (GX formats, TLUTs applied, straight alpha) -
                              ONLY for the .usd files and the .dat files that have no .usd
  <index-out>/<archive>.json  + .txt   the STRUCTURE of each archive - metadata only, no pixels:
                              per public entry its kind and what it contains (joints, meshes,
                              materials, animations, TexAnim-animated textures, cameras, lights,
                              2D/3D guess), per texture its size/format/TLUT/mips/sha1/paths/tags
  <index-out>/_dat_vs_usd.json/.txt   byte-level comparison of the .dat/.usd pairs by structural
                              path: which textures differ (language-specific baked text) or exist
                              in only one version
  <index-out>/../MANIFEST.md  the itemized list, the layout and the headline numbers

Defaults: raw/tex to ~/Desktop/meleedump, index to <repo>/menu/meleedump/index (the art pipeline
folder beside this repo's tools/, found relative to this file).

HOW TEXTURES ARE FOUND. Two independent ways, cross-checked:
  1. A structural walk from every public entry with typed walkers (JObjDesc trees -> DObj -> MObj ->
     TObj -> ImageDesc; AnimJoint/AObj/FObj; MatAnimJoint -> MatAnim -> TexAnim image/TLUT tables;
     SObjDesc; SceneDesc/DynamicModelDesc/StaticModelDesc tables). Every pointer field is validated
     against the archive's relocation table, so a wrong interpretation fails instead of guessing.
  2. A scan of the relocation table for ImageDesc-shaped structs (pointer to 32-byte-aligned data,
     u16 w/h, a valid GX format, finite LODs). Anything the scan finds that the walk did not is
     reported as an orphan and still decoded.

Layouts are the decomp's (melee/src/sysdolphin/baselib: jobj/dobj/mobj/tobj/aobj/fobj, sc/types.h,
mn/mncharsel.c) - big-endian, pointers are archive-data-relative offsets.

PROVENANCE. Extracted locally from a disc image the user supplies. Nothing extracted is committed
or redistributed; `.gitignore` already refuses disc data.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import os
import re
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mex_hsd  # noqa: E402

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

DEFAULT_ISO = r"C:/iso/Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso"
HOME = os.path.expanduser("~")
DEF_RAW = os.path.join(HOME, "Desktop", "meleedump", "raw")
DEF_TEX = os.path.join(HOME, "Desktop", "meleedump", "textures")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEF_INDEX = os.path.join(REPO, "menu", "meleedump", "index")

# ---------------------------------------------------------------------------- the 75 files
BASES_PAIRED = ("MnMaAll MnExtAll MnSlChr MnSlMap GmTitle GmTtAll IfAll IfVsCam IfComSn IfHrNoCn "
                "IfHrReco IfPrize GmPause GmRst GmRegClr GmRegEnd GmTou1p GmTou2p GmTou3p GmTou4p "
                "GmTrain TyMnDisp TyMnFigp TyMnView TyMnInfo TyDatai LbMcGame LbMcSnap").split()
SOLO = ("MnNamedef IfCoGet GmGover GmGoCoin GmGoAnim GmRgEBG2 GmRgEBG3 GmRgStnd GmStRoll GmEvent "
        "GmIntEz GmKumite TmBox TyMnBg TyDataf LbAd LbBf LbRb LbRf").split()
# archives that are pure data tables: indexed, never decoded
NO_DECODE = {"LbAd", "LbBf", "LbRb", "LbRf", "GmEvent", "GmIntEz", "GmKumite", "MnNamedef",
             "TyDatai", "TyDataf", "TmBox"}

WHAT = {  # one line per archive for the manifest
    "MnMaAll": "main menu screens and their backdrop scenes",
    "MnExtAll": "extra/secondary menu scenes (shares the main-menu backdrop scenes)",
    "MnNamedef": "name-entry default/refused/auto name tables (text data)",
    "MnSlChr": "character select screen",
    "MnSlMap": "stage select screen",
    "GmTitle": "title screen scene", "GmTtAll": "title screen scenes, logo, background/camera animations",
    "IfAll": "in-game HUD: damage numbers/marks, name tags, stock icons, counters",
    "IfVsCam": "VS off-screen bubble / camera overlays", "IfCoGet": "coin-get overlay",
    "IfComSn": "'Coming Soon' screen", "IfHrNoCn": "Home-Run Contest counter",
    "IfHrReco": "Home-Run Contest records", "IfPrize": "prize overlay",
    "GmPause": "pause overlay", "GmRst": "results screen",
    "GmGover": "game over", "GmGoCoin": "game over coins", "GmGoAnim": "game over animation",
    "GmRegClr": "single-player clear screen", "GmRegEnd": "ending cuts + ending motion files",
    "GmRgEBG2": "ending background 2", "GmRgEBG3": "ending background 3",
    "GmRgStnd": "ending stand", "GmStRoll": "staff roll",
    "GmEvent": "event table (data)", "GmIntEz": "intro easy table (data)",
    "GmKumite": "Kumite system tables (data)",
    "GmTou1p": "tournament screen (1 player)", "GmTou2p": "tournament screen (2 players)",
    "GmTou3p": "tournament screen (3 players)", "GmTou4p": "tournament screen (4 players)",
    "TmBox": "tournament bracket box tables (data)", "GmTrain": "training mode screen",
    "TyMnBg": "trophy gallery backgrounds", "TyMnDisp": "trophy display screen",
    "TyMnFigp": "trophy 'figure pon' (lottery) screen", "TyMnView": "trophy viewer screen",
    "TyMnInfo": "trophy camera-info buttons", "TyDatai": "trophy lookup tables (data)",
    "TyDataf": "trophy model file tables (data)",
    "LbMcGame": "memory card banner/icons (game data)", "LbMcSnap": "memory card banner/icon (snapshot)",
    "LbAd": "audio load table (data)", "LbBf": "background flash colour anims (data)",
    "LbRb": "rumble data", "LbRf": "reference data",
}

# ---------------------------------------------------------------------------- GX formats
FMT_NAME = {0: "I4", 1: "I8", 2: "IA4", 3: "IA8", 4: "RGB565", 5: "RGB5A3", 6: "RGBA8",
            8: "CI4", 9: "CI8", 10: "CI14X2", 14: "CMPR"}
FMT_TILE = {0: (8, 8), 1: (8, 4), 2: (8, 4), 3: (4, 4), 4: (4, 4), 5: (4, 4), 6: (4, 4),
            8: (8, 8), 9: (8, 4), 10: (4, 4), 14: (8, 8)}
FMT_BPP = {0: 4, 1: 8, 2: 8, 3: 16, 4: 16, 5: 16, 6: 32, 8: 4, 9: 8, 10: 16, 14: 4}
TLUT_NAME = {0: "IA8", 1: "RGB565", 2: "RGB5A3"}


def image_bytes(w, h, fmt):
    tw, th = FMT_TILE[fmt]
    return ((w + tw - 1) // tw * tw) * ((h + th - 1) // th * th) * FMT_BPP[fmt] // 8


def mip_chain_bytes(w, h, fmt, mips):
    total = 0
    for _ in range(max(1, mips)):
        total += image_bytes(w, h, fmt)
        w, h = max(1, w // 2), max(1, h // 2)
    return total


def _rgb5a3(v):
    v = v.astype(np.uint32)
    op = (v & 0x8000) != 0
    r = np.where(op, ((v >> 10) & 31) * 255 // 31, ((v >> 8) & 15) * 17)
    g = np.where(op, ((v >> 5) & 31) * 255 // 31, ((v >> 4) & 15) * 17)
    b = np.where(op, (v & 31) * 255 // 31, (v & 15) * 17)
    a = np.where(op, 255, ((v >> 12) & 7) * 255 // 7)
    return np.stack([r, g, b, a], -1).astype(np.uint8)


def _rgb565(v):
    v = v.astype(np.uint32)
    return np.stack([((v >> 11) & 31) * 255 // 31, ((v >> 5) & 63) * 255 // 63,
                     (v & 31) * 255 // 31, np.full(v.shape, 255)], -1).astype(np.uint8)


def _ia8(v):
    v = v.astype(np.uint32)
    i = v & 255
    return np.stack([i, i, i, v >> 8], -1).astype(np.uint8)


def decode_palette(raw, fmt, n):
    v = np.frombuffer(raw[:2 * n], dtype=">u2")
    return {0: _ia8, 1: _rgb565, 2: _rgb5a3}[fmt](v)


def decode_texture(data, w, h, fmt, palette=None):
    """One GX image (level 0) -> RGBA uint8 (h, w, 4). `palette` is (n,4) RGBA for CI formats."""
    tw, th = FMT_TILE[fmt]
    W, H = (w + tw - 1) // tw * tw, (h + th - 1) // th * th
    nbx, nby = W // tw, H // th
    tile_bytes = tw * th * FMT_BPP[fmt] // 8
    need = nbx * nby * tile_bytes
    if len(data) < need:
        raise ValueError("image data short: need %d have %d" % (need, len(data)))
    blk = np.frombuffer(data[:need], dtype=np.uint8).reshape(nby, nbx, tile_bytes)

    def nib(b):  # (..,n) bytes -> (..,2n) nibbles, high first
        return np.stack([b >> 4, b & 15], -1).reshape(b.shape[:-1] + (b.shape[-1] * 2,))

    if fmt == 0:
        v = nib(blk).astype(np.uint32) * 17
        px = np.stack([v, v, v, v], -1)
    elif fmt == 1:
        v = blk.astype(np.uint32)
        px = np.stack([v, v, v, v], -1)
    elif fmt == 2:
        v = blk.astype(np.uint32)
        i, a = (v & 15) * 17, (v >> 4) * 17
        px = np.stack([i, i, i, a], -1)
    elif fmt in (3, 4, 5):
        v = blk.view(">u2").reshape(nby, nbx, tw * th)
        px = {3: _ia8, 4: _rgb565, 5: _rgb5a3}[fmt](v)
    elif fmt == 6:
        b = blk.reshape(nby, nbx, 2, 16, 2)  # [AR half | GB half], 16 px, 2 bytes
        a, r, g, bl = b[:, :, 0, :, 0], b[:, :, 0, :, 1], b[:, :, 1, :, 0], b[:, :, 1, :, 1]
        px = np.stack([r, g, bl, a], -1)
    elif fmt in (8, 9, 10):
        if palette is None:
            raise ValueError("colour-indexed texture without a palette")
        if fmt == 8:
            idx = nib(blk)
        elif fmt == 9:
            idx = blk
        else:
            idx = (blk.view(">u2").astype(np.uint32) & 0x3FFF).reshape(nby, nbx, tw * th)
        idx = np.minimum(idx, len(palette) - 1)
        px = palette[idx]
    elif fmt == 14:
        b = blk.reshape(nby, nbx, 4, 8)  # 4 sub-blocks of 4x4, each 8 bytes
        c = b[..., :4].copy().view(">u2").reshape(nby, nbx, 4, 2)
        c0, c1 = c[..., 0].astype(np.int32), c[..., 1].astype(np.int32)
        col0, col1 = _rgb565(c0).astype(np.int32), _rgb565(c1).astype(np.int32)
        pal = np.zeros((nby, nbx, 4, 4, 4), dtype=np.int32)
        pal[..., 0, :], pal[..., 1, :] = col0, col1
        four = (c0 > c1)[..., None]
        pal[..., 2, :] = np.where(four, (2 * col0 + col1) // 3, (col0 + col1) // 2)
        pal[..., 3, :] = np.where(four, (col0 + 2 * col1) // 3, 0)
        pal[..., 3, 3] = np.where(c0 > c1, 255, 0)
        bits = b[..., 4:]  # 4 bytes: one per row, 2 bits per pixel, MSB first
        sh = np.array([6, 4, 2, 0])
        idx = (bits[..., :, None] >> sh) & 3  # (nby,nbx,4,4rows,4cols)
        gather = np.take_along_axis(pal[..., None, :, :].repeat(4, axis=4 - 1 + 0) if False else
                                    pal, idx.reshape(nby, nbx, 4, 16)[..., None].repeat(4, -1), axis=3)
        px = gather.reshape(nby, nbx, 4, 4, 4, 4)  # sub-block, row, col, rgba
        # assemble 8x8 tile from 2x2 sub-blocks
        px = px.reshape(nby, nbx, 2, 2, 4, 4, 4).transpose(0, 1, 2, 4, 3, 5, 6).reshape(
            nby, nbx, 8, 8, 4)
        img = px.transpose(0, 2, 1, 3, 4).reshape(H, W, 4)[:h, :w]
        return img.astype(np.uint8)
    else:
        raise ValueError("unsupported GX format %d" % fmt)
    px = px.reshape(nby, nbx, th, tw, 4)
    img = px.transpose(0, 2, 1, 3, 4).reshape(H, W, 4)[:h, :w]
    return img.astype(np.uint8)


# ---------------------------------------------------------------------------- parsing
class Bad(Exception):
    """A pointer/field failed validation: this interpretation of the bytes is wrong."""


JOBJ_PTCL, JOBJ_INSTANCE, JOBJ_SPLINE = 1 << 5, 1 << 12, 1 << 14
MAX_DEPTH = 4000


def _finite(x, lim=1e7):
    return isinstance(x, float) and math.isfinite(x) and abs(x) < lim


class Walker:
    """Typed walkers over one archive's data section. All offsets are data-relative."""

    def __init__(self, ar):
        self.ar = ar
        self.d = ar.data
        self.n = len(ar.data)
        self.rel = ar.reloc_set
        self.textures = {}     # key -> texture dict (unique images)
        self.tex_order = []
        self.scan_hits = set()

    # -- primitives
    def u32(self, o):
        if o < 0 or o + 4 > self.n:
            raise Bad("read past end 0x%X" % o)
        return struct.unpack_from(">I", self.d, o)[0]

    def u16(self, o):
        if o < 0 or o + 2 > self.n:
            raise Bad("read past end 0x%X" % o)
        return struct.unpack_from(">H", self.d, o)[0]

    def f32(self, o):
        if o < 0 or o + 4 > self.n:
            raise Bad("read past end 0x%X" % o)
        return struct.unpack_from(">f", self.d, o)[0]

    def ptr(self, o, allow_null=True):
        """The pointer stored at o: None when null; Bad unless the word is a relocated pointer."""
        v = self.u32(o)
        if v == 0:
            if allow_null:
                return None
            raise Bad("null pointer at 0x%X" % o)
        if o not in self.rel or not (0 < v < self.n):
            raise Bad("not a relocated pointer at 0x%X (=0x%X)" % (o, v))
        return v

    def ptr_array(self, o, maxn=4096):
        out = []
        for i in range(maxn):
            p = self.u32(o + 4 * i)
            if p == 0:
                break
            if (o + 4 * i) not in self.rel or not (0 < p < self.n):
                raise Bad("bad array element at 0x%X" % (o + 4 * i))
            out.append(p)
        else:
            raise Bad("unterminated pointer array at 0x%X" % o)
        return out

    def cstr_ok(self, p):
        if p is None:
            return True
        e = self.d.find(b"\0", p, p + 96)
        return e > p and all(32 <= c < 127 for c in self.d[p:e])

    # -- textures
    def image_desc(self, o):
        p = self.ptr(o, allow_null=False) if False else None
        img = self.u32(o)
        if img == 0 or o not in self.rel or not (0 < img < self.n) or img % 32:
            raise Bad("ImageDesc image pointer at 0x%X" % o)
        w, h, fmt = self.u16(o + 4), self.u16(o + 6), self.u32(o + 8)
        mip = self.u32(o + 12)
        if not (1 <= w <= 2048 and 1 <= h <= 2048) or fmt not in FMT_NAME or mip > 16:
            raise Bad("ImageDesc fields at 0x%X (%dx%d fmt %d mip %d)" % (o, w, h, fmt, mip))
        if not (_finite(self.f32(o + 16)) and _finite(self.f32(o + 20))):
            raise Bad("ImageDesc LOD at 0x%X" % o)
        if img + image_bytes(w, h, fmt) > self.n:
            raise Bad("ImageDesc data runs off the section at 0x%X" % o)
        return img, w, h, fmt, mip

    def tlut_desc(self, o):
        lut = self.u32(o)
        fmt, n = self.u32(o + 4), self.u16(o + 12)
        if lut == 0 or o not in self.rel or not (0 < lut < self.n) or fmt not in TLUT_NAME:
            raise Bad("TlutDesc at 0x%X" % o)
        if not (1 <= n <= 16384) or lut + 2 * n > self.n:
            raise Bad("TlutDesc size at 0x%X" % o)
        return lut, fmt, n

    def add_texture(self, ctx, path, imgdesc, tlutdesc=None, animated=None):
        img, w, h, fmt, mip = self.image_desc(imgdesc)
        tl = self.tlut_desc(tlutdesc) if tlutdesc else None
        key = (img, w, h, fmt, tl)
        raw = bytes(self.d[img:img + image_bytes(w, h, fmt)])
        h1 = hashlib.sha1(raw)
        if tl:
            h1.update(bytes(self.d[tl[0]:tl[0] + 2 * tl[2]]))
        t = self.textures.get(key)
        if t is None:
            t = dict(img=img, w=w, h=h, fmt=fmt, mips=mip, tlut=tl, bytes=len(raw),
                     sha1=h1.hexdigest(), paths=[], entries=[], animated=False, anim_frames=0)
            self.textures[key] = t
            self.tex_order.append(key)
        t["paths"].append(path)
        if ctx["entry"] not in t["entries"]:
            t["entries"].append(ctx["entry"])
        if animated:
            t["animated"] = True
            t["anim_frames"] = max(t["anim_frames"], animated)
        ctx["textures"].append((key, path))
        self.scan_hits.add(imgdesc)
        return key

    # -- node walkers (each counts into ctx["c"], records textures with a deterministic path)
    def tobj_chain(self, o, ctx, path):
        i = 0
        while o:
            if o in ctx["seen_tobj"]:
                break
            ctx["seen_tobj"].add(o)
            nxt = self.ptr(o + 4)
            imgd, tlutd = self.ptr(o + 0x4C), self.ptr(o + 0x50)
            ctx["c"]["tobjs"] += 1
            if imgd:
                self.add_texture(ctx, "%s.t%d" % (path, i), imgd, tlutd)
            o = nxt
            i += 1

    def mobj(self, o, ctx, path):
        if o in ctx["seen_mobj"]:
            return
        ctx["seen_mobj"].add(o)
        if not self.cstr_ok(self.ptr(o)):
            raise Bad("MObj class name")
        ctx["c"]["materials"] += 1
        self.tobj_chain(self.ptr(o + 8), ctx, path)

    def pobj_chain(self, o, ctx):
        while o:
            if o in ctx["seen_pobj"]:
                break
            ctx["seen_pobj"].add(o)
            ctx["c"]["pobjs"] += 1
            nxt = self.ptr(o + 4)
            ctx["c"]["display_list_bytes"] += 32 * self.u16(o + 0xE)
            o = nxt

    def dobj_chain(self, o, ctx, path):
        k = 0
        while o:
            if o in ctx["seen_dobj"]:
                break
            ctx["seen_dobj"].add(o)
            ctx["c"]["meshes"] += 1
            nxt = self.ptr(o + 4)
            mo = self.ptr(o + 8)
            if mo:
                self.mobj(mo, ctx, "%s.d%d" % (path, k))
            self.pobj_chain(self.ptr(o + 0xC), ctx)
            o = nxt
            k += 1

    def jobj_tree(self, o, ctx, path="j", depth=0):
        """DFS over child/next; the DFS index is the path so .dat/.usd copies pair up."""
        stack = [o]
        while stack:
            cur = stack.pop()
            while cur:
                if cur in ctx["seen_jobj"]:
                    break
                if len(ctx["seen_jobj"]) > 200000:
                    raise Bad("jobj tree too large")
                ctx["seen_jobj"].add(cur)
                idx = ctx["jcount"] = ctx.get("jcount", -1) + 1
                ctx["jindex"][cur] = idx
                if not self.cstr_ok(self.ptr(cur)):
                    raise Bad("JObj class name")
                flags = self.u32(cur + 4)
                child, nxt, u = self.ptr(cur + 8), self.ptr(cur + 0xC), self.u32(cur + 0x10)
                for k in range(9):
                    if not _finite(self.f32(cur + 0x14 + 4 * k)):
                        raise Bad("JObj transform")
                self.ptr(cur + 0x38)
                self.ptr(cur + 0x3C)
                ctx["c"]["joints"] += 1
                if flags & (JOBJ_SPLINE | JOBJ_PTCL):
                    ctx["c"]["spline_or_particle_joints"] += 1
                elif flags & JOBJ_INSTANCE:
                    ctx["c"]["instance_joints"] += 1
                elif u:
                    self.ptr(cur + 0x10)
                    self.dobj_chain(u, ctx, "%s%d" % (path, idx))
                if child:
                    stack.append(nxt) if nxt else None
                    cur = child
                    continue
                cur = nxt

    def fobj_chain(self, o, ctx):
        while o:
            if o in ctx["seen_fobj"]:
                break
            ctx["seen_fobj"].add(o)
            ln = self.u32(o + 4)
            if ln > 0x100000:
                raise Bad("FObj length")
            ctx["c"]["fobj_tracks"] += 1
            ctx["c"]["fobj_types"][self.d[o + 12]] += 1
            self.ptr(o + 0x10)
            o = self.ptr(o)

    def aobj(self, o, ctx):
        if o is None or o in ctx["seen_aobj"]:
            return
        ctx["seen_aobj"].add(o)
        end = self.f32(o + 4)
        if not _finite(end, 1e6):
            raise Bad("AObj end frame")
        ctx["c"]["aobjs"] += 1
        ctx["c"]["anim_frames_max"] = max(ctx["c"]["anim_frames_max"], end)
        self.fobj_chain(self.ptr(o + 8), ctx)

    def animjoint_tree(self, o, ctx):
        stack = [o]
        while stack:
            cur = stack.pop()
            while cur:
                if cur in ctx["seen_anim"]:
                    break
                ctx["seen_anim"].add(cur)
                child, nxt, ao = self.ptr(cur), self.ptr(cur + 4), self.ptr(cur + 8)
                self.ptr(cur + 0xC)
                ctx["c"]["animjoints"] += 1
                self.aobj(ao, ctx)
                if child:
                    if nxt:
                        stack.append(nxt)
                    cur = child
                    continue
                cur = nxt

    def texanim_chain(self, o, ctx, path):
        k = 0
        while o:
            if o in ctx["seen_texanim"]:
                break
            ctx["seen_texanim"].add(o)
            nxt = self.ptr(o)
            ao = self.ptr(o + 8)
            imgtbl, tlttbl = self.ptr(o + 0xC), self.ptr(o + 0x10)
            nimg, ntlt = self.u16(o + 0x14), self.u16(o + 0x16)
            ctx["c"]["texanims"] += 1
            ctx["c"]["texanim_frames"] += nimg
            self.aobj(ao, ctx)
            if imgtbl and nimg:
                if nimg > 4096:
                    raise Bad("TexAnim image table")
                imgs = [self.ptr(imgtbl + 4 * i, allow_null=False) for i in range(nimg)]
                tlts = ([self.ptr(tlttbl + 4 * i, allow_null=False) for i in range(ntlt)]
                        if tlttbl and ntlt else [])
                for i, im in enumerate(imgs):
                    tl = tlts[i] if len(tlts) == nimg else (tlts[0] if len(tlts) else None)
                    # colour-indexed frames need a palette; keep going if a frame has none
                    fmt = self.u32(im + 8)
                    self.add_texture(ctx, "%s.ta%d.f%d" % (path, k, i), im,
                                     tl if fmt in (8, 9, 10) else None, animated=nimg)
            o = nxt
            k += 1

    def matanim_tree(self, o, ctx):
        stack = [o]
        n = 0
        while stack:
            cur = stack.pop()
            while cur:
                if cur in ctx["seen_matj"]:
                    break
                ctx["seen_matj"].add(cur)
                idx = n
                n += 1
                child, nxt, ma = self.ptr(cur), self.ptr(cur + 4), self.ptr(cur + 8)
                ctx["c"]["matanim_joints"] += 1
                m = 0
                while ma:
                    if ma in ctx["seen_matanim"]:
                        break
                    ctx["seen_matanim"].add(ma)
                    ctx["c"]["matanims"] += 1
                    nm = self.ptr(ma)
                    self.aobj(self.ptr(ma + 4), ctx)
                    ta = self.ptr(ma + 8)
                    self.ptr(ma + 0xC)
                    if ta:
                        self.texanim_chain(ta, ctx, "mj%d.ma%d" % (idx, m))
                    ma = nm
                    m += 1
                if child:
                    if nxt:
                        stack.append(nxt)
                    cur = child
                    continue
                cur = nxt

    def shapeanim_tree(self, o, ctx):
        stack = [o]
        while stack:
            cur = stack.pop()
            while cur:
                if cur in ctx["seen_shape"]:
                    break
                ctx["seen_shape"].add(cur)
                child, nxt, sa = self.ptr(cur), self.ptr(cur + 4), self.ptr(cur + 8)
                ctx["c"]["shapeanim_joints"] += 1
                while sa:
                    if sa in ctx["seen_shapeanim"]:
                        break
                    ctx["seen_shapeanim"].add(sa)
                    ctx["c"]["shapeanims"] += 1
                    self.aobj(self.ptr(sa + 4), ctx)
                    sa = self.ptr(sa)
                if child:
                    if nxt:
                        stack.append(nxt)
                    cur = child
                    continue
                cur = nxt

    def sobjdesc(self, o, ctx, path="so"):
        im = self.u32(o)
        if im == 0:
            raise Bad("SObjDesc null image")
        tl = self.ptr(o + 4)
        self.image_desc(im)
        img_fmt = self.u32(im + 8)
        ctx["c"]["sprites"] += 1
        self.add_texture(ctx, path, im, tl if img_fmt in (8, 9, 10) else None)
        # SObjDesc2 (a second image) - only when the next word is a valid relocated ImageDesc
        try:
            im2 = self.ptr(o + 8)
            if im2:
                self.image_desc(im2)
                ctx["c"]["sprites"] += 1
                self.add_texture(ctx, path + ".b", im2, None)
        except Bad:
            pass

    # -- composite tables
    def static_model(self, o, ctx, path):
        """StaticModelDesc: joint, animjoint, matanim_joint, shapeanim_joint (all optional)."""
        j, a, m, s = (self.ptr(o + 4 * i) for i in range(4))
        if not (j or a or m or s):
            raise Bad("empty StaticModelDesc")
        if j:
            self.jobj_tree(j, ctx, path + ".j")
        if a:
            self.animjoint_tree(a, ctx)
        if m:
            self.matanim_tree(m, ctx)
        if s:
            self.shapeanim_tree(s, ctx)
        ctx["c"]["models"] += 1

    def dynamic_model(self, o, ctx, path):
        """DynamicModelDesc: joint + NULL-terminated arrays of anim/matanim/shapeanim joints."""
        j = self.ptr(o)
        if j:
            self.jobj_tree(j, ctx, path + ".j")
        for k, walk in ((1, self.animjoint_tree), (2, self.matanim_tree), (3, self.shapeanim_tree)):
            arr = self.ptr(o + 4 * k)
            if arr:
                for p in self.ptr_array(arr):
                    walk(p, ctx)
                    ctx["c"]["anim_sets"] += 1
        ctx["c"]["models"] += 1

    def scene_desc(self, o, ctx):
        models, cams, lights, fogs = (self.ptr(o + 4 * i) for i in range(4))
        if not models:
            raise Bad("SceneDesc without models")
        for i, dm in enumerate(self.ptr_array(models)):
            self.dynamic_model(dm, ctx, "m%d" % i)
        if cams:
            self.camera(cams, ctx)
        if lights:
            ctx["c"]["lights"] += len(self.ptr_array(lights))
        if fogs:
            ctx["c"]["fogs"] += 1

    def camera(self, o, ctx):
        """CObjDesc-ish (best effort: only the projection type is read; may be a list)."""
        ctx["c"]["cameras"] += 1
        try:
            proj = self.u16(o + 6)
            if proj in (1, 2, 3):
                ctx["projection"] = {1: "perspective", 2: "frustum", 3: "orthographic"}[proj]
        except Bad:
            pass


NEW_COUNTERS = ("joints meshes pobjs display_list_bytes materials tobjs animjoints aobjs "
                "fobj_tracks matanim_joints matanims texanims texanim_frames shapeanim_joints "
                "shapeanims sprites models anim_sets lights fogs cameras spline_or_particle_joints "
                "instance_joints").split()


def new_ctx(entry):
    c = collections.defaultdict(int)
    c["fobj_types"] = collections.Counter()
    c["anim_frames_max"] = 0
    return dict(entry=entry, c=c, textures=[], jindex={}, projection=None,
                **{k: set() for k in ("seen_tobj seen_mobj seen_pobj seen_dobj seen_jobj seen_fobj "
                                      "seen_aobj seen_anim seen_texanim seen_matj seen_matanim "
                                      "seen_shape seen_shapeanim").split()})


# ---------------------------------------------------------------------------- entry parsing
def entry_kind(name):
    n = name
    if n.endswith("_matanim_joint"):
        return "matanim_joint"
    if n.endswith("_shapeanim_joint"):
        return "shapeanim_joint"
    if n.endswith("_animjoint"):
        return "animjoint"
    if re.search(r"_listpos\d+_joint$", n) or n.endswith("_joint"):
        return "joint"
    if n.endswith("_scene_data"):
        return "scene_data"
    if n.endswith("_sobjdesc"):
        return "sobjdesc"
    if n.endswith(("_scene_models", "_scene_modelset", "_model_set", "_scemdls", "_rarwmdls")):
        return "model_set"
    if n.endswith("_int1_camera"):
        return "camera"
    if n.endswith("_int1_camanim"):
        return "camanim"
    if n.endswith("_scene_lights"):
        return "lights"
    if n.endswith("_fog"):
        return "fog"
    if re.search(r"(sce|Scene)$", n) or n == "lupe":
        return "scene_data"
    if n in ("MnSelectChrDataTable", "MnSelectStageDataTable"):
        return "select_table"
    if re.match(r"MemCard(Banner|Icon)_|MemSnap(Banner|Icon)_", n):
        return "card_image"
    if n.startswith("ftDemoEndingMotionFile"):
        return "motion_file"
    return "table"


def parse_entry(w, name, off, extent):
    """Parse one public entry with the typed walker its name implies; returns (ctx, method)."""
    kind = entry_kind(name)
    ctx = new_ctx(name)
    method = kind
    try:
        if kind == "joint":
            w.jobj_tree(off, ctx)
        elif kind == "animjoint":
            w.animjoint_tree(off, ctx)
        elif kind == "matanim_joint":
            w.matanim_tree(off, ctx)
        elif kind == "shapeanim_joint":
            w.shapeanim_tree(off, ctx)
        elif kind == "sobjdesc":
            w.sobjdesc(off, ctx)
        elif kind == "scene_data":
            w.scene_desc(off, ctx)
        elif kind == "model_set":
            method = _try_model_set(w, off, ctx)
        elif kind == "camera":
            w.camera(off, ctx)
        elif kind == "camanim":
            ctx["c"]["cameras"] += 1
            try:
                w.aobj(w.ptr(off + 4), ctx)
            except Bad:
                pass
        elif kind == "lights":
            ctx["c"]["lights"] += 1
        elif kind == "fog":
            ctx["c"]["fogs"] += 1
        elif kind == "select_table":
            method = _select_table(w, off, extent, ctx)
        elif kind == "card_image":
            method = "raw card image (decoded by size)"
        else:
            method = "table (not walked)"
    except Bad as e:
        return ctx, "FAILED: %s" % e, kind, str(e)
    return ctx, method, kind, None


def _try_model_set(w, off, ctx):
    """A *_scene_models / *_model_set symbol: try the shapes it can have, in order."""
    errs = []
    for label, fn in (
            ("StaticModelDesc", lambda c: w.static_model(off, c, "s")),
            ("DynamicModelDesc", lambda c: w.dynamic_model(off, c, "d")),
            ("array of DynamicModelDesc", lambda c: [w.dynamic_model(p, c, "m%d" % i)
                                                      for i, p in enumerate(w.ptr_array(off))]),
            ("array of StaticModelDesc pointers", lambda c: [w.static_model(p, c, "s%d" % i)
                                                              for i, p in enumerate(w.ptr_array(off))])):
        trial = new_ctx(ctx["entry"])
        snap = len(w.tex_order), {k: (dict(v, paths=list(v["paths"]), entries=list(v["entries"]))) for k, v in w.textures.items()}
        try:
            fn(trial)
        except Bad as e:
            errs.append("%s: %s" % (label, e))
            # roll back textures added by the failed attempt
            w.textures = {k: v for k, v in snap[1].items()}
            w.tex_order = w.tex_order[:snap[0]]
            continue
        ctx.update({k: trial[k] for k in trial if k != "entry"})
        return label
    raise Bad("; ".join(errs))


def _select_table(w, off, extent, ctx):
    """MnSelectChrDataTable / MnSelectStageDataTable: cam, light0, light1, fog, then StaticModelDescs."""
    for i in range(4):
        w.ptr(off + 4 * i)
    ctx["c"]["cameras"] += 1 if w.ptr(off) else 0
    ctx["c"]["lights"] += sum(1 for i in (1, 2) if w.ptr(off + 4 * i))
    ctx["c"]["fogs"] += 1 if w.ptr(off + 0xC) else 0
    n = 0
    p = off + 0x10
    while p + 16 <= min(extent + off, w.n):
        try:
            trial = new_ctx(ctx["entry"])
            w.static_model(p, trial, "sm%d" % n)
        except Bad:
            break
        # commit: re-run into the real ctx (textures are already recorded, walkers are idempotent)
        w.static_model(p, ctx, "sm%d" % n)
        n += 1
        p += 16
    return "select table: %d static models" % n


# ---------------------------------------------------------------------------- ImageDesc scan
def scan_imagedescs(w):
    """Independent discovery: every relocated word that points at a valid-looking ImageDesc."""
    found = {}
    for r in w.ar.reloc_offsets:
        if r + 24 > w.n:
            continue
        try:
            img, wd, ht, fmt, mip = w.image_desc(r)
        except Bad:
            continue
        found[r] = (img, wd, ht, fmt, mip)
    return found


# ---------------------------------------------------------------------------- memory card
def card_extent_texture(w, name, off, extent):
    """Banners/icons are raw pixel blobs, not ImageDescs. Decode by size when it is unambiguous."""
    sz = extent
    if name.startswith("MemCardBanner") or name.startswith("MemSnapBanner"):
        if sz >= 96 * 32 * 2:
            return dict(w=96, h=32, fmt=5, data=bytes(w.d[off:off + 96 * 32 * 2]), palette=None)
        if sz >= 96 * 32 + 512:
            pal = decode_palette(bytes(w.d[off + 96 * 32:off + 96 * 32 + 512]), 2, 256)
            return dict(w=96, h=32, fmt=9, data=bytes(w.d[off:off + 96 * 32]), palette=pal)
    if "Icon" in name and not name.endswith("IconData"):
        if sz >= 32 * 32 * 2:
            return dict(w=32, h=32, fmt=5, data=bytes(w.d[off:off + 32 * 32 * 2]), palette=None)
        if sz >= 32 * 32 + 512:
            pal = decode_palette(bytes(w.d[off + 32 * 32:off + 32 * 32 + 512]), 2, 256)
            return dict(w=32, h=32, fmt=9, data=bytes(w.d[off:off + 32 * 32]), palette=pal)
    return None


# ---------------------------------------------------------------------------- tagging
CHAR_NAME_RE = re.compile(r"(Stc|Pnm|Emblem|CharName|Chr|Portrait|Face|Icon)", re.I)
TEXT_NAME_RE = re.compile(r"(Msg|Text|Title|Name|Logo|Caption|Menu.*(Str|Txt))", re.I)


def tag_texture(t, in_differ, entry_names):
    tags = []
    en = " ".join(entry_names)
    if in_differ:
        tags.append(dict(tag="baked_text", reason="content differs between the .dat and .usd copy "
                                                  "(heuristic: language-specific pixels)"))
    elif TEXT_NAME_RE.search(en):
        tags.append(dict(tag="baked_text", reason="entry name suggests text: %s (heuristic)" % en[:80]))
    if CHAR_NAME_RE.search(en) or (t["animated"] and 20 <= t["anim_frames"] <= 400):
        why = ("entry name matches a character-art pattern: %s" % en[:80]
               if CHAR_NAME_RE.search(en) else
               "texture-animated with %d frames (per-character/costume arrays are 26-400)" % t["anim_frames"])
        tags.append(dict(tag="character_art", reason=why + " (heuristic)"))
    if t["fmt"] in (0, 2, 8) and t["w"] <= 32 and t["h"] <= 32 and t["animated"] is False and \
            len(entry_names) and re.search(r"(Font|Num|Digit|Ascii|Kana|Char)", en, re.I):
        tags.append(dict(tag="font_like", reason="small I4/IA4/CI4 glyph-sized image in a font/number entry"))
    return tags


# ---------------------------------------------------------------------------- archive driver
def run_archive(iso_gcm, fname, tex_dir, decode, differ_paths=None):
    raw = iso_gcm.read(fname)
    ar = mex_hsd.Archive(raw)
    w = Walker(ar)
    base = fname.rsplit(".", 1)[0]
    pubs = sorted(ar.publics, key=lambda p: p[1])
    extents = {}
    for i, (nm, off) in enumerate(pubs):
        nxt = pubs[i + 1][1] if i + 1 < len(pubs) else ar.data_size
        extents[nm] = max(0, nxt - off)
    entries = []
    for nm, off in ar.publics:
        ctx, method, kind, err = parse_entry(w, nm, off, extents.get(nm, 0))
        entries.append(dict(name=nm, offset=off, extent=extents.get(nm, 0), kind=kind,
                            method=method, error=err, ctx=ctx))
    # independent scan
    scan = scan_imagedescs(w)
    walked = {t for t in w.scan_hits}
    orphans = {r: v for r, v in scan.items() if r not in walked}
    scan_only = sorted(orphans)
    walk_only = sorted(o for o in walked if o not in scan)
    # memory-card raw images
    card = []
    for e in entries:
        if e["kind"] == "card_image":
            c = card_extent_texture(w, e["name"], e["offset"], e["extent"])
            if c:
                card.append((e["name"], c))
    return dict(fname=fname, base=base, raw=raw, ar=ar, w=w, entries=entries, scan=scan,
                orphans=orphans, scan_only=scan_only, walk_only=walk_only, card=card)


def texture_record_list(A):
    """Assign ids in first-appearance order, return the list of texture dicts."""
    w = A["w"]
    out = []
    for i, key in enumerate(w.tex_order):
        t = w.textures[key]
        t["id"] = i
        out.append(t)
    return out


def write_pngs(A, tex_dir):
    w = A["w"]
    d = os.path.join(tex_dir, A["fname"])
    os.makedirs(d, exist_ok=True)
    undec = []
    files = {}
    for t in texture_record_list(A):
        ent = re.sub(r"[^A-Za-z0-9_.-]", "_", t["entries"][0])[:70]
        fn = "%03d_%s_%dx%d_%s.png" % (t["id"], ent, t["w"], t["h"], FMT_NAME[t["fmt"]])
        try:
            pal = None
            if t["fmt"] in (8, 9, 10):
                if not t["tlut"]:
                    raise ValueError("no TLUT reachable for a colour-indexed image")
                lut, tf, n = t["tlut"]
                pal = decode_palette(bytes(w.d[lut:lut + 2 * n]), tf, n)
            img = decode_texture(bytes(w.d[t["img"]:t["img"] + t["bytes"]]), t["w"], t["h"],
                                 t["fmt"], pal)
            Image.fromarray(img, "RGBA").save(os.path.join(d, fn), optimize=False)
            t["file"] = fn
            files[t["id"]] = fn
        except Exception as e:  # noqa: BLE001 - reported, not fatal
            t["file"] = None
            undec.append(dict(id=t["id"], reason=str(e), w=t["w"], h=t["h"], fmt=FMT_NAME[t["fmt"]]))
    # orphans: decoded too, named ORPHAN
    for r, (img, wd, ht, fmt, mip) in sorted(A["orphans"].items()):
        try:
            tl = None
            if fmt in (8, 9, 10):
                undec.append(dict(id=None, reason="orphan CI image (no TLUT context) at 0x%X" % r,
                                  w=wd, h=ht, fmt=FMT_NAME[fmt]))
                continue
            img_arr = decode_texture(bytes(w.d[img:img + image_bytes(wd, ht, fmt)]), wd, ht, fmt)
            Image.fromarray(img_arr, "RGBA").save(
                os.path.join(d, "ORPHAN_%06X_%dx%d_%s.png" % (r, wd, ht, FMT_NAME[fmt])))
        except Exception as e:  # noqa: BLE001
            undec.append(dict(id=None, reason="orphan 0x%X: %s" % (r, e), w=wd, h=ht,
                              fmt=FMT_NAME[fmt]))
    for name, c in A["card"]:
        try:
            img_arr = decode_texture(c["data"], c["w"], c["h"], c["fmt"], c["palette"])
            Image.fromarray(img_arr, "RGBA").save(os.path.join(d, "card_%s_%dx%d_%s.png" % (
                name, c["w"], c["h"], FMT_NAME[c["fmt"]])))
        except Exception as e:  # noqa: BLE001
            undec.append(dict(id=None, reason="card %s: %s" % (name, e), w=c["w"], h=c["h"],
                              fmt=FMT_NAME[c["fmt"]]))
    return undec


def entry_json(e, A):
    c = e["ctx"]["c"]
    st = {k: c[k] for k in NEW_COUNTERS}
    st["fobj_types"] = {str(k): v for k, v in sorted(c["fobj_types"].items())}
    st["anim_frames_max"] = round(c["anim_frames_max"], 2)
    proj = e["ctx"]["projection"]
    if e["kind"] in ("sobjdesc",):
        st["looks_2d"] = "sprite (SObjDesc)"
    elif proj == "orthographic":
        st["looks_2d"] = "orthographic camera"
    elif st["joints"] and st["meshes"] and not st["sprites"] and st["pobjs"]:
        st["looks_2d"] = "mesh scene (3D or flat quads - see projection)"
    elif st["sprites"]:
        st["looks_2d"] = "sprites"
    else:
        st["looks_2d"] = None
    if proj:
        st["camera_projection"] = proj
    tex_ids = []
    anim = []
    for key, path in e["ctx"]["textures"]:
        t = A["w"].textures[key]
        if t["id"] not in tex_ids:
            tex_ids.append(t["id"])
    by_anim = collections.defaultdict(list)
    for key, path in e["ctx"]["textures"]:
        t = A["w"].textures[key]
        if t["animated"]:
            by_anim[path.rsplit(".f", 1)[0]].append(t["id"])
    for p, ids in by_anim.items():
        anim.append(dict(texanim=p, frames=len(ids), texture_ids=ids))
    return dict(name=e["name"], offset=e["offset"], extent=e["extent"], kind=e["kind"],
                parse=e["method"], parse_error=e["error"], structure=st, texture_ids=tex_ids,
                animated_textures=anim)


def archive_json(A, counterpart, differ, decoded, undec):
    w = A["w"]
    texs = texture_record_list(A)
    ents = [entry_json(e, A) for e in A["entries"]]
    tex_out = []
    fmts = collections.Counter()
    pixels = 0
    for t in texs:
        tags = tag_texture(t, (A["fname"], t["sha1"]) in differ, t["entries"])
        fmts[FMT_NAME[t["fmt"]]] += 1
        pixels += t["w"] * t["h"]
        tex_out.append(dict(
            id=t["id"], file=t.get("file"), w=t["w"], h=t["h"], format=FMT_NAME[t["fmt"]],
            tlut=None if not t["tlut"] else dict(format=TLUT_NAME[t["tlut"][1]], entries=t["tlut"][2]),
            mips=t["mips"], image_bytes=t["bytes"], sha1=t["sha1"],
            animated=t["animated"], anim_frames=t["anim_frames"] or None,
            entries=t["entries"], paths=t["paths"][:12], n_paths=len(t["paths"]), tags=tags))
    tot = collections.Counter()
    for e in ents:
        for k in NEW_COUNTERS:
            tot[k] += e["structure"][k]
    return dict(
        archive=A["fname"], size=len(A["raw"]), sha1=hashlib.sha1(A["raw"]).hexdigest(),
        counterpart=counterpart, decoded_to_png=decoded,
        summary=dict(entries=len(ents), textures=len(tex_out),
                     total_texture_pixels=pixels, formats=dict(fmts),
                     structure_totals={k: tot[k] for k in NEW_COUNTERS},
                     orphan_images=len(A["orphans"]), card_images=len(A["card"]),
                     undecodable=len(undec)),
        entries=ents, textures=tex_out,
        cross_check=dict(scan_found=len(A["scan"]), walk_found=len(A["w"].scan_hits),
                         found_by_scan_only=[hex(o) for o in A["scan_only"]],
                         found_by_walk_only=[hex(o) for o in A["walk_only"]]),
        undecodable=undec)


def archive_txt(J):
    L = []
    s = J["summary"]
    L.append("%s  (%d bytes, sha1 %s)%s" % (J["archive"], J["size"], J["sha1"][:12],
                                            "  counterpart: %s" % J["counterpart"] if J["counterpart"] else ""))
    L.append("  decoded to PNG: %s" % ("yes" if J["decoded_to_png"] else "no (%s)" % (
        "has a .usd counterpart" if J["counterpart"] and J["archive"].endswith(".dat") else "data table")))
    L.append("  %d entries, %d textures (%d px), formats %s" % (
        s["entries"], s["textures"], s["total_texture_pixels"], s["formats"]))
    L.append("  structure totals: " + ", ".join("%s=%s" % (k, v) for k, v in
                                                 s["structure_totals"].items() if v))
    L.append("  scan cross-check: scan found %d ImageDescs, walk reached %d; scan-only %s; walk-only %s" % (
        J["cross_check"]["scan_found"], J["cross_check"]["walk_found"],
        len(J["cross_check"]["found_by_scan_only"]), len(J["cross_check"]["found_by_walk_only"])))
    L.append("")
    L.append("ENTRIES")
    for e in J["entries"]:
        st = e["structure"]
        parts = ["%s=%s" % (k, v) for k, v in st.items() if v and k not in ("fobj_types", "looks_2d",
                                                                             "anim_frames_max", "camera_projection")]
        L.append("  %-44s %-14s %8d B  %s" % (e["name"], e["kind"], e["extent"],
                                             ("FAILED " + e["parse_error"]) if e["parse_error"] else e["parse"]))
        if parts or st.get("looks_2d"):
            L.append("      %s%s" % (", ".join(parts), "  [%s]" % st["looks_2d"] if st.get("looks_2d") else ""))
        if e["texture_ids"]:
            L.append("      textures: %s%s" % (e["texture_ids"][:24], " ..." if len(e["texture_ids"]) > 24 else ""))
        for a in e["animated_textures"]:
            L.append("      TexAnim %s: %d frames" % (a["texanim"], a["frames"]))
    L.append("")
    L.append("TEXTURES")
    for t in J["textures"]:
        tl = " tlut=%s/%d" % (t["tlut"]["format"], t["tlut"]["entries"]) if t["tlut"] else ""
        an = " ANIM(%d)" % t["anim_frames"] if t["animated"] else ""
        tg = " [%s]" % ",".join(x["tag"] for x in t["tags"]) if t["tags"] else ""
        L.append("  #%03d %4dx%-4d %-7s%s mips=%d %7dB %s%s%s  <- %s (%d ref)" % (
            t["id"], t["w"], t["h"], t["format"], tl, t["mips"], t["image_bytes"], t["sha1"][:8],
            an, tg, t["entries"][0], t["n_paths"]))
    if J["undecodable"]:
        L.append("")
        L.append("UNDECODABLE")
        for u in J["undecodable"]:
            L.append("  %s" % u)
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------------- dat vs usd
def compare_pair(D, U):
    """Pair textures by structural path (entry / path), compare content hashes."""
    def index(A):
        m = {}
        for e in A["entries"]:
            for key, path in e["ctx"]["textures"]:
                t = A["w"].textures[key]
                m[(e["name"], path)] = (t["sha1"], t["w"], t["h"], FMT_NAME[t["fmt"]], t["bytes"], t["id"])
        return m
    dm, um = index(D), index(U)
    same = diff = 0
    differing, only_d, only_u = [], [], []
    seen_pairs = set()      # unique (dat sha, usd sha): a texture referenced N times counts once
    unique_same = set()
    fallback = 0
    used_u = set()

    def record(kd, vd, ku, vu, via):
        nonlocal same, diff
        used_u.add(ku)
        if vd[0] == vu[0]:
            same += 1
            unique_same.add(vd[0])
        else:
            diff += 1
            pair = (vd[0], vu[0])
            if pair in seen_pairs:
                return
            seen_pairs.add(pair)
            differing.append(dict(entry=kd[0], path=kd[1], usd_path=ku[1], paired_by=via,
                                  dat=dict(w=vd[1], h=vd[2], fmt=vd[3], bytes=vd[4], sha1=vd[0][:10]),
                                  usd=dict(w=vu[1], h=vu[2], fmt=vu[3], bytes=vu[4], sha1=vu[0][:10])))

    left_d = {}
    for k, v in dm.items():
        if k in um:
            record(k, v, k, um[k], "path")
        else:
            left_d[k] = v

    # Fallback pairing for what the path did not match (a joint added/removed in one language shifts
    # every later DFS index): same entry, same path with joint indexes erased, same w/h/format, in order.
    def loose(k, v):
        return (k[0], re.sub(r"j\d+", "j", k[1]), v[1], v[2], v[3])
    pool = collections.defaultdict(list)
    for k, v in um.items():
        if k not in used_u and k not in dm:
            pool[loose(k, v)].append(k)
    for k, v in list(left_d.items()):
        cands = pool.get(loose(k, v))
        if cands:
            ku = cands.pop(0)
            record(k, v, ku, um[ku], "fallback")
            fallback += 1
            del left_d[k]
    for k, v in left_d.items():
        only_d.append(dict(entry=k[0], path=k[1], w=v[1], h=v[2], fmt=v[3], bytes=v[4]))
    for k, v in um.items():
        if k not in dm and k not in used_u:
            only_u.append(dict(entry=k[0], path=k[1], w=v[1], h=v[2], fmt=v[3], bytes=v[4]))
    # pairing validation: how many dat textures whose content exists ANYWHERE in the usd sit at the
    # same path there
    usd_hashes = collections.defaultdict(set)
    for k, v in um.items():
        usd_hashes[v[0]].add(k)
    in_usd = at_same = 0
    for k, v in dm.items():
        if v[0] in usd_hashes:
            in_usd += 1
            if k in usd_hashes[v[0]]:
                at_same += 1
    # entry-level differences
    de = {e["name"] for e in D["entries"]}
    ue = {e["name"] for e in U["entries"]}
    return dict(
        archive=D["base"], dat_textures=len(dm), usd_textures=len(um), compared=same + diff,
        identical=same, differing=len(differing), differing_references=diff,
        paired_by_fallback=fallback, unique_identical=len(unique_same),
        only_in_dat=len(only_d), only_in_usd=len(only_u),
        differing_bytes_usd=sum(x["usd"]["bytes"] for x in differing),
        differing_bytes_dat=sum(x["dat"]["bytes"] for x in differing),
        only_in_dat_bytes=sum(x["bytes"] for x in only_d), only_in_usd_bytes=sum(x["bytes"] for x in only_u),
        pairing_check=dict(dat_textures_whose_content_appears_in_usd=in_usd,
                           of_which_at_the_same_path=at_same),
        entries_only_in_dat=sorted(de - ue), entries_only_in_usd=sorted(ue - de),
        differing_list=differing, only_in_dat_list=only_d, only_in_usd_list=only_u)


def differ_hashes(cmp_result):
    """(archive.usd, sha1-prefix) of every differing usd texture, to tag them baked_text."""
    return {(cmp_result["archive"] + ".usd", None)}


# ---------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--iso", default=DEFAULT_ISO)
    ap.add_argument("--raw-out", default=DEF_RAW)
    ap.add_argument("--tex-out", default=DEF_TEX)
    ap.add_argument("--index-out", default=DEF_INDEX)
    ap.add_argument("--only", help="comma-separated archive names (e.g. MnMaAll.usd,IfAll.dat)")
    ap.add_argument("--no-raw", action="store_true", help="skip copying the raw files")
    ap.add_argument("--no-decode", action="store_true", help="index only, no PNGs")
    args = ap.parse_args()

    t0 = time.time()
    g = mex_hsd.Gcm(args.iso)
    have = {n.rsplit("/", 1)[-1]: n for n in g.files}
    files = []
    for b in BASES_PAIRED:
        for ext in (".dat", ".usd"):
            if b + ext in have:
                files.append(b + ext)
    files += [s + ".dat" for s in SOLO]
    missing = [f for f in files if f not in have]
    if missing:
        sys.exit("not on the disc: %s" % missing)
    if args.only:
        want = set(args.only.split(","))
        files = [f for f in files if f in want]
    for d in (args.raw_out, args.tex_out, args.index_out):
        os.makedirs(d, exist_ok=True)

    # 1. raw copies, verified against the disc
    raw_sizes = {}
    if not args.no_raw:
        for f in files:
            data = g.read(f)
            p = os.path.join(args.raw_out, f)
            with open(p, "wb") as fh:
                fh.write(data)
            with open(p, "rb") as fh:
                assert hashlib.sha1(fh.read()).hexdigest() == hashlib.sha1(data).hexdigest()
            raw_sizes[f] = len(data)
        print("raw: %d files, %.1f MB -> %s" % (len(files), sum(raw_sizes.values()) / 1e6, args.raw_out))

    # 2. walk every archive (also the .dat with a .usd twin: needed for the comparison)
    parsed = {}
    for f in files:
        parsed[f] = run_archive(g, f, args.tex_out, decode=False)
        A = parsed[f]
        texture_record_list(A)
        print("%-16s %4d entries %5d textures %s" % (f, len(A["entries"]), len(A["w"].tex_order),
                                                     "(scan-only %d)" % len(A["scan_only"]) if A["scan_only"] else ""))

    # 3. dat vs usd
    comps = []
    differ = set()
    for b in BASES_PAIRED:
        d, u = b + ".dat", b + ".usd"
        if d in parsed and u in parsed:
            c = compare_pair(parsed[d], parsed[u])
            comps.append(c)
            for x in c["differing_list"]:
                differ.add((u, x["usd"]["sha1"]))
    # tag lookup by full sha1 for the usd side
    differ_full = set()
    for c in comps:
        A = parsed[c["archive"] + ".usd"]
        short = {x["usd"]["sha1"] for x in c["differing_list"]}
        for t in A["w"].textures.values():
            if t["sha1"][:10] in short:
                differ_full.add((A["fname"], t["sha1"]))

    # 4. decode + write per-archive indexes
    decoded_files = [f for f in files if (f.endswith(".usd") or (f.replace(".dat", ".usd") not in files
                                                                   and f.replace(".dat", ".usd") not in have))
                     and f.rsplit(".", 1)[0] not in NO_DECODE]
    summaries = []
    for f in files:
        A = parsed[f]
        base = A["base"]
        do = (f in decoded_files) and not args.no_decode
        undec = write_pngs(A, args.tex_out) if do else []
        cp = None
        if f.endswith(".dat") and base + ".usd" in have:
            cp = base + ".usd"
        elif f.endswith(".usd"):
            cp = base + ".dat"
        J = archive_json(A, cp, differ_full, do, undec)
        with open(os.path.join(args.index_out, f + ".json"), "w") as fh:
            json.dump(J, fh, indent=1)
        with open(os.path.join(args.index_out, f + ".txt"), "w") as fh:
            fh.write(archive_txt(J))
        summaries.append(J)
        if do:
            print("decoded %-14s %4d PNG, %d undecodable" % (f, sum(1 for t in J["textures"] if t["file"]),
                                                            len(undec)))

    # 5. comparison outputs
    tot = collections.Counter()
    for c in comps:
        for k in ("compared", "identical", "differing", "differing_references", "paired_by_fallback",
                  "only_in_dat", "only_in_usd", "differing_bytes_usd", "differing_bytes_dat"):
            tot[k] += c[k]
    with open(os.path.join(args.index_out, "_dat_vs_usd.json"), "w") as fh:
        json.dump(dict(headline=dict(differing_textures=tot["differing"], differing_bytes_usd=tot["differing_bytes_usd"],
                                     differing_bytes_dat=tot["differing_bytes_dat"],
                                     only_in_dat=tot["only_in_dat"], only_in_usd=tot["only_in_usd"],
                                     compared=tot["compared"], identical=tot["identical"]),
                       pairs=comps), fh, indent=1)
    L = ["DAT vs USD: textures compared by structural path, content by sha1 of the raw image (+TLUT)", ""]
    L.append("%-10s %8s %8s %9s %8s %7s %7s %11s   pairing check" % (
        "archive", "compared", "identical", "differing", "dat-only", "usd-only", "", "differ bytes"))
    for c in comps:
        pc = c["pairing_check"]
        L.append("%-10s %8d %8d %9d %8d %7d %7s %11d   %d/%d same-content textures pair at the same path" % (
            c["archive"], c["compared"], c["identical"], c["differing"], c["only_in_dat"], c["only_in_usd"],
            "", c["differing_bytes_usd"], pc["of_which_at_the_same_path"], pc["dat_textures_whose_content_appears_in_usd"]))
    L.append("")
    L.append("HEADLINE: %d unique textures differ between .dat and .usd (%d KB of .usd pixels; %d references); "
             "%d references compared (%d by fallback), %d identical, %d only in .dat, %d only in .usd" % (
                 tot["differing"], tot["differing_bytes_usd"] // 1024, tot["differing_references"],
                 tot["compared"], tot["paired_by_fallback"], tot["identical"],
                 tot["only_in_dat"], tot["only_in_usd"]))
    for c in comps:
        if c["differing"] or c["only_in_dat"] or c["only_in_usd"] or c["entries_only_in_dat"] or c["entries_only_in_usd"]:
            L.append("")
            L.append("== %s" % c["archive"])
            if c["entries_only_in_dat"]:
                L.append("  entries only in .dat: %s" % c["entries_only_in_dat"])
            if c["entries_only_in_usd"]:
                L.append("  entries only in .usd: %s" % c["entries_only_in_usd"])
            for x in c["differing_list"]:
                L.append("  DIFF  %-40s %-22s dat %dx%d %s  usd %dx%d %s" % (
                    x["entry"][:40], x["path"], x["dat"]["w"], x["dat"]["h"], x["dat"]["fmt"],
                    x["usd"]["w"], x["usd"]["h"], x["usd"]["fmt"]))
            for x in c["only_in_dat_list"]:
                L.append("  DAT-ONLY %-37s %-22s %dx%d %s" % (x["entry"][:37], x["path"], x["w"], x["h"], x["fmt"]))
            for x in c["only_in_usd_list"]:
                L.append("  USD-ONLY %-37s %-22s %dx%d %s" % (x["entry"][:37], x["path"], x["w"], x["h"], x["fmt"]))
    with open(os.path.join(args.index_out, "_dat_vs_usd.txt"), "w") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L[:len(comps) + 6]))

    write_manifest(args, files, parsed, summaries, comps, tot, raw_sizes, time.time() - t0)
    print("done in %.0f s" % (time.time() - t0))


def write_manifest(args, files, parsed, summaries, comps, tot, raw_sizes, secs):
    man = os.path.join(os.path.dirname(args.index_out.rstrip("/\\")), "MANIFEST.md")
    js = {s["archive"]: s for s in summaries}
    L = []
    L.append("# Vanilla Melee menu assets - manifest")
    L.append("")
    L.append("Source: `%s` (NTSC-U 1.02). Extracted locally from the user's own disc image; nothing here "
             "is committed or redistributed. **This folder holds metadata only** (names, sizes, formats, "
             "counts, hashes, structure) - no pixels. The raw archives and decoded PNGs live in "
             "`%s` and `%s`, outside this folder and outside the repo." % (args.iso, args.raw_out, args.tex_out))
    L.append("")
    L.append("## Layout")
    L.append("")
    L.append("- `raw/` - all %d files byte for byte (`.dat` = Japanese-region, `.usd` = English overrides; "
             "the US build loads the `.usd` where one exists)." % len(files))
    L.append("- `textures/<archive>/NNN_<entry>_<w>x<h>_<FORMAT>.png` - decoded textures, **only** the "
             "`.usd` files and the `.dat` files with no `.usd` (data tables are not decoded). `ORPHAN_*` "
             "= found by the ImageDesc scan but not by the structural walk. `card_*` = raw memory-card banners/icons.")
    L.append("- `index/<archive>.json|.txt` - per archive: every public entry with its kind and structure, "
             "every texture with size/format/TLUT/mips/sha1/referencing paths/tags.")
    L.append("- `index/_dat_vs_usd.json|.txt` - the language comparison.")
    L.append("")
    L.append("## Headline numbers")
    L.append("")
    L.append("- **%d unique textures differ between the .dat and .usd copies** (%d KB of English pixels; %d KB in "
             "the .dat) - these are the textures with language-specific content baked in. (Counted once per "
             "distinct dat/usd content pair; a texture referenced from several materials counts once.)"
             % (tot["differing"], tot["differing_bytes_usd"] // 1024, tot["differing_bytes_dat"] // 1024))
    L.append("- Of all texture *references* paired by structural path (or, for %d, by the joint-index-blind "
             "fallback): %d identical, %d differ, %d only in .dat, %d only in .usd (the .usd-only ones are "
             "usually screens that gained content in the US build, e.g. the title animation)."
             % (tot["paired_by_fallback"], tot["identical"], tot["differing_references"],
                tot["only_in_dat"], tot["only_in_usd"]))
    ntex = sum(len(parsed[f]["w"].tex_order) for f in files)
    L.append("- %d files, %.1f MB raw, %d unique textures found across all archives (each .dat and .usd counted "
             "separately)." % (len(files), sum(raw_sizes.values()) / 1e6, ntex))
    L.append("")
    L.append("## The 75 files")
    L.append("")
    L.append("| file | bytes | what it holds | entries | textures | PNGs | pair |")
    L.append("|---|---:|---|---:|---:|---:|---|")
    for f in files:
        J = js[f]
        base = f.rsplit(".", 1)[0]
        pngs = sum(1 for t in J["textures"] if t["file"])
        L.append("| `%s` | %d | %s | %d | %d | %d | %s |" % (
            f, J["size"], WHAT.get(base, ""), J["summary"]["entries"], J["summary"]["textures"], pngs,
            J["counterpart"] or "-"))
    L.append("")
    L.append("## Screens that depend on assets that are NOT dumped (loaded from the disc regardless)")
    L.append("")
    L.append("Excluded from the dump on purpose (GD's call). Character/trophy art always comes from the "
             "user's disc; sounds are a separate original-audio job. Dependencies are by file naming and the "
             "decomp's screen loaders, not by walking those files:")
    L.append("")
    L.append("| not dumped | what it is | screens that depend on it |")
    L.append("|---|---|---|")
    L.append("| trophy models (`Ty*.dat` figure models via the trophy lookup tables) | the 3D trophies | "
             "trophy gallery (TyMnDisp), trophy lottery (TyMnFigp), trophy viewer (TyMnView); the "
             "Adventure/Classic trophy-get overlays (IfPrize, GmRegClr) |")
    L.append("| `GmRstM*.dat` | per-character results-screen models | results screen (GmRst): winner "
             "pose/name card; also the tournament results |")
    L.append("| menu sound banks (`.ssm`) and `audio` | button/cursor/announcer sounds | every menu; replacing "
             "them is a separate original-audio job |")
    L.append("| character/costume files (`Pl*.dat`, `Ef*`) | fighter models | CSS/SSS 3D previews, "
             "results, trophies |")
    L.append("| `LbAd`, `LbBf`, `LbRb`, `LbRf` | data tables (kept in `raw/`, indexed, not decoded) | "
             "engine-wide, no screen of their own |")
    L.append("")
    L.append("## How to use the index")
    L.append("")
    L.append("Each `index/<archive>.json` lists entries with a `structure` block (joints, meshes, "
             "materials, TObjs, animation tracks, TexAnim-animated textures, cameras/lights, a 2D/3D guess) and "
             "a `textures` list (id, size, format, TLUT, mips, sha1, referencing entries/paths, heuristic tags "
             "with reasons). Tags are heuristics: `baked_text` (differs between .dat/.usd, or a text-like name), "
             "`character_art` (character-art name patterns or 20-400-frame texture animations), `font_like`. "
             "Paths are structural (`j<DFS index>.d<mesh>.t<texture>`, `mj<n>.ma<n>.ta<n>.f<frame>`, `so`) so a "
             "texture in the `.dat` and `.usd` copies can be matched by path.")
    with open(man, "w") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
