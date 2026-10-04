# SuperTime Envoy controller fixes implementation plan

> For agentic workers: use subagent-driven-development with one writer per file.

Goal: address the first controller review and prepare a fresh normal-speed acceptance build.
Architecture: retain existing Lua mode and native scene loader, preserve save transactions, keep generated admission tied to certification. Menu, room and generator changes have separate writers; one worker owns main.lua integration.
Tech stack: Lua 5.4, Python regression harness, native Windows engine.

Scope approved in chat, updated 2026-10-02: clearer labels/primary actions/controller prompts; no elevated platform ledges; higher platforms; 2x every authored grid cell and stage asset, with fighter mobility unchanged. This supersedes the initial horizontal-width interpretation. New rooms use five 52-unit bays, grid26 and unit13; new editor placement uses scale2/grid13. Saved legacy/prototype geometry is preserved. Exploration must have no parked fighter CPU; combat uses explicit opponents. The approved maze uses seeded randomized DFS with extra loops, reciprocal compass doorways and real collision blockers. Native recipes remain uncertified pending controller traversal.

- [x] Investigate live installed legacy route, menu input contracts, platform geometry and FX draw evidence.
- [x] Menu worker: real-Lua failing regression, readable labels/default Start or Resume, truthful B footer and clearer combat tree.
- [x] Platform worker: unchanged widths, side y18 and center y36, no elevated ledges, floor260, ten structural bays, adjusted sockets and regression fixtures.
- [x] Generation worker: certified-only per-call eligibility, actionable missing-role diagnostics and deterministic regressions; never mark untested recipes certified.
- [x] Integration worker: solo exploration/collection and explicit combat-scene handover, preserved checkpoint/cleanup; main bounds apply/restore and authored spawn positions; main pcall reason, fallback identity; collection/rest Back lifecycle.
- [x] Root: rename native menu/installed manifest, add opt-in rendering probe, review patches, full real-Lua regression suite, game build/bridge ABI audit and native216 suite.
- [x] Root: prepare fresh isolated mod, launch only after replacing this session's owned run safely, confirm mounted mod and controller, record human observations independently.

Review focus: absent P2 must not stall scene readiness; scene handover must preserve saved player lives/loadout; failed cleanup must not lose owned geometry; widened room camera and blast zones must restore; all actual geometry hashes need new traversal certification. Do not commit generated bridge/assets, stage unrelated Slippi edits, or claim full v2 maze or renderer fix from stub results.

Camera follow-up: legacy bounds lowered18 preserving72-unit height;255 real-Lua tests pass; installed script refreshed for nextlaunch. Native geometry occlusion confirmed for shield/Cinder; renderer remedy and maze remain open.


## Final verification amendment - 2026-10-02

- [x] Preserve historical dungeon_v1 bytes; distinguish widened prototype and explicit generator2/3 manifests; protect future saves.
- [x] Implement seeded 4x3 DFS maze plus two loops, real blocker/cap collision and reciprocal compass sockets; analytical screening only.
- [x] Correct 2x authored-cell/asset scaling and editor defaults; no platform ledge grabs.
- [x] Optimize codec/checksum without changing serialized bytes or weakening validation; remove duplicate terminal arrival save.
- [x] Full real-Lua suite:265 tests OK, skipped1. Native maze final2 passes real wall blocking, solo/combat/rest actor lifecycle, retained damage/id/seed/lives, and successful exit.
- [x] Native renderer shield/Cinder now visibly coexist with room art through explicit background bucket; normal depth writes, authored Z0.
- [x] Fix and verify Falco beam overdraw: draw backdrop before fighter/item callbacks, scope native fog and viewport; matched beam/shield/Cinder remain visible with art.
- [x] Preserve reciprocal arrival socket across deferred solo/combat handovers; explicit North/South regression and exact native arrival coordinates pass.
- [x] Final Lua265 OK/skip1; native216/216 on ACE and vanilla; native maze sockets PASS; fresh controller bundle and launch entry prepared.

Human acceptance still required: jump reachability and room seams, camera comfort, controller menus and effect fidelity. The four earlier persistence/Restore/history defects and Sora showcase work remain open.
