"""Pilot world-pose retarget of Ultimate Kirby body motion to the Melee tree.

The mesh importer binds each Ultimate bone into the corresponding Melee rest
world space. Transfer animated *world* matrices through that same bind change,
then solve Melee locals against the already animated Melee parent. This avoids
applying local deltas through two different joint hierarchies.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import warnings

import numpy as np
from scipy.spatial.transform import Rotation

import convert as local

WORLD_REST_SCALE = 5.0 / 4.6
# These actions pause their animation while stock fighter code waits for the
# animation root to reach a particular height. Retiming the stock root to the
# longer Ultimate clip prevents the fighter from landing before that pause.
STOCK_FRAME_LOCKED_ROWS = frozenset((247, 248, 249))


def _srt(translation, rotation, scale):
    matrix = np.eye(4)
    matrix[:3, :3] = rotation.as_matrix() @ np.diag(scale)
    matrix[:3, 3] = translation
    return matrix


def _decompose(matrix):
    translation = matrix[:3, 3].copy()
    basis = matrix[:3, :3]
    scale = np.linalg.norm(basis, axis=0)
    if np.min(scale) < 1e-6:
        raise ValueError("degenerate animated joint scale")
    rotation_matrix = basis / scale
    u, _, vt = np.linalg.svd(rotation_matrix)
    proper = u @ vt
    if np.linalg.det(proper) < 0:
        u[:, -1] *= -1
        proper = u @ vt
        scale[-1] *= -1
    return translation, Rotation.from_matrix(proper), scale


def _source_matrices(anim, skeleton):
    bones = skeleton["bones"]
    frames = round(anim["final_frame_index"])
    nodes = {node["name"]: node for group in anim["groups"]
             if group["group_type"] == "Transform" for node in group["nodes"]}
    rest_local = [np.asarray(bone["transform"], dtype=float).T for bone in bones]
    rest_world = []
    for bone, matrix in zip(bones, rest_local):
        parent = bone["parent_index"]
        rest_world.append((rest_world[parent] @ matrix) if parent is not None else matrix)
    all_world = []
    for frame in range(frames + 1):
        world = []
        for bone, rest in zip(bones, rest_local):
            node = nodes.get(bone["name"])
            if node:
                track = next((t for t in node["tracks"] if t["name"] == "Transform"), None)
                if track is None:
                    raise ValueError(f"missing Transform track: {bone['name']}")
                values = track["values"]["Transform"]
                if len(values) not in (1, frames + 1):
                    raise ValueError(f"unexpected sample count: {bone['name']}")
                value = values[min(frame, len(values) - 1)]
                matrix = _srt(np.asarray([value["translation"][a] for a in "xyz"]),
                              local._rotation(value["rotation"]),
                              np.asarray([value["scale"][a] for a in "xyz"]))
            else:
                matrix = rest
            parent = bone["parent_index"]
            world.append((world[parent] @ matrix) if parent is not None else matrix)
        all_world.append(world)
    return frames, bones, rest_world, all_world


def _target_rest(joints):
    local_matrices = [_srt(np.asarray(j["trans"]), Rotation.from_euler("xyz", j["rot"]),
                           np.asarray(j["scale"])) for j in joints]
    world = []
    for joint, matrix in zip(joints, local_matrices):
        parent = joint["parent"]
        world.append((world[parent] @ matrix) if parent >= 0 else matrix)
    return local_matrices, world


def _stock_root_translation(stock_tree, frame, source_frames, row):
    translation = np.zeros(3)
    tracks = {track["type"]: track for track in stock_tree["joints"][1]}
    # Scripted throws use exact stock-frame root timing: the stock action code
    # waits for a physical landing before it advances past its pause command.
    # Other actions still span the full stock root curve over the source clip.
    stock_frame = (min(frame, stock_tree["frames"])
                   if row in STOCK_FRAME_LOCKED_ROWS
                   else frame * stock_tree["frames"] / source_frames)
    for axis, kind in enumerate(local.TRACK_TYPE["translation"]):
        if kind in tracks:
            translation[axis] = local.F.evaluate(tracks[kind]["keys"], stock_frame)
    return translation


def _compressed_track(values, tolerance):
    """Fit a sparse spline, adding the worst integer-frame error until bounded.

    Kirby's PC fighter animation buffer holds one archive up to 0x10000 bytes.
    Per-frame keys alone made the long 110-frame Wait tree 0x10217 bytes.
    """
    values = np.asarray(values, dtype=float)
    if np.ptp(values) <= tolerance / 4:
        return local._track(values, tolerance)
    n = len(values)
    slopes = np.gradient(values)
    chosen = {0, n - 1}
    while True:
        indices = sorted(chosen)
        points = [(f, float(values[f]), float(slopes[f])) for f in indices]
        body, fv, fs, keys = local.F.encode_spline(points)
        error = np.asarray([abs(local.F.evaluate(keys, f) - values[f]) for f in range(n)])
        worst = int(np.argmax(error))
        if error[worst] <= tolerance:
            return body, fv, fs, float(error[worst])
        if worst in chosen:
            # Fractional fixed-point encoding may itself exceed the tolerance.
            body, fv, fs, keys = local.F.encode_spline(points, 0, 0)
            error = np.asarray([abs(local.F.evaluate(keys, f) - values[f]) for f in range(n)])
            worst = int(np.argmax(error))
            if error[worst] <= tolerance:
                return body, fv, fs, float(error[worst])
            if worst in chosen:
                raise ValueError(f"uncompressible FigaTree curve error {error[worst]}")
        chosen.add(worst)


def convert_clip(anim, skeleton, melee_joints, symbol, row, stock_root=None,
                 bind_policy="rebased", source_root=False):
    frames, bones, source_rest, source_world = _source_matrices(anim, skeleton)
    target_local, target_rest = _target_rest(melee_joints)
    source_indices = {bone["name"]: i for i, bone in enumerate(bones)}
    mapped = {i: source_indices[name] for i, name in local.BONE_MAP.items()
              if name in source_indices}
    root_index = source_indices["Trans"]
    raw_samples = {index: {part: [] for part in local.TRACK_TYPE} for index in mapped}
    desired_frames = []
    for frame, source_pose in enumerate(source_world):
        # Stock Melee action scripts own the fighter's root trajectory. Remove
        # Ultimate's visual root translation before rebinding descendants, then
        # add the stock action's animation root curve below. For physics-driven
        # loops the stock curve is zero; for dash, rolls, throws, ledge actions,
        # and Final Cutter it retains the host's expected travel.
        source_correction = np.eye(4)
        target_correction = np.eye(4)
        if not source_root:
            source_correction[:3, 3] = (source_rest[root_index][:3, 3] -
                                          source_pose[root_index][:3, 3])
            if stock_root is None:
                raise ValueError(f"stock root-motion tree required for row {row}")
            target_correction[:3, 3] = _stock_root_translation(stock_root, frame, frames, row)
        if bind_policy == "rebased":
            # Companion mesh has p_target = Wm_rest @ inv(Wu_rest) @ p_source.
            desired = {index: target_correction @ target_rest[index]
                       @ np.linalg.inv(source_rest[source_index])
                       @ source_correction @ source_pose[source_index]
                       for index, source_index in mapped.items()}
        elif bind_policy in ("source-world", "source-world-scaled"):
            # Companion mesh keeps p_source_world as the Melee rest position.
            # The current model importer multiplies all source world rest
            # vertices by 5/4.6. Conjugate the animated source delta by that
            # scale so pivots and translation match those scaled vertices.
            scale = np.diag((WORLD_REST_SCALE,) * 3 + (1.0,)) if bind_policy == "source-world-scaled" else np.eye(4)
            inv_scale = np.linalg.inv(scale)
            desired = {index: target_correction @ scale @ source_correction
                       @ source_pose[source_index] @ np.linalg.inv(source_rest[source_index])
                       @ inv_scale @ target_rest[index]
                       for index, source_index in mapped.items()}
        else:
            raise ValueError(f"unknown mesh bind policy: {bind_policy}")
        desired_frames.append(desired)
        target_pose = []
        for index, joint in enumerate(melee_joints):
            parent = joint["parent"]
            if index in desired:
                pose_local = (np.linalg.inv(target_pose[parent]) @ desired[index]
                              if parent >= 0 else desired[index])
                translation, rotation, scale = _decompose(pose_local)
                raw_samples[index]["translation"].append(translation)
                raw_samples[index]["rotation"].append(rotation)
                raw_samples[index]["scale"].append(scale)
                pose_local = _srt(translation, rotation, scale)
            else:
                pose_local = target_local[index]
            actual = target_pose[parent] @ pose_local if parent >= 0 else pose_local
            target_pose.append(actual)
    tracks_by_joint = [[] for _ in melee_joints]
    max_curve_error = {part: 0.0 for part in local.TRACK_TYPE}
    for index, part_samples in raw_samples.items():
        target = melee_joints[index]
        reference = np.asarray(target["rot"])
        curves = {
            "rotation": local._continuous_euler(part_samples["rotation"], reference),
            "translation": np.asarray(part_samples["translation"]),
            "scale": np.asarray(part_samples["scale"]),
        }
        if row == 13:
            local._close_loop(curves)
        for part, kinds in local.TRACK_TYPE.items():
            base = np.asarray(target[{"rotation": "rot", "translation": "trans", "scale": "scale"}[part]])
            for axis, kind in enumerate(kinds):
                values = curves[part][:, axis]
                if np.max(np.abs(values - base[axis])) < local.TOLERANCE[part] / 4:
                    continue
                body, fv, fs, error = _compressed_track(values, local.TOLERANCE[part])
                tracks_by_joint[index].append((kind, body, fv, fs))
                max_curve_error[part] = max(max_curve_error[part], error)
    raw = local.F.build_tree_archive(symbol, frames, tracks_by_joint)
    parsed_symbol, parsed = local.F.parse_archive(raw)
    if parsed_symbol != symbol or len(parsed["joints"]) != len(melee_joints):
        raise ValueError("generated world-pose tree failed roundtrip")
    # Measure the decoded archive, not the pre-encoding poses. Run's final six
    # frames intentionally blend to frame zero and therefore differ from source.
    end_checked = frames - 6 if row == 13 else frames
    world_error = 0.0
    marker_error = 0.0
    worst_world = None
    worst_marker = None
    for frame in range(end_checked + 1):
        evaluated = []
        for index, joint in enumerate(melee_joints):
            parts = {"rotation": np.asarray(joint["rot"], dtype=float).copy(),
                     "translation": np.asarray(joint["trans"], dtype=float).copy(),
                     "scale": np.asarray(joint["scale"], dtype=float).copy()}
            for track in parsed["joints"][index]:
                kind = track["type"]
                for part, kinds in local.TRACK_TYPE.items():
                    if kind in kinds:
                        parts[part][kinds.index(kind)] = local.F.evaluate(track["keys"], frame)
            matrix = _srt(parts["translation"], Rotation.from_euler("xyz", parts["rotation"]),
                          parts["scale"])
            parent = joint["parent"]
            evaluated.append((evaluated[parent] @ matrix) if parent >= 0 else matrix)
            if index in mapped:
                difference = evaluated[index] - desired_frames[frame][index]
                translation_error = float(np.linalg.norm(difference[:3, 3]))
                axis_error = float(np.max(np.linalg.norm(difference[:3, :3], axis=0)))
                if translation_error > world_error:
                    world_error, worst_world = translation_error, {"frame": frame, "joint": index,
                        "bone": bones[mapped[index]]["name"]}
                if axis_error > marker_error:
                    marker_error, worst_marker = axis_error, {"frame": frame, "joint": index,
                        "bone": bones[mapped[index]]["name"]}
    return raw, {"frames": frames, "tracks": sum(map(len, tracks_by_joint)),
                 "mapped_bones": [bones[i]["name"] for i in mapped.values()],
                 "max_curve_error": max_curve_error,
                 "max_mapped_world_translation_error": world_error,
                 "max_mapped_world_axis_marker_error": marker_error,
                 "worst_world_translation": worst_world,
                 "worst_world_axis_marker": worst_marker,
                 "world_error_basis": "decoded integer frames; Run excludes final six seam-blend frames",
                 "root_policy": ("preserve scaled Ultimate Trans travel"
                                 if source_root else
                                 "remove Ultimate Trans travel; stock root at exact host frame"
                                 if row in STOCK_FRAME_LOCKED_ROWS else
                                 "remove Ultimate Trans travel; resample stock Melee visual root"),
                 "mesh_bind_policy": bind_policy,
                 "bytes": len(raw)}


def build(root, output, requested=None, bind_policy="rebased"):
    selected = json.loads((root / "ports/kirby-ultimate/animations/manifest.json").read_text()) ["clips"]
    joints = json.loads((root / "experiment/brawl-kirby/analysis/melee_model.json").read_text()) ["PlKbNr.dat"]["joints"]
    decoder = root / "experiment/tooling/ultimate/apps/SSBH-JSON/ssbh_data_json.exe"
    _, archives = local.melee_anim.melee_aj()
    result = {"source_manifest": "ports/kirby-ultimate/animations/manifest.json",
              "retarget": "world pose through matching mesh bind transform",
              "mesh_bind_policy": bind_policy,
              "animations": []}
    with tempfile.TemporaryDirectory(prefix="ultimate-kirby-world-") as tmp:
        tmp = Path(tmp)
        skeleton = local.decode(decoder, root / "experiment/tooling/ultimate/workspace/extracted/fighter/kirby/model/body/c00/model.nusktb", tmp / "skeleton.json")
        for clip in selected:
            stem = Path(clip["ultimate_file"]).stem
            if requested is not None and stem not in requested:
                continue
            source = root / clip["ultimate_file"]
            if hashlib.sha256(source.read_bytes()).hexdigest() != clip["sha256"]:
                raise ValueError(f"source animation changed: {source}")
            anim = local.decode(decoder, source, tmp / "anim.json")
            for row, name in zip(clip["melee_motion_rows"], clip["melee_motion_names"]):
                symbol = f"PlyKirby5K_Share_ACTION_{name}_figatree"
                stock_root = archives[symbol][2]
                raw, report = convert_clip(anim, skeleton, joints, symbol, row, stock_root,
                                           bind_policy)
                # Several Melee rows reuse one public symbol (Landing, special
                # phases, item families) but need different source clips or
                # stock root curves. Keep subarchives distinct by row.
                relative = Path("clips") / f"{row:03d}-{name}.dat"
                target = output / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                result["animations"].append({"row": row, "file": relative.as_posix(),
                    "symbol": symbol, "ultimate_clip_id": clip["ir_clip_id"],
                    "sha256": hashlib.sha256(raw).hexdigest(), **report})
    output.mkdir(parents=True, exist_ok=True)
    (output / "install-manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=local.ROOT)
    parser.add_argument("--out", type=Path, default=local.ROOT / "_build/tmp/ultimate-kirby-anims-world")
    parser.add_argument("--clips", nargs="*")
    parser.add_argument("--bind-policy", choices=("rebased", "source-world", "source-world-scaled"),
                        default="rebased", help="Must match companion mesh vertex bind rule")
    args = parser.parse_args()
    result = build(args.root, args.out, set(args.clips) if args.clips is not None else None,
                   args.bind_policy)
    print(f"wrote {len(result['animations'])} world-pose FigaTrees to {args.out}")


if __name__ == "__main__":
    main()
