#include "game_exe.h"
#include "../testfixture.h"
#include <QDir>
#include <QFile>
#include <QTemporaryDir>
#include <QtTest>
using namespace wb;

class GameExeTest : public QObject {
    Q_OBJECT
private slots:
    void resolutionOrder() {
        QTemporaryDir d; QVERIFY(d.isValid());
        const QString ws = d.filePath("ws"), project = ws + "/ports/fighter", app = d.filePath("app");
#ifdef Q_OS_WIN
        const QString gameName = "melee-pc.exe";
#else
        const QString gameName = "melee-pc";
#endif
        wbtest::put(ws, ".env", "GW_X=1\n");
        wbtest::put(ws, "_build/" + gameName, "x");
        wbtest::put(app, gameName, "x");
        wbtest::put(project, "workbench.json", "{\"schema\":\"workbench/1\",\"gameplay\":\"g.json\"}");
        QProcessEnvironment env;
        // beside-the-launcher is last; the workspace _build wins over it, found by walking up to .env
        auto found = resolveGameExe({}, env, project, app);
        QCOMPARE(QDir::cleanPath(found.path), QDir::cleanPath(ws + "/_build/" + gameName));
        // GW_ROOT also selects the workspace for a project outside it
        const QString outside = d.filePath("elsewhere/fighter"); QDir().mkpath(outside);
        wbtest::put(outside, ".env", "# isolated fixture workspace\n");
        QCOMPARE(resolveGameExe({}, env, outside, app).path, app + "/" + gameName);
        env.insert("GW_ROOT", ws);
        QCOMPARE(resolveGameExe({}, env, outside, app).path, ws + "/_build/" + gameName);
        // workbench.json engine field beats the workspace default
        wbtest::put(ws, "custom/engine.exe", "x");
        wbtest::put(project, "workbench.json", "{\"schema\":\"workbench/1\",\"gameplay\":\"g.json\",\"engine\":\"custom/engine.exe\"}");
        QVERIFY(resolveGameExe({}, env, project, app).path.endsWith("custom/engine.exe"));
        // GW_ENGINE_EXE beats that; the explicit setting beats everything
        const QString envEngine = d.filePath("env/engine"), settingEngine = d.filePath("set/engine");
        env.insert("GW_ENGINE_EXE", envEngine);
        QCOMPARE(resolveGameExe({}, env, project, app).path, envEngine);
        QCOMPARE(resolveGameExe(settingEngine, env, project, app).path, settingEngine);
        QCOMPARE(resolveGameExe(settingEngine, env, project, app).source.isEmpty(), false);
    }
    void nothingFoundExplainsWhatWasSearched() {
        QTemporaryDir d; QVERIFY(d.isValid());
        wbtest::put(d.path(), ".env", "# isolated fixture workspace\n");
        const auto found = resolveGameExe({}, QProcessEnvironment{}, d.path(), d.path() + "/app");
        QVERIFY(found.path.isEmpty());
        QVERIFY(found.error.contains("melee-pc"));
    }
};
QTEST_MAIN(GameExeTest)
#include "game_exe_test.moc"
