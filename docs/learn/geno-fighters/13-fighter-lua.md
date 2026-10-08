# 13. A move written as Lua

Status: **complete for what is built**, 2026-10-08 (slice 5, two real moves). Everything below was run headless on the vanilla disc (the proof scripts of both fixtures, the native
sandbox test, the suite, the bench SyncTest); nobody has played either move, so the **feel** (timings, ranges, damage) is unreviewed. The format number is `"geno": 10`. Engine reference:
game repo `docs/geno.md` section 23. Where this packet and that section disagree, the reference wins for facts.

A `define` (packet 11) can write a Geno state's behaviour as a Lua function instead of script words. This is not `gd` scripting: the Lua runs inside the fighter's own state machine,
has no `gd`, cannot read the disc or the clock, and keeps nothing between calls except a small **typed state** you declare. That is what lets a savestate, a rewind and the rollback hash
cover it. Use it when a move needs to *decide* (count, compare, scale by something the game just told it, choose the next phase); keep using words for the animation and the hitboxes.

## 1. The shape, from two real moves

| fixture (`melee/pc/geno/mods/`) | kind of move | what the Lua decides |
|---|---|---|
| `vanilla-charger` | a charge special: hold B, release to strike | counts the held frames, ends the charge, sets the dash speed and the hit's damage from the count |
| `vanilla-riposte` | a counter with a follow-up: down B | cancels or ends the stance, scales the answer by the hit it countered, turns the fighter toward an attacker behind, chains a second strike on A, keeps a streak across moves |

The second one, trimmed (`vanilla-riposte/geno.json`):

```json
"lua": { "script": "lua/riposte.lua", "state": { "power": "float", "streak": "int", "follow": "bool" } },
"states": [
  { "name": "Parry", "behavior": "geno.ground", "subaction": 295, "like": "motion:349", "phys": "auto", "coll": "both", "iasa": "none",
    "counter": { "from": 4, "to": 24, "target": "geno:Riposte" },
    "lua": { "enter": "parry_enter", "frame": "parry_frame" } },
  { "name": "Riposte", "behavior": "geno.ground", "subaction": 296, "like": "motion:345", "phys": "auto", "coll": "both",
    "lua": { "enter": "riposte_enter", "frame": "riposte_frame" } },
  { "name": "Follow",  "behavior": "geno.ground", "subaction": 297, "like": "motion:343", "phys": "auto", "coll": "both",
    "lua": { "enter": "follow_enter", "frame": "follow_frame" } } ],
"specials": { "lw": "geno:Parry", "air_lw": "geno:Parry" }
```

Two things are split on purpose. **The engine owns the counter window**: `counter` (frames 4 to 24 of the state, packet 5's mechanism) drops the hit's damage and knockback and sends the
fighter to `Riposte`; Lua cannot open or close a window. **Lua owns everything it can decide**: what the answer is worth, whether the stance may be cancelled, what comes next. The
animation and the hitboxes of each state are still small words scripts (`moves/*.genoasm`, assembled to `.words`); Lua only overwrites the damage.

## 2. The module

A module is a file that returns a table of functions. Each function gets one argument, `ctx`, and may run on a state's `enter` (once, as the state begins) or `frame` (once per logic
frame while it runs):

```lua
local MIN_POWER, MAX_POWER, SCALE = 9, 30, 1.5
local M = {}
function M.riposte_enter(ctx)
  local s = ctx.state
  s.streak = math.min(s.streak + 1, 4)
  s.power = math.min(MAX_POWER, math.max(MIN_POWER, SCALE * ctx.self.hit_damage)) + (s.streak - 1)
  if ctx.self.hit_from < 0 then ctx.turn() end   -- the attacker is behind: face them
  ctx.velocity(0.9, 0)
end
function M.riposte_frame(ctx)
  ctx.hitbox_damage(3, ctx.state.power)
  if ctx.input.attack_pressed and not ctx.state.follow and ctx.self.action_frame >= 6 and ctx.self.action_frame <= 16 then
    ctx.state.follow = true
    ctx.go("Follow")
  end
end
return M
```

### What ctx has

| | |
|---|---|
| `ctx.input` | `attack`, `special`, `jump`, `shield`, `grab`, each as `_held` and `_pressed`; `stick_x`, `stick_y`, `stick_fwd` (positive = the way you face) |
| `ctx.self` | `air`, `anim_ended`, `facing` (+1 right, -1 left), `percent`, `x`, `y`, `vel_x`, `vel_y`, `action_frame`, `motion`, and what the **last hit taken** left: `hit_damage` (before a counter negated it), `hit_from` (+1 the attacker is in front of you, -1 behind, 0 unknown), `countered` (hits countered since the fighter was reset) |
| `ctx.state` | your declared slots, by name: `int`, `float` or `bool`, at most 16. An undeclared name, a float into an int slot, or a number into a bool slot is a fault |

### What ctx can do (commands, applied in order when the function returns; at most 8)

| | |
|---|---|
| `ctx.go(name)` | go to the Geno state of that name, or `"auto"` (Wait on the ground, Fall in the air) or `"helpless"` |
| `ctx.velocity(forward, up)` | `forward` is relative to the way you face (after any `ctx.turn()` queued earlier in the same call); on the ground it is the ground speed |
| `ctx.hitbox_damage(mask, damage)` | set the damage of the live hitboxes, bit n of `mask` = hitbox slot n (1 to 15) |
| `ctx.loop()` | restart the animation, the state's variables kept (a clip shorter than the move) |
| `ctx.turn()` | flip the facing |

### Rules that bite

- **`ctx.self.action_frame` is the move's own clock: it does not advance during hitlag.** A counter that lands freezes both fighters for several frames, so the Riposte's frame 6 is about
  frame 13 of what `gd.player(1).action_frame` shows. Write windows in the move's clock (what `counter.from`/`to` and the words scripts use) and convert when you drive it from a test.
- Constants are `local`s at the top of the file. A table of constants must be wrapped in `freeze{...}`. A function may not assign a variable it captured, a global, or a field of a table
  it captured (`count = count + 1` in a function is refused when the module loads): state is `ctx.state` or nothing. Helpers are `local function`s.
- There is no `pairs`, `pcall`, `string`, `table`, `os`, `io`, `load`, metatables, randomness or clock. `math` is `abs min max floor ceil sqrt tointeger huge pi`.
- `ctx.state` persists across states and moves: the Riposte's `streak` survives from one counter to the next until a whiff resets it. It is zeroed when the fighter spawns.
- A call may run 10,000 VM instructions, grow the heap by 64 KB and queue 8 commands. Past that, or on an error, or on a typo in a slot name, the call is a **fault**: its writes are
  dropped, the fighter is sent to Wait or Fall, and `gd.fighter_lua(1).faults` counts it. A fault is a bug in your module: read the first lines of the log (`geno: lua fault ...`).
  (Until online play for defines exists, a fault never ends a match; that is an open decision, section 23.3.)

## 3. Check it, offline

`python -m tools.geno.check <mod folder>` reads the module's text against the engine's own API (it reads `geno_lua_core.h`, so it cannot drift) and tells you, with a line number:

- a `ctx` field, `ctx.self` or `ctx.input` name that does not exist (`ctx.self.hit_dmg`),
- a name the sandbox does not have (`pairs`, `string.format`, `math.random`),
- a slot you use but did not declare, and a literal of the wrong type for a slot (`flag = 1` for a bool, `n = 1.5` for an int),
- `ctx.go("Name")` naming no state; a state function the module lacks; a state nothing targets,
- a `hitbox_damage` mask outside 1 to 15, and `"lua"` in a file below `"geno": 10`.

It does not run the module: the sandbox itself (closure scan, budgets) runs when the game loads the mod. `python -m tools.geno.new my-counter --template lua-counter --output <dir>`
writes a ready format-10 starting point (a counter, a one-state answer, one Lua file) that already checks clean.

## 4. Test it in the LAB (what was run, so you can repeat it)

- The sandbox rules: `tools/port/build.sh --native-test geno-lua` (no game needed). The game half: `run.sh --test` (`geno_lua_*`).
- Load the mod: `mode=lab;p1=geno:vanilla-riposte/hu;p2=mario/cpu0`. `gd.fighter_lua(1)` reads `{profile, faults, last_fault, state = {power=..., streak=..., follow=...}}`;
  `gd.player(1).action` is 1024 (Parry), 1025 (Riposte), 1026 (Follow). The demo `pc/scripts/examples/demos/geno-define-riposte/` has keys (1 stance, 2 short stance,
  3 CPU jab, 4 CPU in front).
- The proof is `scripts/proof.lua`, run headless as a script mod beside the fighter and `geno-lab`: it drives P2 as a script-mode CPU, jabs inside the window and
  checks the counter, the damage scaling (`1.5 x` the hit, clamped 9 to 30, `+1` per hit of the streak), the follow-up (`0.6 x`), the whiff and the early cancel breaking the streak,
  the turn when hit from behind, `gd.rewind_test` with `diff_compared == 0`, and zero faults. The Charger has the same kind of proof for charge, release and savestate.
- `scripts/cycle.lua` repeats stance, counter and follow-up with both fighters on `gd.input` for the bench SyncTest
  (`MELEE_SYNCTEST_BENCH=1 MELEE_SYNCTEST_CURATED=1 MELEE_SYNCTEST=12`).

## 5. What it cannot do yet

Per-frame physics or collision in Lua, looking at opponents beyond `hit_from`, grabs and throws, articles, effects and sounds as commands, a counter window Lua opens itself, Lua for an
attach (m-ex) fighter, Lua on an online match. Rank and order: `10-known-gaps.md` and geno.md 23.6. A move that needs one of these today is words, native behaviours or a later slice.

## Try it

Copy `vanilla-riposte`, change `SCALE` and the follow-up window, run `tools.geno.check`, then run the proof's step 2 in the LAB and watch `gd.fighter_lua(1).state.power`. Then break
something on purpose (`ctx.state.powr = 1`) and read both what `check` says and what the engine logs.

## Sources

- game repo `docs/geno.md` section 23 (API, enforcement, verification); `pc/platform/geno_lua_core.h` (the sandbox and `ctx`); `pc/geno/geno_game_lua.inc` (when it runs, what it reads, how commands apply)
- `pc/geno/mods/vanilla-charger/`, `pc/geno/mods/vanilla-riposte/` and their demos under `pc/scripts/examples/demos/`
- `tools/geno/lua_check.py`, `tools/geno/check.py`, `tools/geno/new.py` (`--template lua-counter`)
- brief and as-built record: `docs/superpowers/plans/2026-10-07-geno-slice5-fighter-lua.md`
