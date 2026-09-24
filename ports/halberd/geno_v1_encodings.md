# Geno v1 script encodings (for the Meta Knight translator)

Source of truth: `worktrees/beta/docs/geno.md` section 15 (branch `private/geno`) and
`pc/geno/geno.h`. This file is a copy for the translator; if they ever differ, geno.md wins.
The encodings below are **stable**: they will not be renumbered. New things get new numbers.

Everything is a Melee subaction (ftcmd) command with **opcode 59** (first byte 0xEC-0xEF). Words are
big-endian 32-bit, like every other ftcmd word in a Pl file.

```
word0  [31:26] 59   [25:20] sub   [19:16] len (total words incl. word0, 1-15)   [15:0] sub-specific
```

Unknown subs are skipped by `len`, so always set `len` correctly.

## 1. Variables (v0, unchanged)

A **var ref** is 8 bits: `[7:6] bank, [5:0] index`. Banks: `0` LA int, `1` RA int, `2` LA float,
`3` RA float (64 vars each). LA = kept across actions (reset at spawn/respawn), RA = cleared on
every action change. PSA bit vars are bits of int vars (translator's choice of packing, e.g.
`RA.Bit[n]` -> RA int `n / 32`, bit `n % 32`).

Variable-sub layout of word0 `[15:0]`: `[15:8] var A`, `[7] B is a var`, `[6:4] cmp`, `[3:0] 0`.
`B` (word1) is an immediate (int, or float bits when A is a float var) or, with `[7]` set, a var
ref in `[7:0]` (converted to A's type).

| sub | name | len | effect |
|---|---|---|---|
| 0x00 | NOP | any | nothing |
| 0x01 | SET | 2 | `A = B` |
| 0x02 | ADD | 2 | `A += B` |
| 0x03 | SUB | 2 | `A -= B` |
| 0x04 | MUL | 2 | `A *= B` |
| 0x05 | SETBIT | 2 | `A |= 1 << B` |
| 0x06 | CLRBIT | 2 | `A &= ~(1 << B)` |
| 0x07 | DIV | 2 | `A /= B` (B == 0: A unchanged) **v1** |
| 0x0A | RAND | 2 | int A: `A = random 0..B-1` (B <= 0: 0); float A: `A = random [0, B)`. Game RNG (rollback-safe) **v1** |
| 0x10 | IF | 3 | if `!(A cmp B)` skip `word2` words (counted from the end of this command) |
| 0x11 | SKIP | 2 | skip `word1` words forward |
| 0x20 | CALL | 3 | native hook `word1` with argument `word2` |

cmp: `0` EQ, `1` NE, `2` LT, `3` LE, `4` GT, `5` GE, `6` BIT (`A & (1 << B)`), `7` NOBIT.

`if (c) {T} else {E}` = `IF !c ->skip |T|+2 ; T ; SKIP |E| ; E`. Skips only go forward. For a
backward jump (a loop) use Melee's own goto/loop commands (they wait frames), guarded by an IF.

## 2. Engine values (v1)

| sub | name | len | layout |
|---|---|---|---|
| 0x08 | GET | 2 | word0 `[15:8]` var A; word1 = value id. `A = value` (converted to A's type) |
| 0x09 | PUT | 3 | word0 `[7]` B is a var; word1 = value id; word2 = B (immediate in the **value's** type, or a var ref). `value = B`. Read-only values ignore it (logged once) |
| 0x12 | IFV | 4 | word0 `[7]` B is a var, `[6:4]` cmp; word1 = value id; word2 = B (value's type or var); word3 = words to skip when `!(value cmp B)` |

Value ids (type: `f` float, `i` int; `W` = writable):

| id | name | type | W | meaning |
|---|---|---|---|---|
| 0x00 | AIR | i | W | 1 in the air, 0 on the ground. Writing 1 on the ground makes the fighter airborne (Melee's own "become airborne"); writing 0 is ignored (landing needs a floor: use the ground check / on_land) |
| 0x01 | FACING | f | W | +1 right, -1 left. Writing: sign sets the facing, **0 turns around** (PSA "Reverse Direction") |
| 0x02 | VEL_X | f | W | self velocity x (world) |
| 0x03 | VEL_Y | f | W | self velocity y |
| 0x04 | GROUND_VEL | f | W | ground velocity (along the floor) |
| 0x05 | FWD_VEL | f | W | self velocity x times facing (forward-positive; PSA "Set Horizontal Speed") |
| 0x06 | KB_VEL_X | f |  | knockback velocity x |
| 0x07 | KB_VEL_Y | f |  | knockback velocity y |
| 0x08 | STICK_X | f |  | control stick x, -1..1 (world) |
| 0x09 | STICK_Y | f |  | control stick y |
| 0x0A | STICK_FWD | f |  | stick x times facing (forward-positive) |
| 0x0B | CSTICK_X | f |  | C-stick x |
| 0x0C | CSTICK_Y | f |  | C-stick y |
| 0x0D | ANIM_FRAME | f |  | current animation frame (0-based, as Melee counts it) |
| 0x0E | ACTION_FRAME | i |  | frames spent in the current action (1 on its first frame) |
| 0x0F | MOTION | i |  | current Melee motion (action state) id |
| 0x10 | PERCENT | f |  | damage percent |
| 0x11 | JUMPS_USED | i | W | jumps used (ground jump counts; 1 in the air after leaving the ground) |
| 0x12 | JUMPS_MAX | i |  | max jumps |
| 0x13 | BUTTONS_HELD | i |  | Geno button mask (section 3) of held buttons |
| 0x14 | BUTTONS_PRESSED | i |  | Geno button mask of buttons pressed this frame |
| 0x15 | POS_X | f |  | position x |
| 0x16 | POS_Y | f |  | position y |
| 0x17-0x1A | CMD_VAR0-3 | i | W | Melee's script variables `fp->cmd_vars[0..3]` (what Melee's own "set cmd var" writes and special states read) |
| 0x1B | ANIM_RATE | f |  | animation speed |
| 0x1C | FAST_FALL | i |  | 1 while fast-falling |
| 0x1D | TRIGGER | f |  | analog shield trigger, 0..1 |
| 0x1000 + i | SPECIAL_F[i] | f |  | special attribute word i (`fp->dat_attrs`), read as float, i < 265 |
| 0x2000 + i | SPECIAL_I[i] | i |  | special attribute word i, read as int |

## 3. Change action (v1)

| sub | name | len | layout |
|---|---|---|---|
| 0x30 | CHG | 2-4 | word0 `[15:8]` condition, `[7]` B is a var, `[6:4]` cmp, `[3]` NOT, `[2]` ONCE; word1 = **target**; word2 = arg1; word3 = arg2 |
| 0x31 | CHGAND | 1-3 | word0 `[15:8]` condition, `[7]`, `[6:4]`, `[3]` NOT as CHG; word1 = arg1; word2 = arg2. Adds an AND condition to the most recent CHG of this action (PSA "Additional Change Action Requirement"). Max 3 conditions per CHG |
| 0x32 | CHGCLR | 1 | removes every change-action check of this action |

Semantics (Brawl's): a CHG **registers** a check. Without `ONCE` it is checked **every frame for
the rest of the action** (cleared by any action change). With `ONCE` it is checked once, at the end
of the frame it was registered in, then dropped. Checks are tested in registration order, first
match wins. Registered checks run every frame after the animation and script advance and **before
the state's own animation callback**, so an "animation end" check beats the state's own anim-end
transition. Up to 8 checks per fighter (a 9th is dropped, logged). `CHG ALWAYS ONCE` = "change
action now" (at the end of this frame's script pass - never in the middle of a script).

Landing: a registered check whose (first) condition is GROUND is also tested **at the moment of
landing** inside the collision callback, and wins over the state's own landing transition (it runs
right after the callback). Likewise AIR at the moment of leaving the ground there. So PSA
`Change Action X, requirement On Ground` is exactly `CHG GROUND -> X`.

Conditions (`[15:8]`):

| id | name | arg1 | arg2 |
|---|---|---|---|
| 0 | ALWAYS | | |
| 1 | ANIM_END | | | the animation has no frames left |
| 2 | GROUND | | | on the ground |
| 3 | AIR | | | in the air |
| 4 | PRESSED | Geno button mask | | any of the buttons pressed this frame |
| 5 | HELD | Geno button mask | | any of the buttons held |
| 6 | BIT | var ref | bit index | bit set (NOT for "bit clear") |
| 7 | VAR | var ref A | B (A's type, or var ref with `[7]`) | `A cmp B` |
| 8 | FRAME | frame N (int) | | animation frame >= N |
| 9 | VALUE | value id (section 2) | B (value's type, or var ref with `[7]`) | `value cmp B` |

Geno button mask: bit 0 ATTACK (A), bit 1 SPECIAL (B), bit 2 JUMP (X or Y), bit 3 SHIELD (L or
R, digital or the analog trigger past Melee's shield threshold), bit 4 GRAB (Z), bit 5 TAUNT
(D-pad up). Brawl's requirement button ids 0-5 are these bits (`1 << id`).

**Target word:**

```
[31:28] kind   0 MOTION  id = Melee motion id (common 0-340, fighter specials 341+)
               1 SPECIAL id = the fighter's special action n (motion = first special + n)
               2 GENO    id = Geno state (v2; v1 skips such a check - logged - and a later
                         matching check still fires, so emit a fallback CHG after it)
[27]    RAW        plain Fighter_ChangeMotionState, even for the common states below
[26]    KEEP_FRAME continue at the current animation frame with Melee's mid-move transition
                   flags (hitboxes, GFX, SFX kept) - Melee's way to swap the air/ground version of
                   a move, i.e. Brawl's "Change Subaction" to the other-situation variant. Implies RAW
[25:16] 0
[15:0]  id
```

Without RAW, these common states enter through Melee's own entry function (so they are set up
the way the game sets them up): Wait (on the ground; in the air it becomes Fall), Fall,
FallSpecial (helpless fall, default landing lag), Landing, LandingFallSpecial. Every other target
is a plain `Fighter_ChangeMotionState(id, 0, frame 0, speed 1, blend 0)` into that motion's row -
the state's callbacks run, its special entry code (if any) does not.

## 4. Hitbox helpers (v1)

| sub | name | len | layout |
|---|---|---|---|
| 0x38 | REHIT | 2 | word0 `[15:8]` hitbox mask (bit i = Melee hitbox id i, 0-3); word1 = N frames (0 = stop) |
| 0x39 | LINK | 2 | word0 `[15:8]` hitbox mask; word1 = mode: 0 off, 1 autolink direction, 2 direction + speed |

**REHIT** = Brawl's rehit rate: every N frames (counted from the command, frozen during the
attacker's hitlag) the victim lists of those hitboxes are cleared - exactly what Melee's
multi-hit moves get by re-creating a hitbox. Lives until the action ends or `REHIT mask 0`.
Emit it right after the hitbox creation (Brawl: `Offensive Collision ... rehit rate 6` ->
Melee hitbox + `REHIT mask(id) 6`).

**LINK** = Brawl angle 365 for these hitboxes (keep Melee's angle field at any value, e.g. 361 or
the Brawl number - LINK overrides it for Geno fighters only; without LINK a Melee hitbox angle is
used as Melee uses it). On a hit, the victim is launched along the attacker's momentum (its air
velocity, or its ground velocity along the floor); when the attacker is nearly still (speed below
0.05) the hitbox's own Melee angle applies unchanged. Mode 1 keeps the hitbox's Melee knockback magnitude (hitstun as Melee
computes it). Mode 2 also raises the knockback so the victim's launch speed is at least the
attacker's speed. This is the agreed approximation of Brawl's 365, not a bit-exact copy.
Lives until the action ends or `LINK mask 0`.

## 5. Script overlays and on_land (geno.json)

```json
"subactions": [ { "index": 87, "words": ["0xEC220001", 5, "0x08000014"] },
                { "index": 88, "file": "geno/mk_fair.txt" } ],
"special_attributes": [ { "index": 13, "float": 16.0 }, { "offset": "0x2C", "int": 10 } ],
"on_land": [ { "from": "special:4", "to": "special:6" },
             { "from": 66, "to": 43, "keep_frame": false } ],
"hooks": { "on_land": ["geno.count_frames:5"] }
```

- `subactions`: replace subaction (animation + script) `index`'s **script** with these words
  (numbers or "0x.." strings; a `file` is whitespace-separated words, `#` comments). Loaded once at
  boot, read-only. Inside an overlay, sub **0x13 ORIG** (len 1) continues with the fighter's
  original script of that subaction from its start - so an overlay can be "Geno prefix + ORIG".
- `special_attributes`: override the fighter's special attribute block (`dat_attrs`) word by word
  (`index` = word, or `offset` = bytes); the value is `float` or `int`. Applied before the
  fighter's own attribute setup copies/scales them, at every spawn and attribute re-apply.
- `on_land`: when the fighter lands while in action `from`, it goes to `to` (after any script
  GROUND check, which wins). Targets: a number (motion id), `"special:N"`, `"motion:N"`,
  `"geno:N"` (v2). `keep_frame` = the KEEP_FRAME bit.
- `hooks.on_land`: native hooks at the moment of landing.

## 6. Brawl PSA -> Geno cheat sheet

| PSA | Geno |
|---|---|
| Change Action X, req R | `CHG R -> X` |
| Additional Change Action Requirement R | `CHGAND R` |
| Change Subaction X, req On Ground / In Air | the Melee action whose subaction is X, `KEEP_FRAME` (or a plain target) |
| Change Action Status 10000/10002 (Wait/Fall group) | `CHG ... -> Wait` / `-> Fall` (common entry) |
| If On Ground / In Air | `IFV AIR EQ 0/1` |
| If Compare IC.x | `GET` the value into a var, then `IF`, or `IFV` directly |
| If Button Pressed n | `IFV BUTTONS_PRESSED BIT n` |
| Set Air/Ground (to air) | `PUT AIR 1` |
| Reverse Direction | `PUT FACING 0` |
| Set/Add Horizontal Speed | `PUT FWD_VEL` (add: GET, ADD, PUT) |
| Set Vertical Speed | `PUT VEL_Y` |
| Offensive Collision rehit N | Melee hitbox + `REHIT mask N` |
| Offensive Collision angle 365 | Melee hitbox + `LINK mask 1` |
| Roll A Die n | `RAND A n` |
