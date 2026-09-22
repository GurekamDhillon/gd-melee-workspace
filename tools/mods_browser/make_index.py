#!/usr/bin/env python3
"""Package mods and write the gdmelee-mods.json index the GD's Melee mods browser reads.

    python tools/mods_browser/make_index.py --out dist  mods/my-mod  mods/other-mod ...
    python tools/mods_browser/make_index.py --out dist --base-url https://github.com/me/my-mods/releases/download/v1/  mods/my-mod

For every mod folder (the layout in docs/mods-packaging.md: mod.json + files/ and/or scripts/):
  - writes dist/<id>-<version>.zip with mod.json at the zip's top level (forward slashes, no
    absolute paths, no symlinks - what the browser accepts);
  - adds an entry to dist/gdmelee-mods.json with the id, name, version, kind, pack, description,
    requires, conflicts, api_version (scripts), size and sha256 of the zip, and its url: the zip's
    file name (resolved against wherever the index is served from) or --base-url + file name.
Existing entries in dist/gdmelee-mods.json for other ids are kept, so a source can grow.

Upload the zips (e.g. as GitHub release assets) and the index (repo root or a release asset); see
docs/mods-browser.md. Never publish mods made from a Nintendo disc (packs, splits): only your own
work, or work whose authors let you redistribute it.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import zipfile

ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
FIELDS = ("name", "version", "kind", "pack", "description", "requires", "conflicts", "api_version",
          "homepage", "authors")


def zip_mod(folder, out_dir):
    folder = os.path.abspath(folder)
    mj = os.path.join(folder, "mod.json")
    if not os.path.isfile(mj):
        sys.exit(f"make_index: {folder} has no mod.json")
    meta = json.load(open(mj, encoding="utf-8"))
    mod_id = meta.get("id") or os.path.basename(folder)
    if not ID_RE.match(mod_id):
        sys.exit(f"make_index: bad id {mod_id!r} (lower-case letters, digits, . _ -)")
    version = str(meta.get("version", "0"))
    name = f"{mod_id}-{version}.zip"
    path = os.path.join(out_dir, name)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(folder):
            dirs.sort()
            for f in sorted(files):
                full = os.path.join(root, f)
                if os.path.islink(full):
                    sys.exit(f"make_index: {full} is a symlink - not allowed in a mod")
                rel = os.path.relpath(full, folder).replace(os.sep, "/")
                z.write(full, rel)
    data = open(path, "rb").read()
    entry = {"id": mod_id}
    for k in FIELDS:
        if k in meta and meta[k] not in ("", None):
            entry[k] = meta[k]
    entry.setdefault("name", mod_id)
    entry.setdefault("kind", "misc")
    entry["size"] = len(data)
    entry["sha256"] = hashlib.sha256(data).hexdigest()
    return entry, name


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--out", required=True, help="output folder for the zips and gdmelee-mods.json")
    ap.add_argument("--base-url", default="", help="prefix for the zip urls (default: relative to the index)")
    ap.add_argument("--name", default="", help="the source's display name, stored in the index")
    ap.add_argument("mods", nargs="+", help="mod folders")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    index_path = os.path.join(args.out, "gdmelee-mods.json")
    index = {"schema": 1, "name": args.name, "mods": []}
    if os.path.isfile(index_path):
        index = json.load(open(index_path, encoding="utf-8"))
        if args.name:
            index["name"] = args.name
    by_id = {m["id"]: m for m in index.get("mods", [])}
    for folder in args.mods:
        entry, zname = zip_mod(folder, args.out)
        entry["url"] = args.base_url + zname
        by_id[entry["id"]] = entry
        print(f"  {entry['id']} {entry.get('version', '')}: {zname} ({entry['size']} bytes)")
    index["schema"] = 1
    index["mods"] = [by_id[k] for k in sorted(by_id)]
    with open(index_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(index, f, indent=2)
        f.write("\n")
    print(f"wrote {index_path} ({len(index['mods'])} mods)")


if __name__ == "__main__":
    main()
