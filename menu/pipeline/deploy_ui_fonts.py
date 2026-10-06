"""Convert the kit's font pages to GX textures and put them, with the font manifest, in a ui directory.

    python menu/pipeline/deploy_ui_fonts.py --outdir _build/ui [--build]

This is the step that makes the font pages (and so the Atlas text roles) reach the game and the release: the release ships
`git ls-files _build/ui`, and the loader reads `ui/font_manifest.json` plus one `<page>.gxtex` per page. It works from a
clean checkout: the PNG pages are git-ignored, so `--build` (default when a page is missing) regenerates them first with
font_atlas.py (deterministic in pixels; Pillow and the OFL fonts in menu/ are all it needs, no browser, no game files).
Unlike `png2gx.py --layout menu/out_kit/manifest.json` it does not need the kit's glyph PNGs, which a clean tree lacks.

The converter is the game checkout's pc/tools/png2gx.py: GW_MELEE selects the checkout, else <workspace>/melee.
Every font page in menu/out_kit/font/font_manifest.json is converted (legacy and Atlas), as I4 at 2x, which is what the
manifest says (format I4). Nothing here is disc-derived: the glyphs are rendered from Source Sans 3, Hasklug and Barlow
Condensed (SIL OFL 1.1).
"""
import argparse
import importlib.util
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MENU = os.path.dirname(HERE)
REPO = os.path.dirname(MENU)
FONT_DIR = os.path.join(MENU, "out_kit", "font")


def load_png2gx():
    game = os.environ.get("GW_MELEE") or os.path.join(REPO, "melee")
    path = os.path.join(game, "pc", "tools", "png2gx.py")
    if not os.path.exists(path):
        raise SystemExit("png2gx.py not found at %s (set GW_MELEE to the game checkout)" % path)
    spec = importlib.util.spec_from_file_location("png2gx", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--outdir", required=True, help="the ui directory (_build/ui for the release)")
    ap.add_argument("--build", action="store_true", help="regenerate the PNG pages with font_atlas.py first")
    a = ap.parse_args(argv)
    manifest_path = os.path.join(FONT_DIR, "font_manifest.json")
    pages = []
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            pages = [t["name"] for t in json.load(f)["textures"]]
    missing = [n for n in pages if not os.path.exists(os.path.join(FONT_DIR, "2x", n + ".png"))]
    if a.build or missing or not pages:
        sys.path.insert(0, HERE)
        import font_atlas
        if font_atlas.main() != 0:
            raise SystemExit("font_atlas.py checks failed")
        with open(manifest_path, encoding="utf-8") as f:
            pages = [t["name"] for t in json.load(f)["textures"]]
    png2gx = load_png2gx()
    os.makedirs(a.outdir, exist_ok=True)
    for name in pages:
        src = os.path.join(FONT_DIR, "2x", name + ".png")
        dst = os.path.join(a.outdir, name + ".gxtex")
        try:
            png2gx.main([src, dst, "--format", "i4"])
        except SystemExit as e:
            if e.code:
                raise SystemExit("%s: png2gx failed: %s" % (name, e.code))
    shutil.copyfile(manifest_path, os.path.join(a.outdir, "font_manifest.json"))
    print("deployed %d font pages and font_manifest.json to %s" % (len(pages), a.outdir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
