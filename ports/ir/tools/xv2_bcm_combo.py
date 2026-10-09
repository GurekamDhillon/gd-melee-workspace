"""XV2 BCM -> Geno combo graph draft (geno 11, game docs/geno.md section 25).

    python ports/ir/tools/xv2_bcm_combo.py --ir ports/goku-xv2/ir/goku.xv2.ir.json \
        [--movemap _build/goku-xv2/movemap/movemap.json] [--root 0/18] [--scope chara/GOK/GOK_PLAYER.bcm] \
        --out _build/goku-xv2/combo/bcm-draft.json

Reads the shared character IR's BCM tree (behavior.actions: every node, its input mask and BAC bindings) and, when given, the
movemap (decoded activator conditions, direction, ki/stamina, loop durations, and each BAC entry's static timeline with its
cancel windows). Writes a DRAFT: one candidate state per BAC entry the walk reaches, one candidate route per parent -> child
BCM edge, with the source node id, the parent's BAC cancel window as the route window, and every condition the Melee engine
cannot express listed under "unmapped". Nothing here is executed XV2 behaviour: BCM conditions are decoded, not run, and BAC
frames are the exporter's static 60 fps convention. A designer turns the draft into routes (the Goku package keeps its
authored routes with the BCM node and BAC window each came from).

Output stays local (source-derived names and frame data): write it under _build/, never commit it.
"""
import argparse
import collections
import json
from pathlib import Path

INPUT_BITS = {1: "light", 2: "heavy", 4: "special", 8: "jump", 16: "shield", 32: "special"}  # Light, Heavy, Blast, Jump, Guard, skills
LABEL_INPUT = {"Light": "light", "Heavy": "heavy", "Jump": "jump", "Blast": "special", "Guard": "shield", "SuperSkill1": "special",
               "SuperSkill2": "special", "SuperSkill3": "special", "SuperSkill4": "special", "UltimateSkill1": "special",
               "UltimateSkill2": "special", "EvasiveSkill": "special"}
# BCM activator / state flags -> what the Melee combo engine can express
MAPPED_COND = {"OnAttackHit": ("on", "hit"), "AttackBlocked": ("on", "block"), "Standing": ("where", "ground"),
               "TouchingGround": ("where", "ground"), "Ground": ("where", "ground"), "Floating": ("where", "air"),
               "Jumping": ("where", "air")}
DROPPED_COND = {"CloseToTarget": "distance to the lock-on target (no lock-on in Melee)",
                "FarFromTarget": "distance to the lock-on target (no lock-on in Melee)",
                "TargetingOpponent": "lock-on", "InTransformedState": "transformation state (not modelled)",
                "OpponentKnockback": "the target's knockback state (the victim's state is never a condition)",
                "TargetIsAttacking": "the target's state", "Opponent": "target relation", "Boosting": "boost/flight (dropped)",
                "Guarding": "guard state (a route source is a move)", "ReceivingDamage": "being hit (Melee's hitstun rules)",
                "NotReceivingDamage": "implicit (a route runs only in the source move)", "Idle": "implicit (a starter is a Melee neutral input)",
                "Attacking": "implicit", "KiBelow100": "ki below 100 (expressible as a Lua gate, not imported)",
                "CurrentBacEntryHits": "per-entry hit count", "SingleActivation": "once per string (\"once\")"}
DIRS = {"Forward": "forward", "Backwards": "back", "Up": "up", "Down": "down"}


def flags(text):
    return [t.strip() for t in str(text or "0").split(",") if t.strip() and t.strip() != "0"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ir", required=True, type=Path)
    ap.add_argument("--movemap", type=Path)
    ap.add_argument("--scope", default="chara/GOK/GOK_PLAYER.bcm")
    ap.add_argument("--root", action="append", help="BCM node path(s) to walk (default: every root of the scope)")
    ap.add_argument("--depth", type=int, default=12)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)
    ir = json.loads(args.ir.read_text(encoding="utf-8"))
    actions = {a["id"]: a for a in ir["behavior"]["actions"]}
    mm = json.loads(args.movemap.read_text(encoding="utf-8")) if args.movemap else {"bcm": {}, "moves": []}
    decoded = mm.get("bcm", {})
    timelines = {m["id"]: m for m in mm.get("moves", [])}
    prefix = f"action:{args.scope}/"

    def node_path(aid):
        return aid[len(prefix):]

    def bac_of(a):
        b = a.get("engine", {}).get("xv2.pc", {}).get("bac_bindings", {}).get("BacEntryPrimary")
        v = b["index"]["value"] if b else 0
        return v or None

    roots = [prefix + r for r in args.root] if args.root else [
        k for k, a in actions.items() if k.startswith(prefix) and a.get("engine", {}).get("xv2.pc", {}).get("parent") not in actions]
    states, routes, unmapped = {}, [], collections.Counter()
    seen = set()

    def state_for(bac):
        sid = f"subaction:{args.scope.replace('.bcm', '.bac')}/{bac}"
        if bac not in states:
            t = timelines.get(sid, {})
            tl = t.get("timeline", {})
            states[bac] = {"bac": bac, "clip": t.get("clip"), "length": t.get("length"),
                           "hits": [[h["frame"], h["dur"]] for h in tl.get("hit", [])],
                           "cancel": [[c["frame"], c["dur"]] for c in tl.get("cancel", [])],
                           "lost": sorted(k for k in tl.get("other", {}) if k in ("engine.tracking", "engine.homing_movement", "engine.targeting_assistance", "engine.camera"))}
        return states[bac]

    def walk(aid, parent_bac, parent_path, depth):
        a = actions.get(aid)
        if a is None or depth > args.depth:
            return
        bac = bac_of(a)
        path = node_path(aid)
        dec = decoded.get(f"{args.scope}#{path}", {})
        if bac is not None and parent_bac is not None and (aid, parent_bac) not in seen:
            seen.add((aid, parent_bac))
            ps = state_for(parent_bac)
            state_for(bac)
            route = {"source": f"BCM {args.scope}#{path}", "from_bac": parent_bac, "to_bac": bac}
            label = dec.get("input") or a.get("name")
            ins = [LABEL_INPUT.get(x) for x in flags(label)]
            route["input"] = ins[0] if ins and ins[0] else None
            if len(ins) > 1:
                route.setdefault("unmapped", []).append(f"chord input {label!r} (Melee: one class per route)")
            for d in flags(dec.get("dir")):
                if d in DIRS:
                    route["dir"] = DIRS[d]
                elif d == "SingleActivation":
                    route["once"] = True
                else:
                    route.setdefault("unmapped", []).append(f"direction {d!r}")
            for c in flags(dec.get("cond")) + flags(dec.get("state")):
                if c in MAPPED_COND:
                    k, v = MAPPED_COND[c]
                    if k == "on" and route.get("on") == "hit" and v == "block":
                        route["on"] = "contact"
                    else:
                        route.setdefault(k, v)
                else:
                    route.setdefault("unmapped", []).append(f"condition {c!r}: {DROPPED_COND.get(c, 'not expressible')}")
            route.setdefault("on", "any")
            for k in ("ki", "stamina", "health"):
                if dec.get(k):
                    route.setdefault("unmapped" if k != "ki" else "ki_note", []).append(f"{k} {dec[k]}")
            if dec.get("loop") and any(dec["loop"]):
                route.setdefault("unmapped", []).append(f"loop {dec['loop']} (hold/repeat duration)")
            if ps["cancel"]:
                # the parent's cancel windows (BAC frames, 0-based) -> 1-based action frames: the first window that opens at or
                # after the parent's first hit; else the last
                hit0 = ps["hits"][0][0] if ps["hits"] else 0
                win = next((c for c in ps["cancel"] if c[0] >= hit0), ps["cancel"][-1])
                route["window"] = [win[0] + 1, win[0] + win[1]]
            else:
                route.setdefault("unmapped", []).append("parent BAC has no cancel window")
            for u in route.get("unmapped", []):
                unmapped[u.split(":")[0]] += 1
            routes.append(route)
        for child in dict.fromkeys(a.get("enters", [])):
            walk(child, bac if bac is not None else parent_bac, path, depth + 1)

    for r in roots:
        walk(r, None, "", 0)
    draft = {"schema": "geno-combo-draft/1", "scope": args.scope, "roots": [node_path(r) for r in roots],
             "caveat": "Draft from static data: BCM conditions decoded, not executed; BAC frames at the exporter's 60 fps convention. "
                       "Source-derived: keep under _build, never commit.",
             "states": [states[k] for k in sorted(states)], "routes": routes,
             "unmapped_summary": dict(unmapped.most_common())}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(draft, indent=1) + "\n", encoding="utf-8")
    print(f"{len(states)} BAC entries, {len(routes)} candidate routes, {sum(1 for r in routes if r.get('unmapped'))} with unmapped conditions -> {args.out}")
    for k, n in unmapped.most_common(12):
        print(f"  unmapped {n:5d}  {k}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
