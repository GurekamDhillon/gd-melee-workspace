#!/bin/bash
# Remove an agent's worktree and build root (tools/port/agent_new.sh made them).
#
#   tools/port/agent_rm.sh stages
#
# The branch agent/<name> is LEFT ALONE: the worktree is scratch space, the commits on it may not
# be. Delete it yourself with `git -C melee branch -D agent/<name>` once you are sure.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
. ./portlib.sh

name="${1:-}"
[ -n "$name" ] || gw_die "usage: agent_rm.sh <name>"
[[ "$name" =~ ^[A-Za-z0-9_-]+$ ]] || gw_die "name must be [A-Za-z0-9_-]+"

worktree="$GW_ROOT/worktrees/$name"
root="$GW_ROOT/_build/agents/$name"

if [ -d "$worktree" ]; then
    dirty="$(git -C "$worktree" status --porcelain | head -5)"
    if [ -n "$dirty" ]; then
        echo "$worktree has uncommitted changes:" >&2
        echo "$dirty" >&2
        gw_die "commit or discard them first (this script will not throw work away)"
    fi
    git -C "$GW_ROOT/melee" worktree remove "$worktree"
    echo "removed   $worktree"
fi
if [ -d "$root" ]; then
    # cmd's rmdir /s removes junctions without entering them; rm -rf may follow one into the tree
    # it points at. The doubled slashes stop Git Bash rewriting the switches as paths.
    cmd //c rmdir //s //q "$(cygpath -w "$root")"
    echo "removed   $root"
fi
echo "branch agent/$name kept; delete with: git -C \"$GW_ROOT/melee\" branch -D agent/$name"
