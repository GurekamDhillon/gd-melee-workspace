#!/bin/bash
# List (default) or remove (--apply) old agent worktrees that can go without losing anything:
# a worktree is removed only when it has no uncommitted changes to tracked files AND its branch
# has no commits that pc-port (melee) / master (root) lacks. Branches are always kept, so any
# removed worktree can be recreated with `git worktree add`. The live lanes are never touched.
#
#   tools/port/prune_worktrees.sh            dry run: what would go, what stays and why
#   tools/port/prune_worktrees.sh --apply    remove them (and their _build/agents/<name> roots)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
. ./portlib.sh
apply=0; [ "${1:-}" = "--apply" ] && apply=1
keep_lanes="alpha beta"

check() { # repo base worktree
    local repo="$1" base="$2" w="$3" br dirty ahead name
    br="$(git -C "$w" branch --show-current 2>/dev/null || true)"
    name="$(basename "$w")"
    for l in $keep_lanes; do [ "$name" = "$l" ] && { echo "keep  $w (live lane)"; return; }; done
    dirty="$(git -C "$w" status --porcelain --untracked-files=no 2>/dev/null | wc -l)"
    ahead="$(git -C "$repo" rev-list --count "$base..$br" 2>/dev/null || echo '?')"
    if [ "$dirty" != 0 ] || [ "$ahead" != 0 ]; then
        echo "keep  $w ($dirty uncommitted, $ahead unmerged commit(s) on $br)"
        return
    fi
    if [ $apply = 1 ]; then
        # core.longpaths: agent worktrees hold paths past MAX_PATH ("Filename too long")
        if git -c core.longpaths=true -C "$repo" worktree remove "$w"; then
            echo "gone  $w (branch $br kept)"
            case "$w" in */worktrees/*)
                if [ -d "$GW_ROOT/_build/agents/$name" ]; then
                    rm -rf "$GW_ROOT/_build/agents/$name" && echo "gone  _build/agents/$name"
                fi;;
            esac
        else
            echo "FAIL  $w (left in place)"
        fi
    else
        echo "would remove  $w (clean, merged; branch $br kept)"
    fi
}

for repo_base in "$GW_ROOT/melee:pc-port" "$GW_ROOT:master"; do
    repo="${repo_base%:*}"; base="${repo_base##*:}"
    git -C "$repo" worktree list --porcelain | sed -n 's/^worktree //p' | tail -n +2 |
        while read -r w; do check "$repo" "$base" "$w"; done
done
[ $apply = 1 ] && { git -C "$GW_ROOT/melee" worktree prune; git -C "$GW_ROOT" worktree prune; }
[ $apply = 1 ] || echo "(dry run - rerun with --apply to remove)"
