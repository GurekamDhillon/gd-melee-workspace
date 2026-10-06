#!/usr/bin/env bash
# build_courier.sh - build the Courier's engine assets from the authored art. ONE command, no disc, no network.
#
#   tools/geno/build_courier.sh [--art-rebuild] [--out DIR] [--scale S] [--install]
#
# Needs: Python 3 with numpy, scipy and Pillow; the .NET 8 SDK (fighterbuild, which needs the HSDLib checkout at
# experiment/tooling/HSDLib, https://github.com/Ploaj/HSDLib). Blender is needed ONLY to regenerate ports/vanilla-original/out/
# (--art-rebuild runs ports/vanilla-original/build_all.sh, headless). A player needs none of this: the compiled outputs
# (four model files, one animation bank, plan.json) are original data and may be zipped into a mod archive.
#
# Outputs (default _build/geno-slice4/courier/, a build product; never committed):
#   GnCourier_<costume>.dat   the model + skeleton, four costumes (palette POBJ path: one piece)
#   GnCourierAJ.dat           the animation bank (179 clips; clip symbols PlyCourier_Share_ACTION_<Clip>_figatree)
#   plan.json                 joint plan, Melee parts table, role -> joint, hurtboxes + ECB in joint-local space
#   bank.json, rep_<costume>.json   what was built (frame counts, sizes, encoding error)
# --install also copies the .dat files into melee/pc/geno/mods/vanilla-courier/files/ (git-ignored there).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && { pwd -W 2>/dev/null || pwd; })"
ART="$ROOT/ports/vanilla-original"
OUT="$ROOT/_build/geno-slice4/courier"; SCALE=1.0; REBUILD=0; INSTALL=0
while [ $# -gt 0 ]; do case "$1" in
  --art-rebuild) REBUILD=1;; --out) OUT="$2"; shift;; --scale) SCALE="$2"; shift;; --install) INSTALL=1;;
  *) echo "unknown option $1" >&2; exit 2;; esac; shift; done
if [ $REBUILD = 1 ] || [ ! -f "$ART/out/courier.glb" ]; then bash "$ART/build_all.sh"; fi
FB="$ROOT/ports/ir/tools/fighterbuild"
(cd "$FB" && dotnet build -c Release -nologo -v q 2>&1 | grep -E "error|rror(s)" || true)
mkdir -p "$OUT"
python "$ROOT/ports/ir/tools/authored_fighter.py" mesh "$ART" "$OUT" --scale "$SCALE"
python "$ROOT/ports/ir/tools/authored_fighter.py" anim "$ART" "$OUT" --scale "$SCALE"
for m in "$OUT"/mesh_*.json; do
  c="$(basename "$m" .json)"; c="${c#mesh_}"
  dotnet "$FB/bin/Release/net8.0/fighterbuild.dll" build "$m" - "$OUT/GnCourier_$c.dat" courier_joint courier_matanim "$OUT/rep_$c.json" --pc-palette 64
  dotnet "$FB/bin/Release/net8.0/fighterbuild.dll" verify "$OUT/GnCourier_$c.dat" "$m" | tail -2
done
# the build record: what this run produced, by hash. tools/release/build_release.ps1 -IncludeCourier packages a
# built file only if it still matches this record (it is how a release tells the Courier's original files from
# disc files: the record is written here, from these outputs, and nowhere else).
python - "$OUT" "$ROOT" <<'PY'
import hashlib, json, subprocess, sys
from pathlib import Path
out, root = Path(sys.argv[1]), sys.argv[2]
def git(*a):
    return subprocess.run(["git", "-C", root, *a], capture_output=True, text=True).stdout.strip()
files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
         for p in sorted(list(out.glob("GnCourier_*.dat")) + [out / "GnCourierAJ.dat", out / "plan.json"])}
rec = {"format": 1, "built_by": "tools/geno/build_courier.sh",
       "art_commit": git("log", "-1", "--format=%H", "--", "ports/vanilla-original"),
       "art_dirty": bool(git("status", "--porcelain", "--", "ports/vanilla-original")), "files": files}
(out / "original-assets.json").write_text(json.dumps(rec, indent=2) + "
")
PY
if [ $INSTALL = 1 ]; then
  D="${GW_MELEE:-$ROOT/melee}/pc/geno/mods/vanilla-courier/files"; mkdir -p "$D"; cp "$OUT"/GnCourier_*.dat "$OUT"/GnCourierAJ.dat "$OUT"/plan.json "$D"/
fi
echo "OK $OUT"
