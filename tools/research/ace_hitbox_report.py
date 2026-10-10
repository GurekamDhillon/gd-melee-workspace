#!/usr/bin/env python3
"""Aggregate the three dump sets into the tables used by _research/ace-hitbox-types-2026-10-10.md.

    python tools/research/ace_hitbox_report.py DUMP_ROOT [section ...]

DUMP_ROOT holds acehb_dump/ (hitbox_timeline_dump.lua, static gd.timeline), acehb_lab/ (the LAB's
measured frame-data export) and acehb_probe/ (special_probe.lua: items and connected hits).
Sections: types, cards, codemod, probes, diff.   Prints markdown to stdout; writes nothing.
Gameplay numbers only; nothing here touches a disc.
"""
import collections
import csv
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ace_hitbox_collect as C  # noqa: E402


def load_set(root, prefix):
    out = {}
    for f in sorted(glob.glob(os.path.join(root, "acehb_dump", prefix + "*.jsonl"))):
        out[os.path.basename(f)[:-6]] = C.fighter_summary(f)
    return out


def type_counts(S, only_own=True):
    c = collections.Counter()
    ex = collections.defaultdict(list)
    nh = 0
    for n, s in S.items():
        nm = s["head"]["char_name"]
        seen = set()
        for m in s["moves"]:
            if only_own and not C.is_own(m["name"]):
                continue
            for h in m["hits"]:
                key = (m["name"], h["start"], h["id"])
                if key in seen:
                    continue
                seen.add(key)
                nh += 1
                for t in C.classify(h):
                    if t.startswith("elem:"):
                        t = "element"
                    c[t] += 1
                    if len(ex[t]) < 4 and t not in ("shielddmg", "angle361"):
                        ex[t].append("%s %s f%d dmg%d ang%d" % (nm, m["name"], h["start"], h["damage"], h["angle"]))
            ids = collections.Counter(h["id"] for h in m["hits"])
            if any(v > 1 for v in ids.values()):
                c["multi-create(same id re-created)"] += 1
                if len(ex["multi"]) < 4:
                    ex["multi"].append("%s %s x%d" % (nm, m["name"], max(ids.values())))
            if any(h["adjust"] for h in m["hits"]):
                c["adjust(op12/13 damage/size change)"] += 1
                if len(ex["adjust"]) < 4:
                    ex["adjust"].append("%s %s" % (nm, m["name"]))
    return c, ex, nh


def read_csv(p):
    return list(csv.DictReader(open(p, encoding="utf-8"))) if os.path.exists(p) else []


def codemod(root):
    """Measured (live) hitbox rows whose damage/angle/kbg/bkb/element tuple the static scripts never contain."""
    res = {}
    for d in sorted(glob.glob(os.path.join(root, "acehb_lab", "ace_*"))):
        n = os.path.basename(d)
        rows = read_csv(os.path.join(d, "hitboxes.csv"))
        jf = os.path.join(root, "acehb_dump", n + ".jsonl")
        if not rows or not os.path.exists(jf):
            continue
        S = C.fighter_summary(jf)
        static = set()
        for m in S["moves"]:
            for h in m["hits"]:
                static.add((round(h["damage"]), h["angle"], h["kbg"], h["bkb"], h["element_name"]))
        miss = collections.defaultdict(set)
        for r in rows:
            k = (round(float(r["hb_damage"])), int(r["hb_angle"]), int(r["hb_kbg"]), int(r["hb_bkb"]), r["hb_element"])
            if k not in static:
                miss[r["motion"]].add(k)
        res[n] = (S["head"]["char_name"], len(rows), miss)
    return res


def probe_summary(root, n):
    """Items owned by P1 (any layer but a stage's own) and connected hits, per trial, from special_probe.lua."""
    p = os.path.join(root, "acehb_probe", "probe_" + n.replace("ace_", "") + ".txt")
    if not os.path.exists(p):
        return None
    items = collections.defaultdict(set)
    hits = collections.defaultdict(list)
    for line in open(p, encoding="utf-8"):
        kv = dict(x.split("=", 1) for x in line.split()[1:] if "=" in x)
        if line.startswith("ITEM") and kv.get("owner") == "1" and kv.get("layer") != "vanilla":
            items[kv["trial"]].add("%s(%s)" % (kv["kind"], kv.get("layer")))
        elif line.startswith("HIT") and kv.get("atk") == "1":
            hits[kv["trial"]].append(kv)
    return items, hits


def cards(root):
    for d in sorted(glob.glob(os.path.join(root, "acehb_lab", "ace_mex*"))):
        if not os.path.isdir(d):
            continue
        n = os.path.basename(d)
        jf = os.path.join(root, "acehb_dump", n + ".jsonl")
        if not os.path.exists(jf):
            continue
        S = C.fighter_summary(jf)
        nm = S["head"]["char_name"]
        sp = []
        for r in read_csv(os.path.join(d, "moves.csv")):
            if r["group"] == "input" and r["air"] == "0":
                sp.append("%s s%s a%s t%s hb%s" % (r["name"], r["startup"] or "-", r["active"] or "-", r["total"], r["hitboxes"]))
        own = [m for m in S["moves"] if C.is_own(m["name"])]
        els = collections.Counter(h["element_name"] for m in own for h in m["hits"])
        tags = collections.Counter(t for m in own for h in m["hits"] for t in C.classify(h) if not t.startswith("elem:"))
        top = sorted(own, key=lambda m: -len(m["hits"]))[:3]
        print("#### %s (%s)" % (nm, n))
        print("- specials (ground, LAB measured): " + "; ".join(sp))
        print("- elements (own moves): " + ", ".join("%s %d" % kv for kv in els.most_common()))
        print("- tags: " + ", ".join("%s %d" % kv for kv in tags.most_common(8)))
        print("- most hitbox creations: " + "; ".join("%s x%d" % (m["name"], len(m["hits"])) for m in top))
        ps = probe_summary(root, n)
        if ps:
            items, hits = ps
            print("- probe items: " + "; ".join("%s: %s" % (k, ",".join(sorted(v))) for k, v in sorted(items.items())))
            # item hits only count in a trial where P1 owned a non-vanilla (mex/geno) item; stage items swing too
            def kind(k, h):
                return "article" if h.get("item") == "true" and k in items else ("stage-item?" if h.get("item") == "true" else "box")
            print("- probe hits (first per trial, dealt after staling; n = connects): " + "; ".join(
                "%s %s %.1f n%d" % (k, kind(k, v[0]), float(v[0].get("dealt", 0)), len(v)) for k, v in sorted(hits.items())))


def main():
    root = sys.argv[1]
    secs = sys.argv[2:] or ["types", "codemod"]
    if "types" in secs:
        A, R = load_set(root, "ace_mex"), load_set(root, "van_ck")
        for label, S in (("ADDED (ACE m-ex fighters), own moves only", A), ("RETAIL (vanilla disc), own moves only", R)):
            c, ex, nh = type_counts(S)
            print("### %s: %d fighters, %d distinct hitbox creations" % (label, len(S), nh))
            for k, v in sorted(c.items(), key=lambda kv: -kv[1]):
                print("- %-38s %6d  (%.1f%%)  e.g. %s" % (k, v, 100.0 * v / max(nh, 1), "; ".join(ex.get(k, [])[:2])))
    if "codemod" in secs:
        for n, (nm, tot, miss) in codemod(root).items():
            if miss:
                print("- %s (%s): %d measured rows; live values absent from every static script:" % (n, nm, tot))
                for mo, ks in sorted(miss.items()):
                    print("    %-18s %s" % (mo, sorted(ks)[:4]))
    if "cards" in secs:
        cards(root)
    if "diff" in secs:
        os.system("%s %s %s --diff" % (sys.executable, os.path.join(os.path.dirname(__file__), "ace_hitbox_collect.py"),
                                       os.path.join(root, "acehb_dump")))


if __name__ == "__main__":
    main()
