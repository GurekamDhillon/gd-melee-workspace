#!/bin/bash
# Commit nothing; build the Windows lane exe and (in parallel) the Linux lane ELF from the lane's committed HEAD.
# usage: build_both.sh   (needs env_win.sh sourced; the Linux tree is ~/lb2/mD in WSL)
. "$(dirname "${BASH_SOURCE[0]}")/env_win.sh"
cd "$GW_MELEE"
# the main workspace's build.sh predates the build-id stamp: stamp with this lane's tool first
python "$(dirname "${BASH_SOURCE[0]}")/../port/build_id.py" --melee "$GW_MELEE"
( bash "$GW_ROOT_ENV/tools/port/build.sh" > "$GW_BUILD_ROOT/build_last.log" 2>&1; echo "win rc=$?" ) &
export MSYS_NO_PATHCONV=1
wsl -d Debian -- bash -lc 'cd ~/lb2/mD && git checkout -q -- pc/platform/gw_mex_bridge.c && git pull -q; cd ../wsD && git pull -q; cd ..; export MELEE_VANILLA_ISO="/mnt/c/iso/Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso"; ./enter.sh bash /mnt/h/d_game.sh > game_last.log 2>&1; echo "linux rc=$?"; tail -2 game_last.log'
wait
tail -2 "$GW_BUILD_ROOT/build_last.log"
