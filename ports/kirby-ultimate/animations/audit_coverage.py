"""Count Ultimate clip coverage of Melee Kirby's native motion rows.

Suffix matches only locate candidates for review. They do not establish action
equivalence, timing, or a safe HSD substitution.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BUCKETS = (
    (0, 45, "movement and defense"),
    (46, 77, "attacks and landings"),
    (78, 164, "items"),
    (165, 215, "damage and recovery"),
    (216, 250, "ledge, grab and throw"),
    (251, 304, "capture and extra jumps"),
    (305, 337, "specials"),
)


def audit(root: Path) -> list[dict]:
    melee = json.loads((root / "experiment/brawl-kirby/analysis/melee_kirby.json").read_text())
    manifest = json.loads((root / "ports/kirby-ultimate/animations/manifest.json").read_text())
    ir = json.loads((root / "experiment/character-ir/instances/kirby.ultimate.ir.json").read_text())
    selected = {row for clip in manifest["clips"] for row in clip["melee_motion_rows"]}
    stems = {Path(clip["file"]).stem for clip in ir["assets"]["animations"]["clips"]
             if clip["id"].startswith("clip:motion.body.c00.")}
    result = []
    for lo, hi, label in BUCKETS:
        rows = []
        for row in melee["motion_table"]:
            if not lo <= row["index"] <= hi or not row.get("figatree"):
                continue
            candidates = sorted(stem for stem in stems if stem.endswith(row["name"].lower()))
            rows.append({"index": row["index"], "name": row["name"],
                         "mapped": row["index"] in selected, "candidates": candidates})
        result.append({"name": label, "rows": rows})
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--list-missing", action="store_true")
    args = parser.parse_args()
    buckets = audit(args.root)
    mapped = sum(row["mapped"] for bucket in buckets for row in bucket["rows"])
    total = sum(len(bucket["rows"]) for bucket in buckets)
    print(f"Kirby native motion rows 0..337: {mapped}/{total} mapped to Ultimate c00 clips")
    for bucket in buckets:
        rows = bucket["rows"]
        covered = sum(row["mapped"] for row in rows)
        possible = sum(not row["mapped"] and bool(row["candidates"]) for row in rows)
        print(f"{bucket['name']}: {covered}/{len(rows)} mapped, {possible} suffix candidates")
        if args.list_missing:
            for row in rows:
                if not row["mapped"]:
                    print(f"  {row['index']:3} {row['name']:26} "
                          f"{','.join(row['candidates'][:5]) or '-'}")


if __name__ == "__main__":
    main()
