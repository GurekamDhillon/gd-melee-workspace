# Meta Knight (vanilla Brawl) into GD's Melee: port plan

Source of every number below: `metaknight.brawl.ir.json` (built by `tools/build_metaknight_brawl.py`).
Scope follows geno.md section 1: character-level only. Brawl's global rules (tripping, air dodge, hitstun
cancelling, ledge rules) are not ported; MK plays by Melee's physics, hitstun, shields and ledges.

## 1. What MK actually is, in data vs code

| part | where it lives in Brawl | size |
|---|---|---|
| attributes | FitMetaknight.pac (185 common words) | Jumps 6, gravity 0.0956, weight 79, glide window 16 |
| special params | paramSpecialN/S/Lw/Final blocks, Misc MultiJump, Misc Glide | 38 words + 5 hop velocities + 22 glide words |
| moves | PSA scripts: 492 subactions (397 with a clip), 16 special actions, 13 subroutines | 3,260 events, 183 hitbox windows in 42 subactions |
| animations | FitMetaknightMotionEtc.pac | 331 CHR0 (all used by subactions), 112 SRT0, 1 CLR0, plus 21 cape-article CHR0 in each costume pac |
| model | FitMetaknight00-05 | 77 bones, 13 meshes, 18 materials (9 + metal twins), 9 textures; separate 28-bone cape article model |
| fighter code | ft_metaknight.rel | 700 functions, almost all C++ template boilerplate (builders, pools, kinetic mediator) |
| MK logic that is native code | rel: Drill Rush (SpecialSRush + SpecialSEnd uniq processes, ~1 KB), Final Smash (3 classes), cape article class. **sora_melee** (engine): Mach Tornado control (`ftMetaknightStatusUniqProcessSpecialNSpin::execStatus`, 696 B), `ftMetaknightTransactor`, the common glide (`ftStatusUniqProcessGlide`, ~2.9 KB) | small |

The main finding: little of MK's identity is native code. Shuttle Loop and Dimensional Cape have no MK code
class at all. They are animation root motion plus PSA (variables, If/Else, Change Action). Shuttle Loop
enters glide through PSA: actions 0x114 and 0x11D run `Change Action 133 (0x85 Glide) on Animation End + In Air`.
The native pieces to rewrite are Mach Tornado's tap-to-rise control, Drill Rush steering and bounce, and
the glide physics.

## 2. Mechanics: what Melee/m-ex already has, and what needs Geno

| mechanic | Brawl implementation | Melee / m-ex mapping | needs |
|---|---|---|---|
| 5 midair jumps | Jumps = 6; MultiJump hops [2.2, 2.1, 2.0, 1.88, 1.75]; 5 own clips JumpAerialF..F5 | Melee multi-jump (`ftCo_JumpAerialF1`, per-kind `x2D0` table with 5 impulses and 5 states) covers exactly 5 air jumps. With a Kirby or Puff base it is vanilla behaviour. | Geno v0 `jumps.air_vy` for Brawl values (already built); nothing new |
| glide from jump | common statuses 0x84-0x88; enter by holding jump for 16 frames after an air jump | none in Melee | **Geno v2 action states** (geno.md section 11 design matches: GlideStart / Glide / GlideAttack / GlideLanding / GlideEnd) |
| glide from Up-B | PSA Change Action to status 0x85 at the end of SpecialHi / SpecialHiLoop | none | Geno v2 plus a Geno script escape or hook "enter Geno state N", callable from the translated Up-B script |
| glide attack | GlideAttack: 12% angle 70, frames 5-7 | ordinary hitbox script | comes with the glide states |
| crouch-walk | **none**: SquatF/SquatB slots (0x2E/0x2F) are empty, CrawlOffset = 0 | n/a | nothing |
| wall cling / tether | none (TetherOffset 0) | n/a | nothing |
| Mach Tornado (N-B) | PSA loops 1% rehit hitboxes; rise and drift are native (sora_melee, params 4012-4015, int 24000) | Melee Mario Tornado (Mario down-B) already has mash-to-rise and a looping multi-hit, so it is a code template | m-ex MoveLogic state with its own physics callback (port the 696-byte execStatus) |
| Drill Rush (S-B) | module `SpecialSRush::execStatus` (272 B, reads param 4020) plus `SpecialSEnd` (384 B); one autolink hitbox (angle 365); rehit rate 6 | no Melee analogue for steered flight | m-ex MoveLogic with native phys/input callbacks. Angle 365 needs a Geno v1 hitbox extension or a fixed-angle approximation |
| Shuttle Loop (Up-B) | root-motion animation plus PSA; 9% / 6% / 5% windows; ends in glide or FallSpecial | Melee states can take velocity from animation (as other up-Bs do) | translated script, then glide (Geno v2) |
| Dimensional Cape (Down-B) | PSA plus the cape article (`wnMetaknightMantle`); N/F/B variants from the stick; intangible via Body Collision; 14% reappear attack | Melee teleports (Sheik Vanish, Mewtwo Teleport) are templates for the state flow | m-ex MoveLogic. Replace the cape article with cape meshes inside the MK model (visibility gates `metaMantleM` / `MantM` already exist) |
| Final Smash | module classes | Melee has no Final Smash | drop |
| PSA features used | 41 Bit Variable Set, 33 Basic Variable Set, 17 If Comparison, 28 Else, 20 Change Action, 12 Change Action Status, loops, 79 Subroutine calls, Switch/Case | Melee ftcmd has timers, hitboxes, GFX, SFX, and no variables or conditionals | Geno v0 escape (vars, IF/SKIP) covers the logic. Change Action with requirements needs a Geno sub (v1) |
| sword trail | 29 Sword Glow + 10 Beam Sword Trail events on RHaveN | Melee has sword trails (Marth/Roy/Link; `Ft_MF_KeepSwordTrail`) | check whether m-ex exposes the trail description per custom fighter; otherwise Geno v1 |
| model parts | Model Changer 2 (354 uses): wings vs closed cape vs open mantle | Melee model-part visibility table (ftData parts / m-ex) | table built from the 4 gate bones |

## 3. Skeleton and clone base

MK's skeleton has 77 bones. It is a Kirby-like body core (25 bone names are shared with Brawl Kirby, and
21 of them already map to Melee Kirby joints through `experiment/brawl-kirby/phase2/bone_map.json`), plus
16 cape bones, 22 wing bones, a sword bone (SwordM under RHaveN), 4 visibility-gate bones and a few
helpers. No Melee fighter has anything like the cape and wings.

**Recommendation: do not retarget.** Ship MK with his own 77-bone skeleton in a new `PlMk.dat`, and convert
the 331 CHR0 one-to-one to Melee figatrees on the same bones. The existing `brawl-kirby/tools/anim` converter
(anim_convert / figatree) handles CHR0 to figatree. The "mapping problem" then shrinks to three things:
1. **Parts table.** Give the engine joints for the roles it asks for by index: Top, Trans, XRot, YRot, Hip,
   Waist (BodyN), head (BodyBN), clavicles, shoulders, arms, hands, the item joints LHaveN/RHaveN, legs,
   knees, feet and Throw. All of these exist by name in MK.
2. **Joint count.** 77 is above Shadow's 71, which already runs in the port. Verify every fixed-size
   per-joint array in the port (parts, dynamics, hurtbox bones) with a 77-joint fighter before starting
   Phase 3.
3. **Hitbox and hurtbox bones.** 145 of 183 hitbox windows are on TopN with offsets. The rest are on XRotN
   (16), RHaveN (10), SwordM (5), LFootJ (3), BodyN (3) and RToeN (1). There are 9 hurtboxes. Once the
   skeleton is MK's own, this is a unit conversion only (MK Size = 0.95).

**Clone base for behaviour (slot and code): Kirby.** Reasons:
- Melee Kirby's multi-jump states (JumpAerialF1-F5 and the `x2D0` table) fit MK's 5 air jumps and 5 jump
  clips exactly.
- Kirby is the same size class and body plan.
- The whole Brawl-Kirby Phase 1-3 toolchain (tuning, bone_map, anim convert, model writer) targets Kirby.
- MK's specials replace all of Kirby's specials anyway.

Fallback base: **Jigglypuff**. She has the same multi-jump machinery and a smaller special-state set, with no
copy-ability hooks into every other fighter's files. Switch to Puff if Kirby's copy-ability code or data
gets in the way of an m-ex clone.

Why not Marth or Link: MK's sword hitboxes are TopN-relative, not tied to a sword joint. Those skeletons are
humanoid, so retargeting would be worse. The only thing they offer is the sword trail, which is a
per-fighter data question, not a skeleton one.

## 4. Animation count

- 331 CHR0 in total, and all are referenced by subactions: 30 are MK specials, 6 glide, 5 air jumps, about
  88 item/ladder/swim/heavy-carry clips (Melee needs only the item subset), and the rest common.
- A Melee fighter needs about 200-230 of them (Melee has no ladders, swimming, footstool, glide in vanilla, or
  Final Smash). Estimate: **about 190 clips to convert for Phase 2, plus 6 glide, 30 specials, 5 jumps**.
- The Brawl Kirby port matched about 200 shared clips, so the scale is similar.
- Cape-article CHR0 (21 per costume) only matter if the article is kept. With the recommended merge into
  the body model, Dimensional Cape and shield poses bake the cape into MK's own clips.

## 5. Phased plan (mirrors the Brawl Kirby port)

**Phase 1: numbers and scripts (no new assets; behaviour host = Kirby's model/anims or a placeholder).**
- Map the 185 common attributes to `ftCo_DatAttrs` with the Kirby tuning tool (Melee feel) and write a
  Geno `geno.json` overlay: `jumps.max 6`, `air_vy` from the hops (scaled).
- Translate the PSA of the ground and air normals, grabs and throws (42 attacking subactions) with the
  Kirby mapping tool (verdicts direct / restructure).
- MK's jab is rapid-only: slots 0x48-0x4A are empty, so there is no Attack11-13. The ftilt is a 3-hit chain.
- Specials in Phase 1: Shuttle Loop and Dimensional Cape as scripts with fall-special endings. Mach Tornado
  and Drill Rush get placeholder physics.

**Phase 2: animations.** Convert the MK CHR0 to figatrees on MK's own skeleton (section 3). This needs the
PlMk skeleton from Phase 3, so in practice Phase 2 and Phase 3 start together, or Phase 2 temporarily
retargets the 21 core bones onto Kirby to test timing.

**Phase 3: model.** Build `PlMk.dat` from FitMetaknight00-05:
- 77 joints; 13 meshes with visibility-gated draw calls, giving 4 part groups (MantM closed cape, WingM
  wings, SwordM sword, metaMantleM open mantle).
- Metal twins map to Melee metal materials.
- Merge the cape article's model into the body (or keep it as an m-ex article if merging looks wrong in
  Dimensional Cape).
- Costumes 01-05 are texture swaps. Shadow model FitMetaknightShd is dropped (Melee draws its own shadow).

**Phase 4: native specials and glide** (after Geno v2): Mach Tornado control, Drill Rush steering,
glide states, and the Up-B to glide hand-off.

## 6. Geno features MK needs

v1 (scripts and moves):
- Subaction script overlays (already planned).
- Escape subs to read and write engine values (ground/air, velocity, facing, stick, frame).
- A **change-action escape** (Brawl `Change Action` with a requirement: animation end, in air, button, bit
  set). This is the heaviest-used control construct MK has after timers.
- Special-attribute (`dat_attrs`) overrides for MK's special params.
- **Rehit-rate hitboxes** (multi-hit specials: Mach Tornado, Drill Rush rehit 6, usmash/fair/bair
  multi-hits). These can compile to Melee's clear-hit-list plus timers, so the translator may handle them
  with no engine change.
- **Autolink angle 365** (1 hitbox, Drill Rush) or an agreed fixed-angle approximation.
- `on_land` dispatch (Shuttle Loop and Drill Rush landings).

v2 (states):
- **Geno action states**: glide (GlideStart / Glide / GlideAttack / GlideLanding / GlideEnd) with
  parameters from the Misc Glide block and the jump-hold entry rule (16 frames).
- An escape or hook to **enter a Geno state from a script** (Up-B to Glide).
- Native phys/input callbacks for Mach Tornado and Drill Rush, if they are not done as m-ex ftFunction code.

Not needed: crawl, wall cling, tether, HUD meters, any global mechanic.

## 7. Risks

- **Native logic is in sora_melee, not the fighter module.** Mach Tornado (696 B), glide (about 2.9 KB) and
  the MK transactor are unnamed engine functions (`fn_27_358CF4`, `fn_27_1680F4`, `fn_27_35A0EC`). Porting
  their feel needs disassembly or Dolphin measurements. The Misc Glide block's 22 words have no field names;
  only the 80/-70 angle limits are plausible guesses.
- **Param-id mapping is inferred.** Which paramSpecialN word is param 4012-4015 assumes floats-then-ints
  numbering. Confirm by reading `fn_111_81A8` before trusting the names.
- **Brawl vs Melee feel.** MK's Brawl frame data (for example dtilt IASA 16, nair f3-4 at 12%, 6 jumps,
  glide) will play very differently under Melee hitstun and shield rules. Expect a tuning pass like the
  Kirby "melee-feel" tuning.
- **Script translation coverage.** 89 Goto, 79 Subroutine calls, Switch/Case and 12 Change Action Status
  (transition-group ids 10000/10002) have no Melee counterpart except through Geno. Frames after loops are
  simulated (infinite loops run once; If takes the true branch).
- **77 joints and the cape/wing chains.** Joint-count limits are unverified above 71. Brawl animates the
  cape with CHR0 (no cloth sim), so there is no dynamics dependency, but the clips are dense.
- **Dimensional Cape article.** Keeping `wnMetaknightMantle` as an m-ex article means a second skeleton,
  21 clips per costume and article state sync. Merging it is simpler but may look wrong for the
  teleport's cape swirl.
- **Netplay/rollback.** All new state (glide angle and speed, tornado counters) must live in the Geno
  block or the Fighter struct (geno.md section 4). Nothing about MK requires host state.
- **Sounds.** 86 PSA sound ids map to BRSAR names (groups 683/486). They need extraction and an SSM bank.
  Waves were not extracted in this pass.
