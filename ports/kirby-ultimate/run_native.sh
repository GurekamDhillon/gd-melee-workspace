#!/usr/bin/env bash
# Persistent LAB session for the isolated native m-ex Ultimate Kirby prototype.
# The default additive pack preserves ACE's existing fighters, including Lucina.
# Usage: bash ports/kirby-ultimate/run_native.sh [--mod-dir _build/tmp/.../mods]
# Legacy Lucina-replacement packs require --replace-lucina explicitly.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
. ./.env
: "${GW_ISO_ACE:?Set GW_ISO_ACE in .env}"
test -f "$GW_ISO_ACE"

mods=_build/tmp/ultimate-kirby-additive-lab/mods
replace_lucina=0
while (( $# )); do
    case "$1" in
        --mod-dir) mods="${2:?--mod-dir needs a directory}"; shift 2 ;;
        --replace-lucina) replace_lucina=1; shift ;;
        *) echo 'usage: bash ports/kirby-ultimate/run_native.sh [--mod-dir PATH] [--replace-lucina]' >&2; exit 2 ;;
    esac
done
if test -f "$mods/ultimate-kirby-additive-slot/slot-build.json"; then
    test "$replace_lucina" -eq 0 || {
        echo '--replace-lucina was supplied with an additive pack' >&2; exit 2;
    }
    test ! -d "$mods/ultimate-kirby-slot" || {
        echo 'both additive and replacement Ultimate Kirby packs are present' >&2; exit 2;
    }
    pack="$mods/ultimate-kirby-additive-slot"
    python -c 'import json,sys; p=json.load(open(sys.argv[1],encoding="utf-8")); assert (p.get("mode"),p["internal"],p["external"],p.get("replaces"))==("additive",59,65,None), "native pack must add Ultimate Kirby at 59/65"' \
        "$pack/slot-build.json"
else
    test -f "$mods/ultimate-kirby-slot/slot-build.json" || {
        echo "native Ultimate Kirby slot pack missing from $mods" >&2; exit 2;
    }
    test "$replace_lucina" -eq 1 || {
        echo 'this pack replaces Lucina; pass --replace-lucina to launch it' >&2; exit 2;
    }
    pack="$mods/ultimate-kirby-slot"
    python -c 'import json,sys; p=json.load(open(sys.argv[1],encoding="utf-8")); assert (p["internal"],p["external"],p["replaces"]["name"])==(53,52,"Lucina"), "native pack must explicitly replace ACE Lucina 53/52"' \
        "$pack/slot-build.json"
fi
test -s "$pack/files/PlUk.dat" && test -s "$pack/files/PlUkAJ.dat" &&
test -s "$pack/files/MxDt.dat" || {
    echo "native slot fighter, animation, or m-ex data missing from $pack" >&2; exit 2;
}
test -d worktrees/kirby_native || {
    echo 'missing isolated melee worktree: create kirby_native with tools/port/agent_new.sh' >&2; exit 2;
}

export GW_MELEE="$(cd worktrees/kirby_native && pwd -W)"
export GW_BUILD_ROOT="$(pwd -W)/_build/agents/kirby_native"
export MELEE_MODS_DIR="$(cd "$mods" && pwd -W)"
export MELEE_SCENE='mode=lab;p1=ultimatekirby;p2=fox/cpu0;stage=fd'
export MELEE_VOLUME=3 GW_RUNS_KEEP=100000
unset MELEE_INPUT MELEE_PAD_SCRIPT

# LAB's saved Inspect view keeps the fighter unobscured for visual assessment.
settings="$GW_BUILD_ROOT/runs/ultimate-kirby-native-play/scripts-data/geno-lab_lab/settings.txt"
mkdir -p "$(dirname "$settings")"
if [ ! -f "$settings" ]; then printf 'mode=inspect\nhidden=false\n' > "$settings"; fi

tools/port/build.sh
tools/port/run.sh ultimate-kirby-native-play --iso "$GW_ISO_ACE"
