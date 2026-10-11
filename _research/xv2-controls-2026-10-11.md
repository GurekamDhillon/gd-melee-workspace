# XV2 controls: what Xenoverse 2's controller actually does, and what a Goku profile in Melee may take from it (2026-10-11)

Research only. No gameplay change. Owner brief (verbatim): "You're writing this in theory. How does XV2's
character controller/animations/state machine actually map to this. We need to do research back into that game
to find out what we are doing is grounded." Owner correction to the earlier Y/R/D-pad proposal: "always floating"
is **animation only**; gameplay keeps Melee's grounded/airborne rules (gimpable, no camping under the stage).

**Update, same day (follow-up dump): sections 7-12 at the end supersede sections 0 (the "missing CMN BCM" bullet), 1.3 (LinkFlags
paragraph), 1.4 (ki charge) and 6 where they disagree.** Short version: there is **no CMN BCM and no system BCM anywhere in the game's archives**
(all 1159 BCMs in the CPKs are `*_PLAYER.bcm`); the engine-level inputs are stated by the game's own help text, which I read. The true ki charge is
skill 591 "Energy Charge" (KTN), i.e. what the earlier section already suspected.

Every claim is tagged **SOURCE** (read from the decoded XV2 data in the shallow dump), **WEB** (cited), or
**INFERENCE** (mine; reasoned, not read). Numbers and ids below are structure, not assets; no XV2 asset data is
committed here.

## 0. What was read, and what is missing

* Data: `goku-base-shallow-v0.1` (`ports/goku-xv2/README.md` lists the path; parser Xv2CoreLib/XV2-Tools commit
  `59242676`, see `ports/ir/schema/engines/xv2.md`). Read directly from `decoded/chara/GOK/GOK_PLAYER.bcm.json`
  (28281 expanded nodes: 1 root, 39 root children, depth 17; **70 distinct BAC entries are ever targeted**),
  `GOK_PLAYER.bac.json` (142 entries), `chara/CMN/CMN.bac.json` (920), `GOK_PLAYER.bdm.json`/`CMN.bdm.json`, the
  seven skill folders' `*_PLAYER.bcm` + `.bac`, and `skills.json` (Goku's equipped skills). Clip names via
  `GOK.ean.json` / `CMN.ean.json`. Existing `_build/goku-xv2/movemap/movemap.json` (from `tools/movemap.py`) used for
  the BAC to clip chains; I re-derived the BCM edges myself.
* **Not in the dump (SOURCE, `raw/` listing): any CMN BCM.** Only `GOK_PLAYER.bcm` and the seven skill BCMs exist.
  So walking/running/hover movement, guard entry, boost start, lock-on, ascend/descend, and the real ki-charge
  input are **engine-driven or in a BCM we do not have**; the BCM below covers only *combat actions*.
* Static only. XV2 never ran (`engines/xv2.md`: "XV2 did not run successfully; there is no `observed` provenance").
  Timing is BAC frames at the 60 fps export convention (EAN `framesPerSecond` is null). Condition evaluation,
  precedence among simultaneously valid nodes, and hold-down semantics are **not executed anywhere**.
* Enum names are the parser's. Its source comments carry the physical buttons (WEB, XV2-Tools
  `Xv2CoreLib/BCM/BCM_File.cs`, https://github.com/LazyBone152/XV2-Tools): `Light=0x1 //Square`,
  `Heavy=0x2 //Triangle`, `Blast=0x4 //Circle`, `Jump=0x8 //X`, `SkillMenu=0x10 //R2`, `Boost=0x20 //L2`,
  `Guard=0x40 //L1`, `SuperSkill1..4=0x100..0x800`, `UltimateSkill1/2=0x1000/0x2000`, `AwokenSkill=0x4000`,
  `EvasiveSkill=0x8000`, `LockOn=0x100000`, `Descend=0x200000`, `DragonRadar`, `Jump_2=0x800000`.
  Condition flags: `ActivatorState` Idle/Attacking/Boosting/Guarding/ReceivingDamage/Jumping/NotReceivingDamage/
  TargetIsAttacking; `PrimaryActivatorConditions` Standing/Floating/TouchingGround/OnAttackHit/AttackBlocked/
  CloseToTarget/FarFromTarget/InBaseForm/InTransformedState/CounterMelee/CounterProjectile/KiBelow100/KiAboveZero/
  Ground/Opponent/OpponentKnockback/TargetingOpponent/StaminaAboveZero/NotNearStageCeiling/... The `UnkNN`
  flags (Unk9-12 on ActivatorState, Unk10/11 on conditions) are undecoded; some are used heavily (below).
  Web search for a full default button map of XV2 itself found nothing authoritative (see section 6); the
  GameSkinny control article (original Xenoverse, WEB, https://www.gameskinny.com/tips/dragon-ball-xenoverse-controls-how-to-vanish-and-throw/)
  gives Grab = Guard+Blast and Vanish = Guard+Jump on keyboard.

## 1. XV2's input model (BCM)

### 1.1 Shape of a BCM node (SOURCE)

Each node has: `ButtonInput` (mask), `DirectionalInput` (mask, e.g. Forward+SingleActivation, Backwards,
Left/RightRelative), `ActivatorState` (what the *user* is doing), `PrimaryActivatorConditions` (position/range/
hit-result conditions), `KiRequired`, `StaminaCost`, `HealthRequired`, `HoldDownConditions`,
`Minimum/MaximumLoopDuration`, `RandomFlag`, `OpponentSizeConditions`, `ReceiverLinkID`, `TransStage`, and **five BAC
slots**: `BacEntryPrimary`, `BacEntryAirborne`, `BacEntryCharge`, `BacEntryUserConnect`, `BacEntryVictimConnect`.
Children are the nodes tried *while the parent's BAC entry plays*; the BAC supplies the windows (section 2.2).
Cost fields in Goku's character BCM: StaminaCost 100 (vanish / dash-strike), 200 (vanish out of damage);
`KiRequired` is **0 everywhere in `GOK_PLAYER.bcm`** (ki costs live in the skill BCMs, below).

### 1.2 Character BCM, root level (39 children of node `0`) (SOURCE; read as rows of `GOK_PLAYER.bcm`)

| root node | input | user state / conditions | cost | BAC (clip chain) | means (INFERENCE unless noted) |
|---|---|---|---|---|---|
| 0/0, 0/1 | Blast+Guard (Idle); Blast alone while Guarding+TargetIsAttacking | | | 600 NAG_TSUKAMI; user-connect 601 (GNY_NAG_A, 201 f), victim-connect 602 (GNY_NAG_D, 157 f) | **Grab.** SOURCE: connect slots are the grab/throw pair. WEB: Grab = Guard+Blast (GameSkinny) |
| 0/2, 0/3 | Heavy+Guard (Idle); Heavy while Guarding+TargetIsAttacking | | 100 stamina | 476 BOOST_F_00 > ATC_008 (homing, hit f33) | homing dash strike, also a guard-cancel |
| 0/4-0/7 | Jump (X) with ActivatorState Unk9/Unk10/Unk11/Unk12 (Idle) | Idle | 0 | 700 / 710 / 713 / 716 (CMN.bac; clips BUKUU_F_S+STEP_F_S, STEP_B_S, STEP_L_S, STEP_R_S) with children 701-704 chosen by Standing/Floating+Opponent | takeoff/step in 4 directions; the four Unk states look like "direction of stick relative to target" (INFERENCE) |
| 0/8, 0/9 | Light+Forward / Heavy+Forward (SingleActivation) | Idle/Attacking | 0 | 460 ATC_001 / 461 ATC_006 (hit f8 / f20, Targeting Assistance) | forward-tilt style lunge strikes |
| 0/10 | Light+Jump | Idle/Attacking/Boosting, TargetingOpponent | 0 | 440 BOOST_F_00 > BOOST_F_01 x2 > BOOST_F_02 (148 f, **no hitbox**) | **Dragon-Dash-style approach** (no hit; INFERENCE on the community name) |
| 0/11, 0/12, 0/13 | Jump | Guarding+CloseToTarget / TargetIsAttacking+OpponentKnockback / ReceivingDamage+CloseToTarget | 100 / 100 / **200** stamina | 415 (STEP_B_S+BOOST_F_02) / 410 / 415, **BAC 410 has Invulnerability f2-18** | **Vanish** variants: backstep while guarding, evade an incoming hit, escape damage (costs more). Note the mask is `Jump` only; WEB says Guard+Jump on keyboard, so a Guard modifier is probably applied before BCM matching (OPEN) |
| 0/14 | Heavy+Blast | Idle/Attacking/Boosting/NotReceivingDamage | 0 | 419 BOOST_F_00 > STEP_F_S > ATC_013 (hit f40) | "Strong + Ki blast" = the **knockback attack** (WEB, GameSkinny beginner guide: strong+blast together performs a knockback attack). The repo already uses BAC 419 as Side B Dragon Rush (`PICKS.md`) |
| 0/15, 0/16 | Light+Backwards / Heavy+Backwards | Idle/Attacking/Guarding/TargetIsAttacking | 0 | 360 ATC_024 (2 hits, Invulnerability f12-18), charge variant 362 | backward-input strike that also works out of guard |
| 0/17-0/28 | Light | Idle, **FarFromTarget**, InTransformedState(?) | 0 | **725** (CMN) | approach when far; groups of 3: far -> 725, close -> **300**, any -> 300; the group is repeated 4 times with identical content (INFERENCE: one per transformation stage; `TransStage` prints 0 so not proven) |
| 0/29 | Light | Idle, no range condition | 0 | 435 BAS_STEP_F_S (lunge step) with the whole light tree below it | base-form entry into the same tree |
| 0/30-0/33 | Heavy | Idle, InTransformedState(?) | 0 | **496** ATC_026, charge variant 498 | transformed heavy |
| 0/34 | Heavy | Idle | 0 | **330** ATC_026, charge variant 332 | base-form strong opener |
| 0/35, 0/36 | Light / Heavy | **Jumping + NotReceivingDamage** | 0 | **370** ATC_020_S > BUKUU_DOWN, then 372 / **373** (BAS_JUMP_FRONT_02 landing, condition `TouchingGround, Ground`) | **the only air-attack-with-landing branch in the tree**: attack while "Jumping" and a landing child |
| 0/37, 0/38 | Light / Heavy | **Boosting** | 0 | 375 / 377 (ATC_022 / ATC_023, hit f6 / f10, Invulnerability f0-10/14) | dash attacks |

Evidence rows: node ids are the `id` field of `GOK_PLAYER.bcm.json` nodes; clips from `movemap.json`.

### 1.3 The combo trees (SOURCE; edges reduced from the 28281 nodes to 70 BAC entries)

Because the decoder expands link/loop references, the same subtree appears hundreds of times; reduced to unique
BAC-to-BAC edges the grammar is small. Condition column: `-` none; `hit` = OnAttackHit; `hit/blk` = OnAttackHit or
AttackBlocked. Every node also offers `Jump (CloseToTarget, 100 stamina) -> 410` ("vanish-step") and in many
nodes `Jump (OnAttackHit, 100) -> 411`; omitted below.

**Light string (all `Light` unless stated)**
`300 (ATC_002 hit f12)` -> L `301 (ATC_003)` -> L,hit/blk `302 (ATC_017)` -> L,hit/blk `303 (ATC_009)` -> L,hit/blk
`304 (ATC_022)` -> then Heavy,hit `310 (ATC_013, launcher-style)` -> Heavy,hit `311 (BOOST_F_00 > ATC_030, 117 f)` ->
Heavy,hit `312 (ATC_007 > ATC_017, 2 hits)` -> Heavy,hit `480 (ATC_015)`; Light after 304 -> `340`.

**Strong-after-light finishers.** From 300/301/302/303: **Heavy -> 320** (ATC_007, charge variant 322, chargeable:
`Charge Control` event f8-10, ChargeTime 30) -> Heavy,hit `325 (ATC_016)`. From 320/311/312: Light -> 340. 360
(back-input) feeds back into 301/340/320/335.

**Strong string.** `330 (ATC_026, chargeable)` -> H `335 (ATC_010)` -> H `336 (ATC_028, 5 hits rapid)` -> H,hit/blk
`337 (ATC_011)` -> H,hit `338 (ATC_005)`. **Light-side branch from 340**: `340 (ATC_027)` -> L,hit `341 (ATC_012)` ->
L,hit `342 (ATC_004)` -> L,hit `343 (BOOST_F_00 > ATC_006)`; `340` -H-> `350 (ATC_028)` -> L,hit `351 (ATC_029)` ->
H,hit `352 (ATC_030, 145 f)`. 341 -H-> 320. Both strings can cross (Heavy from many Light nodes, Light from many
Heavy nodes -> 340), i.e. the tree is "light/heavy alphabet over ~30 attack states" not two separate strings.

**Mechanics of chaining (SOURCE)**
* The BAC entry of the current attack carries `BCM Callback` events with a start frame, duration and `LinkFlags`
  bitmask; children are only matched inside such a window. Examples: 300 opens at f14 for 22 f (hit is f12-15);
  301 at f11 for 30 f; 320 has an early window f2-14 (flags bit 11) and the main window f18-50; 410 (vanish) opens f2.
  Hit/block-gated links (`OnAttackHit`, `AttackBlocked`) therefore only continue strings that connected.
* How `ReceiverLinkID` (1 attack, 2 forward/aerial strike, 5 grab, 7 vanish/step, 8, 9, 12) pairs with the bits of
  `LinkFlags` is **not decoded** (a first guess "bit = recv" does not hold: recv=1 light children sit in windows whose
  bits are 7-12). OPEN; what is certain is that windows exist and gate by time.
* Charge: strong openers 320/330/360 carry a `Charge Control` event; holding past ChargeTime switches to the node's
  `BacEntryCharge` (322/332/362/498/42...). So "hold heavy" is a charged strong. (Skills use the same slot, below.)

### 1.4 Skill BCMs: how supers/ultimates/evasives slot in (SOURCE)

Goku's preset (`skills.json` `selected`): super1 `KMH` (CUS 0, Kamehameha), super2 `KMB` (40, borrowed from GKG),
super3 `TYK` (123, borrowed from TSH; a "TSH_SPA_TYK" clip family), super4 `KTN` (591, from APL), ultimate1 `CKM`
(5000), evasive `KUR` (10001, ID2=1), blast `POW` (21080, ID2=1080). Each skill ships its own `*_PLAYER.bcm` whose
nodes use the **skill-slot virtual buttons**, not face buttons:

| skill | BCM input | ki / stamina | conditions | BAC slots (local to the skill folder) |
|---|---|---|---|---|
| KMH super1 | `SuperSkill1` | **KiRequired 100** | Standing or Floating; `OpponentKnockback` and `InTransformedState` variants | Standing: 30 / 10 / 40 / 0 (+ charge slot +2: 32 / 12 / 42 / 2); Floating: 35 / 15 / 45 / 5 (+2). Entries 12/17/42/47 start at clip f40 (charge-skip). A child (`Attacking`, no button) goes to BAC 50/20 |
| KMB super2 | `SuperSkill1` (slot-relative) | 0 | Idle/Attacking; `RandomFlag 2`; children by OnAttackHit / AttackBlocked | 0 -> 1 on hit / 2 on block (GKG_SPA_KMB_C 175 f; hits 2) |
| TYK super3 | `SuperSkill1` | 0 | Standing -> 0; Floating -> 5 | 66 f clip, Invulnerability f14-34 (Solar-Flare shape) |
| KTN super4 | `SuperSkill4` | 0 | Standing or Floating, **`KiBelow100`**, `HoldDown 0x20000` | 0 / 2 (APL_SPA_KTN_C, 140 f: Aura + 13 Effect + camera, no hitbox, `Time Scale`) |
| CKM ultimate1 | `UltimateSkill1` | 0 (menu-gated) | `OpponentKnockback` -> BAC 1 (airborne slot 1); else 0 | GOK_ULT_CKM_C, 225 f, Invulnerability type 5 f0-240, Camera f0-240 |
| KUR evasive | `EvasiveSkill` (+Forward variant) | **StaminaCost 299** | Idle/Attacking/**Guarding**/ReceivingDamage/TargetIsAttacking; Standing -> 0/1, Floating -> 5/6 | 146 f GOK_ESC_KUR_C (+_S), **Invulnerability f0-145**, Movement flags 128 and 20 (teleport) |
| POW blast | `Blast` (**no cost**) | | Idle/Attacking; `HoldDown 1 / 0x20001 / 0x30001`; loop 2 / 30 / 60-90 / 120-180 | BAC 0 (SHOT_N, projectile BSA 45, from hand R at f14), 1-4 (SHOT_F/B/L/R), 5-9 (looped volley), 11/12/13 = **CMN_BLT_POW_C charge pose, projectile BSA 46/47/48 at f40** (hold 30 / 60-90 / 120-180 frames), 15 = on-block variant |

Consequences (SOURCE unless tagged):
* Supers are **not** "R + face button" in the data: they are slot virtual buttons (`SuperSkill1-4`,
  `UltimateSkill1/2`, `EvasiveSkill`). Which physical input produces them (hold SkillMenu/R2 + face button in XV2,
  WEB-adjacent: the parser comments `SkillMenu //R2`, `SuperMenuPlusSkillInput`) is outside the BCM. INFERENCE:
  XV2's "R2 + face button" is the likely source of the proposal's "R + face buttons = supers"; the data supports
  the *slot* idea, not a specific Melee binding.
* **Ground and air are separate BAC entries of the same skill** (Standing vs Floating nodes). XV2 distinguishes them
  only to pick the right animation/trajectory; it does not forbid either.
* Charge variants exist for supers (`BacEntryCharge`): hold the skill button.
* The tap/hold ki blast is the **Blast skill** (POW), not the character BCM: tap = hands shot, hold longer =
  larger charged ball. `Blast` alone in the character BCM only appears as a grab modifier (0/1).
* **The repo's "ki charge = skill/BLT/1080_CMN_POW.bac 11" pick (PICKS.md row "Down B hold: ki charge") is a
  charged-ki-ball stance, not XV2's ki charge.** The nearest data to an actual Energy Charge is `KTN` (591): a
  no-cost `SuperSkill4`, only usable while `KiBelow100`, 140 f of Aura/Effect/Camera with no hitbox (INFERENCE).
  WEB (Twinfinite via search snippet; page itself 403): Energy Charge is a skill "triggered like a special attack but
  uses none of your resources". Where the in-fight "hold to charge" input lives in XV2 is not in this dump.

## 2. XV2's state machine

### 2.1 Layers (SOURCE structure, INFERENCE naming)

1. **Engine movement layer (no BCM routes at all).** Goku BAC entries 2-9, 14-38, 44-73 are never targeted by
   `GOK_PLAYER.bcm`; they are called by engine code by id (INFERENCE from `routes=0`, and from the same ids being
   overridden per character). Roles by clip: `0/1` stand (BAS_STAND / _S), `2` run, `3-6` hover-move F/B/L/R
   (BUKUU = XV2 word for floating), `7/8/9` boost start/sustain/brake (BOOST_F_00/01/02; 8 lasts 350 f), `14/16/18/20`
   step F/B/L/R (STEP_*_S, 38-39 f, each with 3-6 BCM Callback windows), `21/23` ascend/descend (BUKUU_UP/DOWN),
   `24-38` jump family (JUMP, JUMP_FRONT/BACK 00/01/02), `50-65` guard (GRD_KAMAE start 6 f hitbox event, loop 109 f,
   end 13 f; GRD_L/L_L/L_R = guard hit reactions), `66/67` guard break, `68-73` stun 00/01/02.
2. **BCM layer: combat actions** (section 1), selected by buttons + activator + position/range/hit conditions.
3. **Skill layer:** per-skill BCM/BAC namespaces (section 1.4), dispatched from the same input matching.
4. **CMN.bac layer (920 entries):** shared entries the character BAC may override by id. Ids 700-717 are the Idle+Jump
   step/hover family that GOK's BCM targets (clips `GOK_BAS_BUKUU_F_S`, `STEP_*`, `BOOST_F_*` via the Character scope);
   75-90 get-up/tech (UKEMI_N/F/B/U), 93-157 standing hit reactions in a regular grid (HEAD/BODY/LEG x L/H x
   F/B/L/R, `_S` = the floating-pose duplicate), 161-173 air/spin/up/wall-bound reactions, 194 KUZURE, 252 HAJIKI
   (deflect), 265-266 launched-up. BAC scopes `FaceBase/FaceForehead/CommonTail` are face/tail clips played in
   parallel (not body states).
5. **Reaction layer (BDM):** the attacker's Hitbox event names a `BdmEntryID` in `CMN.bdm` or the character's; the BDM entry
   carries `DamageType` (Standard / Heavy / Knockback2 / Knockback4 / LightStaminaBreak...), `StumbleType` flags
   (StumbleSet4/5/6, Unk8), `KnockbackDuration`, `KnockbackStrength X/Y/Z`, `PushbackStrength`, gravity/ground-impact
   times. Examples read: light chain hits use bdm 0/5/18/10 = Standard, StumbleSet4/5, KnockbackDuration 30, tiny
   knockback, pushback 0.2-0.5; the launcher 310 uses bdm 100 = Knockback4, duration 86, gravity 120; 419 uses
   bdm 74 = Knockback2, duration 110; bdm 43 (460) = LightStaminaBreak. So hitstun is **time-based per BDM entry**
   and the reaction pose is chosen from DamageType/StumbleType + hit region/direction (INFERENCE for the exact
   selection table, which lives in engine code).

### 2.2 Ground vs air (SOURCE)

* XV2 has **no ground/air split in the attack tree.** Most nodes have `BacEntryAirborne = -1` (same entry both
  ways); the vanish nodes set airborne = the same 410. Position conditions exist (`Standing`, `Floating`,
  `TouchingGround`, `Ground`) and are used in exactly: the 700-704 step family (Standing vs Floating pick 701/703
  vs 702/704), the skill BCMs (Standing vs Floating entry pairs, section 1.4), and the air-attack landing child
  (373, `TouchingGround, Ground`).
* "Ground" is therefore a **floor-contact condition on an otherwise airborne-capable body**. The `_S` clip
  family (BAS_STAND_S, GRD_*_S, STEP_*_S, CMN reactions `_S`) are the floating-pose duplicates of each state
  (owner's term in `REMAKE-PLAN.md`: flight-stance; SOURCE names, INFERENCE on the suffix).
* Movement states: STEP (stamina step, ~38 frames, in 4 directions) and BOOST (start 23 f, sustain up to 350 f,
  brake 19 f) are the dash/evade core. Vanish (410/411/415) = a short STEP + BOOST_F_02 with invulnerability, gated by
  100-200 stamina and range, usable *from within combos*.
* Hover/ascend/descend (BUKUU_UP/DOWN) are free movement states; XV2 has no ledge, no helpless fall, no
  platform. Nothing in the data limits air time other than stamina/ki.

### 2.3 Guard / step / stamina (SOURCE)

Guard is its own state family (50-65; BAC 50/54 start has a 6-frame Hitbox-typed event, which is probably the
perfect-guard/just-guard window, INFERENCE) with `Heavy+Guard` and `Blast+Guard` as guard-cancels (grab/dash strike);
`Jump` out of Guarding costs 100 (`0/11`). Stamina is spent by vanish (100/200), dash-strike (100), evasive skill
(299); `LightStaminaBreak` (BDM 43) and KUZURE (CMN 194, "exhausted") are stamina-out reactions. Ki is spent only
in skill BCMs (KMH 100) and gated (KiBelow100 on KTN).

## 3. Animation mapping: every owner-described clip

Owner descriptions are from `CLIP-NOTES.md`. "XV2 uses this for" is SOURCE: the BAC entries that play the clip
(read from the BAC events, not guessed); the role in the right column is INFERENCE from the entry's position in the
BCM/CMN layout.

| clip (owner's words) | XV2 plays it in | role |
|---|---|---|
| `xGOK_NAG_TSUKAMI` (lunges forward to grab from standing) | GOK 600 (Blast+Guard / Blast while guarding) | grab start; 601/602 are the connect pair |
| `xGNY_NAG_A` (unclear) | GOK 601 = BacEntryUserConnect of the grab, 201 f | **the grabber's animation after connect** (a borrowed clip: scope `GNY`) |
| `xGOK_ATC_SHOT_N_LOOP` (floating, firing ki blasts from the hands) | GOK 521 (also POW 5-9 loop families) | held-Blast volley loop (the repeating hand-shot) |
| `xCMN_BAS_HIRAMEKI` (charge-up: looks great) | CMN 40, 41 (`BAS_DOWN_AOMUKE, ITM/ITM_F, HIRAMEKI, DMG_HEAD...`) | item/skill pickup + "hirameki" (awakening spark) state; **not** the ki-charge stance |
| `xGOK_DEM_START` (idle/guard, unclear) | GOK 210 | demo/entry pose entry (DEM = demonstration) |
| `xCMN_BAS_DOWN_STAND_AOMUKE` (get-up) / `..UTSUBUSE` (get-up from knockdown/missed tech) | CMN 83 / 84 | wake-up from face-up / face-down |
| `xCMN_BAS_UKEMI_N` (one-arm push-up into fighting stance) / `_F` (aerial recovery into dragon dive) / `_B` (handspring/cartwheel) / `_U` (unclear) | CMN 85 / 86 / 87 / 90 | **ukemi = tech/recovery** set: neutral/forward/back/up |
| `xCMN_DMG_DOWN_BOUND_*` (unclear; lying face down, techable?) | CMN 74 / 75 / 76 / 77 | the **bounce on landing** after launch (AOMUKE face up / UTSUBUSE face down; `_H` heavy); the `BAS_UKEMI_U` pair in the same entries confirms techable (INFERENCE) |
| `xCMN_DMG_AIR_F`, `_AIR_F_L`, `xCMN_DMG_AIR_SPIN_L` | CMN 161, 195, 164 | air hit reactions (back, other pose, tumble head-down) |
| `xCMN_DMG_BLOW_H_B` (from behind: blasting back; throw candidate), `_BLOW_SPIN` | CMN 280, 170 | heavy blow reaction from behind / spin launch |
| `xCMN_DMG_DIVE_F` (maybe same as 14) | CMN 281 | dive-knockdown reaction |
| `xCMN_DMG_BODY_L_F` / `_H_F` (standing, takes damage / harder, stomach) | CMN 109 / 117, 234 | light / heavy standing body reaction |
| `xCMN_DMG_HEAD_L_F` / `_H_F` (standing / harder, head) | CMN 93, 175 / 101, 226 | standing head reactions |
| `xCMN_DMG_LEG_L_F` / `_H_F` (unclear) | CMN 125 / 133, 242 | standing leg reactions |
| `xCMN_DMG_YOROKE_BODY_F` (slightly launched, stumbles back), `_HEAD_F` (even harder), `_LEG_F` | CMN 149 / 141 / 157 | "yoroke" = stumble-back, the strong stagger (StumbleSet5/6 BDM hits) |
| `xCMN_DMG_UP_F` (knocked down onto back), `xCMN_DMG_UP_BODY_F` (launched up, about to transition into 14) | CMN 166 / 265, 266 | launched-up reaction and its tail |
| `xCMN_DMG_WALL_BOUND_B/F` (unclear) | CMN 173 / 171 | wall-bounce reactions |
| `xCMN_DMG_KUZURE` (lying exhausted; stamina-out candidate) | CMN 175?, 194 | **collapse**; CMN 175 shares the clip list with HEAD_L_F; 194 is KUZURE's entry. Consistent with the owner's stamina-out guess (BDM 43 is "LightStaminaBreak"; mapping of 194 to it is INFERENCE) |
| `xCMN_BAS_DOWN_AOMUKE_S` / `..UTSUBUSE_S` (unclear) | CMN 200, 222 / 201, 223 | floating-pose lying-down states (the `_S` duplicates) |
| `xCMN_BAS_HAJIKI_B_00` (unclear) | CMN 252 | deflect (HAJIKI) of an incoming projectile/attack |

CMN ids come from `CMN.bac.json` with only `Character`/`Common` scoped clips counted (the face/tail scopes are
separate parallel tracks and were excluded). The CMN entry-to-slot tables are not named by the data; names above are
by neighbouring clips.

Goku's own attack clips behind the strings (SOURCE, `movemap.json`): 300 plays `GOK_ATC_002`, 301 `ATC_003`, 302
`ATC_017`, 303 `ATC_009`, 304 `ATC_022`, 310 `ATC_013`, 311 `BOOST_F_00 > ATC_030`, 312 `ATC_007 > ATC_017`; strong:
320 `ATC_007`, 330 `ATC_026`, 335 `ATC_010`, 336 `ATC_028`, 337 `ATC_011`, 338 `ATC_005`; 340 `ATC_027`, 341 `ATC_012`,
342 `ATC_004`, 343 `BOOST_F_00 > ATC_006`, 350 `ATC_028`, 351 `ATC_029`, 352 `ATC_030`; back-input 360 `ATC_024`; air 370
`ATC_020_S`; dash 375 `ATC_022`, 377 `ATC_023`; 419 `BOOST_F_00 > STEP_F_S > ATC_013`; 476 `BOOST_F_00 > ATC_008`.
Note that the repo's earlier labels (`CLIP-NOTES` "candidate for" column) are the remake plan's picks, not XV2's use.
Examples where they differ: `xGOK_ATC_011`'s "Side B Dragon Rush" candidacy vs XV2's use as the third heavy hit (337);
`xGOK_ATC_008` as "Down B counter kick" candidacy vs XV2's 475/476 dash strike.

## 4. Mapping onto Melee, honestly

Melee facts used (repo, SOURCE): X and Y both jump; Z grab; L/R shield; A/B + C-stick smashes; D-pad taunts
(`gd.input_mask(port, bits)` can consume D-pad bits, `docs/scripting.md`); `ports/goku-xv2/PICKS.md` has the current
Goku: Neutral B Kamehameha (hold to charge), Side B Dragon Rush (BAC 419), Up B Instant Transmission (KUR), Down B
tap Z-vanish counter / hold ki charge, ki meter in the combo engine.

| XV2 mechanic | natural Melee equivalent | no equivalent / careful | Notes |
|---|---|---|---|
| Light (Square) 5-hit string with hit/block gating | A jab string with `OnAttackHit` gating (the combo lane already has L1-L5) | XV2 gates on contact; Melee jabs use frame windows | `combo/combo.json` routes exist; the XV2 tree is the source of the order |
| Heavy (Triangle) chains | Tilts / smashes (A-direction, C-stick) | XV2's heavy is a *string*; Melee smashes are single | Map heavy-branch ends to f-smash/launcher; strong-after-light finisher (320/325) = the "hit1 -> forward tilt/smash cancel" the lane may already do |
| Heavy+Blast knockback | Side B (BAC 419) | | grounded: repo uses it as Dragon Rush; fine |
| Blast tap (hand shot) / hold (charged ball) | Special with tap vs hold (like Kamehameha tap vs charge) or a non-B input | XV2 blast is free and spammable in the air | Needs ki/cooldown limits for fairness (INFERENCE) |
| Guard (L1) + step/vanish (Guard+Jump) | Shield, roll/spot-dodge/air-dodge | Melee has no stamina; XV2 vanish cancels strings and is invulnerable (410: f2-18) | Treat as a **bounded** cancel: ki- or meter-cost, not free |
| Boost (L2) / BOOST_F_00-02 dash + Dragon-Dash-like approach (Light+Jump) | Dash / run (grounded), or an air dash if designed | XV2 boost lasts 350 f; unlimited-air-time would break Melee's grounded/airborne rules | Keep to a Melee-style dash; no sustained flight |
| Skill slots (super1-4, ultimate) | B-moves (Neutral/Side/Up/Down) and one "super" input | XV2 has 4+2 slots + 1 evasive; Melee has 4 B directions | One slot per B direction is the natural fit; extra slots need new input |
| Ki charge | Hold Down-B or similar | the true XV2 input is not in the dump | Do not base fidelity claims on POW 11 (it's the charged blast) |
| Ground vs Floating (Standing/Floating node pairs) | Melee grounded vs airborne state | XV2 has no gimps; floating = infinite air | **Keep Melee's rules**: ground attacks only on floor, air attacks only airborne; "floating" is animation |
| Ascend / descend / lock-on | none | | must not exist as free movement (owner's rule); lock-on has no Melee analog (facing/target is automatic) |
| Hitstun by BDM time/StumbleType | Melee knockback formula | XV2 hitstun is per-hit data (30 f light, 86-110 f launcher) | Numbers are design values; do not import durations 1:1 |

**What a Goku control profile must NOT do** (given the owner's rule): no free ascend/descend or sustained
flight; no ground-state attacks used in the air or vice versa; no infinite boost/vanish (needs cost or limited
uses); no standing-on-nothing recovery that skips helpless/gimp states; no input that removes shield access (it
is the defensive tool of the game).

## 5. Three control schemes and a recommendation

**A. "Melee grammar, XV2 vocabulary" (no new buttons).** A/tilts/smashes map to Light/Heavy trees (the combo lane's
routes); Z grab (= XV2 Blast+Guard, coincidentally Melee's grab); Neutral B tap/hold = ki blast vs Kamehameha charge
(XV2's two projectile ladders); Side B = Dragon Rush (419); Up B = Instant Transmission (KUR); Down B tap/hold =
vanish counter / ki charge; vanish-cancel = shield + direction out of a string, ki cost. Everything already exists
or is a small script. Muscle memory: perfect for Melee players. Netplay: no new input surface (determinism easiest;
inputs unchanged). Fairness: Goku is a normal Melee fighter plus meter.

**B. Y = ki blast, D-pad for charge/transform/vanish (the earlier proposal).** Y is a jump button; remapping it
breaks a common tap/short-hop habit and costs the second jump binding (INFERENCE). D-pad is free to take via
`gd.input_mask`, but it removes taunts and sits under the thumb where players do not expect combat inputs. Netplay:
only controller bits are read, so determinism is fine as long as the script reads synced input (INFERENCE:
verify with a two-client run). Fairness: a dedicated spam-able projectile button is the biggest balance risk (XV2
ki blast is free); needs meter/cooldown. Fidelity to XV2: closer to "Blast = Circle" but XV2's Blast also needs its
cooldown/ki economy in its own game.

**C. XV2 skill-slot scheme: hold R (or L) + face button = supers.** Mirrors `SkillMenu(R2)+face button =
SuperSkill1-4`. It removes shield from those inputs (R/L is shield; L+A is a common tech/WD input), so it would
conflict with wavedash/shield-drop and L-cancel timing for any character that shares inputs; netplay still fine.
Fairness: gives Goku four supers always available; balance by ki cost. Highest fidelity to XV2, lowest to Melee.

**Recommendation: A, with two optional additions from B as opt-in settings, never defaults:** an alternative
"tap D-pad Down = vanish/ki charge" binding via `gd.input_mask`, and Blast as a tap/hold variant on Neutral B
rather than a new button. Reasons: (1) it is the only option the data directly supports end to end (the XV2 BCM has
Blast as a tap/hold *skill* and Vanish as a modifier, both fit B-move/shield-direction semantics); (2) it preserves
Melee's grounded/airborne rules by construction; (3) it keeps netplay determinism trivially (no new inputs).
Do not claim "R + face = supers" as XV2 fidelity: the data shows slot buttons, and the physical R2 menu is only a
parser comment.

## 6. Open questions for the owner

1. Is Y allowed to stop being a jump button for Goku (and the X/Y double-jump muscle memory)? Recommendation: no.
2. D-pad: acceptable to lose taunts for Goku? If yes, which: vanish, ki charge, transform?
3. Vanish out of a string: free (XV2) or costing ki/meter? Recommendation: costs meter.
4. Should the true ki-charge (not the POW charged-ball stance) use KTN's clip (`xAPL_SPA_KTN_C`)? This changes the
   "Down B hold" row in PICKS.md.
5. A follow-up dump is needed to answer: the CMN BCM / engine input table (walk, guard entry, boost start, lock-on,
   ascend/descend, real ki charge), `LinkFlags` vs `ReceiverLinkID`, `HoldDownConditions` bit meaning, and the
   reaction selection table. Want the exporter re-run with `chara/CMN/*.bcm` and the XV2 `system/` BCM files?
6. Full default button map of XV2 (PC/pad) was not retrievable from web search (Fandom 402, Twinfinite 403): is
   the owner's in-game controls screen the reference, or should I keep to the parser's Square/Triangle/Circle/X/L1/L2/R2?

---

# Follow-up (2026-10-11, later): the common/system BCM dump and what it settled

Owner approved dumping XV2's common/system BCMs and settling the open items. Tags as above. No data is committed:
the dumps live in `_build/xv2-cmn-bcm/` (git-ignored); only ids, names, counts and short structural quotes are here.

## 7. What was dumped, and the main finding

* **Pipeline (SOURCE).** `ports/goku-xv2/tools/build_source_ir.py` does not read the game itself: it reads the accepted shallow export
  `E:/Torrents/Dragon.Ball.Xenoverse.2.Future.Saga.Chapter.4-RUNE/modding/exports/goku-base-shallow-v0.1`, written by
  `.../exports/goku-base-shallow-v0.1/tools/Program.cs` (Xv2CoreLib/XV2-Tools commit `59242676`, built from `.../modding/src/XV2-Tools`),
  which opens the installed game (`E:/Games/DB Xenoverse 2`, 1.25.02.0) through `Xv2FileIO` and the CPKs `data*.cpk` / `data_d*_dlc.cpk`.
  There is no `.env` entry for it: the paths are in the script (`DEFAULT=`) and the modding README. I wrote a second small tool (scratch only; same
  `Xv2FileIO`, `BCM_File`, `BAC_File`, `MSG_File` loaders) that lists every CPK member (138880) and decodes every `*.bcm`.
* **There is no CMN BCM and no system BCM (SOURCE).** The CPKs hold 1159 `.bcm` files and every one is `<code>_player.bcm` under `chara/` or `skill/`.
  `data/chara/cmn/` has `CMN.bac`, `.bdm`, `.bai`, `.ean` and per-character `CMN.<code>.lby.bac` (lobby) but no `.bcm`; `data/system/` has 76 files, none a BCM
  (it has `special_action_table.sat`, `throw_action_branch.tab`, `aura_setting.aur`, `camera_action_effect.acm`; not decoded here).
  Across all 1159 BCMs the buttons `SkillMenu`, `Boost`, `LockOn`, `Descend`, `DragonRadar`, `Jump_2` and `Unk8` are **never used** (count 0), and the only guard
  chords are Guard, Blast+Guard, Heavy+Guard. So walk, run, boost, lock-on, ascend/descend and the skill menu are **engine code**, not data. This corrects
  section 0: there is no "CMN BCM we do not have".
* **Corpus (SOURCE).** 1159 BCMs plus their BACs (character `<c>_player.bac`; skills `<id>_<code>.bac`); 33429 unique condition-node signatures after
  de-duplicating the loop expansion. Statistics below are over this corpus unless a file is named.
* **The game's own help text (SOURCE).** `data/msg/*_en.msg` (540 English files read) holds the tutorial and quest help strings with placeholders
  `[BTN_1..4]`, `[L1]`, `[L2]`, `[R1]`, `[R2]`, `[R3]`, `[L3]`, `[LS_N]`. This is the best evidence for the engine-level inputs. Quotes below are single short
  phrases. The placeholder legend follows from the BCM and every line agrees with the node it describes: `BTN_1` = Jump (X), `BTN_2` = Blast (Circle),
  `BTN_3` = Light (Square), `BTN_4` = Heavy (Triangle) (Heavy+Blast "knockback attack" = Goku node 0/14; Light+Jump "Aura Burst Dash" = 0/10; L1+BTN_2 "throw" = 0/0;
  tilt forward + Light/Heavy "Heavy Smash" = 0/8, 0/9; tilt back + Light/Heavy "attack from behind" = 0/15, 0/16).

## 8. The engine-level controls, from the game's help text (SOURCE unless tagged)

| control | XV2 input (the game's wording) | note |
|---|---|---|
| move | `[LS_N]` | |
| Boost Dash | "Hold [L2] and use [LS_N]" | costs stamina ("Stamina is used when Boost Dashing with [L2] or performing a Z-Vanish") |
| Step | "press [L2] while using [LS_N]" or "use [LS_N] while holding [L2]" | STEP_F/B/L/R, BAC 14/16/18/20 |
| Jump | "While on the ground, press [BTN_1]" | |
| Ascend / Descend | "Press and hold [BTN_1] to Ascend", "[L3] to Descend" | BUKUU_UP / BUKUU_DOWN, BAC 21 / 23 |
| Lock on / change target | `[R1]` / `[RS_N]` | |
| Ki blast | tap `[BTN_2]` (rapid taps = quick fire); hold, then release = charged blast | the Blast skill (POW), not the character BCM |
| Dash attack | "While Boost Dashing, press [BTN_3] or [BTN_4]" | Goku 0/37, 0/38 (`Boosting`) |
| Aura Burst Dash | `[BTN_3]` + `[BTN_1]`; `[BTN_1]` again circles behind (1 stamina) | Goku 0/10 (Light+Jump), BAC 440 |
| Charged attack | hold `[BTN_4]` (breaks guard) | the `BacEntryCharge` slot (320/330/360) |
| Heavy Smash | tilt `[LS_N]` forward + `[BTN_3]`/`[BTN_4]` (guard break) | 0/8, 0/9 |
| Back attack | tilt back + `[BTN_3]`/`[BTN_4]` (chargeable, works while guarding) | 0/15, 0/16; ReceiverLinkID 9 |
| Knockback attack | `[BTN_4]` + `[BTN_2]` (any time in a combo) | 0/14, BAC 419 |
| Guard / Just Guard | `[L1]`; guarding right before a hit connects restores 1 ki bar and, vs melee, drains 1 stamina bar | |
| Throw | `[L1]` + `[BTN_2]` | 0/0 |
| Z-Vanish | `[BTN_1]` "while attacking or when a foe has been knocked back"; 1 bar of stamina attacking or guarding, **2 bars while staggered** | 0/11-0/13 (100, 100, 200); BAC 410/411/415 |
| Vanishing Step | `[BTN_1]` **during a Step**; invulnerable; `[BTN_3]`/`[BTN_4]` attacks out of it | Jump + ActivatorState Unk9-12 nodes, section 9.3 |
| Super Attack | `[R2]` + an assigned button | skill slot |
| Ultimate Attack | `[R2]` + `[L2]` + `[BTN_3]` or `[BTN_4]` (the GGP variant says `[L2]` alone) | `UltimateMenuPlusSkillInput` |
| Evasive Skill | `[R2]` + `[L2]` + `[BTN_1]` | |
| Awoken Skill | hold `[L2]` + `[R2]`, then `[BTN_2]` | |
| Limit Burst | hold `[R3]` | not a BCM input |
| Items / search / radar | `[BTN_R]` / `[BTN_L]` / `[R3]` | no combat relevance |

So "R2 + face button = supers" is the real XV2 input (confirmed), but the earlier recommendation stands: do not claim it as Melee fidelity.

## 9. The open items

### 9.1 LinkFlags vs ReceiverLinkID (SOURCE statistics; mapping is INFERENCE)

Parser (SOURCE, `BAC_File.cs` `BcmCallbackFlagsEnum`): LinkFlags are *named categories*, not bit indices: Attacks 0x1, Movement 0x2, DisableKiBlastLink 0x4,
Counters 0x10, BackHits 0x80, Combos 0x100, Supers 0x200, UltimatesAndEvasives 0x400, ZVanish 0x800, KiBlasts 0x1000, Jump 0x2000, Guard 0x4000,
FlyingAndStepDash 0x8000. A `BCM Callback` event opens a *window* (start frame + duration) in which the listed categories may be received. The child node's
`ReceiverLinkID` is its **category class**. Joint distribution over the corpus:

* class 1: Light/Heavy chain nodes (4833 + 4167) and auto-links; class 7: Jump with a stamina cost = **Z-Vanish** (6579 of 7184 nodes); class 9: Light/Heavy with
  Backwards (751 + 751 of 1547); class 5: Blast (6); class 8: Blast, Blast+Guard, Heavy hand-offs; classes 2/3/4: skill and evasive hand-offs (SkillInput `0x10000`, `0x20000`, Heavy+Guard).
* Fraction of parent entries (per file, deduplicated) whose windows carry a flag, by child class: class 1 -> **Combos 99%**; class 2 -> **Supers 96%**; class 3 -> UltimatesAndEvasives 94%;
  class 4 -> **UltimatesAndEvasives 98%**; class 5 -> Combos 100% (6 edges); class 7 -> **ZVanish 89%** (Supers 94%); class 8 -> **KiBlasts 80%**; class 9 -> **no single flag**
  (Supers 79%, BackHits only 7%); class 11 -> UltimatesAndEvasives 70%. Light and Heavy children are Combos-gated in **100%** of the edges whose parent has any window.
* Reading: classes 1, 2, 3/4, 7, 8 line up with the consecutive flags 0x100, 0x200, 0x400, 0x800, 0x1000, so the engine almost certainly accepts a child only if a *currently
  open* window carries the flag of its class. That makes the earlier doc's "windows gate by time" concrete. **Not settled:** classes 9 and 11; the 11% of Z-Vanish edges whose parent has no ZVanish flag
  (most of these parents have **no windows at all**: 617 Light and 574 Heavy edges, 29 vanish edges); and the statistic uses the *union* of a parent's windows, not the flag at the frame. A time-aligned test needs the engine.

### 9.2 HoldDownConditions (SOURCE counts, INFERENCE reading)

Values: 0 (32515 nodes), `0x4` (382), `0x1` (222), `0x20000` (143), `0x20001` (91), `0x30001` (33), `0x60000` (22), `0x20002` (14), `0x2` (4), `0x3` (2), `0x30000` (1). Non-zero values occur only in skill BCMs.

* **bit 0 (0x1)**: 348 nodes, 210 on Blast, 90 on SkillInput, 221 with `MinimumLoopDuration > 0`: "button must be held; repeat while held" (the POW volley loop; Goku's POW `HoldDown 1`, loops 2 / 30 / 60-90).
* **bit 17 (0x20000)**: 304 nodes (Blast 114, UltimateSkill1 48, SuperSkill1 24); present on **skill 591 Energy Charge**, whose text is "Hold the button down to charge Ki!": a hold-to-channel requirement.
* **bit 16 (0x10000)**: 34 nodes, all Blast, always with bit 17 (0x30000/0x30001): a second charge tier of the held blast.
* **bit 18 (0x40000)**: 22 nodes, 20 with button 0 and a loop duration (auto-continue tier, e.g. 0x60000).
* **bit 2 (0x4)**: 382 nodes, 316 on SkillInput, 48 on `0x20000`, 16 on Heavy+Guard (0x42); never with a loop or charge slot. INFERENCE only: "held together with a modifier".
* **bit 1 (0x2)**: 20 nodes; no stable reading.

Settled for the purpose here: hold-to-charge is a BCM property of skill nodes (bits 0/17) and the ki-charge skill uses bit 17. Bits 1, 2, 16, 18 keep INFERENCE labels.

### 9.3 ActivatorState Unk9-12 and the unknown condition bits (SOURCE counts, INFERENCE meaning, high confidence)

* **ActivatorState `0x100 / 0x200 / 0x400 / 0x800` (Unk9-12) appear only on `Jump` nodes**, once each in 148 of the 1159 BCMs (identical content), with BAC entries
  **700 / 710 / 713 / 716** (common namespace), DirectionalInput 0xC00, class 7, StaminaCost 0. The clips (Goku's EAN) are `BUKUU_F_S + STEP_F_S` (700), `STEP_B_S` (710), `STEP_L_S` (713),
  `STEP_R_S` (716); children 701-704 are `BOOST_F_02` pairs.
* The game's text: "Press [BTN_1] during a Step ... to perform a Vanishing Step", invulnerable, "attack from a Vanishing Step with [BTN_3] or [BTN_4]". **Conclusion:** Unk9 / 10 / 11 / 12 =
  **currently stepping Forward / Back / Left / Right** (the STEP states, BAC 14/16/18/20). Jump in that state = **Vanishing Step**. The earlier "takeoff/step in 4 directions" is corrected.
  Likewise `Light` with `ActivatorState Idle|Unk9` (0x101) -> BAC 725 (146 nodes): the attack out of a forward step; Goku's far-approach Light is 725 (`BUKUU_F_S + STEP_F_S`).
* `ActivatorState Unk13 (0x1000)` + Jump -> BAC 501, in 8 characters only: character-specific, unknown.
* `PrimaryActivatorConditions Unk11 (0x400)` co-occurs with `Idle (0x800)` in **11623 of 11623** nodes: read `0xC00` as one base predicate. `Unk10 (0x200)` occurs only on Blast nodes (112; 102 in skills).
  `Unk17/18/22/24` are skill-only and rare (50 / 6 / 8 / 4). Meaning unknown.

### 9.4 Which CMN entries the engine picks per reaction (BDM) (data SOURCE; the table is WEB-grade)

* A BDM entry has up to 10 sub-entries chosen by the **victim's state** (the parser's own comment, `BDM_File.cs`): 0 default struck, 1 struck while using a skill, 2 floating hit animation,
  3 struck in back, 4 rolling hit animation, 5 guarding or just guarding, 6 standard hit animation, 7 unknown, 8 heavy stun animation, 9 lying on ground.
* Which **animation entry** plays is not in the BDM; it is engine code. The XenoKit author's reimplementation is `XenoKit/Engine/Character/DamageManager.cs` (same author as the parser, with TODOs, so WEB-grade):

| DamageType | CMN BAC entry | notes |
|---|---|---|
| Block | 60 stand, 61 air, 62/63 left, 64/65 right | the GRD_L family |
| GuardBreak | 66 (67 air) | |
| Standard | stumble base + `dir*2 + air` | dir 0 front, 1 back, 2 left, 3 right from the hit vector; +1 if the victim is airborne |
| Heavy | heavy base 141 / 149 / 157 (+ same offset; 157 front/back only) | |
| Knockback | 265 (back 267), fall 266 (268), impact 74 | |
| Knockback1 | 265 / 267 then 270 / 272 | |
| Knockback2 | 168 / 169, recovery 91 / 92 | |
| Knockback3 | 273 / 275, fall 274 / 276, impact 75 / 76 | |
| Knockback4 | 170, fall 266, impact 80 | |
| HoldStomach / HoldEyes / Dazed | 175 / 176 (air 177) / 183 | |

  Stumble bases: 93 (head L), 101 (head H), 109 (body L), 117 (body H), 125 (leg L), 133 (leg H), and 226 / 234 / 242 (a second set). The StumbleSet flag chooses three of them: Set1 {109,117,226},
  Set2 {93,101,226}, Set3 {125,133,242}, **Set4 {93,109,125}** (all "L"), **Set5 {101,117,133}** (all "H"), Set6 {226,234,242}; one is picked at random per hit (`AllStumbleSets` or no flag = any of nine).
  Goku's light string BDMs (StumbleSet4/5) therefore give the L/H head/body/leg stumbles: the same CMN entries as the clip rows in section 3 (93/109/125 and 101/117/133). The launcher (BDM 100,
  Knockback4) gives CMN 170, 266, 80 and BDM 74 (Knockback2) gives 168/169, also matching section 3.
* **Unknown:** hit region (head vs body vs leg) does not enter this table: XenoKit picks at random within the set, so XV2 either randomises or uses engine code that XenoKit did not model.
  Electric, Freeze, Paralysis, Brainwash, Wildcard and Knockback5-9 are not modelled there either.

### 9.5 The true in-fight ki-charge input (SOURCE, settled)

* There is **no always-available ki-charge button**. "Energy Charge" is a **skill, CUS 591** (`APL_SPA_KTN`, "Where to Get: Advancement Test Quest 1"; description "Hold the button down to charge Ki!").
  It is equipped in a Super slot and used like a super: **R2 + the slot's button**, then **hold** (BCM HoldDown `0x20000`, on `SuperSkill4` in the file I read).
* Its BCM: two nodes, Standing (`0x4c01` = Standing + base + KiBelow100) -> BAC 0 and Floating (`0x4c02`) -> BAC 2; ActivatorState Idle|Attacking; StaminaCost 0, KiRequired 0; usable only while ki < 100.
  BAC callback window f110-139, flags 0xC002 (Movement + Guard + FlyingAndStepDash).
* A second route exists only in the Ultra-Instinct awoken state: "While guarding, press [BTN_4] to charge Ki".
* Other ways ki fills (QUE_TUT_221_1): dealing or taking damage from normal attacks, items, charge moves, a successful Just Guard.
* Consequence: `PICKS.md`'s "Down B hold: ki charge = POW 11" is the charged blast, as section 1.4 said; the faithful clip is KTN's (`xAPL_SPA_KTN_C`, 140 f). By the owner's decision (section 12) the clip stays XV2's.

## 10. Corrections to earlier sections

* 0/10 (Light+Jump) is the **Aura Burst Dash** (game text), not a guessed "Dragon-Dash-style" move.
* 0/14 (Heavy+Blast, BAC 419) is the **knockback attack**, confirmed.
* 0/4-0/7 are the **Vanishing Step** nodes (9.3), not takeoff/step.
* Section 1.3: "how ReceiverLinkID pairs with LinkFlags is not decoded" -> see 9.1.
* Section 2.1: BAC 60-65 are the block-reaction entries (agrees with XenoKit's `BAC_BLOCK_*`), 66 / 67 the guard-break pair.
* Walk: `GOK_BAS_WALK` exists as an EAN clip but **no Character-scope BAC entry in `GOK_PLAYER.bac` plays it**; BAC 2 plays `GOK_BAS_RUN`. INFERENCE: walk is driven by engine code or a scope not exported.

## 11. Per-button table, Scheme A (Melee buttons only)

Columns: XV2 input (the game's help text / the BCM), the XV2 action and its BAC entries, the clip(s) (`GOK_` prefix dropped; SOURCE: Goku's BAC and EAN), and the **proposed** Melee input
(INFERENCE; the owner decides). "Jump button" is the per-player setting (X, Y or both) from section 12. D-pad and new inputs are not used. Ground moves stay on the ground and air moves in the air;
"floating" stays animation only.

| XV2 button / combination | XV2 action (BAC) | clip(s) | proposed Melee input (Scheme A) |
|---|---|---|---|
| Light (BTN_3) | light string 300-304 (hit/block-gated), then the 340 branch | ATC_002, 003, 017, 009, 022 | **A**: jab string, chained on hit like the combo lane's L1-L5 |
| Light, far from target | 725: approach step, then 300 | BUKUU_F_S + STEP_F_S | **A while running** (dash attack): closest Melee shape |
| Heavy (BTN_4), tap | strong opener 330 (chargeable), strings 335-338 | ATC_026, 010, 028, 011, 005 | **A + stick** tilts as string starters (PICKS' tilt rows) |
| Heavy, hold | charge variants 322 / 332 / 362 (Charge Control, ChargeTime 30) | same clips, charge pose | **smash hold** (C-stick / A-smash): the "charged attack" |
| Light/Heavy + forward (Heavy Smash) | 460 / 461, guard break | ATC_001, ATC_006 | **forward smash** (C-stick forward) |
| Light/Heavy + back | 360, invulnerable f12-18; works out of guard; charge 362 | ATC_024 | **back-direction A**: grounded turnaround tilt, **bair** in the air (PICKS' bair is 335); keep the invulnerable window |
| Heavy + Blast (knockback attack) | 419 | BOOST_F_00 > STEP_F_S > ATC_013 | **Side B** (Dragon Rush), already the pick |
| Light + Jump (Aura Burst Dash) | 440, no hitbox; Jump again circles behind | BOOST_F_00 > 01 x2 > 02 | **not mapped**: Melee run/dash is the equivalent; no A+jump chord in Scheme A. The clips can serve dash-start visuals |
| Boost (L2) + stick | Boost Dash: start 7, sustain 8, brake 9 | BOOST_F_00 / 01 / 02 | **run / dash** (stick); no sustained flight |
| Dash + Light/Heavy | dash attacks 375 / 377 (invulnerable f0-10 / 0-14) | ATC_022, ATC_023 | **A while running** (PICKS' dash attack is 337; 375/377 are the data-faithful pair) |
| Boost tap + stick (Step) | STEP F/B/L/R (14/16/18/20, ~38 f, stamina) | STEP_F_S, _B_S, _L_S, _R_S | **roll / spot dodge** (shield + stick) and **air dodge**, with the step clips |
| Jump (BTN_1), grounded | jump family 24-38 | JUMP, JUMP_FRONT_00-02, JUMP_BACK_00-02 | **jump button** (per-player X / Y / both) |
| Jump held in air (Ascend) / L3 (Descend) | BUKUU_UP / BUKUU_DOWN (21 / 23) | BUKUU_UP, BUKUU_DOWN | **no free ascend**; BUKUU_DOWN may be the **fast-fall** pose (animation only) |
| Jump during attack / on hit (Z-Vanish) | 410 / 411 (invulnerable f2-18), 100 stamina | STEP_B_S + BOOST_F_02 | **jump button inside a hit-confirmed string window; costs meter** (owner decision). Melee cannot jump out of a string anyway, so no conflict |
| Jump while guarding (close / attacked) | 410 / 415, 100 stamina | same | **Down B tap** (Z-vanish counter, existing PICKS row); not "jump out of shield", which Melee uses for jumping |
| Jump while hit (out of hitstun) | 415, 200 stamina | same | **not mapped** at launch; if wanted, Down B tap with double meter (design) |
| Jump during a Step (Vanishing Step) | 700 / 710 / 713 / 716; attack out of it 701-704 | STEP_F/B/L/R_S, BOOST_F_02 | **jump button during the roll/dodge**, meter cost; A afterwards = the 701-704 attack. Only if the meter budget allows |
| Guard (L1) | guard 50-59, hit reactions 60-65, break 66 / 67 | GRD_KAMAE, GRD_L, GRD_L_L, GRD_L_R, GRD_BREAK | **L / R shield**; Just Guard (L1 right before the hit) = **perfect-shield timing that restores meter** |
| Guard + Blast (throw) | grab 600; connect 601 (user) / 602 (victim) | NAG_TSUKAMI, GNY_NAG_A, GNY_NAG_D | **Z** (or shield + A) |
| Guard + Heavy (homing strike, also a guard-cancel) | 476, 100 stamina | BOOST_F_00 > ATC_008 | **unmapped** (shield + A is already grab in Melee); candidate: Side B from shield. Owner choice |
| Blast (BTN_2), tap | ki blast (POW 0; F/B/L/R 1-4) | ATC_SHOT_N, SHOT_F/B/L/R | **Neutral B tap** (needs a meter or cooldown limit; in XV2 it is free) |
| Blast, hold | charged blast (POW 11-13 pose, 5-9 loop) | CMN_BLT_POW_C, ATC_SHOT_N_LOOP | **Neutral B hold** turns into the Kamehameha charge (PICKS) |
| R2 + assigned button (Super 1-4) | skill slots: KMH, KMB, TYK, KTN | SPA_KMH, ... | **B moves**: Neutral B = KMH, the rest per PICKS |
| R2 + L2 + Light/Heavy (Ultimate) | CKM (225 f, invulnerable) | ULT_CKM_C | **Neutral B at full meter + full charge** (PICKS' Super Kamehameha) |
| R2 + L2 + Jump (Evasive) | KUR, 299 stamina, invulnerable f0-145 | ESC_KUR_C | **Up B** (Instant Transmission), already the pick |
| R2 + L2 + Blast (Awoken) | skill-specific | n/a for base Goku | **not mapped** (transformation is a later question) |
| hold the Super-slot button of Energy Charge (skill 591) | ki charge, only while ki < 100; BAC 0 standing / 2 floating | APL_SPA_KTN_C | **Down B hold**, clip stays KTN's (owner decision) |
| Lock-on R1 / target change RS_N | engine | none | none: facing/targeting is automatic in Melee |
| Items / search / radar / Limit Burst | engine | none | none |
| Reaction side (not an input) | Standard / Heavy / Knockback* via BDM | CMN 93-157, 168-170, 265-276 | pick the CMN clip by DamageType per 9.4 where the reaction row exists |

"Not mapped" rows are deliberate: Scheme A has no free Melee input for them without breaking a Melee rule.

## 12. Owner decisions recorded (2026-10-11)

1. **The jump button is a per-player setting** (X, Y or both) **for every fighter**, not a Goku exception. Goku's jump and jump-based vanish inputs use whichever the player chose.
2. **Extras (D-pad and similar) are opt-in only**, never a default. Scheme A uses none.
3. **Vanish out of a string costs meter** (XV2: 1 stamina bar attacking or guarding, 2 while staggered; this is the Melee-side meter equivalent).
4. **Stay faithful to XV2's data**: no swapping the ki-charge clip by taste. The clip is KTN's (`xAPL_SPA_KTN_C`); `PICKS.md`'s "Down B hold" row (POW 11) is superseded in intent. No repo change is made here.

## 13. What is settled and what is not

**Settled (SOURCE):** no CMN/system BCM exists; the engine-level inputs (section 8) from the game's own text; ki charge = skill 591 "Energy Charge", hold the Super-slot button; Unk9-12 = step-direction
states and Jump there = Vanishing Step; Light/Heavy, Z-Vanish, Super, Ultimate and ki-blast links are gated by named LinkFlags windows; Z-Vanish costs 1 bar attacking/guarding, 2 staggered; BDM sub-entries are
victim-state variants; the CMN entry per DamageType and StumbleSet (WEB-grade).

**Not settled:** link classes 9 and 11 and the time-aligned window semantics (needs a run); HoldDown bits 1, 2, 16, 18 beyond 9.2; PrimaryActivatorConditions Unk10/17/18/22/24 and ActivatorState Unk13; the hit-region
choice in reactions; walk's driver; precedence between simultaneously valid nodes; whether XV2's Just Guard window is the 6-frame Hitbox event on BAC 50/54 (INFERENCE); the physical PC key defaults (the help text is in pad terms).
