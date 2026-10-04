# Packet A: integrator decisions after the stop (2026-10-03)

You were right to stop. These decisions replace the conflicting parts of `docs/prompts/codex-mission-engine.md`; everything else
in that packet stands (files you own, rules, acceptance, report). Now implement.

1. **E2 lifetime policy: do NOT free assets mid-match.** Keep today's lifetime exactly: native mesh/atlas bytes stay pinned until
   scene reset, retained `gd.model_load` handles keep working, the snapshot ledger is untouched, and the existing ownership
   regression (`gw_script_model_tests.inc`, bytes remain after the last owner retires) must still pass unchanged.
   What changes: (a) asset identity is path PLUS a content stamp covering every file the asset is built from (mesh, collision
   sidecar, atlas, optional glow): a size + modification-time stamp is acceptable, a content hash is better if cheap; an unchanged
   file reuses the existing asset, a changed file at the same path loads as a NEW asset in a new slot while existing instances
   keep the old one; (b) raise the asset cap from 32 to 128 if the memory pools allow, otherwise to the largest safe value, and
   say what bounds it; (c) when the cache is full, the error must say so plainly (it is the signal to restart the match).
   Savestate/rewind behaviour with reloaded assets is out of scope: do not change it, note it in the report.
2. **`gd.stage_hide(bool)`**: implement it as a thin, documented wrapper over the existing `gd.stage_isolate` mechanism (do not
   duplicate game-side code and do not edit files outside your list). It returns `true` on success, `false, err` on a host
   stage the isolate code does not support. Document that only the hosts isolate already supports are covered (Final Destination
   today). `gd.stage_isolate` itself stays as it is.
3. **Per-mesh collision lines**: `melee/pc/platform/gw_model_format.h` is added to the files you own for this one purpose. Raise
   the per-mesh limit to 64 only if the parser constant, the game-side `SCRIPT_MESH_LINES` and the host stage pool reservation
   can all take it; if any cannot, leave all of them at 32 and explain in the report. No half-raised limit.
4. **`gd.fly_target` range**: raise the check to +/-49,000. The research run stood and ran a fighter at 49,850 and the game
   asserts at 50,000, so 49,000 is the intended ceiling; note camera/ECB behaviour as unverified.
5. **`gd.player` fields**: `jumps_left` already exists, leave it. Add `on_floor`, `floor_y`, `floor_passthrough`, `wall`,
   `ceiling`, `ledge` as specified, with fake-fighter tests where the existing tests use one.
6. **Path containment**: string checks plus resolving the final path and confirming it is still inside the mod folder (so a
   junction or reparse point cannot escape). Nested script entries resolve to the mod's root folder, not the script's folder.
7. Docs: correct the instance/line limits in `docs/scripting.md` to what the code enforces, stated as the code states them.

Write the report file again at the end (`_build/tmp/codex-mission-engine-report.md`), replacing the stop report, with the
implemented signatures, file:line for every new function, and the native test plan.
