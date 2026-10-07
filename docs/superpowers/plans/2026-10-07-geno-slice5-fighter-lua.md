# Geno slice 5: fighter Lua, build brief and first increment (2026-10-07)

**Status: written before the code, then executed on game `agent/geno-s5` / workspace `ws/geno-s5`; section 8 records what was built and where it differs.** Not merged. It builds on the road in
`docs/superpowers/plans/2026-10-05-geno-full-fighter-slice2.md` (slice 5 section; decisions D1, D2, D8 apply unchanged) and on the design's section 4
(`docs/superpowers/specs/2026-10-04-geno-full-fighter-design.md:128-140`). Where this brief and that road differ, this one wins for slice 5.

Tags: **[R]** read from source (`path:line`; relative to the game checkout `melee/` unless it begins `docs/`, `tools/`), **[I]** inferred, **[U]** unverified,
needs a test. Line numbers move; re-grep before editing. The first increment is deliberately small: ONE typed-state charge special as a Lua callback, with
the state in snapshotted memory and in the rollback hash. Items marked "later" below are not built by this increment.

## 1. What exists (read from source)

- A Geno state is Melee motion `0x400 + n`; its `MotionState` row (animation, flags, four callbacks `anim/iasa/phys/coll`) is built at spawn from `geno.json`
  [R `pc/geno/geno_game_v2.inc:305-360`, `pc/geno/geno.h:262-271`]. Callback names resolve through one table [R `geno_game_v2.inc:911`], behaviours through
  another; the anim callback `next` ends a state at the animation's end [R `geno_game_v2.inc:516`].
- Entering a state goes through `geno_enter_state`, which runs the behaviour's `enter` routine last [R `geno_game_v2.inc:407-470`]. Specials are bound to
  states by `Geno_SpecialEnter` [R `geno_game_v2.inc:1075`]; the Striker's charge special is two such states driven by script CHG checks and `MOVE_I0`
  [R `pc/geno/mods/vanilla-striker/geno.json` states `NCharge`/`NRelease`, `moves/n_charge.genoasm`].
- All per-fighter Geno state is one game global, `Geno_StateBlock[6][2]`, which the snapshot restores because an uninitialised global is a common symbol that
  `gw_snap.c` walks [R `pc/geno/geno_game.c:100-112`, `docs/geno.md` section 4]. The rollback hash folds `GenoDefine_StateDigest` for defined kinds only
  [R `pc/geno/geno_game.c:2331`, `src/melee/ft/fighter.c:3988-3992`].
- The registry (native half, x86) parses `geno.json` and answers the game half with scalars [R `pc/platform/geno_registry.c:1-30`]; the game half is compiled
  through gwtool, big-endian, and calls a native `gw_X` as `X` [R `pc/platform/CLAUDE.md` "Naming the boundary"]. A game pointer is directly dereferenceable
  natively, every field behind it big-endian [R `pc/platform/gw.h:1-14`].
- Lua today: ONE native `lua_State` for every `gd` script, with an instruction-count hook [R `pc/platform/gw_script.c:7400-7405`], libraries kept or removed by
  `gs_build_base` [R `gw_script.c:6702-6760`]. Script permissions are manifest flags: `gameplay` (the script changes the game) and `rollback_safe`, which is
  retained metadata and permits nothing online; in a netplay or rollback session every Lua gameplay write is refused [R `docs/scripting.md:190-195,240-248,672`].
- The Lua source is vendored, pinned 5.4.7, with its internal headers [R `pc/third_party/lua-5.4.7/src`, `tools/port/build_objects.py:85-96`].
- Defines are offline only until slice 7 [R slice-2 plan D2; `docs/geno.md` section 22 last paragraph].

## 2. Scope of the first increment

**In:** a native fighter-Lua domain (one `lua_State` per profile, library-less, frozen); module load and static checks; per-state `enter` and `frame` callbacks;
a typed per-fighter state block (up to 16 int/float/bool slots) in snapshotted game memory and in the rollback hash for fighters that declare one; three
commands (`go`, `velocity`, `hitbox_damage`) applied by the game half at the callback boundary; deterministic budget faults; the fixture "Vanilla Charger"
(charge on hold, release strikes harder the longer it was held); a read-only `gd.fighter_lua(port)`; native tests; a headless LAB proof of charge/release and of
`gd.rewind_test` (`diff_compared == 0`); docs.

**Out (later):** `phys`/`coll`/`iasa` phases in Lua, `query`, `grab`, `throw_release`, `attribute`, article and FX commands, per-article state, a Lua planner for AI
(design section 4); `check` understanding Lua (S5-5 of the road); a LAB faults/budget display (S5-7); real match fault; online (slice 7).

## 3. Decisions taken

| # | Decision | Reason | Reversed if |
|---|---|---|---|
| L1 | Fighter Lua runs in its own `lua_State` per profile, in the native half, not in the `gd` state. | The `gd` state is shared, carries `gd`, and its hook policy is for scripts [R `gw_script.c:7400-7405`]; the design wants "a dedicated fighter Lua domain with no unrestricted `gd`" [R spec:130]. Per profile (not one global) so a registry swap in a test, or a hot reload, never aliases profile indices [R `geno_registry.c:1269` `gn_registry_clear`]. | Memory per profile matters at 94 defines (a state is ~25 KB [I]): share one state with per-profile module tables. |
| L2 | Lua is bound to a STATE: optional `enter` and `frame` functions named in the state's `"lua"` key. `frame` runs in the anim callback slot (new callback `lua`, which falls back to `next` at the animation's end if the function commanded no transition); physics and collision stay the named native callbacks. | It rides the existing row/callback machinery [R `geno_game_v2.inc:305-360,911`] and keeps Melee's landing, ledge and floor rules native. A Lua `phys` phase is the next increment, not this one. | A customer move needs per-frame position control: add `phys` as a third phase. |
| L3 | Typed state: `"lua": {"state": {"charge": "int", "armed": "bool", "angle": "float"}}`, at most 16 slots of 32 bits, in a new game global `Geno_LuaBlock[6][2]`, zeroed with the Geno block at spawn. NOT inside `GenoState` (its layout is a hot-reload "layout change" for every fighter [R `pc/geno/CLAUDE.md`]). | Snapshot coverage is by symbol, so a new common symbol is covered with no code [R `geno_game.c:100-106`]; the design's ceiling is 4 KiB [R spec:136], 64 bytes is enough for the first move and raising it is a constant. | A move needs more than 16 slots: raise `GENO_LUA_STATE_SLOTS` (a constant plus the block size; format unchanged). |
| L4 | The block is folded into `GenoDefine_StateDigest` ONLY when the profile declares typed state; a define without a `lua` block keeps today's digest bit for bit. | D8 of the road; the same pattern as slice 3's article digest [R `geno_game.c:2331-2400`]. | n/a |
| L5 | Statelessness is enforced three ways: (a) the module chunk is loaded with an environment that is a read-only proxy over a fixed allowlist (`type, select, ipairs, assert, error`, a pinned `math` subset, `freeze`; no `tostring`, which prints addresses); `pairs`, `next`, `pcall`, `load`, `rawset`, `rawget`, `setmetatable`, `getmetatable`, `string`, `table`, `os`, `io`, `debug`, `coroutine` do not exist; (b) after loading, every function's upvalues must be non-table values, or tables made by `freeze` (deep read-only proxies), and its bytecode must contain no `OP_SETUPVAL` (a closure that assigns a captured variable is mutable state); (c) every call gets a fresh `ctx`, and a full GC runs after the call so the heap at the start of every call is identical. | The design's acceptance blocker is "closure/global enforcement feasibility" [R slice-2 plan S5-1; spec:210]. `pairs` order and string hashes depend on a per-state random seed in 5.4 [I: `luai_makeseed`], so iteration order is banned, not trusted. (b) is checkable with the vendored internal headers [R path above]. | The bytecode scan proves unmaintainable across a Lua upgrade: pin the Lua version in the content id and re-audit on every bump. |
| L6 | Budgets: 10,000 VM instructions and 64 KiB of heap growth per call, 8 commands per call (the design's 10,000 / 64 KiB [R spec:134]; its 64 commands is raised only when more commands exist). Overflow, an error, or a bad command is a FAULT: the call's commands and state writes are dropped, the fighter's fault counter increments (in the block and the hash), and the fighter is sent to its landing/auto state so it cannot be stuck in a Lua state. | A fault must be tick-exact and identical on both peers [R spec:134]. State-abort is the smallest deterministic behaviour. **ELEVATE:** the design says a real match fault, not a fallback. | The owner wants a hard match fault: end the match on the first fault (one line in the game half). |
| L7 | Permissions: fighter Lua is content of a `kind: fighter` folder. It has no `gd`, so the `gameplay`/`rollback_safe` manifest flags do not apply to it; it is offline-only because define fighters are (D2). The read-only `gd.fighter_lua(port)` follows the other read accessors (no flag). | The flags govern what a script may do through `gd` [R `docs/scripting.md:190-195`]; fighter Lua cannot call `gd`. **ELEVATE** (API shape). | Defines go online (slice 7): Lua source and compiler version join the content id and the handshake. |
| L8 | No `"geno"` version bump: `lua` is read from a file declaring `"geno": 9` or more. An older build reads the file "for what it knows" and would ignore the key [R `geno_registry.c:1347-1351`]. **ELEVATE:** the road's D4 pattern says a new key set takes a new number (10). | The brief must not take a format number. The Charger fixture is `"geno": 9`; if the owner says 10, one constant and the fixture header change. | n/a |
| L9 | Lua source is part of the content id (appended to the profile hash like overlay words), so two installs with different scripts never share an id. | `gn_hash_node` covers the JSON only; overlay words are folded separately [R `geno_registry.c:1371-1385`]. | n/a |
| L10 | The fixture is a NEW define, "Vanilla Charger" (`vanilla-charger`, Mario donor, `"geno": 9`); the Striker is not edited. | The Striker's id and its tests must not move (slice 2 acceptance). The road's S5-6 (rewrite Striker's charge in Lua, compare frame by frame) is done on the Charger's copy of the same numbers. | n/a |

## 4. The API (proposed; ELEVATED for the owner)

```json
"lua": { "script": "lua/charger.lua", "state": { "charge": "int" } },
"states": [ { "name": "Charge", "behavior": "geno.ground", "subaction": 295, "like": "motion:343",
              "lua": { "enter": "charge_enter", "frame": "charge_frame" } } ]
```

```lua
local MAX = 60
local M = {}
function M.charge_enter(ctx) ctx.state.charge = 0 end
function M.charge_frame(ctx)
  local s = ctx.state
  if ctx.input.special_held and s.charge < MAX then s.charge = s.charge + 1 else ctx.go("Release") end
end
function M.release_enter(ctx) ctx.velocity(1.2 + 0.03 * ctx.state.charge, 0) end
function M.release_frame(ctx) ctx.hitbox_damage(3, 6 + 0.15 * ctx.state.charge) end
return M
```

`ctx.input`: `attack/special/jump/shield/grab` `_held` and `_pressed` booleans, `stick_x`, `stick_y`, `stick_fwd`. `ctx.self`: `air`, `facing`, `percent`, `x`, `y`, `vel_x`, `vel_y`,
`action_frame`, `motion`. `ctx.state`: the declared slots (reading or writing an undeclared name is a fault). Commands, applied after the call returns, in call order:
`ctx.go(stateName | "auto" | "helpless")`, `ctx.velocity(forward, up)` (forward is facing-relative; the ground speed on the ground), `ctx.hitbox_damage(mask, damage)` (as the
script word HBDMG, after staling). Numbers: Lua integers/floats in, narrowed to s32/f32 into slots (an integer outside s32 is a fault).

## 5. Tasks, in order

- **S5-1 Domain and enforcement** (`pc/platform/geno_lua.inc`, included by `geno_registry.c`; no new `.c`, so no link-list edit). Load, frozen env, `freeze`, math subset, upvalue
  and `OP_SETUPVAL` scan, hook-counted budget, allocator limit, fresh `ctx`, post-call full GC. Tests (registry half, `pc/platform/geno_lua_tests.inc`): a good module loads;
  each of: a global write, `pairs`, a mutable table upvalue, `count = count + 1` through an upvalue, a runaway loop, an allocation bomb, a non-s32 integer, an undeclared state
  slot, an unknown command argument, is refused or faulted with its reason; the same call twice gives identical results (stateless).
- **S5-2 Registry parse.** `lua` block (script file or inline `source` for tests), `state` layout, per-state `enter`/`frame`; states naming a missing function refuse a define;
  Lua source into the id; scalar accessors `Geno_LuaFn(p,s,phase)`, `Geno_LuaSlots(p)`, `Geno_LuaCall(p,s,phase,io)`. Tests: parse, refusal paths, id changes with the source,
  profiles without `lua` have unchanged ids (compare the Striker's and Hero's hex ids to literals).
- **S5-3 Game half.** `Geno_LuaBlock`, the io struct, `GenoGame_LuaRun`, callback `lua`, the enter hook in `geno_enter_state`, command application, fault handling, digest term.
  Tests (`geno_tests.c` game half): the charge counter counts frames while held and release leaves; digest 0 for a non-define, unchanged for a define without Lua, moves with a
  slot, restored by `snap_save`/`snap_load`; a fault sends the fighter to auto and is counted.
- **S5-4 `gd.fighter_lua(port)`** read-only (`gw_script.c`, additive) + `docs/scripting.md`.
- **S5-5 Fixture and demo.** `pc/geno/mods/vanilla-charger/` (text only: `geno.json`, `lua/charger.lua`, three small `.words` scripts), `tools/geno` `check` still passes (`lua` is an
  unknown key it must not reject: verify, fix in the checker if needed), demo `pc/scripts/examples/demos/geno-define-charger/`.
- **S5-6 Headless proof.** A LAB script (the demo with a `proof` mode) holds B, samples `gd.fighter_lua(1).state.charge` rising, releases, samples the Release motion and hit
  damage scaling, then `gd.rewind_test` mid-charge: `diff_compared == 0` and the slot restored. Run with `run.sh` offscreen (the machine allows several parallel headless games).
- **S5-7 Docs.** `docs/geno.md` section 23 (fighter Lua), `docs/learn/geno-fighters/13-fighter-lua.md` lesson stub, `docs/NEXT-SESSION.md` pointer.
- **S5-8 Regression.** `build.sh` OK, bridge fixpoint OK, ABI audit 0; full `run.sh --test` (baseline on this tree: 321 of 321 before any change).

## 6. Test plan (what proves what)

| claim | test |
|---|---|
| the domain is stateless and sandboxed | S5-1 refusal tests; same-input-same-output twice |
| budgets are deterministic | the runaway/allocation tests fault at the same count on every run |
| the state is rollback state | `geno_lua_snapshot` (save/mutate/load restores the block), LAB `gd.rewind_test` `diff_compared == 0` mid-charge |
| it is in the hash for defined Lua fighters only | `geno_lua_digest`: 0 for non-define; a define without `lua` has the same digest as before (literal); moves with a slot |
| no existing id or hash moves | Hero and Striker hex ids compared to literals; `RB_GameHash` literal test already in the suite stays green |
| charge/release behaves | game-half test with a capture harness, then the LAB run |
| nothing else broke | full suite, ABI audit |

## 7. Evidence limits

Written after reading the files cited; nothing in section 3 was run when written. Feel (the charge length, the strike) is not reviewed and no window was watched: the
increment is checked by logs, native tests and a headless LAB run, not by looking at it.

## 8. As built (2026-10-07)

Built on game `agent/geno-s5`, workspace `ws/geno-s5`. Tasks S5-1 to S5-8 are done; the deviations from section 5:

- S5-1 is a header (`pc/platform/geno_lua_core.h`) plus an **isolated native test** (`tools/port/build.sh --native-test geno-lua`, `pc/tests/geno_lua_test.c`, 11 refusals and 19 faults plus the positive cases), not a registry test: the same code
  is compiled into the exe and into the test, so the sandbox is tested without the game. The closure scan reads the vendored Lua's internal headers (`lobject.h`, `lopcodes.h`); a Lua upgrade must re-run that test.
- S5-2 registry code is `pc/platform/geno_lua_registry.inc`; no new `.c`, so no link-list edit. Fighter Lua is for **defines only** (an attach entry with `lua` is refused): attach fighters are not in the define hash path, so an attach fighter with
  Lua would have invisible state online.
- A fourth command, `ctx.loop()` (restart the animation), was needed because the clip of Mario's special row is shorter than a 60-frame charge, and `ctx.self.anim_ended` was added to the input.
- `gd.fighter_lua(port)` is `pc/platform/gw_script_fighter_lua.inc` (included by `gw_script.c`, two lines changed there).
- `check` (S5-5 of the road, brought forward because the fixture needs it): `tools/geno/check.py` `lua_checks`, schema keys, a `demo_scenarios.py` row; the generated schema and key reference were regenerated.
- Open items of section 3 are unchanged and are the report's Decisions: API shape and limits (L3, L6, L7), the format number (L8; measured: an older engine loads the Charger as a plain Mario define and ignores the Lua), the fault policy (L6).

Evidence (this build, vanilla disc, headless; nothing watched on screen): build OK with bridge fixpoint and ABI audit 0; native `geno-lua` all pass; `run.sh --test` 326 of 326 (baseline on this tree 321); LAB proof `PROOF RESULT: PASS`
(charge 13 after 15 held frames, release at 25, hitbox damage 9.750 = 6 + 0.15 x 25, savestate at charge 10 / load at 24 gave 11, `gd.rewind_test(120)` `pass=true`, `diff_compared=0`); Hero, Striker and Caster ids identical in the old and new exe;
bench SyncTest: 27,600 curated checks, mismatches only in P2's script frame counter (curated word 23), the same word that mismatches for a retail Mario P1 under the same input, the Charger's own record never.
Owed to a person: the feel of the charge and strike (nobody watched it), a real-rollback run (slice 7), play on a controller.
