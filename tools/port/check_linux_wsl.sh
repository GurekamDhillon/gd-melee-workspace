#!/bin/bash
set -euo pipefail
config="${XDG_CONFIG_HOME:-$HOME/.config}/melee-linux/build.env"
[ -f "$config" ] || { echo "Configure local disc/UI paths in $config; see docs/LINUX_CONTINUOUS_CHECKS.md" >&2; exit 1; }
set -a
source "$config"
set +a
export GW_MELEE="${1:?game checkout required}"
exec bash "$(dirname "$0")/ci_linux.sh"
