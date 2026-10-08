# 13. A move written as Lua (stub)

Status: **stub**, 2026-10-07 (slice 5, first increment). Everything below was run headless on the vanilla disc (the Charger's proof script, the native sandbox test, the suite);
nobody has played it, and looks and feel are unreviewed. The API shape and its limits are not final: the owner has not signed them off (brief:
`docs/superpowers/plans/2026-10-07-geno-slice5-fighter-lua.md`). Engine reference: game repo `docs/geno.md` section 23.

A `define` (lesson 11) can write a Geno state's behaviour as a Lua function instead of script words. This is not `gd` scripting: the Lua runs inside the fighter's own state machine,
has no `gd`, cannot read the disc or the clock, and keeps nothing between calls except a small **typed state** you declare. That is what lets a savestate, a rewind and the rollback hash
cover it.

## 1. The shape

`pc/geno/mods/vanilla-charger/` is the example: hold B to charge (up to 60 frames), release to strike; the dash and the hit's damage grow with the charge.

```json
"lua": { "script": "lua/charger.lua", "state": { "charge": "int", "charged": "bool" } },
"states": [
  { "name": "Charge",  "behavior": "geno.ground", "subaction": 295, "like": "motion:343", "phys": "auto", "coll": "both", "iasa": "none",
    "lua": { "enter": "charge_enter", "frame": "charge_frame" } },
  { "name": "Release", "behavior": "geno.ground", "subaction": 296, "like": "motion:343", "phys": "auto", "coll": "both",
    "lua": { "enter": "release_enter", "frame": "release_frame" } } ],
"specials": { "n": "geno:Charge", "air_n": "geno:Charge" },
"subactions": [ { "index": 295, "file": "moves/charge.words" }, { "index": 296, "file": "moves/release.words" } ]
```

The file says `"geno": 9`. The state still has an animation and (for the strike) a words script with the hitboxes; the Lua decides **when** things happen: it counts, it chooses the next
state, it sets the speed and the damage. `python -m tools.geno.check` knows the keys, checks that every function a state names exists in the module, that `ctx.go("Name")` names a state
(so the state is not reported unreachable) and that a `state.<name>` you spell out is a declared slot (a slot reached through a local alias is only caught at run time, as a fault).

## 2. The module

A module is a file that returns a table of functions. Each function gets one argument, `ctx`:

```lua
local M = {}
function M.charge_enter(ctx) ctx.state.charge = 0 end
function M.charge_frame(ctx)
  local s = ctx.state
  if ctx.input.special_held and s.charge < 60 then s.charge = s.charge + 1
  else ctx.go("Release") end
end
return M
```

- Read: `ctx.input` (buttons held / pressed, the stick), `ctx.self` (air, facing, position, velocity, action frame, ...), `ctx.state` (your slots).
- Act with commands, applied in order when the function returns: `ctx.go(name)`, `ctx.velocity(forward, up)`, `ctx.hitbox_damage(mask, damage)`, `ctx.loop()`.
- Constants are `local`s at the top of the file. A table of constants must be wrapped in `freeze{...}`. A function may not assign a variable it captured, a global, or a field of a table
  it captured (`count = count + 1` in a function is refused when the module loads): state is `ctx.state` or nothing.
- There is no `pairs`, `pcall`, `string`, `table`, `os`, `io`, `load`, metatables, randomness or clock. `math` is `abs min max floor ceil sqrt tointeger huge pi`.
- A call may run 10,000 VM instructions, grow the heap by 64 KB and queue 8 commands. Past that, or on an error, or on a typo in a slot name, the call is a **fault**: its writes are
  dropped, the fighter is sent to Wait / Fall, and `gd.fighter_lua(1).faults` counts it. A fault is a bug in your module: read the first lines of the log (`geno: lua fault ...`).

## 3. Test it (what was run, so you can repeat it)

- The sandbox rules: `tools/port/build.sh --native-test geno-lua` (no game needed).
- The suite: `run.sh --test` (the `geno_lua_*` cases).
- The move in the LAB: `mode=lab;p1=geno:vanilla-charger/hu;p2=mario/cpu0`. `gd.fighter_lua(1)` reads `{profile, faults, last_fault, state = {charge = ..., charged = ...}}`;
  `gd.player(1).action` is 1024 (Charge) then 1025 (Release). The demo `pc/scripts/examples/demos/geno-define-charger/` has keys; its `scripts/proof.lua` is the headless
  proof (charge counts per held frame, release keeps the charge, the hitbox damage is `6 + 0.15 x charge`, a savestate load restores the charge, `gd.rewind_test` reports
  `diff_compared == 0`).

## 4. What it cannot do yet

Per-frame physics or collision in Lua, looking at opponents, grabs and throws, articles, effects and sounds as commands, Lua for an attach (m-ex) fighter, Lua on an online match.
Rank and order: `10-known-gaps.md` and geno.md 23.6. A move that needs one of these today is words, native behaviours or a later slice.
