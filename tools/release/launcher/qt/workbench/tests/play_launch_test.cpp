#include "play_launch.h"
#include "../testfixture.h"
#include <QTemporaryDir>
#include <QtTest>
using namespace wb;

class PlayLaunchTest : public QObject {
    Q_OBJECT
private slots:
    void currentMoveAndPathsStaySeparateArguments() {
        QTemporaryDir dir;
        wbtest::put(dir.path(), ".git", "gitdir: unused");
        wbtest::put(dir.path(), "tools/geno/play.py", "# synthetic, never executed");
        const auto project = dir.filePath("ports/second fighter");
        QVERIFY(QDir().mkpath(project));
        QProcessEnvironment env; env.insert("GW_PYTHON", "Python path with spaces");
        const auto c = playCommand(project, false, "jab1", env);
        QVERIFY(c.error.isEmpty()); QCOMPARE(c.program, QString("Python path with spaces"));
        QCOMPARE(c.workingDir, dir.path());
        QCOMPARE(c.args, QStringList({dir.filePath("tools/geno/play.py"), "--project", project,
            "--lab", "--clip", "jab1", "--json"}));
    }
    void vsCpuDoesNotOpenFrozenClips() {
        QTemporaryDir dir;
        wbtest::put(dir.path(), ".git", "gitdir: unused");
        wbtest::put(dir.path(), "tools/geno/play.py", "# synthetic");
        QProcessEnvironment env; env.insert("GW_PYTHON", "python");
        const auto c = playCommand(dir.path(), true, "jab1", env);
        QVERIFY(c.error.isEmpty()); QVERIFY(c.args.contains("--vs")); QVERIFY(c.args.contains("cpu"));
        QVERIFY(!c.args.contains("--clip")); QVERIFY(!c.args.contains("--lab"));
    }
    void emptyRowStillOpensLab() {
        QTemporaryDir dir;
        wbtest::put(dir.path(), ".git", "gitdir: unused");
        wbtest::put(dir.path(), "tools/geno/play.py", "# synthetic");
        QProcessEnvironment env; env.insert("GW_PYTHON", "python");
        const auto c = playCommand(dir.path(), false, {}, env);
        QVERIFY(c.error.isEmpty()); QVERIFY(!c.args.contains("--clip"));
    }
    void missingToolOrPythonHasNoRunnableCommand() {
        QTemporaryDir dir; QProcessEnvironment env; env.insert("GW_PYTHON", "python");
        auto c = playCommand(dir.path(), false, "jab1", env);
        QVERIFY(!c.error.isEmpty()); QVERIFY(c.program.isEmpty());
        wbtest::put(dir.path(), ".git", "gitdir: unused");
        wbtest::put(dir.path(), "tools/geno/play.py", "# synthetic");
        c = playCommand(dir.path(), false, "jab1", QProcessEnvironment{});
        QVERIFY(!c.error.isEmpty()); QVERIFY(c.args.isEmpty());
    }
    void nearestWorktreeKeepsItsOwnPlayTool() {
        QTemporaryDir dir;
        wbtest::put(dir.path(), ".git", "gitdir: unused");
        wbtest::put(dir.path(), "tools/geno/play.py", "# outer");
        wbtest::put(dir.path(), "worktrees/lab/.git", "gitdir: unused");
        QVERIFY(QDir().mkpath(dir.filePath("worktrees/lab/ports/second")));
        QProcessEnvironment env; env.insert("GW_PYTHON", "python");
        const auto project = dir.filePath("worktrees/lab/ports/second");
        QVERIFY(!playCommand(project, false, "jab1", env).error.isEmpty());
        wbtest::put(dir.path(), "worktrees/lab/tools/geno/play.py", "# inner");
        QCOMPARE(playCommand(project, false, "jab1", env).workingDir, dir.filePath("worktrees/lab"));
    }
};
QTEST_GUILESS_MAIN(PlayLaunchTest)
#include "play_launch_test.moc"
