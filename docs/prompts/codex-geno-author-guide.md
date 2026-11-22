# Codex packet: the Geno fighter author's guide (2026-10-08)

Workspace root `E:\Projects\Melee Workspace`. Worktree ALREADY EXISTS: `E:\Projects\Melee Workspace\worktrees\ws-geno-author-guide`
(branch `ws/geno-author-guide`). Edit files ONLY there. No git writes (the coordinator commits). The game checkout `melee/`
is READ-ONLY for you (integration). You MAY run python tools, `python -m tools.geno.artist ...`, `python -m tools.geno check`,
`build.sh` with `GW_BUILD_ROOT=E:/Projects/Melee Workspace/_build/agents/author-guide`, and the headless suite. No windowed runs:
write those commands into your report.

## Why
An outside agent (the owner's) will design and build an original Geno fighter. The art/import path is documented
(`docs/geno-artist-spec.md`, `docs/geno-artist-checklist.md`, `docs/geno-artist-rows.md`, `tools/geno/artist/README.md`).
The GAMEPLAY side (attributes, states, moves, hitboxes, Lua, articles, online rules) is spread across the 3,000-line design
history `melee/docs/geno.md` (later sections correct earlier ones). Write ONE authoritative, current guide.

## Read
`CLAUDE.md`, `tools/CLAUDE.md`, the artist docs above, `melee/docs/geno.md` (all; esp. 7, 9, 16, 17, 19, 20, 22, 23, 24, 14 LAB),
`docs/scripting.md`, the schema/tooling in `tools/geno/` (`python -m tools.geno.schema`, `check`), the define registry/parser in
`melee/pc/platform/geno_define_registry.inc` and friends, the Lua binding (`pc/geno/*lua*`), and the shipped samples' defines
(Striker, Courier, Charger, Riposte, Caster, Sora/base-none) as worked examples.

## Write `docs/geno-fighter-guide.md`
1. What a fighter is (files, folder layout, `geno.json` + art + Lua), and the 3-command artist loop it plugs into.
2. Every `geno.json` field that is CURRENT: type, range/units, default, which section/code defines it (file:line). Mark
   deprecated/superseded forms and say what replaced them. Attributes table (all 46 the importer emits + any others).
3. Moves: states, subactions/ftcmd scripts vs Lua; frame timing, hitbox fields (damage, angle, KB growth/base, size, bone/role,
   offset, element), hurtbox intangibility, IASA, landing lag, specials, grabs/throws, articles/projectiles, counters, on_hit.
4. Fighter Lua: the API surface actually registered (check registration tables, not prose), hooks, budget/limits, determinism
   rules, what faults do online (soft policy).
5. Online contract: what goes into the identity hash, what must be deterministic, what not to do.
6. Testing: LAB commands (inspect joints/hitboxes/timing), `moves_check`, `geno check`, the parity/rows tools, restart rules.
7. Worked example, BUILT and checked: give the sample `ports/geno-artist-samples/pip/` one NEW original special (e.g. neutral-B)
   with its own state, hitbox and a little Lua, through the pipeline (no converter source edits). Prove it with `geno check`,
   the headless suite, and a `moves_check` command for the coordinator if it needs a window.
8. A one-page "agent brief" at the top: the minimum an agent must read and the hard rules (no disc data, 2 influences, etc.).
Resolve contradictions against the code and list them (as the artist spec §14 did). Every claim checked against code.

## Deliver
Report `E:\Projects\Melee Workspace\_build\tmp\codex-geno-author-guide-report.md`: files changed, contradictions found,
what was built/tested (commands + results), windowed commands for the coordinator, proposed commit message.
