# combolive handoff (lane ws/wb-combo-live, base 7883aa0). No code changes made yet.

## Findings
CONFIRMED by reading (not yet reproduced in the real launcher):
- C1: ports/goku-xv2/workbench.json "mods_dir" = _build/goku-xv2/author-source/package/mods. That package has 14 states
  (no Light3..5/HeavyRush/HeavyUp/HeavyFinish/KiVolley). The combo package (combo_apply.py -> _build/goku-xv2/combo-package/mods)
  appends them as states 14..20 of fighters[0].states. So geno: steps cannot exist in the Creator's engine session.
- C2: commands_combo.cpp play_string: `if (motion < 0) continue;` - geno: steps have motion -1 (stepData/stateStep never sets motion),
  so they are SILENTLY skipped: strings 0,1,2,4 play only jab1/jab2 then stop; no message. Strings 3,5,6 are Moves rows (should work).
- C3: combo/combo.json is gitignored (ports/goku-xv2/.gitignore:61); exists only in the main checkout. A project copy must include it.
- Engine pose API: wb.row{motion}, wb.frame{motion,frame}, wb.step{n}, wb.clip{...} (melee/pc/platform/gw_script.c ~7181-7290). Poses only.
  Custom-state motion number is probably 341 + index in geno.json fighters[0].states (unverified; check via wb.row reply name / frame_info).
SUSPECTED (R5/R6, from timeline.cpp + workbench_window.cpp):
- Timeline::frameRequested -> setPlaying(false) + runCommand("set_frame") per mouse move: synchronous round trip per move = lag, no coalescing (R6).
- playTimer (workbench_window.cpp ~579): returns if busy(); 16 ms tick does one "play" command (engine step + poll) per tick, so speed is
  bound by command latency not wall clock; need time-based frame target (elapsed*60*rate) and check that the timeline frame is updated after
  the play result. Not reproduced.

## Plan (in order)
1. Build launcher: cmake on PATH E:\Projects\gdm-build-tools\cmake\data\bin; QT_ROOT_DIR/CMAKE_PREFIX_PATH=E:\Projects\Qt\6.8.3\msvc2022_64;
   cmake -S <wt>/tools/release/launcher/qt -B E:/Projects/combolive-qt-build/b -G "Visual Studio 18 2026" ; cmake --build b --config Release -j8
   (configure finished OK, build was killed mid-way; just rerun).
2. Copy ports/goku-xv2 (incl. ignored combo/combo.json) to a temp project; run
   gd-melee-launcher --serve --project P --engine-exe E:\Projects\Melee Workspace\_build\melee-pc.exe --mods-dir <combo-package/mods> (MELEE_WINDOW_X/Y=30000)
   and call play_string for each of 7 strings via MCP port (WB_SERVE port=N); check frame_info row/motion sequence.
3. Fix: (a) project config option (e.g. workbench.json "combo_mods_dir", or rebuild chain running combo_apply.py) so the Creator loads the combo package;
   (b) resolve state motion = 341+index from the package geno.json states and pose them in play_string; if state missing, error "needs the combo package; Rebuild with combos" + Fix button;
   (c) Blender preview clips from combo.json states clip names; status-bar messages.
4. R5/R6: time-based playback, coalesced set_frame while dragging (last wins), check RouteLanes/SpawnLane/hitbox bars not stealing drag.
5. R4: inspector tab labels Hitbox/Attrs/Checks/Render/Shots/Combo (+Spanish) and responsive_test elision assert at 4 sizes.
6. Tests: combo_test.cpp, fake_engine.py, ctest, check_qt_strings, geno_workbench pytest.
No processes left running (build killed).
