#!/bin/bash
# Sync a long-lived lane (an agent_new.sh worktree) with pc-port, between tasks.
#
#   tools/port/lane_sync.sh alpha          rebase agent/alpha onto pc-port, then fast-forward
#                                          pc-port to it (publishes this lane's commits)
#   tools/port/lane_sync.sh alpha --pull   only rebase onto pc-port (take the other lane's work)
#
# Lanes never push to GitHub; pc-port in the main melee checkout is the meeting point, and the
# user pushes it. A lock directory serializes the two lanes so their fast-forwards cannot race.
# The lane's worktree must be clean (everything committed) - uncommitted work is never touched.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
. ./portlib.sh

name="${1:-}"
mode="${2:-}"
[ -n "$name" ] || gw_die "usage: lane_sync.sh <lane> [--pull]"
wt="$GW_ROOT/worktrees/$name"
main="$GW_ROOT/melee"
lock="$GW_ROOT/_build/lane_sync.lock"
[ -d "$wt" ] || gw_die "no worktree $wt (make it with agent_new.sh $name)"

for i in $(seq 1 120); do
    mkdir "$lock" 2>/dev/null && break
    [ "$i" = 120 ] && gw_die "lock $lock held for 2 minutes - is the other lane mid-sync? remove it if stale"
    sleep 1
done
trap 'rmdir "$lock" 2>/dev/null || true' EXIT

[ -z "$(git -C "$wt" status --porcelain --untracked-files=no)" ] ||
    gw_die "$wt has uncommitted changes to tracked files - commit them first"

before="$(git -C "$wt" rev-parse HEAD)"
if ! git -C "$wt" rebase pc-port >/dev/null 2>&1; then
    git -C "$wt" rebase --abort >/dev/null 2>&1 || true
    gw_die "rebase of agent/$name onto pc-port conflicts - merge by hand in $wt (git rebase pc-port), then rerun"
fi
echo "rebased   agent/$name: $(git -C "$wt" log --oneline -1)"
echo "picked up $(git -C "$wt" rev-list --count "$before".."$(git -C "$wt" rev-parse pc-port)" 2>/dev/null || echo '?') commit(s) from pc-port"
# Re-stamp every source file the sync brought in, so build.sh's staleness check can never miss
# one (a lane once had to --tu other lanes' files by hand before its link would succeed).
changed="$(git -C "$wt" diff --name-only "$before" HEAD -- '*.c' '*.h' '*.inc' 2>/dev/null || true)"
if [ -n "$changed" ]; then
    (cd "$wt" && echo "$changed" | while read -r f; do [ ! -f "$f" ] || touch "$f"; done)
    echo "touched   $(echo "$changed" | wc -l) changed source file(s); the next build.sh rebuilds them"
    echo "$changed" | grep '^pc/platform/.*\.c$' | sed 's|^pc/platform/|          shim changed - pass --shim |' || true
fi

if [ "$mode" != "--pull" ]; then
    [ -z "$(git -C "$main" status --porcelain --untracked-files=no)" ] ||
        gw_die "the main melee checkout has uncommitted changes - not fast-forwarding pc-port"
    [ "$(git -C "$main" branch --show-current)" = "pc-port" ] || gw_die "main melee checkout is not on pc-port"
    git -C "$main" merge --ff-only -q "agent/$name"
    echo "published pc-port -> $(git -C "$main" log --oneline -1)"
fi

# Regenerate this lane's link list from the shared one (the same transform agent_new.sh uses), so
# objects other lanes added reach this lane without anyone editing its list by hand. Entries only
# this lane has (objects it hasn't published yet) are kept at the end.
src_rsp="$GW_ROOT/_build/melee_link_objects.rsp"
lane_root="$GW_ROOT/_build/agents/$name"
lane_rsp="$lane_root/melee_link_objects.rsp"
if [ -f "$src_rsp" ] && [ -f "$lane_rsp" ]; then
    new_rsp="$lane_rsp.new"
    sed -e "s#^\.\./masstest/#$lane_root/masstest/#" -e 's#^\(..*\)$#""#' "$src_rsp" >"$new_rsp"
    shared_names="$(grep -o '[^/"]*\.obj' "$new_rsp" | sort -u)"
    extra=0
    while IFS= read -r line; do
        obj="$(echo "$line" | grep -o '[^/"]*\.obj' || true)"
        [ -n "$obj" ] || continue
        if ! echo "$shared_names" | grep -qxF "$obj"; then echo "$line" >>"$new_rsp"; extra=$((extra + 1)); fi
    done <"$lane_rsp"
    mv -f "$new_rsp" "$lane_rsp"
    echo "link list regenerated from _build/ ($(wc -l <"$lane_rsp") entries, $extra only in this lane -"
    echo "          add those to _build/melee_link_objects.rsp when you publish them)"
fi
