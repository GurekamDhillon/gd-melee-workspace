#!/usr/bin/env python3
"""Dump the Character Select Screen (CSS) data an m-ex build ships, read-only.

Three sources are decoded:

  * MxDt.dat `mexData`: root +0x04 `menu` -> +0x04 `css` is a relocated copy of the retail
    CSS data block (retail DOL 0x803F0A48): 0x1C bytes of G&W name, 24 mode-info rows (8 bytes),
    then the icon array at +0xDC (0x1C bytes/icon: hudindex, char id, state, anim timer,
    joint vs, joint 1p, sfx, bound l/r/u/d). The count is MexMetaData.css_icon_count.
    `fighter` +0x00 is the name table and +0x0C the external->internal mapping (3 bytes per
    external id, same shape as the retail `ftMapping_list`).
  * MnSlChr.usd: public symbols, and the optional `mexSelectChr` struct (5 words: icon model
    joint, icon anim joint, icon matanim joint, CSP matanim joint, CSP stride).
  * The retail icon table, for comparison, is described in the decomp
    (melee/src/melee/mn/mncharsel.c `icons[]`) - not read from any file here.

Nothing is written. m-ex has no licence: this tool only *describes* data, it copies none.

    python dump_css.py --iso C:/iso/Akaneia.iso
    python dump_css.py --iso C:/iso/Akaneia.iso --joints      # also walk the icon model
"""

import argparse
import struct
import sys

import mex_hsd

ICON_STRIDE = 0x1C
ICONS_OFF = 0xDC
MAPPING_STRIDE = 3


def f32(ar, off):
    return struct.unpack_from(">f", ar.data, off)[0]


def walk_joints(ar, jobj, depth=0, out=None, limit=4096):
    """Pre-order JObj walk over HSD_JObjDesc (+0x04 flags, +0x08 child, +0x0C next,
    +0x2C/0x30/0x34 translate). The walk index is the HSD joint index that
    lb_80011E24 (JObj-by-index lookup) uses."""
    if out is None:
        out = []
    while jobj and ar.in_data(jobj) and len(out) < limit:
        flags = ar.u32(jobj + 0x04)
        child = ar.u32(jobj + 0x08)
        nxt = ar.u32(jobj + 0x0C)
        tx, ty, tz = (f32(ar, jobj + 0x2C), f32(ar, jobj + 0x30), f32(ar, jobj + 0x34))
        out.append((len(out), depth, jobj, flags, tx, ty, tz))
        if child:
            walk_joints(ar, child, depth + 1, out, limit)
        jobj = nxt
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--iso", required=True, help="GCM image (opened read-only)")
    ap.add_argument("--mxdt", default="MxDt.dat")
    ap.add_argument("--slchr", default="MnSlChr.usd")
    ap.add_argument("--joints", action="store_true", help="walk mexSelectChr's icon model")
    args = ap.parse_args()

    gcm = mex_hsd.Gcm(args.iso)

    # ---------------------------------------------------------------- mexData
    try:
        md = mex_hsd.Archive(gcm.read(args.mxdt)).relocate(0)
    except KeyError:
        md = None
        print(f"== no {args.mxdt} on this disc (not an m-ex build)")
    names = []
    mapping = []
    if md is not None:
        base = md.public("mexData")
        meta, menu, fighter = md.u32(base), md.u32(base + 4), md.u32(base + 8)
        n_int, n_ext, n_icons = md.s32(meta + 4), md.s32(meta + 8), md.s32(meta + 12)
        print(f"== mexData metadata: internal {n_int}  external {n_ext}  css icons {n_icons}")
        param, css, sss = md.u32(menu), md.u32(menu + 4), md.u32(menu + 8)
        print(f"== menu @+0x{menu:X}: param +0x{param:X} css +0x{css:X} sss +0x{sss:X}")
        if md.in_data(param):
            print(f"   menu param floats: {[round(f32(md, param + 4 * i), 4) for i in range(4)]}")

        name_tab = md.u32(fighter + 0x00)
        map_tab = md.u32(fighter + 0x0C)
        for e in range(n_ext):
            p = md.u32(name_tab + 4 * e) if md.in_data(name_tab) else 0
            names.append(md.cstr(p) if md.in_data(p) else None)
            if md.in_data(map_tab):
                mapping.append(tuple(struct.unpack_from(">bbb", md.data, map_tab + e * MAPPING_STRIDE)))
        print(f"== fighter.names @+0x{name_tab:X}, external->internal @+0x{map_tab:X}")
        for e in range(n_ext):
            m = mapping[e] if e < len(mapping) else None
            print(f"   ext {e:>2} (0x{e:02X})  -> internal {m}  {names[e]!r}")

        print(f"== CSS icon table @ css+0xDC = data+0x{css + ICONS_OFF:X} "
              f"({n_icons} icons + 1 terminator row)")
        print("   idx hud  ext  st  jVS  j1P   sfx        bound l/r/u/d          name")
        for i in range(n_icons + 1):
            o = css + ICONS_OFF + i * ICON_STRIDE
            hud, ext, st, tim, jvs, j1p = (md.u8(o + k) for k in range(6))
            sfx = md.u32(o + 8)
            b = [round(f32(md, o + 0xC + 4 * k), 2) for k in range(4)]
            nm = names[ext] if ext < len(names) else "-"
            print(f"   {i:>3} {hud:>3} {ext:>4} {st:>3} {jvs:>4} {j1p:>4}  0x{sfx:06X}  {b}  {nm}")

    # ---------------------------------------------------------------- MnSlChr
    raw = gcm.read(args.slchr)
    sl = mex_hsd.Archive(raw).relocate(0)
    print(f"== {args.slchr}: {len(raw)} bytes, publics {[s for s, _ in sl.publics]}")
    try:
        ms = sl.public("mexSelectChr")
    except KeyError:
        print("   no mexSelectChr (retail CSS path)")
        return 0
    words = [sl.u32(ms + 4 * i) for i in range(5)]
    labels = ["icon model (JObjDesc)", "icon animjoint", "icon matanim_joint",
              "CSP matanim_joint", "CSP stride"]
    for lab, w in zip(labels, words):
        shown = ("data+0x%X" % w) if (sl.in_data(w) and lab != "CSP stride") else str(w)
        print(f"   mexSelectChr {lab:<22} {shown}")
    if args.joints and sl.in_data(words[0]):
        js = walk_joints(sl, words[0])
        print(f"== icon model: {len(js)} joints (index = HSD joint index, pre-order)")
        for idx, depth, off, flags, tx, ty, tz in js:
            print(f"   j{idx:<3} {'  ' * depth}+0x{off:X} flags 0x{flags:08X} "
                  f"t=({tx:.2f},{ty:.2f},{tz:.2f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
