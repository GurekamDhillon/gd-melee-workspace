"""Falcon source eligibility and diagnosis of recorded Workbench row sweeps.

This reads metadata, never animation bytes. A bank's N samples include its entry
pose: the move's one-based frame range is 1..N-1, less any authored crop.
Engine observations belong to their action ID; a different action's frame is
not the end of the requested move. Sweep annotations are evidence for that
engine/scene only; a normal project refresh recomputes source eligibility.
"""
from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass, replace
import json
import math
from pathlib import Path
import re

try:  # Both the standalone add-on namespace and python -m tools.... are used.
    from ..rigmap import UNPREVIEWABLE_MOTIONS
except ImportError:
    from rigmap import UNPREVIEWABLE_MOTIONS


# Common-state callbacks need more than a selected animation. The Falcon sweep
# enters these with neutral input and freshly reset state, so they leave the
# requested action before frame 1. These are not bad clip lengths or loop wraps.
# IDs are the source enums in ftCommon/forward.h, not animation/subaction IDs.
_REQUIREMENTS = {
    **dict.fromkeys((15, 16, 17, 21, 22), "Needs held movement input; neutral preview input immediately leaves this action."),
    40: "Needs held crouch input; neutral preview input enters the crouch exit action.",
    **dict.fromkeys(range(75, 87), "Needs initialized hitstun and damage state; the bare preview immediately enters an aerial action."),
    91: "Needs initialized knockback and airborne damage state; the bare preview immediately leaves this action.",
    **dict.fromkeys((178, 179, 182), "Needs held shield input and initialized guard state; the bare preview immediately changes guard action."),
    192: "Needs initialized knockdown state; the bare preview immediately enters a get-up action.",
    **dict.fromkeys((211, 297, 298, 300), "Needs initialized dizzy, sleep or bind timers; the bare preview immediately leaves this status action."),
    **dict.fromkeys((245, 246), "Needs a platform edge and teeter state; the standing preview immediately leaves this action."),
    250: "Needs ceiling collision state; the standing preview immediately leaves this action.",
    **dict.fromkeys((252, 253, 260, 261, 262), "Needs a ledge attachment and initialized cliff state; the bare preview immediately leaves this action."),
}


@dataclass(frozen=True)
class PreviewStatus:
    previewable: bool = True
    category: str = "ready"
    reason: str = ""
    clip: str = ""
    clip_end_frame: int | None = None
    playable_end_frame: int | None = None
    looping: bool = False
    requested_frame: int | None = None
    observed_frame: int | None = None
    observed_motion: int | None = None


@dataclass(frozen=True)
class Probe:
    name: str
    motion: int
    outcome: str
    requested_frame: int | None = None
    observed_frame: int | None = None
    observed_motion: int | None = None
    last_frame: int | None = None


def _integer(value):
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value) and int(value) == value)


def _context_reason(motion):
    if motion in _REQUIREMENTS:
        return _REQUIREMENTS[motion]
    if motion not in UNPREVIEWABLE_MOTIONS:
        return ""
    if motion in (12, 13):
        return "Needs the revival platform; the engine refuses this action in the bare preview scene."
    if motion in (128, 129, 131, 306, 308, 309, 310, 313, 340):
        return "Needs an item and initialized item state; the engine refuses this action in the bare preview scene."
    if 314 <= motion <= 321:
        return "Needs an active mushroom transformation; the engine refuses this action in the bare preview scene."
    if motion in (323, 324):
        return "Needs fighter entry state; the engine refuses this action in the bare preview scene."
    return "Needs a partner or captor and initialized capture/throw state; the engine refuses this action in the bare preview scene."


def classify_row(row, plan):
    """Classify source metadata, without trusting stale preview annotations."""
    motions = [m for m in row.get("motions", []) if _integer(m)]
    sub = row.get("subaction")
    pick = row.get("pick", {})
    clip = pick.get("clip")
    if "clip" not in pick:
        # Falcon maps action IDs to subaction IDs explicitly. Never index the
        # animation table by an action ID when this source mapping is present.
        clips = plan.get("row_clips", [])
        if _integer(sub) and 0 <= sub < len(clips):
            clip = clips[int(sub)]
        elif sub is None:
            by_motion = {m.get("motion"): m.get("clip") for m in plan.get("motion_rows", [])}
            clip = next((by_motion[m] for m in motions if by_motion.get(m)), "")
    clip = clip or ""
    flags = plan.get("row_flags", [])
    looping = bool(_integer(sub) and 0 <= sub < len(flags)
                   and _integer(flags[int(sub)]) and int(flags[int(sub)]) & 0x40000000)
    status = PreviewStatus(clip=clip, looping=looping)
    def refused(category, reason):
        return replace(status, previewable=False, category=category, reason=reason)

    if _integer(sub) and sub < 0:
        return refused("no-fixed-animation", "This action has no fixed animation subaction; it cannot be posed as a move in the bare preview scene.")
    if not clip:
        return refused("missing-clip", "This subaction has no clip in the local animation bank; there is no fixed move frame to preview.")
    bank = plan.get("bank", {}).get("clips", {})
    if clip not in bank:
        return refused("invalid-clip-reference", "The selected clip is absent from the animation bank; correct the clip assignment.")
    samples = bank[clip].get("frames")
    if not _integer(samples) or samples < 0:
        return refused("invalid-frame-count", "The clip sample count must be a nonnegative integer.")
    crop = pick.get("crop_start", 0)
    if not _integer(crop) or crop < 0:
        return refused("invalid-crop", "The clip crop must be a nonnegative integer.")
    end = max(0, int(samples) - int(crop) - 1)
    status = replace(status, clip_end_frame=end)
    if end < 1:
        return refused("no-playable-frames", "The clip has no move frames after its entry pose and crop; move frame 1 is unavailable.")
    reasons = [_context_reason(m) for m in motions]
    if reasons and all(reasons):
        return refused("requires-gameplay-context", reasons[0])
    return status


_SWEEP_LINE = re.compile(r"^(\S+)\s+\[([\d, ]+)\]\s+(ok\b|refused:|DEAD\b)(.*)$")
_REQUEST = re.compile(r"frame (-?\d+) is past the end")
_OBSERVED = re.compile(r"fighter is at frame (-?\d+) of action (\d+)")
_LAST = re.compile(r"last frame (\d+)")


def parse_sweep(text):
    """Read row outcomes only; discard headers, stack traces and local paths."""
    records = []
    for line in text.splitlines():
        match = _SWEEP_LINE.match(line)
        if not match:
            continue
        name, motions, kind, message = match.groups()
        motion = int(motions.split(",")[0])
        outcome = ("ok" if kind == "ok" else "dead" if kind == "DEAD" else
                   "past-end" if "past the end" in message else
                   "engine-motion-unavailable" if "no such motion" in message else
                   "context-refusal" if "cannot be previewed" in message else "engine-refusal")
        request, observed, last = _REQUEST.search(message), _OBSERVED.search(message), _LAST.search(message)
        records.append(Probe(name, motion, outcome,
                             int(request[1]) if request else None,
                             int(observed[1]) if observed else None,
                             int(observed[2]) if observed else None,
                             int(last[1]) if last else None))
    return records


def classify_probe(row, plan, probe):
    """Diagnose a probe without interpreting another action's frame as an end."""
    status = replace(classify_row(row, plan), requested_frame=probe.requested_frame,
                     observed_frame=probe.observed_frame, observed_motion=probe.observed_motion)
    if probe.outcome == "ok":
        return status
    if probe.outcome == "engine-motion-unavailable":
        return replace(status, previewable=False, category="engine-motion-unavailable",
                       reason="This engine/scene reports no such motion for the fighter. The source row is retained; check the fighter template and engine motion table.")
    if not status.previewable:
        return status
    if probe.outcome != "past-end":
        return replace(status, previewable=False, category=probe.outcome,
                       reason="The recorded engine refused or crashed on this row; it is unavailable in that engine/scene.")
    request = probe.requested_frame
    same_action = probe.observed_motion == probe.motion
    if request == 0 and same_action and probe.observed_frame == 1:
        return replace(status, category="frame-numbering-convention",
                       reason="Move frame 1 is the first move frame; requesting frame 0 returned frame 1.")
    if same_action and status.looping and request is not None and probe.observed_frame is not None and probe.observed_frame < request:
        return replace(status, category="loop-wrap", reason="The same looping action wrapped its animation frame; this is not a finite move end.")
    if probe.last_frame is not None and request is not None and 1 <= probe.last_frame < request:
        category = "past-clip-end" if request > status.clip_end_frame else "action-ended"
        return replace(status, category=category, playable_end_frame=probe.last_frame,
                       reason=f"The engine explicitly reported last playable frame {probe.last_frame}; earlier move frames remain previewable.")
    if not same_action:
        return replace(status, previewable=False, category="action-transition",
                       reason=f"The bare scene entered action {probe.observed_motion} before the requested frame; its frame is not this move's end.")
    if request is not None and probe.observed_frame is not None and 1 <= probe.observed_frame < request:
        category = "past-clip-end" if request > status.clip_end_frame else "action-ended"
        return replace(status, category=category, playable_end_frame=probe.observed_frame,
                       reason="The same action stopped before the requested frame; its earlier frames remain previewable.")
    return replace(status, previewable=False, category="unresolved-frame-refusal",
                   reason="The frame refusal establishes no playable end; retain the source count and inspect this engine/scene.")


def annotate_gameplay(gameplay, plan, probes=()):
    """Replace only classifier-owned fields; never rewrite authored move data."""
    updated = copy.deepcopy(gameplay)
    observed = {(p.name, p.motion): p for p in probes}
    for row in updated["moves"]:
        probe = next((observed[(row["name"], m)] for m in row.get("motions", [])
                      if (row["name"], m) in observed), None)
        status = classify_probe(row, plan, probe) if probe else classify_row(row, plan)
        row.update(previewable=status.previewable, preview_reason=status.reason,
                   preview_class=status.category, preview_end_frame=status.clip_end_frame,
                   preview_looping=status.looping)
    return updated


def audit_markdown(gameplay, plan, probes):
    """A path-free evidence table; an unknown playable end stays unknown."""
    from collections import Counter
    by = {(r["name"], m): r for r in gameplay["moves"] for m in r.get("motions", [])}
    outcomes = Counter(p.outcome for p in probes)
    bad = [p for p in probes if p.outcome != "ok"]
    lines = ["# Falcon row sweep classification", "",
             f"Recorded rows: {len(probes)}. Non-OK rows: {len(bad)}.", "",
             "Outcomes: " + ", ".join(f"{k}={v}" for k, v in sorted(outcomes.items())) + ".", "",
             "Clip end is N-1-crop for N samples. A returned frame from another action is never a move end. A dash means the sweep established no value.", "",
             "| Move | Action | Subaction | Clip | Requested frame | Clip end | Confirmed playable end | Returned frame/action | Classification | Reason |",
             "|---|---:|---:|---|---:|---:|---:|---|---|---|"]
    def cell(value):
        return "—" if value is None or value == "" else str(value).replace("|", "\\|").replace("\n", " ")
    for probe in bad:
        row = by.get((probe.name, probe.motion))
        if row is None:
            raise ValueError(f"sweep row is absent from gameplay: {probe.name} [{probe.motion}]")
        status = classify_probe(row, plan, probe)
        returned = f"{probe.observed_frame} / {probe.observed_motion}" if probe.observed_motion is not None else None
        fields = [probe.name, probe.motion, row.get("subaction"), status.clip,
                  probe.requested_frame, status.clip_end_frame, status.playable_end_frame,
                  returned, status.category, status.reason]
        lines.append("| " + " | ".join(map(cell, fields)) + " |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameplay", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--sweep", type=Path, help="recorded engine/scene evidence; no new engine launch")
    parser.add_argument("--report", type=Path, help="write the evidence table")
    parser.add_argument("--annotate", action="store_true", help="refresh source-only gameplay annotations; sweep diagnoses stay in the report")
    args = parser.parse_args(argv)
    gameplay = json.loads(args.gameplay.read_text(encoding="utf-8-sig"))
    plan = json.loads(args.plan.read_text(encoding="utf-8-sig"))
    probes = parse_sweep(args.sweep.read_text(encoding="utf-8-sig")) if args.sweep else []
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(audit_markdown(gameplay, plan, probes), encoding="utf-8")
    if args.annotate:
        # Use the source pipeline's atomic replace and stable-byte behavior.
        from .project_build import write_json
        write_json(args.gameplay, annotate_gameplay(gameplay, plan))
    from collections import Counter
    print(json.dumps({"source_classes": dict(Counter(classify_row(r, plan).category for r in gameplay["moves"])),
                      "sweep_outcomes": dict(Counter(p.outcome for p in probes))}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
