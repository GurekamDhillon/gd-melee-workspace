#!/bin/bash
# Create and verify the original-art venv used by the menu/pipeline generators.
#
# The generators are NOT standard-library only. This script creates a clean venv,
# installs exactly what they import, and proves each one still runs. It is the
# reproducible answer to "can a fresh checkout regenerate the installed assets".
#
#   bash tools/roguelite/art_venv.sh            # create + install + verify
#   bash tools/roguelite/art_venv.sh --verify   # verify only, do not install
#
# Nothing here reads the disc or extracts retail data. Every input is original
# authored vector/procedural source or an OFL font.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
venv="${GW_ART_VENV:-$root/_build/roguelite-art-venv}"
mode="${1:-install}"

# Python wheels used by the generators. Pinned ranges, not exact pins, so a
# security update does not require editing this file; the generators are
# deterministic across the versions exercised here.
pkgs=(pillow numpy fonttools playwright)

# Host binaries. Each is invoked by name from a generator; there is no pip
# equivalent. Checked here because pip succeeding does not mean these exist.
bins=(rsvg-convert)

say() { printf '  %-46s %s\n' "$1" "$2"; }

if [ "$mode" != "--verify" ]; then
    echo "creating $venv"
    python3 -m venv "$venv"
    "$venv/bin/pip" install --quiet --upgrade pip
    "$venv/bin/pip" install --quiet "${pkgs[@]}"
    # Playwright needs its browser separately; the wheel alone cannot render.
    "$venv/bin/playwright" install chromium
fi

echo "verifying the art toolchain"
fail=0

for pkg in PIL numpy fontTools; do
    if "$venv/bin/python" -c "import $pkg" 2>/dev/null; then
        say "import $pkg" "ok"
    else
        say "import $pkg" "MISSING"
        fail=1
    fi
done

for b in "${bins[@]}"; do
    if command -v "$b" >/dev/null 2>&1; then
        say "bin $b" "ok"
    else
        say "bin $b" "MISSING (apt install librsvg2-bin)"
        fail=1
    fi
done

if "$venv/bin/python" - <<'PY' 2>/dev/null
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); b.close()
PY
then
    say "playwright chromium" "ok"
else
    say "playwright chromium" "MISSING ($venv/bin/playwright install chromium)"
    fail=1
fi

# Every generator must at least start and emit something.
echo "running each generator"
for g in effects_assets roguelite_art roguelite_expansion \
         roguelite_build_art roguelite_feedback_art roguelite_expansion_check; do
    if out="$("$venv/bin/python" "$root/menu/pipeline/$g.py" 2>&1)"; then
        say "menu/pipeline/$g.py" "ok"
    else
        say "menu/pipeline/$g.py" "FAILED: $(printf '%s' "$out" | tail -1 | cut -c1-60)"
        fail=1
    fi
done

if [ "$fail" -ne 0 ]; then
    echo
    echo "art toolchain INCOMPLETE - the installed asset set cannot be reproduced"
    exit 1
fi

echo
echo "art toolchain complete; regenerate with:"
echo "  $venv/bin/python menu/pipeline/<generator>.py"
echo "Generated outputs stay untracked. See docs/ROGUELITE-100-100-LEDGER.md M1."
