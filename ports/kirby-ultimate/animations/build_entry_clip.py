"""Build Ultimate Kirby's 120-frame Warp Star arrival body animation.

This is an isolated candidate for additive motion row 489. The companion Warp
Star model/animation and a dedicated host entry route are required in game.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile

import build_hammer_clips as hammer
import convert_world as world


ROOT = Path(__file__).resolve().parents[3]
ROW = 489
NAME = "UltimateEntry"
STEM = "j00entryr"


def build(root: Path, out: Path) -> dict:
    ir_path = root / "experiment/character-ir/instances/kirby.ultimate.ir.json"
    ir = json.loads(ir_path.read_text(encoding="utf-8"))
    clip_id = f"clip:motion.body.c00.{STEM}"
    record = next(item for item in ir["assets"]["animations"]["clips"]
                  if item["id"] == clip_id)
    source = root / f"experiment/tooling/ultimate/workspace/extracted/fighter/kirby/motion/body/c00/{STEM}.nuanmb"
    motion_hash, bindings = hammer._motion_bindings(root)
    statuses = bindings.get(source.name, [])
    if not statuses or source.stat().st_size != record["size"]:
        raise ValueError("Ultimate entry source does not match IR/motion_list")
    decoder = root / "experiment/tooling/ultimate/apps/SSBH-JSON/ssbh_data_json.exe"
    skeleton_path = root / "experiment/tooling/ultimate/workspace/extracted/fighter/kirby/model/body/c00/model.nusktb"
    joints = json.loads((root / "experiment/brawl-kirby/analysis/melee_model.json").read_text())["PlKbNr.dat"]["joints"]
    with tempfile.TemporaryDirectory(prefix="kirby-entry-build-") as temp:
        temp = Path(temp)
        skeleton = world.local.decode(decoder, skeleton_path, temp / "skeleton.json")
        anim = world.local.decode(decoder, source, temp / "animation.json")
        if round(anim["final_frame_index"]) != round(record["frames"]):
            raise ValueError("Ultimate entry duration differs from IR")
        symbol = f"PlyKirby5K_Share_ACTION_{NAME}_figatree"
        raw, detail = world.convert_clip(anim, skeleton, joints, symbol, ROW,
                                         bind_policy="source-world-scaled",
                                         source_root=True)
    relative = Path("clips") / f"{ROW}-{NAME}.dat"
    target = out / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    result = {
        "source_ir": ir_path.relative_to(root).as_posix(),
        "ultimate_motion_list_sha256": motion_hash,
        "mesh_bind_policy": "source-world-scaled",
        "animations": [{
            "row": ROW, "file": relative.as_posix(), "symbol": symbol,
            "ultimate_clip_id": clip_id,
            "ultimate_file": source.relative_to(root).as_posix(),
            "ultimate_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "ultimate_motion_entries": statuses,
            "companion_article_motion": "fighter/kirby/motion/warpstar/c00/j00entry.nuanmb",
            "sha256": hashlib.sha256(raw).hexdigest(),
            **detail,
        }],
    }
    (out / "install-manifest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path,
                        default=ROOT / "_build/tmp/ultimate-kirby-entry-clip")
    args = parser.parse_args()
    result = build(args.root, args.out)
    clip = result["animations"][0]
    print(f"built row {ROW} {clip['frames']}f ({clip['bytes']}B) at {args.out}")


if __name__ == "__main__":
    main()
