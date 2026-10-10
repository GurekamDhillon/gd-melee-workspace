# What ACE's hitbox id 4 really does (2026-10-10)

Lane `ws/research-ace-hitbox-slot4`. Follows `_research/ace-hitbox-types-2026-10-10.md` (finding 3.2) and supersedes its
claim that the id-4 box is merely "an alias nobody checked": this note measures it. Dated note; it wins over 3.2 where they differ.

Tags: **[M]** measured in a run, **[R]** read from code/data (file or address named), **[I]** inferred.
No disc bytes are committed; this note quotes addresses, instruction mnemonics of the mod's patches, and gameplay numbers.

## Answer

1. **[M][R]** On ACE's own code, hitbox id 4 is real data that does nothing in combat. The create-hitbox handler indexes
   `fp->x914[id]` with no bound; id 4 lands on `fp->xDF4[0]` (the first throw record). The disc's `main.dol` polls four capsules
   everywhere, and none of ACE's 1169 Gecko codes touches those loops, the handler, the command table, or the struct layout.
2. **[M]** In the port with ACE data the id-4 record goes `state 1` (enabled) at the event, stays `1` for the rest of the match
   (never the 2 -> 3 sweep states ids 1-3 use), its world position stays (0,0,0), and no connected hit was ever attributed to it.
3. **[I]** It reads as an authoring slip, not a deliberate fifth slot: the move uses ids 3,2,1,4 (id 0 free, four live at frame 12),
   i.e. the author wanted four simultaneous boxes and numbered them 1-4. Skull Kid uses id 0 in 130 other creations, so he did not
   think ids are 1-based everywhere. The intended-but-missing box is the 2.34 bone-48 hand box paired with id 2 (bone 55); the
   frame-12 pair is the other arm. Confidence on "inert in real ACE": high (code read on the real DOL + Gecko list); not yet
   confirmed on Dolphin (see Owed).

## R1: every ACE Gecko code that could touch hit code

**[R]** `tools/research/ace_gecko_map.py` maps all 1169 codes in the ISO's `codes.gct` to decomp symbols
(`melee/config/GALE01/symbols.txt`). Codes landing in hit-related functions (output saved in the build root as `gecko_all.txt`):

| address | decomp function | what the patch does (disassembled, `tools/mex_port/ppc_disasm.py`) | hit slots? |
|---|---|---|---|
| 0x8006D480, 0x8006D48C | `Fighter_ProcessHit_8006D1EC` +0x294/+0x2A0 | replaces `cmpi r0,28` / `cmpi r0,27` (Master/Crazy Hand ids) with a compare against `(r2[328]-5)` / `(r2[328]-6)`: the "boss fighters are the last N internal ids" rule, id count is now data | no |
| 0x8006D654 | `Fighter_ProcessHit_8006D1EC` +0x468 | replaces `addi r0,r3,6152` (vanilla table slot) with `lwz r12,376(r2); lwz r12,12(r12); lwz r0,48(r12)`: fetch the m-ex per-fighter `onAbsorb` function pointer | no |
| 0x8007A180, 0x8007A430 | `ftColl_8007A06C` +0x114/+0x3C4 | prefix to `lwz r0,48(r4)`: `lbz r12,0x21FC(fp); rlwinm bit1; if set, branch to 0x8007A6A8` (skip the hit effect/sound block when a fighter flag is set) | no (effects) |
| 0x8007B4C0 | `ftColl_8007B320` +0x1A0 (992-byte C2, replaces the function epilogue) | builds m-ex "dynamics" tables from the costume file: fp+0x2F0 (24-byte records, error text "costume uses more than 10 dynamics", counter fp+0x3E0) and fp+0x1670 (40-byte records, "more than 11 dynamics hit", counter fp+0x166C). These are physics/cloth bones. The earlier note's "limits 10 and 11" are these | no |
| 0x80009FA4 | `lbColl_80009F54` +0x50 | debug hit-capsule draw colour: reads float at +12 (scale), derives a byte, stores it at `r13-0x8000+1,+2` (colour alpha/animation of the develop-draw bubbles) | no (visual) |
| 0x8000A284 | `lbColl_8000A244` +0x40 | debug hurt-capsule draw: if state byte and `hurt+0x48` are 0, use an in-patch 4-byte colour instead of `lbColl_803B9928[state]` | no (visual) |

- Plus UCF-style input fixes (`ftCo_Attack100_CheckInput`, `ftCo_AttackHi4_CheckInput(NoD0)`, `ftCo_AttackLw4_CheckInput`),
  m-ex table redirections in `ftData_*`, `Fighter_Create`, `Fighter_UnkInitLoad`, `ftParts_*`, `ftAnim_*`: all data-source swaps, none addresses a hit capsule.
- **[R] Whole-patch scan:** every instruction in every C2 payload was checked for `addi/mulli` with 0x914, 0xDF4, 0x1064 or the 0x138 stride and for loads/stores with displacement in [0x914, 0x119C) on a fighter pointer. Only item-struct offsets matched (0xFCC, 0xBC0). **No Gecko code reads or writes `x914[]`, `xDF4[]` or `x1064`.** (Script: inline in this lane; reproduce with `ace_gecko_map.py --disasm` then grep, or see `ace_dol_hitscan.py` for the DOL half.)
- **[R] The hitbox command table is vanilla:** `ftAction_803C06E8` (49 entries, data 0x803C06E8) contains `ftAction_8007121C` at slot 1 in the ACE `main.dol`; no 04/C2 code targets 0x803C0600-0x803C0900.
- **[R] The ACE `main.dol` is byte-identical to vanilla in all hit-array users:** `tools/research/ace_dol_hitscan.py` output for the ACE and vanilla ISOs is identical (diff empty). Loops over `x914` use `cmpli rN,4`: `ftColl_8007AE80` (0x8007AEB8, per-frame capsule update), `ftColl_8007AFF8` (0x8007B02C, clear all), and the compare-4 sits next to the 0x138 stride in `ftColl_80076808, 8007699C, 80076CBC, 80076ED8, 80077970, 80078A2C, 80078C70, 8007925C, 8007BC90` and `ftDrawCommon_800805C8`.
- Answer to "enlarges the array / 5th polled slot / relocates storage": **no, no, no.** m-ex's own per-fighter code (Skull Kid's `PlSd` blob, 28448 bytes, 14 overrides) was scanned too: no reference to fighter offsets 0x914/0xDF4/0x1064/stride 0x138 (the only hits are `stw 0xDD4` on item structs).

## R2: m-ex docs

**[R]** `_research/mex-*.md`, `docs/MEX_PORT_STATUS.md`, `tools/mex_port/README.md`: no statement about hitbox counts (the only "hit box" hit is the CSS cursor bounds). No m-ex release notes are local. m-ex's contribution to hit code is the three Fighter_ProcessHit tweaks above plus `onAbsorb`/dynamics. Not an authoritative negative for the m-ex source itself (no m-ex source is checked out here): **owed** a look at m-ex's repo for a "hitbox" mention, but the executable evidence (DOL + Gecko) already covers what the ACE disc runs.

## R3: what the id-4 box does on ACE

**[R] Setup on the real path.** `ftAction_8007121C` (create hitbox): `hitbox = &fp->x914[cmd->id]` with a 3-bit id and no range check -> id 4 = `&fp->xDF4[0]`. It sets `state=Enabled`, group, `fp->x2219_b3=1`, bone, damage/size/offset/angle/kbg/bkb/element. It calls the position initialiser `ftColl_8007AD18` only when the running proc's `s_link > 9`. `hitboxes_clear` (op 16, `ftColl_8007AFF8`) clears slots 0-3 only, so xDF4[0] is never cleared.

**[M] Port with ACE data, diag build.** A throw-away diagnostic build (game worktree `agent/aceslot4g`, uncommitted; patch saved as `tools/research/slot4_diag.patch`): `gd.hitboxes(port,true)` slot 4 reports `xDF4[0]` instead of the thrown hitbox, and the create handlers log `DIAG4` for id >= 4. Probe `tools/research/slot4_probe.lua`: Skull Kid (mex:40) up-tilt (motion 56 `AttackHi3`) vs idle Mario at x = 6, 9, 12, 15, 18, 21, -6, -9, -12, -15, FD, turbo, offscreen.
- Log: `DIAG4 fighter create_hitbox id=4 port=0 motion=56` x 7 in one run, i.e. the event fires every up-tilt.
- Slot 4 per frame (`HB` lines, 435 lines with id=4): every one reads `state=1 bone=48 hx=0.00 hy=0.00 hz=0.00 r=2.34`. Ids 1-3 go state 2 then 3 and move with their bones (e.g. x=18, f12: id1 (1.08,15.36,-5.25), id2 (-2.66,13.75,-0.86), id3 (-10.79,15.56,-3.24)). The id-4 record never leaves state 1 and never gets a world position, and it stays enabled until the match ends (45 frames after the move, and into the next trial).
- Connected hits (8 of 10 victim placements): all attributed to `hitbox=2` (bone 55, angle 84) or `hitbox=3` (bone 56, angle 110); none to id 4 / bone 48. Because all four boxes share hit group 0 a victim already hit at frame 8 cannot be hit again at frame 12, so the sweep alone would not prove id 4 inert; the static polling code and the never-updated position do.
- Caveat: the port runs the decomp (identical to retail code, shown above to equal ACE's DOL), not the disc DOL; this is the same logic, not an independent emulator.

**Other users of id >= 4.**
- **Fighters [R]:** the static dump of all 22172 ACE scripts (previous lane): one hitbox event with id >= 4 in the 31 added fighters (Skull Kid AttackHi3), 0 in the 24 retail fighters on ACE and on vanilla. Re-checked from the dumps (`acehb_dump/ace_mex*.jsonl`): id histogram per fighter is {0,1,2,3} for 30 of 31, plus `{4: 1}` for Skull Kid.
- **Articles [M]:** see the sweep table below (item create-hitbox handler `it_802790C0` logs `DIAG4 item`).

### Article/fighter id>=4 sweep (diag build, `ace_diag4_sweep.sh`, special_probe.lua)

**[M]** Completed probe runs (`ACEPROBEDONE` in the log) for ACE m-ex fighters 27-33, 35, 43-49 (15 fighters): **0 `DIAG4` lines**, i.e. no fighter or article
(item) hitbox-create with id >= 4 fired in their 5-trial special set, grab, jab, ftilt and smashes. Fighters 36-42 (except Skull Kid via its own probe above) and 50-58 were
not completed: the sweep ran ~15 minutes per fighter with two games in parallel and I stopped it (runs 36, 37, 50 were cut mid-way). So article coverage is **partial** and
only covers articles that spawn in that probe set; the complete fighter answer is the static one (1 event in 22172 scripts). A full article scan would need to parse the
item scripts (`ItemStateDesc.xC_script`) in each ACE `Pl*.dat`; owed.

## R4: reproducing and expressing it

Reality check first: **"faithful" is already what the port does** for ACE data: id 4 writes the throw record, nothing polls it. The question is whether we want that, or the author's apparent intent (a working fourth box).

Options (ordered by cost):
1. **Faithful, no change (recommended default for the ACE import).** Keep id 4 inert. Record it in the fidelity ledger as "authoring slip in the source mod: box never active in ACE either". Cost: 0. Risk: Skull Kid's up-tilt keeps the weaker coverage the real ACE has.
2. **Fix at import (recommended if the owner wants the intended box).** The importer rewrites any create/adjust hitbox id >= 4 to a free slot of that move at that frame (here id 0: free at frames 8-15). Data-only: no engine change, no netplay or snapshot impact, works in Geno moves exported from the Workbench. Must be flagged as a deliberate deviation (it makes Skull Kid's up-tilt hit slightly differently from real ACE).
3. **Engine: a real fifth polled slot (only if more than 4 simultaneous boxes are wanted).** Constraints found:
   - Do NOT grow `x914[]`: every m-ex fighter blob runs as PPC with hard-coded fp offsets (`ASSERT_SIZE(Fighter, 0x23EC)`, offsets after 0xDF4 are used by guest code), so any relocation breaks the 31 added fighters. The throw records at `xDF4[]`/`x1064` must keep their meaning (Throw/Thrown/Shouldered/CaptureCut read `xDF4[0..1]`).
   - The port already has the mechanism: `ftcoll.c` loops through `COLL_CAPSULE_COUNT/COLL_CAPSULE(fp,i)` -> `ScriptGame_EchoCapsuleCount/EchoCapsule` (`pc/gameworld/script_echo.inc:242`), which already returns `x914[0..3]` then up to 40 virtual capsules (`ECHO_COLLISION_CAPS = 4 + 8*5`) from `script_echo.rule[entity][..].capsule[..]`. A fifth slot = one more entry in that table (`index 4` backed by a per-fighter `HitCapsule` held in the echo state, not `xDF4[0]`), plus in `ftAction_8007121C`, `ftAction_8007162C` (adjust damage), `ftAction_8007169C`/`80071708` (scale, flags) mapping `id>=4` to it and in the per-frame updater `ftColl_8007AE80`, the clear `ftColl_8007AFF8`, `ftColl_8007B064` (single clear) and the debug draw `ftDrawCommon_800805C8`, which loop `ARRAY_SIZE(x914)` directly rather than through the macro.
   - Hit rules (`ScriptGame_HitRule*`) and `on_hit` info key off the `HitCapsule*`; the echo pool pointers are already recognised (`ScriptGame_EchoIsCapsule`). The LAB `lab_hit()` (`script_game.c:2156`) maps index 4 to `x1064_thrownHitbox`, which is why the LAB never showed the real id 4: it needs its own index.
   - Netplay/rollback: `Snap_CuratedRegion` snapshots the whole `Fighter` (`fighter.c:3356`), which would include nothing new if the capsule lives in the echo state; the echo state must then be in the snapshot (check `ScriptGame_EchoCapture/Reset` participation in rollback) and netplay protocol numbers would change if the hit set becomes a synced rule (decision for the owner, not made here).
   - Cost estimate: ~1 day plus a netplay pair test; behaviour change for every ACE fighter that already carries id 4 (just Skull Kid) and a new Geno capability.

**Geno expression.** The Workbench/Geno hitbox row has a `slot` limit of 0-3 (previous note, section 5). Propose: keep 0-3 as the authored range; the ACE importer reports `id>=4` as a warning row "out-of-range slot (inert in retail/ACE)" with a one-click "move to free slot N" (option 2). Only if option 3 is built does the field widen to 0-4 and the timeline strip draw five lanes; `docs/geno.md` should also stop calling id 4 "the thrown hitbox" (the LAB's slot 4 is `x1064_thrownHitbox`, the command's id 4 is `xDF4[0]`).

## Owed / not done
- **Dolphin run of real ACE not done.** The user allowed downloading Dolphin; the download (`dl.dolphin-emu.org/releases/2609a/dolphin-2609a-x64.7z`) was refused by the session's permission classifier ("untrusted code integration"), so no emulator was run. Dolphin would also need scripted input (no Lua in mainline Dolphin). A human with Dolphin can verify: `AttackHi3` frame 12, victim placed so only the bone-48 box could reach, expect no hit. Until then the claim "inert on real ACE" rests on [R] code reading of the actual DOL and Gecko list plus the [M] port run of the same logic.
- m-ex source repo not checked for hitbox mentions (R2).
- Articles: only those that spawn in the 5-trial special probe were covered (see sweep).

## Files
`tools/research/ace_gecko_map.py`, `ace_dol_hitscan.py`, `slot4_probe.lua`, `ace_diag4_sweep.sh`, `slot4_diag.patch`. Raw outputs (git-ignored, build root): `_build/agents/aceslot4/{gecko_all.txt,hitscan_ace.txt,slot4b.txt,slot4_melee-pc.log,diag4/}`.
