# ports/goku-xv2/anim: hand-animated rows

`hand.json` (not present until the owner saves a clip) holds the artist's own keyframes for Goku, as deltas over the converted clip of
the same engine row (mode `layer`) or over the rest pose (mode `replace`). It is read by `tools/xv2_to_artist.py` (the last step of the
animation pass) and is a Stage A input of `tools/build.py`, so saving a clip and rebuilding is enough. The converter never writes it,
and re-running Stage A / `--blend` does not lose it (only `goku.blend` is regenerated). Format: `tools/geno/artist/blender/hand_layer.py`.
How to author one: `tools/blender/geno_workbench/README.md` "Hand-animate with IK and FK".

- `examples/hand.reach-jab.json`: the example clip authored with `tools/blender/geno_workbench/anim_rig_demo.py` (Attack11 reaches 3 units
  further with the right hand, torso twist). Not wired: the build only reads `anim/hand.json` (or the file named by `GOKU_HAND`).
  Try it on a copy: `GOKU_AUTHOR=hand-demo GOKU_HAND=ports/goku-xv2/anim/examples/hand.reach-jab.json python ports/goku-xv2/tools/xv2_to_artist.py`.
- No XV2 data is stored here: only the deltas the artist made. Do not paste converted clips into it.
