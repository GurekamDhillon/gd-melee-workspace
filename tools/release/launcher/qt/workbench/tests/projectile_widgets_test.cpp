// Projectiles tab and the spawn lane under the timeline.
#include "atlas_widgets.h"
#include "projectile_widgets.h"
#include "window.h"
#include <QDoubleSpinBox>
#include <QListWidget>
#include <QSignalSpy>
#include <QSpinBox>
#include <QTableWidget>
#include <QtTest>
using namespace wb;

namespace {
QJsonArray sampleArticles() {
    return {QJsonObject{{"name", "Ball"}, {"lifetime", 22}, {"velocity", QJsonArray{3.0, 0}}, {"spawn", QJsonArray{12, 10}},
                {"hitboxes", QJsonArray{QJsonObject{{"slot", 0}, {"damage", 6}, {"size", 3.0}, {"offset", QJsonArray{0, 0, 0}}, {"angle", 361}}}}},
            QJsonObject{{"name", "Arc"}, {"lifetime", 40}}};
}
QJsonArray sampleSpawns() {
    return {QJsonObject{{"row", "volley"}, {"ordinal", 0}, {"frame", 6}, {"article", 0}},
            QJsonObject{{"row", "volley"}, {"ordinal", 1}, {"frame", 14}, {"article", 1}},
            QJsonObject{{"row", "other"}, {"ordinal", 0}, {"frame", 3}, {"article", 0}}};
}
}

class ProjectileWidgetsTest : public QObject {
    Q_OBJECT
private slots:
    void initTestCase() { launcher::spanish = false; launcher::applyTheme(); }

    void laneShowsOnlyTheRowsSpawnsAtTheTimelineFrames() {
        TimelineView timeline; timeline.resize(600, 160); timeline.setMove("volley", 40, {}, 30);
        SpawnLane lane; lane.setTimeline(&timeline); lane.resize(600, 30);
        lane.setSpawns("volley", sampleSpawns(), {"Ball", "Arc"});
        timeline.show(); lane.show();
        QCOMPARE(lane.spawnCount(), 2);
        // the lane maps through the timeline, so a chip sits on its frame's boundary
        const QPoint at = timeline.mapToGlobal(QPoint(int(timeline.framePosition(14)), 0));
        QVERIFY(qAbs(lane.mapFromGlobal(at).x() - (lane.chipRect(1).left() + 6)) <= 1);
        QCOMPARE(lane.frameAt(lane.chipRect(1).left() + 6), 14);
        lane.setSpawns("none", sampleSpawns(), {"Ball", "Arc"});
        QCOMPARE(lane.spawnCount(), 0);
    }
    void draggingAChipRequestsEditSpawn() {
        TimelineView timeline; timeline.resize(600, 160); timeline.setMove("volley", 40, {}, 30);
        SpawnLane lane; lane.setTimeline(&timeline); lane.resize(600, 30);
        lane.setSpawns("volley", sampleSpawns(), {"Ball", "Arc"});
        timeline.show(); lane.show();
        QSignalSpy spy(&lane, &SpawnLane::editRequested);
        const QRectF chip = lane.chipRect(0);
        const QPoint press = chip.center().toPoint();
        const qreal perFrame = (timeline.rulerRect().width()) / 40.0;
        QTest::mousePress(&lane, Qt::LeftButton, {}, press);
        QTest::mouseMove(&lane, press + QPoint(int(perFrame * 3), 0));
        QTest::mouseRelease(&lane, Qt::LeftButton, {}, press + QPoint(int(perFrame * 3), 0));
        QCOMPARE(spy.size(), 1);
        QCOMPARE(spy[0][0].toString(), QString("edit_spawn"));
        const auto args = spy[0][1].toJsonObject();
        QCOMPARE(args["row"].toString(), QString("volley")); QCOMPARE(args["ordinal"].toInt(), 0);
        QCOMPARE(args["frame"].toInt(), 9);
        // a click that does not move asks for nothing
        QTest::mouseClick(&lane, Qt::LeftButton, {}, lane.chipRect(1).center().toPoint());
        QCOMPARE(spy.size(), 1);
        // Delete removes the selected spawn; arrows nudge it
        QTest::keyClick(&lane, Qt::Key_Right);
        QCOMPARE(spy.size(), 2); QCOMPARE(spy[1][1].toJsonObject()["frame"].toInt(), 15);
        QTest::keyClick(&lane, Qt::Key_Delete);
        QCOMPARE(spy[2][0].toString(), QString("delete_spawn"));
    }
    void panelListsEditsAndAddsHitboxes() {
        ProjectilesPanel panel; panel.resize(420, 900); panel.show();
        panel.setData(sampleArticles(), sampleSpawns(), "volley");
        auto *list = panel.findChild<QListWidget *>("wbProjectileList");
        QCOMPARE(list->count(), 2); QVERIFY(list->item(0)->text().startsWith("Ball"));
        QCOMPARE(panel.selectedArticle(), 0);
        QSignalSpy spy(&panel, &ProjectilesPanel::editRequested);
        auto *life = panel.findChild<QSpinBox *>("wbProj_lifetime");
        QCOMPARE(life->value(), 22);
        life->setValue(30);
        QCOMPARE(spy.size(), 1);
        auto ops = spy[0][1].toJsonObject()["ops"].toArray();
        QCOMPARE(spy[0][0].toString(), QString("edit_article"));
        QCOMPARE(ops[0].toObject()["path"].toString(), QString("lifetime")); QCOMPARE(ops[0].toObject()["value"].toInt(), 30);
        // velocity writes the whole pair, keeping the other component
        spy.clear();
        panel.findChild<QDoubleSpinBox *>("wbProj_velocity_0")->setValue(5.5);
        ops = spy[0][1].toJsonObject()["ops"].toArray();
        QCOMPARE(ops[0].toObject()["path"].toString(), QString("velocity"));
        QCOMPARE(ops[0].toObject()["value"].toArray()[0].toDouble(), 5.5);
        // a hitbox cell
        spy.clear();
        auto *table = panel.findChild<QTableWidget *>("wbProjectileBoxes");
        QCOMPARE(table->rowCount(), 1);
        table->item(0, 1)->setText("9");
        ops = spy[0][1].toJsonObject()["ops"].toArray();
        QCOMPARE(ops[0].toObject()["path"].toString(), QString("hitboxes/#0/damage"));
        table->item(0, 5)->setText("-2");
        ops = spy[1][1].toJsonObject()["ops"].toArray();
        QCOMPARE(ops[0].toObject()["path"].toString(), QString("hitboxes/#0/offset"));
        QCOMPARE(ops[0].toObject()["value"].toArray()[2].toDouble(), -2.0);
        // add hitbox
        spy.clear();
        QTest::mouseClick(panel.findChild<QWidget *>("wbProjAddHitbox"), Qt::LeftButton);
        ops = spy[0][1].toJsonObject()["ops"].toArray();
        QCOMPARE(ops[0].toObject()["op"].toString(), QString("insert")); QCOMPARE(ops[0].toObject()["at"].toInt(), 1);
        // add spawn asks the window for the shown frame
        QSignalSpy spawn(&panel, &ProjectilesPanel::addSpawnRequested);
        QTest::mouseClick(panel.findChild<QWidget *>("wbProjAddSpawn"), Qt::LeftButton);
        QCOMPARE(spawn.size(), 1); QCOMPARE(spawn[0][0].toInt(), 0);
    }
    void panelRefreshKeepsSelectionAndDoesNotEcho() {
        ProjectilesPanel panel; panel.show();
        panel.setData(sampleArticles(), sampleSpawns(), "volley");
        panel.selectArticle(1);
        QSignalSpy spy(&panel, &ProjectilesPanel::editRequested);
        panel.setData(sampleArticles(), sampleSpawns(), "volley");
        QCOMPARE(panel.selectedArticle(), 1);
        QCOMPARE(spy.size(), 0);   // refreshing the values from the source is not an edit
        QCOMPARE(panel.findChild<QSpinBox *>("wbProj_lifetime")->value(), 40);
        panel.setData({}, {}, "volley");
        QCOMPARE(panel.selectedArticle(), -1);
    }
};

QTEST_MAIN(ProjectileWidgetsTest)
#include "projectile_widgets_test.moc"
