"""Create a source-only native reference fighter; never read a disc."""
import argparse
import json
from pathlib import Path
import re
from . import script

JAB = """# Authored Hero jab: 12% instead of the inherited normal.
wait 2
hitbox slot=0 joint=0 damage=12 size=5 x=4 y=7 angle=361 kbg=100 bkb=30
wait 3
clear_hitboxes
wait 6
iasa
"""


SKELETON_FTILT = """# Forward tilt: edit this, run `python -m tools.geno.check <folder>` and `python -m tools.geno.report <folder> --frames`.
PUT ANIM_RATE 1.4
wait 6
hitbox slot=0 joint=55 damage=6 size=3.8 angle=38 kbg=95 bkb=25
wait 3
clear_hitboxes
wait 8
iasa
"""


def create(root, key, name, base="mario", template=None):
    if base != "mario":
        raise ValueError("slice 1 supports only the native Mario preset")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,38}", key) or ".." in key:
        raise ValueError("key must be a portable lowercase identifier, at most 39 bytes")
    if not name or len(name.encode("ascii", errors="replace")) > 47 or not name.isascii() or not name.isprintable():
        raise ValueError("name must be printable ASCII, 1..47 bytes")
    root = Path(root)
    if root.exists():
        raise ValueError("output already exists; choose a fresh folder")
    if template not in (None, "striker-skeleton"):
        raise ValueError("unknown template")
    data = {"geno": 6, "fighters": [{
        "define": {"key": key, "name": name, "base": "mario", "common": "melee.common.v1", "resources": "retail:mario"},
        "attributes": {"walk_max_vel": 1.8},
        "subactions": [{"index": 46, "file": "moves/hero-jab.words"}]}]}
    if template == "striker-skeleton":
        # a v7 header with the common attributes a move-set author tunes, one move to edit, and the eight
        # specials left unbound (the checker warns that each runs the donor's code until you bind a state)
        data = {"geno": 7, "fighters": [{
            "define": data["fighters"][0]["define"],
            "attributes": {"walk_max_vel": 1.5, "dash_initial_velocity": 2.0, "weight": 90, "landingairn_lag": 8},
            "subactions": [{"index": 55, "file": "moves/ftilt.words", "move_tag": "tilt"}]}]}
    # Melee's Mario Attack11 animation id is audited against the native state table.
    root.mkdir(parents=True)
    (root / "files").mkdir()  # prevent legacy whole-folder archive mounting
    (root / "files/.gitkeep").write_text("", encoding="utf-8")
    (root / "moves").mkdir()
    (root / "mod.json").write_text(json.dumps({"id": key, "name": name, "version": "0.1.0", "kind": "fighter"}, indent=2)+"\n", encoding="utf-8")
    (root / "geno.json").write_text(json.dumps(data, indent=2)+"\n", encoding="utf-8")
    stub = SKELETON_FTILT if template == "striker-skeleton" else JAB
    stem = "ftilt" if template == "striker-skeleton" else "hero-jab"
    (root / f"moves/{stem}.genoasm").write_text(stub, encoding="utf-8")
    words = script.assemble(stub)
    (root / f"moves/{stem}.words").write_text(" ".join(f"0x{w:08X}" for w in words)+"\n", encoding="utf-8")
    (root / "README.md").write_text("# "+name+"\n\nThe Geno engine native Mario-reference fixture. Offline only.\n"
        "Retail model, clips, effects and sounds are resolved from the user's disc. No disc data ships.\n"
        "Walk speed is 1.8; jab 1 is an authored 12% root-bone hitbox.\n"
        "All other states and scripts inherit the native Mario/common v1 preset.\n"
        "An integrator rebuild and full-stock/LAB verification are required.\n", encoding="utf-8")
    return root


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("key"); ap.add_argument("--name", default="Vanilla Hero")
    ap.add_argument("--base", default="mario"); ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--template", choices=["striker-skeleton"], help="a v7 header and one move stub to start a full move set from")
    args = ap.parse_args()
    try:
        create(args.output, args.key, args.name, args.base, args.template)
        print("Created source-only Geno definition; integrator build required.")
        return 0
    except (ValueError, OSError):
        print("Cannot create definition: unsupported preset, invalid identity or output unavailable.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
