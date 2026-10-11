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
        wbtest::put(ws, ".env", "GW_X=1\n");
        wbtest::put(ws, "_build/melee-pc.exe", "x");
        wbtest::put(app, "melee-pc.exe", "x");
        wbtest::put(project, "workbench.json", "{\"schema\":\"workbench/1\",\"gameplay\":\"g.json\"}");
        QProcessEnvironment env;
        // beside-the-launcher is last; the workspace _build wins over it, found by walking up to .env
        auto found = resolveGameExe({}, env, project, app);
        QCOMPARE(QDir::cleanPath(found.path), QDir::cleanPath(ws + "/_build/melee-pc.exe"));
        // GW_ROOT also selects the workspace for a project outside it
        const QString outside = d.filePath("elsewhere/fighter"); QDir().mkpath(outside);
        wbtest::put(outside, ".env", "# isolated fixture workspace\n");
        QVERIFY(resolveGameExe({}, env, outside, app).path.endsWith("app/melee-pc.exe"));
        env.insert("GW_ROOT", ws);
        QVERIFY(resolveGameExe({}, env, outside, app).path.endsWith("ws/_build/melee-pc.exe"));
        // workbench.json engine field beats the workspace default
        wbtest::put(ws, "custom/engine.exe", "x");
        wbtest::put(project, "workbench.json", "{\"schema\":\"workbench/1\",\"gameplay\":\"g.json\",\"engine\":\"custom/engine.exe\"}");
        QVERIFY(resolveGameExe({}, env, project, app).path.endsWith("custom/engine.exe"));
        // GW_ENGINE_EXE beats that; the explicit setting beats everything
        env.insert("GW_ENGINE_EXE", "C:/env/engine.exe");
        QCOMPARE(resolveGameExe({}, env, project, app).path, QString("C:/env/engine.exe"));
        QCOMPARE(resolveGameExe("D:/set/engine.exe", env, project, app).path, QString("D:/set/engine.exe"));
        QCOMPARE(resolveGameExe("D:/set/engine.exe", env, project, app).source.isEmpty(), false);
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
