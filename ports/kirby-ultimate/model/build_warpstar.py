"""Build a standalone HSD Warp Star model for Kirby's Ultimate Entry state.

The output is game-derived and belongs under the ignored _build directory.
The native host must spawn, animate, and remove the star during the 120-frame
Entry; this tool builds only its visual model.
"""

from pathlib import Path
import argparse
import json
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
DEFAULT_SOURCE = ROOT / "experiment/tooling/ultimate/workspace/extracted/fighter/kirby/model/warpstar/c00"
DEFAULT_PYTHON = ROOT / "experiment/tooling/ultimate/apps/Blender/blender-5.1.2-windows-x64/5.1/python/bin/python.exe"
DEFAULT_CLI = ROOT / "experiment/tooling/ultimate/apps/Ultimate-Tex-CLI/ultimate_tex_cli.exe"
DEFAULT_OUT = ROOT / "_build/tmp/ultimate-kirby-warpstar"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fighter", type=Path, required=True,
                        help="PlKb.dat supplying a known-good textured HSD material template")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--ssbh-python", type=Path, default=DEFAULT_PYTHON)
    parser.add_argument("--tex-cli", type=Path, default=DEFAULT_CLI)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--texture-size", type=int, default=256)
    args = parser.parse_args()
    if not args.fighter.is_file():
        parser.error(f"fighter archive missing: {args.fighter}")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    prepare = [str(HERE / "prepare_warpstar.py"), "--source", str(args.source),
               "--tex-cli", str(args.tex_cli), "--out-dir", str(args.out_dir),
               "--texture-size", str(args.texture_size)]
    subprocess.run([str(args.ssbh_python), *prepare, "--mesh-only"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, *prepare, "--textures-only"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, str(HERE / "prepare_warpstar_anim.py"),
                    "--out-dir", str(args.out_dir)], cwd=ROOT, check=True)
    project = HERE / "warpstarbuild/warpstarbuild.csproj"
    subprocess.run(["dotnet", "build", str(project), "-c", "Release",
                    "-p:NuGetAudit=false", "--nologo"], cwd=ROOT, check=True)
    output = args.out_dir / "PlUkWarpStar.dat"
    report = args.out_dir / "warpstar-report.json"
    builder = HERE / "warpstarbuild/bin/Release/net8.0/warpstarbuild.exe"
    subprocess.run([str(builder), str(args.fighter), str(args.out_dir / "warpstar-mesh.json"),
                    str(args.out_dir), str(args.out_dir / "warpstar-poses.json"),
                    str(output), str(report)], cwd=ROOT, check=True)
    print(json.dumps({"model": str(output), "symbol": "PlyKirbyWarpStar_joint",
                      "anim_symbol": "PlyKirbyWarpStar_animjoint",
                      "report": str(report)}, indent=2))


if __name__ == "__main__":
    main()
