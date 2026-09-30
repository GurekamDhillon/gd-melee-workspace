# TBD: genes and connected routes prototype

Implementation handoff: [full completion and polish plan](../../docs/ROGUELITE-COMPLETION-PLAN.md).
It covers the remaining game, real dungeon generation, effects lab, platform delivery
and acceptance requirements; this README describes the current prototype.

This is an offline, unreleased vertical slice of
[EFFECTS-LAB-PLAN.md](../../docs/EFFECTS-LAB-PLAN.md). It combines a persistent
gene collection/breeding system with disposable run upgrades, a seeded bounded
route, native fighter combat, and a recursive three-way command menu.

The runtime is authored in
`melee/worktrees/linux/pc/scripts/examples/roguelite/`. `prepare.py` bundles Core,
Dungeon, Commands, Roster, Bindings, Visuals, Feedback, Menus, Rooms, EnemyGenes
and TechAI as lexical Lua modules ahead of `main.lua`; the sandbox does not need
`require`. Installed script ID is `roguelite/main`, which
enables the native **TBD** menu entry when the mod is loaded.

## Install and review

Run from the `gdm` repository root, using an existing native build and your own
local NTSC 1.02 disc image. No game content is acquired or modified by the installer.

```sh
python3 tools/roguelite/prepare.py --app-dir _build/agents/linux --enable
MELEE_TURBO=0 MELEE_FPS=60 _build/agents/linux/melee --realtime --iso /path/to/melee.iso
```

Choose **TBD** in the game's main menu, then **Start a run** in the collection.
`--demo` on preparation automatically launches the collection for review; it
does not autoplay combat or manufacture victory. Detailed controller, sound and
readability checks must run at normal game speed, not turbo. Install into the
same application directory you launch. The generic Linux smoke wrapper creates
a fresh sandbox without copying this mod, so it is not a substitute for this
installed-mod review.

Preparation without `--enable` leaves the enabled-mod list unchanged.
`--enable` backs up its original contents once and isolates the list to
`roguelite`, preventing another prototype's autolaunch from taking over the
scene. Close the game before changing the installation. Restore the original list:

```sh
python3 tools/roguelite/prepare.py --app-dir _build/agents/linux --restore
```

The manifest marks the mod gameplay-enabled and rollback-unsafe. It is offline
only. A neutral virtual P4 prevents the disconnected-controller popup; the
runtime does not take ownership of the player's P1 pad.
Scene launch explicitly uses `items='off'`: numeric zero is the lowest spawn
frequency, not the no-items rule. The native scene suite checks the disabled
frequency sentinel and the normal gameplay spawner path.

## Current playable rules

- The collection starts with contrasting Cinder individuals and a Rime. Choose
  a Cinder starter, breed compatible inherited parents and optionally lock its
  potency. A run copies collection genes into independent individuals.
- Collection, breeding, build, reward and rest screens use the native kit UI,
  with mouse or D-pad/A navigation. Comparisons resolve the actual gene stats,
  modifiers and caps. The mannequin depicts logical Assault/Guard/Traversal
  groups; it does not claim to reproduce the selected fighter's geometry.
- The collection picker offers all 26 stock selections, including separate
  Zelda and Sheik entries, and their native costume counts. The selection applies
  to the next fresh run; resume uses that run's saved fighter and costume.
  Ice Climbers use the native Popo/Nana pairing, with gene placement on the primary
  fighter. Selection support does not establish tint coverage for every costume.
- An eight-room seeded graph includes entry, traversal, two alternative arenas
  that merge, rest, another traversal, champion and exit. Each active room uses
  authored added platforms inside an isolated native host's camera/blast zones.
  `gd.stage_isolate(true)` disables the host's native scenery and collision;
  each room supplies its own solid main floor and elevated platforms. The rebuilt
  BF modular kit provides floors, walls, beams, posts, trim and doorway frames.
  Follow the kit's [placement contract](../../melee/worktrees/linux/pc/scripts/examples/bf_interior_room/README.md#placement-contract):
  a doorway replaces a full wall bay, at the same scale and depth as its neighbours.
  Decorative meshes add no collision. An asset failure retains visible debug floors;
  missing native isolation stops entry with an error instead of playing on FD.
  These are bounded room transitions, not a seamless generated world.
- Walk to a labelled exit at the left or right end of the lane and press
  **D-pad Down** at command root. Traversal enemies or fighter encounters can
  prevent departure until cleared. Room transitions remove owned geometry and
  enemies before constructing the next room.
- A level-9 Fox CPU fights in arenas; stand mode parks it safely during
  exploration. One CPU stock clears an arena; two clear the champion. The
  runtime tracks three run lives independently of the native 99-stock scene.
  An opt-in original native input policy assists landing-cancel and hitstun
  ground-tech attempts (skill 2 in arenas, 3 in the champion room). Neutral,
  attacks and recovery still come from the existing CPU. Native Adventure
  Goomba and Redead actors supply the two traversal encounters.
- Direct fighter hits charge Assault, native shieldstun charges Guard, and
  sustained ground movement charges Traversal. Placement changes an authored
  action/trigger, rather than merely recolouring a body part. Commands preflight
  charge, facing and reach; native hit/impulse refusal restores charge.
- D-pad **Left / Right / Down** choose the three branches at every command
  depth. **Up** returns one level; a fresh Up at root retains native taunt.
  Holding Up after returning to root remains consumed until release. Navigation
  does not pause neutral; detailed collection/reward/rest menus pause combat.
- Rewards preview effective potency/gain changes. Rest permits placement changes,
  Cinder fusion and saving/leaving. Fusion consumes compatible run parents and
  retains ancestry. Successful completion exports an inherited base individual
  while excluding temporary run upgrades; a full collection skips export.
  Failure retains the prior collection and discards the ended run's improvements.
- A compact HUD shows lives, damage, supplies and resolved slot charge/readiness,
  with shared feedback for doors, releases, rewards and refusals. The script hides
  the native status HUD while active and restores it on cleanup.

The first ability/effect set is intentionally small: Cinder and Rime, their slot
variants, and an automatic Thermal Shock when fire consumes a Rime mark. Fighter
CPU genes use the same Core resolver, charge and costs with bounded encounter
modifiers. Script-owned Goomba and Redead actors also have Core Assault hosts,
charge from native attack contacts, telegraph a ready release for 24 run frames,
and use bounded native damage calls. Refused releases retain their charge.
Their appearances and ordinary movement AI remain native Adventure behavior.
Enemy-owned genes are excluded from player inventory, fusion and successful-run
export. Natural fighter hits on these actors charge player Assault through the
owner-scoped `on_enemy_hit` event, including a queued killing blow.

The original technical assist supports primary Fox/Falco fight CPUs, observes
real floor collision and native landing/tech eligibility, and inserts delayed
input pulses without changing fighter physics, actions or lag. Skills 1/2/3 use
6/4/2-frame observation delays and seeded 60/80/95% opportunity acceptance;
these percentages are not measured cancel/tech success rates. Diagnostics count
input attempts, not successful techniques. Unsupported actors and refused
configuration retain the native CPU baseline. This is a narrow policy, not a
20XX, UnclePunch, Training Mode, SmashBot or Slippi AI port. The primary-source
audit is in [_research/roguelite-ai-2026-09-30.md](../../_research/roguelite-ai-2026-09-30.md).

## Persistence and assets

For a rotating art/gameplay presentation, run `python3 tools/roguelite/showcase.py`
and open `_build/roguelite-showcase/index.html`. Arrow keys browse, Space toggles
the tour, and F enters fullscreen. Art chapters link to their interactive studies;
the gameplay chapter includes `cinder.mp4` when that recording is present.

Data lives in `<app-dir>/scripts-data/roguelite_main/`. Alternating
`checkpoint-a.txt` / `checkpoint-b.txt` contain complete profile/run pairs,
generation, bounded lengths, the selected fighter and the active run's fighter.
The `TBD2` envelope keeps these choices in the same alternating checkpoint;
legacy `TBD1` checkpoints default to Falco costume 0. Saves read back and validate
the written pair; load chooses the highest valid generation. A torn newest slot can fall back to
the previous complete slot. Invalid files are preserved; two invalid slots block
normal play rather than silently overwriting the collection. This is bounded
checkpoint recovery, not a guarantee of durable filesystem transactions.
Run completion also restores its in-memory profile/run snapshot if saving fails,
so an uncommitted export can be retried without duplicating collection changes.

`run.world_seed` is immutable for route reconstruction; acquisition/fusion uses
a separate mutable seed. Resuming restarts the current encounter rather than
restoring exact fighter physics, damage, enemy positions or an in-progress stock.
Only the reviewed catalogue/version is supported; the checkpoint is not a
general arbitrary-stage save format.

The installer copies original primary-authored glyphs and builds existing reviewed
fire/ice recipes plus release-timed variants. Native kit metadata is
`ui/roguelite_ui.json`; the engine discovers `*_ui.json`, not `kit.json`.
The asset authoring/rebuild paths, for separate primary art work, are:

```sh
python3 menu/pipeline/roguelite_art.py
python3 menu/pipeline/roguelite_build_art.py
python3 menu/pipeline/roguelite_feedback_art.py
python3 tools/roguelite/build_room_kit.py
python3 melee/worktrees/linux/pc/tools/png2gx.py --layout menu/out_roguelite/manifest.json --outdir menu/out_roguelite/gx
```

The vector rebuild requires `rsvg-convert`; conversion requires Pillow.
The modular-room rebuild requires Blender and regenerates the original
`pc/assets_src/bf_interior` kit into `menu/out_roguelite/room-kit/`, with a hashed
manifest. It exports 21 meshes and shared opaque/glass colour/glow atlases.
Installation copies the six opaque room models and their shared atlases;
normal installation uses the supplied exports and does not require Blender.
The [feedback art review](../../menu/out_roguelite/feedback.html) shows the
primary-authored door, charge, release and reward vocabulary; its preview does
not establish that each piece has been exercised in the native renderer.
`prepare.py` builds FX from the reviewed original masks in `menu/out_effects_study`
and invokes `fx_assets.py` for immediate-release timing. It does not invent new
art. `room_assets.py` builds original geometry into room DATs during preparation;
no disc-derived model assets are committed.

`build_bindings.py` generates conservative tint metadata from the local measured
model-parts reports. There are 28 measured fighter/costume entries: all 26 stock
costume-0 selections, plus Pikachu and Jigglypuff costume 1. Five entries have
36 pose/angle captures; the other 23 have four smoke captures. A report's existence
does not establish comprehensive motion coverage or that every gene group has
visible geometry. Runtime binding requires the exact geometry signature, costume,
fighter kind and current draw selectors. Unknown costumes/signatures remain
untinted and report their coverage limit; the gene rules still work. Ambiguous,
face/eye and transparent overlay geometry is excluded. Reviewed hand-mounted
attachments share Assault rather than creating equipment slots. Transient item
models and the Ice Climbers partner remain unbound. Topology is refreshed on
action/model changes and periodically to avoid retaining stale draw selectors.
Texture-preserving tint was observed on Falco after the native texture-stage fix.
Pre-existing magenta stage textures
are a separate renderer issue and are not claimed fixed by this prototype.

## Validation and outstanding work

```sh
python3 -m unittest discover -s tools/roguelite -p 'test_*.py' -v
MELEE_MODS=0 MELEE_TEST_FILTER=script _build/agents/linux/melee --test --iso /path/to/melee.iso
```

The discovery command includes every roguelite test module, including the newer
menus, roster/bindings, feedback, rooms, enemy genes, AI adapter and integration
edges. Tests execute actual Lua with engine stubs where native calls are needed;
the binding generator also checks repeatability and conservative rejection.
Dungeon checks cover 300 reproducible seeds and invalid graphs, gates, budgets
and mobility cases. Runtime checks use engine
stubs and cover collection/breeding/locks, door precedence, native stock events,
commands, hit refusal, shield charge, reward/fusion/export, failure and checkpoint
recovery. They are not a substitute for in-engine collision, physics or controller
play. The v8 Linux native script run (`/tmp/roguelite-native-v8-tests.log`) passed
31 checks with zero failures, out of 209 registered tests. It includes the CPU
technical policy/API, `draw=false` stage options, enemy combat/event API and
unmodified-vanilla regression checks. These policy, argument, ownership and
lifecycle checks do not prove successful natural gameplay techniques, complete
roster rendering or a balanced human playthrough.

Earlier slice evidence, before the newest roster, custom-enemy and technical-assist
integration: normal-speed native observations included main-menu TBD visibility/click,
collection start, connected neutral P4, holding Left descends only one level,
Up backs out without leaking a held press into taunt, and a fresh Up at root
performs native `AppealSR`. A Goomba can leave the stage without a defeat hook;
its stale handle originally blocked an exit.
Native alive polling subsequently unlocked the trail after a Goomba naturally
vanished, and the real Down door input entered arena A. This test used a fixture
teleport to approach the world door; it did not inject a defeat or remove the actor.
An ordinary X jump landed Falco on an added platform at y=12, grounded. Against
a stand-CPU position fixture, three actual jab collisions earned charge 0→3;
the three Left choices released Cinder, consumed charge 3→0 and changed Fox's
damage 36→46%. Native FX inventory reported `RogueCinderRelease`, 92 particles
and six emitters. Capture paused roughly nine frames after activation for a
still image. These fixture checks establish mechanics, not balanced human play.
An immediate transition after a native KO exposed a refused teleport during CPU
respawn. Room entry now keeps simulation running with the CPU standing, retries
placement before starting the encounter or pausing rest, and preserves the prior
checkpoint if placement times out. Lua regressions cover player and CPU refusal,
held-button continuity, timeout cleanup, and claimed-arena resume without another
reward. The subsequent native route completed rest placement changes and fusion,
waited for the second Goomba to disappear, observed two boss stock losses from
labelled ringout fixtures, and completed the deferred exit transition to victory.
Generation 22 checkpoint recorded success/export `g4`, fused parents `r1/r3`,
and empty upgrades on the inherited exported gene. Console item inventory was
empty after this route. This is a mechanics acceptance route with fixture
positioning and KOs; a balanced human playthrough remains outstanding.
Another new run observed three native player stock losses from labelled ringout
fixtures, returned to collection at zero lives, and saved failure in generation
26. The collection remained four genes; `run2` recorded failure with no export,
while `run1` retained its success/export ledger. After a clean quit and fresh
process launch with demo disabled, the collection loaded four genes, two finished
run records and no save error. Normal launches enter through the native TBD menu.
The updated runtime menu also has a native readable-layout capture
(`/tmp/roguelite-menus-v6.png`); it does not validate every selection or new mechanic.

Read-only console diagnostics are:

- `rogue_state`: menu, room, lives, resolved Assault charge/cost/readiness/reach,
  run frame, save error, command node and collection/finished counts.
- `rogue_build`: each run gene's family and host/slot, including enemy ownership.
- `rogue_enemies`: owned encounter actors, positions, host, phase and charge/cost.
- `rogue_bindings`: current per-port tint coverage or refusal diagnostic.
- `rogue_ai`: enabled skill, observed opportunities, input attempts and policy.
- `rogue_menu`: current focus and visible control IDs, mouse bounds and enabled state.

`rogue_start` requests the collection launch when the runtime is not ready; it
changes the scene. These commands do not fake encounter clear or victory.
The console helper is
`melee/worktrees/linux/pc/scripts/console.py`; configure `MELEE_CONSOLE_PORT` only
for local review.

Reusable live evidence capture (start the game separately at normal speed):

```sh
python3 tools/roguelite/live_acceptance.py --port 51700
python3 tools/roguelite/live_acceptance.py --port 51700 --pad-tree
```

The first command only queries state; the second temporarily owns P1 to check
the recursive menu and taunt latch from a fresh entry room. JSONL evidence is
appended to `/tmp/roguelite-acceptance.jsonl`. `--command` logs explicit engine
fixtures separately; they cannot establish naturally earned charge or victory.
`--press` sends neutral-separated controller buttons for supervised tests.

The current charge adapter accepts fighter hurtbox hits and native direct fighter
hits on owned Adventure enemies, and treats shieldstun action 181 separately as
defense. Generic item/projectile callbacks and reflected-article ownership remain
unsupported. Same-action multihits share a deduplication identifier;
cross-action continuing attacks and
simultaneous trade ordering require native evidence. Core rejects reaction
lineage, and native scripted `gd.hit` currently emits no collision `on_hit`
callback, preventing gene releases from charging themselves under that API
contract. This does not establish all future reaction-source behavior.

Still required before a broader completion claim: full normal-speed human/controller
playthrough, the alternate arena branch and hardware-adapter evidence, Windows
validation, natural custom-enemy charge/release evidence, measured CPU technique
success and stronger neutral/recovery decisions, more gene content, alternate
costume and broader pose/equipment/partner tint coverage, broader authored dungeon
pieces and measured fighter mobility, and stronger save/encounter-state continuity.
Analytical reachability screens the room's authored main floor and conservative jump/gap limits;
it does not prove real
engine recovery, collision seams or enjoyable combat. No release, deployment or
distribution has been performed.

## Debug attack cursor

The native debug flight cursor supports a fixed target and a repeating real
fighter hitbox. These are test fixtures, separate from normal player combat:

```lua
gd.fly_target(1, 0, 5)       -- approach, clamp the final step, then hold
gd.fly_attack(1, true, 3, 6) -- damage 3; world-space radius 6
gd.fly_attack(1, false)     -- disarm while holding position
gd.fly_clear(1)             -- clear attack and target; retain stick flight
gd.fly(1, false)            -- return to normal fighter control
```

Console equivalents are `fly target 1 0 5`, `fly attack 1 on 3 6`,
`fly attack 1 off`, `fly clear 1`, and `fly 1 off`. `gd.fly_state(1)` exposes
target and pulse count; `gd.hitboxes(1)` exposes the actual capsule. Clearing both
victim histories and assigning a fresh native attack instance lets a pulse hit
the same target again. Native hitlag still pauses attacks; this is not a promise
of damage every rendered frame, and it does not restart a character's animation.

Live v9 fixture evidence at the normal 60 Hz target: Link converged from
(-42, 0) to (0, 5), emitted 24 pulses during 60 game frames, and repeatedly hit
a stand-mode Fox from 0% to 36% with a 3-damage capsule. Disarming emptied
`gd.player(1).hitboxes`; after another 30 frames Fox remained at 36% and the
pulse count remained 24. A separate 1-damage cursor hit killed a native Goomba
in the custom traversal room and triggered its real charge callback (0→1) and
room clear. These checks do not validate the normal combat balance or CPU AI.

The v10 rebuild passed 46 targeted native checks (33 script, 10 scene, 2 FX,
1 flight) and 35 discovered roguelite tests, plus their standalone Lua suites.
A live moving-frame assertion now verifies that the capsule follows the fighter
after velocity integration; repeated contact, exact target convergence and
disarming also passed again (`/tmp/roguelite-v10-cursor-live.log`).

The same build cold-loaded the corrected grid room without a Lua time-budget
error. Model preloading loads one asset per update, then construction and fighter
placement run in separate updates; isolation loss before placement cannot write
the new checkpoint. The corrected entry-room capture is
`/tmp/roguelite-door-grid-v10.png`. A position fixture at the right door's true
origin `(52,0)` plus real D-pad Down entered the trail; the left trail doorway
at `(-52,0)` entered arena A. These checks validate door alignment and transitions,
not a combat clear: the unopposed traversal enemy later left the stage, and the
idle player lost one run life before the left-door check.
