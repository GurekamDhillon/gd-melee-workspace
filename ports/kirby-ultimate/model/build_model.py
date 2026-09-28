"""Build a local Ultimate Kirby c00 geometry costume for Melee Kirby.

No Nintendo assets are committed. The generated PlKbNr.dat goes under
_build/tmp/ultimate-kirby-model/ by default.

Example:
  python ports/kirby-ultimate/model/build_model.py --iso <ACE.iso>
"""

from pathlib import Path
import argparse
import json
import os
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
DEFAULT_SOURCE = Path(os.environ.get("GW_ULTIMATE_EXTRACT", str(Path(__file__).resolve().parents[3] / "_local" / "ultimate"))) / 'fighter/kirby/model/body/c00'
DEFAULT_PYTHON = ROOT / "experiment/tooling/ultimate/apps/Blender/blender-5.1.2-windows-x64/5.1/python/bin/python.exe"
DEFAULT_OUT = ROOT / "_build/tmp/ultimate-kirby-model"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--iso", type=Path, help="ACE ISO to read stock Kirby costume from")
    source.add_argument("--stock-costume", type=Path, help="existing ignored stock Kirby costume")
    parser.add_argument("--costume-file", default="PlKbNr.dat",
                        choices=("PlKbNr.dat", "PlKbYe.dat", "PlKbBu.dat",
                                 "PlKbRe.dat", "PlKbGr.dat", "PlKbWh.dat"),
                        help="Melee costume filename; match --ultimate-model palette")
    parser.add_argument("--output-file", help="output archive filename for a new costume slot")
    parser.add_argument("--ultimate-model", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--ssbh-python", type=Path, default=DEFAULT_PYTHON)
    parser.add_argument("--tex-cli", type=Path,
                        default=ROOT / "experiment/tooling/ultimate/apps/Ultimate-Tex-CLI/ultimate_tex_cli.exe")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--deform-face", action="store_true")
    parser.add_argument("--rigid-limbs", action="store_true",
                        help="control: bind each arm and foot to one joint")
    parser.add_argument("--preserve-world-rest", dest="preserve_world_rest", action="store_true",
                        default=True, help="preserve Ultimate world-facing geometry before Melee binding (default)")
    parser.add_argument("--mapped-bone-local", dest="preserve_world_rest", action="store_false",
                        help="diagnostic: transform mesh into mapped Melee bone local rest")
    parser.add_argument("--stock-face-patch", action="store_true",
                        help="temporary control: keep stock face patch over Ultimate body")
    parser.add_argument("--winding", choices=("mixed", "reverse", "source"), default="source",
                        help="triangle face order (default: Ultimate source)")
    parser.add_argument("--invert-normals", action="store_true",
                        help="test light-facing normals with source winding")
    parser.add_argument("--unlit", action="store_true",
                        help="render source texture directly while keeping outward normals")
    parser.add_argument("--cull", choices=("stock", "front", "back", "none"), default="back",
                        help="which polygon face to cull after conversion (default: back)")
    parser.add_argument("--eye-cull", choices=("stock", "front", "back", "none"),
                        help="override culling for Eye1 DObjs 0/3 only; default follows --cull")
    parser.add_argument("--eye-yaw-deg", type=float, default=0.0,
                        help="rotate Eye1 around the body Y axis for side-camera presentation (diagnostic)")
    args = parser.parse_args()
    output_name = args.output_file or args.costume_file
    if not re.fullmatch(r"PlKb[A-Za-z0-9]+\.dat", output_name):
        parser.error("--output-file must be a Kirby costume basename such as PlKbOr.dat")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    if args.stock_costume and args.stock_costume.name != args.costume_file:
        parser.error("--stock-costume filename must match --costume-file")
    stock = args.stock_costume or args.out_dir / ("stock-" + args.costume_file)
    if args.iso:
        sys.path.insert(0, str(ROOT / "tools/mex_port"))
        import mex_hsd
        stock.write_bytes(mex_hsd.Gcm(str(args.iso)).read(args.costume_file))
    if not stock.is_file():
        raise SystemExit(f"stock Kirby costume not found: {stock}")
    mesh = args.out_dir / "mesh.json"
    output = args.out_dir / output_name
    converter = [str(args.ssbh_python), str(HERE / "retarget_mesh.py"),
                    "--source", str(args.ultimate_model), "--stock-costume", str(stock),
                    "--out", str(mesh)]
    if args.deform_face:
        converter.append("--deform-face")
    if args.rigid_limbs:
        converter.append("--rigid-limbs")
    if args.preserve_world_rest:
        converter.append("--preserve-world-rest")
    else:
        converter.append("--mapped-bone-local")
    if args.stock_face_patch:
        converter.append("--stock-face-patch")
    subprocess.run(converter, cwd=ROOT, check=True)
    subprocess.run([sys.executable, str(HERE / "prepare_texture.py"),
                    "--source", str(args.ultimate_model), "--tex-cli", str(args.tex_cli),
                    "--out-dir", str(args.out_dir)], cwd=ROOT, check=True)
    project = HERE / "kbbuild/kbbuild.csproj"
    subprocess.run(["dotnet", "build", str(project), "-c", "Release",
                    "-p:NuGetAudit=false", "--nologo"], cwd=ROOT, check=True)
    writer = HERE / "kbbuild/bin/Release/net8.0/kbbuild.exe"
    writer_env = {**os.environ, "KB_FLIP": args.winding,
                  "KB_INVERT_NORMALS": "1" if args.invert_normals else "0",
                  "KB_UNLIT": "1" if args.unlit else "0",
                  "KB_CULL": args.cull,
                  "KB_EYE_CULL": args.eye_cull or args.cull}
    writer_env["KB_EYE_YAW_DEG"] = str(args.eye_yaw_deg)
    writer_args = [str(writer), str(stock), str(mesh), str(output),
                   str(args.out_dir / "body-atlas.bgra"), str(args.out_dir / "skin.bgra")]
    if not args.stock_face_patch:
        writer_args.append(str(args.out_dir))
    subprocess.run(writer_args,
                   cwd=ROOT, env=writer_env, check=True)

    # Independent archive reader checks root symbols and full joint/DObj walk.
    sys.path.insert(0, str(ROOT / "tools/mex_port"))
    sys.path.insert(0, str(ROOT / "experiment/Shadow/analysis/02_assets_scripts"))
    import mex_hsd
    import cos
    archive = mex_hsd.Archive(output.read_bytes()).relocate(0)
    root_symbols = [name for name, _ in archive.publics if name.endswith("_Share_joint")]
    matanim_symbols = [name for name, _ in archive.publics if name.endswith("_Share_matanim_joint")]
    if len(root_symbols) != 1 or len(matanim_symbols) != 1:
        raise SystemExit("unexpected Kirby costume public symbols")
    model = cos.Model(archive, archive.public(root_symbols[0]))
    archive.public(matanim_symbols[0])
    if len(model.joints) != 46 or len(model.dobjs) != 42:
        raise SystemExit("unexpected Kirby model structure after HSD save")
    stats = json.loads(mesh.read_text(encoding="utf-8"))["stats"]
    report = {"costume": str(output), "source_costume": args.costume_file,
              "bytes": output.stat().st_size,
              "joint_symbol": root_symbols[0], "matanim_symbol": matanim_symbols[0],
              "joints": len(model.joints), "dobjs": len(model.dobjs),
              "pobjs": len(model.pobjs), "images": len(model.images),
              "source_triangles": stats["triangles"],
              "body_binding": stats["body_binding"],
              "limb_binding": stats["limb_binding"],
              "geometry_space": stats["geometry_space"],
              "world_rest_scale": stats["world_rest_scale"],
              "stock_face_patch": stats["stock_face_patch"],
              "winding": args.winding,
              "invert_normals": args.invert_normals,
              "unlit": args.unlit,
              "cull": args.cull,
              "eye_cull": args.eye_cull or args.cull,
              "eye_yaw_deg": args.eye_yaw_deg,
              "limitations": "normal/puffed body and Eye1 mesh; four facial atlas frames use stock blink timing, but Ultimate expression mesh switching and animation remain separate"}
    (args.out_dir / "model-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
