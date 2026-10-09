"""Geno combo graph (geno 11; game docs/geno.md section 25): the checks `tools.geno check` runs on a define's "combo" block,
and a text view of the graph.

    python -m tools.geno.combo <mod>/geno.json      print each fighter's routes and strings, with the check's findings

The engine (melee/pc/platform/geno_combo_registry.inc) refuses what it cannot load; these checks add what it cannot see:
strings whose steps have no route, routes shadowed by an earlier route with the same trigger, input-less routes, loops.
"""
import json
import sys
from pathlib import Path

SRC = "melee/pc/platform/geno_combo_registry.inc"
MOVES = {"jab1": [44], "jab2": [45], "jab3": [46], "rapid_jab": [47, 48, 49], "dash_attack": [50], "ftilt": [53],
         "ftilt_any": [51, 52, 53, 54, 55], "utilt": [56], "dtilt": [57], "fsmash": [60], "fsmash_any": [58, 59, 60, 61, 62],
         "usmash": [63], "dsmash": [64], "nair": [65], "fair": [66], "bair": [67], "uair": [68], "dair": [69], "grab": [212],
         "dash_grab": [214], "fthrow": [219], "bthrow": [220], "uthrow": [221], "dthrow": [222]}
ACTS = ["special_n", "special_s", "special_hi", "special_lw", "jump", "nair", "fair", "bair", "uair", "dair"]


def node_keys(value, states):
    """The source keys a node names ('m44', 'g:Light2', '*'); raises ValueError for an unknown node."""
    if value == "*":
        return ["*"]
    if isinstance(value, int):
        return [f"m{value}"]
    s = str(value)
    low = s.lower()
    if low in MOVES:
        return [f"m{m}" for m in MOVES[low]]
    if low.startswith("motion:"):
        return [f"m{int(s[7:], 0)}"]
    if low.startswith("geno:"):
        name = s[5:]
        if name.isdigit():
            if int(name) >= len(states):
                raise ValueError(f"no state {name}")
            return [f"g:{states[int(name)]}"]
        for st in states:
            if st.lower() == name.lower():
                return [f"g:{st}"]
        raise ValueError(f"no state named {name!r}")
    if low in ACTS:
        return [f"a:{low}"]
    if low in ("auto", "helpless"):
        return [low]
    raise ValueError(f"{s!r} is not a move name, geno:<state>, motion:N or *")


def to_key(value, states):
    return node_keys(value, states)[0]


def checks(data, fighter, p, base, errors, warnings, diag):
    combo = fighter.get("combo")
    if combo is None:
        return
    if "define" not in fighter:
        errors.append(diag(p + ".combo", "a combo graph is for a define; an attach entry cannot carry it", SRC))
        return
    if data.get("geno", 0) < 11:
        errors.append(diag(p + ".combo", 'combo needs "geno": 11', SRC))
    states = [s.get("name", "") for s in fighter.get("states", [])]
    slots = set((fighter.get("lua") or {}).get("state", {}) or {})
    routes = combo.get("routes", [])
    max_links = combo.get("max_links", 5)
    edges = {}
    seen = {}
    expanded = 0
    for j, r in enumerate(routes):
        rp = f"{p}.combo.routes[{j}]"
        name = r.get("name", f"route{j}")
        froms = r.get("from")
        froms = froms if isinstance(froms, list) else [froms]
        src = []
        for f in froms:
            try:
                src += node_keys(f, states)
            except (ValueError, TypeError) as e:
                errors.append(diag(rp + ".from", str(e), SRC))
        try:
            dst = to_key(r.get("to"), states)
        except (ValueError, TypeError) as e:
            errors.append(diag(rp + ".to", str(e), SRC))
            continue
        expanded += len(src)
        w = r.get("window", [1, 0])
        if r.get("input", "light") == "none" and r.get("on", "hit") == "any" and w[1] == 0:
            errors.append(diag(rp, "an input-less route needs a condition or a closed window", SRC))
        if "when" in r and r["when"].get("slot") not in slots:
            errors.append(diag(rp + ".when.slot", f"{r['when'].get('slot')!r} is not a slot of lua.state", SRC))
        if r.get("ki_cost", 0) > (combo.get("ki") or {}).get("max", 100):
            errors.append(diag(rp + ".ki_cost", "costs more than the meter can hold: the route can never fire", SRC))
        for s in src:
            edges.setdefault(s, []).append((dst, name))
            trig = (s, r.get("input"), r.get("dir", "any"), r.get("on", "hit"), r.get("where", "any"), r.get("hold", 0),
                    json.dumps(r.get("when")), r.get("ki_min", 0), r.get("ki_cost", 0))
            prev = seen.get(trig)
            lo, hi = w[0], w[1] or 10**9
            if prev and prev[1] <= hi and lo <= prev[2] and prev[3] >= r.get("priority", 0):
                warnings.append(diag(rp, f"route {name!r} is shadowed by route {prev[0]!r} (same source and trigger, overlapping window, not lower priority)", SRC))
            seen.setdefault(trig, (name, lo, hi, r.get("priority", 0)))
    if expanded > 128:
        errors.append(diag(p + ".combo.routes", f"{expanded} routes after expanding from-lists; the engine holds 128 (GENO_COMBO_MAX_ROUTES)", SRC))
    for k, s in enumerate(combo.get("strings", [])):
        sp = f"{p}.combo.strings[{k}]"
        steps = s.get("steps", [])
        if len(steps) - 1 > max_links:
            errors.append(diag(sp, f"{len(steps) - 1} links but max_links is {max_links}: the string cannot finish", SRC))
        for a, b in zip(steps, steps[1:]):
            try:
                ka, kb = node_keys(a, states), to_key(b, states)
            except (ValueError, TypeError) as e:
                errors.append(diag(sp, str(e), SRC))
                continue
            if not any(dst == kb for x in ka + ["*"] for dst, _ in edges.get(x, [])):
                errors.append(diag(sp, f"string {s.get('name')!r}: no route from {a!r} to {b!r}", SRC))
    # loops are legal (max_links bounds them); reported so a designer sees them
    reported = set()
    for s0 in list(edges):
        stack, visited = [(s0, [s0])], set()
        while stack:
            n, trail = stack.pop()
            for dst, _name in edges.get(n, []):
                if dst == s0:
                    key = frozenset(trail)
                    if key not in reported:
                        reported.add(key)
                        warnings.append(diag(p + ".combo", f"loop {' -> '.join(trail + [dst])}: bounded by max_links {max_links}", SRC))
                elif dst not in visited and dst in edges and len(trail) < 8:
                    visited.add(dst)
                    stack.append((dst, trail + [dst]))


def referenced_states(fighter):
    """Geno state names a combo graph enters (for the unreachable-state check)."""
    out = set()
    for r in (fighter.get("combo") or {}).get("routes", []):
        t = str(r.get("to", ""))
        if t.lower().startswith("geno:"):
            out.add(t[5:])
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__)
        return 2
    path = Path(argv[0])
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    rc = 0
    for i, f in enumerate(data.get("fighters", [])):
        c = f.get("combo")
        if not c:
            continue
        errors, warnings = [], []
        checks(data, f, f"$.fighters[{i}]", path.parent, errors, warnings, lambda p, m, s=SRC: {"path": p, "message": m})
        print(f"{(f.get('define') or {}).get('name', i)}: {len(c.get('routes', []))} routes, max_links {c.get('max_links', 5)}, ki {c.get('ki')}")
        for r in c.get("routes", []):
            print(f"  {r.get('name', '?'):<22} {str(r.get('from')):<34} -> {str(r.get('to')):<18} {r.get('input')}/{r.get('dir', 'any')}"
                  f" on {r.get('on', 'hit')} {r.get('where', 'any')} window {r.get('window', [1, 0])} prio {r.get('priority', 0)}")
        for s in c.get("strings", []):
            print(f"  string {s['name']}: {' > '.join(map(str, s['steps']))}")
        for e in errors:
            print("  ERROR", e["path"], e["message"])
            rc = 1
        for w in warnings:
            print("  warning", w["path"], w["message"])
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
