#!/bin/bash
# The pre-Python build.sh scan, retained only for scan_stale_tus.py --compare.
set -euo pipefail
tu_list="$1"
GW_MELEE="$2"
GW_OUT="$3"
[ -f "$tu_list" ] || exit 0

newest_inc=""
while IFS= read -r -d '' h; do
    if [ -z "$newest_inc" ] || [ "$h" -nt "$newest_inc" ]; then newest_inc="$h"; fi
done < <(find "$GW_MELEE/src" "$GW_MELEE/include" "$GW_MELEE/pc/geno" -name '*.h' -newer "$tu_list" -print0 2>/dev/null)

while IFS= read -r f; do
    [ -n "$f" ] || continue
    obj="$GW_OUT/$(echo "$f" | tr '/' '_').obj"
    src="$GW_MELEE/$f"
    [ -e "$src" ] || continue
    inc_newer=0
    for part in "${src%.c}"_*.inc; do
        if [ -e "$part" ] && [ "$part" -nt "$obj" ]; then inc_newer=1; fi
    done
    if [ ! -f "$obj" ] || [ "$src" -nt "$obj" ] || [ "$inc_newer" = 1 ] ||
       { [ -n "$newest_inc" ] && [ "$newest_inc" -nt "$obj" ]; }; then
        printf '%s\n' "$f"
    fi
done < <(tr -d '\r' <"$tu_list")
