#!/bin/bash
# usage: make_mods.sh <dest-dir> [fixture ...]   (default: geno-lab vanilla-striker vanilla-courier)
# Copies the named fixtures from $GW_MELEE/pc/geno/mods into <dest-dir> and writes enabled.txt. The Courier's built
# files (tools/geno/build_courier.sh --install) must already be in its files/ folder.
set -eu
dest="$1"; shift
list="${*:-geno-lab vanilla-striker vanilla-courier}"
rm -rf "$dest"; mkdir -p "$dest"
: > "$dest/enabled.txt"
for m in $list; do cp -r "$GW_MELEE/pc/geno/mods/$m" "$dest/$m"; echo "$m" >> "$dest/enabled.txt"; done
echo "$dest: $list"
