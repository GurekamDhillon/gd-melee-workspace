#!/usr/bin/env bash
# Check a real grab, throw action, and victim damage on the native additive slot.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../../.."
. ./.env
: "${GW_ISO_ACE:?Set GW_ISO_ACE in .env}"
mods="${1:-_build/tmp/ultimate-kirby-additive-visual-fixed/mods}"
variant="${2:-f}"
case "$variant" in
    f) costume=0; name=ultimate-kirby-throw-live ;;
    b) costume=1; name=ultimate-kirby-throw-live-b ;;
    hi) costume=2; name=ultimate-kirby-throw-live-hi ;;
    lw) costume=3; name=ultimate-kirby-throw-live-lw ;;
    *) echo 'throw variant must be f, b, hi, or lw' >&2; exit 2 ;;
esac
test -f "$mods/ultimate-kirby-additive-slot/slot-build.json"
export GW_MELEE="$(cd worktrees/kirby_native && pwd -W)"
export GW_BUILD_ROOT="$(pwd -W)/_build/agents/kirby_native"
export MELEE_MODS_DIR="$(cd "$mods" && pwd -W)"
export MELEE_SCENE="mode=lab;p1=ultimatekirby;p2=fox/c${costume}/hu;stage=fd"
export MELEE_PAD_SCRIPT="$(pwd -W)/ports/kirby-ultimate/probe/throw_live.lua"
export MELEE_INPUT=none MELEE_VOLUME=0 GW_RUNS_KEEP=100000
tools/port/run.sh "$name" --iso "$GW_ISO_ACE"
