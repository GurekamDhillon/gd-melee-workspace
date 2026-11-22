# Packet E1 follow-up: make Envoy slice 1 real against the engine that now exists (2026-10-03)

Same rules as before (Lua/Python only, your mod and tests, no C, no build, no game launch, no commits). The mission runtime
(`melee/pc/scripts/examples/missions/`) has just been changed again by its own job (retries, CPU parking, labels, a camera
module): read `_build/tmp/codex-mission-runtime-fix2-report.md` and re-bundle against it (your bundled copy was stale and one
integration test failed).

The engine capabilities you requested now exist and are verified in the game (read the reports for exact signatures and
measured behaviour): `_build/tmp/codex-engine-batch2-report.md` and `..._fix1-report.md`
- `gd.fighter_mod(port, {damage_dealt=, damage_taken=, run_speed=, air_speed=, shield_max=})`: exact ratios measured;
  survives KO/respawn; clears to exact base; note that damage modifiers also scale knockback.
- `gd.fighter_bench` / `gd.fighter_call` / `gd.fighter_benched`: bench is invisible, intangible, AI-frozen, camera-excluded.
- `gd.cpu_mode(port,"stand"|"fight")`: `cpu0` does NOT mean idle; an idle CPU must be put in "stand".
- Contact traces and `gd.wait_until` (`_build/tmp/codex-contact-events-report.md`) for your test commands.
- Shaders (`docs/shaders.md`): `gd.fighter_shader`, `gd.post_*` exist; use them only as item 4 says.

Do:
1. Wire the companion's stat levels to `gd.fighter_mod` through your one tuning table (Power -> damage_dealt, Speed ->
   run_speed + air_speed, Guard -> damage_taken + shield_max, Reach stays pickup radius/drop rate), small capped steps, applied
   at run start and whenever a level changes, cleared at run end. Because damage scales knockback too, keep Power's cap
   modest and say the number.
2. The boss: bench the boss fighter at run start and call it when the player enters the boss room; keep every other CPU in
   "stand" unless it is the active boss ("fight").
3. **A concrete menu system before any art** (owner: "probably want to do a concrete menu system build before we build any
   art"). Build Envoy's whole menu flow as working, navigable screens with the existing kit components (`gd.kit`, see
   `docs/scripting.md`; laid out with `gd.safe_area`; the old roguelite re-implemented lists and buttons instead of using the
   kit: do not repeat that) and NO new art: plain kit panels, lists, text and the existing icons only. Screens and flow:
   title/profile -> hub menu (stand-in for the walkable hub until slice 2: Start Run, Fighter, Companion, Records, Quit) ->
   fighter select (list) -> run setup -> in-run HUD panel and pause menu (Resume, Companion, Abandon Run with confirm) ->
   run results (drives gained per stat, levels gained, boss result) -> back to hub; Companion screen (four stats with grade,
   level, points bar; age; type; DNA shown plainly as two alleles per trait); later-slice screens present but marked
   unavailable (Nest/Breeding). One menu-state module, pure and tested (navigation, back, confirm, disabled entries, wrap,
   focus memory), separate from drawing; controller only (A/B/START/D-pad/stick; C-stick untouched); every screen fits 4:3,
   16:9 and wider. Write a short `MENUS.md` in the mod listing each screen, its entries and what art it will eventually need,
   so art is commissioned against a fixed, working flow.
4. Colour and shaders, minimal and optional (owner asked whether the shader system is used to colour characters: not yet):
   add one tasteful, cheap use behind a setting in the tuning table, default on: tint the player's fighter subtly by the
   companion's dominant stat using `gd.fighter_shader` (a small rim/tint sample shader in the mod's `shaders/`), cleared at
   run end; and a brief full-screen grade pulse on drive pickup using `gd.post_add` with auto-removal. Both must be skipped
   silently if the shader API reports an error.
5. Console test commands updated; a native test plan for the integrator that uses `gd.wait_until` and the fly commands.
Report: `_build/tmp/codex-envoy-slice1-fix1-report.md`.

## CORRECTION to item 4 (owner, 2026-10-03): "I meant from the old envoy systems. We would recolour the player models based on genes"
The owner's question was about the OLD Envoy's fighter recolouring, which is a working engine system and is wanted in the new
Envoy. Replace item 4's "tint by dominant stat with `gd.fighter_shader`" with this:
- The existing system: `gd.dobj_tint` and the per-draw part controls (read `docs/scripting.md` on `dobj`/part tinting, the
  game side `melee/pc/gameworld/script_parts.inc` (`ScriptParts_Tint`: one recolourable surface per `HSD_DObj` draw, the tint
  appended as one TEV K-colour stage that preserves texture, shading, alpha and cutouts; `recolor_capability =
  "independent_draw_override"`), the model-parts tooling `tools/model_parts/`, and the old audit of how it was used and where it
  fell short: `docs/handoff/2026-10-01/reports/coordination/100-100/reports/B5-region-genetics.md` (flat single-colour static
  tints; only 2 of 6 gene families had a colour; colour was the only cue; the stale-entry risk above a reused index).
  Read but do not reuse or edit the old code in `melee/pc/scripts/examples/roguelite/` and `tools/roguelite/`.
- New design, driven by the companion's DNA (the Chao rules already in `genetics.lua`): the companion's expressed colour
  traits (colour, two-tone, shiny) and its type recolour the PLAYER's fighter: a `recolour.lua` module, pure mapping + thin
  engine glue, that maps traits to a small palette and applies it per body region with `gd.dobj_tint` (regions from the
  fighter's draw list: resolve region->draws through whatever the model-parts data provides; if a fighter has no region map,
  fall back to a whole-model tint and say so). Two-tone = two regions' colours; shiny = a shader sheen via
  `gd.fighter_shader` layered on top ONLY if both systems compose (state from the code whether a surface shader and a dobj
  tint can be active together; if not, shiny uses a brighter palette and the report says why). Applied at run start, after
  every respawn and costume/model reload, cleared exactly at run end and on unload (the old system leaked stale entries:
  prove cleanup with a test). A preview of the recolour belongs on the Companion screen of the menu system (as a palette
  swatch row for now: no fighter render in menus yet).
- Keep the brief full-screen grade pulse on drive pickup from the original item 4.
- Tests for the trait->palette mapping (deterministic), region resolution fallback, apply/clear symmetry.
