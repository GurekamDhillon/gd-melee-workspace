# Slippi gameplay codes on the PC port

Every code in [project-slippi/slippi-ssbm-asm](https://github.com/project-slippi/slippi-ssbm-asm) tagged
`affects-gameplay` — the ones that change what the simulation does, as opposed to recording, UI or
lag reduction. A `.slp` recorded on console or online ran *with these codes patched in*, so a replay
only reproduces frame-for-frame if the port applies the same set. This file is the inventory: what
each code does, where it hooks on GC, whether the port implements it, and under which activation.

Nothing here is vendored. Each code was read as PowerPC, understood, and reimplemented in C at the
equivalent site in the decomp, with an attribution comment naming the .asm file and its GC address.

Source snapshot: slippi-ssbm-asm @ 2025-06 (54 `affects-gameplay` .asm files, 40 distinct codes).

## Activation

`gw_Slippi_Codes()` (pc/platform/gw_replay.c) returns the codeset in force:

| value | codeset | when |
| --- | --- | --- |
| 0 | none — vanilla 1.02 | default for live play |
| 1 | console / tournament (`console_core` + `mods_tournament`) | a replay whose Game Start says major scene != 8 |
| 2 | online (`netplay.json`) | a replay whose Game Start major scene == 8; `MELEE_SLIPPI_CODES=online` |

`MELEE_SLIPPI_CODES=tournament|online|off` overrides it for live play. `gw_Slippi_Version()` returns
the recording's Slippi version as `major*10000 + minor*100 + build` (999999 when not in playback), for
the codes whose behaviour changed across releases. `gw_Slippi_FrozenStadium()` reports the Game Start
Frozen-PS flag (Slippi 2.0+), or `MELEE_SLIPPI_FROZEN_PS=1` outside playback.

The online codeset is a superset of console for gameplay purposes except where noted; codes marked
"online" below are deliberately *not* applied to console replays, because a console recording did not
have them.

## Implemented

| code | GC hook | codeset | port site |
| --- | --- | --- | --- |
| Init Player Data | 0x80068EEC | all | `fighter.c` — `memset(fp, 0, sizeof *fp)` after `HSD_ObjAlloc` |
| Init Stage Data | 0x801C154C | all | `gr/ground.c` — `alloc_user_data_ground()` zeroes the 516-byte block |
| NanaDeterminism | 0x800AC5B8 | all | satisfied by the build: `-ftrivial-auto-var-init=zero` (`_build/masstest/pipe_win.sh`) zeroes exactly the locals the code initialises by hand |
| Frozen PS / IngameCheckIfFrozen | 0x801D45FC, `PokemonStadium_TransformationDecide` | console (toggle), online | `gr/grpstadium.c` — break out of the transformation decision, skipping its `HSD_Randi` draws |
| BrawlOffscreenDamage | Online/Core | online | `ft/fighter.c` `ftSlippi_IsOffscreen()` — off-screen 1% uses position vs `Stage_GetCamBounds*Offset` instead of the magnifier |
| DesyncProofBGTransformations (FD) | 0x8021AAE4 | online | `gr/grlast.c` — save/restore `*HSD_RandSeedPtr` across `grLast_8021B2E8` |
| FreezeGlitchFix | 0x801239A8 | online, console ≥ 2.0.0 | `ft/kinds/ftNana/ftnanaspecials.c` — skip `nana_fp->x1A5C = NULL` |
| WhispyBlowDirFix | 0x8008653C | online | `ft/ftlib.c` — fighters in a Dead motion (≤ 0xB) count for neither side |
| UCF 0.84: pad buffer + 1.0 cardinals | 0x8006B460 | all | `ft/fighter.c` `ftUcf_Cardinal`, `ftUcf_PadBufferPush` |
| UCF 0.84: dashback (+ 0.73) | 0x800C9A44 | all | `ft/kinds/ftCommon/ftCo_Turn.c` |
| UCF 0.84: shield drop, extended | 0x800998A4, 0x8009A0B8 | all | `ftCo_Escape.c`, `ftCo_Pass.c` |
| UCF 0.84: DBOOC SquatRv fix | 0x800D65EC | all | `ftCo_Turn.c` |
| NeutralSpawn | 0x8016E510 | all | owned by the `neutralspawn` agent (separate branch) |

## Not implemented

| code | GC hook | codeset | why |
| --- | --- | --- | --- |
| UCF 0.84: SDI | 0x8008E54C | all | **gap worth closing.** Decoded: inside `ftCo_Damage_OnEveryHitlag` (0x8008E4F0 + 0x5C); reads the UCF pad buffer two polls back and re-registers an SDI input when the squared 1-D stick delta exceeds 0x15F9 (75 raw units), so a flick smoothed away by poll timing still counts. The port has the pad buffer (`ftUcf_PadRaw`), so this is a contained follow-up. |
| UCF 0.84: Shield SDI | 0x80093294 | all | same mechanism, guard variant. Same gap. |
| UCF 0.84: Tumble | 0x800908F4 | all | same mechanism, tumble variant (threshold 0x15F9 against `fp+0x628`). Same gap. |
| PreventWobbling | 0x800DB880, 0x800DBBD4, 0x8008F090 | online, `console_gameplay_wobbling` | Semantics understood: the two init hooks sit at the tails of `fn_800DB790` / `fn_800DBAE4` (CaptureWaitHi/Lw enter) and clear a wobble counter (`fp+0x2384`) and last-move id (`fp+0x2386`) on the victim; the check counts alternating-move hits from an IC leader while the victim is in CapturePulledHi..CaptureDamageLw, and on the 4th, in singles, throws grabber and Nana into CatchCut / CaptureJump. Not landed because the check's injection point (0x8008F090, exit 0x8008F0C8) is 0x400 bytes into `ftCo_8008EC90`, a 2.8 KB function, and placing it needs the 1.02 disassembly to identify which branch it interrupts — guessing would silently change every grab. Needs a disassembly pass, not more reading. |
| FreezeDeadUpFallPhysics | 0x800D4C1C, 0x800D4D68, 0x80080E80 | online | Replaces screen-KO fall physics with its own integrator and moves the model through the camera's inverted view matrix, so Nana's decisions can't depend on screen shake. Needs three coordinated hooks plus repurposing `fp->mv.co` bytes 0x48/0x4C/0x50/0x5C-0x64 as its state. Real work, narrow payoff (screen-KO'd fighters only); deferred deliberately. |
| PSCameraIndependentMonitor | `PokemonStadium_Main` (0x801D24FC) | online | Replaces the monitor-transition trigger with fixed bounds (±120 x, +80/-20 y) so the zoom is camera-independent. Cosmetic-adjacent but tagged gameplay; deferred with FreezeDeadUpFallPhysics. |
| Stadium online hacks: CustomZeroBuffer, GrPsxIsValid, StadiumFileLoad | 0x801C65C8, 0x801D4760, 0x800165AC | online | Work around the GC's transformation file streaming (load-time determinism). The port loads stage files synchronously from the ISO, so the hazard they guard against does not exist here. Skipped as not applicable. |
| Preload Stadium Transformations (5 hooks) | 0x801D14C8, 0x801D45EC, 0x801D4F14, +2 | online | Same reason: a preload cache for DVD streaming the port does not need. Skipped as not applicable. |
| Frozen All (4 hooks) | 0x8021AAE4, `grStadium_801D1520`+0x28, `grStory_801E3334`+0x14, data 0x803E67E0 | optional console toggle | A tournament-organiser toggle, not something a recording implies. Frozen PS (the one a replay records) is implemented. |
| FreezeFDSlippi | 0x8021AAE0 | online | The author's own note says it is only active alongside DesyncProofBGTransformations, which the port implements; separately freezing FD's background would *reduce* replay fidelity. |
| PortPriority (8 hooks) | FighterGrab, LedgeGrab ×2, ThrowHitstun ×5 | online | Makes simultaneous grabs/ledge-grabs resolve by port order rather than by GObj list order. The port preserves the GObj list order, so vanilla and this code agree except in exact ties; deferred pending a replay that actually shows a tie. |
| UCF 0.8 (Logic/DB, SD, Tumble) | — | superseded | 0.84 is what every recording in the corpus used. |
| PAL | many | `PAL` codeset | A full ruleset port (knockback, hitboxes, character values), not a determinism fix. Out of scope; would need its own branch. |

## Validation

Baseline = the pc-port build before these commits; new = with them. `tools/replay/first_div.py`
against the console trace, three replays:

| replay | baseline first divergence | with codes |
| --- | --- | --- |
| RustyJuicyElephant (online, 3.19) | x @ 1596 p0: console 53.42115 / port 47.94615 | unchanged |
| Gang-Steals/10/Game_20190309T081336 (FD, 2019) | action_state @ 1145 p0: console 179 / port 226 | unchanged |
| Gang-Steals/10/Game_20190309T164635 (Stadium, 2019) | action_state @ 48 p0: console 212 / port 89 | unchanged |

No regressions, and no improvement on these three either — expected: none of them is an Ice Climbers
match, none has a screen KO before the divergence, and the FD/Stadium pair are console recordings, so
the online-only codes correctly do not apply to them. Frame 1596 on RustyJuicyElephant is a vanilla
decomp issue, not a missing code: console applies a one-time +5.475 x shift on Marth's ledge action
183 → 193 that the port does not (handed to the accuracy agent).

The zeroing codes (Init Player/Stage Data) are the ones that matter most in practice — they remove
stale-heap nondeterminism the decomp's own `@bug` notes describe, and they apply to every codeset.

The headless suite passes:
`bash tools/port/run.sh --test tests --iso "C:/iso/Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso"`.
