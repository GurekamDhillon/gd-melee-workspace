# Analysis + tool task for Codex: why Sora's body is still 619 mesh pieces

Written 2026-09-26 by the coordinating Claude session. **Offline only.** No game build or run, no
other Codex processes. Don't edit `ports/ir/tools/fighterbuild/` or HSDLib (another agent's
change there is being measured).

## Background

Sora's model (Smash Ultimate `trail`, ported to Melee) is drawn as mesh pieces (POBJs). The GameCube
format allows at most 10 skinning envelopes (weighted bone sets) per piece. After the last change,
the body (`body_highShape` sub 0) is still 619 pieces, versus a few dozen for a Melee fighter;
each piece costs a draw. Input mesh: `_build/tmp/ultimate-mods/ultimate-trail-slot-marth/_work/mesh_c00.json`
(game-derived; read only, never copy into the repo). How pieces are formed:
`experiment/tooling/HSDLib/HSDRaw/Tools/POBJ_Generator.cs` (triangles grouped by envelope set, packed
under 10 envelopes). Previous report: `_build/tmp/codex-drawcalls-report.md`.

## What to do

Write `ports/ir/tools/analyze_envelopes.py` (new; plain python + numpy) that reads the mesh JSON and
reports:
1. The number of distinct envelopes (bone+weight sets) and distinct bone sets; the influences per
   vertex histogram; the weight histogram.
2. A simulated packing (same rule as the generator: group triangles by their envelope set, pack
   greedily under 10) giving the piece count, so it matches today's 619 for the body.
3. What-ifs, each with the resulting piece count and the geometric cost:
   a. drop influences below w (w = 0.01, 0.02, 0.05) and renormalise;
   b. cap influences per vertex at 3 / 2;
   c. quantise weights to steps of 1/8, 1/16 (merging near-identical envelopes);
   d. a better packing order (e.g. cluster triangles by shared bones before greedy packing, or a
      graph-based bin packing) with weights unchanged.
   The cost is measured by skinning the mesh in 10 poses (the rest pose plus 9 frames spread over
   3 animations of your choice; the joint world matrices are computable from the files the port's
   joint probe uses, `ports/ir/tools/compare_joints.py` shows how) and reporting the max and p99
   vertex displacement versus the unmodified weights.
4. A recommendation: the smallest change that gets the body under 150 pieces with max displacement
   under 0.05 units, or the honest best if none does.

## Output

The tool (uncommitted) and `_build/tmp/codex-bodypieces-report.md` with the tables and the
recommendation. Final message: the report path and a five-line summary.
