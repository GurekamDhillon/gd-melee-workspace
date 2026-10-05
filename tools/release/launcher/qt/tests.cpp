#include "launcher_core.h"
#include "diagnostics.h"
#include <QBuffer>
#include <functional>
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

// A minimal but real ELF image: header, PT_INTERP (optional), PT_LOAD over the whole file, PT_DYNAMIC with DT_NEEDED entries.
static QByteArray elfFixture(int bits, const QString &interp, const QStringList &needed, quint16 machine = 3, const QStringList &runpath = {}) {
    const bool is64 = bits == 64; const int eh = is64 ? 64 : 52, ph = is64 ? 56 : 32, nph = interp.isEmpty() ? 2 : 3, word = is64 ? 8 : 4;
    QByteArray strtab(1, '\0'); QVector<int> needOff;
    for (const auto &n : needed) { needOff << strtab.size(); strtab += n.toUtf8() + '\0'; }
    int runOff = -1; if (!runpath.isEmpty()) { runOff = strtab.size(); strtab += runpath.join(':').toUtf8() + '\0'; }
    const QByteArray interpBytes = interp.isEmpty() ? QByteArray() : interp.toUtf8() + '\0';
    const int interpOff = eh + ph * nph, strOff = interpOff + interpBytes.size(), entries = needed.size() + (runOff >= 0 ? 1 : 0) + 3;
    const int dynOff = (strOff + strtab.size() + 7) & ~7, dynSize = entries * 2 * word, total = dynOff + dynSize; const quint64 base = 0x08048000;
    QByteArray f(total, '\0');
    auto put = [&](int off, quint64 v, int n) { for (int i = 0; i < n; ++i) f[off + i] = char((v >> (8 * i)) & 0xff); };
    memcpy(f.data(), "\x7f" "ELF", 4); f[4] = is64 ? 2 : 1; f[5] = 1; f[6] = 1;
    put(16, 2, 2); put(18, machine, 2); put(20, 1, 4);
    if (is64) { put(32, eh, 8); put(52, eh, 2); put(54, ph, 2); put(56, nph, 2); } else { put(28, eh, 4); put(40, eh, 2); put(42, ph, 2); put(44, nph, 2); }
    int p = eh;
    auto phdr = [&](quint32 type, quint64 off, quint64 size) {
        put(p, type, 4);
        if (is64) { put(p + 8, off, 8); put(p + 16, base + off, 8); put(p + 32, size, 8); put(p + 40, size, 8); }
        else { put(p + 4, off, 4); put(p + 8, base + off, 4); put(p + 16, size, 4); put(p + 20, size, 4); }
        p += ph;
    };
    if (nph == 3) phdr(3, interpOff, interpBytes.size());
    phdr(1, 0, total); phdr(2, dynOff, dynSize);
    memcpy(f.data() + interpOff, interpBytes.constData(), interpBytes.size()); memcpy(f.data() + strOff, strtab.constData(), strtab.size());
    int i = 0; auto dyn = [&](quint64 tag, quint64 val) { put(dynOff + i * 2 * word, tag, word); put(dynOff + i * 2 * word + word, val, word); ++i; };
    for (int off : needOff) dyn(1, off);
    if (runOff >= 0) dyn(29, runOff);
    dyn(5, base + strOff); dyn(10, strtab.size()); dyn(0, 0);
    return f;
}
static ElfInfo readElfFixture(QByteArray bytes) { QBuffer b(&bytes); b.open(QIODevice::ReadOnly); return readElf(b); }
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
    void enabledFileCommentsMatchTheEngine() {
        QTemporaryDir d;
        writeAtomic(d.path() + "/foo/mod.json", "{}");
        writeAtomic(d.path() + "/bar/mod.json", "{}");
        writeAtomic(d.path() + "/enabled.txt", "\xef\xbb\xbf# saved selection\n foo # keep this mod\nbar\n");
        auto mods = installedMods(d.path());
        QCOMPARE(mods.size(), 2); QVERIFY(mods[0].enabled); QVERIFY(mods[1].enabled);
        setModEnabled(d.path(), "bar", false);
        QCOMPARE(readText(d.path() + "/enabled.txt"), "# Enabled mods for the next launch\nfoo\n");
    }
    void rejectRequirementCyclesWithoutChangingTheSelection() {
        QTemporaryDir d;
        writeAtomic(d.path() + "/a/mod.json", "{\"requires\":[\"b\"]}");
        writeAtomic(d.path() + "/b/mod.json", "{\"requires\":[\"a\"]}");
        QVERIFY_EXCEPTION_THROWN(setModEnabled(d.path(), "a", true), std::runtime_error);
        QVERIFY(!QFile::exists(d.path() + "/enabled.txt"));
    }
    void disablingInvalidCycleCanRecoverItsDependents() {
        QTemporaryDir d;
        writeAtomic(d.path() + "/a/mod.json", "{\"requires\":[\"b\"]}");
        writeAtomic(d.path() + "/b/mod.json", "{\"requires\":[\"a\"]}");
        writeAtomic(d.path() + "/child/mod.json", "{\"requires\":[\"a\"]}");
        writeAtomic(d.path() + "/unrelated/mod.json", "{}");
        setModEnabled(d.path(), "a", false);
        auto mods = installedMods(d.path());
        for (const auto &m : mods) QCOMPARE(m.enabled, m.id == "unrelated");
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
    // ---- launch diagnostics ------------------------------------------------------------------
    void elfReader() {
        for (int bits : {32, 64}) {
            auto bytes = elfFixture(bits, "/lib/ld-linux.so.2", {"libvulkan.so.1", "libc.so.6"}, bits == 32 ? 3 : 62, {"$ORIGIN/../lib"});
            QBuffer b(&bytes); QVERIFY(b.open(QIODevice::ReadOnly));
            auto e = readElf(b);
            QVERIFY2(e.valid, qPrintable(e.error)); QCOMPARE(e.bits, bits); QCOMPARE(e.machine, quint16(bits == 32 ? 3 : 62));
            QCOMPARE(e.interpreter, QString("/lib/ld-linux.so.2")); QCOMPARE(e.needed, QStringList({"libvulkan.so.1", "libc.so.6"}));
            QCOMPARE(e.runpath, QStringList({"$ORIGIN/../lib"})); QVERIFY(e.dynamic);
            QBuffer h(&bytes); QVERIFY(h.open(QIODevice::ReadOnly)); QVERIFY(readElf(h, true).valid);
        }
    }
    void elfReaderRejectsDamage() {
        auto good = elfFixture(32, "/lib/ld-linux.so.2", {"libc.so.6"});
        auto parse = [](QByteArray bytes) { QBuffer b(&bytes); b.open(QIODevice::ReadOnly); return readElf(b); };
        auto cut = parse(good.left(good.size() - 6));   // inside the dynamic section
        QVERIFY(cut.isElf); QVERIFY(!cut.valid); QCOMPARE(cut.bits, 32); QVERIFY(!cut.error.isEmpty());
        auto header = parse(good.left(40)); QVERIFY(header.isElf); QVERIFY(!header.valid);
        auto phdrs = parse(good.left(60)); QVERIFY(phdrs.isElf); QVERIFY(!phdrs.valid); QVERIFY(phdrs.error.contains("program headers"));
        auto script = parse("#!/bin/sh\nexit 0\n"); QVERIFY(!script.isElf); QVERIFY(script.error.contains("not an ELF"));
        auto tiny = parse("ab"); QVERIFY(!tiny.isElf); QVERIFY(!tiny.valid);
        auto weird = good; weird[4] = 9; QVERIFY(!parse(weird).valid);
        QVERIFY(!readElf(QString("/definitely/not/here")).valid);
    }
    void neededResolutionIgnoresWrongClass() {
        QTemporaryDir d; const auto root = d.path();
        auto put = [&](const QString &rel, int bits) { writeAtomic(root + "/" + rel, elfFixture(bits, {}, {}, bits == 32 ? 3 : 62)); };
        put("lib32/libvulkan.so.1", 32); put("usr/lib/libz.so.1", 64);   // Arch: the 64-bit libz is in /usr/lib
        put("bundle/lib/libSDL.so", 32); put("app/lib/libfoo.so", 32); QDir().mkpath(root + "/app/bin");
        auto exe = readElfFixture(elfFixture(32, "/lib/ld-linux.so.2", {"libvulkan.so.1", "libz.so.1", "libSDL.so", "libfoo.so", "libgone.so.9"}, 3, {"$ORIGIN/../lib"}));
        auto hits = resolveNeeded(exe, root + "/app/bin", {root + "/bundle/lib"}, {root + "/lib32", root + "/usr/lib"});
        QCOMPARE(hits.size(), 5);
        QVERIFY(hits[0].found); QVERIFY(hits[0].path.endsWith("lib32/libvulkan.so.1"));
        QVERIFY(!hits[1].found); QVERIFY2(hits[1].note.contains("64-bit"), "a 64-bit file must be reported as the wrong class, not as found");
        QVERIFY(hits[2].found); QVERIFY(hits[2].path.contains("bundle/lib"));
        QVERIFY(hits[3].found); QVERIFY2(hits[3].path.endsWith("app/lib/libfoo.so"), "$ORIGIN must expand to the binary's folder");
        QVERIFY(!hits[4].found); QVERIFY(hits[4].note.isEmpty());
    }
    void mountOptions() {
        const QString info =
            "26 1 259:2 / / rw,noatime shared:1 - ext4 /dev/nvme0n1p2 rw\n"
            "40 26 8:1 / /mnt/my\\040games rw,nosuid,nodev,noexec,relatime shared:9 - ext4 /dev/sda1 rw\n"
            "41 26 0:35 / /home rw,relatime - btrfs /dev/nvme0n1p3 rw\n";
        auto a = mountFor("/mnt/my games/melee/bin/melee", info); QVERIFY(a.found); QVERIFY(a.noexec); QCOMPARE(a.fsType, QString("ext4")); QCOMPARE(a.mountPoint, QString("/mnt/my games"));
        auto b = mountFor("/home/x/game/bin/melee", info); QVERIFY(!b.noexec); QCOMPARE(b.fsType, QString("btrfs"));
        auto c = mountFor("/homework/x", info); QCOMPARE(c.mountPoint, QString("/"));   // not under /home
        QVERIFY(!mountFor("/x", "").found);
    }
    void loaderMessagesAreParsed() {
        QCOMPARE(missingLibraryInOutput("./melee: error while loading shared libraries: libSDL3.so.0: cannot open shared object file: No such file or directory"), QString("libSDL3.so.0"));
        QVERIFY(missingLibraryInOutput("all fine").isEmpty());
        QVERIFY(libraryVersionInOutput("./melee: /lib/libc.so.6: version `GLIBC_2.38' not found (required by ./melee)").contains("GLIBC_2.38"));
        QVERIFY(graphicsFailureInOutput("Failed to create adapter: No supported adapters")); QVERIFY(!graphicsFailureInOutput("hello"));
        QCOMPARE(signalName(11), QString("SIGSEGV")); QCOMPARE(signalName(6), QString("SIGABRT")); QCOMPARE(signalName(99), QString("signal 99"));
    }
    void verdictForEachCause() {
        auto codeOf = [](const std::function<void(VerdictInput &)> &mutate) { VerdictInput in; mutate(in); return deriveVerdict(in); };
        QCOMPARE(codeOf([](VerdictInput &) {}).code, QString("UNKNOWN"));
        QCOMPARE(codeOf([](VerdictInput &i) { i.prepareError = "No disc"; }).code, QString("LAUNCHER_FAILED"));
        QCOMPARE(codeOf([](VerdictInput &i) { i.binaryExists = false; }).code, QString("BINARY_MISSING"));
        QCOMPARE(codeOf([](VerdictInput &i) { i.elfValid = false; i.elfBits = 0; }).code, QString("BAD_BINARY"));
        QCOMPARE(codeOf([](VerdictInput &i) { i.elfBits = 64; i.machine = 62; }).code, QString("WRONG_ARCHITECTURE"));
        QCOMPARE(codeOf([](VerdictInput &i) { i.executable = false; }).code, QString("NOT_EXECUTABLE"));
        QCOMPARE(codeOf([](VerdictInput &i) { i.noexecMount = true; }).code, QString("NOEXEC_MOUNT"));
        auto loader = codeOf([](VerdictInput &i) { i.interpreter = "/lib/ld-linux.so.2"; i.interpreterExists = false; i.launched = true; i.startFailed = true; i.startError = "ENOENT: No such file or directory"; });
        QCOMPARE(loader.code, QString("NO_32BIT_LOADER")); QCOMPARE(loader.detail, QString("/lib/ld-linux.so.2"));
        auto lib = codeOf([](VerdictInput &i) { i.launched = true; i.finished = true; i.exitCode = 127; i.childOutput = "melee: error while loading shared libraries: libasound.so.2: cannot open shared object file"; });
        QCOMPARE(lib.line(), QString("MISSING_LIBRARY libasound.so.2"));
        QCOMPARE(codeOf([](VerdictInput &i) { i.missingLibs = {"libx.so"}; }).line(), QString("MISSING_LIBRARY libx.so"));   // static, nothing launched
        // a static "missing" is ignored when the game ran fine: the search paths are an estimate
        QCOMPARE(codeOf([](VerdictInput &i) { i.missingLibs = {"libx.so"}; i.launched = true; i.finished = true; }).code, QString("STARTED_OK"));
        QCOMPARE(codeOf([](VerdictInput &i) { i.launched = true; i.finished = true; i.exitCode = 1; i.childOutput = "/lib/libc.so.6: version `GLIBC_2.99' not found (required by melee)"; }).code, QString("LIBRARY_TOO_OLD"));
        QCOMPARE(codeOf([](VerdictInput &i) { i.vulkanKnown = true; i.vulkan32Present = false; }).code, QString("NO_32BIT_VULKAN_DRIVER"));
        QCOMPARE(codeOf([](VerdictInput &i) { i.vulkanKnown = true; i.vulkan32Present = false; i.launched = true; i.finished = true; i.exitCode = 1; }).code, QString("NO_32BIT_VULKAN_DRIVER"));
        auto gfx = codeOf([](VerdictInput &i) { i.vulkanKnown = true; i.vulkan32Present = true; i.launched = true; i.finished = true; i.exitCode = 1; i.gameLog = "Failed to create adapter"; });
        QCOMPARE(gfx.code, QString("GRAPHICS_INIT_FAILED"));
        auto sig = codeOf([](VerdictInput &i) { i.launched = true; i.finished = true; i.crashed = true; i.signal = "SIGSEGV"; });
        QCOMPARE(sig.line(), QString("KILLED_BY_SIGNAL SIGSEGV"));
        auto early = codeOf([](VerdictInput &i) { i.launched = true; i.finished = true; i.exitCode = 3; i.elapsedMs = 1500; });
        QCOMPARE(early.line(), QString("EXITED_EARLY code=3"));
        QCOMPARE(codeOf([](VerdictInput &i) { i.launched = true; i.finished = true; }).code, QString("STARTED_OK"));
        QVERIFY(codeOf([](VerdictInput &i) { i.launched = true; i.finished = true; }).ok());
        QCOMPARE(codeOf([](VerdictInput &i) { i.launched = true; i.startFailed = true; i.startError = "EACCES"; }).code, QString("START_FAILED"));
        QCOMPARE(codeOf([](VerdictInput &i) { i.launched = true; }).code, QString("RUNNING"));
        // precedence: a missing loader beats everything the missing loader would also explain
        QCOMPARE(codeOf([](VerdictInput &i) { i.interpreter = "/lib/ld-linux.so.2"; i.interpreterExists = false; i.missingLibs = {"libc.so.6"}; i.vulkanKnown = true; i.vulkan32Present = false; }).code, QString("NO_32BIT_LOADER"));
        QVERIFY(!loader.message.isEmpty()); QVERIFY(!sig.checked.isEmpty());
    }
    void packageHints() {
        const QString cachy = "NAME=\"CachyOS Linux\"\nID=cachyos\nID_LIKE=arch\n";
        auto radeon = packageHint(cachy, {}, {0x1002}); QVERIFY(radeon.contains("multilib")); QVERIFY(radeon.contains("lib32-vulkan-radeon")); QVERIFY(radeon.contains("guess"));
        QVERIFY(packageHint(cachy, {}, {0x10de}).contains("lib32-nvidia-utils")); QVERIFY(packageHint(cachy, {}, {0x8086}).contains("lib32-vulkan-intel"));
        QVERIFY(packageHint(cachy, "libvulkan.so.1").contains("lib32-vulkan-icd-loader"));
        QVERIFY(packageHint("ID=ubuntu\nID_LIKE=debian\n").contains("i386")); QVERIFY(packageHint("ID=plan9\n").contains("guess"));
    }
    void redaction() {
        QTemporaryDir d; Redactor r; r.home = "/home/alice"; r.discPaths = {"/home/alice/Games/disc ü with spaces.iso"}; r.words = {"alice-pc", "alice"};
        auto out = r.apply("--iso /home/alice/Games/disc ü with spaces.iso cwd=/home/alice/.local/share/melee-linux host alice-pc user alice ip 192.168.1.20");
        QVERIFY2(out.contains("--iso disc ü with spaces.iso"), qPrintable(out)); QVERIFY(!out.contains("/home/alice/Games"));
        QVERIFY(out.contains("~/.local/share/melee-linux")); QVERIFY(!out.contains("alice")); QVERIFY(!out.contains("192.168")); QVERIFY(out.contains("<ip>"));
        // an unknown disc image is reduced to its file name too, and other users' homes are hidden
        auto other = r.apply("Opening /mnt/data/roms/Melee.iso and /home/bob/x.txt and /run/media/carol/DISC/modded-example.iso");
        QVERIFY2(other.contains("Opening Melee.iso and ~/x.txt and modded-example.iso"), qPrintable(other)); QVERIFY(!other.contains("bob")); QVERIFY(!other.contains("carol")); QVERIFY(!other.contains("roms"));
        QCOMPARE(r.apply("opening /home/zed/Games/My Secret Melee.iso now"), QString("opening My Secret Melee.iso now"));
        QVERIFY(!r.apply("cwd=/mnt/c/Users/Alex/Desktop/x").contains("Alex")); QVERIFY(!r.apply("C:\\Users\\Alex\\Desktop").contains("Alex"));
        QVERIFY(r.apply("Mesa 24.1.3 and Qt 6.8.2").contains("Mesa 24.1.3 and Qt 6.8.2"));   // version numbers survive
        QCOMPARE(envValueForReport("LD_PRELOAD", "/secret/lib.so"), QString("(set, value hidden)"));
        QCOMPARE(envValueForReport("GITHUB_TOKEN", "abc"), QString("(set, value hidden)"));
        QCOMPARE(envValueForReport("SDL_VIDEODRIVER", "wayland"), QString("wayland"));
        QCOMPARE(shortList("1\n2\n3\n4\n5\n6", 2, 1), QString("1\n2\n... 3 lines omitted ...\n6")); QCOMPARE(shortList("1\n2\n", 2, 2), QString("1\n2"));
    }
    void redactedLogWriter() {
        QTemporaryDir d; const auto path = d.path() + "/launcher-process.log";
        Redactor r; r.home = "/home/alex"; r.words = {"alex"};
        {
            RedactedLog log(path, r);
            // a line split across reads, a disc path with spaces, a CRLF line, and a partial last line
            log.write("melee-pc: disc image /home/alex/Downloads/GDMelee-0.1.8-linux-x86_64/my game.i");
            log.write("so\ngw: targettest: no mods found in /home/alex/mods\r\nuser alex ip 10.0.0.5\nlast /home/alex/x");
            QFile mid(path); QVERIFY(mid.open(QIODevice::ReadOnly));   // already on disk before finish()
            QVERIFY(mid.readAll().contains("no mods found in ~/mods"));
        }
        QFile f(path); QVERIFY(f.open(QIODevice::ReadOnly)); const auto text = QString::fromUtf8(f.readAll());
        QVERIFY2(text.contains("melee-pc: disc image my game.iso\n"), qPrintable(text));
        QVERIFY(text.contains("no mods found in ~/mods\r\n")); QVERIFY(text.contains("user <name> ip <ip>")); QVERIFY(text.endsWith("last ~/x"));
        QVERIFY(!text.contains("alex")); QVERIFY(!text.contains("Downloads")); QVERIFY(!text.contains("/home"));
        // the first/last-lines capture the diagnostics report uses still works on the redacted file
        QCOMPARE(shortList(text, 1, 1).split('\n').size(), 3);
    }
    void redactedLogOfRealChild() {
#ifdef Q_OS_UNIX
        const QString script = "printf 'disc image %s/Downloads/pkg/example.iso\\n' \"$HOME\"; printf 'gw: no mods found in %s/x\\n' \"$HOME\" >&2; printf 'partial %s' \"$HOME\"; if [ -n \"$HANG\" ]; then sleep 30; fi";
        for (bool kill : {false, true}) {
            QTemporaryDir d; const auto path = d.path() + "/launcher-process.log";
            QProcess p; QProcessEnvironment env = QProcessEnvironment::systemEnvironment(); env.insert("HOME", "/home/alex"); if (kill) env.insert("HANG", "1");
            p.setProcessEnvironment(env); p.setProgram("/bin/sh"); p.setArguments({"-c", script});
            Redactor r; r.home = "/home/alex"; r.words = {"alex"};
            captureRedacted(p, path, r); p.start(); QVERIFY(p.waitForStarted());
            if (kill) {
                // the file already holds the complete lines while the child is still hanging
                QTRY_VERIFY_WITH_TIMEOUT([&] { QFile f(path); return f.open(QIODevice::ReadOnly) && f.readAll().contains("no mods found in ~/x"); }(), 5000);
                p.kill();
            }
            QVERIFY(p.waitForFinished(10000));
            QFile f(path); QVERIFY(f.open(QIODevice::ReadOnly)); const auto text = QString::fromUtf8(f.readAll());
            QVERIFY2(text.contains("disc image example.iso\n"), qPrintable(text)); QVERIFY2(text.contains("no mods found in ~/x\n"), qPrintable(text));
            QVERIFY2(!text.contains("alex") && !text.contains("/home") && !text.contains("Downloads"), qPrintable(text));
            if (!kill) QVERIFY2(text.endsWith("partial ~"), qPrintable(text));
        }
#else
        QSKIP("needs /bin/sh");
#endif
    }
    void launchRedactorNamesTheDisc() {
        auto r = redactorForLaunch({"--iso", "/data/games/example disc.iso", "--x"}); QCOMPARE(r.discPaths, QStringList({"/data/games/example disc.iso"}));
        QVERIFY(redactorForLaunch({"--test"}).discPaths.isEmpty());
    }
    void environmentDifference() {
        QProcessEnvironment a, b; a.insert("KEEP", "1"); a.insert("GONE", "x"); a.insert("CHANGED", "old"); b.insert("KEEP", "1"); b.insert("CHANGED", "new"); b.insert("MELEE_VOLUME", "50"); b.insert("API_TOKEN", "s3cret");
        auto diff = environmentDiff(a, b).join('\n');
        QVERIFY(diff.contains("+ MELEE_VOLUME=50")); QVERIFY(diff.contains("- GONE")); QVERIFY(diff.contains("~ CHANGED=new  (was old)")); QVERIFY(!diff.contains("KEEP")); QVERIFY(!diff.contains("s3cret"));
    }
    void reportRotation() {
        QTemporaryDir d;
        for (int i = 1; i <= 14; ++i) writeAtomic(d.path() + QString("/launch-diagnostics-20260101-0000%1.txt").arg(i, 2, 10, QChar('0')), "x");
        writeAtomic(d.path() + "/launch-diagnostics.txt", "latest"); writeAtomic(d.path() + "/other.txt", "keep");
        rotateReports(d.path());
        auto left = QDir(d.path()).entryList({"launch-diagnostics-*.txt"}, QDir::Files, QDir::Name);
        QCOMPARE(left.size(), 10); QCOMPARE(left.first(), QString("launch-diagnostics-20260101-000005.txt"));
        QVERIFY(QFile::exists(d.path() + "/launch-diagnostics.txt")); QVERIFY(QFile::exists(d.path() + "/other.txt"));
    }
#ifdef Q_OS_LINUX
    void execProbeReportsErrno() {
        QTemporaryDir d;
        QVERIFY(execProbe(d.path() + "/missing", {}).startsWith("ENOENT"));
        writeAtomic(d.path() + "/plain", "not a program"); QFile::setPermissions(d.path() + "/plain", QFile::ReadOwner | QFile::WriteOwner);
        QVERIFY2(execProbe(d.path() + "/plain", {}).startsWith("EACCES"), qPrintable(execProbe(d.path() + "/plain", {})));
        // The real failure from the report: an existing, executable i386 binary whose loader is not installed.
        auto bytes = elfFixture(32, "/lib/ld-gdmelee-absent.so.2", {"libc.so.6"}); writeAtomic(d.path() + "/melee32", bytes);
        QFile::setPermissions(d.path() + "/melee32", QFile::ReadOwner | QFile::WriteOwner | QFile::ExeOwner);
        auto probe = execProbe(d.path() + "/melee32", {}); QVERIFY2(probe.startsWith("ENOENT"), qPrintable(probe)); QVERIFY(probe.contains("No such file"));
    }
    void reportForBrokenInstall() {
        // A game folder whose 32-bit loader and a library are missing, and a disc whose path must not leak.
        QTemporaryDir d; const auto app = d.path() + "/game", user = d.path() + "/user";
        QDir().mkpath(app + "/bin"); QDir().mkpath(app + "/lib");
        writeAtomic(app + "/bin/melee", elfFixture(32, "/lib/ld-gdmelee-absent.so.2", {"libgdmelee-nowhere.so.7"}, 3, {"$ORIGIN/../lib"}));
        QFile::setPermissions(app + "/bin/melee", QFile::ReadOwner | QFile::WriteOwner | QFile::ExeOwner);
        const auto disc = d.path() + "/My Secret Disc.iso";
        DiagContext c; c.appDir = app; c.userDir = user; c.discPaths = {disc}; c.finished = true; c.full = false; c.stamp = "20260101-000000";
        c.spec.program = app + "/bin/melee"; c.spec.workingDirectory = user + "/runs/x"; c.spec.arguments = {"--iso", disc};
        c.spec.environment = QProcessEnvironment::systemEnvironment(); c.spec.environment.insert("LD_LIBRARY_PATH", app + "/lib"); c.haveSpec = true;
        c.spawn.attempted = true; c.spawn.program = c.spec.program; c.spawn.arguments = c.spec.arguments; c.spawn.workingDirectory = c.spec.workingDirectory;
        c.spawn.processError = 0; c.spawn.errorString = "An error occurred when attempting to start the process"; c.spawn.execProbe = "ENOENT: No such file or directory";
        auto report = writeDiagnostics(c);
        QCOMPARE(report.verdict.code, QString("NO_32BIT_LOADER"));
        QVERIFY(report.text.contains("VERDICT: NO_32BIT_LOADER /lib/ld-gdmelee-absent.so.2"));
        QVERIFY(report.text.contains("WHAT THIS FILE CONTAINS")); QVERIFY(report.text.contains("libgdmelee-nowhere.so.7: MISSING"));
        QVERIFY(report.text.contains("--iso \"My Secret Disc.iso\"") || report.text.contains("--iso My"));   // file name only
        QVERIFY(!report.text.contains(d.path() + "/My Secret"));
        QVERIFY(QFile::exists(user + "/diagnostics/launch-diagnostics.txt")); QVERIFY(QFile::exists(user + "/diagnostics/launch-diagnostics-20260101-000000.txt"));
        QCOMPARE(readText(user + "/diagnostics/launch-diagnostics.txt"), report.text);
    }
#endif
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
