# combolive handoff (lane ws/wb-combo-live). Code committed: f6cc083, 4b27df5, ff549cb (on top of 246e54c notes).

## Done (verified)
- C1 fixed: ports/goku-xv2/workbench.json mods_dir -> _build/goku-xv2/combo-package/mods; rebuild argv -> ports/goku-xv2/combo/rebuild_with_combo.py
  (build.py then combo_apply.py --src author-source/package/mods) so a Creator rebuild keeps the combo states.
- C2 fixed: commands_combo.cpp stateMotion() = 0x400 + index of the state in the running package's geno.json (EngineBackend::packageGenoPath);
  a missing state/row is an ERROR ("...combo package: rebuild with combos"), never skipped; route targets that are neither row nor state
  (special_s, jump_short) are returned in "skipped". Aerial rows get lift 120; "past the end" clamps like set_frame; first pose retries once.
  Real engine: strings 0..6 all play (frames_sent 76,41,54,22,37,85,63). realtime play_string: 76 frames in 1.28 s (60 fps = 1.27 s).
- PLAY: EngineLink never handled wb.step "pending" -> every real-game PLAY failed "unexpected engine reply: pending" (fake engines hid it). Fixed
  (polls frame_info). Window PLAY is now a wall-clock accumulator (8 ms tick, owed frames = dt*60*rate, one play{frames,step=due}).
- Scrub: TimelineView::setMove reset scrubbing_ on every command reply, ending the drag after one seek; keepScrub fixes it; scrubbing() virtual so the
  engine reply does not move the cursor mid-drag. Unit test fails without the fix.
- Tabs: InspectorTabs: ElideNone + scroll buttons (7 tabs cannot fit 310-350 px); test asserts every tab keeps its whole label.
- Tests: ctest 37/37, check_qt_strings 0 problems, launch_goku --check and launch_falcon --check status=OK.

## Left
- Owed (needs eyes): GUI PLAY/scrub feel in the real window; Blender "Play string" for state clips (combo_play.py uses clip names, untouched);
  tab bar look with scroll arrows at 352 px.
- jab1 in the combo package chains into jab2 after 4 stepped frames in the engine (PLAY on jab1 shows motion 45 after frame 4): engine behaviour, not fixed.
- strings 2 and 3 end in special_s / jump_short: not poseable (engine-driven); only reported. Could map special_s to the Rush state if the owner wants.
- combo.json is gitignored (main checkout only); a copy sits untracked in this worktree for tests.
- Do not merge: the main session integrates. Launcher build: E:\Projects\combolive-qt-build\b (Release).
