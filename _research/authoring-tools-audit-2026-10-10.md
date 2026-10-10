# Authoring tools audit: what a human holds while making a fighter (2026-10-10)

Supersedes: nothing. Research only; no code changed, no game built. Branch integration/2026-10-01/roguelite-100.
Evidence labels: **[ran]** I executed it; **[read]** code/doc read (file cites given; most by read-only agents, not re-opened by me);
**[hr]** measured in `_research/hot-reload-2026-10-10.md` (scratch-copy goku-xv2, wall clock).
Not touched: wbfalconmoves, wb-hitbox-ux worktree, stress6, `_build/wb-goku`, `_build/wb-win`. Nothing was watched in Blender's GUI or in game: those are "owed".

## What I ran
- `python -m tools.geno.artist new <dir> --key tfighter --name TestFighter` [ran]: 1.6 s, wrote `tfighter.blend` + `fighter.json`. Prints "next: ... build". Printed paths mix `/` and `\`.
- `... validate <the dir>` [ran]: `BLOCKER LOAD ... cannot read ([Errno 13] Permission denied: '...\tf')` (a directory was passed; the message never says "give fighter.json").
- `... validate tf/fighter.json` on the fresh starter [ran]: `BLOCKER LOAD ... art.glb ... does not exist` / `fix: fix the file named, then run again`. The starter fails its own validator until `build` exports the glb, and the fix text does not say "run build". Same for `ports/geno-artist-samples/pip/fighter.json`.
- `... build tf/fighter.json` [ran]: `OK in 11 s` (headless Blender export, validate, convert, fighterbuild, geno check, install into `_build/artist/tfighter/`); prints the LAB command and "Restart the game after every rebuild". Notes like "role fingers.R is missing: hitboxes on it use hand.R" are clear. (I deleted my output dir.)
- `ports/goku-xv2/tools/splice.py list` [ran]: clear listing (recipe, target row, segments, notes; 3 are "preview-only EXAMPLE"). `build.py --help` [ran]: documents `--gameplay-only` and `--auto`.
- `python -m tools.geno.check --help` [ran]: wants a dir containing `mod.json`.

## Round-trip numbers
[hr] full `build.py --fighter` 278-295 s (stage A 244-258 s, 87% the 725-clip bank; stage B 3.5 s; audits ~30 s). Engine restart to ready 1.0-1.3 s. A match restart does NOT re-read a changed bank. Numeric hitbox edits are same-layout (0/180 changed word count); adding a hitbox adds 5 words (layout change). F8 hot reload is refused for native-define fighters (`geno_registry.c:2091`), which is what the artist pipeline and Goku produce. Since that note, `build.py --gameplay-only/--auto` merged (10223eb; its message says "hitbox round trip ~15 s": the commit's figure, not re-measured here). The "~72 s splice preview" figure was never reproduced.

## Step-by-step inventory
| step | tool and gestures | round trip | forced to text/terminal/env | errors | no tool / undocumented |
|---|---|---|---|---|---|
| 1 rig + model | `artist new` (terminal), then starter .blend in Blender; Geno sidebar tab (artist `geno_panel.py`): Validate, Export glb, Export+Build+Install, "Set role of active bone", "Mark hit frame" | new 1.6 s; build 11 s (starter) | install the panel by hand (Preferences or Alt+P in Text Editor); "Repo folder" empty by default; `control_rig.py` bake only via Text Editor or `blender -b --python-expr`; costumes/textures/team colours in JSON | validate on fresh starter: non-actionable fix; Blender crash or traceback swallowed (only `GENO ` lines printed, pipeline.py:51); some `fix` strings empty (NO_MATERIAL, MULTI_MATERIAL) | role is a free-text field (typo caught later as ROLE_UNKNOWN); no panel button for joints/clips/LAB command; `new` does not say to install the panel |
| 2 animations | Blender actions (13 templates); `artist clips` checklist; Workbench Splice panel (Import clip, Lay out recipe, Save strips, Bake & export); `splice.py list/check/preview` | full rebuild ~5 min [hr] | recipes in hand-edited `splices.json`; Splice panel needs GW_SITE with scipy/Pillow; `clips.ps1`/`play.ps1` hard-code `worktrees/goku-polish`, console port 51726, Git bash path | Splice ops: ERROR toast + status (good, operators_nla.py:62) ; `splice check` needs local XV2 IR | animation hot reload does not exist (bank cached); `geno-artist-rows.md` is the only row map (351 rows) |
| 3 moves/hitboxes/frame data | Workbench Hitbox panel (bone, damage, size, xyz, angle, kbg, fkb, bkb, frames; Suggest bone; Apply; Rebuild+reload); LAB HITBOXES/FRAMES; hand `.genoasm`; `tools.geno.report --frames` | hitbox Apply+rebuild ~15 s (10223eb claim); before ~5 min [hr] | non-Goku: hand-edit fighter.json `moves.*` or `.genoasm`; `joint=N` must be looked up (`artist joints` or INSPECT J); `workbench.json` `rebuild` argv | Rebuild/checks greyed, reason only in status ("no_roles", "rebuild_unavailable"); frame-hook errors only in status line; `geno check` failure shows last 6 lines | hitbox placement not editable in the LAB (view only); no add/delete-hitbox UI; `moves_check` README is Courier-specific, 40 scenarios assume Striker moves |
| 4 hurtboxes/ECB | `hurt.py` proposes capsules ("auto"); LAB `B` boxes, `U` hurtbox states, `E` ECB (off by default), INSPECT | rebuild + restart | non-auto hurtboxes are hand JSON | none specific | the engine does not read the ECB (hurt.py:3) and the README omits that; no hurtbox/ECB editor anywhere |
| 5 attributes/feel | hand-edit `geno.json` `attributes`/`jumps`; INSPECT `A` compare (read-only); LAUNCH mode knockback preview | F8 "seconds" for non-define fighters; define fighters: rebuild + restart | all text; geno.md:485 "Not built: live edits written back" | unparsable geno.json on F8 silently keeps old data (log only) | no tuning UI; packet 04 "physics and feel" is an unrun outline |
| 6 specials/scripting | fighter Lua `lua/<fighter>.lua`; console `reload [id]` re-reads Lua from disk; `lua_check` runs inside `geno check` | immediate for Lua | text editor; scripting.md is 2758 lines, mostly roguelite API | Lua errors shown per script with file:line (good) | `lua_check.py` has no CLI; no stepper/debugger; packet 13 unrun |
| 7 effects/sounds | `.gfx.json` by hand (Goku: `fx_build.py` + emitter template); geno.json `sounds` binds retail ids; `audio.py` wav->gnsnd | rebuild + restart | all text; sound ids found by reading a log line "plays retail sound N (no audio.voice row)" | none | no effect or sound audition/authoring UI (EFFECTS-LAB-PLAN is a roguelite prototype); article models have no tool |
| 8 presentation art | `presentation_art.py` (Blender script from a terminal) then `png2gx.py` via build.py | rebuild | pose frames and action names hard-coded to Goku | `SystemExit('missing action ...')` | nothing generic for other fighters |
| 9 playtest | paste the `run-command` line into bash; Workbench via hub "Open in Blender"; `play.ps1`/`clips.ps1`; CLIPS viewer (pose only; scripts do not run) | engine restart ~1 s once built [hr]; cold start owed | env vars MELEE_MODS_DIR, MELEE_SCENE, GW_ISO_VANILLA, MELEE_LAB_MODE, MELEE_LAB_CLIP | Atlas pause menu OFF by default (`lab ui on`, console only) | CLIPS D-pad step documented only in HANDOFF-2026-10-10; geno.md key list stale |
| 10 iterate | Workbench Rebuild+reload; F8; state library (.gdst); frame-data export + `framedata_diff.py` | see above | Workbench needs launcher exe, Qt DLLs (GW_QT_BIN), engine exe, ISO (GW_*); `launch_goku.py` hard-codes `D:/SteamLibrary` Blender and `E:/Projects/Qt/6.8.3` | `start_server` silently reuses a server already on the port; Fighter-panel buttons grey with no reason | Lab output goes to `scripts-data/`, never back to source; no mod packer or checker (packet 08) |

## Other facts [read]
- Workbench add-on panels: Connect, Timeline (600-frame cap hard-coded, panels.py:103), Problems, Hitbox, Splice, Fighter (Load/Calibrate/Verify). Its README still says "Task 6 shell... later tasks arrive" (l.6-9) and omits the Fighter panel, Play/Speed/loop/travel, Restart engine, engine/mods/iso fields and most GW_* vars.
- Role-map editing has no UI: only `art.bone_aliases` in the project JSON (README:249). The `load_row` operator has no panel button.
- Hub "Open in Blender": Settings path, then GW_BLENDER, then PATH; existence not checked; the add-on is found via the nearest `.git` ancestor, so a release build with no repo cannot open Blender; the disabled reason is a tooltip only (hub_panel.cpp:54); no Blender version check (README says 4.x, Falcon section says 5.x).
- `launch_falcon.py` / `launch_goku.py`: terminal only, machine-specific defaults.
- Docs: the only complete beginner walkthroughs are `docs/learn/geno-fighters/01` (change a number on an existing fighter) and 03 (new Kirby neutral special). Packets 04-09 are explicit unrun outlines; 12 is superseded. The Blender-to-playable path is split across the artist README, geno-artist-spec (203 lines), geno-fighter-guide (1404 lines, agent-oriented) and the checklist. Stale: pipeline.py:3 advertises `--no-install --launch --smoke` (absent from `__main__`); `tools/geno/README.md:185` says check/report do not understand `base none` (the build runs check on it); geno.md has no section 21 and its 14.7 key map predates 14.9; fidelity.py EVIDENCE hard-codes `_build/agents/goku-polish/runs/`.
- Patterns from today's already-fixed bugs (not re-reported): UI sending a display label where the engine wants an id (row name); fixed timeouts that do not fit a 5-minute build; operators that fail without telling the user their precondition; per-frame cost from per-frame depsgraph work. Class to watch: any operator whose precondition is not shown.

## Ranked gaps (impact on a human author, effort S <1 day / M days / L week+)
| rank | gap | impact | effort |
|---|---|---|---|
| R1 | Define fighters cannot hot reload; every attribute/overlay tweak is rebuild + restart, while F8 is advertised everywhere | H | M-L |
| R2 | Animation edit to seeing it in game is ~5 min (bank 87%); no single-row bank swap | H | L |
| R3 | Hitboxes are hand-typed `.genoasm` / numbers; no placement gizmo, no add/delete, `joint=N` looked up elsewhere | H | M |
| R4 | No attribute/physics tuning UI (read-only compare; hand-edit JSON) | H | M |
| R5 | No start-to-finish tutorial; docs split; packets 04-09 unrun; stale claims | H | S-M |
| R6 | `new` then `validate` fails on its own starter with a non-actionable fix; directory arg gives "Permission denied"; Blender crash swallowed | M | S |
| R7 | Playtest = paste an env-prefixed bash line; no Play button in Blender or hub; Goku-only scripts | H | S-M |
| R8 | Hard-coded machine paths; silent greyed buttons; silent server reuse | M | S |
| R9 | No sound audition / effect authoring-preview | M | M-L |
| R10 | Tools are Goku-shaped and split across two Blender add-ons with overlapping jobs | M-H | M |
| 11 | Artist panel: role is free text; manual install; no joints/clips/LAB buttons | M | S |
| 12 | Role-map editing UI missing | M | S-M |
| 13 | Atlas pause menu off by default; geno.md keys stale; CLIPS D-pad undocumented | L-M | S |
| 14 | No mod packer/checker for sharing | M | M |
| 15 | Workbench README stale; 600-frame cap undocumented | L | S |

## Top 10 proposals
**R1. Hot reload for define fighters.** Follow the design in hot-reload-2026-10-10.md: for same-layout overlay-word and attribute edits, re-run the define registration pieces and bump the overlay-pool generation, reusing `GenoGame_LabReload`; anything else restarts the match. Then Workbench "Apply" is stage B (3.5 s) plus F8 rather than a restart. Until it lands, make the F8 refusal visible up front in the guide and the Lab toast so authors do not discover it after a rebuild.

**R2. Fast animation path.** Add an engine primitive to drop `ftData_Table_Unk0[kind].data` (or re-parse one row), plus a per-row `--splice-only` bank encode that skips fighterbuild and the other 724 clips. Goal: Blender NLA edit to CLIPS in under 30 s. Even before the engine part, cache unchanged clips in stage A, since 87% of the 5 minutes re-encodes unchanged data.

**R3. Hitbox placement tool.** The Workbench already edits numbers against a posed rig. Add a viewport gizmo (sphere at joint + offset, size) that writes back through `edit_hitbox`, and create/delete-hitbox operators that state honestly that a layout change needs the restart path. In the LAB, a cheap first step: "copy this hitbox as a .genoasm line".

**R4. Attribute/physics tuning panel.** A form (Blender or LAB) listing the 46 default attributes beside the base values, editing `geno.json`, using R1's reload path. INSPECT `A` already has the data; add write-back and a one-line hint per attribute, plus a numeric preview of jump/run/fall arcs before launching.

**R5. One tutorial.** Write `docs/learn/geno-fighters/` "start here": `artist new` to a landed hit in the LAB, with exact commands and expected output (the "What I ran" section is a draft). Mark packets 04-09 as outlines at their top, make `new`'s printout list the next steps (install panel, build, run-command), and fix the stale statements above.

**R6. Make the starter pass and errors actionable.** Have `new` also export the glb (or have the LOAD blocker say "run `build`, it exports the glb"), accept a directory and resolve `fighter.json`, print the Blender stderr tail on preflight/crash, fill the empty `fix` strings. All S, in `pipeline.py` and `validate.py`.

**R7. Play button.** "Play in LAB" in the artist panel and the hub: runs the `run-command` with env set and the ISO from `.env`, and reports the log path. Replace `clips.ps1`/`play.ps1` with one fighter-agnostic `tools/port/play_fighter.sh <key> [--clip C]`.

**R8. De-hardcode and explain.** One paths config (`.env` keys or `tools/geno/paths.json`) with a `--check` that lists every missing item; every disabled operator gets its reason via `poll_message_set` (Blender 4.x) and not only a status string; `start_server` says "reused existing server on port N".

**R9. Sound and effect audition.** Cheapest first: console `lab sfx <id>` and a LAB list of retail sound ids with names; `lab gfx <file>` to spawn a `.gfx.json` on the focus fighter, re-spawning when the file changes. Document `.gfx.json` fields with an example (the Goku emitter template is one).

**R10. Fighter-agnostic tools, one add-on.** Move Goku-specific pieces (presentation pose frames, splice recipes path, rebuild argv) into per-project `workbench.json`, and fold the artist Geno tab (Validate/Export/Build, role dropdown) into the Workbench add-on. Acceptance test: author a trivial second fighter end to end through the UI with no code edits.

## Day in the life today (new author, "Pip")
1. Read three docs to find the start (artist README, fighter guide, checklist), ~20 min. 2. Terminal: `artist new pip --key pip`, then `validate`: blocker "glb does not exist / fix the file named". Confused; `build` works (11 s). 3. Open the .blend; no Geno tab until the panel is installed by Alt+P in the Text Editor; set Repo folder. 4. Model and animate; Export+Build+Install; read results in a Text Editor block "Geno Report". 5. Copy the printed `MELEE_MODS_DIR=... MELEE_SCENE=... bash tools/port/run.sh` line into bash with `GW_ISO_VANILLA` set; INSPECT `J` to learn joint numbers. 6. Jab lands in the wrong place: leave the game, edit `fighter.json`/`.genoasm`, `build` (seconds for a starter, ~5 min for a 725-clip fighter), relaunch, renavigate to the move. F8 does nothing (native define). 7. Attributes feel floaty: hand-edit geno.json, rebuild, relaunch. 8. Sounds and effects: read logs for retail ids, hand-write `.gfx.json`, no preview. 9. On the Goku-style Workbench, Blender gives live pose, a Hitbox panel and a ~15 s hitbox rebuild, but needs launcher exe, Qt, engine, ISO, a role map, and greyed buttons explain themselves only in a tooltip or status string.

## Owed (not verified)
Blender GUI behaviour of both add-ons (layout, grey-out reasons, Alt+P install); a measured hitbox round trip (~15 s is the commit message's figure); artist `geno_panel` Build with an empty Repo folder (suspected cryptic, untested); in-game LAB key behaviour (read from docs only); fighterbuild failure messages; the Workbench panel code was read by an agent, not me. A human with a monitor and the ISO should walk the day in the life once.
