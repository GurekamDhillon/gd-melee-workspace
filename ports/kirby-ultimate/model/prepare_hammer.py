"""Prepare Ultimate Kirby's hammer article mesh and textures for Melee.

The source is a locally extracted Ultimate asset. Output is game-derived and
must stay in an ignored build directory.
"""

from pathlib import Path
import argparse
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
DEPENDENCIES = ROOT / "experiment/tooling/ultimate/profile/blender/scripts/addons/smash-ultimate-blender/dependencies"

DEFAULT_SOURCE = Path(r"E:\Ultimate files\workspace\extracted\fighter\kirby\model\hammer\c00")
DEFAULT_CLI = ROOT / "experiment/tooling/ultimate/apps/Ultimate-Tex-CLI/ultimate_tex_cli.exe"
DEFAULT_OUT = ROOT / "_build/tmp/ultimate-kirby-hammer"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--tex-cli", type=Path, default=DEFAULT_CLI)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--texture-size", type=int, default=256)
    parser.add_argument("--mesh-only", action="store_true")
    parser.add_argument("--textures-only", action="store_true")
    args = parser.parse_args()
    if args.mesh_only and args.textures_only:
        parser.error("select only one preparation mode")
    args.out_dir.mkdir(parents=True, exist_ok=True)

    objects = []
    if not args.textures_only:
        sys.path.insert(0, str(DEPENDENCIES))
        import ssbh_data_py as ssbh  # noqa: E402
        mesh = ssbh.mesh_data.read_mesh(str(args.source / "model.numshb"))
        modl = ssbh.modl_data.read_modl(str(args.source / "model.numdlb"))
        labels = {(e.mesh_object_name, e.mesh_object_subindex): e.material_label for e in modl.entries}
        if len(mesh.objects) != 2:
            raise ValueError(f"expected two Ultimate hammer objects, got {len(mesh.objects)}")
        for obj in mesh.objects:
            if obj.parent_bone_name != "Have" or obj.bone_influences:
                raise ValueError(f"unexpected hammer binding: {obj.name} / {obj.parent_bone_name}")
            label = labels[(obj.name, obj.subindex)]
            material = "metal" if label.startswith("metal_") else "def" if label.startswith("def_") else None
            if material is None:
                raise ValueError(f"unexpected hammer material {label}")
            pos = obj.positions[0].data[:, :3]
            normal = obj.normals[0].data[:, :3]
            uv = obj.texture_coordinates[0].data[:, :2]
            triangles = []
            indices = obj.vertex_indices.tolist()
            for t in range(0, len(indices), 3):
                triangles.append([
                    {"p": pos[i].round(6).tolist(), "n": normal[i].round(6).tolist(),
                     "uv": uv[i].round(6).tolist()}
                    for i in indices[t:t + 3]
                ])
            objects.append({"name": obj.name, "subindex": obj.subindex,
                            "material": material, "triangles": triangles})
        objects.sort(key=lambda obj: (obj["material"] != "def", obj["name"], obj["subindex"]))
        if [obj["material"] for obj in objects] != ["def", "metal"]:
            raise ValueError("expected one wood and one metal hammer object")
        result = {"objects": objects, "texture_size": args.texture_size,
                  "source": str(args.source)}
        (args.out_dir / "hammer-mesh.json").write_text(json.dumps(result), encoding="utf-8")

    if not args.mesh_only:
        from PIL import Image
        for material in ("def", "metal"):
            source = args.source / f"{material}_kirby_hammer_002_col.nutexb"
            png = args.out_dir / f"{material}-source.png"
            subprocess.run([str(args.tex_cli), str(source), str(png)], check=True)
            with Image.open(png) as source_image:
                image = source_image.convert("RGBA").resize(
                    (args.texture_size, args.texture_size), Image.Resampling.LANCZOS)
            image.save(args.out_dir / f"{material}.png")
            # HSDRaw's RGB5A3 encoder consumes BGRA bytes.
            (args.out_dir / f"{material}.bgra").write_bytes(image.tobytes("raw", "BGRA"))
    print(json.dumps({"objects": [{"name": obj["name"], "material": obj["material"],
                                   "triangles": len(obj["triangles"])} for obj in objects],
                      "texture_size": args.texture_size, "out_dir": str(args.out_dir)}, indent=2))


if __name__ == "__main__":
    main()
