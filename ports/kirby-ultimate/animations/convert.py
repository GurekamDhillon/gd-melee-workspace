"""Experimental Ultimate Kirby NUANMB -> Melee Kirby HSD FigaTree retarget.

Run only against the ignored local Ultimate extraction. Outputs are derived game
assets and must stay under an ignored build directory. The retarget uses matched
body joints and local rest-pose deltas; facial deformation is not yet mapped.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import warnings

import numpy as np
from scipy.spatial.transform import Rotation


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experiment/brawl-kirby/tools/anim"))
import figatree as F
import anim_common as melee_anim


# Melee Kirby's DFS joint index -> Ultimate c00 body bone. The mapping excludes
# extra Melee helpers and facial parts where the two hierarchies differ. It is
# intentionally conservative: a plausible but wrong joint is worse than rest.
BONE_MAP = {
    1: "Trans", 2: "Rot", 4: "Hip", 5: "Waist", 6: "Body",
    7: "Head", 8: "Mouth1", 9: "Cheek", 10: "Puff",
    22: "ClavicleL", 24: "ShoulderL", 25: "ArmL", 26: "HandL",
    27: "ClavicleR", 29: "ShoulderR", 30: "ArmR", 31: "HandR",
    33: "LegL", 34: "KneeL", 36: "FootL", 37: "ToeL",
    39: "LegR", 40: "KneeR", 42: "FootR", 43: "ToeR", 44: "Throw",
}

TRACK_TYPE = {"rotation": (1, 2, 3), "translation": (5, 6, 7), "scale": (8, 9, 10)}
TOLERANCE = {"rotation": 0.003, "translation": 0.003, "scale": 0.002}
TRANSLATION_SCALE = 5.0 / 4.6  # Melee XRot height / Ultimate Rot bind height.


def decode(decoder: Path, source: Path, target: Path) -> dict:
    result = subprocess.run([str(decoder), str(source), str(target)],
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"SSBH decode failed: {source}: {result.stderr[-500:]}")
    return json.loads(target.read_text(encoding="utf-8"))


def _rotation(q: dict) -> Rotation:
    return Rotation.from_quat([q[k] for k in ("x", "y", "z", "w")])


def _continuous_euler(rotations: list[Rotation], reference: np.ndarray) -> np.ndarray:
    """Choose equivalent XYZ angles nearest the previous pose each frame.

    `np.unwrap` alone only adjusts each axis by 2π. Near gimbal lock the other
    equivalent XYZ branch can be much closer; ignoring it made Kirby's jump
    hand accumulate more than two spurious revolutions.
    """
    previous = np.asarray(reference, dtype=float)
    out = []
    tau = 2 * math.pi
    for rotation in rotations:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            base = rotation.as_euler("xyz")
        branches = (base, np.asarray((base[0] + math.pi, math.pi - base[1], base[2] + math.pi)))
        candidates = [branch + tau * np.round((previous - branch) / tau) for branch in branches]
        chosen = min(candidates, key=lambda item: np.linalg.norm(item - previous))
        out.append(chosen)
        previous = chosen
    return np.asarray(out)


def _bone_curves(source_bone: dict, track: dict, target_joint: dict, frames: int) -> dict:
    """Evaluate local SRT at every source frame, relative to each model's bind pose."""
    values = track["values"]["Transform"]
    if len(values) not in (1, frames + 1):
        raise ValueError(f"unexpected {len(values)} values for {frames} frames")
    source_matrix = np.asarray(source_bone["transform"], dtype=float)
    source_translation = source_matrix[3, :3]
    source_scale = np.linalg.norm(source_matrix[:3, :3], axis=1)
    source_basis = source_matrix[:3, :3] / source_scale[:, None]
    # SSBH JSON matrices are row-vector style. Transpose for scipy's column
    # convention, while NUANMB rotations are ordinary xyzw quaternions.
    source_rotation = Rotation.from_matrix(source_basis.T)
    target_translation = np.asarray(target_joint["trans"], dtype=float)
    target_scale = np.asarray(target_joint["scale"], dtype=float)
    target_rotation = Rotation.from_euler("xyz", target_joint["rot"])
    out = {part: [] for part in TRACK_TYPE}
    for frame in range(frames + 1):
        value = values[min(frame, len(values) - 1)]
        translation = np.asarray([value["translation"][k] for k in "xyz"])
        scale = np.asarray([value["scale"][k] for k in "xyz"])
        pose_rotation = target_rotation * source_rotation.inv() * _rotation(value["rotation"])
        out["rotation"].append(pose_rotation)
        out["translation"].append(target_translation +
                                  (translation - source_translation) * TRANSLATION_SCALE)
        out["scale"].append(target_scale * scale / source_scale)
    out["rotation"] = _continuous_euler(out["rotation"], np.asarray(target_joint["rot"]))
    out["translation"] = np.asarray(out["translation"])
    out["scale"] = np.asarray(out["scale"])
    return out


def _track(values: np.ndarray, tolerance: float):
    """Encode frame samples and verify each decoded integer frame within tolerance."""
    if np.max(values) - np.min(values) <= tolerance / 4:
        # A one-key CON stream has no wait and expires immediately in HSD.
        # Stock fighter FigaTrees hold constants with two equal keys spanning
        # the clip, so keep the same duration even for a flat source curve.
        value = float(values[0])
        end_frame = len(values) - 1
        fv = F.choose_frac([value])
        encoded = F._enc(value, fv)
        body = bytes([F.CON | 0x10]) + encoded + F._varint(end_frame) + encoded
        quantized = F.quant(value, fv)
        fs = 0
        keys = [(F.CON, quantized, None, end_frame),
                (F.CON, quantized, None, None)]
    else:
        n = len(values)
        slopes = np.gradient(values) if n > 1 else np.zeros(n)
        points = [(frame, float(values[frame]), float(slopes[frame])) for frame in range(n)]
        body, fv, fs, keys = F.encode_spline(points)
        if max(abs(F.evaluate(keys, frame) - values[frame]) for frame in range(n)) > tolerance:
            body, fv, fs, keys = F.encode_spline(points, 0, 0)
    worst = max(abs(F.evaluate(keys, frame) - values[frame]) for frame in range(len(values)))
    if worst > tolerance:
        raise ValueError(f"FigaTree curve error {worst:.6g} > {tolerance:.6g}")
    return body, fv, fs, worst


def _close_loop(curves: dict[str, np.ndarray], blend_frames: int = 6) -> None:
    """Make the last pose meet the first for an HSD loop that has no blend."""
    frames = len(curves["rotation"]) - 1
    start = max(0, frames - blend_frames)
    if start == frames:
        return
    for part, samples in curves.items():
        target = samples[0].copy()
        if part == "rotation":
            target += 2 * math.pi * np.round((samples[start] - target) / (2 * math.pi))
        for frame in range(start + 1, frames + 1):
            weight = (frame - start) / (frames - start)
            samples[frame] = (1 - weight) * samples[frame] + weight * target


def convert_clip(anim: dict, skeleton: dict, melee_joints: list[dict], symbol: str,
                 row: int, stock_dash: dict | None = None) -> tuple[bytes, dict]:
    frames = round(anim["final_frame_index"])
    if abs(frames - anim["final_frame_index"]) > 1e-5 or frames < 1:
        raise ValueError("noninteger or empty animation duration")
    nodes = {node["name"]: node for group in anim["groups"]
             if group["group_type"] == "Transform" for node in group["nodes"]}
    bones = {bone["name"]: bone for bone in skeleton["bones"]}
    joints = []
    used_bones = []
    max_error = {key: 0.0 for key in TRACK_TYPE}
    for index, target in enumerate(melee_joints):
        source_name = BONE_MAP.get(index)
        node = nodes.get(source_name) if source_name else None
        tracks = []
        if node is not None:
            if source_name not in bones:
                raise ValueError(f"animation bone missing from skeleton: {source_name}")
            source_track = next((item for item in node["tracks"]
                                 if item["name"] == "Transform"), None)
            if source_track is None:
                raise ValueError(f"missing Transform track: {source_name}")
            curves = _bone_curves(bones[source_name], source_track, target, frames)
            if index == 1 and row in (7, 8, 9, 13):
                # These Melee walk/run rows are physics-driven. Ultimate's
                # cumulative root Z otherwise moves only the mesh and snaps it
                # back when the clip loops (11–73 model units per cycle).
                curves["translation"][:] = target["trans"]
            elif index == 1 and row == 12:
                # Melee Dash is animation-driven (motion flag 0x80000000), but
                # Ultimate's dash clip has almost no root travel. Preserve the
                # host's stock root curve so the fighter keeps its real dash.
                if stock_dash is None:
                    raise ValueError("stock Dash FigaTree needed for root policy")
                source_tracks = {track["type"]: track for track in stock_dash["joints"][1]}
                stock_end = round(stock_dash["frames"])
                for axis, track_type in enumerate(TRACK_TYPE["translation"]):
                    if track_type in source_tracks:
                        curves["translation"][:, axis] = [
                            F.evaluate(source_tracks[track_type]["keys"], min(f, stock_end))
                            for f in range(frames + 1)]
                    else:
                        curves["translation"][:, axis] = target["trans"][axis]
            if row == 13:
                # Ultimate marks Run as a loop, yet its final pose can differ
                # sharply from frame 0 (Head differs by 2.5 radians). Melee's
                # FigaTree loop would snap; crossfade the last six samples.
                _close_loop(curves)
            used_bones.append(source_name)
            for part, types in TRACK_TYPE.items():
                base = np.asarray(target[{"rotation": "rot", "translation": "trans", "scale": "scale"}[part]])
                for axis, track_type in enumerate(types):
                    values = curves[part][:, axis]
                    if np.max(np.abs(values - base[axis])) < TOLERANCE[part] / 4:
                        continue
                    body, fv, fs, error = _track(values, TOLERANCE[part])
                    tracks.append((track_type, body, fv, fs))
                    max_error[part] = max(max_error[part], error)
        joints.append(tracks)
    raw = F.build_tree_archive(symbol, frames, joints)
    parsed_symbol, parsed = F.parse_archive(raw)
    if parsed_symbol != symbol or len(parsed["joints"]) != len(melee_joints):
        raise ValueError("generated FigaTree failed roundtrip")
    return raw, {"frames": frames, "tracks": sum(map(len, joints)),
                 "mapped_bones": used_bones, "max_curve_error": max_error,
                 "bytes": len(raw)}


def build(root: Path, output: Path, requested: set[str] | None = None) -> dict:
    selected = json.loads((root / "ports/kirby-ultimate/animations/manifest.json").read_text(encoding="utf-8"))["clips"]
    melee_joints = json.loads((root / "experiment/brawl-kirby/analysis/melee_model.json").read_text())[
        "PlKbNr.dat"]["joints"]
    decoder = root / "experiment/tooling/ultimate/apps/SSBH-JSON/ssbh_data_json.exe"
    _, melee_archives = melee_anim.melee_aj()
    stock_dash = melee_archives["PlyKirby5K_Share_ACTION_Dash_figatree"][2]
    source_skeleton = root / "experiment/tooling/ultimate/workspace/extracted/fighter/kirby/model/body/c00/model.nusktb"
    result = {"source_manifest": "ports/kirby-ultimate/animations/manifest.json", "animations": [],
              "retarget": "local rest-pose delta on explicitly mapped body joints; facial helpers held at Melee rest"}
    with tempfile.TemporaryDirectory(prefix="ultimate-kirby-anim-") as tmp:
        temp = Path(tmp)
        skeleton = decode(decoder, source_skeleton, temp / "skeleton.json")
        for clip in selected:
            stem = Path(clip["ultimate_file"]).stem
            if requested is not None and stem not in requested:
                continue
            source = root / clip["ultimate_file"]
            if hashlib.sha256(source.read_bytes()).hexdigest() != clip["sha256"]:
                raise ValueError(f"source animation changed since manifest was built: {source}")
            anim = decode(decoder, source, temp / "anim.json")
            for row, name in zip(clip["melee_motion_rows"], clip["melee_motion_names"]):
                symbol = f"PlyKirby5K_Share_ACTION_{name}_figatree"
                raw, report = convert_clip(anim, skeleton, melee_joints, symbol, row, stock_dash)
                relative = Path("clips") / f"{name}.dat"
                target = output / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                result["animations"].append({"row": row, "file": relative.as_posix(),
                    "symbol": symbol, "ultimate_clip_id": clip["ir_clip_id"],
                    "sha256": hashlib.sha256(raw).hexdigest(), **report})
    output.mkdir(parents=True, exist_ok=True)
    (output / "install-manifest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path, default=ROOT / "_build/tmp/ultimate-kirby-anims")
    parser.add_argument("--clips", nargs="*", help="Ultimate source filename stems; omit for all selected")
    args = parser.parse_args()
    result = build(args.root, args.out, set(args.clips) if args.clips is not None else None)
    print(f"wrote {len(result['animations'])} HSD FigaTree archives to {args.out}")


if __name__ == "__main__":
    main()
