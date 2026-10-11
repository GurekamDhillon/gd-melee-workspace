#include "../testfixture.h"
#include "commands.h"
#include "geno_asm.h"
#include "geno_data.h"
#include <QTemporaryDir>
#include <QtTest>

using namespace wb;

namespace {
// A gameplay.json laid out as Python's json.dump(indent=2) writes the real one, with two articles.
const char *kGameplayWithArticles = R"JSON({
  "version": 1,
  "moves": [
    {
      "name": "jab1",
      "motions": [44],
      "tag": "jab",
      "script": "moves/jab1.genoasm",
      "iasa": 30,
      "pick": {"status": "provisional", "clip": "SYN_ATC_002", "crop_start": 9, "startup": 3}
    },
    {
      "name": "volley",
      "motions": [70],
      "tag": "special",
      "script": "moves/volley.genoasm",
      "iasa": 36,
      "pick": {"status": "provisional", "clip": "SYN_ATC_007", "crop_start": 2, "startup": 6}
    }
  ],
  "states": [],
  "articles": [
    {
      "name": "Ball",
      "lifetime": 22,
      "velocity": [
        3.0,
        0
      ],
      "spawn": [
        12,
        10
      ],
      "max_live": 1,
      "hitboxes": [
        {
          "slot": 0,
          "damage": 6,
          "size": 3.0,
          "offset": [
            0,
            0,
            0
          ],
          "angle": 361,
          "start": 1,
          "end": 0
        }
      ],
      "scale": 1.0
    },
    {
      "name": "Bolt",
      "lifetime": 10
    }
  ]
}
)JSON";
const char *kVolley = "# synthetic\nPUT ANIM_RATE 1.0\nwait 6\nCALL geno.article.spawn 0\nwait 8\nCALL geno.article.spawn 0\nwait_until 30\niasa\n";

QByteArray disk(const QString &dir, const QString &rel) {
    QFile f(QDir(dir).filePath(rel));
    return f.open(QIODevice::ReadOnly) ? f.readAll() : QByteArray();
}
QString makeProject(const QString &dir, const QByteArray &volley = kVolley) {
    wbtest::makeSynthFighter(dir);
    wbtest::put(dir, "gameplay.json", kGameplayWithArticles);
    wbtest::put(dir, "moves/volley.genoasm", volley);
    return dir;
}
QJsonObject articleAt(const QString &dir, int i) {
    return QJsonDocument::fromJson(disk(dir, "gameplay.json")).object()["articles"].toArray()[i].toObject();
}
QJsonArray ops(std::initializer_list<QJsonObject> list) {
    QJsonArray a; for (const auto &o : list) a.append(o); return a;
}
}

class ProjectilesTest : public QObject {
    Q_OBJECT
private slots:
    void spawnsAreReadWithFramesAndDecodedArgument() {
        const auto spawns = GenoAsm::parse(kVolley).spawns();
        QCOMPARE(spawns.size(), 2);
        QCOMPARE(spawns[0].frame, 6); QCOMPARE(spawns[0].article, 0); QCOMPARE(spawns[0].line, 3);
        QCOMPARE(spawns[1].frame, 14);
        const auto packed = GenoAsm::parse("wait 2\nCALL geno.article.spawn 4294574595\n").spawns();  // article 3, variant 2, angle -6
        QCOMPARE(packed.size(), 1);
        QCOMPARE(packed[0].article, 3); QCOMPARE(packed[0].variant, 2); QCOMPARE(packed[0].angle, -6); QCOMPARE(packed[0].frame, 2);
    }
    void spawnReadingStopsAtLoopsAndIgnoresComments() {
        QCOMPARE(GenoAsm::parse("wait 2\n# CALL geno.article.spawn 1\nloop 3\nCALL geno.article.spawn 1\n").spawns().size(), 0);
        QCOMPARE(GenoAsm::parse("wait 2\nCALL geno.article.spawn 1  # fire\n").spawns().size(), 1);
    }
    void moveRebalancesTheWaitsAroundIt() {
        QString err;
        const QString moved = GenoAsm::parse(kVolley).moveSpawn(0, 8, &err);
        QVERIFY2(!moved.isNull(), qPrintable(err));
        QCOMPARE(moved, QString("# synthetic\nPUT ANIM_RATE 1.0\nwait 8\nCALL geno.article.spawn 0\nwait 6\nCALL geno.article.spawn 0\nwait_until 30\niasa\n"));
        const auto after = GenoAsm::parse(moved).spawns();
        QCOMPARE(after[0].frame, 8); QCOMPARE(after[1].frame, 14);
        QCOMPARE(GenoAsm::parse(kVolley).moveSpawn(1, 20, &err),
                 QString("# synthetic\nPUT ANIM_RATE 1.0\nwait 6\nCALL geno.article.spawn 0\nwait 14\nCALL geno.article.spawn 0\nwait_until 30\niasa\n"));
    }
    void moveIntoAnEarlierSlotSplitsAWait() {
        QString err;
        // The spawn shares its frame with the next spawn, so it is lifted out and re-inserted.
        const QString moved = GenoAsm::parse(kVolley).moveSpawn(1, 3, &err);
        QVERIFY2(!moved.isNull(), qPrintable(err));
        const auto spawns = GenoAsm::parse(moved).spawns();
        QCOMPARE(spawns.size(), 2);
        QCOMPARE(spawns[0].frame, 3); QCOMPARE(spawns[1].frame, 6);
    }
    void moveBeyondTheEndAppendsAndBadMovesAreRefused() {
        QString err;
        const QString text = "wait 2\nCALL geno.article.spawn 0\nwait_until 10\niasa\n";
        QVERIFY(GenoAsm::parse(text).moveSpawn(0, 12, &err).isNull() == false);  // lifts it: nothing else moves
        const QString moved = GenoAsm::parse(text).moveSpawn(0, 12, &err);
        QCOMPARE(GenoAsm::parse(moved).spawns()[0].frame, 12);
        QVERIFY(GenoAsm::parse(moved).moveSpawn(0, -1, &err).isNull());
        QVERIFY(GenoAsm::parse("loop 2\nCALL geno.article.spawn 0\n").moveSpawn(0, 5, &err).isNull());
    }
    void moveKeepsOtherCommandsOnTheirFrames() {
        QString err;
        const QString text = "wait_until 3\nhitbox slot=0 joint=@HAND_R@ damage=3 size=3.4 x=0 y=0 z=0 angle=361 kbg=50 fkb=0 bkb=8\n"
                             "CALL geno.article.spawn 1\nwait 2\nclear_hitboxes\nwait_until 18\niasa\n";
        const QString moved = GenoAsm::parse(text).moveSpawn(0, 6, &err);
        QVERIFY2(!moved.isNull(), qPrintable(err));
        QCOMPARE(GenoAsm::parse(moved).spawns()[0].frame, 6);
        const auto hb = GenoAsm::parse(moved).hitboxes();
        QCOMPARE(hb.size(), 1); QCOMPARE(hb[0].startFrame, 3); QCOMPARE(hb[0].endFrame, 5);
    }
    void addAndRemoveSpawn() {
        QString err; int ordinal = -1;
        const QString added = GenoAsm::parse(kVolley).addSpawn(10, 1, &err, &ordinal);
        QVERIFY2(!added.isNull(), qPrintable(err));
        QCOMPARE(ordinal, 1);
        const auto spawns = GenoAsm::parse(added).spawns();
        QCOMPARE(spawns.size(), 3);
        QCOMPARE(spawns[1].frame, 10); QCOMPARE(spawns[1].article, 1); QCOMPARE(spawns[2].frame, 14);
        const auto back = GenoAsm::parse(GenoAsm::parse(added).removeSpawn(1, &err)).spawns();
        QCOMPARE(back.size(), 2); QCOMPARE(back[0].frame, 6); QCOMPARE(back[1].frame, 14);
        QVERIFY(GenoAsm::parse(kVolley).removeSpawn(5, &err).isNull());
        const QString end = GenoAsm::parse("wait 2\niasa\n").addSpawn(9, 0, &err);
        QCOMPARE(GenoAsm::parse(end).spawns()[0].frame, 9);
    }
    void setArgumentKeepsTheFrame() {
        QString err;
        const QString out = GenoAsm::parse(kVolley).setSpawnArg(0, 1, &err);
        QCOMPARE(out, QString("# synthetic\nPUT ANIM_RATE 1.0\nwait 6\nCALL geno.article.spawn 1\nwait 8\nCALL geno.article.spawn 0\nwait_until 30\niasa\n"));
    }

    void articleEditsChangeOnlyTheLeaf() {
        QTemporaryDir d; makeProject(d.path());
        Session s(d.path(), nullptr); QVERIFY(s.data().reload().isEmpty());
        const QByteArray before = disk(d.path(), "gameplay.json");
        QString err;
        auto edits = s.data().editArticle(0, ops({{{"op", "set"}, {"path", "velocity/#0"}, {"value", 5.5}},
                                                  {{"op", "set"}, {"path", "hitboxes/#0/damage"}, {"value", 9}}}), &err);
        QVERIFY2(err.isEmpty(), qPrintable(err));
        QCOMPARE(edits.size(), 1);
        const QString after = QString::fromUtf8(edits[0].after);
        QString was = QString::fromUtf8(before);
        was.replace("        3.0,\n        0\n", "        5.5,\n        0\n");
        was.replace("\"damage\": 6,", "\"damage\": 9,");
        QCOMPARE(after, was);  // nothing but those two numbers moved
        QCOMPARE(s.data().editArticle(0, {}, &err).size(), 0);  // an unchanged article is no change
    }
    void articleMissingKeysAreInsertedAndNested() {
        QTemporaryDir d; makeProject(d.path());
        Session s(d.path(), nullptr); QVERIFY(s.data().reload().isEmpty());
        QString err;
        const auto edits = s.data().editArticle(1, ops({{{"op", "set"}, {"path", "gravity"}, {"value", 0.2}},
                                                        {{"op", "set"}, {"path", "homing/turn"}, {"value", 7}},
                                                        {{"op", "set"}, {"path", "model/file"}, {"value", "Ball.dat"}}}), &err);
        QVERIFY2(err.isEmpty(), qPrintable(err));
        const auto doc = QJsonDocument::fromJson(edits[0].after).object()["articles"].toArray()[1].toObject();
        QCOMPARE(doc["gravity"].toDouble(), 0.2);
        QCOMPARE(doc["homing"].toObject()["turn"].toInt(), 7);
        QCOMPARE(doc["model"].toObject()["file"].toString(), QString("Ball.dat"));
        QCOMPARE(doc["lifetime"].toInt(), 10);
    }
    void articleHitboxInsertAndRemove() {
        QTemporaryDir d; makeProject(d.path());
        Session s(d.path(), nullptr); QVERIFY(s.data().reload().isEmpty());
        QString err;
        auto edits = s.data().editArticle(0, ops({{{"op", "insert"}, {"path", "hitboxes"}, {"at", 1},
                                                   {"value", QJsonObject{{"slot", 1}, {"damage", 4}, {"size", 2.5}}}}}), &err);
        QVERIFY2(err.isEmpty(), qPrintable(err));
        auto art = QJsonDocument::fromJson(edits[0].after).object()["articles"].toArray()[0].toObject();
        QCOMPARE(art["hitboxes"].toArray().size(), 2);
        QCOMPARE(art["hitboxes"].toArray()[1].toObject()["size"].toDouble(), 2.5);
        edits = s.data().editArticle(0, ops({{{"op", "remove"}, {"path", "hitboxes"}, {"at", 0}}}), &err);
        art = QJsonDocument::fromJson(edits[0].after).object()["articles"].toArray()[0].toObject();
        QCOMPARE(art["hitboxes"].toArray().size(), 0);
        // an array that is missing is created by an insert at 0
        edits = s.data().editArticle(1, ops({{{"op", "insert"}, {"path", "hitboxes"}, {"at", 0}, {"value", QJsonObject{{"damage", 2}}}}}), &err);
        QVERIFY2(err.isEmpty(), qPrintable(err));
        QCOMPARE(QJsonDocument::fromJson(edits[0].after).object()["articles"].toArray()[1].toObject()["hitboxes"].toArray().size(), 1);
    }
    void badEditsAreRefused() {
        QTemporaryDir d; makeProject(d.path());
        Session s(d.path(), nullptr); QVERIFY(s.data().reload().isEmpty());
        QString err;
        QVERIFY(s.data().editArticle(7, ops({{{"op", "set"}, {"path", "lifetime"}, {"value", 3}}}), &err).isEmpty() && !err.isEmpty());
        QVERIFY(s.data().editArticle(0, ops({{{"op", "unset"}, {"path", "scale"}}}), &err).isEmpty() && !err.isEmpty());
        QVERIFY(s.data().editArticle(0, ops({{{"op", "remove"}, {"path", "hitboxes"}, {"at", 4}}}), &err).isEmpty() && !err.isEmpty());
        QVERIFY(s.data().editArticle(0, ops({{{"op", "bogus"}, {"path", "x"}}}), &err).isEmpty() && !err.isEmpty());
    }
    void addAndDeleteArticle() {
        QTemporaryDir d; makeProject(d.path());
        Session s(d.path(), nullptr); QVERIFY(s.data().reload().isEmpty());
        QString err; int index = -1;
        const auto edits = s.data().addArticle(QJsonObject{{"name", "Wave"}, {"lifetime", 5}}, &index, &err);
        QVERIFY2(err.isEmpty(), qPrintable(err));
        QCOMPARE(index, 2);
        QCOMPARE(QJsonDocument::fromJson(edits[0].after).object()["articles"].toArray().size(), 3);
        QVERIFY(s.data().addArticle(QJsonObject{{"name", "Ball"}}, &index, &err).isEmpty());  // duplicate name
        QVERIFY(s.data().removeArticle(0, &err).isEmpty());                                   // not the last
        QVERIFY(!s.data().removeArticle(1, &err).isEmpty());                                  // the last, unspawned
    }
    void deleteRefusedWhileAScriptSpawnsIt() {
        QTemporaryDir d; makeProject(d.path(), "wait 2\nCALL geno.article.spawn 1\niasa\n");
        Session s(d.path(), nullptr); QVERIFY(s.data().reload().isEmpty());
        QString err;
        QVERIFY(s.data().removeArticle(1, &err).isEmpty());
        QVERIFY2(err.contains("volley"), qPrintable(err));
    }
    void commandsListEditAndUndo() {
        QTemporaryDir d; makeProject(d.path());
        Session s(d.path(), nullptr); QVERIFY(s.data().reload().isEmpty());
        registerProjectileCommands(s);
        CommandContext c{s};
        const auto listed = s.registry().call("list_articles", {}, c)["result"].toObject()["articles"].toArray();
        QCOMPARE(listed.size(), 2); QCOMPARE(listed[0].toObject()["name"].toString(), QString("Ball"));
        QCOMPARE(listed[1].toObject()["index"].toInt(), 1);
        const auto spawns = s.registry().call("list_spawns", {{"row", "volley"}}, c)["result"].toObject()["spawns"].toArray();
        QCOMPARE(spawns.size(), 2); QCOMPARE(spawns[1].toObject()["frame"].toInt(), 14);
        const auto edited = s.registry().call("edit_spawn", {{"row", "volley"}, {"ordinal", 0}, {"frame", 9}}, c);
        QVERIFY2(edited["ok"].toBool(), qPrintable(QJsonDocument(edited).toJson()));
        QCOMPARE(s.data().spawns("volley")[0].toObject()["frame"].toInt(), 9);
        QVERIFY(QString::fromUtf8(disk(d.path(), "moves/volley.genoasm")).contains("wait 9\nCALL"));
        const auto art = s.registry().call("edit_article", {{"index", 0},
            {"ops", ops({{{"op", "set"}, {"path", "lifetime"}, {"value", 40}}})}}, c);
        QVERIFY2(art["ok"].toBool(), qPrintable(QJsonDocument(art).toJson()));
        QCOMPARE(articleAt(d.path(), 0)["lifetime"].toInt(), 40);
        QVERIFY(s.registry().call("edit_spawn", {{"row", "volley"}, {"ordinal", 0}, {"article", 9}}, c)["ok"].toBool() == false);
        QVERIFY(s.registry().call("add_spawn", {{"row", "volley"}, {"frame", 12}, {"article", 1}}, c)["ok"].toBool());
        QCOMPARE(s.data().spawns("volley").size(), 3);
        QVERIFY(s.registry().call("delete_spawn", {{"row", "volley"}, {"ordinal", 1}}, c)["ok"].toBool());
        QCOMPARE(s.data().spawns("volley").size(), 2);
        QVERIFY(s.registry().call("add_article", {{"article", QJsonObject{{"name", "Wave"}}}}, c)["ok"].toBool());
        QVERIFY(s.registry().call("delete_article", {{"index", 2}}, c)["ok"].toBool());
        QVERIFY(s.registry().call("list_spawns", {{"row", "nope"}}, c)["ok"].toBool() == false);
    }
};

QTEST_GUILESS_MAIN(ProjectilesTest)
#include "projectiles_test.moc"
