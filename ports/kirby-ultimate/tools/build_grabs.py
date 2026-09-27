#!/usr/bin/env python3
"""Stage Ultimate standing and dash grab active/clear windows on Kirby.

Melee's grab boxes, capture rules and status handlers are retained. The local
Ultimate IR has source grab boxes for standing, dash and pivot grabs, but
Melee Kirby has no pivot-grab action; that status needs separate native work.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

import build_side_b as side


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_IR = ROOT / "experiment/character-ir/instances/kirby.ultimate.ir.json"
DEFAULT_BASE = ROOT / "experiment/brawl-kirby/disc/PlKb.dat"
DEFAULT_MOD = ROOT / "_build/tmp/ultimate-kirby-mods/ultimate-kirby-movement"
ROWS = {242: "catch", 243: "catchdash"}


def source_grabs(path: Path) -> dict[int, dict[str, int]]:
    ir = json.loads(path.read_text(encoding="utf-8"))
    if ir.get("document_id") != "kirby.ultimate":
        raise ValueError("expected Ultimate Kirby IR")
    scripts = {entry["id"]: entry for entry in ir["behavior"]["scripts"]}
    result = {}
    for row, name in ROWS.items():
        script = scripts[f"script:kirby/{name}/game_{name}"]
        boxes = [e for e in script["events"] if e["op"] == "grab.box"]
        clears = [e for e in script["events"] if e["op"] == "engine.grab_clear_all"]
        if len(boxes) != 2 or len(clears) != 1:
            raise ValueError(f"Ultimate {name} grab structure changed")
        active = {e.get("frame") for e in boxes}
        if len(active) != 1 or None in active or clears[0].get("frame") is None:
            raise ValueError(f"Ultimate {name} needs static grab times")
        at, clear = int(next(iter(active))), int(clears[0]["frame"])
        if (clear != at + 2 or clears[0]["frame"] != clear
                or any(e["frame"] != at for e in boxes)):
            raise ValueError(f"Ultimate {name} grab window changed")
        result[row] = {"active": at, "clear": clear}
    return result


def retime_script(events: list, times: dict[str, int]) -> tuple[list[int], list[int]]:
    old_active = {frame for frame, op, _, _ in events if op == 11}
    old_clear = {frame for frame, op, _, _ in events if op == 16}
    if len(old_active) != 1 or len(old_clear) != 1:
        raise ValueError("host grab requires one active and one clear frame")
    current_active, current_clear = next(iter(old_active)), next(iter(old_clear))
    out_events = []
    for order, (frame, op, words, relocs) in enumerate(events):
        if op in (11, 34) and frame == current_active:
            frame = times["active"]
        elif op in (16, 20) and frame == current_clear:
            frame = times["clear"]
        elif op == 0:
            frame = max(frame, times["clear"] + 1)
        out_events.append((frame, order, words, relocs))
    out_events.sort(key=lambda event: (event[0], event[1]))
    words_out, relocated, now = [], [], 0
    for frame, _, words, relocs in out_events:
        if frame > now:
            words_out.append((2 << 26) | frame)
            now = frame
        start = len(words_out)
        words_out.extend(words)
        relocated.extend(start + index for index in relocs)
    if words_out[-1] != 0:
        raise ValueError("grab script must end")
    return words_out, relocated


def patch_archive(raw: bytes, sources: dict[int, dict[str, int]]) -> tuple[bytes, list[int]]:
    archive = side.mex_hsd.Archive(raw)
    data, relocs, changed = bytearray(archive.data), set(archive.reloc_offsets), []
    table = side.motion_table(archive)
    for row, times in sorted(sources.items()):
        events = side.flatten(archive, row)
        if ({frame for frame, op, _, _ in events if op == 11} == {times["active"]}
                and {frame for frame, op, _, _ in events if op == 16} == {times["clear"]}):
            continue
        script, script_relocs = retime_script(events, times)
        if side.linear_words(archive, row) == script:
            continue
        while len(data) % 0x20:
            data.append(0)
        at = len(data)
        data.extend(struct.pack(">%dI" % len(script), *script))
        relocs.update(at + 4 * index for index in script_relocs)
        struct.pack_into(">I", data, table + row * 0x18 + 0xC, at)
        changed.append(row)
    if not changed:
        return raw, []
    relocation_offsets = sorted(relocs)
    body = (bytes(data) + b"".join(struct.pack(">I", off) for off in relocation_offsets)
            + archive.raw[archive.o_public:])
    header = (struct.pack(">5I", 0x20 + len(body), len(data), len(relocation_offsets),
                          archive.nb_public, archive.nb_extern) + archive.raw[0x14:0x20])
    return header + body, changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ir", type=Path, default=DEFAULT_IR)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--mod", type=Path, default=DEFAULT_MOD)
    args = parser.parse_args()
    sources = source_grabs(args.ir)
    target = args.mod / "files/PlKb.dat"
    current = target.read_bytes() if target.is_file() else args.base.read_bytes()
    output, changed = patch_archive(current, sources)
    if changed or not target.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(output)
    manifest_path = args.mod / "source-manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["ultimate_grab_windows"] = {
            "ir_sha256": hashlib.sha256(args.ir.read_bytes()).hexdigest(),
            "rows": [{"row": row, "ultimate_script": f"script:kirby/{name}/game_{name}"}
                     for row, name in sorted(ROWS.items())],
            "scope": "standing/dash active and clear frames only; Melee capture boxes, status and pivot-grab absence remain",
        }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Ultimate grab window rows {changed or 'already current'}: {target}")


if __name__ == "__main__":
    main()
