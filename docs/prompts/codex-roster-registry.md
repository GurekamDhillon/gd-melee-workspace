# Parallel packet P5: a roster beyond 94 slots (native registry, phase 3) (2026-10-04)

Rules: `docs/prompts/codex-parallel-rules.md` (read it first). You own: the m-ex slot tables and roster code
(`melee/pc/platform/gw_mex_*` roster/slot files, `gw_uigen.c`, `gw_mods.c` discovery), `tools/port/roster_stress.py`,
`roster_audit.py`. This continues your roster-stress work (`_build/tmp/codex-roster-stress-report.md`: a local mod with
63 extra Sonics fills all 94 slots; 100 is refused; phase 3 had a foundation and a plan).

The owner asked: "can we add 100 sonics to the roster as their own character slots to test expanding well beyond the
limits?" and whether the roster limit is "raisable arbirarily". Carry out phase 3 of your plan: a native registry so the
number of character slots is not bounded by `GW_MEX_SLOT_COUNT 94`, the signed 8-bit character id (127), the CSS icon
cap (128) or the 32 Geno profile cap, without breaking: vanilla and existing m-ex mods, replays and netplay (ids on the
wire and in savestates: say what changes and what is versioned), the character select screen (paging or scrolling for
more icons than fit), results, name tags, records and the memory card. Where a retail structure genuinely cannot widen,
say so and give the real ceiling.
Deliver: the registry, the generator able to produce the 100-Sonic mod (local output only, under the git-ignored
`_build/local-assets/`: never commit game-derived data), an audit tool that reports every remaining fixed-size table,
tests, and a native test plan for a tester (boot with 100 extra slots, select the 1st, 94th, 95th and 163rd, play a
match, save a state, load it).
Report `_build/tmp/codex-roster-registry-report.md`.
