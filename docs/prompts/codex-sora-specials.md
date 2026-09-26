# Code task for Codex: Sora's special-move gaps (Sonic Blade's hit branch, Counter's turn / backward / rebound)

Written 2026-09-26 by lane echo (Claude), who wrote the generator. **Code only.** Do NOT build or run
the game, run build.sh / run.sh, launch other Codex processes, or profile. Write the code, run the
offline checks below, and stop. Claude lanes build, install and test in game afterwards.

## Background

Sora (Smash Ultimate fighter id **`trail`**, dump agent Hash40 `0x5b268858f`) is ported into Melee.
His side / up / down specials are Geno states (Geno = our native fighter-extension engine), generated
by **`ports/ir/tools/trail_specials_geno.py`** (read it whole first: the module docstring lists what is
ported, inferred and missing). Inputs:

- `_build/tmp/ir/trail.acmd.json` - our ACMD dump parsed by `ports/ir/tools/acmd_parse.py` (per script:
  `commands` with `frame`, `cmd`, `args`, `named` ATTACK fields, `when` branch conditions; `motion` =
  cancel_frame / xlu (intangibility) / clip from the motion list). Regenerate it if missing:
  `python ports/ir/tools/acmd_parse.py trail C:/Users/Gurek/ghidra-projects/sora_acmd -o _build/tmp/ir/trail.acmd.json`
  (check the script's `--help` for the exact form).
- The decompiled scripts: `C:/Users/Gurek/ghidra-projects/sora_acmd/game/0x5b268858f__<script_hash>.c`
  (hashes in `index.tsv` and in each acmd.json row's `script_hash`).
- `vl.prc` params (decoded in the generator's `params()`), the clips' frame counts / Trans tracks
  (`clip_info()`).

Run it (baseline and after your change):
`python ports/ir/tools/trail_specials_geno.py --host marth -o _build/tmp/codex-specials/<before|after>`
(outputs `geno.json`, `clips.json`, `geno/sora_sp_<subaction>.txt` word files).

## The Geno encodings you emit (do not invent new ones)

Reference: `melee/docs/geno.md` (the workspace's `melee` checkout, read-only for you).
- Script escape, variables, IF / SKIP / CALL: section 15.1. **IF skips `word2` words when the test
  FAILS** (`IF RAI0 BIT 0, skip 2; CHG X` runs the CHG only when the bit is set).
- Engine values GET / PUT / IFV: 15.2 (FACING 0x01, FWD_VEL 0x05, HIT_DAMAGE 0x35 ...); v2 values
  16.1 (MOVE_F0-7 0x20.., MOVE_I0-7 0x28..).
- Change action CHG (ONCE = "change now", first registered match wins): 15.3; target GENO(n) =
  `(2 << 28) | n` where n = the state's index in the profile.
- Hitboxes: `acmd_to_ftcmd.hitbox_words` (already used by `hit_events()`); HBDMG sub 0x3A (hitbox damage
  from a var): 19.12. Counter windows (`"counter": {from, to, target, negate}`): 19.4.
- Hook 6 `geno.lockon` (faces + aims at the nearest opponent, writes MOVE_F0/F1/I0): 19.12.
- The helpers for all of these already exist at the top of `trail_specials_geno.py` (`GET`, `PUTF`,
  `IF`, `IFV`, `CHG`, `GENO`, `CALL`, `HBDMG`, `Timeline`). Use them.

**State numbering trap:** script targets are numbers = declaration order. `STATES` must list the
states in exactly the order `build()` declares them (there is an assert); `--magic` offsets all of
them by the magic profile's state count. Add new states at the END of `STATES` / `CLIPS` / each
`HOSTS` entry so existing numbers do not move, and give each a free host subaction: Marth's unused
special rows are 310-320 (`SpecialS4S` .. `SpecialAirS4Lw`, see `_build/tmp/ir/marth.melee.ir.json`);
for `kirby` pick unused rows from `kirby.melee.ir.json` (not 322-339 already taken, not 333/336).

## What to do

### 1. Sonic Blade's hit branch (game_specials2 / game_specials3)

Facts (verify in the C, cite lines in your report):
- `game_specials2` = `game/0x5b268858f__0xe9c8f6931.c`, `game_specials3` = `...__0xeeb8859a7.c`.
- At frame 3 both read `WorkModule::is_flag(const_value_table + 0xe648)` (0xe9c8f6931.c ~l.96-106).
  Flag **false** -> ATTACK ids 0-2 at **3.0 %** (specials2 angle 108 kbg 8 bkb 80; specials3 angle 46
  kbg 88 bkb 80); flag **true** -> **5.2 %** (specials3 kbg 85). acmd.json marks them with `when`
  `(uVar8 & 1) == 0` holds True / False. The generator currently keeps only the default path
  (acmd_to_ftcmd's `default_path`: flag false... which in fact selects the **5.2** set - check this
  claim against the C and say which set `default_path` really keeps).
- Flag 0xe648 is set by status code, which is NOT in our dumps (only game/effect/sound/expression).
  The likely meaning is "the previous dash connected". Search every dumped script for 0xe648 and
  report what you find; do not guess beyond that.

Implement: emit BOTH hitbox sets, selected at run time by whether the previous dash hit. Geno now has
(pc-port 060c22b85, `melee/docs/geno.md` 19.12) value **0x3B ATTACK_CONNECTED** (1 when this fighter's
hitbox hit a fighter in the current action) and **0x3C ATTACK_CONNECTED_PREV** (its value when the
previous action ended); both reset at EVERY action change. Between dashes Sora is in the `SStart2`
hover state, so: in `SStart2` at frame 0, `GET LA int 2 = ATTACK_CONNECTED_PREV` (the dash that just
ended); in `SDash2` / `SDash3` at the ATTACK frame, `IF LA int 2 EQ 1, skip <len of the 3.0 set>` +
3.0-set words, then the reverse test for the 5.2 set (or IF / SKIP as in 15.1), matching which flag
value picks which set in the C. (LA int 0 is the magic cycle, LA int 1 the dash count: use 2.) Put it
behind a generator option `--sonic-hit-branch` (default OFF): with it off the output must stay
byte-identical to the baseline. Dash 1 (game_specials1) has no branch; leave it.

### 2. Counter Attack: turn / backward variants

Facts: clips `d03speciallwturn` (7 frames) and `d03speciallwbackward` (60 frames, Trans z -10.3 over the
clip; forward version `d03speciallw` is +13.2), same for `specialairlw*`. There are NO game scripts for
turn / backward (acmd.json has none): the backward counter uses `game_speciallw`'s hitboxes (confirm by
checking the effect/sound dumps for the backward motion name; say what you find).

Implement: in `LwAttack` / `LwAttackAir`, before `CALL geno.lockon`, store FACING (GET RAF6 FACING);
after it, `IFV FACING NE RAF6` (the attacker was behind: lockon turned Sora) -> `CHG` to a new state
`LwAttackBack` / `LwAttackBackAir`. The Back states: same hitboxes and HBDMG scaling as LwAttack, the
lunge from `d03speciallwbackward`'s Trans z deltas (negative = backwards along the new facing - decide
the sign from the clip and explain), frames = that clip's length, same intangibility / IASA rules. Use
`clip_info()` for the clip. The `turn` clip (7 frames) is a visual lead-in: record it in `clips.json`
only; do not add a state for it.

### 3. Counter rebound (game_speciallwrebound / game_specialairlwrebound)

Facts: scripts `0x152a45c23c` / `0x1823287e6e` contain only a QUAKE at frame 2 (camera shake); motion
list xlu 1-30 (intangible); clips 19 frames; params `rebound_*` in `param_special_lw` (printed by the
generator's `params()`: rebound_start_ground 25, rebound_frame_ground 1, rebound_start_air 30,
rebound_speed_y 0.02 / max 0.3, rebound_distance_min 0.9 / max 4.3, rebound_speed_mul_f/b_*,
rebound_attack_start_frame 4, rebound_height 1.9, rebound_approach 0.6). WHEN Ultimate enters rebound
is status code we do not have.

Do: report the most defensible trigger from these facts (with reasoning), and implement a
`LwRebound` / `LwReboundAir` state (19 frames, intangible 1-30 -> whole state, no hitbox, then Wait)
**only reachable behind a generator option `--counter-rebound`** (default OFF, output byte-identical
without it). If you cannot find a trigger expressible with the existing Geno conditions (15.3) /
values (15.2, 16.1, 19.3), do not invent one: leave the state unreachable, say so, and stop on this
item.

## Files you may touch

- `ports/ir/tools/trail_specials_geno.py`
- a new test `ports/ir/tools/test_trail_specials.py`
- nothing else. `acmd_parse.py`, `acmd_to_ftcmd.py`, `trail_magic_geno.py`, `ultimate_vfx_geno.py`,
  `fighterbuild/` and `test_acmd_catch.py` have other agents' uncommitted changes. Never edit
  `melee/` (the Geno engine side is lane echo's; values 0x3B / 0x3C exist).

## Acceptance (you check these yourself)

- `python ports/ir/tools/test_trail_specials.py` (plain python) runs the generator into
  `_build/tmp/codex-specials/test/` with all options on and asserts, decoding the word files:
  - SDash2 / SDash3: both damage sets present (3.0 -> Melee damage 3, 5.2 -> 5) with the dump's
    angles / kbg / bkb, at game frame 3, guarded by an IF on LA int 2, which SStart2 sets from value 0x3C; SDash1 unchanged.
  - LwAttack / LwAttackAir: the FACING compare and a CHG to the Back state's number; Back states' frame
    count = the backward clip's length, their FWD_VEL puts sum to the clip's Trans z total (report the
    number), hitbox frames 7 / 10 / 11 as LwAttack.
  - Rebound (if implemented): 19 frames, intangible for the whole state, no hitbox words.
  - `STATES` order assert holds; every CHG GENO target points at the intended state name.
- With **no options**, `--host marth` and `--host kirby` outputs are byte-identical to the baseline
  (diff every file in the output directory; report the count of differing files: must be 0).
- With the options on, only the files of the changed / new states differ (list them).
- The test reads numbers from the dump at run time and asserts against numbers you wrote in the test
  with a comment citing the .c file and line; no pasted script text.

## Rules

- No commits, pushes or merges; list the files changed.
- Game-derived data (dumps, acmd.json, outputs) stays under `_build/` or the Ghidra folder; never copy
  it into the repo.
- Numbers from the dump carry over 1:1; anything you infer is a named constant with an `INFERRED`
  comment and appears in the generator's printed report.
- If the task is wrong or impossible as written, stop and say so rather than working around it.

## Report (final message, also written to `_build/tmp/codex-specials-report.md`)

1. The 0xe648 findings (every script that reads / writes it) and which damage set `default_path` keeps.
2. The rebound trigger reasoning, and whether the state is reachable.
3. Files changed and what; the new state names, numbers (with and without `--magic` from
   `_build/agents/beta/mods-sora-magic/sora-magic-demo/geno.json`) and subactions.
4. Decoded words for SDash2, LwAttack, LwAttackBack; the test output; the diff counts.
