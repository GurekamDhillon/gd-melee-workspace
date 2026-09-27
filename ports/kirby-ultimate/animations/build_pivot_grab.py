"""Build the new native-slot CatchTurn row from Ultimate Kirby's c00 motion.

The archive is disc-derived and is written only beneath an ignored build path.
Melee Catch supplies the host root curve because the new action has no stock row.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile

import convert as local
import convert_world


ROW = 479
SYMBOL = "PlyKirby5K_Share_ACTION_CatchTurn_figatree"
SOURCE = Path("experiment/tooling/ultimate/workspace/extracted/fighter/kirby/motion/body/c00/e00catchturn.nuanmb")
SKELETON = Path("experiment/tooling/ultimate/workspace/extracted/fighter/kirby/model/body/c00/model.nusktb")


def build(root: Path, output: Path) -> dict:
    source = root / SOURCE
    decoder = root / "experiment/tooling/ultimate/apps/SSBH-JSON/ssbh_data_json.exe"
    joints = json.loads((root / "experiment/brawl-kirby/analysis/melee_model.json").read_text())[
        "PlKbNr.dat"]["joints"]
    _, archives = local.melee_anim.melee_aj()
    stock_catch = archives["PlyKirby5K_Share_ACTION_Catch_figatree"][2]
    with tempfile.TemporaryDirectory(prefix="ultimate-kirby-catchturn-") as name:
        tmp = Path(name)
        anim = local.decode(decoder, source, tmp / "anim.json")
        skeleton = local.decode(decoder, root / SKELETON, tmp / "skeleton.json")
    raw, report = convert_world.convert_clip(
        anim, skeleton, joints, SYMBOL, ROW, stock_catch,
        bind_policy="source-world-scaled",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(raw)
    result = {
        "row": ROW,
        "file": output.name,
        "symbol": SYMBOL,
        "source": SOURCE.as_posix(),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        **report,
    }
    (output.parent / "install-manifest.json").write_text(
        json.dumps({"animations": [result]}, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=local.ROOT)
    parser.add_argument("--out", type=Path,
                        default=local.ROOT / "_build/tmp/ultimate-kirby-catchturn/479-CatchTurn.dat")
    args = parser.parse_args()
    result = build(args.root, args.out)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
