#!/usr/bin/env python3
"""Measure Sora body envelope packing and the deformation cost of weight edits.

This is an offline analysis of the exported Ultimate mesh. It never changes the
mesh or invokes fighterbuild. Run from any directory with::

    python ports/ir/tools/analyze_envelopes.py

The default input is the local, ignored ``mesh_c00.json``. Only the Markdown
report is written. The packing simulation mirrors POBJ_Generator's first-seen
envelope IDs, lexicographic triangle-set buckets and first-fit ten-node bins.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import struct

import numpy as np
from scipy.spatial.transform import Rotation

import convert_ultimate_anim as CA
import plan_parts


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MESH = ROOT / "_build/tmp/ultimate-mods/ultimate-trail-slot-marth/_work/mesh_c00.json"
DEFAULT_REPORT = ROOT / "_build/tmp/codex-bodypieces-report.md"
CLIPS = ("a00wait1", "a01walkmiddle", "c00attack11")
MAX_ENVELOPES = 10
MAX_VERTICES = 32766


def f32_bits(value: float) -> int:
    """C# casts JSON doubles to float before comparing envelope tuples."""
    return struct.unpack("<I", struct.pack("<f", value))[0]


def envelope(weights: tuple[tuple[int, float], ...]) -> tuple[tuple[int, int], ...]:
    return tuple(sorted((bone, f32_bits(weight)) for bone, weight in weights))


def normalize(weights: list[tuple[int, float]]) -> tuple[tuple[int, float], ...]:
    total = sum(w for _, w in weights)
    return tuple(sorted((bone, weight / total) for bone, weight in weights if weight > 0))


def change_weights(weights: tuple[tuple[int, float], ...], mode: str,
                   parameter: float) -> tuple[tuple[int, float], ...]:
    if mode == "drop":
        kept = [(b, w) for b, w in weights if w >= parameter]
        if not kept:
            kept = [max(weights, key=lambda item: item[1])]
        return normalize(kept)
    if mode == "cap":
        kept = sorted(weights, key=lambda item: (-item[1], item[0]))[:int(parameter)]
        return normalize(kept)
    if mode == "quantize":
        steps = int(parameter)
        scaled = [w * steps for _, w in weights]
        units = [math.floor(x) for x in scaled]
        # Largest-remainder apportionment keeps the sum exactly one and
        # guarantees every retained value is a multiple of 1/steps.
        order = sorted(range(len(weights)),
                       key=lambda i: (-(scaled[i] - units[i]), -weights[i][1], weights[i][0]))
        for i in order[:steps - sum(units)]:
            units[i] += 1
        return tuple(sorted((weights[i][0], units[i] / steps)
                            for i in range(len(weights)) if units[i]))
    raise ValueError(mode)


def prepared_triangles(tris: list, mode: str | None = None,
                       parameter: float = 0) -> tuple[list[tuple[int, ...]], int, int]:
    """Assign envelope IDs in vertex order, as CreatePOBJsFromTriangleList does."""
    ids: dict[tuple, int] = {}
    bone_sets: set[tuple[int, ...]] = set()
    out = []
    for tri in tris:
        tri_ids = []
        for vertex in tri:
            weights = tuple((int(b), float(w)) for b, w in vertex["w"])
            if mode:
                weights = change_weights(weights, mode, parameter)
            key = envelope(weights)
            if key not in ids:
                ids[key] = len(ids)
            bone_sets.add(tuple(b for b, _ in key))
            tri_ids.append(ids[key])
        out.append(tuple(sorted(set(tri_ids))))
    return out, len(ids), len(bone_sets)


def pack(triangle_sets: list[tuple[int, ...]], improved: bool = False) -> int:
    """First-fit baseline, or largest/shared-envelope-first best-fit ordering.

    The baseline order is the SortedDictionary<string,...> order in
    POBJ_Generator.PackTriangleGroups. A group with 10,922 triangles reaches
    the signed 16-bit primitive limit and has to open another POBJ.
    """
    buckets: dict[tuple[int, ...], int] = Counter(triangle_sets)
    if improved:
        # Place common, restrictive sets first; choose the group needing the
        # fewest extra envelope IDs. This never changes weights or geometry.
        order = sorted(buckets, key=lambda key: (-len(key), -buckets[key], key))
    else:
        # PNMTXIDX stores each envelope index multiplied by three.
        order = sorted(buckets, key=lambda key: ",".join(str(i * 3) for i in key))
    bins: list[tuple[set[int], int]] = []
    for key in order:
        nodes = set(key)
        for _ in range(buckets[key]):
            chosen = -1
            least_added = 11
            for i, (used, size) in enumerate(bins):
                if size >= MAX_VERTICES // 3:
                    continue
                added = len(nodes - used)
                if len(used) + added <= MAX_ENVELOPES:
                    if not improved:
                        chosen = i
                        break
                    if added < least_added:
                        chosen, least_added = i, added
                        if added == 0:
                            break
            if chosen < 0:
                bins.append((set(nodes), 1))
            else:
                used, size = bins[chosen]
                used.update(nodes)
                bins[chosen] = used, size + 1
    return len(bins)


def local_matrix(translation: np.ndarray, rotation: Rotation,
                 scale: np.ndarray) -> np.ndarray:
    matrix = np.eye(4)
    matrix[:3, :3] = rotation.as_matrix() @ np.diag(scale)
    matrix[:3, 3] = translation
    return matrix


def poses(joints: list[dict], clips: tuple[str, ...]) -> list[tuple[str, np.ndarray]]:
    """Rest + three integer frames per clip, with the port's helper bake."""
    ir = json.loads((Path(CA.INSTANCES) / "trail.ultimate-body.ir.json").read_text(encoding="utf-8"))
    plan = plan_parts.plan(ir)
    assert [j["name"] for j in plan["joints"]] == [j["name"] for j in joints]
    rest = CA.rest_of(ir)
    orient = CA.helper_constraints("trail")[0]

    def world(nodes: dict | None, frame: int = 0) -> np.ndarray:
        matrices = []
        for joint in joints:
            name = joint["name"]
            translation = np.asarray(joint["trans"], dtype=float)
            rotation = Rotation.from_euler("xyz", joint["rot"])
            scale = np.asarray(joint["scale"], dtype=float)
            if nodes and name in nodes:
                track = nodes[name]["tracks"][0]
                values = track["values"]["Transform"]
                value = values[min(frame, len(values) - 1)]
                if not track["transform_flags"]["override_translation"]:
                    translation = np.array([value["translation"][axis] for axis in "xyz"])
                rotation = Rotation.from_quat([value["rotation"][axis] for axis in "xyzw"])
                scale = np.array([value["scale"][axis] for axis in "xyz"])
            matrix = local_matrix(translation, rotation, scale)
            parent = joint["parent"]
            matrices.append(matrices[parent] @ matrix if parent >= 0 else matrix)
        ibm = np.array([np.vstack((np.asarray(j["ibm"]).reshape(3, 4), [0, 0, 0, 1]))
                        for j in joints])
        return np.array(matrices) @ ibm

    result = [("rest", world(None))]
    for clip in clips:
        path = Path(CA.FIGHTERS) / "trail/motion/body/c00" / f"{clip}.nuanmb"
        anim = CA.decode(str(path))
        CA.bake_helpers(anim, plan, rest, orient)
        nodes = {node["name"]: node for group in anim["groups"]
                 if group["group_type"] == "Transform" for node in group["nodes"]}
        last = int(anim["final_frame_index"])
        frames = sorted({round(last * part) for part in (0.25, 0.5, 0.75)})
        if len(frames) != 3:
            raise ValueError(f"clip too short for three samples: {clip}")
        result.extend((f"{clip}:{frame}", world(nodes, frame)) for frame in frames)
    return result


def unique_vertices(tris: list) -> tuple[np.ndarray, list[tuple[tuple[int, float], ...]]]:
    vertices = {}
    for tri in tris:
        for vertex in tri:
            key = (tuple(vertex["p"]), tuple(tuple(w) for w in vertex["w"]))
            vertices[key] = None
    return (np.asarray([key[0] for key in vertices], dtype=float),
            [key[1] for key in vertices])


def skin(positions: np.ndarray, weights: list[tuple[tuple[int, float], ...]],
         pose: np.ndarray) -> np.ndarray:
    out = np.zeros_like(positions)
    for influence in range(max(map(len, weights))):
        rows = [i for i, ws in enumerate(weights) if len(ws) > influence]
        ids = [weights[i][influence][0] for i in rows]
        factors = np.array([weights[i][influence][1] for i in rows])[:, None]
        matrices = pose[ids]
        out[rows] += (np.einsum("nij,nj->ni", matrices[:, :3, :3], positions[rows])
                      + matrices[:, :3, 3]) * factors
    return out


def displacement(positions: np.ndarray, original: list, modified: list,
                 sampled_poses: list[tuple[str, np.ndarray]]) -> tuple[float, float]:
    worst_per_vertex = np.zeros(len(positions))
    for _, pose in sampled_poses:
        error = np.linalg.norm(skin(positions, modified, pose) - skin(positions, original, pose), axis=1)
        np.maximum(worst_per_vertex, error, out=worst_per_vertex)
    return float(worst_per_vertex.max()), float(np.percentile(worst_per_vertex, 99))


def histogram(weights: list[tuple[tuple[int, float], ...]]) -> tuple[Counter, list[tuple[str, int]]]:
    influences = Counter(len(ws) for ws in weights)
    ranges = [(0, .01), (.01, .02), (.02, .05), (.05, .1), (.1, .25), (.25, .5), (.5, 1.00001)]
    values = [weight for ws in weights for _, weight in ws]
    return influences, [(f"[{lo:g}, {min(hi, 1):g}{')' if hi <= 1 else ']'}",
                         sum(lo <= w < hi for w in values)) for lo, hi in ranges]


def run(mesh_path: Path, report_path: Path, clips: tuple[str, ...]) -> None:
    mesh = json.loads(mesh_path.read_text(encoding="utf-8"))
    matches = [d for d in mesh["dobjs"] if d["object"] == "body_highShape" and d["subindex"] == 0]
    if len(matches) != 1:
        raise ValueError(f"expected one body_highShape sub 0, found {len(matches)}")
    tris = matches[0]["tris"]
    base, envelopes, bone_sets = prepared_triangles(tris)
    base_pieces = pack(base)
    if base_pieces != 619:
        raise ValueError(f"packing simulation differs from the 619-piece reference: {base_pieces}")
    positions, originals = unique_vertices(tris)
    sampled_poses = poses(mesh["joints"], clips)
    rest_bind_error = float(np.max(np.abs(sampled_poses[0][1] - np.eye(4))))
    influence_hist, weight_hist = histogram(originals)

    cases = [("Drop <0.01", "drop", .01), ("Drop <0.02", "drop", .02),
             ("Drop <0.05", "drop", .05), ("Cap at 3", "cap", 3),
             ("Cap at 2", "cap", 2), ("Quantize 1/8", "quantize", 8),
             ("Quantize 1/16", "quantize", 16)]
    rows = []
    for label, mode, parameter in cases:
        tri_sets, env_count, bone_count = prepared_triangles(tris, mode, parameter)
        pieces = pack(tri_sets)
        modified = [change_weights(ws, mode, parameter) for ws in originals]
        max_error, p99 = displacement(positions, originals, modified, sampled_poses)
        rows.append((label, pieces, env_count, bone_count, max_error, p99))
        print(f"{label}: {pieces} pieces; max {max_error:.6f}, p99 {p99:.6f}", flush=True)
    improved = pack(base, improved=True)
    rows.append(("Reorder packing only", improved, envelopes, bone_sets, 0.0, 0.0))
    print(f"Reorder packing only: {improved} pieces; zero displacement", flush=True)

    eligible = [row for row in rows if row[1] < 150 and row[4] < .05]
    lines = ["# Sora body envelope analysis", "",
             f"Input: `{mesh_path.relative_to(ROOT).as_posix()}` (`body_highShape` sub 0); offline only. "
             "No game build or run. No mesh or generator files changed.", "",
             "## Baseline", "",
             f"- {len(tris):,} triangles, {len(tris) * 3:,} triangle corners, "
             f"{len(positions):,} distinct position-plus-weight vertices.",
             f"- {envelopes:,} distinct exact float32 bone+weight envelopes; "
             f"{bone_sets:,} distinct bone sets.",
             f"- Simulated C# first-fit packing: **{base_pieces:,} pieces**, matching the serialized "
             "body count of 619. Limit: ten envelopes and 32,766 submitted vertices per piece.",
             "", "### Influences per distinct vertex", "",
             "| Influences | Vertices |", "|---:|---:|"]
    lines += [f"| {n} | {influence_hist[n]:,} |" for n in sorted(influence_hist)]
    lines += ["", "### Individual weight values", "", "| Range | Influences |", "|---|---:|"]
    lines += [f"| {label} | {count:,} |" for label, count in weight_hist]
    lines += ["", "## What-if results", "",
              "Geometric cost is the worst displacement of each distinct position-plus-weight "
              "vertex across ten poses, then the maximum and 99th percentile across vertices. "
              "The poses are rest plus three evenly spread integer frames from each of "
              f"`{clips[0]}`, `{clips[1]}`, and `{clips[2]}`; helpers are baked as in the port. "
              "Weights change only for this measurement. Quantization uses largest remainders "
              "to retain exact unit sum; dropped/capped weights are renormalized.", "",
              "Sampled poses: " + ", ".join(f"`{name}`" for name, _ in sampled_poses) + ".",
              f"The mesh rest joint transforms times inverse binds differ from identity by at most "
              f"{rest_bind_error:.6f} per matrix entry.", "",
              "| Change | Pieces | Envelopes | Bone sets | Max displacement | P99 displacement |",
              "|---|---:|---:|---:|---:|---:|"]
    lines += [f"| {label} | {pieces:,} | {env_count:,} | {bone_count:,} | {max_error:.6f} | {p99:.6f} |"
              for label, pieces, env_count, bone_count, max_error, p99 in rows]
    lines += ["", "## Recommendation", ""]
    if eligible:
        best = min(eligible, key=lambda row: (row[4], base_pieces - row[1]))
        lines.append(f"`{best[0]}` meets both goals: {best[1]} pieces and {best[4]:.6f} maximum "
                     "displacement. It is the eligible option with the smallest measured deformation.")
    else:
        safe = min((row for row in rows if row[4] < .05), key=lambda row: row[1])
        lines.append("None of the tested single changes reaches fewer than 150 pieces while "
                     "keeping maximum displacement below 0.05 units. The lowest-piece option "
                     f"within the error limit is `{safe[0]}` at {safe[1]} pieces "
                     f"(max {safe[4]:.6f}).")
    lines += ["", "The better packing order is an analysis of the same triangle/envelope sets; "
              "its zero displacement does not assert that changing generator order preserves "
              "draw order or transparency behavior. No production mesh weights were modified.", ""]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report: {report_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", type=Path, default=DEFAULT_MESH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--clips", nargs=3, default=CLIPS)
    args = parser.parse_args()
    run(args.mesh.resolve(), args.report.resolve(), tuple(args.clips))


if __name__ == "__main__":
    main()
