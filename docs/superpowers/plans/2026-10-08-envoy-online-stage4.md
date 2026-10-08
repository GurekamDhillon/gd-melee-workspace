# Envoy online, stage 4: the native triggered evaluator (brief, 2026-10-08)

Source of the stage: `_research/envoy-netplay-scoping-2026-10-05.md` section 5, row 4 (architecture (c): a native evaluator over data records,
state in snapshotted game BSS, mixed into the rollback hash). Stages 0 to 3 are in the game checkout (`pc/scripts/examples/envoy/ONLINE.md`):
passive builds only. This stage lets TRIGGERED drives (statuses, stacks, heals, damage over time, armour, forced crits, interrupts) work in the
online Versus set. Lane: `ws/envoy-s4` (this repo), `agent/envoy-s4` (game, build root `_build/agents/envoy-s4`).
Tags: [R] read from source, [D] a decision made in this brief, [U] unverified until the proof runs.

## 1. What the Lua engine does that must now be native

`mod_lab.lua L:frame` (offline) runs once per logic frame: sample players, `engine:begin_frame` (status expiry, Burn tick every 60 frames,
interval events), `engine:drain` (match each queued event against the holder's build, apply effects, chains bounded depth 8 / budget 64 /
queue 128), then commits native ops (fighter values, hit rules, crit config, timed armour, damage) with the Lua state as a blob. [R]
Events reach Lua from host hooks that are skipped while resimulating. Online none of that may run: Lua writes are refused and nothing replays them.

## 2. Design [D]

**Compile in Lua, run in C.** The records are data, so everything that is a pure function of (build, tier) is resolved ONCE per match in Lua
(`E:trigger_program(port)` in `mod_engine.lua`) into a flat numeric program: per record instance the trigger, the interval, the conditions, the
effects, with every `$tier` reference resolved (`S.resolve`), durations already scaled by the build's `status_duration` value and clamped
exactly as `E:apply` does. The C side carries NO tier, growth, budget or schema logic. Both peers compile locally from the agreed record (the
stage 2/3 mechanism); the agreement WORD now also covers the program digest, so a Lua difference is refused in the lobby, not a silent desync.
No new wire field: the protocol stays 5 [R: nothing here changes HELLO/ACCEPT or the lobby messages].

**Derived native tables by status mask.** Fighter values, hit rules (with their status bits), crit configuration are pure functions of the
build and WHICH statuses are present (`E:values/native_rules/crit_config` read presence, plus the Marked amount). Lua enumerates the 64
masks of {burn, chill, curse, haste, guarded, momentum}, computes the same ops the offline engine commits, de-duplicates them into
VARIANTS, and stages `mask -> variant`. The Marked (curse) amount is the only continuous input; it enters the incoming hit rule's `launch`
linearly, so the variant carries the index of that rule and the evaluator adds the amount. At runtime the evaluator only picks a variant when
the mask changes and applies it with the same setters stage 2 uses. This keeps the C free of the budget code and offline/online identical by
construction (same Lua functions produce the numbers).

**The evaluator (C), `pc/gameworld/script_mods_core.h` (pure, no game types) + `script_mods.inc` (hooks and setters).** State in game BSS:
per port 7 status slots {stacks, max, amount, expires, next_tick, cause}, the `recent[event]` frames, the frame counter, the bounded event queue,
the applied variant and mask. It is inside the rollback snapshot like every other piece of match state. One tick per logic frame from
`ScriptGame_StageFrame` (which runs on resimulated frames too): sample percent/grounded/stocks/position, expiry + Burn + interval events
(same order as `begin_frame`), drain the queue (same rules: depth 8, budget 64, queue 128, KO clears statuses), then apply outputs through
the existing setters: percent (the `SetPercent` choke point, boss guard intact), timed armour, intangibility, forced-crit count, the
interrupt window (`ScriptGame_IntrWinSet`), Shock mirror, and the variant.

**Event sources, all inside the simulation (never the post-frame host queue):**
hit_dealt/hit_taken from `ScriptGame_ReportHitContext` (carries move tag, element, grounded, percents); ko_dealt/stock_lost from the
`Script_GameEvent` 14/15 sites; landing (4), jump/air_jump/ledge_grab/grab/throw/taunt/shield_hit/perfect_shield (16 by category) tapped at the
top of `gw_Script_GameEvent`, un-gated by resimulation; technique rows (lcancel*, wavedash, tech, air_dodge, combo, combo_end, ...) from
`script_skill_emit`; clank from the clank observer; crit from `ScriptGame_CritHit`; armour absorbed from the armour reaction.
Sub-fighters are ignored exactly as the Lua host ignores them.

**Hash.** The evaluator's word (program digest, statuses, recent frames, frame counter, queue) is mixed into `ScriptGame_BuildHashWord`, so it is
in `RB_GameHash` and the curated hash with no change to `fighter.c`. The live fighter values and hit rules were already in that word (stage 2),
so a wrong variant also shows. 0 when no program is applied: matches without one hash exactly as before.

**Offline untouched.** The Lua engine keeps its own state and its own path; the native evaluator is inactive without an applied program. The
only Lua-side edits are additive (`trigger_program`, a wider `online_safe`, `program` passed to `gd.netbuild_stage`).

## 3. Known differences from the offline engine (documented, not bugs) [D]

1. Latency: offline, effects land with the post-frame commit (one logic frame after the event); online they land in the same frame's tick.
2. Numbers: Lua uses doubles, C floats for amounts and percents; the parity harness allows 1e-4 on percent deltas and exact on frames/stacks.
3. Presentation (shaders, afterimage, toasts, trace lines, `fired` log) stays Lua and reads `gd.netmods()`; any presentation not wired in this
   lane is listed as owed in the report. Trace/origin strings are not computed natively.
4. The Lua engine's frame counter starts at its creation; the native one at the match arm. Intervals are relative to it in both.

## 4. Slices and proofs

| # | Slice | Proof |
|---|---|---|
| a | `E:trigger_program`, `online_safe` widened to every record the program covers, program staged with the build, word covers it | Lua: every triggered record compiles; compile is byte-identical across fresh processes (hash seeds) |
| b | `script_mods_core.h` + standalone C test | parity: a Lua generator runs the REAL `mod_engine` on scripted event sequences (all 38+ triggered records, chains, KO, expiry, Burn, interval, crit_next, remove_status counts) and writes a fixture; the C test replays it and compares statuses/stacks/expiry/damage per frame |
| c | `script_mods.inc` hooks, setters, hash, `gd.netmods()`, host staging and apply | game-side C syntax check as PPC; native suite `netmods` in the exe; state restore (memcpy) exactness test |
| d | Two real clients over loopback: triggered builds firing, `MELEE_NET_SIM` lag/jitter/loss, long sets | 0 desyncs; hash-injection negative control (poison one status word) trips; curated SyncTest |
| e | Regression | `pc/tests/envoy_*.lua` all pass (72 at the base: all green once the scratch root has `tools/` and `_build/tmp`); netplay lobby/netbuild native suites |

## 5. Not in this lane

Cooperative, CPUs online, drops, Classic/Adventure online, the echo records (they need the echo journal), any protocol bump, any server change.
Netplay tests use the local matchmaking server on 127.0.0.1 only, `MELEE_NETPLAY_BIND=127.0.0.1` on both clients (firewall prompt otherwise),
windows at 30000, at most two games at once.
