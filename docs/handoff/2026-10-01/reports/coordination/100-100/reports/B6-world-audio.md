# B6 — World composition, audio and production feel

Audit lane: read-only static review. No build, no game launch, no console 51701,
no modification of any file other than this report. Nothing here was executed or
heard; every claim marked **PENDING** needs a build or human review.

Sources read: `docs/ROGUELITE-COMPLETION-PLAN.md` (Gate 3 §, Gate 10 §15, §17),
`docs/ROGUELITE-ACCEPTANCE.md`, `docs/FULL-100-100-MODEL-ASSIGNMENT.md`
(Milestone 8), `docs/scripting.md`, `docs/STAGE-FLOOR-SEAMS.md`,
`docs/ROOM-LAYOUT-EXPANSION.md`, `docs/ART-BRIEF-branch-rooms.md`,
`docs/ROGUELITE-WATCHED-RETESTS.md`, plus all 29 Lua modules under
`melee/worktrees/linux/pc/scripts/examples/roguelite/` and
`tools/roguelite/{room_assets.py,prepare.py,certify_rooms.py,live_acceptance.py}`
and the tests named in the assignment.

---

## Summary

Milestone 8 is essentially unstarted. The strongest thing in this lane is the
one that was designed to be provisional and says so out loud: the audio event
map is a complete, validated, honestly-empty *spec* with zero assets and no
playback surface at all.

Three findings dominate everything else.

**Audio cannot be started without native work.** `audio_catalogue.lua` declares
17 events on 3 buses, but every row is `asset = nil` / `provenance =
'unassigned'` and the module is never referenced by `main.lua` (verified: 0
matches). More decisively, the entire documented `gd.*` surface is 126
functions (`docs/scripting.md`) and **none** is audio. There is no
`gd.sound_*`, `gd.music_*`, `gd.voice_*` or bus/mixer call, so no event can be
triggered from Lua today, and §6 (separate controls, focus/device change,
first-use loading) has nothing to configure. The plan's own warning applies
(`ROGUELITE-COMPLETION-PLAN.md:353`): a counter would prove only that a voice
exists — and there are no voices.

**There is no gameplay camera and no bounds verification.** Zero `gd.camera_*`
calls in the roguelite. Blast zones are Final Destination's native ones,
inherited through `gd.stage_isolate` (`docs/scripting.md:340`). `gd.stage_bounds`
exists in the bridge (`melee/worktrees/linux/pc/platform/gw_script.c:5655`) and
is used by the BF example (`pc/scripts/examples/bf_interior_room/scripts/main.lua:87`)
and by the certification fixture, but is **never** called by the game and is not
even documented in `docs/scripting.md`. The authored `camera` field
(`room_recipes.lua:73`, `dungeon.lua:21`) is dead data — `rooms.lua:89-90` does
not copy it into the plan and nothing reads `room.camera`. `ROGUELITE-COMPLETION-PLAN.md:209`
requires "a demonstrated camera/blast-zone envelope" for every admitted layout;
no such demonstration exists. **PENDING** — needs an in-engine bounds/respawn run.

**The transactional transition path is unreachable, and the path that is played
is unmasked.** All 29 recipes are `certified = false` (`room_recipes.lua:82`),
`adapter.lua:48` refuses any uncertified recipe, so `routes.create` fails and
`main.lua:675` falls back to the legacy v1 slice. `RuntimeRooms`' incremental
`begin`/`step`/`commit` is therefore dead in normal play — it is exercised only
by tests that stub `is_certified` to true (`tools/roguelite/test_physical_runtime.py:91`,
`tools/roguelite/test_v2_runtime.py:737-742`), and `tools/roguelite/certify_rooms.py`
explicitly "never sets `recipe.certified`". The played path preloads assets one
model per tick (good) and then spawns the whole room in a single tick with no
mask and no fade, and it tolerates a failed art build with only a `gd.log`.

World composition is a data skeleton: 29 templates, 3 named themes, real
ascent geometry and real doorway prompts — but theme is a single atlas accent
recolour (exactly what `ROGUELITE-COMPLETION-PLAN.md:86` forbids), there is no
lighting, no backdrop/depth layer and no environmental hazard at all. Summaries
are two toast strings; a complete ending screen exists and is dead code. Pacing
is structurally specified and empirically unmeasured, and the route actually
played is 6–9 rooms against a 12–18 target.

---

## Capability table

| System | Status | Evidence |
| --- | --- | --- |
| Theme identity (3 named themes, 29 templates) | **implemented (data)** | `room_catalogue.lua:15-19` (`cobalt`/`frost`/`fire` → Cobalt Halls / Rime Gallery / Ember Court); 27 of 29 templates pin a theme at `room_catalogue.lua:56-64`; theme flows `adapter.lua:75` → `rooms.lua:89` → `rooms.lua:234` → `runtime_rooms.lua:456` |
| Theme as *visual* distinction | **placeholder (recolour only)** | one atlas accent per theme: `tools/roguelite/room_assets.py:24` (`ACCENTS`), `:122-124` (`palette[4] = ACCENTS[theme]`), `:148-150` (writes `rogue_room_palette_<theme>.gxtex`); sidecar just names it, asserted at `tools/roguelite/test_rooms.py:338`. Plan `:86` forbids recolour-only distinction |
| Theme rendered at runtime | **missing** | `rooms.lua:234` stores `s.theme`; no consumer. `main.lua` never reads `node.theme`; no lighting/palette/fog call exists in `gd.*` |
| Background depth | **partial (baked geometry only)** | native rear depth in the kit is asserted at `tools/roguelite/test_rooms.py:144` and relied on at `rooms.lua:174-176`; but the only spawned parts are floor/trim/wall/beam/post/doorway/stairs/balcony/ramp (`rooms.lua:100-127`, `:157-182`) — no backdrop, parallax or sky layer |
| Room lighting / material contrast | **missing** | no light/fog/lamp/ambient call in any of the 29 Lua modules (only unrelated identifiers, e.g. `gene_catalogue.lua:49` `chain_lightning`, `hud_layout.lua:51-53` clamp) |
| Doorway prompts | **implemented, thin** | `main.lua:1180` projects each exit anchor via `gd.project(a.x,a.y+8,0)` and draws the label; door geometry placed at `rooms.lua:117`; labels built at `adapter.lua:110`. No press/state/distance/occupancy affordance |
| Environmental hazards | **missing** | the `zone` archetype is AI spatial denial, not terrain (`encounter_catalogue.lua:11`, `:29-37`); no crusher/fire/spike/void in any recipe. Only hazard is FD's native ring-out. Plan `:355` requires "readable hazard boundaries" |
| Gameplay camera | **missing** | 0 `gd.camera_*` calls in the roguelite. API exists (`docs/scripting.md:384-391`); lab mods and the certification fixture use it only for screenshots (`_build/agents/roguelite-certification/.../main.lua:1914-1923`). Plan `:355` explicitly wants a camera that follows recovery and is not dragged by unused CPUs |
| Camera envelope data | **dead data** | `room_recipes.lua:73` `camera={left=-65,right=65,bottom=-16,top=60}`, same at `dungeon.lua:21` / `dungeon_v1.lua:21`; `rooms.lua:89-90` omits it from the plan; nothing reads `room.camera`; `room_catalogue.lua:108` excludes it from the diversity signature |
| Blast-zone bounds per room | **unverified** | inherited from FD via `gd.stage_isolate` (`docs/scripting.md:340`). Rooms span x∈[-65,65] (`room_recipes.lua:70`) with geometry to y=26, a balcony at y=13, a drop opening at (0,-6). No containment or respawn check. Plan `:209` requires a demonstrated envelope; `docs/ROOM-LAYOUT-EXPANSION.md:220` still lists camera/blast-zone behaviour as pending. **PENDING** |
| `gd.stage_bounds` used | **no** | binding exists at `pc/platform/gw_script.c:5655` (`l_stage_bounds`); used by `pc/scripts/examples/bf_interior_room/scripts/main.lua:87` and the fixture (`_build/agents/roguelite-certification/.../main.lua:1872-1873`); absent from `docs/scripting.md`; 0 uses in the roguelite |
| Unused fighter slots hidden | **missing** | `main.lua:836` always launches `p2='fox/c0/cpu9'`; only `gd.cpu_mode(2,'stand')` is used (`main.lua:524,547,613`, `runtime_campaign.lua:384-385`) — an idle AI, not a hidden actor. No visibility call, no despawn. Matches the known-not-final call-out at `docs/FULL-100-100-MODEL-ASSIGNMENT.md:54` |
| Unused slots parked inside the camera | **missing** | legacy `main.lua:565` `gd.teleport(2, combat and 28 or 58, 2)`; v2 `runtime_campaign.lua:369` `{port=2, x=58, y=2}` for every node without an encounter spec. x=58 sits near FD's right blast zone and inside FD's camera interest |
| Host-stage remnants hidden | **partial** | `gd.stage_isolate(true)` at `main.lua:608`, acquired *after* `Rooms.enter` (`:596`) and the floor/platform adds (`:599-606`), per `docs/scripting.md:340` ("Add your own floor before enabling"). Released only at `on_unload` (`main.lua:1234`); `cleanup()` (`main.lua:~345`) never releases it |
| FD flash window | **exposed** | from `gd.scene_launch{...stage='fd'...}` (`main.lua:836`) to the first `gd.stage_isolate(true)` (`main.lua:608`), the real FD stage is live and visible with both fighters on it under the collection menu opened at `main.lua:847`. Plan `:357`: "Never flash FD or half-built geometry". **PENDING** — needs an on-screen check to size the window |
| Incremental asset loading | **implemented (played path)** | `rooms.lua:14-30` loads one model per call and returns `false` to yield, deliberately "even after the final disk load" (`rooms.lua:27`); `main.lua:886-894` steps once per tick under `gd.input_mask(1,15)`; 10-asset budget at `rooms.lua:23`. Plan instantiates the recipe's own model set (`rooms.lua:16-19`) |
| Room build hitch control | **missing** | `main.lua:596-606` runs `Rooms.enter` (up to `R.max_instances=28`, `rooms.lua:3`) plus every `gd.stage_add_platform` in a single tick; `rooms.lua:211-233` is an unyielding loop. A typical lane is 5 floor + 2 trim + 5 wall + 5 beam + 4 post = 21 spawns; ascent rooms add 5 more. **PENDING** — needs frame-time measurement |
| Half-built room refusal | **missing** | `main.lua:596-597`: a failed `Rooms.enter` only `gd.log`s, then floors are added with `draw=not art` and play proceeds. A room with no room art at all is presented as normal |
| Transactional step/commit ordering | **implemented but unreachable** | `runtime_rooms.lua:256` begin, `:291` step (one asset per call → `'loading'`/`'ready'`), `:313` place, `:375` commit, `:402` rollback, `:355` flush; ordering documented at `:8-18`. Unreachable because all recipes are uncertified (`room_recipes.lua:82`, `adapter.lua:48`, `tools/roguelite/certify_rooms.py` docstring) |
| Played-path ordering vs documented order | **inverted** | documented: load → place → save → commit (`runtime_rooms.lua:8-18`). Played: `enter()` builds art + collision (`main.lua:596-606`), sets `pending_entry` (`:612`), and only on a later tick `complete_entry()` teleports both fighters (`:563-566`) and saves (`:583`) |
| Transition masking / reveal | **missing** | `runtime_campaign.lua` contains 0 occurrences of `reveal|fade|flash|mask|preload`. Legacy loading phase draws only a bare caption and returns before the HUD: `main.lua:1166`. The v2 blocked phase still draws the full scene (`main.lua:1170-1180`) while the destination is mid-`_construct` |
| Both-rooms-live overlap hidden | **missing** | `runtime_rooms.lua:21-26` states the engine has no per-room grouping, so the source stays resident and both rooms' colliders are live during construction; bounded only by `max_total_lines=32` (`:33`, `:281`). Never faded out |
| Warmup hitch | **unmitigated** | nothing warms effects before first use. `main.lua:770-774` plays `gd.fx_play('RogueCinderRelease'|'RogueRimeRelease'|'ThermalShock')` on the first cast, capped at 8 handles with oldest-first eviction (`#fx_handles>=8`). **PENDING** |
| HUD/camera/stage restoration on exit | **partial** | `on_match_end` (`main.lua:1206-1216`) resets room state and releases the HUD but relies on documented auto-restore of the host stage (`docs/scripting.md:340`) instead of owning `gd.stage_isolate(false)`; `on_unload` does own it (`main.lua:1234`). Plan `:357` asks for exactly this check |
| Audio event map | **implemented as spec** | 17 events, 3 buses (`ui`/`sfx`/`music`): `audio_catalogue.lua:7`, `:20-38`; validator `:43-65`; coverage floor of 15 at `:55` |
| Audio assets | **zero, enforced** | every row `asset = nil` (`:12`) and `provenance = 'unassigned'` (`:13`); header states "this module claims no audio exists" (`:3-4`); validator refuses an asset without provenance (`:61-63`); `tools/roguelite/test_audio_catalogue.py` asserts `unassigned == count`, i.e. the test *enforces* the placeholder state |
| Audio wired into the game | **missing** | 0 references to `AudioCatalogue` in `main.lua`; bundled as a lexical global by `tools/roguelite/prepare.py:34` and used only by that test |
| Audio playback API | **does not exist** | enumerated all 126 documented `gd.*` names (`docs/scripting.md`): no sound/music/voice/SFX/bus/mixer call. Only audio-adjacent native hook is Melee's own hitbox `sfx_severity`/`sfx_kind` fields on hitbox reads (`pc/gameworld/script_game.c:1811-1813`, `pc/platform/gw_script.c:1110-1111`), and the roguelite's hit spec never sets them (`main.lua:765`). **PENDING** — needs a native API addition |
| Audio variation | **declared, inert** | `variation` 2 on `menu_focus`, `pickup`, `charge_ready`, `gene_release`, `enemy_tell` (`audio_catalogue.lua:21,26,27,29,32`); 1 (default, `:14`) on the other 12 |
| Audio priority | **boolean only** | `critical` (`:16`) on 4 events; the intent list at `:41` (`menu_refusal`, `charge_ready`, `enemy_tell`, `reaction`), cross-validated at `:56-59`. No numeric priority, ordering or preemption |
| Audio concurrency limiting | **per-event cap only** | `concurrency` (`:15`) is 2 for `menu_focus` and `door_use` (`:21,25`), 1 elsewhere. No voice budget, no per-bus budget, no oldest-voice eviction, no ducking |
| Combat tells over busy music/effects | **cannot be answered** | no mixer, no buses in use. `boss_phase` and `run_complete` are the only `music`-bus rows and are one-shots (`:35,37`). Plan `:351,353` requires the audible-over-spectacle property. **PENDING** — human listening, and nothing to listen to yet |
| Separate audio controls | **missing** | the settings surface declares exactly one item, `REDUCED MOTION` (`runtime_presentation.lua:288-290`), rendered by `menus.lua:135-142` / `:458-464`, which falls back to the literal 'No settings are declared in this build.' when empty. No music/effects/UI volume, no mute, no bus controls |
| Focus / device change / hotplug | **missing** | no focus or device branch in `on_tick`; no audio device event exists to handle |
| First-use audio loading | **N/A (no audio)** | no cold-load or underrun path exists; required at `ROGUELITE-COMPLETION-PLAN.md:353` and `:357`. Native game audio stays vanilla (`pc/platform/gw_mex_graudio.c:87`), so there is no port mixer to hang a bus structure on |
| Death / victory summary | **two toasts** | `main.lua:386-400` `finish()` → `Core.finish`, save, `pause_menu('collection')`, one `Feedback.finish` notification. `feedback.lua:140-152` emits only 'RUN ENDED / Collection retained · Temporary run upgrades lost' or 'RUN COMPLETE / Inherited <id> added · Temporary upgrades excluded' (ttl 360). No stats, no build summary, no next action |
| Ending screen | **implemented but dead** | `menus.lua:152-158` `view_ending` reads `ctx.ending`; `menus.lua:467-471` `draw_ending`; routed at `menus.lua:164` and `:484`. `main.lua` never sets `ctx.ending` and never calls `pause_menu('ending')` (0 matches for `ending` in `main.lua` outside unrelated identifiers) |
| Export | **automatic, not a choice** | `main.lua:388` picks `h.slots.assault or h.slots.traversal or h.slots.guard`, nulled when the collection is full (`:389`). Plan `:359` requires an explicit victory export choice |
| Build consequences | **missing at run scope** | per-stat delta view exists for one reward tick only: `feedback.lua:115-134` `F.reward`, wired at `main.lua:811-814` |
| Run history | **unintegrated** | `run_history.lua:93-107` builds bounded, codec-safe run entries (outcome/export/currency/rewards/mutations/rooms), but `run_history.lua` is absent from `tools/roguelite/prepare.py`'s module list (0 matches) and `RunHistory` appears 0 times in `main.lua`. Only `tools/roguelite/test_inventory_economy.py:30` loads it |
| Extraction framing | **missing** | no `extraction` concept anywhere in the Lua set (0 matches) |
| Recovery copy without engine internals | **implemented** | error pages at `main.lua:396,570,580,610,874,900` explain recovery without leaking handles. The one part of this item already in good shape |
| Encounter pacing structure | **implemented (bounds only)** | `topology.lua:370-371` enforces 12–18 rooms and an 8–12 mandatory spine, matching plan `:83`; `encounter_catalogue.lua:29-39` carries a 1–4 difficulty scalar per encounter |
| Played run length | **below target** | the v1 path that actually runs validates only 6–9 rooms: `dungeon.lua:132` (`count<6 or count>9`), against the plan's 12–18 (`:83`) |
| Detour value | **unmeasured** | reward eligibility per role at `room_catalogue.lua:26-28`, theme pinning at `topology.lua:71`; no detour-value metric or record anywhere |
| Difficulty / AI quality | **unmeasured** | real delayed observation and reaction delay exist (`encounter_behaviors.lua:532-553`, `boss_behaviors.lua:120-171`), and plan `:264` requires measuring techs/spacing against vanilla. No measurement artifact found; `docs/ROGUELITE-WATCHED-RETESTS.md:75-86` records seam/feel observations only |
| Economy bounds | **implemented** | `tools/roguelite/test_economy.py` runs 40 deterministic run cycles asserting collection ≤128 genes, ledger ≤512 entries, failure retention, capacity refusal and export idempotency |
| Economy balance | **unmeasured** | that test's own docstring (lines 5-6): "This is a pure model simulation, not an in-game economy playtest." Bounds are proven; balance is not |

---

## Ranked gaps

**1. Audio has no playback surface and no assets — §5 and §6 are wholly blocked.**
17 declared events, 0 assets, 0 API. `audio_catalogue.lua` is never loaded by the
game and nothing in `gd.*` can make a sound; the only audio-adjacent hook
(`sfx_severity`/`sfx_kind`) is not set by the roguelite's hit spec
(`main.lua:765`). Variation/priority/concurrency exist as three inert fields
(`audio_catalogue.lua:14-16`). Nothing can be reviewed until a native API lands.

**2. No gameplay camera and no bounds verification.**
Zero `gd.camera_*` calls; `gd.stage_bounds` never called though it exists in the
bridge (`gw_script.c:5655`) and is used by the BF example. Blast zones are FD's,
the authored `camera` envelope is dead data (`room_recipes.lua:73`), and the
parked CPU at x=58 sits inside both the blast zone and FD's camera interest —
precisely the failure the plan names at `:355`.

**3. Unused fighter slots are not hidden — standing Fox in every exploration room.**
`main.lua:836` always launches P2; only `cpu_mode 'stand'` is used; P2 is
teleported to x=58 in every non-combat room (`main.lua:565`,
`runtime_campaign.lua:369`). Already documented as not-final at
`docs/FULL-100-100-MODEL-ASSIGNMENT.md:54`. It also feeds gap 2.

**4. Transitions are unmasked, unyielded and built on an unreachable transaction.**
No fade/reveal/mask anywhere. The played path spawns up to 28 model instances in
one tick (`main.lua:596`, `rooms.lua:211-233`). A failed art build is only logged
(`main.lua:597`), so a zero-art room plays on. `RuntimeRooms`' correct
load→place→save→commit ordering exists but is unreachable behind the
uncertified-recipe gate (`room_recipes.lua:82`, `adapter.lua:48`), and the played
order is inverted (art+collision first, placement and save later).

**5. Themes are a one-texel recolour; no lighting, depth layer or hazard.**
`room_assets.py:122-124` swaps a single palette entry per theme. No lighting API,
no backdrop, no environmental hazard in any recipe; the only hazard is FD's
ring-out. This is the explicit prohibition at `ROGUELITE-COMPLETION-PLAN.md:86`.

**6. FD flash window and reliance on documented auto-restore.**
Real FD is visible from `main.lua:836` until the first isolation acquire at
`main.lua:608`; `cleanup()` never releases isolation; `on_match_end` leans on
engine auto-restore rather than owning it. Plan `:357`. **PENDING**.

**7. Run summaries, export choice and run history are unfinished.**
The ending screen is dead code (`menus.lua:152`, `:467`); only two toast strings
ship (`feedback.lua:140-152`); export is automatic (`main.lua:388`); the run
history module is not bundled by `prepare.py`; there is no extraction framing.

**8. Pacing, difficulty, detour value and economy balance are unmeasured.**
Structure exists (`topology.lua:370-371`) but the played route is 6–9 rooms
(`dungeon.lua:132`) against a 12–18 target, and the only economy evidence
explicitly disclaims being a playtest (`tools/roguelite/test_economy.py:5-6`).
Milestone 8's "record iterations and human observations" has no artifact at all.

**9. Doorway prompts are bare labels.**
Real and correctly projected (`main.lua:1180`), but no press prompt, availability
state or distance cue, so traversal affordance is weaker than the rest of the HUD.

---

## Proposed order

Ordered by dependency, then user-visible value. Steps 1 and 2 are independent and
can run in parallel; step 9 needs gameplay to listen to.

1. **Native audio surface (blocks all audio work).** Add a `gd.audio_*` play /
   bus / volume / mute / voice-count surface with per-event priority,
   concurrency and variation consumed directly from `audio_catalogue.lua`, plus
   focus-loss and device-change hooks. Buses (`ui`/`sfx`/`music`), separate
   volume controls, mute, and a ducking rule for the four `critical` tells
   (`audio_catalogue.lua:41`) belong in the same native pass, since §6 has no API
   to configure without it.
2. **Park unused fighter slots and close the FD flash.** Small, self-contained,
   and it removes the standing Fox (`main.lua:565`, `runtime_campaign.lua:369`),
   takes the parked CPU out of FD's camera interest, and lets isolation be
   acquired before anything is drawn and released in `cleanup()`/on exit.
3. **Camera and bounds.** Adopt `gd.stage_bounds`; assert per-room blast-zone
   containment, recovery space and respawn against FD's native zones for all 29
   layouts; implement a follow camera that ignores parked slots. Gates the plan's
   `:209` "demonstrated envelope" and unblocks recipe certification.
4. **Transition mask and build yielding.** Fade to mask on the `pending_room` and
   campaign-loading phases, reveal only at `active`; make a failed `Rooms.enter`
   a hard refusal instead of a log; then measure the single-tick build and, if it
   hitches, move model spawns into a per-tick step.
5. **Real room art past the recolour.** Distinct silhouette/detail per theme, a
   backdrop/depth layer, lighting and material contrast, and at least one authored
   hazard per theme family with readable boundaries.
6. **Finish run summaries.** Feed `ctx.ending`, add run statistics and notable
   build changes, convert export into an explicit victory choice, bundle
   `run_history.lua` through `prepare.py`, and add a next action.
7. **Doorway prompt polish.** Press/state/distance affordance at the exits.
8. **Pacing.** Certify enough recipes for the 12–18 / 8–12 target so the played
   route matches the spec, then run and record human pacing, difficulty, detour
   value and economy iterations with timestamps.
9. **Audio assets, mix and human listening review.** Source original or licensed
   assets with provenance (flip the placeholder rows one at a time), then the mix
   pass and the critical-tell audibility review over real combat with busy music
   and effects — after steps 2–4, so there is gameplay to listen to.

---

## Explicitly PENDING (needs a build or human review — not claimed here)

- Blast-zone containment, recovery space and respawn for all 29 layouts against
  FD's native zones. **PENDING** — in-engine.
- Frame-time of the single-tick room build (up to 28 spawns + platform adds) and
  any warmup hitch on the first `gd.fx_play`. **PENDING** — in-engine.
- On-screen size of the FD window between `main.lua:836` and `main.lua:608`, and
  whether the paused-but-drawn v2 loading phase visibly shows a half-built room.
  **PENDING** — in-engine.
- Camera follow quality, whether parked CPUs drag it, and any host-stage remnant
  visible at gameplay distance. **PENDING** — in-engine + human.
- Combat-tell audibility over music/effects, and whether the mix is balanced.
  **PENDING** — human listening; no audio exists to review.
- Focus-loss / audio-device-change / cold-load behaviour. **PENDING** — no API.
- Whether encounter pacing, difficulty, detour value and run length are fun.
  **PENDING** — human playtest; no tuning artifact exists to review.
