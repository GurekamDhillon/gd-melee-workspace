"""Pure maths for the hitbox visualization (no bpy, no gpu): angles, knockback, colours, badges.

Everything here is engine-space (Melee units, +x forward when facing = 1, +y up). The Blender side
(hitviz.py) converts through wbspace and draws.

Knockback is the game's own expression, transcribed from the decomp:
  melee/src/melee/ft/ftcoll.c  ftColl_80079AB0 / ftColl_80079C70 (macro KNOCKBACK):
      kb = defense * attack * stage * (0.01 * kbg * (x11C * ((xF8 - w*xF8/(1+w)) * inner) + x120) + bkb)
      w = weight * xF4;  inner = x110*(p+d) + x114*(d*(p+d))          (normal hit)
                         inner = x118*x110 + x114*(x118*fkb)          (set knockback, hit->x28 != 0)
      kb is capped at x108.
  The ftCommonData constants (x110 etc.) come from PlCo.dat on the disc, so they are NOT in the repo.
  The values below are the vanilla ones in their community form
      kb = (((p+d)/10 + (p+d)*d/20) * 200/(weight+100) * 1.4 + 18) * kbg/100 + bkb, cap 2500;
  the in-game `gd.kb_preview` reads the live constants and is the check for any modded PlCo.
Angle rules:
  melee/src/melee/ft/kinds/ftCommon/ftCo_Damage.c ftCo_Damage_CalcAngle: 361 is the Sakurai angle
      (air: x144 rad; ground: 0 below kb x14C, then ramps by x148 degrees up to kb x150).
  melee/src/melee/ft/ftcoll.c ftColl_8007AC68: meteor <=> angle != 361 and unk_kb_angle_min <= angle <=
      unk_kb_angle_max (ftCommonData +7E8 / +7EC; vanilla 230..310 inclusive).
"""

from __future__ import annotations

import math

# vanilla ftCommonData values (see the module docstring for what is and is not verified)
KB_PERCENT_SCALE = 0.1            # x110
KB_DAMAGE_SCALE = 0.05            # x114
KB_WEIGHT_SCALE = 0.01            # xF4
KB_DECAY = 2.0                    # xF8
KB_MUL = 1.4                      # x11C
KB_ADD = 18.0                     # x120
KB_SET_PERCENT = 10.0             # x118: set-knockback hits use this as their "percent"
KB_CAP = 2500.0                   # x108
METEOR_MIN, METEOR_MAX = 230, 310  # unk_kb_angle_min / max
SAKURAI = 361
SAKURAI_AIR_DEG = 40.0            # x144 (0.7 rad)
SAKURAI_GROUND_MAX_DEG = 44.0     # x148
SAKURAI_KB_LOW, SAKURAI_KB_HIGH = 32.0, 88.0   # x14C, x150
SPECIAL_ANGLES = frozenset(range(362, 370))     # autolink / reverse / fixed-position forms: no plain direction

TARGET_PERCENTS = (0, 50, 100)
DEFAULT_WEIGHT = 100.0

# Slot priority: slot 0 is the strongest and the darkest; each later slot is paler. One warm ramp
# separated by lightness (not hue), so it survives red/green colour blindness. (r, g, b)
SLOT_RGB = (
    (0.80, 0.10, 0.00),
    (0.95, 0.45, 0.05),
    (1.00, 0.75, 0.35),
    (1.00, 0.93, 0.80),
)
METEOR_RGB = (0.00, 0.45, 0.70)    # blue: the one hue the slot ramp never uses

ELEMENT_NAMES = {   # HitElement (melee/lb/forward.h)
    0: "", 1: "fire", 2: "electric", 3: "slash", 4: "coin", 5: "ice", 6: "sleep (short)", 7: "sleep",
    8: "grab", 9: "ground", 10: "cape", 11: "inert", 12: "disable", 13: "darkness", 14: "screw attack",
}


def slot_rgb(slot: int) -> tuple[float, float, float]:
    return SLOT_RGB[int(slot) % len(SLOT_RGB)]


def luminance(rgb) -> float:
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def knockback(damage: float, kbg: float, bkb: float, fkb: float = 0.0,
              percent: float = 0.0, weight: float = DEFAULT_WEIGHT) -> float:
    """The knockback value of a hit on a victim at `percent` (before the hit) with `weight`."""
    d = float(damage)
    w = float(weight) * KB_WEIGHT_SCALE
    if fkb:
        inner = KB_SET_PERCENT * KB_PERCENT_SCALE + KB_DAMAGE_SCALE * (KB_SET_PERCENT * fkb)
    else:
        total = float(percent) + d
        inner = KB_PERCENT_SCALE * total + KB_DAMAGE_SCALE * (d * total)
    value = 0.01 * float(kbg) * (KB_MUL * ((KB_DECAY - (w * KB_DECAY) / (1.0 + w)) * inner) + KB_ADD) + float(bkb)
    return min(value, KB_CAP)


def is_meteor(angle: int) -> bool:
    """ftColl_8007AC68."""
    angle = int(angle)
    return angle != SAKURAI and METEOR_MIN <= angle <= METEOR_MAX


def sakurai_ground_degrees(kb: float) -> float:
    """ftCo_Damage_CalcAngle's grounded branch for angle 361."""
    if kb < SAKURAI_KB_LOW:
        return 0.0
    ramp = SAKURAI_GROUND_MAX_DEG * ((kb - SAKURAI_KB_LOW) / (SAKURAI_KB_HIGH - SAKURAI_KB_LOW)) + 1.0
    return min(ramp, SAKURAI_GROUND_MAX_DEG)


def classify_angle(angle: int) -> str:
    """'sakurai' | 'meteor' | 'special' | 'normal'."""
    angle = int(angle)
    if angle == SAKURAI:
        return "sakurai"
    if angle in SPECIAL_ANGLES:
        return "special"
    if is_meteor(angle):
        return "meteor"
    return "normal"


def direction(angle_degrees: float, facing: int = 1) -> tuple[float, float]:
    """Unit launch direction in (x, y) engine space: x mirrors with the attacker's facing."""
    r = math.radians(float(angle_degrees))
    return math.cos(r) * (1.0 if facing >= 0 else -1.0), math.sin(r)


def angle_span(angle: int, kb: float) -> tuple[float, float, float | None]:
    """(low, high, resolved) degrees. A plain angle is (a, a, a); Sakurai is the fan 0..44 plus the
    resolved grounded angle for this kb. 'special' angles have no direction: (0, 0, None)."""
    kind = classify_angle(angle)
    if kind == "special":
        return 0.0, 0.0, None
    if kind == "sakurai":
        return 0.0, SAKURAI_GROUND_MAX_DEG, sakurai_ground_degrees(kb)
    return float(angle), float(angle), float(angle)


ARROW_MIN, ARROW_MAX, ARROW_PER_KB = 2.0, 16.0, 0.06


def arrow_length(kb: float) -> float:
    """Melee units: grows with knockback so a weak jab and a kill move read differently."""
    return max(ARROW_MIN, min(ARROW_MAX, ARROW_PER_KB * float(kb)))


def fan_points(low: float, high: float, facing: int, length: float, steps: int = 6):
    """Polyline (engine xy offsets, origin first and last) outlining the wedge between two angles."""
    pts = [(0.0, 0.0)]
    for i in range(steps + 1):
        a = low + (high - low) * i / steps
        dx, dy = direction(a, facing)
        pts.append((dx * length, dy * length))
    pts.append((0.0, 0.0))
    return pts


def arrow_head(tip, direction_xy, size: float):
    """Two barb endpoints (engine xy) for an arrowhead at `tip` pointing along direction_xy."""
    dx, dy = direction_xy
    px, py = -dy, dx
    back = (tip[0] - dx * size, tip[1] - dy * size)
    return ((back[0] + px * size * 0.5, back[1] + py * size * 0.5),
            (back[0] - px * size * 0.5, back[1] - py * size * 0.5))


def badges(record: dict) -> list[str]:
    """Short tags for the non-default properties of a source/engine hitbox record."""
    out: list[str] = []
    element = record.get("element")
    if isinstance(element, int) and not isinstance(element, bool) and element:
        out.append(ELEMENT_NAMES.get(element, "element %d" % element))
    air, ground = record.get("hit_air"), record.get("hit_ground")
    if air is False and ground is not False:
        out.append("ground only")
    elif ground is False and air is not False:
        out.append("air only")
    fkb = record.get("fkb", record.get("wbk", 0)) or 0
    if fkb:
        out.append("set kb %d" % fkb)
    try:
        if float(record.get("damage", 1)) == 0:
            out.append("windbox")
    except (TypeError, ValueError):
        pass
    shield = record.get("shield_damage")
    if shield:
        out.append("shield %+d" % shield)
    return out


def label(slot: int, damage) -> str:
    try:
        text = "%g" % float(damage)
    except (TypeError, ValueError):
        text = "?"
    return "%d · %s%%" % (int(slot), text)


def match_source(source, slot: int, frame: int):
    """The source record that owns engine `slot` at `frame`.

    A later hitbox command on the same slot replaces the earlier one (sweet then sour reuse slots, and
    the earlier record's window still runs to the move's clear), so of the records whose window holds
    `frame` the one that started last wins; ties go to the higher ordinal.
    """
    best, best_key = None, None
    for rec in source or ():
        try:
            if int(rec.get("slot", -1)) == int(slot) and int(rec["start_frame"]) <= frame <= int(rec["end_frame"]):
                key = (int(rec["start_frame"]), int(rec.get("ordinal", 0)))
                if best_key is None or key >= best_key:
                    best, best_key = rec, key
        except (KeyError, TypeError, ValueError):
            continue
    return best


def frame_bar(start: int, end: int, length: int, current: int, cells: int = 40) -> str:
    """ASCII strip of the move: '#' where the hitbox is active, '.' elsewhere, '|' at the current frame."""
    length = max(int(length), int(end), 1)
    cells = max(1, min(cells, length))
    out = []
    for c in range(cells):
        lo = 1 + c * length // cells
        hi = max(lo, (c + 1) * length // cells)
        if lo <= current <= hi:
            out.append("|")
        elif start <= hi and end >= lo:
            out.append("#")
        else:
            out.append(".")
    return "".join(out)


# ---- per-frame draw list (still pure: Blender-space points, no bpy) -------------------------------

try:
    from . import wbspace as _W
except ImportError:  # run from the test directory
    import wbspace as _W


def _bl(p):
    return _W.to_blender_point((p[0], p[1], p[2]))


def _xyz(v):
    return (float(v["x"]), float(v["y"]), float(v.get("z", 0.0)))


def build_items(info, prev_info, source, frame, percent=0, weight=DEFAULT_WEIGHT, flags=None):
    """One dict per active hitbox of `info`: sphere, label, badges, launch arrow / fan, sweep.

    `source` is the move's source records (list_hitboxes); engine fields join by (slot, frame). Absent
    fields are simply not drawn. `prev_info` is the previous logic frame (or None) for the swept capsule.
    Points are Blender-space tuples; `lines` are (p0, p1) pairs.
    """
    flags = flags or {}
    facing = info.get("facing")
    if facing is None:
        facing = (info.get("root") or {}).get("facing", 1)
    facing = -1 if facing is not None and facing < 0 else 1
    prev_by_slot = {}
    for hit in (prev_info or {}).get("hitboxes", []) or []:
        if hit.get("active", True) and "world" in hit:
            prev_by_slot[hit["slot"]] = hit
    items = []
    for hit in info.get("hitboxes", []) or []:
        if not hit.get("active", True) or "world" not in hit or "slot" not in hit:
            continue
        slot = int(hit["slot"])
        world = _xyz(hit["world"])
        rec = match_source(source, slot, frame) or {}
        merged = dict(rec)
        merged.update({k: v for k, v in hit.items() if k in ("damage", "angle", "kbg", "bkb", "fkb", "wbk",
                                                              "element", "shield_damage", "hit_air", "hit_ground")})
        item = {
            "slot": slot, "centre": _bl(world), "radius": float(hit.get("radius", 0.0)),
            "rgb": slot_rgb(slot), "lines": [], "fan": [], "meteor": False, "kb": None, "kind": "none",
            "label": label(slot, merged["damage"]) if "damage" in merged else "slot %d" % slot,
            "badges": badges(merged) if merged else [], "sweep": None, "angle": merged.get("angle"),
        }
        prev = prev_by_slot.get(slot)
        if prev is not None:
            a, b = _xyz(prev["world"]), world
            if math.dist(a, b) > 1e-4:
                item["sweep"] = (_bl(a), _bl(b))
        if "angle" in merged and "kbg" in merged and "bkb" in merged and "damage" in merged:
            angle = int(merged["angle"])
            kb = knockback(merged["damage"], merged["kbg"], merged["bkb"], merged.get("fkb", merged.get("wbk", 0)) or 0,
                           percent, weight)
            kind = classify_angle(angle)
            low, high, resolved = angle_span(angle, kb)
            item.update(kb=kb, kind=kind, meteor=(kind == "meteor"))
            if kind == "meteor":
                item["badges"] = item["badges"] + ["meteor"]
            if kind == "special":
                item["badges"] = item["badges"] + ["angle %d" % angle]
            if resolved is not None:
                length = arrow_length(kb)
                origin = (world[0], world[1])
                d = direction(resolved, facing)
                tip = (origin[0] + d[0] * length, origin[1] + d[1] * length)
                z = world[2]
                item["lines"].append(((origin[0], origin[1], z), (tip[0], tip[1], z)))
                for barb in arrow_head(tip, d, max(1.0, length * 0.25)):
                    item["lines"].append(((tip[0], tip[1], z), (barb[0], barb[1], z)))
                if kind == "sakurai":
                    pts = fan_points(low, high, facing, length)
                    item["fan"] = [((origin[0] + p[0], origin[1] + p[1], z), (origin[0] + q[0], origin[1] + q[1], z))
                                   for p, q in zip(pts, pts[1:])]
                item["lines"] = [(_bl(p), _bl(q)) for p, q in item["lines"]]
                item["fan"] = [(_bl(p), _bl(q)) for p, q in item["fan"]]
        items.append(item)
    items.sort(key=lambda i: i["slot"])
    return items
