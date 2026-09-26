# Code task for Codex: smaller Ultimate animations at the same visible accuracy

Written 2026-09-26 by the coordinating Claude session. **Code only.** Do NOT build or run the game,
run build.sh/run.sh, launch other Codex processes, or profile the game. Write the code, run the
offline checks below, and stop. Claude installs and checks in game afterwards.

## Background

`ports/ir/tools/convert_ultimate_anim.py` turns Ultimate's per-frame animations into Melee
figatrees (encoder: `ports/ir/tools/figatree.py`). Sora (Ultimate fighter id **`trail`**, never
`sora`) has 163 clips, about 6 MB, with helper bones baked in; that is a large share of his memory
and load cost. Today every channel is fitted on its own to a fixed tolerance
(`TOL = {"rot": 2e-3, "tra": 2e-3, "sca": 1e-3}`, line ~52) by greedily adding the worst-fitting
frame as a key (`encode()`, line ~118). That treats a finger joint and the hip the same, and a
greedy fit keeps more keys than needed.

The file already re-decodes each output and checks it against the source per channel and in world
space (joint positions) - `check()`, line ~315, and `--check-half` for half frames. Use that as the
ground truth; read the whole file before changing it.

## What to change (in `convert_ultimate_anim.py`, and `figatree.py` only if needed)

1. **Measure first.** Add a `--stats` output: bytes per clip, and per joint and channel kind (rot /
   tra / sca), plus the key counts. Run it on the current code for all of trail's clips and keep the
   numbers for the report.
2. **Tolerance in world space, not per channel.** Derive each joint's channel tolerance from how far
   its error moves the skinned result: e.g. rotation tolerance = world tolerance / (the largest
   distance from the joint to any descendant joint in the rest pose), translation tolerance = world
   tolerance directly, with a floor and a ceiling so a leaf joint does not get unlimited slack. One
   knob, `--world-tol` (default chosen so the acceptance below holds).
3. **A better fit than greedy insertion,** if the stats show keys dominate: e.g. start from all
   frames and remove keys while the error stays within tolerance, or split recursively at the worst
   frame (Douglas-Peucker style) and then try merging. Keep the s16-then-f32 quantisation logic.
4. Keep everything else as it is: which channels get tracks, the root-motion rules, helper baking,
   the animation-driven rows, the Euler branch handling.

Keep it general (any fighter), not Sora-specific. Do not touch other files in `ports/ir/tools`
(other agents have uncommitted work there: fighterbuild/, trail_magic_geno.py, ultimate_vfx_geno.py,
acmd_parse.py, acmd_to_ftcmd.py, test_acmd_catch.py).

## Acceptance (you check these yourself)

- Run the converter for all of trail's clips the way `ports/ir/tools/install_ultimate.py` runs it
  (copy that invocation), before and after your change, with outputs under `_build/tmp/codex-anim/`
  (never into a mods folder or the repo).
- The built-in world-space check with `--check-half` passes for every clip after the change, and the
  report gives, over all clips and joints: max, p99 and median joint-position error, before and after.
  **Max must stay at or below 0.02 units; median must not rise above 0.006 units.**
- Total animation bytes drop by at least 35%. Report the per-clip table for the 10 largest clips.
- Nothing else in the output changes: the same clip list, joint count per clip, and the same set of
  animated channels (report any difference; there should be none).

## Rules

- No commits, pushes or merges; list the files changed.
- Game-derived data (source animations, outputs) stays under `_build/`; never copy it into the repo.
- If the task is wrong or impossible as written, stop and say so rather than working around it.

## Report (final message, and also written to `_build/tmp/codex-anim-report.md`)

1. Files changed and what.
2. Before/after: total bytes, keys, and the error table (max / p99 / median).
3. The 10 largest clips before/after.
4. The chosen `--world-tol` and why.
5. The exact commands run.
