# Code task for Codex: cut Sora's draw calls in fighterbuild

Written 2026-09-26 by the coordinating Claude session. **This is a code-only task.** Do NOT build the
game, run the game, run build.sh/run.sh, launch other Codex processes, or profile. Write the code,
compile the C# tool, run its own verify, and stop. Claude builds, runs and measures afterwards.

## The measured problem (already done; do not re-measure)

| scene | mean ms | draw calls | game CPU ms |
|---|---|---|---|
| Sora idle | 29.0 | 8,643 | 12.3 |
| Marth idle | 16.7 | 380 | 1.5 |

The cost is the same idle/walking/attacking, so it is per-frame drawing of Sora's model: about 1,000
POBJs, each split into many GX primitives (triangle strips), each of which becomes a draw.

## What to change

Files: `ports/ir/tools/fighterbuild/Program.cs` and
`experiment/tooling/HSDLib/HSDRaw/Tools/POBJ_Generator.cs`. Both already carry a previous Codex
session's uncommitted start (`BatchTriangleLists`, behind `FIGHTERBUILD_BATCH_TRIANGLES=1`). Read
that diff first (`git diff` in the workspace and in `experiment/tooling/HSDLib`) and build on it or
replace it.

1. **One primitive per POBJ.** Each POBJ emits a single GX_TRIANGLES primitive (a triangle list), not
   many strips. Make this the default for fighterbuild (drop the env var, or default it on), and
   keep the old strip path available with `FIGHTERBUILD_STRIPS=1`.
2. **Fewer POBJs.** Where the generator starts a new POBJ, pack as many triangles as fit under GX's
   limit of 10 position/normal matrices per POBJ (its envelope list). Order a DOBJ's triangles so
   triangles sharing bones/envelopes are adjacent (e.g. group by their sorted envelope set, then
   pack groups greedily) before generating. Also respect the display-list vertex-count limit the
   generator already has (16-bit count per primitive: split at 65,535 vertices max).
3. **Report counts.** fighterbuild's existing report JSON gains, per DOBJ and in total:
   `pobjs`, `primitives`, `vertices`, before and after (the "before" from the strip path, run
   in-process or from the numbers the old path would give).

Do not change how anything looks: same vertices, normals, UVs, colours, weights, cull mode, material.
Only the grouping and primitive type change.

## Acceptance (you check these yourself)

- `dotnet build -c Release` of fighterbuild succeeds.
- Run fighterbuild on Sora's existing inputs, which are already built:
  `_build/tmp/ultimate-mods/ultimate-trail-slot-marth/_work/` (mesh_c00.json and the template; see
  how `ports/ir/tools/install_ultimate.py` invokes fighterbuild and copy that exact command line,
  with the output going to a new folder under `_build/tmp/codex-drawcalls/`, never into a mods folder).
- fighterbuild's own verify passes (it re-reads the output DAT).
- The report shows total primitives down by at least 5x vs the strip path, and total POBJs down.
- A triangle-set equality check you add (a small Python or C# check that reads both the old and new
  output and compares the multiset of skinned triangles: positions, UVs, weights) reports 0
  differences.

## Rules

- No commits, pushes or merges. Leave the diff; list the files changed.
- Never copy or commit game-derived data (the `_work` inputs and outputs are Ultimate-derived and stay
  under `_build/`).
- If something in the task is wrong or impossible, stop and say so in the report instead of working
  around it.

## Report (final message, and also write it to `_build/tmp/codex-drawcalls-report.md`)

1. Files changed and what.
2. The before/after counts table (POBJs, primitives, vertices; total and for the 5 biggest DOBJs).
3. The equality check result.
4. The exact fighterbuild command line you used.
