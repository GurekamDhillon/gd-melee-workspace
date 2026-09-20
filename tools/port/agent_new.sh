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
#
# Each path is QUOTED on the way out. The shared file's entries are relative (../masstest/...) and
# so never contain a space; an agent root's are absolute, and link.exe splits an unquoted response
# -file line on whitespace. With a checkout at "C:/Users/.../GD's Melee" that produced
# `LNK1181: cannot open input file 'C:\Users\Gurek\Desktop\GD's.obj'` and no agent could link
# at all. link.exe accepts quotes around every path, space or not, so quote unconditionally.
# THREE THINGS A FRESH WORKTREE GETS WRONG. Each cost a separate agent real time before this
# existed, and two of them look nothing like what they are.
#
# 1. EVERY TU LOOKS STALE. build.sh rebuilds a TU whose source is newer than its object, and a
#    fresh `git worktree add` stamps every file with the checkout time - so the whole 988-TU set
#    looks stale and the agent's first build is a full rebuild. Backdate the checkout to before
#    the hardlinked baseline. Edits get fresh mtimes, so this is self-correcting and only affects
#    files nobody has touched.
# 2. TWO GENERATED HEADERS ARE NOT IN GIT. src/sysdolphin/baselib/{debug_font,sislib_font}.inc
#    are produced by pc/tools/extract_assets.py into build/GALE01/include/. Without them a real
#    full rebuild fails on those two TUs, long after setup, with an error that says nothing about
#    worktrees. Copy them across.
# 3. AURORA MUST BE BUILT THROUGH C:\gdm. _build/ax86m is configured against that junction, which
#    avoids the apostrophe in "GD's Melee". Building it through the real path poisons the cmake
#    cache and the next regenerate fails deep inside Dawn's third-party tree - a failure that
#    looks like a broken dependency, not a path problem. Noted in the ready-message below.
inc_src="$GW_ROOT/melee/build/GALE01/include"
if [ -d "$inc_src" ]; then
    inc_dst="$worktree/build/GALE01/include"
    mkdir -p "$inc_dst"
    ( cd "$inc_src" && find . -name '*.inc' -print0 ) |
        ( cd "$inc_src" && xargs -0 -I{} sh -c 'mkdir -p "$2/$(dirname "$1")" && cp -f "$1" "$2/$1"' _ {} "$inc_dst" )
    echo "includes  $(find "$inc_dst" -name '*.inc' | wc -l | tr -d ' ') generated .inc copied"
fi

# Anchor to the OLDEST object, not the newest: a source newer than ANY object it feeds is stale,
# so the whole checkout has to predate the earliest one. Using the newest left most of the tree
# looking stale and the backdating did nothing.
oldest_obj="$(ls -1tr "$GW_ROOT/_build/masstest/out"/*.obj 2>/dev/null | head -1)"
if [ -n "$oldest_obj" ]; then
    # A full minute before the oldest object. Matching it exactly would also work - build.sh
    # tests -nt, which is strictly-newer - but sub-second timestamps make equality a coin flip.
    obj_epoch="$(date -r "$oldest_obj" +%s 2>/dev/null)"
    stamp=""
    [ -n "$obj_epoch" ] && stamp="$(date -d "@$((obj_epoch - 60))" +%Y%m%d%H%M.%S 2>/dev/null)"
    if [ -n "$stamp" ]; then
        n=0
        for d in src pc extern include; do
            [ -d "$worktree/$d" ] || continue
            find "$worktree/$d" -type f \( -name '*.c' -o -name '*.h' -o -name '*.cpp'                  -o -name '*.inc' \) -exec touch -t "$stamp" {} + 2>/dev/null
            n=$((n + 1))
        done
        echo "mtimes    $n source trees backdated to $stamp (before the object baseline)"
    fi
fi

src_rsp="$GW_ROOT/_build/melee_link_objects.rsp"
[ -f "$src_rsp" ] || gw_die "missing $src_rsp"
sed -e "s#^\.\./masstest/#$root/masstest/#" -e 's#^\(..*\)$#"\1"#' \
    "$src_rsp" >"$root/melee_link_objects.rsp"
echo "          $(wc -l <"$root/melee_link_objects.rsp") entries in melee_link_objects.rsp"

cat <<EOF

Ready. In that agent's shell:

  export GW_MELEE="$worktree"
  export GW_BUILD_ROOT="$root"

  cd "\$GW_MELEE"
  bash "$GW_ROOT/tools/port/build.sh" --tu src/melee/ft/ftdata.c
  bash "$GW_ROOT/tools/port/run.sh" --test t --iso "C:/iso/Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso"

If you need to rebuild vendored aurora, do it THROUGH THE JUNCTION or you will poison the
cmake cache and the next regenerate will fail inside Dawn's third-party tree:

  GW_ROOT=C:/gdm cmd //c "C:\gdm\_build\build_aurora_melee.bat"

Remove it with: tools/port/agent_rm.sh $name
EOF
