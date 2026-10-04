# Packet 10: Known gaps

Everything the course could not verify, where sources disagree, and what an author needs that does
not exist yet. Written 2026-10-03. If you fix one, delete its line.

## A. Not run, and what the 2026-10-03 test settled

The author wrote packets 0 to 3 without launching the game. A tester then ran them on a source
build with the vanilla disc, driving the game through the console socket and scripted pad input.
**Settled by that run** (no longer open): the `geno:` log lines of packet 1 (the shapes are now in
the text, with the corrections that the count line comes first and the fighter line has more
fields); hot reload on a vanilla Kirby (attributes and overlay words reload without a restart;
adding states restarts the match); `jumps.air_vy`; Kirby's `SpecialN` row being used by no other
state (the one-liner works; once Geno states exist it lists them too); the whole packet 3 recipe
(an overlay on a reused row, two Geno states, `specials` for neutral B on the ground and in the
air, a hitbox that hits for exactly its damage, a damage change by reload); `like` with a jab or
aerial motion id (entered without visible side effect); the hitbox word layout and the order of the
offset fields (x, y, z, read back as `ox`, `oy`, `oz`). Side, up and down B were unaffected.

**Found wrong and fixed in the text:** the jab's bone is not 2; the move was not cancellable until
the state sets `"iasa": "interrupt"`; with no offset the hitbox appeared behind Kirby (the reused
inhale animation); the LAB's `lab events`, `gd.timeline`, `lab card` and the frame-data export cannot
decode an overlay script (0 events); `lab events` takes no port argument; a level 0 CPU is not a
standing dummy (`gd.cpu_mode(2,"stand")`); the second log line of a layout-change reload.

**Still open** (the original list follows; items marked settled above can be struck when someone
rereads them):

0. **Kirby does not get past 6 jumps.** With `"jumps": {"max": 9, ...}` `gd.attrs(1).jumps_max` reads
   9 and the log says `max jumps 9`, but Kirby chained at most five air jumps (`jumps_used` 6)
   in every try, with the pad pressing jump every 2 frames or every 12 frames, and the line
   `... air jump N of 8 (beyond Melee's multi-jump table)` never appeared. `Geno_MultiJump` in
   `melee/pc/geno/geno_game.c` looks designed to repeat Kirby's last jump state; whether Kirby's
   last jump script blocks a further jump input is unchecked. Packet 1 step 6 now says only what
   was seen. A fighter that uses `JumpAerial` rather than Kirby's special jump states was not tried.
0b. **A scripted one-frame hold of B did not start the move**; three frames did. Probably the
   harness, not the game, but unchecked with a real controller.
0c. **Hot reload does not apply a change to a state's `iasa`** (and probably its other callbacks):
   after the reload B still could not cancel; a new match did. The reload log says the profile
   changed. Whether the other callback keys behave the same was not tried.
0d. **Kirby's copy abilities** could not be tested: with B bound the inhale cannot be entered, and
   the console has no command that gives a copy ability. Whether a held copy ability's neutral B
   asks Geno first is unknown.
0e. **The LAB cannot decode Geno overlays.** A tool that walks the overlay words (or at least
   `lab events` and the frame-data export taking the overlay when the state's row has one) would
   let a learner check a script against what they wrote.
0f. **Key presses and displays** (`6`, `V`, `T`, `D`, `3`, `F3`, `F5`, `F8`, the timeline's IASA mark,
   the HITBOXES panel) were not pressed or seen by a person. The console equivalents were used.

1. **Packet 1, step 3 and 5.** The `geno:` log lines are copied from the source's format strings,
   not seen. The console expression `= gd.attrs(1).gravity` follows the documented `gd.attrs(port)`
   return (`melee/docs/geno.md` 14.3) and the console's `=` form (`docs/scripting.md`).
2. **Packet 1: an overlay on a vanilla disc.** The reference states overlays attach to vanilla
   fighters. The only vanilla-disc run recorded is attributes plus an `on_init` hook on Marth
   (`_research/vanilla-single-folder-mods-2026-10-03.md`, RUNS case 5). Hot reload, `jumps`, states
   and `specials` on a vanilla disc are not recorded there.
3. **Packet 1: where the mod goes in a release build.** The course says `mods/` beside the game
   (`docs/mods-packaging.md` section 2.1). The release's exact layout was not read end to end.
4. **Packet 3, step 1: `SpecialN` as the free row.** That Kirby's neutral special state is named
   `SpecialN` and its row is unused by other states is expected, not checked. The console one-liner
   that lists states sharing an `anim_id` is untested Lua over the documented `gd.motion_list`
   table.
5. **Packet 3, whole: a Geno state on a reused row with a replaced script.** The pieces are each
   documented (overlay replaces a row's script; a state's `subaction` sets the row's `anim_id`; B
   binds through `specials`), but no document or test shows the combination working on a vanilla
   fighter. The nearest recorded case is Sora's "stand-in states on a host fighter's unused ItemScope
   subactions" (`melee/docs/geno.md` 19.8).
6. **Packet 3: `like` with a jab or aerial motion id** for a special-move state. It copies flags and
   the move id; whether a jab's flags cause side effects on a special input is unchecked.
7. **Packet 3: hitbox word offsets.** The axis order of the three offset fields is as the repository's
   encoder writes it and its authors say they checked it in game. Leave offsets at zero first.
8. **Packets 4 and 5: hand-encoded `PUT` and `CALL` words** are derived from the layout and from the
   two words the engine's test reproduces (`0xEC120100`, `0xED310000`). They were not run.
9. **Frame numbering.** The timeline may read one frame high (14.12, "Open"). The reference leaves it open.

## B. The reference and the code disagree, or are unclear

1. **"Does m-ex run PowerPC code?"** `docs/mods-packaging.md` section 1 says the port "never runs a
   mod's PowerPC code (no DOL patches, no `codes.gct`)", while section 2.3 says the m-ex function
   blobs inside a fighter's data file are relocated and run in a PowerPC interpreter. Read together:
   no DOL patches, but a fighter's own embedded callbacks are interpreted. The wording should say so.
2. **Roadmap version names.** `melee/docs/geno.md` section 13's roadmap calls `define` "v3" and
   glide "v2", while sections 16 to 19 use "v3" for root motion and "v5" for articles, and the file's
   `"geno"` field is up to 5. The README's list stops at v4. "v3" means two things.
3. **Section 1's customers.** It names Brawl Kirby as a first customer. The fighters in the tree
   today are Halberd, Ultimate Kirby and Sora (`ports/README.md`).
4. **The reference's date.** The top says "current as of 2026-09-27" while 19.13 is dated 2026-10-03.
5. **`geno.md` examples cite build outputs** (a demo mod folder, screenshots) that are not in the
   repository, so they cannot be reproduced. This course does not rely on them.
6. **Test counts in `geno.md`** (133/133, 149/149, 189/189) are historical per section, not current.
7. **README says "m-ex can't express"** while some table items (hook tables, custom items) overlap
   with m-ex in kind. The table in packet 0 is the careful version.
8. **`subaction` and `anim_id`** are the same number by the code (`geno_game_v2.inc`, `row->anim_id =
   anim`), but no document says so in one sentence. Packet 2 does.
9. **Standalone Geno items** (19.13) are being added today, "source update 2026-10-03", not run.
   They are not covered.
10. **Vanilla attach names.** The 27 names `attach` accepts are in `geno_registry.c` (the
    `gn_vanilla` table: `mario`, `fox`, `captain` or `falcon`, `donkey` or `dk`, `kirby`, `koopa` or
    `bowser`, ... `gnw`, `ganondorf`, `roy`, `marth`, `younglink`, `jigglypuff`); no document lists them.

## C. What an author needs that does not exist today, ranked

1. **A starter fighter an author can copy.** A small, committed, assets-free sample mod folder
   (`mod.json`, `geno.json`, one word file) that is known to load on a vanilla disc and does
   something visible. Packets 1 and 3 had to invent one. Nothing in the tree is both public and
   complete: the working Geno packs are generated into ignored build folders or need game data.
2. **A `geno.json` template with every key, commented.** JSON has no comments, so a documented
   example file or a schema (`geno.schema.json`) is needed. The reference describes keys across 20
   sections and the parser silently ignores unknown keys, so a typo costs an hour.
3. **A validator command.** Something like `geno_check mods/<id>`: parse the JSON as the engine
   does, check every key name, every target string, every `file`, every state's `subaction` index
   against the 0 to 1023 range, the 48-state and 16-article limits, the overlay words (lengths,
   forward skips), and warn on shadowed rows. Today the only feedback is the log after a game start.
4. **A script assembler and disassembler.** Authors hand-encode words. A small tool turning text
   (`wait 5`, `hitbox joint=2 dmg=8 ...`, `CHG ANIM_END -> GENO(0)`) into words, and words back to
   text, would remove the largest barrier. `hitbox_words.py` here covers one command; the LAB's
   `lab events` decodes but only reads the engine's walk and cannot export.
5. **A way to dump an existing move's script as editable words.** An overlay can only prefix or
   replace a script, so "change one number" in a stock move needs the original words, and there is
   no tool that exports a row from the user's own disc into a word file.
6. **A way to add animations and rows without the Ultimate/Brawl pipeline.** Geno states reuse
   existing rows. A small installer that adds a clip from a user's own animation file and a row
   pointing at it would let non-porters make new moves.
7. **A hand-authorable effect package and article model.** A minimal `.gfx.json` example and a
   documented route to an article `.dat` (or support for a simple mesh format).
8. **Geno-native fighters (`define`) and the one-folder vanilla design**, so an author's whole
   fighter is shareable. This is the largest piece and is already designed
   (`_research/vanilla-single-folder-mods-2026-10-03.md`).
9. **A packer and checker for mods** that refuses disc-derived files and writes `mod.json`'s hash.
10. **A way to add a hook without editing the engine**, or a documented process for it.

## Sources

Each item cites its own source above. Primary: `melee/docs/geno.md`, `docs/mods-packaging.md`,
`_research/vanilla-single-folder-mods-2026-10-03.md`, `melee/pc/platform/geno_registry.c`,
`melee/pc/geno/geno_game_v2.inc`, `ports/README.md`.
