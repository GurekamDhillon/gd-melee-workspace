#!/bin/bash
# envoy_look_tour.sh: open ONE visible Envoy Classic run (the ws/envoy-feel build, the agent/envoy-feel mod) and, from the console, put
# every look the owner has not seen in a while on screen within about a minute. The list of what to look at is printed below at launch.
#
#   bash tools/port/envoy_look_tour.sh            (from any directory; vanilla disc from .env; main monitor; volume 3)
#
# What it does: boots the exe built in _build/agents/envoy-feel, mounts the mod FOLDERS (Windows-style paths) through MELEE_SCRIPT, starts
# `envoy classic mario`, waits for the match, then sends console commands on a timer. Nothing is written outside the run's own sandbox.
# The drive models are the local-only Sonic Adventure 2 set (never committed); without them the cells are flat and look item 1 is moot.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS="$(cd "$HERE/../.." && pwd -W)"
MAIN="$(cd "$(git -C "$WS" rev-parse --git-common-dir)/.." && pwd -W)"
export GW_ROOT="$MAIN"
LANE="${ENVOY_TOUR_LANE:-envoy-feel}"
export GW_MELEE="${GW_MELEE:-$MAIN/worktrees/$LANE}"
export GW_BUILD_ROOT="${GW_BUILD_ROOT:-$MAIN/_build/agents/$LANE}"
set -a; . "$MAIN/.env"; set +a
[ -f "$GW_BUILD_ROOT/melee-pc.exe" ] || { echo "no exe at $GW_BUILD_ROOT: run tools/port/build.sh with GW_MELEE and GW_BUILD_ROOT set first" >&2; exit 1; }

MOD="$GW_MELEE/pc/scripts/examples/envoy"
MODELS="$MAIN/_build/local-assets/envoy-play/mods/envoy_drives_sa2"
SCRIPTS="$MOD"
if [ -d "$MODELS" ]; then SCRIPTS="$MOD;$MODELS"; else echo "note: $MODELS is missing, so drive cells will be flat (no model tilt to look at)"; fi
export MELEE_SCRIPT="$SCRIPTS"
export MELEE_VOLUME="${MELEE_VOLUME:-3}"
PORT="${ENVOY_TOUR_PORT:-52317}"
export MELEE_CONSOLE_PORT="$PORT"
NAME="${ENVOY_TOUR_RUN:-envoy-look-tour-$(date +%H%M%S)}"

cat <<'EOF'

ENVOY LOOK TOUR (about a minute; the console feeds it, you play). What to look at, in order:
  1  0:00  Run-start panel: the last line now reads "Keystones are permanent for this run." Strip (top left): pip and keystone-cell SCALE.
  2  0:05  Run around: EARNED AFTERIMAGES. Blue (L-cancel Haste) 0:05-0:15, teal (shield Guarded) 0:17-0:27, gold (wave Haste) 0:29-0:39.
  3  0:42  Bottom-left card: "Bag full: the next drive replaces one." (NEW signal: told BEFORE a drive is replaced.)
  4  0:47  Bottom-left card: "No reward this stage / Next one: in 2 stages." (NEW: rewards come every third stage.)
  5  0:52  Developer overlay on: strip gets "x1.xx" (Build strength is now an index, not "+N%") and the generic "Modifier!" flash appears
           under the strip whenever one of your rules fires (hit the CPU).
  6  0:55  The reward grid opens (a preview): DRIVE MODEL TILT in the cells; the KEYSTONE FRAME (offered keystone row); focus a keystone:
           "Permanent: it stays for the whole run..." (NEW); focus a drive with a technique rule if one is offered: "...counts it lightly" (NEW);
           the detail panel's "Build strength x1.xx -> x2.xx". B closes it.
Close the window when done. The log is in the run's sandbox (printed at exit).
EOF

# the timed driver: waits for the console and for the match, then sends the schedule
python - "$PORT" <<'PY' &
import socket, sys, time
port = int(sys.argv[1])
def connect():
    for _ in range(300):
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=60)
            f = s.makefile("r", encoding="utf-8", errors="replace"); f.readline(); return s, f
        except OSError: time.sleep(2)
    sys.exit(1)
s, f = connect()
def cmd(line):
    s.sendall((line + "\n").encode()); out = []
    while True:
        r = f.readline()
        if not r: return "\n".join(out)
        r = r.rstrip("\n")
        if r in (">>> ok", ">>> error"): return "\n".join(out)
        if not r.startswith("> "): out.append(r)
def match_ready():
    try: return cmd("= gd.match().active") .strip() == "true" and cmd("= gd.player(1) and gd.player(2) and 1").strip() == "1"
    except Exception: return False
for _ in range(60):   # `envoy classic` once: "started", "deferred" (the screen is still settling; it starts by itself) or "refused" (a run is already on) all mean go on
    if any(k in cmd("envoy classic mario").lower() for k in ("started", "deferred", "refused")): break
    time.sleep(3)
t0 = time.time()
while not match_ready():
    time.sleep(1)
    if time.time() - t0 > 240: sys.exit(1)
base = time.time()
schedule = [
    (5,  ["mod status haste 1 600 lcancel"]),
    (17, ["mod status guarded 1 600 shield"]),
    (29, ["mod status haste 1 600 wave"]),
    (42, ["uxgain full"]),
    (47, ["uxnoreward 0"]),
    (52, ["envoy devui on"]),
    (55, ["uxpreview keys"]),
]
for at, cmds in schedule:
    time.sleep(max(0, base + at - time.time()))
    for c in cmds: cmd(c)
PY
HELPER=$!
trap 'kill $HELPER 2>/dev/null' EXIT

exec_name="$NAME"
bash "$MAIN/tools/port/run.sh" --realtime "$exec_name" --iso "$GW_ISO_VANILLA"
