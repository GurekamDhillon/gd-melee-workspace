#include "window.h"
#define WB_CORE_USE_LAUNCHER_T 1
#include "commands.h"
#include "panels.h"
#include "../testfixture.h"
#include <QTemporaryDir>
#include <QtTest>

using namespace wb;

namespace {
void setMove(const QString &root, const QJsonObject &fields) {
    auto gameplay = QJsonDocument::fromJson(wbtest::kGameplay).object();
    auto moves = gameplay["moves"].toArray();
    auto move = moves[0].toObject();
    for (auto it = fields.begin(); it != fields.end(); ++it) move[it.key()] = it.value();
    moves[0] = move; gameplay["moves"] = moves;
    wbtest::put(root, "gameplay.json", QJsonDocument(gameplay).toJson());
}
}

class PreviewabilityTest : public QObject {
    Q_OBJECT
private slots:
    void initTestCase() { launcher::spanish = false; launcher::applyTheme(); }
    void sourceRefusalIsListedWithReasonAndBlocksEngineCall() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        const QString reason = "This action needs held movement input in the preview scene.";
        setMove(d.path(), {{"previewable", false}, {"preview_reason", reason}});
        wbtest::FakeEngine engine; Session s(d.path(), &engine);
        QVERIFY(s.data().reload().isEmpty()); registerRowCommands(s);
        CommandContext ctx{s};
        const auto listed = s.registry().call("list_rows", {}, ctx)["result"].toObject()["rows"].toArray();
        QVERIFY(!listed[0].toObject()["previewable"].toBool(true));
        QCOMPARE(listed[0].toObject()["preview_reason"].toString(), reason);
        QVERIFY(listed[1].toObject()["previewable"].toBool());
        engine.calls.clear();
        s.currentRow = "dair";
        s.uiView = {{"available", true}, {"revision", 7}, {"row", "dair"}};
        s.blenderAckRevision = 7;
        const auto result = s.registry().call("load_row", {{"row", "jab1"}}, ctx);
        QVERIFY(!result["ok"].toBool());
        QVERIFY(result["error"].toString().contains(reason));
        QVERIFY(engine.calls.isEmpty());
        QVERIFY(s.currentRow.isEmpty());
        QVERIFY(!s.uiView["available"].toBool());
        QCOMPARE(s.uiView["revision"].toInteger(), 8);
        QCOMPARE(s.blenderAckRevision, 0);
    }
    void explicitEmptyClipHasAVisibleReasonWithoutSourceAnnotations() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        setMove(d.path(), {{"pick", QJsonObject{{"clip", ""}}}});
        Session s(d.path(), nullptr); QVERIFY(s.data().reload().isEmpty()); registerRowCommands(s);
        CommandContext ctx{s};
        const auto row = s.registry().call("list_rows", {}, ctx)["result"].toObject()["rows"].toArray()[0].toObject();
        QVERIFY(!row["previewable"].toBool(true));
        QVERIFY(!row["preview_reason"].toString().isEmpty());
        QCOMPARE(row["frames"].toInt(), 0);
        OutlinerPanel panel; panel.setSession(s); panel.refresh();
        QVERIFY(panel.topLevelItem(0)->text(0).contains("not previewable"));
        QVERIFY(panel.topLevelItem(0)->toolTip(0).contains(row["preview_reason"].toString()));
    }
    void movesListPreservesSelectionAndHitboxesForUnavailableRows() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        const QString reason = "This row has no fixed animation.";
        setMove(d.path(), {{"previewable", false}, {"preview_reason", reason}});
        Session s(d.path(), nullptr); QVERIFY(s.data().reload().isEmpty());
        OutlinerPanel panel; panel.setSession(s); panel.refresh(); panel.setSelection("jab1", 0);
        panel.setGrouped(true); panel.setFilter("jab1");
        auto *item = panel.topLevelItem(0);
        QVERIFY(item->text(0).contains("not previewable"));
        QVERIFY(item->toolTip(0).contains(reason));
        QCOMPARE(item->childCount(), 1);
        QCOMPARE(panel.currentItem(), item->child(0));
        QVERIFY(!item->isHidden());
    }
    void oldSafetyListStillWinsOverAnExplicitTrueFlag() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        setMove(d.path(), {{"motions", QJsonArray{12}}, {"previewable", true}});
        Session s(d.path(), nullptr); QVERIFY(s.data().reload().isEmpty()); registerRowCommands(s);
        CommandContext ctx{s};
        const auto row = s.registry().call("list_rows", {}, ctx)["result"].toObject()["rows"].toArray()[0].toObject();
        QVERIFY(!row["previewable"].toBool(true));
        QVERIFY(row["preview_reason"].toString().contains("platform"));
    }
    void missingEngineMotionIsMarkedOnlyUntilTheEngineRestarts() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        QFile source(QDir(d.path()).filePath("gameplay.json"));
        QVERIFY(source.open(QIODevice::ReadOnly)); const auto before = source.readAll(); source.close();
        wbtest::FakeEngine engine; Session s(d.path(), &engine);
        QVERIFY(s.data().reload().isEmpty()); registerRowCommands(s); registerViewCommands(s);
        CommandContext ctx{s};
        s.currentRow = "dair";
        s.uiView = {{"available", true}, {"revision", 7}, {"row", "dair"}};
        s.blenderAckRevision = 7;
        engine.failWith = "no such motion for this fighter";
        QVERIFY(!s.registry().call("load_row", {{"row", "jab1"}}, ctx)["ok"].toBool());
        QVERIFY(s.currentRow.isEmpty());
        QVERIFY(!s.uiView["available"].toBool());
        QCOMPARE(s.uiView["revision"].toInteger(), 8);
        QCOMPARE(s.blenderAckRevision, 0);
        auto rows = s.registry().call("list_rows", {}, ctx)["result"].toObject()["rows"].toArray();
        QVERIFY(!rows[0].toObject()["previewable"].toBool(true));
        QVERIFY(rows[0].toObject()["preview_reason"].toString().contains("no such motion"));
        engine.calls.clear();
        QVERIFY(!s.registry().call("load_row", {{"row", "jab1"}}, ctx)["ok"].toBool());
        QVERIFY(engine.calls.isEmpty());
        engine.failWith.clear();
        QVERIFY(s.registry().call("engine_restart", {}, ctx)["ok"].toBool());
        rows = s.registry().call("list_rows", {}, ctx)["result"].toObject()["rows"].toArray();
        QVERIFY(rows[0].toObject()["previewable"].toBool());
        QVERIFY(rows[0].toObject()["preview_reason"].toString().isEmpty());
        QVERIFY(source.open(QIODevice::ReadOnly)); QCOMPARE(source.readAll(), before);
    }
    void connectionFailureKeepsTheLastValidPreview() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        wbtest::FakeEngine engine; Session s(d.path(), &engine);
        QVERIFY(s.data().reload().isEmpty()); registerRowCommands(s);
        CommandContext ctx{s};
        QVERIFY(s.registry().call("load_row", {{"row", "dair"}}, ctx)["ok"].toBool());
        const QJsonObject view{{"available", true}, {"revision", 7}, {"row", "dair"}};
        s.uiView = view; s.blenderAckRevision = 7;
        engine.failWith = "connection lost";
        QVERIFY(!s.registry().call("load_row", {{"row", "jab1"}}, ctx)["ok"].toBool());
        QCOMPARE(s.currentRow, QString("dair"));
        QCOMPARE(s.uiView, view);
        QCOMPARE(s.blenderAckRevision, 7);
        QVERIFY(s.data().rows()[0].previewable());
    }
};
QTEST_MAIN(PreviewabilityTest)
#include "previewability_test.moc"
