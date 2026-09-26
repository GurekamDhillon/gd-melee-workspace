# Task packet for Codex: profile and improve performance with Sora in a match

Written 2026-09-26 by the coordinating Claude session for GD. Run from the workspace root:

```powershell
Get-Content -Raw .\docs\prompts\codex-sora-performance.md |
  codex exec -C . --sandbox workspace-write `
    -o .\_build\tmp\codex-perf-report.md - *> .\_build\tmp\codex-perf-run.log
```

---

## Objective

GD played Ultimate Sora in GD's Melee (the PC port) and says it "worked very well except for
performance". Find **where the frame time goes** when Sora is in a match, then **reduce it** without
changing how the game looks or plays. Measure first; change second; every claim needs a number.

## Read first (required)

1. `CLAUDE.md` (workspace root), `docs/NEXT-SESSION.md` and the handoff it points to, `docs/HANDOFF.md`
   §6 Traps and §7 Conventions.
2. `melee/CLAUDE.md`, `melee/pc/docs/PORT_DEV_QUICKREF.md` (building), and the `CLAUDE.md` files under
   `melee/pc/platform`, `melee/pc/geno`, `tools/`, `ports/`.
3. `_build/agents/LANES.md` - the multi-agent rules below come from it.
4. `melee/docs/geno.md` §19 (Geno articles/effects) - Sora's magic uses them.

## Where things are

- Game repo: `melee/` (branch `pc-port`). Workspace (this repo): tools, ports, build system.
- Sora is an m-ex fighter slot built by `ports/ir/tools/install_ultimate.py`. The current build GD plays:
  mods folder `C:\Users\Gurek\Desktop\GD's Melee\_build\agents\alpha\sora\mods-marth`, scene
  `mode=training;p1=mex:52;p2=fox/cpu1/kind0;stage=fd`. Launch through `tools/port/run.sh <name>
  --iso "C:/iso/SSBM ACE Build v2.0.0.iso"` with `MELEE_MODS_DIR` and `MELEE_SCENE` set.
- Known heavy parts of Sora, from the lanes' reports: 175 joints, one body of ~1,002 draw pieces
  (POBJs) - two bodies (1,609) once overflowed the renderer's 24 MiB uniform buffer -, 88k triangles,
  ~6 MB of animation (163 clips, helper bones baked in), Geno articles and particle effects for his
  magic (Firaga with ~20 particle generators). None of these is proven to be the bottleneck.
- Renderer: Aurora (WebGPU via Dawn), GX shims in `melee/pc/platform/shim_gx*.c`. The log already has
  per-frame diagnostics (`gw: DIAG ... aurora drawcalls=... merged=... verts=...`, `heartbeat retrace/
  presented`) - start from those.

## What to do

1. **Baseline.** Build (`tools/port/build.sh`) into your own build root (below), run the Sora scene and
   a vanilla reference (same scene with `p1=marth`), and record per frame: CPU frame time split into
   game logic / animation (joint matrices, skinning) / GX command building / Aurora submit, GPU time if
   available, draw calls, vertices, uniform-buffer bytes, allocations. Add timing instrumentation where
   it is missing, behind an env var (e.g. `MELEE_PROFILE=1`) that writes log lines; don't leave it on by
   default. Record 60 s of each scene: idle, walking, and using moves (script inputs with a pad script
   and `MELEE_INPUT=none`; see existing `_build/agents/*/sora/test/*.lua` and `docs/scripting.md`).
2. **Find the top costs** with numbers: which of the above dominate with Sora vs the vanilla reference.
3. **Fix the biggest ones**, in order, general rather than Sora-specific where possible (other ported
   fighters will share them). Candidates to check, not conclusions: per-POBJ draw overhead and batching
   in Aurora; envelope/skinning cost for 175 joints; matrix recomputation; animation decode; particle
   generator cost; uniform-buffer churn. Also check `ports/ir/tools/fighterbuild` output (POBJ splitting,
   strips) if the draw-piece count is the cost - fewer, larger POBJs may be the fix.
4. **Re-measure** after each change with the same scenes; keep a before/after table.

## Acceptance (all required)

- A before/after table: frame time (mean, p95, worst) for the Sora scene and the vanilla reference, with
  the per-stage split, and draw calls/vertices. Sora's frame time measurably lower; the vanilla scene
  not slower.
- No change in look or play: the headless test suite passes (`tools/port/run.sh --test tests --iso
  "C:/iso/SSBM ACE Build v2.0.0.iso"`, currently 190/190); Sora's in-game pose still matches its source
  (`ports/ir/tools/compare_joints.py` on a joint-probe log, median error stays ~0.006 units); hitbox
  positions unchanged. GD judges the look himself - leave a game window running for him with the final
  build (Sora scene above) and say which one it is.
- Every fix verified in the built exe, not the source (`grep -a` a new log string in the exe; a stale exe
  is the documented failure mode), and in the run's log.

## Rules

- **Work in your own worktree and build root:** `bash tools/port/agent_new.sh codex-perf pc-port`, then
  export `GW_MELEE` and `GW_BUILD_ROOT` it prints in every shell call. `GW_BUILD_ROOT` must be a
  Windows-style path (`C:/Users/...`), not `/c/...`, or build.sh silently leaves a stale exe. **Never
  edit the main `melee/` checkout** - other agents (lanes alpha, beta, echo) are working in parallel.
- Workspace files you change: only what the task needs; other agents are editing `ports/ir/tools/*`
  (lane alpha) - coordinate by touching them minimally and saying exactly what you changed.
- **Do not commit, push, merge or publish.** Leave your changes in your worktree and list them; the
  coordinator reviews and merges.
- Game instances: at most ONE for you, TWO in total on this machine (check running `melee-pc` processes
  and free RAM first; wait if two are running - an out-of-memory bluescreen has happened before). Disk is
  nearly full: delete your own old run folders when done with them.
- Test matches use a passive CPU (`p2=<fighter>/cpu1/kind0`); scripted runs use `MELEE_INPUT=none`.
  `MELEE_VOLUME=3` (run.sh sets it). ACE disc. **No screenshots** - verify with numbers.
- Never commit or copy game-derived data (anything from the disc images or Ultimate extraction).
- Don't use as a source any work in `ports/kirby-ultimate/` or `experiment/character-ir/*ultimate*`.

## Report (write it as your final message)

1. The before/after table and where the time went.
2. Each change: files, what and why, the measured effect.
3. Commands run and their results (build, tests, runs with their run-folder names).
4. What you did not finish, and remaining uncertainty.
5. The game window left for GD (run folder, scene).
