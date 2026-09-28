"""Prepare Ultimate Kirby Stone shapes for the Melee costume converter.

The extracted game files are read locally; the mesh and texture output belongs
under the ignored build directory and must never be committed.
"""

import os
from pathlib import Path
import argparse
import json
import math
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
DEPENDENCIES = ROOT / "experiment/tooling/ultimate/profile/blender/scripts/addons/smash-ultimate-blender/dependencies"
DEFAULT_SOURCE = Path(os.environ.get("GW_ULTIMATE_EXTRACT", str(Path(__file__).resolve().parents[3] / "_local" / "ultimate"))) / 'fighter/kirby/model/stone/c00'
DEFAULT_CLI = ROOT / "experiment/tooling/ultimate/apps/Ultimate-Tex-CLI/ultimate_tex_cli.exe"
DEFAULT_OUT = ROOT / "_build/tmp/ultimate-kirby-stone"
SCALE = 5.0 / 4.6
SHAPES = {
    "100t": ("BodyStone100t_VIS_O_OBJShape", "def_PlyKirby5KStn100tB_001_col"),
    "tbox": ("BodyStoneTBoxM_VIS_O_OBJShape", "def_tbox_a_001_col"),
    "dosun": ("BodyStoneDosunM_VIS_O_OBJShape", "def_dossun_all_001_col"),
    "kirby": ("BodyStoneKirbyM_VIS_O_OBJShape", "def_kirbystone_i_001_col"),
    "ppon": ("BodyStonePPonM_VIS_O_OBJShape", "def_PlyKirby5KStnPPon_001_col"),
    "hammer": ("BodyStoneHammerM_VIS_O_OBJShape", "def_PlyKirby5KStnHmmr_001_col"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--tex-cli", type=Path, default=DEFAULT_CLI)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--texture-size", type=int, default=256)
    parser.add_argument("--camera-yaw-deg", type=float, default=0.0,
                        help="rotate all Stone shapes about their Attach Y axis toward Melee's side camera")
    parser.add_argument("--shape-yaws", default="",
                        help="comma-separated per-shape overrides, e.g. dosun=-90,ppon=180")
    parser.add_argument("--mesh-only", action="store_true")
    parser.add_argument("--textures-only", action="store_true")
    args = parser.parse_args()
    shape_yaws = {}
    for entry in filter(None, args.shape_yaws.split(",")):
        name, sep, value = entry.partition("=")
        if not sep or name not in SHAPES or name in shape_yaws:
            parser.error(f"invalid or duplicate Stone shape yaw: {entry}")
        shape_yaws[name] = float(value)
    if args.mesh_only and args.textures_only:
        parser.error("select one preparation mode")
    if not 16 <= args.texture_size <= 1024 or args.texture_size % 4:
        parser.error("texture size must be a multiple of 4 from 16 to 1024")
    args.out_dir.mkdir(parents=True, exist_ok=True)

    if not args.textures_only:
        sys.path.insert(0, str(DEPENDENCIES))
        import ssbh_data_py as ssbh  # noqa: E402

        mesh = ssbh.mesh_data.read_mesh(str(args.source / "model.numshb"))
        modl = ssbh.modl_data.read_modl(str(args.source / "model.numdlb"))
        matl = ssbh.matl_data.read_matl(str(args.source / "model.numatb"))
        labels = {(e.mesh_object_name, e.mesh_object_subindex): e.material_label
                  for e in modl.entries}
        material_textures = {
            e.material_label: next((t.data for t in e.textures if t.param_id.name == "Texture0"), None)
            for e in matl.entries
        }
        pieces = {name: [] for name in SHAPES}
        def rotate_y(v, name):
            yaw = math.radians(shape_yaws.get(name, args.camera_yaw_deg))
            cos_yaw, sin_yaw = math.cos(yaw), math.sin(yaw)
            x, y, z = v
            return [cos_yaw * x + sin_yaw * z, y,
                    -sin_yaw * x + cos_yaw * z]

        for obj in mesh.objects:
            matches = [name for name, (mesh_name, _) in SHAPES.items() if obj.name == mesh_name]
            if len(matches) != 1 or obj.parent_bone_name != "Attach" or obj.bone_influences:
                raise ValueError(f"unexpected Stone mesh or binding: {obj.name}")
            name = matches[0]
            texture = material_textures[labels[(obj.name, obj.subindex)]]
            if texture.casefold() != SHAPES[name][1].casefold():
                raise ValueError(f"unexpected Stone texture for {name}: {texture}")
            pos = obj.positions[0].data[:, :3]
            normal = obj.normals[0].data[:, :3]
            uv = obj.texture_coordinates[0].data[:, :2]
            indices = obj.vertex_indices.tolist()
            for t in range(0, len(indices), 3):
                pieces[name].append([
                    {"p": [round(float(x) * SCALE, 6) for x in rotate_y(pos[i], name)],
                     "n": [round(float(x), 6) for x in rotate_y(normal[i], name)],
                     "uv": uv[i].round(6).tolist()}
                    for i in indices[t:t + 3]
                ])
        if any(not v for v in pieces.values()):
            raise ValueError("one or more Stone meshes missing")
        description = {"source": str(args.source), "texture_size": args.texture_size,
                       "camera_yaw_deg": args.camera_yaw_deg,
                       "shape_yaws": shape_yaws,
                       "shapes": [{"name": name, "texture": tex, "triangles": pieces[name]}
                                  for name, (_, tex) in SHAPES.items()]}
        (args.out_dir / "stone-mesh.json").write_text(json.dumps(description), encoding="utf-8")
        print(json.dumps({name: len(tris) for name, tris in pieces.items()}))

    if not args.mesh_only:
        from PIL import Image

        for name, (_, texture) in SHAPES.items():
            source = args.source / (texture.lower() + ".nutexb")
            png = args.out_dir / f"{name}-source.png"
            subprocess.run([str(args.tex_cli), str(source), str(png)], check=True)
            with Image.open(png) as source_image:
                image = source_image.convert("RGBA").resize(
                    (args.texture_size, args.texture_size), Image.Resampling.LANCZOS)
            image.save(args.out_dir / f"{name}.png")
            (args.out_dir / f"{name}.bgra").write_bytes(image.tobytes("raw", "BGRA"))
        print(json.dumps({"texture_size": args.texture_size, "out_dir": str(args.out_dir)}))


if __name__ == "__main__":
    main()
