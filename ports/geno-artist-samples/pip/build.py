"""Build Pip's art and original Palm Skip special. Run from any directory.

Outputs, including generated Blender source, stay below --out (default _build/agents/pip-author).
The artist assembler rewrites its package; always apply this sample overlay AFTER that step.
No converter or game source is modified. Existing generated Blender art is preserved.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from tools.geno.artist import pipeline


def run(*args):
    subprocess.run([str(x) for x in args], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "_build/agents/pip-author")
    args = parser.parse_args()
    out = args.out.resolve()
    # pipeline.build replaces out/build and out/mods/sample-pip. Refuse source roots.
    if out == ROOT or ROOT.is_relative_to(out) or out.is_relative_to(HERE):
        parser.error("--out must be a dedicated output folder, not the workspace or sample sources")
    source = out / "source"
    source.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((HERE / "fighter.json").read_text())
    cfg["clips"] = {"map": {"PalmSkip": ["SpecialN"]}}
    (source / "fighter.json").write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    blend = source / "pip.blend"
    if not blend.exists():
        blender = pipeline.blender_exe()
        run(blender, "-b", "--python", ROOT / "tools/geno/artist/blender/make_starter.py",
            "--", "--out", blend, "--name", "Pip", "--params", HERE / "params.json")
        run(blender, "-b", blend, "--python", HERE / "make_special.py")
    rc, _ = pipeline.build(str(source / "fighter.json"), str(out))
    if rc:
        return rc
    package = out / "mods/sample-pip"
    plan = json.loads((package / "files/plan.json").read_text())
    right_hand = plan["roles"]["hand.R"][0]
    move = (HERE / "palm_skip.genoasm").read_text().replace("@HAND_R@", str(right_hand))
    asm = package / "moves/palm_skip.genoasm"
    asm.write_text(move, encoding="utf-8")
    run(sys.executable, "-m", "tools.geno.asm", asm, "-o", asm.with_suffix(".words"), "--words")
    (package / "lua").mkdir(exist_ok=True)
    shutil.copy2(HERE / "lua/palm_skip.lua", package / "lua/palm_skip.lua")
    gameplay = json.loads((HERE / "gameplay.json").read_text())
    doc = json.loads((package / "geno.json").read_text())
    fighter = doc["fighters"][0]
    fighter["lua"] = gameplay["lua"]
    fighter["states"] = [s for s in fighter["states"] if s["name"] not in ("NCharge", "NRelease")]
    fighter["subactions"] = [s for s in fighter["subactions"] if s["index"] not in (295, 296)]
    for old_move in ("n_charge", "n_release"):
        for suffix in (".genoasm", ".words"):
            (package / "moves" / (old_move + suffix)).unlink(missing_ok=True)
    fighter["states"].append(gameplay["state"])
    fighter["subactions"].append(gameplay["subaction"])
    fighter["specials"].update(gameplay["specials"])
    (package / "geno.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    run(sys.executable, "-m", "tools.geno.check", package)
    print("Pip PalmSkip built and checked:", package)
    print("Art timing warnings use the default Striker table; PalmSkip is authored at 6/14, ends at 40.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
