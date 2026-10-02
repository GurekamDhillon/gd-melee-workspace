#!/bin/bash
# Match the game's i686 architecture; Vulkan is loaded at runtime, not linked.
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"
output="${1:-$root/_build/graphics-probe/melee-graphics-probe}"
mkdir -p "$(dirname "$output")"
"${CC:-cc}" -m32 -std=c11 -O2 -Wall -Wextra -Werror "$root/tools/port/graphics_probe.c" -ldl -o "$output"
