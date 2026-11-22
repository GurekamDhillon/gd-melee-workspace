# Codex packet: base-none Geno define gets no shield pushback (2026-10-08)

Workspace root `E:\Projects\Melee Workspace`. Worktrees ALREADY EXIST; edit files ONLY there:
- game: `E:\Projects\Melee Workspace\worktrees\geno-s8` (branch `agent/geno-s8`)
- workspace: `E:\Projects\Melee Workspace\worktrees\ws-geno-s8` (branch `ws/geno-s8`)
Your sandbox cannot write `.git`: run NO git command that writes. You MAY build (`bash tools/port/build.sh`, with
`GW_MELEE` = the game worktree, `GW_BUILD_ROOT=E:/Projects/Melee Workspace/_build/agents/geno-s8`) and run the
HEADLESS suite (`run.sh --test`) and native tests. Windowed runs crash in your sandbox: do not attempt them; put the
exact windowed re-check command in your report. Note: in your sandbox the `mexid_disc_table` headless test fails
because the sandbox cannot read the disc's identity table; it passes outside. Ignore that one test, report the rest.

## The bug (measured)

Old Sora mod (a donor-based fighter) vs Sora as a base-`none` format-10 define, same exe, scenario `def_shield_fsmash`
(Sora shields Fox's forward smash): the old mod goes `GuardReflect -> Guard -> GuardSetOff -> Guard` and slides back
(x reaches -5.049); the define goes `GuardReflect -> Guard`, never enters `GuardSetOff`, and x stays 0. Every other
defense scenario (jab, tilts, smashes, aerials, shield vs jab, grab, throw) is identical. Diff:
`E:\Projects\Melee Workspace\_build\tmp\geno-slice8\continued\defense-diff.json`; scenario driver:
`worktrees/ws-geno-s8/tools/geno/moves_check/defense.lua`.
So a base-none define does not get shield set-off (shield pushback / shield stun state). It affects every base-none
define (the Courier too), not just Sora.

## Find and fix

Read the shield-hit path in the game worktree: the retail guard code (`src/melee/ft/chara/ftCommon/ftCo_Guard*.c` or
equivalent `GuardSetOff` handling), what decides the set-off (shield-stun) transition and pushback velocity (the hit's
damage / shield attributes such as `shield_break`/`guard` attributes in the fighter attributes, a donor table read
through ftData, or a motion row the generic "none" preset lacks: the set-off motion 0x... and its animation row), and
how a base-none define supplies it (melee/docs/geno.md 22.x, `geno_define_data.inc`, `GenoDefine_FtDataSharedMask`,
the slice-4 notes on donor requests a none define cannot honour, fighter.rows). Fix it in the engine so a base-none
define enters GuardSetOff with the same pushback as a donor-based fighter given the same attributes (deterministic,
additive, no change to retail or donor-based fighters). Add a native or headless test that would have caught it.

## Deliver

Report to `E:\Projects\Melee Workspace\_build\tmp\codex-shield-setoff-report.md`: root cause (file:line), proposed
commit message(s), files changed, build/headless/native results quoted, and the exact windowed re-check: the
`defense` part of the slice-8 parity commands (see `_build/tmp/codex-geno-s8-report.md`, "Exact windowed parity
commands") so the coordinator can confirm `def_shield_fsmash` now matches.
