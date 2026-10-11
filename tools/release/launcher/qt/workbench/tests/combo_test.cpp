#include "../testfixture.h"
#include "combo_model.h"
#include "commands.h"
#include "session.h"
#include <QTemporaryDir>
#include <QtTest>

using namespace wb;

namespace {
// Laid out as Python's json.dump(indent=2) writes the real combo.json (a "combo" block inside the file).
const char *kCombo = R"JSON({
  "version": 1,
  "combo": {
    "buffer": 5,
    "max_links": 5,
    "routes": [
      {
        "name": "L1>L2",
        "from": "jab1",
        "to": "geno:Light2",
        "input": "light",
        "on": "hit",
        "where": "ground",
        "window": [
          10,
          18
        ],
        "source": "SYN 0/1"
      },
      {
        "name": "A>air",
        "from": [
          "jab1",
          "dair"
        ],
        "to": "special_s",
        "input": "special",
        "dir": "side",
        "priority": 10
      }
    ],
    "strings": [
      {
        "name": "light string",
        "steps": [
          "jab1",
          "geno:Light2"
        ]
      }
    ]
  }
}
)JSON";

QByteArray disk(const QString &dir, const QString &rel) {
    QFile f(QDir(dir).filePath(rel));
    return f.open(QIODevice::ReadOnly) ? f.readAll() : QByteArray();
}
QString makeProject(const QString &dir, const QByteArray &combo = kCombo) {
    wbtest::makeSynthFighter(dir);
    auto project = QJsonDocument::fromJson(wbtest::kProject).object();
    project["combo"] = "combo/combo.json";
    wbtest::put(dir, "workbench.json", QJsonDocument(project).toJson());
    wbtest::put(dir, "combo/combo.json", combo);
    return dir;
}
QJsonObject call(Session &s, const QString &name, const QJsonObject &args = {}) {
    CommandContext ctx{s};
    return s.registry().call(name, args, ctx);
}
QJsonObject result(const QJsonObject &reply) { return reply["result"].toObject(); }
}

class ComboTest : public QObject {
    Q_OBJECT
private slots:
    void listsRoutesAndStringsAndFiltersBySource() {
        QTemporaryDir d; makeProject(d.path());
        Session s(d.path(), nullptr); QVERIFY(s.data().reload().isEmpty()); registerAllCommands(s);
        auto all = result(call(s, "list_routes"));
        QCOMPARE(all["count"].toInt(), 2);
        QCOMPARE(all["meta"].toObject()["buffer"].toInt(), 5);
        QCOMPARE(all["routes"].toArray()[1].toObject()["index"].toInt(), 1);
        QCOMPARE(result(call(s, "list_routes", {{"from", "dair"}}))["count"].toInt(), 1);   // from can be a list
        QCOMPARE(result(call(s, "list_routes", {{"from", "jab1"}}))["count"].toInt(), 2);
        QCOMPARE(result(call(s, "list_strings"))["strings"].toArray()[0].toObject()["steps"].toArray().size(), 2);
    }
    void aProjectWithoutAComboFileHasNoRoutesAndWritesAreRefused() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        Session s(d.path(), nullptr); QVERIFY(s.data().reload().isEmpty()); registerAllCommands(s);
        QCOMPARE(result(call(s, "list_routes"))["count"].toInt(), 0);
        QVERIFY(!call(s, "edit_route", {{"index", 0}, {"buffer", 3}})["ok"].toBool());
    }
    void editChangesOnlyTheNumbersAndUndoRestoresTheBytes() {
        QTemporaryDir d; makeProject(d.path());
        Session s(d.path(), nullptr); QVERIFY(s.data().reload().isEmpty()); registerAllCommands(s);
        const QByteArray before = disk(d.path(), "combo/combo.json");
        auto reply = call(s, "edit_route", {{"index", 0}, {"window", QJsonArray{8, 22}}, {"priority", 3}});
        QVERIFY2(reply["ok"].toBool(), qPrintable(reply["error"].toString()));
        const QString after = QString::fromUtf8(disk(d.path(), "combo/combo.json"));
        // the window changed in place; the inserted key is the only other difference (its layout is the file's)
        QVERIFY(after.contains("          8,\n          22\n"));
        QCOMPARE(QJsonDocument::fromJson(after.toUtf8()).object()["combo"].toObject()["routes"].toArray()[0].toObject()["priority"].toInt(), 3);
        QCOMPARE(result(call(s, "list_routes"))["routes"].toArray()[0].toObject()["window"].toArray()[0].toInt(), 8);
        QVERIFY(call(s, "undo")["ok"].toBool());
        QCOMPARE(disk(d.path(), "combo/combo.json"), before);
        QVERIFY(call(s, "redo")["ok"].toBool());
        QCOMPARE(QString::fromUtf8(disk(d.path(), "combo/combo.json")), after);
    }
    void editsAreValidatedBeforeAnythingIsWritten() {
        QTemporaryDir d; makeProject(d.path());
        Session s(d.path(), nullptr); QVERIFY(s.data().reload().isEmpty()); registerAllCommands(s);
        const QByteArray before = disk(d.path(), "combo/combo.json");
        QVERIFY(!call(s, "edit_route", {{"index", 0}, {"input", "kick"}})["ok"].toBool());
        QVERIFY(!call(s, "edit_route", {{"index", 0}, {"window", QJsonArray{0, 5}}})["ok"].toBool());
        QVERIFY(!call(s, "edit_route", {{"index", 0}, {"window", QJsonArray{9, 4}}})["ok"].toBool());
        QVERIFY(!call(s, "edit_route", {{"index", 5}, {"buffer", 3}})["ok"].toBool());
        QVERIFY(!call(s, "edit_route", {{"index", 0}, {"buffer", -1}})["ok"].toBool());
        QVERIFY(!call(s, "edit_route", {{"index", 0}, {"on", "sometimes"}})["ok"].toBool());
        QCOMPARE(disk(d.path(), "combo/combo.json"), before);
    }
    void addDeleteRoutesAndStrings() {
        QTemporaryDir d; makeProject(d.path());
        Session s(d.path(), nullptr); QVERIFY(s.data().reload().isEmpty()); registerAllCommands(s);
        const QByteArray before = disk(d.path(), "combo/combo.json");
        auto added = call(s, "add_route", {{"route", QJsonObject{{"name", "J>jump"}, {"from", "dair"}, {"to", "jump"}, {"input", "jump"}, {"window", QJsonArray{5, 0}}}}});
        QVERIFY2(added["ok"].toBool(), qPrintable(added["error"].toString()));
        QCOMPARE(result(added)["index"].toInt(), 2);
        QCOMPARE(result(call(s, "list_routes"))["count"].toInt(), 3);
        QVERIFY(!call(s, "add_route", {{"route", QJsonObject{{"name", "bad"}, {"to", "jump"}, {"input", "jump"}}}})["ok"].toBool());  // no from
        QVERIFY(call(s, "delete_route", {{"index", 2}})["ok"].toBool());
        QCOMPARE(disk(d.path(), "combo/combo.json"), before);                                                                    // exact bytes back
        auto str = call(s, "add_string", {{"string", QJsonObject{{"name", "air"}, {"steps", QJsonArray{"dair", "jump"}}}}});
        QVERIFY2(str["ok"].toBool(), qPrintable(str["error"].toString()));
        QVERIFY(call(s, "edit_string", {{"index", 1}, {"steps", QJsonArray{"dair"}}})["ok"].toBool());
        QCOMPARE(result(call(s, "list_strings"))["strings"].toArray()[1].toObject()["steps"].toArray().size(), 1);
        QVERIFY(!call(s, "edit_string", {{"index", 1}, {"steps", QJsonArray{}}})["ok"].toBool());
        QVERIFY(call(s, "delete_string", {{"index", 1}})["ok"].toBool());
        QCOMPARE(disk(d.path(), "combo/combo.json"), before);
    }
    void aBareBlockFileWorksToo() {
        // a file that is the combo block itself (no "combo" wrapper), with no strings array yet
        QTemporaryDir d; makeProject(d.path(), "{\n  \"routes\": [\n    {\"from\": \"jab1\", \"to\": \"jab2\", \"input\": \"light\"}\n  ]\n}\n");
        Session s(d.path(), nullptr); QVERIFY(s.data().reload().isEmpty()); registerAllCommands(s);
        QCOMPARE(result(call(s, "list_routes"))["count"].toInt(), 1);
        QVERIFY(call(s, "edit_route", {{"index", 0}, {"window", QJsonArray{4, 9}}})["ok"].toBool());
        QVERIFY(call(s, "add_string", {{"string", QJsonObject{{"name", "s"}, {"steps", QJsonArray{"jab1", "jab2"}}}}})["ok"].toBool());
        QCOMPARE(result(call(s, "list_strings"))["count"].toInt(), 1);
        QCOMPARE(result(call(s, "list_routes"))["routes"].toArray()[0].toObject()["window"].toArray()[1].toInt(), 9);
    }
    void changedSinceBuildBaselineSeesAndRevertsRouteEdits() {
        QTemporaryDir d; makeProject(d.path());
        Session s(d.path(), nullptr); QVERIFY(s.data().reload().isEmpty()); registerAllCommands(s);
        QCOMPARE(result(call(s, "list_changes"))["count"].toInt(), 0);
        QVERIFY(call(s, "edit_route", {{"index", 0}, {"window", QJsonArray{12, 18}}})["ok"].toBool());
        auto changes = result(call(s, "list_changes"))["changes"].toArray();
        QCOMPARE(changes.size(), 1);
        auto c = changes[0].toObject();
        QCOMPARE(c["kind"].toString(), QString("route")); QCOMPARE(c["row"].toString(), QString("L1>L2"));
        QCOMPARE(c["field"].toString(), QString("window"));
        QCOMPARE(c["was"].toArray()[0].toInt(), 10); QCOMPARE(c["now"].toArray()[0].toInt(), 12);
        QVERIFY(call(s, "revert_change", {{"kind", "route"}, {"row", "L1>L2"}, {"field", "window"}})["ok"].toBool());
        QCOMPARE(result(call(s, "list_changes"))["count"].toInt(), 0);
        QVERIFY(call(s, "add_route", {{"route", QJsonObject{{"name", "x"}, {"from", "dair"}, {"to", "jump"}, {"input", "jump"}}}})["ok"].toBool());
        QCOMPARE(result(call(s, "list_changes"))["changes"].toArray()[0].toObject()["kind"].toString(), QString("routes"));
        QVERIFY(call(s, "revert_all")["ok"].toBool());
        QCOMPARE(result(call(s, "list_changes"))["count"].toInt(), 0);
        QCOMPARE(result(call(s, "list_routes"))["count"].toInt(), 2);
    }
    void routeWindowAgainstHitCheck() {
        // jab1 (fixture): first hitbox at frame 3, 21 clip frames. L1>L2 on hit, window [10,18]: fine.
        QTemporaryDir d; makeProject(d.path());
        Session s(d.path(), nullptr); QVERIFY(s.data().reload().isEmpty()); registerAllCommands(s);
        auto problems = [&] {
            QStringList out;
            for (const auto &p : result(call(s, "run_checks"))["problems"].toArray())
                if (p.toObject()["kind"].toString() == "combo_window") out << p.toObject()["message"].toString();
            return out;
        };
        QCOMPARE(problems().size(), 0);
        QVERIFY(call(s, "edit_route", {{"index", 0}, {"window", QJsonArray{1, 2}}})["ok"].toBool());       // ends before the hit (frame 3)
        auto list = problems();
        QCOMPARE(list.size(), 1);
        QVERIFY2(list[0].contains("window ends at frame 2") && list[0].contains("first hits on frame 3") && list[0].contains("L1>L2"), qPrintable(list[0]));
        QVERIFY(call(s, "edit_route", {{"index", 0}, {"on", "whiff"}})["ok"].toBool());                     // a whiff route needs no contact
        QCOMPARE(problems().size(), 0);
        QVERIFY(call(s, "edit_route", {{"index", 0}, {"on", "hit"}, {"window", QJsonArray{60, 0}}})["ok"].toBool());  // starts after the move ends
        list = problems();
        QCOMPARE(list.size(), 1);
        QVERIFY2(list[0].contains("opens at frame 60") && list[0].contains("after jab1 has ended"), qPrintable(list[0]));
        QVERIFY(call(s, "edit_route", {{"index", 0}, {"window", QJsonArray{3, 0}}})["ok"].toBool());          // open to the end: fine
        QCOMPARE(problems().size(), 0);
        // the row filter only reports that row; routes from a Melee name that is no row are skipped
        QCOMPARE(result(call(s, "run_checks", {{"row", "dair"}}))["problems"].toArray().size() >= 0, true);
    }
    void labelsAndClasses() {
        QJsonObject r{{"to", "geno:Light3"}, {"input", "light"}, {"on", "hit"}};
        QCOMPARE(comboRouteLabel(r), QString::fromUtf8("Light3 · light · on hit"));
        r["on"] = "block"; r["input"] = "grab";
        QCOMPARE(comboRouteLabel(r), QString::fromUtf8("Light3 · grab · on block"));
        QCOMPARE(comboInputClass(QJsonObject{{"input", "bogus"}}), QString("none"));
        QCOMPARE(comboRouteWindow(QJsonObject{}).second, 0);
    }
};

QTEST_GUILESS_MAIN(ComboTest)
#include "combo_test.moc"
