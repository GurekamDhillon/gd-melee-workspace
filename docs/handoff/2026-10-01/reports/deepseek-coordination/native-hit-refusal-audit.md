# Native hit refusal contract audit

Read-only audit of the actual root game checkout, 2026-09-30. No native/main
edits, build, install, or game launch. Paths below are relative to
`gdm/melee/worktrees/linux`.

## Confirmed contract mismatch

`src/melee/ft/ftcoll.c:216-237`, ftColl_80076640, is a damage-result helper, not a
transactional admission check:

```c
if (fp->x221C_b4) {
    fp->dmg.x1834 -= *dmg;
    if (fp->dmg.x1834 < 0) {
        *dmg = -fp->dmg.x1834;
        fp->x221C_b4 = false;
    }
}
if (!fp->x221C_b4) {
    fp->dmg.x1838_percentTemp += *dmg;
    /* updates x183C_applied using original damage */
    return true;
}
return false;
```

Its false means armor absorbed the entire hit. For armorHP20 and damage10 it
returns false with armorHP10; actual percent and pending damage remain unchanged.
For armorHP10 and damage10 it returns false with armorHP0 and armor still enabled.
Depletion uses strict `< 0`, so a subsequent positive hit breaks that remaining
zero-HP armor. For armorHP5 and damage10 it returns true, disables armor and passes
only spill damage5 to pending percent.

`pc/gameworld/script_game.c:2415-2428`, ScriptGame_Hit, exposes this absorbed
result as zero/false after the irreversible chip. ScriptGame_EnemyStrike
(`2482-2503`) includes the mutating call in its compound refusal guard and also
returns zero/false. A caller that restores Lua charge/run state on false therefore
refunds a cast that already changed native armor.

The ordinary fighter and item collision paths preserve this same armor mechanic:
`src/melee/ft/ftcoll.c:674-680` and `1313-1333` subtract x1834, use strict `<0`, and
only install a fighter damage result when armor no longer absorbs it. Do not
change ftColl_80076640 globally: its existing result has callers/semantics outside
the public scripting boolean.

## Minimal honest fix

Define the scripting boolean as **accepted native damage action**, including
armor absorption; it is not proof of percent loss, knockback, defeat, or an
ordinary collision callback.

1. Preserve all existing pure pointer/ownership/spec/reach/eligibility refusals.
   They remain false and must precede any damage-helper call.
2. In ScriptGame_Hit, change the fully absorbed helper branch to return1.
   Returning there deliberately skips ftColl_8007A06C and Fighter_ProcessHit,
   because there is no spill damage result to process.
3. In ScriptGame_EnemyStrike, remove the helper call from the compound refusal
   expression. Finish those preconditions first, then call the helper. Fully
   absorbed armor returns1 before hit-result construction/processing.
4. Leave the existing spill/ordinary damage branches and native collision
   mechanisms unchanged. Do not force percent, undo armorHP, or apply full damage
   after armor absorbs it.
5. Do not add on_hit, ScriptGame_EnemyContact, or a fabricated ordinary event to
   the absorbed branch. gd.hit currently emits no collision-loop on_hit
   (`docs/scripting.md:709`); preserve that. EnemyStrike's existing processed
   damage event has reaction lineage1; keep its existing branch unchanged.
6. Update the public gd.hit/strike documentation: false is pre-acceptance refusal;
   true includes armor absorption and does not promise a landed percent hit.
   Lua can then retain the charge spend on native true without guessing from
   percent readback.

An alternative is snapshot/restore of x1834 on absorption and returning false.
That makes refusal transactional but removes armor chipping by these attacks.
It is a deliberate gameplay change and does not preserve the ordinary Melee
armor mechanic. Accepted-true is the smaller compatible correction.

## Item wrapper comparison

ScriptGame_EnemyHurt (`script_game.c:2522-2557`) performs spec, pointer,
hurtbox/vulnerability, hitlag, pending-damage, distance/facing, owner and team
checks before preparation. It then sets xCA0/xCA4 to positive bounded damage,
records the ordinary item damage log, resolves it with it_80270E30, and calls
Item_ScriptCommitDamage while scripted_hurt is set.

`src/melee/it/item.c:1961-1966` returns0 only before commit when gobj is null or
xCA0 is nonpositive. Otherwise it invokes Item_8026A294 and returns1, including
when the ordinary damage callback destroys the item. it_80270E30
(`src/melee/it/itcoll.c:697-884`) resolves damage-log knockback/source/effects and
does not zero that prepared xCA0. No analogous absorbed-armor false result was
found in this path. Keep its accepted-action semantics; destruction or unchanged
HP does not itself mean native refusal. This is source inspection, not a native
successful-damage test.

## State readers already available, and wrapper gaps

No gd.stats API was found. Use **gd.player(port)**, which creates a fresh table
and calls gs_push_lab_fields (`pc/platform/gw_script.c:1195-1215`). Alongside the
basic movement/action/percent/stock/hitlag fields, it already exposes:

| Lua field | native source |
| --- | --- |
| body_state | x1988; normal/invincible/intangible |
| timed_state | x198C; same names |
| intangible | x1990 timer |
| invincible | x1994 timer |
| shield_on | x221B_b0 |
| shield | shield_health |
| in_hitlag / in_hitstun | x2219_b5 / x221C_b6 |

Proof: gs_push_lab_fields `gw_script.c:1150-1155`, `1178-1184`;
ScriptGame_LabI `script_game.c:1712-1721`, `1748-1751`; ScriptGame_LabF at1637.
gd.hurtboxes(port) also exposes each capsule's state as
normal/invincible/intangible (`gw_script.c:2718-2744`, ScriptGame_HurtI at1861).
The basic player-table paragraph in wrapper docs is incomplete relative to the
actual fields; this is not a missing ABI or a need to invent gd.stats.

Neither armor-enabled x221C_b4 nor armorHP x1834 is exposed by those readers.
The opaque immunity flag x221D_b6 used by ordinary collision admission is also
not exposed. Per-capsule states require gd.hurtboxes, not body_state alone.

ScriptGame_Hit currently only validates fighter/source existence before calling
the armor/damage helper. It does not check shield, invulnerability, intangible
state, or hitlag. EnemyStrike checks GuardOn..GuardReflect action IDs and victim
hitlag, but does not check x1988/x198C, x221D_b6, or capsule state before damage.
Normal item collision checks those states before armor mutation
(`ftcoll.c:1298-1313`, `2335-2339`). Thus fixing the armor boolean alone does not
prove immunity/shield parity.

For gameplay targeting, available player/hurtbox fields can reject shield and
known immunity states honestly. For an authoritative native gameplay strike,
perform chosen immunity/shield admission before the mutating helper, using the
native fields and enabled hurtbox policy. Keep that eligibility change explicit:
gd.hit is a synthetic damage-result API, not full hitbox collision. Do not
silently claim a body-state/action filter reproduces normal collision geometry,
shield damage, shieldstun, reflections, or hurtbox intersection.

## Focused native regression plan

Existing headless script_hit (`gw_script.c:8873-8896`) covers only missing
fighter, invalid damage and invalid source. ScriptGame_EnemyTest at2561 covers
scalar/lifecycle/contact guards and missing-target combat refusal. Neither
exercises a successful armor contact; a green existing suite cannot prove this
contract.

Add an asset-independent native test using a real initialized Fighter and actual
ftColl_80076640. To prove the scripting acceptance mapping, put that mapping in a
small shared gameworld helper used by both wrappers and test that real helper;
do not substitute a true-returning ftColl or entire wrapper. A tri-state local
result (refused before entry, absorbed, process damage) is optional; keep bridge
ABI/public boolean unchanged. The test must check:

- armor20, hit10: public acceptance true, armor10, armor flag retained, no change
  to x1838_percentTemp/x183C_applied/actual percent, no hit processor/event.
- armor10, hit10: acceptance true, armor0, armor flag retained; next hit5 breaks
  armor and queues spill5. Preserve strict zero-boundary behavior.
- armor5, hit10: acceptance true, armor flag cleared, pending damage5, and
  x183C_applied follows the helper's original-damage protocol.
- armor disabled, hit10: acceptance true and pending damage10; existing ordinary
  processing still runs once in a capable successful-hit fixture.
- missing/invalid source, invalid spec, out-of-range/facing/ownership/team
  refusal: false with byte-equal victim damage/armor fields; no event and no Lua
  spend. Test EnemyStrike's split guard to ensure the helper is not called early.
- chosen shield/invincible/intangible admission: false with unchanged armor and
  damage fields. Verify timed state and per-capsule/opaque native gating where
  claimed; otherwise explicitly leave that parity gate pending.
- the absorbed branch emits no fabricated collision callback; a subsequent real
  ordinary contact still delivers once and is not suppressed by a pending-count
  workaround. Preserve existing EnemyStrike reaction lineage on processed hits.

Then add a Lua runtime seam regression with the engine returning true for an
absorbed accepted action: charge is spent exactly once even though percent is
unchanged. This supplements the native test; it cannot replace it. Successful
fighter damage/KO and normal-speed watched shield/immunity behavior still need
the separately authorized native validation pass. No tests/build were executed
for this read-only audit.
