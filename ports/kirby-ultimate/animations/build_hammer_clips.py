"""Build native Ultimate Hammer body clips for extended Melee Kirby motion rows.

These row numbers are reserved by the additive Ultimate Kirby slot. The source
NUANMB bytes stay in the private extraction; only generated HSD archives go in
the ignored build directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

import yaml

import convert_world as world


ROOT = Path(__file__).resolve().parents[3]
# row, public symbol suffix, Ultimate c00 clip, stock root template
HAMMER = (
    (479, "HammerHold", "d01specialshold", "Wait1"),
    (480, "HammerWalk", "d01specialswalk", "WalkMiddle"),
    (481, "HammerMax", "d01specialsmax", "SpecialS"),
    (482, "HammerAirStart", "d01specialairsstart", "SpecialAirS"),
    (483, "HammerAirMax", "d01specialairsmax", "SpecialAirS"),
    (484, "HammerStart", "d01specialsstart", "SpecialS"),
    (485, "HammerHoldMax", "d01specialsholdmax", "Wait1"),
    (486, "HammerTurn", "d01specialsturn", "Turn"),
    (487, "HammerJump", "d01specialsjump", "JumpF"),
    (488, "HammerJumpSquat", "d01specialsjumpsquat", "JumpF"),
)


def _motion_bindings(root: Path) -> tuple[str, dict[str, list[dict]]]:
    motion = root / "experiment/tooling/ultimate/workspace/extracted/fighter/kirby/motion/body/c00/motion_list.bin"
    yamlist = root / "experiment/tooling/ultimate/apps/yamlist/yamlist.exe"
    labels = root / "experiment/tooling/ultimate/references/motion-labels.txt"
    with tempfile.TemporaryDirectory(prefix="kirby-hammer-motion-") as temp:
        target = Path(temp) / "motion.yml"
        subprocess.run([str(yamlist), "-l", str(labels), "-o", str(target),
                        "disasm", str(motion)], check=True, capture_output=True, text=True)
        entries = yaml.safe_load(target.read_text(encoding="utf-8"))["list"]
    bindings: dict[str, list[dict]] = {}
    for status, entry in entries.items():
        for animation in entry.get("animations", []):
            bindings.setdefault(animation["name"], []).append({
                "status": status,
                "loop": entry.get("flags", {}).get("loop"),
                "move": entry.get("flags", {}).get("move"),
                "blend_frames": entry.get("blend_frames"),
            })
    return hashlib.sha256(motion.read_bytes()).hexdigest(), bindings


def build(root: Path, out: Path) -> dict:
    ir_path = root / "experiment/character-ir/instances/kirby.ultimate.ir.json"
    ir = json.loads(ir_path.read_text(encoding="utf-8"))
    ir_clips = {clip["id"]: clip for clip in ir["assets"]["animations"]["clips"]}
    motion_hash, bindings = _motion_bindings(root)
    decoder = root / "experiment/tooling/ultimate/apps/SSBH-JSON/ssbh_data_json.exe"
    source_dir = root / "experiment/tooling/ultimate/workspace/extracted/fighter/kirby/motion/body/c00"
    skeleton_path = root / "experiment/tooling/ultimate/workspace/extracted/fighter/kirby/model/body/c00/model.nusktb"
    joints = json.loads((root / "experiment/brawl-kirby/analysis/melee_model.json").read_text())["PlKbNr.dat"]["joints"]
    _, archives = world.local.melee_anim.melee_aj()
    report = {
        "source_ir": ir_path.relative_to(root).as_posix(),
        "ultimate_motion_list_sha256": motion_hash,
        "mesh_bind_policy": "source-world-scaled",
        "root_policy": "remove Ultimate Trans travel; use named stock action root template",
        "animations": [],
    }
    with tempfile.TemporaryDirectory(prefix="kirby-hammer-build-") as temp:
        temp = Path(temp)
        skeleton = world.local.decode(decoder, skeleton_path, temp / "skeleton.json")
        for row, name, stem, root_template in HAMMER:
            source = source_dir / f"{stem}.nuanmb"
            clip_id = f"clip:motion.body.c00.{stem}"
            record = ir_clips[clip_id]
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            if source.stat().st_size != record["size"] or not record.get("frames"):
                raise ValueError(f"IR metadata mismatch: {clip_id}")
            statuses = bindings.get(source.name, [])
            if not statuses:
                raise ValueError(f"Ultimate motion_list has no binding for {source.name}")
            anim = world.local.decode(decoder, source, temp / "animation.json")
            if round(anim["final_frame_index"]) != round(record["frames"]):
                raise ValueError(f"IR frame count mismatch: {clip_id}")
            symbol = f"PlyKirby5K_Share_ACTION_{name}_figatree"
            stock_symbol = f"PlyKirby5K_Share_ACTION_{root_template}_figatree"
            raw, detail = world.convert_clip(anim, skeleton, joints, symbol, row,
                                             archives[stock_symbol][2],
                                             bind_policy="source-world-scaled")
            relative = Path("clips") / f"{row:03d}-{name}.dat"
            target = out / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            report["animations"].append({
                "row": row, "file": relative.as_posix(), "symbol": symbol,
                "ultimate_clip_id": clip_id,
                "ultimate_file": source.relative_to(root).as_posix(),
                "ultimate_sha256": digest,
                "ultimate_motion_entries": statuses,
                "stock_root_template": root_template,
                "sha256": hashlib.sha256(raw).hexdigest(),
                **detail,
            })
    out.mkdir(parents=True, exist_ok=True)
    (out / "install-manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path,
                        default=ROOT / "_build/tmp/ultimate-kirby-hammer-clips")
    args = parser.parse_args()
    result = build(args.root, args.out)
    print(f"built {len(result['animations'])} native Hammer clips at {args.out}")


if __name__ == "__main__":
    main()
