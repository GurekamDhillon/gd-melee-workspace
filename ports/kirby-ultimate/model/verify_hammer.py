"""Independently inspect Kirby's hammer article in an HSD fighter archive."""

from pathlib import Path
import argparse
import json
import struct
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/mex_port"))
sys.path.insert(0, str(ROOT / "experiment/Shadow/analysis/02_assets_scripts"))
import mex_hsd  # noqa: E402
import cos  # noqa: E402
sys.path.insert(0, str(ROOT / "ports/kirby-ultimate/tools"))
import build_side_b  # noqa: E402


def inspect(path, baseline=None, min_pobjs=2, motion_rows=479):
    archive = mex_hsd.Archive(path.read_bytes()).relocate(0)
    fighter = archive.public("ftDataKirby")
    article_list = archive.u32(fighter + 0x48)
    hammer_article = archive.u32(article_list + 4)
    hammer_model = archive.u32(hammer_article + 0x10)
    hammer_joint = archive.u32(hammer_model)
    model = cos.Model(archive, hammer_joint)
    result = {"path": str(path), "bytes": path.stat().st_size,
              "joints": len(model.joints), "dobjs": len(model.dobjs),
              "pobjs": len(model.pobjs), "images": len(model.images)}
    if result["joints"] != 2 or result["dobjs"] != 3 or result["pobjs"] < min_pobjs:
        raise ValueError(f"unexpected hammer structure: {result}")
    if baseline is not None:
        old = mex_hsd.Archive(baseline.read_bytes()).relocate(0)
        new_table = archive.u32(fighter + 0xC)
        old_table = old.u32(old.public("ftDataKirby") + 0xC)
        for row in range(motion_rows):
            offset = row * 0x18 + 4
            original = struct.unpack_from(">II", old.data, old_table + offset)
            converted = struct.unpack_from(">II", archive.data, new_table + offset)
            if original != converted:
                raise ValueError(f"motion row {row} AJ offset/size changed")
        for row in (322, 323):
            if build_side_b.linear_words(old, row) != build_side_b.linear_words(archive, row):
                raise ValueError(f"side-B ftcmd row {row} changed")
        result["motion_rows_preserved"] = motion_rows
        result["side_b_ftcmd_rows_preserved"] = [322, 323]
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--min-pobjs", type=int, default=2)
    parser.add_argument("--motion-rows", type=int, default=479,
                        help="number of fighter AJ rows to compare with the input archive")
    args = parser.parse_args()
    print(json.dumps(inspect(args.archive, args.baseline, args.min_pobjs,
                             args.motion_rows), indent=2))
