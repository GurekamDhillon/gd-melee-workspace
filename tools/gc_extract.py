#!/usr/bin/env python3
"""Extract a GameCube disc image's file system (FST) to a directory.

Needed because the akaneia-build repository ships project data only -- `files/` and `sys/`
must be extracted from the patched disc, which this produces.

Usage: gc_extract.py <disc.iso> <outdir> [--only <path-prefix>]
"""
import argparse
import os
import struct
import sys

DISC_MAGIC = 0xC2339F3D


def load_fst(f):
    header = f.read(0x440)
    if len(header) < 0x440 or struct.unpack(">I", header[0x1C:0x20])[0] != DISC_MAGIC:
        raise SystemExit("not a GameCube disc image")
    game_id = header[0:6].decode("ascii", "replace")
    fst_off, fst_size = struct.unpack(">II", header[0x424:0x42C])
    if not fst_size:
        raise SystemExit("disc has no file system table")
    f.seek(fst_off)
    fst = f.read(fst_size)
    n_entries = struct.unpack(">I", fst[8:12])[0]
    return fst, n_entries, game_id


def entry_name(fst, n_entries, name_off):
    start = n_entries * 12 + name_off
    end = fst.find(b"\0", start)
    if end < 0:
        end = len(fst)
    return fst[start:end].decode("shift_jis", "replace")


def extract(f, fst, n_entries, out_dir, only):
    extracted = 0
    total_bytes = 0
    stack = []
    idx = 1  # entry 0 is the root directory itself
    prefix = ""
    while idx < n_entries:
        w0, offset, length = struct.unpack(">III", fst[idx * 12:idx * 12 + 12])
        is_dir = (w0 >> 24) & 0xFF
        # A name offset of 0 is a valid offset (it points at the first string in the table);
        # only the root entry, which this loop skips, has a name that is ignored. Treating 0
        # as "no name" flattened the first directory (`audio/`) into the output root.
        name = entry_name(fst, n_entries, w0 & 0xFFFFFF)
        if is_dir:
            prefix = os.path.join(prefix, name) if name else prefix
            stack.append((length, prefix))
            if only and prefix.replace(os.sep, "/").startswith(only):
                os.makedirs(os.path.join(out_dir, prefix), exist_ok=True)
            idx += 1
            continue
        # A directory entry's `length` field is the index of the LAST entry in its subtree, so a
        # file at exactly that index is still inside it: pop only once idx exceeds it.
        if stack and idx > stack[-1][0]:
            while stack and idx > stack[-1][0]:
                prefix = os.path.dirname(stack.pop()[1])
        rel = os.path.join(prefix, name) if prefix else name
        want = (not only) or rel.replace(os.sep, "/").startswith(only)
        if want:
            dest = os.path.join(out_dir, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            f.seek(offset)
            data = f.read(length)
            with open(dest, "wb") as o:
                o.write(data)
            extracted += 1
            total_bytes += len(data)
        idx += 1
    return extracted, total_bytes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("disc")
    ap.add_argument("outdir")
    ap.add_argument("--only", default=None, help="extract only paths starting with this prefix")
    ap.add_argument("--list", action="store_true", help="list entries, extract nothing")
    args = ap.parse_args()

    with open(args.disc, "rb") as f:
        fst, n_entries, game_id = load_fst(f)
        print(f"{args.disc}: {game_id}, {n_entries} FST entries", file=sys.stderr)
        if args.list:
            for i in range(n_entries):
                w0, offset, length = struct.unpack(">III", fst[i * 12:i * 12 + 12])
                is_dir = (w0 >> 24) & 0xFF
                name = "/" if i == 0 else entry_name(fst, n_entries, w0 & 0xFFFFFF)
                print(f"{'DIR ' if is_dir else 'FILE'} {name:<40} {offset:#010x} {length}")
            return
        extracted, total = extract(f, fst, n_entries, args.outdir, args.only)
    print(f"extracted {extracted} files, {total / (1024 * 1024):.1f} MiB -> {args.outdir}", file=sys.stderr)


if __name__ == "__main__":
    main()
