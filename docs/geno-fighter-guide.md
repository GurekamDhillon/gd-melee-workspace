# Geno fighter author's guide

Current source contract, **2026-10-08**. This guide supersedes historical gameplay-authoring claims in `melee/docs/geno.md` where they conflict with the code cited here. The design history remains useful background. Paths beginning `melee/` refer to the separate game checkout selected by `GW_MELEE`; other paths refer to this workspace. A code citation establishes implementation, not a successful play test. The Pip evidence below states exactly what ran.

## Agent brief: read this first

Build an original **Geno engine fighter**, packaged as a `"geno": 10` native `define` with `base: "none"`. Its source art, gameplay scripts and Lua belong to you; its common engine callbacks and unnamed donor fields are still shared. Read this brief, [the artist specification](geno-artist-spec.md), [the animation checklist](geno-artist-checklist.md), and this guide's move/Lua/testing sections before authoring. Use the [generated row list](geno-artist-rows.md) and the field/attribute reference below as lookup tables. The reproducible [Pip sample](../ports/geno-artist-samples/pip/build.py) is the smallest complete worked example here.

- **Keep source and output apart.** Maintain `fighter.json`, original art, `.genoasm`, gameplay JSON and Lua. The artist builder replaces its generated package. Reapply custom gameplay in a maintained wrapper after every art build; do not patch the converter for one fighter. Sources: `tools/geno/artist/pipeline.py:113`, `tools/geno/artist/assemble.py:121`.
- **No disc-derived data in commits or shared packages.** Never add a retail model/archive, extracted disc image, m-ex table or converted source-game asset. Native authored output stays under `_build` for this workflow. `base: "mario"` refers to the user's installed retail assets; it does not authorize copying them. Sources: root `AGENTS.md` conventions; `tools/geno/check.py` `refusal_files`; `melee/pc/platform/geno_define_registry.inc:303`.
- **Artist contract:** one skinned mesh/material, at most **two influences per vertex**, normalized weights, 60 fps sampled animation, Blender Z-up/facing −Y, explicit required skeleton roles including `translation`, and no animated bone scale. Two influences is a converter limit. Sources: `tools/geno/artist/spec.py:29`, `:37`, `:41`, `:65`; artist spec §§2–5,8–10.
- **Do not treat a parser maximum as proven safe.** The artist contract advertises 252 source bones plus three generated joints, but the inspected native define backend still copies into a 128-byte joint-to-part table. Keep generated joint count at most 128 pending an engine fix/proof; Pip has 34. This is a source-level storage conflict, not a tested crash. Sources: `tools/geno/artist/spec.py:17`, `melee/pc/geno/geno_define_data.inc:24`, `:44`.
- **Separate the three move layers:** state/callbacks, animation row, and timed ftcmd script. A new Lua function cannot create a clip or hitbox. Bind intended ground/air specials; unbound entries can run donor behavior. Source: `melee/pc/geno/geno_game_v2.inc:408`, `melee/pc/platform/geno_registry.c:981`.
- **Fighter Lua is `ctx`, not `gd`.** Only `enter`/`frame`, declared typed state and the five registered commands are available. No Lua `on_hit`, article spawn, file access, random generator or hidden persistent mutable tables. Sources: `melee/pc/platform/geno_lua_registry.inc:127`, `melee/pc/platform/geno_lua_core.h:468`, `:594`.
- **Online means matching content and deterministic simulation.** Package/module/slot changes affect identity. Keep authoritative state in engine-owned fields or declared `ctx.state`; use deterministic native callbacks. Default faults roll back the call's writes and return to Wait/Fall. Read the identity exclusions and cross-platform caveats below. Sources: `melee/pc/platform/geno_registry.c:1423`, `melee/pc/platform/gw_mexid.c:268`, `melee/pc/geno/geno_game_lua.inc:170`.
- **Restart the process after each package rebuild.** Match restart and `lab reload` do not reload native defines. Pass static checks, then inspect the actual loaded package and input-driven behavior in the LAB. Visual feel, hitbox alignment and online rollback need their own evidence. Source: `melee/pc/platform/geno_registry.c:2007`.

The ordinary three-command artist loop is:

```text
python -m tools.geno.artist validate path/to/fighter.json -v
python -m tools.geno.artist build path/to/fighter.json
python -m tools.geno.artist run-command path/to/fighter.json
```

`run-command` **prints** a launch command; it does not start the game. On a new character first run `python -m tools.geno.artist new my-fighter --key my-fighter --name "My Fighter"`, then author the generated Blender file. For the worked special, use Pip's wrapper in place of plain `artist build`. Commands: `tools/geno/artist/__main__.py:14`, `tools/geno/artist/pipeline.py:92`.

Navigation: [package anatomy](#what-a-fighter-package-contains), [moves](#a-move-has-three-connected-pieces), [fighter Lua](#fighter-lua-belongs-to-the-fighter), [online identity](#online-admission-and-identity), [LAB](#a-repeatable-lab-authoring-loop), [Pip](#worked-example-pips-palm-skip), [field reference](#every-current-genojson-field-recursive), [attributes](#attribute-defaults-all-46-importer-values-plus-every-other-accepted-field), [contradictions](#contradictions-and-source-caveats).

## What a fighter package contains

`fighter.json` is **artist input**, not the runtime `geno.json`. The former locates art and supplies overrides to the converter. The latter declares runtime identity, effective attributes, animation/model resources, state graph, scripts and optional Lua. `mod.json` tells the mod loader the package id/name/version/kind and requirements. An attach augments an existing fighter; a define has its own stable roster key. For an original artist fighter use `base: "none"`, `common: "melee.common.v1"`, `resources: "mod:files"`. Sources: `tools/geno/artist/model.py:109`, `tools/geno/artist/assemble.py:154`, `melee/pc/platform/geno_define_registry.inc:260`.

```text
author-source/
  fighter.json, params.json      # artist inputs; params only needed by starter
  fighter.blend                 # original model, rig, actions, embedded textures
  art/fighter.glb[.geno.json]    # exported art and role/clip sidecar
  gameplay.json                 # your maintained state/special configuration
  moves/*.genoasm               # your timed scripts
  lua/*.lua                     # optional fighter module
output/mods/
  enabled.txt                   # enabled mod ids, one per line
  geno-lab/                     # offline author inspection companion
  my-fighter/
    mod.json
    geno.json
    moves/*.words               # assembled scripts actually named by geno.json
    lua/special.lua
    files/plan.json             # mapped joints, parts, hurtboxes, bank rows
    files/GnMyFighterAJ.dat     # authored animation bank
    files/GnMyFighter_default.dat
    # optional files/*.gxtex, files/*.gnsnd, FX packages
```

The artist builder derives roles, plan, model and bank, retargets Striker's default scripts by role, writes format 10, runs the package checker and installs the LAB companion. Models and animation bank are mounted by **basename**, so use a fighter-specific prefix. The Blender `.geno.json` sidecar is artist metadata and is different from the package's runtime file with the same suffix. Sources: `tools/geno/artist/assemble.py:25`, `:110`, `:170`; `tools/geno/artist/pipeline.py:107`; `melee/pc/platform/geno_define_registry.inc:5`.

`base: "none"` does not mean every engine field is newly authored. Common callbacks and unoverridden attributes still originate from the donor; ECB values emitted into the plan are not parsed as authored collision bounds. The parsed plan owns the mapped skeleton, supported joint fields, hurtboxes and bank. Do not mistake an `ecb`/role metadata entry for a functioning engine override. Sources: `melee/pc/geno/geno_define_data.inc:71`; `melee/pc/platform/geno_define_registry.inc:740`; artist spec §12; plan reference below.

The author tools read current game source via `GW_MELEE`. Use `python -m tools.geno.check PACKAGE` and `python -m tools.geno.schema --check`; there is no `python -m tools.geno check` dispatcher in this checkout. Generate schema artifacts with `python -m tools.geno.schema` when the game contract changes, then review the diff. A schema pass and `geno check` are useful gates; the runtime parser and registered callback tables remain the authority. Sources: `tools/geno/check.py:672`, `tools/geno/schema.py:309`, `tools/geno/__init__.py:1`.

## A move has three connected pieces

An **action state** controls what the fighter does each frame: animation handling, input/cancels, physics, and collision. An **animation/subaction row** selects the clip and its ftcmd script. The **ftcmd script** opens and closes hitboxes, sets animation rates and script flags, and can register transitions. Editing the script does not create an animation or a new input callback.

| Piece | Authoring surface | What it changes |
|---|---|---|
| Existing normal, aerial, grab, or throw | `subactions[]` overlay for the row's numeric `index`; optional `common_states[]` for a define | The effective script; optionally the motion's subaction, flags, move id, and named callbacks |
| New move state | `states[]` with a native `behavior`, `subaction`, and optional callback overrides | A new Melee state, motion id `0x400 +` its zero-based position in `states` |
| Special input | `specials.n/s/hi/lw/air_n/air_s/air_hi/air_lw` | Which target the game's B input enters |
| Per-frame decision logic | Define-level `lua` plus `states[].lua.enter/frame` | Stateless Lua callbacks that read input/self, change declared typed state, and queue a small set of commands |

State `name` resolves JSON targets such as `"geno:Release"`. The standalone assembler has no fighter context, so its `CHG geno:1 ...` uses the state index; the Python assembler API can resolve names when supplied the state list. Reordering states therefore changes numeric script targets. A numeric `subaction` is an animation/script row, **not** the motion id. The LAB's `anim_id` is that row number. (`melee/pc/geno/geno_game_v2.inc:408`, `melee/pc/platform/geno_registry.c:860`, `melee/pc/platform/geno_define_registry.inc:318`, `melee/pc/geno/geno_define_rows.inc:5`, `tools/geno/script.py:124`; reference `melee/docs/geno.md:1617`.)

`like` gives the new state another motion row's flags, move id and camera callback. It does not automatically adopt all its behavior callbacks: use a callback value `"like"` explicitly when you mean that. `next` is the animation-end target. `auto` becomes Wait on the ground and Fall in the air; `helpless` becomes Wait on the ground and FallSpecial in the air. `phys: "auto"` uses friction on the ground and normal gravity/drift in the air. `coll: "both"` lets a move keep the same state while its ground/air situation changes. (`melee/pc/geno/geno_game_v2.inc:518`, `:606`, `:617`, `:675`; `melee/docs/geno.md:1637`.)

For ordinary new states, start with `geno.ground` or `geno.air`. The default IASA callback for both is `none`. If the script contains `iasa`, add `"iasa": "interrupt"`: the word sets `allow_interrupt`, then the callback opens normal Wait/Fall inputs while that flag is true. With no callback, the flag alone does not make the move cancel. (`melee/pc/geno/geno_game_v2.inc:971`; `melee/pc/geno/geno_game_specials.inc:703`; `melee/src/melee/ft/ftaction.c:519`.)

## Author and assemble a hitbox script

Write a `.genoasm` text file, assemble it to the whitespace `.words` file that `geno.json` names, and check the package:

```text
python -m tools.geno.asm mods/my-fighter/moves/jab.genoasm -o mods/my-fighter/moves/jab.words --words
python -m tools.geno.check mods/my-fighter
python -m tools.geno.report mods/my-fighter --frames
```

Example script shape (replace `joint=0` with the correct joint on your skeleton):

```text
PUT ANIM_RATE 1.0
wait 5
hitbox slot=0 joint=0 damage=8 size=3.5 x=0 y=5 z=4 angle=45 kbg=90 bkb=30
wait 3
clear_hitboxes
wait 12
iasa
```

`wait N` waits N script frames relative to the current timer. `wait_until N` waits until absolute script frame N. Changing `ANIM_RATE` changes the animation and the ftcmd pace together; it is not a separate physics speed multiplier. The loader appends End when reading an overlay, and the assembler does not append it. End stops commands; the state's animation-end callback still determines when the move leaves its state. Keep the clip long enough for the entire move script, including recovery and IASA. A short clip can return to Wait before a later hitbox ever opens. (`melee/src/melee/lb/lbcommand.c:20`, `:27`; `melee/src/melee/ft/ftaction.c:1349`; `melee/pc/geno/geno_game_v2.inc:518`; `tools/geno/README.md:50`; `melee/docs/geno.md:2835`.)

| Friendly `hitbox` field | Meaning and units |
|---|---|
| `slot` | Fighter hitbox slot 0–3; four simultaneous fighter hitboxes |
| `joint` | Zero-based joint index on the loaded skeleton; find it in the LAB or `artist joints` |
| `damage` | Percent damage, rounded to an integer by this encoder, 0–1023. Use `HBDMG` after creation for a fractional or computed value |
| `size` | Sphere radius in game units, quantized to 1/256; 0–65535/256 |
| `x/y/z` | Bone-local offsets in game units, quantized to signed 1/256; −128 through 32767/256. These axes follow the bone's pose, not the world |
| `angle` | Melee angle encoding, 0–511; 361 is the special Sakurai-angle rule |
| `kbg` | Knockback growth, 0–511 |
| `fkb` | Weight-set/fixed knockback field, 0–511; LAB reads it as `wbk` |
| `bkb` | Base knockback, 0–511 |
| `element` | Melee hit element, 0–31 |
| `shield` | Additional shield damage, signed −128–127 |
| `ground/air` | 0 or 1: whether the box may hit a grounded/airborne victim |

The friendly command defaults to damage 8, radius 4, angle 361, KBG 100, both ground and air enabled; unspecified joint, offsets, fixed/base knockback, element and shield damage are zero. It also encodes hit sound fields from its element. Raw opcode fields have different rules: for example `gfx offsetY=256` is an encoded integer, not a coordinate of 256 game units. Check `tools/geno/reference.md` before using generic named fields. The convenient `hitbox x/y/z` coordinates are intentionally tied to the observed bone-local offsets; the decomp's generic `z_offset`/`x_offset` names should not be used to reinterpret them. (`tools/geno/script.py:205`; `ports/ir/tools/acmd_to_ftcmd.py:127`; `melee/src/melee/ft/ftaction.c:335`; `tools/geno/README.md:74`.)

`HBDMG 3 9.75` sets slots 0 and 1 to 9.75% after creating them: masks are bits, so `3 = 1 | 2`, not hitbox number 3. `HBSTUN mask N` adds up to 255 hitstun frames; `HBFLAGS` declares `NO_HITLAG`, `FLINCHLESS`, `ZERO_DAMAGE`, or `FORCE_REACTION`. They are per-action settings. `REHIT mask N` clears those hitboxes' victim lists every N non-hitlag action frames; it is a periodic clock from the command, not a separate cooldown per victim. `LINK` launches along the attacker's momentum and is an approximation of source-game autolink angles. (`melee/pc/geno/geno_game.c:2163`, `:2186`; `melee/pc/geno/geno.h:186`; `melee/docs/geno.md:1482`.)

### Keep the frame clocks distinct

The source currently exposes several clocks. Record the clock with each result:

| Clock | Concrete current convention |
|---|---|
| `.genoasm` waits and `tools.geno.report --frames` | The report begins at 0 and sums `wait`; a first `wait 5` puts `start=5` in this report |
| `gd.timeline` / `lab events` | Event `frame = cumulative wait + 1`; the same first `wait 5` appears at event frame 6 |
| `gd.player(1).action_frame` | Diagnostic state counter reset to 0 when its post-frame sampler first sees a changed motion; the documented rate-1 sampling of first `wait N` sees the box at about `N−2` |
| `gd.player(1).anim_frame_f` | The engine's fractional animation frame, distinct from a sampled logic-frame count |
| `ctx.self.action_frame`, ftcmd `ACTION_FRAME`, native counter window | `GenoState.action_time`, incremented before the state's anim callback; frozen in hitlag, unlike the external diagnostic counter |

Do not subtract two from every `gd.timeline` number: the timeline itself adds one, while the static Python report does not. The current fixture report predicts `max(0, report_start / rate − 2)`, with a tolerance of one frame at rate 1 and two otherwise. This is a fixture measurement convention, not a universal conversion for a script with rate changes, loops, branching, hitlag, or chained states. Measure the actual input and sampled hitboxes for those moves. The LAB labels static IF/IFV timelines as conditional and shows their fall-through path. (`tools/geno/report.py:79`; `tools/geno/moves_check/moves_report.py:181`; `melee/pc/platform/gw_script.c:3784`, `:3879`, `:8977`; `melee/pc/geno/geno_game_lua.inc:131`; `melee/pc/geno/geno_game.c:1897`; `melee/src/melee/ft/fighter.c:1993`; historical measurement `melee/docs/geno.md:2815`.)

## Windows beyond damage hitboxes

**Intangibility.** `body_state state=2` makes the script's whole-body state intangible; `state=1` is invincible, `state=0` normal. The same 0/1/2 states exist for `hurtboxes_state` and `hurtbox_state bone_idx=N`. A single hurtbox command addresses the capsule on the named bone, rather than the capsule's list position. Make the return to normal explicit in your script and check both `gd.player().body_state` and `gd.hurtboxes`. Script body state and timed respawn/ledge intangibility are separate reads. (`tools/geno/reference.md:38`; `melee/pc/gameworld/script_lab.h:48`; `melee/src/melee/ft/ftaction.c:552`; `melee/src/melee/ft/ftcoll.c:3274`, `:3290`, `:3440`.)

**IASA and recovery.** `iasa` sets a flag, not the animation's length. A new ordinary Geno state needs `iasa: "interrupt"` to act on it. Existing normal rows already have their own input callbacks unless you replace them with `common_states`. Test an actual next action in the intended window as well as inspecting the flag. (`melee/src/melee/ft/ftaction.c:519`; `melee/pc/geno/geno_game_specials.inc:703`; `melee/pc/geno/geno_define_rows.inc:27`.)

**Aerial landing and autocancel.** The ordinary aerial callback uses `cmd_var idx=0 value=1` to enable the aerial's own landing lag; value 0 gives normal landing. The five `landingair*_lag` attributes supply the lag, and the retail L-cancel timing/divisor still apply. Courier's nair turns the flag on before its hitboxes and off after they close. A custom Geno special uses its own `land` target; when that is automatic and `landing_lag > 0`, the native collision callback uses LandingFallSpecial with that lag. With `coll: "both"`, landing changes the situation while retaining the state. Test landing in startup, active frames, recovery, and an autocancel window separately. (`melee/src/melee/ft/kinds/ftCommon/ftCo_LandingAir.c:18`; `melee/pc/geno/geno_game_v2.inc:617`, `:675`; `melee/pc/geno/mods/vanilla-courier/moves/nair.genoasm:1`.)

**Grabs and throws.** Work through the common Catch/CatchDash/CatchWait/CatchAttack and ThrowF/B/Hi/Lw flow. Grabs need the capture hitbox fields, not an ordinary damaging sphere; the current Courier grab deliberately uses raw words preserving the donor's capture setup. Pummels use their own script. A throw script configures `throw idx=0 ...` and its other throw record, then uses `throw_flag hit_idx=0` at release. `throw` alone does not grab someone or release a victim: the common throw callbacks and existing held victim are part of the move. Courier forward throw authors 6% and releases after its waits. Test Z catching a victim, pummel, directional release, damage and victim launch. (`melee/pc/geno/mods/vanilla-courier/moves/grab.genoasm:1`; `.../fthrow.genoasm:1`; `melee/src/melee/ft/ftaction.c:714`; `melee/src/melee/ft/kinds/ftCommon/ftCo_Throw.c:245`; `tools/geno/moves_check/moves_check.lua:46`.)

**Specials.** Bind all intended ground and air entries. Missing air bindings use their ground counterpart; an unbound direction takes the underlying donor special. New states can run in both situations or use separate ground/air states. The normal input path asks `Geno_SpecialEnter` before entering retail/m-ex special code. Trigger donor/m-ex specials through input or the LAB's input rows: a bare motion change does not run a special's entry setup. (`melee/pc/platform/geno_registry.c:963`; `melee/pc/geno/geno_game_v2.inc:1082`; `melee/src/melee/ft/kinds/ftCommon/ftCo_Attack100.c:61`; `melee/src/melee/ft/kinds/ftCommon/ftCo_SpecialAir.c:29`; reference `melee/docs/geno.md:745`.)

**Counters and `on_hit`.** A state's `counter: {from:4,to:24,target:"geno:Riposte"}` checks the inclusive window against the native action clock. Default `negate` drops incoming damage and knockback before Melee applies them, leaves the existing hitlag, records the original damage, enters the answer state, then runs the fighter's `hooks.on_hit`. This Geno hook means **the fighter took a hit**, not that its attack connected. The general scripting callback `on_hit(attacker,victim,info)` is a separate post-frame event. `HIT_DAMAGE`, `HIT_PORT`, `HIT_COUNTER`, and `HIT_COUNT` are reads of the stored incoming-hit context. A counter can scale its answer with HBDMG or fighter Lua. (`melee/pc/geno/geno_game_articles.inc:1072`; `melee/docs/geno.md:2163`; general event reference `melee/docs/geno.md:426`.)

**Articles.** A projectile is a native Melee item. Declare it in `articles[]` and call `CALL geno.article.spawn 0` at the release frame. Index 0 selects the first declaration; it is not an item kind id. Declare lifetime, facing-relative spawn/velocity, caps/despawn behavior and item hitboxes. `start/end` are one-based frames of article life, `end:0` means through the end, and each active window hits a victim once until reopened. Article knockback uses `wkb` rather than the friendly fighter script's `fkb`; do not invent a universal field name. An article's `fx` package supplies visuals and its own named sounds can mark spawn/end. A define's Lua API currently has no article, FX, sound, grab or throw command; use the script/native data surfaces for those. (`melee/pc/platform/geno_registry.c:1074`; `melee/pc/geno/geno_game_articles.inc:541`, `:1035`; `melee/docs/geno.md:2116`, `:2208`, `:2610`, `:2944`; Caster fixture below.)

## Fighter Lua belongs to the fighter

A fighter module runs inside a Geno `define` state machine. It receives one `ctx` argument and uses its declared typed state to retain values between calls. It has its own Lua domain per profile and no `gd` table. General script-mod `gameplay` and `rollback_safe` manifest flags do not grant or restrict this fighter API. Native physics, collision, landing and ledge callbacks continue to run around the Lua state callback. Sources: `melee/pc/platform/geno_lua_core.h:3`, `melee/pc/platform/geno_lua_core.h:468`, `melee/pc/geno/geno_game_lua.inc:15`, `melee/pc/platform/gw_script_fighter_lua.inc:1`.

Use Lua for decisions that the registered fields and five commands can express. Use `.genoasm`/word scripts for hitbox geometry and timing, and native Geno state keys for counters, collision, physics and articles. The Charger combines word-script hitboxes with Lua charge/damage decisions; the Riposte combines a native counter window with Lua response decisions. Sources: `melee/pc/geno/mods/vanilla-charger/moves/release.genoasm:1`, `melee/pc/geno/mods/vanilla-charger/lua/charger.lua:30`, `melee/pc/geno/mods/vanilla-riposte/geno.json:32`, `melee/pc/geno/mods/vanilla-riposte/lua/riposte.lua:36`.

### Declare the module and callbacks

```json
{
"geno": 10,
"fighters": [{
  "define": {
    "key": "my-fighter", "name": "My Fighter", "base": "mario",
    "common": "melee.common.v1", "resources": "retail:mario"
  },
  "lua": {
    "script": "lua/special.lua",
    "state": {"charge": "int", "power": "float", "ready": "bool"}
  },
  "states": [{
    "name": "Charge", "behavior": "geno.ground", "subaction": 295,
    "like": "motion:343", "phys": "auto", "coll": "both",
    "lua": {"enter": "charge_enter", "frame": "charge_frame"}
  }]
}]
}
```

The root format must be at least 10 when either an entry or a state contains `lua`. Attach entries cannot contain fighter Lua. A state naming Lua requires the entry's module block. Exactly one of `lua.script` and `lua.source` is required: the former names text relative to the mod directory, the latter supplies inline text. Source length is 1–65,536 bytes measured with `strlen`; script paths containing `..` or `:`, or beginning `/` or `\`, are refused. Sources: `melee/pc/platform/geno_lua_registry.inc:56`, `melee/pc/platform/geno_lua_registry.inc:60`, `melee/pc/platform/geno_lua_registry.inc:64`, `melee/pc/platform/geno_lua_registry.inc:73`, `melee/pc/platform/geno_lua_registry.inc:84`.

The module returns a table whose string keys name Lua functions; no constants or C functions may be exported. At most 24 exported functions, each name shorter than 32 bytes, are allowed. Keep constants in locals and helpers as local functions. A reference to a missing exported function refuses the fighter at load. Sources: `melee/pc/platform/geno_lua_core.h:43`, `melee/pc/platform/geno_lua_core.h:525`, `melee/pc/platform/geno_lua_core.h:534`, `melee/pc/platform/geno_lua_registry.inc:135`.

Only `enter` and `frame` are fighter Lua phases. `enter` runs after the behavior's native entry routine. A `frame` binding installs the registered animation callback `lua` when the state has no explicit animation callback. That callback runs the function, then takes the state's ordinary `next` transition if the animation ended and the call did not change the action. An explicit different `anim` prevents this automatic callback assignment; declaring a frame function alone does not make it run through an unrelated animation callback. Sources: `melee/pc/platform/geno_lua_registry.inc:127`, `melee/pc/platform/geno_lua_registry.inc:141`, `melee/pc/geno/geno_game_v2.inc:455`, `melee/pc/geno/geno_game_lua.inc:258`.

The frame callback is in the animation phase of a logic frame, after animation/subaction script advancement and registered Geno change checks. A check that changes the action skips the old animation callback. Hitlag skips this phase, so `ctx.self.action_frame` does not count hitlag. Sources: `melee/src/melee/ft/fighter.c:1993`, `melee/src/melee/ft/fighter.c:2017`, `melee/src/melee/ft/fighter.c:2026`, `melee/pc/geno/geno_game.c:1883`, `melee/pc/geno/geno_game.c:1897`.

### Typed state

`lua.state` maps names to `int`, `float` or `bool`, with at most 16 slots. A name is 1–23 characters, begins with an ASCII letter or underscore, and otherwise uses ASCII letters, digits or underscores. Duplicate names are refused. Declare persistent move state here, then access it as `ctx.state.name`. Sources: `melee/pc/platform/geno_lua_registry.inc:33`, `melee/pc/platform/geno_lua_registry.inc:90`, `melee/pc/platform/geno_lua_core.h:45`, `melee/pc/geno/geno.h:495`.

| Slot type | Accepted writes and stored representation | Source |
|---|---|---|
| `int` | A Lua number exactly convertible to an integer in −2,147,483,648…2,147,483,647; stored as signed 32-bit bits. `1.0` is accepted when exactly integral. | `melee/pc/platform/geno_lua_core.h:233` |
| `float` | A numeric, non-NaN value with absolute magnitude at most `3.0e38`; narrowed to 32-bit float. | `melee/pc/platform/geno_lua_core.h:244` |
| `bool` | Lua `true` or `false`, stored as 1 or 0. Numbers are refused. | `melee/pc/platform/geno_lua_core.h:252` |

Unknown slot names and non-string keys fault on reads and writes. Slots start at zero (float 0, int 0, bool false) when the fighter resets; ordinary action changes do not zero this separate Lua block, so an `enter` function decides which move-local values to reset. Each fighter/partner has an independent block indexed by player and sub-fighter. Sources: `melee/pc/platform/geno_lua_core.h:208`, `melee/pc/platform/geno_lua_core.h:228`, `melee/pc/geno/geno_game.c:808`, `melee/pc/geno/geno_game_lua.inc:51`, `melee/pc/geno/geno_state.h:103`.

`lua.state` is currently optional and can be empty. For an authored fighter, declare at least one real slot when using Lua: the Lua digest and `gd.fighter_lua` currently require a positive slot count, including for reporting faults. Sources: `melee/pc/platform/geno_lua_registry.inc:90`, `melee/pc/geno/geno_game_lua.inc:79`, `melee/pc/geno/geno_game_lua.inc:283`. This is a source caveat, not a schema requirement imposed by the loader.

### Complete registered `ctx` API

`ctx`, `ctx.input` and `ctx.self` are fresh per-call snapshot tables. Their fields are inputs; assigning them does not mutate the fighter. `ctx.state` is the special proxy that writes the transactional state copy. Sources: `melee/pc/platform/geno_lua_core.h:594`, `melee/pc/platform/geno_lua_core.h:632`, `melee/pc/geno/geno_game_lua.inc:120`.

| Input fields | Type and meaning | Source |
|---|---|---|
| `attack_held`, `attack_pressed` | Booleans for the Geno attack button mask. | `melee/pc/platform/geno_lua_core.h:603` |
| `special_held`, `special_pressed` | Booleans for the special button mask. | `melee/pc/platform/geno_lua_core.h:603` |
| `jump_held`, `jump_pressed` | Booleans for the jump button mask. | `melee/pc/platform/geno_lua_core.h:604` |
| `shield_held`, `shield_pressed` | Booleans for the shield button mask. | `melee/pc/platform/geno_lua_core.h:604` |
| `grab_held`, `grab_pressed` | Booleans for the grab button mask. | `melee/pc/platform/geno_lua_core.h:605` |
| `stick_x`, `stick_y` | Fighter's normalized current left-stick values. | `melee/pc/geno/geno_game_lua.inc:132`, `melee/pc/platform/geno_lua_core.h:613` |
| `stick_fwd` | `stick_x` when facing right, negated when facing left. | `melee/pc/platform/geno_lua_core.h:615` |

| `ctx.self` field | Type and meaning | Source |
|---|---|---|
| `air` | Boolean: not grounded. | `melee/pc/geno/geno_game_lua.inc:127`, `melee/pc/platform/geno_lua_core.h:618` |
| `anim_ended` | Boolean: current animation ended, supplied for the frame phase; false in enter. | `melee/pc/geno/geno_game_lua.inc:167`, `melee/pc/platform/geno_lua_core.h:619` |
| `facing` | Number `+1` or `−1`. | `melee/pc/platform/geno_lua_core.h:620` |
| `percent` | Current percent damage. | `melee/pc/geno/geno_game_lua.inc:138`, `melee/pc/platform/geno_lua_core.h:621` |
| `x`, `y` | Current fighter world position. | `melee/pc/geno/geno_game_lua.inc:134`, `melee/pc/platform/geno_lua_core.h:622` |
| `vel_x`, `vel_y` | Current `self_vel` components, not facing-relative speeds. | `melee/pc/geno/geno_game_lua.inc:136`, `melee/pc/platform/geno_lua_core.h:624` |
| `action_frame` | Integer Geno action clock (`GenoState.action_time`), not the clip's animation frame. | `melee/pc/geno/geno_game_lua.inc:128`, `melee/pc/platform/geno_lua_core.h:626` |
| `motion` | Integer current motion ID. | `melee/pc/geno/geno_game_lua.inc:129`, `melee/pc/platform/geno_lua_core.h:627` |
| `hit_damage` | Last hit **taken**, before counter negation, from `GenoState.hit_damage`. | `melee/pc/geno/geno.h:517`, `melee/pc/geno/geno_game_lua.inc:139`, `melee/pc/platform/geno_lua_core.h:628` |
| `hit_from` | Integer `+1` attacker in front now, `−1` behind now, 0 when there is no live primary fighter attacker. Derived from current positions/facing; not the direction at impact. | `melee/pc/geno/geno_game_lua.inc:102`, `melee/pc/platform/geno_lua_core.h:629` |
| `countered` | Integer count of hits countered since reset, from `GenoState.counters`. | `melee/pc/geno/geno.h:519`, `melee/pc/platform/geno_lua_core.h:630` |

Use dot-call syntax for commands; they accept the listed arguments directly, not a colon-call implicit `self`. They return no Lua result and queue effects for the game to apply after successful completion. Sources: `melee/pc/platform/geno_lua_core.h:290`, `melee/pc/platform/geno_lua_core.h:306`, `melee/pc/platform/geno_lua_core.h:636`, `melee/pc/geno/geno_game_lua.inc:180`.

| Command | Contract | Source |
|---|---|---|
| `ctx.go(name)` | A named state of this profile, `"auto"` (Wait grounded/Fall airborne) or `"helpless"`. No `geno:` prefix and no arbitrary retail motion ID. Unknown names fault. Make this your final command and return from the function. | `melee/pc/platform/geno_lua_core.h:290`, `melee/pc/geno/geno_game_lua.inc:191` |
| `ctx.velocity(forward, up)` | Two numeric finite values, each absolute magnitude ≤1000, narrowed to float. Grounded: writes facing-relative ground velocity, ignores `up`. Airborne: writes facing-relative self velocity x and self velocity y. | `melee/pc/platform/geno_lua_core.h:306`, `melee/pc/geno/geno_game_lua.inc:196` |
| `ctx.hitbox_damage(mask, damage)` | Integer mask 1…15, bit n selects fighter hitbox n (slots 0…3); damage numeric finite 0…1000. Changes damage; does not create, enable, resize or clear a hitbox. | `melee/pc/platform/geno_lua_core.h:313`, `melee/pc/geno/geno_game_lua.inc:211` |
| `ctx.loop()` | Restarts the current animation at 0 with rate 1 and selected motion-change keep flags; Lua slots are retained. | `melee/pc/platform/geno_lua_core.h:326`, `melee/pc/geno/geno_game_lua.inc:222` |
| `ctx.turn()` | Flips facing and rotates the model's root. A later velocity in this call uses the new facing. | `melee/pc/platform/geno_lua_core.h:331`, `melee/pc/geno/geno_game_lua.inc:232` |

Commands apply in queue order on a successful call, with a maximum of eight. A `go` can invoke the destination's enter callback immediately. The game uses one shared command exchange block, so a nested enter refills/clears that block; do not author additional commands after a state transition. Sources: `melee/pc/platform/geno_lua_core.h:264`, `melee/pc/geno/geno_game_lua.inc:28`, `melee/pc/geno/geno_game_lua.inc:188`, `melee/pc/geno/geno_game_v2.inc:458`, `melee/pc/geno/geno_game_lua.inc:243`.

### Sandbox and budgets

The complete environment is `type`, `select`, `ipairs`, `assert`, `error`, `freeze`, and `math.{abs,min,max,floor,ceil,sqrt,tointeger,huge,pi}`. No `gd`, `pairs`, `next`, `pcall`, `require`, `load`, `string`, `table`, `os`, `io`, `debug`, `coroutine`, metatable/raw access, random generator or clock is exposed. Modules load as text only through the vendored Lua 5.4.7 implementation. Sources: `melee/pc/platform/geno_lua_core.h:36`, `melee/pc/platform/geno_lua_core.h:468`, `melee/pc/platform/geno_lua_core.h:507`.

Returned functions and nested functions are scanned for assignments to upvalues (`OP_SETUPVAL`) and globals/captured table fields (`OP_SETTABUP`), which refuse the module. Captures may be nil, boolean, number, string, accepted functions or frozen tables. Mutable table captures—including the module table—are refused. Use `local function helper(ctx)` for helpers and `freeze{...}` for constant tables. Frozen tables are deep read-only proxies; table/function keys and nesting deeper than eight are refused. Sources: `melee/pc/platform/geno_lua_core.h:338`, `melee/pc/platform/geno_lua_core.h:363`, `melee/pc/platform/geno_lua_core.h:135`.

Each call has a nominal budget of 10,000 VM instructions, checked every 50, and 65,536 bytes of heap growth from its starting heap. The hook faults when its count exceeds 10,000, so this is a count-hook boundary rather than an exact individual-instruction cutoff. Loading uses the same instruction budget but 4 MiB of heap growth. The collector is stopped during execution and fully collected afterward. Enter/go recursion is capped at depth four in the game half. Sources: `melee/pc/geno/geno.h:499`, `melee/pc/platform/geno_lua_core.h:93`, `melee/pc/platform/geno_lua_core.h:414`, `melee/pc/platform/geno_lua_core.h:443`, `melee/pc/platform/geno_lua_core.h:504`, `melee/pc/platform/geno_lua_core.h:671`, `melee/pc/geno/geno_game_lua.inc:159`.

There are no Lua `phys`, `coll`, `iasa`, `on_hit`, `on_land` or article callbacks. There is no opponent-query API, hit-confirm field, general attribute write, grab/throw command, or article/FX/sound command in this domain. Native Geno `hooks.on_hit` is the event “this fighter was hit” and binds registered native hooks, not arbitrary Lua function names. Native `ATTACK_CONNECTED` exists in the word VM but is not exposed in `ctx.self`. Sources: `melee/pc/platform/geno_lua_registry.inc:127`, `melee/pc/platform/geno_lua_core.h:594`, `melee/pc/geno/geno.h:239`, `melee/pc/platform/geno_registry.c:1391`, `melee/pc/geno/geno_game.c:1494`, `melee/pc/geno/geno_game.c:2014`.

### Faults, snapshots and inspection

A failed call discards its state writes and queued commands, increments the fighter's fault count, records the last fault code, and sends the fighter to `auto`. A later successful call does not clear the last-fault record. The first eight native faults per profile are logged; logging counters are diagnostics, separate from the per-fighter simulation fault count. Sources: `melee/pc/platform/geno_lua_core.h:663`, `melee/pc/geno/geno_game_lua.inc:170`, `melee/pc/platform/geno_lua_registry.inc:217`, `melee/pc/geno/geno_state.h:105`.

| Code | Meaning | Source |
|---|---|---|
| 0 | Success/no fault | `melee/pc/geno/geno.h:533` |
| 1 | Lua runtime error | `melee/pc/geno/geno.h:534` |
| 2 | Instruction budget exceeded | `melee/pc/geno/geno.h:535` |
| 3 | Heap budget/allocation error | `melee/pc/geno/geno.h:536`, `melee/pc/platform/geno_lua_core.h:665` |
| 4 | Bad command argument or state target | `melee/pc/geno/geno.h:537` |
| 5 | Undeclared slot or value incompatible with its type | `melee/pc/geno/geno.h:538` |
| 6 | Too many commands; also the game-side enter recursion limit | `melee/pc/geno/geno.h:539`, `melee/pc/geno/geno_game_lua.inc:163` |

The authoritative state is game-memory `Geno_LuaBlock[6][2]`: 16 slot words, `faults`, `last_fault`. Snapshot discovery includes `pc_geno_*` game objects; reset zeroes the Lua block. A positive slot layout adds all 16 words and both fault words to the defined fighter's rollback digest. Sources: `melee/pc/geno/geno_game.c:108`, `melee/pc/geno/geno_state.h:103`, `melee/pc/platform/gw_snap.c:192`, `melee/pc/geno/geno_game.c:808`, `melee/pc/geno/geno_game_lua.inc:277`.

From a general `gd` inspection script, `gd.fighter_lua(port)` returns `nil` unless the primary fighter has a positive Lua slot layout; otherwise it returns `{profile, faults, last_fault, state={name=value,...}}`. This is read-only and does not require the gameplay manifest flag. It is registered under that exact name. Sources: `melee/pc/platform/gw_script_fighter_lua.inc:9`, `melee/pc/geno/geno_game_lua.inc:63`, `melee/pc/platform/gw_script.c:6665`.

## Online admission and identity

A defined fighter can play online when it has a netplay fighter identity and its peer has the same identity. Missing mandatory resource files prevent identity creation. Local resident aliases are not content identities: peers can map the same fighter to different local CharacterKind numbers. Sources: `melee/pc/platform/gw_mexid.c:268`, `melee/pc/platform/gw_mexid.c:283`, `melee/pc/platform/gw_mexid.c:806`, `melee/pc/platform/gw_mexid.c:825`.

There are three separate hashes to understand: the profile content ID, the online fighter identity, and the evolving simulation digest. Packaging export SHA-256 values are a separate tool artifact; the netplay code below uses its own 64-bit mixers. Sources: `melee/pc/platform/geno_registry.c:264`, `melee/pc/platform/geno_registry.c:1425`, `melee/pc/platform/gw_mexid.c:92`, `melee/pc/geno/geno_game.c:2323`.

### Profile content ID: exact constituents

The profile's ID starts from the Geno seed `0x47454E4F00000000` mixed with `GENO_ID_VERSION`, then hashes the **whole fighter entry node**, including unknown keys. Canonicalization uses node type tags, object keys in file order, array/object counts, string bytes, and numbers formatted `%.9g`. JSON whitespace is absent from this hash; numeric spellings such as 1 and 1.0 normalize, but reordering object keys changes the ID. The root format number and sibling fighters are not part of the entry node. Sources: `melee/pc/platform/geno_registry.c:282`, `melee/pc/platform/geno_registry.c:1423`.

It then folds every loaded subaction overlay in order: tag `0x4F56000000000000 | subaction_index`, followed by every parsed word. If Lua exists, it additionally folds `lua_hash`. That hash is FNV-style text mixing beginning at `0x4C55412D56310000` (constant “LUA-V1”), over module source text, then each declared slot name including its terminating NUL and its type number (`int=0`, `float=1`, `bool=2`) in declaration order. Lua source comments and whitespace therefore change identity. The output is forced to 1 if it would be zero and printed as 16 hex digits. Sources: `melee/pc/platform/geno_registry.c:1429`, `melee/pc/platform/geno_registry.c:1436`, `melee/pc/platform/geno_lua_registry.inc:26`, `melee/pc/platform/geno_lua_registry.inc:147`, `melee/pc/platform/geno_lua_core.h:48`.

**Compiler version is not an explicit constituent in the inspected code.** The engine includes vendored 5.4.7 and the Lua hash has a fixed domain tag, but neither `LUA_VERSION` nor compiled bytecode is folded into `p->lua_hash`. Do not repeat game `docs/geno.md` §24.1's claim that the content ID contains the Lua compiler version. Sources: `melee/pc/platform/geno_lua_core.h:36`, `melee/pc/platform/geno_lua_registry.inc:147`, `melee/pc/platform/geno_registry.c:1436`.

### Online fighter identity: exact constituents

The online identity is built by mixing the string domain `"geno-define"`, the entry content ID, the `none` flag (0 donor/1 authored), and file-content hashes in fixed resource-list order. The resident alias and the mod-install profile index are not fed into this identity. Sources: `melee/pc/platform/gw_mexid.c:281`, `melee/pc/platform/geno_define_online.inc:22`.

| Definition base | Resource contents hashed, in order | Source |
|---|---|---|
| `mario` | `PlMr.dat`, then `PlMrAJ.dat`, through the mounted/disc file layer | `melee/pc/platform/geno_define_online.inc:34`, `melee/pc/platform/gw_mexid.c:121` |
| `none` | Package animation bank, plan, then declared costume model files in their order | `melee/pc/platform/geno_define_online.inc:26` |

File contents are hashed as the file layer would load them. File names are only `mx_file` cache keys and do not directly enter each file hash, although names present in fighter entry keys already enter the profile ID. Mandatory absent files refuse identity construction. Presentation textures, custom audio and FX package bytes are not in the mandatory list; changing their entry keys changes the profile ID, while changing only their file contents does not change this online identity. Sources: `melee/pc/platform/gw_mexid.c:121`, `melee/pc/platform/gw_mexid.c:268`, `melee/pc/platform/geno_define_online.inc:26`, `melee/pc/platform/geno_registry.c:1425`.

Internally the identity is 64 bits; lobby identity announcements compare the low 48 bits. `MXD` messages additionally carry the define key and short hash for named diagnostics. The key announcement explains a mismatch; admission uses the identity table. Missing packages yield `<name>: your opponent doesn't have it`; the same key with different identity yields `<name>: your opponent has another version`; an incomplete local package yields `<name>: its package is incomplete (see the log)`. Sources: `melee/pc/platform/gw_mexid.c:655`, `melee/pc/platform/gw_mexid.c:774`, `melee/pc/platform/gw_mexid.c:825`, `melee/pc/platform/gw_mexid.c:837`, `melee/pc/platform/gw_mexid.c:852`.

### Simulation digest: exact Geno term

`RB_FighterHash` mixes `GenoDefine_StateDigest` only when nonzero. It returns zero for non-defines or invalid profiles. The Geno digest starts with `0x47444946` (“GDIF”) and uses `geno_dg` (`h ^= word; h *= 0x01000193; return h ^ (h >> 13)`); float fields contribute raw f32 bits. Sources: `melee/src/melee/ft/fighter.c:4033`, `melee/pc/geno/geno_game.c:2323`, `melee/pc/geno/geno_game.c:2347`.

The digest includes:

- Every `la_i`, `ra_i`, `la_f`, `ra_f` bank element; `extra_jumps`, `action_time`, `nchecks`, `last_check`; each active check's `target`, `once`, `ncond`, and active conditions' `head`, `arg1`, `arg2`. Source: `melee/pc/geno/geno_game.c:2359`.
- Every `rehit_period`, `rehit_count`, `link_mode`, `stun_add`, `hb_flags`; `stun_bonus`, `hold_motion`, `hold_frames`; every `move_i`, `move_f`. Source: `melee/pc/geno/geno_game.c:2379`.
- `enter_from`, `hidden`, `hit_count`, `hit_damage`, `hit_port`, `hit_counter`, `counters`, `ledge`, `motion_started`, `motion_vy`, `motion_facing`, `motion_gravity`, `enter_keep`, `atk_connected`, `atk_connected_prev`, `fall_limit`. Source: `melee/pc/geno/geno_game.c:2393`.
- A nonzero owned-live-article digest, then a nonzero Lua block digest. Sources: `melee/pc/geno/geno_game.c:2409`, `melee/pc/geno/geno_game_lua.inc:277`.

The article digest sums per-item words independent of item-list order; each starts at `0x41525449` (“ARTI”) and covers raw profile index, article index, age/frame, despawn reason, travel vx/vy, position x/y/z, engine velocity x/y and current article hitbox-entry slots. The Lua digest starts at `0x4C554131` (“LUA1”), includes all 16 slot words, faults and last fault, and is added only with positive layout size. Sources: `melee/pc/geno/geno_game_articles.inc:443`, `melee/pc/geno/geno_game_lua.inc:278`.

Excluded Geno state fields are explicitly classified in the coverage test: fixed-at-spawn `profile` and `kind` (not perturbed); diagnostic `resets`, `hook_calls`, `changes`, `state_entries`, `art_spawned`, `motion_land`; marker `flags`; frame-keyed `stun_bonus_frame`, `react_flags`, `react_frame`; callback-local `in_coll`, `edge_pending`, `edge_target`. The test assigns each struct word to a field and verifies perturbations according to that classification. This audit concerns the hash; snapshots cover the game memory separately. Sources: `melee/pc/geno/geno_online_tests.inc:20`, `melee/pc/geno/geno_online_tests.inc:93`, `melee/pc/platform/gw_snap.c:192`.

The separate match item hash substitutes a stable content-derived kind for Geno article numeric kinds: profile ID high/low halves xor-folded to 32 bits, mixed with the article index under “ARTG.” It then hashes item motion/state, position x/y/z and velocity x/y/z and sums items. Sources: `melee/pc/platform/geno_define_online.inc:6`, `melee/pc/geno/geno_game_articles.inc:429`, `melee/src/melee/ft/fighter.c:4097`.

### Online Lua faults

Default soft policy applies the same transactional discard and Wait/Fall recovery used offline. Faults are simulation state, and budgets use instruction/allocation counts rather than wall time. These choices make faults repeatable under identical execution environments, rather than requiring a fixed-time callback watchdog. Sources: `melee/pc/geno/geno_game_lua.inc:170`, `melee/pc/platform/geno_lua_core.h:71`, `melee/pc/platform/geno_lua_core.h:93`, `melee/pc/platform/geno_lua_registry.inc:182`.

`MELEE_GENO_FAULT_ONLINE=hard` optionally records a native Lua fault while netplay and rollback are active. It ends the session only once the earliest fault frame is confirmed, with `Disconnected: a fighter's script faulted (hard fault policy)`. Rollback clears the pending note and resimulation can record it again. Sources: `melee/pc/platform/geno_lua_registry.inc:194`, `melee/pc/platform/geno_lua_registry.inc:203`, `melee/pc/platform/geno_lua_registry.inc:216`, `melee/pc/platform/gw_rollback.c:1355`, `melee/pc/platform/gw_netplay.c:4016`.

Do not promise identical heap faults across ABIs. The allocator counts requested bytes, whose Lua object layouts depend on the host ABI. The engine reference §24.3 records different 32-bit Windows/Linux value sizes and identifies an ABI-neutral heap budget as unfinished. The requested checker warning above 32 KiB peak allocation is also not implemented in `tools/geno/lua_check.py`; it is a source-text API checker, not a VM allocator profiler. Sources: `melee/pc/platform/geno_lua_core.h:71`, game `melee/docs/geno.md:2995`, `tools/geno/lua_check.py:66`.

## A repeatable LAB authoring loop

1. Assemble the files that `geno.json` actually names and run the package checker. The artist build regenerates its output moves and definition from `fighter.json`; do not treat edits inside the generated output as persistent source customizations. `artist assemble` presently copies the Striker set and retargets joints, size, offsets, rate and delay. A hand-authored new script/state needs its own maintained package inputs. (`tools/geno/artist/assemble.py:110`, `:135`, `:156`.)
2. **Close and relaunch the executable after editing a native define.** `gw_Geno_Reload` explicitly refuses hot reload while any native definitions exist, returning `native definitions require a process restart; current data kept`. F8 / `lab reload` and restarting only the match cannot apply changed define metadata, words or Lua through this path. Rebuild the engine executable only if engine source changed. (`melee/pc/platform/geno_registry.c:2007`.)
3. Mount a mods parent containing your fighter and `geno-lab`, with both enabled. Launch the LAB with a stable fighter key and a stage, for example `MELEE_SCENE="mode=lab;p1=geno:my-fighter/hu;p2=mario/cpu0;stage=fd"`, using `tools/port/run.sh`. For clean frame timings launch with P1 alone; an opponent in range adds hitlag. Confirm the mounted mod and resolved fighter in the run's log. (`melee/docs/geno.md:488`, `:826`; `tools/geno/artist/pipeline.py` generated `run-command`.)
4. Identify the joints and actual clip, then inspect the effective script. Use the real input for entry and step across startup, contact and recovery. Save a clean baseline and repeat the same input after each executable restart. Add your own script/proof for a custom state chain. This produces behavior evidence separate from a successful JSON check.

The LAB command registration and modes are in `melee/pc/geno/mods/geno-lab/scripts/lab.lua:5527`. Current modes are clean, hitboxes, frames, stage, inspect, moves, launch, ab, training and combo. Use `lab help` for the complete current key map; older sections listing only five modes are incomplete.

| Purpose | Exact commands/API |
|---|---|
| Focus P1; inspect skeleton/joints | `lab port 1`; `lab mode inspect`; `lab set inspect.joints on`; INSPECT `S` skeleton, `J` numbered joints |
| Print exported joint→bone mapping | `python -m tools.geno.artist joints path/to/fighter.json` |
| Read current joint positions | `gd.joints(1, true)`; returned list position is joint index + 1; `true` refreshes matrices offline |
| Hitbox display and data | `lab mode hitboxes`; `lab set hitboxes.labels on`; `gd.hitboxes(1)` active, `gd.hitboxes(1,true)` all slots |
| Read geometry | Live hitbox `bone`, `radius`, `ox/oy/oz` local offsets, `x/y/z` current world center, `px/py/pz` previous center; `gd.hurtboxes(1)` for capsules |
| See actual playing clip/state | `gd.player(1)` fields `motion_name`, `anim_id`, `anim_name`, `anim_symbol`, `anim_frame_f`, `anim_rate`, `action_frame`, `iasa`, `body_state`, `in_hitlag` |
| Effective script | `lab events` or `gd.timeline(1)`; `gd.timeline(1,44)` for a specified motion |
| Browse/play a state | `lab mode moves`; `lab moves <text>`; `lab play <id-or-name>`; use input rows for donor/m-ex specials |
| Enter/scrub common/Geno motion | `lab move 44 1` or `gd.set_motion(1,44,1,1)`; lift an aerial with the fifth argument; the LAB enters Geno states through their behavior entry |
| Step/rewind | SPACE pause; RIGHT +1; LEFT −1; `gd.step(1)`; `lab back 1`; `lab history 10` |
| Quick baseline | F5/F6; `gd.savestate(1)` / `gd.loadstate(1)` |
| Compare typed fighter Lua state | `gd.fighter_lua(1)` (slots, faults and last fault) |
| Actual inputs from a pad script | `gd.input(1,{buttons="B",x=127},2)`; `gd.wait(1)` to sample after logic; `gd.release(1)` when finished |
| Restart the same LAB match | `gd.lab_leave("restart")`; useful for resetting a match, **not** for reloading a define's package edits |

Joints and hitbox fields: `melee/docs/geno.md:396`; public API `docs/scripting.md:831`; joints CLI `tools/geno/artist/__main__.py:35`; state browser code `melee/pc/geno/mods/geno-lab/scripts/lab.lua:1676`; LAB motion entry `melee/pc/geno/geno_game_v2.inc:1117`.

## What each checker proves

| Tool | Use | Scope/limit |
|---|---|---|
| `python -m tools.geno.check MOD` | Validate source fields, references, word scripts and Lua names | Static check; cannot prove in-game timing, callback execution, geometry or controller feel |
| `python -m tools.geno.report MOD --frames` | Inspect which of 351 motion rows are authored/inherited/donor-special and the eight special bindings | Its `own` describes effective behavior ownership; not proof every animation is authored. Frame report is straight-line, does not follow loops/conditions |
| `python -m tools.geno.artist clips --markdown` | Generate the motion-row checklist and expected default-script timings | Clip availability/fallback checklist, not a gameplay pass |
| `python -m tools.geno.artist.proof_report LOG` | Summarize artist `proof.lua` run | Specific idle/walk/run/jump/jab/shield/grab/throw proof; not a complete custom-move harness |
| `moves_check.lua` + `moves_report.py` | Drive and compare Striker/Courier's 40 known scenarios against their declared data | Hardcoded scenario/state names and subaction numbers. Adapt scenarios/expectations for new specials or a different state graph; charge-scaled/conditional cases can be `works*` |
| `moves_check_sora.lua` + `moves_diff.py` | Compare existing installed Sora with the migrated define using the same driver | Local installed source content required; equality of measured scenarios is not source-game visual parity |
| `lab export 1 version-name` / `lab fdiff` | Export sampled frame data for common attacks, input specials and Geno states; compare versions | Run solo for clean timings; inspect conditional warnings and sampled state chains |
| `gd.rewind_test(n)` / `gd.rewind_test_result()` | Check return to a previous snapshot against simulation bytes | Read result including resimulated frame count; a successful result with zero frames resimulated does not establish Lua callback resimulation |
| `pc/geno/tools/parity.sh` | Replay vanilla console `.slp` inputs and compare console frame state | Vanilla parity regression only. Missing inputs skipped, all missing gives exit 2; pin passes mean exact known first divergence, not full parity |

The row report and frames implementation: `tools/geno/report.py:79`, `:124`, `:179`. Artist checklist generation: `tools/geno/artist/rows_doc.py:1`. Fixture scenario/expectation tables: `tools/geno/moves_check/moves_check.lua:30`, `tools/geno/moves_check/moves_report.py:24`. `moves_diff` refuses empty/failed/incomplete logs: `tools/geno/moves_check/moves_diff.py:22`. Export implementation/help: `melee/pc/geno/mods/geno-lab/scripts/lab.lua:2363`, `:2855`. Vanilla parity semantics: `melee/pc/geno/tools/parity.sh:1`, `:117`.

The fixture launch scripts below use Git Bash. Set `GW_ROOT` to the workspace containing the correct `.env`, because the runner changes directory there; `GW_MELEE` selects the game source checkout and `GW_BUILD_ROOT` the executable/run root. `MELEE_MODS_DIR` must be a Windows-readable path to the parent folder. Use a separate disposable mods directory for `make_mods.sh`: it removes and recreates its destination.

```bash
# Existing built Striker fixture; do not pass an important folder to make_mods.sh.
bash tools/geno/moves_check/make_mods.sh "$GW_BUILD_ROOT/author-fixtures" geno-lab vanilla-striker
export MELEE_MODS_DIR="$GW_BUILD_ROOT/author-fixtures"
bash tools/geno/moves_check/run_moves_check.sh author-striker vanilla-striker 300
python -m tools.geno.moves_check.moves_report \
  "$GW_MELEE/pc/geno/mods/vanilla-striker" \
  "$GW_BUILD_ROOT/runs/author-striker/melee-pc.log" \
  --json "$GW_BUILD_ROOT/author-striker.json"

# A general proof driver, with its own scenarios appropriate to your move.
bash tools/geno/moves_check/run_scene.sh author-my-fighter \
  "mode=lab;p1=geno:my-fighter/hu;p2=mario/cpu0;stage=fd" \
  "$GW_ROOT/path/to/my-proof.lua" 300

# Two completed MOVECHK runs driven by the same scenario set.
python -m tools.geno.moves_check.moves_diff old-melee-pc.log new-melee-pc.log --json diff.json

# Vanilla console replay regression; own local replay list and matching vanilla disc.
GW_ROOT="$PWD" PARITY_CONF="path/to/parity.local.conf" \
  bash "$GW_MELEE/pc/geno/tools/parity.sh"
```

Runner behavior is in `tools/geno/moves_check/run_moves_check.sh:10`, `tools/geno/moves_check/run_scene.sh:6`, and `tools/geno/moves_check/make_mods.sh:6`. The runners launch muted turbo with a far-offscreen window; a game build, the appropriate local disc and available author assets are prerequisites. Read `melee-pc.log` and the terminal completion marker before reporting a pass. A timeout is not an exception permitting a pass. Visual and controller review should use a separate realtime run.

## Learn from committed fixtures

These are committed source recipes. Generated native art in fixture `files/` folders may need building; migration output derived from an installed port stays local.

| Example | Read first | What to borrow |
|---|---|---|
| Vanilla Striker | `melee/pc/geno/mods/vanilla-striker/geno.json:1`; `moves/n_charge.genoasm:1`; `moves/n_release.genoasm:1` | Independent script overlays on Mario reference clips; all eight B inputs bound; charge counted in MOVE_I0 by ftcmd loop, release damage/speed computed by GET/MUL/ADD/PUT and HBDMG |
| Vanilla Courier | `melee/pc/geno/mods/vanilla-courier/geno.json:1`; `moves/nair.genoasm:1`; `moves/fthrow.genoasm:1` | `base:"none"`, own costume models/animation bank/plan, retargeted limb hitboxes, ordinary aerial autocancel and common grab/throw flow |
| Vanilla Charger | `melee/pc/geno/mods/vanilla-charger/geno.json:1`; `lua/charger.lua:1`; `moves/release.genoasm:1` | Same charge/release idea implemented as native-state Lua; 60-frame cap, clip looping, typed int/bool state, speed `1.6 + .03×charge` and damage `6 + .15×charge` |
| Vanilla Riposte | `melee/pc/geno/mods/vanilla-riposte/geno.json:1`; `lua/riposte.lua:1`; its `moves/*.genoasm` | Counter window in data; answer power from incoming damage, a streak that survives states and resets on whiff, facing correction for a behind hit, A follow-up window |
| Vanilla Caster | `melee/pc/geno/mods/vanilla-caster/geno.json:1`; `moves/cast.genoasm:1` | The special spawns article index 0 after `wait 8`, recovers and returns auto. CasterBolt declares lifetime 70, speed `[2.2,0]`, spawn `[6,9]`, cap 3, 5% radius 3.5 hitbox, effect and named sounds |
| Sora migration | `ports/ir/tools/trail_define.py:1`; `tools/geno/moves_check/moves_check_sora.lua:1`; `tools/geno/moves_check/locomotion.lua:1`; `defense.lua:1` | Port a local installed attach+m-ex package into own animation rows, native states/scripts/articles, retain explicit conversion-loss report, then compare old/new measured move, movement and defense scenarios |

Striker proves that behavior more complicated than one fixed hitbox need not be Lua. Charger shows when Lua makes an input-dependent state machine easier to maintain. Riposte keeps capture/counter collision native and uses Lua for the response. The native counter window stays in JSON: there is no Lua command to open or resize it. Its `power` is `clamp(1.5×hit_damage,9,30) + streak−1`, so the streak can raise its final value above 30. `hit_from` comes from attacker positions **at callback time**, not a stored direction at impact. The typed state block is snapshotted; a captured mutable Lua local is refused. (`melee/pc/geno/mods/vanilla-riposte/lua/riposte.lua:39`; `melee/pc/geno/geno_game_lua.inc:101`; `melee/pc/platform/geno_lua_core.h:12`.)

A base-none authoring pipeline gives you your own model, clips, parts and hurtboxes while keeping the shared `melee.common.v1` behavior backend. Its default set still comes from Striker; own art does not automatically imply wholly new behavior. Review authored/inherited rows, special bindings, fallback clips and the boot independence census. The currently implemented plan does not read author ECB or arbitrary socket-role documentation as custom collision rules. For source-game migrations, separately track ModelVis expressions, ECB/IK/ledge geometry, victim clips, menu art, sounds and effects. Sora's current conversion keeps such gaps in its report; numerical parity of the driver cannot silently close them. (`tools/geno/artist/assemble.py:3`; `melee/pc/geno/geno_define_data.inc:1`; `ports/ir/tools/trail_define.py:23`, `:344`; `melee/docs/geno.md:2835`; migration record `docs/superpowers/plans/2026-10-08-geno-slice8-migrations.md:136`.)

## Worked example: Pip's Palm Skip

Pip is an original, short, long-armed artist sample. **Palm Skip** replaces its neutral special with two open-palm beats and a short forward step. Tap B for 5% then 8%; keep B held through Geno action tick 12 for 5% then 11%. This is an authored behavior specification, not a playability/balance endorsement. Original source lives in `ports/geno-artist-samples/pip/`; the sample uses the unchanged artist and script toolchain.

| Source | Purpose |
|---|---|
| `fighter.json`, `params.json` | Pip's proportions, renamed bones, palette and walk-speed override |
| `make_special.py` | Adds the original `PalmSkip` action to generated Blender source: 41 sampled keys, 40-frame duration, strike poses at 6 and 14, no root translation |
| `palm_skip.genoasm` | Two hitboxes on `hand.R`: script windows `[6,9)` and `[14,17)`, recovery through script frame 40 |
| `gameplay.json` | New `PalmSkip` state, neutral ground/air targets, subaction 295 and the typed Lua declaration |
| `lua/palm_skip.lua` | Entry reset/forward velocity, action-tick-10 brake, tick-12 B latch, second-pulse damage override |
| `build.py` | Generates source under output/source if absent, runs artist build, resolves `hand.R` from the plan, assembles the move, replaces inherited neutral states, copies Lua and reruns the checker |
| `check_lua.lua` | Offline checks of both input branches, entry reset, brake and first-tick boost; ordinary Lua context stub, not an engine simulation |
| `moves_check.lua` | Prepared LAB proof for four casts: ground/air × tap/hold. Checks two separated pulses and the first damage sample of each, recovery and zero Lua faults; not executed in this task |

The state uses `behavior: "geno.ground"`, `like: "motion:343"`, `phys: "auto"`, `coll: "both"`, `iasa: "none"`, and Lua `enter`/`frame`. The finite animation ends through the default auto transition. Both neutral bindings enter this state; auto physics/collision handle its ground/air situation. The other default specials remain. The wrapper removes obsolete `NCharge`/`NRelease` states and overlays; simply appending a new special leaves an unreachable state, which the checker rejects. This example reuses neutral subaction 295. A new subaction at 303 or above requires a declared extra `fighter.rows` entry. Sources: `ports/geno-artist-samples/pip/gameplay.json:1`, `build.py:55`; state behavior `melee/pc/geno/geno_game_v2.inc:967`; checker `tools/geno/check.py:316`.

Animation motion 343 and subaction 295 are different identifiers. The generated clip map assigns `PalmSkip` to `SpecialN`; the state requests that row with subaction 295. The hitbox source uses `@HAND_R@` only as a **sample build token**; `build.py` replaces it with `plan.roles["hand.R"][0]` before calling the normal assembler. That is author-side role resolution, not a runtime role-name API. Pip's current generated joint is 18; other skeletons must resolve their own number. Sources: sample `build.py:39`, `:46`; `tools/geno/artist/convert.py:183`; `tools/geno/artist/data/clip_table.json` SpecialN row.

For a fresh build, set `GW_MELEE` to the read-only game checkout and ensure Blender and fighterbuild are available as in the artist README. A worktree can point `GW_FIGHTERBUILD` at an existing DLL; the sample does not build or modify the game:

```text
python ports/geno-artist-samples/pip/build.py
python -m tools.geno.check _build/agents/pip-author/mods/sample-pip
python -m tools.geno.report _build/agents/pip-author/mods/sample-pip --frames
lua ports/geno-artist-samples/pip/check_lua.lua
```

The default output is `_build/agents/pip-author/`; `--out` selects another dedicated output directory. Art is generated at `<out>/source/pip.blend` only if absent; later runs preserve edits to that file and rebuild the package. `source/fighter.json` is regenerated from the sample inputs. Change maintained Python/JSON/Lua sources for persistent gameplay edits. The prototype still has **321 placeholder motion rows**: an original special does not make the rest of Pip a finished moveset.

### The timing correction this example exercises

At state entry, `Fighter_ChangeMotionState` calls the script interpreter once with a zero timer. The interpreter subtracts the animation rate before executing `wait 6`, leaving five ticks; the second pulse's authored frame 14 therefore starts on Geno action tick 13 at rate 1. The Lua override covers ticks 13–16, so the first possible hit of the boosted pulse already has damage 11. Starting it at 14 would be late. This is a **source-derived expectation**, pending the LAB proof below; it is not a general rule for arbitrary rate changes or state chains. Sources: `melee/src/melee/ft/fighter.c:1574`, `:1625`; `melee/src/melee/ft/ftaction.c:1349`; `melee/src/melee/lb/lbcommand.c:22`; sample `lua/palm_skip.lua:13`.

The brake sets horizontal velocity to zero at its callback boundary and preserves the current vertical self velocity. Native ground friction or air gravity/drift runs afterward, so it does not freeze the fighter in space. Source: `melee/pc/geno/geno_game_lua.inc:196`, `melee/pc/geno/geno_game_v2.inc:606`.

### Evidence from this authoring task

| Check | Result and boundary |
|---|---|
| Artist export/validate/convert/model build | PASS; 34 joints, 15 hurtboxes, 1,320 triangles, 40 bank clips; model verification reported zero triangle/weight differences. 321 placeholder rows remain |
| Generated Pip `geno check` | PASS after applying the gameplay overlay |
| Static move report | Row 295 contains the two authored windows/damage values; Lua's dynamic 11% is outside this straight-line report |
| `check_lua.lua` | PASS for tap/hold, reset, frame-13 first boost, damage mask and brake; executed by installed Lua, not the fighter sandbox |
| Current-source `build.sh --native-test geno-lua` | PASS, `geno-lua: all passed`; checks the domain implementation, not Pip in a match |
| `python -m pytest tools/geno -q` | 81 passed, 5 skipped, 1,028 subtests passed after regenerating five stale source-hash entries in the schema |
| Existing executable, true `run.sh --test` on ACE with Pip-only mods | 355/355 passed. Executable provenance does **not** match the audited source; this is baseline suite evidence, not current integration or custom-move certification |
| LAB companion enabled during first suite attempt | 354/355; `script_lab_events`: “event queue still armed with no hook defined”. Omitting the LAB script mod while retaining Pip made the same executable pass |
| Custom LAB proof, visual/controller feel, real rollback | **Not run**: no game windows were permitted. The copied suite executable was not rebuilt; see the coordinator commands below |

The native suite does not drive Palm Skip through a match. A mounted mod line is not proof that its state, Lua, hitboxes and animations executed together. Do not call the worked example gameplay-accepted until the custom proof and visual checks are complete.

### Coordinator commands: these launch a game window

First build a current executable with `tools/port/build.sh` in the coordinator's isolated build root and verify its provenance. Set `GW_ROOT` to the workspace with the machine's `.env`, `GW_MELEE` to that game checkout and `GW_BUILD_ROOT` to the matching built executable. Set `AUTHOR_ROOT` to this guide's workspace using a Windows-style path. The `run_scene.sh` wrapper calls itself headless but launches the ordinary game offscreen; it was deliberately **not run** here.

```bash
export MELEE_MODS_DIR="$AUTHOR_ROOT/_build/agents/pip-author/mods"
bash "$AUTHOR_ROOT/tools/geno/moves_check/run_scene.sh" pip-palm-skip \
  'mode=lab;p1=geno:sample-pip/hu;p2=mario/cpu0;stage=fd' \
  "$AUTHOR_ROOT/ports/geno-artist-samples/pip/moves_check.lua" 300
```

Read `$GW_BUILD_ROOT/runs/pip-palm-skip/melee-pc.log`. Require `PIPCHECK PASS 4 casts`, no `PIPCHECK FAIL`, zero Lua faults, and first-pulse/second-pulse samples of 5/8 for tap and 5/11 for hold in both situations. The driver leaves P2 out of range to isolate timing; it does not certify contact, knockback or hitlag. Afterward, in a realtime LAB run, place P2 at the right palm and check contact and launch, startup/active/recovery alignment, shield interaction, interrupted casts, landing mid-move, both facings, and recovery to common states. Use the registered APIs above to inspect the actual clip and right-hand joint. Also resimulate active casts with `gd.rewind_test` and inspect its result before claiming rollback support for the new move.

The stock 40-scenario `moves_check.lua` expects `NCharge` and `NRelease` and therefore is not Pip's special proof. The sample-specific command above exercises `PalmSkip`; use/adapt the generic suite separately for the inherited normals, aerials, grabs and other specials. Sources: `tools/geno/moves_check/moves_check.lua:50`, sample `moves_check.lua:1`.

## Format and interpretation

- Current format is `geno: 10` (`melee/pc/geno/geno.h:16`). Root keys: `geno`, `fighters`. Use `define` OR `attach` per fighter; standalone author workflow uses `define`.
- Definitions: v6 Mario/common preset; v7 all accepted attributes, special_attributes and fx_bindings; v8 articles/sounds; v9 base none/model data/presentation/audio; v10 Lua/AI/Kirby policy. See `melee/pc/platform/geno_define_registry.inc:264`, `:277`, `:306`, `:182`, `:185`; `melee/pc/platform/geno_lua_registry.inc:60`.
- Most objects in the editor schema forbid unknown keys, except Lua state names and move names. Runtime is more permissive in many blocks; ignored keys still change entry identity (`melee/pc/platform/geno_registry.c:1423`). Strict subblocks are called out below.
- Units: Melee model/world units; logic is 60 frames/s. Distances and velocities are game units, never Blender metres. Comments `//`, trailing commas and UTF-8 BOM are accepted. Runtime escaped Unicode `\uXXXX` becomes `?`; author names are printable ASCII (`melee/pc/platform/geno_registry.c:99`, `:110`, `:179`, `:244`). Duplicate object keys resolve FIRST in runtime, but checker refuses them (`:256`; `tools/geno/check.py:59`).
- In the table, required keys are marked in Meaning. `absent` on a container means no override; required primitive keys have no usable absence default. Schema limits are listed exactly, followed by runtime differences.

## Every current geno.json field (recursive)


### Root fields

| Path | Accepted editor type / constraints | Meaning and units | Default on absence | Code reference |
|---|---|---|---|---|
| geno | integer (minimum=1; maximum=10) | REQUIRED. Format version | required; no default when absent (schema helper advertises 10) | `melee/pc/platform/geno_registry.c:1453` |
| fighters | array of object (maxItems=65535) | REQUIRED. Ordered entries | required by checker; runtime missing/non-array yields no profiles | `melee/pc/platform/geno_registry.c:1461` |

### `attach`

| Path | Accepted editor type / constraints | Meaning and units | Default on absence | Code reference |
|---|---|---|---|---|
| fighters[].attach | string (maxLength=31) | Vanilla name/alias or existing fighter .dat file | required for attachment; no target when missing | `melee/pc/platform/geno_registry.c:1335` |

### `define`

| Path | Accepted editor type / constraints | Meaning and units | Default on absence | Code reference |
|---|---|---|---|---|
| fighters[].define | object | Standalone fighter identity and resource preset | absent | `melee/pc/platform/geno_define_registry.inc:260` |
| fighters[].define.key | string (pattern="^[a-z0-9][a-z0-9_.-]{0,38}$") | REQUIRED. Stable lowercase definition identity (not resident character slot) | REQUIRED; no usable absence default | `melee/pc/platform/geno_define_registry.inc:282` |
| fighters[].define.name | string (minLength=1; maxLength=47; pattern="^[ -~]+$") | REQUIRED. Printable ASCII fighter display name | REQUIRED; no usable absence default | `melee/pc/platform/geno_define_registry.inc:289` |
| fighters[].define.base | enum (enum=["mario", "none"]) | REQUIRED. mario: the retail Mario preset is the template; none (geno 9): the package owns its model, bank, parts table and joint fields (docs/geno.md 22.4) | REQUIRED; no usable absence default | `melee/pc/platform/geno_define_registry.inc:276` |
| fighters[].define.common | value (const="melee.common.v1") | REQUIRED. Versioned common-state backend identifier | REQUIRED; no usable absence default | `melee/pc/platform/geno_define_registry.inc:279` |
| fighters[].define.resources | enum (enum=["retail:mario", "mod:files"]) | REQUIRED. retail:mario with base mario; mod:files with base none | REQUIRED; no usable absence default | `melee/pc/platform/geno_define_registry.inc:280` |

### `common_states`

| Path | Accepted editor type / constraints | Meaning and units | Default on absence | Code reference |
|---|---|---|---|---|
| fighters[].common_states | array of object (maxItems=64) | Overrides on native motion rows (definition only) | absent | `melee/pc/platform/geno_define_registry.inc:320` |
| fighters[].common_states[].motion | integer (minimum=0; maximum=350) | REQUIRED. Native motion row | REQUIRED; no usable absence default | `melee/pc/platform/geno_define_registry.inc:320` |
| fighters[].common_states[].like | integer (minimum=0; maximum=350) | Inherited motion row | absent sentinel -1; keep original motion row | `melee/pc/platform/geno_define_registry.inc:320` |
| fighters[].common_states[].subaction | integer (minimum=0; maximum=1023) | Installed retail animation row | absent sentinel -1; keep selected row animation | `melee/pc/platform/geno_define_registry.inc:320` |
| fighters[].common_states[].flags | integer (minimum=0; maximum=2147483647) | Motion flags | absent sentinel -1; keep selected row flags | `melee/pc/platform/geno_define_registry.inc:320` |
| fighters[].common_states[].move_id | integer (minimum=0; maximum=255) | Stale move id | absent sentinel -1; keep selected row stale move id | `melee/pc/platform/geno_define_registry.inc:320` |
| fighters[].common_states[].move_tag | string (enum=["jab", "dash_attack", "tilt", "smash", "aerial", "grab", "throw", "special", "projectile"]) | Declared move tag | undeclared (runtime tag 0) | `melee/pc/platform/geno_define_registry.inc:320` |
| fighters[].common_states[].anim | string (enum=["like", "next", "loop", "lua", "hold", "glide.start", "glide", "tornado", "drill", "drill.end", "glide.after", "cape"]) | Callback override | keep selected row anim callback | `melee/pc/platform/geno_define_registry.inc:320` |
| fighters[].common_states[].iasa | string (enum=["like", "interrupt", "none", "glide"]) | Callback override | keep selected row input callback | `melee/pc/platform/geno_define_registry.inc:320` |
| fighters[].common_states[].phys | string (enum=["like", "cape", "none", "air", "air_nodrift", "air_drift", "brake", "ground", "auto", "anim_motion", "glide.start", "glide", "glide.attack", "glide.end", "tornado", "drill", "drill.end", "drill.start"]) | Callback override | keep selected row physics callback | `melee/pc/platform/geno_define_registry.inc:320` |
| fighters[].common_states[].coll | string (enum=["like", "cape", "cape.after", "none", "air", "air_noledge", "ground", "ground_stop", "both", "anim_motion", "glide", "drill", "drill.start"]) | Callback override | keep selected row collision callback | `melee/pc/platform/geno_define_registry.inc:320` |

### `name`

| Path | Accepted editor type / constraints | Meaning and units | Default on absence | Code reference |
|---|---|---|---|---|
| fighters[].name | string (maxLength=63) | Log display name | attach: target Pl file; define: define.name (entry name ignored) | `melee/pc/platform/geno_registry.c:1352` |

### `attributes`

| Path | Accepted editor type / constraints | Meaning and units | Default on absence | Code reference |
|---|---|---|---|---|
| fighters[].attributes | object (maxProperties=128) | Accepted common attribute overrides; full attribute table below | no overrides; donor data remains | `melee/pc/platform/geno_registry.c:1356` |

### `jumps`

| Path | Accepted editor type / constraints | Meaning and units | Default on absence | Code reference |
|---|---|---|---|---|
| fighters[].jumps | object | Named block | absent | `melee/pc/platform/geno_registry.c:1382` |
| fighters[].jumps.max | integer (minimum=1; maximum=250) | Total jumps including ground jump | effective attributes.max_jumps (including its override) | `melee/pc/platform/geno_registry.c:1382`; `melee/pc/geno/geno_game.c:1062` |
| fighters[].jumps.air_vy | array of number (maxItems=16) | Per-air-jump vertical impulses in Melee units/frame; last supplied entry repeats on multijump fighters | existing multijump table impulses | `melee/pc/platform/geno_registry.c:1386`; `melee/pc/geno/geno_game.c:1070` |

### `hooks`

| Path | Accepted editor type / constraints | Meaning and units | Default on absence | Code reference |
|---|---|---|---|---|
| fighters[].hooks | object | Named block | absent | `melee/pc/platform/geno_registry.c:1391` |
| fighters[].hooks.on_init | array of string (maxItems=8) | Ordered entries | absent | `melee/pc/platform/geno_registry.c:1391` |
| fighters[].hooks.on_frame | array of string (maxItems=8) | Ordered entries | absent | `melee/pc/platform/geno_registry.c:1391` |
| fighters[].hooks.on_action | array of string (maxItems=8) | Ordered entries | absent | `melee/pc/platform/geno_registry.c:1391` |
| fighters[].hooks.on_land | array of string (maxItems=8) | Ordered entries | absent | `melee/pc/platform/geno_registry.c:1391` |
| fighters[].hooks.on_hit | array of string (maxItems=8) | Ordered entries | absent | `melee/pc/platform/geno_registry.c:1391` |

### `states`

| Path | Accepted editor type / constraints | Meaning and units | Default on absence | Code reference |
|---|---|---|---|---|
| fighters[].states | array of object (maxItems=48) | Ordered entries | absent | `melee/pc/platform/geno_registry.c:862` |
| fighters[].states[].name | string (maxLength=31) | State target name | empty name; use numeric state index | `melee/pc/platform/geno_registry.c:866` |
| fighters[].states[].behavior | string (enum=["geno.air", "geno.ground", "geno.anim_motion", "geno.glide.start", "geno.glide", "geno.glide.attack", "geno.glide.landing", "geno.glide.end", "geno.tornado", "geno.drill", "geno.drill.end", "geno.cape", "geno.cape.attack", "geno.cape.end", "geno.drill.start"]) | Callback bundle | GENO_BHV_NONE; same callbacks/defaults as geno.air; recommend explicit behavior | `melee/pc/platform/geno_registry.c:873`; `melee/pc/geno/geno_game_v2.inc:968` |
| fighters[].states[].subaction | integer (minimum=0; maximum=1023) OR string (pattern="^(motion\|special):[0-9]+$") | Animation/script row index, or animation borrowed from a motion/special target | copied like row animation; -1 only if no row resolves | `melee/pc/platform/geno_registry.c:889`; `melee/pc/geno/geno_game_v2.inc:304` |
| fighters[].states[].like | integer (minimum=0; maximum=65535) OR string (pattern="^(auto\|helpless\|stay\|[mM][oO][tT][iI][oO][nN]:.+\|[sS][pP][eE][cC][iI][aA][lL]:.+\|[gG][eE][nN][oO]:.+)$") | Native motion row to copy flags, stale move id and camera callback; named Geno-state lookup unavailable | behavior default native motion; invalid/missing resolved row falls back to Fall | `melee/pc/platform/geno_registry.c:894`; `melee/pc/geno/geno_game_v2.inc:301` |
| fighters[].states[].flags | integer (minimum=-2147483648; maximum=4294967295) OR string (pattern="^(0[xX][0-9a-fA-F]+\|[0-9]+)$") | Motion-state flag bits as a 32-bit word | copied like row flags; no override | `melee/pc/platform/geno_registry.c:896`; `melee/pc/geno/geno_game_v2.inc:310` |
| fighters[].states[].move_id | integer (minimum=0; maximum=255) | Move id for staling | copied like row stale move id; no override | `melee/pc/platform/geno_registry.c:900`; `melee/pc/geno/geno_game_v2.inc:310` |
| fighters[].states[].next | integer (minimum=0; maximum=65535) OR string (pattern="^(auto\|helpless\|stay\|[mM][oO][tT][iI][oO][nN]:.+\|[sS][pP][eE][cC][iI][aA][lL]:.+\|[gG][eE][nN][oO]:.+)$") | Action target; motion integer, prefixed motion/special, Geno state or auto/helpless/stay (target reference below) | behavior-dependent; commonly auto | `melee/pc/platform/geno_registry.c:902` |
| fighters[].states[].land | integer (minimum=0; maximum=65535) OR string (pattern="^(auto\|helpless\|stay\|[mM][oO][tT][iI][oO][nN]:.+\|[sS][pP][eE][cC][iI][aA][lL]:.+\|[gG][eE][nN][oO]:.+)$") | Action target; motion integer, prefixed motion/special, Geno state or auto/helpless/stay (target reference below) | behavior-dependent; ordinary air uses Landing / landing_lag | `melee/pc/platform/geno_registry.c:904` |
| fighters[].states[].landing_lag | number | Landing lag; logic frames | 0 | `melee/pc/platform/geno_registry.c:906` |
| fighters[].states[].ledge | enum (enum=["none", "front", "both"]) OR integer (minimum=0; maximum=2) | Root-motion ledge policy: none=0, front=1, both=2 | none (0) | `melee/pc/platform/geno_registry.c:911` |
| fighters[].states[].liftoff | boolean/number | Enable when nonzero; dimensionless / flag | 1 | `melee/pc/platform/geno_registry.c:924` |
| fighters[].states[].origin | boolean/number | Enable when nonzero; dimensionless / flag | 0 | `melee/pc/platform/geno_registry.c:927` |
| fighters[].states[].move_tag | string (enum=["jab", "dash_attack", "tilt", "smash", "aerial", "grab", "throw", "special", "projectile"]) | Declared move tag | undeclared (runtime tag 0) | `melee/pc/platform/geno_registry.c:860` |
| fighters[].states[].lua | object | Named block | absent | `melee/pc/platform/geno_lua_registry.inc:127` |
| fighters[].states[].lua.enter | string (maxLength=31) | Module function run once when the state is entered | no entry Lua callback | `melee/pc/platform/geno_lua_registry.inc:127` |
| fighters[].states[].lua.frame | string (maxLength=31) | Module function invoked each logic frame; selects anim callback lua unless an explicit callback wins | no per-frame Lua callback | `melee/pc/platform/geno_lua_registry.inc:127` |
| fighters[].states[].gravity | number | Root-motion gravity multiplier | 0 | `melee/pc/platform/geno_registry.c:930` |
| fighters[].states[].facing | string (enum=["entry"]) | Lock root-motion travel to entry facing | travel follows current facing | `melee/pc/platform/geno_registry.c:932` |
| fighters[].states[].counter | object | Named block | absent | `melee/pc/platform/geno_registry.c:1080` |
| fighters[].states[].counter.from | integer | First counter action frame; logic frames | 1 | `melee/pc/platform/geno_registry.c:1083` |
| fighters[].states[].counter.to | integer | Last counter action frame; logic frames | 2147483647 | `melee/pc/platform/geno_registry.c:1084` |
| fighters[].states[].counter.target | integer (minimum=0; maximum=65535) OR string (pattern="^(auto\|helpless\|stay\|[mM][oO][tT][iI][oO][nN]:.+\|[sS][pP][eE][cC][iI][aA][lL]:.+\|[gG][eE][nN][oO]:.+)$") | Action target; motion integer, prefixed motion/special, Geno state or auto/helpless/stay (target reference below) | none: a countered hit only stays flagged | `melee/pc/platform/geno_registry.c:1087` |
| fighters[].states[].counter.negate | boolean/number | Enable when nonzero; dimensionless / flag | 1 | `melee/pc/platform/geno_registry.c:1085` |
| fighters[].states[].anim | string (enum=["like", "next", "loop", "lua", "hold", "glide.start", "glide", "tornado", "drill", "drill.end", "glide.after", "cape"]) | Override anim callback | behavior callback; lua.frame can select lua for anim | `melee/pc/platform/geno_registry.c:936`; `melee/pc/geno/geno_game_v2.inc:328`; `melee/pc/platform/geno_lua_registry.inc:141` |
| fighters[].states[].iasa | string (enum=["like", "interrupt", "none", "glide"]) | Override iasa callback | behavior callback | `melee/pc/platform/geno_registry.c:936`; `melee/pc/geno/geno_game_v2.inc:328` |
| fighters[].states[].phys | string (enum=["like", "cape", "none", "air", "air_nodrift", "air_drift", "brake", "ground", "auto", "anim_motion", "glide.start", "glide", "glide.attack", "glide.end", "tornado", "drill", "drill.end", "drill.start"]) | Override phys callback | behavior callback | `melee/pc/platform/geno_registry.c:936`; `melee/pc/geno/geno_game_v2.inc:328` |
| fighters[].states[].coll | string (enum=["like", "cape", "cape.after", "none", "air", "air_noledge", "ground", "ground_stop", "both", "anim_motion", "glide", "drill", "drill.start"]) | Override coll callback | behavior callback | `melee/pc/platform/geno_registry.c:936`; `melee/pc/geno/geno_game_v2.inc:328` |

### `articles`

| Path | Accepted editor type / constraints | Meaning and units | Default on absence | Code reference |
|---|---|---|---|---|
| fighters[].articles | array of object (maxItems=16) | Ordered entries | absent | `melee/pc/platform/geno_registry.c:1113` |
| fighters[].articles[].name | string (maxLength=31) | Article name | empty name; reference article by numeric index | `melee/pc/platform/geno_registry.c:1124` |
| fighters[].articles[].model | object | Named block | absent | `melee/pc/platform/geno_registry.c:1212` |
| fighters[].articles[].model.file | string (maxLength=63) | REQUIRED. Model archive path | REQUIRED; no usable absence default | `melee/pc/platform/geno_registry.c:1212` |
| fighters[].articles[].model.symbol | string (maxLength=63) | Model joint public symbol; absent uses first *_joint | first *_joint public symbol | `melee/pc/platform/geno_registry.c:1212` |
| fighters[].articles[].lifetime | number | Lifetime in logic frames; logic frames | 60 | `melee/pc/platform/geno_registry.c:1128` |
| fighters[].articles[].velocity | array of number (maxItems=2) | Ordered entries; Melee units / logic frame | [0,0] | `melee/pc/platform/geno_registry.c:1129` |
| fighters[].articles[].spawn | array of number (maxItems=2) | Ordered entries; Melee units | [0,0] | `melee/pc/platform/geno_registry.c:1132` |
| fighters[].articles[].scale | number | Model scale; dimensionless / flag | 1 | `melee/pc/platform/geno_registry.c:1139` |
| fighters[].articles[].spin | number | Model spin in degrees per frame; degrees / logic frame | 0 | `melee/pc/platform/geno_registry.c:1140` |
| fighters[].articles[].max_live | integer (minimum=1) | Live article limit | 4 | `melee/pc/platform/geno_registry.c:1141` |
| fighters[].articles[].homing | object | Named block | absent | `melee/pc/platform/geno_registry.c:1142` |
| fighters[].articles[].homing.turn | number | turn; degrees / logic frame | 0 | `melee/pc/platform/geno_registry.c:1143` |
| fighters[].articles[].homing.range | number | range; Melee units | 0 | `melee/pc/platform/geno_registry.c:1144` |
| fighters[].articles[].homing.delay | number | delay; logic frames | 0 | `melee/pc/platform/geno_registry.c:1145` |
| fighters[].articles[].despawn | object | Named block | hit, shield, stage and clank all enabled | `melee/pc/platform/geno_registry.c:1118`; `melee/pc/platform/geno_registry.c:1147` |
| fighters[].articles[].despawn.hit | boolean/number | Enable when nonzero | 1 | `melee/pc/platform/geno_registry.c:1073`, `melee/pc/platform/geno_registry.c:1147` |
| fighters[].articles[].despawn.shield | boolean/number | Enable when nonzero | 1 | `melee/pc/platform/geno_registry.c:1073`, `melee/pc/platform/geno_registry.c:1147` |
| fighters[].articles[].despawn.stage | boolean/number | Enable when nonzero | 1 | `melee/pc/platform/geno_registry.c:1073`, `melee/pc/platform/geno_registry.c:1147` |
| fighters[].articles[].despawn.clank | boolean/number | Enable when nonzero | 1 | `melee/pc/platform/geno_registry.c:1073`, `melee/pc/platform/geno_registry.c:1147` |
| fighters[].articles[].spins | array of object (maxItems=4) | Ordered entries | absent | `melee/pc/platform/geno_registry.c:1152` |
| fighters[].articles[].spins[].joint | integer | Model joint index | 0 | `melee/pc/platform/geno_registry.c:1156` |
| fighters[].articles[].spins[].z | number | Joint spin radians per frame; radians / logic frame | 0 | `melee/pc/platform/geno_registry.c:1157` |
| fighters[].articles[].bone | integer | Spawn from fighter joint/part index; -1 uses fighter position | -1 | `melee/pc/platform/geno_registry.c:1164` |
| fighters[].articles[].effect | integer | Melee effect id | 0 | `melee/pc/platform/geno_registry.c:1177` |
| fighters[].articles[].fx | string | Effect package name | no Geno effect package | `melee/pc/platform/geno_registry.c:1178` |
| fighters[].articles[].show_model | boolean/number | Keep the article's model drawn beside its fx package (v5.7; default: the package is the look and the model is hidden); dimensionless / flag | 0 | `melee/pc/platform/geno_registry.c:1183` |
| fighters[].articles[].spawn_sound | string (maxLength=31) | Name from the fighter's sounds table played at spawn | no named spawn sound | `melee/pc/platform/geno_registry.c:1166` |
| fighters[].articles[].end_sound | string (maxLength=31) | Name from the fighter's sounds table played when the article goes | no named end sound | `melee/pc/platform/geno_registry.c:1166` |
| fighters[].articles[].effects | array of integer OR object (maxItems=8) | Ordered entries | absent | `melee/pc/platform/geno_registry.c:1184` |
| fighters[].articles[].effects[].id | integer | Effect id | 0 | `melee/pc/platform/geno_registry.c:1189` |
| fighters[].articles[].effects[].frame | integer (minimum=0; maximum=65535) | Attach life frame; logic frames | 0 | `melee/pc/platform/geno_registry.c:1189` |
| fighters[].articles[].effects[].joint | integer (minimum=0; maximum=255) | Model joint | 0 | `melee/pc/platform/geno_registry.c:1189` |
| fighters[].articles[].effects[].count | integer (minimum=1; maximum=256) | Consecutive effect count | 1 | `melee/pc/platform/geno_registry.c:1193` |
| fighters[].articles[].spawns | array of array of number (maxItems=2) (maxItems=4) | Ordered entries; Melee units | absent | `melee/pc/platform/geno_registry.c:1198` |
| fighters[].articles[].hitboxes | array of object (maxItems=8) | Ordered entries | absent | `melee/pc/platform/geno_registry.c:1219` |
| fighters[].articles[].hitboxes[].damage | number | Damage percent; percent damage | 1 | `melee/pc/platform/geno_registry.c:1226` |
| fighters[].articles[].hitboxes[].size | number | Hitbox radius; Melee units | 3 | `melee/pc/platform/geno_registry.c:1227` |
| fighters[].articles[].hitboxes[].offset | array of number (maxItems=3) | Ordered entries; Melee units | [0,0,0] | `melee/pc/platform/geno_registry.c:1228` |
| fighters[].articles[].hitboxes[].angle | integer | Launch angle; degrees (hitbox angle also accepts engine sentinels such as 361) | 361 | `melee/pc/platform/geno_registry.c:1232` |
| fighters[].articles[].hitboxes[].kbg | integer | Knockback growth | 100 | `melee/pc/platform/geno_registry.c:1233` |
| fighters[].articles[].hitboxes[].wkb | integer | Weight-set knockback | 0 | `melee/pc/platform/geno_registry.c:1234` |
| fighters[].articles[].hitboxes[].bkb | integer | Base knockback | 0 | `melee/pc/platform/geno_registry.c:1235` |
| fighters[].articles[].hitboxes[].element | integer | Hit element | 0 | `melee/pc/platform/geno_registry.c:1236` |
| fighters[].articles[].hitboxes[].shield_damage | integer | Shield damage; percent damage | 0 | `melee/pc/platform/geno_registry.c:1237` |
| fighters[].articles[].hitboxes[].stun | integer (minimum=0; maximum=255) | Extra hitstun; extra hitstun frames | 0 | `melee/pc/platform/geno_registry.c:1239` |
| fighters[].articles[].hitboxes[].sfx_severity | integer | Hit sound severity | 1 | `melee/pc/platform/geno_registry.c:1242` |
| fighters[].articles[].hitboxes[].sfx_kind | integer | Hit sound kind | 0 | `melee/pc/platform/geno_registry.c:1243` |
| fighters[].articles[].hitboxes[].start | integer | First active life frame; logic frames | 1 | `melee/pc/platform/geno_registry.c:1244` |
| fighters[].articles[].hitboxes[].end | integer | Last active life frame; 0 = lifetime; logic frames | 0 | `melee/pc/platform/geno_registry.c:1245` |
| fighters[].articles[].hitboxes[].slot | integer (minimum=0; maximum=3) | Live hitbox slot | entry index modulo 4 | `melee/pc/platform/geno_registry.c:1247` |
| fighters[].articles[].hitboxes[].hits | object | Named block | ground, air, reflect, absorb and counter all enabled | `melee/pc/platform/geno_registry.c:1246`; `melee/pc/platform/geno_registry.c:1248` |
| fighters[].articles[].hitboxes[].hits.ground | boolean/number | Enable when nonzero | 1 | `melee/pc/platform/geno_registry.c:1074`; `melee/pc/platform/geno_registry.c:1248` |
| fighters[].articles[].hitboxes[].hits.air | boolean/number | Enable when nonzero | 1 | `melee/pc/platform/geno_registry.c:1074`; `melee/pc/platform/geno_registry.c:1248` |
| fighters[].articles[].hitboxes[].hits.reflect | boolean/number | Enable when nonzero | 1 | `melee/pc/platform/geno_registry.c:1074`; `melee/pc/platform/geno_registry.c:1248` |
| fighters[].articles[].hitboxes[].hits.absorb | boolean/number | Enable when nonzero | 1 | `melee/pc/platform/geno_registry.c:1074`; `melee/pc/platform/geno_registry.c:1248` |
| fighters[].articles[].hitboxes[].hits.counter | boolean/number | Enable when nonzero | 1 | `melee/pc/platform/geno_registry.c:1074`; `melee/pc/platform/geno_registry.c:1248` |
| fighters[].articles[].children | array of object (maxItems=2) | Ordered entries | absent | `melee/pc/platform/geno_registry.c:1266` |
| fighters[].articles[].children[].article | integer (minimum=0; maximum=15) OR string | REQUIRED. Child article index or declared article name | REQUIRED; no usable absence default | `melee/pc/platform/geno_registry.c:1269` |
| fighters[].articles[].children[].frame | integer | First spawn frame; logic frames | 1 | `melee/pc/platform/geno_registry.c:1279` |
| fighters[].articles[].children[].every | integer | Repeat interval; 0 = once; logic frames | 0 | `melee/pc/platform/geno_registry.c:1280` |
| fighters[].articles[].children[].count | integer | Spawn count | 1 | `melee/pc/platform/geno_registry.c:1281` |
| fighters[].articles[].children[].spawn | integer (minimum=0; maximum=3) | Spawn-variant index for child article, not a distance | 0 | `melee/pc/platform/geno_registry.c:1282` |
| fighters[].articles[].gravity | number | gravity; Melee units / logic-frame² | 0 | `melee/pc/platform/geno_registry.c:1135` |
| fighters[].articles[].max_fall | number | max fall; Melee units / logic frame | 0 | `melee/pc/platform/geno_registry.c:1136` |
| fighters[].articles[].accel | number | accel; Melee units / logic-frame² | 0 | `melee/pc/platform/geno_registry.c:1137` |
| fighters[].articles[].max_speed | number | max speed; Melee units / logic frame | 0 | `melee/pc/platform/geno_registry.c:1138` |
| fighters[].articles[].min_speed | number | min speed; Melee units / logic frame | 0 | `melee/pc/platform/geno_registry.c:1162` |
| fighters[].articles[].angle | number | angle; degrees | 0 | `melee/pc/platform/geno_registry.c:1163` |

### `subactions`

| Path | Accepted editor type / constraints | Meaning and units | Default on absence | Code reference |
|---|---|---|---|---|
| fighters[].subactions | array of object (maxItems=192) | Effective script overlays by animation row | absent | `melee/pc/platform/geno_registry.c:775` |
| fighters[].subactions[].index | integer (minimum=0; maximum=1023) | REQUIRED. Subaction row to replace | REQUIRED; no usable absence default | `melee/pc/platform/geno_registry.c:775` |
| fighters[].subactions[].words | array of integer (minimum=-2147483648; maximum=4294967295) OR string (pattern="^(0[xX][0-9a-fA-F]+\|[0-9]+)$") (minItems=1; maxItems=16383) | Encoded script words (portable word reference below) | exclusive alternative to file; missing both invalidates overlay | `melee/pc/platform/geno_registry.c:775` |
| fighters[].subactions[].file | string | Whitespace word file relative to mod root | exclusive alternative to words; missing both invalidates overlay | `melee/pc/platform/geno_registry.c:775` |
| fighters[].subactions[].move_tag | string (enum=["jab", "dash_attack", "tilt", "smash", "aerial", "grab", "throw", "special", "projectile"]) | Declared move tag | undeclared (runtime tag 0) | `melee/pc/platform/geno_registry.c:817` |

### `special_attributes`

| Path | Accepted editor type / constraints | Meaning and units | Default on absence | Code reference |
|---|---|---|---|---|
| fighters[].special_attributes | array of object (maxItems=64) | Ordered entries | absent | `melee/pc/platform/geno_registry.c:713` |
| fighters[].special_attributes[].index | integer (minimum=0; maximum=264) | Special attribute word index | uses offset/4; index or offset is required | `melee/pc/platform/geno_registry.c:713`; `melee/pc/platform/geno_registry.c:717` |
| fighters[].special_attributes[].offset | integer (minimum=-2147483648; maximum=4294967295) OR string (pattern="^(0[xX][0-9a-fA-F]+\|[0-9]+)$") | 4-aligned byte offset in special-attribute block, 0..1056 (0x420) | uses index; index or offset is required | `melee/pc/platform/geno_registry.c:713`; `melee/pc/platform/geno_registry.c:717` |
| fighters[].special_attributes[].float | number | Float override | uses int; float or int is required | `melee/pc/platform/geno_registry.c:713`; `melee/pc/platform/geno_registry.c:717` |
| fighters[].special_attributes[].int | integer (minimum=-2147483648; maximum=2147483647) | Integer override | uses float; float or int is required | `melee/pc/platform/geno_registry.c:713`; `melee/pc/platform/geno_registry.c:717` |

### `moves`

| Path | Accepted editor type / constraints | Meaning and units | Default on absence | Code reference |
|---|---|---|---|---|
| fighters[].moves | object | Authoring sugar for defines (move names: lowercase letters, digits, hyphens): expands to a subactions overlay plus a common_states row at export/check; the engine reads no such key | absent | `tools/geno/define.py:123` (authoring expansion; no runtime key) |
| fighters[].moves.<move> | object | Dynamic key matching `^[a-z][a-z0-9-]*$` | absent | `tools/geno/define.py:123` |
| fighters[].moves.<move>.motion | integer (minimum=0; maximum=350) | REQUIRED. Native motion row | REQUIRED; no usable absence default | `tools/geno/define.py:123` (authoring expansion; no runtime key) |
| fighters[].moves.<move>.words | string OR array of integer (minimum=-2147483648; maximum=4294967295) OR string (pattern="^(0[xX][0-9a-fA-F]+\|[0-9]+)$") (minItems=1; maxItems=16383) | REQUIRED. Encoded script words (portable word reference below) | required; overlay word array OR relative word file | `tools/geno/define.py:123` (authoring expansion; no runtime key) |
| fighters[].moves.<move>.subaction | integer (minimum=0; maximum=302) | Animation row; default: the donor's row for this motion | donor animation row for motion; unresolved row requires explicit subaction | `tools/geno/define.py:136` |
| fighters[].moves.<move>.tag | string (enum=["jab", "dash_attack", "tilt", "smash", "aerial", "grab", "throw", "special", "projectile"]) | Declared move tag | undeclared (runtime tag 0) | `tools/geno/define.py:123` (authoring expansion; no runtime key) |

### `on_land`

| Path | Accepted editor type / constraints | Meaning and units | Default on absence | Code reference |
|---|---|---|---|---|
| fighters[].on_land | array of object (maxItems=16) | Ordered entries | absent | `melee/pc/platform/geno_registry.c:739` |
| fighters[].on_land[].from | integer (minimum=0; maximum=65535) OR string (pattern="^(auto\|helpless\|stay\|[mM][oO][tT][iI][oO][nN]:.+\|[sS][pP][eE][cC][iI][aA][lL]:.+\|[gG][eE][nN][oO]:.+)$") | REQUIRED. Action target; motion integer, prefixed motion/special, Geno state or auto/helpless/stay (target reference below); action target (not frames) | REQUIRED; no usable absence default | `melee/pc/platform/geno_registry.c:739` |
| fighters[].on_land[].to | integer (minimum=0; maximum=65535) OR string (pattern="^(auto\|helpless\|stay\|[mM][oO][tT][iI][oO][nN]:.+\|[sS][pP][eE][cC][iI][aA][lL]:.+\|[gG][eE][nN][oO]:.+)$") | REQUIRED. Action target; motion integer, prefixed motion/special, Geno state or auto/helpless/stay (target reference below); action target (not frames) | REQUIRED; no usable absence default | `melee/pc/platform/geno_registry.c:739` |
| fighters[].on_land[].keep_frame | boolean | Keep current animation frame | False | `melee/pc/platform/geno_registry.c:739` |

### `motion_anims`

| Path | Accepted editor type / constraints | Meaning and units | Default on absence | Code reference |
|---|---|---|---|---|
| fighters[].motion_anims | array of object (maxItems=8) | Ordered entries | absent | `melee/pc/platform/geno_registry.c:759` |
| fighters[].motion_anims[].motion | integer (minimum=0; maximum=1023) | REQUIRED. Common motion id | REQUIRED; no usable absence default | `melee/pc/platform/geno_registry.c:759` |
| fighters[].motion_anims[].subaction | integer (minimum=0; maximum=1023) | REQUIRED. Animation row | REQUIRED; no usable absence default | `melee/pc/platform/geno_registry.c:759` |

### `specials`

| Path | Accepted editor type / constraints | Meaning and units | Default on absence | Code reference |
|---|---|---|---|---|
| fighters[].specials | object | Named block | unbound: donor specials; missing air_* inherits grounded counterpart | `melee/pc/platform/geno_registry.c:968` |
| fighters[].specials.n | integer (minimum=0; maximum=65535) OR string (pattern="^(auto\|helpless\|stay\|[mM][oO][tT][iI][oO][nN]:.+\|[sS][pP][eE][cC][iI][aA][lL]:.+\|[gG][eE][nN][oO]:.+)$") OR object | Value in the listed alternatives | unbound: donor special | `melee/pc/platform/geno_registry.c:968` |
| fighters[].specials.n.select | string (pattern="^(la_i\|ra_i):(?:[0-9]\|[1-5][0-9]\|6[0-3])$") | REQUIRED. Integer bank selector | REQUIRED; no usable absence default | `melee/pc/platform/geno_registry.c:830` |
| fighters[].specials.n.targets | array of integer (minimum=0; maximum=65535) OR string (pattern="^(auto\|helpless\|stay\|[mM][oO][tT][iI][oO][nN]:.+\|[sS][pP][eE][cC][iI][aA][lL]:.+\|[gG][eE][nN][oO]:.+)$") (minItems=1; maxItems=4) | REQUIRED. Ordered entries | REQUIRED; no usable absence default | `melee/pc/platform/geno_registry.c:830` |
| fighters[].specials.s | integer (minimum=0; maximum=65535) OR string (pattern="^(auto\|helpless\|stay\|[mM][oO][tT][iI][oO][nN]:.+\|[sS][pP][eE][cC][iI][aA][lL]:.+\|[gG][eE][nN][oO]:.+)$") OR object | Value in the listed alternatives | unbound: donor special | `melee/pc/platform/geno_registry.c:968` |
| fighters[].specials.s.select | string (pattern="^(la_i\|ra_i):(?:[0-9]\|[1-5][0-9]\|6[0-3])$") | REQUIRED. Integer bank selector | REQUIRED; no usable absence default | `melee/pc/platform/geno_registry.c:830` |
| fighters[].specials.s.targets | array of integer (minimum=0; maximum=65535) OR string (pattern="^(auto\|helpless\|stay\|[mM][oO][tT][iI][oO][nN]:.+\|[sS][pP][eE][cC][iI][aA][lL]:.+\|[gG][eE][nN][oO]:.+)$") (minItems=1; maxItems=4) | REQUIRED. Ordered entries | REQUIRED; no usable absence default | `melee/pc/platform/geno_registry.c:830` |
| fighters[].specials.hi | integer (minimum=0; maximum=65535) OR string (pattern="^(auto\|helpless\|stay\|[mM][oO][tT][iI][oO][nN]:.+\|[sS][pP][eE][cC][iI][aA][lL]:.+\|[gG][eE][nN][oO]:.+)$") OR object | Value in the listed alternatives | unbound: donor special | `melee/pc/platform/geno_registry.c:968` |
| fighters[].specials.hi.select | string (pattern="^(la_i\|ra_i):(?:[0-9]\|[1-5][0-9]\|6[0-3])$") | REQUIRED. Integer bank selector | REQUIRED; no usable absence default | `melee/pc/platform/geno_registry.c:830` |
| fighters[].specials.hi.targets | array of integer (minimum=0; maximum=65535) OR string (pattern="^(auto\|helpless\|stay\|[mM][oO][tT][iI][oO][nN]:.+\|[sS][pP][eE][cC][iI][aA][lL]:.+\|[gG][eE][nN][oO]:.+)$") (minItems=1; maxItems=4) | REQUIRED. Ordered entries | REQUIRED; no usable absence default | `melee/pc/platform/geno_registry.c:830` |
| fighters[].specials.lw | integer (minimum=0; maximum=65535) OR string (pattern="^(auto\|helpless\|stay\|[mM][oO][tT][iI][oO][nN]:.+\|[sS][pP][eE][cC][iI][aA][lL]:.+\|[gG][eE][nN][oO]:.+)$") OR object | Value in the listed alternatives | unbound: donor special | `melee/pc/platform/geno_registry.c:968` |
| fighters[].specials.lw.select | string (pattern="^(la_i\|ra_i):(?:[0-9]\|[1-5][0-9]\|6[0-3])$") | REQUIRED. Integer bank selector | REQUIRED; no usable absence default | `melee/pc/platform/geno_registry.c:830` |
| fighters[].specials.lw.targets | array of integer (minimum=0; maximum=65535) OR string (pattern="^(auto\|helpless\|stay\|[mM][oO][tT][iI][oO][nN]:.+\|[sS][pP][eE][cC][iI][aA][lL]:.+\|[gG][eE][nN][oO]:.+)$") (minItems=1; maxItems=4) | REQUIRED. Ordered entries | REQUIRED; no usable absence default | `melee/pc/platform/geno_registry.c:830` |
| fighters[].specials.air_n | integer (minimum=0; maximum=65535) OR string (pattern="^(auto\|helpless\|stay\|[mM][oO][tT][iI][oO][nN]:.+\|[sS][pP][eE][cC][iI][aA][lL]:.+\|[gG][eE][nN][oO]:.+)$") OR object | Value in the listed alternatives | inherit corresponding grounded special | `melee/pc/platform/geno_registry.c:968`; `melee/pc/platform/geno_registry.c:981` |
| fighters[].specials.air_n.select | string (pattern="^(la_i\|ra_i):(?:[0-9]\|[1-5][0-9]\|6[0-3])$") | REQUIRED. Integer bank selector | REQUIRED; no usable absence default | `melee/pc/platform/geno_registry.c:830` |
| fighters[].specials.air_n.targets | array of integer (minimum=0; maximum=65535) OR string (pattern="^(auto\|helpless\|stay\|[mM][oO][tT][iI][oO][nN]:.+\|[sS][pP][eE][cC][iI][aA][lL]:.+\|[gG][eE][nN][oO]:.+)$") (minItems=1; maxItems=4) | REQUIRED. Ordered entries | REQUIRED; no usable absence default | `melee/pc/platform/geno_registry.c:830` |
| fighters[].specials.air_s | integer (minimum=0; maximum=65535) OR string (pattern="^(auto\|helpless\|stay\|[mM][oO][tT][iI][oO][nN]:.+\|[sS][pP][eE][cC][iI][aA][lL]:.+\|[gG][eE][nN][oO]:.+)$") OR object | Value in the listed alternatives | inherit corresponding grounded special | `melee/pc/platform/geno_registry.c:968`; `melee/pc/platform/geno_registry.c:981` |
| fighters[].specials.air_s.select | string (pattern="^(la_i\|ra_i):(?:[0-9]\|[1-5][0-9]\|6[0-3])$") | REQUIRED. Integer bank selector | REQUIRED; no usable absence default | `melee/pc/platform/geno_registry.c:830` |
| fighters[].specials.air_s.targets | array of integer (minimum=0; maximum=65535) OR string (pattern="^(auto\|helpless\|stay\|[mM][oO][tT][iI][oO][nN]:.+\|[sS][pP][eE][cC][iI][aA][lL]:.+\|[gG][eE][nN][oO]:.+)$") (minItems=1; maxItems=4) | REQUIRED. Ordered entries | REQUIRED; no usable absence default | `melee/pc/platform/geno_registry.c:830` |
| fighters[].specials.air_hi | integer (minimum=0; maximum=65535) OR string (pattern="^(auto\|helpless\|stay\|[mM][oO][tT][iI][oO][nN]:.+\|[sS][pP][eE][cC][iI][aA][lL]:.+\|[gG][eE][nN][oO]:.+)$") OR object | Value in the listed alternatives | inherit corresponding grounded special | `melee/pc/platform/geno_registry.c:968`; `melee/pc/platform/geno_registry.c:981` |
| fighters[].specials.air_hi.select | string (pattern="^(la_i\|ra_i):(?:[0-9]\|[1-5][0-9]\|6[0-3])$") | REQUIRED. Integer bank selector | REQUIRED; no usable absence default | `melee/pc/platform/geno_registry.c:830` |
| fighters[].specials.air_hi.targets | array of integer (minimum=0; maximum=65535) OR string (pattern="^(auto\|helpless\|stay\|[mM][oO][tT][iI][oO][nN]:.+\|[sS][pP][eE][cC][iI][aA][lL]:.+\|[gG][eE][nN][oO]:.+)$") (minItems=1; maxItems=4) | REQUIRED. Ordered entries | REQUIRED; no usable absence default | `melee/pc/platform/geno_registry.c:830` |
| fighters[].specials.air_lw | integer (minimum=0; maximum=65535) OR string (pattern="^(auto\|helpless\|stay\|[mM][oO][tT][iI][oO][nN]:.+\|[sS][pP][eE][cC][iI][aA][lL]:.+\|[gG][eE][nN][oO]:.+)$") OR object | Value in the listed alternatives | inherit corresponding grounded special | `melee/pc/platform/geno_registry.c:968`; `melee/pc/platform/geno_registry.c:981` |
| fighters[].specials.air_lw.select | string (pattern="^(la_i\|ra_i):(?:[0-9]\|[1-5][0-9]\|6[0-3])$") | REQUIRED. Integer bank selector | REQUIRED; no usable absence default | `melee/pc/platform/geno_registry.c:830` |
| fighters[].specials.air_lw.targets | array of integer (minimum=0; maximum=65535) OR string (pattern="^(auto\|helpless\|stay\|[mM][oO][tT][iI][oO][nN]:.+\|[sS][pP][eE][cC][iI][aA][lL]:.+\|[gG][eE][nN][oO]:.+)$") (minItems=1; maxItems=4) | REQUIRED. Ordered entries | REQUIRED; no usable absence default | `melee/pc/platform/geno_registry.c:830` |

### `fx_bindings`

| Path | Accepted editor type / constraints | Meaning and units | Default on absence | Code reference |
|---|---|---|---|---|
| fighters[].fx_bindings | string | Effect bindings JSON relative path | no effect bindings | `melee/pc/platform/geno_registry.c:1375` |

### `lua`

| Path | Accepted editor type / constraints | Meaning and units | Default on absence | Code reference |
|---|---|---|---|---|
| fighters[].lua | object | Named block | absent | `melee/pc/platform/geno_lua_registry.inc:45` |
| fighters[].lua.script | string | Lua module file relative to the mod root (returns a table of functions) | source alternative required when lua exists; missing both refuses entry | `melee/pc/platform/geno_lua_registry.inc:64` |
| fighters[].lua.source | string | Inline Lua module text (tests; a script file is the normal form) | script alternative required when lua exists; missing both refuses entry | `melee/pc/platform/geno_lua_registry.inc:64` |
| fighters[].lua.state | object (maxProperties=16) | Typed per-fighter state: slot name to int / float / bool | no slots; each declared slot begins zero / false | `melee/pc/platform/geno_lua_registry.inc:90` |
| fighters[].lua.state.<slot> | enum (enum=["int", "float", "bool"]) | Dynamic key matching `^.*$` | absent | `melee/pc/platform/geno_lua_registry.inc:90` |

### `sounds`

| Path | Accepted editor type / constraints | Meaning and units | Default on absence | Code reference |
|---|---|---|---|---|
| fighters[].sounds | array of object (maxItems=16) | Ordered entries | absent | `melee/pc/platform/geno_registry.c:1035` |
| fighters[].sounds[].name | string (minLength=1; maxLength=31) | REQUIRED. Sound name an article refers to | REQUIRED; no usable absence default | `melee/pc/platform/geno_registry.c:1035` |
| fighters[].sounds[].retail_sfx | integer (minimum=1; maximum=999999) | REQUIRED. Engine sound id (ft_PlaySFX's) | REQUIRED; no usable absence default | `melee/pc/platform/geno_registry.c:1035` |
| fighters[].sounds[].volume | integer (minimum=0; maximum=127) | Volume 0..127; engine volume 0..127 | 127 | `melee/pc/platform/geno_registry.c:1035` |

### `glide`

| Path | Accepted editor type / constraints | Meaning and units | Default on absence | Code reference |
|---|---|---|---|---|
| fighters[].glide | object | Named block | native parameter defaults listed below; no overrides | `melee/pc/platform/geno_registry.c:945` |
| fighters[].glide.angle_max | number/boolean | Behavior parameter angle_max; degrees | 80.0 | `melee/pc/geno/geno_game_v2.inc:55` |
| fighters[].glide.angle_min | number/boolean | Behavior parameter angle_min; degrees | -70.0 | `melee/pc/geno/geno_game_v2.inc:56` |
| fighters[].glide.start_vy | number/boolean | Behavior parameter start_vy; Melee units / logic frame | 0.75 | `melee/pc/geno/geno_game_v2.inc:57` |
| fighters[].glide.start_gravity | number/boolean | Behavior parameter start_gravity | 1.0 | `melee/pc/geno/geno_game_v2.inc:58` |
| fighters[].glide.start_vx | number/boolean | Behavior parameter start_vx; dimensionless / flag | 1.0 | `melee/pc/geno/geno_game_v2.inc:59` |
| fighters[].glide.speed | number/boolean | Behavior parameter speed; Melee units / logic frame | 1.7 | `melee/pc/geno/geno_game_v2.inc:60` |
| fighters[].glide.speed_accel | number/boolean | Behavior parameter speed_accel; Melee units / logic-frame² | 0.04 | `melee/pc/geno/geno_game_v2.inc:61` |
| fighters[].glide.max_speed | number/boolean | Behavior parameter max_speed; Melee units / logic frame | 2.2 | `melee/pc/geno/geno_game_v2.inc:62` |
| fighters[].glide.stall_speed | number/boolean | Behavior parameter stall_speed; Melee units / logic frame | 0.7 | `melee/pc/geno/geno_game_v2.inc:63` |
| fighters[].glide.sink_accel | number/boolean | Behavior parameter sink_accel; Melee units / logic-frame² | 0.03 | `melee/pc/geno/geno_game_v2.inc:64` |
| fighters[].glide.max_sink | number/boolean | Behavior parameter max_sink; Melee units / logic frame | 0.6 | `melee/pc/geno/geno_game_v2.inc:65` |
| fighters[].glide.recover_angle | number/boolean | Behavior parameter recover_angle; degrees | 15.0 | `melee/pc/geno/geno_game_v2.inc:66` |
| fighters[].glide.dive_angle | number/boolean | Behavior parameter dive_angle; degrees | -25.0 | `melee/pc/geno/geno_game_v2.inc:67` |
| fighters[].glide.dive_bonus | number/boolean | Behavior parameter dive_bonus; Melee units / logic-frame² | 0.03 | `melee/pc/geno/geno_game_v2.inc:68` |
| fighters[].glide.w14 | number/boolean | Behavior parameter w14 | 0.15 | `melee/pc/geno/geno_game_v2.inc:69` |
| fighters[].glide.deadzone | number/boolean | Behavior parameter deadzone; dimensionless / flag | 0.25 | `melee/pc/geno/geno_game_v2.inc:70` |
| fighters[].glide.pitch_up | number/boolean | Behavior parameter pitch_up; degrees / logic-frame² | 0.55 | `melee/pc/geno/geno_game_v2.inc:71` |
| fighters[].glide.pitch_down | number/boolean | Behavior parameter pitch_down; degrees / logic-frame² | 0.75 | `melee/pc/geno/geno_game_v2.inc:72` |
| fighters[].glide.max_pitch_rate | number/boolean | Behavior parameter max_pitch_rate; degrees / logic frame | 7.0 | `melee/pc/geno/geno_game_v2.inc:73` |
| fighters[].glide.stall_pitch | number/boolean | Behavior parameter stall_pitch | 1.0 | `melee/pc/geno/geno_game_v2.inc:74` |
| fighters[].glide.wing_node | number/boolean | Behavior parameter wing_node | 44.0 | `melee/pc/geno/geno_game_v2.inc:75` |
| fighters[].glide.w21 | number/boolean | Behavior parameter w21 | 0.0 | `melee/pc/geno/geno_game_v2.inc:76` |
| fighters[].glide.hold_frames | number/boolean | Behavior parameter hold_frames; logic frames | 16.0 | `melee/pc/geno/geno_game_v2.inc:77` |
| fighters[].glide.from_ground_jump | number/boolean | Behavior parameter from_ground_jump | 0.0 | `melee/pc/geno/geno_game_v2.inc:78` |
| fighters[].glide.end_helpless | number/boolean | Behavior parameter end_helpless | 0.0 | `melee/pc/geno/geno_game_v2.inc:79` |
| fighters[].glide.landing_lag | number/boolean | Behavior parameter landing_lag; logic frames | 0.0 | `melee/pc/geno/geno_game_v2.inc:80` |
| fighters[].glide.entry | number/boolean | Behavior parameter entry | 1.0 | `melee/pc/geno/geno_game_v2.inc:81` |
| fighters[].glide.max_frames | number/boolean | Behavior parameter max_frames; logic frames | 0.0 | `melee/pc/geno/geno_game_v2.inc:82` |
| fighters[].glide.pose_center | number/boolean | Behavior parameter pose_center | 0.0 | `melee/pc/geno/geno_game_v2.inc:83` |
| fighters[].glide.end_buttons | number/boolean | Behavior parameter end_buttons | 14 | `melee/pc/geno/geno_game_v2.inc:84` |
| fighters[].glide.script_entry_helpless | number/boolean | Behavior parameter script_entry_helpless | 1.0 | `melee/pc/geno/geno_game_v2.inc:127` |
| fighters[].glide.w00 | number/boolean | Behavior parameter w00 | 80.0 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].glide.w01 | number/boolean | Behavior parameter w01 | -70.0 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].glide.w02 | number/boolean | Behavior parameter w02 | 0.75 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].glide.w03 | number/boolean | Behavior parameter w03 | 1.0 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].glide.w04 | number/boolean | Behavior parameter w04 | 1.0 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].glide.w05 | number/boolean | Behavior parameter w05 | 1.7 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].glide.w06 | number/boolean | Behavior parameter w06 | 0.04 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].glide.w07 | number/boolean | Behavior parameter w07 | 2.2 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].glide.w08 | number/boolean | Behavior parameter w08 | 0.7 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].glide.w09 | number/boolean | Behavior parameter w09 | 0.03 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].glide.w10 | number/boolean | Behavior parameter w10 | 0.6 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].glide.w11 | number/boolean | Behavior parameter w11 | 15.0 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].glide.w12 | number/boolean | Behavior parameter w12 | -25.0 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].glide.w13 | number/boolean | Behavior parameter w13 | 0.03 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].glide.w15 | number/boolean | Behavior parameter w15 | 0.25 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].glide.w16 | number/boolean | Behavior parameter w16 | 0.55 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].glide.w17 | number/boolean | Behavior parameter w17 | 0.75 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].glide.w18 | number/boolean | Behavior parameter w18 | 7.0 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].glide.w19 | number/boolean | Behavior parameter w19 | 1.0 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].glide.w20 | number/boolean | Behavior parameter w20 | 44.0 | `melee/pc/geno/geno_game_v2.inc:152` |

### `tornado`

| Path | Accepted editor type / constraints | Meaning and units | Default on absence | Code reference |
|---|---|---|---|---|
| fighters[].tornado | object | Named block | native parameter defaults listed below; no overrides | `melee/pc/platform/geno_registry.c:945` |
| fighters[].tornado.entry_vy | number/boolean | Behavior parameter entry_vy; Melee units / logic frame | 1.0 | `melee/pc/geno/geno_game_v2.inc:88` |
| fighters[].tornado.entry_vx_mul | number/boolean | Behavior parameter entry_vx_mul; dimensionless / flag | 0.7 | `melee/pc/geno/geno_game_v2.inc:89` |
| fighters[].tornado.start_rate | number/boolean | Behavior parameter start_rate | 80.0 | `melee/pc/geno/geno_game_v2.inc:90` |
| fighters[].tornado.ground_accel | number/boolean | Behavior parameter ground_accel; Melee units / logic-frame² | 0.12 | `melee/pc/geno/geno_game_v2.inc:91` |
| fighters[].tornado.ground_speed | number/boolean | Behavior parameter ground_speed; Melee units / logic frame | 2.0 | `melee/pc/geno/geno_game_v2.inc:92` |
| fighters[].tornado.air_accel | number/boolean | Behavior parameter air_accel; Melee units / logic-frame² | 0.1 | `melee/pc/geno/geno_game_v2.inc:93` |
| fighters[].tornado.air_speed | number/boolean | Behavior parameter air_speed; Melee units / logic frame | 1.7 | `melee/pc/geno/geno_game_v2.inc:94` |
| fighters[].tornado.brake | number/boolean | Behavior parameter brake; Melee units / logic-frame² | 0.008 | `melee/pc/geno/geno_game_v2.inc:95` |
| fighters[].tornado.gravity | number/boolean | Behavior parameter gravity; Melee units / logic-frame² | -0.08 | `melee/pc/geno/geno_game_v2.inc:96` |
| fighters[].tornado.max_fall | number/boolean | Behavior parameter max_fall; Melee units / logic frame | 0.5 | `melee/pc/geno/geno_game_v2.inc:97` |
| fighters[].tornado.tap_vy | number/boolean | Behavior parameter tap_vy; Melee units / logic frame | 1.0 | `melee/pc/geno/geno_game_v2.inc:98` |
| fighters[].tornado.tap_cooldown | number/boolean | Behavior parameter tap_cooldown; logic frames | 10.0 | `melee/pc/geno/geno_game_v2.inc:99` |
| fighters[].tornado.max_rise | number/boolean | Behavior parameter max_rise; Melee units / logic frame | 1.4 | `melee/pc/geno/geno_game_v2.inc:100` |
| fighters[].tornado.tap_rate | number/boolean | Behavior parameter tap_rate | 16.0 | `melee/pc/geno/geno_game_v2.inc:101` |
| fighters[].tornado.max_rate | number/boolean | Behavior parameter max_rate | 80.0 | `melee/pc/geno/geno_game_v2.inc:102` |
| fighters[].tornado.rate_decay | number/boolean | Behavior parameter rate_decay | 1.5 | `melee/pc/geno/geno_game_v2.inc:103` |
| fighters[].tornado.spin_frames | number/boolean | Behavior parameter spin_frames; logic frames | 70.0 | `melee/pc/geno/geno_game_v2.inc:104` |
| fighters[].tornado.late_decay | number/boolean | Behavior parameter late_decay | 2.0 | `melee/pc/geno/geno_game_v2.inc:105` |
| fighters[].tornado.end_rate | number/boolean | Behavior parameter end_rate | 10.0 | `melee/pc/geno/geno_game_v2.inc:106` |
| fighters[].tornado.w19 | number/boolean | Behavior parameter w19 | 0.0 | `melee/pc/geno/geno_game_v2.inc:107` |
| fighters[].tornado.max_speed | number/boolean | Behavior parameter max_speed; Melee units / logic frame | 2.5 | `melee/pc/geno/geno_game_v2.inc:108` |
| fighters[].tornado.end_helpless | number/boolean | Behavior parameter end_helpless | 1.0 | `melee/pc/geno/geno_game_v2.inc:109` |
| fighters[].tornado.spin_anim | number/boolean | Behavior parameter spin_anim | 0.0 | `melee/pc/geno/geno_game_v2.inc:110` |
| fighters[].tornado.spin_period | number/boolean | Behavior parameter spin_period | 0.0 | `melee/pc/geno/geno_game_v2.inc:111` |
| fighters[].tornado.w00 | number/boolean | Behavior parameter w00 | 1.0 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].tornado.w01 | number/boolean | Behavior parameter w01 | 0.7 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].tornado.w02 | number/boolean | Behavior parameter w02 | 80.0 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].tornado.w03 | number/boolean | Behavior parameter w03 | 0.12 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].tornado.w04 | number/boolean | Behavior parameter w04 | 2.0 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].tornado.w05 | number/boolean | Behavior parameter w05 | 0.1 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].tornado.w06 | number/boolean | Behavior parameter w06 | 1.7 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].tornado.w07 | number/boolean | Behavior parameter w07 | 0.008 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].tornado.w08 | number/boolean | Behavior parameter w08 | -0.08 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].tornado.w09 | number/boolean | Behavior parameter w09 | 0.5 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].tornado.w10 | number/boolean | Behavior parameter w10 | 1.0 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].tornado.w11 | number/boolean | Behavior parameter w11 | 10.0 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].tornado.w12 | number/boolean | Behavior parameter w12 | 1.4 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].tornado.w13 | number/boolean | Behavior parameter w13 | 16.0 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].tornado.w14 | number/boolean | Behavior parameter w14 | 80.0 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].tornado.w15 | number/boolean | Behavior parameter w15 | 1.5 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].tornado.w16 | number/boolean | Behavior parameter w16 | 70.0 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].tornado.w17 | number/boolean | Behavior parameter w17 | 2.0 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].tornado.w18 | number/boolean | Behavior parameter w18 | 10.0 | `melee/pc/geno/geno_game_v2.inc:152` |

### `drill`

| Path | Accepted editor type / constraints | Meaning and units | Default on absence | Code reference |
|---|---|---|---|---|
| fighters[].drill | object | Named block | native parameter defaults listed below; no overrides | `melee/pc/platform/geno_registry.c:945` |
| fighters[].drill.start_vx_mul | number/boolean | Behavior parameter start_vx_mul; dimensionless / flag | 0.5 | `melee/pc/geno/geno_game_v2.inc:114` |
| fighters[].drill.start_vy | number/boolean | Behavior parameter start_vy; Melee units / logic frame | 1.0 | `melee/pc/geno/geno_game_v2.inc:115` |
| fighters[].drill.start_gravity | number/boolean | Behavior parameter start_gravity | -0.08 | `melee/pc/geno/geno_game_v2.inc:116` |
| fighters[].drill.steer | number/boolean | Behavior parameter steer; degrees / logic frame | 3.0 | `melee/pc/geno/geno_game_v2.inc:117` |
| fighters[].drill.end_frames | number/boolean | Behavior parameter end_frames; logic frames | 10.0 | `melee/pc/geno/geno_game_v2.inc:118` |
| fighters[].drill.w05 | number/boolean | Behavior parameter w05 | 0.0 | `melee/pc/geno/geno_game_v2.inc:119` |
| fighters[].drill.speed | number/boolean | Behavior parameter speed; Melee units / logic frame | 2.0 | `melee/pc/geno/geno_game_v2.inc:120` |
| fighters[].drill.angle_max | number/boolean | Behavior parameter angle_max; degrees | 0.0 | `melee/pc/geno/geno_game_v2.inc:121` |
| fighters[].drill.bounce | number/boolean | Behavior parameter bounce | 0.0 | `melee/pc/geno/geno_game_v2.inc:122` |
| fighters[].drill.pop_vx | number/boolean | Behavior parameter pop_vx; Melee units / logic frame | 1.0 | `melee/pc/geno/geno_game_v2.inc:123` |
| fighters[].drill.pop_vy | number/boolean | Behavior parameter pop_vy; Melee units / logic frame | 2.1 | `melee/pc/geno/geno_game_v2.inc:124` |
| fighters[].drill.end_helpless | number/boolean | Behavior parameter end_helpless | 1.0 | `melee/pc/geno/geno_game_v2.inc:125` |
| fighters[].drill.pitch_model | number/boolean | Behavior parameter pitch_model | 1.0 | `melee/pc/geno/geno_game_v2.inc:126` |
| fighters[].drill.w00 | number/boolean | Behavior parameter w00 | 0.5 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].drill.w01 | number/boolean | Behavior parameter w01 | 1.0 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].drill.w02 | number/boolean | Behavior parameter w02 | -0.08 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].drill.w03 | number/boolean | Behavior parameter w03 | 3.0 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].drill.w04 | number/boolean | Behavior parameter w04 | 10.0 | `melee/pc/geno/geno_game_v2.inc:152` |

### `cape`

| Path | Accepted editor type / constraints | Meaning and units | Default on absence | Code reference |
|---|---|---|---|---|
| fighters[].cape | object | Named block | native parameter defaults listed below; no overrides | `melee/pc/platform/geno_registry.c:945` |
| fighters[].cape.keep_vx | number/boolean | Behavior parameter keep_vx; dimensionless / flag | 0.5 | `melee/pc/geno/geno_game_v2.inc:130` |
| fighters[].cape.keep_vy | number/boolean | Behavior parameter keep_vy; dimensionless / flag | 0.4 | `melee/pc/geno/geno_game_v2.inc:131` |
| fighters[].cape.steer_accel_x | number/boolean | Behavior parameter steer_accel_x | 0.5 | `melee/pc/geno/geno_game_v2.inc:132` |
| fighters[].cape.steer_max_x | number/boolean | Behavior parameter steer_max_x; Melee units / logic frame | 2.5 | `melee/pc/geno/geno_game_v2.inc:133` |
| fighters[].cape.steer_accel_y | number/boolean | Behavior parameter steer_accel_y | 0.5 | `melee/pc/geno/geno_game_v2.inc:134` |
| fighters[].cape.steer_max_y | number/boolean | Behavior parameter steer_max_y; Melee units / logic frame | 2.5 | `melee/pc/geno/geno_game_v2.inc:135` |
| fighters[].cape.steer_frame | number/boolean | Behavior parameter steer_frame; logic frames | 12.0 | `melee/pc/geno/geno_game_v2.inc:136` |
| fighters[].cape.decide_frame | number/boolean | Behavior parameter decide_frame; logic frames | 26.0 | `melee/pc/geno/geno_game_v2.inc:137` |
| fighters[].cape.neutral_x | number/boolean | Behavior parameter neutral_x; dimensionless / flag | 0.3 | `melee/pc/geno/geno_game_v2.inc:138` |
| fighters[].cape.attack_buttons | number/boolean | Behavior parameter attack_buttons | 3 | `melee/pc/geno/geno_game_v2.inc:139` |
| fighters[].cape.w00 | number/boolean | Behavior parameter w00 | 0.5 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].cape.w01 | number/boolean | Behavior parameter w01 | 0.4 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].cape.w02 | number/boolean | Behavior parameter w02 | 0.5 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].cape.w03 | number/boolean | Behavior parameter w03 | 2.5 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].cape.w04 | number/boolean | Behavior parameter w04 | 0.5 | `melee/pc/geno/geno_game_v2.inc:152` |
| fighters[].cape.w05 | number/boolean | Behavior parameter w05 | 2.5 | `melee/pc/geno/geno_game_v2.inc:152` |

### `fighter`

| Path | Accepted editor type / constraints | Meaning and units | Default on absence | Code reference |
|---|---|---|---|---|
| fighters[].fighter | object | Own model, bank and plan declaration for base none | required for base none; unused for base mario | `melee/pc/platform/geno_define_registry.inc:13` |
| fighters[].fighter.plan | string | REQUIRED. The fighter plan (plan.json): joints, parts, rows, ftData joint fields, hurtboxes | REQUIRED; no usable absence default | `melee/pc/platform/geno_define_registry.inc:20` |
| fighters[].fighter.animation | string | REQUIRED. The animation file (a .dat of figatrees, the bank) | REQUIRED; no usable absence default | `melee/pc/platform/geno_define_registry.inc:20` |
| fighters[].fighter.costumes | array of object (maxItems=16) | REQUIRED. Ordered entries | REQUIRED; no usable absence default | `melee/pc/platform/geno_define_registry.inc:23` |
| fighters[].fighter.costumes[].file | string | REQUIRED. Costume model .dat | REQUIRED; no usable absence default | `melee/pc/platform/geno_define_registry.inc:43` |
| fighters[].fighter.costumes[].joint | string | REQUIRED. Joint-tree symbol | REQUIRED; no usable absence default | `melee/pc/platform/geno_define_registry.inc:43` |
| fighters[].fighter.costumes[].matanim | string | Material-animation symbol | no material-animation symbol | `melee/pc/platform/geno_define_registry.inc:43` |
| fighters[].fighter.costumes[].name | string (minLength=1; maxLength=23; pattern="^[ -~]+$") | Costume name the select shows (printable ASCII, 1..23 characters) | displayed as Costume N | `melee/pc/platform/geno_define_registry.inc:48` |
| fighters[].fighter.costumes[].team | string (enum=["red", "blue", "green"]) | The team battle colour this costume is (the first one declared wins; undeclared: red is costume 0, blue 1, green 2) | red index 0; blue 1; green 2, out-of-range wraps 0; first declared team wins | `melee/pc/platform/geno_define_registry.inc:48` |
| fighters[].fighter.rows | array of string (minLength=1; maxLength=31) (maxItems=128) | Ordered entries | absent | `melee/pc/platform/geno_define_registry.inc:71` |

### `presentation`

| Path | Accepted editor type / constraints | Meaning and units | Default on absence | Code reference |
|---|---|---|---|---|
| fighters[].presentation | object | Own select icon/portrait, HUD and results stock icon, results card portrait, and nonpaletted results emblem; geno 9 | absent | `melee/pc/platform/geno_define_registry.inc:104`; `melee/src/melee/gm/gmresultplayer.c:804`; `:1535` |
| fighters[].presentation.icon | string (maxLength=63; pattern="^[A-Za-z0-9_.+@#%&=,;'!()-]+\\.[gG][xX][tT][eE][xX]$") | A .gxtex file of the mod's files/ folder (pc/tools/png2gx.py); a plain file name | donor art for base mario; letters for base none | `melee/pc/platform/geno_define_registry.inc:104` |
| fighters[].presentation.portrait | string (maxLength=63; pattern="^[A-Za-z0-9_.+@#%&=,;'!()-]+\\.[gG][xX][tT][eE][xX]$") OR array of string (maxLength=63; pattern="^[A-Za-z0-9_.+@#%&=,;'!()-]+\\.[gG][xX][tT][eE][xX]$") (minItems=1; maxItems=16) | One .gxtex or list by costume; also supplies results card picture | donor select art for base mario; DISC ART for base none; results card picture hidden | `melee/pc/platform/geno_define_registry.inc:104` |
| fighters[].presentation.stock | string (maxLength=63; pattern="^[A-Za-z0-9_.+@#%&=,;'!()-]+\\.[gG][xX][tT][eE][xX]$") OR array of string (maxLength=63; pattern="^[A-Za-z0-9_.+@#%&=,;'!()-]+\\.[gG][xX][tT][eE][xX]$") (minItems=1; maxItems=16) | One nonpaletted .gxtex or list by costume; HUD stock and small results stock icon | donor stock frame | `melee/pc/platform/geno_define_registry.inc:104` |
| fighters[].presentation.emblem | string (maxLength=63; pattern="^[A-Za-z0-9_.+@#%&=,;'!()-]+\\.[gG][xX][tT][eE][xX]$") | A .gxtex file of the mod's files/ folder (pc/tools/png2gx.py); a plain file name | no package results emblem | `melee/pc/platform/geno_define_registry.inc:104` |

### `ai`

| Path | Accepted editor type / constraints | Meaning and units | Default on absence | Code reference |
|---|---|---|---|---|
| fighters[].ai | object | The CPU plays this define as that retail fighter (its recovery, special-move choices and per-kind AI tables) (geno: 10) | absent | `melee/pc/platform/geno_define_registry.inc:186` |
| fighters[].ai.like | string | REQUIRED. A retail fighter (mario, fox, captain, donkey, kirby, koopa, link, seak, ness, peach, popo, pikachu, samus, yoshi, purin, mewtwo, luigi, mars, zelda, clink, drmario, falco, pichu, gamewatch, ganon, emblem, or their aliases) | REQUIRED when ai is present; absent ai leaves per-kind switches at default arms | `melee/pc/platform/geno_define_registry.inc:192` |

### `kirby_copy`

| Path | Accepted editor type / constraints | Meaning and units | Default on absence | Code reference |
|---|---|---|---|---|
| fighters[].kirby_copy | string (pattern="^(none\|retail:[a-z]+)$") | What Kirby gets from inhaling the define: "none" (the default) or "retail:<fighter>" (that fighter's hat and ability) (geno: 10) | none | `melee/pc/platform/geno_define_registry.inc:199` |

### `audio`

| Path | Accepted editor type / constraints | Meaning and units | Default on absence | Code reference |
|---|---|---|---|---|
| fighters[].audio | object | Own announcer and replacement voice clips (geno 9); undeclared voice ids retain the retail sound path | no own clips; announcer silent; retail voice path retained | `melee/pc/platform/geno_define_registry.inc:209`; `:709` |
| fighters[].audio.announcer | string (maxLength=63; pattern="^[A-Za-z0-9_.+@#%&=,;'!()-]+\\.[gG][nN][sS][nN][dD]$") | A .gnsnd file of the mod's files/ folder (python -m tools.geno.audio in.wav out.gnsnd); a plain file name | silent pick call | `melee/pc/platform/geno_define_registry.inc:218` |
| fighters[].audio.voice | array of object (minItems=1; maxItems=32) | Replacement clips keyed by retail voice sound id | no replacements; undeclared voice ids retain retail sound | `melee/pc/platform/geno_define_registry.inc:714` |
| fighters[].audio.voice[].sfx | integer (minimum=1; maximum=999999) | REQUIRED. The retail sound id this fighter would play | REQUIRED; no usable absence default | `melee/pc/platform/geno_define_registry.inc:230` |
| fighters[].audio.voice[].file | string (maxLength=63; pattern="^[A-Za-z0-9_.+@#%&=,;'!()-]+\\.[gG][nN][sS][nN][dD]$") | REQUIRED. A .gnsnd file of the mod's files/ folder (python -m tools.geno.audio in.wav out.gnsnd); a plain file name | REQUIRED; no usable absence default | `melee/pc/platform/geno_define_registry.inc:230` |
| fighters[].audio.voice[].volume | integer (minimum=0; maximum=127) | Volume 0..127; engine volume 0..127 | 127 | `melee/pc/platform/geno_define_registry.inc:230` |

## Attribute defaults: all 46 importer values plus every other accepted field

The engine does NOT have 46 universal defaults. The importer copies 46 authored Courier fixture values, measures walk/run reference speeds, forces model_scaling to 1, then applies fighter.json overrides (`tools/geno/artist/assemble.py:137`). A manually omitted field inherits the donor’s actual data: `GenoDefine_Load` copies `source->x0` and `ext_attr` (`melee/pc/geno/geno_define_data.inc:363`). The runtime applies overrides before modifiers at spawn/reapply (`melee/pc/geno/geno_game.c:1045`). `jumps.max` is a separate override and wins over `attributes.max_jumps` (`melee/pc/geno/geno_game.c:1068`); importer default jumps.max=3 while attributes.max_jumps=2.

| Attribute | Stored type | Units / purpose | Importer default | Runtime absence / range | Code |
|---|---|---|---|---|---|
| walk_accel_mul | float32 | Melee units/frame² (stick multiplier for *_mul) | 0.1 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:902` |
| walk_accel_base | float32 | Melee units/frame² (stick multiplier for *_mul) | 0.1 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:903` |
| walk_max_vel | float32 | Melee units/frame; walk and run scaling are reference clip speeds | 1.3 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:904` |
| slow_walk_max | float32 | Melee units/frame; walk and run scaling are reference clip speeds | 0.29; replaced by measured clip reference speed | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:905` |
| mid_walk_point | float32 | Melee units/frame; walk and run scaling are reference clip speeds | 0.5; replaced by measured clip reference speed | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:906` |
| fast_walk_min | float32 | Melee units/frame; walk and run scaling are reference clip speeds | 0.72; replaced by measured clip reference speed | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:907` |
| ground_friction | float32 | Melee units/frame² (stick multiplier for *_mul) | 0.06 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:908` |
| dash_initial_velocity | float32 | Melee units/frame; walk and run scaling are reference clip speeds | 1.5 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:909` |
| dash_accel_mul | float32 | Melee units/frame² (stick multiplier for *_mul) | 0.06 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:910` |
| dash_accel_base | float32 | Melee units/frame² (stick multiplier for *_mul) | 0.02 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:911` |
| dash_max_velocity | float32 | Melee units/frame; walk and run scaling are reference clip speeds | 1.5 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:912` |
| run_animation_scaling | float32 | Melee units/frame; walk and run scaling are reference clip speeds | 1.32; replaced by measured clip reference speed | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:913` |
| max_run_brake_frames | float32 | logic frames (float fields remain numbers, not integer-only) | 30 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:914` |
| ground_max_horizontal_velocity | float32 | Melee units/frame; walk and run scaling are reference clip speeds | 3 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:915` |
| jump_startup_time | float32 | logic frames (float fields remain numbers, not integer-only) | 4 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:916` |
| jump_h_initial_velocity | float32 | Melee units/frame; walk and run scaling are reference clip speeds | 1 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:917` |
| jump_v_initial_velocity | float32 | Melee units/frame; walk and run scaling are reference clip speeds | 2.3 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:918` |
| ground_to_air_jump_momentum_multiplier | float32 | dimensionless multiplier | 0.8 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:919` |
| jump_h_max_velocity | float32 | Melee units/frame; walk and run scaling are reference clip speeds | 1.5 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:920` |
| hop_v_initial_velocity | float32 | Melee units/frame; walk and run scaling are reference clip speeds | 1.4 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:921` |
| air_jump_v_multiplier | float32 | dimensionless multiplier | 1 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:922` |
| air_jump_h_multiplier | float32 | dimensionless multiplier | 0.9 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:923` |
| max_jumps | int32 | jump count including ground jump | 2 | donor value; runtime truncates/clamps 1..250 (editor attribute lacks range) | `melee/pc/geno/geno_game.c:924` |
| gravity | float32 | Melee units/frame² (stick multiplier for *_mul) | 0.085 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:925` |
| terminal_velocity | float32 | Melee units/frame; walk and run scaling are reference clip speeds | 1.7 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:926` |
| air_drift_stick_mul | float32 | Melee units/frame² (stick multiplier for *_mul) | 0.025 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:927` |
| aerial_drift_base | float32 | Melee units/frame² (stick multiplier for *_mul) | 0.02 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:928` |
| air_drift_max | float32 | Melee units/frame; walk and run scaling are reference clip speeds | 0.86 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:929` |
| aerial_friction | float32 | Melee units/frame² (stick multiplier for *_mul) | 0.016 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:930` |
| fast_fall_velocity | float32 | Melee units/frame; walk and run scaling are reference clip speeds | 2.3 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:931` |
| air_max_horizontal_velocity | float32 | Melee units/frame; walk and run scaling are reference clip speeds | 3 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:932` |
| jab_2_input_window | float32 | logic frames (float fields remain numbers, not integer-only) | 24 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:933` |
| jab_3_input_window | float32 | logic frames (float fields remain numbers, not integer-only) | 24 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:934` |
| standing_turn_frames | float32 | logic frames (float fields remain numbers, not integer-only) | 4 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:935` |
| weight | float32 | Melee knockback weight value (dimensionless) | 100 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:936` |
| model_scaling | float32 | dimensionless multiplier | 1.0 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:937` |
| initial_shield_size | float32 | Melee units (shield radius / nametag offset / ice size) | 10.75 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:938` |
| shield_break_initial_velocity | float32 | Melee units/frame; walk and run scaling are reference clip speeds | 2.5 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:939` |
| rapid_jab_window | int32 | logic frames (stored int32) | 0 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:940` |
| clank_animation_length | float32 | logic frames (float fields remain numbers, not integer-only) | 16 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:941` |
| hit_spark_variant | int32 | 0 normal spark; 1 no spark | not supplied by importer; donor value | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:945` |
| ledge_jump_horizontal_velocity | float32 | Melee units/frame; walk and run scaling are reference clip speeds | not supplied by importer; donor value | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:946` |
| ledge_jump_vertical_velocity | float32 | Melee units/frame; walk and run scaling are reference clip speeds | not supplied by importer; donor value | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:947` |
| item_throw_velocity_multiplier | float32 | dimensionless multiplier | not supplied by importer; donor value | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:948` |
| heavy_throw_velocity_multiplier | float32 | dimensionless multiplier | not supplied by importer; donor value | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:949` |
| specials_ground_speed_retention | float32 | dimensionless multiplier | not supplied by importer; donor value | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:950` |
| kirby_b_star_damage | float32 | damage percent | not supplied by importer; donor value | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:951` |
| normal_landing_lag | float32 | logic frames (float fields remain numbers, not integer-only) | 4 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:952` |
| landingairn_lag | float32 | logic frames (float fields remain numbers, not integer-only) | 16 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:953` |
| landingairf_lag | float32 | logic frames (float fields remain numbers, not integer-only) | 21 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:954` |
| landingairb_lag | float32 | logic frames (float fields remain numbers, not integer-only) | 15 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:955` |
| landingairhi_lag | float32 | logic frames (float fields remain numbers, not integer-only) | 15 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:956` |
| landingairlw_lag | float32 | logic frames (float fields remain numbers, not integer-only) | 23 | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:957` |
| name_tag_height | float32 | Melee units (shield radius / nametag offset / ice size) | not supplied by importer; donor value | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:958` |
| passivewall_vel_x | float32 | Melee units/frame; walk and run scaling are reference clip speeds | not supplied by importer; donor value | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:959` |
| wall_jump_horizontal_velocity | float32 | Melee units/frame; walk and run scaling are reference clip speeds | not supplied by importer; donor value | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:960` |
| wall_jump_vertical_velocity | float32 | Melee units/frame; walk and run scaling are reference clip speeds | not supplied by importer; donor value | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:961` |
| passiveceil_vel_x | float32 | Melee units/frame; walk and run scaling are reference clip speeds | not supplied by importer; donor value | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:962` |
| trophy_scale | float32 | dimensionless multiplier | not supplied by importer; donor value | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:963` |
| screw_attack_launch_velocity | float32 | Melee units/frame; walk and run scaling are reference clip speeds | not supplied by importer; donor value | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:964` |
| wall_jump_min_approach_speed | float32 | Melee units/frame; walk and run scaling are reference clip speeds | not supplied by importer; donor value | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:965` |
| damageice_ice_size | float32 | Melee units (shield radius / nametag offset / ice size) | not supplied by importer; donor value | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:966` |
| damageicejump_vel_y | float32 | Melee units/frame; walk and run scaling are reference clip speeds | not supplied by importer; donor value | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:967` |
| damageicejump_vel_x_mult | float32 | dimensionless multiplier | not supplied by importer; donor value | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:968` |
| respawn_platform_scale | float32 | dimensionless multiplier | not supplied by importer; donor value | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:969` |
| warp_star_hitbox_scale | float32 | dimensionless multiplier | not supplied by importer; donor value | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:970` |
| camera_zoom_target_bone | int32 | joint index | not supplied by importer; donor value | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:971` |
| unused_0 | int32 | not used in game code | not supplied by importer; donor value | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:973` |
| xDC | float32 | unspecified / unnamed decomp field; do not invent meaning | not supplied by importer; donor value | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:974` |
| x12C | float32 | unspecified / unnamed decomp field; do not invent meaning | not supplied by importer; donor value | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:975` |
| x13C | float32 | unspecified / unnamed decomp field; do not invent meaning | not supplied by importer; donor value | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:976` |
| x144 | float32 | unspecified / unnamed decomp field; do not invent meaning | not supplied by importer; donor value | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:977` |
| x150_damageice_unk | float32 | unspecified / unnamed decomp field; do not invent meaning | not supplied by importer; donor value | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:978` |
| x154_damageice_unk | float32 | unspecified / unnamed decomp field; do not invent meaning | not supplied by importer; donor value | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:979` |
| x168 | float32 | unspecified / unnamed decomp field; do not invent meaning | not supplied by importer; donor value | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:980` |
| x17C | float32 | unspecified / unnamed decomp field; do not invent meaning | not supplied by importer; donor value | donor value; no declared numeric min/max | `melee/pc/geno/geno_game.c:981` |

Importer defaults count: 46. Runtime accepted attribute count: 76. The comments claiming 40 or 67 in docs/header are stale. `max_jumps`, `rapid_jab_window`, `hit_spark_variant`, `camera_zoom_target_bone`, `unused_0` are the integer attributes. Every other accepted scalar is float32. No JSON access to the nested vectors, struct xBC, or weight_independent_throws_mask exists (`melee/pc/geno/geno_game.c:901`; `melee/src/melee/ft/types.h:752`).

## Runtime limits

| Constant | Current value | Code |
|---|---|---|
| GENO_VARS_PER_BANK | 64 | `melee/pc/geno/geno.h:49` |
| GENO_SPECIAL_WORDS | 265 | `melee/pc/geno/geno.h:139` |
| GENO_MAX_CHECKS | 8 | `melee/pc/geno/geno.h:182` |
| GENO_CHECK_CONDS | 3 | `melee/pc/geno/geno.h:183` |
| GENO_MAX_REHIT | 4 | `melee/pc/geno/geno.h:184` |
| GENO_EV_MAX_HOOKS | 8 | `melee/pc/geno/geno.h:249` |
| GENO_MAX_ATTRS | 128 | `melee/pc/geno/geno.h:253` |
| GENO_MAX_JUMP_VY | 16 | `melee/pc/geno/geno.h:254` |
| GENO_MAX_PROFILES | 65535 | `melee/pc/geno/geno.h:255` |
| GENO_MAX_SPECIAL | 64 | `melee/pc/geno/geno.h:256` |
| GENO_MAX_ONLAND | 16 | `melee/pc/geno/geno.h:257` |
| GENO_MAX_MOTION_ANIM | 8 | `melee/pc/geno/geno.h:258` |
| GENO_MAX_OVERLAYS | 192 | `melee/pc/geno/geno.h:259` |
| GENO_POOL_WORDS | 16384 | `melee/pc/geno/geno.h:260` |
| GENO_MAX_STATES | 48 | `melee/pc/geno/geno.h:271` |
| GENO_ART_KIND_BASE | 4096 | `melee/pc/geno/geno.h:361` |
| GENO_MAX_ARTICLES | 16 | `melee/pc/geno/geno.h:362` |
| GENO_ART_PER_RANGE | 8 | `melee/pc/geno/geno.h:363` |
| GENO_ART_EXTRA_BASE | 131072 | `melee/pc/geno/geno.h:368` |
| GENO_MAX_SOUNDS | 16 | `melee/pc/geno/geno.h:376` |
| GENO_ART_HITBOXES | 4 | `melee/pc/geno/geno.h:377` |
| GENO_ART_HIT_ENTRIES | 8 | `melee/pc/geno/geno.h:378` |
| GENO_ART_SPAWNS | 4 | `melee/pc/geno/geno.h:380` |
| GENO_ART_CHILDREN | 2 | `melee/pc/geno/geno.h:381` |
| GENO_SP_SELECT | 4 | `melee/pc/geno/geno.h:483` |
| JDOC_NODES | 4096 | `melee/pc/platform/geno_registry.c:74` |
| JDOC_ARENA | 65536 | `melee/pc/platform/geno_registry.c:75` |
| GN_MAX_VOICE | 32 | `melee/pc/platform/geno_registry.c:403` |
| GN_MAX_SLOTS | 512 | `melee/pc/platform/geno_registry.c:507` |
| JSON_DEPTH | 32 | `melee/pc/platform/geno_registry.c:194` |
| JSON_FILE_BYTES | 1048576 | `melee/pc/platform/geno_registry.c:1498` |

## Attach vocabulary, callbacks, hooks

Attach aliases: `mario` → `PlMr.dat`, `fox` → `PlFx.dat`, `captain` → `PlCa.dat`, `falcon` → `PlCa.dat`, `donkey` → `PlDk.dat`, `dk` → `PlDk.dat`, `kirby` → `PlKb.dat`, `koopa` → `PlKp.dat`, `bowser` → `PlKp.dat`, `link` → `PlLk.dat`, `seak` → `PlSk.dat`, `sheik` → `PlSk.dat`, `ness` → `PlNs.dat`, `peach` → `PlPe.dat`, `popo` → `PlPp.dat`, `nana` → `PlNn.dat`, `pikachu` → `PlPk.dat`, `samus` → `PlSs.dat`, `yoshi` → `PlYs.dat`, `purin` → `PlPr.dat`, `jigglypuff` → `PlPr.dat`, `mewtwo` → `PlMt.dat`, `luigi` → `PlLg.dat`, `mars` → `PlMs.dat`, `marth` → `PlMs.dat`, `zelda` → `PlZd.dat`, `clink` → `PlCl.dat`, `younglink` → `PlCl.dat`, `drmario` → `PlDr.dat`, `falco` → `PlFc.dat`, `pichu` → `PlPc.dat`, `gamewatch` → `PlGw.dat`, `gnw` → `PlGw.dat`, `ganon` → `PlGn.dat`, `ganondorf` → `PlGn.dat`, `emblem` → `PlFe.dat`, `roy` → `PlFe.dat`. Unknown `.dat` names are accepted as existing-fighter references by tools; runtime resolves mounted fighter tables. Attach supports Nana, AI and Kirby-copy intentionally exclude her (`melee/pc/platform/geno_define_registry.inc:165`).

Behaviors: `geno.air`, `geno.ground`, `geno.anim_motion`, `geno.glide.start`, `geno.glide`, `geno.glide.attack`, `geno.glide.landing`, `geno.glide.end`, `geno.tornado`, `geno.drill`, `geno.drill.end`, `geno.cape`, `geno.cape.attack`, `geno.cape.end`, `geno.drill.start`. Definitions and default callback rows: `melee/pc/geno/geno_game_v2.inc` table geno_bhvs.
- anim: `like`, `next`, `loop`, `lua`, `hold`, `glide.start`, `glide`, `tornado`, `drill`, `drill.end`, `glide.after`, `cape`
- iasa: `like`, `interrupt`, `none`, `glide`
- phys: `like`, `cape`, `none`, `air`, `air_nodrift`, `air_drift`, `brake`, `ground`, `auto`, `anim_motion`, `glide.start`, `glide`, `glide.attack`, `glide.end`, `tornado`, `drill`, `drill.end`, `drill.start`
- coll: `like`, `cape`, `cape.after`, `none`, `air`, `air_noledge`, `ground`, `ground_stop`, `both`, `anim_motion`, `glide`, `drill`, `drill.start`

Hook strings accept optional `:signed-int32` argument; omitted argument is 0 (`tools/geno/check.py:514`; runtime uses atoi at `melee/pc/platform/geno_registry.c:564`). Hook names: `geno.log` (id 1), `geno.jumps.refill` (id 2), `geno.jumps.to_var` (id 3), `geno.count_frames` (id 4), `geno.article.spawn` (id 5), `geno.lockon` (id 6), `geno.aim_stick` (id 7), `geno.dash.search` (id 8), `geno.dash.aim` (id 9), `geno.brake` (id 10).

Targets: integer 0..65535 = native motion; `motion:N`, `special:N`, `geno:N`, `geno:StateName`, `auto`, `helpless`, `stay`. Runtime string comparisons are case-insensitive; named state matching is case-insensitive. Numeric tokens use C base 0: hexadecimal works and leading 0 is octal. Do not use octal-style strings in author files (`melee/pc/platform/geno_registry.c:578`). Geno state motion id is 1024 + its zero-based index. `like` has no profile for named-state lookup. State subaction borrowed-target schema accepts only decimal motion/special syntax; runtime target helper is broader.


## Behavior parameters: units, live word aliases and absence defaults

Every parameter accepts number/boolean, stored float32; no numeric range is imposed by parser/schema. Prefer explicit numeric values. Named and wNN aliases identify the same storage slot; later occurrence in object order wins (`melee/pc/platform/geno_registry.c:959`). The wNN columns are compatibility forms, not deprecated.

| Family | Named key | Word alias | Units / meaning | Absence default | Code |
|---|---|---|---|---|---|
| glide | angle_max | w00 | degrees | 80.0 | `melee/pc/geno/geno_game_v2.inc:55` |
| glide | angle_min | w01 | degrees | -70.0 | `melee/pc/geno/geno_game_v2.inc:56` |
| glide | start_vy | w02 | Melee units / logic frame | 0.75 | `melee/pc/geno/geno_game_v2.inc:57` |
| glide | start_gravity | w03 | multiplier of common gravity | 1.0 | `melee/pc/geno/geno_game_v2.inc:58` |
| glide | start_vx | w04 | multiplier of incoming horizontal speed | 1.0 | `melee/pc/geno/geno_game_v2.inc:59` |
| glide | speed | w05 | Melee units / logic frame | 1.7 | `melee/pc/geno/geno_game_v2.inc:60` |
| glide | speed_accel | w06 | Melee units / logic-frame² | 0.04 | `melee/pc/geno/geno_game_v2.inc:61` |
| glide | max_speed | w07 | Melee units / logic frame | 2.2 | `melee/pc/geno/geno_game_v2.inc:62` |
| glide | stall_speed | w08 | Melee units / logic frame | 0.7 | `melee/pc/geno/geno_game_v2.inc:63` |
| glide | sink_accel | w09 | Melee units / logic-frame² | 0.03 | `melee/pc/geno/geno_game_v2.inc:64` |
| glide | max_sink | w10 | Melee units / logic frame | 0.6 | `melee/pc/geno/geno_game_v2.inc:65` |
| glide | recover_angle | w11 | degrees | 15.0 | `melee/pc/geno/geno_game_v2.inc:66` |
| glide | dive_angle | w12 | degrees | -25.0 | `melee/pc/geno/geno_game_v2.inc:67` |
| glide | dive_bonus | w13 | Melee units / logic-frame² | 0.03 | `melee/pc/geno/geno_game_v2.inc:68` |
| glide | w14 | w14 | glide unused source word | 0.15 | `melee/pc/geno/geno_game_v2.inc:69` |
| glide | deadzone | w15 | dimensionless / flag | 0.25 | `melee/pc/geno/geno_game_v2.inc:70` |
| glide | pitch_up | w16 | degrees / logic-frame² | 0.55 | `melee/pc/geno/geno_game_v2.inc:71` |
| glide | pitch_down | w17 | degrees / logic-frame² | 0.75 | `melee/pc/geno/geno_game_v2.inc:72` |
| glide | max_pitch_rate | w18 | degrees / logic frame | 7.0 | `melee/pc/geno/geno_game_v2.inc:73` |
| glide | stall_pitch | w19 | degrees/frame (automatic nose-up adjustment at stall) | 1.0 | `melee/pc/geno/geno_game_v2.inc:74` |
| glide | wing_node | w20 | unused Brawl wing partial animation joint | 44.0 | `melee/pc/geno/geno_game_v2.inc:75` |
| glide | w21 | w21 | glide unused source word | 0.0 | `melee/pc/geno/geno_game_v2.inc:76` |
| glide | hold_frames | — | logic frames | 16.0 | `melee/pc/geno/geno_game_v2.inc:77` |
| glide | from_ground_jump | — | nonzero permits glide entry from ground jump | 0.0 | `melee/pc/geno/geno_game_v2.inc:78` |
| glide | end_helpless | — | nonzero ends airborne as FallSpecial | 0.0 | `melee/pc/geno/geno_game_v2.inc:79` |
| glide | landing_lag | — | logic frames; currently unused by default behaviors | 0.0 | `melee/pc/geno/geno_game_v2.inc:80` |
| glide | entry | — | nonzero allows automatic held-jump glide entry | 1.0 | `melee/pc/geno/geno_game_v2.inc:81` |
| glide | max_frames | — | logic frames | 0.0 | `melee/pc/geno/geno_game_v2.inc:82` |
| glide | pose_center | — | clip frame at neutral angle; samples frame=pose_center-angle; 0 disabled | 0.0 | `melee/pc/geno/geno_game_v2.inc:83` |
| glide | end_buttons | — | GENO_BTN bitmask (default14=shield8+special2+jump4) | 14 | `melee/pc/geno/geno_game_v2.inc:84` |
| glide | script_entry_helpless | — | nonzero allows script glide entry while helpless | 1.0 | `melee/pc/geno/geno_game_v2.inc:127` |
| tornado | entry_vy | w00 | Melee units / logic frame | 1.0 | `melee/pc/geno/geno_game_v2.inc:88` |
| tornado | entry_vx_mul | w01 | dimensionless / flag | 0.7 | `melee/pc/geno/geno_game_v2.inc:89` |
| tornado | start_rate | w02 | spin rate (degrees/frame in source model); animation rate uses spin_anim | 80.0 | `melee/pc/geno/geno_game_v2.inc:90` |
| tornado | ground_accel | w03 | Melee units / logic-frame² | 0.12 | `melee/pc/geno/geno_game_v2.inc:91` |
| tornado | ground_speed | w04 | Melee units / logic frame | 2.0 | `melee/pc/geno/geno_game_v2.inc:92` |
| tornado | air_accel | w05 | Melee units / logic-frame² | 0.1 | `melee/pc/geno/geno_game_v2.inc:93` |
| tornado | air_speed | w06 | Melee units / logic frame | 1.7 | `melee/pc/geno/geno_game_v2.inc:94` |
| tornado | brake | w07 | Melee units / logic-frame² | 0.008 | `melee/pc/geno/geno_game_v2.inc:95` |
| tornado | gravity | w08 | Melee units / logic-frame² | -0.08 | `melee/pc/geno/geno_game_v2.inc:96` |
| tornado | max_fall | w09 | Melee units / logic frame | 0.5 | `melee/pc/geno/geno_game_v2.inc:97` |
| tornado | tap_vy | w10 | Melee units / logic frame | 1.0 | `melee/pc/geno/geno_game_v2.inc:98` |
| tornado | tap_cooldown | w11 | logic frames | 10.0 | `melee/pc/geno/geno_game_v2.inc:99` |
| tornado | max_rise | w12 | Melee units / logic frame | 1.4 | `melee/pc/geno/geno_game_v2.inc:100` |
| tornado | tap_rate | w13 | spin-rate increase per tap | 16.0 | `melee/pc/geno/geno_game_v2.inc:101` |
| tornado | max_rate | w14 | maximum spin rate | 80.0 | `melee/pc/geno/geno_game_v2.inc:102` |
| tornado | rate_decay | w15 | spin-rate decrease/frame | 1.5 | `melee/pc/geno/geno_game_v2.inc:103` |
| tornado | spin_frames | w16 | logic frames | 70.0 | `melee/pc/geno/geno_game_v2.inc:104` |
| tornado | late_decay | w17 | spin-rate decrease/frame after spin_frames | 2.0 | `melee/pc/geno/geno_game_v2.inc:105` |
| tornado | end_rate | w18 | spin rate below which Tornado ends | 10.0 | `melee/pc/geno/geno_game_v2.inc:106` |
| tornado | w19 | w19 | tornado reserved/unused word | 0.0 | `melee/pc/geno/geno_game_v2.inc:107` |
| tornado | max_speed | — | Melee units / logic frame | 2.5 | `melee/pc/geno/geno_game_v2.inc:108` |
| tornado | end_helpless | — | nonzero ends airborne as FallSpecial | 1.0 | `melee/pc/geno/geno_game_v2.inc:109` |
| tornado | spin_anim | — | clip-frame playback rate per spin-rate unit (0 disables separate looping spin animation) | 0.0 | `melee/pc/geno/geno_game_v2.inc:110` |
| tornado | spin_period | — | animation clip frames before wrap (0 disables separate wrap) | 0.0 | `melee/pc/geno/geno_game_v2.inc:111` |
| drill | start_vx_mul | w00 | dimensionless / flag | 0.5 | `melee/pc/geno/geno_game_v2.inc:114` |
| drill | start_vy | w01 | Melee units / logic frame | 1.0 | `melee/pc/geno/geno_game_v2.inc:115` |
| drill | start_gravity | w02 | signed Melee units/frame² | -0.08 | `melee/pc/geno/geno_game_v2.inc:116` |
| drill | steer | w03 | degrees / logic frame | 3.0 | `melee/pc/geno/geno_game_v2.inc:117` |
| drill | end_frames | w04 | logic frames | 10.0 | `melee/pc/geno/geno_game_v2.inc:118` |
| drill | w05 | w05 | drill reserved/unused word | 0.0 | `melee/pc/geno/geno_game_v2.inc:119` |
| drill | speed | — | Melee units / logic frame | 2.0 | `melee/pc/geno/geno_game_v2.inc:120` |
| drill | angle_max | — | degrees | 0.0 | `melee/pc/geno/geno_game_v2.inc:121` |
| drill | bounce | — | bitmask1 wall/2 hit/4 shield; default0 (Brawl does not early-bounce) | 0.0 | `melee/pc/geno/geno_game_v2.inc:122` |
| drill | pop_vx | — | Melee units / logic frame | 1.0 | `melee/pc/geno/geno_game_v2.inc:123` |
| drill | pop_vy | — | Melee units / logic frame | 2.1 | `melee/pc/geno/geno_game_v2.inc:124` |
| drill | end_helpless | — | nonzero ends airborne as FallSpecial | 1.0 | `melee/pc/geno/geno_game_v2.inc:125` |
| drill | pitch_model | — | nonzero pitches fighter model along travel (default1) | 1.0 | `melee/pc/geno/geno_game_v2.inc:126` |
| cape | keep_vx | w00 | dimensionless / flag | 0.5 | `melee/pc/geno/geno_game_v2.inc:130` |
| cape | keep_vy | w01 | dimensionless / flag | 0.4 | `melee/pc/geno/geno_game_v2.inc:131` |
| cape | steer_accel_x | w02 | Melee units/frame² at full stick | 0.5 | `melee/pc/geno/geno_game_v2.inc:132` |
| cape | steer_max_x | w03 | Melee units / logic frame | 2.5 | `melee/pc/geno/geno_game_v2.inc:133` |
| cape | steer_accel_y | w04 | Melee units/frame² at full stick | 0.5 | `melee/pc/geno/geno_game_v2.inc:134` |
| cape | steer_max_y | w05 | Melee units / logic frame | 2.5 | `melee/pc/geno/geno_game_v2.inc:135` |
| cape | steer_frame | — | logic frames | 12.0 | `melee/pc/geno/geno_game_v2.inc:136` |
| cape | decide_frame | — | logic frames | 26.0 | `melee/pc/geno/geno_game_v2.inc:137` |
| cape | neutral_x | — | normalized horizontal stick magnitude cutoff | 0.3 | `melee/pc/geno/geno_game_v2.inc:138` |
| cape | attack_buttons | — | GENO_BTN bitmask (default3=attack1+special2) | 3 | `melee/pc/geno/geno_game_v2.inc:139` |
## Requirements across fields and runtime behavior

- A definition needs all five `define` strings. `key`: lowercase letter/digit first, then lowercase letters/digits/`_`/`.`/`-`, 1..39 bytes, no `..`; `name`: printable ASCII 1..47 bytes; `common` exactly `melee.common.v1`; resources exactly `retail:mario` for base mario, `mod:files` for base none. Definitions accept formats 6..10, not arbitrary future formats (`melee/pc/platform/geno_define_registry.inc:257`). A duplicate definition identity refuses catalogue admission (`:379`).
- `fighter` is consumed only for a base none definition. `plan` and `animation` are required, plain file names in the mounted files/ namespace, 1..63 bytes; costume file names 1..63, joint/matanim symbols 1..47; no slash, colon or `..` (`melee/pc/platform/geno_define_registry.inc:5`). The schema does not encode those lengths/path rules. File lookup is the mounted virtual filesystem by basename, not a private namespaced directory: prefix files for each fighter.
- The runtime accepts 1..255 costumes and 1..255 portrait/stock entries; the schema has maxItems=16 and does not require at least one costume. The checker forbids duplicate teams and excess per-costume art; the runtime picks the first declared team and falls back to entry 0 for a costume beyond the art list (`melee/pc/platform/geno_define_registry.inc:24`, `:138`, `:526`, `:530`; `tools/geno/define.py:50`). `fighter.rows`: up to 128 names; their subactions are 303..430, so even base none subactions do have a finite range. Unlisted own bank clips are not magically available as action rows (`melee/pc/platform/geno_define_registry.inc:71`, `:314`, `:354`).
- `states[].subaction`: numeric 0..1023 for attachments; for definitions it must be below 303 + number of declared own rows. Omitted uses the like row’s animation. A borrowed string target (`motion:N`/`special:N`) asks for that motion’s subaction. Parser resolves names before other state fields. Do not duplicate state names or article names: the checker rejects case-insensitive duplicates (`tools/geno/check.py:489`).
- `common_states` is definition-only. Required motion 0..350; all optional numeric fields must be exact integers with the listed bounds. Duplicate motion override refuses the definition. `like` selects a native motion to inherit. Overrides affect animation, motion flags, stale move id and the four callbacks; omitted fields inherit the selected row. Callback `like` keeps the copied callback (`melee/pc/platform/geno_define_registry.inc:318`; `melee/pc/geno/geno_define_rows.inc:22`).
- `states[].lua.frame` automatically selects anim callback `lua` only while the existing callback id remains negative; an explicit `anim` wins. The callback executes the function then obeys next if the animation ended and Lua issued no action change (`melee/pc/platform/geno_lua_registry.inc:141`; `melee/pc/geno/geno_game_lua.inc`). Module must return its exported functions; exactly one source/script; 1..65536 encoded bytes. Slot names `[A-Za-z_][A-Za-z0-9_]{0,22}`; values int/float/bool; up to 16. Function names 1..31 bytes, maximum 24 exported functions; the domain has further sandbox/closure/instruction/allocation checks. The schema alone does not enforce script/source exclusivity or module content (`melee/pc/platform/geno_lua_registry.inc:64`, `:85`, `:90`; `melee/pc/platform/geno_lua_core.h:43`, `:44`, `:542`; `tools/geno/check.py:390`).
- Special selector `select`: `la_i:0..63` or `ra_i:0..63`; targets list 1..4. At action entry it reads that integer slot; out of range falls back to donor special. Missing air direction inherits ground direction, including the selector. Read/write integer bank variables with ftcmd script words; fighter Lua ctx does not expose those banks; a selector is not a stateful cycle by itself (`melee/pc/platform/geno_registry.c:830`, `:981`).
- `subactions` is script overlay data, never an animation asset. Require index and exactly one words/file. Integers in [-2^31,2^32-1] preserve word bits; decimal or hex strings encode an unsigned word. Word file: whitespace/comma separators and `#` comments; runtime parses C base 0. Pool includes one appended End word per overlay; global 16384 words, 512 slots; 192 overlays/profile (`melee/pc/platform/geno_registry.c:636`, `:654`, `:808`; `melee/pc/geno/geno.h:259`). Invalid definition overlay refuses that definition; attachments may ignore invalid overlays (`melee/pc/platform/geno_registry.c:1415`). Absolute script calls/gotos are not portable and checker refuses them (`tools/geno/check.py:168`).
- `special_attributes`: index 0..264 OR 4-aligned byte offset 0..1056 (0x420), plus float OR signed int32. These are numeric fields of the donor special block; values are stored as float bits or integer bits. If both index/offset exist runtime uses index; if both float/int exist runtime uses float. The schema uses anyOf rather than exclusive oneOf; checker still validates supplied offset even when index wins (`melee/pc/platform/geno_registry.c:709`; `tools/geno/check.py:524`). No first-class descriptions of unnamed special words exist; use the donor’s decomp struct when deliberately customizing them.
- `jumps.max` and attributes.max_jumps: runtime truncates/clamps 1..250. `jumps.air_vy` up to 16 numbers; last repeats, but only multi-jump fighters use the table interception. Setting this on a normal Mario-based two-jump fighter does not manufacture Kirby-style multijump states (`melee/pc/platform/geno_registry.c:1289`; `melee/pc/geno/geno_game.c:1070`). Importer default jumps.max=3 is independent of attribute default max_jumps=2; document this explicitly.
- Hook argument syntax is one signed 32-bit value; bit-packed hook arguments also travel through that value. Every event list max 8. Runtime unknown hooks are ignored; checker rejects. `on_init`, `on_frame`, `on_action`, `on_land`, `on_hit` are the five events (`melee/pc/platform/geno_registry.c:1326`, `:1391`). All current hook names are listed above.
- `moves` is author-tool sugar only. `check.validate` expands it before schema validation; export expands it into subactions/common_states. Motion required; optional subaction uses the donor’s motion->subaction table. `words` string means file; array means words. `tag` becomes move_tag on both generated entries. No engine reads moves, so shipping unexpanded sugar will leave the donor move. Naming restriction in nominal schema is lowercase letters/digits/hyphens, starting a lowercase letter, but expansion discards the move names before schema validation, so the restriction is not actually applied by check.validate (`tools/geno/check.py:438`; `tools/geno/define.py:123`).
- `move_tag`: jab, dash_attack, tilt, smash, aerial, grab, throw, special, projectile. Omitted/unknown runtime tag=0; checker rejects unknown tag. Available on states, subactions, common_states. This declaration provides hit-rule vocabulary, not animation routing (`melee/pc/platform/geno_registry.c:622`).
- Article lifecycle: lifetime <=0 resets to 60, scale <=0 resets to 1, max_live <1 resets to 4. Missing gravity/max_fall/accel/max_speed/min_speed/angle/spin/homing=0. `max_fall=0` and `max_speed=0` remove those caps; homing.range=0 means unlimited search, turn=0 disables turning. Initial velocity is forward/up in owner’s facing, then angle rotates it. Spawn offset likewise forward/up; bone >=0 anchors to the fighter part; -1 uses fighter position (`melee/pc/platform/geno_registry.c:1128`; `melee/pc/geno/geno_game_articles.inc:575`, `:983`).
- Articles: max 16 types/profile; max 8 hitbox entries/article mapped onto 4 live slots. End=0 extends to lifetime. Life windows are 1-based, so start default1. Entries on one slot preserve victim lists when replacing an active entry; a closed/reopened window clears the list. Default ground/air/reflect/absorb/counter all enabled, as are despawn hit/shield/stage/clank; absorber always takes an article (`melee/pc/geno/geno.h:437`, `:466`; `melee/pc/geno/geno_game_articles.inc:549`; `melee/docs/geno.md:2153`).
- Article hitbox fields use native Melee integer semantics: damage is float but the item hitbox rounds to whole percent; angle 361 is the engine angle sentinel, not degrees 361 in geometry. kbg/bkb/wkb are native knockback inputs; element native id (0 normal,1 fire,2 electric,3 slash,5 ice); severity/kind native sound selectors. Shield damage native signed input. Stun clamps 0..255; slot is bitmasked &3 (`melee/pc/platform/geno_registry.c:1232`; `melee/pc/geno/geno_game_articles.inc:497`; `melee/docs/geno.md:2265`).
- Article `effects[]`: up to 8 native ids or objects. Object id default0; frame default0, stored 16 bits; joint default0, stored 8 bits; count default1, stored (count-1)&255 then interpreted as count, so schema range1..256. Frame is article life tick, 0 spawns immediately. `effect` is one native id at spawn. `fx` selects the package effect name; show_model default0 hides model alongside that effect, nonzero retains it. No authored package fallback is guaranteed without the package (`melee/pc/platform/geno_registry.c:1177`, `:1184`; `melee/pc/geno/geno_game_articles.inc:866`).
- `spawns` max4 vectors are absolute spawn offsets, selected through the packed spawn argument; index0 uses first variant when available, otherwise base spawn. `children` max2 schedules/article, articles may be forward referenced by name; frame1, every0=once, count1, spawn0. Own fighter remains child owner. `spins` max4 per-joint angular speeds in radians/frame; model root spin uses degrees/frame (`melee/pc/platform/geno_registry.c:1152`, `:1198`, `:1259`; `melee/pc/geno/geno_game_articles.inc:734`, `:810`).
- `sounds`: up to16 names mapping native retail_sfx id1..999999 and volume0..127 (127 default). This is a resolver for article spawn_sound/end_sound, separate from audio.voice replacement. A definition refuses duplicate names, unresolved article references, empty/malformed entries (`melee/pc/platform/geno_registry.c:1031`). Audio voice at most32 mappings; each sfx once; announcer and voice source are plain .gnsnd names from files/. Missing/malformed named clip stays silent with one log; missing presentation draws fallback with one log (`melee/pc/platform/geno_define_registry.inc:209`, `:675`).
- `presentation.stock` and emblem forbid palette formats but do not require only RGB5A3/RGBA8. Checker accepts all nonpaletted supported formats (I4,I8,IA4,IA8,RGB565,RGB5A3,RGBA8), matching the runtime no-palette path; the earlier docs saying “rgb5a3 or rgba8 only” overstate the limit (`tools/geno/check.py:250`, `:287`). Icon/portrait nominal retail sizes are64x56/136x188; supported dimensions1..1024 are fitted. Code does not require those exact retail sizes. Results portrait and stock are separate images: stale schema stock description saying stock is the card picture is wrong (`melee/src/melee/gm/gmresultplayer.c:804`, `:1535`; `melee/docs/geno.md:2801`).
- ai.like retail aliases accepted case-insensitively, excludes Nana; omitted does not automatically set Mario AI. Kirby defaults none; retail:<name> excludes Kirby and Nana. Palette and .gnsnd file payload checks happen only when read; existence checker warning is not proof of successful render/audio (`melee/pc/platform/geno_define_registry.inc:162`, `:178`; `tools/geno/check.py:253`, `:295`).

## External plan.json: actual consumed fields (not inline geno.json)

The `fighter.plan` file is a converter output. It has many authoring/report metadata fields the runtime does not consume. Only the following affect its flat GenoPlan read; retain the converter’s full output rather than hand-maintaining this table. `melee/pc/platform/geno_define_registry.inc:740` and `melee/pc/geno/geno_plan.h` are the contract.

| Field | Runtime type / range / default | Meaning / code |
|---|---|---|
| joint_count | required integer1..256 | total depth-first joints, TopN0; :744 |
| parts | required object | parts table container; :745 |
| parts.joint_to_part | required array exactly joint_count | byte values,255 means no Melee part; cast unchecked; :749 |
| parts.part_to_joint | required array1..56 | byte joint for each common part,255 none; cast unchecked; :752 |
| bank | required object | bank container; :756 |
| bank.clips | required object max256 properties | clip name keys <=31 bytes, each clip metadata object; :757 |
| bank.clips.<clip>.symbol | required string <=71 bytes | figatree archive symbol; :759 |
| bank.clips.<clip>.offset | required int0..2^31-1 | byte offset in animation bank; :759 |
| bank.clips.<clip>.bytes | required int1..2^31-1 | encoded clip bytes; :759 (converter checks128KiB separately) |
| bank.clips.<clip>.frames | int1..100000; invalid returns-1 | frames metadata; parser does not reject returned-1 at this call; :764 |
| motion_rows | required array max351 entries | no minimum, each describes a native motion; :767 |
| motion_rows[].motion | required int0..350 | maps native motion to a clip; :783 |
| motion_rows[].clip | optional string or non-string/no animation | named clip must exist or plan refuses; :785 |
| row_clips | optional array, first512 entries used | per-animation-row clip names, unknown/missing remains-1; :771 |
| row_blend | optional array, first512 entries used | each row optional2-item array of bytes; unchecked cast; :792 |
| row_flags | optional array, first512 entries used | number0..2^32-1, low6 bits stripped; null retains donor; :801 |
| ftdata | required object indirectly through children | all six lists must resolve; :810 |
| ftdata.x8_part_bytes | required array5 resolved joints | nested arrays flattened; each leaf object{joint:int0..255}; :811 |
| ftdata.x34_centre | required array1 resolved joint | centre; :811 |
| ftdata.x38_coin | required array2 resolved joints | coin anchors; :811 |
| ftdata.x44_ecb | required array6 resolved joints | ECB joints only, donor offsets retained; :811 |
| ftdata.x54_gfx | required array5 resolved joints | effect attachments; :811 |
| ftdata.x58_ik | required array10 resolved joints | IK joints only, donor lengths retained; :811 |
| hurtboxes | required array1..15 | capsule definitions; :825 |
| hurtboxes[].joint | required integer0..255 | actual joint index; :829 |
| hurtboxes[].height | string high=>2, mid=>1, otherwise0/low | code reads string, not schema $defs integer; :830 |
| hurtboxes[].grabbable | bool; absent/non-bool=>true | integer0 does not mean false here; :831 |
| hurtboxes[].a / b | required3-item arrays | joint-local offset xyz in Melee units, numeric values loosely checked/cast; :832 |
| hurtboxes[].radius | required value cast float | capsule radius in Melee units, no positivity check; :835 |
| ecb, roles, role_joint, joints, hierarchy, metadata, costumes, ftdata.x30_hurtbox_bones | not parsed | retained/report metadata; does not create runtime ECB offsets or independent shield joint |

**Potential source defect, unresolved in this read-only task:** GPL_MAX_JOINTS grew to256 (`melee/pc/geno/geno_plan.h:6`), yet game-side `GenoDefine_PartsJ2P` is still128 bytes per fighter and memcpy uses the plan’s njoints (`melee/pc/geno/geno_define_data.inc:24`, `:48`). The documented252 exported bones plus3 synthesized joints therefore pass parser/importer but appear capable of overwriting game-side static storage above128. This audit cannot certify large rigs. The part-to-joint storage56 matches the current header limit56; the artist spec’s “part limit255” refers to the game’s joint/part array capacity, not number of canonical common part slots. Raise this to the coordinator; no fix or game proof was attempted here.

### Reference limits

The attribute table names/types and importer defaults are exhaustive. Unit labels for unnamed decomp x* fields deliberately remain unspecified. All callback enums/parameter names above are extracted from current tables, including currently unused fields; accepted does not imply behavior uses them. The schema generator’s `x-source` for most fields points generically to geno_registry.c, so use the actual definition/Lua/attribute references above. Some generated runtime-limit references to included-file macros count the concatenated source as though it were registry lines: cite exact header/parser references for those limits instead of treating those generator line numbers as literal.

Standalone native items are **not** a geno.json root `items` block. They have separate `items/<name>/item.json` files, independently parsed by `gw_Geno_ItemDefineText` (`melee/pc/platform/geno_items_registry.inc:105`; `melee/docs/geno.md:2371`). The geno.json parser reads root geno/fighters only (`melee/pc/platform/geno_registry.c:1453`). This recursive field map covers fighter-owned articles, separate from standalone items.

## Contradictions and source caveats

The following resolutions supersede the referenced historical prose. Source-level concerns without a reproduction are identified as such; this task did not change the game engine.

### Superseded guidance versus supported compatibility forms

| Historical form or advice | Current authoring rule |
|---|---|
| Formats 1–5 / old attach examples as the complete feature set | New authored Lua fighters use format 10. Older formats remain readable for their supported features; definitions need at least 6, owned art at least 9, Lua at least 10. A version number is not a migration that supplies missing fields (`melee/pc/platform/geno_registry.c:1453`, `melee/pc/platform/geno_define_registry.inc:264`, `melee/pc/platform/geno_lua_registry.inc:60`) |
| Attach plus a generated m-ex clone as the original-fighter workflow | Prefer native `define` / `base: "none"` for new original art. `attach` remains supported for extending existing fighters; it has not been removed and cannot carry fighter Lua (`melee/pc/platform/geno_registry.c:1335`, `melee/pc/platform/geno_define_registry.inc:260`, `melee/pc/platform/geno_lua_registry.inc:56`) |
| Opaque behavior `w00`, `w01`, … parameter names | Prefer the documented named parameter for readability. These aliases still address the same native words and are **not deprecated**; later JSON occurrence wins (`melee/pc/geno/geno_game_v2.inc:152`, `melee/pc/platform/geno_registry.c:959`) |
| `special_attributes` byte offsets instead of indices | Both remain accepted. Prefer an index and exactly one typed value; index wins over offset and float wins over int when both are supplied (`melee/pc/platform/geno_registry.c:709`) |
| Shipping author-tool `moves` sugar directly | Export/expand it to `subactions` / `common_states`. It is tool input, not a deprecated runtime block; the runtime never consumes it (`tools/geno/define.py:123`, `tools/geno/check.py:438`) |

### Field/parser and artist-contract differences


| Topic | Schema/checker | Runtime / source resolution |
|---|---|---|
| Format beyond10 | max10 | attach entries log and read understood fields; definitions refuse >10. Do not claim all new versions load. `geno_registry.c:1458`, `geno_define_registry.inc:264` |
| Unknown keys | schema additionalProperties false | most historical blocks ignore and hash them; definition identity/common_states/presentation/AI/audio explicitly strict. The Lua parser does not loop/reject unknown module/state-phase keys, despite broad prose describing it as strict. `geno_lua_registry.inc:64`, `:127` |
| Cos/portrait/stock count | max16 | current parser1..255; generated schema is stale. `schema.py:183`, `:187`; `geno_define_registry.inc:24`, `:138` |
| Costume count0 | schema permits0 | base none refuses. `schema.py:183`; `geno_define_registry.inc:24` |
| Definition name/key lengths | schema character count | runtime byte buffers and ASCII; checker additionally checks encoded bytes; 1..39 key,1..47 name. `define.py:17`; `geno_define_registry.inc:282` |
| Model file/symbol lengths | fighter strings unrestricted in schema | runtime file63, symbol47, plain nonempty names; plan bank symbol71. `geno_define_registry.inc:5`, `:35`, `:760` |
| State missing behavior | schema default string blank | behavior none is air-like (next/none/air/air, like Fall). `geno_game_v2.inc:968` |
| State target defaults | helper advertises0 | next/land/like resolve by behavior; counter target none. `geno_game_v2.inc:967`; `geno_registry.c:1086` |
| State flags | word allows uint32 bits | common_states.flags only nonnegative <=2^31-1; plan row_flags allows full uint32 and strips low6. Different fields, different limits. `geno_define_registry.inc:332`, `:805` |
| Numeric attribute maxima | integer attributes unbounded in schema | max_jumps clamp/truncate1..250; other values accepted as numbers then cast. Avoid inventing “safe ranges”. `geno_registry.c:1289`, `:1367` |
| gn_num coercions | number/boolean declared inconsistently | article numbers, hitbox ints, counter negate, sounds can accept bool through gn_num; vectors only JN_NUM. Prefer the checker’s narrower encodings. `geno_registry.c:993`, `:1001` |
| Article lifecycle invalid sign | schema mostly unconstrained | lifetime/scale<=0 replaced with defaults; max_live<1 defaults4. `geno_registry.c:1128`, `:1139` |
| Array dimensions | schema maxItems only | vectors may be short/empty; runtime leaves missing components zero. No minItems2/3. For clarity always author complete vectors. `schema.py:63`, `geno_registry.c:1000` |
| Special attrs choose forms | schema anyOf | both index/offset or float/int accepted; index/float take priority. This is compatibility, not deprecated. `geno_registry.c:713` |
| Binary words decimal0 prefix | schema decimal digit strings | runtime C base0 parses leading0 as octal or refuses8/9; author plain decimal or0x. `geno_registry.c:646` |
| Duplicate attach/overlay/names | checker refuses | later profiles win target; duplicate overlays can shadow; named targets have ambiguous first/last behavior. Follow checker. `check.py:485`, `:495`, `:536`; `geno_registry.c:1483` |
| `moves` names and constraints | nominal schema | check expands before schema, discarding move names and unused keys; runtime ignores moves entirely. Export first. `check.py:438`; `define.py:123` |
| Plan $defs | schema.py contains descriptive $defs | no $ref binds it to fighter.plan (which is a filename), and $defs shape is stale/wrong: parts described integer, bank.clips array, height int, grabbable int. Runtime actual plan contract below. Never cite this as validated plan schema. `schema.py:206`; `geno_define_registry.inc:740` |
| Attribute count | docs40, header67 | actual table76 entries, importer defaults46. `geno_game.c:901`; `geno.h:253`; `default_attributes.json` |
| Base none donor independence | old prose implied no donor numeric data | load copies all common/special attrs then overrides; joint-specific values replaced, callback/scripts and unnamed numeric data still donor-derived. `geno_define_data.inc:374` |
| Offline-only prose | export manifest offline_only=true and sections22 claim offline | current slice7 is built in code; defines can online with content intersection; fighter Lua modules hashed. Do not perpetuate offline restriction. `geno_define_data.inc:370`; `geno_define_online.inc`; geno.md24 |

There is no explicit deprecation-removal mechanism in the current registry. Earlier formats1..9 remain accepted in their scopes, parameter wNN aliases remain live, integer versus named state targets are both live, and special-attribute offset versus index are both live. Old instruction that row overlays require a disc-derived fighter slot is superseded by native definitions. “Deprecated” should mean historical workflow/prose unless a cited parser actually rejects the form.

### Move and testing documentation corrections


- **Hot reload:** native define package changes require a **process restart**, confirmed by `geno_registry.c:2007`; the generic attach hot-reload prose in geno.md 14.10 is insufficient for this guide.
- **Frame clocks:** `gd.timeline` is `wait-total+1`; Python report starts at 0; sampled diagnostic readout is approximately `report-start/rate−2`. The prose at geno.md 22's frame-count convention implies subtract-two directly from timeline; code resolves the distinction above.
- **Opening status:** geno.md says format 6 and offline-only in older sections; `melee/pc/geno/geno.h:16` is format 10 and section 24 describes current define online identities. Treat older fixture history as dated, not current feature ceilings.
- **State and article limits:** Geno states 48, articles 16, overlays 192 in `melee/pc/geno/geno.h:259`, `:271`, `:362`; do not copy the old 64-overlay/16-state figures from historical text. See the runtime/plan tables and the joint-storage caveat in this guide for asset limits.
- **Courier README:** still calls the fixture format 9 and contains historical gaps; current `geno.json` is 10. Its old "static stand-in" heading is stale for the now-playing source fixture.
- **`own` row:** report ownership concerns script/callback/state declarations, separate from clip authorship in the artist build report.
- **Incomplete fixtures:** `moves_diff.py` refuses failed/incomplete logs; `moves_report.py` primarily judges named result rows and exits based on move verdicts. Inspect DONE and fatal lines yourself as part of acceptance.
- **Sora:** use committed converter/driver paths, not historical private generated packages as public prerequisites. The migration source is explicitly local-only (`trail_define.py:20`, `:344`).

### Lua and online corrections


1. **Stale offline-only statements:** game `melee/docs/geno.md:2856`, workspace `docs/scripting.md:2457`, and some slice-6 audio prose conflict with current §24. Online identities and admission are implemented in `melee/pc/platform/gw_mexid.c:268`; custom audio nevertheless remains separately guarded during rollback. Replace offline-only generalizations with current admission requirements.
2. **Compiler version:** game `melee/docs/geno.md:2984` overstates identity constituents; actual Lua hash is source/slots plus fixed LUA-V1 tag (`melee/pc/platform/geno_lua_registry.inc:147`).
3. **Strictness is selective:** unknown Lua block/per-state keys are not iterated or rejected by `gn_lua_parse`; unsupported `phys`, `on_hit` etc. keys inside `states[].lua` will not create callbacks. Native hook names not in the registry are logged and ignored. Do not say every unknown key refuses a define (`melee/pc/platform/geno_lua_registry.inc:64`, `melee/pc/platform/geno_lua_registry.inc:127`, `melee/pc/platform/geno_registry.c:1396`).
4. **Zero slots:** loader permits absent/empty state; digest/readout requires slots >0 (`melee/pc/platform/geno_lua_registry.inc:90`, `melee/pc/geno/geno_game_lua.inc:79`, `melee/pc/geno/geno_game_lua.inc:283`). Avoid asserting every possible Lua module always hashes faults.
5. **Nested GO:** the shared exchange block can be overwritten by nested enter calls; transition-last examples are safer than promising arbitrary later commands survive a `go` (`melee/pc/geno/geno_game_lua.inc:188`, `melee/pc/geno/geno_game_v2.inc:458`). This was read from code, not reproduced in a test.
6. **Enter depth and hard mode:** the game-side depth-four fault bypasses native `gw_Geno_LuaCall` and therefore its hard-policy frame note (`melee/pc/geno/geno_game_lua.inc:159`, `melee/pc/platform/geno_lua_registry.inc:216`). Do not say every kind of fault necessarily triggers hard-mode disconnect.
7. **Article profile numbering:** `RB_ItemHash` has the content-kind substitution, but `geno_art_digest` still includes raw `v->profile` (`melee/pc/geno/geno_game_articles.inc:459`). That term may differ with different installed-profile numbering. This is a source finding, not a demonstrated desync; do not overstate arbitrary different-install compatibility for article fighters without confirming this case.
8. **Coverage test scope:** `geno_digest_coverage` perturbs every word with all checks/conditions active and a nonempty Lua layout, but does not prove zero-layout fault inclusion or arbitrary native/article state coverage (`melee/pc/geno/geno_online_tests.inc:133`).
9. **Evidence boundaries:** game `docs/geno.md` §24.4 records the existing loopback matrix/soaks/lobby and one Windows/Linux match; §24.5 still marks replay headers for defined fighters, online voice/announcer, online Kirby copy and ABI-neutral heap budgeting unfinished. Cite these as recorded results, not verification run in this docs task.
