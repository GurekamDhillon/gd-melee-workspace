#!/bin/bash
# Regenerate the whole Vanilla Original asset set (model, rig, 179 clips, glb, manifest, validation).
#   ports/vanilla-original/build_all.sh [--renders]
# Needs Blender 5.x (headless only) and Python 3 with numpy (+ Pillow for --renders sheets).
# BLENDER=/path/to/blender.exe overrides the default. Every Blender process is logged by Windows PID to
# out/blender_pids.txt; stop one only by that number.
set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BLENDER="${BLENDER:-/d/SteamLibrary/steamapps/common/Blender/blender.exe}"
OUT="$HERE/out"; mkdir -p "$OUT"
W() { cygpath -m "$1" 2>/dev/null || echo "$1"; }   # native Windows path for Blender
bl() {  # bl <script.py> [blend] -- runs one headless Blender job, logs its PID, waits
  local script="$1"; local blend="${2:-}"; shift; shift || true
  local args=(--background)
  [ -n "$blend" ] && args+=("$(W "$blend")")
  args+=(--python "$(W "$HERE/src/$script")" -- "$@")
  "$BLENDER" "${args[@]}" > "$OUT/log_$script.txt" 2>&1 &
  local pid=$!
  echo "$(cat /proc/$pid/winpid 2>/dev/null || echo $pid) $script $(date +%FT%T)" >> "$OUT/blender_pids.txt"
  wait $pid
  grep -E "^(STAGE|EXPORTED|VALIDATE|REIMPORT|RENDERED|FAIL|Traceback)" "$OUT/log_$script.txt" || true
}
bl build_model.py ""
bl build_clips.py "$OUT/stage1_model.blend"
bl validate_blend.py "$OUT/stage2_anim.blend"
bl export.py "$OUT/stage2_anim.blend"
bl reimport_check.py ""
python "$(W "$HERE/src/make_manifest.py")"
python "$(W "$HERE/src/validate.py")"
if [ "$1" = "--renders" ]; then
  R="${2:-roundX}"
  bl render_static.py "$OUT/stage1_model.blend" "$R"
  bl render_clips.py "$OUT/stage1_model.blend" "$R" moves
  for k in weights hurt size silsheet smallsheet; do bl render_extra.py "$OUT/stage1_model.blend" "$R" $k; done
fi
