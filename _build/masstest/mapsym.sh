#!/bin/bash
# Resolve a runtime address (as printed by the port's crash handler) to a symbol in melee-pc.map.
#
# The map has two symbol tables -- "Publics by Value" and a trailing "Static symbols" -- and the
# statics are the majority of the game's functions, so a lookup that reads only the first table
# lands hundreds of bytes into whatever global happened to precede the real function. This merges
# both and reports the nearest preceding symbol with its offset.
#
# Usage: mapsym.sh 0x1025EA8A [more addresses...]
map="${MAP:-C:/gdm/_build/melee-pc.map}"
[ -f "$map" ] || { echo "no map at $map" >&2; exit 1; }

syms=$(mktemp)
# Both tables share the layout: "0001:0025ea50  name  1025fa50 f  lib:obj"; column 3 is the VA.
grep -E '^ [0-9a-f]{4}:[0-9a-f]{8} ' "$map" \
  | awk '{ printf "%d\t%s\t%s\n", strtonum("0x" $3), $2, $NF }' \
  | sort -n > "$syms"

for a in "$@"; do
  target=$(( a ))
  awk -F'\t' -v t="$target" '
    $1 <= t { addr = $1; name = $2; obj = $3 }
    END {
      if (name == "") { printf "0x%X: below every symbol\n", t; exit }
      printf "0x%X = %s+0x%X   [%s]\n", t, name, t - addr, obj
    }' "$syms"
done
rm -f "$syms"
