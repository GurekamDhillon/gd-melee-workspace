# Handoff, 2026-10-10 (night)

Supersedes `docs/HANDOFF-2026-10-10c-evening.md` for the current state; read with `docs/NEXT-SESSION.md`, `docs/HANDOFF.md` §7
(lanes work in their own worktree; the main session is the sole integrator) and memory `queue-2026-10-10-evening` (owner
decisions, one line each). Nothing is pushed. Written because the session limit is about to hit: every lead below may be
cut off mid-work; its state is on disk in its worktree.

## Integration tips
- Workspace `integration/2026-10-01/roguelite-100` at `236b2b0` (+ this handoff).
- Game `integration/2026-10-01/roguelite-100-game` at `d3eca5609`.
- FIRST THING: `python -m tools.geno.schema` is stale against the game tip; regenerate, run `pytest tools/geno`, commit the two
  generated files (`tools/geno/geno.schema.json`, `docs/learn/geno-fighters/template/geno.json.md`).
- `_build/melee-pc.exe` was built 20:58 from game `01174ff10`; it LACKS: custom stages (11b8e4d31), second-match crash fix +
  `ctx.go("roll")` (5903f942e), mod fighters (d3eca5609). Rebuild: `GW_MELEE="E:/Projects/Melee Workspace/melee" bash tools/port/build.sh`.
- Launcher installed in `_build/release` and `_build/wb-win` from workspace `126b839` (37/37 ctest). Later workspace commits that
  touch only Python (calibration default `7883aa0`) need no reinstall; they apply on the next Blender start.
- Owner's uncommitted edits in the main checkout, leave them: `ports/goku-xv2/gameplay.json` (Marth mobility, dair),
  `moves/dair.genoasm`, `moves/jab1.genoasm`. Never `git commit -a` there.

## Leads running when this was written (resume or re-brief each)
| lane | worktree(s) / branch | state on disk | what it was doing / next |
|---|---|---|---|
| Kamehameha combined build | game `worktrees/kamefx` (agent/kame-fx-integration, has agent/fx-render-features merged, 6 dirty); workspace `worktrees/kamexv2` (ws/goku-kame-xv2 at 9ed6887, 8 dirty, NOT merged) | mid-work | One Kamehameha the owner accepts: beam as ribbon layers anchored at the hands (hand.R, rotate [0.1223,-0.4751,0], D=(-0.454,-0.122,0.881), head at (0,0,L)), XV2 comet-tail width curves, per-tier look, subtle flash; charge ~10 s to MAX with chant beats; MEWTWO behaviour (verify retail: jump cancel, ledge grab from the air charge, hold MAX forever in LoopFull, no auto-store); XV2 ki-charge aura (after the rest); KAMECHECK + rewind 0 bytes + second_match + strips. |
| Combo strings live + timeline bugs | `worktrees/combolive` (ws/wb-combo-live, no commits yet) | just started | Owner: "combo strings appeared not to work in the launcher"; PLAY at playback speed doesn't work; click-drag scrub on the timeline is wrong; inspector tab labels squeezed. Hypothesis: strings go through geno states (Light3-5, HeavyRush, HeavyUp, HeavyFinish, KiVolley) that exist only in the combo package, not the package the Creator loads. Reproduce with the real launcher + engine + Blender, fix, real-engine tests. |
| Custom fighters round 2 | game `worktrees/nucfighters` (agent/nucleus-fighters, 1 dirty); workspace `worktrees/nucfighters-ws` | round 1 merged (opt-in); round 2 just resumed | FighterPartsTable for foreign skeletons (Giga Bowser panics `ftparts.c:453`), netplay refusal, slot cap/conflicts, coexistence with Geno + stage mods, rewind 0 bytes, N-B/down-B/up-B/nair parity, CSS + match screenshots, "download is an external link" message (Tails post 17327 is only a Google Drive link: not installable; do not follow it). |
| Netplay mod sync | `worktrees/modsync` (agent/netplay-mod-sync at eb924740d, 3 dirty) | commits exist, not reported | Mod manifest in the handshake, room diff UI, "match the host's mods" by Nucleus post id only (NO peer-to-peer transfer, owner decision), session-scoped with crash-safe restore, two-client loopback tests. |
| Throw-bank rollback check | `worktrees/tbroll` (agent/throw-banks-rollback at 98ccab765, 2 dirty) | commits exist, near a report | Rewind/SyncTest/two-client netplay across lazy throw-bank loads and evictions; fix anything that desyncs; bisect Falco parity outlier `hit_fsmash_p100_tech_b` (406/407). |

Engine FX features (`agent/fx-render-features`, tip 5ec78dba4: bloom tint/radius, ribbon span/taper, soft particles, dissolve,
rings, shake/flash, FX_MAX_EMITTERS 96) are NOT merged on their own; they ride in agent/kame-fx-integration.

## Merged since the evening handoff
Game: `.gdlp` v2 (Slippi events, embedded state, `lab rec export-slp`, `MELEE_GDLP_RECORD` / `MELEE_GDLP`, 4-port rewind log);
unpreviewable Workbench rows refused instead of asserting; lazy throw stand-in banks (six template fighters fit one match);
in-game Nucleus browser: stage skins, effects, menus, audio, category tabs, reasons for unsupported posts; custom stages as mods
on the vanilla disc; mod fighters on the vanilla disc (same-skeleton clones proven: ACE B. Falcon repackaged); second-match
crash fix (`lbDvd` preloaded archive moved by handle-heap compaction; pre-existing, Mario vs Luigi too); `ctx.go("roll")`.
Workspace: combo tooling (route lanes, Combo tab, string map, route-window check, Blender Play string); engine-death recovery,
"(not previewable)" rows, newest engine staged, Falcon calibration offset; Falcon scale tracks (the "stretched foot" was dropped
HSD scale tracks in the animation import); calibration default N==N (Goku was 5 units off after the frame-numbering change);
Gecko study (owner then DROPPED Gecko codes); Nucleus conversion-path and `.ssbm` notes; vcdiff + iso_diff prototypes.

## Owner decisions since the evening handoff (also in memory)
- Gecko codes dropped. No peer-to-peer mod transfer; owner will work with sc00p to host Geno mods on Nucleus.
- Kamehameha: tiers per chant syllable, each tier looks and behaves differently; ~10 s to MAX; Mewtwo charge behaviour (hold MAX
  forever, jump cancel / ledge grab as retail); stored FULL charge survives a hit; XV2 look + audio; beam must leave the hands.
- Skull Kid hitbox id 4 remapped to a free slot. Zelda/Sheik template pair. UCF on by default offline.
- Costumes: 255 per fighter already supported. Menu/UI mods and xdelta are wanted; `.ssbm` = xdelta of a built ISO (+ HD textures).

## Waiting on the owner
- Look at: the in-game Nucleus browser (main menu Right, Up, Up, A, then Z); combo tools; Falcon in Blender (regenerated
  `falcon.blend`: scale tracks, LOD hidden, visor alpha; grey shoulder slab DObj 77 still open); Kamehameha A/B audio files in
  `worktrees/kamexv2/_build/xv2-kame/audio/ab/`.
- Decide: online rule for effect/menu/audio mods (recommend: refuse menus online, hash effects); flash strength; tier table;
  whether Goku's `combo/combo.json` becomes tracked; Creator projects for the other template fighters; a standalone ki-charge move.

## Queue (not started)
Falcon shoulder slab material; Creator projects for template fighters; tutorial for the Workbench tools; bundled pinned Blender;
figatree -> Blender actions importer; xdelta in-game path (needs one real patch); onFloat m-ex slot; throw/hurtbox-state
statements in the Workbench; 151 Falcon rows "past the end of this move" marked not previewable; cleanup of merged worktrees
(check junctions first; empty unused ones: `worktrees/datapatch`, `worktrees/datapatch-ws`, `worktrees/rebirthb`).

## Traps (new tonight)
- Sonnet leads hit the session limit around six parallel leads; keep to ~4.
- A merge with `-X ours` was used twice for `gw_mex_bridge.c` churn only (verified no other file changed on both sides);
  prefer `git checkout -- pc/platform/gw_mex_bridge.c` before merging and resolve by hand otherwise.
- Changing a shared convention (frame numbering) needs a sweep of every consumer: the calibration pairing was missed and Goku
  deformed. Run `launch_goku.py --check` and `launch_falcon.py --check` after any Workbench frame/pose change.
- The Creator loads the normal Goku package; combo-only geno states live in `_build/goku-xv2/combo-package`.
- Nucleus posts can be external-link stubs (a text file pointing at Google Drive): not installable; never follow the link.
