#!/bin/sh
# Shell test for gd-melee-diagnose.sh: builds tiny fake game folders and checks the verdict line,
# the privacy filter and the mount parsing. POSIX sh; run on Linux:  sh tools/release/linux/test_diagnose.sh
# (ELF headers are written with printf, so no compiler is needed; the checks read only the header.)
set -u
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
SCRIPT=$HERE/gd-melee-diagnose.sh
T=$(mktemp -d "${TMPDIR:-/tmp}/gd-diag-test.XXXXXX") || exit 2
trap 'rm -rf "$T"' EXIT INT TERM
FAILS=0
ok() { printf 'ok   %s\n' "$1"; }
bad() { printf 'FAIL %s\n' "$1"; FAILS=$((FAILS + 1)); }

# an ELF header (class 1 or 2, e_machine 3 or 62) followed by padding and an optional interpreter string
elf() { # file class machine interp
    cls=$(printf '%03o' "$2"); mach=$(printf '%03o' "$3")
    printf "\\177ELF\\${cls}\\001\\001\\000\\000\\000\\000\\000\\000\\000\\000\\000\\002\\000\\${mach}\\000" > "$1"
    head -c 80 /dev/zero >> "$1"
    [ -z "${4:-}" ] || printf '%s\0' "$4" >> "$1"
    chmod +x "$1"
}
game() { rm -rf "$T/g"; mkdir -p "$T/g/bin" "$T/g/lib"; }
verdict() { # extra env is passed by the caller; prints the VERDICT line
    HOME=$T/home sh "$SCRIPT" -o "$T/out.txt" "$T/g" 2>&1 | sed -n 's/^VERDICT: //p' | head -n 1
}
expect() { # description expected-prefix
    got=$(verdict)
    case "$got" in "$2"*) ok "$1: $got" ;; *) bad "$1: expected $2, got '$got'" ;; esac
}
mkdir -p "$T/home"

game; expect "missing binary" BINARY_MISSING
game; printf '#!/bin/sh\n' > "$T/g/bin/melee"; chmod +x "$T/g/bin/melee"; expect "not an ELF file" BAD_BINARY
game; elf "$T/g/bin/melee" 2 62 /lib64/ld-linux-x86-64.so.2; expect "64-bit binary" WRONG_ARCHITECTURE
game; elf "$T/g/bin/melee" 1 3 /lib/ld-linux.so.2; chmod -x "$T/g/bin/melee"
if [ "$(id -u)" = 0 ]; then ok "not executable (skipped: root can execute anything)"; else expect "no execute bit" NOT_EXECUTABLE; fi
game; elf "$T/g/bin/melee" 1 3 /lib/ld-gdmelee-absent.so.2; expect "loader absent" "NO_32BIT_LOADER /lib/ld-gdmelee-absent.so.2"

# noexec mount: a fake mountinfo that mounts the temp folder noexec
game; elf "$T/g/bin/melee" 1 3 /lib/ld-linux.so.2
printf '1 0 8:1 / / rw - ext4 /dev/x rw\n2 1 8:2 / %s rw,nosuid,noexec,relatime - ext4 /dev/y rw\n' "$(cd "$T" && pwd -P)" > "$T/mountinfo"
got=$(GD_DIAG_MOUNTINFO=$T/mountinfo verdict)
case "$got" in NOEXEC_MOUNT*) ok "noexec mount: $got" ;; *) bad "noexec mount: got '$got'" ;; esac

# privacy: the home folder, user name, a disc path in a MELEE_ variable, and a secret-looking variable
game; elf "$T/g/bin/melee" 1 3 /lib/ld-gdmelee-absent.so.2
MELEE_ISO="$T/home/Games/My Melee.iso" MELEE_API_TOKEN=hunter2hunter2 HOME=$T/home sh "$SCRIPT" -o "$T/priv.txt" "$T/g" >/dev/null 2>&1
if grep -q 'hunter2' "$T/priv.txt"; then bad "a secret-looking variable leaked"; else ok "secret-looking variable hidden"; fi
if grep -q "$T/home" "$T/priv.txt"; then bad "home folder leaked"; else ok "home folder shortened"; fi
if grep -q 'MELEE_ISO=.*Games' "$T/priv.txt"; then bad "disc folder leaked"; else ok "disc path reduced to a file name"; fi
grep -q 'WHAT THIS FILE CONTAINS' "$T/priv.txt" && ok "privacy statement present" || bad "privacy statement missing"
grep -q '^MELEE_API_TOKEN\|MELEE_API_TOKEN=(set, value hidden)' "$T/priv.txt" && ok "token shown as set only" || bad "token presence not reported"

# the same file must also run under dash when it is installed
if command -v dash >/dev/null 2>&1; then
    game; elf "$T/g/bin/melee" 1 3 /lib/ld-gdmelee-absent.so.2
    got=$(HOME=$T/home dash "$SCRIPT" -o "$T/dash.txt" "$T/g" 2>&1 | sed -n 's/^VERDICT: //p' | head -n 1)
    case "$got" in NO_32BIT_LOADER*) ok "dash: $got" ;; *) bad "dash: got '$got'" ;; esac
fi
[ "$FAILS" -eq 0 ] && { echo "all shell tests passed"; exit 0; }
echo "$FAILS shell test(s) failed"; exit 1
