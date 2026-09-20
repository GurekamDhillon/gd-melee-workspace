#!/usr/bin/env python3
"""Pack YOUR OWN mod disc into a mods/ folder, so the port runs it off a VANILLA ISO.

    python tools/mex_port/make_mod_from_disc.py \
        --vanilla "C:/iso/Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso" \
        --mod     "C:/iso/Akaneia.iso" \
        --name    akaneia \
        --out     "C:/gdm/_build/packs"

WE SHIP THE TOOL, NEVER THE PACK. Both discs are supplied by whoever runs this; the tool computes
the difference on their machine and writes `<out>/<name>/`. Nothing it produces may enter the
repository, a release or a commit - `.gitignore` refuses disc data and `/_build/packs/` outright.
Neither Nintendo's data nor the mod teams' (Akaneia, ACE) is ours to redistribute.

How the pack is used: `shim_dvd.c`'s overlay treats every directory under `mods/` as a mod whose
files answer the disc path of their position inside it. A path the vanilla disc already has is
OVERRIDDEN in place (it keeps its disc entrynum, so anything that cached the number is
unaffected); a path vanilla does not have is ADDED with a fresh entrynum past the disc FST. So a
pack needs exactly two classes of file, and this tool emits exactly those:

  NEW       on the mod disc, absent from vanilla     (fighters, stages, banks, MxDt.dat, ...)
  MODIFIED  on both, but the CONTENT differs         (MnSlChr.usd, PlCo.dat, IfAll.usd, Ef*Data)

Content, not size: the shared tables this port depends on are frequently the same length with a
different payload, so a size-only diff silently drops them. Every same-size pair is hashed on
both discs.

Resumable and idempotent. A manifest beside the pack records each emitted file's size and sha256;
a re-run re-reads it, copies only what is missing or wrong, and prunes what is no longer in the
delta. An interrupted run loses at most one file - writes go to `.part` and are renamed into
place.
"""
import argparse
import fnmatch
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mex_hsd import Gcm  # noqa: E402

# The manifest lives BESIDE the pack, never inside it. Everything inside a mod folder becomes
# a disc file: a manifest dropped in there is handed a fresh entrynum past the disc FST and
# shows up in the overlay log as a 58 KB "new file" nothing will ever open. A plain file in
# the mods directory is ignored, because the overlay only walks directories.
MANIFEST_SUFFIX = ".gdm_pack.json"
CHUNK = 1 << 20


def _iso_digest(path, off, size):
    """sha256 of `size` bytes at `off` in the image, without holding them in memory."""
    h = hashlib.sha256()
    with open(path, "rb") as fp:
        fp.seek(off)
        left = size
        while left:
            b = fp.read(min(CHUNK, left))
            if not b:
                break
            h.update(b)
            left -= len(b)
    return h.hexdigest()


def _file_digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as fp:
        while True:
            b = fp.read(CHUNK)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _extract(iso_path, off, size, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = dst + ".part"
    h = hashlib.sha256()
    with open(iso_path, "rb") as src, open(tmp, "wb") as out:
        src.seek(off)
        left = size
        while left:
            b = src.read(min(CHUNK, left))
            if not b:
                raise IOError(f"short read at {off:#x} (+{size - left}/{size}) in {iso_path}")
            out.write(b)
            h.update(b)
            left -= len(b)
    os.replace(tmp, dst)
    return h.hexdigest()


def _human(n):
    return f"{n / (1 << 20):,.1f} MB"


def classify(vanilla, mod, exclude):
    """-> (new, modified, same, skipped); each a list of (path, offset, size)."""
    new, modified, same, skipped = [], [], [], []
    for path in sorted(mod.files):
        off, size = mod.files[path]
        if any(fnmatch.fnmatch(path.lower(), p.lower()) for p in exclude):
            skipped.append((path, off, size))
            continue
        base = vanilla.files.get(path)
        if base is None:
            new.append((path, off, size))
            continue
        voff, vsize = base
        if vsize != size:
            modified.append((path, off, size))
        elif _iso_digest(mod.path, off, size) != _iso_digest(vanilla.path, voff, vsize):
            modified.append((path, off, size))
        else:
            same.append((path, off, size))
    return new, modified, same, skipped


def main():
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--vanilla", required=True, help="your clean retail Melee ISO")
    ap.add_argument("--mod", required=True, help="your mod disc (Akaneia, ACE, ...)")
    ap.add_argument("--name", required=True,
                    help="the mod folder's name; mods apply in name order, a later one wins")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                  "..", "..", "_build", "packs"),
                    help="where <name>/ is written. Keep it OUTSIDE the repository.")
    ap.add_argument("--exclude", action="append", default=[], metavar="GLOB",
                    help="disc paths to leave out (repeatable, case-insensitive fnmatch)")
    ap.add_argument("--only", action="append", default=[], metavar="GLOB",
                    help="if given, keep only delta paths matching one of these")
    ap.add_argument("--dry-run", action="store_true", help="classify and report, write nothing")
    ap.add_argument("--recheck", action="store_true",
                    help="re-hash files already on disk instead of trusting the manifest")
    ap.add_argument("--no-prune", action="store_true",
                    help="keep files a previous run wrote that are no longer in the delta")
    args = ap.parse_args()

    t0 = time.time()
    vanilla, mod = Gcm(args.vanilla), Gcm(args.mod)
    print(f"vanilla  {args.vanilla}  ({len(vanilla.files)} files)")
    print(f"mod      {args.mod}  ({len(mod.files)} files)")
    print("scanning (every same-size pair is hashed on both discs) ...")

    new, modified, same, skipped = classify(vanilla, mod, args.exclude)
    if args.only:
        def keep(e):
            return any(fnmatch.fnmatch(e[0].lower(), p.lower()) for p in args.only)
        new, modified = [e for e in new if keep(e)], [e for e in modified if keep(e)]

    nb = sum(e[2] for e in new)
    mb = sum(e[2] for e in modified)
    print(f"  NEW       {len(new):>5} files  {_human(nb):>12}")
    print(f"  MODIFIED  {len(modified):>5} files  {_human(mb):>12}")
    print(f"  same      {len(same):>5} files  (not packed)")
    if skipped:
        print(f"  excluded  {len(skipped):>5} files")
    gone = sorted(set(vanilla.files) - set(mod.files))
    if gone:
        # The overlay adds and overrides but cannot REMOVE, so anything the mod disc dropped still
        # answers from vanilla. Nothing in Melee's data is known to need a deletion; say so anyway.
        print(f"  note: {len(gone)} vanilla paths are absent from the mod disc; the overlay "
              f"cannot delete, so they stay (e.g. {gone[0]})")
    print(f"  total to pack  {len(new) + len(modified)} files, {_human(nb + mb)}")

    out = os.path.normpath(os.path.join(args.out, args.name))
    if args.dry_run:
        print(f"dry run: nothing written (would be {out})")
        return 0

    os.makedirs(out, exist_ok=True)
    mpath = out + MANIFEST_SUFFIX
    # Older packs kept it inside; drop that copy so it stops answering as a disc path.
    stale = os.path.join(out, MANIFEST_SUFFIX)
    if os.path.isfile(stale):
        if not os.path.isfile(mpath):
            os.replace(stale, mpath)
        else:
            os.remove(stale)
    try:
        with open(mpath, "r", encoding="utf-8") as fp:
            old = json.load(fp).get("files", {})
    except (OSError, ValueError):
        old = {}

    want = {}
    copied = copied_bytes = kept = 0
    for path, off, size in new + modified:
        dst = os.path.join(out, *path.split("/"))
        prev = old.get(path)
        on_disk = os.path.isfile(dst) and os.path.getsize(dst) == size
        if on_disk and prev and prev.get("size") == size and not args.recheck:
            want[path] = prev
            kept += 1
            continue
        if on_disk:
            # No manifest entry, or --recheck: trust the bytes, not the record.
            have = _file_digest(dst)
            if have == _iso_digest(mod.path, off, size):
                want[path] = {"size": size, "sha256": have}
                kept += 1
                continue
        want[path] = {"size": size, "sha256": _extract(mod.path, off, size, dst)}
        copied += 1
        copied_bytes += size
        if copied % 50 == 0:
            print(f"    ... {copied} copied, {_human(copied_bytes)}")

    removed = 0
    if not args.no_prune:
        for path in sorted(set(old) - set(want)):
            try:
                os.remove(os.path.join(out, *path.split("/")))
                removed += 1
            except OSError:
                pass
        for root, dirs, files in os.walk(out, topdown=False):
            if root != out and not dirs and not files:
                try:
                    os.rmdir(root)
                except OSError:
                    pass

    with open(mpath, "w", encoding="utf-8") as fp:
        json.dump({"version": 1, "name": args.name,
                   "vanilla": os.path.basename(args.vanilla),
                   "mod": os.path.basename(args.mod),
                   "new": len(new), "modified": len(modified),
                   "files": want}, fp, indent=1, sort_keys=True)

    print(f"{len(want)} files, {_human(sum(v['size'] for v in want.values()))} -> {out}")
    print(f"  copied {copied} ({_human(copied_bytes)}), already present {kept}, pruned {removed}, "
          f"{time.time() - t0:.0f}s")
    print("This pack is disc content. Do not commit it, ship it, or move it into the repository.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
