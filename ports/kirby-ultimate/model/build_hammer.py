"""Convert Ultimate Kirby's hammer into the Melee hammer article in PlKb.dat.

Pass an existing fighter archive, preferably the built movement/side-B mod, so
its action data remains in the output. Generated files stay under _build/tmp.
"""

from pathlib import Path
import argparse
import json
import os
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
DEFAULT_SOURCE = Path(os.environ.get("GW_ULTIMATE_EXTRACT", str(Path(__file__).resolve().parents[3] / "_local" / "ultimate"))) / 'fighter/kirby/model/hammer/c00'
DEFAULT_PYTHON = ROOT / "experiment/tooling/ultimate/apps/Blender/blender-5.1.2-windows-x64/5.1/python/bin/python.exe"
DEFAULT_CLI = ROOT / "experiment/tooling/ultimate/apps/Ultimate-Tex-CLI/ultimate_tex_cli.exe"
DEFAULT_OUT = ROOT / "_build/tmp/ultimate-kirby-hammer"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fighter", type=Path, required=True, help="existing Melee PlKb.dat")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--ssbh-python", type=Path, default=DEFAULT_PYTHON)
    parser.add_argument("--tex-cli", type=Path, default=DEFAULT_CLI)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--texture-size", type=int, default=256)
    parser.add_argument("--wood-only", action="store_true",
                        help="omit the metallic overlay mesh for a rendering control")
    parser.add_argument("--motion-rows", type=int, default=479,
                        help="number of existing fighter AJ rows to compare after article conversion")
    args = parser.parse_args()
    if not args.fighter.is_file():
        parser.error(f"fighter archive missing: {args.fighter}")
    if not 16 <= args.texture_size <= 1024 or args.texture_size % 4:
        parser.error("texture size must be a multiple of 4 from 16 to 1024")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    prepare = [str(HERE / "prepare_hammer.py"), "--source", str(args.source),
               "--tex-cli", str(args.tex_cli), "--out-dir", str(args.out_dir),
               "--texture-size", str(args.texture_size)]
    subprocess.run([str(args.ssbh_python), *prepare, "--mesh-only"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, *prepare, "--textures-only"], cwd=ROOT, check=True)
    project = HERE / "hammerbuild/hammerbuild.csproj"
    subprocess.run(["dotnet", "build", str(project), "-c", "Release",
                    "-p:NuGetAudit=false", "--nologo"], cwd=ROOT, check=True)
    output = args.out_dir / "PlKb.dat"
    if output.resolve() == args.fighter.resolve():
        parser.error("output would overwrite input fighter archive")
    report = args.out_dir / "hammer-report.json"
    builder = HERE / "hammerbuild/bin/Release/net8.0/hammerbuild.exe"
    build_env = {**os.environ, "KB_HAMMER_WOOD_ONLY": "1" if args.wood_only else "0"}
    subprocess.run([str(builder), str(args.fighter), str(report),
                    str(args.out_dir / "hammer-mesh.json"), str(args.out_dir), str(output)],
                   cwd=ROOT, env=build_env, check=True)
    verifier = HERE / "verify_hammer.py"
    subprocess.run([sys.executable, str(verifier), str(output),
                    "--baseline", str(args.fighter),
                    "--min-pobjs", "1" if args.wood_only else "2",
                    "--motion-rows", str(args.motion_rows)], cwd=ROOT, check=True)
    print(json.dumps({"fighter": str(output), "report": str(report)}, indent=2))


if __name__ == "__main__":
    main()
