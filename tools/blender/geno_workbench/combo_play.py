"""Combo strings in Blender, the pure half: how a string's moves are laid end to end, and where its markers go.

Mirrors the Workbench's planComboString (tools/release/launcher/qt/workbench/combo_model.cpp; geno.md 25): each move runs
until the route to the next one opens, then the next move starts.  No bpy, no engine: the numbers come from the server's
string_plan reply (steps with clip, length, first hit and hitboxes; the routes) or from a test.

Frames are the Workbench's: 1-based, frame 1 is the first frame of a move.  A string frame is the same idea over the whole
string: the first move's frame 1 is string frame 1, and the next move's frame 1 comes right after the cancel frame.
"""
from __future__ import annotations

INPUT_COLOURS = {
    "light": (0.376, 0.784, 0.549),
    "heavy": (0.941, 0.502, 0.251),
    "special": (0.431, 0.588, 1.0),
    "jump": (0.941, 0.824, 0.314),
    "grab": (0.808, 0.486, 0.886),
    "shield": (0.439, 0.808, 0.878),
    "none": (0.627, 0.627, 0.627),
}
CONTACT_ON = ("hit", "block", "contact")
CANCEL_PREFIX = "CANCEL "
ROUTE_PREFIX = "ROUTE "
PLAYED_OUT = 30          # a move of unknown length plays this many frames when nothing cuts it


def input_class(route: dict) -> str:
    value = route.get("input")
    return value if value in INPUT_COLOURS else "none"


def sources(route: dict) -> list[str]:
    from_ = route.get("from")
    if isinstance(from_, str):
        return [from_]
    if isinstance(from_, list):
        return [s for s in from_ if isinstance(s, str)]
    return []


def window(route: dict) -> tuple[int, int]:
    w = route.get("window")
    if isinstance(w, list) and len(w) == 2:
        return int(w[0]), int(w[1])
    return 1, 0


def target_name(to: str) -> str:
    return to[5:] if to.startswith("geno:") else to


def route_label(route: dict) -> str:
    on = route.get("on", "hit")
    when = {"hit": "on hit", "whiff": "on whiff", "block": "on block", "contact": "on contact"}.get(on, "any time")
    return "%s · %s · %s" % (target_name(str(route.get("to", ""))), input_class(route), when)


def find_route(routes: list[dict], source: str, target: str) -> dict | None:
    """The route from `source` to `target`: an exact source beats "*", then priority, then file order."""
    best, best_key = None, None
    for route in routes:
        if route.get("to") != target:
            continue
        srcs = sources(route)
        score = 2 if source in srcs else 1 if "*" in srcs else 0
        if not score:
            continue
        key = (score, int(route.get("priority", 0)))
        if best is None or key > best_key:   # strict: ties keep the file order
            best, best_key = route, key
    return best


def plan_string(steps: list[str], routes: list[dict], info: dict, default_buffer: int = 5, add_buffer: bool = False) -> list[dict]:
    """Segments for the string, one per step.

    info[step] = {"length": frames or 0, "first_hit": first active hit frame or 0}.  A segment is
    {move, start, cut, length, linked, route, input, lo, hi, buffer, cancel_frame}; `cut` is the last move frame played.
    """
    plan, start = [], 1
    for i, step in enumerate(steps):
        data = info.get(step) or {}
        length = int(data.get("length") or 0)
        seg = {"move": step, "start": start, "cut": length if length > 0 else PLAYED_OUT, "length": length,
               "linked": False, "route": "", "input": "", "lo": 0, "hi": 0, "buffer": 0}
        route = find_route(routes, step, steps[i + 1]) if i + 1 < len(steps) else None
        if route is not None:
            lo, hi = window(route)
            cut = lo
            if route.get("on", "hit") in CONTACT_ON and int(data.get("first_hit") or 0) > 0:
                cut = max(cut, int(data["first_hit"]))
            buffer = int(route["buffer"]) if "buffer" in route else int(default_buffer)
            if add_buffer:
                cut += buffer
            if hi > 0:
                cut = min(cut, hi)
            if length > 0:
                cut = min(cut, length)
            seg.update(cut=max(1, cut), linked=True, route=str(route.get("name", "")), input=input_class(route),
                       lo=lo, hi=hi, buffer=buffer)
        seg["cancel_frame"] = start + seg["cut"] - 1
        plan.append(seg)
        start += seg["cut"]
    return plan


def total_frames(plan: list[dict]) -> int:
    return plan[-1]["start"] + plan[-1]["cut"] - 1 if plan else 0


def locate(plan: list[dict], string_frame: int) -> tuple[int, int] | None:
    """(segment index, move frame) shown on a string frame, or None outside the string."""
    for i, seg in enumerate(plan):
        if seg["start"] <= string_frame < seg["start"] + seg["cut"]:
            return i, string_frame - seg["start"] + 1
    return None


def markers(plan: list[dict], routes: list[dict]) -> list[dict]:
    """Timeline markers: the cancel point of every linked segment and the window start of every route that leaves a
    played move.  {name, frame, kind (cancel|route), input}.  Routes that only open after the cut get no marker."""
    out = []
    for i, seg in enumerate(plan):
        if seg["linked"]:
            nxt = plan[i + 1]["move"] if i + 1 < len(plan) else ""
            out.append({"name": "%s%s → %s" % (CANCEL_PREFIX, seg["route"], target_name(nxt)),
                        "frame": seg["cancel_frame"], "kind": "cancel", "input": seg["input"]})
        last = seg["start"] + seg["cut"] - 1
        for route in routes:
            if seg["move"] not in sources(route) and "*" not in sources(route):
                continue
            lo, hi = window(route)
            frame = seg["start"] + lo - 1
            if frame > last:          # it opens after the cut: not part of this string
                continue
            out.append({"name": "%s%s %s [%d-%s]" % (ROUTE_PREFIX, input_class(route), route.get("name", ""), lo, hi or "end"),
                        "frame": frame, "kind": "route", "input": input_class(route)})
    return out


def hit_windows(plan: list[dict], steps: list[dict]) -> list[dict]:
    """Hitbox windows in string frames, from the server's per-step hits (start_frame, end_frame exclusive; -1 never cleared).
    {segment, slot, bone, size, first, last} with first/last the inclusive string frames, clipped to the played part."""
    out = []
    for i, seg in enumerate(plan):
        for hit in (steps[i].get("hits") or []) if i < len(steps) else []:
            start = int(hit.get("start_frame", 0))
            end = int(hit.get("end_frame", -1))
            if start < 1 or start > seg["cut"]:
                continue
            last = seg["cut"] if end < 0 else min(end - 1, seg["cut"])
            if last < start:
                continue
            out.append({"segment": i, "slot": int(hit.get("slot", 0)), "bone": hit.get("bone", ""), "size": float(hit.get("size", 1)),
                        "x": float(hit.get("x", 0)), "y": float(hit.get("y", 0)), "z": float(hit.get("z", 0)),
                        "first": seg["start"] + start - 1, "last": seg["start"] + last - 1})
    return out


def clip_range(seg: dict, crop: int, action_end: float) -> tuple[int, int]:
    """Action frames (first, last) a segment plays: move frame n is action frame crop + n, held inside the action."""
    first = crop + 1
    last = crop + seg["cut"]
    last = min(last, int(action_end)) if action_end else last
    return min(first, last), last
