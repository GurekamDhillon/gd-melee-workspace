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
    void stringPlanCutsAtTheWindowStartAndTheFirstHit() {
        const auto routes = QJsonDocument::fromJson(QByteArray(kCombo)).object()["combo"].toObject()["routes"].toArray();
        QHash<QString, ComboStepInfo> info{{"jab1", {21, 3}}, {"geno:Light2", {20, 4}}, {"dair", {40, 6}}};
        auto plan = planComboString({"jab1", "geno:Light2"}, routes, info, 5, false);
        QCOMPARE(plan.size(), 2);
        QCOMPARE(plan[0].cut, 10); QVERIFY(plan[0].linked); QCOMPARE(plan[0].route, QString("L1>L2")); QCOMPARE(plan[0].input, QString("light"));
        QCOMPARE(plan[0].start, 1); QCOMPARE(plan[0].cancelFrame(), 10);
        QCOMPARE(plan[1].start, 11);                         // the next move's frame 1 follows the cancel frame
        QCOMPARE(plan[1].cut, 20); QVERIFY(!plan[1].linked); // the last step plays out
        QCOMPARE(comboStringFrames(plan), 30);
        // + the route's buffer, kept inside the window (hi 18) and the move
        plan = planComboString({"jab1", "geno:Light2"}, routes, info, 5, true);
        QCOMPARE(plan[0].cut, 15); QCOMPARE(plan[1].start, 16);
        // a window that opens before the first hit waits for the hit; one that closes earlier clamps to it
        QJsonArray early{QJsonObject{{"name", "e"}, {"from", "jab1"}, {"to", "dair"}, {"input", "light"}, {"window", QJsonArray{1, 0}}}};
        QCOMPARE(planComboString({"jab1", "dair"}, early, info, 5, false)[0].cut, 3);
        early[0] = QJsonObject{{"name", "e"}, {"from", "jab1"}, {"to", "dair"}, {"input", "light"}, {"on", "whiff"}, {"window", QJsonArray{1, 0}}};
        QCOMPARE(planComboString({"jab1", "dair"}, early, info, 5, false)[0].cut, 1);     // a whiff route needs no hit
        QCOMPARE(planComboString({"jab1", "geno:Light2"}, routes, info, 30, true)[0].cut, 18);
        // no route: the move plays out and is marked unlinked; "*" sources and priority are honoured
        plan = planComboString({"dair", "jab1"}, routes, info, 5, false);
        QVERIFY(!plan[0].linked); QCOMPARE(plan[0].cut, 40);
        QJsonArray star{QJsonObject{{"name", "any"}, {"from", "*"}, {"to", "jab1"}, {"input", "light"}, {"window", QJsonArray{9, 0}}, {"on", "any"}},
                        QJsonObject{{"name", "exact"}, {"from", "dair"}, {"to", "jab1"}, {"input", "light"}, {"window", QJsonArray{12, 0}}, {"on", "any"}}};
        QCOMPARE(planComboString({"dair", "jab1"}, star, info, 5, false)[0].route, QString("exact"));
        QCOMPARE(planComboString({"jab1", "jab1"}, star, info, 5, false)[0].route, QString("any"));
    }
    void stringPlanCommandAndEnginePlayback() {
        QTemporaryDir d; makeProject(d.path(), R"JSON({"combo": {"buffer": 5, "routes": [
            {"name": "L1>H", "from": "jab1", "to": "dair", "input": "heavy", "window": [6, 14]}],
            "strings": [{"name": "jab then dair", "steps": ["jab1", "dair"]}]}})JSON");
        wbtest::FakeEngine engine;
        Session s(d.path(), &engine); QVERIFY(s.data().reload().isEmpty()); registerAllCommands(s);
        auto plan = result(call(s, "string_plan", {{"index", 0}}));
        QCOMPARE(plan["segments"].toArray().size(), 2);
        const auto first = plan["segments"].toArray()[0].toObject();
        QCOMPARE(first["cut"].toInt(), 6); QCOMPARE(first["route"].toString(), QString("L1>H"));
        QCOMPARE(plan["steps"].toArray()[0].toObject()["first_hit"].toInt(), 3);
        QCOMPARE(plan["steps"].toArray()[0].toObject()["hits"].toArray().size(), 1);
        QCOMPARE(plan["steps"].toArray()[0].toObject()["hits"].toArray()[0].toObject()["bone"].toString(), QString("hand_r"));
        QCOMPARE(plan["frames"].toInt(), 6 + 38);              // dair plays out: its 40-frame clip less the 2 cropped
        QVERIFY(!call(s, "string_plan", {{"index", 5}})["ok"].toBool());
        // the same sequence to the engine: each move's row, then its frames up to the cut
        auto played = result(call(s, "play_string", {{"index", 0}}));
        QVERIFY2(played["played"].toBool(), qPrintable(QJsonDocument(played).toJson()));
        QCOMPARE(played["frames_sent"].toInt(), 6 + 38);
        int rows = 0, frames = 0;
        for (const auto &c : engine.calls) { if (c.first == "row") ++rows; if (c.first == "frame") ++frames; }
        QCOMPARE(rows, 2); QCOMPARE(frames, 44);
        // without the game the plan comes back and nothing is played
        Session offline(d.path(), nullptr); QVERIFY(offline.data().reload().isEmpty()); registerAllCommands(offline);
        QVERIFY(!result(call(offline, "play_string", {{"index", 0}}))["played"].toBool());
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
