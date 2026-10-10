"""Build Captain Falcon's model + skeleton as a .blend, from YOUR disc, headless.

    python tools/blender/geno_workbench/falcon/make_falcon_art.py [--force]

Steps (each skipped when its output exists):
  1. fetch HSDRaw (Ploaj/HSDLib "LatestCommit" release, MIT) and Blender Source Tools (Artfunkel, GPL-2.0+,
     pinned commit) into _build/tools-ext; they are used as external tools, nothing of theirs is copied here;
  2. build the small driver in HsdExport/ against HSDRaw's DLLs (needs the dotnet SDK);
  3. extract PlCaNr.dat and PlCaAJ.dat from GW_ISO_VANILLA with tools/gc_extract.py;
  4. export the model (glTF: meshes, materials, textures, skinning), the skeleton (.smd) and the animation
     clips (.smd, one per clip in the Geno Falcon plan) with the driver;
  5. build_blend.py in Blender: meshes from the glTF on the .smd rig, clips as Actions, saved to
     _build/geno-falcon-art/falcon.blend.
Everything written stays under _build/ (git-ignored); nothing disc-derived is committed.
Needs: dotnet SDK (8+), Blender, the disc image. GW_ROOT, GW_BLENDER, GW_ISO_VANILLA override defaults.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import urllib.request
import zipfile

HERE = Path(__file__).resolve().parent
HSD_URL = "https://github.com/Ploaj/HSDLib/releases/download/LatestCommit/HSDRAW.zip"
BST_COMMIT = "3d5fd9bf681547d86fa369715a0e8dd6013edcb7"   # BlenderSourceTools 3.4.3, checked on Blender 5.2.2
BST_URL = "https://github.com/Artfunkel/BlenderSourceTools/archive/%s.zip" % BST_COMMIT


def root_dir():
    if os.environ.get("GW_ROOT"):
        return Path(os.environ["GW_ROOT"])
    for p in HERE.parents:
        if (p / ".env").is_file() and (p / "_build").is_dir():
            return p
    return Path("E:/Projects/Melee Workspace")


def iso_path(root):
    if os.environ.get("GW_ISO_VANILLA"):
        return os.environ["GW_ISO_VANILLA"]
    env = root / ".env"
    if env.is_file():
        for line in env.read_text(errors="replace").splitlines():
            line = line.strip().removeprefix("export ")
            if line.startswith("GW_ISO_VANILLA="):
                return line.split("=", 1)[1].strip().strip("\"'")
    return ""


def run(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd))
    subprocess.run([str(c) for c in cmd], check=True, **kw)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="redo every step")
    ap.add_argument("--clips", default="all", help="comma list of clip names to import as Actions, or all (default)")
    args = ap.parse_args()
    root = root_dir()
    out = root / "_build/geno-falcon-art"
    ext = root / "_build/tools-ext"
    blender = os.environ.get("GW_BLENDER", "D:/SteamLibrary/steamapps/common/Blender/blender.exe")
    blend = out / "falcon.blend"
    if blend.is_file() and not args.force:
        print("exists:", blend)
        return 0
    iso = iso_path(root)
    if not iso or not Path(iso).is_file():
        print("GW_ISO_VANILLA is not set or missing: %r" % iso)
        return 2

    hsd = ext / "hsdraw/x"
    if args.force or not (hsd / "HSDRaw.dll").is_file():
        (ext / "hsdraw").mkdir(parents=True, exist_ok=True)
        z = ext / "hsdraw/HSDRAW.zip"
        urllib.request.urlretrieve(HSD_URL, z)
        with zipfile.ZipFile(z) as zf:
            zf.extractall(hsd)
    driver = ext / "driver/out/hsdexport.exe"
    if args.force or not driver.is_file():
        run(["dotnet", "build", HERE / "HsdExport/HsdExport.csproj", "-c", "Release", "-o", ext / "driver/out",
             "-p:HsdDir=" + str(hsd), "-p:BaseIntermediateOutputPath=" + str(ext / "driver/obj") + "/"])
    scripts = ext / "blscripts"
    if args.force or not (scripts / "addons/io_scene_valvesource/__init__.py").is_file():
        z = ext / "bst.zip"
        urllib.request.urlretrieve(BST_URL, z)
        (scripts / "addons").mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(z) as zf:
            prefix = "BlenderSourceTools-%s/io_scene_valvesource/" % BST_COMMIT
            for name in zf.namelist():
                if name.startswith(prefix) and not name.endswith("/"):
                    dest = scripts / "addons/io_scene_valvesource" / name[len(prefix):]
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(zf.read(name))
    package = Path(os.environ.get("GW_FALCON_PACKAGE") or root / "_build/falcon-look/geno-falcon")
    plan = package / "files/plan.json"
    if not plan.is_file():
        print("missing the Geno Falcon plan: %s (set GW_FALCON_PACKAGE)" % plan)
        return 2
    src = out / "src"
    for name in ("PlCaNr", "PlCaAJ"):
        if args.force or not (src / (name + ".dat")).is_file():
            src.mkdir(parents=True, exist_ok=True)
            run([sys.executable, root / "tools/gc_extract.py", iso, src, "--only", name])
    glb, smd, anim = out / "glb/falcon.glb", out / "smd/falcon.smd", out / "anim"
    if args.force or not glb.is_file():
        glb.parent.mkdir(parents=True, exist_ok=True)
        run([driver, src / "PlCaNr.dat", glb])
    if args.force or not smd.is_file():
        smd.parent.mkdir(parents=True, exist_ok=True)
        run([driver, src / "PlCaNr.dat", smd, "--no-textures"])
    if args.force or not any(anim.glob("*.smd")):
        run([driver, "--anim", src / "PlCaNr.dat", src / "PlCaAJ.dat", plan, anim] + args.clips.split(","))
    env = dict(os.environ, BLENDER_USER_SCRIPTS=str(scripts))
    run([blender, "--background", "--python", HERE / "build_blend.py", "--", glb, smd, anim, blend], env=env)
    print("done:", blend)
    return 0


if __name__ == "__main__":
    sys.exit(main())
