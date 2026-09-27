#!/usr/bin/env bash
# Build and play the local Ultimate Kirby proof on the ACE disc.
# Usage: bash ports/kirby-ultimate/run.sh [--probe] [--refresh-visuals]
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
. ./.env
: "${GW_ISO_ACE:?Set GW_ISO_ACE in .env before running Ultimate Kirby}"
test -f "$GW_ISO_ACE"

probe=false
refresh_visuals=false
for arg in "$@"; do
    case "$arg" in
        --probe) probe=true ;;
        --refresh-visuals) refresh_visuals=true ;;
        *) echo 'usage: bash ports/kirby-ultimate/run.sh [--probe] [--refresh-visuals]' >&2; exit 2 ;;
    esac
done

python ports/kirby-ultimate/tools/build_movement.py --out-parent _build/tmp/ultimate-kirby-mods
python ports/kirby-ultimate/tools/build_side_b.py \
    --mod _build/tmp/ultimate-kirby-mods/ultimate-kirby-movement
python ports/kirby-ultimate/tools/build_normals.py \
    --mod _build/tmp/ultimate-kirby-mods/ultimate-kirby-movement
python ports/kirby-ultimate/tools/build_rapid_jab.py \
    --mod _build/tmp/ultimate-kirby-mods/ultimate-kirby-movement
python ports/kirby-ultimate/tools/build_throws.py \
    --mod _build/tmp/ultimate-kirby-mods/ultimate-kirby-movement
python ports/kirby-ultimate/tools/build_grabs.py \
    --mod _build/tmp/ultimate-kirby-mods/ultimate-kirby-movement
python ports/kirby-ultimate/tools/build_final_cutter.py \
    --mod _build/tmp/ultimate-kirby-mods/ultimate-kirby-movement

# Derived game assets remain in the ignored build tree. Refresh explicitly
# after changing the model or animation converters; normal launches reuse them.
costume=_build/tmp/ultimate-kirby-model-world-rest-default/PlKbNr.dat
animations=_build/tmp/ultimate-kirby-anims-world-rest-scaled-complete/install-manifest.json
if "$refresh_visuals" || [ ! -f "$costume" ]; then
    python ports/kirby-ultimate/model/build_model.py \
        --stock-costume experiment/brawl-kirby/disc/PlKbNr.dat \
        --out-dir _build/tmp/ultimate-kirby-model-world-rest-default
fi
if "$refresh_visuals" || [ ! -f "$animations" ]; then
    python ports/kirby-ultimate/animations/convert_world.py \
        --bind-policy source-world-scaled \
        --out _build/tmp/ultimate-kirby-anims-world-rest-scaled-complete
fi
python ports/kirby-ultimate/tools/install_visuals.py \
    --mod _build/tmp/ultimate-kirby-mods/ultimate-kirby-movement \
    --costume "$costume" --animations "$animations"

# The LAB script provides the move timeline, live hitbox view and frame tools.
lab_dir=_build/tmp/ultimate-kirby-mods/geno-lab
mkdir -p "$lab_dir"
cp -R melee/pc/geno/mods/geno-lab/. "$lab_dir/"

export GW_ISO="$GW_ISO_ACE"
export MELEE_MODS_DIR="$(pwd -W)/_build/tmp/ultimate-kirby-mods"
export MELEE_SCENE='mode=lab;p1=kirby;p2=fox/cpu0;stage=fd'
export MELEE_VOLUME=3
export GW_RUNS_KEEP=100000

name=ultimate-kirby-play
if "$probe"; then
    name=ultimate-kirby-probe
    export MELEE_SCENE='mode=lab;p1=kirby;p2=fox/hu;stage=fd'
    export MELEE_INPUT=none
    export MELEE_PAD_SCRIPT="$(pwd -W)/ports/kirby-ultimate/probe/movement.lua"
else
    unset MELEE_INPUT MELEE_PAD_SCRIPT
    # Start visual assessment with only the fighter model drawn. The LAB can
    # switch to hitboxes later and its saved settings are respected on reruns.
    settings_dir="${GW_BUILD_ROOT:-_build}/runs/$name/scripts-data/geno-lab_lab"
    mkdir -p "$settings_dir"
    if [ ! -f "$settings_dir/settings.txt" ]; then
        printf 'mode=inspect\nhidden=false\n' > "$settings_dir/settings.txt"
    fi
fi

tools/port/run.sh "$name" --iso "$GW_ISO"
