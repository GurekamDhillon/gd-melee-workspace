#!/bin/bash
# Shared entry point for a Linux CI runner or Windows/WSL2. Discs stay on that machine.
set -euo pipefail
export GW_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
: "${GW_MELEE:?set GW_MELEE to the game checkout under test}"
: "${MELEE_VANILLA_ISO:?set MELEE_VANILLA_ISO to the local vanilla v1.02 disc}"
export GW_MELEE="$(realpath "$GW_MELEE")"
export GW_BUILD_ROOT="${GW_BUILD_ROOT:-$GW_ROOT/_build/ci/linux}"
export GW_AURORA_LINUX_BUILD="${GW_AURORA_LINUX_BUILD:-$GW_ROOT/_build/ci/aurora}"
export GW_GWTOOL="${GW_GWTOOL:-$GW_ROOT/_build/ci/gwtool/gwtool}"
export GWTOOL_OUT="$(dirname "$GW_GWTOOL")"
export GW_LIBUSB_BUILD="${GW_LIBUSB_BUILD:-$GW_ROOT/_build/ci/libusb}"
export GW_ENET_BUILD="${GW_ENET_BUILD:-$GW_ROOT/_build/ci/enet}"
export GW_JOBS="${GW_JOBS:-8}"
export GW_TU_LIST="$GW_ROOT/tools/port/linux_tus.txt"
bash "$GW_ROOT/tools/port/build_gwtool_linux.sh"
python3 "$GW_MELEE/pc/tools/extract_assets.py" --iso "$MELEE_VANILLA_ISO"
bash "$GW_ROOT/tools/port/build_aurora_linux.sh"
cmake -S "$GW_MELEE/extern/enet" -B "$GW_ENET_BUILD" -G Ninja \
    -DCMAKE_C_COMPILER=clang -DCMAKE_C_FLAGS=-m32 -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build "$GW_ENET_BUILD" -j "$GW_JOBS"
bash "$GW_ROOT/tools/port/build_libusb_linux.sh"
python3 "$GW_ROOT/tools/port/map_to_msvc.py" --self-test
bash "$GW_ROOT/tools/port/test_linux_abi.sh"
bash "$GW_ROOT/tools/port/build_linux.sh"
mkdir -p "$GW_BUILD_ROOT/assets/fonts"
font_dir="${MELEE_BUILD_FONT_DIR:-/usr/share/fonts/truetype/liberation2}"
cp "$font_dir/LiberationSans-Bold.ttf" "$font_dir/LiberationSerif-Bold.ttf" "$GW_BUILD_ROOT/assets/fonts/"
cp "${MELEE_FONT_LICENSE:-/usr/share/doc/fonts-liberation2/copyright}" "$GW_BUILD_ROOT/assets/fonts/LICENSE.txt"
MELEE_UI_ASSETS="${MELEE_UI_ASSETS:-$GW_ROOT/_build/ui}"
mkdir -p "$GW_BUILD_ROOT/ui"
cp -a "$MELEE_UI_ASSETS/." "$GW_BUILD_ROOT/ui/"
for variable in MELEE_VANILLA_ISO MELEE_AKANEIA_ISO MELEE_ACE_ISO; do
    if [ -n "${!variable:-}" ]; then
        bash "$GW_ROOT/tools/port/run_linux_smoke.sh" "${!variable}" test 180
    else
        echo "ERROR: $variable is required for the three-disc acceptance gate" >&2
        exit 1
    fi
done
bash "$GW_ROOT/tools/release/build_launcher.sh" "$GW_ROOT/_build/launcher-package"
python3 "$GW_ROOT/tools/port/package_linux.py" --build "$GW_BUILD_ROOT"
