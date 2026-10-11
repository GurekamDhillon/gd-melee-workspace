#include "blender_launch.h"
#include "../testfixture.h"
#include <QFile>
#include <QTemporaryDir>
#include <QtTest>
using namespace wb;

class BlenderLaunchTest : public QObject {
    Q_OBJECT
private slots:
    void findBlenderOrder() {
        QTemporaryDir dir; QVERIFY(dir.isValid());
#ifdef Q_OS_WIN
        const QString binary = dir.filePath("blender.exe");
#else
        const QString binary = dir.filePath("blender");
#endif
        wbtest::put(dir.path(), QFileInfo(binary).fileName(), "synthetic executable; never run");
        QVERIFY(QFile::setPermissions(binary, QFileDevice::ReadOwner | QFileDevice::WriteOwner | QFileDevice::ExeOwner));
        QProcessEnvironment env; env.insert("PATH", dir.path()); env.insert("GW_BLENDER", "env Blender");
        QCOMPARE(findBlender("settings Blender", env), QString("settings Blender"));
        QCOMPARE(findBlender("", env), QString("env Blender"));
        env.remove("GW_BLENDER");
        QCOMPARE(QDir::cleanPath(findBlender("", env)), QDir::cleanPath(binary));
        env.insert("PATH", ""); QVERIFY(findBlender("", env).isEmpty());
        QVERIFY(findBlender("  ", QProcessEnvironment{}).isEmpty());
        env.insert("GW_BLENDER", " \t"); QVERIFY(findBlender("", env).isEmpty());
    }
    void findAddonDir() {
        QTemporaryDir dir; QVERIFY(dir.isValid());
        QVERIFY(QDir().mkpath(dir.filePath(".git")));
        wbtest::put(dir.path(), "tools/blender/geno_workbench/bootstrap.py", "# synthetic\n");
        QVERIFY(QDir().mkpath(dir.filePath("ports/synth/nested")));
        QCOMPARE(wb::findAddonDir(dir.filePath("ports/synth/nested")), dir.filePath("tools/blender/geno_workbench"));
        QTemporaryDir outside; wbtest::put(outside.path(), ".git", "gitdir: unused");
        QVERIFY(wb::findAddonDir(outside.path()).isEmpty());
        QVERIFY(QFile::remove(dir.filePath("tools/blender/geno_workbench/bootstrap.py")));
        QVERIFY(wb::findAddonDir(dir.filePath("ports/synth")).isEmpty());
    }
    void worktreeGitFileIsTheNearestBoundary() {
        QTemporaryDir dir;
        QVERIFY(QDir().mkpath(dir.filePath(".git")));
        wbtest::put(dir.path(), "tools/blender/geno_workbench/bootstrap.py", "# outer\n");
        wbtest::put(dir.path(), "worktrees/hub/.git", "gitdir: unused\n");
        QVERIFY(QDir().mkpath(dir.filePath("worktrees/hub/ports/synth")));
        const QString project = dir.filePath("worktrees/hub/ports/synth");
        QVERIFY(wb::findAddonDir(project).isEmpty());
        wbtest::put(dir.path(), "worktrees/hub/tools/blender/geno_workbench/bootstrap.py", "# inner\n");
        QCOMPARE(wb::findAddonDir(project), dir.filePath("worktrees/hub/tools/blender/geno_workbench"));
    }
    void blenderCommandShape() {
        QTemporaryDir dir;
        const QString addon = dir.filePath("add on"), project = dir.filePath("fighter with spaces");
        QVERIFY(QDir().mkpath(project)); wbtest::put(addon, "bootstrap.py", "# synthetic\n");
        const auto cmd = blenderCommand("Blender path", addon, project, 1234);
        QVERIFY(cmd.error.isEmpty()); QCOMPARE(cmd.program, QString("Blender path"));
        QCOMPARE(cmd.args, QStringList({"--python", addon + "/bootstrap.py", "--", "--project", project, "--port", "1234"}));
    }
    void artArgumentResolvesAgainstWorkspace() {
        QTemporaryDir dir;
        wbtest::put(dir.path(), ".git", "gitdir: unused\n");
        const QString addon = dir.filePath("tools/blender/geno_workbench");
        const QString project = dir.filePath("ports/synth");
        QVERIFY(QDir().mkpath(project)); wbtest::put(addon, "bootstrap.py", "# synthetic\n");
        wbtest::put(dir.path(), "art/fighter with spaces.blend", "synthetic path fixture, never opened");
        const auto cmd = blenderCommand("Blender", addon, project, 1234, "art/fighter with spaces.blend");
        QVERIFY(cmd.error.isEmpty());
        QCOMPARE(cmd.args, QStringList({"--python", addon + "/bootstrap.py", "--", "--project", project,
            "--port", "1234", "--art", dir.filePath("art/fighter with spaces.blend")}));
        const auto absolute = blenderCommand("Blender", addon, project, 1234, dir.filePath("art/fighter with spaces.blend"));
        QCOMPARE(absolute.args, cmd.args);
    }
    void artAtFixtureRootIsProjectRelative() {
        QTemporaryDir dir;
        wbtest::put(dir.path(), ".git", "gitdir: unused"); // keep ancestor checkouts out of this fixture
        wbtest::put(dir.path(), "addon/bootstrap.py", "# synthetic\n");
        wbtest::put(dir.path(), "fighter.glb", "synthetic path fixture, never opened");
        const auto cmd = blenderCommand("Blender", dir.filePath("addon"), dir.path(), 1234, "fighter.glb");
        QVERIFY(cmd.error.isEmpty()); QCOMPARE(cmd.args.last(), dir.filePath("fighter.glb"));
    }
    void invalidLaunchHasNoRunnableCommand() {
        QTemporaryDir dir; wbtest::put(dir.path(), "bootstrap.py", "# synthetic\n");
        const QList<BlenderCommand> bad = {
            blenderCommand("", dir.path(), dir.path(), 1234),
            blenderCommand("Blender", dir.filePath("missing"), dir.path(), 1234),
            blenderCommand("Blender", dir.path(), dir.filePath("missing"), 1234),
            blenderCommand("Blender", dir.path(), dir.path(), 0),
            blenderCommand("Blender", dir.path(), dir.path(), 1234, "missing.blend")
        };
        for (const auto &cmd : bad) { QVERIFY(!cmd.error.isEmpty()); QVERIFY(cmd.program.isEmpty()); QVERIFY(cmd.args.isEmpty()); }
    }
};
QTEST_GUILESS_MAIN(BlenderLaunchTest)
#include "blender_launch_test.moc"
