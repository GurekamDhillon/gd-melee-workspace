"""Decode Ultimate Kirby's c00 open-eye body atlas for the HSD writer."""

from pathlib import Path
import argparse
import json
import subprocess

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE = Path(r"E:\Ultimate files\workspace\extracted\fighter\kirby\model\body\c00")
DEFAULT_CLI = ROOT / "experiment/tooling/ultimate/apps/Ultimate-Tex-CLI/ultimate_tex_cli.exe"
DEFAULT_OUT = ROOT / "_build/tmp/ultimate-kirby-model"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--tex-cli", type=Path, default=DEFAULT_CLI)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--size", type=int, default=128)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    source = args.source / "melee_eye_kirby_w_col.nutexb"
    png = args.out_dir / "body-atlas-source.png"
    subprocess.run([str(args.tex_cli), str(source), str(png)], check=True)
    with Image.open(png) as source_image:
        body = source_image.convert("RGBA").resize((args.size, args.size), Image.Resampling.LANCZOS)
    body.save(args.out_dir / "body-atlas.png")
    # HSDRaw's GXImageConverter accepts BGRA byte order even though its
    # EncodeImage parameter is named rgba. Its RGB5A3 path reads red from
    # byte 2 and blue from byte 0.
    (args.out_dir / "body-atlas.bgra").write_bytes(body.tobytes("raw", "BGRA"))
    # Melee's costume matanim expects four eye images: open, half, closed,
    # hurt. Keep Ultimate's matching cXX atlas for each frame.
    (args.out_dir / "face-w.bgra").write_bytes(body.tobytes("raw", "BGRA"))
    for variant in ("d", "c", "f"):
        variant_source = args.source / f"melee_eye_kirby_{variant}_col.nutexb"
        variant_png = args.out_dir / f"face-{variant}-source.png"
        subprocess.run([str(args.tex_cli), str(variant_source), str(variant_png)], check=True)
        with Image.open(variant_png) as source_image:
            face = source_image.convert("RGBA").resize((args.size, args.size), Image.Resampling.LANCZOS)
        (args.out_dir / f"face-{variant}.bgra").write_bytes(face.tobytes("raw", "BGRA"))
    skin_source = args.source / "skin_kirby_001_col.nutexb"
    skin_png = args.out_dir / "skin-source.png"
    subprocess.run([str(args.tex_cli), str(skin_source), str(skin_png)], check=True)
    with Image.open(skin_png) as source_image:
        skin = source_image.convert("RGBA")
    if skin.size != (16, 16):
        raise ValueError(f"unexpected Kirby skin texture size: {skin.size}")
    (args.out_dir / "skin.bgra").write_bytes(skin.tobytes("raw", "BGRA"))
    (args.out_dir / "body-atlas.json").write_text(json.dumps({
        "source": str(source), "size": [args.size, args.size],
        "source_format": "RGBA8", "encoder_input_format": "BGRA8",
        "target_format": "RGB5A3",
    }, indent=2), encoding="utf-8")
    print("prepared Ultimate Kirby body and skin textures from", args.source)


if __name__ == "__main__":
    main()
