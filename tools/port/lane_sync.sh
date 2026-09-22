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

if [ "$mode" != "--pull" ]; then
    [ -z "$(git -C "$main" status --porcelain --untracked-files=no)" ] ||
        gw_die "the main melee checkout has uncommitted changes - not fast-forwarding pc-port"
    [ "$(git -C "$main" branch --show-current)" = "pc-port" ] || gw_die "main melee checkout is not on pc-port"
    git -C "$main" merge --ff-only -q "agent/$name"
    echo "published pc-port -> $(git -C "$main" log --oneline -1)"
fi

# Remind about the one shared file that is not in the melee repo.
if ! diff -q <(grep -o '[^/"]*\.obj' "$GW_ROOT/_build/melee_link_objects.rsp" | sort) \
              <(grep -o '[^/"]*\.obj' "$GW_ROOT/_build/agents/$name/melee_link_objects.rsp" | sort) >/dev/null; then
    echo "NOTE      the link lists differ between _build/ and _build/agents/$name/ - a lane added or"
    echo "          removed a TU/shim. Add it to _build/melee_link_objects.rsp (root repo, commit it)"
    echo "          and to the other lane's _build/agents/<lane>/melee_link_objects.rsp (quoted, absolute)."
fi
