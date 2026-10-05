#!/usr/bin/env python3
"""Turn the files one combo-search session wrote into a mergeable result tree (see README.md).

The in-game search (search.lua, kept with the session that wrote it) leaves:
  path_*.txt        the committed chain: '# name dmg=.. vp=.. hf=..' then 'abs_frame x y cx cy buttons' rows
  valid_d0_*.txt    every candidate of the root node that landed a hit: 'name | dmg= vhs= hf= amove= score=' joined by '|'
  a probe's log     'TC M <name> | fox <f:action ...> | hits f3(+4.0,hs7) ... | free-between <f,..> | foxdx <n>'
  the demo's log    'TURBO-COMBO[variant] hit N frame F fox_action A victim P% hitstun H'
Nothing is invented here: every edge is a line a game run printed.

    import_session.py --out result.json --header header.json [--chain path.txt --hits log --root @ax-9_vx0]
                      [--root-valid valid_d0.txt] [--probe-log melee-pc.log --probe-lua m1.lua --probe-root PATH]
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tree as T  # noqa: E402


def parse_chain(path):
    """-> list of {name, dmg, vp, hf, rows[(abs_frame, x, y, cx, cy, buttons)]}"""
    links, cur = [], None
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            m = re.match(r"#\s*(.+?)\s+dmg=([\d.]+)\s+vp=([\d.]+)\s+hf=(\d+)", line)
            cur = {"name": m.group(1), "dmg": float(m.group(2)), "vp": float(m.group(3)), "hf": int(m.group(4)), "rows": []}
            links.append(cur)
        else:
            cur["rows"].append(tuple(int(v) for v in line.split()))
    return links


def pad_inputs(rows, base):
    return [{"f": r[0] - base, "x": r[1], "y": r[2], "cx": r[3], "cy": r[4], "buttons": r[5]} for r in rows]


def parse_hits(path, variant):
    """hitstun values of the demo's hit lines, per run (last complete run)."""
    runs, cur = [], []
    pat = re.compile(r"TURBO-COMBO(?:\[(\w+)\])? hit (\d+) frame (\d+) fox_action (\d+) victim ([\d.]+)% hitstun (\d+)")
    for line in open(path, encoding="utf-8", errors="replace"):
        m = pat.search(line)
        if not m:
            continue
        v = m.group(1) or "classic"
        if int(m.group(2)) == 1 and cur:
            runs.append(cur)
            cur = []
        cur.append({"variant": v, "n": int(m.group(2)), "fox_action": int(m.group(4)), "hitstun": int(m.group(6))})
    if cur:
        runs.append(cur)
    runs = [r for r in runs if r and r[0]["variant"] == variant]
    return runs[-1] if runs else []


def chain_to_nodes(links, hits, root, nodes, turbo_notes):
    path, base = root, 0
    nodes.setdefault(path, {"situation": {"victim_percent": [0, 0], "grounded": True, "note": "start of the match, both fighters placed"}, "edges": []})
    for i, lk in enumerate(links):
        edge = {
            "move": lk["name"], "result": "true", "inputs": pad_inputs(lk["rows"], base), "hit_frame": lk["hf"],
            "damage": lk["dmg"], "victim_percent_after": lk["vp"], "confirmed": 1, "source": "search",
        }
        if i < len(hits):
            edge["victim_hitstun"] = hits[i]["hitstun"]
            edge["fox_action_at_hit"] = hits[i]["fox_action"]
        else:
            edge["victim_hitstun"] = -1
        if i < len(turbo_notes) and turbo_notes[i]:
            edge["turbo"] = turbo_notes[i]
        child = T.node_path(path, edge)
        edge["to"] = child
        nodes[path]["edges"].append(edge)
        nodes.setdefault(child, {"situation": {"victim_percent": [lk["vp"], lk["vp"]], "grounded": None}, "edges": []})
        path, base = child, base + lk["hf"]
    return path


def parse_root_valid(path):
    text = open(path, encoding="utf-8").read().replace("\r", "")
    parts = [p.strip("\n") for p in text.replace("|", "\n").split("\n") if p.strip()]
    out = []
    for a, b in zip(parts[0::2], parts[1::2]):
        m = re.search(r"dmg=([\d.]+)\s+vhs=([\d.]+)\s+hf=(\d+)\s+amove=(\d+)", b)
        if m:
            out.append((a.strip(), float(m.group(1)), int(float(m.group(2))), int(m.group(3)), int(m.group(4))))
    return out


def parse_probe_lua(path):
    """name -> inputs, from lines mk("name",{[1]={buttons=256},[7]={y=-127}})"""
    out = {}
    for line in open(path, encoding="utf-8"):
        m = re.match(r'mk\("([^"]+)",(\{.*\})\)\s*$', line.strip())
        if not m:
            continue
        ins = []
        for f, body in re.findall(r"\[(\d+)\]=\{([^}]*)\}", m.group(2)):
            d = {"f": int(f), "x": 0, "y": 0, "cx": 0, "cy": 0, "buttons": 0}
            for k, v in re.findall(r"(\w+)=(-?\w+)", body):
                d[k] = int(v)
            ins.append(d)
        out[m.group(1)] = sorted(ins, key=lambda s: s["f"])
    return out


def parse_probe_log(path):
    pat = re.compile(r"TC M (\S+) \| fox (.*?) \| hits (.*?) \| free-between (.*?) \| foxdx (-?[\d.]+)")
    out = {}
    for line in open(path, encoding="utf-8", errors="replace"):
        m = pat.search(line)
        if m:
            out[m.group(1)] = {"fox": m.group(2), "hits": m.group(3), "free": m.group(4), "dx": float(m.group(5))}
    return out


GROUP = {"a": "crouch>jab", "b": "dash>dash-attack", "c": "dash>crouch>jab", "d": "walk", "e": "dash>shine-or-usmash"}


def probe_to_edges(log, luains, count_cancels):
    """Classify each probe case after one jab hit: a second hit with no free frame in between = true;
    a second hit with free frames = broke; no second hit and no cancel = refused; otherwise whiff."""
    edges = []
    for name, r in sorted(log.items()):
        hits = [h for h in r["hits"].split() if h]
        free = [f for f in r["free"].split(",") if f]
        key = name[0]
        move = GROUP.get(key, name) + " (" + name + ")"
        e = {"move": move, "inputs": luains.get(name, []), "confirmed": 1, "source": "search-probe",
             "fox_actions": r["fox"], "fox_dx": r["dx"]}
        if len(hits) >= 2 and not free:
            m = re.match(r"f(\d+)\(\+([\d.]+),hs(\d+)\)", hits[1])
            e.update(result="true", hit_frame=int(m.group(1)), damage=float(m.group(2)), victim_hitstun=int(m.group(3)))
        elif len(hits) >= 2:
            m = re.match(r"f(\d+)\(\+([\d.]+),hs(\d+)\)", hits[1])
            e.update(result="broke", hit_frame=int(m.group(1)), damage=float(m.group(2)), victim_hitstun=int(m.group(3)),
                     free_frames=[int(f) for f in free])
        elif key == "d":
            e.update(result="refused", note="no 'turbo: cancel' line; Fox stayed in the jab until its own end")
        else:
            e.update(result="whiff")
        edges.append(e)
    return edges


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--header", required=True, help="JSON file with the header keys")
    ap.add_argument("--chain")
    ap.add_argument("--hits")
    ap.add_argument("--variant", default="classic")
    ap.add_argument("--root", default="@start")
    ap.add_argument("--turbo", help="JSON list, one entry per chain link: {cancel_from_key,into_motion} or null")
    ap.add_argument("--root-valid")
    ap.add_argument("--probe-log")
    ap.add_argument("--probe-lua")
    ap.add_argument("--probe-parent", help="path of the node the probe cases start from (after the first jab)")
    a = ap.parse_args()
    out = {"format": T.FORMAT, "header": json.load(open(a.header)), "nodes": {}}
    nodes = out["nodes"]
    notes = json.load(open(a.turbo)) if a.turbo else []
    if a.chain:
        links = parse_chain(a.chain)
        hits = parse_hits(a.hits, a.variant) if a.hits else []
        chain_to_nodes(links, hits, a.root, nodes, notes)
    if a.root_valid:
        root = nodes.setdefault(a.root, {"situation": {"victim_percent": [0, 0], "grounded": True}, "edges": []})
        have = {e["move"] for e in root["edges"]}
        for name, dmg, vhs, hf, amove in parse_root_valid(a.root_valid):
            if name in have:
                continue
            root["edges"].append({"move": name, "result": "true", "inputs": [], "inputs_from_name": True, "hit_frame": hf,
                                  "damage": dmg, "victim_hitstun": vhs, "fox_action_at_hit": amove, "confirmed": 1, "source": "search"})
    if a.probe_log:
        root = nodes.setdefault(a.root, {"situation": {"victim_percent": [0, 0], "grounded": True}, "edges": []})
        jab = {"move": "jab", "result": "true", "inputs": [{"f": 1, "x": 0, "y": 0, "cx": 0, "cy": 0, "buttons": 256}], "hit_frame": 3,
               "damage": 4.0, "victim_hitstun": 7, "confirmed": 1, "source": "search-probe"}
        parent = T.node_path(a.root, jab)
        jab["to"] = parent
        root["edges"].append(jab)
        node = nodes.setdefault(parent, {"situation": {"victim_percent": [4, 4], "note": "Fox right after its first jab hit (hitlag 4, Falco hitstun 7)"}, "edges": []})
        node["edges"].extend(probe_to_edges(parse_probe_log(a.probe_log), parse_probe_lua(a.probe_lua) if a.probe_lua else {}, None))
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=1, sort_keys=True)
        f.write("\n")
    print("wrote", a.out, sum(len(n["edges"]) for n in nodes.values()), "edges")


if __name__ == "__main__":
    main()
