"""Convert five Ultimate Kirby Stone shapes into Melee costume Stone slots.

Kirby's existing costume has five Stone visibility states; Ultimate has six.
This preserves the stock five states and prepares the sixth Hammer source mesh
for a separate game-side visibility-table extension. No fighter PlKb.dat data is
changed by this converter.
"""

from pathlib import Path
import argparse
import json
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
DEFAULT_SOURCE = Path(r"E:\Ultimate files\workspace\extracted\fighter\kirby\model\stone\c00")
DEFAULT_PYTHON = ROOT / "experiment/tooling/ultimate/apps/Blender/blender-5.1.2-windows-x64/5.1/python/bin/python.exe"
DEFAULT_CLI = ROOT / "experiment/tooling/ultimate/apps/Ultimate-Tex-CLI/ultimate_tex_cli.exe"
DEFAULT_OUT = ROOT / "_build/tmp/ultimate-kirby-stone"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--costume", type=Path, required=True,
                        help="converted Kirby costume archive to extend")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--ssbh-python", type=Path, default=DEFAULT_PYTHON)
    parser.add_argument("--tex-cli", type=Path, default=DEFAULT_CLI)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--texture-size", type=int, default=256)
    parser.add_argument("--camera-yaw-deg", type=float, default=0.0,
                        help="rotate Stone models about Y for Melee side-camera presentation")
    parser.add_argument("--shape-yaws", default="",
                        help="comma-separated Stone shape Y rotation overrides")
    parser.add_argument("--append-sixth", action="store_true",
                        help="append the Ultimate Hammer statue as DObjs42/43; requires game-side visibility state7")
    args = parser.parse_args()
    if not args.costume.is_file():
        parser.error(f"costume archive missing: {args.costume}")
    if not 16 <= args.texture_size <= 1024 or args.texture_size % 4:
        parser.error("texture size must be a multiple of 4 from 16 to 1024")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    output = args.out_dir / args.costume.name
    if output.resolve() == args.costume.resolve():
        parser.error("output would overwrite input costume")
    prepare = [str(HERE / "prepare_stone.py"), "--source", str(args.source),
               "--tex-cli", str(args.tex_cli), "--out-dir", str(args.out_dir),
               "--texture-size", str(args.texture_size),
               "--camera-yaw-deg", str(args.camera_yaw_deg)]
    if args.shape_yaws:
        prepare.extend(["--shape-yaws", args.shape_yaws])
    subprocess.run([str(args.ssbh_python), *prepare, "--mesh-only"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, *prepare, "--textures-only"], cwd=ROOT, check=True)
    project = HERE / "stonebuild/stonebuild.csproj"
    subprocess.run(["dotnet", "build", str(project), "-c", "Release",
                    "-p:NuGetAudit=false", "--nologo"], cwd=ROOT, check=True)
    builder = HERE / "stonebuild/bin/Release/net8.0/stonebuild.exe"
    report = args.out_dir / "stone-report.json"
    build = [str(builder), str(args.costume),
                    str(args.out_dir / "stone-mesh.json"), str(args.out_dir),
                    str(output), str(report)]
    if args.append_sixth:
        build.append("--append-sixth")
    subprocess.run(build, cwd=ROOT, check=True)
    print(json.dumps({"costume": str(output), "report": str(report)}, indent=2))


if __name__ == "__main__":
    main()
