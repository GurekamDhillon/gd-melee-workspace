# Meta Knight Phase 1: numbers and scripts

Local only, nothing committed. Everything is under `ports/halberd/`.

The slot now ships Meta Knight's own model and clips (Phases 2 and 3, `model_anim_ready.md`). Phase 1 started on
Kirby's body. When Phases 2 and 3 landed, the script writer was moved onto MK's skeleton and clips. The Kirby-body
build is kept as `tools/legacy/build_mk_kirbyhost.py` for reference.

That old build had one bug the coordinator found: its hitbox bone field held Kirby JObj numbers where the engine
expects part slots.

## How to build

```
python tools/mk_scaling.py                    # cast scaling + the 185-attribute map (analysis/)
python tools/build_mk_slot.py                 # tuning.json -> mods-slot/metaknight-slot (build, verify, install, check)
python tools/build_mk_slot.py --preset tuning.melee-feel.json
```

`build_mk_slot.py` does the following, in order:

1. Runs `build_mk.py`.
2. Runs `verify_mk.py`. If verification fails, the mod folder is left untouched.
3. Writes the shared m-ex files (`mk_slot_files.py`).
4. Runs `model/tools/install_mk.py --scripts=mk --no-vis`.
5. Writes the clip overrides and checks every scripted row plays the clip it was built for.
6. Writes `geno.json` and `mod.json`.

Re-run it after brawl-kirby-slot or the model/anim outputs change.

## Slot and ids

| | |
|---|---|
| mod | `mods-slot/metaknight-slot` (id `metaknight-slot`, kind fighter, 0.2.0) |
| m-ex row | internal **52**, external **51** (a Kirby clone). It replaces ACE's duplicate "Wolf SSBU" row (`PlWfU.dat`). |
| name / scene token | **"Brawl Meta Knight"**, so `p1=brawlmetaknight`. ACE already has a "Meta Knight" (ext 41, `PlMk.dat`), and name lookup takes the first match. `--name` changes it. |
| port kind | Dense: slot 25 means CharacterKind 0x3B and FighterKind 58, **with brawl-kirby-slot on**. The same install always gives the same kind. |
| files | `PlBm.dat`, `PlBmAJ.dat`, `PlBm{Nr,Ye,Bu,Re,Gr,Wh}.dat`, and `MxDt.dat` / `PlCo.dat` / `MnSlChr.usd` / `IfAll.usd` |
| netplay id (Geno exe, with geno.json) | `3554268fb680629e` (profile id; changes with the build) |

### Why internal 52

- ACE has one free row, 34/33, and brawl-kirby-slot uses it.
- The port has 31 m-ex fighter slots (`GW_MEX_SLOTS`, the 6-bit kind field), and rows 27..58 already hold 31 ACE fighters.
- So any extra fighter pushes one ACE fighter out, whichever row it takes.
- With brawl-kirby-slot on, ACE's row 58 (playable Giga Bowser) already drops off the end. This happened before MK too (see the log line `m-ex 58 (PlGkp.dat) and later are left out`).

### Coexistence with brawl-kirby-slot

- The later mod wins a disc path. `metaknight-slot` sorts after `brawl-kirby-slot`, so MK's `MxDt` / `PlCo` / `MnSlChr` / `IfAll` win.
- They are built on top of brawl-kirby-slot's copies, so they contain both rows.
- The filtered-base rule skips a row whose Pl file is missing. With MK's mod alone, Brawl Kirby's row simply isn't there.
- Tested: both mods on together, Brawl Kirby at internal 34 and MK at 52.

### CSS

- MK has no icon or CSP art yet. The existing ext-51 icon cell gets a new icon joint (58), a copy of **Kirby's icon, as a placeholder**.
- The CSP and stock icons are Kirby's.

## Attributes and tuning knobs

The Kirby method (`tools/mk_scaling.py` runs `brawl-kirby/tools/scaling.py`'s tables and rules with subject = metaknight):

- **Physics:** cast ratio, or z-score where the two games' cast spread differs.
- **Frames:** Brawl literal.

Of the 185 common words (`analysis/attributes_185.json`):

| status | count |
|---|---|
| written | 32 |
| map to a Melee field but keep the host value | 11 |
| Brawl global mechanic | 5 |
| Brawl-only ability (glide window, chain flags) | 2 |
| camera box | 1 |
| no Melee counterpart / unknown word | 134 |

| attribute | Melee Kirby | Brawl MK | written | variant |
|---|---|---|---|---|
| walk_max_vel | 0.85 | 1.22 | 1.228 | ratio |
| dash_initial_velocity | 1.4 | 1.75 | 1.752 | ratio |
| dash_max_velocity (run) | 1.4 | 1.847 | 1.804 | ratio |
| ground_friction | 0.08 | 0.055 | 0.0696 | ratio |
| jump_startup_time | 3 | 4 | 4 | Brawl frames |
| jump_v_initial / hop_v_initial | 2.0 / 1.5 | 2.4 / 1.68 | 2.563 / 1.62 | ratio |
| gravity | 0.08 | 0.0956 | 0.1207 | z-score |
| terminal_velocity / fast_fall | 1.6 / 2.0 | 1.39 / 1.946 | 1.9 / 2.432 | z-score |
| air_drift_max | 0.78 | 0.752 | 0.73 | ratio |
| weight | 70 | 79 | 74.98 | ratio |
| landing lag normal / N / F / B / Hi / Lw | 4/15/20/15/15/20 | 3/15/15/12/12/15 | Brawl | frames (L-cancel halves them) |
| max_jumps | 6 | 6 | 6 | 1 ground + 5 air |
| rapid_jab_window | 4 | - | **0** | MK's jab is rapid-only |
| model_scaling | 0.92 | 0.95 (Size) | 0.95 | MK's own model is in Brawl units |

Multi-jump uses Kirby's own 5-state table, with Brawl's hops [2.2, 2.1, 2.0, 1.88, 1.75] × 1.0679 (the jump scale):

- **Special attrs** (Kirby's `jumpaerial_jump1..5`): 2.349, 2.243, 2.136, 2.008, 1.869.
- **`geno.json`** carries the same values: `jumps.max 6`, `air_vy`.
- The next-jump gate moves from Kirby's frame 28 to MK's 24 (`JumpAerialF1-4`).

Host special attributes are knobs for Kirby's special code running MK's specials:

| knob | value | Kirby's | effect |
|---|---|---|---|
| `speciallw_max/min_time_in_stone` | 8 | 150/18 | cape vanish frames |
| `speciallw_gravity` | 0.4 | 4.5 | cape air sink |
| `speciallw_freefall_toggle` | 20 | 0 | non-zero sends the cape end into FallSpecial, with this landing lag |

The MK special parameter block (paramSpecialN/S/Lw, MultiJump, Glide) is in `geno.json` as `mk_special_attributes`, in v1 `{index, float|int}` form. It is **deliberately inactive**:

- v1 `special_attributes` overrides the host's `dat_attrs`, and Kirby's code reads those.
- Rename the key once MK-native special code (Phase 4) reads MK's layout.

**Tuning files:**

- `tuning.json` is the identity: pure Brawl MK. Same syntax as Brawl Kirby's, with MK move keys (`--show`-style list in its `_readme`).
- An `"mk"` block holds the structural knobs:
  - `hitbox_scale` 1.0
  - `model_scaling` 0.95
  - `autolink_angle` 80: the Drill Rush 365 stand-in in the Pl file. The Geno exe uses LINK instead.
  - `tornado_rehit` 10
  - `drill_rehit` null, which means Brawl's 6
  - `geno_v1` true
- `tuning.melee-feel.json`:
  - Brawl timing, angles and sizes, with **+15% damage** on everything except the rapid jab, tornado and drill.
  - **Knockback growth -5%** on fair, bair, usmash and dtilt.
  - Melee Kirby's jump squat and landing lags.
  - It builds and verifies with 0 mismatches. There is no Melee MK, so `"melee"` for a hitbox means the Kirby hitbox it was mapped onto.

## Subaction coverage

Verdict legend (the Kirby mapping tool's):
- **direct**: same window count as the Melee host move.
- **restructure**: different window count.
- **unsupported**: needs code.

All hitboxes use MK's bone, offset and size, with Brawl damage, angle, KBG, BKB, WDSK and shield values. Brawl's sound class (weak/medium/strong × slash/kick/punch) maps to the Melee hit SFX. Clip lengths are Brawl's.

| move | rows (clip) | status | verdict | notes |
|---|---|---|---|---|
| jab | 46 Attack11 (Attack100Start) | translated | restructure | Attack11 sets RapidJab at counter 2. Window 0 means every A press goes straight into the rapid jab. |
| rapid jab start / loop / end | 49 / 50 / 51 | translated | direct | 5 rehit windows (2%/1%). Loop checkpoints sit at MK's RA.Bit[25] frames 9 and 19. The finisher is 3 × 2%. |
| dash attack | 52 | translated | direct | 8/7/6%, f5-11 |
| ftilt 1 | 53/55/57 | translated | direct | 4% ×3, f3. Brawl MK has no angled ftilt. |
| ftilt 2 / 3 | 47 Attack12 / 48 Attack13 (AttackS3S2/S3S3 clips) | translated (**Geno exe**) | unsupported in plain Melee | 3% / 5-4%. Reached by v1 `CHG PRESSED(A)` inside Brawl's RA.Bit[16] window. Plain exe: ftilt 1 only. Motions 45/46 are unreachable otherwise, because MK's Attack11 never sets JabCombo. |
| utilt | 58 | translated | restructure | sweet f7 8%, then 7/8/6% to f18 |
| dtilt | 59 | translated | direct | 4-7% f3-4, IASA 16 |
| fsmash | 60/62/64 (Start+S4S, 43) | translated | direct | 14% f25-26. SmashCharge at 21. |
| usmash | 66 (51) | translated | restructure | 3+2+4 multi-hit (f9/13/18). SmashCharge at 4. |
| dsmash | 67 (35) | translated | restructure | 11% f5-6, 13% f10-11. SmashCharge at 1. |
| nair / fair / bair / uair / dair | 68-72 | translated | restructure/direct | nair 12% f3-4 then 7-5% to f24, IASA 32; fair 3/3/4; bair 3/3/4; uair 6% f2-3, IASA 14; dair 7-9% f4-5 |
| landing N/F/B/Hi/Lw | 73-77 | translated | restructure (Kirby's landing hits removed) | Lag comes from the attributes. |
| grab / dash grab | 242 / 243 | translated | direct | catch boxes f6-7 / f8-9 (MK size and offset, Melee catch element) |
| pivot grab | - | stubbed-for-v2 | unsupported | no Melee motion |
| pummel | 245 | translated | direct | 3% f4 |
| throws F / B / Hi / Lw | 247-250 | translated | direct | Throw Specifier to ThrowHitbox values; release at MK's Throw Applier (4/16/43/73); bystander and grabbed hitboxes (dthrow 9 × 1% + 1). Kirby's throw code attaches the victim. |
| ledge attacks | 221 / 222 | translated | direct | 10% f39-42 / 8% f25-28; intangibility from Brawl's Body Collision |
| getup attacks | 187 / 195 | translated | direct/restructure | 6% f16-17, 26-27; intangible to f27 |
| multi-jump | 295-298 (+Met) | translated | direct | wings via ModelVis; next jump allowed at 24 |
| **Mach Tornado** start / spin / end | 305/320, 306/321, 307 | approximated | unsupported (native physics) | 4 × 1% set-knockback hitboxes, rehit every 10 frames while B is held, 3% finisher. **Placeholder physics:** Kirby's inhale loop (stands still; no rise, drift or tap-to-rise). The hitboxes aren't catch-element, so nothing is swallowed. |
| **Drill Rush** ground / air | 322 / 323 (SpecialSDrill clip) | approximated | unsupported (native steering) | 3 hitboxes rehit 6 from f5, then end hits. **Placeholder physics:** Kirby's hammer code (ground: in place; air: hop, fall-special landing). No 22-frame start. Pl file uses angle 80 for 365. Geno exe adds `LINK` (autolink), plus `PUT FWD_VEL -1 / VEL_Y 2.1` on the air end. |
| **Shuttle Loop** rise / loop | 324/328 (SpecialHi), 325/329 (SpecialHiLoop) | approximated | restructure | 9% f8-9, 6% f10-12, 6% f22+, loop 9%/5%; intangible f5-8. Path = Kirby's Final Cutter code. **Geno exe:** `CHG ANIM_END -> FallSpecial` at the loop end. Plain exe: Kirby's plunge. |
| Shuttle Loop fall / land | 326/330, 327/331 (SpecialHiEnd) | approximated | unsupported (Brawl: glide) | no hitbox, no cutter wave; glide is v2 |
| **Dimensional Cape** start / vanish / attack | 332/335, 333/336, 334/337 (SpecialLw clip on the end rows) | approximated | direct (attack) | Cape article shows (ModelVis 0,2). Intangible from 17, hidden from 12 (FighterVis). Then 8 frames hidden and intangible on Kirby's stone hold. Then the neutral reappear attack, 14% f6-7, then FallSpecial. **Geno exe:** `PUT FACING 0` at 1 (Brawl's Reverse Direction). No stick-steered teleport or F/B variants. |
| glide attack | - | stubbed-for-v2 | unsupported | needs the Geno glide states |
| final smash, trip attack | - | not ported | Brawl global mechanic | |

**Stub lists** (`analysis/v1_stubs.json`):

- **Expressed as v1 overlays:** 10 rows, 12 escapes.
- **v2 (native / Geno states):** tornado physics (`execStatus`), glide (Shuttle Loop hand-off and glide attack), pivot grab.
- **No v1 value:** Allow/Disallow Ledgegrab (4×), Disable/Enable Horizontal Gravity, Frame Speed Modifier.
- **Later:** MK's SFX bank (29 events, BRSAR not extracted), EfMk effects (39), sword trail (Sword Glow, 21).
- **Not needed** on Kirby's code paths: 3 × Set Air/Ground.

## Verification

1. **Offline** (`tools/verify_mk.py`, run by every slot build): **0 fails**.
   - `brawl-kirby/tools/verify_mod.py`, unchanged:
     - 1,858 tuning values re-derived, 0 mismatches.
     - 33 attributes.
     - Every hitbox field, start and window, the IASAs and the throw values match.
     - 402 untouched rows byte-identical to vanilla Kirby.
   - MK checks:
     - Grab boxes are catch-element.
     - Every added command sits at its counter.
     - Loops wait.
     - No escape in the Pl file.
   - Stage B (the shipped file), across 2,143 commands in 469 row scripts:
     - Every hitbox, GFX and wind bone is an MK joint.
     - Every hurtbox-state bone is one of MK's 9 hurtbox joints.
     - ModelVis stays within MK's two models.
   - `geno.json`: 10 overlays / 12 escapes are valid v1 forms, and each overlay minus its escapes equals the Pl script.
   - After install: all 67 scripted rows play the clip they were built for.
2. **In game** (Geno exe copy, ACE disc, training vs a level-0 Kirby CPU, FD). `tools/ingame_moves.py` drives MK through every normal, grab, throw, special and the 5 air jumps. It reads `gd.hitboxes` every frame (`analysis/ingame_moves.json`).
   - Every hitbox the engine creates matches CHANGES.json in damage, angle, KBG, BKB and WDSK. Stale-move damage is accepted.
   - No crash across the whole move list.
   - **Result: 40 input plans, 0 fails, no crash.** The run went through:
     - Rapid jab from one tap.
     - Every tilt, smash and aerial.
     - Grab, pummel and all four throws on the CPU (10-12% each).
     - All four specials, ground and air.
     - The ftilt chain `AttackS3S > Attack12 > Attack13` (4+3+5 = 12% on the CPU).
     - Up-B `SpecialHi1 > SpecialAirHi2 > FallSpecial > LandingFallSpecial`.
     - Down-B with the turn.
     - 5 air jumps `JumpAerialF1..F5`.
   - One Brawl hitbox is not reached in game: the air Drill Rush's end hit (3%). Kirby's air hammer code lands the move first (LandingFallSpecial).
   - The **main exe** (non-Geno, overlays inactive) ran MK in the pad-driven netplay matches below, with no crash.
3. **Netplay** (`_build/netplay_local.ps1`, ACE disc, MK vs vanilla Kirby, pad-driven through every move family):
   - **Main exe** (Geno off), wifi simulation (20 ms lag, 12 ms jitter, 2% loss):
     - The match ran to game over at about 3,360 frames.
     - Rollbacks: 122 host / 135 guest, max depth 7.
     - **0 desyncs.**
     - An earlier main-exe run on loopback: about 3,390 frames, 0 desyncs.
   - **Geno exe** (v1 overlays and geno.json active), wifi simulation:
     - About 4,850 frames to game over.
     - Rollbacks: 122 host / 214 guest, max depth 7.
     - **0 desyncs.**
   - The results screen loads with no "Demo Status error".

## Findings for the coordinator and GD

- **Results screen shows "G.BOWSER": this is a port bug, not slot data.**
  - The results name and panel art come from `gm_80168B34` (gm_1601.c:4066). For any m-ex CharacterKind it returns `ckind - 1`.
  - MK's kind is 0x3B, so it returns frame 58, which is Giga Bowser's.
  - Call sites: gmresultplayer.c:1065, :1083, :453, :1100.
  - The fix belongs in the port: map an m-ex kind to m-ex's own frame, as m-ex's `GetStockFrame` does, or return a neutral frame.
  - Every m-ex fighter is affected, Brawl Kirby included (frame 40 at CK 0x29).
- The **"Demo Status error"** on the results screen is fixed for MK by `install_mk.py` (demo-table hole). brawl-kirby-slot's `PlBk.dat` has the same hole; it was left untouched, as asked.
- Kirby's clone code runs MK's specials, so their **physics are placeholders** (tornado, drill, cape teleport) until Phase 4.

## What GD should try (Geno exe, `MELEE_LAB=1`)

- **Jab:** tap A. You get the rapid jab straight away; mash to keep it going.
- **Ftilt:** A, A, A for the 3-hit chain (Geno exe only). Compare with the plain exe, where you get ftilt 1 only.
- **Fair/bair auto-cancel feel:** L-cancel landing lags are Brawl's 15/12.
- **Nair:** IASA 32 on the sweetspot.
- **Up-B:** watch it end in FallSpecial and grab the ledge.
- **Down-B:** the 8-frame vanish, then the turn-around slash.
- **Side-B in the air:** autolink (LINK) and the end hop.
- **Movement:** 5 air jumps, gravity 0.12 / fall 1.9 / fast fall 2.43, run 1.80. Does it feel like MK in Melee?
- **Melee-feel preset:** `python tools/build_mk_slot.py --preset tuning.melee-feel.json`, then restart the game (+15% damage).
- **Lab keys:** `M` shows the move timeline (hitbox windows and IASA), PageUp/PageDown scrub, `1` shows the hitboxes.

## Geno v3 specials (Up-B, Side-B, Down-B rebuilt; Geno exe)

On the Geno exe every MK special now runs as Geno states on MK's own clips; no Kirby special code runs
(`specials` binds n / s / hi / lw and their air versions). The main exe keeps the older approximations on
Kirby's rows (Final Cutter 324-331, hammer 322/323, stone 332-337), and they run without a crash.

| move | Geno v3 states (row, clip) | how it moves | ends |
|---|---|---|---|
| Shuttle Loop, ground | UpB (352, SpecialHi, 32f) | the clip's TransN (`geno.anim_motion`, origin, lift-off when the rise starts) | Glide in the air (helpless after); landing -> UpBLand (355, SpecialHiEnd, 32f) -> Wait |
| Shuttle Loop, air | UpBAir (353, SpecialAirHiStart, 8f, holds still) -> UpBLoop (354, SpecialHiLoop, 31f) | TransN | Glide in the air; landing -> UpBLand |
| Drill Rush | DrillStart / DrillStartAir (343/344) -> Drill (345) -> DrillEndGround (347) / DrillEnd (346) | Brawl's code: stick-Y pitch 3 deg/f, unlimited, TransN speed; drills through hits | ground: Wait; air: FallSpecial (landing LandingFallSpecial) |
| Dimensional Cape | CapeStart / CapeStartAir (356/357) -> CapeN/NAir/F/FAir/B/BAir (358-363) or CapeEnd/EndAir (364/365) | start keeps 0.5 / 0.4 of the momentum; hidden at 12; stick-steered vanish (0.5 accel, 2.5 max per axis); intangible 17 -> reappear f1; slash variants move by TransN | ground: Wait; air: FallSpecial |

Hitboxes are Brawl's (verify_mk re-derives them; in game every hitbox matches CHANGES.json):
- Shuttle Loop ground: 9% (angles 70 and 80) f8-9, 6% f10-12, 6% angle 110 from f22. Intangible f4-8.
- Shuttle Loop air loop: 9% angle 30 f1-7, 5% angle 361 from f8.
- Ledge grab (front and back) from f7 of both.
- Drill: 3 x 1% (365 via LINK / 78 / 70), rehit 6, from f5. Ground end 3% + 2% f1-2; air end 3% + 3% f1-5.
- Cape slash: 14% angle 60, f6-7, 2 boxes.

Evidence and checks:
- Brawl evidence: geno.md s17 (the disassembly of SpecialSRush / SpecialSEnd and of MK's kinetic types 0x66-0x6A, and the PSA).
- Offline: verify_mk (0 fails, with the new v3 checks).
- In game: tools/ingame_v2.py "v3" plans, analysis/ingame_v2.json, 34/34.
- Netplay: 0 desyncs.
