#include "../testfixture.h"
#include "commands.h"
#include "geno_data.h"
#include "session.h"
#include "timeline.h"
#include "viewport.h"
#include "workbench_window.h"
#include "window.h"
#include "kit.h"
#include <QApplication>
#include <QCheckBox>
#include <QComboBox>
#include <QDateTime>
#include <QSemaphore>
#include <QSignalSpy>
#include <QStackedWidget>
#include <QTemporaryDir>
#include <QThread>
#include <QTimer>
#include <QWheelEvent>
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

class UiTest : public QObject {
    Q_OBJECT
private slots:
    void initTestCase() { launcher::spanish = false; launcher::applyTheme(); }
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
    void viewportOverlayToggleAndCamera() {
        Viewport v; v.resize(320, 360); v.show();
        QSignalSpy spy(&v, &Viewport::cameraChanged);
        v.setOverlay("hitboxes", false);
        QTest::mousePress(&v, Qt::LeftButton, {}, QPoint(100, 100));
        QTest::mouseMove(&v, QPoint(140, 120));
        QTest::mouseRelease(&v, Qt::LeftButton, {}, QPoint(140, 120));
        QVERIFY(!spy.isEmpty());
        const auto camera = spy.last()[0].value<QJsonObject>();
        QCOMPARE(camera.value("yaw").toDouble(), 20.0);
        QCOMPARE(camera.value("pitch").toDouble(), 10.0);
        QWheelEvent wheel(QPointF(100, 100), QPointF(100, 100), {}, QPoint(0, 120),
                          Qt::NoButton, Qt::NoModifier, Qt::NoScrollPhase, false);
        QApplication::sendEvent(&v, &wheel);
        QCOMPARE(spy.last()[0].value<QJsonObject>().value("distance").toDouble(), 36.0);
    }
    void viewportPreservesPngAspectAndFallbackToggles() {
        Viewport v; v.resize(320, 360); v.show();
        QImage png(200, 100, QImage::Format_RGB32); png.fill(Qt::magenta); v.setImage(png);
        const QImage shot = v.grab().toImage();
        QCOMPARE(shot.pixelColor(160, 180), QColor(Qt::magenta));
        QVERIFY(shot.pixelColor(160, 10) != QColor(Qt::magenta));
        v.setImage({}); FrameInfo fi; fi.bones = {{0, -1, {0, 0, 0}}, {1, 0, {3, 5, 0}}};
        v.setFrameInfo(fi); v.setOverlay("bones", true);
        const auto bones = v.grab().toImage(); v.setOverlay("bones", false);
        QVERIFY(bones != v.grab().toImage());
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
    void commandsStayOffGuiThreadAndRendersCoalesce() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); SlowEngine engine;
        engine.canned["frame"] = FrameInfo{}.toJson();
        Session s(d.path(), &engine); s.data().reload(); registerAllCommands(s); WorkbenchWindow w(s);
        QTRY_VERIFY(!w.isBusy());
        engine.blockNext = true; w.runCommand("frame_info", {});
        QTRY_VERIFY(engine.entered.available() > 0);
        bool heartbeat = false; QTimer::singleShot(0, &w, [&] { heartbeat = true; });
        w.runCommand("render_view", {{"w", 100}, {"h", 100}});
        w.runCommand("render_view", {{"w", 200}, {"h", 100}});
        w.runCommand("render_view", {{"w", 300}, {"h", 100}});
        QTRY_VERIFY(heartbeat); engine.release.release();
        QTRY_VERIFY(!w.isBusy());
        int renders = 0;
        for (const auto &call : engine.calls) if (call.first == "render") {
            ++renders; QCOMPARE(call.second.value("w").toInt(), 300);
        }
        QCOMPARE(renders, 1); QCOMPARE(engine.peak.load(), 1);
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
        QCOMPARE(engine.calls.last().first, QString("render"));
    }
    void pngWaitsForCompleteFreshFile() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); wbtest::FakeEngine engine;
        const QString png = d.filePath("view.png"); engine.canned["render"] = {{"path", png}};
        Session s(d.path(), &engine); s.data().reload(); registerAllCommands(s); WorkbenchWindow w(s); w.show();
        QTRY_VERIFY(!w.isBusy());
        w.runCommand("render_view", {});
        QTimer::singleShot(100, &w, [png] { QFile f(png); f.open(QIODevice::WriteOnly); f.write("partial"); });
        QTimer::singleShot(200, &w, [png] { QImage img(20, 10, QImage::Format_RGB32); img.fill(Qt::magenta); img.save(png); });
        QTRY_VERIFY(!w.isBusy());
        auto *v = w.findChild<Viewport *>(); QVERIFY(v);
        QCOMPARE(v->grab().toImage().pixelColor(v->width() / 2, v->height() / 2), QColor(Qt::magenta));
    }
    void aSupersededCaptureDrainsBeforeTheNextRender() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); wbtest::FakeEngine engine;
        const QString png = d.filePath("view.png"); engine.canned["render"] = {{"path", png}};
        Session s(d.path(), &engine); s.data().reload(); registerAllCommands(s); WorkbenchWindow w(s); w.show();
        QTRY_VERIFY(!w.isBusy());
        QSignalSpy done(&w, &WorkbenchWindow::commandFinished);
        w.runCommand("render_view", {{"w", 100}, {"h", 100}});
        QTRY_COMPARE(done.size(), 1); // first render has replied, its PNG has not arrived
        w.runCommand("render_view", {{"w", 200}, {"h", 100}});
        w.runCommand("render_view", {{"w", 300}, {"h", 100}});
        QTest::qWait(100); QCOMPARE(done.size(), 1); // no overlapping writes to view.png
        QImage old(20, 10, QImage::Format_RGB32); old.fill(Qt::red); QVERIFY(old.save(png));
        QTRY_COMPARE(done.size(), 2);
        QTest::qWait(20); // Ensure a distinct filesystem timestamp even on coarse clocks.
        QImage latest(20, 10, QImage::Format_RGB32); latest.fill(Qt::blue); QVERIFY(latest.save(png));
        QTRY_VERIFY(!w.isBusy());
        auto *v = w.findChild<Viewport *>(); QVERIFY(v);
        QCOMPARE(v->grab().toImage().pixelColor(v->width() / 2, v->height() / 2), QColor(Qt::blue));
        int count = 0; for (const auto &c : engine.calls) if (c.first == "render") {
            ++count; QCOMPARE(c.second.value("w").toInt(), count == 1 ? 100 : 300);
        }
        QCOMPARE(count, 2);
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
    void stalePngTimesOutInsteadOfShowingOldFrame() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); wbtest::FakeEngine engine;
        const QString png = d.filePath("view.png"); QImage img(20, 10, QImage::Format_RGB32); img.fill(Qt::magenta); QVERIFY(img.save(png));
        QFile file(png); QVERIFY(file.open(QIODevice::ReadWrite));
        QVERIFY(file.setFileTime(QDateTime::currentDateTime().addSecs(-60), QFileDevice::FileModificationTime)); file.close();
        engine.canned["render"] = {{"path", png}};
        Session s(d.path(), &engine); s.data().reload(); registerAllCommands(s); WorkbenchWindow w(s);
        QTRY_VERIFY(!w.isBusy()); w.runCommand("render_view", {});
        QTRY_VERIFY_WITH_TIMEOUT(w.statusText().contains("Screenshot timed out"), 4500);
    }
    void timedOutCaptureRequiresRestartBeforeReusingItsPath() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); wbtest::FakeEngine engine;
        const QString png = d.filePath("view.png"); engine.canned["render"] = {{"path", png}};
        Session s(d.path(), &engine); s.data().reload(); registerAllCommands(s); WorkbenchWindow w(s);
        QTRY_VERIFY(!w.isBusy()); w.runCommand("render_view", {});
        QTRY_VERIFY_WITH_TIMEOUT(w.statusText().contains("Screenshot timed out"), 4500);
        QImage late(20, 10, QImage::Format_RGB32); late.fill(Qt::red); QVERIFY(late.save(png));
        w.runCommand("render_view", {}); QTRY_VERIFY(!w.isBusy());
        int renders = 0; for (const auto &c : engine.calls) if (c.first == "render") ++renders;
        QCOMPARE(renders, 1); QVERIFY(w.statusText().contains("Restart"));
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
