# B1 — native hit/armor acceptance contract

Read-only audit, 2026-09-30. Game checkout: `/home/gd/melee_linux_test/gdm/melee/worktrees/linux`
@ `5664a6db1`. **No build, no test run, no game launch, no console contact.** Every claim below is
source inspection; anything requiring execution is marked PENDING.

## Summary

`ftColl_80076640` is **not** an admission check and **has no refusal arm**. All of its `false`
returns occur *after* it has already mutated the victim's armor. Both scripted wrappers discard
that boolean and re-emit it as the public Lua result, so the public API reports "refused" for a
hit that in fact landed against armor. A live consumer at
`pc/scripts/examples/roguelite/main.lua:768` performs a full state rollback on that `false`, so
the refund is not merely mislabelled — it is actively wrong.

The prior audit (`_build/deepseek-coordination/native-hit-refusal-audit.md`) reached the same core
conclusion and the same recommended fix. This audit adds: (a) the two engine callers it did not
cite, (b) the finding that `EnemyStrike:2503` is *not* an ordering bug, and (c) a live Lua
refund consumer it did not find.

### What the prior audit concluded
- `ftcoll.c:216-237` is a damage-result helper; its `false` means "armor absorbed the whole hit"
  (`native-hit-refusal-audit.md:9-34`).
- `ScriptGame_Hit`/`ScriptGame_EnemyStrike` expose that as zero/false post-chip (`:35-39`).
- Ordinary collision paths must stay unchanged (`:41-45`).
- Fix: make the scripting boolean mean "accepted native damage action, including armor
  absorption"; do not fabricate callbacks (`:47-71`).
- Item path `ScriptGame_EnemyHurt` has no analogous absorbed-false and should keep accepted-action
  semantics (`:78-93`).
- Existing armor state is not observable from Lua; only `body_state`/`intangible`/`invincible`/
  `shield` are (`:95-120`).
- No existing test exercises a successful armor contact (`:138-144`).

### What it left open
- No concrete regression test exists or is written (`:138-175`, proposals only).
- Shield/intangible/`x221D_b6` parity explicitly left pending (`:164-166`).
- Native validation of successful damage/KO deferred to a Windows pass (`:174-175`).
- It asserted `EnemyStrike` "includes the mutating call in its compound refusal guard" as a defect
  (`:36-38`, `:57-60`). **This audit disputes that** — see "Why refund-on-false is unsafe".

## Current behaviour

### The helper (`src/melee/ft/ftcoll.c:216-237`)

```c
216 bool ftColl_80076640(Fighter* fp, float* dmg) {
218     int env_dmg = getEnvDmg(*dmg);   /* captured from ORIGINAL damage, pre-mutation */
220     if (fp->x221C_b4) {
221         fp->dmg.x1834 -= *dmg;                      /* ARMOR MUTATION */
222         if (fp->dmg.x1834 < 0) {                     /* strict <, so x1834==0 survives */
223             *dmg = -fp->dmg.x1834;                   /* spill remainder */
224             fp->x221C_b4 = false;                    /* ARMOR MUTATION: flag cleared */
227     if (!fp->x221C_b4) {
231         fp->dmg.x1838_percentTemp += *dmg;           /* percent mutation */
233             fp->dmg.x183C_applied = env_dmg;
235         return true;
237     return false;
```

Mutation sites: `ftcoll.c:221` (armor HP), `ftcoll.c:224` (armor flag), `ftcoll.c:231` (percent),
`ftcoll.c:233` (applied-damage record). Fields declared at `src/melee/ft/types.h:1477` (`x1834`),
`types.h:1761` (`x221C_b4`), `types.h:1562` (`shield_health`), `types.h:1747` (`x221B_b0`).

**Every return path is post-mutation.** The `false` at `:237` is reached only when `x221C_b4` was
true at `:220`, which means `:221` already executed. The helper therefore *cannot* express
"refused before contact".

Trace (armorHP 20, damage 10 → `x1834`=10, not `<0` → flag kept, `false`, armor chipped to 10):
identical for armorHP 10 / damage 10 (`x1834`=0, strict `<` at `:222` fails, `false`, armor 0
still enabled). armorHP 5 / damage 10 → `:222` true, spill 5, flag cleared, `true`.

Note `*dmg` is **not** zeroed on full absorption, so a caller cannot distinguish "absorbed" from
"damage dealt" by inspecting `applied` — `applied` equals the original damage in both the
absorbed and the disabled-armor cases. The helper's own return value is the only discriminator.

### Callers and wrappers

| Site | Use of the result |
| --- | --- |
| `pc/gameworld/script_game.c:2426-2428` | `if (!ftColl_80076640(fp, &applied)) return 0;` — **mapped to public false** |
| `pc/gameworld/script_game.c:2503` | `... \|\| !ftColl_80076640(fp, &applied)) return 0;` — **mapped to public false** |
| `src/melee/ft/kinds/ftCommon/ftCo_Bury.c:88` | `if (ftColl_80076640(fp, &f) != 0)` — correct: absorbed skips the damage event |
| `src/melee/ft/kinds/ftCommon/ftCo_Bury.c:194` | `if (ftColl_80076640(fp, &f))` — correct, same shape |
| `src/melee/ft/kinds/ftCommon/ftCo_Throw.c:540` | return value **discarded**; proceeds to knockback regardless |

Declaration `src/melee/ft/ftcoll.h:30`; guest address mapping `pc/platform/gw_mex_bridge.c:1471`.

The two `ftCo_Bury` callers — not cited by the prior audit — are the in-engine proof that
"absorbed" is a *skip the damage pipeline* decision, not a refusal. `ftCo_Throw.c:540`
discarding the result reinforces that no engine caller reads it as a veto.

### Lua surface

`gw_script.c:1728` (`l_hit`, defined `gw_script.c:1709`) returns the `ScriptGame_Hit` boolean
straight to Lua. `gs_enemy_combat` (`gw_script.c:5486-5490`) does the same for
`ScriptGame_EnemyStrike`. Registrations: `gw_script.c:5611`, `gw_script.c:5659`. Documented
contract at `/home/gd/melee_linux_test/gdm/docs/scripting.md:312`: *"Returns false for a missing
fighter/source or refused damage, true after processing."* — **this sentence is wrong**, because
a fully absorbed hit returns false having already spent armor.

## Why refund-on-false is unsafe

The unsafe mapping is the two `return 0` sites above, not the compound expression.

`script_game.c:2503` uses `||`, which short-circuits left to right. The helper is the **last**
operand, so it is evaluated only after every precondition in `script_game.c:2495-2503` has already
passed. The prior audit's characterisation of this as calling the helper inside an early guard is
incorrect; ordering is already correct and needs no change beyond the boolean mapping.

The defect is that both wrappers treat the helper's `false` as "the native engine declined". It
never declines. Concretely:

- `script_game.c:2426`: victim has 20 armor, `gd.hit` deals 10. Armor drops to 10
  (`ftcoll.c:221`), wrapper returns 0, Lua sees `false`.
- `pc/scripts/examples/roguelite/main.lua:768` on that `false` runs
  `rebind_current_run(assert(Core.restore(before)))` and reports `'Activation refused; charge retained'`.

The player's charge is refunded, the run state is rolled back, and the victim's armor has still
been permanently reduced. The script is told a refusal occurred; armor says a hit occurred. This
is exploitable in both directions: a script can farm armor depletion while its own bookkeeping
records no hits.

The same inversion is reachable via `gd.enemy_strike` (`main.lua:767` routes to
`gw_ScriptGame_EnemyStrike` for handle-owned targets), which shares the defect at
`script_game.c:2503`.

Secondary: `pc/tests/boss_end.lua:29` treats `false` as `"environment hit rejected"` and fails the
run. Whether Master Hand carries armor in that fixture is PENDING without a build.

## Proposed contract change

**The minimal fix requires no new native signal at all.** The information needed is already
returned by the helper; the wrappers simply discard it. Step 1 is mandatory and sufficient.

1. **Stop mapping helper-`false` to public-`false`** — `pc/gameworld/script_game.c:2426-2428`.
   Call the helper unconditionally after the existing `fp == NULL` / `from_slot` validation at
   `script_game.c:2421-2423`. Capture its result in a local `absorbed`. If absorbed, return 1
   immediately, *before* `ftColl_8007A06C` / `Fighter_ProcessHit_8006D1EC` — there is no spill
   value to process, mirroring `ftCo_Bury.c:88`.
2. **Same split in `EnemyStrike`** — `pc/gameworld/script_game.c:2503`. Remove the `!ftColl(...)`
   operand from the `||` chain (keeping the short-circuit order intact), call the helper after the
   chain, and return 1 on the absorbed path before `ftColl_8007A06C` /
   `Fighter_ProcessHit_8006D1EC` at `script_game.c:2510-2512`.
3. **Leave `ftColl_80076640` untouched** — `src/melee/ft/ftcoll.c:216-237`. Its `false` is correct
   for `ftCo_Bury.c:88`/`:194`, which legitimately skip the damage pipeline, and is discarded at
   `ftCo_Throw.c:540`. Changing it would break in-engine bury/throw semantics.

If an explicit tri-state is wanted (so a caller can *tell* absorbed from damaged rather than
merely not be refused), the minimal additional surface is one shared helper:

- New `static int script_armor_stage(Fighter* fp, float* dmg)` in `pc/gameworld/script_game.c`
  returning `0 = refused before entry`, `1 = accepted, fully absorbed`, `2 = accepted, damage
  queued`. Both `ScriptGame_Hit` (`:2415`) and `ScriptGame_EnemyStrike` (`:2482`) call it; steps
  1-2 above are then one-line substitutions. Bridge ABI and the public boolean are unchanged.
- Optional read-only observation for Lua: add `armor_hp` (`x1834`) and `armor` (`x221C_b4`) to
  `gs_push_lab_fields` (`pc/platform/gw_script.c:1150-1215`). This lets scripts *report* chipping
  without fabricating a callback. Not required for refund safety.

Explicitly not proposed: snapshot/restore of `x1834` on absorption. It would make refusal
transactional but deletes armor chipping for these attacks — a gameplay change, and inconsistent
with the ordinary mechanic preserved at `ftcoll.c:674-680` and `ftcoll.c:1313-1333`.

Also required: correct `docs/scripting.md:312` to state that `false` means pre-acceptance refusal
(missing fighter/source, bad spec, defeated/owned/out-of-reach target) and that `true` includes
armor absorption without promising percent, knockback, or defeat.

## Test impact

**Zero existing coverage.** `grep -rli "armor\|armour"` over `pc/` returns no test file at all;
`armor`, `armour`, `x1834`, `x221C_b4`, `76640` have **no matches** in `pc/platform/gw_test.c`,
`pc/platform/gw_tests_core.c`, `pc/geno/geno_tests.c`, or `pc/tests/*.c`.

Tests that touch the changed wrappers:

- `pc/platform/gw_script.c:8873` `test_script_hit` (comment at `:8871-8872`) — exercises only
  missing fighter, negative damage, invalid `from`. All three are Lua-side or pre-helper
  rejections, so the fix does not alter them. **It will not catch a regression of this contract.**
- `pc/platform/gw_script.c:8534-8536` → `gw_ScriptGame_EnemyTest` (`script_game.c:2561`) —
  enemy contact/lifecycle/guard invariants. Whether any assertion depends on the old absorbed→0
  mapping is **PENDING** without a build.
- `pc/tests/boss_end.lua:29-32` — `"environment hit rejected"` on `false`. Pass/fail impact is
  **PENDING** without a run; it depends on whether the Master Hand fixture has armor enabled.
- `pc/scripts/examples/roguelite/main.lua:767-768` — behaviour changes by design: armor-only
  targets now charge the attack. Existing run-state assertions may need review.

New test required (asset-independent, real `Fighter` + real `ftColl_80076640`, targeting the shared
`script_armor_stage` helper if adopted):

- armor 20 / hit 10 → public `true`, armor 10, flag retained, `x1838_percentTemp`/`x183C_applied`
  unchanged, no hit processor or event.
- armor 10 / hit 10 → `true`, armor 0, flag retained; next hit 5 breaks armor and queues spill 5
  (locks the strict `<` boundary at `ftcoll.c:222`).
- armor 5 / hit 10 → `true`, flag cleared, pending 5, `x183C_applied` per the `ftcoll.c:218`
  original-damage protocol.
- armor disabled / hit 10 → `true`, pending 10, processing runs exactly once.
- All `script_game.c:2421-2423` and `script_game.c:2495-2503` refusals → `false` with
  byte-equal armor/damage fields.
- A Lua seam test where the engine reports absorbed-accepted: charge spent exactly once while
  percent is unchanged.

## Open questions

1. Does `ScriptGame_EnemyTest` (`script_game.c:2561`) encode the old absorbed→0 mapping?
   **PENDING** — needs inspection under a build-capable agent.
2. Is armor enabled on the Master Hand fixture in `pc/tests/boss_end.lua`? **PENDING**.
3. Shield/intangible/`x221D_b6` parity remains unproven. Ordinary collision gates on
   `ftcoll.c:1298-1301` (`x1988`, `x198C`, `x221D_b6`, capsule state); `ScriptGame_Hit`
   (`script_game.c:2415`) checks none of these and `ScriptGame_EnemyStrike` (`:2482`) checks only
   motion IDs and hitlag. Fixing the armor boolean does **not** establish immunity parity. Whether
   to add that gating is a design decision, not a bug fix.
4. `ftCo_Throw.c:540` discards the result. Intentional, or a latent bug? Needs engine context.
5. `x221D_b6` is described as "opaque immunity" by the prior audit (`:118-120`); its exact
   gameplay meaning is unverified here. **PENDING**.