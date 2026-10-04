# Packet E2 follow-up: merge the drive polish into Envoy (2026-10-03)

Same rules (Lua/Python/JSON/Markdown only, your mod and tests, no C, no build, no game launch, no commits).
While you built slices 2-4, another job delivered the drive pickup polish as a patch rather than editing your files:
`_build/tmp/codex-drive-polish-envoy.patch` (report `_build/tmp/codex-drive-polish-report.md`: hover 6 units, 2.5x size,
tilted visible spin, effects, pickup sounds with rising pitch on quick consecutive pickups, a distinct white-drive sound,
HUD stat-bar flash, an A/B demo). It no longer applies to the current Envoy source (`scripts/app.lua` and the generated
`scripts/main.lua` reject). Merge its intent into the current source by hand: every behaviour in that patch must end up in
the mod, wired to the current code (the item definition `items/drive/item.json` changes, the pickup streak pitch, the
per-colour identity, the HUD flash, the effect lifecycle with nothing left after collect or expiry), each switchable in the
tuning table, guarded for missing engine calls. Never edit the generated bundle by hand: change the sources and regenerate
with `tools/port/envoy_bundle.py`. Carry its tests across. Also note for your slices report: an engine request you raised
(per-instance collection radius for native drives, so Reach can widen pickup range) is being added by the integrator's
next engine packet: keep the Reach radius behind one small interface, guarded for absence.
Reply with what was merged, file:line, and the test counts.
