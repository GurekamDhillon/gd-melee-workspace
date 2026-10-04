# Packet P follow-up: standalone Geno items after their first run in the game (2026-10-03)

Same rules (no commits/reset, no build, no game launch, keep files compilable; no game-derived data in the repos). Another
Codex job is editing `melee/pc/geno/` and the LAB mod for three guide gaps, one is editing `pc/gameworld/script_stage_slots*`,
and Lua-only jobs are in the missions and demo mods: re-read shared files before editing.

Verified in the game on the stamped build (vanilla disc, LAB): `gd.item_spawn("drive", ...)` for five colours spawns, pops
up, falls and RESTS on the stage floor, a solid script platform and a pass-through platform; spins about the vertical axis;
is collected on touch exactly once by the permitted port with the payload in `on_item_collect`; a CPU does not collect; two
fighters on the same frame give one collect; appears in `gd.items()` (`kind=4608 name=drive layer=geno`); 60 items with no
cap problem; expiry and off-stage destruction fire `on_item_expire`; savestate, rewind across a collect, and `rewind_test`
with 0 differing bytes; the fallback visual; `gd.data_exists`, `nil,"missing"`, `gd.fighter_mod` read-back, one defeat
event for a Koopa in its shell. Evidence: `_build/audit-20261003/drive-assets/` (`patches/`, `shots2/`, logs
`_build/runs/drv2-*`).

Fix at the root, each with a test:
1. **An item whose model has a `.material.json` is invisible**: log `invalid relative shader path:` and the draw is skipped.
   `relative_path` (`melee/pc/platform/gw_shader_models.inc` ~17-21) compares a canonical `\\?\C:\...` mesh path with a plain
   `C:\...` root that `gw_script_items.inc` ~106-109 builds from `gw_Mods_Dir()` + mod id, so `lexically_relative` returns
   empty. Proposed: `patches/engine-item-material-root.diff` (strip the prefix from both). Fix it where paths are
   normalised so every caller agrees, and add a fixture with a prefixed and an unprefixed path.
2. **The first `gd.item_spawn` of a definition can exceed the 50 ms Lua budget and orphan an item**: the call raised
   "ran too long" but the native item already existed; the script never got its handle and the item later fired
   `on_item_expire`. `gs_item_visual_prepare` (`gw_script_items.inc` ~114-125) loads mesh, atlas, glow and material
   synchronously inside the Lua call. Preload each registered item's visuals when the definition is registered (spread
   over frames, off the Lua budget), never create the native item before everything that can fail has succeeded, and make
   spawn atomic: handle returned or nothing created. Notes: `patches/engine-item-first-spawn-budget.txt`.
3. **`on_item_collect` / `on_item_expire` fire for things that are not items a script cares about**: a Fox laser produced
   `collect name=vanilla:74 port=2`, shell items produced `expire name=vanilla:211 reason=destroyed`. Fighter articles and
   projectiles must not produce these events by default; emit for standalone Geno items always, and for vanilla/m-ex items
   only when a script opts in (a filter argument or a separate event), documented.
4. **Vanilla rows in `gd.items()` show a payload nobody set** (`payload=red/1` on a capsule): payload is per Geno item only.
5. **`gd.cpu_mode(port,"stand")` called on the first frame of a match does not stick** (the CPU walked off and fought);
   called again at frame 2 or 30 it holds. Find the ordering (the CPU's own initialisation overwriting the mode after the
   script's first frame) and make the selected mode survive it, or refuse with a clear message until the fighter is ready.
6. **Vanilla item refusals share one message** whatever the cause (kind 34, 35, 200, `vanilla:3` all identical, and that run
   had a full pool): each refusal names its real reason (unsupported kind, pool full, unsafe kind).
7. **Bob and blink**: the drive definition has `"bob": 0` and the tester could not catch a blink frame: confirm in code that
   blink-before-expiry toggles visibility, give the drive a small bob by default, and log one line when blink starts.
8. **The Envoy patch you delivered no longer applies** (the Envoy source moved on: it already has model hooks and a
   `mission_events` module; the failed `drives.lua` hunk left `self.native` nil and `envoy start` refused with
   `drives.lua:81: bad argument #1 to 'for iterator'`). The tester rebased it by hand and it ran:
   `patches/envoy_drives.lua.rebased.diff`, `envoy_app.lua.rebased.diff`, `envoy_bundle.py.diff`. Review those against the
   CURRENT Envoy source and deliver one clean, tested patch set under `_build/tmp/` that the integrator can apply with
   `git apply --check` passing (do not edit the Envoy mod yourself), plus the filter from item 3 so Envoy credits only
   `name == "drive"`.
Report `_build/tmp/codex-geno-items-fix1-report.md`: causes in a few lines each, file:line, tests, and a re-test plan.
