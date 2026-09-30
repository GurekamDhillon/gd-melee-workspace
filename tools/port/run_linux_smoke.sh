#!/bin/bash
# Isolated, bounded acceptance run. Pass disc path, test|scene, and duration in seconds.
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"
disc="$(realpath "${1:?disc path required}")"
mode="${2:-test}"
seconds="${3:-60}"
source_build="${GW_BUILD_ROOT:-$root/_build/agents/linux}"
run="$(mktemp -d "$source_build/run-XXXXXXXX")"
cp --reflink=auto "$source_build/melee" "$source_build/melee-pc.msvc.map" "$run/"
cp -a "$source_build/assets" "$source_build/ui" "$run/"
sha256sum "$run/melee" > "$run/executable.sha256"
printf 'disc=%s\nmode=%s\nseconds=%s\n' "$disc" "$mode" "$seconds" > "$run/run.txt"
echo "RUN $run"
cd "$run"
set +e
if [ "$mode" = test ]; then
    timeout --kill-after=5 "$seconds" ./melee --test --iso "$disc" > run.log 2>&1
else
    MELEE_SCENE="$mode" timeout --kill-after=5 "$seconds" ./melee --iso "$disc" > run.log 2>&1
fi
result=$?
printf 'exit=%s\n' "$result" >> run.txt
tail -20 run.log
exit "$result"
