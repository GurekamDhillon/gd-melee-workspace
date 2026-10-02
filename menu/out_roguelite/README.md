# Roguelite UI art study

Original Astra-authored SVG masks and interactive menu-kit art review. No game
images or fonts. Open index.html; click branch buttons or use arrow keys. Up backs
out within the tree; at root it signals taunt without running a game.

Rebuild: `python3 menu/pipeline/roguelite_art.py` (requires rsvg-convert).
Build/placement study: `python3 menu/pipeline/roguelite_build_art.py`, then open
`build.html`. Its abstract mannequin is original vector art, not a fighter mesh.
Feedback/motion study: `python3 menu/pipeline/roguelite_feedback_art.py`, then open
`feedback.html` and click Replay Feedback. These HTML studies are proposals, not
captures of completed game screens.

Convert the masks with a Python environment containing Pillow:
`python melee/worktrees/linux/pc/tools/png2gx.py --layout menu/out_roguelite/manifest.json --outdir menu/out_roguelite/gx`.
The roguelite installer copies these GX textures and supplies their kit metadata.

The preview is an art study, not a screenshot of implemented gameplay. Names and
numbers illustrate the proposed commands. 18 masks are exported as 128px PNG/SVG;
manifest records original source, hashes and recommended GX mask format.
