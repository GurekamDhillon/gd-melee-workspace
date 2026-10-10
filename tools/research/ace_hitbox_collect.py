#!/usr/bin/env python3
"""Summarise gd.timeline dumps (hitbox_timeline_dump.lua / ace_hitbox_batch.sh) into hitbox-type tables.

    python tools/research/ace_hitbox_collect.py DUMPDIR [--json OUT.json] [--fighter NAME] [--diff]

DUMPDIR holds <name>.jsonl files (one line per motion; first line is {"head":...}). Reads only; writes
nothing unless --json is given (the JSON is gameplay numbers, but keep it out of git anyway).

Raw hitbox words are decoded here with the layout in melee src/melee/lb/types.h (spawn_hitbox_0..5),
so fields the Lua decoder does not expose (clank, rebound, sfx severity/kind, only_hit_grabbed,
item interaction, ignore_fighter_scale, ignore_thrown) are reported too.

--diff compares ace_ck<N> against van_ck<N> (retail fighters on the two discs).
"""
import argparse
import collections
import glob
import json
import os


def sbits(v, lsb, w):
    x = (v >> lsb) & ((1 << w) - 1)
    return x - (1 << w) if x >> (w - 1) else x


def ubits(v, lsb, w):
    return (v >> lsb) & ((1 << w) - 1)


def decode_hit(e):
    w = e["words"]
    d = dict(frame=e["frame"], id=e["id"], group=e["group"], bone=e["bone"], damage=e["damage"],
             size=e["size"], ox=e["ox"], oy=e["oy"], oz=e["oz"], angle=e["angle"], kbg=e["kbg"],
             wbk=e["wbk"], bkb=e["bkb"], element=e["element"], element_name=e["element_name"],
             hit_air=e["hit_air"], hit_ground=e["hit_ground"])
    d["shield_damage"] = sbits(w[4], 10, 8)           # raw layout; Lua field is compared in main()
    d["shield_damage_lua"] = e["shield_damage"]
    d["only_hit_grabbed"] = ubits(w[0], 19, 1)
    d["common_bone_ids"] = ubits(w[0], 10, 1)
    d["item_hit_interaction"] = ubits(w[3], 4, 1)
    d["ignore_thrown"] = ubits(w[3], 3, 1)
    d["ignore_fighter_scale"] = ubits(w[3], 2, 1)
    d["clank"] = ubits(w[3], 1, 1)
    d["rebound"] = ubits(w[3], 0, 1)
    d["sfx_severity"] = ubits(w[4], 7, 3)
    d["sfx_kind"] = ubits(w[4], 2, 5)
    d["w5_x0"] = ubits(w[0], 0, 0)  # placeholder keeps keys stable
    return d


def load(path):
    head, motions = None, []
    for line in open(path, encoding="utf-8"):
        d = json.loads(line)
        if "head" in d:
            head = d["head"]
        else:
            motions.append(d)
    return head, motions


import re
OWN = re.compile(r"^(Attack|Special|Catch|Throw|CliffAttack|DownAttack|Final|Swallow|Kirby)")


def is_own(name):
    """True for the fighter's own attack/special/grab/throw motions (not item swings, damage, falling hits)."""
    return bool(OWN.match(name or ""))


def classify(h):
    """Return the hitbox 'type' tags for one decoded hitbox."""
    t = []
    a = h["angle"]
    if h["damage"] == 0:
        t.append("windbox/0dmg")
    if h["wbk"] > 0:
        t.append("set-kb(wbk>0)")
    if a == 361:
        t.append("angle361")
    elif a == 0 or a == 180:
        t.append("horizontal(0/180)")
    elif 230 <= a <= 310:
        t.append("meteor/spike(230-310)")
    elif a > 361:
        t.append("angle>361(%d)" % a)
    if h["element_name"] != "normal":
        t.append("elem:" + h["element_name"])
    if h["shield_damage"]:
        t.append("shielddmg")
    if not h["hit_air"]:
        t.append("ground-only")
    if not h["hit_ground"]:
        t.append("air-only")
    if h["id"] > 3:
        t.append("id>3")
    if h["clank"] == 0:
        t.append("no-clank")
    if h["rebound"] == 0:
        t.append("no-rebound")
    if h["only_hit_grabbed"]:
        t.append("only-hit-grabbed")
    return t


def analyse_motion(m):
    """Windows: per hitbox id, (start, end) frames and later-adjustments."""
    evs = m.get("events", [])
    out = dict(motion=m["motion"], name=m["motion_name"], conditional=m.get("conditional"),
               stop=m.get("stop"), length=m.get("length"), hits=[], other=collections.Counter())
    live = {}
    wins = []
    for e in evs:
        op = e["op"]
        if op == 11:
            h = decode_hit(e)
            if h["id"] in live:   # same id re-created (multi-hit / reposition)
                live[h["id"]]["end"] = h["frame"]
                wins.append(live.pop(h["id"]))
            h["start"] = h["frame"]
            h["end"] = None
            h["adjust"] = []
            live[h["id"]] = h
            out["hits"].append(h)
        elif op in (12, 13) and e["id"] in live:
            live[e["id"]]["adjust"].append(("damage" if op == 12 else "size", e["frame"], e["value"]))
        elif op == 15 and e["id"] in live:
            live[e["id"]]["end"] = e["frame"]
            wins.append(live.pop(e["id"]))
        elif op == 16:
            for h in live.values():
                h["end"] = e["frame"]
                wins.append(h)
            live = {}
        else:
            out["other"][e["name"]] += 1
            if e["name"] in ("body_state", "hurtbox_state", "hurtboxes_state", "throw", "throw_flag",
                             "throw_flag_b0", "throw_flag_b1", "self_damage", "item_visibility",
                             "article_visibility", "air_state"):
                out.setdefault("states", []).append((e["name"], e["frame"], e.get("value"), e.get("bone")))
    for h in live.values():
        wins.append(h)
    out["windows"] = wins
    # concurrent slots at any frame: ids simultaneously live
    ev = []
    for h in out["hits"]:
        ev.append((h["start"], 1, h["id"], h))
        ev.append((h["end"] if h["end"] is not None else 1e9, -1, h["id"], h))
    ev.sort(key=lambda x: (x[0], x[1]))
    cur, peak, overlaps = {}, 0, []
    for fr, k, i, h in ev:
        if k == 1:
            cur[i] = h
            if len(cur) > 1:
                overlaps.append((fr, sorted(cur)))
        else:
            cur.pop(i, None)
        peak = max(peak, len(cur))
    out["peak_concurrent"] = peak
    out["overlaps"] = overlaps
    return out


def fighter_summary(path):
    head, motions = load(path)
    S = dict(head=head, moves=[], elements=collections.Counter(), tags=collections.Counter(),
             ops=collections.Counter(), slots=collections.Counter(), per_tag_moves=collections.defaultdict(set),
             nhit=0, shield_mismatch=0)
    for m in motions:
        for e in m.get("events", []):
            S["ops"][(e["op"], e["name"])] += 1
        a = analyse_motion(m)
        if not a["hits"] and not a.get("states"):
            continue
        S["moves"].append(a)
        for h in a["hits"]:
            S["nhit"] += 1
            S["elements"][h["element_name"]] += 1
            S["slots"][h["id"]] += 1
            if h["shield_damage"] != h["shield_damage_lua"]:
                S["shield_mismatch"] += 1
            for t in classify(h):
                S["tags"][t] += 1
                S["per_tag_moves"][t].add(a["name"])
    return S


def sig(a):
    return [(h["start"], h["id"], h["bone"], h["damage"], h["size"], h["angle"], h["kbg"], h["bkb"],
             h["wbk"], h["element"], h["shield_damage"], h["hit_air"], h["hit_ground"]) for h in a["hits"]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dump")
    ap.add_argument("--json")
    ap.add_argument("--fighter")
    ap.add_argument("--diff", action="store_true")
    a = ap.parse_args()
    files = sorted(glob.glob(os.path.join(a.dump, "*.jsonl")))
    if a.diff:
        for f in files:
            n = os.path.basename(f)
            if not n.startswith("ace_ck"):
                continue
            g = os.path.join(a.dump, "van_" + n[4:])
            if not os.path.exists(g):
                continue
            A, B = fighter_summary(f), fighter_summary(g)
            ma = {m["name"]: sig(m) for m in A["moves"]}
            mb = {m["name"]: sig(m) for m in B["moves"]}
            diffs = [k for k in sorted(set(ma) | set(mb)) if ma.get(k) != mb.get(k)]
            print("%s %s: moves ace=%d van=%d changed=%d %s" % (n[:-6], (A["head"] or {}).get("char_name"),
                  len(ma), len(mb), len(diffs), diffs[:12]))
        return
    res = {}
    for f in files:
        n = os.path.basename(f)[:-6]
        if a.fighter and a.fighter != n:
            continue
        S = fighter_summary(f)
        res[n] = S
        print("%-12s %-12s hitboxes=%-4d moves=%-3d slots=%s elements=%s mism_shield=%d" % (
            n, (S["head"] or {}).get("char_name"), S["nhit"], len(S["moves"]), dict(S["slots"]),
            dict(S["elements"]), S["shield_mismatch"]))
        print("    tags:", dict(S["tags"]))
    if a.json:
        def enc(o):
            if isinstance(o, (set, collections.Counter)):
                return sorted(o) if isinstance(o, set) else dict(o)
            return str(o)
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(res, fh, default=enc)


if __name__ == "__main__":
    main()
