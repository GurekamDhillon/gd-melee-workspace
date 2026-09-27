#!/usr/bin/env python3
"""Expand ACE m-ex fighter tables for an additional Ultimate Kirby row.

The PC host has 94 m-ex slots, but ACE's MxDt.dat has 65 fighter rows. Row 59
is where its six boss internal rows begin. Insert the new fighter there, move
those six rows by one, and append external row 65 so existing selectable
fighters keep their names, menus, and data. This pass changes only MxDt.dat;
the companion PlCo and menu atlases are handled separately.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import shutil
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/mex_port"))
from mex_hsd import Archive  # noqa: E402
sys.path.insert(0, str(ROOT / "experiment/brawl-kirby/tools"))
import texanim_keys  # noqa: E402

COLORS = ("Nr", "Ye", "Bu", "Re", "Gr", "Wh", "Or", "Bk")
OLD_COUNT = 65
NEW_COUNT = 66
NEW_INTERNAL = 59
NEW_EXTERNAL = 65

# MexData.fighter's 33 arrays, in mxdt.h order. m-ex's accessor sites use
# internal IDs for fighter assets/state and external IDs for menus/results.
FIGHTER_SPACES = (
    "e", "i", "e", "e", "e", "i", "i", "i", "i", "i", "e",
    "e", "e", "e", "e", "i", "i", "i", "i", "i", "e", "e",
    "e", "e", "e", "e", "e", "e", "i", "i", "e", "e", "e",
)


def _u32(data: bytes | bytearray, at: int) -> int:
    return struct.unpack_from(">I", data, at)[0]


def _put(data: bytearray, at: int, value: int) -> None:
    struct.pack_into(">I", data, at, value)


def _pack(ar: Archive, data: bytearray, relocs: set[int]) -> bytes:
    while len(data) % 4:
        data.append(0)
    entries = sorted(relocs)
    body = bytes(data) + b"".join(struct.pack(">I", at) for at in entries) + ar.raw[ar.o_public:]
    header = (struct.pack(">5I", 0x20 + len(body), len(data), len(entries), ar.nb_public,
                          ar.nb_extern) + ar.raw[0x14:0x20])
    return header + body


def expand_mxdt(raw: bytes, icon_joint: int, anim_count: int = 479) -> bytes:
    ar = Archive(raw)
    data = bytearray(ar.data)
    relocs = set(ar.reloc_offsets)
    root = ar.public("mexData")
    meta, menu, fighter, funcs, kirby_data, kirby_funcs = (
        _u32(data, root + offset) for offset in (0, 4, 8, 12, 32, 36)
    )
    if struct.unpack_from(">ii", data, meta + 4) != (OLD_COUNT, OLD_COUNT):
        raise ValueError("additive slot needs ACE's 65/65 m-ex fighter tables")
    if not 1 <= icon_joint < 128:
        raise ValueError("new CSS icon joint must fit the menu model")

    targets = sorted({_u32(data, at) for at in relocs} | {len(data)})

    def append(payload: bytes | bytearray, alignment: int = 4) -> int:
        while len(data) % alignment:
            data.append(0)
        at = len(data)
        data.extend(payload)
        return at

    def string(value: str) -> int:
        return append(value.encode("ascii") + b"\0", 1)

    def stretch(pointer_at: int, space: str) -> int:
        if pointer_at not in relocs:
            return 0
        old = _u32(data, pointer_at)
        if old == 0:
            return 0
        span = targets[bisect.bisect_right(targets, old)] - old
        stride = span // OLD_COUNT
        if stride < 1 or span - stride * OLD_COUNT >= 4:
            raise ValueError(f"m-ex table at 0x{old:X} has uncertain span {span}")
        if stride >= 4 and stride % 4:
            raise ValueError(f"m-ex pointer table at 0x{old:X} has odd stride {stride}")
        if space == "i":
            source_rows = list(range(NEW_INTERNAL)) + [4] + list(range(NEW_INTERNAL, OLD_COUNT))
        else:
            source_rows = list(range(OLD_COUNT)) + [4]
        at = append(b"".join(data[old + source * stride:old + (source + 1) * stride]
                             for source in source_rows))
        if stride >= 4:
            for dest, source in enumerate(source_rows):
                for offset in range(0, stride, 4):
                    if old + source * stride + offset in relocs:
                        relocs.add(at + dest * stride + offset)
        _put(data, pointer_at, at)
        return at

    if len(FIGHTER_SPACES) != 33:
        raise AssertionError("fighter field inventory changed")
    fields = [stretch(fighter + 4 * i, space) for i, space in enumerate(FIGHTER_SPACES)]
    counts = fields[8]
    if anim_count not in (479, 480, 489) or _u32(data, counts + 8 * 4 + 4) != 479:
        raise ValueError("additive slot requires Kirby's 479-row baseline")
    _put(data, counts + 8 * NEW_INTERNAL + 4, anim_count)
    # fighter_function is 64 pointers to per-internal arrays (two have stride
    # eight); kirby_data's six populated fields and kirby_function's nine are
    # also per-internal arrays.
    for i in range(64):
        stretch(funcs + 4 * i, "i")
    for i in range(6):
        stretch(kirby_data + 4 * i, "i")
    for i in range(9):
        stretch(kirby_funcs + 4 * i, "i")

    names, pl_file, _, desc, info, costume_file = fields[:6]
    anim_file = fields[7]
    _put(data, names + 4 * NEW_EXTERNAL, string("Ultimate Kirby"))
    relocs.add(names + 4 * NEW_EXTERNAL)
    _put(data, pl_file + 8 * NEW_INTERNAL, string("PlUk.dat"))
    relocs.add(pl_file + 8 * NEW_INTERNAL)
    _put(data, anim_file + 4 * NEW_INTERNAL, string("PlUkAJ.dat"))
    relocs.add(anim_file + 4 * NEW_INTERNAL)

    # Existing external rows remain at the same index; their boss internal IDs
    # advance by one. The new row starts from Kirby's clone flags.
    for e in range(OLD_COUNT):
        old_kind = data[desc + 3 * e]
        if NEW_INTERNAL <= old_kind < OLD_COUNT:
            data[desc + 3 * e] = old_kind + 1
    data[desc + 3 * NEW_EXTERNAL] = NEW_INTERNAL
    data[info + 4 * NEW_EXTERNAL] = len(COLORS)

    rows = bytearray()
    for index, color in enumerate(COLORS):
        stem = "PlyKirby5K" + (color if 1 <= index <= 5 else "") + "_Share"
        row_at = len(rows)
        rows.extend(struct.pack(">4I", string(f"PlUk{color}.dat"),
                                string(stem + "_joint"),
                                string(stem + "_matanim_joint"),
                                index if index < 6 else index - 6))
        assert len(rows) == row_at + 16
    costume_rows = append(rows)
    for index in range(len(COLORS)):
        relocs.update(costume_rows + 16 * index + offset for offset in (0, 4, 8))
    _put(data, costume_file + 4 * NEW_INTERNAL, costume_rows)
    relocs.add(costume_file + 4 * NEW_INTERNAL)

    css = _u32(data, menu + 4)
    n_icons = _u32(data, meta + 12)
    row_size = 0x1C
    rows_at = css + 0xDC
    icons = [bytearray(data[rows_at + i * row_size:rows_at + (i + 1) * row_size])
             for i in range(n_icons)]
    kirby = next((row for row in icons if row[1] == 4), None)
    if kirby is None or not any(row[1] == 30 for row in icons):
        raise ValueError("ACE CSS is missing Kirby or Sonic icon")
    new_icon = bytearray(kirby)
    new_icon[1] = NEW_EXTERNAL
    new_icon[4] = new_icon[5] = icon_joint
    struct.pack_into(">4f", new_icon, 0xC, -32.98, -27.91, 4.62, -0.06)
    sonic = next(i for i, row in enumerate(icons) if row[1] == 30)
    icons.insert(sonic, new_icon)
    css_block = data[css:rows_at] + b"".join(icons) + data[rows_at + n_icons * row_size:
                                                           rows_at + (n_icons + 1) * row_size]
    _put(data, menu + 4, append(css_block, 0x20))
    struct.pack_into(">iii", data, meta + 4, NEW_COUNT, NEW_COUNT, n_icons + 1)

    result = _pack(ar, data, relocs)
    check = Archive(result)
    check_meta = check.u32(check.public("mexData"))
    if struct.unpack_from(">ii", check.data, check_meta + 4) != (NEW_COUNT, NEW_COUNT):
        raise ValueError("expanded MxDt did not round-trip")
    return result


def expand_plco(raw: bytes) -> bytes:
    ar = Archive(raw)
    data = bytearray(ar.data)
    relocs = set(ar.reloc_offsets)
    root = ar.public("ftLoadCommonData")
    source_rows = list(range(NEW_INTERNAL)) + [4] + list(range(NEW_INTERNAL, OLD_COUNT))
    for field in (4, 5):
        pointer_at = root + 4 * field
        if pointer_at not in relocs:
            raise ValueError("PlCo kind table is not a relocated pointer")
        old = _u32(data, pointer_at)
        if old + OLD_COUNT * 4 > len(ar.data):
            raise ValueError("PlCo kind table is too short")
        while len(data) % 4:
            data.append(0)
        at = len(data)
        for index, source in enumerate(source_rows):
            data.extend(ar.data[old + 4 * source:old + 4 * (source + 1)])
            if old + 4 * source in ar.reloc_set:
                relocs.add(at + 4 * index)
        _put(data, pointer_at, at)
    result = _pack(ar, data, relocs)
    Archive(result).public("ftLoadCommonData")
    return result


def expand_menu(raw: bytes) -> tuple[bytes, int]:
    ar = Archive(raw)
    data = bytearray(ar.data)
    relocs = set(ar.reloc_offsets)
    root = ar.public("mexSelectChr")

    def clone(node: int, size: int, next_offset: int) -> int:
        while len(data) % 0x20:
            data.append(0)
        at = len(data)
        data.extend(data[node:node + size])
        for offset in range(0, size, 4):
            if node + offset in relocs:
                relocs.add(at + offset)
        _put(data, at + next_offset, 0)
        relocs.discard(at + next_offset)
        return at

    new_joint = None
    for field, child_offset, next_offset, size in ((0, 8, 0xC, 0x40),
                                                    (4, 0, 4, 0x14),
                                                    (8, 0, 4, 0xC)):
        parent = _u32(data, root + field)
        node = _u32(data, parent + child_offset)
        chain = []
        while node:
            chain.append(node)
            node = _u32(data, node + next_offset)
            if len(chain) > 127:
                raise ValueError("CSS icon joint chain is unexpectedly long")
        if len(chain) < 20:
            raise ValueError("CSS icon joint chain has no Kirby icon")
        new = clone(chain[19], size, next_offset)
        _put(data, chain[-1] + next_offset, new)
        relocs.add(chain[-1] + next_offset)
        index = len(chain) + 1
        if new_joint is not None and index != new_joint:
            raise ValueError("CSS icon chains disagree on their new joint index")
        new_joint = index

    csp_joint = _u32(data, root + 0xC)
    texanim = _u32(data, csp_joint + 8)
    if _u32(data, root + 0x10) != OLD_COUNT:
        raise ValueError("ACE CSP atlas stride is not 65")
    _resample_texanim(data, texanim, 0, "e")
    _put(data, root + 0x10, NEW_COUNT)
    result = _pack(ar, data, relocs)
    Archive(result).public("mexSelectChr")
    return result, int(new_joint)


def expand_stock(raw: bytes) -> bytes:
    ar = Archive(raw)
    data = bytearray(ar.data)
    relocs = set(ar.reloc_offsets)
    root = ar.public("Stc_icns")
    reserved, stride = struct.unpack_from(">HH", data, root)
    if (reserved, stride) != (8, OLD_COUNT):
        raise ValueError("ACE stock-icon atlas layout changed")
    texanim = _u32(data, _u32(data, _u32(data, root + 4) + 8) + 8)
    _resample_texanim(data, texanim, reserved, "i")
    struct.pack_into(">H", data, root + 2, NEW_COUNT)
    result = _pack(ar, data, relocs)
    Archive(result).public("Stc_icns")
    return result


def _resample_texanim(data: bytearray, texanim: int, reserved: int, space: str) -> None:
    """Reindex eight constant-key costume atlases from stride 65 to 66."""
    aobj = _u32(data, texanim + 8)
    old_end = struct.unpack_from(">f", data, aobj + 4)[0]
    if old_end < reserved + 8 * OLD_COUNT:
        raise ValueError("costume atlas animation ends before its eighth color")
    fobj = _u32(data, aobj + 8)
    while fobj:
        next_fobj = _u32(data, fobj)
        keys = texanim_keys._decode(data, fobj)
        times = [key[0] for key in keys]

        def old_value(frame: int) -> tuple[int, bytes]:
            index = bisect.bisect_right(times, frame) - 1
            if index < 0:
                raise ValueError("costume atlas lacks an initial texture key")
            return keys[index][1], keys[index][2]

        def source_frame(frame: int) -> int:
            if frame < reserved:
                return frame
            offset = frame - reserved
            color, fighter = divmod(offset, NEW_COUNT)
            if color >= 8:
                return frame - 8
            if space == "e":
                source = fighter if fighter < OLD_COUNT else 4
            else:
                source = fighter if fighter < NEW_INTERNAL else (
                    4 if fighter == NEW_INTERNAL else fighter - 1)
            return reserved + color * OLD_COUNT + source

        last: tuple[int, bytes] | None = None
        out = bytearray()
        changed: list[tuple[int, int, bytes]] = []
        for frame in range(int(old_end) + 8):
            value = old_value(source_frame(frame))
            if value != last:
                changed.append((frame, *value))
                last = value
        for index, (frame, op, value) in enumerate(changed):
            out.append(op)
            out.extend(value)
            if index + 1 < len(changed):
                out.extend(texanim_keys._varint(changed[index + 1][0] - frame))
        while len(data) % 4:
            data.append(0)
        at = len(data)
        data.extend(out)
        _put(data, fobj + 4, len(out))
        _put(data, fobj + 16, at)
        fobj = next_fobj
    struct.pack_into(">f", data, aobj + 4, old_end + 8)


def build(source_mod: Path, base_files: Path, output: Path,
          costumes: list[Path]) -> dict:
    if len(costumes) != len(COLORS):
        raise ValueError("the additive slot needs eight costume archives")
    for index, path in enumerate(costumes):
        ar = Archive(path.read_bytes())
        stem = "PlyKirby5K" + (COLORS[index] if 1 <= index <= 5 else "") + "_Share"
        ar.public(stem + "_joint")
        ar.public(stem + "_matanim_joint")
    source_files = source_mod / "files"
    fighter = (source_files / "PlKb.dat").read_bytes()
    animation = (source_files / "PlKbAJ.dat").read_bytes()
    Archive(fighter).public("ftDataKirby")
    if not animation:
        raise ValueError("the additive slot needs a nonempty Kirby AJ archive")
    anim_count = 479
    hammer = source_mod / "hammer-visuals.json"
    hammer_marker = None
    if hammer.is_file():
        marker = json.loads(hammer.read_text(encoding="utf-8"))
        ar = Archive(fighter)
        table = ar.u32(ar.public("ftDataKirby") + 0xC)
        if (marker.get("rows") != list(range(479, 489)) or
                marker.get("motion_count") != 489 or
                marker.get("fighter_sha256") != hashlib.sha256(fighter).hexdigest() or
                marker.get("animation_sha256") != hashlib.sha256(animation).hexdigest() or
                table + 489 * 0x18 > ar.data_size):
            raise ValueError("Hammer marker does not match the source motion table")
        for row in range(479, 489):
            field = table + row * 0x18
            if (field not in ar.reloc_set or field + 0xC not in ar.reloc_set or
                    ar.u32(field + 4) + ar.u32(field + 8) > len(animation)):
                raise ValueError(f"Hammer row {row} is not installed")
        anim_count = 489
        hammer_marker = marker
    pivot = source_mod / "pivot-grab.json"
    pivot_marker = None
    if pivot.is_file():
        if hammer_marker is not None:
            raise ValueError("pivot and Hammer motion extensions both claim row479")
        marker = json.loads(pivot.read_text(encoding="utf-8"))
        ar = Archive(fighter)
        table = ar.u32(ar.public("ftDataKirby") + 0xC)
        row = table + 479 * 0x18
        if (marker.get("row") != 479 or
                marker.get("fighter_sha256") != hashlib.sha256(fighter).hexdigest() or
                marker.get("animation_sha256") != hashlib.sha256(animation).hexdigest() or
                row + 0x18 > ar.data_size or row not in ar.reloc_set or
                bytes(ar.data[ar.u32(row):]).split(b"\0", 1)[0] !=
                b"PlyKirby5K_Share_ACTION_CatchTurn_figatree" or
                ar.u32(row + 4) + ar.u32(row + 8) > len(animation)):
            raise ValueError("pivot marker does not match the source fighter and AJ row479")
        anim_count = 480
        pivot_marker = marker
    if output.resolve() == source_mod.resolve() or (output.exists() and any(output.iterdir())):
        raise ValueError("additive slot output must be a new separate directory")

    menu, icon_joint = expand_menu((base_files / "MnSlChr.usd").read_bytes())
    mxdt = expand_mxdt((base_files / "MxDt.dat").read_bytes(), icon_joint, anim_count)
    plco = expand_plco((base_files / "PlCo.dat").read_bytes())
    stock = expand_stock((base_files / "IfAll.usd").read_bytes())

    files = output / "files"
    files.mkdir(parents=True, exist_ok=True)
    for name, payload in (("MxDt.dat", mxdt), ("PlCo.dat", plco),
                          ("MnSlChr.usd", menu), ("IfAll.usd", stock),
                          ("PlUk.dat", fighter), ("PlUkAJ.dat", animation)):
        (files / name).write_bytes(payload)
    for index, color in enumerate(COLORS):
        shutil.copyfile(costumes[index], files / f"PlUk{color}.dat")

    profile = json.loads((source_mod / "geno.json").read_text(encoding="utf-8"))
    entries = profile.get("fighters", [])
    if len(entries) != 1 or entries[0].get("attach") not in ("kirby", "PlKb.dat"):
        raise ValueError("source Geno profile must attach exactly one Kirby fighter")
    entries[0]["attach"] = "PlUk.dat"
    entries[0]["name"] = "Ultimate Kirby"
    (output / "geno.json").write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
    (output / "mod.json").write_text(json.dumps({
        "id": "ultimate-kirby-additive-slot", "name": "Ultimate Kirby", "version": "0.1.0",
        "kind": "fighter",
        "description": ("Adds Ultimate Kirby at m-ex internal 59 / external 65; keeps all "
                        "existing fighter rows and shifts six boss internals to 60..65. "
                        "Requires the PC host's expanded 94-slot m-ex runtime."),
        "requires": [], "conflicts": ["ultimate-kirby-slot"],
    }, indent=2) + "\n", encoding="utf-8")

    sha = lambda payload: hashlib.sha256(payload).hexdigest()
    report = {
        "mode": "additive", "internal": NEW_INTERNAL, "external": NEW_EXTERNAL,
        "replaces": None, "pl": "PlUk.dat", "aj": "PlUkAJ.dat",
        "anim_count": anim_count,
        "css_icon_joint": icon_joint, "fighter_sha256": sha(fighter),
        "animation_sha256": sha(animation),
        "source_mod": str(source_mod.resolve()), "base_files": str(base_files.resolve()),
        "costumes": [f"PlUk{color}.dat" for color in COLORS],
        "costume_sources": [
            {"index": index, "source": str(path.resolve()), "sha256": sha(path.read_bytes())}
            for index, path in enumerate(costumes)
        ],
    }
    if pivot_marker is not None:
        report["pivot_grab"] = pivot_marker
        (output / "pivot-grab.json").write_text(
            json.dumps(pivot_marker, indent=2) + "\n", encoding="utf-8")
    if hammer_marker is not None:
        report["hammer_visuals"] = hammer_marker
        (output / "hammer-visuals.json").write_text(
            json.dumps(hammer_marker, indent=2) + "\n", encoding="utf-8")
    (output / "slot-build.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    source_manifest = source_mod / "source-manifest.json"
    if source_manifest.is_file():
        provenance = json.loads(source_manifest.read_text(encoding="utf-8"))
        provenance["m_ex_slot"] = {key: report[key] for key in
                                   ("mode", "internal", "external", "replaces", "pl", "aj",
                                    "costume_sources")}
        if pivot_marker is not None:
            provenance["pivot_grab"] = pivot_marker
        if hammer_marker is not None:
            provenance["hammer_visuals"] = hammer_marker
        (output / "source-manifest.json").write_text(
            json.dumps(provenance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-mod", type=Path, required=True)
    parser.add_argument("--base-files", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--costume", action="append", required=True,
                        help="INDEX:PATH; supply indices 0..7")
    args = parser.parse_args()
    # The Brawl tooling path above also has a build_slot.py. Resolve the
    # sibling native-slot parser rather than importing that unrelated CLI.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from build_slot import parse_costumes  # same symbol validation and ordering
    report = build(args.source_mod, args.base_files, args.out, parse_costumes(args.costume))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
