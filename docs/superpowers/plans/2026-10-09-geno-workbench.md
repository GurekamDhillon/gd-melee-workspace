# Geno Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Creator mode in the Qt launcher (and an MCP server over the same command registry) that shows a Geno fighter exactly as the real game does, lets a person or agent fix hitbox limbs, clips and ground behaviour, and writes the fixes back to the fighter's source.

**Architecture:** The real game exe runs in a `workbench` mode (a LAB scene with logic paused unless stepped) and is driven over the existing console socket by new `wb.*` Lua calls. The launcher gets `workbench_core` (registry, history, file store, source editing, engine link, checks, MCP; Qt Core/Network only) and `workbench_ui` (Widgets). Every UI action and every MCP tool is a call into one typed, undoable command registry. All edits are order-preserving text edits of the fighter's source files.

**Tech Stack:** C++17, Qt 6 (Core/Network/Widgets/Test), CMake + CTest, the game's C11 + Lua 5.4 console, Python 3 for workspace tools.

**Spec:** `docs/superpowers/specs/2026-10-09-geno-workbench-design.md`

## Global Constraints

- No Rust. C++17 and Qt 6 inside the existing launcher (`tools/release/launcher/qt`).
- MCP is JSON-RPC over stdio via `gd-melee-launcher --mcp`, plus an optional localhost socket while the UI is open. Every command is an MCP tool.
- Localhost only: the MCP socket and the engine link bind/connect to `127.0.0.1`. The game console already binds `127.0.0.1`.
- No disc-derived or XV2-derived data is committed, bundled, or placed in test fixtures. Tests use synthetic fighters only (built in code in `testfixture.h`).
- Game workbench mode is inert unless enabled (`MELEE_SCENE=mode=workbench` / `--workbench`), is never active online, and never touches hashed or rollback state.
- The tool edits fighter SOURCE (`gameplay.json`, `moves/*.genoasm`, clip map, fidelity ledger), then runs the port's own build. It never edits built output.
- A snapshot of every file is taken before a save overwrites it. History persists across sessions.
- External changes (mtime/hash) are detected and never silently overwritten.
- Launcher strings follow the bilingual rule: every user-visible string is `t("English", "Spanish")` (new strings may be `t("English", "English")`); `tools/release/launcher/check_qt_strings.py` and the CTest `launcher_qt_strings` must pass.
- Branches: game changes on a NEW branch `agent/geno-workbench` cut from `agent/goku-polish` (new worktree `worktrees/geno-workbench`); workspace changes on `ws/geno-workbench`. Never edit the other worktrees' working trees.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. No push.
- Game builds use `tools/port/build.sh` (bridge fixpoint; never raw clang). Game test runs use `MELEE_TURBO=1` with a pad script (`MELEE_PAD_SCRIPT`), windows on screen (`MELEE_WINDOW_X/Y` on-desktop or off to the side but not minimised), and kill only processes the run started.
- Animation authoring stays in Blender. Out of scope for v1: attribute/state/combo-route/effect/material editing, stages, items.

## Review Focus

Failure modes the spec implies but its tests do not name. Each has a pinned test in the owning task.

1. **Hand edit while the tool is open** (a person saves `gameplay.json` in an editor, or Blender/`build.py` rewrites a file): `save`/`undo`/`accept` must refuse and report `changed externally`, never overwrite. Pinned: Task 3 (`FileStore`), Task 3 (`History::undo`), Task 9.
2. **Edit-order diff noise**: re-serialising `gameplay.json` through `QJsonDocument` sorts keys and reformats 1000+ lines. All JSON edits must leave every unrelated byte identical. Pinned: Task 2.
3. **Unusual hitbox scripts** (hitbox with no `clear_hitboxes`, `wait_until` before a hitbox missing, two hitboxes on one slot, a move with no script): parsing must not throw or misreport; frame edits must refuse with a clear reason instead of corrupting the script. Pinned: Task 4.
4. **Engine not running / dying mid-call / console reply larger than 16 KB**: every engine command returns `{ok:false,error}` (never hangs the UI or MCP), and large payloads travel as files, not console text. Pinned: Task 6 (timeout, dead socket), Task 12 (payload file).
5. **Bad MCP input**: unknown tool, wrong argument type, missing required field, malformed JSON line, notification without id. Server must answer with a JSON-RPC error and keep running. Pinned: Task 11.

---

## Spec gaps found while planning (decisions flagged in the report; plan assumes the recommendation)

- **G-a Console reply cap.** `gw_Script_Exec` output is a static `char out[16384]` (`gw_script.c` ~9693) and input lines are capped at 4096. `frame_info` and PNGs do not fit. Plan: `wb.*` writes payloads into `$MELEE_WB_DIR` and replies with a one-line `@<path>`.
- **G-b Render path.** Spec says Aurora offscreen frames. `aurora_begin_frame_offscreen` exists but nothing in `pc/` calls it, and `gw_Screenshot(path)` (shim_vi.h) already writes the next presented frame as PNG at render resolution, overlays excluded. Plan: v1 `wb.render` uses `gw_Screenshot` with the window on-screen/off to the side (a hidden window answers the console slowly, per `gd_prompt.py`). True offscreen is a follow-up.
- **G-c JSON key order.** See Review Focus 2; plan adds an order-preserving patcher (Task 2).
- **G-d Bone names.** The game reports joint indices only. Role/bone names come from the built package's `files/plan.json` (`joints[]`, `roles`, `role_joint`, `bank.clips`, `motion_rows`) read by `GenoData`.
- **G-e Ground modes have no data field.** Hover/anchored lives in per-row lists inside `ports/goku-xv2/tools/xv2_to_artist.py` (`HOVER_Y`). Plan adds `ground_modes.json` per port (Task 14) consumed by that script.
- **G-f `import_clip`** calls the retarget tool another lane is building: contract defined in Task 10 as a subprocess + JSON; the tool's real CLI is TBD by that lane and is configured in `workbench.json`.
- **G-g `set_frame` is not a seek.** The game cannot rewind; `wb.frame(f)` re-enters the motion with `gd.set_motion(port, motion, f)` and runs f-1 frames. Cost is O(f); fine for moves (<120 frames).
- **G-h Proposals default.** Agent edits apply immediately unless `propose:true` is passed or `Session::agentProposals` is on. Recommendation: on by default for MCP clients.
- **G-i Rebuild command per port** is configuration (`workbench.json: rebuild`), not code.

---

## File Structure

### Workspace repo (branch `ws/geno-workbench`)

All under `tools/release/launcher/qt/workbench/` unless noted.

| File | Responsibility |
|---|---|
| `CMakeLists.txt` | `workbench_core`, `workbench_ui`, test executables |
| `json_patch.h/.cpp` | order-preserving JSON value find/replace/insert (text level) |
| `file_store.h/.cpp` | project-rooted read/atomic write, snapshots, hash+mtime external-change detection |
| `history.h/.cpp` | undo/redo/proposals; entries carry before/after bytes; JSON persistence |
| `command_registry.h/.cpp` | typed commands, schema validation, result envelope |
| `geno_asm.h/.cpp` | parse `.genoasm`, list hitboxes with active frames, edit fields/frames |
| `project.h/.cpp` | `workbench.json` project config |
| `geno_data.h/.cpp` | read fighter source; produce `FileChange` lists for edits |
| `engine_link.h/.cpp` | `EngineBackend` interface, `ConsoleClient`, `EngineLink` (process + `wb.*` calls), `FrameInfo` |
| `checks.h/.cpp` | `suggestBone`, `runChecks` (pure) |
| `session.h/.cpp` | owns store/history/data/engine/registry; `commit()` |
| `commands_view.cpp`, `commands_rows.cpp`, `commands_hitbox.cpp`, `commands_clips.cpp`, `commands_ground.cpp`, `commands_save.cpp` | command registrations by area |
| `mcp_server.h/.cpp` | JSON-RPC server (pure `handle()` + stdio + localhost) |
| `testfixture.h` | builds a synthetic fighter project in a temp dir; `FakeEngine` |
| `workbench_window.*`, `viewport.*`, `timeline.*`, `panels.*`, `palette.*` | Widgets UI (`workbench_ui`) |
| `tests/*.cpp` | one QtTest executable per area |

Modified: `tools/release/launcher/qt/CMakeLists.txt` (add_subdirectory), `main.cpp` (`--mcp`, `--wb-call`, `--workbench`), `window.cpp` (Creator entry behind a setting), `tools/release/launcher/check_qt_strings.py` (also scan `workbench/`).

Other workspace files: `ports/goku-xv2/workbench.json`, `ports/goku-xv2/ground_modes.json`, `ports/goku-xv2/tools/xv2_to_artist.py` (read ground modes), `tools/workbench/compare_hitboxes.py` + `tools/workbench/test_compare_hitboxes.py`, `tools/workbench/acceptance.md`, `docs/workbench.md`, `tools/workbench/CLAUDE.md`.

### Game repo (branch `agent/geno-workbench`, worktree `worktrees/geno-workbench`)

| File | Responsibility |
|---|---|
| `pc/platform/gw_workbench.h/.c` | gate (`gw_Wb_Enabled`), payload dir, pure JSON writer for frame info, `wb` Lua table |
| `pc/gameworld/script_game.c` | `ScriptGame_WbFrame` accessor (bones, hitboxes, hurtboxes, ECB) |
| `pc/platform/gw_runtime.c` | scene mode `workbench` (alias of LAB) + flag |
| `pc/platform/gw_script.c` | register `wb` table; hook into `gs_gd_funcs` neighbours |
| `pc/tests/workbench_test.c` | pure native test (writer + gate) |
| `pc/tests/workbench_check.lua` | scripted in-game check |
| `tools/port/native_test.sh` (workspace repo, `tools/port/`) | add `workbench` case |

## Task Index and Parallelism

| # | Task | Repo | Group |
|---|---|---|---|
| 1 | Workbench CMake scaffold + synthetic fixture | W | A (start) |
| 2 | Order-preserving JSON patcher | W | A |
| 3 | FileStore + History | W | A |
| 4 | GenoAsm parser/editor | W | A |
| 5 | CommandRegistry + Session | W | after 3 |
| 6 | Project + GenoData | W | after 2,4 |
| 7 | EngineLink + ConsoleClient | W | A |
| 8 | Checks + suggestBone | W | A |
| 9 | Save/undo/propose commands | W | after 5,6 |
| 10 | Hitbox + clip commands (+import_clip contract) | W | after 6,7,8,9 |
| 11 | McpServer + CLI | W | after 5 (parallel with 6-10) |
| 12 | Game: workbench mode + wb.* | G | B (independent of W) |
| 13 | Compare script | W | after 12 |
| 14 | Ground modes | W | after 10 |
| 15 | UI shell, viewport, timeline | W | after 7,9 |
| 16 | UI panels, palette, strings | W | after 10,15 |
| 17 | Goku project file, acceptance, docs | W | last |

Parallel groups: **A** = tasks 1,2,3,4,7,8 (disjoint files; 1 first by whoever starts, others only need the CMake stub). **B** = task 12 (game, fully independent; a separate Sonnet lane). **C** = 11 (after 5) beside 6/9/10. Tasks 15 and 16 split between a Sonnet lane (UI) and Codex (palette + panels) once the commands exist.

---

### Task 1: Workbench CMake scaffold and synthetic fixture  (Workspace repo)

**Files:**
- Create: `tools/release/launcher/qt/workbench/CMakeLists.txt`
- Create: `tools/release/launcher/qt/workbench/testfixture.h`
- Create: `tools/release/launcher/qt/workbench/tests/scaffold_test.cpp`
- Modify: `tools/release/launcher/qt/CMakeLists.txt` (after the `launcher_ui` target block, before `qt_add_executable(gd-melee-launcher`)

**Interfaces:**
- Produces: CMake helper `wb_test(name)` (builds `tests/<name>.cpp` into exe `workbench_<name>`, CTest `workbench_<name>`); `makeSynthFighter(const QString& dir)` in `testfixture.h` creating the synthetic project (below); library targets `workbench_core`, `workbench_ui`.

- [ ] **Step 1: Create the worktree and branch**

```bash
cd "E:/Projects/Melee Workspace"
git worktree add worktrees/ws-geno-workbench -b ws/geno-workbench
cd worktrees/ws-geno-workbench
```

All workspace paths below are relative to this worktree.

- [ ] **Step 2: Write the fixture (the failing test's dependency)**

`tools/release/launcher/qt/workbench/testfixture.h`:

```cpp
#pragma once
// Synthetic fighter project for workbench tests. No disc- or XV2-derived data: names, numbers and
// bone roles are invented. Layout mirrors a port (ports/<id>/): gameplay.json, moves/*.genoasm,
// fidelity.json, workbench.json, and a stand-in for the built package's plan.json.
#include <QDir>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QString>

namespace wbtest {
inline void put(const QString &dir, const QString &rel, const QByteArray &data) {
    QFileInfo fi(QDir(dir).filePath(rel));
    QDir().mkpath(fi.absolutePath());
    QFile f(fi.absoluteFilePath());
    if (!f.open(QIODevice::WriteOnly)) qFatal("fixture: cannot write %s", qPrintable(rel));
    f.write(data);
}

inline const char *kGameplay = R"({
  "version": 1,
  "moves": [
    {
      "name": "jab1",
      "motions": [44],
      "tag": "jab",
      "script": "moves/jab1.genoasm",
      "iasa": 18,
      "pick": {"status": "provisional", "clip": "SYN_ATC_002", "crop_start": 9, "startup": 3}
    },
    {
      "name": "dair",
      "motions": [70],
      "tag": "aerial",
      "script": "moves/dair.genoasm",
      "iasa": 36,
      "pick": {"status": "provisional", "clip": "SYN_ATC_007", "crop_start": 2, "startup": 6}
    }
  ],
  "states": []
}
)";

inline const char *kJab = "# synthetic\nPUT ANIM_RATE 1.0\nwait_until 3\n"
    "hitbox slot=0 joint=@HAND_R@ damage=3 size=3.40 x=0.00 y=0.00 z=0.00 angle=361 kbg=50 fkb=0 bkb=8\n"
    "wait 2\nclear_hitboxes\nwait_until 18\niasa\n";

inline const char *kDair = "# synthetic\nPUT ANIM_RATE 1.0\nwait_until 6\n"
    "hitbox slot=0 joint=@FOOT_L@ damage=14 size=2.80 x=0.00 y=0.00 z=0.00 angle=270 kbg=90 fkb=0 bkb=20\n"
    "wait 3\nclear_hitboxes\nwait_until 9\n"
    "hitbox slot=0 joint=@FOOT_L@ damage=10 size=2.40 x=0.00 y=0.00 z=0.00 angle=361 kbg=90 fkb=0 bkb=15\n"
    "wait 6\nclear_hitboxes\nwait_until 36\niasa\n";

inline const char *kFidelity = R"({
 "schema": "synthetic-fidelity/1",
 "rows": [
  {"row": "Jab1", "motion": 44, "status": "SOURCE-RETIMED", "clip": "SYN_ATC_002", "source": "x", "source_clip": "x", "how": "", "deviation": "", "checked": []},
  {"row": "AirDown", "motion": 70, "status": "SOURCE-RETIMED", "clip": "SYN_ATC_007", "source": "x", "source_clip": "x", "how": "", "deviation": "", "checked": []}
 ]
}
)";

inline const char *kPlan = R"({
  "joints": [
    {"index": 0, "name": "TopN", "parent": null},
    {"index": 1, "name": "root", "parent": 0},
    {"index": 2, "name": "hand_r", "parent": 1},
    {"index": 3, "name": "foot_l", "parent": 1}
  ],
  "roles": {"hand.R": [2], "foot.L": [3]},
  "bank": {"clips": {"SYN_ATC_002": {"frames": 30}, "SYN_ATC_007": {"frames": 40}, "SYN_ATC_009": {"frames": 24}}},
  "motion_rows": [{"motion": 44, "row": "Jab1", "clip": "SYN_ATC_002"}, {"motion": 70, "row": "AirDown", "clip": "SYN_ATC_007"}]
})";

inline const char *kProject = R"({
  "schema": "workbench/1",
  "id": "synth",
  "gameplay": "gameplay.json",
  "moves_dir": "moves",
  "fidelity": "fidelity.json",
  "plan": "package/files/plan.json",
  "mod_id": "synth",
  "rebuild": ["python", "-c", "print('rebuilt')"],
  "import_clip": ["python", "-c", "import sys,json; print(json.dumps({'clip': 'SYN_IMPORTED', 'frames': 20}))"]
})";

// Creates the project in `dir` (must exist). Returns dir.
inline QString makeSynthFighter(const QString &dir) {
    put(dir, "gameplay.json", kGameplay);
    put(dir, "moves/jab1.genoasm", kJab);
    put(dir, "moves/dair.genoasm", kDair);
    put(dir, "fidelity.json", kFidelity);
    put(dir, "package/files/plan.json", kPlan);
    put(dir, "workbench.json", kProject);
    return dir;
}
}
```

- [ ] **Step 3: Write the failing scaffold test**

`tools/release/launcher/qt/workbench/tests/scaffold_test.cpp`:

```cpp
#include "../testfixture.h"
#include <QTemporaryDir>
#include <QtTest>

class ScaffoldTest : public QObject {
    Q_OBJECT
private slots:
    void fixtureIsValidJson() {
        QTemporaryDir tmp;
        QVERIFY(tmp.isValid());
        wbtest::makeSynthFighter(tmp.path());
        for (const char *rel : {"gameplay.json", "fidelity.json", "workbench.json", "package/files/plan.json"}) {
            QFile f(QDir(tmp.path()).filePath(rel));
            QVERIFY2(f.open(QIODevice::ReadOnly), rel);
            QJsonParseError err;
            QJsonDocument::fromJson(f.readAll(), &err);
            QVERIFY2(err.error == QJsonParseError::NoError, rel);
        }
        QVERIFY(QFile::exists(QDir(tmp.path()).filePath("moves/dair.genoasm")));
    }
};
QTEST_MAIN(ScaffoldTest)
#include "scaffold_test.moc"
```

- [ ] **Step 4: Write the CMake and wire it in**

`tools/release/launcher/qt/workbench/CMakeLists.txt`:

```cmake
# workbench_core: Qt Core/Network only (no Widgets). workbench_ui: Widgets, depends on launcher_ui for the Atlas look.
set(WB_CORE_SOURCES)  # appended by later tasks via wb_core_sources()
function(wb_core_sources)
  foreach(f IN LISTS ARGN)
    list(APPEND WB_CORE_SOURCES "${CMAKE_CURRENT_SOURCE_DIR}/${f}")
  endforeach()
  set(WB_CORE_SOURCES "${WB_CORE_SOURCES}" PARENT_SCOPE)
endfunction()

wb_core_sources()  # tasks add: json_patch.cpp file_store.cpp history.cpp ...
if(WB_CORE_SOURCES)
  add_library(workbench_core STATIC ${WB_CORE_SOURCES})
else()
  add_library(workbench_core STATIC empty.cpp)
endif()
target_link_libraries(workbench_core PUBLIC launcher_core Qt6::Core Qt6::Network)
target_include_directories(workbench_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

if(BUILD_TESTING)
  function(wb_test name)
    qt_add_executable(workbench_${name} tests/${name}.cpp)
    set_target_properties(workbench_${name} PROPERTIES WIN32_EXECUTABLE FALSE)
    target_link_libraries(workbench_${name} PRIVATE workbench_core Qt6::Test)
    add_test(NAME workbench_${name} COMMAND workbench_${name} -o "${CMAKE_CURRENT_BINARY_DIR}/${name}.txt,txt" -o "-,txt")
    set_tests_properties(workbench_${name} PROPERTIES ENVIRONMENT "QT_QPA_PLATFORM=offscreen")
  endfunction()
  wb_test(scaffold)
endif()
```

Create `tools/release/launcher/qt/workbench/empty.cpp` containing only `// placeholder removed once workbench_core has sources` -- delete it in Task 2 when `json_patch.cpp` lands (the `else()` branch is then dead; Task 2 removes it).

In `tools/release/launcher/qt/CMakeLists.txt`, directly after the `target_include_directories(launcher_ui ...)` line add:

```cmake
add_subdirectory(workbench)
```

- [ ] **Step 5: Build and run the test**

```bash
cmake -S tools/release/launcher/qt -B _build/wb-qt -G Ninja -DBUILD_TESTING=ON -DLAUNCHER_DEPLOY_QT=OFF
cmake --build _build/wb-qt --target workbench_scaffold
ctest --test-dir _build/wb-qt -R workbench_scaffold --output-on-failure
```

Expected: `100% tests passed, 0 tests failed out of 1`.

- [ ] **Step 6: Commit**

```bash
git add tools/release/launcher/qt/workbench tools/release/launcher/qt/CMakeLists.txt
git commit -m "workbench: CMake scaffold and synthetic fixture" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Order-preserving JSON patcher  (Workspace repo)

Why: `QJsonObject` sorts keys; re-serialising `gameplay.json` would rewrite the whole file. We edit by text span.

**Files:**
- Create: `workbench/json_patch.h`, `workbench/json_patch.cpp`
- Create: `workbench/tests/json_patch_test.cpp`
- Modify: `workbench/CMakeLists.txt` (`wb_core_sources(json_patch.cpp)`, `wb_test(json_patch)`, delete the `else()` branch and `empty.cpp`)

**Interfaces:**
- Produces:
  - `using wb::JsonPath = QStringList;` elements are object keys, or `#N` for array index N.
  - `bool wb::jsonFind(const QString &text, const JsonPath &path, int *start, int *end);` span of the value text (end exclusive).
  - `QString wb::jsonReplace(const QString &text, const JsonPath &path, const QString &valueText, QString *err);` returns new text; on failure returns `QString()` and sets `*err`.
  - `QString wb::jsonInsertKey(const QString &text, const JsonPath &objectPath, const QString &key, const QString &valueText, QString *err);` appends `"key": value` as the last member, matching the indent of the previous member.
  - `QString wb::jsonScalar(const QJsonValue &v);` compact text of a scalar/array/object value (`QJsonDocument::Compact`; doubles via shortest round-trip).

- [ ] **Step 1: Write the failing tests**

`workbench/tests/json_patch_test.cpp`:

```cpp
#include "json_patch.h"
#include <QJsonDocument>
#include <QtTest>
using namespace wb;

static const QString kDoc = QStringLiteral(
    "{\n  \"version\": 1,\n  \"moves\": [\n    {\n      \"name\": \"jab1\",\n      \"pick\": {\"clip\": \"A\", \"crop_start\": 9},\n"
    "      \"tag\": \"x,}\\\"\"\n    },\n    {\n      \"name\": \"dair\",\n      \"pick\": {\"clip\": \"B\", \"crop_start\": 2}\n    }\n  ],\n"
    "  \"zeta\": 1,\n  \"alpha\": 2\n}\n");

class JsonPatchTest : public QObject {
    Q_OBJECT
private slots:
    void findsNestedValue() {
        int s, e;
        QVERIFY(jsonFind(kDoc, {"moves", "#1", "pick", "clip"}, &s, &e));
        QCOMPARE(kDoc.mid(s, e - s), QString("\"B\""));
    }
    void missingPathFails() {
        int s, e;
        QVERIFY(!jsonFind(kDoc, {"moves", "#5"}, &s, &e));
        QVERIFY(!jsonFind(kDoc, {"nope"}, &s, &e));
    }
    void stringWithBracesAndEscapesIsSkipped() {
        int s, e;
        QVERIFY(jsonFind(kDoc, {"zeta"}, &s, &e));
        QCOMPARE(kDoc.mid(s, e - s), QString("1"));
    }
    void replaceLeavesEveryOtherByteIdentical() {
        QString err;
        QString out = jsonReplace(kDoc, {"moves", "#1", "pick", "clip"}, "\"C\"", &err);
        QVERIFY2(!out.isNull(), qPrintable(err));
        QString expect = kDoc;
        expect.replace("\"B\"", "\"C\"");
        QCOMPARE(out, expect);
    }
    void replaceKeepsKeyOrder() {
        QString err;
        QString out = jsonReplace(kDoc, {"zeta"}, "7", &err);
        QVERIFY(out.indexOf("zeta") < out.indexOf("alpha"));
    }
    void insertKeyAppendsWithIndent() {
        QString err;
        QString out = jsonInsertKey(kDoc, {"moves", "#0"}, "ground", "{\"mode\": \"hover\"}", &err);
        QVERIFY2(!out.isNull(), qPrintable(err));
        QVERIFY(out.contains("\"tag\": \"x,}\\\"\",\n      \"ground\": {\"mode\": \"hover\"}\n    }"));
        QJsonParseError pe;
        QJsonDocument::fromJson(out.toUtf8(), &pe);
        QCOMPARE(pe.error, QJsonParseError::NoError);
    }
    void insertIntoEmptyObject() {
        QString err;
        QString out = jsonInsertKey("{\n}\n", {}, "a", "1", &err);
        QVERIFY2(!out.isNull(), qPrintable(err));
        QJsonParseError pe;
        QCOMPARE(QJsonDocument::fromJson(out.toUtf8(), &pe).object().value("a").toInt(), 1);
    }
    void replaceMissingPathReportsError() {
        QString err;
        QVERIFY(jsonReplace(kDoc, {"moves", "#9", "name"}, "1", &err).isNull());
        QVERIFY(!err.isEmpty());
    }
    void scalarFormatting() {
        QCOMPARE(jsonScalar(QJsonValue(2.8)), QString("2.8"));
        QCOMPARE(jsonScalar(QJsonValue(9)), QString("9"));
        QCOMPARE(jsonScalar(QJsonValue("a\"b")), QString("\"a\\\"b\""));
    }
};
QTEST_MAIN(JsonPatchTest)
#include "json_patch_test.moc"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cmake --build _build/wb-qt --target workbench_json_patch` (after adding `wb_test(json_patch)`). Expected: FAIL to compile, `json_patch.h: No such file`.

- [ ] **Step 3: Implement**

`workbench/json_patch.h`:

```cpp
#pragma once
#include <QJsonValue>
#include <QString>
#include <QStringList>

namespace wb {
using JsonPath = QStringList;  // keys, or "#N" for array index N
bool jsonFind(const QString &text, const JsonPath &path, int *start, int *end);
QString jsonReplace(const QString &text, const JsonPath &path, const QString &valueText, QString *err);
QString jsonInsertKey(const QString &text, const JsonPath &objectPath, const QString &key, const QString &valueText, QString *err);
QString jsonScalar(const QJsonValue &v);
}
```

`workbench/json_patch.cpp`:

```cpp
#include "json_patch.h"
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>

namespace wb {
namespace {
int skipWs(const QString &t, int i) {
    while (i < t.size() && t[i].isSpace()) ++i;
    return i;
}
// returns index just past the string literal starting at i (t[i] == '"'), or -1
int skipString(const QString &t, int i) {
    if (i >= t.size() || t[i] != '"') return -1;
    for (++i; i < t.size(); ++i) {
        if (t[i] == '\\') { ++i; continue; }
        if (t[i] == '"') return i + 1;
    }
    return -1;
}
// returns index just past the value starting at i, or -1
int skipValue(const QString &t, int i) {
    i = skipWs(t, i);
    if (i >= t.size()) return -1;
    if (t[i] == '"') return skipString(t, i);
    if (t[i] == '{' || t[i] == '[') {
        int depth = 0;
        for (; i < t.size(); ++i) {
            if (t[i] == '"') { i = skipString(t, i); if (i < 0) return -1; --i; continue; }
            if (t[i] == '{' || t[i] == '[') ++depth;
            else if (t[i] == '}' || t[i] == ']') { if (--depth == 0) return i + 1; }
        }
        return -1;
    }
    while (i < t.size() && !QStringLiteral(",}]").contains(t[i]) && !t[i].isSpace()) ++i;
    return i;
}
// One step down: value at [vs, ve) is an object/array; find child by key or #N. Returns child span.
bool child(const QString &t, int vs, int ve, const QString &step, int *cs, int *ce) {
    (void) ve;
    int i = skipWs(t, vs);
    const bool arr = step.startsWith('#');
    if (i >= t.size() || t[i] != (arr ? '[' : '{')) return false;
    const int want = arr ? step.mid(1).toInt() : -1;
    int idx = 0;
    for (++i;;) {
        i = skipWs(t, i);
        if (i >= t.size() || t[i] == '}' || t[i] == ']') return false;
        QString key;
        if (!arr) {
            int ke = skipString(t, i);
            if (ke < 0) return false;
            key = t.mid(i + 1, ke - i - 2);
            i = skipWs(t, ke);
            if (i >= t.size() || t[i] != ':') return false;
            ++i;
        }
        i = skipWs(t, i);
        int e = skipValue(t, i);
        if (e < 0) return false;
        if (arr ? idx == want : key == step) { *cs = i; *ce = e; return true; }
        ++idx;
        i = skipWs(t, e);
        if (i < t.size() && t[i] == ',') ++i;
    }
}
}  // namespace

bool jsonFind(const QString &text, const JsonPath &path, int *start, int *end) {
    int s = skipWs(text, 0), e = skipValue(text, s);
    if (e < 0) return false;
    for (const QString &step : path) {
        int cs, ce;
        if (!child(text, s, e, step, &cs, &ce)) return false;
        s = cs; e = ce;
    }
    *start = s; *end = e;
    return true;
}

QString jsonReplace(const QString &text, const JsonPath &path, const QString &valueText, QString *err) {
    int s, e;
    if (!jsonFind(text, path, &s, &e)) {
        if (err) *err = "json path not found: " + path.join('/');
        return QString();
    }
    return text.left(s) + valueText + text.mid(e);
}

QString jsonInsertKey(const QString &text, const JsonPath &objectPath, const QString &key, const QString &valueText, QString *err) {
    int s, e;
    if (!jsonFind(text, objectPath, &s, &e) || text[s] != '{') {
        if (err) *err = "json object not found: " + objectPath.join('/');
        return QString();
    }
    int close = e - 1;  // the '}'
    int lastEnd = -1;   // end of the last member's value
    {
        int i = s + 1;
        for (;;) {
            i = skipWs(text, i);
            if (i >= close) break;
            int ke = skipString(text, i);
            if (ke < 0) break;
            i = skipWs(text, ke);
            ++i;  // ':'
            int ve = skipValue(text, i);
            if (ve < 0) break;
            lastEnd = ve;
            i = skipWs(text, ve);
            if (i < text.size() && text[i] == ',') ++i;
        }
    }
    const QString member = "\"" + key + "\": " + valueText;
    if (lastEnd < 0) {  // empty object
        return text.left(s + 1) + member + text.mid(close);
    }
    // indent of the previous member = whitespace between the last newline and its key
    int lineStart = text.lastIndexOf('\n', lastEnd) + 1;
    int firstKey = text.lastIndexOf('"', text.lastIndexOf(':', lastEnd));
    Q_UNUSED(firstKey);
    QString indent;
    {
        // walk back from lastEnd to the start of this member's line and take its leading spaces
        int ls = text.lastIndexOf('\n', lastEnd - 1) + 1;
        // the member may start on an earlier line than the value ends; find the line that starts with the key
        int k = text.lastIndexOf(QRegularExpression("\\n[ \\t]*\"[^\"\\n]*\"\\s*:"), lastEnd);
        if (k >= 0) {
            int j = k + 1;
            while (j < text.size() && (text[j] == ' ' || text[j] == '\t')) indent += text[j++];
        } else {
            indent = "";
        }
        Q_UNUSED(ls);
    }
    Q_UNUSED(lineStart);
    const bool multiline = text.mid(s, lastEnd - s).contains('\n');
    const QString sep = multiline ? ",\n" + indent : ", ";
    return text.left(lastEnd) + sep + member + text.mid(lastEnd);
}

QString jsonScalar(const QJsonValue &v) {
    if (v.isArray()) return QString::fromUtf8(QJsonDocument(v.toArray()).toJson(QJsonDocument::Compact));
    if (v.isObject()) return QString::fromUtf8(QJsonDocument(v.toObject()).toJson(QJsonDocument::Compact));
    // wrap in an array to reuse the serializer, strip the brackets
    QString s = QString::fromUtf8(QJsonDocument(QJsonArray{v}).toJson(QJsonDocument::Compact));
    return s.mid(1, s.size() - 2);
}
}  // namespace wb
```

Add `#include <QRegularExpression>` to the includes. (The indent-finder uses a regex for "last line that starts with a key at or before lastEnd".)

- [ ] **Step 4: Run tests**

Run: `cmake --build _build/wb-qt --target workbench_json_patch && ctest --test-dir _build/wb-qt -R workbench_json_patch --output-on-failure`
Expected: all 9 slots pass. If `insertKeyAppendsWithIndent` fails on indent, fix the regex step, not the test.

- [ ] **Step 5: Commit**

```bash
git add tools/release/launcher/qt/workbench
git commit -m "workbench: order-preserving JSON patcher" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: FileStore and History  (Workspace repo)

**Files:**
- Create: `workbench/file_store.h/.cpp`, `workbench/history.h/.cpp`
- Create: `workbench/tests/file_store_test.cpp`, `workbench/tests/history_test.cpp`
- Modify: `workbench/CMakeLists.txt` (sources + `wb_test(file_store)`, `wb_test(history)`)

**Interfaces:**
- Consumes: `launcher::writeAtomic(const QString&, const QByteArray&)`, `launcher::readText` (launcher_core.h).
- Produces:

```cpp
namespace wb {
struct FileChange { QString path; QByteArray before; QByteArray after; };   // path is project-relative
class FileStore {
public:
  explicit FileStore(QString root);
  QString root() const;
  bool exists(const QString &rel) const;
  QByteArray read(const QString &rel);                       // records hash as "known"
  void write(const QString &rel, const QByteArray &data);    // atomic; snapshots the old file once per snapshot group; records hash
  QString beginSnapshot(const QString &label);               // new group dir under .workbench/snapshots/; returns abs path
  QStringList externalChanges() const;                       // known paths whose disk hash differs from known
  void acknowledge(const QString &rel);
  static QString safeRel(const QString &rel, QString *err); // rejects "..", absolute, empty
  static QString hash(const QByteArray &d);
};
struct HistoryEntry {
  int id = 0; QString author, command, summary, state; // state: applied|undone|proposed|rejected
  QJsonObject args; QVector<FileChange> changes; qint64 time = 0;
};
class History {
public:
  int record(HistoryEntry e);            // state=applied; clears redo
  int propose(HistoryEntry e);           // state=proposed; does not touch files
  bool undo(FileStore &fs, QString *err);
  bool redo(FileStore &fs, QString *err);
  bool accept(int id, FileStore &fs, QString *err);
  bool reject(int id, QString *err);
  const QVector<HistoryEntry> &entries() const;
  QJsonArray toJson() const;             // metadata + base64 before/after
  static History fromJson(const QJsonArray &a);
  bool save(const QString &path) const;  // writeAtomic
  static History load(const QString &path);
};
}
```

Behaviour rules: `undo()` takes the newest `applied` entry; for each change it compares disk to `after`; any mismatch aborts with `err = "changed externally: <path>"` and writes nothing; else writes `before`, state=`undone`. `redo()` mirror (compares disk to `before`). `accept()` requires state `proposed` and disk == `before` for every change, else `err = "stale proposal: <path> changed since it was proposed"`; applies, state=`applied`. A missing file counts as empty bytes with `before` empty (new files).

- [ ] **Step 1: Write the failing tests**

`workbench/tests/file_store_test.cpp`:

```cpp
#include "file_store.h"
#include <QTemporaryDir>
#include <QtTest>
using namespace wb;

class FileStoreTest : public QObject {
    Q_OBJECT
private slots:
    void writeAndRead() {
        QTemporaryDir d; FileStore fs(d.path());
        fs.write("a/b.txt", "one");
        QCOMPARE(fs.read("a/b.txt"), QByteArray("one"));
    }
    void snapshotKeepsOldBytesBeforeOverwrite() {
        QTemporaryDir d; FileStore fs(d.path());
        fs.write("x.json", "old");
        QString snap = fs.beginSnapshot("save");
        fs.write("x.json", "new");
        fs.write("x.json", "newer");   // second write in the same group must not re-snapshot "new"
        QFile f(snap + "/x.json");
        QVERIFY(f.open(QIODevice::ReadOnly));
        QCOMPARE(f.readAll(), QByteArray("old"));
    }
    void detectsExternalChange() {
        QTemporaryDir d; FileStore fs(d.path());
        fs.write("g.json", "A");
        QVERIFY(fs.externalChanges().isEmpty());
        QFile f(d.filePath("g.json")); QVERIFY(f.open(QIODevice::WriteOnly)); f.write("B"); f.close();
        QCOMPARE(fs.externalChanges(), QStringList{"g.json"});
        fs.acknowledge("g.json");
        QVERIFY(fs.externalChanges().isEmpty());
    }
    void detectsExternalDelete() {
        QTemporaryDir d; FileStore fs(d.path());
        fs.write("g.json", "A");
        QFile::remove(d.filePath("g.json"));
        QCOMPARE(fs.externalChanges(), QStringList{"g.json"});
    }
    void rejectsEscapingPaths() {
        QString err;
        QVERIFY(FileStore::safeRel("../x", &err).isNull());
        QVERIFY(FileStore::safeRel("/etc/x", &err).isNull());
        QVERIFY(FileStore::safeRel("C:/x", &err).isNull());
        QVERIFY(FileStore::safeRel("", &err).isNull());
        QCOMPARE(FileStore::safeRel("a\\b.txt", &err), QString("a/b.txt"));
    }
};
QTEST_MAIN(FileStoreTest)
#include "file_store_test.moc"
```

`workbench/tests/history_test.cpp`:

```cpp
#include "history.h"
#include <QTemporaryDir>
#include <QtTest>
using namespace wb;

static HistoryEntry edit(const QString &path, const QByteArray &b, const QByteArray &a, const QString &author = "human") {
    HistoryEntry e; e.author = author; e.command = "t"; e.summary = "s";
    e.changes.append({path, b, a});
    return e;
}

class HistoryTest : public QObject {
    Q_OBJECT
private slots:
    void undoRedoRoundTrip() {
        QTemporaryDir d; FileStore fs(d.path()); History h;
        fs.write("f", "1");
        fs.write("f", "2");
        h.record(edit("f", "1", "2"));
        QString err;
        QVERIFY2(h.undo(fs, &err), qPrintable(err));
        QCOMPARE(fs.read("f"), QByteArray("1"));
        QVERIFY2(h.redo(fs, &err), qPrintable(err));
        QCOMPARE(fs.read("f"), QByteArray("2"));
    }
    void undoRefusesAfterExternalEdit() {
        QTemporaryDir d; FileStore fs(d.path()); History h;
        fs.write("f", "2"); h.record(edit("f", "1", "2"));
        QFile f(d.filePath("f")); QVERIFY(f.open(QIODevice::WriteOnly)); f.write("HAND"); f.close();
        QString err;
        QVERIFY(!h.undo(fs, &err));
        QVERIFY(err.contains("changed externally"));
        QCOMPARE(fs.read("f"), QByteArray("HAND"));   // untouched
    }
    void newRecordClearsRedo() {
        QTemporaryDir d; FileStore fs(d.path()); History h; QString err;
        fs.write("f", "2"); h.record(edit("f", "1", "2")); QVERIFY(h.undo(fs, &err));
        fs.write("f", "9"); h.record(edit("f", "1", "9"));
        QVERIFY(!h.redo(fs, &err));
    }
    void proposalDoesNotTouchFilesUntilAccepted() {
        QTemporaryDir d; FileStore fs(d.path()); History h; QString err;
        fs.write("f", "1");
        int id = h.propose(edit("f", "1", "2", "agent"));
        QCOMPARE(fs.read("f"), QByteArray("1"));
        QVERIFY2(h.accept(id, fs, &err), qPrintable(err));
        QCOMPARE(fs.read("f"), QByteArray("2"));
    }
    void staleProposalIsRefused() {
        QTemporaryDir d; FileStore fs(d.path()); History h; QString err;
        fs.write("f", "1");
        int id = h.propose(edit("f", "1", "2", "agent"));
        fs.write("f", "OTHER");
        QVERIFY(!h.accept(id, fs, &err));
        QVERIFY(err.contains("stale proposal"));
    }
    void rejectMarksRejected() {
        History h; QString err;
        int id = h.propose(edit("f", "1", "2", "agent"));
        QVERIFY(h.reject(id, &err));
        QCOMPARE(h.entries().first().state, QString("rejected"));
    }
    void persistsAcrossSessions() {
        QTemporaryDir d; History h;
        h.record(edit("f", QByteArray("\x00\x01", 2), "2"));
        QVERIFY(h.save(d.filePath("history.json")));
        History h2 = History::load(d.filePath("history.json"));
        QCOMPARE(h2.entries().size(), 1);
        QCOMPARE(h2.entries().first().changes.first().before, QByteArray("\x00\x01", 2));
    }
    void newFileUndoDeletesIt() {
        QTemporaryDir d; FileStore fs(d.path()); History h; QString err;
        fs.write("new.txt", "x"); h.record(edit("new.txt", "", "x"));
        QVERIFY2(h.undo(fs, &err), qPrintable(err));
        QVERIFY(!fs.exists("new.txt"));
    }
};
QTEST_MAIN(HistoryTest)
#include "history_test.moc"
```

(`FileStore` needs a `remove(rel)` used by undo when `before` is empty and the file did not exist; add `bool remove(const QString&)`; empty `before` on a path that did not pre-exist deletes it. Record "did not exist" as `before.isNull()`; `QByteArray()` is null, `QByteArray("")` is not. The test's `""` literal is a non-null empty array: treat `isEmpty()` as "absent" for simplicity; empty source files are not valid fighter source.)

- [ ] **Step 2: Run to verify failure**

Run: `cmake --build _build/wb-qt --target workbench_file_store workbench_history`. Expected: compile error (headers missing).

- [ ] **Step 3: Implement `file_store.*`**

`workbench/file_store.h`: the declarations from Interfaces, plus `bool remove(const QString &rel);` and members `QString root_; QHash<QString, QString> known_; QString snapDir_; QSet<QString> snapped_;`.

`workbench/file_store.cpp`:

```cpp
#include "file_store.h"
#include "launcher_core.h"
#include <QCryptographicHash>
#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QFileInfo>

namespace wb {
FileStore::FileStore(QString root) : root_(QDir(root).absolutePath()) {}
QString FileStore::root() const { return root_; }

QString FileStore::safeRel(const QString &rel, QString *err) {
    QString r = QDir::fromNativeSeparators(rel);
    bool bad = r.isEmpty() || r.startsWith('/') || (r.size() > 1 && r[1] == ':') || r.split('/').contains("..");
    if (bad) { if (err) *err = "unsafe path: " + rel; return QString(); }
    return r;
}
QString FileStore::hash(const QByteArray &d) { return QString::fromLatin1(QCryptographicHash::hash(d, QCryptographicHash::Sha256).toHex()); }

static QString abs(const QString &root, const QString &rel) {
    QString err; QString r = FileStore::safeRel(rel, &err);
    if (r.isNull()) qFatal("FileStore: %s", qPrintable(err));
    return QDir(root).filePath(r);
}
bool FileStore::exists(const QString &rel) const { return QFileInfo::exists(abs(root_, rel)); }

QByteArray FileStore::read(const QString &rel) {
    QFile f(abs(root_, rel));
    if (!f.open(QIODevice::ReadOnly)) return QByteArray();
    QByteArray d = f.readAll();
    known_[rel] = hash(d);
    return d;
}
QString FileStore::beginSnapshot(const QString &label) {
    snapDir_ = QDir(root_).filePath(".workbench/snapshots/" + QDateTime::currentDateTimeUtc().toString("yyyyMMdd-HHmmsszzz") + "-" + label);
    QDir().mkpath(snapDir_);
    snapped_.clear();
    return snapDir_;
}
void FileStore::write(const QString &rel, const QByteArray &data) {
    const QString p = abs(root_, rel);
    if (!snapDir_.isEmpty() && !snapped_.contains(rel) && QFileInfo::exists(p)) {
        const QString dst = QDir(snapDir_).filePath(rel);
        QDir().mkpath(QFileInfo(dst).absolutePath());
        QFile::copy(p, dst);
    }
    snapped_.insert(rel);
    QDir().mkpath(QFileInfo(p).absolutePath());
    launcher::writeAtomic(p, data);
    known_[rel] = hash(data);
}
bool FileStore::remove(const QString &rel) { known_.remove(rel); return QFile::remove(abs(root_, rel)); }
QStringList FileStore::externalChanges() const {
    QStringList out;
    for (auto it = known_.cbegin(); it != known_.cend(); ++it) {
        QFile f(abs(root_, it.key()));
        QString now = f.open(QIODevice::ReadOnly) ? hash(f.readAll()) : QString("<missing>");
        if (now != it.value()) out << it.key();
    }
    out.sort();
    return out;
}
void FileStore::acknowledge(const QString &rel) {
    QFile f(abs(root_, rel));
    if (f.open(QIODevice::ReadOnly)) known_[rel] = hash(f.readAll()); else known_.remove(rel);
}
}  // namespace wb
```

Note: `snapped_.insert(rel)` after the first write means a path created in the group is also never snapshotted again; `beginSnapshot` resets it.

- [ ] **Step 4: Implement `history.*`**

```cpp
#include "history.h"
#include <QDateTime>
#include <QJsonDocument>
#include <QJsonObject>
#include "launcher_core.h"

namespace wb {
static QByteArray diskOrEmpty(FileStore &fs, const QString &p) { return fs.exists(p) ? fs.read(p) : QByteArray(); }
static void put(FileStore &fs, const QString &p, const QByteArray &d) { if (d.isEmpty()) fs.remove(p); else fs.write(p, d); }

int History::record(HistoryEntry e) {
    e.id = ++nextId_; e.state = "applied"; e.time = QDateTime::currentSecsSinceEpoch();
    // new work invalidates redo: entries that are "undone" are dropped
    entries_.erase(std::remove_if(entries_.begin(), entries_.end(), [](const HistoryEntry &x) { return x.state == "undone"; }), entries_.end());
    entries_.append(e);
    return e.id;
}
int History::propose(HistoryEntry e) {
    e.id = ++nextId_; e.state = "proposed"; e.time = QDateTime::currentSecsSinceEpoch();
    entries_.append(e);
    return e.id;
}
bool History::undo(FileStore &fs, QString *err) {
    for (int i = entries_.size() - 1; i >= 0; --i) {
        if (entries_[i].state != "applied") continue;
        for (const FileChange &c : entries_[i].changes)
            if (diskOrEmpty(fs, c.path) != c.after) { if (err) *err = "changed externally: " + c.path; return false; }
        fs.beginSnapshot("undo");
        for (const FileChange &c : entries_[i].changes) put(fs, c.path, c.before);
        entries_[i].state = "undone";
        return true;
    }
    if (err) *err = "nothing to undo";
    return false;
}
bool History::redo(FileStore &fs, QString *err) {
    for (int i = 0; i < entries_.size(); ++i) {
        if (entries_[i].state != "undone") continue;
        for (const FileChange &c : entries_[i].changes)
            if (diskOrEmpty(fs, c.path) != c.before) { if (err) *err = "changed externally: " + c.path; return false; }
        fs.beginSnapshot("redo");
        for (const FileChange &c : entries_[i].changes) put(fs, c.path, c.after);
        entries_[i].state = "applied";
        return true;
    }
    if (err) *err = "nothing to redo";
    return false;
}
bool History::accept(int id, FileStore &fs, QString *err) {
    for (HistoryEntry &e : entries_) {
        if (e.id != id) continue;
        if (e.state != "proposed") { if (err) *err = "not a proposal"; return false; }
        for (const FileChange &c : e.changes)
            if (diskOrEmpty(fs, c.path) != c.before) { if (err) *err = "stale proposal: " + c.path + " changed since it was proposed"; return false; }
        fs.beginSnapshot("accept");
        for (const FileChange &c : e.changes) put(fs, c.path, c.after);
        e.state = "applied";
        return true;
    }
    if (err) *err = "no such entry";
    return false;
}
bool History::reject(int id, QString *err) {
    for (HistoryEntry &e : entries_)
        if (e.id == id) {
            if (e.state != "proposed") { if (err) *err = "not a proposal"; return false; }
            e.state = "rejected"; return true;
        }
    if (err) *err = "no such entry";
    return false;
}
const QVector<HistoryEntry> &History::entries() const { return entries_; }

QJsonArray History::toJson() const {
    QJsonArray a;
    for (const HistoryEntry &e : entries_) {
        QJsonArray ch;
        for (const FileChange &c : e.changes)
            ch.append(QJsonObject{{"path", c.path}, {"before", QString::fromLatin1(c.before.toBase64())}, {"after", QString::fromLatin1(c.after.toBase64())}});
        a.append(QJsonObject{{"id", e.id}, {"author", e.author}, {"command", e.command}, {"summary", e.summary}, {"state", e.state},
                             {"args", e.args}, {"time", double(e.time)}, {"changes", ch}});
    }
    return a;
}
History History::fromJson(const QJsonArray &a) {
    History h;
    for (const QJsonValue &v : a) {
        QJsonObject o = v.toObject();
        HistoryEntry e;
        e.id = o["id"].toInt(); e.author = o["author"].toString(); e.command = o["command"].toString();
        e.summary = o["summary"].toString(); e.state = o["state"].toString(); e.args = o["args"].toObject(); e.time = qint64(o["time"].toDouble());
        for (const QJsonValue &cv : o["changes"].toArray()) {
            QJsonObject c = cv.toObject();
            e.changes.append({c["path"].toString(), QByteArray::fromBase64(c["before"].toString().toLatin1()), QByteArray::fromBase64(c["after"].toString().toLatin1())});
        }
        h.nextId_ = std::max(h.nextId_, e.id);
        h.entries_.append(e);
    }
    return h;
}
bool History::save(const QString &path) const {
    try { launcher::writeAtomic(path, QJsonDocument(toJson()).toJson(QJsonDocument::Compact)); return true; } catch (...) { return false; }
}
History History::load(const QString &path) {
    QFile f(path);
    if (!f.open(QIODevice::ReadOnly)) return History();
    return fromJson(QJsonDocument::fromJson(f.readAll()).array());
}
}  // namespace wb
```

Header adds `#include <QJsonArray> <QJsonObject> <QVector> <QByteArray>`, `#include "file_store.h"`, and private members `QVector<HistoryEntry> entries_; int nextId_ = 0;`. Add `#include <algorithm>`.

- [ ] **Step 5: Register and run**

Add to `CMakeLists.txt`: `wb_core_sources(file_store.cpp history.cpp)`, `wb_test(file_store)`, `wb_test(history)`.

Run: `cmake --build _build/wb-qt --target workbench_file_store workbench_history && ctest --test-dir _build/wb-qt -R "workbench_(file_store|history)" --output-on-failure`
Expected: 2 of 2 pass (5 + 8 slots).

- [ ] **Step 6: Commit**

```bash
git add tools/release/launcher/qt/workbench
git commit -m "workbench: FileStore with snapshots and external-change detection; History with undo/redo/proposals" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: GenoAsm parser and editor  (Workspace repo)

The `.genoasm` hitbox lines look like `hitbox slot=0 joint=@FOOT_L@ damage=14 size=2.80 x=0.00 y=0.00 z=0.00 angle=270 kbg=90 fkb=0 bkb=20`. Time advances with `wait_until N` (absolute) and `wait N` (relative); `clear_hitboxes` ends every active hitbox.

**Files:**
- Create: `workbench/geno_asm.h/.cpp`, `workbench/tests/geno_asm_test.cpp`
- Modify: `workbench/CMakeLists.txt`

**Interfaces:**
- Produces:

```cpp
namespace wb {
struct HitboxRef {
  int ordinal = 0;      // order in file, 0-based (hitbox id within a row)
  int line = 0;         // 0-based line index of the "hitbox" op
  int slot = 0; QString joint;           // joint without @ signs, e.g. "FOOT_L"
  double damage = 0, size = 0, x = 0, y = 0, z = 0;
  int angle = 0, kbg = 0, fkb = 0, bkb = 0;
  int startFrame = 0;                    // frame the hitbox appears (time at the op)
  int endFrame = -1;                     // exclusive; -1 = never cleared
};
struct HitboxEdit {                      // unset = leave alone
  std::optional<QString> joint; std::optional<double> damage, size, x, y, z;
  std::optional<int> angle, kbg, fkb, bkb, startFrame, endFrame;
};
class GenoAsm {
public:
  static GenoAsm parse(const QString &text);
  QVector<HitboxRef> hitboxes() const;
  QString apply(int ordinal, const HitboxEdit &edit, QString *err) const;  // new text, or null + err
  QString text() const;
};
}
```

Rules for `apply` with `startFrame`/`endFrame`: allowed only when lines are exactly `wait_until S` (immediately before the hitbox line, ignoring `#` comments and blank lines), and `wait D` followed by `clear_hitboxes` (immediately after, same ignoring), and the hitbox is the only one active in that span; then S := startFrame, D := endFrame - startFrame (must be > 0). Otherwise return null with `err = "frames not editable for this script shape: <why>"`. Other fields rewrite only that `key=value` token (floats with two decimals except `damage` printed as integer when whole), preserving all other tokens and the rest of the text byte for byte. `joint` is written as `@NAME@` (input may include or omit the `@`).

- [ ] **Step 1: Write the failing tests**

```cpp
#include "../testfixture.h"
#include "geno_asm.h"
#include <QtTest>
using namespace wb;

class GenoAsmTest : public QObject {
    Q_OBJECT
private slots:
    void listsHitboxesWithFrames() {
        auto hb = GenoAsm::parse(wbtest::kDair).hitboxes();
        QCOMPARE(hb.size(), 2);
        QCOMPARE(hb[0].joint, QString("FOOT_L"));
        QCOMPARE(hb[0].startFrame, 6); QCOMPARE(hb[0].endFrame, 9);
        QCOMPARE(hb[1].startFrame, 9); QCOMPARE(hb[1].endFrame, 15);
        QCOMPARE(hb[0].damage, 14.0); QCOMPARE(hb[0].size, 2.8); QCOMPARE(hb[0].angle, 270);
    }
    void unclearedHitboxHasOpenEnd() {
        auto hb = GenoAsm::parse("wait_until 4\nhitbox slot=0 joint=@A@ damage=1 size=1 x=0 y=0 z=0 angle=0 kbg=0 fkb=0 bkb=0\n").hitboxes();
        QCOMPARE(hb.size(), 1); QCOMPARE(hb[0].endFrame, -1);
    }
    void noHitboxesOrEmptyText() {
        QCOMPARE(GenoAsm::parse("").hitboxes().size(), 0);
        QCOMPARE(GenoAsm::parse("wait_until 3\niasa\n").hitboxes().size(), 0);
    }
    void hitboxBeforeAnyWaitStartsAtZero() {
        auto hb = GenoAsm::parse("hitbox slot=0 joint=@A@ damage=1 size=1 x=0 y=0 z=0 angle=0 kbg=0 fkb=0 bkb=0\nclear_hitboxes\n").hitboxes();
        QCOMPARE(hb[0].startFrame, 0); QCOMPARE(hb[0].endFrame, 0);
    }
    void editJointOnlyTouchesThatToken() {
        QString err; HitboxEdit e; e.joint = "HAND_R";
        QString out = GenoAsm::parse(wbtest::kDair).apply(0, e, &err);
        QVERIFY2(!out.isNull(), qPrintable(err));
        QString expect = wbtest::kDair;
        expect.replace(expect.indexOf("@FOOT_L@"), 8, "@HAND_R@");
        QCOMPARE(out, expect);
    }
    void editNumbers() {
        QString err; HitboxEdit e; e.damage = 12; e.size = 3.25; e.angle = 45;
        QString out = GenoAsm::parse(wbtest::kJab).apply(0, e, &err);
        QVERIFY2(!out.isNull(), qPrintable(err));
        auto hb = GenoAsm::parse(out).hitboxes();
        QCOMPARE(hb[0].damage, 12.0); QCOMPARE(hb[0].size, 3.25); QCOMPARE(hb[0].angle, 45);
        QVERIFY(out.contains("size=3.25 "));
        QVERIFY(out.contains("damage=12 "));
    }
    void editFramesRewritesWaits() {
        QString err; HitboxEdit e; e.startFrame = 7; e.endFrame = 11;
        QString out = GenoAsm::parse(wbtest::kDair).apply(0, e, &err);
        QVERIFY2(!out.isNull(), qPrintable(err));
        auto hb = GenoAsm::parse(out).hitboxes();
        QCOMPARE(hb[0].startFrame, 7); QCOMPARE(hb[0].endFrame, 11);
        QCOMPARE(hb[1].startFrame, 9);   // second hitbox unaffected: wait_until is absolute
    }
    void editFramesRefusesWeirdShape() {
        QString text = "hitbox slot=0 joint=@A@ damage=1 size=1 x=0 y=0 z=0 angle=0 kbg=0 fkb=0 bkb=0\nwait 3\nwait 1\nclear_hitboxes\n";
        QString err; HitboxEdit e; e.endFrame = 9;
        QVERIFY(GenoAsm::parse(text).apply(0, e, &err).isNull());
        QVERIFY(err.contains("frames not editable"));
    }
    void editUnknownOrdinalFails() {
        QString err; HitboxEdit e; e.damage = 1;
        QVERIFY(GenoAsm::parse(wbtest::kJab).apply(5, e, &err).isNull());
        QVERIFY(!err.isEmpty());
    }
    void windowsLineEndingsSurvive() {
        QString crlf = QString(wbtest::kJab).replace("\n", "\r\n");
        auto hb = GenoAsm::parse(crlf).hitboxes();
        QCOMPARE(hb.size(), 1); QCOMPARE(hb[0].startFrame, 3);
        QString err; HitboxEdit e; e.damage = 5;
        QString out = GenoAsm::parse(crlf).apply(0, e, &err);
        QVERIFY(out.contains("\r\n") && !out.contains("\n\n"));
    }
};
QTEST_MAIN(GenoAsmTest)
#include "geno_asm_test.moc"
```

- [ ] **Step 2: Run to verify failure**

Run: `cmake --build _build/wb-qt --target workbench_geno_asm` Expected: compile error (no `geno_asm.h`).

- [ ] **Step 3: Implement**

`geno_asm.cpp` structure (write exactly this algorithm):

```cpp
#include "geno_asm.h"
#include <QRegularExpression>

namespace wb {
namespace {
struct Tok { QString key, val; };   // "key=value" tokens of a line, in order
QString eolOf(const QString &t) { return t.contains("\r\n") ? "\r\n" : "\n"; }
QStringList splitLines(const QString &t) {   // without terminators
    QString u = t; u.replace("\r\n", "\n");
    QStringList l = u.split('\n');
    if (!l.isEmpty() && l.last().isEmpty()) l.removeLast();
    return l;
}
QString opOf(const QString &line) { QString s = line.trimmed(); return s.isEmpty() || s[0] == '#' ? QString() : s.section(QRegularExpression("\\s+"), 0, 0); }
bool significant(const QString &line) { return !opOf(line).isEmpty(); }
QString fmtNum(double v) { return v == int(v) ? QString::number(int(v)) : QString::number(v, 'f', 2); }
}

GenoAsm GenoAsm::parse(const QString &text) { GenoAsm a; a.text_ = text; a.eol_ = eolOf(text); a.lines_ = splitLines(text); a.trailingEol_ = text.endsWith('\n'); return a; }
QString GenoAsm::text() const { return text_; }

QVector<HitboxRef> GenoAsm::hitboxes() const {
    QVector<HitboxRef> out; int t = 0; QVector<int> open;
    for (int i = 0; i < lines_.size(); ++i) {
        const QString op = opOf(lines_[i]); const QStringList w = lines_[i].trimmed().split(QRegularExpression("\\s+"));
        if (op == "wait_until" && w.size() > 1) t = w[1].toInt();
        else if (op == "wait" && w.size() > 1) t += w[1].toInt();
        else if (op == "clear_hitboxes") { for (int k : open) out[k].endFrame = t; open.clear(); }
        else if (op == "hitbox") {
            HitboxRef h; h.ordinal = out.size(); h.line = i; h.startFrame = t;
            for (int k = 1; k < w.size(); ++k) {
                int eq = w[k].indexOf('='); if (eq < 0) continue;
                const QString key = w[k].left(eq), v = w[k].mid(eq + 1);
                if (key == "slot") h.slot = v.toInt();
                else if (key == "joint") { h.joint = v; h.joint.remove('@'); }
                else if (key == "damage") h.damage = v.toDouble();
                else if (key == "size") h.size = v.toDouble();
                else if (key == "x") h.x = v.toDouble(); else if (key == "y") h.y = v.toDouble(); else if (key == "z") h.z = v.toDouble();
                else if (key == "angle") h.angle = v.toInt(); else if (key == "kbg") h.kbg = v.toInt();
                else if (key == "fkb") h.fkb = v.toInt(); else if (key == "bkb") h.bkb = v.toInt();
            }
            open.append(out.size()); out.append(h);
        }
    }
    return out;
}
```

`apply()`:
1. find `HitboxRef h` by ordinal, else `err="no hitbox #N"`.
2. Build replacements `QMap<QString,QString>` for key → text (`joint` → `"@"+name.remove('@')+"@"`, `damage` via `fmtNum`, `size/x/y/z` via `QString::number(v,'f',2)`, ints via `QString::number`).
3. Rewrite the hitbox line by regex per key: `QRegularExpression("(^|\\s)" + key + "=\\S+")` replace captured `\\1key=value`. If the key is absent in the line, append ` key=value`.
4. For frames (either set): let `s = edit.startFrame.value_or(h.startFrame)`, `e = edit.endFrame.value_or(h.endFrame)`. Find `prev` = nearest earlier significant line index, `next1` = nearest later significant line, `next2` = the one after. Require `opOf(lines_[prev])=="wait_until"`, `opOf(lines_[next1])=="wait"`, `opOf(lines_[next2])=="clear_hitboxes"`, and that no other hitbox starts between (they cannot: next ops are wait/clear). Else `err = "frames not editable for this script shape: expected wait_until / hitbox / wait / clear_hitboxes"`. Require `e > s` else `err="end frame must be after start frame"`. Set `lines_[prev] = "wait_until " + s` (preserve leading whitespace), `lines_[next1] = "wait " + (e - s)`.
5. Join with `eol_`, add trailing eol if `trailingEol_`. Return.

`apply` is const: operate on a copy of `lines_`. Header declares members `QString text_, eol_; QStringList lines_; bool trailingEol_ = false;` and `#include <optional>`.

- [ ] **Step 4: Run tests**

Run: `cmake --build _build/wb-qt --target workbench_geno_asm && ctest --test-dir _build/wb-qt -R workbench_geno_asm --output-on-failure`
Expected: 10 slots pass.

- [ ] **Step 5: Commit**

```bash
git add tools/release/launcher/qt/workbench
git commit -m "workbench: genoasm hitbox parser and editor" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: CommandRegistry and Session  (Workspace repo)

**Files:**
- Create: `workbench/command_registry.h/.cpp`, `workbench/session.h/.cpp`
- Create: `workbench/tests/command_registry_test.cpp`
- Modify: `workbench/CMakeLists.txt`

**Interfaces:**
- Consumes: `FileStore`, `History`, `FileChange`.
- Produces:

```cpp
namespace wb {
class Session;
struct CommandContext { Session &session; QString author = "human"; bool propose = false; };
struct CommandError { QString message; };                      // thrown by handlers
using Handler = std::function<QJsonObject(const QJsonObject &args, CommandContext &ctx)>;
struct CommandSpec {
  QString name, description; QJsonObject inputSchema;           // JSON Schema subset: type, properties, required, enum
  bool mutating = false; Handler run;
};
class CommandRegistry {
public:
  void add(CommandSpec spec);                                   // duplicate name -> qFatal
  bool has(const QString &name) const;
  QVector<CommandSpec> list() const;                            // registration order
  // Always returns {"ok":true,"result":{...}} or {"ok":false,"error":"..."}; never throws.
  QJsonObject call(const QString &name, const QJsonObject &args, CommandContext &ctx) const;
  static QString validate(const QJsonObject &schema, const QJsonObject &args);   // "" if ok, else message
};
class EngineBackend;   // engine_link.h (Task 7); forward-declared here
class GenoData;        // geno_data.h (Task 6)
class Session {
public:
  Session(const QString &projectDir, EngineBackend *engine);   // engine may be null (offline: engine commands return an error)
  ~Session();
  FileStore &files(); History &history(); CommandRegistry &registry();
  GenoData &data(); EngineBackend *engine();
  bool agentProposals = false;
  // The ONLY way a command changes files. Applies (writes + records) or proposes.
  QJsonObject commit(const CommandContext &ctx, const QString &command, const QJsonObject &args,
                     const QString &summary, const QVector<FileChange> &changes);
  QString historyPath() const;        // <project>/.workbench/history.json
};
}
```

`commit` rules: if `changes` empty -> `{"applied":false,"note":"no change"}`. If `ctx.propose || (ctx.author=="agent" && agentProposals)` -> `history.propose`, return `{"proposed":true,"entry":id}`. Else check `files.externalChanges()` intersect `changes` paths -> throw `CommandError{"changed externally: <path>"}`; `files.beginSnapshot(command)`; write each `after`; `data().reload()`; `history.record`; `history.save(historyPath())`; return `{"applied":true,"entry":id}`.

Because `GenoData` lands in Task 6, make this task compile with a forward declaration and have `Session::data()` defined in Task 6 (Task 5's `session.cpp` holds `std::unique_ptr<GenoData>` constructed in Task 6). To keep Task 5 testable alone: `Session` stores `std::function<void()> onApplied` hook (default no-op) that Task 6 sets to `data().reload()`. Remove `data()` from this task's public API; Task 6 adds it.

- [ ] **Step 1: Write the failing tests**

```cpp
#include "../testfixture.h"
#include "command_registry.h"
#include "session.h"
#include <QTemporaryDir>
#include <QtTest>
using namespace wb;

static CommandSpec echo() {
    CommandSpec s; s.name = "echo"; s.description = "echo";
    s.inputSchema = QJsonDocument::fromJson(R"({"type":"object","required":["n"],"properties":{"n":{"type":"integer"},"mode":{"type":"string","enum":["a","b"]}}})").object();
    s.run = [](const QJsonObject &a, CommandContext &) { return QJsonObject{{"n", a["n"]}}; };
    return s;
}

class RegistryTest : public QObject {
    Q_OBJECT
private slots:
    void callsAndWrapsResult() {
        QTemporaryDir d; Session s(d.path(), nullptr); CommandContext c{s};
        s.registry().add(echo());
        QJsonObject r = s.registry().call("echo", {{"n", 3}}, c);
        QVERIFY(r["ok"].toBool()); QCOMPARE(r["result"].toObject()["n"].toInt(), 3);
    }
    void unknownCommand() {
        QTemporaryDir d; Session s(d.path(), nullptr); CommandContext c{s};
        QJsonObject r = s.registry().call("nope", {}, c);
        QVERIFY(!r["ok"].toBool()); QVERIFY(r["error"].toString().contains("unknown command"));
    }
    void validationErrors() {
        QTemporaryDir d; Session s(d.path(), nullptr); CommandContext c{s};
        s.registry().add(echo());
        QVERIFY(s.registry().call("echo", {}, c)["error"].toString().contains("missing required: n"));
        QVERIFY(s.registry().call("echo", {{"n", "x"}}, c)["error"].toString().contains("n: expected integer"));
        QVERIFY(s.registry().call("echo", {{"n", 1.5}}, c)["error"].toString().contains("n: expected integer"));
        QVERIFY(s.registry().call("echo", {{"n", 1}, {"mode", "z"}}, c)["error"].toString().contains("mode: not one of"));
    }
    void handlerExceptionBecomesError() {
        QTemporaryDir d; Session s(d.path(), nullptr); CommandContext c{s};
        CommandSpec t; t.name = "boom"; t.inputSchema = QJsonObject{{"type", "object"}};
        t.run = [](const QJsonObject &, CommandContext &) -> QJsonObject { throw CommandError{"bad thing"}; };
        s.registry().add(t);
        QJsonObject r = s.registry().call("boom", {}, c);
        QVERIFY(!r["ok"].toBool()); QCOMPARE(r["error"].toString(), QString("bad thing"));
    }
    void commitWritesSnapshotsAndRecords() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); Session s(d.path(), nullptr); CommandContext c{s};
        s.files().read("fidelity.json");
        QByteArray old = s.files().read("moves/jab1.genoasm");
        QJsonObject r = s.commit(c, "edit", {}, "test", {{"moves/jab1.genoasm", old, "changed\n"}});
        QVERIFY(r["applied"].toBool());
        QCOMPARE(s.files().read("moves/jab1.genoasm"), QByteArray("changed\n"));
        QCOMPARE(s.history().entries().size(), 1);
        QVERIFY(QFile::exists(d.filePath(".workbench/history.json")));
    }
    void commitRefusesWhenFileChangedExternally() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); Session s(d.path(), nullptr); CommandContext c{s};
        QByteArray old = s.files().read("moves/jab1.genoasm");
        QFile f(d.filePath("moves/jab1.genoasm")); QVERIFY(f.open(QIODevice::WriteOnly)); f.write("HAND\n"); f.close();
        bool threw = false;
        try { s.commit(c, "edit", {}, "t", {{"moves/jab1.genoasm", old, "x\n"}}); } catch (const CommandError &e) { threw = e.message.contains("changed externally"); }
        QVERIFY(threw);
        QCOMPARE(s.files().read("moves/jab1.genoasm"), QByteArray("HAND\n"));
    }
    void agentProposalsAreNotApplied() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); Session s(d.path(), nullptr);
        s.agentProposals = true; CommandContext c{s, "agent"};
        QByteArray old = s.files().read("moves/jab1.genoasm");
        QJsonObject r = s.commit(c, "edit", {}, "t", {{"moves/jab1.genoasm", old, "x\n"}});
        QVERIFY(r["proposed"].toBool());
        QCOMPARE(s.files().read("moves/jab1.genoasm"), old);
    }
};
QTEST_MAIN(RegistryTest)
#include "command_registry_test.moc"
```

- [ ] **Step 2: Run to verify failure** — build `workbench_command_registry`; Expected compile error.

- [ ] **Step 3: Implement `validate`**

```cpp
QString CommandRegistry::validate(const QJsonObject &schema, const QJsonObject &args) {
    for (const QJsonValue &r : schema["required"].toArray())
        if (!args.contains(r.toString())) return "missing required: " + r.toString();
    const QJsonObject props = schema["properties"].toObject();
    for (auto it = args.begin(); it != args.end(); ++it) {
        if (!props.contains(it.key())) continue;           // unknown keys are tolerated
        const QJsonObject p = props[it.key()].toObject();
        const QString type = p["type"].toString();
        const QJsonValue v = it.value();
        bool ok = type.isEmpty() || (type == "string" && v.isString()) || (type == "boolean" && v.isBool()) ||
                  (type == "number" && v.isDouble()) || (type == "integer" && v.isDouble() && v.toDouble() == std::floor(v.toDouble())) ||
                  (type == "object" && v.isObject()) || (type == "array" && v.isArray());
        if (!ok) return it.key() + ": expected " + type;
        if (p.contains("enum")) {
            bool found = false;
            for (const QJsonValue &e : p["enum"].toArray()) found |= (e == v);
            if (!found) return it.key() + ": not one of the allowed values";
        }
    }
    return QString();
}
```

`call`: look up; unknown -> `{"ok":false,"error":"unknown command: <name>"}`; validate -> error; run in try/catch(`CommandError`, `std::exception`, `...`) -> `{"ok":false,"error":...}`; success `{"ok":true,"result":...}`.

`Session`: constructor builds `FileStore(projectDir)`, loads `History::load(historyPath())`. `commit` as specified; `onApplied` hook (`std::function<void()>`) invoked after writes.

- [ ] **Step 4: Run tests** — `ctest --test-dir _build/wb-qt -R workbench_command_registry --output-on-failure`. Expected 7 slots pass.

- [ ] **Step 5: Commit** — `git commit -m "workbench: command registry and session commit path"` (with the co-author trailer as in Task 1).

---

### Task 6: Project config and GenoData  (Workspace repo)

**Files:**
- Create: `workbench/project.h/.cpp`, `workbench/geno_data.h/.cpp`, `workbench/tests/geno_data_test.cpp`
- Modify: `workbench/session.h/.cpp` (add `GenoData &data()`, wire `onApplied` -> `data().reload()`), `workbench/CMakeLists.txt`

**Interfaces:**
- Consumes: `FileStore`, `GenoAsm`, `HitboxEdit`, `wb::jsonFind/jsonReplace/jsonInsertKey/jsonScalar`.
- Produces:

```cpp
struct ProjectConfig {
  QString id, gameplay, movesDir, fidelity, plan, modId;
  QStringList rebuild, importClip;          // argv templates, {project} {package} substituted by the caller
  static ProjectConfig load(FileStore &fs, QString *err);   // reads workbench.json
};
struct RowInfo { QString name; int moveIndex; QVector<int> motions; QString script, tag, clip; int cropStart = 0; int iasa = 0; bool aerial = false; };
struct ClipInfo { QString name; int frames = 0; };
struct Joint { int index; QString name; int parent; };
class GenoData {
public:
  GenoData(FileStore &fs);
  QString reload();                                          // "" or error text
  const ProjectConfig &project() const;
  QVector<RowInfo> rows() const;
  QVector<HitboxRef> hitboxes(const QString &row) const;     // empty if the row has no script
  QVector<ClipInfo> clips() const;                           // plan.json bank.clips
  QVector<Joint> joints() const;                             // plan.json joints
  int jointForRole(const QString &role) const;               // "FOOT_L" -> index via the role map; -1 unknown
  QVector<FileChange> editHitbox(const QString &row, int ordinal, const HitboxEdit &e, QString *err) const;
  QVector<FileChange> assignClip(const QString &row, const QString &clip, std::optional<int> cropStart, QString *err) const;
  QString rowByMotion(int motion) const;
};
```

Role names: `@FOOT_L@` -> plan role key `foot.L`: map via the table `HAND_R:hand.R, HAND_L:hand.L, FOOT_R:foot.R, FOOT_L:foot.L, CHEST:chest, ARM_R:lower_arm.R, ARM_L:lower_arm.L, LEG_R:lower_leg.R, LEG_L:lower_leg.L, HIPS:hips, FLOOR:translation, UPLEG_R:upper_leg.R, UPLEG_L:upper_leg.L, UPARM_R:upper_arm.R, UPARM_L:upper_arm.L, HEAD:head, NECK:neck, SPINE:spine, TOE_R:toe.R, TOE_L:toe.L` (copied from `ports/goku-xv2/tools/build.py` `ROLE`; synthetic fixtures use HAND_R/FOOT_L only). `aerial` = `tag == "aerial"` or script name starts with a/b/d/f/u + "air" is NOT used; tag only.

`assignClip`: patches `moves[i].pick.clip` (and `pick.crop_start` if given) in `gameplay.json` via `jsonReplace`, and for every fidelity row whose `motion` is in the move's `motions`, replaces its `clip` with the new clip and appends to `deviation` the text `workbench: clip reassigned`. Errors: unknown row, unknown clip (not in plan bank), `err` set and empty result.

- [ ] **Step 1: Write the failing tests**

```cpp
#include "../testfixture.h"
#include "geno_data.h"
#include "session.h"
#include <QTemporaryDir>
#include <QtTest>
using namespace wb;

class GenoDataTest : public QObject {
    Q_OBJECT
    QTemporaryDir d;
    void init_fixture() {}
private slots:
    void listsRows() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); Session s(d.path(), nullptr);
        QVERIFY(s.data().reload().isEmpty());
        auto rows = s.data().rows();
        QCOMPARE(rows.size(), 2);
        QCOMPARE(rows[1].name, QString("dair")); QVERIFY(rows[1].aerial);
        QCOMPARE(rows[0].clip, QString("SYN_ATC_002")); QCOMPARE(rows[0].motions, QVector<int>{44});
    }
    void hitboxesForRow() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); Session s(d.path(), nullptr); s.data().reload();
        QCOMPARE(s.data().hitboxes("dair").size(), 2);
        QCOMPARE(s.data().hitboxes("nope").size(), 0);
    }
    void rolesAndClips() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); Session s(d.path(), nullptr); s.data().reload();
        QCOMPARE(s.data().jointForRole("FOOT_L"), 3);
        QCOMPARE(s.data().jointForRole("HEAD"), -1);
        QCOMPARE(s.data().clips().size(), 3);
    }
    void editHitboxProducesOneFileChange() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); Session s(d.path(), nullptr); s.data().reload();
        QString err; HitboxEdit e; e.joint = "HAND_R";
        auto ch = s.data().editHitbox("dair", 0, e, &err);
        QVERIFY2(ch.size() == 1, qPrintable(err));
        QCOMPARE(ch[0].path, QString("moves/dair.genoasm"));
        QVERIFY(ch[0].after.contains("@HAND_R@"));
    }
    void assignClipPatchesGameplayAndFidelityKeepingOtherBytes() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); Session s(d.path(), nullptr); s.data().reload();
        QString err;
        auto ch = s.data().assignClip("dair", "SYN_ATC_009", 4, &err);
        QVERIFY2(ch.size() == 2, qPrintable(err));
        QString g = QString::fromUtf8(ch[0].after);
        QString expect = wbtest::kGameplay;
        expect.replace("\"SYN_ATC_007\", \"crop_start\": 2", "\"SYN_ATC_009\", \"crop_start\": 4");
        QCOMPARE(g, expect);
    }
    void assignClipRejectsUnknownClipAndRow() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); Session s(d.path(), nullptr); s.data().reload();
        QString err;
        QVERIFY(s.data().assignClip("dair", "NOPE", {}, &err).isEmpty()); QVERIFY(err.contains("unknown clip"));
        QVERIFY(s.data().assignClip("zzz", "SYN_ATC_009", {}, &err).isEmpty()); QVERIFY(err.contains("unknown row"));
    }
    void missingProjectFileReportsError() {
        QTemporaryDir d; Session s(d.path(), nullptr);
        QVERIFY(s.data().reload().contains("workbench.json"));
    }
    void malformedGameplayReportsErrorNotCrash() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); wbtest::put(d.path(), "gameplay.json", "{ not json");
        Session s(d.path(), nullptr);
        QVERIFY(!s.data().reload().isEmpty());
        QCOMPARE(s.data().rows().size(), 0);
    }
};
QTEST_MAIN(GenoDataTest)
#include "geno_data_test.moc"
```

(Remove the unused `QTemporaryDir d;` member and `init_fixture` when writing the file; they are noise.)

- [ ] **Step 2: Run to verify failure** — build `workbench_geno_data`; Expected compile error.

- [ ] **Step 3: Implement**

`ProjectConfig::load`: read `workbench.json` via `fs.read`; parse with `QJsonDocument`; require `schema == "workbench/1"` else `err = "workbench.json: unsupported schema"`; missing file -> `err = "workbench.json not found in <root>"`. Strings from keys `id, gameplay, moves_dir, fidelity, plan, mod_id`; arrays `rebuild`, `import_clip` -> `QStringList`.

`GenoData::reload`: calls `ProjectConfig::load`, reads gameplay (parse for rows; keep the raw text `gameplayText_` for patching), plan (optional; missing plan => empty joints/clips, no error), fidelity (optional). Rows: for each `moves[i]`: `name, motions[], tag, script, iasa, pick.clip, pick.crop_start`. Parse errors return `"gameplay.json: <QJsonParseError::errorString> at offset N"` and leave rows empty. Hitboxes: `GenoAsm::parse(fs.read(row.script)).hitboxes()`.

`editHitbox`: `GenoAsm::apply`, then `FileChange{row.script, oldBytes, newText.toUtf8()}`.

`assignClip`: gameplay patch uses `jsonReplace(text, {"moves","#<i>","pick","clip"}, jsonScalar(clip))`; crop with `{"…","crop_start"}`; fidelity patch: for each fidelity row index `j` with `motion` in motions: `jsonReplace(fid, {"rows","#j","clip"}, ...)`. Row index `j` found by parsing fidelity with `QJsonDocument` (array order is preserved in arrays) and patching by text path.

`Session::data()` lazily constructs `GenoData`; `onApplied = [this]{ data().reload(); }`.

- [ ] **Step 4: Run tests** — `ctest --test-dir _build/wb-qt -R "workbench_(geno_data|command_registry)" --output-on-failure`. Expected: both pass.

- [ ] **Step 5: Commit** — `git commit -m "workbench: project config and GenoData over source files"`.

---

### Task 7: EngineLink and ConsoleClient  (Workspace repo)

Game console protocol (`gw_script.c` ~9588): connect to `127.0.0.1:MELEE_CONSOLE_PORT`; the game sends one banner line `GD's Melee console (scripting API 1)`; each command is one `\n`-terminated line (max 4095 bytes); the reply is output lines then `>>> ok` or `>>> error`. One command is served per rendered frame per client. `= expr` evaluates and prints an expression (see `tools/port/gd_prompt.py`, `:raw = gd.player(1).x`).

**Files:**
- Create: `workbench/engine_link.h/.cpp`, `workbench/tests/engine_link_test.cpp`
- Modify: `workbench/testfixture.h` (add `FakeConsole` and `FakeEngine`), `workbench/CMakeLists.txt`

**Interfaces:**
- Produces:

```cpp
namespace wb {
struct Vec3 { double x = 0, y = 0, z = 0; };
struct BoneLive { int joint = 0; int parent = -1; Vec3 pos; };
struct HitLive { int slot = 0; int joint = 0; Vec3 offset; double radius = 0; Vec3 world; bool active = false; };
struct HurtLive { int joint = 0; Vec3 a, b; double radius = 0; };
struct FrameInfo {
  QString row; int motion = 0; int frame = 0;
  QVector<BoneLive> bones; QVector<HitLive> hitboxes; QVector<HurtLive> hurtboxes;
  Vec3 ecbBottom, ecbTop; double floorY = 0, lowestY = 0;
  static FrameInfo fromJson(const QJsonObject &o);
  QJsonObject toJson() const;
};
class EngineBackend {                       // test seam
public:
  virtual ~EngineBackend() = default;
  // fn is a wb.* function name without the prefix ("frame", "step", ...). Returns the JSON payload; err set on failure.
  virtual QJsonObject call(const QString &fn, const QJsonObject &args, QString *err) = 0;
  virtual QString status() = 0;             // "stopped" | "starting" | "ready" | "error: ..."
  virtual bool restart(QString *err) = 0;
};
struct ConsoleReply { bool ok = false; QString text; };
class ConsoleClient {
public:
  bool connectTo(quint16 port, int timeoutMs, QString *err);
  ConsoleReply call(const QString &line, int timeoutMs);   // timeout => ok=false, text="timeout"
  bool connected() const; void close(); QString banner() const;
};
QString luaLiteral(const QJsonValue &v);     // JSON -> Lua table/string/number literal
class EngineLink : public EngineBackend {
public:
  struct Launch { QString exe, workDir, modsDir, modId, wbDir; QStringList extraArgs; QProcessEnvironment env; int port = 0; };
  explicit EngineLink(Launch l);
  bool start(QString *err);                  // spawn melee-pc, connect, wait for the workbench banner
  void stop();                               // kills ONLY the process this object spawned
  QJsonObject call(const QString &fn, const QJsonObject &args, QString *err) override;
  QString status() override; bool restart(QString *err) override;
  bool attach(quint16 port, QString *err);   // connect to an already-running game (tests, manual runs)
};
}
```

`call()` builds `=wb.<fn>(<luaLiteral(args)>)`, sends it, and parses the reply: take the last non-empty line before `>>>`; if it starts with `@` read that file (relative to `wbDir` if not absolute; must resolve inside `wbDir`) and parse as JSON; else if it starts with `{` parse inline JSON; on `>>> error` return `err = <reply text>`. A dead socket (`QAbstractSocket::state() != Connected` or remote close) sets `status()=="error: engine connection lost"` and returns an error rather than hanging. Default call timeout 8000 ms (configurable `setTimeoutMs`).

`luaLiteral`: objects -> `{key=value,...}` with keys `["key"]=` quoted; arrays -> `{v1,v2}`; strings -> `"..."` with `\\`, `\"`, `\n`, `\r`, and control chars as `\ddd`; numbers via `QString::number(v, 'g', 17)`; booleans/null (`nil`).

`FakeConsole` (test): a `QTcpServer` on `127.0.0.1:0` that writes the banner on connect and replies to each received line using a user-supplied `std::function<QString(const QString&)>` returning `"text\n>>> ok\n"` (or error); it can be told to drop the connection or to never reply.

- [ ] **Step 1: Write the failing tests**

```cpp
#include "../testfixture.h"
#include "engine_link.h"
#include <QTemporaryDir>
#include <QtTest>
using namespace wb;

class EngineLinkTest : public QObject {
    Q_OBJECT
private slots:
    void luaLiteralQuotesAndNests() {
        QJsonObject o{{"name", "a\"b\n"}, {"n", 2.5}, {"ok", true}, {"list", QJsonArray{1, 2}}};
        QString s = luaLiteral(o);
        QVERIFY(s.contains("[\"name\"]=\"a\\\"b\\n\""));
        QVERIFY(s.contains("[\"n\"]=2.5"));
        QVERIFY(s.contains("[\"ok\"]=true"));
        QVERIFY(s.contains("[\"list\"]={1,2}"));
    }
    void consoleCallParsesOkAndError() {
        wbtest::FakeConsole fc([](const QString &l) { return l.contains("bad") ? QString("nope\n>>> error\n") : QString("hello\n>>> ok\n"); });
        ConsoleClient c; QString err;
        QVERIFY2(c.connectTo(fc.port(), 2000, &err), qPrintable(err));
        QVERIFY(c.banner().contains("GD's Melee console"));
        auto r = c.call("= 1", 2000); QVERIFY(r.ok); QCOMPARE(r.text.trimmed(), QString("hello"));
        r = c.call("bad", 2000); QVERIFY(!r.ok); QCOMPARE(r.text.trimmed(), QString("nope"));
    }
    void timeoutDoesNotHang() {
        wbtest::FakeConsole fc(nullptr);   // never replies
        ConsoleClient c; QString err; QVERIFY(c.connectTo(fc.port(), 2000, &err));
        QElapsedTimer t; t.start();
        auto r = c.call("= 1", 300);
        QVERIFY(!r.ok); QCOMPARE(r.text, QString("timeout")); QVERIFY(t.elapsed() < 2000);
    }
    void droppedSocketIsAnErrorNotAHang() {
        auto fc = std::make_unique<wbtest::FakeConsole>([](const QString &) { return QString("x\n>>> ok\n"); });
        EngineLink link({}); QString err;
        QVERIFY2(link.attach(fc->port(), &err), qPrintable(err));
        fc->dropClients();
        QJsonObject r = link.call("frame", {}, &err);
        QVERIFY(r.isEmpty()); QVERIFY(!err.isEmpty());
        QVERIFY(link.status().startsWith("error"));
    }
    void payloadFileIsReadFromWbDir() {
        QTemporaryDir wbd;
        QFile f(wbd.filePath("frame.json")); QVERIFY(f.open(QIODevice::WriteOnly)); f.write(R"({"frame":7,"row":"dair"})"); f.close();
        wbtest::FakeConsole fc([&](const QString &) { return "@" + wbd.filePath("frame.json") + "\n>>> ok\n"; });
        EngineLink::Launch l; l.wbDir = wbd.path();
        EngineLink link(l); QString err; QVERIFY(link.attach(fc.port(), &err));
        QJsonObject r = link.call("frame", {{"f", 7}}, &err);
        QCOMPARE(r["frame"].toInt(), 7);
    }
    void payloadPathCannotEscapeWbDir() {
        QTemporaryDir wbd, other;
        QFile f(other.filePath("x.json")); QVERIFY(f.open(QIODevice::WriteOnly)); f.write("{}"); f.close();
        wbtest::FakeConsole fc([&](const QString &) { return "@" + other.filePath("x.json") + "\n>>> ok\n"; });
        EngineLink::Launch l; l.wbDir = wbd.path();
        EngineLink link(l); QString err; QVERIFY(link.attach(fc.port(), &err));
        link.call("frame", {}, &err);
        QVERIFY(err.contains("outside"));
    }
    void frameInfoRoundTrip() {
        FrameInfo fi; fi.row = "dair"; fi.frame = 6; fi.motion = 70;
        fi.bones.append({3, 1, {1, 2, 3}}); fi.hitboxes.append({0, 3, {0, 0, 0}, 2.8, {1, 2, 3}, true});
        FrameInfo b = FrameInfo::fromJson(fi.toJson());
        QCOMPARE(b.hitboxes.size(), 1); QCOMPARE(b.hitboxes[0].world.y, 2.0); QVERIFY(b.hitboxes[0].active);
    }
};
QTEST_MAIN(EngineLinkTest)
#include "engine_link_test.moc"
```

Add to `testfixture.h`:

```cpp
#include <QTcpServer>
#include <QTcpSocket>
#include <functional>
namespace wbtest {
class FakeConsole : public QObject {
public:
    explicit FakeConsole(std::function<QString(const QString &)> reply) : reply_(std::move(reply)) {
        server_.listen(QHostAddress::LocalHost, 0);
        QObject::connect(&server_, &QTcpServer::newConnection, [this] {
            QTcpSocket *s = server_.nextPendingConnection();
            clients_.append(s);
            s->write("GD's Melee console (scripting API 1)\n");
            QObject::connect(s, &QTcpSocket::readyRead, [this, s] {
                buf_ += s->readAll();
                int nl;
                while ((nl = buf_.indexOf('\n')) >= 0) {
                    QString line = QString::fromUtf8(buf_.left(nl)); buf_.remove(0, nl + 1);
                    if (reply_) s->write(reply_(line).toUtf8());
                }
            });
        });
    }
    quint16 port() const { return server_.serverPort(); }
    void dropClients() { for (auto *c : clients_) c->disconnectFromHost(); }
private:
    QTcpServer server_; std::function<QString(const QString &)> reply_; QList<QTcpSocket *> clients_; QByteArray buf_;
};
}
```

`FakeConsole` lives in the test process and the client calls block with `waitForReadyRead`; the server must be serviced: `ConsoleClient::call` pumps with `QCoreApplication::processEvents(QEventLoop::AllEvents, 10)` between `waitForReadyRead(10)` calls so an in-process fake server runs. This is also fine for the real game (no cost).

`FakeEngine` (implements `EngineBackend`, canned by function name, records calls) also goes in `testfixture.h`:

```cpp
class FakeEngine : public wb::EngineBackend {
public:
    QMap<QString, QJsonObject> canned; QVector<QPair<QString, QJsonObject>> calls; QString state = "ready"; QString failWith;
    QJsonObject call(const QString &fn, const QJsonObject &a, QString *err) override {
        calls.append({fn, a});
        if (!failWith.isEmpty()) { if (err) *err = failWith; return {}; }
        return canned.value(fn);
    }
    QString status() override { return state; }
    bool restart(QString *) override { calls.append({"restart", {}}); return true; }
};
```

- [ ] **Step 2: Run to verify failure** — build `workbench_engine_link`; Expected compile error.

- [ ] **Step 3: Implement** `ConsoleClient` over `QTcpSocket` (blocking-with-pump). `EngineLink::start`: choose a free port (listen on `QTcpServer` port 0, read, close), set env `MELEE_CONSOLE_PORT`, `MELEE_SCENE=mode=workbench;p1=geno:<modId>/hu;stage=fd`, `MELEE_MODS_DIR`, `MELEE_WB_DIR`, `MELEE_WINDOW_X=100 MELEE_WINDOW_Y=80` (on-screen; see G-b), `MELEE_NETPLAY` removed from the environment; start the `QProcess`; retry `connectTo` every 250 ms up to 60 s; `stop()` calls `QProcess::terminate()` then `kill()` after 3 s on the object's own `QProcess` only. Path check for payload files: `QFileInfo(path).canonicalFilePath().startsWith(QFileInfo(wbDir).canonicalFilePath() + "/")` else `err = "payload outside wb dir: <path>"`.

- [ ] **Step 4: Run tests** — `ctest --test-dir _build/wb-qt -R workbench_engine_link --output-on-failure`. Expected: 7 slots pass.

- [ ] **Step 5: Commit** — `git commit -m "workbench: console client, EngineLink, FrameInfo and fake console for tests"`.

---

### Task 8: Checks and suggestBone  (Workspace repo)

**Files:**
- Create: `workbench/checks.h/.cpp`, `workbench/tests/checks_test.cpp`
- Modify: `workbench/CMakeLists.txt`

**Interfaces:**
- Produces:

```cpp
namespace wb {
struct BoneSample { QString role; double displacement = 0; double speed = 0; };    // at the hitbox's active frame; displacement from the torso
struct HitboxSample { int ordinal = 0; QString role; int startFrame = 0; double lowestY = 0; };
struct RowAnalysis {
  QString row, tag, clip; bool aerial = false, groundedClip = false, hasSwingMotion = false;
  double floorY = 0, rowLowestY = 0;
  QVector<HitboxSample> hitboxes; QVector<BoneSample> bones;
};
struct Problem { QString kind, row, message; int ordinal = -1; };   // kind: wrong_limb|below_floor|duplicate_clip|grounded_clip_on_aerial|swing_without_hitbox
QString suggestBone(const QVector<BoneSample> &bones);   // role with max displacement*(1+speed) among limb roles; "" if none
QVector<Problem> runChecks(const QVector<RowAnalysis> &rows);
inline bool isLimbRole(const QString &role);   // HAND_L/R, FOOT_L/R, ARM_L/R, LEG_L/R, TOE_L/R, UPARM_L/R, UPLEG_L/R, HEAD
}
```

Rules: `wrong_limb`: for each hitbox, `suggestBone(row.bones)` non-empty and differs from `hitbox.role`, AND the suggested bone's score exceeds the hitbox bone's score by a factor >= 1.5. `below_floor`: `rowLowestY < floorY - 0.5` (units = game units; matches `ground_audit` BELOW_EPS idea) for non-aerial rows. `duplicate_clip`: two rows (different `row`) share a non-empty `clip` -> one problem per extra row. `grounded_clip_on_aerial`: `aerial && groundedClip`. `swing_without_hitbox`: `hasSwingMotion && hitboxes.isEmpty()`.

- [ ] **Step 1: Write the failing tests**

```cpp
#include "checks.h"
#include <QtTest>
using namespace wb;

static RowAnalysis row(const QString &name) { RowAnalysis r; r.row = name; r.tag = "jab"; return r; }

class ChecksTest : public QObject {
    Q_OBJECT
private slots:
    void suggestPicksFastestFarthestLimb() {
        QVector<BoneSample> b{{"CHEST", 9, 9}, {"HAND_R", 5, 1}, {"FOOT_L", 6, 3}, {"HAND_L", 1, 0}};
        QCOMPARE(suggestBone(b), QString("FOOT_L"));    // non-limbs ignored
    }
    void suggestEmptyWhenNoLimbs() { QCOMPARE(suggestBone({{"CHEST", 9, 9}}), QString()); QCOMPARE(suggestBone({}), QString()); }
    void wrongLimbFlagged() {
        RowAnalysis r = row("dair"); r.hitboxes = {{0, "HAND_R", 6, 0}}; r.bones = {{"HAND_R", 1, 0}, {"FOOT_L", 6, 4}};
        auto p = runChecks({r});
        QCOMPARE(p.size(), 1); QCOMPARE(p[0].kind, QString("wrong_limb")); QCOMPARE(p[0].ordinal, 0); QVERIFY(p[0].message.contains("FOOT_L"));
    }
    void closeCallIsNotWrongLimb() {
        RowAnalysis r = row("jab"); r.hitboxes = {{0, "HAND_R", 3, 0}}; r.bones = {{"HAND_R", 5, 1}, {"HAND_L", 5.2, 1}};
        QVERIFY(runChecks({r}).isEmpty());
    }
    void belowFloorOnGroundOnly() {
        RowAnalysis g = row("dtilt"); g.floorY = 0; g.rowLowestY = -1.2;
        RowAnalysis a = row("dair"); a.aerial = true; a.floorY = 0; a.rowLowestY = -3;
        auto p = runChecks({g, a});
        QCOMPARE(p.size(), 1); QCOMPARE(p[0].kind, QString("below_floor")); QCOMPARE(p[0].row, QString("dtilt"));
    }
    void duplicateClip() {
        RowAnalysis a = row("a"), b = row("b"), c = row("c"); a.clip = b.clip = "X"; c.clip = "Y";
        auto p = runChecks({a, b, c});
        QCOMPARE(p.size(), 1); QCOMPARE(p[0].kind, QString("duplicate_clip")); QCOMPARE(p[0].row, QString("b"));
    }
    void emptyClipsAreNotDuplicates() { RowAnalysis a = row("a"), b = row("b"); QVERIFY(runChecks({a, b}).isEmpty()); }
    void groundedClipOnAerial() {
        RowAnalysis a = row("uair"); a.aerial = true; a.groundedClip = true;
        QCOMPARE(runChecks({a})[0].kind, QString("grounded_clip_on_aerial"));
    }
    void swingWithoutHitbox() {
        RowAnalysis a = row("ftilt"); a.hasSwingMotion = true;
        QCOMPARE(runChecks({a})[0].kind, QString("swing_without_hitbox"));
    }
    void noRowsNoProblems() { QVERIFY(runChecks({}).isEmpty()); }
};
QTEST_MAIN(ChecksTest)
#include "checks_test.moc"
```

- [ ] **Step 2: Run to verify failure.** Expected compile error.

- [ ] **Step 3: Implement** per the rules. `score(b) = b.displacement * (1.0 + b.speed)`. `wrong_limb` message: `"hitbox #<n> is on <role> but <suggest> moves most at frame <start>"`.

- [ ] **Step 4: Run tests** — `ctest --test-dir _build/wb-qt -R workbench_checks --output-on-failure`. Expected 9 slots pass.

- [ ] **Step 5: Commit** — `git commit -m "workbench: checks and limb suggestion"`.

---

### Task 9: Save, undo, proposals, rebuild, reload commands  (Workspace repo)

**Files:**
- Create: `workbench/commands_save.cpp`, `workbench/commands.h`, `workbench/tests/commands_save_test.cpp`
- Modify: `workbench/session.cpp` (call `registerAllCommands`), `workbench/CMakeLists.txt`

**Interfaces:**
- Consumes: `Session::commit`, `History`, `FileStore`, `EngineBackend`, `ProjectConfig`.
- Produces: `workbench/commands.h`:

```cpp
namespace wb {
void registerViewCommands(Session &);    // Task 10
void registerRowCommands(Session &);     // Task 10
void registerHitboxCommands(Session &);  // Task 10
void registerClipCommands(Session &);    // Task 10
void registerGroundCommands(Session &);  // Task 14
void registerSaveCommands(Session &);    // this task
void registerAllCommands(Session &);     // calls each; defined in session.cpp
QJsonObject changeToJson(const QVector<FileChange> &);   // {path, bytes_before, bytes_after}
}
```

Commands (all in `registerSaveCommands`):

| name | args | behaviour |
|---|---|---|
| `save` | `{}` | In this design edits are written on `commit`; `save` snapshots nothing new but verifies: returns `{"external":[...paths changed outside the tool...]}` and `{"dirty":false}`. If `external` is non-empty, `ok` is still true but `warning` is set. (Explicit so agents have the spec's `save` verb; the real write is the edit command's commit.) |
| `rebuild` | `{}` | Runs `ProjectConfig::rebuild` argv (substituting `{project}`, `{package}` = project-relative `package` dir from config id) with `QProcess` in the project's workspace root (parent of `ports/`); timeout 30 min; returns `{"exit":N,"output":"<last 4000 chars>"}`; non-zero exit => `ok:false`. |
| `reload` | `{}` | `engine->call("reload", {})` then `data().reload()`. |
| `undo`, `redo` | `{}` | `History::undo/redo`, then `data().reload()`; error on `changed externally`. |
| `history` | `{limit?:integer}` | Entries without bytes: id, author, command, summary, state, time. |
| `propose` | `{command:string, args:object}` | Runs the named mutating command with `ctx.propose=true`. |
| `accept`, `reject` | `{id:integer}` | `History::accept/reject`; accept then `data().reload()`. |

- [ ] **Step 1: Write the failing tests**

```cpp
#include "../testfixture.h"
#include "commands.h"
#include "session.h"
#include <QTemporaryDir>
#include <QtTest>
using namespace wb;

static QJsonObject callCmd(Session &s, const QString &n, QJsonObject a = {}, const QString &author = "human") {
    CommandContext c{s, author};
    return s.registry().call(n, a, c);
}

class SaveCmdTest : public QObject {
    Q_OBJECT
private slots:
    void undoRedoViaCommands() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); Session s(d.path(), nullptr); s.data().reload();
        registerSaveCommands(s);
        QByteArray old = s.files().read("moves/jab1.genoasm");
        CommandContext c{s};
        s.commit(c, "x", {}, "t", {{"moves/jab1.genoasm", old, "changed\n"}});
        QVERIFY(callCmd(s, "undo")["ok"].toBool());
        QCOMPARE(s.files().read("moves/jab1.genoasm"), old);
        QVERIFY(callCmd(s, "redo")["ok"].toBool());
        QCOMPARE(s.files().read("moves/jab1.genoasm"), QByteArray("changed\n"));
    }
    void undoReportsExternalChange() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); Session s(d.path(), nullptr); s.data().reload();
        registerSaveCommands(s);
        QByteArray old = s.files().read("moves/jab1.genoasm");
        CommandContext c{s}; s.commit(c, "x", {}, "t", {{"moves/jab1.genoasm", old, "changed\n"}});
        QFile f(d.filePath("moves/jab1.genoasm")); f.open(QIODevice::WriteOnly); f.write("HAND\n"); f.close();
        QJsonObject r = callCmd(s, "undo");
        QVERIFY(!r["ok"].toBool()); QVERIFY(r["error"].toString().contains("changed externally"));
    }
    void saveReportsExternalChanges() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); Session s(d.path(), nullptr); s.data().reload();
        registerSaveCommands(s);
        s.files().read("gameplay.json");
        QFile f(d.filePath("gameplay.json")); f.open(QIODevice::WriteOnly); f.write("{}"); f.close();
        QJsonObject r = callCmd(s, "save")["result"].toObject();
        QCOMPARE(r["external"].toArray().size(), 1);
    }
    void rebuildRunsConfiguredCommand() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); Session s(d.path(), nullptr); s.data().reload();
        registerSaveCommands(s);
        QJsonObject r = callCmd(s, "rebuild");
        QVERIFY(r["ok"].toBool()); QVERIFY(r["result"].toObject()["output"].toString().contains("rebuilt"));
    }
    void rebuildFailureIsError() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        wbtest::put(d.path(), "workbench.json", QString(wbtest::kProject).replace("print('rebuilt')", "raise SystemExit(3)").toUtf8());
        Session s(d.path(), nullptr); s.data().reload(); registerSaveCommands(s);
        QJsonObject r = callCmd(s, "rebuild");
        QVERIFY(!r["ok"].toBool()); QVERIFY(r["error"].toString().contains("exit 3"));
    }
    void proposeAcceptReject() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); Session s(d.path(), nullptr); s.data().reload();
        registerSaveCommands(s);
        CommandSpec t; t.name = "touch"; t.mutating = true; t.inputSchema = QJsonObject{{"type", "object"}};
        t.run = [](const QJsonObject &, CommandContext &ctx) {
            QByteArray old = ctx.session.files().read("moves/jab1.genoasm");
            return ctx.session.commit(ctx, "touch", {}, "touch", {{"moves/jab1.genoasm", old, "p\n"}});
        };
        s.registry().add(t);
        QByteArray old = s.files().read("moves/jab1.genoasm");
        QJsonObject r = callCmd(s, "propose", {{"command", "touch"}, {"args", QJsonObject()}}, "agent")["result"].toObject();
        QVERIFY(r["proposed"].toBool());
        QCOMPARE(s.files().read("moves/jab1.genoasm"), old);
        int id = r["entry"].toInt();
        QVERIFY(callCmd(s, "accept", {{"id", id}})["ok"].toBool());
        QCOMPARE(s.files().read("moves/jab1.genoasm"), QByteArray("p\n"));
    }
    void historyListsWithoutBytes() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); Session s(d.path(), nullptr); s.data().reload();
        registerSaveCommands(s);
        CommandContext c{s}; QByteArray old = s.files().read("moves/jab1.genoasm");
        s.commit(c, "x", {}, "hello", {{"moves/jab1.genoasm", old, "c\n"}});
        QJsonArray h = callCmd(s, "history")["result"].toObject()["entries"].toArray();
        QCOMPARE(h.size(), 1); QCOMPARE(h[0].toObject()["summary"].toString(), QString("hello")); QVERIFY(!h[0].toObject().contains("changes"));
    }
};
QTEST_MAIN(SaveCmdTest)
#include "commands_save_test.moc"
```

Note: `Session` constructor must NOT call `registerAllCommands` automatically in this task's tests (they register selectively); `registerAllCommands` is invoked by app code (`workbench_main`, Task 11). Duplicate registration is a `qFatal`, so tests call only what they need.

- [ ] **Step 2: Run to verify failure.** Expected compile error (`commands.h`).

- [ ] **Step 3: Implement** `commands_save.cpp`. `rebuild` argv substitution: replace `{project}` with `files().root()` and `{package}` with `QDir(root).filePath("package")`; `QProcess::setProgram(argv[0])`, working directory = `files().root()`; `waitForFinished(30*60*1000)`; collect `readAllStandardOutput + readAllStandardError`, keep last 4000 chars; non-zero exit -> `throw CommandError{"rebuild failed: exit N: <tail 300 chars>"}`; process that fails to start -> `CommandError{"rebuild failed to start: <errorString>"}`. `propose`: look up spec, require `spec.mutating`, set `ctx.propose = true` on a copy of the context, call `spec.run`, return its result.

- [ ] **Step 4: Run tests** — `ctest --test-dir _build/wb-qt -R workbench_commands_save --output-on-failure`. Expected 7 slots pass (requires `python` on PATH; on a machine without it use `python3` by editing the fixture's argv).

- [ ] **Step 5: Commit** — `git commit -m "workbench: save/undo/redo/history/propose/accept/reject/rebuild/reload commands"`.

---

### Task 10: View, row, hitbox and clip commands  (Workspace repo)

**Files:**
- Create: `workbench/commands_view.cpp`, `workbench/commands_rows.cpp`, `workbench/commands_hitbox.cpp`, `workbench/commands_clips.cpp`, `workbench/analysis.h/.cpp`, `workbench/tests/commands_edit_test.cpp`
- Modify: `workbench/CMakeLists.txt`, `workbench/session.cpp` (`registerAllCommands`)

**Interfaces:**
- Consumes: `EngineBackend::call`, `FrameInfo`, `GenoData`, `suggestBone`, `runChecks`, `RowAnalysis`.
- Produces: these commands. `ENG` marks calls that need an engine (error `"engine not running"` if `engine()==nullptr`).

| command | args (required first) | result |
|---|---|---|
| `open_fighter` | `path:string` (project dir) | reopens the session on that dir (UI/CLI level; in-session: reloads `GenoData`, returns `{rows:N}`) |
| `engine_status` | `{}` | `{status}` |
| `engine_restart` | `{}` | ENG restart |
| `set_camera` | `preset?:enum[side,front,top,three_quarter], yaw?:number, pitch?:number, distance?:number, target_joint?:integer` | stores camera in `Session::camera` (JSON object) |
| `set_overlays` | `hitboxes?:boolean, hurtboxes?:boolean, bones?:boolean, ecb?:boolean, floor?:boolean` | stores in `Session::overlays` |
| `render_view` | `w?:integer, h?:integer` | ENG `render` with camera+overlays; `{path:"<png path>"}` |
| `list_rows` | `{}` | `{rows:[{name,motions,tag,clip,aerial,hitboxes}]}` |
| `load_row` | `row:string` | ENG `row` {motion: first motion}; stores `Session::currentRow` |
| `set_frame` | `frame:integer` | ENG `frame` {motion, frame}; result = `FrameInfo` JSON |
| `play` | `frames:integer, step?:integer` | ENG `step` repeatedly (chunks of `step`, default 1) returns last `FrameInfo` |
| `frame_info` | `{}` | ENG `frame_info` -> FrameInfo JSON |
| `list_hitboxes` | `row:string` | `{hitboxes:[HitboxRef as JSON]}` (from source) |
| `edit_hitbox` | `row, ordinal:integer, bone?, damage?, size?, x?, y?, z?, angle?, kbg?, fkb?, bkb?, start_frame?, end_frame?, propose?:boolean` | mutating; `GenoData::editHitbox` -> `commit`; a `bone` that is not a known role is rejected (`unknown bone`) when a plan is loaded |
| `suggest_hitbox_bone` | `row, ordinal:integer` | ENG: loads the row at the hitbox's `startFrame`, samples bones (`frame_info` at start-1 and start), computes `BoneSample{displacement,speed}` per role via `GenoData::jointForRole`, returns `{suggested, current, scores:[...]}` |
| `list_clips` | `{}` | `{clips:[{name,frames}]}` |
| `preview_clip` | `clip:string, frame?:integer` | ENG `clip` -> FrameInfo |
| `assign_clip` | `row, clip, crop_start?:integer, propose?` | mutating; `GenoData::assignClip` -> `commit` |
| `import_clip` | `source:string, target_name:string, row?:string` | runs `ProjectConfig::importClip` argv with `{source}` `{target}` substituted; expects stdout JSON `{"clip":"<name>","frames":<int>}`; non-zero exit or non-JSON stdout -> error. Contract (owner of the retarget tool: another lane): stdin none, cwd = project root, writes the clip into the project's bank source, prints one JSON line. On success it refreshes `data().reload()` and returns the JSON. |
| `run_checks` | `row?:string` | builds `RowAnalysis` per row (ENG sweeps hitbox start frames; static fields from `GenoData`), returns `{problems:[...]}`. Without an engine only static checks run (`duplicate_clip`, `grounded_clip_on_aerial`, `swing_without_hitbox`) and `engine:false` is reported. |

`analysis.h`: `RowAnalysis analyzeRow(Session &, const RowInfo &, QString *err)` (engine sweep) and `QVector<BoneSample> sampleBones(EngineBackend &, GenoData &, const RowInfo &, int frame, QString *err)`; displacement = distance from the `CHEST`-role joint at that frame; speed = distance moved between frame-1 and frame.

`groundedClip` = clip name present in the optional `ground_modes.json` list `grounded_clips` (Task 14), else false. `hasSwingMotion` = row tag in {`jab`,`tilt`,`smash`,`aerial`,`special`} (static).

- [ ] **Step 1: Write the failing tests** (uses `FakeEngine` canned responses; one test per command family)

```cpp
#include "../testfixture.h"
#include "commands.h"
#include "session.h"
#include <QTemporaryDir>
#include <QtTest>
using namespace wb;

struct Rig {
    QTemporaryDir d; wbtest::FakeEngine eng; Session s;
    Rig() : d(), s((wbtest::makeSynthFighter(d.path()), d.path()), &eng) {
        s.data().reload();
        registerViewCommands(s); registerRowCommands(s); registerHitboxCommands(s); registerClipCommands(s);
    }
    QJsonObject call(const QString &n, QJsonObject a = {}, const QString &who = "human") { CommandContext c{s, who}; return s.registry().call(n, a, c); }
};

static QJsonObject frameJson(int f, double footY) {
    return QJsonObject{{"row", "dair"}, {"frame", f}, {"motion", 70},
        {"bones", QJsonArray{QJsonObject{{"joint", 1}, {"parent", 0}, {"pos", QJsonObject{{"x", 0}, {"y", 5}, {"z", 0}}}},
                              QJsonObject{{"joint", 2}, {"parent", 1}, {"pos", QJsonObject{{"x", 1}, {"y", 5}, {"z", 0}}}},
                              QJsonObject{{"joint", 3}, {"parent", 1}, {"pos", QJsonObject{{"x", 0}, {"y", footY}, {"z", 0}}}}}},
        {"hitboxes", QJsonArray{}}};
}

class EditCmdTest : public QObject {
    Q_OBJECT
private slots:
    void listRowsAndHitboxes() {
        Rig r;
        QCOMPARE(r.call("list_rows")["result"].toObject()["rows"].toArray().size(), 2);
        QCOMPARE(r.call("list_hitboxes", {{"row", "dair"}})["result"].toObject()["hitboxes"].toArray().size(), 2);
    }
    void editHitboxWritesSourceAndReloads() {
        Rig r;
        QJsonObject res = r.call("edit_hitbox", {{"row", "dair"}, {"ordinal", 0}, {"bone", "HAND_R"}});
        QVERIFY(res["ok"].toBool());
        QVERIFY(r.s.files().read("moves/dair.genoasm").contains("@HAND_R@"));
        QCOMPARE(r.s.data().hitboxes("dair")[0].joint, QString("HAND_R"));
    }
    void editHitboxUnknownBoneRejected() {
        Rig r;
        QJsonObject res = r.call("edit_hitbox", {{"row", "dair"}, {"ordinal", 0}, {"bone", "TAIL"}});
        QVERIFY(!res["ok"].toBool()); QVERIFY(res["error"].toString().contains("unknown bone"));
    }
    void editHitboxAgentProposalDoesNotWrite() {
        Rig r; QByteArray old = r.s.files().read("moves/dair.genoasm");
        QJsonObject res = r.call("edit_hitbox", {{"row", "dair"}, {"ordinal", 0}, {"bone", "HAND_R"}, {"propose", true}}, "agent");
        QVERIFY(res["result"].toObject()["proposed"].toBool());
        QCOMPARE(r.s.files().read("moves/dair.genoasm"), old);
    }
    void frameCommandsHitEngine() {
        Rig r; r.eng.canned["frame"] = frameJson(6, 0);
        QVERIFY(r.call("load_row", {{"row", "dair"}})["ok"].toBool());
        QJsonObject res = r.call("set_frame", {{"frame", 6}});
        QCOMPARE(res["result"].toObject()["frame"].toInt(), 6);
        QCOMPARE(r.eng.calls.last().first, QString("frame"));
        QCOMPARE(r.eng.calls.last().second["motion"].toInt(), 70);
    }
    void engineCommandsErrorWithoutEngine() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); Session s(d.path(), nullptr); s.data().reload();
        registerViewCommands(s); registerRowCommands(s);
        CommandContext c{s};
        QJsonObject res = s.registry().call("render_view", {}, c);
        QVERIFY(!res["ok"].toBool()); QVERIFY(res["error"].toString().contains("engine not running"));
    }
    void engineErrorPropagates() {
        Rig r; r.eng.failWith = "engine connection lost";
        QJsonObject res = r.call("frame_info");
        QVERIFY(!res["ok"].toBool()); QVERIFY(res["error"].toString().contains("lost"));
    }
    void suggestBoneUsesEngineSamples() {
        Rig r;
        // the same canned reply is used for both samples; speed 0, foot is 5 below chest, hand is 1 away: suggests FOOT_L
        r.eng.canned["frame"] = frameJson(6, 0);
        QJsonObject res = r.call("suggest_hitbox_bone", {{"row", "dair"}, {"ordinal", 0}});
        QVERIFY2(res["ok"].toBool(), qPrintable(res["error"].toString()));
        QCOMPARE(res["result"].toObject()["suggested"].toString(), QString("FOOT_L"));
    }
    void assignClipAndListClips() {
        Rig r;
        QCOMPARE(r.call("list_clips")["result"].toObject()["clips"].toArray().size(), 3);
        QVERIFY(r.call("assign_clip", {{"row", "dair"}, {"clip", "SYN_ATC_009"}})["ok"].toBool());
        QVERIFY(r.s.files().read("gameplay.json").contains("SYN_ATC_009"));
        QCOMPARE(r.s.data().rows()[1].clip, QString("SYN_ATC_009"));
    }
    void importClipRunsConfiguredTool() {
        Rig r;
        QJsonObject res = r.call("import_clip", {{"source", "x.anim"}, {"target_name", "SYN_IMPORTED"}});
        QVERIFY2(res["ok"].toBool(), qPrintable(res["error"].toString()));
        QCOMPARE(res["result"].toObject()["clip"].toString(), QString("SYN_IMPORTED"));
    }
    void importClipBadOutputIsError() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        wbtest::put(d.path(), "workbench.json", QString(wbtest::kProject).replace("import sys,json; print(json.dumps({'clip': 'SYN_IMPORTED', 'frames': 20}))", "print('not json')").toUtf8());
        wbtest::FakeEngine eng; Session s(d.path(), &eng); s.data().reload(); registerClipCommands(s);
        CommandContext c{s};
        QJsonObject res = s.registry().call("import_clip", {{"source", "x"}, {"target_name", "y"}}, c);
        QVERIFY(!res["ok"].toBool()); QVERIFY(res["error"].toString().contains("not JSON"));
    }
    void runChecksStaticWithoutEngine() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        // make both rows share a clip
        QString g = wbtest::kGameplay; g.replace("SYN_ATC_007", "SYN_ATC_002");
        wbtest::put(d.path(), "gameplay.json", g.toUtf8());
        Session s(d.path(), nullptr); s.data().reload(); registerHitboxCommands(s);
        CommandContext c{s};
        QJsonObject res = s.registry().call("run_checks", {}, c)["result"].toObject();
        QVERIFY(!res["engine"].toBool());
        QCOMPARE(res["problems"].toArray()[0].toObject()["kind"].toString(), QString("duplicate_clip"));
    }
};
QTEST_MAIN(EditCmdTest)
#include "commands_edit_test.moc"
```

- [ ] **Step 2: Run to verify failure.** Expected compile error.

- [ ] **Step 3: Implement** the four `register*Commands` functions and `analysis.*`. Helper in `commands.h`: `inline EngineBackend &needEngine(Session &s) { if (!s.engine()) throw CommandError{"engine not running"}; return *s.engine(); }` and `inline QJsonObject engineCall(Session &s, const QString &fn, const QJsonObject &a) { QString err; QJsonObject r = needEngine(s).call(fn, a, &err); if (!err.isEmpty()) throw CommandError{err}; return r; }`. Every mutating command schema includes `"propose": {"type":"boolean"}` and its handler sets `ctx.propose |= args["propose"].toBool()`. `set_frame` requires `Session::currentRow` (set by `load_row`) else `CommandError{"no row loaded; call load_row first"}`.

Session additions (same task): `QString currentRow; QJsonObject camera, overlays;`.

- [ ] **Step 4: Run tests** — `ctest --test-dir _build/wb-qt -R workbench_commands_edit --output-on-failure`. Expected 11 slots pass.

- [ ] **Step 5: Commit** — `git commit -m "workbench: view, row, hitbox, clip and check commands"`.

---

### Task 11: McpServer and CLI entry points  (Workspace repo)

**Files:**
- Create: `workbench/mcp_server.h/.cpp`, `workbench/workbench_main.h/.cpp`, `workbench/tests/mcp_test.cpp`
- Modify: `workbench/CMakeLists.txt`, `tools/release/launcher/qt/main.cpp` (options `--mcp`, `--wb-call`, `--workbench`, `--project`)

**Interfaces:**
- Consumes: `CommandRegistry::list/call`, `Session`.
- Produces:

```cpp
namespace wb {
class McpServer {
public:
  explicit McpServer(Session &s);
  // Pure: one JSON-RPC request object in, one response out; notifications (no "id") return an empty object.
  QJsonObject handle(const QJsonObject &request);
  // Parses a line; malformed JSON yields a -32700 error response (id null).
  QByteArray handleLine(const QByteArray &line);
  int runStdio();                       // read stdin lines, write stdout lines; returns 0 at EOF
  bool listenLocal(quint16 port, QString *err);   // 127.0.0.1 only; newline-delimited JSON-RPC, one QTcpServer
  static QJsonObject toolSchema(const CommandSpec &);
};
int runWorkbenchCli(int argc, char **argv);   // implements --mcp / --wb-call
}
```

Protocol: `initialize` -> `{protocolVersion:"2024-11-05", capabilities:{tools:{}}, serverInfo:{name:"gd-melee-workbench", version:"1"}}`; `notifications/initialized` -> no response; `tools/list` -> `{tools:[{name,description,inputSchema}]}` for every registered command; `tools/call` `{name, arguments}` -> `{content:[{type:"text", text:<result JSON>}], isError:<bool>}`; `ping` -> `{}`. Unknown method -> error `-32601`. `tools/call` with unknown tool -> JSON-RPC error `-32602`. Author on all MCP calls is `"agent"`. `--wb-call <command> '<json args>' --project <dir>` runs one command (author `human`) and prints the envelope; exit code 1 when `ok` is false.

`workbench_main`'s `buildSession(projectDir, enginePortOrExe)` creates `Session`, optional `EngineLink` (attach if `--engine-port N`, spawn if `--engine-exe`), and calls `registerAllCommands`.

- [ ] **Step 1: Write the failing tests**

```cpp
#include "../testfixture.h"
#include "commands.h"
#include "mcp_server.h"
#include "session.h"
#include <QTemporaryDir>
#include <QtTest>
using namespace wb;

struct McpRig {
    QTemporaryDir d; wbtest::FakeEngine eng; Session s; McpServer m;
    McpRig() : d(), s((wbtest::makeSynthFighter(d.path()), d.path()), &eng), m(s) { s.data().reload(); registerAllCommands(s); }
};
static QJsonObject req(int id, const QString &method, QJsonObject params = {}) { return {{"jsonrpc", "2.0"}, {"id", id}, {"method", method}, {"params", params}}; }

class McpTest : public QObject {
    Q_OBJECT
private slots:
    void initializeAndList() {
        McpRig r;
        QJsonObject i = r.m.handle(req(1, "initialize"));
        QVERIFY(i["result"].toObject().contains("protocolVersion"));
        QJsonArray tools = r.m.handle(req(2, "tools/list"))["result"].toObject()["tools"].toArray();
        QSet<QString> names; for (auto t : tools) names.insert(t.toObject()["name"].toString());
        for (const char *n : {"open_fighter", "engine_status", "engine_restart", "render_view", "set_camera", "set_overlays", "list_rows", "load_row",
                              "set_frame", "play", "frame_info", "list_hitboxes", "edit_hitbox", "suggest_hitbox_bone", "list_clips", "preview_clip",
                              "assign_clip", "import_clip", "set_ground_mode", "run_checks", "save", "rebuild", "reload", "undo", "redo", "history",
                              "propose", "accept", "reject"})
            QVERIFY2(names.contains(n), n);
    }
    void everyToolHasAValidSchema() {
        McpRig r;
        for (auto t : r.m.handle(req(2, "tools/list"))["result"].toObject()["tools"].toArray()) {
            QJsonObject o = t.toObject();
            QVERIFY(!o["description"].toString().isEmpty());
            QCOMPARE(o["inputSchema"].toObject()["type"].toString(), QString("object"));
        }
    }
    void callEveryToolWithEmptyArgsNeverCrashes() {
        McpRig r;
        r.eng.canned["frame"] = QJsonObject{{"frame", 1}}; r.eng.canned["render"] = QJsonObject{{"path", "x.png"}};
        for (auto t : r.m.handle(req(2, "tools/list"))["result"].toObject()["tools"].toArray()) {
            QString name = t.toObject()["name"].toString();
            if (name == "rebuild" || name == "import_clip") continue;   // run external tools; covered elsewhere
            QJsonObject resp = r.m.handle(req(3, "tools/call", {{"name", name}, {"arguments", QJsonObject()}}));
            QVERIFY2(resp.contains("result") || resp.contains("error"), qPrintable(name));
        }
    }
    void toolCallReturnsTextContent() {
        McpRig r;
        QJsonObject resp = r.m.handle(req(4, "tools/call", {{"name", "list_rows"}, {"arguments", QJsonObject()}}));
        QJsonObject res = resp["result"].toObject();
        QVERIFY(!res["isError"].toBool());
        QJsonObject payload = QJsonDocument::fromJson(res["content"].toArray()[0].toObject()["text"].toString().toUtf8()).object();
        QCOMPARE(payload["rows"].toArray().size(), 2);
    }
    void commandErrorIsToolError() {
        McpRig r;
        QJsonObject res = r.m.handle(req(5, "tools/call", {{"name", "edit_hitbox"}, {"arguments", QJsonObject{{"row", "dair"}}}}))["result"].toObject();
        QVERIFY(res["isError"].toBool());
    }
    void unknownToolAndMethod() {
        McpRig r;
        QCOMPARE(r.m.handle(req(6, "tools/call", {{"name", "nope"}}))["error"].toObject()["code"].toInt(), -32602);
        QCOMPARE(r.m.handle(req(7, "bogus/method"))["error"].toObject()["code"].toInt(), -32601);
    }
    void notificationHasNoResponse() {
        McpRig r;
        QVERIFY(r.m.handle({{"jsonrpc", "2.0"}, {"method", "notifications/initialized"}}).isEmpty());
    }
    void malformedJsonLine() {
        McpRig r;
        QJsonObject resp = QJsonDocument::fromJson(r.m.handleLine("{ nope")).object();
        QCOMPARE(resp["error"].toObject()["code"].toInt(), -32700);
        QVERIFY(resp["id"].isNull());
        // server still works afterwards
        QJsonObject ok = QJsonDocument::fromJson(r.m.handleLine(QJsonDocument(req(1, "ping")).toJson(QJsonDocument::Compact))).object();
        QVERIFY(ok.contains("result"));
    }
    void mcpEditsAreAuthoredByAgent() {
        McpRig r;
        r.m.handle(req(8, "tools/call", {{"name", "edit_hitbox"}, {"arguments", QJsonObject{{"row", "dair"}, {"ordinal", 0}, {"damage", 20}}}}));
        QCOMPARE(r.s.history().entries().last().author, QString("agent"));
    }
    void localSocketRoundTrip() {
        McpRig r; QString err;
        QVERIFY2(r.m.listenLocal(0, &err), qPrintable(err));
        QTcpSocket c; c.connectToHost(QHostAddress::LocalHost, r.m.localPort());
        QVERIFY(c.waitForConnected(2000));
        c.write(QJsonDocument(req(1, "ping")).toJson(QJsonDocument::Compact) + "\n");
        QTRY_VERIFY_WITH_TIMEOUT(c.bytesAvailable() > 0 || c.waitForReadyRead(50), 3000);
        QVERIFY(QJsonDocument::fromJson(c.readLine()).object().contains("result"));
    }
};
QTEST_MAIN(McpTest)
#include "mcp_test.moc"
```

(Add `quint16 localPort() const;` to the interface; `listenLocal(0, ...)` picks a free port. Never bind anything but `QHostAddress::LocalHost`.)

- [ ] **Step 2: Run to verify failure.** Expected compile error.

- [ ] **Step 3: Implement.** `handle`: switch on method; for `tools/call` set `CommandContext{session, "agent"}`, call `registry.call`, wrap: `{content:[{type:"text",text:QJsonDocument(env["ok"] ? env["result"] : QJsonObject{{"error",env["error"]}}).toJson(Compact)}], isError:!ok}`. Add a `set_ground_mode` stub registration only in Task 14; for this task's `initializeAndList` test to pass, Task 14's command must exist, so mark `QVERIFY2(names.contains("set_ground_mode"))` as part of Task 14's acceptance: **in this task remove `"set_ground_mode"` from the list; Task 14 re-adds it** to this test.
`runStdio`: `QTextStream`-free: `std::getline(std::cin, line)` loop, write `handleLine(line) + '\n'` to `stdout` and flush; skip empty replies (notifications) and blank lines. Logging goes to stderr only (stdout is the protocol channel).
`main.cpp`: before constructing `QApplication` (it must not create windows for `--mcp`/`--wb-call`), construct `QCoreApplication` when `argv` contains `--mcp` or `--wb-call` and return `runWorkbenchCli`.

- [ ] **Step 4: Run tests** — `ctest --test-dir _build/wb-qt -R workbench_mcp --output-on-failure`. Expected 9 slots pass.

- [ ] **Step 5: Smoke the real binary over stdio**

```bash
cmake --build _build/wb-qt --target gd-melee-launcher
printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize"}' '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  | _build/wb-qt/gd-melee-launcher --mcp --project tools/release/launcher/qt/workbench/tests/none 2>/dev/null | head -c 400
```

Expected: two JSON lines; the first contains `"protocolVersion"`. (With a non-project dir, `tools/list` still lists tools; commands error on call.)

- [ ] **Step 6: Commit** — `git commit -m "workbench: MCP server over stdio and localhost, wb-call CLI"`.

---

### Task 12: Game workbench mode and wb.* API  (Game repo, branch agent/geno-workbench)

Independent of every workspace task above. Can run in parallel from the start.

**Files (all in the game repo worktree):**
- Create: `pc/platform/gw_workbench.h`, `pc/platform/gw_workbench.c`, `pc/tests/workbench_test.c`, `pc/tests/workbench_check.lua`
- Modify: `pc/platform/gw_runtime.c` (mode table ~1654 and the scene parse that fills `gw_sl_cfg`), `pc/platform/gw_script.c` (register `wb` table next to `gs_gd_funcs` ~6725; include header), `pc/gameworld/script_game.c` (accessor next to `ScriptGame_LabF` ~1983), the build file listing platform TUs for the game (find with `grep -rn "gw_script.c" tools/port/*.py tools/port/*.sh CMakeLists.txt 2>/dev/null` in the workspace's `tools/port/`), and `tools/port/native_test.sh` (workspace repo: separate commit on `ws/geno-workbench`).

**Interfaces:**
- Produces (C): 

```c
/* gw_workbench.h */
int  gw_Wb_Enabled(void);                       /* 1 only when mode=workbench was requested AND no netplay/slippi session */
void gw_Wb_SetEnabled(int on);                  /* called by the scene parser */
const char *gw_Wb_Dir(void);                    /* MELEE_WB_DIR or "" */
int  gw_Wb_WritePayload(const char *name, const char *data, size_t n, char *path_out, size_t cap); /* writes <wbdir>/<name>; 0 ok */
typedef struct { int joint, parent; float x, y, z; } GwWbBone;
typedef struct { int slot, joint, active; float ox, oy, oz, radius, wx, wy, wz; } GwWbHit;
typedef struct { int joint; float ax, ay, az, bx, by, bz, radius; } GwWbHurt;
typedef struct { int motion, frame; int nbones, nhits, nhurts; GwWbBone bones[160]; GwWbHit hits[8]; GwWbHurt hurts[24];
                 float ecb_bx, ecb_by, ecb_tx, ecb_ty, floor_y, lowest_y; } GwWbFrame;
int gw_Wb_FrameJson(const GwWbFrame *f, const char *row, char *out, size_t cap);  /* returns length or -1 if cap too small */
```

Lua (registered as table `wb`): all return ONE string.
- `wb.load(mod_id, costume)` -> `"ok"`; checks `gw_Wb_Enabled()`; the fighter is already seeded by the scene (`p1=geno:<mod>/hu`); `load` only validates that port 1 has a fighter and returns `"ok"` or errors `"no fighter on port 1"`.
- `wb.row(t)` t={motion=int} -> remembers the motion; `"ok"`.
- `wb.frame(t)` t={motion=int, frame=int} -> `gd.set_motion(1, motion, frame, 1.0, 0)` semantics (re-enter then run frame-1 logic frames, paused), then waits via the same mechanism as `l_set_motion`; returns `@<wbdir>/frame.json`.
- `wb.step(t)` t={n=int} -> sets `gs.step += n` (as `gd.step`); returns `@frame.json`.
- `wb.frame_info(t)` -> `@frame.json` from the live fighter.
- `wb.clip(t)` t={clip=string, frame=int} -> preview by clip name via `gd.anim_preview` row lookup (row index from `gw_ScriptGame_LabAnimSymbolFor`), `@frame.json`.
- `wb.render(t)` t={w,h,camera={...},overlays={...}} -> sets camera override + overlay flags, `gw_Screenshot("<wbdir>/view.png")`, returns `"@<wbdir>/view.png"` (file appears a few frames later; the launcher polls for it, see Task 15).
- `wb.reload()` -> re-reads the fighter package: v1 returns error `"reload needs restart"` unless the registry already exposes a reinstall call (Step 5 finds out); EngineLink treats that error as "restart required" and calls `restart()`.

- [ ] **Step 1: Create the worktree and branch**

```bash
cd "E:/Projects/Melee Workspace"
git -C worktrees/goku-polish worktree add ../geno-workbench -b agent/geno-workbench agent/goku-polish
```

(The game checkout is a git worktree of the `melee` repo; if `git -C worktrees/goku-polish worktree list` shows a different layout, use `tools/port/agent_new.sh geno-workbench` and `GW_BUILD_ROOT=_build/agents/geno-workbench`.) Set for all following commands: `export GW_MELEE="E:/Projects/Melee Workspace/worktrees/geno-workbench"`, `export GW_BUILD_ROOT="E:/Projects/Melee Workspace/_build/agents/geno-workbench"`.

- [ ] **Step 2: Write the failing native test (pure: gate + JSON writer)**

`pc/tests/workbench_test.c`:

```c
/* Pure test of gw_workbench.c: the gate and the frame JSON writer. No game link. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "gw_workbench.h"

static int netplay_stub = 0;
int gw_Wb_NetplayActive(void) { return netplay_stub; }   /* test seam: gw_workbench.c declares it extern */

int main(void) {
    char out[4096];
    GwWbFrame f;
    /* gate */
    assert(!gw_Wb_Enabled());
    gw_Wb_SetEnabled(1);
    assert(gw_Wb_Enabled());
    netplay_stub = 1;
    assert(!gw_Wb_Enabled());           /* never active online */
    netplay_stub = 0;
    gw_Wb_SetEnabled(0);
    assert(!gw_Wb_Enabled());

    /* json */
    memset(&f, 0, sizeof f);
    f.motion = 70; f.frame = 6; f.nbones = 1; f.nhits = 1; f.nhurts = 0;
    f.bones[0].joint = 3; f.bones[0].parent = 1; f.bones[0].x = 1.5f; f.bones[0].y = 2.0f; f.bones[0].z = -0.25f;
    f.hits[0].slot = 0; f.hits[0].joint = 3; f.hits[0].active = 1; f.hits[0].radius = 2.8f; f.hits[0].wy = 4.0f;
    f.floor_y = 0.0f; f.lowest_y = -0.5f;
    assert(gw_Wb_FrameJson(&f, "dair", out, sizeof out) > 0);
    assert(strstr(out, "\"row\":\"dair\""));
    assert(strstr(out, "\"motion\":70"));
    assert(strstr(out, "\"joint\":3"));
    assert(strstr(out, "\"active\":true"));
    assert(strstr(out, "\"lowestY\":-0.5"));
    /* too small buffer is reported, not truncated silently */
    assert(gw_Wb_FrameJson(&f, "dair", out, 20) == -1);
    /* a row name with quotes is escaped */
    assert(gw_Wb_FrameJson(&f, "a\"b", out, sizeof out) > 0 && strstr(out, "a\\\"b"));
    /* payload write refuses an empty dir */
    { char p[256]; assert(gw_Wb_WritePayload("x.json", "{}", 2, p, sizeof p) != 0); }
    puts("workbench native test OK");
    return 0;
}
```

- [ ] **Step 3: Register the native test and run it (fails to compile)**

In `tools/port/native_test.sh` (workspace repo, worktree `ws-geno-workbench`) add before the `*)` default and in the error list:

```bash
workbench)
    sources=(pc/tests/workbench_test.c pc/platform/gw_workbench.c) ;;
```

Run: `GW_MELEE=... GW_BUILD_ROOT=... bash tools/port/build.sh --native-test workbench`
Expected: FAIL, `gw_workbench.h: No such file`.

- [ ] **Step 4: Implement `gw_workbench.h/.c`**

`gw_Wb_Enabled()`: `return g_enabled && !gw_Wb_NetplayActive();` where `gw_workbench.c` declares `extern int gw_Wb_NetplayActive(void);` and the game links the real one defined in `gw_script.c` as `int gw_Wb_NetplayActive(void) { return <the existing offline predicate negated>; }` (use the same predicate `gs_require_offline` uses, `gw_script.c:846`). `gw_Wb_FrameJson` uses `snprintf` into a cursor with a bounds check after each append; floats printed with `%.4g`... use `%.5f` trimmed? Use `%g` (the test expects `-0.5`, `4.0` prints as `4`; test only checks `lowestY:-0.5`). Strings escaped for `"` and `\`. `gw_Wb_WritePayload`: returns nonzero if `MELEE_WB_DIR` is unset/empty; else writes `<dir>/<name>` through a temp file and `rename` (so the launcher never reads half a file).

JSON shape (must match `FrameInfo::fromJson`, Task 7): `{"row":"…","motion":N,"frame":N,"bones":[{"joint":J,"parent":P,"pos":{"x":..,"y":..,"z":..}}],"hitboxes":[{"slot":S,"joint":J,"active":true|false,"offset":{x,y,z},"radius":R,"world":{x,y,z}}],"hurtboxes":[{"joint":J,"a":{..},"b":{..},"radius":R}],"ecb":{"bottom":{"x":..,"y":..},"top":{"x":..,"y":..}},"floorY":F,"lowestY":L}`. Update `FrameInfo::fromJson/toJson` in Task 7 to this exact shape (the Task 7 round-trip test only exercises `bones`, `hitboxes[].world/active`).

- [ ] **Step 5: Run the native test**

Run: `bash tools/port/build.sh --native-test workbench`
Expected: `workbench native test OK`.

- [ ] **Step 6: Scene mode `workbench`**

In `pc/platform/gw_runtime.c` add to `gw_sl_modes[]` after the `lab` row:

```c
    {"workbench", 0x2F, 0}, /* LAB's game mode; gw_sl_parse also calls gw_Wb_SetEnabled(1) for this keyword */
```

In the function that resolves the `mode` keyword into `gw_sl_cfg.mode` (find with `grep -n "gw_sl_modes\[" pc/platform/gw_runtime.c`), after a match whose `name` is `"workbench"`, call `gw_Wb_SetEnabled(1)`; also accept the `--workbench` argv by setting `MELEE_SCENE` default (`mode=workbench;p1=geno:<MELEE_WB_MOD>/hu;stage=fd`) when `argv` has it. `gm_Mode_Lab_OnLoad` (`geno_lab_mode.c` ~229) compares `SceneLaunch_BootGameMode() == GM_LAB`; it stays correct because `0x2F` is GM_LAB. Add `p2` absent => no second fighter (verify with `grep -n "slot_type" pc/platform/gw_runtime.c`; if an absent p2 seeds a default CPU, add `p2=none` handling or require the launcher to pass `p2=` empty; record the finding in the commit message).

- [ ] **Step 7: Frame accessor in `script_game.c`**

Next to `ScriptGame_LabF`, add:

```c
/* Workbench (pc/platform/gw_workbench.h): read-only snapshot of the live fighter for wb.frame_info.
 * Reads only; never writes game state. Fighter *fp; hit capsules are fp->x914[4] (types.h), hurtboxes fp->hurt_capsules. */
int ScriptGame_WbFrame(int slot, GwWbFrame *out)
{
    Fighter* fp = script_fighter(slot);
    int i;
    if (fp == NULL) return 0;
    memset(out, 0, sizeof *out);
    out->motion = fp->motion_id;
    out->frame = (int) fp->anim_frame; /* verify the exact field names with grep in ft/types.h before building */
    for (i = 0; i < 4 && out->nhits < 8; ++i) {
        HitCapsule* h = &fp->x914[i];
        GwWbHit* o;
        if (h->state == HitCapsule_Disabled) continue;
        o = &out->hits[out->nhits++];
        o->slot = i; o->active = 1; o->radius = h->scale;
        o->ox = h->b_offset.x; o->oy = h->b_offset.y; o->oz = h->b_offset.z;
        o->wx = h->x58.x; o->wy = h->x58.y; o->wz = h->x58.z;   /* x58 is the world position this frame (confirm against ftcoll.c users) */
        o->joint = ScriptGame_WbJointIndex(h->jobj);
    }
    /* bones: walk fp->parts / the root jobj with HSD_JObjGetTranslation + the world matrix; hurtboxes: fp->hurt_capsules[].capsule;
       ecb: fp->coll_data.ecb; lowest_y: min over bone world y minus nothing (bones only) */
    return 1;
}
```

Before writing the body, the implementer runs, in the game worktree: `grep -n "motion_id\|anim_frame\|cur_anim_frame\|hurt_capsules\|x914\|parts" src/melee/ft/types.h | head -30`, `grep -n "x58\|x4C" src/melee/ft/ftcoll.c | head`, and `grep -rn "HSD_JObjGetTranslation\|JObjGetWorld\|lb_8000B1CC" pc/gameworld/script_arena.inc | head` (the arena spawn code already converts jobj to world coordinates and has a native test, `pc/tests/arena_spawn_test.c`, to copy the matrix approach). The field names in the snippet above are the intent; use the real names found by those greps. `ScriptGame_WbJointIndex` maps a `HSD_JObj*` to its index by walking the fighter's joint array (`fp->parts[i].joint`).

- [ ] **Step 8: `wb` Lua table in `gw_script.c`**

Add after `gs_gd_funcs` a `static const luaL_Reg gs_wb_funcs[]` (`load,row,frame,step,frame_info,clip,render,reload`) and register it where `gd` is registered (`grep -n "gs_gd_funcs" pc/platform/gw_script.c`): `luaL_newlib(L, gs_wb_funcs); lua_setglobal(L, "wb");`, only `if (gw_Wb_Enabled())` (so the table is absent outside the mode). Each function begins with `gs_require_offline(L, "wb.<fn>")` and `if (!gw_Wb_Enabled()) luaL_error(L, "workbench mode is not enabled")`. `wb.frame` implementation reuses `l_set_motion`'s body by calling it with a constructed stack (push port 1, motion, frame, 1.0, 0) via a shared static helper `gs_set_motion_core(int slot, int motion, int frame, float rate, float lift)` extracted from `l_set_motion` (a pure refactor: `l_set_motion` calls the helper; run the existing script tests to prove no behaviour change, Step 10). Because the pause/step machinery runs on later frames, `wb.frame` returns `@frame.json` only after those frames ran: implement as a Lua-side task: `wb.frame` registers `gs.wb_pending = FRAME` and returns `"pending"`; EngineLink then polls with `wb.frame_info()` until the reply's `frame == requested` (EngineLink handles this in Task 7 `call("frame", ...)`: after the call, poll `frame_info` every 50 ms up to 5 s until `frame` matches; add that loop and a FakeConsole test for it).

- [ ] **Step 9: Build the game**

Run: `bash tools/port/build.sh` (with `GW_MELEE`/`GW_BUILD_ROOT` as above). Expected: ends with the bridge audit passing (`build.sh` regenerates `gw_mex_bridge.c`; leave it uncommitted). Verify the new code is in the exe: `grep -a "workbench mode is not enabled" "$GW_BUILD_ROOT/melee-pc.exe" | head -c 100` (path per `tools/port/README.md`).

- [ ] **Step 10: In-game scripted check**

`pc/tests/workbench_check.lua`: a pad script that runs under `MELEE_TURBO=1`; waits until `gd.lab_mode()` is true; calls `wb.load`, `wb.frame{motion=<a Geno attack motion>, frame=6}`, `wb.frame_info()`, reads the JSON file named in the reply, and `gd.print`s `WBCHECK hitboxes=<n> bones=<n>` then `gd.quit()`. It also asserts that on a normal VS scene `wb` is nil (`assert(wb == nil)`) in a second run (below).

```bash
# workbench scene; uses a built Geno fighter from the mods dir; disc from .env
MELEE_TURBO=1 MELEE_PAD_SCRIPT="$GW_MELEE/pc/tests/workbench_check.lua" MELEE_WB_DIR="$GW_BUILD_ROOT/wb" \
MELEE_SCENE="mode=workbench;p1=geno:goku-xv2/hu;stage=fd" MELEE_MODS_DIR="E:/Projects/Melee Workspace/_build/goku-xv2/author-source/package/mods" \
MELEE_WINDOW_X=100 MELEE_WINDOW_Y=80 bash tools/port/run.sh batch --iso "$GW_ISO_VANILLA"
grep -a "WBCHECK" "$GW_BUILD_ROOT"/runs/*/melee-pc.log | tail -3
```

Expected: a line `WBCHECK hitboxes=1 bones=126` (a dair-like move at an active frame; bones equals the plan's `joint_count`). A second run with `MELEE_SCENE="mode=vs;p1=fox;p2=marth;stage=fd"` prints `WBCHECK wb=nil`. Also run the existing script test suite (`bash tools/port/run.sh --test` per `tools/port/README.md`) and expect no new failures vs the base branch.

- [ ] **Step 11: Commit (game repo, then workspace repo)**

```bash
git -C worktrees/geno-workbench add pc/platform/gw_workbench.h pc/platform/gw_workbench.c pc/tests/workbench_test.c pc/tests/workbench_check.lua pc/platform/gw_runtime.c pc/platform/gw_script.c pc/gameworld/script_game.c
git -C worktrees/geno-workbench commit -m "workbench mode: scene keyword, wb.* console API, frame snapshot" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C worktrees/ws-geno-workbench add tools/port/native_test.sh
git -C worktrees/ws-geno-workbench commit -m "native_test: workbench case" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 13: Hitbox cross-check against the existing checker  (Workspace repo)

Spec test: step frames of a sample fighter and compare `wb.frame_info` hitbox positions with the existing hitbox-position checker (`ports/ir/tools/check_hitbox_positions.py`).

**Files:**
- Create: `tools/workbench/compare_hitboxes.py`, `tools/workbench/test_compare_hitboxes.py`

**Interfaces:**
- Consumes: `check_hitbox_positions.sphere(words, pose)`, `.read_installed_words`, `.hitbox_events`, `.live_spheres`, `.pose_matrices`, `.installed_tree` (module imports as in `ground_audit.py`: `sys.path.insert(0, ROOT/'ports/ir/tools')`; `import check_hitbox_positions as HP`), and `tools/port/gd_prompt.Console` (`Console(host, port)`, line API) for the live side.
- Produces: `compare(wb_hits, ref_spheres, tol) -> list[dict]` (pure) and a CLI `python tools/workbench/compare_hitboxes.py --port 51726 --row dair --motion 70 --frames 6,9 --tol 0.5` printing one line per (frame, slot): `OK|DIFF frame=6 slot=0 wb=(x,y,z) ref=(x,y,z) d=0.12`.

- [ ] **Step 1: Write the failing pytest (pure function only; synthetic numbers)**

```python
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import compare_hitboxes as C


def test_match_within_tolerance():
    wb = [{"slot": 0, "world": {"x": 1.0, "y": 2.0, "z": 0.0}, "radius": 2.8, "active": True}]
    ref = [{"slot": 0, "pos": (1.1, 2.0, 0.0), "radius": 2.8}]
    r = C.compare(wb, ref, 0.5)
    assert r[0]["ok"] and math.isclose(r[0]["d"], 0.1, abs_tol=1e-9)


def test_diff_beyond_tolerance_and_radius_mismatch():
    wb = [{"slot": 0, "world": {"x": 0, "y": 0, "z": 0}, "radius": 2.0, "active": True}]
    assert not C.compare(wb, [{"slot": 0, "pos": (3, 0, 0), "radius": 2.0}], 0.5)[0]["ok"]
    assert not C.compare(wb, [{"slot": 0, "pos": (0, 0, 0), "radius": 3.0}], 0.5)[0]["ok"]


def test_missing_on_either_side_is_reported():
    wb = [{"slot": 0, "world": {"x": 0, "y": 0, "z": 0}, "radius": 1, "active": True}]
    r = C.compare(wb, [], 0.5)
    assert r[0]["ok"] is False and r[0]["why"] == "missing in reference"
    r = C.compare([], [{"slot": 1, "pos": (0, 0, 0), "radius": 1}], 0.5)
    assert r[0]["why"] == "missing in wb"


def test_inactive_wb_hitboxes_ignored():
    wb = [{"slot": 0, "world": {"x": 0, "y": 0, "z": 0}, "radius": 1, "active": False}]
    assert C.compare(wb, [], 0.5) == []
```

- [ ] **Step 2: Run** — `python -m pytest tools/workbench/test_compare_hitboxes.py -q`. Expected: FAIL (`No module named compare_hitboxes`).

- [ ] **Step 3: Implement** `compare()` (match by slot; distance `math.dist`; ok = `d <= tol and abs(r_wb - r_ref) <= 0.1`; one dict per slot with keys `slot, ok, d, why`) and the CLI. The CLI side: connect with `gd_prompt.Console`, send `= wb.frame({motion=M, frame=F})`, poll `= wb.frame_info()` until the file in the reply has `frame == F`, read it, and take the reference from `HP` for the same installed fighter (documented in the module docstring: needs the built package under `_build/goku-xv2/author-source/package`; reference spheres via `HP.live_spheres(HP.hitbox_events(words), frame)` and `HP.sphere(words, pose)`; exact call sequence copied from `HP.check_install` lines ~340-420, which the implementer reads first).

- [ ] **Step 4: Run** — `python -m pytest tools/workbench/test_compare_hitboxes.py -q`. Expected: 4 passed.

- [ ] **Step 5: Live run (owed to a machine with the disc)** — start the game as in Task 12 Step 10 with `MELEE_CONSOLE_PORT=51726` and `MELEE_TURBO` unset (the console answers one command per rendered frame), then `python tools/workbench/compare_hitboxes.py --port 51726 --row dair --motion 70 --frames 6,9 --tol 0.5`. Expected: all lines `OK`. Report the output verbatim in the lane report.

- [ ] **Step 6: Commit** — `git add tools/workbench && git commit -m "workbench: wb.frame_info vs check_hitbox_positions comparison"`.

---

### Task 14: Ground modes  (Workspace repo, ports/goku-xv2)

**Files:**
- Create: `ports/goku-xv2/ground_modes.json` (synthetic-free: names only, no data derived from the game)
- Modify: `ports/goku-xv2/tools/xv2_to_artist.py` (read the file; fall back to the current hard-coded lists when absent), `workbench/commands_ground.cpp` (create), `workbench/tests/commands_ground_test.cpp` (create), `workbench/mcp test` list, `workbench/CMakeLists.txt`
- Test: `ports/goku-xv2/tests/test_ground_modes.py` (create)

**Interfaces:**
- Consumes: `jsonReplace/jsonInsertKey/jsonScalar`, `Session::commit`.
- Produces: `ground_modes.json` schema `{"schema":"ground-modes/1","rows":{"<RowName>":{"mode":"hover|anchored|blend","blend_in":0,"blend_out":0}},"grounded_clips":["..."]}`; command `set_ground_mode{row:string, mode:enum[hover,anchored,blend], blend_in?:integer, blend_out?:integer, propose?:boolean}`; Python `ground_mode_for(row) -> dict` in `xv2_to_artist.py`.

- [ ] **Step 1: Read how the script chooses HOVER/ANCHORED today**

Run: `grep -n "HOVER\|ANCHORED\|HOVER_Y" ports/goku-xv2/tools/xv2_to_artist.py | head -30`. Record the data structure (a set/dict of row names) in the commit message. `ground_mode_for(row)` must return exactly what that structure returns today when `ground_modes.json` is absent, so builds are unchanged until a row is edited.

- [ ] **Step 2: Write the failing tests**

pytest (`ports/goku-xv2/tests/test_ground_modes.py`):

```python
import json, sys
from pathlib import Path
PORT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PORT / "tools"))
import xv2_to_artist as X


def test_default_matches_legacy_when_file_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(X, "GROUND_MODES_PATH", tmp_path / "missing.json")
    assert X.ground_mode_for("Wait")["mode"] in ("hover", "anchored", "blend")


def test_file_overrides_row(tmp_path, monkeypatch):
    p = tmp_path / "g.json"
    p.write_text(json.dumps({"schema": "ground-modes/1", "rows": {"Wait": {"mode": "blend", "blend_in": 3, "blend_out": 5}}}))
    monkeypatch.setattr(X, "GROUND_MODES_PATH", p)
    m = X.ground_mode_for("Wait")
    assert (m["mode"], m["blend_in"], m["blend_out"]) == ("blend", 3, 5)


def test_bad_mode_rejected(tmp_path, monkeypatch):
    p = tmp_path / "g.json"
    p.write_text(json.dumps({"schema": "ground-modes/1", "rows": {"Wait": {"mode": "float"}}}))
    monkeypatch.setattr(X, "GROUND_MODES_PATH", p)
    try:
        X.ground_mode_for("Wait")
        assert False
    except ValueError as e:
        assert "float" in str(e)
```

C++ (`commands_ground_test.cpp`): fixture project plus `ground_modes.json` containing `{"schema":"ground-modes/1","rows":{},"grounded_clips":[]}`; `set_ground_mode{row:"Jab1",mode:"hover"}` -> file contains `"Jab1": {"mode":"hover","blend_in":0,"blend_out":0}` and parses as JSON; calling again with `anchored` replaces in place (single occurrence of `Jab1`); `mode:"blend"` without `blend_in` defaults both to 0; unknown row (not in `fidelity.json` rows) -> error `unknown row`; missing `ground_modes.json` is created from the template `{\n  "schema": "ground-modes/1",\n  "rows": {},\n  "grounded_clips": []\n}\n`.

- [ ] **Step 3: Run both; verify failure.**
- [ ] **Step 4: Implement** the Python reader (`GROUND_MODES_PATH = PORT / "ground_modes.json"`, validate modes) and the command (row existence checked against `GenoData` fidelity rows plus move names; patch via `jsonInsertKey`/`jsonReplace` on `rows`). Add `registerGroundCommands(Session&)` to `registerAllCommands`. Re-add `"set_ground_mode"` to the Task 11 tool list test.
- [ ] **Step 5: Run** — `python -m pytest ports/goku-xv2/tests/test_ground_modes.py -q` and `ctest --test-dir _build/wb-qt -R "workbench_(commands_ground|mcp)" --output-on-failure`. Expected: pass. Then `python ports/goku-xv2/tools/ground_audit.py` must print the same BELOW/FLOATING counts as before the change when no override exists (needs the built package; report both outputs).
- [ ] **Step 6: Commit** — `git commit -m "workbench: per-row ground modes (data file, builder reads it, set_ground_mode)"`.

---

### Task 15: UI shell, viewport and timeline  (Workspace repo)

Depends on Tasks 7, 9, 10. Uses the Atlas look: read `atlas.h`, `kit.h` first and reuse their helpers (`capLabel`, `kit::TabRail`, `atlas::Role`); do not invent a second style.

**Files:**
- Create: `workbench/workbench_ui_strings.h` (no; strings stay inline `t()` per the rule), `workbench/viewport.h/.cpp`, `workbench/timeline.h/.cpp`, `workbench/workbench_window.h/.cpp`, `workbench/tests/ui_test.cpp`
- Modify: `workbench/CMakeLists.txt` (`workbench_ui` target: `add_library(workbench_ui STATIC viewport.cpp timeline.cpp workbench_window.cpp ...)` linking `workbench_core launcher_ui Qt6::Widgets`), `window.cpp`/`window.h` (Creator entry), `tools/release/launcher/check_qt_strings.py` and `test_check_qt_strings.py` (scan `workbench/` too)

**Interfaces:**
- Consumes: `Session`, `CommandRegistry::call`, `FrameInfo`, `launcher::t`, `launcher::Settings::flag/option`.
- Produces:

```cpp
namespace wb {
class Viewport : public QWidget {          // shows the latest engine PNG, draws overlays on top when the engine cannot
  Q_OBJECT
public:
  explicit Viewport(QWidget *parent = nullptr);
  void setImage(const QImage &img);
  void setFrameInfo(const FrameInfo &fi);  // overlay data for the 2D fallback (bones, ECB, floor)
  void setOverlay(const QString &name, bool on);   // "hitboxes","hurtboxes","bones","ecb","floor"
signals:
  void cameraChanged(const QJsonObject &camera);   // orbit by drag, wheel zoom, preset buttons call this
};
class Timeline : public QWidget {
  Q_OBJECT
public:
  void setRange(int frames);
  void setBars(const QVector<QPair<QString, QPair<int,int>>> &bars);   // label, [start,end) e.g. "hitbox 0", "IASA"
  void setFrame(int f);
signals:
  void frameRequested(int f);              // J (-1) / K (play/pause) / L (+1), click, Home/End
  void playToggled(bool playing);
};
class WorkbenchWindow : public QMainWindow {
public:
  WorkbenchWindow(Session &s, QWidget *parent = nullptr);
  void runCommand(const QString &name, const QJsonObject &args);   // human author; refreshes panels
};
}
```

Behaviour: `WorkbenchWindow::runCommand` calls the registry on the GUI thread through `QtConcurrent::run` + a `QFutureWatcher` so a slow engine never freezes the window; render requests are coalesced (only the latest pending `render_view` runs). The viewport refreshes after `set_frame`, `set_camera`, `set_overlays`, `edit_hitbox` (+ reload) by running `render_view` and polling the PNG path every 50 ms up to 3 s (G-a/G-b), then `QImage(path)`. J/K/L step keys map to `set_frame`/`play`. Strings: window title `t("Creator","Creador")`, button/labels examples `t("Hitboxes","Cajas de golpe")`, `t("Engine not running","Motor detenido")`, `t("Frame %1","Cuadro %1")`.

Launcher integration: `window.cpp` adds a rail entry `t("CREATOR","CREADOR")` only when `settings_.flag("creator_enabled")` is true; Diagnostics/About tab gets a checkbox `t("Enable Creator (experimental)","Activar Creador (experimental)")` that writes the flag. Creator tab shows a project-folder picker (`t("Open fighter folder","Abrir carpeta del luchador")`) and an `Engine` row with Start/Stop (uses `EngineLink` with the game exe from `prepareLaunch` + `MELEE_SCENE`).

- [ ] **Step 1: Write the failing UI test (offscreen)**

```cpp
#include "../testfixture.h"
#include "commands.h"
#include "session.h"
#include "timeline.h"
#include "viewport.h"
#include "workbench_window.h"
#include <QApplication>
#include <QSignalSpy>
#include <QTemporaryDir>
#include <QtTest>
using namespace wb;

class UiTest : public QObject {
    Q_OBJECT
private slots:
    void timelineKeysEmitFrames() {
        Timeline t; t.setRange(40); t.setFrame(10); t.show();
        QSignalSpy spy(&t, &Timeline::frameRequested);
        QTest::keyClick(&t, Qt::Key_L); QTest::keyClick(&t, Qt::Key_J); QTest::keyClick(&t, Qt::Key_J);
        QCOMPARE(spy.size(), 3);
        QCOMPARE(spy[0][0].toInt(), 11); QCOMPARE(spy[1][0].toInt(), 10); QCOMPARE(spy[2][0].toInt(), 9);
    }
    void timelineClampsAtEnds() {
        Timeline t; t.setRange(5); t.setFrame(4); QSignalSpy spy(&t, &Timeline::frameRequested);
        QTest::keyClick(&t, Qt::Key_L);       // already last frame
        QVERIFY(spy.isEmpty() || spy[0][0].toInt() == 4);
        t.setFrame(0); spy.clear(); QTest::keyClick(&t, Qt::Key_J);
        QVERIFY(spy.isEmpty() || spy[0][0].toInt() == 0);
    }
    void viewportOverlayToggleAndCamera() {
        Viewport v; v.resize(320, 240); QSignalSpy spy(&v, &Viewport::cameraChanged);
        v.setOverlay("hitboxes", false);
        QTest::mousePress(&v, Qt::LeftButton, {}, QPoint(100, 100));
        QTest::mouseMove(&v, QPoint(140, 100));
        QTest::mouseRelease(&v, Qt::LeftButton, {}, QPoint(140, 100));
        QVERIFY(spy.size() >= 1);
        QVERIFY(spy.last()[0].value<QJsonObject>().contains("yaw"));
    }
    void windowRunsACommandOffline() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); Session s(d.path(), nullptr); s.data().reload(); registerAllCommands(s);
        WorkbenchWindow w(s);
        w.runCommand("list_rows", {});          // must not crash with no engine
        QVERIFY(true);
    }
    void renderWithoutEngineShowsStatusNotCrash() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); Session s(d.path(), nullptr); s.data().reload(); registerAllCommands(s);
        WorkbenchWindow w(s); w.show();
        w.runCommand("render_view", {});
        QTest::qWait(200);
        QVERIFY(w.statusText().contains("Engine not running") || w.statusText().contains("Motor detenido"));
    }
};
QTEST_MAIN(UiTest)
#include "ui_test.moc"
```

(Add `QString WorkbenchWindow::statusText() const;`. The UI test target links `workbench_ui` and sets `QT_QPA_PLATFORM=offscreen`; add `wb_ui_test(ui)` to CMake mirroring `wb_test` but linking `workbench_ui Qt6::Test Qt6::Widgets`.)

- [ ] **Step 2: Run to verify failure.** Expected compile error.
- [ ] **Step 3: Implement** the three widgets and the launcher entry. Orbit: horizontal drag changes `yaw` by `dx*0.5`, vertical `pitch` by `dy*0.5` clamped to [-89, 89]; wheel scales `distance` by `0.9^notches`; emits `cameraChanged({yaw,pitch,distance})`. The window routes `cameraChanged` to `set_camera` then `render_view`.
- [ ] **Step 4: Run** — `ctest --test-dir _build/wb-qt -R "workbench_ui|launcher_qt_strings|launcher_atlas" --output-on-failure`. Expected: pass. Update `check_qt_strings.py`'s `scan()` to also glob `workbench/*.cpp`/`*.h` (extend the `files` list); add a case to `test_check_qt_strings.py` that a `t("", "x")` in `workbench/` is reported; run `python -m pytest tools/release/launcher/test_check_qt_strings.py -q`.
- [ ] **Step 5: Manual shot (owed, on-screen)** — `gd-melee-launcher --shots <dir>` includes the Creator tab when the flag is set; capture it for the report. Real-engine behaviour (frame stepping against the actual game) is owed to the acceptance run (Task 17).
- [ ] **Step 6: Commit** — `git commit -m "workbench: Creator tab, viewport, timeline, window shell"`.

---

### Task 16: Panels, command palette and bilingual strings  (Workspace repo)

Depends on Tasks 10, 15. Split across lanes: outliner+inspector (Sonnet), problems/clip browser/history-review (Sonnet), palette (Codex).

**Files:**
- Create: `workbench/panels.h/.cpp` (OutlinerPanel, InspectorPanel, ProblemsPanel, ClipBrowserPanel, FidelityPanel, ReviewPanel), `workbench/palette.h/.cpp`, `workbench/tests/panels_test.cpp`
- Modify: `workbench/workbench_window.cpp` (dock the panels), `workbench/CMakeLists.txt`

**Interfaces:**
- Consumes: `Session`, registry, `Problem`, `HistoryEntry`.
- Produces:

```cpp
class OutlinerPanel : public QTreeWidget { Q_OBJECT public: void setSession(Session &); void refresh(); signals: void rowSelected(const QString &row); void hitboxSelected(const QString &row, int ordinal); };
class InspectorPanel : public QWidget { Q_OBJECT public: void showHitbox(const QString &row, const HitboxRef &h); signals: void editRequested(const QString &command, const QJsonObject &args); };
class ProblemsPanel : public QListWidget { Q_OBJECT public: void setProblems(const QVector<Problem> &); signals: void problemActivated(const QString &row, int ordinal); };
class ClipBrowserPanel : public QListWidget { Q_OBJECT public: void setClips(const QVector<ClipInfo> &, const QString &current); signals: void previewRequested(const QString &clip); void assignRequested(const QString &clip); };
class ReviewPanel : public QTableWidget { Q_OBJECT public: void setHistory(const QVector<HistoryEntry> &); signals: void acceptRequested(int id); void rejectRequested(int id); void undoRequested(); void redoRequested(); };
class CommandPalette : public QDialog { Q_OBJECT public: CommandPalette(CommandRegistry &, QWidget *parent = nullptr); static QVector<CommandSpec> filter(const QVector<CommandSpec> &, const QString &query); signals: void commandChosen(const QString &name); };
```

Rules: inspector edits emit `editRequested("edit_hitbox", {row, ordinal, <field>: value})` only when the value changed (no echo loops); Ctrl+P opens the palette; `filter` is case-insensitive subsequence match on `name` then on `description`, name matches first; ReviewPanel shows `proposed` rows with Accept/Reject enabled only for them; authors rendered as `t("agent","agente")` / `t("you","tú")`.

- [ ] **Step 1: Write the failing tests**

```cpp
#include "../testfixture.h"
#include "commands.h"
#include "palette.h"
#include "panels.h"
#include "session.h"
#include <QSignalSpy>
#include <QTemporaryDir>
#include <QtTest>
using namespace wb;

class PanelsTest : public QObject {
    Q_OBJECT
private slots:
    void outlinerShowsRowsAndHitboxes() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); Session s(d.path(), nullptr); s.data().reload(); registerAllCommands(s);
        OutlinerPanel o; o.setSession(s); o.refresh();
        QCOMPARE(o.topLevelItemCount(), 2);
        QCOMPARE(o.topLevelItem(1)->text(0), QString("dair"));
        QCOMPARE(o.topLevelItem(1)->childCount(), 2);
        QSignalSpy spy(&o, &OutlinerPanel::hitboxSelected);
        o.setCurrentItem(o.topLevelItem(1)->child(1));
        QCOMPARE(spy.size(), 1); QCOMPARE(spy[0][1].toInt(), 1);
    }
    void inspectorEmitsOnlyChangedFields() {
        InspectorPanel p; HitboxRef h; h.ordinal = 0; h.joint = "FOOT_L"; h.damage = 14; h.size = 2.8;
        p.showHitbox("dair", h);
        QSignalSpy spy(&p, &InspectorPanel::editRequested);
        p.setField("damage", 14);              // unchanged
        QCOMPARE(spy.size(), 0);
        p.setField("damage", 16);
        QCOMPARE(spy.size(), 1);
        QCOMPARE(spy[0][1].value<QJsonObject>()["damage"].toInt(), 16);
        QCOMPARE(spy[0][1].value<QJsonObject>()["row"].toString(), QString("dair"));
    }
    void reviewPanelEnablesActionsOnlyForProposals() {
        ReviewPanel r;
        HistoryEntry a; a.id = 1; a.state = "applied"; a.author = "human"; a.summary = "x";
        HistoryEntry b; b.id = 2; b.state = "proposed"; b.author = "agent"; b.summary = "y";
        r.setHistory({a, b});
        QCOMPARE(r.rowCount(), 2);
        QVERIFY(!r.actionsEnabled(0)); QVERIFY(r.actionsEnabled(1));
        QSignalSpy spy(&r, &ReviewPanel::acceptRequested);
        r.accept(1);
        QCOMPARE(spy[0][0].toInt(), 2);
    }
    void paletteFilterRanksNameMatchesFirst() {
        QVector<CommandSpec> specs;
        CommandSpec a; a.name = "edit_hitbox"; a.description = "Edit one hitbox"; specs << a;
        CommandSpec b; b.name = "list_rows"; b.description = "Rows (hitbox counts)"; specs << b;
        auto f = CommandPalette::filter(specs, "hit");
        QCOMPARE(f.size(), 2); QCOMPARE(f[0].name, QString("edit_hitbox"));
        QCOMPARE(CommandPalette::filter(specs, "zzz").size(), 0);
        QCOMPARE(CommandPalette::filter(specs, "").size(), 2);
        QCOMPARE(CommandPalette::filter(specs, "ehb").size(), 1);   // subsequence of edit_hitbox
    }
    void problemsPanelActivationCarriesRowAndOrdinal() {
        ProblemsPanel p; p.setProblems({{"wrong_limb", "dair", "msg", 0}});
        QSignalSpy spy(&p, &ProblemsPanel::problemActivated);
        p.itemActivated(p.item(0));
        QCOMPARE(spy[0][0].toString(), QString("dair")); QCOMPARE(spy[0][1].toInt(), 0);
    }
};
QTEST_MAIN(PanelsTest)
#include "panels_test.moc"
```

(Add `InspectorPanel::setField(const QString&, const QVariant&)` test hook = the slot the spin boxes call; `ReviewPanel::actionsEnabled(int row)` and `accept(int row)`.)

- [ ] **Step 2: Run to verify failure.**
- [ ] **Step 3: Implement.** Every user-visible literal uses `t("English","Spanish")`; Spanish for new strings may equal the English text per the workspace rule, but give real Spanish where obvious (`t("Problems","Problemas")`, `t("Clips","Clips")`, `t("Accept","Aceptar")`, `t("Reject","Rechazar")`, `t("Undo","Deshacer")`, `t("Redo","Rehacer")`, `t("Fidelity","Fidelidad")`).
- [ ] **Step 4: Run** — `ctest --test-dir _build/wb-qt -R "workbench_panels|launcher_qt_strings" --output-on-failure` and `python tools/release/launcher/check_qt_strings.py`. Expected: pass, zero problems.
- [ ] **Step 5: Commit** — `git commit -m "workbench: outliner, inspector, problems, clips, review panels and command palette"`.

---

### Task 17: Goku project file, acceptance run and docs  (Workspace repo)

**Files:**
- Create: `ports/goku-xv2/workbench.json`, `tools/workbench/acceptance.md`, `tools/workbench/CLAUDE.md`, `docs/workbench.md`, `tools/workbench/mcp_smoke.py`
- Modify: `tools/CLAUDE.md` (one row), `docs/CLAUDE.md` (one row), `ports/goku-xv2/README.md` (one paragraph)

**Interfaces:**
- Consumes: everything above. `ports/goku-xv2/workbench.json` (names and paths only; no data):

```json
{
  "schema": "workbench/1",
  "id": "goku-xv2",
  "gameplay": "gameplay.json",
  "moves_dir": "moves",
  "fidelity": "fidelity.json",
  "plan": "../../_build/goku-xv2/author-source/package/mods/goku-xv2/files/plan.json",
  "mod_id": "goku-xv2",
  "rebuild": ["python", "ports/goku-xv2/tools/build.py", "--fighter", "_build/goku-xv2/author-source/fighter.json"],
  "import_clip": []
}
```

(`rebuild` copied from `ports/goku-xv2/README.md` line 43. `import_clip` stays empty until the retarget lane publishes its CLI; `import_clip` then errors `import_clip not configured` — add that behaviour and test in Task 10's file: empty argv -> that error.)

`plan` path crosses outside the project dir: `FileStore::safeRel` forbids `..`. Resolve this by making `ProjectConfig` accept an optional absolute-or-workspace-relative `plan_abs` read through `QFile` directly (read-only, never written) instead of `FileStore`; implement and test in Task 6 (add a `planAbs` field and a test that `jointForRole` works with `plan_abs` set and `plan` absent). **Edit Task 6 accordingly when executing: fixture keeps `plan`; add a second fixture variant using `plan_abs`.**

- [ ] **Step 1: Write `mcp_smoke.py`** (stdlib only): spawns `gd-melee-launcher --mcp --project <dir>`, sends `initialize`, `tools/list`, then `tools/call list_rows`, asserts the three replies parse and `list_rows` has >= 1 row; used against the synthetic fixture dir created by a tiny `--make-synth` flag in the script (it writes the same files as `testfixture.h` into a temp dir). Run: `python tools/workbench/mcp_smoke.py --exe _build/wb-qt/gd-melee-launcher`. Expected last line `mcp smoke OK`.
- [ ] **Step 2: Write `acceptance.md`** (the owner-watched script; spec "Acceptance"): (1) start the game: `MELEE_SCENE="mode=workbench;p1=geno:goku-xv2/hu;stage=fd" MELEE_CONSOLE_PORT=51726 MELEE_WB_DIR=<dir> ...` (windowed, on screen), launch the Creator on `ports/goku-xv2`; (2) via MCP only: `run_checks`, then for each `wrong_limb` problem `suggest_hitbox_bone` + `edit_hitbox` (3 hitboxes), `rebuild`, `reload`; (3) via MCP only: `list_clips`, `preview_clip`, `assign_clip` for `dair`, `rebuild`, `reload`; (4) quit; play Goku normally (`ports/goku-xv2/tools/play.ps1`) and watch the three hitboxes and dair; (5) record: history ids, the `git diff --stat ports/goku-xv2`, and `python ports/ir/tools/check_hitbox_positions.py` (or `tools/workbench/compare_hitboxes.py`) output. Mark every item owed until a human has watched it.
- [ ] **Step 3: Docs** (`docs/workbench.md`: what it is, the command table from the spec, MCP setup snippet `{"command":"gd-melee-launcher","args":["--mcp","--project","ports/goku-xv2"]}`, data-safety rules, the `workbench.json` schema; no private paths, no disc locations). `tools/workbench/CLAUDE.md` 10 lines. One row each in `tools/CLAUDE.md` and `docs/CLAUDE.md`.
- [ ] **Step 4: Full verification**

```bash
cmake --build _build/wb-qt && ctest --test-dir _build/wb-qt --output-on-failure
python tools/release/launcher/check_qt_strings.py
python -m pytest tools/workbench tools/release/launcher/test_check_qt_strings.py ports/goku-xv2/tests/test_ground_modes.py -q
python tools/check_workspace_paths.py
python tools/port/check_no_disc_text.py
```

Expected: all CTest tests pass (new `workbench_*` plus the existing `launcher_*`), strings check clean, pytest green, the two guards report no findings.

- [ ] **Step 5: Commit** — `git add ports/goku-xv2 tools/workbench docs/workbench.md tools/CLAUDE.md docs/CLAUDE.md && git commit -m "workbench: Goku project file, acceptance script, docs"`.

---

## Self-Review

**Spec coverage.**
- Goal (show / inspect+fix / write back): Tasks 12 (show), 10 (inspect/fix), 6+9 (write back).
- Decisions table: real exe in workbench mode (12); Qt launcher C++17 no Rust (1, 15; Global Constraints); one command registry (5); MCP stdio + localhost (11); animation authoring out of scope (Global Constraints).
- Architecture list: CommandRegistry 5, History 3, GenoData 6, EngineLink 7, Checks 8, McpServer 11, viewport/timeline 15, outliner/inspector/clip/fidelity/problems/history/palette 16, Creator entry behind a toggle 15.
- Game side: `MELEE_SCENE=mode=workbench` (12 Step 6), paused/stepped (12 `wb.frame/step`), offscreen frames (G-b: deliberate deviation, flagged), console transport + `wb.load/row/frame/step/frame_info/render/reload` (12; `wb.reload` limited, flagged), inert unless set and never online (12 gate test).
- v1 commands: Open 10; View 10; Rows/frames 10; Hitboxes 10; Clips 10 (+`import_clip` contract); Ground 14; Checks 8/10; Save group 9. All 29 names asserted in Task 11's list test.
- Data safety: source-only edits (6, 14), snapshots (3), history persistence (3), external changes (3, 5, 9), proposals/accept/reject (3, 9, 16), no committed disc data (fixtures synthetic; Task 17 runs the guards), localhost-only (7, 11).
- Testing: workbench_core CTest on synthetic fighters (all W tasks); game native/scripted test vs hitbox checker (12 Step 10 + 13); MCP list/call-each/schema validation (11); acceptance (17, owed).
- Build order: 1 game (12), 2 core (1-6), 3 EngineLink/viewport/timeline (7, 15), 4 hitbox editing and checks (4, 8, 10), 5 clips (10), 6 MCP (11), 7 ground (14). The plan front-loads MCP before UI because it only needs the registry; allowed by the dependency graph.

**Placeholder scan.** No TBD/TODO. Items that depend on facts not verifiable from the plan are explicit steps with exact commands: the real Fighter field names (12 Step 7 greps), the build file that lists platform TUs (12 files list), how `xv2_to_artist.py` stores HOVER/ANCHORED (14 Step 1), the retarget tool's CLI (configuration; contract in Task 10). Task 6/17 `plan_abs` cross-reference is an explicit edit instruction.

**Type consistency.** `FileChange{path,before,after}`, `HitboxRef/HitboxEdit`, `CommandContext{session,author,propose}`, `Session::commit(ctx, command, args, summary, changes)`, `EngineBackend::call(fn,args,err)`, `FrameInfo` JSON shape (defined in Task 12 Step 4 and mirrored in Task 7), `RowAnalysis/BoneSample/HitboxSample/Problem` used identically in 8 and 10. Role strings are `HAND_R`-style everywhere (source files); `plan.json` roles are `hand.R`-style, mapped only inside `GenoData::jointForRole`.

**Review Focus coverage.** (1) Task 3 `undoRefusesAfterExternalEdit`, Task 5 `commitRefusesWhenFileChangedExternally`, Task 9 `undoReportsExternalChange`. (2) Task 2 `replaceLeavesEveryOtherByteIdentical`, Task 6 `assignClipPatches...KeepingOtherBytes`. (3) Task 4 `unclearedHitboxHasOpenEnd`, `editFramesRefusesWeirdShape`, `noHitboxesOrEmptyText`, `windowsLineEndingsSurvive`; Task 6 `malformedGameplayReportsErrorNotCrash`. (4) Task 7 `timeoutDoesNotHang`, `droppedSocketIsAnErrorNotAHang`, `payloadPathCannotEscapeWbDir`; Task 10 `engineCommandsErrorWithoutEngine`. (5) Task 11 `malformedJsonLine`, `unknownToolAndMethod`, `notificationHasNoResponse`, `callEveryToolWithEmptyArgsNeverCrashes`.

**Known fragile spots for the executor.** Task 2's `jsonInsertKey` indent detection is regex-based; if `insertKeyAppendsWithIndent` fails, fix the finder, not the assertion. Task 12 is the riskiest (game internals, bridge fixpoint); do it first in its own lane and commit early.
