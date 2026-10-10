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
