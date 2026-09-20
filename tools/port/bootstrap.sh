#!/bin/bash
# Check that this machine can build the port, and say precisely what is missing and how to get it.
#
#   bash tools/port/bootstrap.sh
#
# It changes nothing. Five things are needed that this repository deliberately does not carry:
# a toolchain, a code generator, prebuilt third-party libraries, their runtime DLLs, and a disc
# image. The first four are large build artefacts; the fifth is Nintendo's. See SETUP.md.
set -u
cd "$(dirname "${BASH_SOURCE[0]}")"
. ./portlib.sh

missing=0
ok()   { printf '  \033[32mok\033[0m    %-28s %s\n' "$1" "$2"; }
bad()  { printf '  \033[31mMISSING\033[0m %-25s %s\n' "$1" "$2"; missing=$((missing + 1)); }
note() { printf '        %s\n' "$1"; }

echo "root      $GW_ROOT"
echo "melee     $GW_MELEE"
echo "build     $GW_BUILD_ROOT"
echo

echo "Toolchain and generators"
if [ -x "$GW_CLANG" ]; then ok clang "$GW_CLANG"; else
    bad clang "$GW_CLANG"
    note "A clang that can target both ppc32-none-eabi and i686-pc-windows-msvc."
    note "Unpack an LLVM release into _toolchains/llvm, or set GW_CLANG."
fi
gwtool="${GW_GWTOOL:-$GW_ROOT/_build/gwtool/gwtool.exe}"
if [ -x "$gwtool" ]; then ok gwtool "$gwtool"; else
    bad gwtool "$gwtool"
    note "The PowerPC->x86 retargeter. Built from melee/pc/tools/gwtool."
fi
if [ -d "$GW_MELEE/pc/platform" ]; then ok "melee worktree" "$GW_MELEE"; else
    bad "melee worktree" "$GW_MELEE"
    note "Clone the melee fork's pc-port branch into <root>/melee."
fi
echo

echo "Prebuilt third-party libraries (build_aurora_melee.bat)"
for lib in aurora_core aurora_gx aurora_main aurora_vi; do
    if [ -f "$GW_ROOT/_build/ax86m/$lib.lib" ]; then ok "$lib.lib" ""; else
        bad "$lib.lib" "$GW_ROOT/_build/ax86m/$lib.lib"
    fi
done
[ -d "$GW_IMGUI_INCLUDE" ] && ok "imgui headers" "$GW_IMGUI_INCLUDE" ||
    bad "imgui headers" "$GW_IMGUI_INCLUDE"
[ -d "$GW_SDL_INCLUDE" ] && ok "SDL3 headers" "$GW_SDL_INCLUDE" ||
    bad "SDL3 headers" "$GW_SDL_INCLUDE"
echo

echo "Runtime DLLs (copied next to melee-pc.exe by run.sh)"
for dll in SDL3.dll webgpu_dawn.dll; do
    [ -f "$GW_ROOT/_build/$dll" ] && ok "$dll" "" || bad "$dll" "$GW_ROOT/_build/$dll"
done
echo

echo "Disc images - supply your own; none is distributed with this repository"
for v in GW_ISO_VANILLA:vanilla GW_ISO_AKANEIA:Akaneia GW_ISO_ACE:ACE; do
    var="${v%%:*}" label="${v##*:}" path="${!var:-}"
    if [ -n "$path" ] && [ -f "$path" ]; then ok "$label" "$path"
    elif [ -n "$path" ]; then bad "$label" "$path  (set, but no such file)"
    else
        printf '  \033[33m-\033[0m     %-28s %s\n' "$label" "$var is not set"
        [ "$var" = GW_ISO_VANILLA ] && missing=$((missing + 1))
    fi
done
note "Set them in $GW_ROOT/.env (not tracked). Vanilla NTSC 1.02 is required;"
note "Akaneia and ACE are only needed for m-ex content."
echo

echo "MSVC (for the link step)"
# "ProgramFiles(x86)" is not a valid shell identifier (the parentheses), so it cannot be expanded
# as a variable here even though cmd.exe has it. vswhere's location is fixed by design.
vswhere="C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe"
[ -f "$vswhere" ] || vswhere="C:/Program Files/Microsoft Visual Studio/Installer/vswhere.exe"
if [ -f "$vswhere" ]; then
    vs="$("$vswhere" -latest -products '*' -property installationPath 2>/dev/null | tr -d '\r')"
    [ -n "$vs" ] && ok "Visual Studio" "$vs" || bad "Visual Studio" "vswhere found no install"
else
    bad vswhere "$vswhere"
    note "Install Visual Studio Build Tools with \"Desktop development with C++\"."
fi
echo

if [ "$missing" -eq 0 ]; then
    echo "Ready. Next:"
    echo "  bash tools/port/build.sh"
    echo "  bash tools/port/run.sh --test t --iso \"\$GW_ISO_VANILLA\""
    exit 0
fi
echo "$missing thing(s) missing - see SETUP.md."
exit 1
