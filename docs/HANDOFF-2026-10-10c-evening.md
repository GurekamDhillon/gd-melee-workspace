# Handoff, 2026-10-10 (evening)

Supersedes `docs/HANDOFF-2026-10-10b-restart.md` for the current state; read with `docs/NEXT-SESSION.md` and
`docs/HANDOFF.md` §7 (lanes work in their own worktree; the main session is the sole integrator). Nothing is pushed.
Sonnet leads hit the session limit at about 19:20 (resets 21:10 local); two lanes were cut off mid-work (below).

## Integration tips
- Workspace `integration/2026-10-01/roguelite-100` at `a9c2f64` (+ this handoff).
- Game `integration/2026-10-01/roguelite-100-game` at `092a8420d`. `_build/melee-pc.exe` was built from `1f51198c5`
  (UCF, .gdlp recorder, ACE fixes, Fox/Falco/Marth templates); it does NOT have the Puff/Zelda/Sheik merge yet.
- Launcher installed in `_build/release` from `a9c2f64` (35/35 ctest); `_build/wb-win` still has the build before
  projectiles (it was in use); copy `E:\Projects\integ-qt-build\out\launcher\bin\gd-melee-launcher.exe` there when free.
- Owner's uncommitted edits in the main checkout, leave them: `ports/goku-xv2/gameplay.json` (Marth mobility option c,
  dair windows), `moves/dair.genoasm`, `moves/jab1.genoasm`; `gameplay.full.json` (ignored) carries the same.

## Merged today (all on integration)
Workbench: hitbox add/delete, Falcon moves, attributes, artist errors, tutorial, CSP Render UI, Play in LAB, Atlas redesign,
responsive layout (portrait: Move view full width, Moves as a tab), hitbox fields (element, shield, ground/air, slot),
hitbox order/timing check, engine discovery + Start game / Start Blender chips, changed-since-build markers, wheel guard,
QOL (Fix buttons, crash restore, queued edits, shortcuts + F1), frame convention (frame 1 = first move frame; conversion
only in `EngineLink`), Play feeds Blender, projectiles (Blender collection, spawn markers, ghost path, Projectiles tab).
Blender: Geno workspace tab, async Rebuild + reload with progress, hitbox viz (spheres, arrows, fans, strips), IK/FK control
rig + hand layer (`anim/hand.json`) for Goku and Falcon, part visibility (LOD hidden, visor alpha) for retail art.
Game: anim bank reload, six-slot (slots 2560, pool 65536, heap 3 enlarged, MEM1 48 MB, netplay protocol 6), ACE fixes
(Daisy, Knuckles, onDSmash, MoveLogic for B. Falcon/Lucina, hitbox id >= 4 remapped to a free slot), LAB `.gdlp` recorder
(`lab rec ...`, F7 / Shift+F7; rewind-resume now replays), UCF 0.84 offline (default on, settings row, `MELEE_UCF`),
templates Fox, Falco, Marth, Jigglypuff, Zelda/Sheik pair (`define.transform_partner`).
Goku: mobility option c (Marth), JumpF/JumpB 36 frames, Kamehameha rework (stored charge, multi-hit beam).
CSP: per-asset framing from the skeleton, own Blender 5 backend (default stays csproject).
Research: `_research/ace-hitbox-types-2026-10-10.md`, `ace-hitbox-slot4-2026-10-10.md`. Tools: build_launcher guard,
Steam Blender discovery, stub forwards stdio.

## Lanes cut off by the session limit (resume these first)
| worktree | branch | state | next |
|---|---|---|---|
| `worktrees/falconskin` | ws/falcon-skin-fix (uncommitted: HsdExport/Program.cs, build_blend.py, pose.py, rigmap.py, tests/test_rigmap.py) | owner: Falcon's HQ meshes deform wrongly in Blender (`Joint_0_Object_13`, foot/ankle stretched) | finish root cause + fix, regenerate falcon.blend with the fix AND part visibility |
| `worktrees/kamexv2` (+ `kamexv2-game`) | ws/goku-kame-xv2 at 5e424b4, NOT merged | XV2 effects + audio converted; owner: "still looks like shit", "sounds like shit", "doesn't behave like Mewtwo or Samus charges at all" | 1) audio quality (trace ACB/HCA -> wav -> .gnsnd -> AX; A/B files in `_build/xv2-kame/audio/ab/`); 2) native charge model from the decomp (tap B enters a self-running charge, shield stores, roll/spotdodge/jump cancel, full auto-stores, B fires); keep "full stored charge survives a hit"; 3) get the owner's specifics on the look (ask for a screenshot; likely needs additive glow/soft particles in the engine) |

Falcon art files: `_build/geno-falcon-art/falcon.blend` is currently the ORIGINAL (LOD + HQ overlap, dark visor);
`falcon.blend.parts-baked` is the LOD-hidden bake; `falcon.blend.pre-parts` the backup.

## Queue (owner-approved; see memory `queue-2026-10-10-evening`)
1. Combo tooling (route rows on the timeline, Combo tab, string map, Blender "play a string").
2. Falcon shoulder slab (DObj 77): check its material before hiding it.
3. `.gdlp` v2 (standard Slippi events, embedded state, `.slp` export) + rewind-log pad 48 -> 64 bytes.
4. Throw stand-in banks loaded lazily (option c) so six different template fighters fit heap 0 — owner has NOT yet said yes.
5. Creator (Workbench) projects for the template fighters (only Falcon has one) — owner has NOT yet said yes.
6. Kamehameha follow-ups: screen shake/flash (engine camera hook), stick aiming, roll-cancel.
7. Hands-on Workbench tutorial; bundled pinned Blender ("GD Blender"); figatree -> Blender actions importer (offered).
8. Falco parity 406/407 (`hit_fsmash_p100_tech_b`, looks like a scenario-order effect on the retail side): bisect.
9. onFloat m-ex slot (Daisy, Skull Kid) still unwired; Workbench throw/hurtbox-state statements need assembler forms.

## Owner decisions today (also in memory)
Codex paused (usage out; its shell is still broken). Workbench = Atlas-styled Qt editor, Blender is the only 3D viewport.
`.gdlp` = GD live playback. Zelda/Sheik = template pair. Skull Kid id 4 = remap (deviation from ACE, ledgered).
Goku = Marth mobility. Kamehameha: native charge behaviour, full stored charge survives hits, Super 31.7%.
UCF on by default offline. Combos need not be true; no combo brute forcing.

## Traps (new today)
- `gd.rewind_to` then console `resume` used to fork the timeline and drop the logged input (fixed in the recorder merge).
- A worktree's `_build` is a junction to the main `_build`: build to absolute paths outside the repo.
- `build_launcher.ps1` needs `CMAKE_PREFIX_PATH`/`QT_ROOT_DIR` = `E:\Projects\Qt\6.8.3\msvc2022_64` and cmake on PATH
  (`E:\Projects\gdm-build-tools\cmake\data\bin`); clear `E:\Projects\integ-qt-build\b\CMakeCache.txt` if another worktree used it.
- `build.sh` needs `E:/...` style `GW_MELEE`/`GW_BUILD_ROOT`, not `/e/...` (link fails on Slippi symbols otherwise).
- After a game merge that touches the registry, regenerate `python -m tools.geno.schema` and commit.
- Leads can re-send their final report several times; stop them (TaskStop) once merged.
- Jev `check_claims`/`coverage` returned nothing usable all day (`claims: []`, `unclear`); `runparse` works.
- Never `git commit -a` in the main checkout: the owner's Goku edits are uncommitted there.
