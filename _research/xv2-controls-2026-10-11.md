# XV2 controls: what Xenoverse 2's controller actually does, and what a Goku profile in Melee may take from it (2026-10-11)

Research only. No gameplay change. Owner brief (verbatim): "You're writing this in theory. How does XV2's
character controller/animations/state machine actually map to this. We need to do research back into that game
to find out what we are doing is grounded." Owner correction to the earlier Y/R/D-pad proposal: "always floating"
is **animation only**; gameplay keeps Melee's grounded/airborne rules (gimpable, no camping under the stage).

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
