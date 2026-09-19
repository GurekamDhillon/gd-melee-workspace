#!/usr/bin/env python3
"""Dump m-ex's `MxDt.dat` (the `mexData` archive).

`MxDt.dat` is an HSD archive whose single public symbol is literally `mexData`. Offline we
relocate with base 0, so every pointer printed below is a **data-section offset** inside
the archive - the same number the port will see before it adds its own guest base.

Struct order follows m-ex's `MexTK/include/mxdt.h` (`MexData`, `MexMetaData`, and the
anonymous `MexData.fighter` struct). That header carries a `// theres more im just lazy`
comment mid-struct, so `--validate` re-derives the interesting fields from independent
evidence (the fighter names and filenames stored in the file) instead of trusting the
declared field order. Trust `--validate` over `--fighter`.

Examples:

    python dump_mxdt.py --iso C:/iso/Akaneia.iso MxDt.dat --root --metadata
    python dump_mxdt.py --iso C:/iso/Akaneia.iso MxDt.dat --validate
    python dump_mxdt.py --iso C:/iso/Akaneia.iso MxDt.dat --item-lookup
    python dump_mxdt.py --iso C:/iso/Akaneia.iso MxDt.dat --item --runtime-index
    python dump_mxdt.py MxDt.dat --fighter
"""

import argparse
import sys

import mex_hsd

# MexData root, in declaration order (mxdt.h `MexData`).
ROOT_FIELDS = [
    "metadata", "menu", "fighter", "fighter_function", "ssm", "music", "effect",
    "item", "kirby_data", "kirby_function", "stage", "stage_desc", "scene", "misc",
]

# MexMetaData (mxdt.h): u8 v_major, u8 v_minor, s16 flags, then 14 s32 counts.
METADATA_COUNTS = [
    "internal_id_count", "external_id_count", "css_icon_count", "internal_stage_count",
    "external_stage_count", "sss_icon_count", "ssm_count", "bgm_count", "effect_count",
    "bootup_scene", "last_major", "last_minor", "trophy_count", "trophy_sd_offset",
]

# Independently recorded expectations (_research/mex-content-expansion.md) - a mismatch
# means either the file changed or the struct order is off by one.
METADATA_EXPECT = {
    "internal_id_count": 41, "css_icon_count": 32,
    "internal_stage_count": 96, "sss_icon_count": 67,
}

# MexData.fighter: the parallel per-kind arrays, in mxdt.h declaration order. The header is
# self-admittedly incomplete, so this list is a hypothesis that --validate tests.
FIGHTER_FIELDS = [
    "names", "pl_file", "insignia_idx", "ft_kind_desc", "costume_info", "costume_file",
    "ftdemo", "anim_filenames", "anim_num", "effect_index", "result_file", "result_scale",
    "victory_theme", "announcer_call", "ssm_files", "costume_pointers", "ft_archives",
    "walljump", "rst_runtime", "item_lookup", "target_test_lookup", "fighter_music",
    "vi_files", "endclassicfiles", "endadventurefiles", "endallstarfiles", "endmoviefiles",
    "race_to_finish", "demo_params", "classic_trophy_id", "adventure_trophy_id",
    "allstar_trophy_id", "ending_fall_scale",
]

# MexData.item / m-ex's Arch_ItemsAdded (Header.s).
ITEM_FIELDS = ["Common", "Fighter", "Pokemon", "Stages", "Custom", "RuntimeIndex"]

CUSTOM_ITEM_START = 237     # Header.s CustomItemStart
ITEM_LOOKUP_STRIDE = 8      # { s32 count; u16 *global_item_kinds }
ITEM_CUSTOM_STRIDE = 0x3C   # item.Custom function-table stride (Item Extension/Create Item.asm)
ITEM_RUNTIME_STRIDE = 4     # item.RuntimeIndex is one descriptor pointer per custom kind

SONIC_INTERNAL_KIND = 31


class MexData:
    def __init__(self, archive, symbol="mexData"):
        self.ar = archive
        self.base = archive.public(symbol)
        self.root = {name: archive.u32(self.base + i * 4)
                     for i, name in enumerate(ROOT_FIELDS)}

    # ------------------------------------------------------------------ metadata
    def metadata(self):
        p = self.root["metadata"]
        ar = self.ar
        out = {"v_major": ar.u8(p), "v_minor": ar.u8(p + 1),
               "flags": ar.u16(p + 2)}
        for i, name in enumerate(METADATA_COUNTS):
            out[name] = ar.s32(p + 4 + i * 4)
        return out

    # ------------------------------------------------------------------ fighter
    def fighter_fields(self):
        p = self.root["fighter"]
        return [(i, name, self.ar.u32(p + i * 4)) for i, name in enumerate(FIGHTER_FIELDS)]

    def fighter_field(self, name):
        return self.ar.u32(self.root["fighter"] + FIGHTER_FIELDS.index(name) * 4)

    def item_lookup(self, table, count):
        """[(kind, count, ids_off, [ids])] over `count` entries at data offset `table`."""
        out = []
        for k in range(count):
            e = table + k * ITEM_LOOKUP_STRIDE
            n = self.ar.s32(e)
            ptr = self.ar.u32(e + 4)
            ids = []
            if 0 < n < 256 and self.ar.in_data(ptr):
                ids = [self.ar.u16(ptr + j * 2) for j in range(n)]
            out.append((k, n, ptr, ids))
        return out

    def item(self):
        p = self.root["item"]
        return {name: self.ar.u32(p + i * 4) for i, name in enumerate(ITEM_FIELDS)}


def is_reloc(ar, off):
    return off in ar.reloc_set


def main():
    ap = argparse.ArgumentParser(
        description="Parse m-ex's MxDt.dat (the mexData archive).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Examples:", 1)[1])
    ap.add_argument("dat", nargs="?", default="MxDt.dat",
                    help="MxDt.dat: a loose file, or a name inside --iso (default MxDt.dat)")
    ap.add_argument("--iso", help="read `dat` out of this GCM image instead (read-only)")
    ap.add_argument("--symbol", default="mexData", help="public symbol (default mexData)")

    ap.add_argument("--root", action="store_true", help="the 14 MexData root words")
    ap.add_argument("--metadata", action="store_true", help="decode MexMetaData + check counts")
    ap.add_argument("--fighter", action="store_true",
                    help="the MexData.fighter array pointers (UNTRUSTED field names)")
    ap.add_argument("--item-lookup", action="store_true",
                    help="fighter.item_lookup: per-kind { count, u16 *global_item_kinds }")
    ap.add_argument("--item", action="store_true", help="the MexData.item table")
    ap.add_argument("--runtime-index", action="store_true",
                    help="dump item.RuntimeIndex and confirm it ships zeroed")
    ap.add_argument("--validate", action="store_true",
                    help="cross-check struct decoding against independent evidence in the file")
    ap.add_argument("--kind", type=int, default=SONIC_INTERNAL_KIND,
                    help=f"internal fighter kind to spotlight (default {SONIC_INTERNAL_KIND} = Sonic)")
    ap.add_argument("--item-lookup-off", default=None,
                    help="override the item_lookup data offset (default: read from the struct)")
    ap.add_argument("--custom-item-count", type=int, default=0,
                    help="how many custom-item slots to scan for --runtime-index "
                         "(default: derive from the largest id in fighter.item_lookup)")
    ap.add_argument("--all", action="store_true", help="everything")
    args = ap.parse_args()

    if args.all:
        args.root = args.metadata = args.fighter = args.item_lookup = True
        args.item = args.runtime_index = args.validate = True
    if not any([args.root, args.metadata, args.fighter, args.item_lookup, args.item,
                args.runtime_index, args.validate]):
        args.root = args.metadata = args.validate = True

    try:
        raw = mex_hsd.load_dat(args.dat, args.iso)
        ar = mex_hsd.Archive(raw).relocate(0)
        md = MexData(ar, args.symbol)
    except (KeyError, ValueError, OSError) as exc:
        print(f"dump_mxdt: {exc}", file=sys.stderr)
        return 1
    rc = 0

    print(f"== {args.dat}  ({len(raw)} bytes)")
    print(f"archive: fileSize 0x{ar.file_size:X}  dataSize 0x{ar.data_size:X}  "
          f"relocs {ar.nb_reloc}  publics {ar.nb_public}  externs {ar.nb_extern}")
    for sym, off in ar.publics:
        print(f"  public  {sym:<12} data+0x{off:X}")

    if args.root:
        print(f"== MexData root ({len(ROOT_FIELDS)} words @ data+0x{md.base:X})")
        for i, name in enumerate(ROOT_FIELDS):
            v = md.root[name]
            flag = "" if ar.in_data(v) else "   <-- NOT a data offset"
            print(f"  +0x{i * 4:02X}  {name:<17} data+0x{v:05X}{flag}")

    if args.metadata:
        m = md.metadata()
        print(f"== MexMetaData @ data+0x{md.root['metadata']:X}")
        print(f"  version v{m['v_major']}.{m['v_minor']}  flags 0x{m['flags']:X}")
        for name in METADATA_COUNTS:
            exp = METADATA_EXPECT.get(name)
            if exp is None:
                note = ""
            elif exp == m[name]:
                note = f"   (matches the independently recorded {exp})"
            else:
                note = f"   *** MISMATCH: expected {exp} ***"
                rc = 2
            print(f"  {name:<22} {m[name]}{note}")
        if rc:
            print("  !! metadata disagrees with _research/mex-content-expansion.md - either the "
                  "file changed or MexMetaData's field order is wrong.")

    if args.fighter:
        print(f"== MexData.fighter @ data+0x{md.root['fighter']:X} "
              f"({len(FIGHTER_FIELDS)} pointers; names are mxdt.h's and are NOT verified)")
        for i, name, v in md.fighter_fields():
            mark = "" if ar.in_data(v) else "   <-- NOT a data offset"
            print(f"  [{i:>2}] +0x{i * 4:02X}  {name:<20} data+0x{v:05X}{mark}")

    lookup_off = (int(args.item_lookup_off, 0) if args.item_lookup_off
                  else md.fighter_field("item_lookup"))
    n_kinds = md.metadata()["internal_id_count"]

    if args.item_lookup:
        print(f"== fighter.item_lookup @ data+0x{lookup_off:X} "
              f"(stride {ITEM_LOOKUP_STRIDE}, {n_kinds} internal kinds, "
              f"{n_kinds * ITEM_LOOKUP_STRIDE} bytes)")
        rows = md.item_lookup(lookup_off, n_kinds)
        for k, n, ptr, ids in rows:
            if n == 0 and ptr == 0:
                continue
            ptr_reloc = "reloc" if is_reloc(ar, lookup_off + k * ITEM_LOOKUP_STRIDE + 4) else "RAW"
            mark = "  <== " + f"kind {args.kind}" if k == args.kind else ""
            print(f"  kind {k:>3}  count {n:>3}  ids @ data+0x{ptr:05X} ({ptr_reloc})  "
                  f"{ids}{mark}")
        empty = sum(1 for _, n, p, _ in rows if n == 0 and p == 0)
        print(f"  ({empty} of {n_kinds} entries are zero - vanilla articles stay hardcoded)")

    if args.item:
        it = md.item()
        print(f"== MexData.item @ data+0x{md.root['item']:X}")
        for i, name in enumerate(ITEM_FIELDS):
            v = it[name]
            if (v & 0xF0000000) == 0x80000000:
                kind = "absolute guest address (vanilla table)"
            elif ar.in_data(v):
                kind = "data offset (in-file table)"
            else:
                kind = "???"
            print(f"  +0x{i * 4:02X}  {name:<13} 0x{v:08X}  {kind}")

    if args.runtime_index:
        it = md.item()
        rows = md.item_lookup(lookup_off, n_kinds)
        all_ids = sorted({i for _, _, _, ids in rows for i in ids})
        derived = (max(all_ids) - CUSTOM_ITEM_START + 1) if all_ids else 0
        n = args.custom_item_count if args.custom_item_count else derived
        print(f"== custom item kinds {CUSTOM_ITEM_START}..{max(all_ids) if all_ids else '?'} "
              f"-> {derived} slots, derived from fighter.item_lookup (scanning {n})")

        off = it["RuntimeIndex"]
        if ar.in_data(off):
            words = [ar.u32(off + i * ITEM_RUNTIME_STRIDE) for i in range(n)]
            nonzero = [(CUSTOM_ITEM_START + i, w) for i, w in enumerate(words) if w]
            relocs = [i for i in range(n) if is_reloc(ar, off + i * ITEM_RUNTIME_STRIDE)]
            zrun = 0
            while off + zrun < ar.data_size and ar.data[off + zrun] == 0:
                zrun += 1
            print(f"== item.RuntimeIndex @ data+0x{off:X} (stride {ITEM_RUNTIME_STRIDE}): "
                  f"{len(nonzero)} non-zero of {n}, {len(relocs)} relocated; "
                  f"zero run from the table start = {zrun} bytes = {zrun // 4} words")
            if nonzero:
                print(f"   non-zero: {[(k, hex(w)) for k, w in nonzero[:16]]}")
            print(f"   -> {'SHIPS ZEROED (runtime-filled), as expected'if not nonzero else '*** NOT zeroed ***'}"
                  f"; the zero run is exactly {zrun // 4} words vs {derived} custom kinds "
                  f"({'exact match - pins the table length' if zrun // 4 == derived else 'MISMATCH'})")

        off = it["Custom"]
        if ar.in_data(off):
            print(f"== item.Custom @ data+0x{off:X} (stride 0x{ITEM_CUSTOM_STRIDE:X}, {n} entries, "
                  f"spans 0x{off:X}..0x{off + n * ITEM_CUSTOM_STRIDE:X})")
            pop = 0
            for i in range(n):
                e = off + i * ITEM_CUSTOM_STRIDE
                ws = [ar.u32(e + j * 4) for j in range(ITEM_CUSTOM_STRIDE // 4)]
                if not any(ws):
                    continue
                pop += 1
                nz = ", ".join(f"+0x{j * 4:02X}=0x{w:08X}" for j, w in enumerate(ws) if w)
                print(f"   kind {CUSTOM_ITEM_START + i:>3} (idx {i:>2}): {nz}")
            print(f"   -> {pop} of {n} entries ship POPULATED. item.Custom is NOT an all-zero "
                  f"runtime table (contrast RuntimeIndex).")

    if args.validate:
        print("== validation (independent of the mxdt.h field order)")
        ok = True

        # 1. fighter.names[k] must be a readable string; that pins the `names` slot.
        names_off = md.fighter_field("names")
        names = [ar.cstr(ar.u32(names_off + i * 4)) for i in range(n_kinds)]
        good = sum(1 for s in names if s and s.isprintable())
        print(f"  fighter.names @ data+0x{names_off:X}: {good}/{n_kinds} entries decode as "
              f"strings; [{args.kind}] = {names[args.kind]!r}")
        if good < n_kinds:
            ok = False

        # 2. fighter.pl_file[k] = { char *name; char *symbol; } - a second, independent name.
        pl_off = md.fighter_field("pl_file")
        pl_name = ar.cstr(ar.u32(pl_off + args.kind * 8))
        pl_sym = ar.cstr(ar.u32(pl_off + args.kind * 8 + 4))
        print(f"  fighter.pl_file[{args.kind}] @ data+0x{pl_off:X}: "
              f"file {pl_name!r} symbol {pl_sym!r}")

        # 2b. names[] and pl_file[] are NOT in the same index space. pl_file[0] is Mario
        # (internal kind 0) while names[0] is Captain Falcon (external/CSS id 0). Every array
        # in MexData.fighter must therefore be asked "internal or external?" individually;
        # mxdt.h's `indexed by ft_kind` comment on the whole struct is not true of `names`.
        if names[0] != "Mario" and (pl_sym or "").startswith("ftData"):
            print(f"    NOTE: names[0]={names[0]!r} but pl_file[0]="
                  f"{ar.cstr(ar.u32(pl_off))!r} -> `names` is indexed by EXTERNAL id, "
                  f"`pl_file` by INTERNAL kind. They are different index spaces.")
            if args.kind == SONIC_INTERNAL_KIND:
                ext = next((i for i, s in enumerate(names) if s == "Sonic"), None)
                print(f"    Sonic: internal kind {args.kind}, external id {ext} "
                      f"(names[{ext}] == 'Sonic')")

        # 3. Does that agree with what the port hardcodes for Sonic?
        if args.kind == SONIC_INTERNAL_KIND:
            want = ("PlSn.dat", "ftDataSonic")
            hit = (pl_name, pl_sym) == want
            print(f"    -> internal kind {SONIC_INTERNAL_KIND} is "
                  f"{'SONIC (confirmed: ' + str(want) + ')' if hit else 'NOT Sonic *** '}")
            if not hit:
                ok = False

        # 4. item_lookup, with the {count, ptr} stride proved by the relocation table.
        rows = md.item_lookup(lookup_off, n_kinds)
        cnt_reloc = sum(1 for k in range(n_kinds)
                        if is_reloc(ar, lookup_off + k * ITEM_LOOKUP_STRIDE))
        ptr_reloc = sum(1 for k in range(n_kinds)
                        if is_reloc(ar, lookup_off + k * ITEM_LOOKUP_STRIDE + 4))
        print(f"  fighter.item_lookup @ data+0x{lookup_off:X}: relocations land on "
              f"{cnt_reloc} +0 words and {ptr_reloc} +4 words "
              f"-> stride 8, pointer in the SECOND word ({'consistent' if cnt_reloc == 0 else '*** INCONSISTENT'})")
        if cnt_reloc != 0:
            ok = False
        k, n, ptr, ids = rows[args.kind]
        print(f"  item_lookup[{args.kind}] = count {n}, ids @ data+0x{ptr:X} -> {ids}")
        if args.kind == SONIC_INTERNAL_KIND:
            triple_ok = (n == 1 and ids == [277])
            print(f"    -> Sonic-is-kind-31 / 1-article / global-ItemKind-277 triple: "
                  f"{'REPRODUCED' if triple_ok else '*** NOT REPRODUCED ***'}")
            if not triple_ok:
                ok = False

        # 5. Every non-empty entry's ids must be >= CUSTOM_ITEM_START and contiguous per kind.
        bad = [(k, ids) for k, n, p, ids in rows
               if ids and (min(ids) < CUSTOM_ITEM_START or ids != list(range(ids[0], ids[0] + n)))]
        print(f"  all populated id arrays are contiguous and >= {CUSTOM_ITEM_START}: "
              f"{'yes' if not bad else '*** no: ' + str(bad)}")
        if bad:
            ok = False

        print(f"  RESULT: {'all checks passed' if ok else '*** AT LEAST ONE CHECK FAILED ***'}")
        if not ok:
            rc = 2
    return rc


if __name__ == "__main__":
    sys.exit(main())
