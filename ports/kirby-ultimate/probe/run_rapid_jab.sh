#!/usr/bin/env bash
# Rebuild the rapid-jab ftcmd pack and exercise it with actual LAB input.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../../.."
. ./.env
: "${GW_ISO_ACE:?Set GW_ISO_ACE in .env}"
test -f "$GW_ISO_ACE"

parent=_build/tmp/ultimate-kirby-rapid-lab
mod="$parent/ultimate-kirby-movement"
python ports/kirby-ultimate/tools/build_movement.py --out-parent "$parent"
python ports/kirby-ultimate/tools/build_side_b.py --mod "$mod"
python ports/kirby-ultimate/tools/build_normals.py --mod "$mod"
python ports/kirby-ultimate/tools/build_rapid_jab.py --mod "$mod"
mkdir -p "$parent/geno-lab"
cp -R melee/pc/geno/mods/geno-lab/. "$parent/geno-lab/"

export GW_ISO="$GW_ISO_ACE"
export MELEE_MODS_DIR="$(pwd -W)/$parent"
export MELEE_SCENE='mode=lab;p1=kirby;p2=fox/hu;stage=fd'
export MELEE_INPUT=none
export MELEE_PAD_SCRIPT="$(pwd -W)/ports/kirby-ultimate/probe/rapid_jab.lua"
export MELEE_VOLUME=0 GW_RUNS_KEEP=100000
tools/port/run.sh ultimate-kirby-rapid-jab --iso "$GW_ISO"
