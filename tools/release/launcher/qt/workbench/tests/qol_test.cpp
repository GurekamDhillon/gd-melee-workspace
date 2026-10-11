#include "../testfixture.h"
#include "atlas_widgets.h"
#include "commands.h"
#include "error_help.h"
#include "geno_data.h"
#include "history.h"
#include "hub_panel.h"
#include "panels.h"
#include "recovery.h"
#include "session.h"
#include "timeline.h"
#include "window.h"
#include "workbench_window.h"
#include <QApplication>
#include <QComboBox>
#include <QDateTime>
#include <QDialog>
#include <QLabel>
#include <QLineEdit>
#include <QPushButton>
#include <QSemaphore>
#include <QSignalSpy>
#include <QTemporaryDir>
#include <QtTest>
#include <atomic>
using namespace wb;

namespace {
constexpr qint64 kDeadPid = 2147483000;
class ScopedEnvironment {
    QByteArray name_, value_; bool existed_;
public:
    ScopedEnvironment(const char *name, const QByteArray &value)
        : name_(name), value_(qgetenv(name)), existed_(qEnvironmentVariableIsSet(name)) { qputenv(name, value); }
    ~ScopedEnvironment() { if (existed_) qputenv(name_.constData(), value_); else qunsetenv(name_.constData()); }
};
// Answers `frame` like a running game does; everything else is the plain fake.
class FrameEngine : public wbtest::FakeEngine {
public:
    QJsonObject call(const QString &fn, const QJsonObject &args, QString *err) override {
        auto result = FakeEngine::call(fn, args, err);
        if (fn == "frame" && failWith.isEmpty()) {
            FrameInfo fi; fi.frame = args.value("frame").toInt(); fi.motion = args.value("motion").toInt(); result = fi.toJson();
        }
        return result;
    }
};
QByteArray readAll(const QString &dir, const QString &rel) {
    QFile f(QDir(dir).filePath(rel));
    return f.open(QIODevice::ReadOnly) ? f.readAll() : QByteArray();
}
void writeFile(const QString &dir, const QString &rel, const QByteArray &bytes) {
    QFile f(QDir(dir).filePath(rel));
    QVERIFY(f.open(QIODevice::WriteOnly | QIODevice::Truncate)); f.write(bytes);
}
void plantDeadMark(const QString &dir, qint64 ago) {
    QDir().mkpath(QDir(dir).filePath(".workbench"));
    writeFile(dir, ".workbench/session.lock.json",
              QJsonDocument(QJsonObject{{"pid", kDeadPid}, {"started", QDateTime::currentSecsSinceEpoch() - ago}}).toJson());
}
HitboxEdit damageEdit(double d) { HitboxEdit e; e.damage = d; return e; }
QPushButton *fixButton(WorkbenchWindow &w) { return w.findChild<QPushButton *>("wbStatusFix"); }
bool fixShown(WorkbenchWindow &w) { auto *b = fixButton(w); return b && !b->isHidden(); }
}

class QolTest : public QObject {
    Q_OBJECT
    // A window over a borrowed session with the whole command set, ready and idle.
    struct Bench {
        QTemporaryDir dir; FrameEngine engine; Session session; std::unique_ptr<WorkbenchWindow> window;
        explicit Bench(bool registerAll = true) : session((wbtest::makeSynthFighter(dir.path()), dir.path()), &engine) {
            session.data().reload();
            if (registerAll) registerAllCommands(session);
        }
        void open() { window = std::make_unique<WorkbenchWindow>(session); window->resize(1440, 900); window->show();
                      QVERIFY(QTest::qWaitForWindowActive(window.get())); QTRY_VERIFY(!window->isBusy()); }
        WorkbenchWindow &w() { return *window; }
    };
private slots:
    void initTestCase() { qputenv("GW_BLENDER_DISCOVERY", "0"); launcher::spanish = false; launcher::applyTheme(); }

    // ---- R1: every failure says what to do, and the Fix button does it --------------------------------------------
    void engineNotRunningOffersStartGame() {
        Bench b; b.open(); auto &w = b.w();
        b.engine.failWith = "engine not running";
        w.runCommand("render_view", {}); QTRY_VERIFY(!w.isBusy());
        QVERIFY2(w.statusText().contains("Engine not running") && w.statusText().contains("Start the game"), qPrintable(w.statusText()));
        QVERIFY(fixShown(w)); QCOMPARE(fixButton(w)->text(), QString("Start game"));
        QCOMPARE(fixButton(w)->property("fix").toString(), fixName(FixKind::StartGame));
        b.engine.failWith.clear(); b.engine.calls.clear();
        fixButton(w)->click(); QTRY_VERIFY(!w.isBusy());
        int restarts = 0; for (const auto &c : b.engine.calls) if (c.first == "restart") ++restarts;
        QCOMPARE(restarts, 1);
        QVERIFY(!fixShown(w)); QCOMPARE(w.statusText(), QString("Ready"));
    }
    void missingGameExeOffersThePicker() {
        Bench b; b.open(); auto &w = b.w();
        QSignalSpy picker(&w, &WorkbenchWindow::gameExePickRequested);
        b.engine.failWith = "Game executable not found. Set Game exe in Settings or GW_ENGINE_EXE. Looked in: nowhere";
        w.runCommand("engine_restart", {}); QTRY_VERIFY(!w.isBusy());
        QVERIFY(fixShown(w)); QCOMPARE(fixButton(w)->text(), QString("Choose game exe…"));
        QVERIFY(w.statusText().contains("nowhere")); // the raw reason survives
        fixButton(w)->click(); QCOMPARE(picker.size(), 1);
    }
    void missingBlenderOffersThePicker() {
        ScopedEnvironment path("PATH", ""), blender("GW_BLENDER", "");
        Bench b; b.open(); auto &w = b.w();
        QSignalSpy picker(&w, &WorkbenchWindow::blenderPickRequested);
        w.findChild<QPushButton *>("wbShowBlender")->click(); // Blender is not running and cannot be found
        QVERIFY2(w.statusText().contains("Blender"), qPrintable(w.statusText()));
        QVERIFY(fixShown(w)); QCOMPARE(fixButton(w)->text(), QString("Choose Blender…"));
        fixButton(w)->click(); QCOMPARE(picker.size(), 1);
    }
    void blenderClosedOffersStartBlender() {
        ScopedEnvironment blender("GW_BLENDER", "synthetic-missing-blender-executable");
        Bench b;
        wbtest::put(b.dir.path(), ".git", "gitdir: unused\n");
        wbtest::put(b.dir.path(), "tools/blender/geno_workbench/bootstrap.py", "# synthetic\n");
        wbtest::put(b.dir.path(), "fighter.blend", "synthetic path fixture, never opened");
        auto project = QJsonDocument::fromJson(wbtest::kProject).object(); project["art_blend"] = "fighter.blend";
        wbtest::put(b.dir.path(), "workbench.json", QJsonDocument(project).toJson());
        b.session.data().reload();
        b.open(); auto &w = b.w();
        w.setBlenderProcessId(kDeadPid); // a Blender that was open and is gone
        QTRY_VERIFY_WITH_TIMEOUT(fixShown(w) && fixButton(w)->text() == "Start Blender", 5000);
        QVERIFY(w.statusText().contains("Blender was closed"));
        // The Fix runs the same path as Open in Blender: with the engine idle it restarts it first.
        b.engine.state = "stopped"; b.engine.failWith = "synthetic restart refused"; b.engine.calls.clear();
        fixButton(w)->click(); QTRY_VERIFY(!w.isBusy());
        int restarts = 0; for (const auto &c : b.engine.calls) if (c.first == "restart") ++restarts;
        QCOMPARE(restarts, 1); QVERIFY(w.statusText().contains("synthetic restart refused"));
    }
    void failedRebuildExplainsAndOffersRebuildAgain() {
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path()); FrameEngine engine;
        Session s(dir.path(), &engine); s.data().reload();
        registerViewCommands(s); registerRowCommands(s); registerHitboxCommands(s);
        int builds = 0; bool fail = true;
        s.registry().add({"rebuild", "Synthetic rebuild", commandSchema(), false, [&](const QJsonObject &, CommandContext &) {
            ++builds; if (fail) throw CommandError{"rebuild failed: exit 2: build: --gameplay-only refused: Stage A input changed. Run a full build"};
            return QJsonObject{{"exit", 0}};
        }});
        WorkbenchWindow w(s); w.show(); QTRY_VERIFY(!w.isBusy());
        w.findChild<QPushButton *>("wbRebuild")->click(); QTRY_VERIFY(!w.isBusy());
        QVERIFY2(w.statusText().contains("needs a full build"), qPrintable(w.statusText()));
        QVERIFY(fixShown(w)); QCOMPARE(fixButton(w)->text(), QString("Run full rebuild"));
        fail = false; fixButton(w)->click(); QTRY_VERIFY(!w.isBusy());
        QCOMPARE(builds, 2); QVERIFY(!fixShown(w));
    }
    void changedExternallyOffersReloadFromDisk() {
        Bench b; b.open(); auto &w = b.w();
        w.runCommand("load_row", {{"row", "dair"}}); QTRY_VERIFY(!w.isBusy());
        QFile hand(QDir(b.dir.path()).filePath("moves/dair.genoasm"));
        QVERIFY(hand.open(QIODevice::WriteOnly | QIODevice::Append)); hand.write("# hand edit\n"); hand.close();
        w.runCommand("edit_hitbox", {{"row", "dair"}, {"ordinal", 0}, {"damage", 30}}); QTRY_VERIFY(!w.isBusy());
        QVERIFY2(w.statusText().contains("changed externally") && w.statusText().contains("Reload from disk"), qPrintable(w.statusText()));
        QCOMPARE(b.session.data().hitboxes("dair")[0].damage, 14.0);
        QVERIFY(fixShown(w)); QCOMPARE(fixButton(w)->text(), QString("Reload from disk"));
        fixButton(w)->click(); QTRY_VERIFY(!w.isBusy());
        QVERIFY2(!fixShown(w), qPrintable(w.statusText()));
        QVERIFY(b.session.files().externalChanges().isEmpty());
        // The edit that was refused now goes through, on top of the hand edit.
        w.runCommand("edit_hitbox", {{"row", "dair"}, {"ordinal", 0}, {"damage", 30}}); QTRY_VERIFY(!w.isBusy());
        QCOMPARE(b.session.data().hitboxes("dair")[0].damage, 30.0);
        QVERIFY(readAll(b.dir.path(), "moves/dair.genoasm").contains("# hand edit"));
    }
    void aPlainEditFailureStillSaysWhatToDo() {
        Bench b; b.open(); auto &w = b.w();
        w.runCommand("load_row", {{"row", "jab1"}}); QTRY_VERIFY(!w.isBusy());
        w.runCommand("edit_hitbox", {{"row", "jab1"}, {"ordinal", 0}, {"damage", -4}}); QTRY_VERIFY(!w.isBusy());
        QVERIFY2(w.statusText().contains("Your edit was not applied") && w.statusText().contains("nonnegative"), qPrintable(w.statusText()));
        QVERIFY(!fixShown(w));
    }

    // ---- R2: crash recovery ------------------------------------------------------------------------------------------
    void aSessionMarkExistsWhileOpenAndGoesOnCleanClose() {
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path()); FrameEngine engine;
        {
            Session s(dir.path(), &engine); s.data().reload(); registerAllCommands(s);
            WorkbenchWindow w(s); QTRY_VERIFY(!w.isBusy());
            const auto mark = readSessionMark(dir.path());
            QVERIFY(mark.existed); QCOMPARE(mark.pid, qint64(QCoreApplication::applicationPid()));
            QVERIFY(w.findChild<QWidget *>("wbRecoveryBanner")->isHidden());
        }
        QVERIFY(!QFileInfo::exists(sessionMarkPath(dir.path())));
    }
    void interruptedEditIsOfferedAndRestoredFromTheBanner() {
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path()); FrameEngine engine;
        QVector<FileChange> changes;
        { Session s(dir.path(), nullptr); QString err; changes = s.data().editHitbox("dair", 0, damageEdit(19), &err); QVERIFY2(!changes.isEmpty(), qPrintable(err)); }
        // The previous run died after the journal and the first file, before history was written.
        HistoryEntry entry; entry.author = "human"; entry.command = "edit_hitbox"; entry.summary = "dair damage"; entry.changes = changes;
        writeJournal(dir.path(), entry); writeFile(dir.path(), changes[0].path, changes[0].after); plantDeadMark(dir.path(), 60);
        Session s(dir.path(), &engine); s.data().reload(); registerAllCommands(s);
        WorkbenchWindow w(s); w.show(); QTRY_VERIFY(!w.isBusy());
        auto *banner = w.findChild<QWidget *>("wbRecoveryBanner"); QVERIFY(banner); QVERIFY(!banner->isHidden());
        auto *text = w.findChild<QLabel *>("wbRecoveryText");
        QVERIFY2(text->text().startsWith("Restore 1 unsaved change from"), qPrintable(text->text()));
        QVERIFY(!w.findChild<QPushButton *>("wbRecoveryRestore")->isHidden());
        QVERIFY(!w.findChild<QPushButton *>("wbRecoveryDiscard")->isHidden());
        w.findChild<QPushButton *>("wbRecoveryRestore")->click(); QTRY_VERIFY(!w.isBusy());
        QTRY_VERIFY(banner->isHidden());
        for (const auto &change : changes) QCOMPARE(readAll(dir.path(), change.path), change.after);
        QCOMPARE(s.history().entries().size(), qsizetype(1));
        QCOMPARE(s.data().hitboxes("dair")[0].damage, 19.0);
        QVERIFY(!QFileInfo::exists(journalPath(dir.path())));
    }
    void interruptedEditCanBeDiscardedFromTheBanner() {
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path()); FrameEngine engine;
        QVector<FileChange> changes;
        { Session s(dir.path(), nullptr); QString err; changes = s.data().editHitbox("dair", 0, damageEdit(19), &err); }
        HistoryEntry entry; entry.command = "edit_hitbox"; entry.summary = "dair damage"; entry.changes = changes;
        writeJournal(dir.path(), entry); writeFile(dir.path(), changes[0].path, changes[0].after);
        Session s(dir.path(), &engine); s.data().reload(); registerAllCommands(s);
        WorkbenchWindow w(s); w.show(); QTRY_VERIFY(!w.isBusy());
        w.findChild<QPushButton *>("wbRecoveryDiscard")->click(); QTRY_VERIFY(!w.isBusy());
        for (const auto &change : changes) QCOMPARE(readAll(dir.path(), change.path), change.before);
        QVERIFY(s.history().entries().isEmpty());
    }
    void anUncleanCloseWithEditsSinceTheBuildOffersKeepOrRevert() {
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path()); FrameEngine engine;
        { // the previous run: a build, then an edit, then it died
            Session s(dir.path(), nullptr); registerAllCommands(s); captureBaseline(s);
            QString err; const auto changes = s.data().editHitbox("dair", 0, damageEdit(19), &err);
            CommandContext ctx{s}; s.commit(ctx, "edit_hitbox", {}, "dair damage", changes);
        }
        plantDeadMark(dir.path(), 60);
        Session s(dir.path(), &engine); s.data().reload(); registerAllCommands(s);
        WorkbenchWindow w(s); w.show(); QTRY_VERIFY(!w.isBusy());
        auto *banner = w.findChild<QWidget *>("wbRecoveryBanner"); QVERIFY(!banner->isHidden());
        QVERIFY2(w.findChild<QLabel *>("wbRecoveryText")->text().contains("ended unexpectedly"), qPrintable(w.findChild<QLabel *>("wbRecoveryText")->text()));
        QVERIFY(w.findChild<QPushButton *>("wbRecoveryRestore")->isHidden()); // nothing to restore: the edit is on disk
        QCOMPARE(s.data().hitboxes("dair")[0].damage, 19.0); // nothing lost
        w.findChild<QPushButton *>("wbRecoveryRevert")->click(); QTRY_VERIFY(banner->isHidden());
        QTRY_VERIFY(!w.isBusy());
        QCOMPARE(s.data().hitboxes("dair")[0].damage, 14.0); // back to the last build
    }
    void keepClearsTheNoticeAndLeavesTheEdits() {
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path()); FrameEngine engine;
        { Session s(dir.path(), nullptr); registerAllCommands(s); captureBaseline(s);
          QString err; const auto changes = s.data().editHitbox("dair", 0, damageEdit(19), &err);
          CommandContext ctx{s}; s.commit(ctx, "edit_hitbox", {}, "dair damage", changes); }
        plantDeadMark(dir.path(), 60);
        Session s(dir.path(), &engine); s.data().reload(); registerAllCommands(s);
        WorkbenchWindow w(s); w.show(); QTRY_VERIFY(!w.isBusy());
        w.findChild<QPushButton *>("wbRecoveryKeep")->click(); QTRY_VERIFY(!w.isBusy());
        QVERIFY(w.findChild<QWidget *>("wbRecoveryBanner")->isHidden());
        QVERIFY(s.recovery.isEmpty()); QCOMPARE(s.data().hitboxes("dair")[0].damage, 19.0);
    }

    // ---- R3: edits during a rebuild --------------------------------------------------------------------------------
    void editsDuringARebuildAreQueuedMarkedAndOfferRebuildAgain() {
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path()); FrameEngine engine;
        Session s(dir.path(), &engine); s.data().reload();
        registerViewCommands(s); registerRowCommands(s); registerHitboxCommands(s); registerBaselineCommands(s);
        QSemaphore entered, release; std::atomic<int> builds{0};
        s.registry().add({"rebuild", "Gated rebuild", commandSchema(), false, [&](const QJsonObject &, CommandContext &ctx) {
            ++builds; entered.release(); release.tryAcquire(1, 10000); captureBaseline(ctx.session);
            return QJsonObject{{"exit", 0}};
        }});
        WorkbenchWindow w(s); w.resize(1440, 900); w.show(); QTRY_VERIFY(!w.isBusy());
        auto *hub = w.findChild<HubPanel *>("wbHub"); QVERIFY(hub);
        auto *rebuild = w.findChild<QPushButton *>("wbRebuild"); auto *queued = w.findChild<QLabel *>("wbQueued");
        auto *view = w.findChild<TimelineView *>("wbTimeline"); auto *add = w.findChild<QPushButton *>("wbAddHitbox");
        QVERIFY(rebuild && queued && view && add);
        QVERIFY(queued->isHidden()); QCOMPARE(rebuild->text(), QString("Rebuild + reload"));
        w.runCommand("load_row", {{"row", "dair"}}); QTRY_VERIFY(!w.isBusy());
        rebuild->click(); QVERIFY(entered.tryAcquire(1, 5000)); QVERIFY(w.isBusy());
        // Editing is still allowed: the timeline and the Add button stay live.
        QVERIFY(view->isEnabled()); QVERIFY(add->isEnabled());
        view->editRequested("edit_hitbox", {{"row", "dair"}, {"ordinal", 0}, {"damage", 20}});
        view->editRequested("edit_hitbox", {{"row", "dair"}, {"ordinal", 0}, {"damage", 21}});
        QVERIFY(!queued->isHidden()); QVERIFY2(queued->text().contains("2 edits queued") && queued->text().contains("in next rebuild"), qPrintable(queued->text()));
        QCOMPARE(s.data().hitboxes("dair")[0].damage, 14.0); // not applied yet: it waits behind the build
        add->click(); // a structural edit queues too, once
        QVERIFY2(queued->text().contains("3 edits queued"), qPrintable(queued->text()));
        QVERIFY(!view->isEnabled()); QVERIFY(!add->isEnabled()); // the pending add/delete rule still holds
        release.release(); QTRY_VERIFY_WITH_TIMEOUT(!w.isBusy(), 15000);
        QCOMPARE(builds.load(), 1);
        QCOMPARE(s.data().hitboxes("dair").size(), qsizetype(3));
        bool edited = false; // the new hitbox starts at frame 0, so the edited one is no longer first
        for (const auto &hit : s.data().hitboxes("dair")) edited |= hit.damage == 21.0;
        QVERIFY(edited);
        QVERIFY(queued->isHidden());
        QCOMPARE(rebuild->text(), QString("Rebuild again (3 new changes)"));
        QVERIFY(view->isEnabled());
        // Those edits count as changes since the build, so the Revert/pending chips see them.
        QVERIFY(w.findChild<QLabel *>("wbUnsaved")->text().contains("not in game"));
        // A new build starts the count again.
        release.release(100); rebuild->click(); QTRY_VERIFY_WITH_TIMEOUT(!w.isBusy(), 15000);
        QCOMPARE(builds.load(), 2); QCOMPARE(rebuild->text(), QString("Rebuild + reload"));
    }
    void editsOutsideARebuildAreNotMarked() {
        Bench b; b.open(); auto &w = b.w();
        w.runCommand("load_row", {{"row", "dair"}}); QTRY_VERIFY(!w.isBusy());
        w.runCommand("edit_hitbox", {{"row", "dair"}, {"ordinal", 0}, {"damage", 22}}); QTRY_VERIFY(!w.isBusy());
        QVERIFY(w.findChild<QLabel *>("wbQueued")->isHidden());
        QCOMPARE(w.findChild<QPushButton *>("wbRebuild")->text(), QString("Rebuild + reload"));
    }

    // ---- R4: keyboard ------------------------------------------------------------------------------------------------
    void undoAndRedoKeys() {
        Bench b; b.open(); auto &w = b.w();
        w.runCommand("load_row", {{"row", "dair"}}); QTRY_VERIFY(!w.isBusy());
        w.runCommand("edit_hitbox", {{"row", "dair"}, {"ordinal", 0}, {"damage", 22}}); QTRY_VERIFY(!w.isBusy());
        auto *hub = w.findChild<HubPanel *>("wbHub"); hub->setFocus(); QVERIFY(QTest::qWaitFor([&] { return hub->hasFocus(); }));
        // The key queues the command at once; read the session's data only when the worker is idle again.
        const auto press = [&](Qt::Key key, Qt::KeyboardModifiers mods) {
            QTest::keyClick(hub, key, mods); QVERIFY(w.isBusy()); QTRY_VERIFY(!w.isBusy());
        };
        press(Qt::Key_Z, Qt::ControlModifier); QCOMPARE(b.session.data().hitboxes("dair")[0].damage, 14.0);
        press(Qt::Key_Y, Qt::ControlModifier); QCOMPARE(b.session.data().hitboxes("dair")[0].damage, 22.0);
        press(Qt::Key_Z, Qt::ControlModifier); QCOMPARE(b.session.data().hitboxes("dair")[0].damage, 14.0);
        press(Qt::Key_Z, Qt::ControlModifier | Qt::ShiftModifier); QCOMPARE(b.session.data().hitboxes("dair")[0].damage, 22.0);
    }
    void f5RebuildsAndReloads() {
        Bench b; b.open(); auto &w = b.w();
        QSignalSpy done(&w, &WorkbenchWindow::commandFinished);
        auto *hub = w.findChild<HubPanel *>("wbHub"); hub->setFocus();
        QTest::keyClick(hub, Qt::Key_F5); QTRY_VERIFY_WITH_TIMEOUT(!w.isBusy(), 20000);
        QStringList names; for (const auto &e : done) names << e[0].toString();
        QVERIFY2(names.contains("rebuild"), qPrintable(names.join(',')));
        QVERIFY(names.indexOf("reload") > names.indexOf("rebuild"));
    }
    void frameStepAndPlayKeys() {
        Bench b; b.open(); auto &w = b.w();
        w.runCommand("load_row", {{"row", "jab1"}}); QTRY_VERIFY(!w.isBusy());
        auto *hub = w.findChild<HubPanel *>("wbHub"); hub->setFocus();
        auto *readout = w.findChild<QLabel *>("wbFrameReadout"); auto *play = w.findChild<QPushButton *>("wbPlay");
        QVERIFY2(readout->text().startsWith("Frame 0 /"), qPrintable(readout->text()));
        QTest::keyClick(hub, Qt::Key_Right); QVERIFY2(readout->text().startsWith("Frame 1 /"), qPrintable(readout->text()));
        QTest::keyClick(hub, Qt::Key_Right); QVERIFY(readout->text().startsWith("Frame 2 /"));
        QTest::keyClick(hub, Qt::Key_Left); QVERIFY(readout->text().startsWith("Frame 1 /"));
        QTRY_VERIFY(!w.isBusy());
        QCOMPARE(play->text(), QString("Play"));
        QTest::keyClick(hub, Qt::Key_Space); QCOMPARE(play->text(), QString("Pause"));
        QTest::keyClick(hub, Qt::Key_Space); QCOMPARE(play->text(), QString("Play"));
    }
    void duplicateAndDeleteKeysAreUndoable() {
        Bench b; b.open(); auto &w = b.w();
        w.runCommand("load_row", {{"row", "jab1"}}); QTRY_VERIFY(!w.isBusy());
        auto *hub = w.findChild<HubPanel *>("wbHub"); hub->setFocus();
        QCOMPARE(b.session.data().hitboxes("jab1").size(), qsizetype(1));
        QTest::keyClick(hub, Qt::Key_D, Qt::ControlModifier); QTRY_VERIFY(!w.isBusy());
        QTRY_COMPARE(b.session.data().hitboxes("jab1").size(), qsizetype(2));
        const auto copy = b.session.data().hitboxes("jab1");
        QCOMPARE(copy[1].damage, copy[0].damage); QCOMPARE(copy[1].joint, copy[0].joint);
        QCOMPARE(copy[1].startFrame, copy[0].startFrame); QCOMPARE(copy[1].angle, copy[0].angle); QCOMPARE(copy[1].bkb, copy[0].bkb);
        QTest::keyClick(hub, Qt::Key_Delete); QTRY_VERIFY(!w.isBusy());
        QTRY_COMPARE(b.session.data().hitboxes("jab1").size(), qsizetype(1));
        QVERIFY2(w.statusText().contains("Ctrl+Z"), qPrintable(w.statusText()));
        QTest::keyClick(hub, Qt::Key_Z, Qt::ControlModifier); QTRY_VERIFY(!w.isBusy());
        QTRY_COMPARE(b.session.data().hitboxes("jab1").size(), qsizetype(2)); // the deleted copy is back
    }
    void findKeyFocusesTheMoveSearch() {
        Bench b; b.open(); auto &w = b.w();
        auto *search = w.findChild<QLineEdit *>("wbMoveSearch"); search->setText("jab");
        auto *hub = w.findChild<HubPanel *>("wbHub"); hub->setFocus(); QVERIFY(!search->hasFocus());
        QTest::keyClick(hub, Qt::Key_F, Qt::ControlModifier);
        QTRY_VERIFY(search->hasFocus()); QCOMPARE(search->selectedText(), QString("jab"));
    }
    void f1ShowsTheShortcutSheetWithEveryKey() {
        Bench b; b.open(); auto &w = b.w();
        auto *hub = w.findChild<HubPanel *>("wbHub"); hub->setFocus();
        QVERIFY(!w.findChild<QDialog *>("wbShortcutSheet"));
        QTest::keyClick(hub, Qt::Key_F1);
        auto *sheet = w.findChild<QDialog *>("wbShortcutSheet"); QVERIFY(sheet); QVERIFY(sheet->isVisible());
        for (const char *id : {"undo", "redo", "rebuild", "prev_frame", "next_frame", "play_pause", "duplicate", "delete", "find", "palette", "help"})
            QVERIFY2(sheet->findChild<QLabel *>(QString("wbShortcutKeys_") + id), id);
        QCOMPARE(sheet->findChild<QLabel *>("wbShortcutKeys_play_pause")->text(), QString("Space"));
        QCOMPARE(sheet->findChild<QLabel *>("wbShortcutKeys_redo")->text(), QString("Ctrl+Y, Ctrl+Shift+Z"));
        sheet->findChild<QPushButton *>("wbShortcutClose")->click(); QVERIFY(!sheet->isVisible());
        QTest::keyClick(hub, Qt::Key_F1); QVERIFY(sheet->isVisible());
        QTest::keyClick(hub, Qt::Key_F1); QVERIFY(!sheet->isVisible());
    }
    void typingInAFieldKeepsItsKeys() {
        Bench b; b.open(); auto &w = b.w();
        w.runCommand("load_row", {{"row", "jab1"}}); QTRY_VERIFY(!w.isBusy());
        auto *search = w.findChild<QLineEdit *>("wbMoveSearch"); auto *readout = w.findChild<QLabel *>("wbFrameReadout");
        auto *play = w.findChild<QPushButton *>("wbPlay");
        search->setFocus(); QVERIFY(QTest::qWaitFor([&] { return search->hasFocus(); }));
        QTest::keyClicks(search, "ja b"); QCOMPARE(search->text(), QString("ja b")); // Space is a space
        QCOMPARE(play->text(), QString("Play"));
        QTest::keyClick(search, Qt::Key_Left); QCOMPARE(search->cursorPosition(), 3);   // Left moves the caret
        QVERIFY(readout->text().startsWith("Frame 0 /"));
        QTest::keyClick(search, Qt::Key_Delete); QCOMPARE(search->text(), QString("ja ")); // Delete deletes a character
        QCOMPARE(b.session.data().hitboxes("jab1").size(), qsizetype(1));              // ...not the hitbox
        QTest::keyClick(search, Qt::Key_D, Qt::ControlModifier);                        // Ctrl+D is not Duplicate here
        QCOMPARE(b.session.data().hitboxes("jab1").size(), qsizetype(1));
        // Ctrl+Z undoes the text, not the last hitbox edit.
        w.runCommand("edit_hitbox", {{"row", "jab1"}, {"ordinal", 0}, {"damage", 9}}); QTRY_VERIFY(!w.isBusy());
        search->setFocus(); search->clear(); QTest::keyClicks(search, "xyz"); QCOMPARE(search->text(), QString("xyz"));
        QTest::keyClick(search, Qt::Key_Z, Qt::ControlModifier);
        QTest::qWait(150); QTRY_VERIFY(!w.isBusy());
        QCOMPARE(b.session.data().hitboxes("jab1")[0].damage, 9.0);
        QVERIFY(search->text() != "xyz");
    }
    void aFocusedButtonKeepsSpace() {
        Bench b; b.open(); auto &w = b.w();
        w.runCommand("load_row", {{"row", "jab1"}}); QTRY_VERIFY(!w.isBusy());
        auto *add = w.findChild<QPushButton *>("wbAddHitbox"); add->setFocus(); QVERIFY(QTest::qWaitFor([&] { return add->hasFocus(); }));
        QTest::keyClick(add, Qt::Key_Space); QTRY_VERIFY(!w.isBusy());
        QCOMPARE(w.findChild<QPushButton *>("wbPlay")->text(), QString("Play")); // not play/pause
        QTRY_COMPARE(b.session.data().hitboxes("jab1").size(), qsizetype(2));    // the button was pressed
    }
    // Not an assertion: with WB_QOL_SHOTS=<dir> the new surfaces are saved as PNGs for a human to look at.
    void screenshotsForReview() {
        const QString out = qEnvironmentVariable("WB_QOL_SHOTS");
        if (out.isEmpty()) QSKIP("set WB_QOL_SHOTS to a folder to save the review screenshots");
        QDir().mkpath(out);
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path()); FrameEngine engine;
        { Session s(dir.path(), nullptr); registerAllCommands(s); captureBaseline(s);
          QString err; const auto changes = s.data().editHitbox("dair", 0, damageEdit(19), &err);
          CommandContext ctx{s}; s.commit(ctx, "edit_hitbox", {}, "dair damage", changes); }
        plantDeadMark(dir.path(), 3600);
        Session s(dir.path(), &engine); s.data().reload(); registerAllCommands(s);
        WorkbenchWindow w(s); w.resize(1440, 900); w.show(); QVERIFY(QTest::qWaitForWindowActive(&w)); QTRY_VERIFY(!w.isBusy());
        w.runCommand("load_row", {{"row", "dair"}}); QTRY_VERIFY(!w.isBusy());
        w.grab().save(out + "/wb-recovery-banner.png");
        engine.failWith = "engine not running"; w.runCommand("render_view", {}); QTRY_VERIFY(!w.isBusy());
        w.grab().save(out + "/wb-fix-button.png");
        w.findChild<HubPanel *>("wbHub")->setFocus(); QTest::keyClick(w.findChild<HubPanel *>("wbHub"), Qt::Key_F1);
        if (auto *sheet = w.findChild<QDialog *>("wbShortcutSheet")) sheet->grab().save(out + "/wb-shortcut-sheet.png");
    }
    void keysDoNothingWhenFocusIsOutsideTheWorkbench() {
        Bench b; b.open(); auto &w = b.w();
        w.runCommand("load_row", {{"row", "jab1"}}); QTRY_VERIFY(!w.isBusy());
        QLineEdit other; other.show(); QVERIFY(QTest::qWaitForWindowActive(&other)); other.setFocus();
        QTest::keyClick(&other, Qt::Key_Space);
        QCOMPARE(w.findChild<QPushButton *>("wbPlay")->text(), QString("Play"));
        QTest::keyClick(&other, Qt::Key_Delete); QTest::qWait(100);
        QCOMPARE(b.session.data().hitboxes("jab1").size(), qsizetype(1));
    }
};
QTEST_MAIN(QolTest)
#include "qol_test.moc"
