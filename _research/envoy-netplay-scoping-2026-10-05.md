# Envoy over the port's own netplay: scoping study (2026-10-05)

Date: 2026-10-05. Supersedes nothing as a whole. It qualifies one sentence: "Offline only; nothing here runs in
netplay" in `docs/superpowers/specs/2026-10-04-envoy-loot-and-modifiers-design.md` section 9 (that was a scope
choice, not a limit of the engine; this study says what lifting it costs). Read-only study: nothing was built,
launched or committed. The one thing executed was a throwaway `lua` script in the session scratch directory that
loaded `mod_pool.lua` to count records (output quoted in section 2).

Tags: **[R]** read from source (file:line given or the file is named), **[I]** inferred, **[U]** unverified, needs a test.
Paths are repo-relative to the game checkout `melee/` unless they start with `tools/`, `docs/`, `_research/`.

Owner brief (verbatim): "I actually also envisioned envoy supporting our custom online netplay. two player,
cooperative or adversarial envoy." and "we control our server, we can build whatever we want on it, and give it the
capabilities."

"Our netplay" is the port's rollback netplay (`pc/platform/gw_netplay.c`, `gw_rollback.c`, `gw_net.c/.h`, protocol 4).
Not Slippi.

Outside reference: GGPO's documentation and design notes (Tony Cannon, https://www.ggpo.net/) for the rollback
vocabulary (input delay, prediction, SyncTest); the port already credits it through its own netplay work. If any
idea here beyond that is adopted (for example the "input authority / spectator relay" shapes in section 9) it would
need a `CREDITS.md` line. Also credited, ideas only: Path of Exile (keystone/modifier concept, already in
`CREDITS.md` per `keystones.lua:3`). No other outside source was consulted.

---

## 0. Findings in ten lines

1. Online today is exactly one thing: a 1v1 human Versus match, scene string `mode=vs;at=match;p1=../hu;p2=../hu;...;items=off`
   [R `gw_netplay.c:189-211`], slots fixed to host=port 0, guest=port 1 [R `gw_netplay.c:1965-1966`]. Between games a lobby
   with pick/ban and a persistent room carries a set [R `gw_netplay.c:1182-1215`, `:2288`]. No 1P modes, no CPUs in the online scene
   builder (the scene launcher itself can build CPU slots [R `_research/scene-launch.md:151-187`]; whether CPU AI is
   rollback-exact online is [U]).
2. Every Envoy gameplay write is refused online by design: `gs_require_offline` [R `gw_script.c:836-842`], the 1P layer is
   gated by `gs_1p_offline()` [R `gw_script_1p.inc:17-19`], and `mod.json` has `"rollback_safe": false` [R `envoy/mod.json`].
   No script hook runs on a resimulated frame [R `docs/scripting.md:233-237`; `gw_script.c:8749-8752`].
3. The Lua VM is never replayed; offline rewind restores a Lua blob that the script itself exports with every
   `sim_commit`, plus replays the native ops [R `gw_script_sim_state.inc:1-3`, `:81-118`]. That mechanism is local
   to the LAB's own timeline; rollback does not call it [R: `gs_sim_replay` is invoked only for lab frame kinds,
   `gw_script.c:8786`; resimulated rollback frames return before it, `:8749-8752`].
4. The native state under the modifiers is mostly already snapshotted game BSS (hit rules, fighter mods, caps, armour,
   crit, timed channels) [R catalogue rows; `script_hit_rules.inc:1-3`]. But it is **not in the rollback hash**: `RB_GameHash`
   mixes seed, motion, position, velocity, percent, facing and Turbo's window word, nothing else [R `src/melee/ft/fighter.c:3930-3956`].
   So a modifier divergence is detected only after it has changed a position or a percent.
5. In the Envoy pool, 85 records: 38 are passive (`equip`) and compile to native ops that already live in BSS;
   47 are triggered, and their per-event logic (statuses, stacks, heal/damage, emit) runs in Lua with state in Lua tables
   (section 2).
6. Every roll is already a pure function of a run seed (`seed_for(seed, stage, loop, port)`, `run_host.lua:15-17`;
   `drive_loot.lua:22-28`; `foe_roll.lua:5-8,94`). The only per-peer randomness is where the run seed itself is
   chosen (`classic.lua:50`, `math.random`) and the default rng of `drives.lua:18`/`run.lua:7`.
7. Recommended: (c) native evaluator for in-match rules over data records, a BUILD word agreed at each stage boundary
   (the Turbo pattern), Lua kept for menus, rolls and presentation; with the lobby HOST arbitrating between stages from pure functions of an agreed
   seed. Strictly peer to peer; the server stays a light matchmaker (owner constraint, section 9).
8. First slice playable by two people live: **adversarial, passive-only builds, one Versus game per stage**, build
   agreed in the lobby and applied once before frame 0. Ghost builds are cheap in netcode but
   need server storage: parked as an owner decision (section 9).
9. Biggest risks: in-match evaluator parity (Lua-to-native rewrite of 47 triggered records and their event sources),
   hash coverage (silent desync), and Classic/Adventure's 1P stack being entirely outside the online path.
10. Protocol: a build word plus a build blob is a protocol 4 -> 5 change, handled like Turbo's (section 8).

---

## 1. Inventory of what Envoy calls during a match

The Envoy modules reach the engine through a wrapper `g` (the bundle in `main.lua` is generated by
`tools/port/envoy_bundle.py`; the sources are `scripts/*.lua`). I counted `g.<name>` call sites across `scripts/*.lua`
(counts in parentheses are call sites, [R], by grep). The class is from the registration's gate; where I did not read
the individual registration I say [I].

### 1a. Read-only and online-safe (reads game state; same on both peers if the sim is)
`g.player` (118), `g.match` (43), `g.frame` (14), `g.items` (12), `g.hit_rules` read form (8), `g.entity_valid`/`entity_resolve`,
`g.sim_read`/`mod_read`/`mod_list`, `g.fighter_benched` (19), `g.fly_state`, `g.enemy_state`, `g.item_kinds`, `g.floor_below`,
`g.stage_bounds` read form, `g.camera_get`, `g.zones_at`, `g.sim_replaying`, `g.sim_supported`, `g.lab_mode`, `g.paused`.
Caveat [R `docs/scripting.md:233-237`]: hooks that read these are skipped on resimulated frames, so a script that reads a
value at on_frame sees only confirmed-timeline frames, never the rolled-back ones. Fine for display, wrong for decisions.
Per-peer by construction (must never feed a decision): `g.time` (37; wall clock; used by the reward screen timer
`run_screen.lua:303`, and run_host profiling `run_host.lua:615,626,635`), `g.pad` (15; the local controller, `docs/scripting.md:484`),
`g.safe_area`, `g.project`, mouse.

### 1b. Presentation only (fine if it differs per peer)
`g.kit`, `g.text`, `g.box`, `g.fill`, `g.panel` (UI; 79+26+11+68); `g.fx_world`/`fx_move`/`fx_control`/`fx_end` (16 total);
`g.model_*` (about 50: load, spawn, set, get, despawn, release, label); `g.post_add`/`post_set`/`post_remove`;
`g.fighter_shader`/`fighter_shader_set`/`shader_status`/`dobj_tint`; `g.echo_afterimage`/`afterimage_remove`; `g.play_sound`;
`g.warm`/`warm_done`/`warm_release`; `g.parts`/`parts_clear`; `g.mod_stamp`; `g.rgb`; `g.log`; `g.command`.
Catalogue "Presentation" rows say selection/state is presentation, "Restore clears/refills history, never gameplay"
[R catalogue lines 83-92]. Caution [I]: `g.input_mask`/`g.input_chord` (16 + 6) filter the local pad before the game sees it. They
are local-UI conveniences but they change what is SENT as input, so online they must either stay local-only and
neutral for the sim, or be disallowed while the opponent is live. Needs a deliberate rule.

### 1c. Gameplay writes, offline-only today

| call(s) (Envoy call sites) | gate | native state under it | in snapshot? | in rollback hash? | what is wrong online |
|---|---|---|---|---|---|
| `g.sim_commit` (4) with ops `fighter_mod`, `damage`, `hit_rules`, `echoes`, `fighter_caps`, `fighter_effect`, `fighter_armor`, `timed_status`, `crit` | `gs_require_offline` in `gw_script_sim_state.inc` [R grep: 2 sites]; ops listed at `gw_script_sim_state.inc:14-17`, `mod_registry.lua:47-61` | fighter mods: 6 roots BSS `script_fighter_mod.inc:4`; hit rules `script_hit_ports[12]` BSS `script_hit_rules.inc:5-15`; caps overlays, 12 entities, BSS; armour/crit/timed BSS | yes [R catalogue 69-81, `script_hit_rules.inc:1`] | **no** (only Turbo's word) [R `fighter.c:3930-3956`] | the WRITE: it runs from Lua after the frame, on one timeline, and the Lua blob that explains why the ops were written is not rolled back. The state itself is rollback-safe once written identically |
| `g.sim_clear` (24) | `gs_require_offline` `gw_script_sim_state.inc:70` | releases owned rules | yes (BSS) | no | write path |
| `g.set_damage`/`set_percent` (11+4) | offline [R `docs/scripting.md:504-505`] | fighter percent (hashed) | yes | yes (percent) | write path. Burn damage over time uses the `damage` op = absolute percent each frame [R `mod_lab.lua:~305`] |
| `g.fighter_mod` (4) | offline [R `docs/scripting.md:519`] | as above | yes | no | write path |
| `g.fighter_timed_status` (2) | offline [I: catalogue 80] | 4 timed channels/entity BSS, "no journal operation" [R catalogue line 77] | yes | no | write path; also absent from the journal |
| `g.fighter_interrupt` (1) | offline | `ft_intrwin[12]` BSS, hashed [R `script_fighter_interrupt.inc:386-400`] | yes | **yes** | write path only: "No sim_commit operation exists for an interrupt window ... direct, not journalled" [R `mod_registry.lua:13-14`] |
| `g.set_stocks` (1), `g.cpu_mode` (16), `g.spawn_enemy`/`enemy_*` (7), `g.fighter_bench`/`fighter_call` (24), `g.item_spawn`/`despawn`/`item_remove` (24) | offline [R `gw_script_cpu_ctl.inc`, `gw_script_items.inc`, `gw_script_fighter_bench.inc` carry `gs_require_offline`] | retail structures/heap | yes (MEM1) | partly (positions via the fighter) | writes; drops are physical items spawned by Lua (`drive_drop.lua`) |
| `g.match_end_hold` (8), `g.hold_1p`/`release_1p`/`spawn_1p`/`start_1p`/`end_1p`/`mode_1p`/`loop_1p` (34) | `gs_1p_offline()` and `gs_require_offline` [R `gw_script_1p.inc:17,71-112,189`] | host `gs_1p` struct, wall-clock hold `hold_ms` [R `gw_script_1p.inc:5-7`] | **no** (host state: "not a generic game checkpoint", catalogue line 123) | no | the whole 1P lifecycle is host state outside the snapshot |
| `g.stage_*` (about 40), `g.area_*`, `g.fly*`, `g.teleport`, `g.fly_attack` | offline | stage geometry, debug movement | mixed | no | Envoy uses them for hubs, fly-based cinematics, bonus staging; irrelevant to a Versus slice |
| `g.scene_launch`, `g.launch_*`, `g.pause`/`resume` (10+16) | gameplay gate | host | no | no | run flow |

Honest summary of the "only the WRITE path is the problem" question: it is true for hit rules, fighter mods,
caps, armour, crit and the timed channels (state in snapshotted BSS; writing it identically on both peers at an agreed
point would be deterministic). It is not yet true for: (i) the hash (nothing but Turbo's window is mixed in), (ii) every status, stack and
expiry, which exist only in Lua tables (`mod_engine.lua:22`, `statuses`), (iii) the interrupt window (state is hashed but
there is no journal op), (iv) drops and 1P state (host or heap, written by Lua).

---

## 2. Where decisions are made, and how much is already data

### Per frame, inside a match (all in `mod_lab.lua:255-332`, `mod_engine.lua`)
One pass at the end of every logic frame (`L:frame`): sample players (`g.player`), turn engine events into the queue (`L:hit`,
`L:ko`, `L:action`, `L:clank` from engine event hooks), `engine:begin_frame` (status expiry, Burn tick every 60 frames
`mod_engine.lua:66-68`, interval events), `engine:drain` (match triggers against each fighter's build, apply effects, bounded
chains: depth 8, budget 64 `mod_engine.lua:9`), then derive native ops from the result (`engine:values`, `native_rules`,
`damage`, echoes) and commit them with the whole Lua state exported as a blob (`g.sim_commit(self:export(), ops)`).
Technique events (wavedash, L-cancel, tech, combo, crit, armour) come from a game-side producer that reads game decisions and writes a
snapshotted ring [R `script_skill.inc:1-17`] but the Lua side receives them as post-frame host events "skipped while
resimulating" [R `gw_script_skill.inc:15`]. So an effect reacts at the earliest one logic frame later [R `gw_script_skill.inc:10-12`].

### Between stages
Rolling offers/drops/keystone offers/opponent builds, the reward screen (grid UI), equipping, depth progression, New Game+:
`run_host.lua` (667 lines), `run_screen.lua` (448), `drive_bag.lua`, `drive_loot.lua`, `foe_roll.lua`, `keystones.lua`,
`mod_progression.lua`, `classic.lua`. All pure functions of (run seed, stage, loop, port, context) except the player's
choices and the wall-clock reward timer [R `run_host.lua:15-17,287,319,385`; `run_screen.lua:303-306`]. Opponent rolls retry
up to a distance target ("distance" `foe_roll.lua:118`) but from a seeded stream, so deterministic.

### The data/code split in the pool (measured)
`lua` script run on `mod_pool.lua` + keystones + techniques + echo records (read-only, scratch dir):

| measure | count |
|---|---|
| records in the pool | **85** (38 normal, 41 keystone, 6 unique) |
| passive `equip` records | **38** |
| triggered records | **47** (hit_dealt 11, interval 5, perfect_shield 4, landing 3, plus clank, combo, crit, wavedash, ko_dealt, status_applied, hit_taken, ledge_grab, lcancel_hit 2 each; armor, air_dodge, air_jump, jump, tech, combo_end, 1 each) |
| effect instances by op | status 57, value 36, convert 11, damage 8, remove_status 7, versus-status 7, heal 6, crit 6, echo 5, armor 4, crit_next 3, restrict 2, air_jumps 1, intangible 1, clank_damage 1 |
| effect instances by native journal (`mod_registry.lua:12-32`) | `lua_state` 65, `fighter_mod` 36, `hit_rules` 18, `damage` 14, `crit` 9, `echoes` 5, `fighter_armor` 4, `fighter_caps` 3, `fighter_effect` 1 |
| records whose effects are all native-journalled | 45; Lua-state only 29; mixed 11 |

Reading: the records are data in the full sense (`mod_schema.lua` validates tags, triggers, conditions, effects;
bounded vocabulary of 22 events x 11 condition kinds x 15 effect ops [R `mod_schema.lua:5-30`]). There is NO per-record Lua
callback. The behaviour is in the engine: `matches` (a 30-line condition interpreter, `mod_engine.lua:78-118`) and `apply` (an
op switch, `:123-170`), roughly 150 lines of interpretive code, plus derivation (`native_rules`, `values`, `crit_config`,
`passive_state`, `earned`, `echo_window`) that turns equipped records and statuses into native op tables. That is a
small, closed interpreter, which is the property that makes a native port plausible. What is NOT data: the status
definitions' derived values and budgets (`mod_status.lua`, data with two small functions), the 1P/run director, the bag screen.

Passive vs triggered matters most: the 38 passives are already compiled to native ops (36 `fighter_mod`, 18 `hit_rules`
including the convert/versus-status pair evaluated natively per hit; the hit-rule evaluator is a pure native function
over data [R `gw_script_hit_rules.inc`, `script_hit_rules_core.h`]). Only the 47 triggered records need an in-match event loop.

---

## 3. Architectures

Facts that bound all of them [R unless marked]: max rollback depth 7 by default, 12 maximum, input delay 2
(`gw_rollback.h:17-23`); restore about 2 ms and about 0.6 ms per resimulated frame (owner's measured figures,
not re-measured here) so a depth-7 rollback is about 2 + 7 x 0.6 = 6.2 ms of extra work in one display frame, against an
8.3 ms frame target at 120 fps (`MEMORY performance-target-120-fps`). Hook calls are skipped in resimulated frames, so
any Lua in the loop would be skipped there too.

### (a) The same Lua on both peers, made rollback-safe
Two ways: snapshot the Lua VM, or replay it.
- *Snapshot the VM.* The engine already has the pieces: `E:export`/`E:import` serialize the whole evaluator state
  (`mod_engine.lua:397-420`) and Envoy restores it in `on_loadstate`. Doing that every frame for rollback means
  exporting, and for a depth-7 rollback re-importing and then re-running all Lua for 7 frames, which the engine forbids
  (no hooks on resim) and which would have to be new: a resim-aware hook cycle. Cost: serialize per frame (the codec encode in
  `mod_codec.lua`, string build over statuses/trace/recent/display) plus Lua runs inside the 0.6 ms resim budget it
  would double. The VM is "never replayed" because arbitrary closures, coroutines, handles and file/model state are not capturable
  (`docs/superpowers/specs/2026-10-04-geno-full-fighter-design.md` item 3 recommends typed state, not arbitrary VM state [R]).
- *Replay the VM.* Needs every input to Lua to be deterministic and redelivered: events (hit, ko, skill rows) are ring-recorded game-side
  but delivered "post-frame, skipped while resimulating" [R]. Replay requires re-delivering them on resim.
- Determinism requirements that Envoy would have to meet: no `g.time`, no `math.random` (found at `classic.lua:50`,
  `genetics.lua:11`, `drives.lua:18`, `run.lua:7`; the engine itself uses an own LCG `mod_engine.lua:25`), no table iteration
  order dependence (`pairs` is used in `emit`, `memo_key` sorts: partially careful), identical Lua version/float behaviour (embedded Lua 5.4.7).
- Breaks: every Lua write goes through the post-frame journal ops, whose effect lands one frame late and must be re-issued on resim. Also
  every `g.*` presentation call would be called in resim unless filtered.
- Verdict: largest engine change (a replayable script runtime), keeps all of Lua, and the 8.3 ms budget has no
  slack for Lua in resim. Not recommended.

### (b) Scripts act only on confirmed frames, writes scheduled for an agreed future frame
Mechanism: Lua runs only when frame f is confirmed on both peers (all remote inputs in), and its writes are journal ops
stamped for frame f + D that both peers apply at that frame, identically. Delay D: confirmed lag is RTT/2 in frames
plus up to 7 frames of the prediction window, so D of roughly 8 to 20 frames (133 to 333 ms) at typical internet latency; both
peers must agree D (handshake constant). Costs: the ops needed at frame f+D must be known to both peers deterministically, so Lua must run
identically on both on confirmed frames, in lockstep; a stalled peer stalls Lua. Which Envoy effects tolerate it:
slow ones (Burn tick every 60 frames, status expiry, passive recompute after a status change, healing, drops) yes;
reactive ones no: "wavedash -> super armour next frame", "perfect shield -> next hit extra damage", hit-triggered haste,
intangibility on a technique, crit_next, interrupts (windows of 6 to 20 frames; a D of 8+ consumes them). Any status
that feeds a hit rule (Burn -> Pyre's launch bonus) would apply D frames late and unequal-in-feel across peers.
Verdict: sound but breaks the defining feedback of a technique-reward mod. Suitable only as a fallback for slow effects.

### (c) Native in-match evaluator over data records; the BUILD agreed at stage boundaries
Design: a native `ModRules` evaluator in game BSS (like `ft_intrwin`, `script_hit_ports`), which:
- holds per entity (12): the active record ids and tiers (the BUILD), status slots (7 statuses x {expires, stacks, amount, next_tick}), recent-event
  frames, momentum counters, a bounded event queue;
- is fed from simulation hooks (ftcoll.c hit/shield/KO, fighter.c landing/jump/ledge, the existing game-side skill ring rows
  [R `script_skill.inc`]), deterministically, in a fixed order, the same way Turbo hooks `ftcoll.c` and `fighter.c` [R `script_fighter_interrupt.inc:7-14`];
- writes only through the existing native setters (fighter mod, hit rules, caps, armour, crit, damage) from inside the simulation, so no journal and no Lua are
  involved in a match;
- mixes a build word and a status word into `RB_GameHash` (Turbo's `IntrWinHashWord` is the template, `script_fighter_interrupt.inc:393-398`),
  so divergence is a checksum desync at once, which the curated SyncTest can then prove;
- reads its build from a `GwMatchBuild` record applied at match arm: the lobby's "G <seed> <scene>" message and the scene string are already the
  agreed-before-play channel (`gw_netplay.c:1182-1190`, `np_build_scene :189-211`); the turbo token `turbo=<hex>` is the precedent, a new `build=<base64>`
  token (or a lobby message, 200 bytes max `GW_NET_LOBBY_MAX`, vs 900 bytes `GW_NET_MAX_BLOB` for the scene) carries it.
Size of a build [I]: 4 to 6 equipped records x (id u8, tier u8, copies) plus keystone, implicit colours: well under 100 bytes per player. 2 players: under 250.
Cost per rollback: none beyond the existing snapshot (the state is BSS), plus a few extra words hashed per frame.
What it breaks: Lua can no longer be the evaluator in online matches, so effect behaviour must exist twice (Lua for offline/LAB prototypes, native for
play) unless the Lua evaluator is retired for hosted runs. Parity tests needed (replay an event script through both and diff).
Extension: the statuses' gameplay effects already have native carriers: `status_bits` in hit rules, fighter mod values; the native
evaluator would own the status lifetime ("Lua status instances -> native hit predicates and timed channels, with one lifetime authority" is ranked #2 in the
catalogue's own missing connections, line 17). So (c) is aligned with the work already planned for the offline spine, not a fork.
Verdict: best fit. The first slice can be (c) restricted to passives (section 5).

### (d) Hybrids
- (c) for rules + Lua for presentation: Lua reads the native status/build state (read-only calls, online-safe) and drives shaders, nameplates, HUD. This
  is the recommended hybrid and costs nothing in determinism.
- (c) + (b) for slow effects: effects with durations of 60+ frames and no input-frame reactivity (Burn, heal, drops) scheduled by the server/Lua at stage boundary only.
- (c) + the lobby host as arbiter for between-stage truth (section 9).

### Recommendation
(c), hybrid with Lua presentation, plus host-arbitrated between-stage layer. Reasons: it makes the in-match path identical on both peers by construction
(same native code, same agreed data, same hashed state), it spends none of the 8.3 ms budget in resimulation, it follows Turbo's pattern exactly
(rule word agreed at connect, state in snapshot memory, mixed into the hash, `gw_matchrules.h`), and 38 of 85 records plus the hit-rule evaluator are
already native or nearly so.
Survives unchanged: the schema, records, pool, budget, progression, keystone data and meta, loot/foe rolls (pure functions of seeds), the bag, reward grid UI,
text/tooltips (`S.describe`), the visual adapter's look tables, techniques vocabulary (`mod_skill.lua`).
Must be rewritten: `mod_engine.lua`'s matches/apply/drain/values/native_rules/crit_config/passive_state in C (about 400 lines of Lua, 430 including export/import) as a native
evaluator; `mod_lab.lua`'s frame loop (replaced by simulation hooks); statuses' storage; the post-frame ops path (no longer used online); drops (see section 4).
Lua keeps: `run_host.lua` between-stage logic (adapted), `run_screen.lua`, `mod_display.lua` reading native state.

---

## 4. The mode itself online

### What runs online today [R]
Only the Versus scene. `np_build_scene` produces `mode=vs;at=match;p1/p2 hu;...;match=stock;stocks;minutes;items=off;pause=0`
(`gw_netplay.c:189-211`). The session layer knows 4 ports and leader/follower slots (`GW_RB_SLOTS 8`), `gw_net` has 8 slots and payload up to 32 bytes
(`gw_net.h:53-54`), but the adapter assigns exactly two (`gw_netplay.c:1965-1966`). The rollback and snapshot machinery is scene-generic in
principle (MEM1 plus game BSS) but has only been exercised on Versus [I]. 1P (Classic/Adventure) modes: their lifecycle code is explicitly offline
(`gs_1p_offline()` returns 0 when `gw_RB_Enabled() || gw_Netplay_Enabled()`; `gw_script_1p.inc:17-19`); the host state `gs_1p` is outside the snapshot;
the stage-clear hold counts wall-clock ms (`hold_ms`, line 5; `docs/scripting.md:914`); and the 1P game logic (stage sequence, results, bonus stages, Master Hand/Crazy Hand
boss, NG+ loop) is retail scene flow that has never been driven by two peers [I]. Items online are off in the scene string [R `:207`], so physical drive drops
(items on the floor) do not exist online.

### Verdict: Classic/Adventure online is not a small step
It needs the retail 1P scene flow to run under a networked session: a scene-transition protocol between stages (both peers load the next stage identically),
the 1P stage tables and CPU spawns identical on both peers (deterministic if seeds are agreed; [U]), the results/reward screens synchronised, and the Envoy 1P adapter
reworked. Estimated large (the 1P hook layer `gw_script_1p.inc` is about 250 lines of offline-gated host state). Recommendation: do NOT start there.

### Smallest viable online Envoy: a "Versus run"
A sequence of Versus-shaped games between the two players, the existing lobby between games carrying the run. This reuses everything online play already does well:
the persistent room, per-game scene string, rematch loop, stage pick/ban (which can be bypassed for run stages the host or server picks). Two shapes:

**Adversarial** (recommended first): player A and B each have a build; they fight a set (best of N games, N from the lobby); between games each gets a reward.
- Reward screen: both see their own offer (their own stage-seed roll), never the opponent's, on the existing lobby channel as a timed phase, replacing
  "stage pick/ban" in `lb_*` with `LB_REWARD`. [I]
- Synchronisation: each player's pick is a lobby message (`A <action>`), the HOST (or server) validates against the same pure rules (`lb_apply` is a pure function
  tested headless, `gw_netplay.c:1213-1214`) and rebroadcasts the state; the shared timer is counted in lobby ticks by the host, not wall clock; on timeout the host
  auto-picks by a fixed rule (take the first offer / keep the build). Stall: the host's timer resolves it; guest disconnect = the existing 90 s hold / 5 s disconnect
  timeouts [R `gw_net.h:60`, config `disconnect_timeout_ms` 0 = 5000]; a run that loses a peer ends for that pair, the survivor may continue offline (section 9).
- Drops and pickups: no physical items online (items=off). Two choices: (i) the reward is simply offered on the screen after the game (no floor drop), decided from
  `seed_for(run_seed, game, loop, port)` which is identical on both peers; (ii) a native, rollback-safe drop spawn later. (i) first.
- Opponent builds: for a human opponent the build IS the other player's build (agreed in the build word). No roll needed.
- Desync: curated hash mismatch -> `np_cb_desync` (already exists, `gw_netplay.c:293-301`); with the build word hashed it fires early; the match is abandoned
  with a message, the set is void (no server records results). Resume: the run state (two builds, scores, seed, game index) is small; either
  the host re-sends it on `Rejoin` (the room is persistent and reconnects, `gw_netplay.c:2288`) or each client's local run record is presented and digest-compared (section 9).

**Cooperative**: both humans on one side against CPU opponents generated by the run. This needs three things adversarial does not:
(1) CPUs in an online match (scene supports `cpuN` slots [R scene-launch.md:151-187] but the netplay builder, slot ownership (4 ports; slots 0 and 2 for two humans, CPUs on
the rest) and CPU AI exactness under rollback are [U]; CPU AI reads game RNG which is in the hash [R `fighter.c:3935`], so plausible but never proven online);
(2) teams (`teams=1`, team ids; [R scene-launch.md:187]), friendly-fire rules and shared stock/results; (3) the opponents' own builds from the same pool, evaluated by the
native evaluator for CPU entities (the hit-rule layer is per entity 0..11, so it is plausible, [I]). Rewards: each player picks their own, plus a shared
decision (keystone for the team? [I, design choice]).

Recommended order: adversarial first (no CPUs, no teams), co-op second.

### Resume or abandon
A run is: seed, game index, loop, each player's build (ids/tiers/keystone/bag), scores. Under (c) with a lobby-borne run record (about 300 bytes) either peer can
reconstruct it. With the locally saved record both clients present at reconnect (section 9) a dropped pair resumes from the last stage boundary. Mid-match drops always forfeit that game
(rollback cannot recover a missing peer).

---

## 5. Staged plan

Sizes are relative: S (days), M (about a week or two), L (multi-week). "Proofs" use the two-client loopback harness the Turbo lane
used (`_build/audit-20261003/turbo/run_np.sh`: two real clients over loopback, `MELEE_NET_SIM=lag/jitter/loss`, pad scripts, no server;
tools/netplay/np_drive.py is the menu-driving server variant) and `MELEE_SYNCTEST_CURATED=1` with `MELEE_SYNCTEST=12`
(`pc/docs/PORT_DEV_QUICKREF.md:109`; note the byte-compare SyncTest is NOT usable for plain matches, only the curated hash is). Turbo's own record: two real
clients, lag50/jitter20/loss3, 12,300 ticks, 3429+3551 rollbacks, 0 desyncs [R turbo PROGRESS.md FINAL].

| # | Stage | Size | Files touched | Proof | Protocol / version |
|---|---|---|---|---|---|
| 0 | Hygiene in current code (section 6): seeds from the run record, no wall-clock in decisions, builds serializable as a small blob, evaluator effect list frozen | S | `classic.lua`, `run.lua`, `drives.lua`, `genetics.lua`, `run_screen.lua`, `run_host.lua`, `mod_engine.lua` | Lua unit checks; `luac -p` | none |
| 1 | Build serialization: sorted versioned run record plus 64-bit digest (lobby and local save, peer-to-peer resume); pool digest | S | `run_host.lua`, `save.lua`, `mod_codec.lua` | Lua round-trip and ordering checks | none |
| 2 | Native build + passives, applied once at match arm: new `ScriptGame_BuildApply(entity, record ids, tiers)` driving the existing native setters; build word + status word mixed into `RB_GameHash`; `gw_matchrules`-style `GW_BUILD_*` agreement; scene token `build=`; refusal at handshake if unknown record ids / version differ | M | `pc/platform/gw_matchrules.h` (or new `gw_matchbuild.h`), `gw_net.c/.h` (HELLO/ACCEPT carry a build digest), `gw_netplay.c` (scene token, lobby), `pc/gameworld/script_game.c` + new `script_build.inc`, `src/melee/ft/fighter.c` (hash), `gw_script.c` (an allowance: build apply is not a Lua write) | loopback with two different builds + SyncTest curated; mismatch refused test (copy Turbo's `np_mm`); desync-injection test (poison a record, hash must trip) | **protocol 4 -> 5** (HELLO/ACCEPT grow; server's protocol check in `gdmelee_server.py:NETPLAY_PROTOCOL`, `tools/release/netplay_protocol.ps1`, HOW TO PLAY) |
| 3 | Versus-run lobby (**first slice playable by two people online**): adversarial set, each with a build from a starter + 1 keystone, reward screen between games from `seed_for`, host-validated pick, no drops, passives only | M | `gw_netplay.c` lobby (`LB_REWARD` phase, run record), `gmfrontend.c` menu entry, Envoy `run_host.lua`/`run_screen.lua` as a lobby client (Lua presentation of native lobby state: `gd.netplay` exists, `docs/scripting.md:691`; needs a read-only `gd.netplay_run`) | two-client loopback, N=3 set, lag/jitter/loss; kill-a-peer between games; reward timeout; curated SyncTest | build blob in lobby (message type), no new transport |
| 4 | Native triggered evaluator: statuses (7 x 12), event hooks (hit, KO, shield, perfect shield, clank, landing, jump, ledge, skill ring rows), the 47 triggered records, Burn tick, crit_next, interrupt as native op; mixes status state into the hash | L | `script_game.c` + new `script_mods.inc` (about 600-900 lines C [I]), hooks in `ftcoll.c`, `fighter.c`, `script_skill.inc`; parity harness comparing Lua engine vs native on event scripts | parity tests (new), loopback, SyncTest curated, a long soak like Turbo's 3.5 min | none beyond stage 2; hash content changes (every peer must run the same build anyway) |
| 5 | Co-op prerequisites; peer-to-peer resume and abandon/continue-offline polish; optional mode flag in the lobby | M | `gw_netplay.c`, `run_host.lua` | disconnect/reconnect on loopback with the simulated network | mode word rides in the scene string; server unchanged |
| 6 | Opponents that are CPUs (co-op), then items/drops online | L | scene builder, 4-port ownership, CPU AI exactness, native drop spawn, 1P-like stage tables | CPU-in-netplay soak: first needs its own feasibility test | protocol bump for slot ownership |
| 7 | Classic/Adventure online (only if still wanted) | L (largest) | `gw_script_1p.inc`, scene flow, snapshots across stage transitions | new | new |

Stage 3's "first playable by two people online" includes only passives (38 records, those that are 36 fighter-value and 18 hit-rule effects, plus echoes if in flight work lands)
so the in-match evaluator is NOT needed for it. Triggered records are the next step, not a prerequisite.

---

## 6. What to stop doing now (so online stays reachable)

1. **Effects as Lua callbacks or Lua-only state.** Statuses, stacks, momentum, `recent`, `trace` live only in `engine.statuses` etc. Keep every new effect a record in
   the 15-op vocabulary; do not add a record that needs its own Lua function. A new op needs a native counterpart on the same day (`mod_registry.lua` is the one place).
2. **`math.random` and the default rng parameters.** `classic.lua:50` (run seed), `genetics.lua:11`, `drives.lua:18`, `run.lua:7`. The run seed must come from an agreed
   source (lobby/handshake/server) in any hosted run; every other roll must derive from it with `seed_for`.
3. **Wall-clock timers in decisions.** `g.time` for the reward countdown (`run_screen.lua:303`) and the wall-clock stage-clear hold (`gw_script_1p.inc` `hold_ms`,
   `docs/scripting.md:914`). Count lobby ticks or logic frames, never milliseconds, in anything both players must agree on.
4. **State kept only in Lua that the sim depends on.** E.g. burn damage applied as absolute percent from Lua each frame (`damage` op), `fighter_interrupt` called directly (no journal op, `mod_registry.lua:13`). New
   gameplay state belongs in game BSS (snapshotted), with a hash word (the Turbo pattern).
5. **Writes that depend on per-peer observations.** Host event queues are "not simulation authority" (catalogue line 65); hooks skipped on resim [R]. Do not let a decision
   (an offer, a drop, a status) depend on a host-delivered event; derive it from game state or a game-side ring.
6. **Drops as Lua-spawned items** (`drive_drop.lua`, `item_spawn`): items are off online and Lua spawns are offline writes. New drop design should be decided at the stage boundary from the run seed, not from where a physical item lands.
7. **Hash gaps.** Every new native modifier state added without a hash word creates silent desyncs. Add the word when adding the state (Turbo is the template).
8. **Per-peer inputs through `g.input_mask`/`input_chord`/`g.pad` into decisions.** Fine for local UI; never for rules.
9. **Assuming `rollback_safe: true` helps.** It does not; the engine refuses Lua writes online regardless (`docs/scripting.md:234-237`). Do not set it hoping to unlock online.
10. **Build/stage identity by Lua table order.** Serialise builds in a fixed order (ids sorted) for the build digest.

---

## 7. Tests already available and their limits [R]
- Turbo's lane evidence: mismatch refused at the handshake; two-client loopback soak with 0 desyncs; `gd.rewind_test` proves snapshot restore, not a resimulated window; the byte-compare SyncTest mismatches in HSD particle state with Turbo off, so use `MELEE_SYNCTEST_CURATED=1` [R turbo PROGRESS.md D.1, FINAL; QUICKREF:109].
- Gap [U]: no test has Envoy modifiers under rollback; the curated hash would not see them until the build/status words are mixed in.

## 8. Protocol and version consequences
- Build agreement requires a handshake or scene-borne field. Turbo's precedent: protocol 3 -> 4 for one word (`gw_net.h:46-51`). A build digest (u64) in HELLO/ACCEPT would be protocol 5; the full build travels in the scene string (900 byte blob budget) or a lobby message (200 bytes per message).
- Mixing new words into `RB_GameHash` means all peers must run the same exe (already required: `exe_hash` in the handshake).
- `mods_hash` includes only `rollback_safe` gameplay scripts [R `docs/scripting.md:239`]; an Envoy native build does not need a script in the must-match set, but the pool's record content must be part of the identity: add a pool digest to the global hash or the build word.
- Server side: `NETPLAY_PROTOCOL = 4` in `gdmelee_server.py`, `tools/release/netplay_protocol.ps1` + its test, `publish.ps1` text, HOW TO PLAY (as Turbo's lane did).

---

## 9. The server, and the between-stage layer without a referee

**Owner constraint (2026-10-05, overrides the earlier brief):** the public server is free and open to everyone to matchmake; it must not become dedicated
hosting. The recommendation is strictly **peer to peer; the server does no more than it does for a Turbo private room today**: introduce two peers and carry a few bytes of agreed settings.
Nothing whose cost grows with concurrent matches or match length is in the plan.

### What the server is today [R]
- `tools/netplay/server/gdmelee_server.py` (345 lines, Python standard library, asyncio UDP, one port, default 51600). Rooms: 4-character codes, REG/JOIN/KA/BYE, a random queue keyed by `mods_hash`
  (RAND), and RELAY as a fallback when no direct path opens. State is in memory; "Nothing is stored on disk" (server README). Production `netplay.gsd.sh:51600`; TCP crash uploads on the same number in a separate process
  (`tools/release/crash_upload_server.py`, opt-in text reports, 64 KB cap, rate limited).
- Game traffic is peer to peer when hole punching works, relayed only as fallback (about 25 KB/s per relayed match, README "What it costs"). A room is two addresses and a timestamp.
- Turbo's rule word never touches the server except as bytes inside the relayed handshake: it is agreed in HELLO/ACCEPT and the host's scene string [R `gw_net.c:368,398`, `gw_netplay.c:189-211`].

### Considered and rejected (and why)
- Simulation on the server: needs the disc image on a public machine (legal exposure; the project never ships disc data), CPU and 40 MB+ memory per match, and Windows/Linux determinism has never been tested here
  (Linux status scope excludes networking: `docs/LINUX_PORT_STATUS.md:3,58`; the Geno design only says "same engine build ... cross-platform needs dedicated tests", `2026-10-04-geno-full-fighter-design.md:203`). Cost grows per match.
- Relay as a design element, or the server as a third rollback peer / input authority: cost per match-minute, latency on the common direct path, the server sees inputs. The existing fallback relay stays exactly as it is.
- Server-held live run state and arbitration: per-match state and logic on the VPS, plus a pool mirror kept in step with every release. The lobby host arbitrates instead (below).
- Server-side verification by replay (needs the simulation) and spectating through the server (a relay by another name).

### Between stages with the lobby host as arbiter (no server)
Everything below reuses the lobby protocol Turbo's private rooms already use: the host runs the rules, the guest sends requests (`A ...`), the host validates, applies and broadcasts the whole state (`S ...`), then sends the
match (`G <seed> <scene>`) [R `gw_netplay.c:1182-1190`]. The rules are pure functions (`lb_new_set`/`lb_reset_game`/`lb_apply`, headless-tested, `:1213-1214`), so a reward phase follows the same shape [I].
1. **Run seed.** The host client chooses it (the match seed is already host-chosen: `np.seed`, `gw_netplay.c:1957-1962`); the run seed travels in the lobby `S` state or the scene string. Both clients derive everything from
   (run seed, game index, loop, player index) through the existing `seed_for` (`run_host.lua:15-17`). No peer-local randomness (section 6).
2. **Offers.** Each client computes both players' offers locally and identically (`drive_loot.lua:26`, `keystones.offer`: pure functions of seed and context). Each shows only its own player's offer. Nothing is transmitted except the choice.
3. **Choices.** A pick (index into the player's own offer; bag actions) is a lobby message to the host; the host checks it with the same pure function (index inside the offer), broadcasts the resulting run record, and both clients apply the identical update to both builds.
   Both players pick simultaneously; the phase ends when both have picked or the countdown expires.
4. **Countdown.** Started by the host when the phase opens, counted in lobby ticks (the transport sends heartbeats in the lobby, `gw_net.h:188-190`) and broadcast as remaining ticks; never `g.time()`. On expiry the host applies a deterministic default:
   keep the build, take offer 1 (or skip the reward). A slow player loses the choice, not the run.
5. **Stall or disconnect (proposal).** The lobby channel is reliable and ordered; INTERRUPTED after 1 s of silence and DISCONNECTED after 5 s by default (`gw_net.h` `notify_timeout_ms`, `disconnect_timeout_ms`); loading tolerates 90 s.
   A lost peer **ends the run for that pair**; the remaining player is offered "Continue offline", which hands their build and the run record to the existing offline Envoy (rolls continue from the same seed). A mid-match loss forfeits that game (rollback cannot recover a missing peer).
6. **Resume peer to peer (proposal).** After each stage boundary both clients write the same compact run record locally (about 300 bytes: pool/protocol version, run seed, loop, game index, scores, both builds as sorted record ids and tiers, a 64-bit digest of the record).
   To resume, the same two players reconnect in a private room and present their records; the host compares the digests (8 bytes in the lobby plus the record). Equal: the run continues from that boundary. Different: start fresh, or one side adopts the other's by choice.
7. **Desync.** The curated hash mixes a build word and the modifier states (stages 2 and 4); on mismatch `np_cb_desync` fires and the game ends; the record from the last boundary is valid on both sides and can be resumed.
8. **Cheating in a friends-only private room.** The host validates picks against the pure offer function, so a modified guest cannot pick outside its offer. A modified HOST, or any client with edited memory or a changed pool, can invent anything; the handshake catches different exes and pool digests, not tampered memory.
   In a private room between friends that is acceptable and I recommend we say so plainly instead of adding server validation. Random-matchmaking rooms should not offer Envoy sets (as "Random matches force 0" for Turbo: `np.turbo = (np.host && rnd.state != NP_RAND_MATCHED) ? ...`, `gw_netplay.c`).

### Optional server additions (each tiny and stateless per request)
| addition | what the server does | storage | requests | needed for the first slice? |
|---|---|---|---|---|
| Lobby flag "Envoy co-op / adversarial" beside the Turbo flag | nothing new: the mode word rides in the host's scene string and handshake like `turbo=<hex>` (the relay forwards opaque payloads) | 0 bytes | 0 extra | no; only the `NETPLAY_PROTOCOL` constant in `gdmelee_server.py` follows the game's bump, as Turbo's lane did |
| Published daily seed | one number on request, or derived from the date by both clients with a published formula (no server at all) | a constant | at most 1 per player per day; 0 if derived | no |
| Queue key includes the mode | RAND key gains a mode word | 0 | same as today | no (private rooms first) |

### Would need the owner to choose to host more (explicitly NOT in the plan)
Ghost builds (fight a build another player made: asynchronous, cheap in netcode), leaderboards, run history, shared seed lists, any validation of uploads. Each needs storage, rate limiting and moderation.
If ever chosen: a build record is about 100 to 300 bytes; a minimal player record would be an opaque install id, a display name, build, score, seed, version and timestamp, with retention and delete-by-id. Not recommended now.

### The boundary, stated plainly
Between-stage truth does not need a server: the host's client plus pure functions of an agreed seed give both peers identical offers and builds, with one lobby message per choice. In-match rules still have to be computed identically by both clients under rollback,
which is why the evaluator has to be native, data-driven and hash-covered (architecture c).

---

## 10. Biggest risks
1. **Parity and size of the native triggered evaluator** (stage 4): 47 records, 7 statuses, 22 event kinds with sources spread across `ftcoll.c`, `fighter.c`, the skill ring and the clank observer; Lua and native versions must match event for event, or the offline and online games differ.
2. **Silent desync**: modifier state is snapshotted but unhashed today (`fighter.c:3930-3956`). Any new native modifier state without a hash word will pass checksum and diverge later. Mitigation: hash words from day one; a poison-injection test per state kind (Turbo has `MELEE_SYNCTEST_CURATED_POISON`, `gw_snap.c:1579`).
3. **Scope creep to Classic/Adventure online and CPUs online**: both are unproven under rollback, 1P state is host-side, and co-op needs CPUs and teams. Keep them out of the first slices.
Runner-ups: reward-screen UX under lag (timers in ticks, not milliseconds); online drops (items off); a server mirror of the pool drifting from the client pool (pin with a digest).

---

## 11. Not verified (so a Windows agent knows what to check)
- Whether CPU AI is rollback-exact in an online Versus match (never exercised).
- Whether a non-Versus scene can run under a rollback session.
- Actual restore/resim costs with Envoy builds (the 2 ms and 0.6 ms figures are the owner's).
- Per-call gate classification for every `g.*` in section 1 beyond those read (gates were read in `gw_script.c`, `gw_script_sim_state.inc`, `gw_script_1p.inc`; the remaining calls are classed by registration documentation and the catalogue).
- Windows to Linux determinism: never tested here.
