#include "../testfixture.h"
#include "commands.h"
#include "geno_data.h"
#include "session.h"
#include "timeline.h"
#include "hub_panel.h"
#include "blender_launch.h"
#include "workbench_window.h"
#include "window.h"
#include "kit.h"
#include <QApplication>
#include <QCheckBox>
#include <QComboBox>
#include <QElapsedTimer>
#include <QEventLoop>
#include <QDockWidget>
#include <QLabel>
#include <QLineEdit>
#include <QMessageBox>
#include <QTcpSocket>
#include <QSemaphore>
#include <QSignalSpy>
#include <QStackedWidget>
#include <QTemporaryDir>
#include <QThread>
#include <QTimer>
#include <QtTest>
#include <atomic>
using namespace wb;

// Only the external engine is replaced. Registry dispatch and the entire UI are real.
class SlowEngine : public wbtest::FakeEngine {
public:
    QSemaphore entered, release;
    std::atomic<bool> blockNext{false};
    std::atomic<int> active{0}, peak{0};
    QVector<QThread *> threads;
    QJsonObject call(const QString &fn, const QJsonObject &args, QString *err) override {
        const int now = ++active;
        peak.store(std::max(peak.load(), now));
        threads.append(QThread::currentThread());
        if (blockNext.exchange(false)) {
            entered.release();
            release.tryAcquire(1, 3000); // A failed assertion must not strand the worker.
        }
        auto result = FakeEngine::call(fn, args, err);
        if (fn == "frame" && failWith.isEmpty()) {
            FrameInfo fi; fi.frame = args.value("frame").toInt(); fi.motion = args.value("motion").toInt(); result = fi.toJson();
        }
        --active;
        return result;
    }
};


namespace {
class ScopedEnvironment {
    QByteArray name_, value_; bool existed_;
public:
    ScopedEnvironment(const char *name, const QByteArray &value)
        : name_(name), value_(qgetenv(name)), existed_(qEnvironmentVariableIsSet(name)) { qputenv(name, value); }
    ~ScopedEnvironment() { if (existed_) qputenv(name_.constData(), value_); else qunsetenv(name_.constData()); }
};
QByteArray toolRequest(const QString &name, const QJsonObject &args = {}) {
    return QJsonDocument(QJsonObject{{"jsonrpc", "2.0"}, {"id", 1}, {"method", "tools/call"},
        {"params", QJsonObject{{"name", name}, {"arguments", args}}}}).toJson(QJsonDocument::Compact) + '\n';
}
QJsonObject toolPayload(const QJsonObject &reply) {
    const auto content = reply["result"].toObject()["content"].toArray();
    return content.isEmpty() ? QJsonObject{} : QJsonDocument::fromJson(content[0].toObject()["text"].toString().toUtf8()).object();
}
}

class UiTest : public QObject {
    Q_OBJECT
private slots:
    void initTestCase() { launcher::spanish = false; launcher::applyTheme(); }
    void playLabUsesCurrentProjectAndRowThroughSharedTool() {
        ScopedEnvironment python("GW_PYTHON", WB_PLAY_HELPER);
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path());
        wbtest::put(dir.path(), ".git", "gitdir: unused");
        wbtest::put(dir.path(), "tools/geno/play.py", "# synthetic, helper substitutes only process boundary");
        Session s(dir.path(), nullptr); s.data().reload(); registerAllCommands(s);
        WorkbenchWindow w(s); QTRY_VERIFY(!w.isBusy());
        w.runCommand("load_row", {{"row", "dair"}}); QTRY_VERIFY(!w.isBusy());
        auto *button = w.findChild<QPushButton *>("wbPlayLab"); QVERIFY(button); QVERIFY(button->isEnabled());
        button->click(); QTRY_VERIFY(!w.isBusy());
        QFile request(dir.filePath(".play-requests.json")); QVERIFY(request.open(QIODevice::ReadOnly));
        const auto calls = QJsonDocument::fromJson(request.readAll()).array(); QCOMPARE(calls.size(), 2);
        const auto check = calls[0].toArray(), launch = calls[1].toArray();
        QCOMPARE(check[0].toString(), dir.filePath("tools/geno/play.py"));
        QCOMPARE(check[2].toString(), dir.path()); QVERIFY(check.contains("--check"));
        QVERIFY(launch.contains("--lab")); QVERIFY(launch.contains("--clip")); QVERIFY(launch.contains("dair"));
        QVERIFY(!launch.contains("--check")); QVERIFY(!launch.contains("--rebuild"));
        QVERIFY(w.statusText().contains("melee-pc.log"));
    }
    void playVsCpuDoesNotRequestClips() {
        ScopedEnvironment python("GW_PYTHON", WB_PLAY_HELPER);
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path());
        wbtest::put(dir.path(), ".git", "gitdir: unused"); wbtest::put(dir.path(), "tools/geno/play.py", "# synthetic");
        Session s(dir.path(), nullptr); s.data().reload(); registerAllCommands(s);
        WorkbenchWindow w(s); QTRY_VERIFY(!w.isBusy());
        auto *button = w.findChild<QPushButton *>("wbPlayCpu"); QVERIFY(button); button->click();
        QTRY_VERIFY(!w.isBusy()); QFile request(dir.filePath(".play-requests.json")); QVERIFY(request.open(QIODevice::ReadOnly));
        const auto calls = QJsonDocument::fromJson(request.readAll()).array(); QCOMPARE(calls.size(), 2);
        const auto args = calls[1].toArray(); QVERIFY(args.contains("--vs")); QVERIFY(args.contains("cpu"));
        QVERIFY(!args.contains("--clip")); QVERIFY(!args.contains("--lab"));
    }
    void stalePlayOffersRebuildAndCanBeCancelled() {
        ScopedEnvironment python("GW_PYTHON", WB_PLAY_HELPER), stale("WB_PLAY_HELPER_STALE", "1");
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path());
        wbtest::put(dir.path(), ".git", "gitdir: unused"); wbtest::put(dir.path(), "tools/geno/play.py", "# synthetic");
        Session s(dir.path(), nullptr); s.data().reload(); registerAllCommands(s);
        WorkbenchWindow w(s); QTRY_VERIFY(!w.isBusy()); w.findChild<QPushButton *>("wbPlayLab")->click();
        QTRY_VERIFY(w.findChild<QMessageBox *>("wbPlayRebuild") != nullptr);
        auto *dialog = w.findChild<QMessageBox *>("wbPlayRebuild");
        QVERIFY(w.isBusy()); QVERIFY(!w.findChild<QPushButton *>("wbPlayLab")->isEnabled());
        dialog->button(QMessageBox::Cancel)->click(); QTRY_VERIFY(!w.isBusy());
        QFile request(dir.filePath(".play-requests.json")); QVERIFY(request.open(QIODevice::ReadOnly));
        QCOMPARE(QJsonDocument::fromJson(request.readAll()).array().size(), 1);
    }
    void acceptedRebuildKeepsSelectionAndFailureIsVisible() {
        ScopedEnvironment python("GW_PYTHON", WB_PLAY_HELPER), stale("WB_PLAY_HELPER_STALE", "1"),
                          fail("WB_PLAY_HELPER_FAIL", "1");
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path());
        wbtest::put(dir.path(), ".git", "gitdir: unused"); wbtest::put(dir.path(), "tools/geno/play.py", "# synthetic");
        Session s(dir.path(), nullptr); s.data().reload(); registerAllCommands(s);
        WorkbenchWindow w(s); QTRY_VERIFY(!w.isBusy());
        w.findChild<QPushButton *>("wbPlayLab")->click();
        QTRY_VERIFY(w.findChild<QMessageBox *>("wbPlayRebuild") != nullptr);
        auto *accept = w.findChild<QPushButton *>("wbPlayRebuildAccept"); QVERIFY(accept); accept->click();
        QTRY_VERIFY(!w.isBusy()); QVERIFY(w.statusText().contains("synthetic rebuild refused"));
        QFile request(dir.filePath(".play-requests.json")); QVERIFY(request.open(QIODevice::ReadOnly));
        const auto calls = QJsonDocument::fromJson(request.readAll()).array(); QCOMPARE(calls.size(), 2);
        QVERIFY(calls[1].toArray().contains("--rebuild")); QVERIFY(calls[1].toArray().contains("jab1"));
    }
    void timelineKeysEmitFrames() {
        Timeline t; t.setRange(40); t.setFrame(10); t.show();
        QSignalSpy spy(&t, &Timeline::frameRequested);
        QTest::keyClick(&t, Qt::Key_L); QTest::keyClick(&t, Qt::Key_J); QTest::keyClick(&t, Qt::Key_J);
        QCOMPARE(spy.size(), 3);
        QCOMPARE(spy[0][0].toInt(), 11); QCOMPARE(spy[1][0].toInt(), 10); QCOMPARE(spy[2][0].toInt(), 9);
    }
    void timelineClampsAtEndsAndHandlesEmptyRange() {
        Timeline t; t.setRange(5); t.setFrame(4);
        QSignalSpy spy(&t, &Timeline::frameRequested);
        QTest::keyClick(&t, Qt::Key_L); QVERIFY(spy.isEmpty() || spy.last()[0].toInt() == 4);
        t.setFrame(0); spy.clear(); QTest::keyClick(&t, Qt::Key_J);
        QVERIFY(spy.isEmpty() || spy.last()[0].toInt() == 0);
        t.setRange(0); spy.clear(); QTest::keyClick(&t, Qt::Key_End);
        QVERIFY(spy.isEmpty());
    }
    void timelineHomeEndPlayAndClick() {
        Timeline t; t.resize(400, 150); t.setRange(40); t.setFrame(10); t.show();
        QSignalSpy frames(&t, &Timeline::frameRequested), play(&t, &Timeline::playToggled);
        QTest::keyClick(&t, Qt::Key_Home); QTest::keyClick(&t, Qt::Key_End);
        QCOMPARE(frames[0][0].toInt(), 0); QCOMPARE(frames[1][0].toInt(), 39);
        QTest::keyClick(&t, Qt::Key_K); QTest::keyClick(&t, Qt::Key_K);
        QCOMPARE(play.size(), 2); QCOMPARE(play[0][0].toBool(), true); QCOMPARE(play[1][0].toBool(), false);
        frames.clear(); QTest::mouseClick(&t, Qt::LeftButton, {}, QPoint(200, 35));
        QCOMPARE(frames.size(), 1); QVERIFY(frames[0][0].toInt() >= 18 && frames[0][0].toInt() <= 21);
    }
    void timelineCursorAndActiveBarUseTheSameFramePositions() {
        Timeline t; t.resize(400, 100); t.setRange(5); t.setFrame(3);
        t.setBars({{"synthetic", {3, 4}}}); t.show();
        const auto image = t.grab().toImage();
        // A five-cell ruler places frame 3 at x=238 (padding 12, usable width 376).
        QCOMPARE(image.pixelColor(238, 30), launcher::atlas::colour("ember"));
        QCOMPARE(image.pixelColor(242, 76), launcher::atlas::colour("jade"));
    }
    void hubReplacesViewerAndExplainsMissingBlender() {
        ScopedEnvironment path("PATH", ""), blender("GW_BLENDER", "");
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path()); Session s(dir.path(), nullptr);
        s.data().reload(); registerAllCommands(s); WorkbenchWindow w(s);
        QTRY_VERIFY(!w.isBusy());
        QVERIFY(qobject_cast<HubPanel *>(w.centralWidget()));
        QVERIFY(w.findChild<QWidget *>("viewport") == nullptr);
        auto *open = w.findChild<QPushButton *>("openInBlender"); QVERIFY(open);
        QVERIFY(!open->isEnabled()); QVERIFY(open->toolTip().contains("GW_BLENDER"));
        QCOMPARE(w.findChild<QLabel *>("wbProjectName")->text(), QString("synth"));
        QVERIFY(w.findChild<QLabel *>("wbProjectCounts")->text().contains("2"));
        QVERIFY(w.findChild<QLabel *>("wbProjectCounts")->text().contains("3"));
        for (const QString &name : {"wbOutlinerDock", "wbInspectorDock", "wbProblemsDock", "wbClipsDock", "wbFidelityDock", "wbReviewDock"})
            QVERIFY(w.findChild<QDockWidget *>(name));
    }
    void serveForBlenderReusesHumanSessionAndClosesWithHub() {
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path()); Session s(dir.path(), nullptr);
        s.data().reload(); registerAllCommands(s); WorkbenchWindow w(s); QTRY_VERIFY(!w.isBusy());
        const quint16 port = w.serveForBlender(); QVERIFY(port != 0); QCOMPARE(w.serveForBlender(), port);
        QTcpSocket socket; socket.connectToHost(QHostAddress::LocalHost, port);
        QTRY_COMPARE(socket.state(), QAbstractSocket::ConnectedState);
        QCOMPARE(socket.peerAddress(), QHostAddress(QHostAddress::LocalHost));
        QSignalSpy done(&w, &WorkbenchWindow::commandFinished);
        socket.write(toolRequest("edit_hitbox", {{"row", "jab1"}, {"ordinal", 0}, {"damage", 9}}));
        QTRY_VERIFY(socket.canReadLine());
        const auto edit = QJsonDocument::fromJson(socket.readLine()).object();
        QVERIFY(!edit["result"].toObject()["isError"].toBool()); QVERIFY(toolPayload(edit)["applied"].toBool());
        QTRY_VERIFY(!done.isEmpty()); QTRY_VERIFY(!w.isBusy());
        // Reading the synthetic source confirms the socket used this Session's actual store.
        QFile source(dir.filePath("moves/jab1.genoasm")); QVERIFY(source.open(QIODevice::ReadOnly));
        QVERIFY(source.readAll().contains("damage=9")); source.close(); // Windows cannot replace a file that is still open
        socket.write(toolRequest("history")); QTRY_VERIFY(socket.canReadLine());
        const auto history = toolPayload(QJsonDocument::fromJson(socket.readLine()).object());
        const auto entries = history["entries"].toArray(); QCOMPARE(entries.size(), 1);
        QCOMPARE(entries[0].toObject()["author"].toString(), QString("human"));
        socket.write(toolRequest("undo")); QTRY_VERIFY(socket.canReadLine());
        QVERIFY(!QJsonDocument::fromJson(socket.readLine()).object()["result"].toObject()["isError"].toBool());
        QTRY_VERIFY(!w.isBusy()); source.close(); QVERIFY(source.open(QIODevice::ReadOnly));
        QVERIFY(source.readAll().contains("damage=3")); source.close();
        QSignalSpy stopped(&w, &WorkbenchWindow::shutdownFinished); w.shutdown();
        QTRY_COMPARE(stopped.size(), 1); QTRY_COMPARE(socket.state(), QAbstractSocket::UnconnectedState);
        QCOMPARE(w.serveForBlender(), quint16(0));
    }
    void openInBlenderRefreshesStatusAfterIdleEngineDeath() {
        ScopedEnvironment blender("GW_BLENDER", "synthetic-missing-blender-executable");
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path());
        wbtest::put(dir.path(), ".git", "gitdir: unused\n");
        wbtest::put(dir.path(), "tools/blender/geno_workbench/bootstrap.py", "# synthetic\n");
        wbtest::put(dir.path(), "fighter.blend", "synthetic path fixture, never opened");
        auto project = QJsonDocument::fromJson(wbtest::kProject).object(); project["art_blend"] = "fighter.blend";
        wbtest::put(dir.path(), "workbench.json", QJsonDocument(project).toJson());
        wbtest::FakeEngine engine; Session s(dir.path(), &engine); s.data().reload(); registerAllCommands(s);
        WorkbenchWindow w(s); QTRY_VERIFY(!w.isBusy());
        auto *open = w.findChild<QPushButton *>("openInBlender"); QVERIFY(open); QVERIFY(open->isEnabled());
        QVERIFY(w.findChild<QLabel *>("wbEngineStatus")->text().contains("running"));
        // Simulate death with no intervening command/snapshot. Refuse the restart
        // so this test never starts Blender, even on a developer's machine.
        engine.state = "stopped"; engine.failWith = "synthetic restart refused";
        open->click(); QTRY_VERIFY(!w.isBusy());
        int restarts = 0; for (const auto &call : engine.calls) if (call.first == "restart") ++restarts;
        QCOMPARE(restarts, 1); QVERIFY(w.statusText().contains("synthetic restart refused"));
        QVERIFY(w.findChild<QLabel *>("wbEngineStatus")->text().contains("not running"));
    }
    void shutdownWaitsForAnEventPumpingSocketCommand() {
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path()); Session s(dir.path(), nullptr);
        s.data().reload(); registerAllCommands(s);
        std::atomic<bool> entered{false}, release{false}, finished{false};
        s.registry().add({"slow_read", "Synthetic event-pumping read", commandSchema(), false,
            [&](const QJsonObject &, CommandContext &) {
                QEventLoop loop; QTimer poll; poll.setInterval(5);
                connect(&poll, &QTimer::timeout, &loop, [&] { if (release.load()) loop.quit(); });
                QTimer::singleShot(3000, &loop, &QEventLoop::quit); poll.start(); entered = true; loop.exec();
                finished = true; return QJsonObject{{"read", true}};
            }});
        WorkbenchWindow w(s); QTRY_VERIFY(!w.isBusy());
        QTcpSocket socket; socket.connectToHost(QHostAddress::LocalHost, w.serveForBlender());
        QTRY_COMPARE(socket.state(), QAbstractSocket::ConnectedState);
        socket.write(toolRequest("slow_read")); QTRY_VERIFY(entered.load());
        QSignalSpy stopped(&w, &WorkbenchWindow::shutdownFinished); w.shutdown();
        bool heartbeat = false; QTimer::singleShot(0, &w, [&] { heartbeat = true; });
        QTRY_VERIFY(heartbeat); QVERIFY(stopped.isEmpty()); QVERIFY(!finished.load());
        release = true; QTRY_COMPARE(stopped.size(), 1); QVERIFY(finished.load());
        QTRY_COMPARE(socket.state(), QAbstractSocket::UnconnectedState); QVERIFY(w.shutdownComplete());
    }
    void eventPumpingMcpCallDefersUiEdits() {
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path()); Session s(dir.path(), nullptr);
        s.data().reload(); registerAllCommands(s);
        std::atomic<bool> entered{false}, editedDuringCall{false};
        s.registry().add({"slow_read", "Synthetic event-pumping read", commandSchema(), false,
            [&](const QJsonObject &, CommandContext &ctx) {
                entered = true; QEventLoop loop;
                QTimer::singleShot(200, &loop, &QEventLoop::quit); loop.exec();
                editedDuringCall = !ctx.session.history().entries().isEmpty();
                return QJsonObject{{"read", true}};
            }});
        WorkbenchWindow w(s); QTRY_VERIFY(!w.isBusy());
        QTcpSocket socket; socket.connectToHost(QHostAddress::LocalHost, w.serveForBlender());
        QTRY_COMPARE(socket.state(), QAbstractSocket::ConnectedState);
        socket.write(toolRequest("slow_read")); QTRY_VERIFY(entered.load());
        w.runCommand("edit_hitbox", {{"row", "jab1"}, {"ordinal", 0}, {"damage", 7}, {"propose", true}});
        bool heartbeat = false; QTimer::singleShot(0, &w, [&] { heartbeat = true; }); QTRY_VERIFY(heartbeat);
        QTRY_VERIFY(socket.canReadLine()); QVERIFY(toolPayload(QJsonDocument::fromJson(socket.readLine()).object())["read"].toBool());
        QTRY_VERIFY(!w.isBusy()); QVERIFY(!editedDuringCall.load());
        QCOMPARE(s.history().entries().size(), 1);
    }
    void debugRenderRemainsCallableWithoutWaitingForAnImage() {
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path()); wbtest::FakeEngine engine;
        engine.canned["render"] = {{"path", dir.filePath("never-created.png")}};
        Session s(dir.path(), &engine); s.data().reload(); registerAllCommands(s); WorkbenchWindow w(s);
        QTRY_VERIFY(!w.isBusy()); QSignalSpy done(&w, &WorkbenchWindow::commandFinished);
        w.runCommand("set_camera", {{"yaw", 30}}); w.runCommand("set_overlays", {{"bones", true}});
        w.runCommand("render_view", {{"w", 320}, {"h", 240}}); QTRY_VERIFY(!w.isBusy());
        QCOMPARE(done.size(), 3); QVERIFY(done.last()[1].toJsonObject()["ok"].toBool());
        QCOMPARE(engine.calls.size(), 1); QCOMPARE(engine.calls[0].first, QString("render"));
        QCOMPARE(engine.calls[0].second["camera"].toObject()["yaw"].toInt(), 30);
        QVERIFY(engine.calls[0].second["overlays"].toObject()["bones"].toBool());
    }
    void modeToggleRecreatesEngineLaunchWithoutStartingOnOpen() {
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path()); std::atomic<int> launches{0};
        WorkbenchWindow w(dir.path(), [&] { ++launches; return EngineLink::Launch{}; });
        QTRY_VERIFY(!w.isBusy()); QCOMPARE(launches.load(), 0);
        auto *headless = w.findChild<QCheckBox *>("wbHeadless"); QVERIFY(headless); QVERIFY(headless->isChecked());
        auto *start = w.findChild<QPushButton *>("wbStart"); QVERIFY(start); start->click();
        QTRY_VERIFY(!w.isBusy()); QCOMPARE(launches.load(), 1);
        headless->setChecked(false); QTRY_VERIFY(!w.isBusy()); QCOMPARE(launches.load(), 2);
        headless->setChecked(true); QTRY_VERIFY(!w.isBusy()); QCOMPARE(launches.load(), 3);
    }
    void blenderSettingPersists() {
        QTemporaryDir dir; launcher::Window w(dir.path(), dir.path(), {});
        auto *path = w.findChild<QLineEdit *>("blenderExe"); QVERIFY(path);
        path->setText("C:/Artist Tools/Blender/blender.exe");
        QVERIFY(QMetaObject::invokeMethod(path, "editingFinished", Qt::DirectConnection));
        QCOMPARE(launcher::Settings::load(dir.path()).option("blender_exe"), path->text());
        QVERIFY(w.findChild<QPushButton *>("blenderBrowse"));
    }
    void windowRunsACommandOffline() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); Session s(d.path(), nullptr);
        s.data().reload(); registerAllCommands(s); WorkbenchWindow w(s);
        QSignalSpy done(&w, &WorkbenchWindow::commandFinished);
        w.runCommand("list_rows", {});
        QTRY_VERIFY(!w.isBusy());
        QVERIFY(!done.isEmpty()); QVERIFY(done.last()[1].toJsonObject().value("ok").toBool());
        auto *rows = w.findChild<QComboBox *>("wbRows"); QVERIFY(rows); QCOMPARE(rows->count(), 2);
    }
    void renderWithoutEngineShowsStatusNotCrash() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); Session s(d.path(), nullptr);
        s.data().reload(); registerAllCommands(s); WorkbenchWindow w(s); w.show();
        w.runCommand("render_view", {});
        QTRY_VERIFY(w.statusText().contains("Engine not running"));
    }
    void commandsStayOffGuiThreadAndSeeksCoalesce() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); SlowEngine engine;
        engine.canned["frame"] = FrameInfo{}.toJson();
        Session s(d.path(), &engine); s.data().reload(); registerAllCommands(s); WorkbenchWindow w(s);
        QTRY_VERIFY(!w.isBusy());
        w.runCommand("load_row", {{"row", "jab1"}}); QTRY_VERIFY(!w.isBusy()); engine.calls.clear();
        engine.blockNext = true; w.runCommand("frame_info", {});
        QTRY_VERIFY(engine.entered.available() > 0);
        bool heartbeat = false; QTimer::singleShot(0, &w, [&] { heartbeat = true; });
        w.runCommand("set_frame", {{"frame", 10}});
        w.runCommand("set_frame", {{"frame", 11}});
        w.runCommand("set_frame", {{"frame", 12}});
        QTRY_VERIFY(heartbeat); engine.release.release();
        QTRY_VERIFY(!w.isBusy());
        int seeks = 0;
        for (const auto &call : engine.calls) if (call.first == "frame") {
            ++seeks; QCOMPARE(call.second.value("frame").toInt(), 12);
        }
        QCOMPARE(seeks, 1); QCOMPARE(engine.peak.load(), 1);
        for (auto *thread : engine.threads) QVERIFY(thread != qApp->thread());
        QVERIFY(!engine.threads.isEmpty());
        for (auto *thread : engine.threads) QCOMPARE(thread, engine.threads.first());
    }
    void cameraChangesDoNotCancelLoadingTheSelectedMove() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); SlowEngine engine;
        Session s(d.path(), &engine); s.data().reload(); registerAllCommands(s); WorkbenchWindow w(s);
        QTRY_VERIFY(!w.isBusy()); engine.blockNext = true;
        w.runCommand("load_row", {{"row", "dair"}});
        QTRY_VERIFY(engine.entered.available() > 0);
        w.runCommand("set_camera", {{"yaw", 30}}); w.runCommand("set_overlays", {{"bones", true}});
        engine.release.release(); QTRY_VERIFY(!w.isBusy());
        bool selected = false;
        for (const auto &c : engine.calls) if (c.first == "frame") {
            selected = true; QCOMPARE(c.second.value("motion").toInt(), 70); QCOMPARE(c.second.value("frame").toInt(), 0);
        }
        QVERIFY(selected);
        QCOMPARE(w.findChild<QComboBox *>("wbRows")->currentData().toString(), QString("dair"));
    }
    void explicitSeekAfterLoadIsNotReplacedByFrameZero() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); SlowEngine engine;
        Session s(d.path(), &engine); s.data().reload(); registerAllCommands(s); WorkbenchWindow w(s);
        QTRY_VERIFY(!w.isBusy()); engine.blockNext = true;
        w.runCommand("load_row", {{"row", "dair"}}); QTRY_VERIFY(engine.entered.available() > 0);
        w.runCommand("set_frame", {{"frame", 12}}); w.runCommand("set_camera", {{"yaw", 30}});
        engine.release.release(); QTRY_VERIFY(!w.isBusy());
        int seeks = 0; for (const auto &c : engine.calls) if (c.first == "frame") {
            ++seeks; QCOMPARE(c.second.value("frame").toInt(), 12);
        }
        QCOMPARE(seeks, 1); QCOMPARE(w.findChild<Timeline *>()->frame(), 12);
        w.runCommand("reload", {}); QTRY_VERIFY(!w.isBusy());
        QCOMPARE(w.findChild<Timeline *>()->frame(), 12);
        for (const auto &c : engine.calls) QVERIFY(c.first != "render");
    }
    void shutdownWaitsAsynchronouslyAndDropsPendingCommands() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); SlowEngine engine;
        Session s(d.path(), &engine); s.data().reload(); registerAllCommands(s); WorkbenchWindow w(s);
        QTRY_VERIFY(!w.isBusy()); engine.blockNext = true; w.runCommand("frame_info", {});
        QTRY_VERIFY(engine.entered.available() > 0);
        w.runCommand("render_view", {}); QSignalSpy stopped(&w, &WorkbenchWindow::shutdownFinished);
        w.shutdown(); bool heartbeat = false; QTimer::singleShot(0, &w, [&] { heartbeat = true; });
        QTRY_VERIFY(heartbeat); QVERIFY(stopped.isEmpty()); engine.release.release();
        QTRY_COMPARE(stopped.size(), 1); QVERIFY(w.shutdownComplete());
        for (const auto &c : engine.calls) QVERIFY(c.first != "render");
    }
    void editReloadsByRestartAndProposalsDoNotRestart() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); wbtest::FakeEngine engine;
        Session s(d.path(), &engine); s.data().reload(); registerAllCommands(s); WorkbenchWindow w(s);
        QTRY_VERIFY(!w.isBusy());
        w.runCommand("edit_hitbox", {{"row", "jab1"}, {"ordinal", 0}, {"damage", 7}});
        QTRY_VERIFY(!w.isBusy());
        int restarts = 0; for (const auto &c : engine.calls) if (c.first == "restart") ++restarts;
        QCOMPARE(restarts, 1);
        w.runCommand("edit_hitbox", {{"row", "jab1"}, {"ordinal", 0}, {"damage", 8}, {"propose", true}});
        QTRY_VERIFY(!w.isBusy());
        restarts = 0; for (const auto &c : engine.calls) if (c.first == "restart") ++restarts;
        QCOMPARE(restarts, 1);
    }
    void ownedProjectDoesNotLaunchUntilStartAndShutsDownCleanly() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); std::atomic<int> launches{0};
        WorkbenchWindow w(d.path(), [&] { ++launches; return EngineLink::Launch{}; });
        QTRY_VERIFY(!w.isBusy()); QCOMPARE(launches.load(), 0);
        QCOMPARE(w.findChild<QComboBox *>("wbRows")->count(), 2);
        QSignalSpy stopped(&w, &WorkbenchWindow::shutdownFinished); w.shutdown();
        QTRY_COMPARE(stopped.size(), 1); QVERIFY(w.shutdownComplete()); QCOMPARE(launches.load(), 0);
    }
    void creatorSettingAddsAndRemovesRailEntry() {
        QTemporaryDir d; launcher::Window w(d.path(), d.path(), {});
        auto *tabs = w.findChild<QStackedWidget *>("atlasTabs"); QVERIFY(tabs); QCOMPARE(tabs->count(), 4);
        auto *enable = w.findChild<QCheckBox *>("creatorEnabled"); QVERIFY(enable);
        enable->setChecked(true); QCOMPARE(tabs->count(), 5);
        QVERIFY(launcher::Settings::load(d.path()).flag("creator_enabled"));
        auto *rail = w.findChild<launcher::kit::TabRail *>("atlasRail"); QVERIFY(rail); rail->setCurrent(4);
        QCOMPARE(tabs->currentIndex(), 4);
        enable->setChecked(false); QCOMPARE(tabs->count(), 4); QCOMPARE(rail->current(), 0);
        QVERIFY(!launcher::Settings::load(d.path()).flag("creator_enabled"));
    }
};
QTEST_MAIN(UiTest)
#include "ui_test.moc"
