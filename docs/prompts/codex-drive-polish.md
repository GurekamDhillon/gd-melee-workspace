# Packet: make the drive pickup feel good (owner feedback after playing) (2026-10-03)

Workspace `<workspace>`; game checkout `melee/`. Both trees are deliberately dirty: do NOT commit,
reset, stash, revert or reformat. Do NOT run `tools/port/build.sh`, do NOT launch the game. Keep every file compilable.
Other Codex jobs are in `melee/src/melee/gr/`, `pc/gameworld/script_stage_slots*`, `ftcommon.c` and the missions/Envoy Lua
(a crash fix): re-read shared files before editing; make Envoy Lua changes small. No game-derived data in the repositories:
the Sonic Adventure 2 drive models live only in `_build/local-assets/mods/envoy_drives_sa2/` (not yours to edit; report
what its files should change).

## The owner played Envoy and said (verbatim)
"drives as a pick up felt nice. Just no eye/ear candy attached to them yet. They dont float above the ground for one. They
need to be like 2.5x the size. I couldn't tell any rotation on them but that might have just been me"

The drive is a standalone Geno item (`melee/pc/scripts/examples/envoy/items/drive/item.json`, engine side
`melee/pc/platform/gw_script_items.inc` and the Geno item code; report `_build/tmp/codex-geno-items-fix1-report.md`). Its
definition has `"spin": 3` and `"bob": 0`; it rests ON the floor.

## Do
1. **Hover.** A drive floats above the ground: after its pop-up arc it settles to a hover height above the floor under it
   (default about 6 units, in the definition as `hover`) and bobs gently around that height (`bob` amplitude and period),
   following the floor if it is a moving platform, and still falling off edges. The item's collision position for stage
   physics stays on the floor; the VISUAL and the pickup volume are lifted (pickup must still work for a fighter standing
   under it or jumping through it: make the collect volume a capsule from the floor to above the visual). If the item
   system has no hover concept, add it as a general item-definition field, not a drive special case.
2. **Size.** 2.5 times the current size on screen (the tester measured the model at about 38% of Mario's height: make it
   about 95%, i.e. roughly Mario-sized is too big: use 2.5x of 4.55 units = about 11.4 units tall, and state the final
   number), through the definition's visual scale; scale the collect radius and the fallback visual with it.
3. **Rotation the eye can see.** The owner could not tell it was spinning. Find out why from the code: is the spin applied
   to the bound model at all for mesh visuals (the tester saw facing differ between two screenshots, so it turns, but
   slowly or about an axis where a symmetric crystal shows nothing); the crystal and tube are close to rotationally
   symmetric, so a slow vertical spin reads as static. Make it read: a faster spin (state degrees per second), a slight
   tilt of the spin axis so the caps describe a small circle, and a highlight that moves with rotation (see 4).
4. **Eye candy** using what the engine has (`docs/shaders.md`, `docs/scripting.md` effects and post passes; custom
   materials with emission; the effect-only bloom; `gd.fx_*`): an emissive core that glows in the drive's colour and
   actually blooms (the tester found the glow weak: item models with a material sidecar were invisible until a fix landed:
   confirm the material path now works for item visuals and say what emission value reads well), a soft ground glow or
   light pool under it, a few rising sparkles, a brighter pulse and a short trail when it pops out of a defeated enemy, a
   burst of particles toward the collector plus the existing screen pulse on pickup, and a visible blink/fade before it
   expires. Each as data in the item definition or the Envoy mod's tuning table, each switchable, each cheap (state the
   cost; 30 drives on screen must not move the frame time measurably).
5. **Ear candy.** A sound when a drive drops, a pickup sound whose pitch rises with consecutive pickups in quick
   succession, and a distinct sound for the rare white drive. Use the game's existing sound effects through the scripting
   API if it can play them (find the call and pick fitting vanilla sound ids; list the candidates you chose from and why);
   if scripts cannot play a sound today, add the smallest engine call that plays an existing game sound effect by id with
   volume and pitch, offline-safe, and document it. No new audio assets.
6. Per-colour identity beyond tint, cheaply: a different sparkle colour and pickup pitch per stat, and the HUD stat bar that
   receives the points flashes.
7. A demo for the catalogue (`melee/pc/scripts/examples/demos/`): "pickup with juice", showing the same item with and
   without the effects, per the project rule that every capability ships with a single-feature demo.
Tests for the definition fields (hover, scale, collect volume, spin), and offline Lua tests for the pickup streak pitch and
the effect lifecycle (nothing left after collect or expiry). Deliver the Envoy changes as edits if the crash-fix job is not
in those files when you get there; otherwise as a patch under `_build/tmp/` that applies with `git apply --check`.
Report `_build/tmp/codex-drive-polish-report.md`: final numbers (hover height, size, spin rate, emission), the sound ids
used, what changed in the engine, what the asset mod's files should change (for the integrator to apply locally), and what
the owner should look at.
