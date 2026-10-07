// The crash-upload client against the real tools/release/crash_upload_server.py, started on 127.0.0.1 with a
// temporary --dir. Nothing here ever reaches the public server.
#include "crash_upload.h"
#include <QDateTime>
#include <QDir>
#include <QDirIterator>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QProcess>
#include <QTcpServer>
#include <QTcpSocket>
#include <QTemporaryDir>
#include <QtTest>
#include <atomic>
#include <thread>
using namespace launcher;

static const QByteArray kHeader = "==== GD's Melee crash report ====\n";

static void writeFile(const QString &path, const QByteArray &data, const QDateTime &when = {}) {
    QDir().mkpath(QFileInfo(path).absolutePath());
    QFile f(path); QVERIFY(f.open(QIODevice::WriteOnly)); f.write(data); f.close();
    if (when.isValid()) { QVERIFY(f.open(QIODevice::ReadWrite)); QVERIFY(f.setFileTime(when, QFileDevice::FileModificationTime)); f.close(); }
}
static QByteArray report(const QString &name) { return kHeader + "version:         0.2.0 (melee test)\nbuild id:        " + name.toUtf8() + "\nreason:          test\n"; }

// crash_upload_server.py as a child process, on a free loopback port, storing into its own temp dir.
struct LocalServer {
    QTemporaryDir dir; QProcess process; int port = 0; QString crashes;
    bool start() {
        QTcpServer probe; if (!probe.listen(QHostAddress::LocalHost, 0)) return false;
        port = probe.serverPort(); probe.close();
        crashes = dir.path() + "/stored";
        process.setStandardOutputFile(dir.path() + "/server.out"); process.setStandardErrorFile(dir.path() + "/server.err");
        process.start(CRASH_TEST_PYTHON, {"-I", CRASH_SERVER_PY, "--bind", "127.0.0.1", "--port", QString::number(port), "--dir", crashes});
        if (!process.waitForStarted(10000)) return false;
        for (int i = 0; i < 100; ++i) {                       // wait until it accepts
            QTcpSocket s; s.connectToHost("127.0.0.1", quint16(port));
            if (s.waitForConnected(200)) return true;
            if (process.state() != QProcess::Running) return false;
            QTest::qWait(100);
        }
        return false;
    }
    QString address() const { return "127.0.0.1:" + QString::number(port); }
    QStringList stored(const QString &suffix) const {
        QStringList out; QDirIterator it(crashes, {"*" + suffix}, QDir::Files, QDirIterator::Subdirectories);
        while (it.hasNext()) out << it.next();
        out.sort(); return out;
    }
    // One raw request; returns the status line + body, or "" when the server closed on us.
    QString raw(const QByteArray &request) const {
        QTcpSocket s; s.connectToHost("127.0.0.1", quint16(port));
        if (!s.waitForConnected(5000)) return {};
        s.write(request); s.waitForBytesWritten(5000);
        QByteArray reply; while (s.state() == QAbstractSocket::ConnectedState || s.bytesAvailable()) { if (!s.waitForReadyRead(3000)) break; reply += s.readAll(); }
        return QString::fromUtf8(reply);
    }
    ~LocalServer() { process.kill(); process.waitForFinished(3000); }
};

class CrashUploadTests : public QObject {
    Q_OBJECT
    static bool havePython() { return QFileInfo::exists(CRASH_TEST_PYTHON) && QFileInfo::exists(CRASH_SERVER_PY); }
private slots:
    void serverAddressComesFromNetplayServerTxt() {
        QTemporaryDir d;
        QCOMPARE(crashServer(d.path()), QString());                                        // no file: no server, no upload
        writeFile(d.path() + "/netplay_server.txt", "# the matchmaking server\n\n  netplay.example:51600  \nother:1\n");
        QCOMPARE(crashServer(d.path()), QString("netplay.example:51600"));
        writeFile(d.path() + "/netplay_server.txt", "# only a comment\n");
        QCOMPARE(crashServer(d.path()), QString());
    }
    void selection_isTheNewestThreeCompactReports() {
        QTemporaryDir d; const auto base = QDateTime::currentDateTime().addDays(-1); auto at = [&](int minutes) { return base.addSecs(60 * minutes); };
        const auto dir = d.path() + "/crashlogs/";
        writeFile(dir + "crash-a.log", report("a"), at(1));
        writeFile(dir + "crash-b.log", report("b"), at(2));
        writeFile(dir + "crash-b-full.log", "the whole log, never sent", at(3));
        writeFile(dir + "crash-c.log", kHeader + "during shutdown: yes\n", at(4));            // a teardown fault
        writeFile(dir + "crash-d.log", "an old style report with no header\n", at(5));
        writeFile(dir + "crash-e.log", kHeader + QByteArray(kCrashUploadMax, 'x'), at(6));   // over 64 KB
        writeFile(dir + "crash-f.log", report("f"), at(7));
        writeFile(dir + "crash-g.log", report("g"), at(8));
        writeFile(dir + "crash-h.log", report("h"), at(9));
        QStringList names; for (const auto &p : uploadableCrashes(d.path())) names << QFileInfo(p).fileName();
        QCOMPARE(names, QStringList({"crash-h.log", "crash-g.log", "crash-f.log"}));
        names.clear(); for (const auto &p : uploadableCrashes(d.path(), 10)) names << QFileInfo(p).fileName();
        QCOMPARE(names, QStringList({"crash-h.log", "crash-g.log", "crash-f.log", "crash-b.log", "crash-a.log"}));
        QTemporaryDir empty; QVERIFY(uploadableCrashes(empty.path()).isEmpty());
    }
    void scrub_removesTheProfileAndTheUserName() {
        const auto out = scrubCrashReport("C:\\Users\\Tester\\game C:/Users/tester/x user=TESTER", "C:\\Users\\Tester", "Tester");
        QCOMPARE(out, QString("%USERPROFILE%\\game %USERPROFILE%/x user=<user>"));
        QCOMPARE(scrubCrashReport("keep ab here", "C:\\", "ab"), QString("keep ab here"));   // too short to be a name or a profile
    }
    void nothingToSend_neverOpensAConnection() {
        QCOMPARE(uploadCrashReports("127.0.0.1:1", {}, "t", {}, {}).failure, CrashUploadResult::NoReports);
        QTemporaryDir d; writeFile(d.path() + "/c.log", report("c"));
        QCOMPARE(uploadCrashReports({}, {d.path() + "/c.log"}, "t", {}, {}).failure, CrashUploadResult::NoServer);
        QVERIFY(!QFileInfo::exists(d.path() + "/c.log.sent"));
    }
    void unreachableServer_failsWithAReason() {
        QTcpServer probe; QVERIFY(probe.listen(QHostAddress::LocalHost, 0)); const auto port = probe.serverPort(); probe.close();   // nothing listens here now
        QTemporaryDir d; writeFile(d.path() + "/c.log", report("c"));
        const auto r = uploadCrashReports("127.0.0.1:" + QString::number(port), {d.path() + "/c.log"}, "t", {}, {}, 3000);
        QCOMPARE(r.failure, CrashUploadResult::Network); QVERIFY(!r.detail.isEmpty()); QCOMPARE(r.sent, 0);
        QVERIFY(!QFileInfo::exists(d.path() + "/c.log.sent"));
    }
    void oversizedReport_isNotSent() {
        QTemporaryDir d; writeFile(d.path() + "/c.log", kHeader + QByteArray(kCrashUploadMax, 'x'));   // 64 KB + header
        const auto r = uploadCrashReports("127.0.0.1:1", {d.path() + "/c.log"}, "t", {}, {});
        QCOMPARE(r.failure, CrashUploadResult::TooLarge);                                              // refused before any connection
    }
    void uploadsThreeReportsToALocalServer() {
        if (!havePython()) QSKIP("no Python to run crash_upload_server.py");
        LocalServer server; QVERIFY2(server.start(), "crash_upload_server.py did not start");
        QTemporaryDir d; QStringList files;
        for (const char *n : {"one", "two", "three"}) {
            const auto path = d.path() + "/crash-" + n + ".log"; files << path;
            writeFile(path, report(n) + "stack: C:\\Users\\Tester\\melee\\x.c user Tester\n");
        }
        const auto r = uploadCrashReports(server.address(), files, "0.2.0-test", "C:\\Users\\Tester", "Tester");
        QVERIFY2(r.ok(), qPrintable(r.detail)); QCOMPARE(r.sent, 3); QCOMPARE(r.total, 3);
        const auto logs = server.stored(".log"); QCOMPARE(logs.size(), 3);
        QStringList bodies; for (const auto &p : logs) { QFile f(p); QVERIFY(f.open(QIODevice::ReadOnly)); bodies << QString::fromUtf8(f.readAll()); }
        for (const char *n : {"one", "two", "three"}) {
            const auto expected = QString::fromUtf8(report(n) + "stack: %USERPROFILE%\\melee\\x.c user <user>\n");     // scrubbed before it left
            QVERIFY2(bodies.contains(expected), n);
        }
        for (const auto &b : bodies) { QVERIFY(!b.contains("Tester")); QVERIFY(b.startsWith(QString::fromUtf8(kHeader.trimmed()))); }
        const auto metas = server.stored(".json"); QCOMPARE(metas.size(), 3);                    // the server's metadata beside each
        QFile m(metas.first()); QVERIFY(m.open(QIODevice::ReadOnly));
        QCOMPARE(QJsonDocument::fromJson(m.readAll()).object()["version"].toString(), QString("0.2.0 (melee test)"));
        for (const auto &f : files) {                                                            // the launcher notes what it sent
            QFile s(f + ".sent"); QVERIFY(s.open(QIODevice::ReadOnly));
            const auto note = QString::fromUtf8(s.readAll()); QVERIFY(note.contains(server.address())); QVERIFY(note.contains("OK "));
        }
    }
    void fourthUploadInAnHour_isTheServers429() {
        if (!havePython()) QSKIP("no Python to run crash_upload_server.py");
        LocalServer server; QVERIFY2(server.start(), "crash_upload_server.py did not start");
        QTemporaryDir d; QStringList files;
        for (int i = 0; i < 4; ++i) { const auto p = d.path() + "/crash-" + QString::number(i) + ".log"; files << p; writeFile(p, report(QString::number(i))); }
        const auto r = uploadCrashReports(server.address(), files, "t", {}, {});
        QCOMPARE(r.failure, CrashUploadResult::ServerRefused); QCOMPARE(r.status, 429); QCOMPARE(r.detail, QString("slow down"));
        QCOMPARE(r.sent, 3); QCOMPARE(r.total, 4);                                              // 3 an hour per address
        QCOMPARE(server.stored(".log").size(), 3);
        QVERIFY(QFileInfo::exists(files[2] + ".sent")); QVERIFY(!QFileInfo::exists(files[3] + ".sent"));
    }
    void theServersOtherReplies() {
        if (!havePython()) QSKIP("no Python to run crash_upload_server.py");
        LocalServer server; QVERIFY2(server.start(), "crash_upload_server.py did not start");
        auto post = [&](const QByteArray &body, qint64 declared = -1) {
            return server.raw("POST /crash HTTP/1.1\r\nHost: x\r\nContent-Type: text/plain\r\nContent-Length: " + QByteArray::number(declared >= 0 ? declared : body.size()) + "\r\nConnection: close\r\n\r\n" + body);
        };
        QVERIFY2(post("not a crash report").startsWith("HTTP/1.1 400"), "a body without the report header");
        QVERIFY2(post({}, kCrashUploadMax + 1).startsWith("HTTP/1.1 413"), "over 64 KB is refused on the declared length");
        QVERIFY2(server.raw("GET /crash HTTP/1.1\r\nHost: x\r\n\r\n").startsWith("HTTP/1.1 404"), "only POST /crash");
        const auto ok = post(report("ok"));
        QVERIFY2(ok.startsWith("HTTP/1.1 200") && ok.contains("OK "), qPrintable(ok));
        QCOMPARE(server.stored(".log").size(), 1);                                              // only the good one was kept
    }
    void cancelEndsTheWait() {
        QTcpServer silent; QVERIFY(silent.listen(QHostAddress::LocalHost, 0));                 // accepts, never answers
        QTemporaryDir d; writeFile(d.path() + "/c.log", report("c"));
        std::atomic<bool> cancel{false};
        std::thread stopper([&] { QThread::msleep(500); cancel = true; });
        QElapsedTimer t; t.start();
        const auto r = uploadCrashReports("127.0.0.1:" + QString::number(silent.serverPort()), {d.path() + "/c.log"}, "t", {}, {}, 60000, &cancel);
        QCOMPARE(r.failure, CrashUploadResult::Cancelled); stopper.join(); QVERIFY2(t.elapsed() < 5000, "cancel was not noticed");
    }
};
QTEST_GUILESS_MAIN(CrashUploadTests)
#include "crash_upload_tests.moc"
