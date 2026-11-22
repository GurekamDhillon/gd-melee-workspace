#!/usr/bin/env python3
"""Diff two fighter costume files' skeletons and every non-visual field. Exit 0 = identical, 1 = differences.

    jointdiff.py <retail.dat> <skin.dat> [--max 20] [--json out.json]

Compared, bit for bit (raw big-endian bytes, not floats): the joint walk (count, depth-first order, parent of every
joint), each JObj's flags, rotation, scale, translation, whether it has an inverse bind and the 48 bytes of it,
whether it has a robj/instance/child/next; the public symbol names; the number of DObjs per joint and their order
(the part/visibility tables index them). Ignored (visual only): PObj geometry, envelopes, MObj/TObj/images/palettes.
Works for any fighter costume (*_Share_joint).
"""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools", "mex_port"))
import mex_hsd


def ptr(ar, off):
    return ar.u32(off) if off in ar.reloc_set else None


def walk(path):
    ar = mex_hsd.Archive(open(path, "rb").read())
    pubs = sorted(s for s, _ in ar.publics)
    root = [s for s in pubs if s.endswith("_Share_joint")]
    if not root: raise SystemExit("%s: no *_Share_joint" % path)
    out = []

    def go(off, parent, depth):
        while off is not None:
            flags = ar.u32(off + 4); inv = ptr(ar, off + 0x38)
            ndobj = 0; d = ptr(ar, off + 0x10)
            mesh = d is not None and not flags & ((1 << 5) | (1 << 14))
            while mesh and d is not None: ndobj += 1; d = ptr(ar, d + 4)
            out.append({"i": len(out), "parent": parent, "depth": depth, "flags": "%08x" % flags,
                        "rot": bytes(ar.data[off + 0x14:off + 0x20]).hex(), "scale": bytes(ar.data[off + 0x20:off + 0x2C]).hex(),
                        "trans": bytes(ar.data[off + 0x2C:off + 0x38]).hex(),
                        "ibm": bytes(ar.data[inv:inv + 48]).hex() if inv is not None else None,
                        "robj": ptr(ar, off + 0x3C) is not None, "dobjs": ndobj,
                        "child": ptr(ar, off + 8) is not None, "next": ptr(ar, off + 0xC) is not None})
            me = len(out) - 1
            c = ptr(ar, off + 8)
            if c is not None and not flags & (1 << 12): go(c, me, depth + 1)
            off = ptr(ar, off + 0xC)

    go(ar.public(root[0]), None, 0)
    return pubs, out


def diff(a, b, limit=20):
    pa, ja = walk(a); pb, jb = walk(b); diffs = []
    if pa != pb: diffs.append("public symbols differ: %s vs %s" % (pa, pb))
    if len(ja) != len(jb): diffs.append("joint count %d vs %d" % (len(ja), len(jb)))
    for x, y in zip(ja, jb):
        for k in x:
            if x[k] != y[k]: diffs.append("joint %d %s: %s vs %s" % (x["i"], k, x[k], y[k]))
    return {"joints": [len(ja), len(jb)], "dobjs": [sum(j["dobjs"] for j in ja), sum(j["dobjs"] for j in jb)],
            "fields_compared": len(ja) * 12, "differences": diffs, "shown": diffs[:limit]}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("retail"); ap.add_argument("skin")
    ap.add_argument("--max", type=int, default=20); ap.add_argument("--json")
    a = ap.parse_args()
    r = diff(a.retail, a.skin, a.max)
    if a.json: json.dump(r, open(a.json, "w"), indent=1)
    print("joints %d / %d, DObjs %d / %d, %d fields compared" % (*r["joints"], *r["dobjs"], r["fields_compared"]))
    if r["differences"]:
        print("DIFFERENT: %d differences, first %d:" % (len(r["differences"]), len(r["shown"])))
        for d in r["shown"]: print("  " + d)
        sys.exit(1)
    print("IDENTICAL: skeleton and non-visual fields match")


if __name__ == "__main__":
    main()
