2026-10-04. Research note: Turbo Mode in Project M / Project+ and how to build it in the port.
Supersedes: nothing.

Labels used below: [FACT] read from a primary source (code or changelog) in this session; [WIKI] secondary
source, not checked against code; [READING] my interpretation of code I read; [INFERENCE] reasoning, untested;
[UNVERIFIED] could not reach a primary source (Smashboards returned HTTP 403 to the fetch tool).

## Plain answer (five lines)

1. Turbo is a status, not a move list: while a fighter has it, a connected hit (or shielded hit) lets the
   fighter cancel the attack's remaining frames into almost any other action. [WIKI + FACT]
2. The same attack cannot be cancelled into itself (spam guard), except moves made of several separate actions;
   Input Assist removes the guard. [WIKI] A hook on action-change enforces this. [FACT: Turbo.asm hook 3]
3. Implementation is three Gecko hooks in the Project M codeset: one runs each frame, sees "this fighter has
   hit something", sets a per-fighter "interrupt open" bit, then re-enables a few transitions (turn, crouch,
   walk) by hand; one clears the bit on the normal IASA path; one vetoes repeating the same action. [FACT code, READING of meaning]
4. It is enabled by Special Brawl "Turbo" (a rule) or by the Turbo item (a timed status, the old Superspicy Curry
   slot, reusing Brawl's Curry status and aura). [WIKI + FACT: the codes patch "Curry Special Brawl"]
5. In this port it is an "open the interrupt window on an event" feature: the read-only flag exists
   (`LAB_I_IASA`), the write does not; one small general engine capability plus modifier data gives turbo. [READING]

## Part 1: Project M / Project+

### Sources (primary first)

- [FACT] Turbo.asm, Project M codeset, 196 lines. Cloned to
  `_build/tmp/turbo-research/ProjectMCodes/GCTRM/Source/ProjectM/SpecialModes/Turbo.asm` from
  https://github.com/Fracture17/ProjectMCodes (file URL:
  https://github.com/Fracture17/ProjectMCodes/blob/master/GCTRM/Source/ProjectM/SpecialModes/Turbo.asm ;
  clone HEAD dated 2024-04-16). Header: "Turbo Mode - On Hit Interrupts v1.2 [Magus, Dantarion, standardtoaster,
  DukeItOut]". It is `.include`d from `GCTRM/Project+RSBE01.txt` line 688. The same file is vendored in many
  Project+ builds (for example https://github.com/KingJigglypuff/project-plus-ex , Build/P+Ex/Source/ProjectM/SpecialModes/Turbo.asm,
  last touched 2024-10-08), so the code is stable across P+ versions. I did not find a Project+ team repo with
  the source; their org (https://github.com/Project-Plus-Development-Team) holds the website, releases,
  Dolphin fork and GCTRealMate (the compiler for these .asm files) only.
- [FACT] P+ changelog JSON in https://github.com/Project-Plus-Development-Team/pplus-website , `app/changes/data/2.3.1.json`,
  section "Turbo Mode Adjustments" (see below), plus the same file's note that "Turbo status no longer has an
  unintentionally random chance of being removed when hit" (a variable conflict) and Turbo items "no longer
  eaten, use the equip animation", with a power-up sound.
- [FACT] Also touched by the codeset: `CustomAI.asm:341` "CPU falls from respawn plane when Turbo [Bero]" and
  `Events.asm:1` "Event Status3=Turbo [Bero]" (an Event Match that grants Turbo).
- [WIKI] SmashWiki, Project M page: https://www.ssbwiki.com/Project_M ; a Turbo page fetched through a search
  summary (rules below). EventHubs announcement, 2013-04-02:
  https://www.eventhubs.com/news/2013/apr/02/incredible-super-smash-bros-brawl-combos-project-ms-new-turbo-mode-every-attack-cancellable-another/
  (it was an April Fools reveal that became real; the team said "a few minor details" were left). Smashboards
  thread https://smashboards.com/threads/april-fools-turbo-mode-revealed.335378/ [UNVERIFIED: 403].
- [WIKI/UNVERIFIED] Melee: https://smashboards.com/threads/turbo-mode-replaces-single-button-mode-v1-3-20xx-4-07-compatible.449823/
  and https://smashboards.com/threads/melees-turbo-mode-gameshark-ar-code.434127/ (both 403; content below is from
  search-result summaries only).

### The rule

[WIKI] "Cancel any successful attack, upon hit or shield, into any other action except the same attack; all
aerial attacks auto-cancel when landing if they hit. Moves made of several actions (Farore's Wind) can cancel into themselves."
Visible indicator: faint purple flame on the fighter while turbo is on (regular Curry was red). [WIKI]

[FACT] 2.3.1 "Turbo Mode Adjustments" (verbatim list), the best statement of the real rules after 3.0:
- Only Jabs and Dash Attacks can dash cancel.
- Down, Up and Forward Smashes can no longer cancel into crouching, jumping or dashing, as these were bypassing
  the cancel limits and allowed smashes to be spammed into themselves.
- Rolls and Spot Dodges can be dash cancelled on frames 6-14.
- Grounded attacks can no longer cancel into Shield, but can still cancel into Rolls and Spot Dodges.
- Aerial attacks and specials can no longer cancel into Air Dodges.
- Landing a hit in the air restores mid-air jumps.
- Taunts can be cancelled using any mobility option.

What I can state from the code (Turbo.asm) [READING]:
- Scope: only the fighter-kind object (halfword 5 at struct+8 of a module; first hook exits otherwise) and not in
  statuses 0x3A and 0x3C (I believe damage/hit statuses; unverified).
- Trigger is "an attack of mine connected", read from a hit-state flag word (bit 0x400 of a word reached
  through `r3+0xCC` -> `+0x70` -> `+0x20` -> `+0x1C`). Whiffs never set it. Shield hits count per the wiki; the
  code does not distinguish, so presumably the shield path sets the same flag. [INFERENCE]
- State is two bits in a per-fighter word at `[[[[r3+0xCC]+0x70]+0x24]+0x1C]+4`: 0x01000000 = "turbo interrupt open"
  (set by hook 1, tested by hook 3) and 0x00800000 = guard that stops hook 1 re-firing while already set. Hook 1
  also clears 0x40000000 in word +0 when the status is 0x33.
- It does not touch damage, knockback, hitlag or hitstun: nothing in the 196 lines scales them. No damage penalty exists. [FACT by absence]
- Re-enabled transitions: after setting the bit it calls a transition-enable routine (0x807815C0) for three
  entries, ids 0x273E (turn, slow), 0x2743 (enter crouch), 0x274B (walk). The wiki's "any other action" works
  because the normal IASA tests already run once the window opens; these three are the ones the engine's normal
  gating would still have refused. [READING]
- Repeat guard (hook 3, 0x8077F184): vetoes an action change (`r0 = -1`) when the new action equals the current
  attack and the open bit is set, for action ids >= 0x24. Smash attacks (ids 0x2A-0x32) are special-cased in
  three groups (0x2A-0x2C side, 0x2D-0x2F, 0x30-0x32) so a smash's startup/charge/release sub-actions count as one
  move. A second block (current id 0x33, stick-quantised ids 0x62-0x66) handles a directional case;
  I could not decode what move 0x33 is without a symbol map. [READING; ID mapping UNVERIFIED]
- Clearing: hook 2 (0x8084B6EC), a hook in the routine that sets the "normal allow interrupt" word: every call
  that is not marker 0x2329 (the turbo call itself) clears 0x01000000. So the engine's own "IASA reached" /
  action-change processing ends the turbo window; the turbo call is the one thing exempt. [READING]
- Disabling Curry's own behaviour: three 4-byte patches (`04FAC8F0`, `04FAB728`, `04FABB88`) turn off Curry wait
  and run; `048434D4` makes the Curry Special Brawl use the Curry aura; `048377C8` stops it excluding Nana (Ice
  Climbers); `04843540` silences the Super Spicy Curry sound. [FACT] That shows Turbo piggybacks on the existing
  Curry status (a timed status whose Special Brawl "rule" gives it to every fighter permanently).

### How it is enabled

[WIKI] Special Brawl menu, "Turbo" (since Project M 3.0, replaced the Curry option); or the Turbo item
(replaced Superspicy Curry, gives the status for a duration). [FACT] 2.3.1 notes: equip animation and sound; P+
"Turbo item does not fire curry shots in any mode" (`Project+RSBE01.txt:518`, `half 0x4800 @ $8083A0A0`, a
branch over the fire-breath routine). Input Assist on removes the same-attack restriction. [WIKI]

### Design lessons

- The first version let smashes cancel into crouch/jump/dash and then back into themselves; 2.3.1 had to remove
  those exits. The guard has to be on the *outcome* (same attack twice), and every side door that reaches the
  same attack (via crouch, jump, dash) needs closing. [FACT]
- Shield-cancel and air-dodge-cancel were removed for grounded attacks and aerials/specials respectively; rolls
  and spot dodges kept. [FACT]
- Landing a hit restores air jumps (a deliberate buff so aerial chains continue). [FACT]
- Variable conflict made Turbo vanish when hit: status state must have its own storage. [FACT]
- Multi-action moves (Farore's Wind) are exempt from the repeat guard because the guard compares action ids. [WIKI + READING]
- Netplay/replay: not discussed in any source I could reach. The state is a per-fighter bit set deterministically
  from the hit result, so it would rollback fine if it lives in saved state. [INFERENCE]

### Related modes

- Melee, 20XX: **a Melee turbo code exists.** UnclePunch's "Turbo Mode Replaces Single Button Mode" (v1.3, 20XX
  4.07++ compatible; Gecko, USB loadable). [UNVERIFIED primary; summary from search] Hitting an opponent, a
  shield or anything with a hurtbox gives turbo for **40 frames**; any move can interrupt during that window,
  **including during hitlag**; cannot be spent on walking or crouching, nor on the move that granted it; v1.3 made
  non-reflectable projectiles (spacie side-B) grant it. A time-window design rather than P+'s "this attack
  connected" design. I could not read the code.
- Smash Ultimate: a "Turbo Mode" mod on GameBanana (https://gamebanana.com/mods/652581) cancels attacks into
  anything except some up specials; Project M-for-Ultimate/HDR also ship one (YouTube coverage only). [WIKI/UNVERIFIED]
- Rivals of Aether: I found nothing reliable about a comparable mode; not claimed.
- Project M's other special modes (same directory `SpecialModes/`): AllStarVs, BombRain, RandomElement, Stamina,
  Wild, Zero2Death. [FACT, file listing] Only Turbo alters move rules.

## Part 2: mapping to this project

Read: `CLAUDE.md`, `docs/TERMINOLOGY.md`, `docs/scripting.md`, the Envoy loot-and-modifiers spec, the catalogue,
and the game checkout `melee/src/melee/ft/` (game repo commit a4c05db88 at read time). No code was run.

### Where it hooks in Melee [READING of decompiled source]

- Melee's "IASA" is each action's **input callback**: `fp->input_cb` (`ft/types.h:1676`, fp+219C), invoked once
  a frame from the fighter input process at `ft/fighter.c:2712`, inside `if (!fp->x2219_b5)` (`:2709`), i.e.
  **not run during hitlag**. Each action state's `*_IASA` function is installed there (`fighter.c:1648`).
- The "interrupt window" is one bit, `fp->allow_interrupt` (`ft/types.h:1719`, fp+2218 bit0). It is set to true
  by the subaction command `ftAction_80071950` ("Allow interrupt", `ft/ftaction.c:520-524`), cleared on state
  entry (for example `ftCo_AttackAir.c:128`, `ftCo_Attack1.c:118`, `ftCo_AttackS4.c:207`).
- Each attack's IASA only opens its exits under that bit: aerials via the `DO_IASA` macro (`ftCo_AttackAir.c:146-154`:
  item/throw/special/jump-type checks), jab via `ftCo_Attack11_IASA` (`ftCo_Attack1.c:139-158`:
  smash/tilt inputs, then jump, dash, walk, turn). Note this means flipping the bit alone gives each move **its
  own** exit list (an aerial's IASA offers no jump or air dodge by default; a jab's offers jump/dash). Project M
  needed a custom transition list because its transitions are gated differently; Melee's per-state callbacks
  are the equivalent gate, and a "full cancel" needs a shared exit list. [INFERENCE]
- "An attack connected": the collision loop emits `Script_GameEvent(2 /*LAB_EV_HIT*/ ...)` at
  `ft/ftcoll.c:784` (fighter vs fighter hit; `inner_ret` true means it connected) and `ftcoll.c:1464` (item
  hits). Shield contacts surface as `on_shield_hit` (`melee/pc/platform/gw_script.c:7323`, documented at
  `docs/scripting.md:1826`). Per-hit context (`attacker_action`, `move_tag`) is on `on_hit`
  (`docs/scripting.md:1793`).
- Hitlag gate on the player side: `x2219_b5`; surfaced to scripts as `LAB_I_IN_HITLAG`
  (`melee/pc/gameworld/script_game.c:2074`).

### Can existing script capabilities express it?

- Readable already: the interrupt flag (`LAB_I_IASA`, `script_game.c:2077`, `script_lab.h:55`; Lua `player.iasa`,
  `gw_script.c:1290`), hit and shield events, `attacker_action`, move tags, hitlag state.
- **Not writable**: no script call sets `allow_interrupt` (grep over `melee/pc` finds only reads and Geno's own
  writes: `geno_game_v2.inc:430`, `geno_game_specials.inc:708`). `gd.fighter_caps` (`docs/scripting.md:2027`)
  can only *forbid* shield, air dodge, run, grab and specials, or set air jumps; it cannot open anything.
  So a scripted turbo cannot be done today. Also `on_hit` is an observer queued after the collision result
  and runs post-frame (`docs/scripting.md:1813`, `on_event` `delivery='post_frame'`), so a window opened from it
  takes effect one frame later; fine for a cancel, noted for timing.
- **The addition, as a general capability** [INFERENCE]: a timed, owned, rewind-safe "interrupt window"
  override, in the style of the 2026-10-04 fighter-caps pass:
  `gd.fighter_interrupt(entity, {frames=N, on="hit"|"shield"|"now", moves={...tags}, exits={"jump","dash","special",...}})`
  which (a) sets `allow_interrupt` for the owner's attacks while the window lives, and (b) widens the exit list to a
  shared set when the current action's own IASA would not offer it (call the common exits from a wrapper around
  `fp->input_cb` rather than editing each state), (c) honours the same ownership, snapshot (`script_game.c` BSS),
  `gd.sim_commit` op and release-on-teardown contract as `fighter_caps`. A second small piece is a **veto**:
  "do not allow action change into the action just left" (P+'s hook 3), a general `repeat_guard` field on the
  same call. Neither is turbo-specific: Reprisal-style "your next hit has extra hitstop" and "cancel your
  taunt" use the same window.
  Also expose hitlag behaviour: PM/20XX interrupt during hitlag; in Melee `input_cb` does not run in hitlag
  (`fighter.c:2709`), so a "cancel during hitlag" mode means invoking the IASA callback in the hitlag path, a
  second, optional flag.

### Turbo as data in the modifier system

Fits the section 3-4 vocabulary of `docs/superpowers/specs/2026-10-04-envoy-loot-and-modifiers-design.md`
(trigger, condition, effect; tags not names). Existing parts: trigger "on hit dealt" and "on shield hit", move
tags, `grounded/airborne`, "recently", self status, effects "change a fighter value for a duration", statuses,
`Momentum` stacks. New vocabulary needed: an effect `open_interrupt` (above) and condition `move_tag in {...}`
for the repeat guard (the spec's tags already cover it).

Sketches (not a final schema):

- Run-wide rule (Special-Brawl style, "turbo on"): `{trigger: on_hit_dealt | on_shield_hit, conditions: [move_tag != special_multi],
  effects: [open_interrupt{frames: until_action_end, exits: all, repeat_guard: same_action}, restore_air_jump if airborne]}`
  applied to every fighter at stage start (trigger `on stage start` installs it).
- Keystone, "Overdrive": your hits open the interrupt window; costs: `damage_dealt x0.8` (a stated cost per rule 4;
  any damage penalty is *new*, P+ has none), and cannot shield; exits limited to movement, no specials. This is the
  nearest thing to PM's list and uses only existing "multiply damage" and "cannot shield" (`fighter_caps.shield`) pieces.
- Drive modifier (small, stackable): "of the Cancel: on `jab` or `tilt` hit, your next action may cancel
  (window 10 frames)"; tier raises the window or adds `aerial`. Synergy: tags only, so Updraft ("on aerial hit, +1
  Momentum") plus a turbo-aerial drive chains.
- Opponent modifier: same record applied to the CPU entity, with a lower window; the CPU must be able to use the
  cancels, so an AI action selection check is needed (spec section 10 already asks the engine to confirm
  opponent hooks). A CPU that never inputs the cancel makes the modifier invisible. [INFERENCE]
- Visual: purple flame as a status marker per spec 8b (layered surface treatment); P+ used a purple aura.

### Risks specific to Melee [READING + INFERENCE]

- Existing early exits: jump-cancel (shine/up-smash out of shield are not IASA: `docs/geno.md:918`), L-cancel
  (halved landing lag from `gd.lab_common()` `lcancel_window`), jab chain and IASA frames. A global window could
  stack a hit-gated window on top of per-move IASAs; define it as "union, never earlier than hit confirm".
- Multi-hit moves: each hit emits `on_hit`; the window should open on the first connecting hit and be refreshed or
  ignored on later ones (use the `x2068_attackID` / `x206C_attack_instance` identifiers at `types.h:1625-1626`).
  Drill-style multi-hit (Falco/Fox drill, Link up-B) would cancel mid-multi-hit, which is the infinites case.
- Infinites: any jab / grab / dash attack chain with no repeat guard; up/down smash cancel spam; throws (Melee
  throws do not "hit" via the same event; `docs/scripting.md:1812`: direct throw percent routes do not currently emit `on_hit`)
  so grabs would not open turbo; that is a convenient exclusion.
- Hitlag: opening the window during hitlag (20XX style) changes frame data heavily; start with after-hitlag only.
- Shield hit: shield stun/hitlag differences; Melee has shield stun, Brawl P+ does not. Cancelling into shield
  after a shielded hit is a hard-to-balance exit; exclude it (P+ did).
- Rewind/offline: all state must sit in snapshotted BSS and use `sim_commit`, matching the spec's determinism rule.

### Sensible first rule set (from what Project M learned)

1. Open on a connecting attack hit (fighter-vs-fighter `inner_ret`) or shielded hit, from `jab`, `tilt`, `smash`,
   `aerial`, `dash_attack`, `special`; not on grabs/throws; items and projectiles optional (20XX v1.3 added them).
2. Window lasts until the current action ends; exits: walk, turn, jump (grounded), dash only from jab and dash
   attack, roll/spot dodge, any attack input, specials.
3. Smashes may not exit to crouch, jump or dash (PM 2.3.1); grounded attacks may not exit to shield; aerials and
   specials may not exit to air dodge.
4. Repeat guard: cannot cancel into the same action id; treat smash start/charge/release as one move; multi-state
   specials exempt.
5. A hit in the air restores air jumps (PM); consider capping at one per cancel.
6. No damage change in the base rule; the keystone version carries a damage cost.
7. Cap chain length (for example 4 cancels without the opponent being knocked out of hitstun) as a safety net;
   PM has no such cap in the code I read, so this is my addition.

### Test plan for a tester in the LAB (not run; agents do not drive the game here)

Use the LAB mode, ACE disc and fighters, a CPU set with `gd.cpu_mode(port,"stand")` (cpu0 is not idle),
probes using the debug fly cursor. Gate on an actual hit.
1. Whiff test: with the rule on, throw each of jab, ftilt, fsmash, nair, fair, special on empty air. Expect the
   normal frame data and **no** early cancel (read `player.iasa` in the LAB readout: stays false).
2. Hit test: same moves on a standing opponent. Expect the window opens on the first connecting frame; cancelled
   into a different attack input on the next logic frame after hitlag; hitlag/hitstun unchanged.
3. Shield test: hit a shielding opponent; expect window opens (if shield hits are in scope); cancel into roll,
   not into shield.
4. Repeat guard: hit with jab then jab; fsmash then fsmash (including via crouch/jump/dash); expect refusal and
   a log entry. Check Fox/Falco multi-action specials separately (Fox side-B, Falco up-B).
5. Multi-hit: Link or Fox multi-hit moves cancelled mid-sequence; confirm window refreshes without double-count.
6. Aerial landing: hit in the air, cancel to jump (air jump restored), then land with and without L-cancel;
   check landing lag against the baseline (`gd.lab_common`).
7. Infinite hunt: jab-cancel-jab-different-move loops on a heavy character at 0%, 60%, 120%; stop condition = victim leaves hitstun.
8. Rewind: use the LAB rewind (`gd.sim_commit` path): save before a cancel, restore, step, and confirm identical
   frames (compare with the existing `rewind-proof` pattern of `fighter-targeting`).
9. Keystone/opponent variants: confirm the CPU actually uses its cancels (log the action sequence).

## Gaps to close if this goes further

- Read Smashboards threads (403 here) for the 20XX Gecko code and any PM dev commentary on infinite fixes.
- A Brawl symbol map to name the hooked routines (0x807803A0, 0x8084B6EC, 0x8077F184, 0x807815C0,
  0x8084B6D8) with certainty; I describe them only by behaviour.
- Confirm the 40-frame/hitlag details of UnclePunch's code from the code itself, not search summaries.
