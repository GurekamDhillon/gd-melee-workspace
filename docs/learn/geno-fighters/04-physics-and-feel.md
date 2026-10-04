# Packet 4: Physics and feel (outline)

**Status: outline.** The facts are verified against the reference and the code. The steps are not
yet a worked tutorial, and nothing here was run. Where a worked example is missing, this packet says so.

**Goal:** know the tools that make a move feel right: engine values, conditions, hooks, and the
physics and collision callbacks of a Geno state.

**You will have at the end (once written up):** your packet 3 move with a hop, a landing rule and a
cancel, each checked in the LAB.

**Prerequisites:** packet 3.

## The four tools

| tool | what it is | where |
|---|---|---|
| **Engine values** | named numbers a script reads (`GET`, `IFV`) or writes (`PUT`): facing, velocity, stick, buttons, jumps, animation frame, percent... | `melee/docs/geno.md` 15.2, 17.2, 19.3, 19.12 |
| **Variables** | script storage: LA (kept across states), RA (cleared on each action change), int and float banks, 64 each | 8, 15.1 |
| **Change-action checks** | "go to X when Y": `CHG` with a condition, `CHGAND` to add conditions, `CHGCLR` | 15.3 |
| **Behaviours and callbacks** | a state's four per-frame functions (anim, iasa, phys, coll), chosen as a bundle or one by one | 16.2, 17.3 |

### Values you will use first

Writable values (15.2): `AIR`, `FACING`, `VEL_X`, `VEL_Y`, `GROUND_VEL`, `FWD_VEL`, `JUMPS_USED`,
`CMD_VAR0-3`, `ANIM_RATE`. Read-only: `STICK_X/Y/FWD`, `BUTTONS_HELD/PRESSED`, `ANIM_FRAME`,
`ACTION_FRAME`, `MOTION`, `PERCENT`, `POS_X/Y`. v3 and later add `LEDGE`, `HIDDEN`, `TRANSN_FWD/UP`,
`MOTION_GRAVITY`, `ATTACK_CONNECTED`, `STICK_LEN`, `FALL_LIMIT` (17.2, 19.12). The ids are stable
and never renumbered.

### A hop in a script, hand-encoded

The escape word is `(59 << 26) | (sub << 20) | (length << 16) | sub-specific` (section 8). `PUT`
is sub `0x09`, length 3: word 0 `0xEC930000`, word 1 the value id, word 2 the value in the value's
own type (a float's bit pattern for a float value). So "set vertical velocity to 1.5" is:

```
0xEC930000  0x00000003  0x3FC00000     # PUT VEL_Y (id 0x03) = 1.5f
```

This is derived from the documented layout and from the repository's encoder tests (the SET and
ORIG words in `geno_tests.c` reproduce under the same formula). It has not been run. To try it, put
those three words into a word file at the point of the move where the hop should happen, after a
wait. `PUT AIR 1` first, if the fighter is on the ground, to leave the floor (15.2: "writing 1 on the
ground makes the fighter airborne").

## Physics callbacks of a state

A Geno state picks a behaviour (16.2) or overrides one callback with its name (`phys`, `coll`,
`anim`, `iasa`):

- `geno.air`: Melee's aerial physics (gravity, fast fall, drift) and air collision with ledge grab.
- `geno.ground`: ground physics and collision.
- `geno.anim_motion` (v3): the animation's own root motion moves the fighter. It takes `liftoff`,
  `origin`, `facing`, `gravity`, `ledge` and `land` keys (17.1). Moves that travel with their clip
  (Brawl's Shuttle Loop, the cape's reappear) are built from it.
- Callback names per slot: phys `none air air_nodrift ground auto ... anim_motion brake air_drift`,
  coll `none air air_noledge ground ground_stop both glide drill anim_motion cape`; `like` copies the
  like-motion's own callback (16.2, 17.3, 19.12).

**Landing.** A state's `land` key decides where it goes on touching the floor: a motion, a Geno
state, `"stay"` (become grounded, keep the state), or Melee's Landing, with `landing_lag` for a
fixed lag via LandingFallSpecial (16.1, 17.1). A registered `CHG GROUND -> X` is also tested at
the moment of landing and wins over the state's own transition (15.3).

## The worked example in the tree: Meta Knight's up special

`ports/halberd/mods-slot/metaknight-slot/geno.json` is a real profile (research configuration;
it needs the fighter's own data files, which are not in this repository). Four of its states chain
a Brawl-style up special:

```
UpB      geno.anim_motion  like motion:385  liftoff origin  ledge none  land geno:UpBLand  next auto
UpBAir   geno.anim_motion  like motion:389  ledge none      land geno:UpBLand  next geno:UpBLoop
UpBLoop  geno.anim_motion  like motion:386  origin  ledge none  land geno:UpBLand  next auto
UpBLand  geno.ground       like motion:43   next auto
```

Read it with section 17.1: each state moves by its clip's root motion; `liftoff` lets an upward
step leave the ground; `origin` also takes the clip's frame-0 offset; `ledge: none` disables ledge
grab for the state; `land` sends a landing to `UpBLand`. The up special is bound in the same file by
`"specials": {"hi": "geno:UpB", "air_hi": "geno:UpBAir"}`.

**To write for the complete packet:** rebuild a smaller version of this on your tutorial fighter. It
needs a clip that has root motion, which Kirby's reused rows may not have. Until a sample
fighter exists (packet 10), a person cannot follow this part end to end.

## Hooks

Native hooks, bound to dispatch points in `geno.json` or called from a script's `CALL`:

| # | name | does |
|---|---|---|
| 1 | `geno.log` | writes the argument and LA int 0 to the log |
| 2 | `geno.jumps.refill` | gives back air jumps |
| 3 | `geno.jumps.to_var` | copies air jumps left into a variable |
| 4 | `geno.count_frames` | adds one to a counter variable |
| 5 | `geno.article.spawn` | spawns an article (packet 5) |
| 6 | `geno.lockon` | aim and face the nearest other fighter |
| 7 | `geno.aim_stick` | aim from the stick |
| 8, 9 | `geno.dash.search`, `geno.dash.aim` | a targeting dash |
| 10 | `geno.brake` | slow the fighter along its own direction |

(`melee/docs/geno.md` sections 9, 19.12.) Dispatch points: `on_init`, `on_frame`, `on_action`,
`on_land`, `on_hit` (numbers 0 to 4). The hook table is `const` and fixed: **an author cannot add a
hook without changing the engine** (`melee/pc/geno/CLAUDE.md`: a feature adds hooks as rows in
`geno_game.c`).

## What "feel" means here

Geno will not change Melee's global rules: hitstun, knockback formulas, air dodge, ledges and tech
stay as they are (section 1). Feel therefore means your fighter's numbers (packet 6), the shape of
its moves (this packet) and its cancels. If you want a Brawl or Ultimate rule that is global,
it is out of scope by design.

## Check yourself (for the full packet)

- Which values can a script write, and which only read?
- What does `CHG ... ONCE` do that plain `CHG` does not?
- Why is `GROUND` special among the change-action conditions?
- What is the difference between `LA` and `RA` variables?

## Sources

- `melee/docs/geno.md`: 1, 8, 9, 15.1 to 15.3, 16.1 to 16.2, 17.1 to 17.3, 19.12.
- `melee/pc/geno/geno.h` (the sub-command, value and condition numbers); `melee/pc/geno/geno_tests.c`
  (`test_geno_v1_overlay`: the SET and ORIG word values the formula reproduces).
- `ports/halberd/mods-slot/metaknight-slot/geno.json`.
- `melee/pc/geno/CLAUDE.md`.
