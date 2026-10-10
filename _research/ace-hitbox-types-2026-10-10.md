# ACE hitbox types and hitbox mechanics vs retail Melee (2026-10-10)

Lane `ws/research-ace-hitboxes`. Question: what hitbox types and hitbox-related mechanics do the characters
on the ACE build (`SSBM ACE Build v2.0.0.iso`, `GW_ISO_ACE`) use, compared with retail, and what would Geno's
authoring tools need to express them. Dated note; it is the only note on this topic (no older one to defer to).

Evidence tags: **[M]** measured in a run (the data set is named), **[R]** read from code or docs (file named).
Nothing here is a disc dump: it is frame/damage/angle/knockback numbers, the same class as `docs/geno-artist-spec.md`.
The raw per-run dumps live in the lane's build root (`_build/agents/acehbg/`, git-ignored), not in git.

Data sets (all produced by the scripts in `tools/research/`, turbo, offscreen windows, build `3186a4af1`):

| tag | what | where (build root `_build/agents/acehbg/`) |
|---|---|---|
| **[M:dump]** | static `gd.timeline(port, motion)` for motions 0..700 of one fighter (events decoded, raw words kept) | `acehb_dump/<fighter>.jsonl`; 31 ACE m-ex fighters + 24 retail on ACE + 24 retail on vanilla |
| **[M:lab]** | the Geno LAB's measured frame-data export (`MELEE_LAB_BATCH`, live `gd.hitboxes`) | `acehb_lab/<fighter>/{moves,hitboxes}.csv`; 29 of 31 added fighters + 26 retail x 2 discs |
| **[M:probe]** | live probe: 4 ground specials, grab, jab, ftilt, 3 smashes vs an idle Mario at 3 ranges; items P1 owns; connected hits | `acehb_probe/probe_mex<N>.txt`; 31 added fighters |
| **[M:interp]** | boot of each added fighter, `interp:` log lines (which m-ex ftFunction slots the port runs) | `interp_scan.txt` |
| **[R]** | `tools/mex_port/dump_mex_slots.py`, `dump_ftfunction.py`, `dump_gct.py`, `scan_ftcmd_opcodes.py` read-only on the ISO | quoted inline |

## 1. Fighters (R1)

ACE is an m-ex disc: `internal_id_count 65`. **[R]** `dump_mex_slots.py --iso ACE`: internal ids 0-26 are the retail
roster, **27-58 are 32 added rows, one of them empty (id 34 has no Pl file) = 31 added fighters**, 59-64 are the six
retail bosses kept last. The port has `GW_MEX_SLOTS = 31`: "FITS EXACTLY, 0 spare".

**Retail fighters are not modified.** Three independent checks:

- **[M]** all `Pl*.dat` present on both discs: 272 byte-identical, 1 different (`PlCo.dat`, the common file, not a fighter). (md5 of every file, ACE vs vanilla.)
- **[M:dump]** `ace_hitbox_collect.py --diff`: for all 24 retail fighters that loaded in the static run, ACE vs vanilla `changed=0` in every one (e.g. `ace_ck2 Fox: moves ace=152 van=152 changed=0`). Kirby (ck4) and Mewtwo (ck10) did not load in the static run (VS ends at once with `p2=none`).
- **[M:lab]** all 26 retail CharacterKinds, `hitboxes.csv` and `moves.csv` ACE vs vanilla: `diff rows 0` for every one (Falcon 106 hitbox rows both discs, Link 115, Kirby 96, Mewtwo 64 ...).

What this does **not** exclude: ACE ships 1169 Gecko codes (**[R]** `dump_gct.py`, "1169 codes total"), some of which patch hit code
(section 3.6). Those are not in the PlXX files, and the port does not run Gecko codes.

Added fighters (**[R]** `dump_mex_slots.py` + **[M:interp]** installed override counts; "code bytes" is the blob's header
value, `hdr 0` = header says 0 and the real size was recovered by the loader; "articles" = non-vanilla item kinds P1 owned during
**[M:probe]**, an article = a projectile or helper with its own hitbox):

| slot | mex int | name | Pl file | clone base | ftFunction overrides | code bytes | articles seen (kind ids) |
|---|---|---|---|---|---|---|---|
| 0 | 27 | Wolf | PlWf | Mario (none shares fn) | 21 | 0x3F88 | 253,254 |
| 1 | 28 | Diddy Kong | PlDd | Mario (none) | 23 | 0x6138 | 257,258,259 |
| 2 | 29 | Charizard | PlLz | Koopa | 23 | 0x36F4 | 262,263,264 |
| 3 | 30 | Lucas | PlLc | Mario (none) | 28 | 0x7DC8 | 266,267,269-275 |
| 4 | 31 | Sonic | PlSn | Mario (none) | 25 | 0x5778 | 277 |
| 5 | 32 | King Dedede | PlDe | Mario (none) | 24 | 0x6C7C | 280,281 |
| 6 | 33 | Tails | PlTs | Mario (none) | 26 | 0x64DC | 284 |
| 7 | 35 | Wario | PlWr | Mario (none) | 18 | hdr 0 / 8608 | - |
| 8 | 36 | Daisy | PlDa | Peach | 12 | hdr 0 / 8448 | 290 |
| 9 | 37 | Lucas TDX | PlLc2 | Mario (none) | 21 | hdr 0 / 20256 | 294,296,297,302 |
| 10 | 38 | Raichu | PlRc | Pikachu | 8 | hdr 0 / 20992 | 304 |
| 11 | 39 | S. Mewtwo | PlSm | Mewtwo | 15 | hdr 0 / 26592 | 307,309 |
| 12 | 40 | Skull Kid | PlSd | Ness | 14 | hdr 0 / 28448 | 310,311,312 |
| 13 | 41 | Fay | PlFy | Fox | 13 | hdr 0 / 18688 | 313,314,317 |
| 14 | 42 | Meta Knight | PlMk | Mario | 14 | hdr 0 / 15584 | - |
| 15 | 43 | Sonic BM | PlSc | Mario | 14 | hdr 0 / 16032 | 320,321,322 |
| 16 | 44 | Luigi & Boo | PlLb | Luigi | 14 | hdr 0 / 9952 | 324 (Boo, always present) |
| 17 | 45 | B. Falcon | PlBF | Captain | 4 | 0x13F0 | - |
| 18 | 46 | Metal Mario | PlMM | Mario | 6 | hdr 0 / 4224 | 325 |
| 19 | 47 | Dr. Luigi | PlDl | Luigi | 4 | hdr 0 / 2816 | 328 |
| 20 | 48 | Ninten | PlNt | Mario (none) | 23 | 0x4C28 | 329,331 |
| 21 | 49 | Metal Sonic | PlNm | Fox | 10 | hdr 0 / 22432 | - |
| 22 | 50 | Knuckles | PlKx | Mario (none) | 26 | 0x58D4 | 337 |
| 23 | 51 | Zero | PlZx | Link | 10 | 0x269C | 338 |
| 24 | 52 | Wolf SSBU | PlWfU | Mario (none) | 21 | 0x3F88 | 340,341 |
| 25 | 53 | Lucina | PlLu | Mars | 6 | 0xF00 | - |
| 26 | 54 | Blastoise | PlBl | Koopa | 22 | 0x1DC0 | 344,345 |
| 27 | 55 | Chun-Li | PlCn | Zelda | 15 | hdr 0 / 13312 | 348 |
| 28 | 56 | Shadow | PlSh | Mario (none) | 25 | hdr 0 / 24416 | - |
| 29 | 57 | Toad | PlTd | Mario | 13 | hdr 0 / 8256 | 354 |
| 30 | 58 | Giga Bowser | PlGkp | Mario (none) | 1 | 0x424 | - (Bowser's flame, vanilla kind 100) |

"Mario (none)" is `gw_Mex_FtBaseKind`'s fallback when no retail fighter shares `fighter_function[0]`. All 31 carry an
ftFunction PPC blob (**[R]** `PlWf.dat --header`: `codeSize 0x3F88, debugSymbolNum 184, functionRelocTableNum 21`); 14 have
debug symbols (so function names are readable), 17 do not. Costume/art sets are not discussed here.

Naming caveat that matters for every table below: `gd.motion_name` has no table for an m-ex fighter, so special-state names
in the dumps (`SpecialLwStart`, `SpecialHi x32`, ...) are the **clone base's** names for the same motion ids, not the fighter's.
Use motion ids, and the LAB's "Neutral B / Side B / Up B / Down B" rows, to talk about specials. (**[R]** `gw_script.c` comment
on `gs_motion_name`; **[M:probe]** Sonic's Side B enters action 351 named `SpecialLwStart`.)

## 2. Summary table: hitbox types (R2)

Counts are hitbox creations (ftcmd op 11) in the fighters' **own moves** (motion names Attack*, Special*, Catch*, Throw*,
CliffAttack*, DownAttack*), de-duplicated per (motion, frame, slot). Item swings (`BatSwing*`, `*Screw`, ...) and
falling/damage hits are common states shared by every fighter and are excluded; including them changes no ratio by more than 2 points.
**[M:dump]** `ace_hitbox_report.py types`: **4903 creations in 31 added fighters; 4053 in the 24 retail fighters on the vanilla disc.**

| type | how it is built (retail ftcmd) | added (4903) | retail (4053) | where in ACE; example |
|---|---|---|---|---|
| angle 361 (Sakurai) | op 11 `angle` = 361 | 51.3% | 45.8% | everywhere; Tails 212 of 476 |
| non-normal element | op 11 `element` != 0 | 42.5% | 43.5% | incl. grab boxes (`catch`, 10-16 per fighter, = 8 + dashes) |
| set knockback | op 11 `wbk` (weight-set kb) > 0 | 27.5% | 18.5% | most different: Metal Mario 114, Metal Sonic 605 (rehit loop), Charizard 68 |
| no rebound flag | w3 bit 0 = 0 | 28.6% | 26.8% | |
| no clank flag | w3 bit 1 = 0 | 26.2% | 24.5% | Charizard 81, Zero 126, Ninten 77 |
| shield damage != 0 | w4 bits 10-17 | 22.5% | 23.1% | negative values: see 3.3 |
| multi-create (same slot re-created) | op 11 again on a live id (rehit) | 7.8% of creations; 39% of moves | 6.8%; 34% | Metal Sonic Down B loop, Dedede Attack100Loop x36 |
| windbox / 0 damage | op 11 `damage` 0 | 6.9% (mostly `catch` grabs) | 7.2% | non-grab 0-damage: 23 added (Wario Side B start `inert`, Skull Kid, Meta Knight) vs 25 retail (Falcon Punch start `inert`) |
| meteor / spike band 230-310 | `angle` 230..310 | 4.0% | 3.5% | Shadow 28 (ground-only 10), Lucas 15 |
| horizontal 0 / 180 | `angle` 0 or 180 | 2.8% | 2.6% | Meta Knight 30 |
| ground-only / air-only | `hit_ground` / `hit_air` = 0 | 1.3% / 0.6% | 2.6% / 0.8% | Wolf AttackHi3 (ground 12, air 9) |
| only-hit-grabbed | op 11 header bit 19 | 0.7% | 0.8% | CatchAttack (pummel) |
| hitbox id 4 | op 11 id field = 4 | 1 (Skull Kid up-tilt) | 0 | see 3.2 |
| sweet / sour (concurrent boxes, differing damage/angle/kbg) | several slots live together | 34% of moves | 35% | Wolf AttackS3Hi |
| clean / late (same slot, later window, other damage) | op 11 again, or op 12 `hitbox_damage` / 13 size | 26% of moves | 22% | `hitbox_damage` events are rare in own moves (14 vs 12) |
| throw hitbox | op 34, id 0 (the throw) + id 1 (collision for the thrown) | 381 | 330 | dark-element throws (elem 13): 2 added; wbk>0: 2 vs 1 |
| per-bone hurtbox state | op 28 | 610 events in own moves | 57 events in 24 fighters | Tails, S. Mewtwo, Giga Bowser, Blastoise (3.4; counts are walker events, see the note below the table) |
| whole-body state | op 26 (0 normal, 1 invincible, 2 intangible) | 163 motions with an event | 92 | same shape as retail; `invincible` only in Special S of one fighter (2 events vs 6 retail) |

Counting caveat: the static walker expands loops up to 2000 commands / 1000 frames, so loop-heavy moves (Metal Sonic `SpecialLwLoop` 143, Raichu `SpecialSHold` 101, Tails' intangible events) inflate counts. Read counts as "used", not "how often"; the percentages above are de-duplicated per (motion, frame, slot) and are not much affected.

Reading: **the added fighters use the same hitbox vocabulary as retail, in the same proportions.** The distributions differ by
the usual character-design noise (set-kb is 9 points higher, Metal Sonic alone contributes 605 rehit-loop creations).

Elements seen in added fighters (**[M:dump]**, names from `gs_element_names`): normal, fire, electric, slash, coin, ice, catch,
ground, cape, inert, dark, lipstick (item swing), leadead. Maximum element id 16; **no element id outside the retail enum**
(`HitElement` in `src/melee/lb/forward.h`, 0-16); no `"?"` name in any dump. Raichu and Blastoise use `leadead`
(ReDead grab element, the retail enum comment says so) in 5 and 1 hitbox. Dark: S. Mewtwo 45, Skull Kid 28, Giga Bowser 12, Shadow 9.

## 3. Mechanics that are not plain retail hitbox commands (R3)

### 3.1 Subaction opcodes: none custom

- **[R]** `scan_ftcmd_opcodes.py ACE`: `79 fighter files, 22172 scripts, 138365 commands, highest opcode 58; opcodes >= 59: none; Geno escape 0x3B (59) used 0 time(s)`. So ACE adds no m-ex subaction command and does not collide with Geno's opcode 59.
- **[M:dump]** the ops that occur in added fighters but in none of the 24 retail fighters dumped (41 distinct ops in each of ACE-retail and vanilla, identical sets): only `models_revert` (32; Wolf, Skull Kid, Meta Knight, B. Falcon) and `color_overlay_off` (47; Diddy, Skull Kid). Both are retail opcodes (cosmetic: model state, colour overlay); 0 hitbox ops are new.
- Engine: all of these are retail opcodes `gd.timeline` decodes; supported.

### 3.2 Hitbox slot 4 (Skull Kid up-tilt)

- **[M:dump]** `ace_mex40 AttackHi3`: four creations in one move, ids 3 and 2 at frame 8, ids 1 and **4** at frame 12 (damage 11, bone 48, size 2.34, angle 84). The command's id field is 3 bits.
- **[R]** `ft/types.h:1461-1463`: `HitCapsule x914[4]`, then `xDF4[2]`, then `x1064_thrownHitbox`; stride 0x138, so a hitbox command with id 4 writes `x914[4]` = `xDF4[0]`, which is also the first **throw** hitbox record (`ftAction_80071E04` indexes `fp->xDF4[idx]`, ftaction.c:720). The hit loops walk `ARRAY_SIZE(x914)` = 4 (`ftColl_8007AE80`, ftcoll.c:3213; the damage scan `i < 4`, ftcoll.c:3731). So the id-4 box is a throw-record alias that the 4-slot loops never poll. `docs/geno.md` says id 4 is "the thrown hitbox"; by the struct it is `xDF4[0]` (the throw record), and `x1064_thrownHitbox` is another member (suggest correcting the doc, owed).
- **[M:lab]** `acehb_lab/ace_mex40/hitboxes.csv` shows AttackHi3 ids 1, 2, 3 only (frames 7-13), no id 4. **Whether the id-4 box ever hits is owed** (needs a hit test on hardware or a live hit probe on this move).

### 3.3 Hitbox values written by code, and one negative shield damage

- **[M:lab]** vs **[M:dump]**: live hitbox tuples (damage, angle, kbg, bkb, element) that no static script contains. Added fighters: Diddy Up B (bkb 50, 51, 53, 54 ... fire, 19 creations), Wario AttackAirB (bkb 55), Raichu Side B (3 variants, bkb 30/35), B. Falcon Side/Up/Down B (inert 0-damage, catch, fire 9-15 dmg with 3 steps), Dr. Luigi Side B and AttackAirF/B, Lucina Neutral B (bkb 30, 34, 40 = charge) and Side B (angle 76-96), Giga Bowser Side/Up/Down B. **Retail has the same effect**: Pikachu/Pichu Side B, Yoshi Side B and AttackDash, Link/Young Link AttackAirHi/Lw, Luigi Side B. So hitbox values written at run time by a state callback are not an m-ex feature; ACE just has more of them (8 of 29 measured added fighters vs 5 of 26 retail).
- Counter-evidence that the LAB can mislead: Meta Knight `AttackS4S` reads `damage 94137296.0` live in the LAB (static script says 15). **[M:probe]** MK's real F-smash hit dealt `15.0` (`probe_mex42.txt`: `fsmash ... dealt=15.0`). The LAB enters the state by plain `Fighter_ChangeMotionState` without the smash input, and MK overrides the `onFSmash` hook; treat as a LAB artefact, not a game fault.
- **Negative shield damage**: Metal Sonic `SpecialLwLoop`/`SpecialAirLwLoop` (Down B spin) create `shield_damage -3` 286 times each; retail own moves have no negative value (the only negatives anywhere are `BatSwing4`'s -9/-3, in every fighter, item-bat). **[M:lab]** Metal Sonic Down B: `damage 2, angle 361, kbg 100, bkb 5, wbk 5, electric, shield -3`, hit windows `8, 14-15, 21-22` (rehit every 7 frames), final hit `7 dmg, 80, 60/60`.

### 3.4 Per-bone hurtbox state, body states

- **[M:dump]** op 28 (`hurtbox_state`, bone + state), events in the static walk, all motions: Tails 568 (state 2 = intangible; 6 x state 0), S. Mewtwo 812, Giga Bowser 276, Blastoise 96, Daisy 9, Fay 5, others 1-4. In own moves 610 (added) vs 57 (24 retail). State values seen: 0 and 2 only. Op 26 (`body_state`): values 0 (169), 1 (2: Special S), 2 (214), same shape as retail (138 / 6 / 153).
- **[R]** `ft/ftaction.c:550-566`: op 26 -> `ftColl_8007B62C`, op 27 -> `ftColl_8007B0C0`, op 28 -> `ftColl_8007B128(bone, state)`; `HurtCapsuleState { Enabled, Disabled, Intangible }` in `lb/forward.h`. So the retail command set already gives per-bone intangibility; ACE uses it more (spinning/tail moves).
- **Walker artefact**: three `hurtboxes_state` events decode to ASCII (`0x6d5f6669` = "m_fi"): Dedede `SpecialLwHold`, S. Mewtwo `AppealSL`/`SpecialNLoop`. `gd.timeline`'s static walk ran off the end of a script into non-command data on those loops; ignore events at frame > 400 there.

### 3.5 Code-driven behaviour (m-ex ftFunction PPC), and what the port dispatches

- **[R]** `gw_mex_ftfunction.c` slot table (46 hooks: `onLoad` ... `GetTrailData`) and `gw_mex_ftfunction_runtime.c`: the port runs the fighter's blob in a PPC interpreter and dispatches slots 0-26, 32-36, 41, 43, 44 (`GW_MEX_SLOT_*`; `gw_mex_slot_is_wired`) plus slot 45 `GetTrailData` through its own entry `gw_Mex_FtTrailData`; special moves are 4-11 and `MoveLogic` is 3.
- **[M:interp]** boot log of each added fighter: slots it overrides but the port **does not dispatch** ("the clone base's handler runs instead"):
  - Daisy (mex 36) and Skull Kid (mex 40): slot 31 `onFloat`
  - Luigi & Boo (mex 44): slot 37 `onDSmash`
  - slot 45 `GetTrailData` is also logged for Daisy, Zero (mex 51) and Lucina (mex 53), but **[R]** `gw_mex_ftfunction_runtime.c:2804-2825` dispatches it via `gw_Mex_FtTrailData`, so this is a stale diagnostic (`gw_mex_slot_is_wired` has no 45), not a missing feature.
  - `MoveLogic table missing (slot3=.. slot4=0)` for B. Falcon (mex 45), Lucina (mex 53) and Giga Bowser (mex 58). **[R]** `gw_mex_movelogic_setup` (line 2978) sizes the table by the next override (`SpecialN`, slot 4); these three have none, so the table is **not rewritten** (Giga Bowser has no MoveLogic at all, harmless). For B. Falcon and Lucina that means the state callbacks in their own MoveLogic table (including `Rebound_Coll` and the `*_CollCB` hit callbacks for B. Falcon) are not wired to native trampolines. **Inference, not measured**: their specials may run on the clone base's logic; the LAB shows B. Falcon's specials as the retail Captain set (Side B `inert` start, Up B `catch`, Down B fire steps). Owed: compare against the disc's intended moves.
  None of these is a hitbox command; `onFloat` (the float) and `onDSmash` change when a state is entered. They matter because Daisy's/Skull Kid's air moves run without their float logic.
- **[M:run]** stability of code-driven fighters: Daisy panics (`PANIC ppc: resolver returned NULL for guest address 0x8011C9E0`, `runs/probe_mex36/melee-pc.log` frame 624, VS probe, third Neutral B) and crashes in the LAB export (`CRASH code=3221226505`, `acehb_lab/ace_mex36.out`, frame 179); Knuckles crashes in the LAB export (`melee-pc.map rva 0x1049466D`, `0x01001008 (no module)`, `acehb_lab/ace_mex50.out`, frame 255) but ran the probe (86 action lines). Both ran the static dump fine.
- Code-driven hit logic by symbol name (**[R]** `dump_ftfunction.py --symbols`, 15 fighters with symbols): per-state `*_Coll` callbacks everywhere (retail pattern: `SpecialN_CollCB`, `SpecialHiStart_Coll` ...), B. Falcon `Rebound_Coll`, `SpecialN_OnTakeDamage`, `SpecialLw_Hit`; Diddy `Banana_OnHit`, `SpecialS_ThrowDetach`, `SpecialSStick_OnVictimGrabbed` (code grab: Monkey Flip holds the victim); Wolf `SpecialLwReflect*` (reflector states, with `SpecialLwReflect_GFX`); Lucas `OnAbsorb`, `PlayReflectSound`, `Catch_CheckEnterRebound` and the `onAbsorb` slot (12). Lucas TDX also overrides `onAbsorb` (slot 12, PSI Magnet; the runtime comment says Lucas is the only Akaneia fighter that does, ACE adds TDX).
- **Reflect and absorb are not ftcmd commands**: the retail op list (10-56, section 3.1) has no reflect/absorb opcode; they are state callbacks plus the engine's `ReflectDesc`/`ShieldDesc`. Geno models them for articles (`hits.reflect`, `hits.absorb`, `docs/geno.md` 2163) and shows them in LAB HITBOXES (`HIT` switch, `docs/geno.md` 373).

### 3.6 Gecko codes that touch hit code (not run by the port)

- **[R]** `dump_gct.py --range`, mapped to decomp symbols through `config/GALE01/symbols.txt`: 569 functions are patched by the 1169 codes; the hit-related ones are `Fighter_ProcessHit_8006D1EC` (3 codes: 0x8006D480/0x8006D48C change a compare against `lwz r12,328(r2)` minus 5/6 = the m-ex "bosses last" count; 0x8006D654 is the onAbsorb dispatch), `ftColl_8007A06C` (2 codes at 0x8007A180/0x8007A430: skip when a Fighter-struct flag, `+0x21FC` bit 1, is set), `ftColl_8007B320` (one 992-byte C2 at 0x8007B4C0: a per-fighter table-driven rewrite of hurtbox/hit-bubble set-up with limits 10 and 11), `lbColl_80009F54`/`lbColl_8000A244` (capsule maths), plus UCF-style input fixes in `ftCo_Attack100_CheckInput` / `AttackHi4/Lw4_CheckInput`.
- The port implements 49 `Mex_Enabled` flags (`docs/MEX_PORT_STATUS.md`); none is hit-related. Whether the retail decomp's behaviour in those five functions already equals the patched behaviour is **owed**; the 26 retail fighters' measured hitboxes being identical to vanilla (section 1) only shows the scripts are unchanged.

### 3.7 Articles / projectiles with hitboxes

- **[M:probe]** mex-layer items P1 owned (table in section 1): 22 of 31 fighters spawn at least one non-vanilla article kind in the 5-trial special set. Examples of an article hit connecting, `dealt` damage after staling: Wolf blaster `3.0`, Diddy popgun `3.0`, Charizard flame `2.0`, Lucas PK Fire `3.0`, Raichu Thunder `10.0`, Zero shot `5.0`, Blastoise Hydro Pump `12.0`, Chun-Li fireball `8.0`, Luigi & Boo Boo `7.0 / 13.0 / 9.0`. The probe's `on_hit` info carries `item=true` and `dealt`, not the article's own angle/kbg/bkb; those live in the article's item data and are **not extracted** here (owed).
- Confounder: the default match spawns stage items; vanilla-layer owned items (kinds 1, 4, 11, 12, 14 ...) are those, plus the clone base's articles (Giga Bowser's flame, kind 100). Only mex-layer kinds are counted as ACE articles.

## 4. Per-fighter notes (R2)

Format: ground specials from **[M:lab]** (`s` startup, `a` active frames, `t` total, `hb` hitbox rows), then what stands out.
"x N" = hitbox creations in a move (**[M:dump]**, own moves). Probe hits are **[M:probe]**.

- **Wolf (27)**: Neutral B no fighter hitbox (blaster = articles 253/254, `dealt 3.0`); Side B s22 a22 hb3 electric (18 damage, shield 20 in the LAB row); Up B s26 a26-55 hb2; Down B s1 a1 hb1 (reflector; `SpecialLwReflect` code state). 342 creations; `Attack100Loop` x15. Electric 5, slash 18. All fighter hits ids 0-3.
- **Wolf SSBU (52)**: shares Wolf's blob (same `0x3F88`, 21 overrides). Neutral B s11 a11 hb2 (articles 340/341), Up B 10 windows (s27 ... 43, 48-54, hb6). 407 creations, slash 57 (more sword-like Attack set).
- **Diddy Kong (28)**: Side B s12 a12-34 hb2, Up B s8 a8,10-27 hb19 (rocket barrel; live bkb 50..54 varies by code, 3.3), Neutral B/Down B no fighter hitbox (popgun 257/258, banana 259). Code grab: `SpecialSStick_OnVictimGrabbed`, `SpecialS_ThrowDetach`, `Banana_OnHit`. The probe's Side B pulled Mario into a hold (a later trial hit a teleport refusal, `TELEPORT-REFUSED`).
- **Charizard (29)**: fire 77 hits, no-clank 81, set-kb 68. Up B (flight) `SpecialHi x32`, s9 a9,11,13,...,23-24 hb8. Neutral B flame article 262 (`dealt 2.0` falling to 1.66 in one stream = multi-hit article), Down B 263/264. Clone base Koopa.
- **Lucas (30) / Lucas TDX (37)**: electric 91 / 76 hits. Specials are article-driven (PK Fire 266/267..., PK Thunder 269-273, 5 kinds, Side B article hits `3.0 / 6.37 / 2.73` (one stream)); LAB shows Neutral/Side/Up B with hb0, only Down B s28 a28 hb1. Lucas' F-smash and grab each own an article (274, 275: `onFSmash`/`onCatch` hooks). `onAbsorb` override = PSI Magnet. Largest blob (0x7DC8, 28 overrides).
- **Sonic (31)**: Neutral B s35 a35-39 hb1, Up B s2 a2-30 hb1 with spring 277; Side B shows hb0 in the LAB but the live probe hit with a 9-damage electric box at range 28 (action 358, `kbg 120 bkb 30 angle 40`), i.e. the LAB's chain for Side B (Special10>14>11) does not reach the hitting state; use the probe (3.3 caveat on LAB). 393 creations.
- **Sonic BM (43)**: Neutral B s26 a26-36 hb1, Side B s14 a14-34 hb2, Down B s12 a12-71 t300 hb1 (long spin); articles 320/321/322.
- **King Dedede (32)**: `Attack100Loop` x36 (rapid jab: 36 creations), fire 16, catch 16 (Dedede inhale/spit are code states: `SpecialNEat_Coll`, `SpecialNSpit_Coll`, `SpecialNGrab_Anim`). Neutral B s17 a17-59 hb3; Up B s71 a71-84; Side B article 280 (`10.92` per hit), Up B article 281 (`7.28`).
- **Tails (33)**: Side B s18 a18-20,30-33 hb6; Up B (tail flight) s16 a16, 23-24, 32-33, ... 68-69 (7 windows, hb1); 562 per-bone intangible events (3.4); 476 creations, 212 are angle 361. Neutral B Tails Bomb/article 284.
- **Wario (35)**: Neutral B s5 a5,7,9,...,21-22 hb4 (waft/bite multi-window), Side B (bike) s14 a14-37 hb2 plus six 0-damage `inert` boxes at its start and jump (static), Up B s5 a5-28,38-40 hb6, Down B s29 a29-38 hb4. No articles (the probe's items were stage items). `AttackAirB` live bkb 55 not in the static scripts.
- **Daisy (36)**: no LAB data (LAB run crashed, 3.5). Static: 3 non-grab 0-damage boxes (ThrowLw angle 270 wbk 20, retail Peach has the same), 2 `inert`. Article 290 on Neutral B. Override `onFloat` is not dispatched (3.5).
- **Raichu (38)**: electric 145; `SpecialSHold x101` (a 10-damage electric box re-created while the move is held; loop, 1011-frame walk limit); Side B s17 a17-70,75-100 hb5; Down B s40 a40-48 hb1; Neutral B article 304 (`10.0` / 9.1 / 8.3 in one stream). `leadead` x5.
- **S. Mewtwo (39)**: 839 creations (second highest), dark 45, fire 14, 812 per-bone intangible events (3.4); Neutral B s32 a32-37 hb2, Side B s12 a12-15,40 hb3, Up B s20 a20-39 hb4, Down B total 1 hb0 (the LAB chain ended at once; not understood, owed). Articles 307, 309. Clone base Mewtwo.
- **Skull Kid (40)**: hitbox id 4 (3.2); dark 28; article 310 is present in almost every trial (a standing helper, like Boo); 311/312 appear with F-smash and U-smash; Side B s35 a35-37,40-42,45-47 hb1 (3 windows). `onFloat` not dispatched.
- **Fay (41)**: Fox clone; Neutral B hb0 (articles 313/314), Up B s22 a22-27 hb1, Down B s1 a1 t36 hb1 (same timing shape as Fox's reflector). Article 317 on Side B. Static creation count equals Fox's (361 vs 361).
- **Meta Knight (42)**: slash 136; `SpecialSDrill x30` (drill rush, 30 windows `s23, 26, 29 ... 50` every 3 frames), horizontal angle 0/180 x30; Neutral B s13 a13-56 hb3, Up B s12 a12-40 hb4. No articles. `AttackS4S` live damage artefact (3.3).
- **Luigi & Boo (44)**: Boo (324) is an always-present helper article; its hits arrive as article hits (Neutral B `7.0`, Down B `13.0`, Side B `9.0`) in the probe. Up B s5 a5-23 hb3; Neutral B/Down B t0/t1 hb0 (no fighter hitbox). `onDSmash` override not dispatched. Coin 8 (Luigi base).
- **B. Falcon (45)**: only 4 overrides, but the biggest delta vs the static scripts: Side B `inert` 0-damage box, Up B `catch` box (1 damage), Down B 3 fire steps (9/12/15 damage, angles 90/80/361). `Rebound_Coll`. `MoveLogic table missing`.
- **Metal Mario (46)**: coin 40 (same as Mario), set-kb 114 (Mario clone with metal), Down B s8 a8,12-13,...,38-39 hb7, article 325 (fireball, `15.0 / 13.65` hits: heavy).
- **Dr. Luigi (47)**: Side B s22 a22-57 hb1 (live 9-damage normal, 80/20); Down B s6 a6-9,11-14,...,43 hb5 (5 windows); article 328; `AttackAirF`/`AttackAirB` live bkb 10 vs script.
- **Ninten (48)**: electric 48; no-clank 77 (PSI moves); `SpecialHi x23` (PK Thunder-like); articles 329 (Neutral B) and 331 (F-smash); LAB: Up B s45 a45-47 hb1 only.
- **Metal Sonic (49)**: 1026 creations (the most): electric 588, fire 130, `SpecialLwLoop x143` (+ `SpecialAirLwLoop x143`), Down B spin dash described in 3.3, `SpecialHi` x63 (fire, shield 5, id 2). No articles. Negative shield damage here only.
- **Knuckles (50)**: Neutral B article 337 (the probe saw it on Up B); LAB crash (3.5), static ok. Down B `SpecialNRebound_*` states (rebound on hit, code).
- **Zero (51)**: slash 98, fire 60, electric 56; `SpecialAirHi x44`, Up B s4 a4-6,8-9,... hb16 (16 windows), Down B s13 a13-24,26 hb6; article 338 (buster `5.0 / 4.55 / 4.15`); no-clank 126.
- **Lucina (53)**: Mars clone; Neutral B (Shield Breaker) bkb 30 -> 34 -> 40 live = charge in code, Side B (Dancing Blade) angle 76/80/85/96 kbg 25 bkb 55 (4 variants), Up B 6 windows; `MoveLogic table missing` (3.5); no articles.
- **Blastoise (54)**: ice 4, `leadead` 1; Up B s5 a5-30 hb10 (`SpecialHi x28`), Side B s14 a14-27 hb2; articles 344/345 (Hydro Pump `12.0 / 10.9 / 9.96`, Down B `2.0 / 1.8`); 96 per-bone intangible events.
- **Chun-Li (55)**: `SpecialS x24` (Side B s17 a17-18,21-22,... 75, 81-82 hb8: Hundred Rend Kicks), Up B s3 ... hb14 (Spinning Bird Kick), `AttackLw4 x22`; fireball article 348 (`8.0`); no-clank 62; no `Fighter`-specific code size (hdr 0 / 13312).
- **Shadow (56)**: dark 9, fire 29, electric 16; meteor band 28 (ground-only 10); `AttackAirN x26`, `SpecialLwHold x11`; Neutral B s45 a45-50 hb1. No articles seen (probe).
- **Toad (57)**: fire 20, no-rebound 103, no-clank 87 (headbutt/up B); Side B s3 a3-8 hb2, Up B s5 a5-17 hb4; article 354 (`5.0`).
- **Giga Bowser (58)**: ice 25, electric 23, dark 12 hits, 1 override (`onLoad` only; `MoveLogic table missing`); Side B s16 a16-18 hb4 (live: catch + slash 10/12 dmg bkb 80), Up B s5 a5-46 hb7, Down B s40 a40-51 hb1 (25 damage, 90/100/15 live), `AttackLw4 x25`; hitboxes up to size 18.8 (Attack Dash/Hi4). The loader gives it the Mario base; behaviour is data + the `PlGkp` script.

## 5. What Geno's authoring tools would need (R4)

Workbench fields today (**[R]** `tools/blender/geno_workbench/api.py` `EDITABLE` / `ADDABLE`): `bone, damage, size, x, y, z, angle, kbg, fkb, bkb, start_frame, end_frame` (add: the same minus bone, plus `duration`). `.genoasm` `hitbox` (**[R]** `tools/geno/script.py:205`) already takes `slot, joint, damage, size, x, y, z, angle, kbg, fkb, bkb, element, shield, ground, air` and `item_hit, ignore_thrown, ignore_scale, clank, rebound, sfx_kind, sfx_severity, header_bits`; plus `clear_hitbox`, `clear_hitboxes`, and Geno ops `REHIT`, `LINK`, `HBDMG`, `HBSTUN`, `HBFLAGS`.

| ACE type (section 2/3) | expressible in `.genoasm` | in the Workbench Hitbox panel | missing / needed |
|---|---|---|---|
| plain hit (damage, angle, kbg, bkb, size, offset, joint) | yes | yes | none |
| set knockback (`wbk`) | `fkb` | `fkb` | none (label it "fixed/weight-set kb") |
| angle 361, meteor, horizontal | yes (`angle` 0-511) | yes (numeric) | angle presets (361, 270, 0/180, autolink) |
| element (normal ... leadead) | `element` | **no** | element dropdown with the 17 names; `catch` = grab box needs an `only_hit_grabbed` toggle too |
| shield damage (+ negative, Metal Sonic -3) | `shield` | **no** | field; allow negatives (-128..127) |
| hit_ground / hit_air | `ground`, `air` | **no** | two toggles |
| clank / rebound / item_hit / ignore_* / sfx kind+severity | yes | **no** | an "advanced" foldout |
| hitbox slot / id (0-3; Skull Kid id 4) | `slot` limit 0-3 | row ordinal only | slot field; decide id 4 policy (3.2): refuse or support `xDF4[0]` |
| hit group (header bits 20-22), only-hit-grabbed (19), common-bone ids (10) | only through opaque `header_bits` (bits 10 and 19..22 allowed) | no | named `group`, `only_hit_grabbed`, `common_bone` fields |
| sweet / sour, clean / late (concurrent boxes, damage change over time) | `hitbox` x N, `HBDMG` | rows only | a per-move "stack" view: concurrent slots, window per slot, `HBDMG` events as keyframes |
| multi-hit (rehit loops: Metal Sonic, Dedede jab, Raichu hold, Chun-Li kicks) | repeated `hitbox` / `REHIT mask N` | frames only | "rehit every N frames" field (REHIT) and a loop-length check |
| throw hitbox (op 34: damage, angle, kbg, wbk, bkb, element, sfx; id 0 + id 1) | raw op 34 only (no named form in `script.py`) | no | named `throw` statement with its 9-bit fields |
| per-bone hurtbox state / body state (op 26/27/28) | raw ops | no | `hurtbox bone=.. state=intangible` and `body state=` statements, drawn in the timeline strip |
| grab box (`catch`) and follow-up pummel (`only_hit_grabbed`) | `element=8` | no | covered by element + `only_hit_grabbed` |
| article / projectile hitbox | JSON `articles[].hitboxes[]` (`damage, size, offset, angle, kbg, wkb, bkb, element, shield_damage, sfx_*, start, end, hits{ground,air,reflect,absorb,counter}`; **[R]** `docs/geno.md` 2150-2180) | no | Workbench article panel; parity with the fighter fields (element, shield, rebound) |
| reflect / absorb / counter | articles: `hits.reflect/absorb`; fighter: state callbacks only | no | a reflect/absorb "bubble" box type (the `ReflectDesc`/`ShieldDesc` data) for fighter states |
| hitbox values written by code (charge, per-frame bkb: Diddy Up B, Lucina Neutral B, Giga Bowser) | `HBDMG`/`HBSTUN`/`HBFLAGS` cover damage, stun, flags | no | a charge-scaled damage/bkb op; today these need a native hook |
| code-created hit logic (`*_Coll` callbacks, code grabs: Diddy Monkey Flip) | `CALL` a registered hook | no | out of scope for hand authoring; keep as hooks |

Priority if time is short: element, shield damage (signed), ground/air toggles, slot, then a throw statement and a hurtbox-state
statement. Those four cover 100% of the field-level differences between ACE's added fighters and what the Workbench edits today;
the rest of ACE's "types" are patterns of the same fields over time.

## 6. Limits and owed

- No hitbox of the added fighters was watched on screen; everything is numbers from headless runs. Whether a hit **feels** the same, and whether the id-4 box connects, are owed (a human with a monitor).
- Specials in the LAB export follow the LAB's input chain, which can miss states (Sonic Side B reaches the hitting state only in the live probe). Treat LAB `hb0` on a special as "no hitbox on that chain", not "no hitbox".
- The probe is 5 specials-class inputs x 3 ranges against an idle Mario. Air versions, smash charges, held inputs and counters were not exercised. Stage items in the default match confound item hits (3.7). Daisy's probe stops at her third Neutral B (panic).
- Articles' own hit data (angle, kbg, bkb) is not extracted; only `dealt` damage.
- Kirby (ck4) and Mewtwo (ck10) are missing from the static retail comparison (they are in the LAB comparison). Kirby is deprecated for this project.
- Gecko-code effects on hit resolution are read, not measured (3.6).
- Counts in section 2 exclude common-state hits; the dump walks scripts statically, so conditional branches (`IF` / `IFV`) show their fall-through path only (`conditional` flag in the dump).

## 7. Reproduce

```
bash tools/port/agent_new.sh acehbg                       # game worktree + build root, then tools/port/build.sh
export GW_MELEE=<worktree> GW_BUILD_ROOT=<root>
bash tools/research/ace_hitbox_batch.sh       <out>/acehb_dump     # static gd.timeline, all fighters, both discs
bash tools/research/ace_hitbox_lab_batch.sh   <out>/acehb_lab      # LAB measured export, needs the geno-lab mod copy
bash tools/research/ace_hitbox_probe_batch.sh <out>/acehb_probe    # live specials probe
bash tools/research/ace_interp_scan.sh        <out>/interp_scan.txt
python tools/research/ace_hitbox_report.py <out> types codemod cards diff
```
