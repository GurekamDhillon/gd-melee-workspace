"""Projectiles (Geno articles) as parts of a fighter: the pure half (no bpy).

An article is an entry of a fighter's ``"articles"`` list (geno.md section 19.2; the Goku package keeps it
in ``gameplay.json``).  This module is the data model behind the Blender "Projectiles" collection, the
Workbench server's ``list_articles`` / ``edit_article`` commands and the ghost trajectory:

* ``FIELDS`` / ``HITBOX_FIELDS``: every editable key, its engine default (geno.md 19.2, the schema's
  ``x-engine-default``) and its type.  Keys the table does not know are never touched: an edit starts from
  the article exactly as the source has it.
* ``diff_ops(old, new)`` / ``apply_ops(article, ops)``: the edit as path operations.  ``set`` writes one leaf
  (inserting the key when missing), ``insert`` / ``remove`` change an array.  An unchanged article gives no
  ops, so import then export is a no-op on the bytes.
* ``step`` / ``trajectory``: the article's flight, a line-for-line port of the engine's motion
  (``GenoGame_ArticleStep``, melee/pc/geno/geno_game_articles.inc; the spawn velocity from
  ``geno_art_spawn`` in the same file).
* spawn arguments (``CALL geno.article.spawn N``): ``[7:0]`` article, ``[15:8]`` variant, ``[31:16]`` signed
  extra angle in degrees (``GenoGame_ArticleSpawn``).
"""
from __future__ import annotations

import copy
import json
import math

# --- field tables -------------------------------------------------------------------------------------
# (path, default, kind).  kind: int, float, bool, str.  Paths are "/"-separated; "#N" is an array index.
FIELDS = [
    ("name", "", "str"),
    ("model/file", "", "str"),
    ("model/symbol", "", "str"),
    ("scale", 1.0, "float"),
    ("spin", 0.0, "float"),
    ("lifetime", 60, "int"),
    ("spawn/#0", 0.0, "float"),
    ("spawn/#1", 0.0, "float"),
    ("bone", -1, "int"),
    ("velocity/#0", 0.0, "float"),
    ("velocity/#1", 0.0, "float"),
    ("angle", 0.0, "float"),
    ("gravity", 0.0, "float"),
    ("max_fall", 0.0, "float"),
    ("accel", 0.0, "float"),
    ("max_speed", 0.0, "float"),
    ("min_speed", 0.0, "float"),
    ("homing/turn", 0.0, "float"),
    ("homing/range", 0.0, "float"),
    ("homing/delay", 0, "int"),
    ("max_live", 4, "int"),
    ("despawn/hit", True, "bool"),
    ("despawn/shield", True, "bool"),
    ("despawn/stage", True, "bool"),
    ("despawn/clank", True, "bool"),
    ("effect", 0, "int"),
    ("fx", "", "str"),
    ("show_model", False, "bool"),
    ("spawn_sound", "", "str"),
    ("end_sound", "", "str"),
]
HITBOX_FIELDS = [
    ("slot", None, "int"),            # default: the entry's index mod 4
    ("damage", 1.0, "float"),
    ("size", 3.0, "float"),
    ("offset/#0", 0.0, "float"),
    ("offset/#1", 0.0, "float"),
    ("offset/#2", 0.0, "float"),
    ("angle", 361, "int"),
    ("kbg", 100, "int"),
    ("wkb", 0, "int"),
    ("bkb", 0, "int"),
    ("element", 0, "int"),
    ("shield_damage", 0, "int"),
    ("sfx_severity", 1, "int"),
    ("sfx_kind", 0, "int"),
    ("start", 1, "int"),
    ("end", 0, "int"),
    ("stun", 0, "int"),
    ("hits/ground", True, "bool"),
    ("hits/air", True, "bool"),
    ("hits/reflect", True, "bool"),
    ("hits/absorb", True, "bool"),
    ("hits/counter", True, "bool"),
]
MAX_HITBOXES = 4  # Melee's item limit (geno.md 19.2); entries beyond share slots via "slot" (19.8)

_FIELD_DEFAULT = {p: d for p, d, _ in FIELDS}
_FIELD_KIND = {p: k for p, _, k in FIELDS}
_HB_DEFAULT = {p: d for p, d, _ in HITBOX_FIELDS}
_HB_KIND = {p: k for p, _, k in HITBOX_FIELDS}


# --- paths ----------------------------------------------------------------------------------------------
def _split(path: str):
    return [p for p in path.split("/") if p != ""]


def get_path(obj, path: str, missing=None):
    cur = obj
    for part in _split(path):
        if part.startswith("#"):
            i = int(part[1:])
            if not isinstance(cur, list) or i >= len(cur):
                return missing
            cur = cur[i]
        else:
            if not isinstance(cur, dict) or part not in cur:
                return missing
            cur = cur[part]
    return cur


def _container(obj, parts, create, leaf_is_index=False):
    cur = obj
    for n, part in enumerate(parts):
        nxt_is_index = parts[n + 1].startswith("#") if n + 1 < len(parts) else leaf_is_index
        if part.startswith("#"):
            i = int(part[1:])
            while create and isinstance(cur, list) and i >= len(cur):
                cur.append(0)
            cur = cur[i]
        else:
            if part not in cur:
                if not create:
                    raise KeyError(part)
                cur[part] = [] if nxt_is_index else {}
            cur = cur[part]
    return cur


def set_path(obj, path: str, value) -> None:
    parts = _split(path)
    last = parts[-1]
    parent = _container(obj, parts[:-1], True, last.startswith("#"))
    if last.startswith("#"):
        i = int(last[1:])
        while i >= len(parent):
            parent.append(0)
        parent[i] = value
    else:
        parent[last] = value


# --- values ----------------------------------------------------------------------------------------------
def _cast(value, kind):
    if kind == "bool":
        return bool(value)
    if kind == "int":
        return int(round(float(value)))
    if kind == "float":
        return float(value)
    return str(value)


def effective(article: dict, path: str, kind_default=None):
    """The value the engine would use: the article's own, else the default."""
    got = get_path(article, path, None)
    if got is not None:
        return got
    return _FIELD_DEFAULT.get(path, kind_default)


def hitbox_effective(hb: dict, path: str, index: int = 0):
    got = get_path(hb, path, None)
    if got is not None:
        return got
    if path == "slot":
        return index % MAX_HITBOXES
    return _HB_DEFAULT.get(path)


def _same(a, b, kind) -> bool:
    if kind in ("float",):
        return math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-9)
    if kind == "bool":
        return bool(a) == bool(b)
    return a == b


def flatten(article: dict) -> dict:
    """Editable view: {path: effective value} for the article and ``hitboxes`` as a list of such dicts."""
    out = {p: effective(article, p) for p, _, _ in FIELDS}
    out["hitboxes"] = [
        {p: hitbox_effective(hb, p, i) for p, _, _ in HITBOX_FIELDS} for i, hb in enumerate(article.get("hitboxes", []))
    ]
    return out


def unflatten(base: dict, flat: dict) -> dict:
    """A new article: ``base`` (the source, every unknown key kept) with the flat values applied.

    A value that equals what the article already means (its own value, or the default of an absent key) is
    not written, so an unchanged view reproduces ``base`` exactly (same keys, same order, same numbers).
    """
    art = copy.deepcopy(base)
    for path, _, kind in FIELDS:
        if path not in flat:
            continue
        new = _cast(flat[path], kind)
        if _same(effective(art, path), new, kind):
            continue
        set_path(art, path, _json_number(new, kind))
    if "hitboxes" in flat:
        boxes = art.setdefault("hitboxes", [])
        want = flat["hitboxes"]
        del boxes[len(want):]
        for i, fh in enumerate(want):
            if i >= len(boxes):
                boxes.append({})
            hb = boxes[i]
            for path, _, kind in HITBOX_FIELDS:
                if path not in fh:
                    continue
                new = _cast(fh[path], kind)
                if _same(hitbox_effective(hb, path, i), new, kind):
                    continue
                set_path(hb, path, _json_number(new, kind))
        if not boxes and "hitboxes" not in base:
            del art["hitboxes"]
    return art


def _json_number(value, kind):
    if kind == "float" and float(value).is_integer() and abs(value) < 1e15:
        return float(value)
    return value


# --- edits as operations ------------------------------------------------------------------------------------
def diff_ops(old: dict, new: dict) -> list:
    """Operations turning ``old`` into ``new`` (both full article dicts); [] when they are equal.

    ``{"op":"set","path":"velocity/#0","value":3.5}`` writes a leaf (inserting a missing key),
    ``{"op":"insert","path":"hitboxes","at":2,"value":{...}}`` / ``{"op":"remove","path":"hitboxes","at":2}`` change an array.
    Only leaves that differ are written; hitboxes beyond the common length are inserted or removed from the end.
    """
    ops: list = []
    _diff(old, new, "", ops)
    return ops


def _diff(a, b, path, ops):
    if isinstance(a, dict) and isinstance(b, dict):
        for key in b:
            sub = f"{path}/{key}" if path else key
            if key not in a:
                ops.append({"op": "set", "path": sub, "value": copy.deepcopy(b[key])})
            else:
                _diff(a[key], b[key], sub, ops)
        for key in a:
            if key not in b:
                ops.append({"op": "unset", "path": f"{path}/{key}" if path else key})
        return
    if isinstance(a, list) and isinstance(b, list):
        common = min(len(a), len(b))
        for i in range(common):
            _diff(a[i], b[i], f"{path}/#{i}", ops)
        for i in range(len(a) - 1, common - 1, -1):
            ops.append({"op": "remove", "path": path, "at": i})
        for i in range(common, len(b)):
            ops.append({"op": "insert", "path": path, "at": i, "value": copy.deepcopy(b[i])})
        return
    if a != b or type(a) is not type(b) and not (isinstance(a, (int, float)) and isinstance(b, (int, float)) and a == b):
        ops.append({"op": "set", "path": path, "value": copy.deepcopy(b)})


def apply_ops(article: dict, ops: list) -> dict:
    """Reference implementation of the server's ``edit_article`` (the C++ command must agree with it)."""
    art = copy.deepcopy(article)
    for op in ops:
        kind = op["op"]
        if kind == "set":
            set_path(art, op["path"], copy.deepcopy(op["value"]))
        elif kind == "insert":
            arr = get_path(art, op["path"], None)
            if arr is None:
                set_path(art, op["path"], [])
                arr = get_path(art, op["path"])
            if not 0 <= op["at"] <= len(arr):
                raise IndexError("insert position out of range")
            arr.insert(op["at"], copy.deepcopy(op["value"]))
        elif kind == "remove":
            arr = get_path(art, op["path"], None)
            if arr is None or not 0 <= op["at"] < len(arr):
                raise IndexError("remove position out of range")
            del arr[op["at"]]
        elif kind == "unset":
            parts = _split(op["path"])
            parent = _container(art, parts[:-1], False)
            parent.pop(parts[-1], None)
        else:
            raise ValueError("unknown op " + str(kind))
    return art


def canonical(article: dict) -> str:
    return json.dumps(article, sort_keys=False, separators=(",", ":"))


# --- finding the articles in a document ----------------------------------------------------------------------
def articles_of(doc: dict) -> list:
    """The articles of a gameplay.json (top level ``articles``) or a geno.json (``fighters[0].articles``)."""
    if isinstance(doc.get("articles"), list):
        return doc["articles"]
    fighters = doc.get("fighters")
    if isinstance(fighters, list):
        for f in fighters:
            if isinstance(f, dict) and isinstance(f.get("articles"), list):
                return f["articles"]
    return []


# --- spawn argument --------------------------------------------------------------------------------------------
def decode_spawn_arg(arg: int):
    """(article, variant, extra_angle_degrees) from a ``geno.article.spawn`` argument."""
    arg &= 0xFFFFFFFF
    angle = (arg >> 16) & 0xFFFF
    if angle >= 0x8000:
        angle -= 0x10000
    return arg & 0xFF, (arg >> 8) & 0xFF, angle


def encode_spawn_arg(article: int, variant: int = 0, angle: int = 0) -> int:
    return (article & 0xFF) | ((variant & 0xFF) << 8) | ((angle & 0xFFFF) << 16)


# --- the flight ------------------------------------------------------------------------------------------------
def spawn_offset(article: dict, variant: int = 0):
    """(forward, up) from the owner (or bone), as ``geno_art_spawn``: ``spawns`` variants first, else ``spawn``."""
    spawns = article.get("spawns")
    if isinstance(spawns, list) and spawns:
        v = variant if 0 < variant < len(spawns) else 0
        s = spawns[v]
        return float(s[0]), float(s[1])
    s = article.get("spawn", [0, 0])
    return float(s[0]), float(s[1] if len(s) > 1 else 0)


def initial_velocity(article: dict, facing: int = 1, extra_angle: float = 0.0):
    """geno_art_spawn: the velocity [forward, up] turned up by ``angle`` + the spawn argument's angle."""
    vel = article.get("velocity", [0, 0])
    vf, vu = float(vel[0]), float(vel[1] if len(vel) > 1 else 0)
    rad = (float(article.get("angle", 0)) + extra_angle) * math.pi / 180.0
    c, s = math.cos(rad), math.sin(rad)
    return facing * (vf * c - vu * s), vf * s + vu * c


def step(article: dict, frame: int, vx: float, vy: float, px: float = 0.0, py: float = 0.0, target=None):
    """One frame of travel: GenoGame_ArticleStep, same order (accel/brake, homing, gravity, fall cap, speed cap)."""
    g = lambda k, d=0.0: float(effective(article, k, d))  # noqa: E731
    grav, mf = g("gravity"), g("max_fall")
    acc, ms, mn = g("accel"), g("max_speed"), g("min_speed")
    turn, rng, delay = g("homing/turn"), g("homing/range"), g("homing/delay")
    speed = math.hypot(vx, vy)
    if acc != 0.0 and speed > 0.0001:
        ns = speed + acc
        if acc < 0.0 and ns < mn:
            ns = speed if speed < mn else mn
        if ns < 0.0:
            ns = 0.0
        vx *= ns / speed
        vy *= ns / speed
        speed = ns
    if turn > 0.0 and target is not None and frame > delay and speed > 0.0001:
        dx, dy = target[0] - px, target[1] - py
        if rng <= 0.0 or dx * dx + dy * dy <= rng * rng:
            cur = math.atan2(vy, vx)
            d = math.atan2(dy, dx) - cur
            lim = turn * math.pi / 180.0
            while d > math.pi:
                d -= 2.0 * math.pi
            while d < -math.pi:
                d += 2.0 * math.pi
            d = max(-lim, min(lim, d))
            cur += d
            vx = speed * math.cos(cur)
            vy = speed * math.sin(cur)
    vy -= grav
    if mf > 0.0 and vy < -mf:
        vy = -mf
    if ms > 0.0:
        speed = math.hypot(vx, vy)
        if speed > ms:
            vx *= ms / speed
            vy *= ms / speed
    return vx, vy


def trajectory(article: dict, base=(0.0, 0.0), facing: int = 1, extra_angle: float = 0.0, variant: int = 0,
               frames=None, target=None):
    """Positions ``[(x, y)]`` by article life frame: index 0 = the spawn, n = after n item ticks.

    Item order (item.c): the anim callback counts the frame, the phys callback runs ``step`` and stores the
    velocity, then the engine adds it to the position (``Item_802697D4``): p[n] = p[n-1] + v[n].  The article is
    destroyed when its frame passes ``lifetime``, so ``lifetime`` is the last frame it exists.  Stage contact and
    despawn-on-hit are not simulated (the path is the free flight).
    """
    fwd, up = spawn_offset(article, variant)
    x = base[0] + facing * fwd
    y = base[1] + up
    vx, vy = initial_velocity(article, facing, extra_angle)
    n_max = int(effective(article, "lifetime")) if frames is None else int(frames)
    pts = [(x, y)]
    for n in range(1, n_max + 1):
        vx, vy = step(article, n, vx, vy, x, y, target)
        x += vx
        y += vy
        pts.append((x, y))
    return pts


def hitbox_live(article: dict, index: int, life_frame: int) -> bool:
    """Is hitbox ``index`` active at article frame ``life_frame`` (1-based; ``end`` 0 = to the end of life)."""
    hb = article.get("hitboxes", [])[index]
    start = int(hitbox_effective(hb, "start", index))
    end = int(hitbox_effective(hb, "end", index))
    last = int(effective(article, "lifetime"))
    return life_frame <= (last if end == 0 else min(end, last)) and life_frame >= start and life_frame >= 1


def hitbox_world(article: dict, index: int, root, facing: int = 1):
    """(x, y, radius) of hitbox ``index`` with the article root at ``root`` (offset is root-relative, x with facing)."""
    hb = article.get("hitboxes", [])[index]
    off = hitbox_effective  # noqa: F841 (readability)
    ox = float(hitbox_effective(hb, "offset/#0", index))
    oy = float(hitbox_effective(hb, "offset/#1", index))
    return root[0] + facing * ox, root[1] + oy, float(hitbox_effective(hb, "size", index))


def ghost_at(article: dict, spawn_frame: int, frame: int, base=(0.0, 0.0), facing: int = 1,
             extra_angle: float = 0.0, variant: int = 0):
    """What to draw while the move is scrubbed to ``frame``.

    Returns ``{"path": [(x,y)...], "life": n or None, "root": (x,y) or None, "hitboxes": [(x,y,r,slot,index)]}``;
    ``life`` is None before the spawn and after the article's last frame.  ``frame`` and ``spawn_frame`` are
    move frames (the script's ``wait`` count), the spawn happening at the end of ``spawn_frame``; life frame n is move
    frame ``spawn_frame + n``.
    """
    pts = trajectory(article, base, facing, extra_angle, variant)
    n = frame - spawn_frame
    out = {"path": pts, "life": None, "root": None, "hitboxes": []}
    last = len(pts) - 1
    if n < 0 or n > last:
        return out
    out["life"] = n
    out["root"] = pts[n]
    for i, hb in enumerate(article.get("hitboxes", [])):
        if hitbox_live(article, i, n):
            x, y, r = hitbox_world(article, i, pts[n], facing)
            out["hitboxes"].append((x, y, r, int(hitbox_effective(hb, "slot", i)), i))
    return out


def summary(article: dict) -> str:
    """One line for a list: name, lifetime, speed, hits."""
    vel = article.get("velocity", [0, 0])
    spd = math.hypot(float(vel[0]), float(vel[1] if len(vel) > 1 else 0))
    dmg = ",".join("%g" % float(h.get("damage", 1)) for h in article.get("hitboxes", []))
    return "%s  life %s  speed %.2f  dmg %s" % (article.get("name", "?"), effective(article, "lifetime"), spd, dmg or "-")
