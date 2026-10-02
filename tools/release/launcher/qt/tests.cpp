#include "launcher_core.h"
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QProcess>
#include <QTemporaryDir>
#include <QtEndian>
#include <QtTest>
#include <stdexcept>
#ifdef Q_OS_WIN
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#endif
using namespace launcher;

static QString canonicalPath(const QString &path) {
#ifdef Q_OS_WIN
    // QFileInfo's canonical path preserves 8.3 spelling. Expand it before
    // comparing a legacy-game path against its original Unicode spelling.
    auto native = QDir::toNativeSeparators(QFileInfo(path).absoluteFilePath());
    wchar_t expanded[32768];
    auto n = GetLongPathNameW(reinterpret_cast<LPCWSTR>(native.utf16()), expanded, 32768);
    if (!n || n >= 32768) return {};
    return QFileInfo(QString::fromWCharArray(expanded, n)).canonicalFilePath().toCaseFolded();
#else
    return QFileInfo(path).canonicalFilePath();
#endif
}

static QString fixture(const QString &dir, const QStringList &names = {}, const QByteArray &title = "Super Smash Bros Melee") {
    QByteArray data(0x440, '\0'); data.replace(0, 6, "GALE01"); data[7] = 2;
    qToBigEndian<quint32>(0xc2339f3d, data.data() + 0x1c); data.replace(0x20, title.size(), title);
    QByteArray fst((names.size() + 1) * 12, '\0'); fst[0] = 1; qToBigEndian<quint32>(names.size() + 1, fst.data() + 8);
    QByteArray strings; int i = 1;
    for (auto name : names) { qToBigEndian<quint32>(strings.size(), fst.data() + i * 12); strings += name.toUtf8() + '\0'; ++i; }
    fst += strings; qToBigEndian<quint32>(0x440, data.data() + 0x424); qToBigEndian<quint32>(fst.size(), data.data() + 0x428);
    auto path = dir + "/disc ü with spaces.iso"; writeAtomic(path, data + fst); return path;
}
class Tests : public QObject {
    Q_OBJECT
private slots:
    void discDetection() {
        QTemporaryDir d;
        auto path = fixture(d.path(), {"MxDt.dat", "AltSlippiCSS.dat"}, "Super Smash Bros. Melee: Akaneia");
        QCOMPARE(probeDisc(path).kind, "ACE (m-ex mod)"); QCOMPARE(probeDisc(path).verdict, DiscInfo::Good);
        path = fixture(d.path(), {"MxDt.dat"}, "Super Smash Bros. Melee: Akaneia"); QCOMPARE(probeDisc(path).kind, "Akaneia (m-ex mod)");
        QStringList vanilla; for (int i = 0; i < 1211; ++i) vanilla << QString::number(i);
        path = fixture(d.path(), vanilla); QCOMPARE(probeDisc(path).kind, "Melee 1.02 (vanilla)");
    }
    void damagedDiscs() {
        QTemporaryDir d; auto path = fixture(d.path(), {"MxDt.dat"});
        QFile f(path); QVERIFY(f.open(QIODevice::ReadWrite)); auto bytes = f.readAll();
        auto mutate = [&](const QByteArray &b) { f.resize(0); f.seek(0); f.write(b); f.flush(); QCOMPARE(probeDisc(path).verdict, DiscInfo::Bad); };
        auto bad = bytes; bad[7] = 1; mutate(bad);
        bad = bytes; bad[3] = 'P'; mutate(bad);
        bad = bytes; qToBigEndian<quint32>(0xffffffff, bad.data() + 0x424); mutate(bad);
        bad = bytes; qToBigEndian<quint32>(0xffffffff, bad.data() + 0x448); mutate(bad);
        bad = bytes; bad[bad.size() - 1] = 'x'; mutate(bad);
        bad = bytes; qToBigEndian<quint32>(0xfffffffe, bad.data() + 0x450); qToBigEndian<quint32>(32, bad.data() + 0x454); mutate(bad);
        mutate(QByteArray("RVZ\1test"));
    }
    void legacyMigrationAndSaveIdentity() {
        QTemporaryDir d;
        QByteArray legacy = "# old launcher\ndefault=my-ace\nvolume=73\nlanguage=es\nfuture_option=keep\ndisc=my-ace|My ACE|ACE (m-ex mod)|C:\\Games\\ACE.iso\n";
        writeAtomic(d.path() + "/launcher.cfg", legacy);
        auto s = Settings::load(d.path()); QCOMPARE(s.discs.size(), 1); QCOMPARE(s.defaultId, "my-ace"); QCOMPARE(s.option("volume"), "73");
        s.discs[0].path = d.path() + "/different | disc ü.iso"; s.discs[0].name = "Renamed"; s.save(d.path());
        auto loaded = Settings::load(d.path()); QCOMPARE(loaded.discs[0].id, "my-ace"); QCOMPARE(loaded.discs[0].path, s.discs[0].path);
        QCOMPARE(loaded.option("future_option"), "keep"); QCOMPARE(readText(d.path() + "/launcher.cfg").toUtf8(), legacy);
        writeAtomic(d.path() + "/launcher.json", "broken"); QVERIFY_EXCEPTION_THROWN(Settings::load(d.path()), std::runtime_error);
    }
    void rejectTraversal() {
        QVERIFY(!safeId("../escape")); QVERIFY(!safeId("a/b")); QVERIFY(!safeId("..")); QVERIFY(safeId("my-mod_1.2"));
        QTemporaryDir d; writeAtomic(d.path() + "/launcher.cfg", "disc=../outside|name|kind|path\n");
        QVERIFY_EXCEPTION_THROWN(Settings::load(d.path()), std::runtime_error);
        QVERIFY_EXCEPTION_THROWN(removeMod(d.path(), "../outside"), std::runtime_error);
    }
    void installedModRules() {
        QTemporaryDir d;
        writeAtomic(d.path() + "/base/mod.json", "{\"name\":\"Base\"}");
        writeAtomic(d.path() + "/addon/mod.json", "{\"requires\":[\"base\"]}");
        QCOMPARE(installedMods(d.path()).size(), 2); QVERIFY(installedMods(d.path())[0].enabled);
        QVERIFY_EXCEPTION_THROWN(setModEnabled(d.path(), "base", false), std::runtime_error);
        setModEnabled(d.path(), "addon", false); setModEnabled(d.path(), "base", false);
        QVERIFY_EXCEPTION_THROWN(setModEnabled(d.path(), "addon", true), std::runtime_error);
        setModEnabled(d.path(), "base", true); setModEnabled(d.path(), "addon", true);
        writeAtomic(d.path() + "/rival/mod.json", "{\"conflicts\":[\"base\"]}");
        QVERIFY_EXCEPTION_THROWN(setModEnabled(d.path(), "rival", true), std::runtime_error);
        removeMod(d.path(), "addon"); QVERIFY(!QDir(d.path() + "/addon").exists()); QVERIFY(QDir(d.path() + "/.removed").exists());
        QVERIFY(QDir(d.path() + "/base").exists());
    }
    void launchArgumentsAndEnvironment() {
        QTemporaryDir d; auto app = d.path() + "/game with spaces"; auto user = d.path() + "/profile ü";
        QDir().mkpath(app);
#ifdef Q_OS_WIN
        auto exe = app + "/melee-pc.exe";
#else
        auto exe = app + "/melee";
#endif
        QVERIFY(QFile::copy(QCoreApplication::applicationFilePath(), exe));
        writeAtomic(app + "/ui/manifest.json", "{}");
        auto iso = fixture(d.path(), {"MxDt.dat"}, "Akaneia");
        Settings settings; settings.options["volume"] = "77"; settings.options["unlock_all"] = "0"; settings.options["traces"] = "card,fps";
        Disc disc{"my-disc", "Test", "Akaneia", iso};
        qputenv("MELEE_NETPLAY", "host"); qputenv("MELEE_SCENE", "unwanted"); qputenv("MELEE_INPUT", "keyboard");
        auto spec = prepareLaunch(app, user, settings, disc);
        QCOMPARE(spec.arguments.size(), 2); QCOMPARE(spec.arguments[0], "--iso");
        QCOMPARE(spec.environment.value("MELEE_VOLUME"), "77"); QVERIFY(!spec.environment.contains("MELEE_UNLOCK_ALL"));
        QVERIFY(!spec.environment.contains("MELEE_NETPLAY")); QVERIFY(!spec.environment.contains("MELEE_SCENE")); QVERIFY(!spec.environment.contains("MELEE_INPUT"));
        QCOMPARE(spec.environment.value("MELEE_CARD_DIAG"), "1"); QCOMPARE(spec.environment.value("MELEE_SHOW_FPS"), "1");
        QVERIFY(QDir(user + "/saves/my-disc").exists());
        // Actually start a child with the launch spec. This catches quoting and Unicode regressions.
        spec.environment.insert("LAUNCHER_TEST_CHILD", "1");
        spec.environment.insert("LAUNCHER_TEST_OUTPUT", d.path() + "/child.json");
        // The test child itself uses Qt, unlike the game. Keep its native runtime for this test.
        spec.environment.remove("LD_LIBRARY_PATH");
        QProcess process; process.setProgram(spec.program); process.setArguments(spec.arguments); process.setWorkingDirectory(spec.workingDirectory); process.setProcessEnvironment(spec.environment);
        process.start(); QVERIFY2(process.waitForStarted(), qPrintable(process.errorString())); QVERIFY(process.waitForFinished(10000)); QCOMPARE(process.exitStatus(), QProcess::NormalExit); QCOMPARE(process.exitCode(), 0);
        auto report = QJsonDocument::fromJson(readText(d.path() + "/child.json").toUtf8()).object();
        auto received = report["args"].toArray(); QCOMPARE(received.size(), 3); QCOMPARE(received[1].toString(), "--iso");
        QVERIFY(!canonicalPath(iso).isEmpty());
        QCOMPARE(canonicalPath(received[2].toString()), canonicalPath(iso));
        QVERIFY(!canonicalPath(user + "/saves/my-disc").isEmpty());
        QCOMPARE(canonicalPath(report["card"].toString()), canonicalPath(user + "/saves/my-disc"));
        QCOMPARE(canonicalPath(report["cwd"].toString()), canonicalPath(spec.workingDirectory));
        auto second = prepareLaunch(app, user, settings, disc); QVERIFY(second.workingDirectory != spec.workingDirectory);
        QCOMPARE(second.environment.value("MELEE_CARD_PATH"), spec.environment.value("MELEE_CARD_PATH"));
        qunsetenv("MELEE_NETPLAY"); qunsetenv("MELEE_SCENE"); qunsetenv("MELEE_INPUT");
    }
    void crashClassification() {
        QTemporaryDir d;
        writeAtomic(d.path() + "/crashlogs/crash-1.log", "==== GD's Melee crash report ====\nduring shutdown: yes\n");
        QVERIFY(latestCrash(d.path()).isEmpty());
        writeAtomic(d.path() + "/crashlogs/crash-2-full.log", "full log"); QVERIFY(latestCrash(d.path()).isEmpty());
        writeAtomic(d.path() + "/crashlogs/crash-3.log", "==== GD's Melee crash report ====\nduring shutdown: no\n");
        QVERIFY(latestCrash(d.path()).endsWith("crash-3.log"));
    }
};
int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    if (qEnvironmentVariableIsSet("LAUNCHER_TEST_CHILD")) {
        QJsonArray args; for (const auto &arg : app.arguments()) args.append(arg);
        writeAtomic(qEnvironmentVariable("LAUNCHER_TEST_OUTPUT"), QJsonDocument(QJsonObject{{"args", args}, {"cwd", QDir::currentPath()}, {"card", qEnvironmentVariable("MELEE_CARD_PATH")}}).toJson());
        return 0;
    }
    Tests tests; return QTest::qExec(&tests, argc, argv);
}
#include "tests.moc"
