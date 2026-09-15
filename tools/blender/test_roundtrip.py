#!/usr/bin/env python3
"""Standalone round-trip test for the pure .tt format layer.

Runs OUTSIDE Blender with plain python3 and never imports bpy. It exercises the
text-format serialize/parse functions plus the coordinate mapping, proving that
Blender <-> Melee round trips are the identity.
"""

import os
import sys

# Make the add-on importable without bpy (its bpy layer is guarded by try/import).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from melee_target_test_io import (  # noqa: E402
    CHARACTER_NAMES,
    DEFAULT_PLATFORM_THICKNESS,
    MAX_TARGETS,
    blender_to_melee,
    melee_to_blender,
    normalize_character,
    parse_tt,
    resolve_ckind,
    serialize_tt,
)

_passed = 0


def check(label, cond):
    global _passed
    if not cond:
        raise AssertionError("FAIL: %s" % label)
    _passed += 1
    print("ok   %s" % label)


# --- 1. coordinate mapping is a symmetric involution --------------------------
for pt in [(0, 0, 0), (10, -20, 30), (-1.5, 2.25, -3.75), (45, 60, 0)]:
    b2m = blender_to_melee(*pt)
    m2b = melee_to_blender(*b2m)
    check("roundtrip blender->melee->blender %r" % (pt,), m2b == pt)
    check("roundtrip melee->blender->melee %r" % (pt,), blender_to_melee(*melee_to_blender(*pt)) == pt)

# Explicit axis check: Blender +X -> Melee +X, Blender +Z -> Melee +Y,
# Blender +Y -> Melee -Z.
check("blender +X maps to melee +X", blender_to_melee(1, 0, 0) == (1, 0, 0))
check("blender +Z maps to melee +Y", blender_to_melee(0, 0, 1) == (0, 1, 0))
check("blender +Y maps to melee -Z", blender_to_melee(0, 1, 0) == (0, 0, -1))
check("melee +Y maps to blender +Z", melee_to_blender(0, 1, 0) == (0, 0, 1))
check("melee +Z maps to blender -Y", melee_to_blender(0, 0, 1) == (0, -1, 0))

# --- 2. character resolution --------------------------------------------------
check("resolve name mario -> 8", resolve_ckind("mario") == 8)
check("resolve name fox -> 2", resolve_ckind("fox") == 2)
check("resolve name zelda -> 18", resolve_ckind("zelda") == 18)
check("resolve name ganondorf -> 25", resolve_ckind("ganondorf") == 25)
check("resolve int '8' -> 8", resolve_ckind("8") == 8)
check("resolve int 8 -> 8", resolve_ckind(8) == 8)
check("resolve unknown -> None", resolve_ckind("notacharacter") is None)
check("normalize 'MARIO' -> 'mario'", normalize_character("MARIO") == "mario")
check("normalize '08' -> '8'", normalize_character("08") == "8")
check("normalize '+8' -> '8'", normalize_character("+8") == "8")
check("name table has mario=8", CHARACTER_NAMES["mario"] == 8)
check("max targets is 21", MAX_TARGETS == 21)

# --- 3. serialize -> parse data round trip -----------------------------------
sample = {
    "name": "Mario 3-target sample",
    "character": "mario",
    "targets": [(0, 30, 0), (45, 60, 0), (-45, 60, 0)],
    "platforms": [(0, 0, 0, 100, 20), (-30, 50, 10, 40, 40)],
}
text = serialize_tt(sample)
reparsed = parse_tt(text)

check("serialized text ends with single LF", text.endswith("\n") and not text.endswith("\n\n"))
check("serialized text has no CRLF", "\r" not in text)
check("roundtrip name", reparsed["name"] == "Mario 3-target sample")
check("roundtrip character", reparsed["character"] == "mario")
check("roundtrip targets", reparsed["targets"] == sample["targets"])
check("roundtrip platforms", reparsed["platforms"] == sample["platforms"])
check("full level dict equality", reparsed == sample)

# --- 4. parse comments / blanks / unknown keys -------------------------------
tt = (
    "# a comment line\n"
    "\n"
    "name    Test Level\n"
    "character fox\n"
    "\n"
    "target 1.5 2.5 3.5\n"
    "target -1 0 0.25\n"
    "platform 0 10 0 50 30\n"
    "basestage mario_test\n"  # accepted-and-ignored key
    "unknownkey whatever\n"
)
parsed = parse_tt(tt)
check("comments/blank lines ignored", parsed["name"] == "Test Level")
check("character parsed as canonical name", parsed["character"] == "fox")
check("target floats parsed", parsed["targets"] == [(1.5, 2.5, 3.5), (-1.0, 0.0, 0.25)])
check("platform parsed", parsed["platforms"] == [(0.0, 10.0, 0.0, 50.0, 30.0)])
check("unknown keys dropped", set(parsed.keys()) == {"name", "character", "targets", "platforms"})

# --- 5. parse(serialize(parse(x))) is a stable fixpoint -----------------------
p1 = parse_tt(tt)
p2 = parse_tt(serialize_tt(p1))
check("parse/serialize fixpoint stable", p2 == p1)

# --- 6. integer-character form round trips ------------------------------------
int_sample = {"name": "int char", "character": "8", "targets": [(1, 2, 3)], "platforms": []}
check("int character roundtrip", parse_tt(serialize_tt(int_sample)) == int_sample)

# --- 7. platform top-surface convention self-consistency ----------------------
# A cube centered at blender (0, 1, 2) with extents (w=4, depth=6, height=8):
# top surface melee_y = blender_z + height/2 = 2 + 4 = 6.
b_center = (0.0, 1.0, 2.0)
dims = (4.0, 6.0, 8.0)
mx, my, mz = blender_to_melee(*b_center)
cx, cy, cz = mx, my + dims[2] / 2.0, mz
check("platform top-surface cy", cy == 6.0)
t = DEFAULT_PLATFORM_THICKNESS
bx, by, bz = melee_to_blender(cx, cy, cz)
imported_center_z = bz - t / 2.0
check("platform import center z = cy - t/2", imported_center_z == cy - t / 2.0)
# Re-export of the imported cube yields the original cy back:
check(
    "platform re-export recovers cy",
    imported_center_z + t / 2.0 == cy,
)

print("\nAll %d checks passed." % _passed)
