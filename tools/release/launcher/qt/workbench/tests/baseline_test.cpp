#include "rebuild_fixture.h"
#include "commands.h"
#include "session.h"
#include <QFile>
#include <QJsonDocument>
#include <QTemporaryDir>
#include <QtTest>

using namespace wb;

static QJsonObject callCmd(Session &s, const QString &name, const QJsonObject &args = {}) {
    CommandContext ctx{s};
    return s.registry().call(name, args, ctx);
}
static void setRebuild(const QString &dir, const QStringList &argv) {
    QFile file(dir + "/workbench.json"); QVERIFY(file.open(QIODevice::ReadOnly));
    auto config = QJsonDocument::fromJson(file.readAll()).object(); file.close();
    config["rebuild"] = QJsonArray::fromStringList(argv);
    QVERIFY(file.open(QIODevice::WriteOnly | QIODevice::Truncate)); file.write(QJsonDocument(config).toJson());
}

class BaselineTest : public QObject {
    Q_OBJECT
private slots:
    void editShowsRevertRestoresAndHistoryUndoes() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); Session s(d.path(), nullptr);
        QVERIFY(s.data().reload().isEmpty()); registerAllCommands(s);
        QCOMPARE(callCmd(s, "list_changes")["result"].toObject()["count"].toInt(), 0);
        const double before = s.data().hitboxes("dair")[0].damage;
        QVERIFY(callCmd(s, "edit_hitbox", {{"row", "dair"}, {"ordinal", 0}, {"damage", before + 3}})["ok"].toBool());
        auto changes = callCmd(s, "list_changes")["result"].toObject()["changes"].toArray();
        QCOMPARE(changes.size(), 1);
        const auto change = changes[0].toObject();
        QCOMPARE(change["kind"].toString(), QString("hitbox")); QCOMPARE(change["field"].toString(), QString("damage"));
        QCOMPARE(change["was"].toDouble(), before); QCOMPARE(change["now"].toDouble(), before + 3);
        const auto reverted = callCmd(s, "revert_change", {{"kind", "hitbox"}, {"row", "dair"}, {"ordinal", 0}, {"field", "damage"}});
        QVERIFY2(reverted["ok"].toBool(), qPrintable(reverted["error"].toString()));
        QCOMPARE(s.data().hitboxes("dair")[0].damage, before);
        QCOMPARE(callCmd(s, "list_changes")["result"].toObject()["count"].toInt(), 0);
        QVERIFY(callCmd(s, "undo")["ok"].toBool()); // the revert went through the normal, undoable path
        QCOMPARE(s.data().hitboxes("dair")[0].damage, before + 3);
        QCOMPARE(callCmd(s, "list_changes")["result"].toObject()["count"].toInt(), 1);
    }
    void rebuildSuccessClearsAndFailureKeeps() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); Session s(d.path(), nullptr);
        QVERIFY(s.data().reload().isEmpty()); registerAllCommands(s);
        QCOMPARE(callCmd(s, "list_changes")["result"].toObject()["count"].toInt(), 0);
        QVERIFY(callCmd(s, "edit_hitbox", {{"row", "dair"}, {"ordinal", 1}, {"size", 5.5}})["ok"].toBool());
        setRebuild(d.path(), wbtest::rebuildHelper("fail"));
        QVERIFY(!callCmd(s, "rebuild")["ok"].toBool());
        QCOMPARE(callCmd(s, "list_changes")["result"].toObject()["count"].toInt(), 1);
        setRebuild(d.path(), wbtest::rebuildHelper());
        QVERIFY(callCmd(s, "rebuild")["ok"].toBool());
        QCOMPARE(callCmd(s, "list_changes")["result"].toObject()["count"].toInt(), 0);
    }
    void revertAllRestoresEveryChangedFile() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); Session s(d.path(), nullptr);
        QVERIFY(s.data().reload().isEmpty()); registerAllCommands(s);
        QCOMPARE(callCmd(s, "list_changes")["result"].toObject()["count"].toInt(), 0);
        const auto first = s.data().hitboxes("dair");
        QVERIFY(callCmd(s, "edit_hitbox", {{"row", "dair"}, {"ordinal", 0}, {"damage", 20}})["ok"].toBool());
        QVERIFY(callCmd(s, "edit_hitbox", {{"row", "dair"}, {"ordinal", 1}, {"angle", 80}})["ok"].toBool());
        QCOMPARE(callCmd(s, "list_changes")["result"].toObject()["count"].toInt(), 2);
        const auto reply = callCmd(s, "revert_all");
        QVERIFY2(reply["ok"].toBool(), qPrintable(reply["error"].toString()));
        QCOMPARE(callCmd(s, "list_changes")["result"].toObject()["count"].toInt(), 0);
        QCOMPARE(s.data().hitboxes("dair")[0].damage, first[0].damage);
        QCOMPARE(s.data().hitboxes("dair")[1].angle, first[1].angle);
    }
};
QTEST_MAIN(BaselineTest)
#include "baseline_test.moc"
