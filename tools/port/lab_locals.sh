#!/usr/bin/env bash
# lab.lua's main chunk is at Lua's 200-local limit. This compiles it (a real overflow fails here) and reports how many locals
# the main function declares, so a change that adds one shows up before the harness refuses to load it.
#   tools/port/lab_locals.sh [path to lab.lua]
set -eu
F="${1:-melee/pc/geno/mods/geno-lab/scripts/lab.lua}"
luac -p "$F" && echo "luac -p: ok"
n=$(luac -l -l "$F" | awk '/^main /{f=1} f && /^locals \(/{gsub(/[^0-9]/,"",$2); print $2; exit}')
echo "main chunk locals declared: ${n:-unknown}"
