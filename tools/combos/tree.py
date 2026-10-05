#!/usr/bin/env python3
"""Combo tree: measured combo-search results, one JSON file per context. See README.md.

    tree.py validate <tree.json> [...]
    tree.py merge <tree.json> <result.json|result.jsonl> [...]    (writes the tree in place; exit 2 on conflicts)
    tree.py export-lua <tree.json> [-o out.lua]                   (a table the in-game search dofiles)
    tree.py show <tree.json>

Only data the search measured in the game belongs in a tree. Plain Python 3, no dependencies.
"""
import json
import sys

FORMAT = 1
RESULTS = ("true", "broke", "whiff", "refused")
HEADER_KEYS = ("attacker", "victim", "stage", "rules", "build", "date", "start", "seed", "continuity", "victim_behaviour")


class TreeError(Exception):
    pass


def edge_key(edge):
    """Identity of an edge inside a node: its move name. The search's names carry every parameter
    (kind, delay, direction), so one name is one input program in one node."""
    return edge["move"]


def new_tree(header):
    return {"format": FORMAT, "header": dict(header), "nodes": {}}


def node_path(parent_path, edge):
    return (parent_path + "/" if parent_path else "") + edge_key(edge)


def validate(tree):
    """Raise TreeError with every problem found; return the tree if it is sound."""
    errs = []
    if not isinstance(tree, dict) or tree.get("format") != FORMAT:
        raise TreeError("format must be %d" % FORMAT)
    for k in HEADER_KEYS:
        if k not in tree.get("header", {}):
            errs.append("header.%s missing" % k)
    nodes = tree.get("nodes")
    if not isinstance(nodes, dict):
        raise TreeError("nodes must be an object keyed by path")
    for path, node in nodes.items():
        if not isinstance(node.get("situation", {}), dict):
            errs.append("%s: situation must be an object" % path)
        seen = set()
        for e in node.get("edges", []):
            where = "%s: edge %s" % (path or "<root>", e.get("move"))
            if "move" not in e:
                errs.append("%s: no move" % where)
                continue
            if e.get("result") not in RESULTS:
                errs.append("%s result %r not in %s" % (where, e.get("result"), RESULTS))
            if not isinstance(e.get("inputs", []), list):
                errs.append("%s inputs must be a list" % where)
            for s in e.get("inputs", []):
                if "f" not in s:
                    errs.append("%s input without frame f" % where)
            if e.get("result") == "true":
                for k in ("hit_frame", "damage", "victim_hitstun"):
                    if k not in e:
                        errs.append("%s true link without %s" % (where, k))
            if int(e.get("confirmed", 0)) < 1:
                errs.append("%s confirmed must be >= 1" % where)
            k = edge_key(e)
            if k in seen:
                errs.append("%s duplicate edge" % where)
            seen.add(k)
    if errs:
        raise TreeError("; ".join(errs))
    return tree


# fields that must agree when the same edge is measured again; a difference is a conflict
COMPARE = ("result", "hit_frame", "damage", "victim_hitstun")


def _differs(a, b):
    for k in COMPARE:
        x, y = a.get(k), b.get(k)
        if isinstance(x, float) or isinstance(y, float):
            if x is None or y is None or abs(float(x) - float(y)) > 0.051:
                return k
        elif x != y:
            return k
    return None


def merge(tree, result):
    """Merge `result` (a tree-shaped dict) into `tree`. Returns (merged_edges, new_edges, conflicts).
    Same edge measured the same way: confirmed += its count. Measured differently: a conflict is
    recorded on the stored edge (`conflicts` list) and the stored result is kept."""
    validate(tree)
    for k in ("attacker", "victim", "stage", "rules"):
        a, b = tree["header"].get(k), result.get("header", {}).get(k)
        if b is not None and a != b:
            raise TreeError("different context: header.%s %r vs %r" % (k, a, b))
    n_new = n_same = 0
    conflicts = []
    for path, node in result.get("nodes", {}).items():
        dst = tree["nodes"].setdefault(path, {"situation": node.get("situation", {}), "edges": []})
        if node.get("situation") and not dst.get("situation"):
            dst["situation"] = node["situation"]
        index = {edge_key(e): e for e in dst["edges"]}
        for e in node.get("edges", []):
            k = edge_key(e)
            old = index.get(k)
            if old is None:
                e = dict(e)
                e.setdefault("confirmed", 1)
                dst["edges"].append(e)
                index[k] = e
                n_new += 1
                continue
            field = _differs(old, e)
            if field is None:
                old["confirmed"] = int(old.get("confirmed", 1)) + int(e.get("confirmed", 1))
                n_same += 1
            else:
                c = {"path": path, "edge": k, "field": field, "stored": old.get(field), "new": e.get(field),
                     "new_build": result.get("header", {}).get("build")}
                old.setdefault("conflicts", []).append(c)
                conflicts.append(c)
    validate(tree)
    return n_same, n_new, conflicts


def read_results(path):
    """A result file is a tree-shaped JSON, or JSON lines {"path","situation","edge"} as the in-game search writes."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    stripped = text.lstrip()
    if stripped.startswith("{") and '"nodes"' in stripped[:4000]:
        return json.loads(text)
    out = {"format": FORMAT, "header": {}, "nodes": {}}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        if "header" in rec:
            out["header"] = rec["header"]
            continue
        n = out["nodes"].setdefault(rec["path"], {"situation": rec.get("situation", {}), "edges": []})
        n["edges"].append(rec["edge"])
    return out


def _lua(v, indent=0):
    pad = "  " * indent
    if isinstance(v, dict):
        if not v:
            return "{}"
        items = ["%s  [%s] = %s" % (pad, _lua(str(k)), _lua(x, indent + 1)) for k, x in v.items()]
        return "{\n" + ",\n".join(items) + "\n" + pad + "}"
    if isinstance(v, list):
        if not v:
            return "{}"
        return "{\n" + ",\n".join("%s  %s" % (pad, _lua(x, indent + 1)) for x in v) + "\n" + pad + "}"
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "nil"
    if isinstance(v, (int, float)):
        return repr(v)
    return json.dumps(str(v))


def export_lua(tree):
    """A Lua chunk `return {header=..., nodes={[path]={situation=..., edges={...}}}}` with each edge's `key` added."""
    validate(tree)
    out = {"format": tree["format"], "header": tree["header"], "nodes": {}}
    for path, node in tree["nodes"].items():
        edges = []
        for e in node["edges"]:
            e = dict(e)
            e["key"] = edge_key(e)
            e.pop("conflicts", None)
            edges.append(e)
        out["nodes"][path] = {"situation": node.get("situation", {}), "edges": edges}
    return "-- generated by tools/combos/tree.py export-lua; do not edit\nreturn " + _lua(out) + "\n"


def load(path):
    with open(path, encoding="utf-8") as f:
        return validate(json.load(f))


def save(tree, path):
    validate(tree)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(tree, f, indent=1, sort_keys=True)
        f.write("\n")


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    cmd = argv[1]
    try:
        if cmd == "validate":
            for p in argv[2:]:
                t = load(p)
                n = sum(len(x["edges"]) for x in t["nodes"].values())
                print("%s: ok, %d nodes, %d edges" % (p, len(t["nodes"]), n))
            return 0
        if cmd == "merge":
            t = load(argv[2])
            bad = 0
            for p in argv[3:]:
                same, new, conf = merge(t, read_results(p))
                print("%s: %d confirmed again, %d new, %d conflicts" % (p, same, new, len(conf)))
                for c in conf:
                    print("  CONFLICT %s %s %s: stored %r, new %r" % (c["path"] or "<root>", c["edge"], c["field"], c["stored"], c["new"]))
                bad += len(conf)
            save(t, argv[2])
            return 2 if bad else 0
        if cmd == "export-lua":
            out = None
            if "-o" in argv:
                i = argv.index("-o")
                out = argv[i + 1]
                argv = argv[:i] + argv[i + 2:]
            text = export_lua(load(argv[2]))
            if out:
                with open(out, "w", encoding="utf-8", newline="\n") as f:
                    f.write(text)
            else:
                sys.stdout.write(text)
            return 0
        if cmd == "show":
            t = load(argv[2])
            print(json.dumps(t["header"], indent=1))
            for path, node in sorted(t["nodes"].items()):
                print("node %s" % (path or "<root>"))
                for e in node["edges"]:
                    print("   %-28s %-8s dmg=%s hs=%s hit@%s x%d" % (e["move"], e["result"], e.get("damage"), e.get("victim_hitstun"),
                                                                    e.get("hit_frame"), e.get("confirmed", 1)))
            return 0
    except (TreeError, OSError, ValueError, KeyError) as ex:
        print("error: %s" % ex, file=sys.stderr)
        return 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
