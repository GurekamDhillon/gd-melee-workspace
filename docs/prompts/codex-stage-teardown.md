# Parallel packet P3: full retail stage lifecycle on a mid-match stage switch (2026-10-04)

Rules: `docs/prompts/codex-parallel-rules.md` (read it first). You own: `melee/src/melee/gr/` (under `TARGET_PC` only),
`melee/pc/gameworld/script_stage_slot*`, `script_stage_host.inc`, `script_stage_music.inc`, and the
`stage_switch_demo` example. This continues your stage-switch work (fix1-fix5).

Fix5 repaired the transition hang but left the main requirement undone, in your own words: "full vanilla stage
teardown/reinitialization is unimplemented". The owner's standing rule: "ideallistically I want stages to look and feel
like they are vanilla, aside from the transition mid-match"; a switched-to stage must run its full retail
initialisation, and the end state may not be a partial stand-in. Research already done:
`_research/stage-switch-full-retail-lifecycle-2026-10-03.md`, `_research/seamless-stage-switch-2026-10-03.md`.

Build:
1. On a switch, the outgoing stage is torn down the way retail does at match end (its gobjs, map collision, hazards,
   items owned by the stage, cameras bounds, blast zones, lighting, fog, particles, music stream, any per-stage static
   state), and the incoming stage runs its real `grXxx` init, callbacks and per-frame update exactly as in a normal
   match on that stage, from preloaded data so the switch itself stays loading-free. No stage-specific special cases in
   the switcher beyond what retail itself has; remove the Yoshi's Story and Fountain "native controller" stand-ins once
   the real init runs (keep them only behind a fallback switch).
2. Fighters, items in hands, projectiles in flight and the camera survive the switch sensibly: define and document the
   rule for each (carried, repositioned onto the new stage's spawn/respawn points, or removed), with ledges and blast
   zones valid on the first frame.
3. A table in the report of every retail stage: full lifecycle supported / supported with a stated difference /
   refused, and why. Stages with unusual lifecycles (transforming, scrolling, target/1P stages) may be refused for now.
4. Snapshot and rewind across a switch: state what is covered and what is refused, with a fixture.
5. Tests in the suite pattern; an acceptance checklist for a tester who will compare each supported stage SIDE BY SIDE
   with a normal match (Randall's 1,200-frame lap on Yoshi's Story, Fountain's platform cycle, Whispy on Dream Land,
   Shy Guys, Pokemon Stadium transformations if supported, ledges, blast zones, music).
Report `_build/tmp/codex-stage-teardown-report.md`.
