#include "window.h"
#include "kit.h"
#include "update_test_fixture.h"
#include "workbench/testfixture.h"
#include "workbench/workbench_window.h"
#include <QApplication>
#include <QCheckBox>
#include <QLabel>
#include <QPointer>
#include <QPushButton>
#include <QScrollArea>
#include <QScrollBar>
#include <QTemporaryDir>
#include <QScopeGuard>
#include <QStackedWidget>
#include <QtTest>
using namespace launcher;

class UpdateUiTests : public QObject {
    Q_OBJECT
    QByteArray previousSuppression_;
private slots:
    void initTestCase() { applyTheme(); previousSuppression_ = qgetenv("GDMELEE_NO_UPDATE_CHECK"); }
    void init() { qputenv("GDMELEE_NO_UPDATE_CHECK", "0"); }
    void cleanup() { qputenv("GDMELEE_NO_UPDATE_CHECK", previousSuppression_); spanish = false; }
    void notification_data() {
        QTest::addColumn<bool>("es");
        QTest::newRow("English") << false; QTest::newRow("Spanish") << true;
    }
    void notification() {
        QFETCH(bool, es); spanish = es;
        HttpFixture server; QTemporaryDir dir; QVERIFY(dir.isValid());
        const QString app = dir.path() + "/app", user = dir.path() + "/user";
        writeAtomic(app + "/version.txt", "0.2.2 (melee abc)\nnetplay_protocol 6\n");
        writeAtomic(app + "/update_url.txt", server.url().toEncoded());
        Settings s; s.options["update_last_attempt"] = QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs);
        Window window(app, user, s); window.show();
        auto *toggle = window.findChild<kit::Toggle *>("atlasUpdateEnabled");
        auto *check = window.findChild<QPushButton *>("atlasUpdateCheckNow");
        auto *banner = window.findChild<QWidget *>("atlasUpdateBanner");
        auto *notes = window.findChild<QLabel *>("atlasUpdateNotes");
        auto *warning = window.findChild<QLabel *>("atlasUpdateWarning");
        auto *skip = window.findChild<QPushButton *>("atlasUpdateSkip");
        QVERIFY(toggle && check && banner && notes && warning && skip);
        QVERIFY(toggle->isChecked()); QVERIFY(banner->isHidden()); QCOMPARE(server.count, 0);
        toggle->click(); QCOMPARE(Settings::load(user).option("update_enabled"), QString("0"));
        check->click(); QTRY_COMPARE(server.count, 1); QTRY_VERIFY(!banner->isHidden());
        QCOMPARE(notes->text(), es ? QString::fromUtf8("Una actualización.") : QString("An update."));
        QCOMPARE(notes->textFormat(), Qt::PlainText);
        QVERIFY(warning->text().contains("6")); QVERIFY(warning->text().contains("7"));
        QVERIFY(!warning->isHidden()); QVERIFY(check->isEnabled());
        auto *link = window.findChild<QPushButton *>("atlasUpdateRelease"); QVERIFY(link);
        QCOMPARE(link->toolTip(), QString("https://github.com/GurekamDhillon/gd-melee-workspace/releases/tag/v0.3.0"));
        window.findChild<kit::TabRail *>("atlasRail")->setCurrent(3);
        QApplication::processEvents();
        QVERIFY(window.rect().contains(check->mapTo(&window, check->rect().center())));
        QVERIFY(window.grab().save(QCoreApplication::applicationDirPath() + (es ? "/update-banner-es.png" : "/update-banner-en.png")));
        skip->click(); QVERIFY(banner->isHidden());
        QCOMPARE(Settings::load(user).option("update_skipped_version"), QString("0.3.0"));
    }
    void long_notes_do_not_displace_play() {
        HttpFixture server; auto payload = QJsonDocument::fromJson(server.response).object();
        payload["notes_short"] = QJsonObject{{"en", QString("Release notes. ").repeated(130)}, {"es", "Notas"}};
        server.response = QJsonDocument(payload).toJson();
        QTemporaryDir dir; const QString app = dir.path() + "/app";
        writeAtomic(app + "/version.txt", "0.2.2\nnetplay_protocol 6\n"); writeAtomic(app + "/update_url.txt", server.url().toEncoded());
        Settings s; s.options["update_last_attempt"] = QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs);
        Window window(app, dir.path() + "/user", s); window.resize(900, 600); window.show();
        window.findChild<QPushButton *>("atlasUpdateCheckNow")->click();
        QTRY_VERIFY(!window.findChild<QWidget *>("atlasUpdateBanner")->isHidden());
        auto *scroll = window.findChild<QScrollArea *>("atlasUpdateNotesScroll"); QVERIFY(scroll);
        QCOMPARE(scroll->widget(), window.findChild<QLabel *>("atlasUpdateNotes"));
        QTRY_VERIFY(scroll->verticalScrollBar()->maximum() > 0);
        QVERIFY(window.height() <= 600); QVERIFY(window.findChild<QPushButton *>("atlasPlay")->isVisible());
    }
    void offline_and_session_suppression_have_no_modals() {
        QTemporaryDir dir; HttpFixture server; server.response = "malformed";
        const QString app = dir.path() + "/app", user = dir.path() + "/user";
        writeAtomic(app + "/version.txt", "0.2.2\nnetplay_protocol 6\n");
        writeAtomic(app + "/update_url.txt", server.url().toEncoded());
        Settings s; s.options["update_last_attempt"] = QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs);
        Window window(app, user, s); window.show();
        auto *check = window.findChild<QPushButton *>("atlasUpdateCheckNow"); QVERIFY(check);
        check->click(); QTRY_COMPARE(server.count, 1);
        auto *status = window.findChild<QLabel *>("atlasUpdateStatus"); QVERIFY(status);
        QTRY_VERIFY(status->text().contains("Couldn't check"));
        QVERIFY(!QApplication::activeModalWidget());
        QVERIFY(window.findChild<QWidget *>("atlasUpdateBanner")->isHidden());
        qputenv("GDMELEE_NO_UPDATE_CHECK", "1");
        Window suppressed(app, dir.path() + "/suppressed", s);
        QVERIFY(!suppressed.findChild<QPushButton *>("atlasUpdateCheckNow")->isEnabled());
        QTest::qWait(50); QCOMPARE(server.count, 1);
    }
    void creator_shutdown_keeps_checks_paused() {
#ifndef UPDATE_TEST_PYTHON
        QSKIP("Creator shutdown fixture needs Python");
#else
        HttpFixture server; QTemporaryDir dir; QVERIFY(dir.isValid());
        const QString app = dir.path() + "/app", project = dir.path() + "/project";
        QDir().mkpath(project); wbtest::makeSynthFighter(project); QDir().mkpath(project + "/.git");
        // Hold a real Creator command at its external process boundary. This
        // synthetic rebuild never starts the game or writes outside the fixture.
        writeAtomic(project + "/blocked-rebuild.py", R"(import pathlib, sys, time
root = pathlib.Path(sys.argv[1])
(root / 'entered').write_text('1')
deadline = time.monotonic() + 10
while not (root / 'release').exists() and time.monotonic() < deadline:
    time.sleep(0.01)
sys.exit(1)
)");
        auto config = QJsonDocument::fromJson(QByteArray(wbtest::kProject)).object();
        config["rebuild"] = QJsonArray{QString::fromUtf8(UPDATE_TEST_PYTHON), project + "/blocked-rebuild.py", project};
        writeAtomic(project + "/workbench.json", QJsonDocument(config).toJson());
        writeAtomic(app + "/version.txt", "0.2.2\nnetplay_protocol 6\n");
        writeAtomic(app + "/update_url.txt", server.url().toEncoded());
        Settings s; s.options["creator_enabled"] = "1"; s.options["creator_project"] = project;
        s.options["update_last_attempt"] = QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs);
        Window window(app, dir.path() + "/user", s); window.show();
        QTRY_VERIFY(window.findChild<wb::WorkbenchWindow *>());
        QPointer<wb::WorkbenchWindow> creator = window.findChild<wb::WorkbenchWindow *>();
        QTRY_VERIFY(!creator->isBusy());
        auto release = qScopeGuard([&] { writeAtomic(project + "/release", "1"); });
        creator->runCommand("rebuild", {}); QTRY_VERIFY(QFile::exists(project + "/entered"));
        auto *creatorToggle = window.findChild<QCheckBox *>("creatorEnabled"); QVERIFY(creatorToggle);
        creatorToggle->setChecked(false);
        QCOMPARE(window.findChild<QStackedWidget *>("atlasTabs")->count(), 4);
        QVERIFY(creator); QVERIFY(!creator->shutdownComplete());
        auto *toggle = window.findChild<kit::Toggle *>("atlasUpdateEnabled");
        toggle->click(); toggle->click();
        auto *check = window.findChild<QPushButton *>("atlasUpdateCheckNow"); check->click();
        QTest::qWait(60); QCOMPARE(server.count, 0); QVERIFY(!check->isEnabled());
        writeAtomic(project + "/release", "1");
        QTRY_VERIFY(!creator || creator->shutdownComplete()); QTRY_VERIFY(check->isEnabled());
        check->click(); QTRY_COMPARE(server.count, 1);
#endif
    }
};
QTEST_MAIN(UpdateUiTests)
#include "update_ui_tests.moc"
