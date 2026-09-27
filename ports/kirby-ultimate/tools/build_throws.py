#!/usr/bin/env python3
"""Install Ultimate Kirby throw damage/knockback and release timing.

The Melee throw action, grabbed-victim animation and non-hitbox events remain
host behavior; those require dedicated native work separately.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

import build_side_b as side


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_IR = ROOT / "experiment/character-ir/instances/kirby.ultimate.ir.json"
DEFAULT_BASE = ROOT / "experiment/brawl-kirby/disc/PlKb.dat"
DEFAULT_MOD = ROOT / "_build/tmp/ultimate-kirby-mods/ultimate-kirby-movement"
ROWS = {247: "throwf", 248: "throwb", 249: "throwhi", 250: "throwlw"}


def source_throws(path: Path) -> dict[int, dict]:
    ir = json.loads(path.read_text(encoding="utf-8"))
    if ir.get("document_id") != "kirby.ultimate":
        raise ValueError("expected Ultimate Kirby IR")
    scripts = {entry["id"]: entry for entry in ir["behavior"]["scripts"]}
    result = {}
    for row, name in ROWS.items():
        script = scripts[f"script:kirby/{name}/game_{name}"]
        source = {}
        for event in script["events"]:
            if event["op"] != "throw.set":
                continue
            args = event.get("args", {}).get("arguments", [])
            if len(args) < 8:
                raise ValueError(f"incomplete Ultimate {name} ATTACK_ABS")
            if "_THROW" in args[1]:
                role = "throw"
            elif "_CATCH" in args[1]:
                role = "catch"
            else:
                raise ValueError(f"unknown Ultimate {name} absolute role {args[1]}")
            if role in source:
                raise ValueError(f"duplicate Ultimate {name} absolute role {role}")
            source[role] = {
                "damage": side.bounded_int(round(float(args[3])), "throw damage", 0x7FFFFF),
                "angle": side.bounded_int(int(args[4]), "throw angle", 0x1FF),
                "kbg": side.bounded_int(int(args[5]), "throw KBG", 0x1FF),
                "wdsk": side.bounded_int(int(args[6]), "throw WDSK", 0x1FF),
                "bkb": side.bounded_int(int(args[7]), "throw BKB", 0x1FF),
            }
        if set(source) != {"throw", "catch"}:
            raise ValueError(f"Ultimate {name} requires throw and catch absolutes")
        releases = [e["frame"] for e in script["events"]
                    if e["op"] == "throw.release" and e.get("frame") is not None]
        if name == "throwlw":
            # The IR marks commands after the source's Rust loop dynamic. Its
            # readable game function has an explicit release at frame 58.
            game_path = (ROOT / "experiment/tooling/ultimate/scripting/SSBU-Dumped-Scripts/"
                         "smashline/lua2cpp_kirby/kirby/ThrowLw.txt")
            game = game_path.read_text(encoding="utf-8").split(
                'unsafe extern "C" fn effect_throwlw', 1)[0]
            matches = re.findall(
                r"frame\(agent\.lua_state_agent, (\d+)\.0\);"
                r"(?:(?!frame\(agent\.lua_state_agent).)*?"
                r"macros::ATK_HIT_ABS\(agent, \*FIGHTER_ATTACK_ABSOLUTE_KIND_THROW",
                game, re.S)
            if not re.search(r"for _ in 0\.\.9\s*\{", game) or len(matches) != 1:
                raise ValueError("Ultimate down-throw release loop structure changed")
            releases = [int(matches[0])]
        if len(releases) != 1 or int(releases[0]) != releases[0]:
            raise ValueError(f"Ultimate {name} needs one static release frame")
        source["release_frame"] = int(releases[0])
        result[row] = source
    return result


def throw_words(archive: side.mex_hsd.Archive, row: int) -> list[tuple[int, list[int]]]:
    offset = side.script_pointer(archive, row)
    found = []
    for _ in range(1024):
        op, words = side.command_at(archive, offset)
        if op in (5, 6, 7):
            raise ValueError(f"throw row {row} uses unsupported script branch")
        if op == 34:
            found.append((offset, words))
        if op == 0:
            return found
        offset += 4 * len(words)
    raise ValueError(f"throw row {row} did not terminate")


def _replace(words: list[int], source: dict[str, int]) -> tuple[int, int, int]:
    w0, w1, w2 = words
    return (
        (w0 & ~0x7FFFFF) | source["damage"],
        (w1 & 0x1F) | (source["angle"] << 23) | (source["kbg"] << 14) | (source["wdsk"] << 5),
        (w2 & 0x7FFFFF) | (source["bkb"] << 23),
    )


def retime_script(events: list, source: dict) -> tuple[list[int], list[int]]:
    """Rebuild a linear host throw script with source release timing."""
    release = source["release_frame"]
    if sum(op == 20 for _, op, _, _ in events) != 1:
        raise ValueError("host throw script requires one release command")
    rewritten = []
    for order, (frame, op, words, relocs) in enumerate(events):
        if op == 34:
            role = {0: "throw", 1: "catch"}.get((words[0] >> 23) & 7)
            if role is None:
                raise ValueError("unexpected host throw absolute kind")
            words = list(_replace(words, source[role]))
        if op == 20 or (op == 16 and frame == 57 and release == 58):
            frame = release
        if op == 0:
            frame = max(frame, release + 1)
        rewritten.append((frame, order, words, relocs))
    rewritten.sort(key=lambda event: (event[0], event[1]))
    words_out, relocated, now = [], [], 0
    for frame, _, words, relocs in rewritten:
        if frame > now:
            words_out.append((2 << 26) | frame)
            now = frame
        start = len(words_out)
        words_out.extend(words)
        relocated.extend(start + index for index in relocs)
    if words_out[-1] != 0:
        raise ValueError("throw script must end")
    return words_out, relocated


def patch_archive(raw: bytes, sources: dict[int, dict]) -> tuple[bytes, list[int]]:
    archive = side.mex_hsd.Archive(raw)
    data = bytearray(archive.data)
    relocs = set(archive.reloc_offsets)
    changed = []
    for row, entries in sorted(sources.items()):
        found = throw_words(archive, row)
        if len(found) != 2:
            raise ValueError(f"throw row {row} has {len(found)} absolutes, expected two")
        touched = False
        seen = set()
        for offset, words in found:
            kind = (words[0] >> 23) & 7
            role = {0: "throw", 1: "catch"}.get(kind)
            if role is None or role in seen:
                raise ValueError(f"throw row {row} has invalid absolute kind {kind}")
            seen.add(role)
            replacement = _replace(words, entries[role])
            if tuple(words) != replacement:
                struct.pack_into(">3I", data, offset, *replacement)
                touched = True
        if seen != {"throw", "catch"}:
            raise ValueError(f"throw row {row} lacks throw/catch absolute")
        if row in (248, 250):
            script, script_relocs = retime_script(side.flatten(archive, row), entries)
            if side.linear_words(archive, row) != script:
                while len(data) % 0x20:
                    data.append(0)
                at = len(data)
                data.extend(struct.pack(">%dI" % len(script), *script))
                relocs.update(at + 4 * index for index in script_relocs)
                table = side.motion_table(archive)
                struct.pack_into(">I", data, table + row * 0x18 + 0xC, at)
                touched = True
        if touched:
            changed.append(row)
    if not changed:
        return raw, []
    relocations = sorted(relocs)
    body = (bytes(data) + b"".join(struct.pack(">I", offset) for offset in relocations)
            + archive.raw[archive.o_public:])
    header = (struct.pack(">5I", 0x20 + len(body), len(data), len(relocations),
                          archive.nb_public, archive.nb_extern) + archive.raw[0x14:0x20])
    return header + body, changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ir", type=Path, default=DEFAULT_IR)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--mod", type=Path, default=DEFAULT_MOD)
    args = parser.parse_args()
    sources = source_throws(args.ir)
    target = args.mod / "files/PlKb.dat"
    current = target.read_bytes() if target.is_file() else args.base.read_bytes()
    output, changed = patch_archive(current, sources)
    if changed or not target.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(output)
    manifest_path = args.mod / "source-manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["ultimate_throw_absolutes"] = {
            "ir_sha256": hashlib.sha256(args.ir.read_bytes()).hexdigest(),
            "rows": [{"row": row, "ultimate_script": f"script:kirby/{name}/game_{name}"}
                     for row, name in sorted(ROWS.items())],
            "scope": "absolute throw/catch damage, angle and knockback plus throw release frames; host status, victim motion, other ftcmd retained",
        }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Ultimate throw absolute rows {changed or 'already current'}: {target}")


if __name__ == "__main__":
    main()
