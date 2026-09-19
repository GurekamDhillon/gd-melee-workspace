#!/usr/bin/env python3
"""Dump an m-ex `itFunction` (fighter/stage article code) out of a .dat.

Layout (derived from the shipped data and from the behaviour of m-ex's itFunction loader,
see _research/mex-item-spawn.md Q1):

    itFunction:
        +0x00 u32          count           number of articles this file carries code for
        +0x04 MEXFunction* item[count]     inline array of relocated pointers, one per
                                           article, in *article index* order (item[n] is
                                           the code for this fighter's article n). NULL = none.

Each item[n] is an ordinary 8-word MEXFunction (same layout as ftFunction; see
dump_ftfunction.py). The difference is what its functionRelocTable means: each entry is
    { u32 slot; u32 code_offset; }
and slot is a WORD INDEX into that article's 0x3C-byte ItemLogicTable (the per-kind
callback table the game keeps at Item.xB8). At load time the loader writes
    ItemLogicTable[slot] = code_base + code_offset
into the MxDt item.Custom entry for the article's global ItemKind. Slot 0 is `states`
(the ItemStateTable*), so for m-ex articles the state table itself lives INSIDE the code
blob and its function pointers are fixed up by the blob's own abs32 instruction relocs.

Examples:

    python dump_itfunction.py --iso C:/iso/Akaneia.iso PlSn.dat
    python dump_itfunction.py --iso C:/iso/Akaneia.iso PlSn.dat --states 8
    python dump_itfunction.py --iso C:/iso/Akaneia.iso PlSn.dat --symbols --relocs
    python dump_itfunction.py --iso C:/iso/Akaneia.iso PlSn.dat --emit-blob it_sn.bin
    python dump_itfunction.py --iso C:/iso/Akaneia.iso --survey PlSn.dat PlTs.dat PlWf.dat

Read-only: nothing is ever written except the explicit --emit-blob target.
"""

import argparse
import struct
import sys

import mex_hsd
from dump_ftfunction import FtFunction, RELOC_FLAGS, build_index, resolve

# struct ItemLogicTable, melee/src/melee/it/kinds/types.h (15 words = 0x3C).
LOGIC_SLOTS = [
    "states", "spawned", "destroyed", "picked_up", "dropped", "thrown",
    "dmg_dealt", "dmg_received", "entered_air", "reflected", "clanked",
    "absorbed", "shield_bounced", "hit_shield", "evt_unk",
]
STATE_STRIDE = 0x10  # struct ItemStateTable { anim_id; animated; physics_updated; collided; }


class ItFunction(FtFunction):
    """One element of itFunction.item[]: a MEXFunction at an explicit data offset."""

    def __init__(self, archive, base):
        # FtFunction resolves its base from a public symbol; reuse its parser at `base`.
        self.ar = archive
        self.symbol = f"itFunction.item@0x{base:X}"
        self.base = base
        r = archive.u32
        b = base
        self.code_off = r(b + 0x00)
        self.instr_reloc_off = r(b + 0x04)
        self.instr_reloc_num = r(b + 0x08)
        self.func_reloc_off = r(b + 0x0C)
        self.func_reloc_num = r(b + 0x10)
        self.code_size = r(b + 0x14)
        self.debug_num = r(b + 0x18)
        self.debug_off = r(b + 0x1C)
        self.warnings = self._sanity(archive.data_size)


def parse(ar):
    top = ar.public("itFunction")
    count = ar.u32(top)
    items = []
    for n in range(count):
        slot = top + 4 + n * 4
        ptr = ar.u32(slot)
        relocated = slot in ar.reloc_set
        items.append((n, ptr, relocated, ItFunction(ar, ptr) if ptr else None))
    return top, count, items


def reloc_at(it, code_base):
    """{code_offset: (flag, target_va)} for the item's instruction relocs."""
    out = {}
    for flag, off, target in it.instr_relocs():
        fn = target if (target & 0xF0000000) == 0x80000000 else code_base + target
        out[off] = (flag, fn)
    return out


def main():
    ap = argparse.ArgumentParser(
        description="Parse an m-ex itFunction (article code) out of a .dat.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Examples:", 1)[1])
    ap.add_argument("dat", nargs="+", help=".dat file(s): loose, or names inside --iso")
    ap.add_argument("--iso", help="read the .dat out of this GCM image (read-only)")
    ap.add_argument("--code-base", default="0x80000000",
                    help="guest VA to relocate each article's code blob to (default 0x80000000)")
    ap.add_argument("--item", type=int, default=None, help="only this article index")
    ap.add_argument("--symbols", action="store_true", help="dump the article's debug symbols")
    ap.add_argument("--relocs", action="store_true", help="dump the instruction reloc table")
    ap.add_argument("--states", type=int, default=0, metavar="N",
                    help="decode N ItemStateTable rows at the `states` slot (inside the blob)")
    ap.add_argument("--emit-blob", metavar="PATH",
                    help="write the relocated code blob of the (single / --item) article")
    ap.add_argument("--survey", action="store_true", help="one summary line per file")
    args = ap.parse_args()
    code_base = int(args.code_base, 0)
    gcm = mex_hsd.Gcm(args.iso) if args.iso else None

    rc = 0
    for name in args.dat:
        try:
            raw = gcm.read(name) if gcm else open(name, "rb").read()
            ar = mex_hsd.Archive(raw).relocate(0)
            top, count, items = parse(ar)
        except (KeyError, ValueError, OSError) as exc:
            print(f"{name}: {exc}")
            rc = 1
            continue

        if args.survey:
            parts = []
            for n, ptr, rel, it in items:
                if not it:
                    parts.append(f"[{n}] NULL")
                    continue
                slots = sorted(s for s, _ in it.func_relocs())
                parts.append(f"[{n}] code 0x{it.code_off:X}+0x{it.code_size:X} "
                             f"ir {it.instr_reloc_num} slots {slots} dbg {it.debug_num}"
                             f"{' WARN' if it.warnings else ''}")
            print(f"{name:<10} itFunction@0x{top:X} count {count}: " + "; ".join(parts))
            continue

        print(f"== {name}: itFunction @ data+0x{top:X}  count {count}")
        for n, ptr, rel, it in items:
            if args.item is not None and n != args.item:
                continue
            print(f"-- article {n}: item[{n}] = data+0x{ptr:X} "
                  f"({'relocated' if rel else 'NOT in reloc table'})")
            if not it:
                continue
            for w in it.warnings:
                print(f"   WARNING: {w}")
            print(f"   code  data+0x{it.code_off:X} size 0x{it.code_size:X}  "
                  f"instrRelocs {it.instr_reloc_num} @ data+0x{it.instr_reloc_off:X}  "
                  f"funcRelocs {it.func_reloc_num} @ data+0x{it.func_reloc_off:X}  "
                  f"debugSyms {it.debug_num} @ data+0x{it.debug_off:X}")
            index = build_index(it.debug_symbols(), it.code_size)
            relocs = reloc_at(it, code_base)

            def name_of(off):
                hit = resolve(index, off)
                if not hit:
                    return "?"
                return hit[2] if hit[0] == off else f"{hit[2]}+0x{off - hit[0]:X}"

            print("   ItemLogicTable slots written by the loader:")
            state_off = None
            for slot, off in it.func_relocs():
                label = LOGIC_SLOTS[slot] if slot < len(LOGIC_SLOTS) else f"?slot{slot}"
                if slot == 0:
                    state_off = off
                print(f"     +0x{slot * 4:02X} {label:<15} = code+0x{off:04X} "
                      f"(0x{code_base + off:08X})  {name_of(off)}")
            if args.states and state_off is not None:
                nrows = args.states
                hit = resolve(index, state_off)
                if hit and hit[0] == state_off:
                    # the debug symbol bounds the table: never decode code as state rows
                    nrows = min(nrows, (hit[1] - hit[0]) // STATE_STRIDE)
                print(f"   ItemStateTable @ code+0x{state_off:X} ({nrows} rows"
                      f"{', bounded by its debug symbol' if nrows != args.states else ''}):")
                for i in range(nrows):
                    row = []
                    for f in range(4):
                        co = state_off + i * STATE_STRIDE + f * 4
                        raw_w = ar.u32(it.code_off + co)
                        if co in relocs:
                            flag, va = relocs[co]
                            row.append(f"0x{va:08X}<{name_of(va - code_base) if va >= code_base and va < code_base + it.code_size else 'abs'}>")
                        else:
                            row.append(f"{raw_w:#x}" if f == 0 else
                                       (f"0x{raw_w:08X}" if raw_w else "NULL"))
                    print(f"     [{i}] anim {row[0]:<6} animated {row[1]}  phys {row[2]}  "
                          f"coll {row[3]}")
            if args.symbols:
                print("   debug symbols:")
                for s, e, nm in index:
                    print(f"     0x{code_base + s:08X}..0x{code_base + e:08X}  {nm}")
            if args.relocs:
                counts = {}
                for flag, off, target in it.instr_relocs():
                    counts[flag] = counts.get(flag, 0) + 1
                print("   instr relocs: " + ", ".join(
                    f"{RELOC_FLAGS.get(f, hex(f))}={c}" for f, c in sorted(counts.items())))
                for flag, off, target in it.instr_relocs():
                    kind = "abs" if (target & 0xF0000000) == 0x80000000 else "code-rel"
                    print(f"     code+0x{off:04X} {RELOC_FLAGS.get(flag, hex(flag)):<7} "
                          f"-> 0x{target:08X} ({kind})  in {name_of(off)}")
            if args.emit_blob:
                blob, _ = it.relocated_code(code_base)
                with open(args.emit_blob, "wb") as fp:
                    fp.write(blob)
                print(f"   wrote {len(blob)} bytes to {args.emit_blob} (base 0x{code_base:08X})")
    return rc


if __name__ == "__main__":
    sys.exit(main())
