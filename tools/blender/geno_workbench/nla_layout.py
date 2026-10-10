"""The splice.py sample clock, without bpy or source-tool dependencies.

All ranges are inclusive POSE indices, starting at zero. clip_lengths contains
sample counts (last legal source frame is count - 1). A segment's frame_end is
its last moving sample; hold_end includes its extra held samples. NLA strip
boundaries are continuous intervals; the bpy adapter supplies their endpoints.
scale is 1/speed; multiply by Layout.retime_scale for the output clock.
Marks deliberately use splice.bake's two rounds, not round(continuous_time).
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import math


@dataclass
class Segment:
    action_name: str
    source_from: float
    source_to: float
    frame_start: float
    frame_end: float
    hold_end: float
    scale: float
    samples: int
    hold: int = 0
    mirror: bool = False
    root_yaw: float = 0.0
    yaw_ramp: bool = False
    marks: dict = field(default_factory=dict)
    extras: dict = field(default_factory=dict)

    @property
    def reversed(self):
        return self.source_from > self.source_to

    def output_frame(self, source_frame, retime_scale=1.0):
        direction = -1 if self.reversed else 1
        return self.frame_start + (source_frame - self.source_from) * direction * self.scale * retime_scale


@dataclass
class BlendGap:
    previous: int
    following: int
    frame_start: float
    frame_end: float
    length: int


@dataclass
class Mark:
    segment: int
    label: str
    source_frame: float
    frame: int


@dataclass
class Layout:
    segments: list[Segment]
    blend_gaps: list[BlendGap]
    marks: list[Mark]
    total_length: int
    raw_length: int
    retime_scale: float
    metadata: dict = field(default_factory=dict)


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _integer(value, minimum=0):
    return _number(value) and value == int(value) and value >= minimum


def sample_count(frm, to, speed=1.0):
    """Same inclusive sampling and epsilon as splice.seg_times."""
    return int(math.floor(abs(to - frm) / speed + 1e-9)) + 1


def validate(recipe: dict, clip_lengths: dict[str, int]) -> list[str]:
    """Return actionable errors; never import a source tool or read clip data.

    Unlike splice's permissive endpoint clamping, the editor rejects out-of-range
    crops: a hand-authored recipe should not silently substitute an endpoint.
    """
    errors = []
    if not isinstance(recipe, dict):
        return ["recipe must be an object"]
    if not any(isinstance(recipe.get(k), str) and recipe[k].strip() for k in ("row", "move")):
        errors.append("recipe needs a row or move")
    if not isinstance(clip_lengths, dict):
        return errors + ["clip_lengths must map clip names to sample counts"]
    for key, minimum in (("blend", 0), ("loop_blend", 0), ("frames", 2)):
        if key in recipe and not _integer(recipe[key], minimum):
            errors.append(f"{key} must be an integer >= {minimum}")
    for key in ("loop", "wired", "example"):
        if key in recipe and not isinstance(recipe[key], bool):
            errors.append(f"{key} must be a boolean")
    segments = recipe.get("segments")
    if not isinstance(segments, list) or not segments:
        return errors + ["recipe needs a nonempty segments list"]
    allowed = {"clip", "from", "to", "speed", "mirror", "root_yaw", "yaw_ramp", "hold", "blend", "marks", "note"}
    for index, seg in enumerate(segments):
        prefix = f"segment {index}: "
        if not isinstance(seg, dict):
            errors.append(prefix + "must be an object")
            continue
        unknown = set(seg) - allowed
        if unknown:
            errors.append(prefix + "unknown keys " + ", ".join(sorted(map(str, unknown))))
        clip = seg.get("clip")
        length = clip_lengths.get(clip) if isinstance(clip, str) else None
        if not isinstance(clip, str) or not clip or not _integer(length, 1):
            errors.append(prefix + "unknown clip or invalid sample count: " + str(clip))
        good_range = True
        for key in ("from", "to"):
            value = seg.get(key)
            if not _number(value):
                errors.append(prefix + key + " must be a finite number")
                good_range = False
            elif value < 0 or (_integer(length, 1) and value > length - 1):
                errors.append(prefix + key + " is outside the source sample range")
        speed = seg.get("speed", 1)
        if not _number(speed) or speed <= 0:
            errors.append(prefix + "speed must be finite and > 0")
        for key in ("hold", "blend"):
            if key in seg and not _integer(seg[key]):
                errors.append(prefix + key + " must be a nonnegative integer")
        for key in ("mirror", "yaw_ramp"):
            if key in seg and not isinstance(seg[key], bool):
                errors.append(prefix + key + " must be a boolean")
        if not _number(seg.get("root_yaw", 0)):
            errors.append(prefix + "root_yaw must be a finite number")
        marks = seg.get("marks", {})
        if not isinstance(marks, dict):
            errors.append(prefix + "marks must be an object")
        else:
            for label, value in marks.items():
                if not isinstance(label, str) or not label or not _number(value):
                    errors.append(prefix + "marks need nonempty labels and finite source frames")
                elif good_range and not min(seg["from"], seg["to"]) <= value <= max(seg["from"], seg["to"]):
                    errors.append(prefix + f"mark {label} is outside the crop")
    return errors


def layout(recipe: dict, clip_lengths: dict[str, int]) -> Layout:
    errors = validate(recipe, clip_lengths)
    if errors:
        raise ValueError("; ".join(errors))
    segments, gaps, marks = [], [], []
    start = 0
    for index, seg in enumerate(recipe["segments"]):
        blend = int(seg.get("blend", recipe.get("blend", 3))) if index else 0
        if blend:
            gaps.append(BlendGap(index - 1, index, start, start + blend - 1, blend))
        start += blend
        speed = float(seg.get("speed", 1))
        count = sample_count(seg["from"], seg["to"], speed)
        hold = int(seg.get("hold", 0))
        direction = -1 if seg["from"] > seg["to"] else 1
        for label, source_frame in seg.get("marks", {}).items():
            frame = start + int(round((source_frame - seg["from"]) / (speed * direction)))
            marks.append(Mark(index, label, source_frame, frame))
        segments.append(Segment(
            action_name=seg["clip"], source_from=seg["from"], source_to=seg["to"],
            frame_start=start, frame_end=start + count - 1,
            hold_end=start + count + hold - 1, scale=1.0 / speed,
            samples=count, hold=hold, mirror=seg.get("mirror", False),
            root_yaw=seg.get("root_yaw", 0), yaw_ramp=seg.get("yaw_ramp", False),
            marks=deepcopy(seg.get("marks", {})),
            extras={"note": deepcopy(seg["note"])} if "note" in seg else {},
        ))
        start += count + hold
    total = int(recipe.get("frames", start))
    rate = (total - 1) / max(start - 1, 1) if "frames" in recipe else 1.0
    for seg in segments:
        seg.frame_start *= rate
        seg.frame_end *= rate
        seg.hold_end *= rate
    for gap in gaps:
        gap.frame_start *= rate
        gap.frame_end *= rate
    for mark in marks:
        mark.frame = int(round(mark.frame * rate))
    return Layout(segments, gaps, marks, total, start, rate,
                  deepcopy({k: v for k, v in recipe.items() if k != "segments"}))


def _whole(value, label):
    if not _number(value) or not math.isclose(value, round(value), abs_tol=1e-4, rel_tol=0):
        raise ValueError(label + " must land on a whole logic frame")
    return int(round(value))


def recipe_from_layout(value: Layout) -> dict:
    """Recover a recipe from edited source ranges, scales, holds and positions.

    The first strip is at output zero (the bpy reader subtracts the track's
    origin). Overlaps, fractional gaps and duration/range mismatches are not
    representable by splice.py and are rejected instead of approximated.
    """
    if not value.segments or not _number(value.retime_scale) or value.retime_scale <= 0:
        raise ValueError("layout needs segments and a positive retime scale")
    result = deepcopy(value.metadata)
    result["segments"] = []
    rate = value.retime_scale
    previous_end = -1
    for index, seg in enumerate(value.segments):
        if not _number(seg.scale) or seg.scale <= 0:
            raise ValueError(f"segment {index}: scale must be > 0")
        speed = 1.0 / seg.scale
        count = sample_count(seg.source_from, seg.source_to, speed)
        start = _whole(seg.frame_start / rate, f"segment {index} start")
        end = _whole(seg.frame_end / rate, f"segment {index} end")
        hold_end = _whole(seg.hold_end / rate, f"segment {index} hold end")
        if index == 0 and start != 0:
            raise ValueError("first segment must start at zero")
        gap = start - previous_end - 1
        if gap < 0:
            raise ValueError(f"segment {index}: strips overlap")
        if end - start + 1 != count:
            raise ValueError(f"segment {index}: duration does not match its source range and speed")
        if hold_end < end or hold_end - end != seg.hold:
            raise ValueError(f"segment {index}: hold duration does not match")
        item = deepcopy(seg.extras)
        item.update(clip=seg.action_name, **{"from": seg.source_from, "to": seg.source_to})
        if speed != 1:
            item["speed"] = speed
        if seg.hold:
            item["hold"] = seg.hold
        if seg.mirror:
            item["mirror"] = True
        if seg.root_yaw:
            item["root_yaw"] = seg.root_yaw
        if seg.yaw_ramp:
            item["yaw_ramp"] = True
        if seg.marks:
            item["marks"] = deepcopy(seg.marks)
        if index:
            item["blend"] = gap
        result["segments"].append(item)
        previous_end = hold_end
    if "frames" in result:
        # A one-pose source can be held by a whole-clip retime.
        result["frames"] = value.total_length if previous_end == 0 else _whole(previous_end * rate, "retimed end") + 1
    elif not math.isclose(rate, 1.0, abs_tol=1e-8):
        raise ValueError("a non-unit retime scale needs frames metadata")
    return result
