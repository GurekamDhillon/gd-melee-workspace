"""Map plan joint indices to actual Blender bone names without Blender.

Synthesized joints remain in the parent graph but are never mapped or
included in the coverage denominator. Matching preserves input order.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

_SUFFIX = re.compile(r"\.\d{3}$")


def _norm(name: str) -> str:
    return _SUFFIX.sub("", name).lower()


def _depths(parents: dict[int, int | None]) -> dict[int, int]:
    """Follow all parent chains iteratively, including unmapped joints."""
    depths: dict[int, int] = {}
    for start in parents:
        path: list[int] = []
        seen: set[int] = set()
        node = start
        while node is not None and node in parents and node not in depths:
            if node in seen:
                raise ValueError(f"cycle in joint parent chain at {node}")
            seen.add(node)
            path.append(node)
            node = parents[node]

        depth = depths.get(node, -1)
        for index in reversed(path):
            depth += 1
            depths[index] = depth
    return depths


@dataclass
class JointMap:
    by_index: dict[int, str]
    skipped_synth: list[int]
    missing_bones: list[int]
    unmapped_bones: list[str]
    _parents: dict[int, int | None] = field(
        default_factory=dict, repr=False, compare=False
    )

    def coverage(self) -> float:
        non_synth_count = len(self.by_index) + len(self.missing_bones)
        return len(self.by_index) / max(1, non_synth_count)

    def order(self) -> list[int]:
        """Return mapped joints parent-first, with index breaking ties.

        Missing external parents terminate a chain. Cycles raise
        ValueError rather than allowing an infinite traversal.
        """
        depths = _depths(self._parents)
        return sorted(self.by_index, key=lambda index: (depths.get(index, 0), index))


def load_plan(path) -> dict:
    with open(path, "r", encoding="utf-8") as stream:
        plan = json.load(stream)
    if not isinstance(plan, dict):
        raise ValueError("plan must be a JSON object")
    return plan


def build_joint_map(
    plan: dict,
    bone_names: Iterable[str],
    aliases: dict[str, str] | None = None,
) -> JointMap:
    """Match alias target, exact name, then normalized name.

    Alias values name actual bones. Each bone name can be used once.
    Within a normalized-name collision the first free input bone wins.
    """
    names = list(bone_names)
    if any(not isinstance(name, str) for name in names):
        raise ValueError("bone names must be strings")

    all_bones = set(names)
    normalized: dict[str, list[str]] = {}
    for name in names:
        normalized.setdefault(_norm(name), []).append(name)

    joints = plan.get("joints", [])
    if not isinstance(joints, (list, tuple)):
        raise ValueError("plan joints must be a sequence")

    parents: dict[int, int | None] = {}
    entries: list[tuple[int, str, bool]] = []
    for joint in joints:
        if not isinstance(joint, Mapping):
            raise ValueError("plan joint must be an object")
        try:
            index = int(joint["index"])
            name = joint["name"]
            parent = joint.get("parent")
            if parent is not None:
                parent = int(parent)
                if parent < 0:
                    parent = None
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ValueError("plan joint has invalid index, name or parent") from exc
        if index < 0:
            raise ValueError("joint index must be non-negative")
        if index in parents:
            raise ValueError(f"duplicate joint index {index}")
        if not isinstance(name, str):
            raise ValueError(f"joint {index} name must be a string")
        parents[index] = parent
        entries.append((index, name, bool(joint.get("synth", False))))

    alias_map = {} if aliases is None else aliases
    used: set[str] = set()
    by_index: dict[int, str] = {}
    skipped_synth: list[int] = []
    missing_bones: list[int] = []

    for index, name, synthesized in entries:
        if synthesized:
            skipped_synth.append(index)
            continue

        chosen = None
        alias_target = alias_map.get(name)
        if alias_target is not None and alias_target in all_bones and alias_target not in used:
            chosen = alias_target
        if chosen is None and name in all_bones and name not in used:
            chosen = name
        if chosen is None:
            for candidate in normalized.get(_norm(name), []):
                if candidate not in used:
                    chosen = candidate
                    break

        if chosen is None:
            missing_bones.append(index)
        else:
            by_index[index] = chosen
            used.add(chosen)

    return JointMap(
        by_index=by_index,
        skipped_synth=skipped_synth,
        missing_bones=missing_bones,
        unmapped_bones=[name for name in names if name not in used],
        _parents=parents,
    )


# Action states the bare Workbench scene cannot pose: Rebirth/RebirthWait (12, 13) need the revival platform; grabs,
# throws, shoulder carries, items, mushrooms etc. need a partner or an item (found by engine_check/sweep_rows.py;
# before the engine refused them they died on a jobj assert). Keep in step with gs_wb_unpreviewable in the
# engine (pc/platform/gw_script.c) and kUnpreviewable in the launcher (commands_rows.cpp).
UNPREVIEWABLE_MOTIONS = frozenset((12, 13, 128, 129, 131, 223, 224, 225, 226, 227, 228, 239, 240, 241, 242, 243, 266, 267, 268, 269, 270, 271, 272, 273, 274, 277, 280, 285, 289, 290, 291, 292, 306, 308, 309, 310, 313, 314, 315, 316, 317, 318, 319, 320, 321, 323, 324, 328, 332, 333, 334, 337, 340))


def row_previewable(row):
    """False for a row the engine cannot pose in the bare scene (list_rows says so; the motions are the fallback)."""
    if row.get("previewable") is False:
        return False
    motions = [m for m in (row.get("motions") or []) if isinstance(m, int) and not isinstance(m, bool)]
    return not (motions and all(m in UNPREVIEWABLE_MOTIONS for m in motions))


def resolve_row_name(names, name):
    """The engine row a --row / --exercise argument names. A special move's row is "side_b (Rush)" (the input, then
    the Geno state), so "side_b" alone selects it; an exact name always wins."""
    if name in names:
        return name
    hits = [n for n in names if isinstance(n, str) and n.startswith(name + " (")]
    return hits[0] if hits else name


def wait_row_name(rows):
    """The row to fall back to: the previewable row named "wait", else a clip "Wait" row, else the first previewable."""
    rows = [r for r in rows if row_previewable(r)]
    for test in (lambda r: str(r.get("name", "")).casefold() == "wait", lambda r: r.get("clip") == "Wait"):
        found = next((r for r in rows if test(r)), None)
        if found:
            return found.get("name", "")
    return rows[0].get("name", "") if rows else ""


def pick_reference_row(rows, action_exists):
    """The row the Workbench calibrates against: (row, action_name), or (None, "").

    Calibration records, per bone, the fixed offset between the engine's joint frame and the Blender bone frame,
    from one pose both sides agree on, so the reference must be a row whose engine pose equals its clip's pose at
    the calibration frame. The standing "wait" row is that. Order: a row whose clip is exactly "Wait" (Goku), the
    row named "wait" with an existing action (Falcon's clip is "Wait1"), then the first row with an existing
    action. Falling straight to the first action row picked Falcon's "dead_up_star" (clip DamageFall): the engine
    plays those rows blended with a previous pose, the offsets absorbed the mismatch, and the posed rig's feet and
    arms sat up to 3.4 units off the engine's joints (pose error 3.44 vs 0.20 with the wait reference)."""
    rows = [r for r in rows if row_previewable(r)] or list(rows)
    matching = [r for r in rows if r.get("clip") and action_exists(r["clip"])]
    reference = next((r for r in matching if r["clip"] == "Wait"), None)
    if reference is None:
        reference = next((r for r in matching if str(r.get("name", "")).casefold() == "wait"), None)
    if reference is None and matching:
        reference = matching[0]
    if reference is not None:
        return reference, reference["clip"]
    reference = next((r for r in rows if str(r.get("name", "")).casefold() == "wait"), rows[0] if rows else None)
    return reference, ""
