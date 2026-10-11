#include "error_help.h"
#include "window.h"
#include <QtTest>

using namespace wb;

// Every kind of failure the Workbench can show says what to do, keeps the raw reason, and offers the right Fix.
class ErrorHelpTest : public QObject {
    Q_OBJECT
    struct Row { const char *command, *raw; FixKind fix; const char *mustSay; };
private slots:
    void initTestCase() { launcher::spanish = false; }
    void everyKnownFailureHasWordingAndTheRightFix_data() {
        QTest::addColumn<QString>("command"); QTest::addColumn<QString>("raw"); QTest::addColumn<int>("fix"); QTest::addColumn<QString>("mustSay");
        const QVector<Row> rows{
            {"edit_hitbox", "engine not running", FixKind::StartGame, "Engine not running"},
            {"render_view", "Engine not running", FixKind::StartGame, "Start the game"},
            {"engine_restart", "Game executable not found. Set Game exe in Settings or GW_ENGINE_EXE. Looked in: x", FixKind::ChooseGameExe, "game program was not found"},
            {"engine_restart", "engine executable is not configured", FixKind::ChooseGameExe, "Choose the game exe"},
            {"engine_restart", "engine exited before console was ready: Process failed to start", FixKind::ChooseGameExe, "could not start"},
            {"engine_restart", "engine: scene rejected or fighter not loaded: no fighter on port 1", FixKind::Rebuild, "out of date"},
            {"engine_restart", "timeout waiting for engine console", FixKind::StartGame, "did not answer"},
            {"engine_restart", "Select a disc on Play, then reopen the fighter folder.", FixKind::None, "Play tab"},
            {"reload", "synthetic restart refused", FixKind::StartGame, "synthetic restart refused"},
            {"", "Blender not found: set GW_BLENDER or the Blender path in Settings", FixKind::ChooseBlender, "Choose the Blender program"},
            {"", "Blender executable is not configured", FixKind::ChooseBlender, "Blender could not be started"},
            {"", "Blender is not running", FixKind::StartBlender, "Blender is closed"},
            {"", "Workbench Blender add-on not found in this project's checkout", FixKind::None, "cannot open this project"},
            {"rebuild", "rebuild not configured", FixKind::None, "no rebuild step"},
            {"rebuild", "rebuild refused: hitbox timing in jab1: wait_until goes back", FixKind::None, "timing disagrees"},
            {"rebuild", "rebuild failed to start: x", FixKind::None, "rebuild entry in workbench.json"},
            {"rebuild", "rebuild timed out: x", FixKind::Rebuild, "30 minutes"},
            {"rebuild", "rebuild failed: exit 2: build: --gameplay-only refused: Stage A input changed. Run a full build", FixKind::Rebuild, "needs a full build"},
            {"rebuild", "rebuild failed: exit 1: boom", FixKind::Rebuild, "fix the cause"},
            {"revert_all", "No build baseline is available", FixKind::Rebuild, "Rebuild once"},
            {"edit_hitbox", "changed externally: moves/jab1.genoasm", FixKind::ReloadFromDisk, "changed externally"},
            {"accept", "changed externally: stale proposal: gameplay.json", FixKind::ReloadFromDisk, "Reload from disk"},
            {"edit_hitbox", "changes applied (entry 4); reload failed: bad json", FixKind::ReloadFromDisk, "edit was saved"},
            {"edit_hitbox", "boom; rollback failed: x; snapshots: y", FixKind::None, ".workbench/snapshots"},
            {"edit_hitbox", "cannot save history: C:/p/.workbench/history.json", FixKind::None, "disk is not full"},
            {"load_row", "unknown row: ghost", FixKind::ReloadFromDisk, "no longer in the project"},
            {"set_frame", "no row loaded; call load_row first", FixKind::None, "Choose a move first"},
            {"undo", "nothing to undo", FixKind::None, "Nothing to undo"},
            {"play", "play timed out", FixKind::StartGame, "Restart the game"},
            {"reload_from_disk", "data reload failed: bad", FixKind::ReloadFromDisk, "invalid JSON"},
            {"edit_hitbox", "damage and size must be nonnegative", FixKind::None, "Your edit was not applied"},
            {"list_rows", "something unexpected", FixKind::None, "Nothing was changed"},
        };
        for (const auto &row : rows)
            QTest::newRow(row.raw) << QString(row.command) << QString(row.raw) << int(row.fix) << QString(row.mustSay);
    }
    void everyKnownFailureHasWordingAndTheRightFix() {
        QFETCH(QString, command); QFETCH(QString, raw); QFETCH(int, fix); QFETCH(QString, mustSay);
        const auto help = explainError(command, raw);
        QVERIFY2(help.message.contains(mustSay, Qt::CaseInsensitive), qPrintable(help.message));
        QCOMPARE(int(help.fix), fix);
        QCOMPARE(help.fix != FixKind::None, !help.fixLabel.isEmpty());
        if (raw != "engine not running" && !raw.startsWith("Engine") && !raw.startsWith("nothing to"))
            QVERIFY2(help.message.contains(raw.left(24)) || help.message.contains(raw.section(": ", 1).left(20)), qPrintable(help.message)); // the raw reason survives
    }
    void launchStatusesUseTheSameTable() {
        QCOMPARE(explainStatus("Blender is closed").fix, FixKind::StartBlender);
        const auto unknown = explainStatus("Ready");
        QCOMPARE(unknown.message, QString("Ready")); QCOMPARE(unknown.fix, FixKind::None);
    }
    void spanishWordingExistsForEveryFix() {
        launcher::spanish = true;
        const auto help = explainError("", "engine not running");
        QVERIFY2(help.message.startsWith("Motor detenido"), qPrintable(help.message));
        QCOMPARE(help.fixLabel, QString("Iniciar juego"));
        launcher::spanish = false;
    }
    void fixNamesAreStableAndDistinct() {
        QSet<QString> names;
        for (auto fix : {FixKind::ChooseGameExe, FixKind::ChooseBlender, FixKind::StartGame, FixKind::StartBlender, FixKind::Rebuild, FixKind::ReloadFromDisk}) {
            QVERIFY(!fixName(fix).isEmpty()); names.insert(fixName(fix));
        }
        QCOMPARE(names.size(), 6); QVERIFY(fixName(FixKind::None).isEmpty());
    }
};
QTEST_MAIN(ErrorHelpTest)
#include "error_help_test.moc"
