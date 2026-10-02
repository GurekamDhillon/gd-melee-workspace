#!/bin/bash
# Native 64-bit Qt launcher; build separately from the 32-bit game.
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"
build="${GW_LAUNCHER_BUILD:-$root/_build/launcher-qt}"
cmake -S "$root/tools/release/launcher/qt" -B "$build" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON \
    -DLAUNCHER_DEPLOY_QT="${GW_LAUNCHER_DEPLOY:-ON}"
cmake --build "$build" -j "${GW_JOBS:-8}"
bash "$root/tools/port/build_graphics_probe.sh" "$build/melee-graphics-probe"
ctest --test-dir "$build" --output-on-failure
if [ $# -gt 0 ]; then
    cmake --install "$build" --prefix "$(realpath -m "$1")/launcher"
    cp "$build/melee-graphics-probe" "$(realpath -m "$1")/launcher/bin/"
fi
