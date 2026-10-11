# Goku XV2 to GD's Melee: v0.2 shallow handoff

The main deliverable is [the source character IR](ir/goku.xv2.ir.json), compared
with [the Falcon host IR](ir/host.melee.ir.json). Root `parity[]` is the bridge
used by art and gameplay tools. Read [PARITY.md](PARITY.md) and
[ROLE-MAP.md](ROLE-MAP.md) before changing a mapping. The
[XV2 engine conventions](../ir/schema/engines/xv2.md) define scoped indices and
extension semantics without changing the shared schema.

See [HANDOFF.md](HANDOFF.md) for completed gates, native run evidence, remaining
placeholders and the renderer shutdown fault. Launch with
`& 'E:\Projects\Melee Workspace\ports\goku-xv2\tools\play.ps1'` in PowerShell.

## Local paths

| Artifact | Full path |
|---|---|
| Source IR | `E:\Projects\Melee Workspace\ports\goku-xv2\ir\goku.xv2.ir.json` |
| Host IR | `E:\Projects\Melee Workspace\ports\goku-xv2\ir\host.melee.ir.json` |
| Read-only source package | `E:\Torrents\Dragon.Ball.Xenoverse.2.Future.Saga.Chapter.4-RUNE\modding\exports\goku-base-shallow-v0.1\` |
| Artist input | `E:\Projects\Melee Workspace\_build\goku-xv2\author-source\fighter.json` |
| Editable Blender source | `E:\Projects\Melee Workspace\_build\goku-xv2\author-source\goku.blend` |
| Built mod | `E:\Projects\Melee Workspace\_build\goku-xv2\author-source\package\mods\goku-xv2\` |
| Build and audit reports | `E:\Projects\Melee Workspace\_build\goku-xv2\author-source\package\build\` |
| Conversion losses | `E:\Projects\Melee Workspace\_build\goku-xv2\conversion_losses.json` |
| Contact sheets | `E:\Projects\Melee Workspace\_build\goku-xv2\contact-sheets\` |

All source game bytes, converted models/textures/clips and generated reports stay
under the read-only source package or ignored `_build`. This port directory holds
only tools, metadata, documentation and authored gameplay. Nothing is committed
automatically. The source IR contains external BlobRefs, never pixel/key/vertex
arrays. Its large controller graph accounts for most of the JSON size.

## Rebuild

Run from `E:\Projects\Melee Workspace`:

```powershell
python ports/goku-xv2/tools/build_source_ir.py
python ports/ir/tools/validate.py ports/goku-xv2/ir/goku.xv2.ir.json
python ports/goku-xv2/tools/check_ir_integrity.py
python ports/goku-xv2/tools/xv2_to_artist.py --blend
python ports/goku-xv2/tools/build.py --fighter _build/goku-xv2/author-source/fighter.json
python -m tools.geno.schema --check
```

`build.py` wraps the existing artist builder and reapplies maintained gameplay,
native row bindings, attributes, hurtboxes and losses after every art rebuild.
Directly invoking the generic artist builder is a diagnostic gate: reapply this
wrapper before running the fighter. Scripts resolve anatomical role tokens to
the newly generated plan's actual joint indices.

**Gameplay data in git.** The committed `gameplay.json` is the *stripped* file: the same structure and the authored
Melee design values (damage, angle, KBG/BKB, sizes, offsets, windows, IASA), without the source-game fields
(candidate windows, picks, pose reviews, BAC ids, clip names, strike frames, clip lengths, timing notes). The full
file lives locally as `gameplay.full.json` (git-ignored). Every tool reads the full file when it exists and the stripped
one otherwise, and tolerates the stripped fields being absent; `attacks.py` and `cross_port.py` write the full file and
regenerate the stripped one. After editing `gameplay.full.json` by hand run `python ports/goku-xv2/tools/strip_gameplay.py`
(`--check` verifies it; `tests/test_gameplay.py` does too when the full file is present). A fresh clone has only the
stripped file, so `build.py` there lacks the clip-length check and the source-derived losses text, and needs the local IR anyway.

The source IR covers every captured BAC entry and BCM node, all canonical Move
keys, the three physical rigs plus animation reference skeletons, costumes,
models, textures, effects and projectile references. Audio bank contents and XV2
stats are absent. Each original v0.1 gap remains an Issue. All comparisons are
inferred or unknown; XV2 did not run and runtime fidelity is out of scope.

The artist adapter makes one mesh/material/atlas, rigidly attaches hair and belt,
reduces skinning to two influences and uses 63 weighted bones. The initial
target bind-pose height is 20 units after the user's in-game size correction;
the loaded joint count is 126. The bent Wait pose is approximately 16.65 units
tall (formerly 11.65 at the initial 14-unit setting). Facial deformation,
SCD physics, full toon/DYT shading and source eye composition are losses.
`ANIM-ROWS.json` records authored-needed rows and aliases; a successful package
build does not make those animations complete. Source FPS is unmeasured; 60 fps
resampling uses a documented exporter convention.

Gameplay is a Melee design derived through parity: percentage damage, angle,
KBG/BKB, collider spheres, movement and charge thresholds are authored. Eight
special inputs are bound. Lua selects the Kamehameha release tier; the beam is a
hitbox beam with authored effect meshes (KAMEHAMEHA.md; the old article projectiles are no longer spawned).
Tracking, homing, camera locks and untranslated source functions are recorded
as losses. Falcon supplies the initial attribute design. Host ECB behavior,
placeholder rows, contact, balance and both-facing visual alignment still need
the validation status recorded in the generated reports and handoff notes.

The legacy `framedata_check.py` and `check_hitbox_positions.py` CLIs require
Ultimate ACMD/install inputs. `tools/audit_gameplay.py` instead uses real
parity-selected BAC candidates and reuses their native script/FigaTree/geometry
readers. It neither fabricates ACMD nor claims numerical XV2 collider parity.

Native runs use `tools/port/build.sh` and `tools/port/run.sh`. Restart after every
package rebuild. `lua/lab_check.lua` tests special input/state/article execution;
the shared artist proof tests locomotion, shield, jab and grab. Static contact
sheets use installed animation-bank collision coordinates drawn in Blender.
Read the final handoff's gate results before treating any runtime check as done.

## XV2 clip browser (LAB CLIPS page, 2026-10-08)

Every Goku body clip in the XV2 source (GOK.ean, the shared CMN.ean, and the skill EANs:
Kamehameha variants, Instant Transmission, ultimates, blasts, evasives) is in Goku's bank as its own
clip named `x<source name>` (`_build/goku-xv2/author-source/clip-library.json` lists the source file,
name and length). They are unbound rows (`fighter.rows`, 303 on): no input or state uses them, so the
playable moveset is unchanged. Clips longer than 180 frames are cut at 180 (the engine's 128 KB
per-clip buffer); the library file records the source length.

Launch (needs the `agent/goku-polish` build):

```powershell
& 'E:\Projects\Melee Workspace\ports\goku-xv2\tools\clips.ps1'                 # opens on CLIPS
& 'E:\Projects\Melee Workspace\ports\goku-xv2\tools\clips.ps1' xGOK_SPA_KMH    # and starts that clip
```

The page is a general LAB mode (any fighter: retail rows too), reached with TAB in the LAB or
`lab mode clips`. Goku stays in Wait while a clip plays: grounded, in place, no move script, no root
motion.

| key | does |
|---|---|
| UP / DOWN | choose a clip (mouse wheel / pad: use the keys) |
| ENTER | play the chosen clip from frame 1 |
| SPACE | pause / resume |
| RIGHT / LEFT | one frame forward / back (CTRL: 10) |
| PAGEDOWN / PAGEUP | jump 10 frames forward / back |
| Z / X | slower / faster (x2, 1, 0.5, 0.25, 0.1) |
| V | category: ALL, LIBRARY (the XV2 set), ATTACKS, SPECIALS, MOVEMENT, DAMAGE, OTHER |
| O | flip facing |
| L | loop on / off |
| M / S / B | model / skeleton / hit+hurtbox draw |
| C | close-up camera on / off |
| F | focus the other port |

Console (`MELEE_CONSOLE_PORT` 51726, or the LAB console): `lab clips find kame`,
`lab clips play xGOK_ATC_009 12`, `lab clips show <row|name> <frame>` (paused there),
`lab clips frame 30`, `lab clips speed 0.25`, `lab clips category specials`, `lab clips stop`.
Note a clip by its name (`xGOK_ATC_009`) and a frame range when picking moves.

### REMAKE picker (LAB mode REMAKE, temporary tooling, 2026-10-10)

The CLIPS machinery with a picker on top, to choose Goku's remake animations slot by slot in the game instead of in a web page.
One command (needs the game checkout whose `geno-lab` has the REMAKE mode; `GW_MELEE` / `GW_BUILD_ROOT` select it):

```powershell
& 'E:\Projects\Melee Workspace\ports\goku-xv2\tools\remake.ps1'
emake.ps1'          # optional arg: a slot number or name fragment
```

It writes `missions/remake-slots.txt` (`tools/remake_lab_data.py`: the 55 slots of `remake-candidates.json` in picking order, their
candidates, and every clip of `CLIP-NOTES.md`), runs two Gokus (left: what you judge, right: the reference for compare) and opens on
**BROWSE**: all clips in CLIP-NOTES order, clips without a note first. Press K for the current slot's candidates instead
(the recommended one plays first; the current clip is entry 1).

| key | does |
|---|---|
| UP / DOWN | previous / next clip (BROWSE) or slot (candidate view); every clip auto-plays and loops |
| A / D | previous / next candidate of the slot (or clip, in BROWSE) |
| N / P | next / previous slot (the slot a pick goes to) |
| K | switch BROWSE (all clips) / the slot's candidates |
| Y | pick the shown clip for the slot. Asks first: press Y again within 4 s to confirm. |
| U | undo the last pick (and again for the one before) |
| I / J | mark range in / out at the shown frame (press again on the same frame to clear); the range loops and is saved with the pick |
| T | A/B: back to the clip viewed before this one |
| W | compare: the second Goku plays the reference (default: the slot's current clip) beside the shown clip; W again to stop |
| R | make the shown clip the compare reference |
| Q | slots without a pick only |
| E | shows how to add a note (the engine has no text entry for the LAB: use the console, below) |
| SPACE, LEFT / RIGHT, Z / X, L, M, S, B, C | as CLIPS (pause, frame step, speed, loop, model, skeleton, boxes, close-up) |

Console (the in-game backquote console, or `MELEE_CONSOLE_PORT`): `lab n <what it is>` (or `lab clips note <text>`) notes the shown
clip (`+text` appends, `-` clears); `lab remake` lists the picks; `lab remake slot <n|name>`, `next`, `prev`, `cand <1|-1>`,
`browse`, `undo`, `status`.

Saved after every change, in `_build/goku-xv2/lab-data/geno-lab_lab/`: `remake-picks.json` (one slot per line: `n`, `slot`, `clip`,
`in`, `out`, `browse` = not one of the plan's candidates) and `remake-notes.json`. Fold them into the workspace with

```powershell
python ports/goku-xv2/tools/remake_sheet.py --sync-picks
```

which copies both next to the plan (`ports/goku-xv2/remake-picks.json`, `remake-notes.json`), writes the notes into the `what it is`
column of `CLIP-NOTES.md`, and regenerates `REMAKE-CANDIDATES.md` with the owner-pick column filled and the notes beside each candidate.
Not run in game beyond the checks in `melee/pc/geno/tools/lab_stage_d_check.lua`; see the lane report.

### XV2 move map and MOVES playback (2026-10-08)

`python ports/goku-xv2/tools/movemap.py` reads the source IR (BCM input/condition tree, BAC entries
and their events) and writes, locally only:

- `_build/goku-xv2/movemap/index.html`: open it in a browser. A searchable list of Goku's BAC moves
  (basic, his skills, borrowed skills); each shows its timeline bar (animation events, source hitbox
  and cancel windows, movement), the clips it plays in order with frame ranges and speed, other events,
  and the BCM routes into it (input/direction, activator conditions, ki/stamina, loop durations,
  parent chain) plus the BCM children of its first node.
- `_build/goku-xv2/movemap/movemap.json`: the same data for tools.
- `missions/moves-goku.txt` in the package's `geno-lab` mod: the LAB's MOVES table.

Timing is the BAC's static frames at the 60 fps export convention: unverified, nothing observed.
In the LAB CLIPS page press V until MOVES; ENTER plays a move's clips in order at their source speed
(LOOP, SPACE, LEFT/RIGHT, PAGEUP/PAGEDOWN, Z/X work the same). The bar under SOURCE MOVE marks
source hitboxes (red) and cancel windows (blue). Console: `lab clips play chara/GOK/GOK_PLAYER.bac:430`.
Launch: `tools/clips.ps1 chara/GOK/GOK_PLAYER.bac:350` opens straight on a move.

## Ledge, grab, hurt set and the fidelity ledger (2026-10-08)

- **Ledge**: authored hang/climb/attack/roll/jump rows (XV2 has no ledges; hang pose GOK_BAS_JUMP_BACK_00 f12,
  TransN puts the hands on the ledge). Checked on FD and Battlefield, both sides, every option.
- **Grab**: ThrowN (`grab_anchor`) hangs off the root 5.3 in front of the chest, so the victim is held at about
  (8.1, -1.0) like Mario and Falcon; CatchPull 1 frame, pummel 24, throws from XV2's throw (BAC 601) and his
  uppercut / low sweep. Throw scripts set only `throw_flag` (the release). They must NOT set `cmd_var idx=0`: that freezes the thrower at the release frame until the victim's thrown animation reaches it, which a retail victim of a base-none thrower never does (Goku stayed in ThrowF for 400+ frames; fixed 2026-10-09, gate `lua/grab_check.lua`).
- **Hurt set**: every damage, launch, down, tech, capture, thrown, item and misc row maps to an XV2 clip
  (`tools/rowmap.py`), at Melee length.
- **Ledger**: `python ports/goku-xv2/tools/fidelity.py` writes `FIDELITY.md` / `fidelity.json`: status, XV2 source,
  deviation, evidence, and the row's length against Mario's measured in game (`row-lengths.json`).

## 2026-10-09 specials, ground and effects pass

- Specials (PICKS.md, all provisional): Kamehameha (reworked 2026-10-10, see KAMEHAMEHA.md: a stored charge and a sustained multi-hit hitbox beam with its own effects, four tiers incl. the Super Kamehameha at ki 100); Dragon Rush into RushCombo;
  Instant Transmission with a reappear hitbox; Z-vanish counter (ki) and ki charge. `lua/goku.lua` is the geno 10 text; lines marked `-- @KI` use the combo engine's meter and
  are stripped by `build.py`, the full text ships as `lua/goku_ki.lua` and `combo/combo_apply.py` installs it.
- Hybrid hover stance (owner): `tools/xv2_to_artist.py` lifts each ground row's pelvis per frame so nothing sinks (HOVER rows keep the lowest point 2.0 units up: `HOVER_Y`;
  ANCHORED rows only on frames that would sink). `tools/ground_audit.py` measures every frame of every ground row (`_build/goku-xv2/ground-audit.json`) and `build.py` fails on BELOW.
  `tools/ground_sheets.py` draws before/after silhouettes (`_build/goku-xv2/ground-sheets/`, needs a `GOKU_GROUND=0` build kept in `ground-before/`).
  Lower hurtboxes are 1.6 units fatter; dtilt/dsmash carry floor-level spheres (`FLOOR` role). Native checks: `lua/ground_check.lua` (Fox/Marth/Falcon dtilt+dsmash vs Goku, both
  sides) and `lua/ground_show.lua` (the visible cycle next to Mario).
- Effects: `tools/fx_build.py` writes original particle packages; `build.py` copies them to `fx/`, writes `fx/fx_bindings.json` and sets article `fx`.
- Select art: `tools/presentation_art.py` (Blender) + `png2gx` in `build.py`.
- Row lengths: `tools/rowlen_sync.py` refreshes `row-lengths.json` from the built plan (bank frames - 1, equal to the in-game number on every row measured and not re-cropped);
  `lua/measure_rows.lua` hangs on its first preview and is unused.

## Optional CSProject UI render

A full build accepts `--ui` to render select, stock and results art through the shared
[CSProject UI tool](../../tools/csp/README.md). It is off by default; `--auto --ui` forces a full build,
and `--gameplay-only --ui` is rejected. Prepare external tools first with
`python tools/csp/fetch_csproject.py`; no CSProject assets are stored in this repository.
The rendering and in-game appearance remain unverified until the lead runs them.
