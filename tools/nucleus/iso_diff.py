#!/usr/bin/env python3
"""Diff two GameCube ISOs by FST: python iso_diff.py VANILLA PATCHED [--out DIR]

Prints unchanged/changed/added/removed counts, changed+added names, whether
MxDt.dat exists, whether the main DOL differs, and a verdict:
LOOSE-OVERRIDE or NEEDS-DISC-BOOT. With --out, copies changed/added files to
DIR/files/<disc path>. Files are compared in chunks (sizes first); nothing is
held in memory beyond one chunk.
"""
import argparse
import os
import struct
import sys

CHUNK = 1 << 20


class Gcm:
    def __init__(self, path):
        self.path = path
        self.f = open(path, "rb")
        h = self._rd(0, 0x440)
        if len(h) < 0x440:
            raise ValueError("%s: too small for a GCM header" % path)
        self.dol_off, self.fst_off, self.fst_size = struct.unpack(">III", h[0x420:0x42C])
        fst = self._rd(self.fst_off, self.fst_size)
        count = struct.unpack(">I", fst[8:12])[0]
        if count * 12 > len(fst) or count < 1:
            raise ValueError("%s: bad FST" % path)
        names = fst[count * 12:]
        self.files = {}  # path -> (offset, size)
        stack = [(count, "")]  # (end index, prefix)
        for i in range(1, count):
            while stack and i >= stack[-1][0]:
                stack.pop()
            fl_name, a, b = struct.unpack(">III", fst[i * 12:i * 12 + 12])
            no = fl_name & 0xFFFFFF
            end = names.index(b"\0", no)
            nm = names[no:end].decode("shift_jis", "replace")
            if fl_name >> 24:
                stack.append((b, stack[-1][1] + nm + "/"))
            else:
                self.files[stack[-1][1] + nm] = (a, b)
        self.dol_size = self._dol_size()

    def _rd(self, off, n):
        self.f.seek(off)
        return self.f.read(n)

    def _dol_size(self):
        h = self._rd(self.dol_off, 0x100)
        if len(h) < 0x100:
            return 0
        offs = struct.unpack(">18I", h[0:0x48])
        sizes = struct.unpack(">18I", h[0x90:0xD8])
        return max([o + s for o, s in zip(offs, sizes) if s] + [0x100])

    def regions(self):
        return {"<main.dol>": (self.dol_off, self.dol_size)}

    def has(self, base):
        return any(p.rsplit("/", 1)[-1].lower() == base.lower() for p in self.files)


def same_content(a, ra, b, rb):
    if ra[1] != rb[1]:
        return False
    n = ra[1]
    pa, pb = ra[0], rb[0]
    while n:
        k = min(n, CHUNK)
        if a._rd(pa, k) != b._rd(pb, k):
            return False
        pa += k
        pb += k
        n -= k
    return True


def copy_out(g, region, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    off, n = region
    with open(dest, "wb") as o:
        while n:
            k = min(n, CHUNK)
            o.write(g._rd(off, k))
            off += k
            n -= k


def diff(van, pat):
    unchanged, changed, added = 0, [], []
    for p, r in pat.files.items():
        if p not in van.files:
            added.append(p)
        elif same_content(van, van.files[p], pat, r):
            unchanged += 1
        else:
            changed.append(p)
    removed = [p for p in van.files if p not in pat.files]
    dol_diff = not same_content(van, van.regions()["<main.dol>"], pat, pat.regions()["<main.dol>"])
    return unchanged, sorted(changed), sorted(added), sorted(removed), dol_diff


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("vanilla")
    ap.add_argument("patched")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    van, pat = Gcm(a.vanilla), Gcm(a.patched)
    unchanged, changed, added, removed, dol_diff = diff(van, pat)
    mx_v, mx_p = van.has("MxDt.dat"), pat.has("MxDt.dat")
    mx_changed = any(p.rsplit("/", 1)[-1].lower() == "mxdt.dat" for p in changed)
    print("files: unchanged=%d changed=%d added=%d removed=%d" % (unchanged, len(changed), len(added), len(removed)))
    names = [("changed", p) for p in changed] + [("added", p) for p in added]
    for k, p in names[:60]:
        print("  %-7s %s" % (k, p))
    if len(names) > 60:
        print("  ... %d more" % (len(names) - 60))
    print("MxDt.dat: vanilla=%s patched=%s" % (mx_v, mx_p))
    print("main.dol differs: %s" % dol_diff)
    ndiff = len(changed) + len(added)
    boot = dol_diff or mx_p or mx_v or mx_changed or ndiff > 400
    print("VERDICT: " + ("NEEDS-DISC-BOOT" if boot else "LOOSE-OVERRIDE"))
    if a.out:
        for p in changed + added:
            dest = os.path.join(a.out, "files", *p.split("/"))
            copy_out(pat, pat.files[p], dest)
        print("copied %d files to %s" % (ndiff, os.path.join(a.out, "files")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
