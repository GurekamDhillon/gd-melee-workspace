#!/bin/bash
# Shared environment for the port's build and run scripts (tools/port/*.sh). Source it; do not
# run it.
#
# GW_BUILD_ROOT is the knob that makes parallel work possible. It names the directory holding one
# tree's object files, link response file and melee-pc.exe. It defaults to C:/gdm/_build, so a
# single-agent session behaves exactly as before; agent_new.sh points a git worktree at
# C:/gdm/_build/agents/<name> instead, and from then on two agents never write the same file.
#
# What stays shared on purpose:
#   - $GW_ROOT/_build/ax86m     the Aurora/Dawn/SDL3 import libraries. melee_link_libs.rsp names
#                               them relative to that directory, so the link always runs there;
#                               only its OUTPUTS move per agent. They are read-only here and cost
#                               gigabytes to duplicate.
#   - the ISOs ($GW_ISO_*)      read-only.
#   - melee/config/GALE01/symbols.txt via the worktree, which each agent has its own copy of.
#
# NOTHING HERE IS TIED TO A PARTICULAR CHECKOUT PATH. GW_ROOT defaults to the directory two levels
# above this script, so a fresh clone works with no setup and no C:/gdm symlink; exporting GW_ROOT
# still wins. See SETUP.md.

# The toolchain (clang.exe, gwtool.exe, link.exe) is native Windows and cannot read /c/... paths,
# so the root must be a Windows-style path even though this is bash. `pwd -W` gives that under Git
# Bash; the fallback rewrites an MSYS /c/... prefix by hand for other shells.
gw_win_path() {
    local d="$1"
    ( cd "$d" 2>/dev/null && { pwd -W 2>/dev/null || pwd; } ) |
        sed -E 's#^/([a-zA-Z])/#\1:/#'
}

if [ -z "${GW_ROOT:-}" ]; then
    GW_ROOT="$(gw_win_path "$(dirname "${BASH_SOURCE[0]}")/../..")"
fi
GW_BUILD_ROOT="${GW_BUILD_ROOT:-$GW_ROOT/_build}"

# The melee worktree to build FROM: an explicit GW_MELEE wins, then the git repo the caller is
# standing in (so an agent in its own worktree needs no configuration), then the default checkout.
if [ -z "${GW_MELEE:-}" ]; then
    GW_MELEE="$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null || true)"
    if [ -z "$GW_MELEE" ] || [ ! -d "$GW_MELEE/pc/platform" ]; then
        GW_MELEE="$GW_ROOT/melee"
    fi
fi

GW_OUT="${GW_OUT:-$GW_BUILD_ROOT/masstest/out}"          # gwtool-transformed game TU objects
GW_SHIMOBJ="${GW_SHIMOBJ:-$GW_BUILD_ROOT/masstest/shimobj}"  # native platform shim objects
GW_EXE="$GW_BUILD_ROOT/melee-pc.exe"
GW_MAP="$GW_BUILD_ROOT/melee-pc.map"
GW_LINK_OBJECTS="${GW_LINK_OBJECTS:-$GW_BUILD_ROOT/melee_link_objects.rsp}"

# Optional per-machine settings: ISO paths and any toolchain override. Not tracked (see
# .gitignore); SETUP.md documents it. Sourced before the defaults below so it can set anything.
if [ -f "$GW_ROOT/.env" ]; then
    # shellcheck disable=SC1091
    . "$GW_ROOT/.env"
fi

# The discs. Supply your own legally dumped images; none is distributed with this repo.
# GW_ISO is what run.sh uses when --iso is not given.
GW_ISO_VANILLA="${GW_ISO_VANILLA:-}"
GW_ISO_AKANEIA="${GW_ISO_AKANEIA:-}"
GW_ISO_ACE="${GW_ISO_ACE:-}"
GW_ISO="${GW_ISO:-$GW_ISO_VANILLA}"

GW_CLANG="${GW_CLANG:-$GW_ROOT/_toolchains/llvm/bin/clang.exe}"
GW_SDL_INCLUDE="${GW_SDL_INCLUDE:-$GW_ROOT/_build/ax86/_deps/sdl3_prebuilt-src/include}"
GW_IMGUI_INCLUDE="${GW_IMGUI_INCLUDE:-$GW_ROOT/_build/ax86m/_deps/imgui-src}"  # C++ shims only

gw_die() {
    echo "error: $*" >&2
    exit 1
}

gw_env_summary() {
    echo "melee     $GW_MELEE"
    echo "build     $GW_BUILD_ROOT"
    echo "objects   $GW_OUT"
    echo "shims     $GW_SHIMOBJ"
    echo "exe       $GW_EXE"
}

# A shim .c under pc/platform -> its object. Shim sources are native x86, NOT gwtool input, and
# they need the SDL3 headers: main.c, shim_ax.c and shim_vi.c reach them through aurora/event.h.
gw_build_shim() {
    local src="$1" name
    local -a extra=()
    case "$src" in
    *.cpp)
        # gw_overlay.cpp is the only C++ shim: it drives Dear ImGui, which Aurora already links
        # (extern\imgui.lib) and already pumps around every frame. It needs ImGui's own headers,
        # which live in Aurora's CMake dependency tree rather than anywhere on the include path.
        name="$(basename "$src" .cpp)"
        # -fms-runtime-lib=dll (/MD) is required, not cosmetic. clang defaults this target to the
        # STATIC CRT, while Aurora and ImGui are built against the DYNAMIC one (their objects ask
        # for MSVCRT + msvcprt). Getting it wrong fails the link in two different ways: as static,
        # a wall of LNK2005 "already defined in libcpmt.lib(cout.obj)"; as static-with-/MT, a wall
        # of unresolved __imp__ symbols from imgui/absl/png instead.
        # An ARRAY, not a word-split string: the checkout path may contain spaces (the author's
        # does - "GD's Melee"), and the old `extra="... -I $GW_IMGUI_INCLUDE"` silently split it,
        # so clang looked for "Melee/_build/..." and the build linked a STALE object instead.
        extra=(-std=c++17 -fms-runtime-lib=dll -I "$GW_IMGUI_INCLUDE")
        [ -d "$GW_IMGUI_INCLUDE" ] ||
            gw_die "no ImGui headers at $GW_IMGUI_INCLUDE - set GW_IMGUI_INCLUDE"
        ;;
    *)
        name="$(basename "$src" .c)"
        ;;
    esac
    [ -f "$GW_MELEE/pc/platform/$src" ] || gw_die "no such shim: pc/platform/$src"
    mkdir -p "$GW_SHIMOBJ"
    # Remove the old object FIRST. Otherwise a failed compile leaves the previous one in place,
    # the existence check below passes, and the link silently produces an exe built from stale
    # code - the same class of lie as a failed link leaving the old exe, which build.sh already
    # guards against. This was not hypothetical: it happened the first time a checkout path with
    # a space was used.
    rm -f "$GW_SHIMOBJ/$name.obj"
    "$GW_CLANG" --target=i686-pc-windows-msvc -c -O2 -DTARGET_PC "${extra[@]}" \
        -I "$GW_MELEE/extern/aurora/include" -I "$GW_MELEE/pc/platform" -I "$GW_SDL_INCLUDE" \
        -I "$GW_MELEE/extern/enet/include" \
        "$GW_MELEE/pc/platform/$src" -o "$GW_SHIMOBJ/$name.obj" 2>&1 |
        grep -E "error|warning: .*(uninitialized|implicit)" || true
    [ -f "$GW_SHIMOBJ/$name.obj" ] || gw_die "shim $src did not compile"
}

# A game TU (path relative to the melee worktree) through clang -> gwtool -> object.
gw_build_tu() {
    local f="$1"
    ( cd "$GW_MELEE" && GW_OUT="$GW_OUT" bash "$GW_ROOT/_build/masstest/pipe_win.sh" "$f" ) ||
        gw_die "TU failed: $f"
}

# Link. Always runs in _build/ax86m (see the note above); only the outputs follow GW_BUILD_ROOT.
# The batch file's own exit code is not trustworthy through cmd.exe here, so key off the
# MELEE_PC_LINK_OK line it prints on success - otherwise a link error scrolls past and the next
# step happily runs against a stale exe.
gw_link() {
    local out
    mkdir -p "$GW_BUILD_ROOT"
    out="$( cd "$GW_ROOT/_build/ax86m" &&
        GW_ROOT="$(cygpath -w "$GW_ROOT" 2>/dev/null || echo "$GW_ROOT")" \
        GW_BUILD_ROOT="$(cygpath -w "$GW_BUILD_ROOT" 2>/dev/null || echo "$GW_BUILD_ROOT")" \
        GW_LINK_OBJECTS="$(cygpath -w "$GW_LINK_OBJECTS" 2>/dev/null || echo "$GW_LINK_OBJECTS")" \
            cmd.exe //c "$(cygpath -w "$GW_ROOT/_build/build_melee_pc.bat")" 2>&1 )" || true
    if ! grep -q MELEE_PC_LINK_OK <<<"$out"; then
        grep -v "vswhere" <<<"$out" | tail -15 >&2
        gw_die "link failed"
    fi
    echo "      -> $GW_EXE"
}
