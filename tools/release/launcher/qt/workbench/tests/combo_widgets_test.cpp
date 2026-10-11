// The combo tab, the route lanes under the timeline and the string map. Optional screenshots: WB_COMBO_SHOTS=<dir>.
#include "../testfixture.h"
#include "atlas_widgets.h"
#include "combo_widgets.h"
#include "commands.h"
#include "panels.h"
#include "session.h"
#include "window.h"
#include "workbench_window.h"
#include <QAbstractButton>
#include <QAbstractSpinBox>
#include <QCheckBox>
#include <QComboBox>
#include <QDir>
#include <QLineEdit>
#include <QListWidget>
#include <QPlainTextEdit>
#include <QScrollArea>
#include <QSignalSpy>
#include <QSpinBox>
#include <QTemporaryDir>
#include <QtTest>
using namespace wb;

namespace {
QJsonArray sampleRoutes() {
    const auto idx = [](QJsonObject o, int i) { o["index"] = i; return o; };
    return {idx({{"name", "L1>L2"}, {"from", "jab1"}, {"to", "geno:Light2"}, {"input", "light"}, {"on", "hit"}, {"window", QJsonArray{10, 18}},
                 {"source", "BCM 0/18/3; BAC 300 cancel f14+22"}}, 0),
            idx({{"name", "L1>H up"}, {"from", "jab1"}, {"to", "geno:HeavyUp"}, {"input", "heavy"}, {"dir", "up"}, {"window", QJsonArray{12, 0}}}, 1),
            idx({{"name", "L2>L3"}, {"from", "geno:Light2"}, {"to", "geno:Light3"}, {"input", "light"}, {"window", QJsonArray{7, 30}}}, 2),
            idx({{"name", "any>Special"}, {"from", QJsonArray{"jab1", "dair"}}, {"to", "special_s"}, {"input", "special"}, {"window", QJsonArray{1, 0}}}, 3)};
}
QJsonArray sampleStrings() {
    return {QJsonObject{{"name", "light string"}, {"steps", QJsonArray{"jab1", "geno:Light2", "geno:Light3"}}}};
}
const char *kCombo = R"JSON({
  "version": 1,
  "states": [
    {"name": "Light2", "clip": "SYN_ATC_009", "script": "moves/light2.genoasm"}
  ],
  "combo": {
    "buffer": 5,
    "routes": [
      {"name": "L1>L2", "from": "jab1", "to": "geno:Light2", "input": "light", "on": "hit", "where": "ground", "window": [10, 18], "source": "SYN BCM 0/1; cancel f9+8"},
      {"name": "L1>H", "from": "jab1", "to": "dair", "input": "heavy", "dir": "forward", "window": [12, 0]},
      {"name": "L1>Spc", "from": ["jab1", "dair"], "to": "special_s", "input": "special", "priority": 10},
      {"name": "A>J", "from": "dair", "to": "jump_short", "input": "jump", "window": [3, 0]}
    ],
    "strings": [
      {"name": "light then heavy", "steps": ["jab1", "dair"]},
      {"name": "two lights", "steps": ["jab1", "geno:Light2"]}
    ]
  }
}
)JSON";
QString makeProject(const QString &dir) {
    wbtest::makeSynthFighter(dir);
    auto project = QJsonDocument::fromJson(wbtest::kProject).object();
    project["combo"] = "combo/combo.json";
    wbtest::put(dir, "workbench.json", QJsonDocument(project).toJson());
    wbtest::put(dir, "combo/combo.json", kCombo);
    wbtest::put(dir, "combo/moves/light2.genoasm", "# synthetic\nPUT ANIM_RATE 1.0\nwait_until 4\nhitbox slot=0 joint=@HAND_R@ damage=3 size=3.40 x=0.00 y=0.00 z=0.00 angle=361 kbg=50 fkb=0 bkb=8\nwait 2\nclear_hitboxes\nwait_until 20\niasa\n");
    return dir;
}
bool insideScroll(const QWidget *w) {
    for (const QWidget *p = w->parentWidget(); p; p = p->parentWidget()) if (qobject_cast<const QScrollArea *>(p)) return true;
    return false;
}
QStringList clippedControls(QWidget *root, QWidget *scope) {
    QStringList bad;
    const QRect scopeRect(scope->mapTo(root, QPoint(0, 0)), scope->size());
    for (auto *w : scope->findChildren<QWidget *>()) {
        if (!w->isVisibleTo(scope)) continue;
        const bool control = qobject_cast<QAbstractButton *>(w) || qobject_cast<QComboBox *>(w) || qobject_cast<QAbstractSpinBox *>(w) || qobject_cast<QLineEdit *>(w);
        if (!control) continue;
        if (qobject_cast<QAbstractSpinBox *>(w->parentWidget()) || qobject_cast<QComboBox *>(w->parentWidget())) continue;
        if (w->inherits("QTabBar") || w->objectName().startsWith("qt_")) continue;
        const QString name = w->objectName().isEmpty() ? QString(w->metaObject()->className()) : w->objectName();
        const QRect r(w->mapTo(root, QPoint(0, 0)), w->size());
        if (r.left() < scopeRect.left() || r.right() > scopeRect.right()) bad << name + " outside the workbench horizontally";
        for (const QWidget *p = w->parentWidget(); p; p = p->parentWidget()) {
            if (auto *area = qobject_cast<const QScrollArea *>(p)) {
                const QRect view(area->viewport()->mapTo(root, QPoint(0, 0)), area->viewport()->size());
                if (r.right() > view.right() + 1) bad << name + " is clipped by its scroll area";
                break;
            }
        }
    }
    return bad;
}
}

class ComboWidgetsTest : public QObject {
    Q_OBJECT
private slots:
    void initTestCase() { launcher::spanish = false; launcher::applyTheme(); }

    void lanesShowTheMovesOutgoingRoutesOnTheirWindows() {
        TimelineView timeline; timeline.resize(700, 160); timeline.setMove("jab1", 40, {}, 30);
        RouteLanes lanes; lanes.setTimeline(&timeline); lanes.resize(700, 60);
        lanes.setRoutes("jab1", {"jab1", "motion:44"}, sampleRoutes());
        timeline.show(); lanes.show();
        QCOMPARE(lanes.laneCount(), 3);                       // L1>L2, L1>H up and the list-source route; not Light2's
        QCOMPARE(lanes.routeIndexAt(2), 3);
        const qreal perFrame = timeline.rulerRect().width() / 40.0;
        const QRectF bar = lanes.barRect(0);                  // window [10, 18] = boundaries 10 .. 19
        QVERIFY2(qAbs(bar.width() - perFrame * 9) < 2, qPrintable(QString("width %1 vs %2").arg(bar.width()).arg(perFrame * 9)));
        const QPoint at = timeline.mapToGlobal(QPoint(int(timeline.framePosition(10)), 0));
        QVERIFY(qAbs(lanes.mapFromGlobal(at).x() - bar.left()) <= 1);
        QVERIFY(lanes.barRect(1).right() >= timeline.mapTo(&lanes, QPoint(int(timeline.framePosition(40)), 0)).x() - 2);   // "to the end" reaches the end
        lanes.setRoutes("dair", {"dair"}, sampleRoutes());
        QCOMPARE(lanes.laneCount(), 1);
        lanes.setRoutes("none", {"none"}, sampleRoutes());
        QCOMPARE(lanes.laneCount(), 0);
    }
    void draggingABarMovesOrResizesItsWindow() {
        TimelineView timeline; timeline.resize(700, 160); timeline.setMove("jab1", 40, {}, 30);
        RouteLanes lanes; lanes.setTimeline(&timeline); lanes.resize(700, 80);
        lanes.setRoutes("jab1", {"jab1"}, sampleRoutes());
        timeline.show(); lanes.show();
        QSignalSpy spy(&lanes, &RouteLanes::editRequested);
        const qreal perFrame = timeline.rulerRect().width() / 40.0;
        // body: slide by 3 frames, the width stays
        QRectF bar = lanes.barRect(0);
        QPoint press = bar.center().toPoint(), release = press + QPoint(int(perFrame * 3), 0);
        QTest::mousePress(&lanes, Qt::LeftButton, {}, press); QTest::mouseMove(&lanes, release); QTest::mouseRelease(&lanes, Qt::LeftButton, {}, release);
        QCOMPARE(spy.size(), 1);
        QCOMPARE(spy[0][0].toString(), QString("edit_route"));
        QCOMPARE(spy[0][1].toJsonObject()["index"].toInt(), 0);
        QCOMPARE(spy[0][1].toJsonObject()["window"].toArray(), (QJsonArray{13, 21}));
        // the right edge: end 18 -> 22 (boundary 19 -> 23)
        bar = lanes.barRect(0);
        press = QPoint(int(bar.right()) - 2, int(bar.center().y())); release = press + QPoint(int(perFrame * 4), 0);
        QTest::mousePress(&lanes, Qt::LeftButton, {}, press); QTest::mouseMove(&lanes, release); QTest::mouseRelease(&lanes, Qt::LeftButton, {}, release);
        QCOMPARE(spy.size(), 2);
        QCOMPARE(spy[1][1].toJsonObject()["window"].toArray(), (QJsonArray{10, 22}));
        // the left edge: start 10 -> 6
        bar = lanes.barRect(0);
        press = QPoint(int(bar.left()) + 2, int(bar.center().y())); release = press - QPoint(int(perFrame * 4), 0);
        QTest::mousePress(&lanes, Qt::LeftButton, {}, press); QTest::mouseMove(&lanes, release); QTest::mouseRelease(&lanes, Qt::LeftButton, {}, release);
        QCOMPARE(spy.size(), 3);
        QCOMPARE(spy[2][1].toJsonObject()["window"].toArray(), (QJsonArray{6, 18}));
        // dragging the end to the end of the timeline means "to the end" (0); a click asks for nothing
        bar = lanes.barRect(0);
        press = QPoint(int(bar.right()) - 2, int(bar.center().y()));
        QTest::mousePress(&lanes, Qt::LeftButton, {}, press); QTest::mouseMove(&lanes, QPoint(690, press.y())); QTest::mouseRelease(&lanes, Qt::LeftButton, {}, QPoint(690, press.y()));
        QCOMPARE(spy[3][1].toJsonObject()["window"].toArray()[1].toInt(), 0);
        const int before = spy.size();
        QTest::mouseClick(&lanes, Qt::LeftButton, {}, lanes.barRect(1).center().toPoint());
        QCOMPARE(spy.size(), before);
        QCOMPARE(lanes.selectedRoute(), 1);
        QTest::keyClick(&lanes, Qt::Key_Right);
        QCOMPARE(spy.last()[1].toJsonObject()["window"].toArray(), (QJsonArray{13, 0}));
        QTest::keyClick(&lanes, Qt::Key_Delete);
        QCOMPARE(spy.last()[0].toString(), QString("delete_route"));
    }
    void panelListsTheMovesRoutesEditsThemAndShowsTheSource() {
        ComboPanel panel; panel.resize(420, 1200); panel.show();
        panel.setData(sampleRoutes(), sampleStrings(), QJsonObject{{"buffer", 5}}, {"jab1", "dair"}, "jab1", {"jab1"}, true);
        auto *list = panel.findChild<QListWidget *>("wbComboRoutes");
        QCOMPARE(list->count(), 3);
        QVERIFY2(list->item(0)->text().contains("L1>L2") && list->item(0)->text().contains("Light2 · light · on hit"), qPrintable(list->item(0)->text()));
        QCOMPARE(panel.selectedRoute(), 0);
        QVERIFY(panel.findChild<QPlainTextEdit *>("wbComboSource")->toPlainText().contains("BAC 300 cancel f14+22"));
        panel.findChild<QCheckBox *>("wbComboAll")->setChecked(true);
        QCOMPARE(list->count(), 4);
        panel.findChild<QCheckBox *>("wbComboAll")->setChecked(false);
        QSignalSpy spy(&panel, &ComboPanel::editRequested);
        panel.findChild<QSpinBox *>("wbComboLo")->setValue(8);
        QCOMPARE(spy.size(), 1);
        QCOMPARE(spy[0][0].toString(), QString("edit_route"));
        QCOMPARE(spy[0][1].toJsonObject()["window"].toArray(), (QJsonArray{8, 18}));
        panel.findChild<QSpinBox *>("wbComboPriority")->setValue(4);
        QCOMPARE(spy[1][1].toJsonObject()["priority"].toInt(), 4);
        auto *input = panel.findChild<QComboBox *>("wbComboInput");
        input->setCurrentIndex(input->findText("heavy")); emit input->activated(input->currentIndex());
        QCOMPARE(spy[2][1].toJsonObject()["input"].toString(), QString("heavy"));
        auto *from = panel.findChild<QLineEdit *>("wbComboFrom");
        from->setText("jab1, dair"); emit from->editingFinished();
        QCOMPARE(spy[3][1].toJsonObject()["from"].toArray(), (QJsonArray{"jab1", "dair"}));
        from->setText("jab1"); emit from->editingFinished();   // an unchanged name asks for nothing
        QCOMPARE(spy.size(), 4);
        QTest::mouseClick(panel.findChild<QPushButton *>("wbComboAdd"), Qt::LeftButton);
        QCOMPARE(spy.last()[0].toString(), QString("add_route"));
        QCOMPARE(spy.last()[1].toJsonObject()["route"].toObject()["from"].toString(), QString("jab1"));
        QTest::mouseClick(panel.findChild<QPushButton *>("wbComboDelete"), Qt::LeftButton);
        QCOMPARE(spy.last()[0].toString(), QString("delete_route"));
        // strings
        QSignalSpy play(&panel, &ComboPanel::playStringRequested);
        QCOMPARE(panel.findChild<QListWidget *>("wbComboStrings")->count(), 1);
        QCOMPARE(panel.findChild<QLineEdit *>("wbComboSteps")->text(), QString("jab1, geno:Light2, geno:Light3"));
        QTest::mouseClick(panel.findChild<QPushButton *>("wbComboPlay"), Qt::LeftButton);
        QCOMPARE(play.size(), 1); QCOMPARE(play[0][0].toInt(), 0);
        auto *steps = panel.findChild<QLineEdit *>("wbComboSteps");
        steps->setText("jab1, dair"); emit steps->editingFinished();
        QCOMPARE(spy.last()[0].toString(), QString("edit_string"));
        QCOMPARE(spy.last()[1].toJsonObject()["steps"].toArray(), (QJsonArray{"jab1", "dair"}));
    }
    void stringMapIsAGraphOfMovesAndClickingANodeSelectsTheMove() {
        const auto graph = buildComboGraph(sampleRoutes(), sampleStrings());
        // the string's steps run left to right; the special target sits after its source
        QCOMPARE(graph.nodes[graph.node("jab1")].col, 0);
        QCOMPARE(graph.nodes[graph.node("geno:Light2")].col, 1);
        QCOMPARE(graph.nodes[graph.node("geno:Light3")].col, 2);
        QVERIFY(graph.nodes[graph.node("special_s")].col >= 1);
        QCOMPARE(graph.edges.size(), 5);                      // list-source route contributes jab1 and dair
        StringMap map; map.setGraph(sampleRoutes(), sampleStrings(), {"jab1", "dair"}); map.resize(map.sizeHint()); map.show();
        QCOMPARE(map.nodeCount(), graph.nodes.size());
        QSignalSpy moves(&map, &StringMap::moveClicked), nodes(&map, &StringMap::nodeClicked);
        QTest::mouseClick(&map, Qt::LeftButton, {}, map.nodeRect("jab1").center().toPoint());
        QCOMPARE(moves.size(), 1); QCOMPARE(moves[0][0].toString(), QString("jab1"));
        QTest::mouseClick(&map, Qt::LeftButton, {}, map.nodeRect("geno:Light2").center().toPoint());   // a geno state: no row to select
        QCOMPARE(moves.size(), 1); QCOMPARE(nodes.size(), 2);
        // a cycle does not hang the layout
        QJsonArray cyc{QJsonObject{{"from", "a"}, {"to", "b"}, {"input", "light"}}, QJsonObject{{"from", "b"}, {"to", "a"}, {"input", "light"}}};
        QCOMPARE(buildComboGraph(cyc, {}).nodes.size(), 2);
    }
    void theWorkbenchHasTheLanesTheTabAndTheDragEditsTheFile() {
        QTemporaryDir d; makeProject(d.path()); wbtest::FakeEngine engine;
        Session s(d.path(), &engine); s.data().reload(); registerAllCommands(s);
        WorkbenchWindow w(s); w.resize(1440, 900); w.show(); QTRY_VERIFY(!w.isBusy());
        auto *lanes = w.findChild<RouteLanes *>("wbRouteLanes"); auto *panel = w.findChild<ComboPanel *>("wbCombo");
        auto *tabs = w.findChild<InspectorTabs *>("wbInspectorTabs"); auto *timeline = w.findChild<TimelineView *>("wbTimeline");
        QVERIFY(lanes && panel && tabs && timeline);
        QVERIFY(tabs->indexOf(panel) >= 0);
        QTRY_COMPARE(lanes->laneCount(), 3);                  // L1>L2, L1>H, and the list-source route, all leaving jab1
        QVERIFY(lanes->isVisible());
        tabs->setCurrentWidget(panel); QTest::qWait(60);
        QCOMPARE(panel->findChild<QListWidget *>("wbComboRoutes")->count(), 3);
        // drag L1>L2 by 2 frames: the route file changes, and the lane follows
        const qreal perFrame = timeline->rulerRect().width() / double(timeline->frameCount());
        const QRectF bar = lanes->barRect(0);
        const QPoint press = bar.center().toPoint(), release = press + QPoint(int(perFrame * 2 + perFrame / 2), 0);
        QTest::mousePress(lanes, Qt::LeftButton, {}, press); QTest::mouseMove(lanes, release); QTest::mouseRelease(lanes, Qt::LeftButton, {}, release);
        QTRY_VERIFY(!w.isBusy());
        QTRY_COMPARE(s.data().routes()[0].toObject()["window"].toArray()[0].toInt(), 12);
        QTRY_COMPARE(lanes->laneCount(), 3);
        QVERIFY(s.data().routes()[0].toObject()["window"].toArray()[1].toInt() == 20);
        CommandContext ctx{s};
        QVERIFY(s.registry().call("undo", {}, ctx)["ok"].toBool());
        QCOMPARE(s.data().routes()[0].toObject()["window"].toArray()[0].toInt(), 10);
    }
    void realProjectShots() {
        // WB_COMBO_PROJECT=<a copy of a real project dir> WB_COMBO_ROW=<move> WB_COMBO_SHOTS=<dir>: screenshots of real data.
        const QString project = QString::fromLocal8Bit(qgetenv("WB_COMBO_PROJECT")), out = QString::fromLocal8Bit(qgetenv("WB_COMBO_SHOTS"));
        if (project.isEmpty() || out.isEmpty()) QSKIP("WB_COMBO_PROJECT / WB_COMBO_SHOTS not set");
        QDir().mkpath(out);
        wbtest::FakeEngine engine; Session s(project, &engine); QVERIFY2(s.data().reload().isEmpty(), "project loads"); registerAllCommands(s);
        WorkbenchWindow win(s); win.resize(1936, 1048); win.show(); QTRY_VERIFY(!win.isBusy()); QTest::qWait(300);
        const QString row = QString::fromLocal8Bit(qgetenv("WB_COMBO_ROW"));
        if (!row.isEmpty()) { auto *outline = win.findChild<OutlinerPanel *>(); QVERIFY(outline); emit outline->rowSelected(row); QTRY_VERIFY(!win.isBusy()); QTest::qWait(300); }
        auto *panel = win.findChild<ComboPanel *>("wbCombo"); auto *tabs = win.findChild<InspectorTabs *>("wbInspectorTabs");
        auto *lanes = win.findChild<RouteLanes *>("wbRouteLanes"); QVERIFY(panel && tabs && lanes);
        tabs->setCurrentWidget(panel); QTest::qWait(300);
        QVERIFY(win.grab().save(QDir(out).filePath("workbench_combo.png")));
        QVERIFY(lanes->grab().save(QDir(out).filePath("real_route_lanes.png")));
        QVERIFY(panel->grab().save(QDir(out).filePath("real_combo_tab.png")));
        if (auto *scroll = panel->findChild<QScrollArea *>("wbComboMapScroll")) {
            auto *map = panel->stringMap(); map->resize(map->sizeHint());
            QVERIFY(map->grab().save(QDir(out).filePath("real_string_map.png")));
        }
        qInfo() << "lanes" << lanes->laneCount() << "nodes" << panel->stringMap()->nodeCount() << "edges" << panel->stringMap()->edgeCount();
    }
    void layoutHoldsAtTheOwnersWindowSizesAndShotsAreSaved_data() {
        QTest::addColumn<int>("w"); QTest::addColumn<int>("h"); QTest::addColumn<QString>("shot");
        QTest::newRow("small") << 1094 << 943 << "combo_1094x943";
        QTest::newRow("portrait") << 1096 << 1888 << "combo_1096x1888";
        QTest::newRow("full") << 1936 << 1048 << "combo_1936x1048";
        QTest::newRow("720p") << 1280 << 720 << "combo_1280x720";
    }
    void layoutHoldsAtTheOwnersWindowSizesAndShotsAreSaved() {
        QFETCH(int, w); QFETCH(int, h); QFETCH(QString, shot);
        QTemporaryDir d; makeProject(d.path()); wbtest::FakeEngine engine;
        Session s(d.path(), &engine); s.data().reload(); registerAllCommands(s);
        WorkbenchWindow win(s); win.resize(w, h); win.show(); QTRY_VERIFY(!win.isBusy()); QTest::qWait(150);
        auto *lanes = win.findChild<RouteLanes *>("wbRouteLanes"); auto *panel = win.findChild<ComboPanel *>("wbCombo");
        auto *tabs = win.findChild<InspectorTabs *>("wbInspectorTabs");
        QVERIFY(lanes && panel && tabs);
        QTRY_COMPARE(lanes->laneCount(), 3);
        QVERIFY2(lanes->isVisible(), "route lanes are on screen");
        QVERIFY2(lanes->mapTo(&win, QPoint(0, 0)).x() >= 0 && lanes->mapTo(&win, QPoint(lanes->width(), 0)).x() <= win.width(), "lanes inside the window");
        tabs->setCurrentWidget(panel); QTest::qWait(120);
        const auto bad = clippedControls(&win, &win);
        QVERIFY2(bad.isEmpty(), qPrintable(bad.join("; ")));
        const QByteArray dir = qgetenv("WB_COMBO_SHOTS");
        if (!dir.isEmpty()) {
            const QString out = QString::fromLocal8Bit(dir); QDir().mkpath(out);
            QVERIFY(win.grab().save(QDir(out).filePath(shot + ".png")));
            if (w == 1936) {
                QVERIFY(lanes->grab().save(QDir(out).filePath("route_lanes.png")));
                QVERIFY(panel->grab().save(QDir(out).filePath("combo_tab.png")));
                if (auto *scroll = panel->findChild<QScrollArea *>("wbComboMapScroll")) QVERIFY(scroll->grab().save(QDir(out).filePath("string_map.png")));
            }
        }
    }
};

QTEST_MAIN(ComboWidgetsTest)
#include "combo_widgets_test.moc"
