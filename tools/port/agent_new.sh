#!/bin/bash
# Give an agent its own melee worktree and its own build root, so it can compile, link and play
# without touching anyone else's.
#
#   tools/port/agent_new.sh stages              branch off the current HEAD
#   tools/port/agent_new.sh stages origin/main  branch off something else
#
# It prints the two lines the agent needs to export. Everything else (tools/port/build.sh,
# tools/port/run.sh) then follows those automatically.
#
# The objects are HARDLINKED from the shared baseline, not copied. A full set is ~1 GB and ~989
# TUs; hardlinking costs a second and no disk, and the first time the agent rebuilds a TU the
# pipeline replaces the directory entry, so the baseline is never modified.
#
# THAT INVARIANT IS LOAD-BEARING AND IT IS NOT AUTOMATIC. gwtool truncates its -o path in place
# rather than unlinking it, so writing objects directly would mutate the inode every agent
# shares. pipe_win.sh and pipe_wsl.sh therefore write "$n.obj.tmp" and `mv` it into place; a
# rename replaces only that one directory entry. Do not "simplify" those two lines back into a
# direct -o, and be suspicious of any new tool that writes into $GW_OUT. The failure is quiet:
# builds stay green, one agent's objects link into another's exe, and the generated bridge comes
# out too small. It cost most of an evening once - docs/HANDOFF.md section 6.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
. ./portlib.sh

name="${1:-}"
base="${2:-HEAD}"
[ -n "$name" ] || gw_die "usage: agent_new.sh <name> [base-rev]"
[[ "$name" =~ ^[A-Za-z0-9_-]+$ ]] || gw_die "name must be [A-Za-z0-9_-]+"

worktree="$GW_ROOT/worktrees/$name"
root="$GW_ROOT/_build/agents/$name"
[ -e "$worktree" ] && gw_die "$worktree already exists"
[ -e "$root" ] && gw_die "$root already exists"

echo "worktree  $worktree"
git -C "$GW_ROOT/melee" worktree add -b "agent/$name" "$worktree" "$base" >/dev/null
echo "root      $root"
mkdir -p "$root/masstest/out" "$root/masstest/shimobj" "$root/runs"

echo "objects   hardlinking the baseline"
link_dir() {
    local src="$1" dst="$2" n=0
    for f in "$src"/*.obj; do
        [ -e "$f" ] || continue
        ln -f "$f" "$dst/$(basename "$f")" 2>/dev/null || cp -f "$f" "$dst/$(basename "$f")"
        n=$((n + 1))
    done
    echo "          $n objects -> $dst"
}
link_dir "$GW_ROOT/_build/masstest/out" "$root/masstest/out"
link_dir "$GW_ROOT/_build/masstest/shimobj" "$root/masstest/shimobj"

# The link response file is hand-maintained and lists exactly the right objects, so rewrite that
# curated list for this root instead of globbing the directory (which would also pick up stale
# objects from abandoned experiments).
src_rsp="$GW_ROOT/_build/melee_link_objects.rsp"
[ -f "$src_rsp" ] || gw_die "missing $src_rsp"
sed -e "s#^\.\./masstest/#$root/masstest/#" "$src_rsp" >"$root/melee_link_objects.rsp"
echo "          $(wc -l <"$root/melee_link_objects.rsp") entries in melee_link_objects.rsp"

cat <<EOF

Ready. In that agent's shell:

  export GW_MELEE="$worktree"
  export GW_BUILD_ROOT="$root"

  cd "\$GW_MELEE"
  bash "$GW_ROOT/tools/port/build.sh" --tu src/melee/ft/ftdata.c
  bash "$GW_ROOT/tools/port/run.sh" --test t --iso "C:/iso/Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso"

Remove it with: tools/port/agent_rm.sh $name
EOF
