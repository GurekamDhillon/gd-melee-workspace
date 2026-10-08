# tools/skins: skin mods (costume packs) for the registry

A **skin** is a mod (`kind: "skin"`) that adds costumes to one target fighter: a retail fighter, an
m-ex fighter (`PlWf.dat`) or a Geno define. The format is specified in
`docs/superpowers/plans/2026-10-08-skins-registry.md` section 2 (later `docs/mods-packaging.md`).

Three tools, one shared core:

- `skinlib.py`: reads a costume DAT's public symbols, writes a skin mod folder, lints one. No disc access.
- `skin_import.py`: turns costume `.dat`/`.usd` files (or a folder of them) into skin mods, or lints one.
- `make_test_skins.py`: writes a synthetic test pack. Model files are copies of your own retail costume
  DATs, read from your disc at run time; the art is generated (a number on a hue gradient).

```
python tools/skins/skin_import.py Pikachu.dat --out mods --name "Pika Blue" --csp csp.png --stock stock.png
python tools/skins/skin_import.py costumes/ --out mods --author someone --target retail:fox
python tools/skins/skin_import.py mods/pika-blue --lint-only
python tools/skins/make_test_skins.py --out "$TEMP/skin-pack" --iso "$GW_ISO_VANILLA" \
    --fighters mario:40,fox:30,falco:20,mars:20,captain:10,link:10 --art-every 5
python -m pytest tools/skins/tests -q        # from the worktree root; needs no disc
```

Notes:

- `--target` is `retail:NAME`, `mex:PlWf.dat` or `geno:KEY`. Without it the DAT is classified by its
  `Ply<Fighter>5K<Colour>_Share_joint` symbol. A DAT with no such symbol needs `--joint` (and `--matanim`).
- Sheik (`seak`) and Nana costumes are refused: they belong with Popo or Zelda as a partner.
- `skin_import.py` refuses disc images (`.iso` and similar) and reads only the costume file it is given.
- `png2gx.py` comes from the game checkout: `GW_MELEE` (default: the skins255 worktree). Art is
  converted with `--allow-odd-size`, as the format specifies.
- `make_test_skins.py` refuses an `--out` inside `tools/`, `docs/` or `pc/` (exit 2) and writes
  `.gitignore` containing `*` into `--out`.

**Never commit the generated folder** (a mods folder or a test pack). It holds disc-derived model
files. Keep generated output outside the repo, or in a folder git ignores. Only the code in this
directory and its tests belong in git.
