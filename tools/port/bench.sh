#!/bin/bash
# Benchmark one scene and judge it: tools/port/bench.sh <retail2|ported1|ported2|"scene token"> [options]
# See tools/port/bench.py (or --help) and tools/port/README.md ("Reading the perf verdict").
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
. ./portlib.sh
export GW_ISO_VANILLA GW_BUILD_ROOT GW_ROOT
exec python "$GW_ROOT/tools/port/bench.py" "$@"
