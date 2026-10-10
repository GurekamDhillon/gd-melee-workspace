// The Creator tab at the owner's real window sizes: nothing clipped, Rebuild visible, the inspector
// reachable, and the empty/number-format fixes. Optional screenshots: WB_RESP_SHOTS=<dir>.
#include "../testfixture.h"
#include "atlas_widgets.h"
#include "commands.h"
#include "hub_panel.h"
#include "kit.h"
#include "panels.h"
#include "session.h"
#include "window.h"
#include "workbench_window.h"
#include <QAbstractButton>
#include <QAbstractSpinBox>
#include <QComboBox>
#include <QDir>
#include <QLabel>
#include <QLineEdit>
#include <QScrollArea>
#include <QStackedWidget>
#include <QTemporaryDir>
#include <QtTest>
using namespace wb;

namespace {
bool insideScroll(const QWidget *w) {
    for (const QWidget *p = w->parentWidget(); p; p = p->parentWidget()) if (qobject_cast<const QScrollArea *>(p)) return true;
    return false;
}
// Controls that must show whole: no clipped button, combo or field.
QStringList clippedControls(QWidget *root, QWidget *scope) {
    QStringList bad;
    const QRect scopeRect(scope->mapTo(root, QPoint(0, 0)), scope->size());
    for (auto *w : scope->findChildren<QWidget *>()) {
        if (!w->isVisibleTo(scope)) continue;
        const bool control = qobject_cast<QAbstractButton *>(w) || qobject_cast<QComboBox *>(w) || qobject_cast<QAbstractSpinBox *>(w);
        if (!control) continue;
        if (qobject_cast<QAbstractSpinBox *>(w->parentWidget()) || qobject_cast<QComboBox *>(w->parentWidget())) continue;
        if (w->inherits("QTabBar") || w->objectName().startsWith("qt_")) continue;
        const QString name = w->objectName().isEmpty() ? QString(w->metaObject()->className()) : w->objectName();
        const QRect r(w->mapTo(root, QPoint(0, 0)), w->size());
        if (r.left() < scopeRect.left() || r.right() > scopeRect.right())
            bad << QString("%1 outside the workbench horizontally %2..%3 vs %4..%5").arg(name).arg(r.left()).arg(r.right()).arg(scopeRect.left()).arg(scopeRect.right());
        if (w->parentWidget() && !insideScroll(w) && !w->parentWidget()->rect().contains(w->geometry()))
            bad << QString("%1 sticks out of its parent").arg(name);
        if (!qobject_cast<QAbstractSpinBox *>(w) && w->width() + 1 < w->minimumSizeHint().width())
            bad << QString("%1 is %2 wide, needs %3").arg(name).arg(w->width()).arg(w->minimumSizeHint().width());
        // inside a horizontally non-scrolling scroll area the control must still fit its viewport
        for (const QWidget *p = w->parentWidget(); p; p = p->parentWidget()) {
            if (auto *area = qobject_cast<const QScrollArea *>(p)) {
                const QRect view(area->viewport()->mapTo(root, QPoint(0, 0)), area->viewport()->size());
                if (r.right() > view.right() + 1) bad << QString("%1 is clipped by its scroll area").arg(name);
                break;
            }
        }
    }
    return bad;
}
}

class ResponsiveTest : public QObject {
    Q_OBJECT
private slots:
    void initTestCase() { launcher::spanish = false; launcher::applyTheme(); }
    void creatorLaysOutAtTheOwnersWindowSizes_data() {
        QTest::addColumn<int>("w"); QTest::addColumn<int>("h"); QTest::addColumn<QString>("shot"); QTest::addColumn<bool>("narrow");
        QTest::newRow("small") << 1094 << 943 << "after_small_1094x943" << true;
        QTest::newRow("portrait") << 1096 << 1888 << "after_portrait_1096x1888" << true;
        QTest::newRow("full") << 1936 << 1048 << "after_full_1936x1048" << false;
        QTest::newRow("720p") << 1280 << 720 << "after_1280x720" << true;
    }
    void creatorLaysOutAtTheOwnersWindowSizes() {
        QFETCH(int, w); QFETCH(int, h); QFETCH(QString, shot); QFETCH(bool, narrow);
        QTemporaryDir d; const QString project = QDir(d.path()).filePath("fighter"); QDir().mkpath(project); wbtest::makeSynthFighter(project);
        launcher::Settings settings; settings.options["creator_enabled"] = "1"; settings.options["creator_project"] = project;
        launcher::Window window(d.path(), d.path(), settings);
        window.resize(w, h); window.show();
        auto *rail = window.findChild<launcher::kit::TabRail *>("atlasRail"); QVERIFY(rail); rail->setCurrent(4);
        QTRY_VERIFY(window.findChild<WorkbenchWindow *>());
        auto *bench = window.findChild<WorkbenchWindow *>(); QTRY_VERIFY(!bench->isBusy());
        QTest::qWait(200);
        QVERIFY2(bench->isVisible(), "workbench visible");
        // R3: the nav is an icon rail while the window is narrow, full when wide.
        QCOMPARE(rail->collapsed(), w < 1500); QCOMPARE(rail->width(), w < 1500 ? launcher::kit::TabRail::kCollapsedWidth : 204);
        // R2: Rebuild is on screen, fully, whatever the width.
        auto *rebuild = bench->findChild<QWidget *>("wbRebuild"); QVERIFY(rebuild);
        const QRect rr(rebuild->mapTo(&window, QPoint(0, 0)), rebuild->size());
        QVERIFY2(QRect(QPoint(0, 0), window.size()).contains(rr), qPrintable(QString("Rebuild at %1,%2 %3x%4 in %5x%6").arg(rr.x()).arg(rr.y()).arg(rr.width()).arg(rr.height()).arg(w).arg(h)));
        QVERIFY(rebuild->isVisible());
        for (const char *name : {"wbPlayCpu", "wbPlayLab", "wbUndo"}) {
            auto *button = bench->findChild<QWidget *>(name); QVERIFY(button); QVERIFY(button->isVisible());
            const QRect r(button->mapTo(&window, QPoint(0, 0)), button->size());
            QVERIFY2(QRect(QPoint(0, 0), window.size()).contains(r), name);
        }
        // R1: the inspector sits under the timeline when narrow, beside it when wide.
        auto *tabs = bench->findChild<InspectorTabs *>("wbInspectorTabs"); auto *timeline = bench->findChild<TimelineView *>("wbTimeline");
        QVERIFY(tabs && timeline); QVERIFY(tabs->isVisible());
        const QPoint tabsAt = tabs->mapTo(bench, QPoint(0, 0)), timelineAt = timeline->mapTo(bench, QPoint(0, 0));
        if (narrow) QVERIFY2(tabsAt.y() > timelineAt.y() && tabs->width() > 520, qPrintable(QString("tabs %1,%2 w%3").arg(tabsAt.x()).arg(tabsAt.y()).arg(tabs->width())));
        else QVERIFY2(tabsAt.x() > timelineAt.x() + timeline->width() - 5, "inspector is a third column when wide");
        QVERIFY2(tabs->width() >= 300, "inspector is not squeezed");
        // R4: the timeline panel hugs its rows.
        auto *plate = bench->findChild<QWidget *>("wbTimelinePlate"); QVERIFY(plate);
        QVERIFY2(plate->height() < timeline->sizeHint().height() + 260, qPrintable(QString("plate %1 for timeline %2").arg(plate->height()).arg(timeline->sizeHint().height())));
        // No clipped control anywhere in the workbench, on every inspector tab.
        for (int tab = 0; tab < tabs->count(); ++tab) {
            tabs->setCurrentIndex(tab); QTest::qWait(60);
            const auto bad = clippedControls(bench, bench);
            QVERIFY2(bad.isEmpty(), qPrintable(QString("tab %1: ").arg(tab) + bad.join("; ")));
        }
        tabs->setCurrentIndex(0);
        const QByteArray dir = qgetenv("WB_RESP_SHOTS");
        if (!dir.isEmpty()) { QDir().mkpath(QString::fromLocal8Bit(dir)); QVERIFY(window.grab().save(QDir(QString::fromLocal8Bit(dir)).filePath(shot + ".png"))); }
    }
    void standaloneWindowReflowsBetweenWideAndNarrow() {
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path()); wbtest::FakeEngine engine;
        Session s(dir.path(), &engine); s.data().reload(); registerAllCommands(s);
        WorkbenchWindow w(s); w.resize(1600, 900); w.show(); QTRY_VERIFY(!w.isBusy());
        auto *tabs = w.findChild<InspectorTabs *>("wbInspectorTabs"); auto *rebuild = w.findChild<QWidget *>("wbRebuild");
        QVERIFY(tabs && rebuild);
        const auto beside = [&] { return tabs->mapTo(&w, QPoint(0, 0)).x() > w.width() / 2; };
        QTRY_VERIFY(beside());
        w.resize(1000, 800); QTRY_VERIFY(!beside()); QVERIFY(rebuild->mapTo(&w, QPoint(0, 0)).x() + rebuild->width() <= w.width());
        w.resize(1600, 900); QTRY_VERIFY(beside());
        w.resize(900, 1500); QTRY_VERIFY(!beside());
    }
    void emptyStateAndDefaultRow() {
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path());
        QByteArray source(wbtest::kGameplay);
        source.replace("\"moves\": [", "\"moves\": [{\"name\": \"aaa_idle\", \"motions\": [1], \"tag\": \"idle\", \"script\": \"moves/idle.genoasm\", \"iasa\": 0},");
        wbtest::put(dir.path(), "gameplay.json", source); wbtest::put(dir.path(), "moves/idle.genoasm", "# synthetic\nPUT ANIM_RATE 1.0\nwait_until 5\n");
        wbtest::FakeEngine engine; Session s(dir.path(), &engine); s.data().reload(); registerAllCommands(s);
        WorkbenchWindow w(s); w.resize(1440, 900); w.show(); QTRY_VERIFY(!w.isBusy());
        auto *rows = w.findChild<QComboBox *>("wbRows"); QVERIFY(rows);
        QCOMPARE(rows->currentData().toString(), QString("jab1")); // the first move that has hitboxes, not the first move
        auto *form = w.findChild<QWidget *>("wbHitboxForm"); auto *empty = w.findChild<QWidget *>("wbHitboxEmpty"); QVERIFY(form && empty);
        QVERIFY(form->isVisibleTo(&w)); QVERIFY(!empty->isVisibleTo(&w));
        auto *outline = w.findChild<OutlinerPanel *>(); QVERIFY(outline);
        emit outline->rowSelected("aaa_idle"); QTRY_VERIFY(!w.isBusy());
        QTRY_VERIFY(empty->isVisibleTo(&w)); QVERIFY(!form->isVisibleTo(&w));
        QVERIFY(w.findChild<QLabel *>("wbHitboxEmptyTitle")->text().contains("No hitboxes"));
        auto *inspector = w.findChild<InspectorPanel *>(); QVERIFY(inspector); QVERIFY(!inspector->isEnabled());
        const QByteArray shots = qgetenv("WB_RESP_SHOTS");
        if (!shots.isEmpty()) { QDir().mkpath(QString::fromLocal8Bit(shots)); QVERIFY(w.grab().save(QDir(QString::fromLocal8Bit(shots)).filePath("after_empty_state_1440x900.png"))); }
    }
    void numbersMatchTheirFieldAndLastActiveFrameConverts() {
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path()); wbtest::FakeEngine engine;
        Session s(dir.path(), &engine); s.data().reload(); registerAllCommands(s);
        WorkbenchWindow w(s); w.resize(1440, 900); w.show(); QTRY_VERIFY(!w.isBusy());
        auto *damage = w.findChild<QDoubleSpinBox *>("wbHitbox_damage"); auto *size = w.findChild<QDoubleSpinBox *>("wbHitbox_size");
        auto *last = w.findChild<QSpinBox *>("wbHitbox_end_frame"); auto *angle = w.findChild<QSpinBox *>("wbHitbox_angle");
        QVERIFY(damage && size && last && angle);
        QCOMPARE(damage->decimals(), 1); QCOMPARE(size->decimals(), 2);
        QCOMPARE(damage->text(), QString("3.0")); QCOMPARE(size->text(), QString("3.40"));
        QCOMPARE(angle->text(), QString("361"));
        const auto hit = s.data().hitboxes("jab1")[0];
        QVERIFY(hit.endFrame > 1);
        QCOMPARE(last->value(), hit.endFrame - 1); // shown as the last active frame, stored as an exclusive end
        bool sawLabel = false;
        for (auto *l : w.findChildren<QLabel *>()) { sawLabel |= l->text() == "Last active frame"; QVERIFY(!l->text().contains("exclusive")); }
        QVERIFY(sawLabel);
        last->setValue(last->value() + 2); emit last->editingFinished(); QTRY_VERIFY(!w.isBusy());
        QCOMPARE(s.data().hitboxes("jab1")[0].endFrame, hit.endFrame + 2);
        QCOMPARE(last->value(), hit.endFrame + 1);
        // a value with more precision than the box shows is not rewritten by merely leaving the field
        w.runCommand("edit_hitbox", {{"row", "jab1"}, {"ordinal", 0}, {"damage", 3.25}}); QTRY_VERIFY(!w.isBusy());
        emit damage->editingFinished(); QTRY_VERIFY(!w.isBusy());
        QCOMPARE(s.data().hitboxes("jab1")[0].damage, 3.25);
    }
};
QTEST_MAIN(ResponsiveTest)
#include "responsive_test.moc"
