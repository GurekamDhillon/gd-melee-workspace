#!/usr/bin/env bash
# Stage throw absolutes in an isolated pack and verify loaded ftcmd in LAB.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../../.."
. ./.env
: "${GW_ISO_ACE:?Set GW_ISO_ACE in .env}"
test -f "$GW_ISO_ACE"

pack_parent=_build/tmp/ultimate-kirby-throws-lab
pack="$pack_parent/ultimate-kirby-movement"
python ports/kirby-ultimate/tools/build_movement.py --out-parent "$pack_parent"
python ports/kirby-ultimate/tools/build_side_b.py --mod "$pack"
python ports/kirby-ultimate/tools/build_normals.py --mod "$pack"
python ports/kirby-ultimate/tools/build_throws.py --mod "$pack"
mkdir -p "$pack_parent/geno-lab"
cp -R melee/pc/geno/mods/geno-lab/. "$pack_parent/geno-lab/"

export GW_ISO="$GW_ISO_ACE"
export MELEE_MODS_DIR="$(pwd -W)/$pack_parent"
export MELEE_SCENE='mode=lab;p1=kirby;p2=fox/hu;stage=fd'
export MELEE_INPUT=none
export MELEE_PAD_SCRIPT="$(pwd -W)/ports/kirby-ultimate/probe/throws.lua"
export MELEE_VOLUME=0
export GW_RUNS_KEEP=100000
tools/port/run.sh ultimate-kirby-throws-probe --iso "$GW_ISO"
