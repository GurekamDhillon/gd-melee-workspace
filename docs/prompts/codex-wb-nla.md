# Codex packet WB-NLA: hand-splicing in Blender with NLA strips (2026-10-10)

Your cwd is a workspace worktree (`worktrees/wbnla`, branch `ws/wb-nla`, cut from `ws/geno-workbench` `db4cd16`). Read `CLAUDE.md` first.
Owner-approved follow-up to Workbench Task 9: the owner wants to **splice Goku moves by hand in Blender** from the XV2 kit and cross-port clips.

## Rules (important)
- SHELL IS UNAVAILABLE on this machine (every command fails with "setup refresh had errors"). Write code and tests with file tools only. Do NOT build, run, or use git. A Claude lead runs and commits everything.
- Write only inside this worktree. Tests first, then code. Mentally execute every test against your code.
- No disc-derived or XV2-derived data in code, tests or fixtures (synthetic numbers only). Clip data is read at runtime from the local IR, never copied into the repo.
- Pure modules: standard library only, no bpy (tests import them via `tests/conftest.py`). bpy only in the bpy modules.
- Do not edit `ports/goku-xv2/tools/splice.py`, `splices.json`, `fidelity.py` or `xv2_to_artist.py`; another lane is changing them. Read them only.
- Do not stop for design approval; record choices in the report.

## Read first
- `ports/goku-xv2/tools/splice.py`: the docstring is the recipe format (segments, from/to, speed, mirror, root_yaw, hold, blend, marks). Blend frames are INSERTED between segments; output index = segment start + (source frame - from) / speed. Your layout must give the same output frame for every source frame as splice.py does.
- `ports/goku-xv2/splices.json` (the 3 EXAMPLE recipes).
- `tools/geno/artist/blender/actions.py`, `export_fighter.py`, `geno_panel.py` and `tools/geno/artist/README.md`: how a Blender action becomes a clip and is exported (Bake & export goes through this; do not write a second exporter).
- `ports/goku-xv2/tools/cross_port.py` and `xv2_to_artist.py`: where XV2 and `melee:<fighter>/<action>` clips come from (read-only; call their public functions, don't duplicate them).
- `tools/blender/geno_workbench/` (`__init__.py`, `props.py`, `operators.py`, `panels.py`, `rig.py`, `tests/`): the add-on you extend; follow its style, STRINGS table and registration.

## Scope
1. `tools/blender/geno_workbench/nla_layout.py` (pure): `layout(recipe: dict, clip_lengths: dict[str,int]) -> Layout` giving, per segment, the strip's action name, `frame_start`/`frame_end` in output frames, `scale` (1/speed), `reversed` (from > to), hold length, mirror and root_yaw flags, the blend gaps between strips, the output frame of every mark, and total length (with `frames` retime). Plus `recipe_from_layout(layout) -> dict` (the inverse, so a hand-edited NLA track can be written back as a recipe) and `validate(recipe, clip_lengths) -> list[str]`.
   Tests `tests/test_nla_layout.py`: the 3 recipe shapes (synthetic clip lengths), speed 2, reversed crop, hold, per-segment blend override, `frames` retime, mark output frames equal to splice.py's formula, round trip layout -> recipe -> layout.
2. `tools/blender/geno_workbench/nla.py` (bpy): import a clip as an action on the active armature (XV2 or cross-port, via the existing tools), lay a recipe out as NLA strips on one track per recipe (blend gaps as strip blend_in/blend_out or gap strips; document which and why it matches the inserted-blend semantics), read the current strips back as a recipe, and Bake (bake NLA to one action) then export through `tools/geno/artist` with the clip marked status AUTHORED in what it writes.
3. Operators and a "Splice" panel in the Geno sidebar: Import clip, Lay out recipe (pick from `splices.json`), Save strips as recipe (writes a NEW recipe file next to the project, `splices.authored.json`; never edits `splices.json`), Bake & export.
4. A headless check `tools/blender/geno_workbench/selftest_nla.py` in the style of `selftest_edit.py`: synthetic armature and two synthetic actions, lay out a recipe, read it back, bake, assert the baked pose at the mark frames equals the source pose; print `GENO_WB_CHECK nla OK`.

## Report
Write `.omo/evidence/wb-nla-report.md` in this worktree (max 40 lines): files, public API, how blends map to NLA, deviations, the exact commands the lead must run (pytest paths; the Blender headless command for selftest_nla), and what is unverified.
