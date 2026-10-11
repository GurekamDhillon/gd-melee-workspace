#include "update_check.h"
#include "update_test_fixture.h"
#include <QFile>
#include <QJsonDocument>
#include <QTcpServer>
#include <QTcpSocket>
#include <QTemporaryDir>
#include <QSignalSpy>
#include <QScopeGuard>
#include <QSslCertificate>
#include <QSslConfiguration>
#include <QSslKey>
#include <QSslSocket>
#include <QtTest>
using namespace launcher;

// Uses a public localhost-only fixture certificate. Trust lives in this test
// process's Qt configuration; the Windows certificate store is never changed.
class HttpsFixture : public HttpFixture {
    QSslCertificate cert_;
    QSslKey key_;
public:
    HttpsFixture() {
        QFile cert(QString::fromUtf8(UPDATE_TLS_TESTDATA) + "/tls-localhost.pem");
        QFile key(QString::fromUtf8(UPDATE_TLS_TESTDATA) + "/tls-localhost-key.pem");
        if (!cert.open(QIODevice::ReadOnly) || !key.open(QIODevice::ReadOnly)) qFatal("Missing test TLS fixture");
        cert_ = QSslCertificate(cert.readAll()); key_ = QSslKey(key.readAll(), QSsl::Rsa);
        if (cert_.isNull() || key_.isNull()) qFatal("Invalid test TLS fixture");
    }
    QUrl url() const { return QUrl("https://127.0.0.1:" + QString::number(serverPort()) + "/update.json"); }
    QSslCertificate certificate() const { return cert_; }
protected:
    void incomingConnection(qintptr descriptor) override {
        auto *socket = new QSslSocket(this);
        socket->setLocalCertificate(cert_); socket->setPrivateKey(key_);
        socket->setPeerVerifyMode(QSslSocket::VerifyNone); // server does not require a client certificate
        socket->setProtocol(QSsl::TlsV1_2OrLater);
        if (!socket->setSocketDescriptor(descriptor)) { socket->deleteLater(); return; }
        addPendingConnection(socket); socket->startServerEncryption();
    }
};

class UpdateTests : public QObject {
    Q_OBJECT
private:
    UpdateCheckConfig config(const QUrl &url) {
        UpdateCheckConfig c; c.url = url; c.installedVersion = "0.2.2 (melee abc)"; c.installedProtocol = 6;
        c.connectTimeoutMs = 500; c.totalTimeoutMs = 1000; return c;
    }
private slots:
    void versions_data() {
        QTest::addColumn<QString>("a"); QTest::addColumn<QString>("b"); QTest::addColumn<int>("want");
        QTest::newRow("numeric") << "0.10.0" << "0.9.9" << 1;
        QTest::newRow("fourth") << "0.1.8.1-linux" << "0.1.8 (melee abc)" << 1;
        QTest::newRow("zero-fourth") << "0.3.0.0" << "0.3.0" << 0;
        QTest::newRow("suffix") << "0.3.0-linux" << "0.3.0" << 0;
        QTest::newRow("older") << "0.2.2" << "0.3.0" << -1;
    }
    void versions() {
        QFETCH(QString, a); QFETCH(QString, b); QFETCH(int, want);
        const auto va = Version::parse(a), vb = Version::parse(b); QVERIFY(va && vb);
        QCOMPARE(va->compare(*vb), want);
    }
    void bad_versions() {
        for (const auto &s : {"", "dev", "1.2", "-1.2.3", "1.2.3.4.5", "1.2.3garbage", "2147483648.0.0", "1.02.3"}) QVERIFY2(!Version::parse(s), s);
    }
    void manifest_parse_and_unsigned_verification() {
        QString error; auto m = parseUpdateManifest(updateFixture(), ManifestPolicy::NotifyOnlyUnsigned, &error);
        QVERIFY2(m, qPrintable(error)); QCOMPARE(m->version.text(), QString("0.3.0"));
        QCOMPARE(m->protocol, 7); QCOMPARE(m->packageSize, qint64(1234)); QCOMPARE(m->notesEs, QString::fromUtf8("Una actualización."));
        // A caller requiring authenticity must not silently receive an unsigned result.
        QVERIFY(!parseUpdateManifest(updateFixture(), ManifestPolicy::RequireSignature, &error));
        QVERIFY(error.contains("signature", Qt::CaseInsensitive));
    }
    void malformed_manifests() {
        const auto original = QJsonDocument::fromJson(updateFixture()).object();
        const QList<QPair<QString, QJsonValue>> invalid{{"schema", 2}, {"schema", "1"}, {"channel", "beta"},
            {"version", "0.3.0-beta"}, {"released", "2026-02-30"}, {"netplay_protocol", "7"},
            {"netplay_protocol", -1}, {"netplay_protocol", 6.5}, {"critical", "false"},
            {"notes_url", "http://github.com/release"}, {"notes_url", "https://user:pass@example.com/release"},
            {"notes_short", QJsonObject{{"en", "Only English"}}}, {"files_manifest_sha256", "abc"},
            {"package", QJsonObject{{"url", "https://example.com/pkg.zip"}, {"size", 0}, {"sha256", QString(64, 'a')}}}};
        for (const auto &bad : invalid) {
            auto o = original; o[bad.first] = bad.second;
            QVERIFY2(!parseUpdateManifest(QJsonDocument(o).toJson()), qPrintable(bad.first));
        }
        for (const auto &key : original.keys()) { auto o = original; o.remove(key); QVERIFY2(!parseUpdateManifest(QJsonDocument(o).toJson()), qPrintable(key)); }
        QVERIFY(!parseUpdateManifest("[1,2]")); QVERIFY(!parseUpdateManifest("{"));
        QVERIFY(!parseUpdateManifest(QByteArray(65537, ' ')));
    }
    void scheduling() {
        Settings s; const auto now = QDateTime::fromString("2026-10-11T12:00:00Z", Qt::ISODate);
        QVERIFY(updateCheckDue(s, now));
        s.options["update_last_attempt"] = "2026-10-10T12:00:01Z"; QVERIFY(!updateCheckDue(s, now));
        s.options["update_last_attempt"] = "2026-10-10T12:00:00Z"; QVERIFY(updateCheckDue(s, now));
        s.options["update_last_attempt"] = "invalid"; QVERIFY(updateCheckDue(s, now));
        s.options["update_last_attempt"] = "2027-10-11T12:00:00Z"; QVERIFY(updateCheckDue(s, now));
        s.options["update_enabled"] = "0"; QVERIFY(!updateCheckDue(s, now));
    }
    void suppression_and_override() {
        QProcessEnvironment e;
        QVERIFY(!updateChecksSuppressed({}, e));
        QVERIFY(updateChecksSuppressed({"--no-update-check"}, e));
        e.insert("GDMELEE_NO_UPDATE_CHECK", "1"); QVERIFY(updateChecksSuppressed({}, e));
        QTemporaryDir d; QVERIFY(d.isValid());
        QCOMPARE(updateConfig(d.path()).url, QUrl("https://github.com/GurekamDhillon/gd-melee-workspace/releases/latest/download/update.json"));
        writeAtomic(d.path() + "/update_url.txt", "http://127.0.0.1:12345/update.json\n");
        QCOMPARE(updateConfig(d.path()).url, QUrl("http://127.0.0.1:12345/update.json"));
        writeAtomic(d.path() + "/update_url.txt", "http://example.com/update.json\n");
        QVERIFY(!updateConfig(d.path()).url.isValid());
        writeAtomic(d.path() + "/version.txt", "0.2.2 (melee abc)\nnetplay_protocol 6\n");
        QCOMPARE(updateConfig(d.path()).installedProtocol, 6);
    }
    void get_is_private_and_never_downloads_package() {
        HttpFixture server; QTemporaryDir dir; Settings s;
        UpdateChecker checker(s, dir.path(), config(server.url()));
        QVERIFY(checker.check(true)); QCOMPARE(checker.state(), UpdateState::Checking);
        QTRY_COMPARE(checker.state(), UpdateState::Available);
        QCOMPARE(server.count, 1); QVERIFY(server.request.startsWith("GET /update.json HTTP/1.1\r\n"));
        QVERIFY(server.request.toLower().contains("user-agent: gdmeleelauncher/0.2.2\r\n"));
        QVERIFY(!server.request.toLower().contains("cookie:")); QVERIFY(!server.request.toLower().contains("authorization:"));
        QVERIFY(server.request.toLower().contains("accept-language: en,es\r\n"));
        QVERIFY(checker.manifest()); QCOMPARE(checker.manifest()->protocol, 7);
        auto stored = Settings::load(dir.path()); QVERIFY(!stored.option("update_last_attempt").isEmpty());
        QVERIFY(!checker.check()); QCOMPARE(server.count, 1);
        QVERIFY(checker.check(true)); QTRY_COMPARE(server.count, 2); QTRY_COMPARE(checker.state(), UpdateState::Available);
    }
    void skip_persists_and_cache_is_hint_only() {
        HttpFixture server; QTemporaryDir dir; Settings s; auto c = config(server.url());
        {
            UpdateChecker checker(s, dir.path(), c); QVERIFY(checker.check(true)); QTRY_COMPARE(checker.state(), UpdateState::Available);
            checker.skipVersion(); QCOMPARE(checker.state(), UpdateState::Skipped);
            QCOMPARE(Settings::load(dir.path()).option("update_skipped_version"), QString("0.3.0"));
        }
        UpdateChecker next(s, dir.path(), c); QCOMPARE(next.state(), UpdateState::Idle);
        QVERIFY(!next.manifest()); QVERIFY(next.cachedManifest()); QCOMPARE(next.cachedManifest()->protocol, 7);
        QVERIFY(next.check(true)); QTRY_COMPARE(next.state(), UpdateState::Skipped);
        server.response.replace("0.3.0", "0.3.1");
        QVERIFY(next.check(true)); QTRY_COMPARE(next.state(), UpdateState::Available);
    }
    void opt_out_and_game_running_prevent_requests() {
        HttpFixture server; QTemporaryDir dir; Settings s; auto c = config(server.url());
        UpdateChecker checker(s, dir.path(), c); checker.setEnabled(false);
        QVERIFY(!checker.check()); QCOMPARE(server.count, 0);
        QVERIFY(checker.check(true)); QTRY_COMPARE(checker.state(), UpdateState::Available); // explicit manual consent
        checker.setGameRunning(true); QVERIFY(!checker.check(true));
        checker.setGameRunning(false); checker.setEnabled(true);
        c.suppressed = true; UpdateChecker suppressed(s, dir.path(), c);
        QVERIFY(!suppressed.check(true)); QVERIFY(!suppressed.check()); QCOMPARE(server.count, 1);
    }
    void offline_failure_is_rate_limited() {
        QTcpServer closed; QVERIFY(closed.listen(QHostAddress::LocalHost)); const auto port = closed.serverPort(); closed.close();
        QTemporaryDir dir; Settings s;
        UpdateChecker checker(s, dir.path(), config(QUrl("http://127.0.0.1:" + QString::number(port) + "/update.json")));
        QVERIFY(checker.check()); QTRY_COMPARE(checker.state(), UpdateState::Failed);
        QVERIFY(!checker.manifest()); QVERIFY(!checker.check());
        QVERIFY(checker.check(true)); QTRY_COMPARE(checker.state(), UpdateState::Failed);
    }
    void stalled_request_times_out_and_launch_cancels() {
        HttpFixture server; server.stall = true; QTemporaryDir dir; Settings s; auto c = config(server.url());
        c.connectTimeoutMs = 60; c.totalTimeoutMs = 150;
        UpdateChecker checker(s, dir.path(), c); QVERIFY(checker.check(true));
        QTRY_COMPARE_WITH_TIMEOUT(checker.state(), UpdateState::Failed, 1000);
        QVERIFY(checker.error().contains("timeout"));
        QVERIFY(checker.check(true)); checker.setGameRunning(true);
        QVERIFY(checker.state() != UpdateState::Checking); QVERIFY(!checker.check(true));
    }
    void total_timeout_bounds_a_trickling_response() {
        HttpFixture server; server.trickle = true; QTemporaryDir dir; Settings s; auto c = config(server.url());
        c.connectTimeoutMs = 500; c.totalTimeoutMs = 100;
        UpdateChecker checker(s, dir.path(), c); QVERIFY(checker.check(true));
        QTRY_COMPARE_WITH_TIMEOUT(checker.state(), UpdateState::Failed, 1000);
        QVERIFY(checker.error().contains("timeout")); QVERIFY(!checker.manifest());
    }
    void redirect_stays_on_a_safe_transport() {
        HttpFixture target, source; source.code = 302; source.response.clear();
        source.extraHeaders = "Location: " + target.url().toEncoded() + "\r\n";
        QTemporaryDir dir; Settings s; UpdateChecker checker(s, dir.path(), config(source.url()));
        QVERIFY(checker.check(true)); QTRY_COMPARE(checker.state(), UpdateState::Available);
        QCOMPARE(target.count, 1); QVERIFY(target.request.toLower().contains("user-agent: gdmeleelauncher/0.2.2"));
        source.extraHeaders = "Location: http://example.com/update.json\r\n";
        QVERIFY(checker.check(true)); QTRY_COMPARE(checker.state(), UpdateState::Failed);
        QVERIFY(checker.error().contains("redirect", Qt::CaseInsensitive)); QCOMPARE(target.count, 1);
    }
    void https_redirects_allow_tls_and_reject_loopback_downgrades() {
#ifdef Q_OS_WIN
        if (QSslSocket::activeBackend() != "schannel") QVERIFY(QSslSocket::setActiveBackend("schannel"));
#endif
        QVERIFY(QSslSocket::supportsSsl());
        const auto original = QSslConfiguration::defaultConfiguration();
        auto restore = qScopeGuard([&] { QSslConfiguration::setDefaultConfiguration(original); });
        HttpsFixture source, target; HttpFixture plain;
        auto trusted = original; trusted.addCaCertificate(source.certificate());
        QSslConfiguration::setDefaultConfiguration(trusted);
        source.code = 302; source.response.clear();
        source.extraHeaders = "Location: " + target.url().toEncoded() + "\r\n";
        QTemporaryDir dir; Settings s; auto c = config(source.url());
        c.connectTimeoutMs = 2000; c.totalTimeoutMs = 5000;
        UpdateChecker checker(s, dir.path(), c);
        QVERIFY(checker.check(true)); QTRY_COMPARE_WITH_TIMEOUT(checker.state(), UpdateState::Available, 6000);
        QCOMPARE(source.count, 1); QCOMPARE(target.count, 1);
        source.extraHeaders = "Location: " + plain.url().toEncoded() + "\r\n";
        QVERIFY(checker.check(true)); QTRY_COMPARE_WITH_TIMEOUT(checker.state(), UpdateState::Failed, 6000);
        QCOMPARE(source.count, 2); QCOMPARE(target.count, 1); QCOMPARE(plain.count, 0);
        QVERIFY(checker.error().contains("redirect", Qt::CaseInsensitive));
    }
    void untrusted_http_and_oversized_response_fail() {
        QTemporaryDir dir; Settings s; UpdateChecker unsafe(s, dir.path(), config(QUrl("http://example.com/update.json")));
        QVERIFY(!unsafe.check(true)); QCOMPARE(unsafe.state(), UpdateState::Failed);
        HttpFixture server; server.response = QByteArray(65537, ' '); UpdateChecker large(s, dir.path(), config(server.url()));
        QVERIFY(large.check(true)); QTRY_COMPARE(large.state(), UpdateState::Failed); QVERIFY(!large.manifest());
    }
    void release_date_rollback_and_old_version_do_not_notify() {
        HttpFixture server; QTemporaryDir dir; Settings s; UpdateChecker checker(s, dir.path(), config(server.url()));
        QVERIFY(checker.check(true)); QTRY_COMPARE(checker.state(), UpdateState::Available);
        server.response.replace("2026-10-11", "2026-10-10").replace("0.3.0", "0.4.0");
        QVERIFY(checker.check(true)); QTRY_COMPARE(checker.state(), UpdateState::Failed); QVERIFY(!checker.manifest());
        server.response = updateFixture(); server.response.replace("0.3.0", "0.2.1");
        QVERIFY(checker.check(true)); QTRY_COMPARE(checker.state(), UpdateState::UpToDate);
    }
};
QTEST_GUILESS_MAIN(UpdateTests)
#include "update_tests.moc"
