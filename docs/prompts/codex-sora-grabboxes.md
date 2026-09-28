# Code task for Codex: Sora's own grab boxes (CATCH → Melee grab hitboxes)

**Revision 2 (2026-09-26), after the first attempt stopped correctly:**
- Rows are **Catch and CatchDash only**. Melee has no CatchTurn row, so `game_catchturn` is skipped
  (Melee's rules win). Acceptance: exactly those two rows change.
- The Ultimate fighter id is **`trail`** everywhere (dump agent Hash40(`trail`) = 0x5b268858f), not
  `sora`: e.g. `python ports/ir/tools/acmd_parse.py trail ${GW_GHIDRA_PROJECTS}/sora_acmd ...`.
- Step 1 is already answered by the first attempt: grab boxes are ordinary op-11 hitboxes with element
  `HitElement_Catch` = 8 (ftaction.c:178-181, 325-347; ftcoll.c:1626-1635; lb/forward.h:52-66).
  Still check a vanilla Catch script (Marth's) for the other fields a grab box sets (damage, angle,
  grounded/aerial bits) and match them.
- `ports/ir/tools/fighterbuild/`, `trail_magic_geno.py` and `ultimate_vfx_geno.py` have other agents'
  uncommitted changes; don't touch them.

Written 2026-09-26 by the coordinating Claude session. **Code only.** Do NOT build or run the game,
run build.sh/run.sh, launch other Codex processes, or profile. Write the code, run the offline checks
below, and stop. Claude builds, installs and tests in game afterwards.

## Background

Sora is ported from Smash Ultimate into Melee with our own tools. His move scripts are converted by
`ports/ir/tools/acmd_to_ftcmd.py` from our own ACMD dumps (Ghidra decompilation in
`${GW_GHIDRA_PROJECTS}/sora_acmd/game/*.c`, parsed by `ports/ir/tools/acmd_parse.py`) into
Melee fighter commands (ftcmd). Hitboxes, throws, JabCombo and IASA are already mapped. **Grabs are
not:** Sora's grab states (Catch, CatchDash, CatchTurn) still run the host fighter's (Marth's) own grab
script, so his grab range is Marth's, not Sora's. The Ultimate grab scripts use the `CATCH` macro
(`macros::CATCH` / `CatchModule`, `grab!(... MA_MSC_CMD_GRAB_CLEAR_ALL)` and the like). Files that
contain it: `grep -l CATCH ${GW_GHIDRA_PROJECTS}/sora_acmd/game/*.c`.

## What to do

1. **Find Melee's grab-box command** in the decomp (`melee/src/melee/ft/` - the ftcmd/subaction
   parser, e.g. `ftaction.c` or wherever the command table lives). Grabs in Melee are regular hitbox
   commands (op 11) flagged to grab, or a dedicated command; confirm which, with the word layout,
   from the source and from a vanilla fighter's Catch script (Marth's: how the host's catch script is
   read in `acmd_to_ftcmd.py` / `install_ultimate.py` shows where scripts come from). Write the
   finding with file:line citations into the report.
2. **Parse CATCH in `acmd_parse.py`**: id, bone, size, offsets (x, y, z and the optional x2/y2/z2
   extension), the status/situation argument, and the grab-clear calls. Mirror how `ATTACK` is parsed
   (Hash40 bone names are resolved the same way).
3. **Emit grab boxes in `acmd_to_ftcmd.py`** for the rows Catch, CatchDash, CatchTurn: grab box on at
   the CATCH frame, cleared at the clear call, using the same unit scale, bone mapping and x/y/z word
   order the ATTACK path uses (word1 low = X, word2 = Y<<16 | Z; see the existing hitbox encoder).
   Ultimate's extended (capsule) boxes: Melee has none, so use the existing ATTACK path's rule for
   x2/y2/z2 (read it and apply the same rule; do not invent a new one).
4. **Remove the fallback** that keeps the host's grab script for those rows, only once Sora's own
   version is emitted.

Keep the change general (any Ultimate fighter's CATCH), not Sora-only. Touch only `acmd_parse.py`,
`acmd_to_ftcmd.py`, and a new test file.

## Acceptance (you check these yourself)

- A new offline test `ports/ir/tools/test_acmd_catch.py` (plain `python`, no pytest needed) that
  parses Sora's three grab scripts from the dump and asserts: the frame each box turns on and off
  (read them from the decompiled C and write them in the test with a comment citing the file), box
  count, bone, size and offsets after scaling. It passes.
- Running `acmd_to_ftcmd.py` the way `ports/ir/tools/install_ultimate.py` runs it for Sora (copy that
  invocation, output to `_build/tmp/codex-grab/`, never into a mods folder) produces grab boxes in
  those three rows; print the decoded command words for each in the report.
- Every other row's output is byte-identical to before your change (diff the whole output against a
  run of the unchanged code; report the count of changed rows, which must be exactly those three).

## Rules

- No commits, pushes or merges; list the files changed.
- Game-derived data (the dumps and any outputs) stays under `_build/` or the Ghidra folder; never copy
  it into the repo, and keep test assertions to numbers, not pasted script text.
- If the task is wrong or impossible as written, stop and say so rather than working around it.

## Report (final message, also written to `_build/tmp/codex-grab-report.md`)

1. Melee's grab command and its layout, with file:line citations.
2. Files changed and what.
3. The decoded grab commands per row, and the test output.
4. The row diff count.
