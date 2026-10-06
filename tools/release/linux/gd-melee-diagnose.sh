#!/bin/sh
# gd-melee-diagnose.sh - "the game will not start" in one file you can attach.
#
#   ./gd-melee-diagnose.sh                 run it from the folder you extracted GD's Melee into
#   ./gd-melee-diagnose.sh /path/to/game   or point it at the game folder
#   ./gd-melee-diagnose.sh -o report.txt   choose the output file (default: gd-melee-diagnostics-<time>.txt here)
#
# It needs only POSIX sh and coreutils (ldd, readelf, file, lspci, vulkaninfo are used when present). It
# never starts the game and never reads your disc image. It also asks the Qt launcher to start with its
# stderr captured, which is how "the launcher does not even open" is told apart from "the game fails".
#
# The same checks, in the same words, are written by the launcher itself on every launch (see
# tools/release/README.md, "Linux: the game will not start"). Keep the two in step.
#
# Privacy: the report holds versions, the distribution, the kernel, the GPU model and the results of the
# file checks. Your home folder is shown as ~; user name, computer name, IP and MAC addresses are
# replaced; disc images appear by file name only; the whole environment is never dumped.

set -u
umask 077

OUT=
ROOT=
while [ $# -gt 0 ]; do
    case "$1" in
    -o) OUT=${2:-}; shift 2 || exit 2 ;;
    -h|--help) sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) ROOT=$1; shift ;;
    esac
done
if [ -z "$ROOT" ]; then
    ROOT=$(dirname -- "$0")
fi
ROOT=$(cd -- "$ROOT" 2>/dev/null && pwd) || { printf 'gd-melee-diagnose: cannot enter the game folder\n' >&2; exit 2; }
STAMP=$(date +%Y%m%d-%H%M%S)
[ -n "$OUT" ] || OUT=$PWD/gd-melee-diagnostics-$STAMP.txt
BODY=$(mktemp "${TMPDIR:-/tmp}/gd-melee-diag.XXXXXX") || exit 2
trap 'rm -f "$BODY" "$BODY.err" "$BODY.out"' EXIT INT TERM

# ---- helpers ------------------------------------------------------------------------------------
h() { printf '\n== %s ==\n' "$1"; }
have() { command -v "$1" >/dev/null 2>&1; }
# first N bytes as decimal values, space separated: byte offset, count
bytes() { od -An -v -tu1 -j"$2" -N"$3" "$1" 2>/dev/null | tr -s ' \n' ' ' | sed 's/^ //; s/ $//'; }
# ELF class of a file: 32, 64, or empty when it is not an ELF file
elfbits() {
    [ -r "$1" ] && [ -f "$1" ] || return 0
    m=$(bytes "$1" 0 5)
    case "$m" in
    "127 69 76 70 1") printf 32 ;;
    "127 69 76 70 2") printf 64 ;;
    esac
}
# e_machine, little-endian 16 bit at offset 18
elfmachine() { set -- $(bytes "$1" 18 2); [ $# -eq 2 ] && printf '%s' $(( $1 + 256 * $2 )); }
machine_name() {
    case "$1" in 3) printf 'i386 (32-bit x86)' ;; 62) printf 'x86-64' ;; 40) printf 'ARM' ;; 183) printf 'AArch64' ;; *) printf 'machine %s' "$1" ;; esac
}
# the dynamic loader named inside the binary (PT_INTERP): readelf when there, else the string near the start
interp_of() {
    r=
    have readelf && r=$(readelf -l "$1" 2>/dev/null | sed -n 's/.*Requesting program interpreter: \([^]]*\)].*/\1/p' | head -n 1)
    # readelf prints nothing for a truncated file; the loader path is a plain string near the start
    [ -n "$r" ] || r=$(head -c 4096 -- "$1" 2>/dev/null | tr -c '[:print:]' '\n' | grep -a '^/.*ld.*\.so' | head -n 1)
    printf '%s' "$r"
}
needed_of() {
    if have readelf; then readelf -d "$1" 2>/dev/null | sed -n 's/.*(NEEDED).*\[\(.*\)\].*/\1/p'
    elif have objdump; then objdump -p "$1" 2>/dev/null | sed -n 's/^ *NEEDED *//p'
    fi
}
LIBDIRS32="/lib32 /usr/lib32 /lib/i386-linux-gnu /usr/lib/i386-linux-gnu /lib/i686-linux-gnu /usr/lib/i686-linux-gnu /usr/lib /lib"
# first 32-bit file with this name in the game's lib folder or the system's 32-bit folders
find32() {
    for d in "$ROOT/lib" $LIBDIRS32; do
        [ -e "$d/$1" ] || continue
        [ "$(elfbits "$d/$1")" = 32 ] && { printf '%s' "$d/$1"; return 0; }
    done
    return 1
}
mount_info() {
    p=$(readlink -f -- "$1" 2>/dev/null || printf '%s' "$1")
    MI_FILE=${GD_DIAG_MOUNTINFO:-/proc/self/mountinfo}   # overridable for the shell test
    [ -r "$MI_FILE" ] || return 0
    awk -v p="$p" '{
        mp = $5; gsub(/\\040/, " ", mp)
        pre = (mp == "/") ? "/" : mp "/"
        if (p == mp || index(p, pre) == 1) if (length(mp) >= best) { best = length(mp); o = $6; for (i = 7; i <= NF; i++) if ($i == "-") { fs = $(i + 1); break }; m = mp }
    } END { if (best) printf "%s|%s|%s\n", fs, m, o }' "$MI_FILE"
}
arch_hint() {
    printf 'Arch family (CachyOS, Manjaro, EndeavourOS): enable [multilib] in /etc/pacman.conf, then install lib32-glibc lib32-mesa lib32-vulkan-icd-loader and %s. The GPU package is a guess from the GPU vendor.' "$1"
}

# ---- verdict flags (filled while the report is written) ---------------------------------------------
V_BIN_MISSING=; V_NOT_ELF=; V_WRONG_ARCH=; V_NOT_EXEC=; V_NOEXEC_MOUNT=; V_NO_LOADER=; V_LIB_MISSING=; V_NO_VK32=; V_LAUNCHER_FAIL=; V_LAUNCHER_OK=
GPUVENDORS=

BIN=$ROOT/bin/melee
[ -e "$BIN" ] || BIN=$ROOT/melee

{
h "Launcher"
printf 'Written: %s\n' "$(date '+%Y-%m-%dT%H:%M:%S')"
printf 'Script: gd-melee-diagnose.sh (POSIX sh)\n'
printf 'Game folder: %s\n' "$ROOT"
printf 'Working directory: %s\n' "$PWD"
[ -r "$ROOT/version.txt" ] && printf 'Game version: %s\n' "$(head -n 1 "$ROOT/version.txt")"
printf 'Qt launcher present: %s\n' "$([ -x "$ROOT/launcher/bin/gd-melee-launcher" ] && echo yes || echo 'NO (launcher/bin/gd-melee-launcher)')"

h "System"
if [ -r /etc/os-release ]; then
    # shellcheck disable=SC1091
    ( . /etc/os-release; printf 'os-release: ID=%s NAME="%s" VERSION_ID=%s ID_LIKE=%s VARIANT_ID=%s\n' "${ID:-}" "${NAME:-}" "${VERSION_ID:-}" "${ID_LIKE:-}" "${VARIANT_ID:-}" )
    OSID=$( . /etc/os-release; printf '%s %s' "${ID:-}" "${ID_LIKE:-}" )
else
    printf 'os-release: not readable\n'; OSID=
fi
printf 'Kernel: %s %s, machine %s\n' "$(uname -s)" "$(uname -r)" "$(uname -m)"
printf 'Session: XDG_SESSION_TYPE=%s WAYLAND_DISPLAY=%s DISPLAY=%s XDG_CURRENT_DESKTOP=%s\n' "${XDG_SESSION_TYPE:-(unset)}" "${WAYLAND_DISPLAY:-(unset)}" "${DISPLAY:-(unset)}" "${XDG_CURRENT_DESKTOP:-(unset)}"
HOW=
[ -n "${GAMESCOPE_WAYLAND_DISPLAY:-}" ] && HOW="$HOW gamescope"
[ "${SteamDeck:-}" = 1 ] && HOW="$HOW steamos-handheld"
{ [ -n "${SteamGameId:-}" ] || [ -n "${SteamAppId:-}" ]; } && HOW="$HOW steam"
[ -t 0 ] && HOW="$HOW terminal"
printf 'Started from (guess):%s\n' "${HOW:- unknown}"
printf 'Environment the game or SDL reads (a short allowlist; not the full environment):\n'
for v in SDL_VIDEODRIVER SDL_VIDEO_DRIVER SDL_AUDIODRIVER SDL_AUDIO_DRIVER VK_ICD_FILENAMES VK_DRIVER_FILES VK_LOADER_DRIVERS_SELECT VK_LOADER_DRIVERS_DISABLE VK_LOADER_DEBUG __NV_PRIME_RENDER_OFFLOAD __VK_LAYER_NV_optimus MESA_LOADER_DRIVER_OVERRIDE XDG_SESSION_TYPE WAYLAND_DISPLAY DISPLAY LD_LIBRARY_PATH DRI_PRIME MESA_VK_DEVICE_SELECT QT_QPA_PLATFORM DESKTOP_SESSION XDG_SESSION_DESKTOP GAMESCOPE_WAYLAND_DISPLAY SteamDeck; do
    eval "val=\${$v-__unset__}"
    [ "$val" = __unset__ ] || printf '  %s=%s\n' "$v" "$val"
done
if [ -n "${LD_PRELOAD:-}" ]; then printf '  LD_PRELOAD=(set, value hidden)\n'; fi
for v in $(env | sed -n 's/^\(MELEE_[A-Za-z0-9_]*\)=.*/\1/p'); do
    case "$v" in *TOKEN*|*KEY*|*SECRET*|*PASS*|*AUTH*) printf '  %s=(set, value hidden)\n' "$v" ;; *) eval "printf '  %s=%s\\n' \"$v\" \"\${$v}\"" ;; esac
done

h "Game binary"
printf 'Path: %s\n' "$BIN"
if [ ! -e "$BIN" ]; then
    printf 'Exists: NO\n'; V_BIN_MISSING=1
else
    printf 'Exists: yes\n'
    printf 'Size: %s bytes\n' "$(wc -c < "$BIN" | tr -d ' ')"
    printf 'Permissions: %s\n' "$(ls -ld -- "$BIN" | cut -c1-10)"
    if [ -x "$BIN" ]; then printf 'Executable by this user: yes\n'; else printf 'Executable by this user: NO\n'; V_NOT_EXEC=1; fi
    MI=$(mount_info "$BIN"); MOPTS=${MI##*|}
    if [ -n "$MI" ]; then printf 'File system: %s mounted at %s, options %s
' "${MI%%|*}" "$(printf '%s' "$MI" | cut -d'|' -f2)" "$MOPTS"; else printf 'File system: (mount table unreadable)
'; fi
    case ",$MOPTS," in *,noexec,*) V_NOEXEC_MOUNT=1; printf 'noexec: YES
' ;; *) printf 'noexec: no
' ;; esac
    BITS=$(elfbits "$BIN")
    if [ -z "$BITS" ]; then
        printf 'ELF: not an ELF file (first bytes: %s)\n' "$(bytes "$BIN" 0 8)"; V_NOT_ELF=1
    else
        MACH=$(elfmachine "$BIN")
        printf 'ELF: class %s-bit, machine %s\n' "$BITS" "$(machine_name "$MACH")"
        if have file; then printf 'file: %s\n' "$(file -b -- "$BIN" | cut -c1-200)"; fi
        { [ "$BITS" = 32 ] && [ "$MACH" = 3 ]; } || V_WRONG_ARCH="$BITS-bit machine $MACH"
        INTERP=$(interp_of "$BIN")
        printf 'Interpreter (PT_INTERP): %s\n' "${INTERP:-(none found)}"
        if [ -n "$INTERP" ]; then
            if [ -e "$INTERP" ]; then printf 'Interpreter exists: yes\n'
            else printf 'Interpreter exists: NO  (an existing binary that reports "No such file or directory" means this 32-bit loader is not installed)\n'; V_NO_LOADER=$INTERP; fi
        fi
    fi
fi
printf '32-bit loader candidates:\n'
for l in /lib/ld-linux.so.2 /lib32/ld-linux.so.2 /usr/lib32/ld-linux.so.2 /lib/i386-linux-gnu/ld-linux.so.2 /usr/lib/i386-linux-gnu/ld-linux.so.2; do
    [ -e "$l" ] && printf '  present: %s\n' "$l"
done
[ -e /lib/ld-linux.so.2 ] || printf '  (/lib/ld-linux.so.2 is absent)\n'

h "Shared libraries"
if [ -n "${BITS:-}" ] && [ -e "$BIN" ]; then
    NEEDED=$(needed_of "$BIN")
    if [ -n "$NEEDED" ]; then
        printf 'DT_NEEDED, checked against %s/lib and the 32-bit system folders (only 32-bit files count):\n' "$ROOT"
        for n in $NEEDED; do
            p=$(find32 "$n") && printf '  %s: FOUND (%s)\n' "$n" "$p" || { printf '  %s: MISSING\n' "$n"; [ -n "$V_LIB_MISSING" ] || V_LIB_MISSING=$n; }
        done
    else
        printf 'DT_NEEDED: unavailable (needs readelf or objdump); see ldd below.\n'
    fi
    if have ldd; then
        printf 'ldd (with the game'"'"'s library path), then exit status:\n'
        LD_LIBRARY_PATH="$ROOT/lib" LD_PRELOAD= timeout 10 ldd "$BIN" > "$BODY.out" 2>&1; st=$?
        sed 's/^/  /' "$BODY.out"; printf '  exit %s\n' "$st"
        L=$(sed -n 's/^[[:space:]]*\([^ ]*\) => not found.*/\1/p' "$BODY.out" | head -n 1)
        [ -z "$L" ] || { [ -n "$V_LIB_MISSING" ] || V_LIB_MISSING=$L; }
    else
        printf 'ldd: not installed\n'
    fi
else
    printf 'Not available: the game binary is missing or is not an ELF file.\n'
fi
printf 'Bundled libraries in %s/lib: ' "$ROOT"
nb=0; bad=0
for f in "$ROOT"/lib/*.so*; do
    [ -f "$f" ] || continue; nb=$((nb + 1))
    [ "$(elfbits "$f")" = 32 ] || { bad=$((bad + 1)); printf '\n  not a 32-bit ELF: %s' "$(basename -- "$f")"; }
done
printf '%s files, %s not 32-bit ELF\n' "$nb" "$bad"

h "Graphics"
for c in /sys/class/drm/card[0-9]; do
    [ -r "$c/device/vendor" ] || continue
    vid=$(cat "$c/device/vendor"); did=$(cat "$c/device/device" 2>/dev/null)
    drv=$(basename -- "$(readlink "$c/device/driver" 2>/dev/null)" 2>/dev/null)
    case "$vid" in 0x1002) vn=AMD ;; 0x8086) vn=Intel ;; 0x10de) vn=NVIDIA ;; *) vn=unknown ;; esac
    GPUVENDORS="$GPUVENDORS $vn"
    printf 'GPU %s: vendor %s (%s), device %s, kernel driver %s\n' "$(basename -- "$c")" "$vn" "$vid" "$did" "${drv:-(none)}"
done
[ -n "$GPUVENDORS" ] || printf 'GPU: none visible in /sys/class/drm\n'
have lspci && lspci -nn 2>/dev/null | grep -E 'VGA|3D controller|Display controller' | sed 's/^[^ ]* /lspci: /'
printf 'Vulkan ICD manifests:\n'
ICDDIRS="/etc/vulkan/icd.d /usr/share/vulkan/icd.d /usr/local/share/vulkan/icd.d ${XDG_DATA_HOME:-$HOME/.local/share}/vulkan/icd.d"
ICDLIST=
if [ -n "${VK_DRIVER_FILES:-${VK_ICD_FILENAMES:-}}" ]; then
    printf '  (overridden by VK_DRIVER_FILES / VK_ICD_FILENAMES)\n'
    ICDLIST=$(printf '%s' "${VK_DRIVER_FILES:-$VK_ICD_FILENAMES}" | tr ':' ' ')
else
    for d in $ICDDIRS; do for f in "$d"/*.json; do [ -f "$f" ] && ICDLIST="$ICDLIST $f"; done; done
fi
ANY32=
for f in $ICDLIST; do
    lib=$(sed -n 's/.*"library_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$f" 2>/dev/null | head -n 1)
    case "$lib" in
    "") st="no library_path" ;;
    */*) if [ "$(elfbits "$lib")" = 32 ]; then st="32-bit build FOUND ($lib)"; ANY32=1; else st="library_path $lib is not a 32-bit file"; fi ;;
    *) if p=$(find32 "$lib"); then st="32-bit build FOUND ($p)"; ANY32=1; else st="library_path $lib: 32-bit build MISSING"; fi ;;
    esac
    printf '  %s: %s\n' "$f" "$st"
done
[ -n "$ICDLIST" ] || printf '  (none found)\n'
NICD=0; for f in $ICDLIST; do NICD=$((NICD + 1)); done
if [ "$NICD" -gt 1 ]; then
    printf '  NOTE: %s Vulkan drivers are installed. The game asks the Vulkan loader for every GPU at once, so one driver that fails while enumerating can leave the game with no adapter (log: "No supported adapters"). To try one driver at a time start the game with VK_LOADER_DRIVERS_SELECT=*radeon* (or *nvidia*, *intel*; Vulkan loader 1.3.234 or newer) or VK_DRIVER_FILES=<one manifest listed above>; VK_LOADER_DEBUG=error,warn,driver shows which driver failed. MELEE_BACKEND=opengles skips Vulkan.\n' "$NICD"
fi
if p=$(find32 libvulkan.so.1); then printf '32-bit Vulkan loader libvulkan.so.1: FOUND (%s)\n' "$p"; VKLOADER=1; else printf '32-bit Vulkan loader libvulkan.so.1: MISSING\n'; VKLOADER=; fi
[ -n "$ANY32" ] && [ -n "$VKLOADER" ] || V_NO_VK32=1
if [ -x "$ROOT/bin/melee-graphics-probe" ]; then
    printf 'Launcher'"'"'s 32-bit graphics helper (creates a Vulkan device the way the game does):\n'
    LD_LIBRARY_PATH="$ROOT/lib" LD_PRELOAD= timeout 15 "$ROOT/bin/melee-graphics-probe" > "$BODY.out" 2>&1; st=$?
    head -c 4000 "$BODY.out" | sed 's/^/  /'; printf '\n  exit %s\n' "$st"
    if grep -q '"usable": *true' "$BODY.out"; then V_NO_VK32=; elif grep -q '"devices"' "$BODY.out"; then V_NO_VK32=1; fi
fi
if have vulkaninfo; then
    printf 'vulkaninfo --summary (the 64-bit loader: it does NOT prove the 32-bit driver works):\n'
    timeout 10 vulkaninfo --summary 2>&1 | grep -E '^GPU|deviceName|driverName|driverInfo|apiVersion|deviceType|driverVersion|vendorID' | sed 's/^[[:space:]]*/  /'
fi
case " $OSID " in
*" arch "*|*" cachyos "*|*" manjaro "*|*" endeavouros "*)
    g='lib32-vulkan-radeon, lib32-vulkan-intel or lib32-nvidia-utils for your GPU'
    case "$GPUVENDORS" in *AMD*) g=lib32-vulkan-radeon ;; *Intel*) g=lib32-vulkan-intel ;; *NVIDIA*) g='lib32-nvidia-utils (must match the installed NVIDIA driver)' ;; esac
    printf 'HINT: %s\n' "$(arch_hint "$g")" ;;
*" debian "*|*" ubuntu "*) printf 'HINT: Debian/Ubuntu: sudo dpkg --add-architecture i386, then install libc6:i386 libvulkan1:i386 mesa-vulkan-drivers:i386 (NVIDIA: the matching libnvidia-gl-<version>:i386). A guess from the distribution family.\n' ;;
*" fedora "*|*" rhel "*) printf 'HINT: Fedora family: install glibc.i686 vulkan-loader.i686 mesa-vulkan-drivers.i686 (NVIDIA: the matching i686 driver libraries). A guess from the distribution family.\n' ;;
*) printf 'HINT: install your distribution'"'"'s 32-bit glibc, Vulkan loader and GPU Vulkan driver. A generic guess; the distribution is not recognised.\n' ;;
esac

h "Launcher start attempt"
LAUNCHER=$ROOT/launcher/bin/gd-melee-launcher
if [ -x "$LAUNCHER" ]; then
    for platform in "" offscreen; do
        label=${platform:-default}
        printf 'Starting the launcher with --diagnose (platform: %s), stderr captured:
' "$label"
        # The launcher's own runtime library path, as ./GD-Melee sets it. "default" keeps your QT_QPA_PLATFORM.
        (
            [ -z "$platform" ] || { QT_QPA_PLATFORM=$platform; export QT_QPA_PLATFORM; }
            LD_LIBRARY_PATH="$ROOT/launcher/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"; export LD_LIBRARY_PATH
            timeout 30 "$LAUNCHER" --app-dir "$ROOT" --diagnose
        ) > "$BODY.out" 2> "$BODY.err"
        st=$?
        printf '  exit status %s
  stdout:
' "$st"; head -c 3000 "$BODY.out" | sed 's/^/    /'
        printf '  stderr:
'; head -c 3000 "$BODY.err" | sed 's/^/    /'
        if [ "$st" = 0 ]; then
            [ "$label" = default ] || V_LAUNCHER_FAIL="no window (a display or Qt platform plugin problem; it runs headless)"
            break
        fi
        V_LAUNCHER_FAIL="did not start (exit $st)"
    done
    RPT=$(sed -n 's/^Report: //p' "$BODY.out" | head -n 1)
    if [ -n "$RPT" ] && [ -r "$RPT" ]; then printf '\nThe launcher wrote its own report (%s); its first lines:\n' "$RPT"; sed -n '1,14p' "$RPT" | sed 's/^/  /'; fi
else
    printf 'launcher/bin/gd-melee-launcher is not executable or not present.\n'; V_LAUNCHER_FAIL="launcher missing"
fi
} > "$BODY" 2>&1

# ---- verdict ------------------------------------------------------------------------------------------
if [ -n "$V_BIN_MISSING" ]; then VERDICT="BINARY_MISSING"; MSG="The game program file is missing. The download may be incomplete, or this is not the game folder."
elif [ -n "$V_NOT_ELF" ]; then VERDICT="BAD_BINARY"; MSG="The game program file is not a readable Linux executable (damaged or truncated download?)."
elif [ -n "$V_WRONG_ARCH" ]; then VERDICT="WRONG_ARCHITECTURE $V_WRONG_ARCH"; MSG="The game program is not a 32-bit x86 executable, which this release requires."
elif [ -n "$V_NOT_EXEC" ]; then VERDICT="NOT_EXECUTABLE"; MSG="The game program has no execute permission for your user. Run: chmod +x \"$BIN\" (unzip can drop it; tar keeps it)."
elif [ -n "$V_NOEXEC_MOUNT" ]; then VERDICT="NOEXEC_MOUNT"; MSG="The game folder is on a file system mounted noexec, so programs there cannot run. Move the game to your home folder."
elif [ -n "$V_NO_LOADER" ]; then VERDICT="NO_32BIT_LOADER $V_NO_LOADER"; MSG="This computer has no 32-bit program loader ($V_NO_LOADER), so the 32-bit game cannot begin. Install the 32-bit glibc package (Arch family: enable multilib, then lib32-glibc)."
elif [ -n "$V_LIB_MISSING" ]; then VERDICT="MISSING_LIBRARY $V_LIB_MISSING"; MSG="The 32-bit library $V_LIB_MISSING is missing, so the game cannot load. Install your distribution's 32-bit package that provides it."
elif [ -n "$V_NO_VK32" ]; then VERDICT="NO_32BIT_VULKAN_DRIVER"; MSG="No working 32-bit Vulkan driver was found. The game needs one for your graphics card even though the launcher is 64-bit."
elif [ -n "$V_LAUNCHER_FAIL" ]; then VERDICT="LAUNCHER_FAILED $V_LAUNCHER_FAIL"; MSG="The game files look fine, but the Qt launcher itself did not start; its error is in the Launcher start attempt section."
else VERDICT="UNKNOWN"; MSG="No problem was found by the static checks (binary, loader, libraries, 32-bit Vulkan, launcher start). Start the game from the launcher and attach the launch diagnostics it writes."
fi

# ---- privacy filter and output --------------------------------------------------------------------------
ME=$(id -un 2>/dev/null); HN=$(uname -n 2>/dev/null)
FILTER=$(mktemp "${TMPDIR:-/tmp}/gd-melee-sed.XXXXXX") || exit 2
trap 'rm -f "$BODY" "$BODY.err" "$BODY.out" "$FILTER"' EXIT INT TERM
{
    [ -z "${HOME:-}" ] || [ "$HOME" = / ] || printf 's#%s#~#g\n' "$(printf '%s' "$HOME" | sed 's/[#.*^$[\]/\\&/g')"
    printf '%s\n' 's#/home/[^/[:space:]"]*#~#g' 's#/run/media/[^/[:space:]"]*#/media/<user>#g' 's#/media/[^/[:space:]"]*#/media/<user>#g'
    # disc images by file name only (the name may hold spaces)
    printf '%s\n' 's#\(^\|[[:space:]"=(]\)[^[:space:]"=]*/\([^/"]*\.\(iso\|ISO\|gcm\|GCM\|ciso\|rvz\|gcz\|wia\)\)#\1\2#g'
    # an address followed by "-" is a kernel release such as 6.6.87.2-microsoft, not an address
    printf '%s\n' 's#\b\([0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}\)\([^-0-9A-Za-z.]\|$\)#<ip>\2#g' 's#\b[0-9a-fA-F]\{2\}\(:[0-9a-fA-F]\{2\}\)\{5\}\b#<mac>#g'
    for w in "$ME" "$HN"; do
        [ "${#w}" -ge 3 ] && [ "$w" != localhost ] && printf 's#\\(^\\|[^A-Za-z0-9._-]\\)%s\\([^A-Za-z0-9._-]\\|$\\)#\\1<name>\\2#g\n' "$(printf '%s' "$w" | sed 's/[#.*^$[\]/\\&/g')"
    done
} > "$FILTER"

{
    printf "GD's Melee launch diagnostics (shell script)\n"
    printf 'Written: %s\n\n' "$(date '+%Y-%m-%dT%H:%M:%S')"
    printf 'WHAT THIS FILE CONTAINS: the game version, your Linux distribution, kernel, session type, graphics card model, the results of file and library checks on the game, the launcher'"'"'s start attempt and its error output. Your home folder is shown as ~; your user name, computer name and IP addresses are removed; disc images appear by file name only; the full environment is NOT included. Read it before sharing.\n\n'
    printf 'VERDICT: %s\n%s\n' "$VERDICT" "$MSG"
    cat "$BODY"
} | sed -f "$FILTER" > "$OUT"

printf 'VERDICT: %s\n%s\n\nReport written to: %s\nPlease attach that file when you ask for help.\n' "$VERDICT" "$MSG" "$OUT" | sed -f "$FILTER"
exit 0
