"""Extract Ultimate Kirby's Warp Star Entry model into an ignored build directory.

Run mesh extraction with Blender's bundled Python (matching ssbh_data_py), and
texture extraction with a Python that has Pillow. The two modes can be run
independently; no game-derived output belongs in git.
"""

from pathlib import Path
import argparse
import json
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
DEPENDENCIES = ROOT / "experiment/tooling/ultimate/profile/blender/scripts/addons/smash-ultimate-blender/dependencies"
DEFAULT_SOURCE = ROOT / "experiment/tooling/ultimate/workspace/extracted/fighter/kirby/model/warpstar/c00"
DEFAULT_CLI = ROOT / "experiment/tooling/ultimate/apps/Ultimate-Tex-CLI/ultimate_tex_cli.exe"
DEFAULT_OUT = ROOT / "_build/tmp/ultimate-kirby-warpstar"
OBJECTS = {
    "WarpstarShape": "star",
    "group7_O_OBJ_O_SORTEACHNODEShape": "star",
    "group8_O_OBJ_O_SORTEACHNODEShape": "star",
    "polySurface1Shape": "glow",
    "polySurface2Shape": "glow",
}
TEXTURES = {
    "star": "metal_starmissile_001_col.nutexb",
    "glow": "skin_starmissile_001_col.nutexb",
}


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
    if not 16 <= args.texture_size <= 1024 or args.texture_size % 4:
        parser.error("texture size must be a multiple of four from 16 to 1024")
    args.out_dir.mkdir(parents=True, exist_ok=True)

    objects = []
    if not args.textures_only:
        sys.path.insert(0, str(DEPENDENCIES))
        import ssbh_data_py as ssbh  # noqa: E402

        mesh = ssbh.mesh_data.read_mesh(str(args.source / "model.numshb"))
        modl = ssbh.modl_data.read_modl(str(args.source / "model.numdlb"))
        labels = {(entry.mesh_object_name, entry.mesh_object_subindex): entry.material_label
                  for entry in modl.entries}
        if len(mesh.objects) != len(OBJECTS):
            raise ValueError(f"expected {len(OBJECTS)} Warp Star mesh objects, got {len(mesh.objects)}")
        for obj in mesh.objects:
            material = OBJECTS.get(obj.name)
            expected_label = "ShaderfxShader3" if material == "star" else "starmissile_pbr_glow"
            if (material is None or obj.parent_bone_name != "Rot" or obj.bone_influences
                    or labels.get((obj.name, obj.subindex)) != expected_label):
                raise ValueError(f"unexpected Warp Star object binding/material: {obj.name}")
            positions = obj.positions[0].data[:, :3]
            normals = obj.normals[0].data[:, :3]
            uv = obj.texture_coordinates[0].data[:, :2]
            indices = obj.vertex_indices.tolist()
            triangles = [[{"p": positions[i].round(6).tolist(),
                           "n": normals[i].round(6).tolist(),
                           "uv": uv[i].round(6).tolist()}
                          for i in indices[t:t + 3]]
                         for t in range(0, len(indices), 3)]
            objects.append({"name": obj.name, "subindex": obj.subindex,
                            "material": material, "triangles": triangles})
        objects.sort(key=lambda obj: (obj["material"] != "star", obj["name"]))
        (args.out_dir / "warpstar-mesh.json").write_text(json.dumps({
            "source": str(args.source), "texture_size": args.texture_size,
            "parent_bone": "Rot", "objects": objects,
        }), encoding="utf-8")

    if not args.mesh_only:
        from PIL import Image

        for material, filename in TEXTURES.items():
            decoded = args.out_dir / f"{material}-source.png"
            subprocess.run([str(args.tex_cli), str(args.source / filename), str(decoded)], check=True)
            with Image.open(decoded) as source_image:
                image = source_image.convert("RGBA").resize(
                    (args.texture_size, args.texture_size), Image.Resampling.LANCZOS)
            image.save(args.out_dir / f"{material}.png")
            (args.out_dir / f"{material}.bgra").write_bytes(image.tobytes("raw", "BGRA"))
    print(json.dumps({"out_dir": str(args.out_dir), "objects": [
        {"name": obj["name"], "material": obj["material"],
         "triangles": len(obj["triangles"])} for obj in objects]}, indent=2))


if __name__ == "__main__":
    main()
