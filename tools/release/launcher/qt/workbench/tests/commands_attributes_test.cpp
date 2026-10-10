#include "../testfixture.h"
#include "commands.h"
#include "geno_data.h"
#include <QTemporaryDir>
#include <QtTest>
using namespace wb;

namespace {
QByteArray disk(const QString &dir, const QString &path = "gameplay.json") {
    QFile file(QDir(dir).filePath(path));
    return file.open(QIODevice::ReadOnly) ? file.readAll() : QByteArray{};
}
void fixture(const QString &dir) {
    wbtest::makeSynthFighter(dir);
    QByteArray gameplay(wbtest::kGameplay);
    gameplay.replace("\"version\": 1", "\"version\": 1,\n  \"attributes\": {\"weight\": 73.25, \"walk_max_vel\": 1.25, \"rapid_jab_window\": 4},\n  \"jumps\": {\"max\": 3, \"air_vy\": [2.5, 1.75]}");
    wbtest::put(dir, "gameplay.json", gameplay);
    wbtest::put(dir, "package/geno.json", R"JSON({"geno":11,"fighters":[{"define":{"key":"synth"},"attributes":{"weight":65,"gravity":0.125,"initial_shield_size":7.5}}]})JSON");
}
QJsonObject call(Session &s, const QString &command, const QJsonObject &args = {}, const QString &author = "human") {
    CommandContext ctx{s, author};
    return s.registry().call(command, args, ctx);
}
QJsonObject attribute(const QJsonObject &reply, const QString &name) {
    for (const auto &entry : reply["result"].toObject()["attributes"].toArray())
        if (entry.toObject()["name"].toString() == name) return entry.toObject();
    return {};
}
}

class AttributesCmdTest : public QObject {
    Q_OBJECT
private slots:
    void allCommandsExposeReadAndMutation() {
        QTemporaryDir dir; fixture(dir.path()); Session s(dir.path(), nullptr);
        registerAllCommands(s);
        QVERIFY(s.registry().has("list_attributes"));
        QVERIFY(s.registry().has("edit_attribute"));
        for (const auto &spec : s.registry().list()) {
            if (spec.name == "list_attributes") QVERIFY(!spec.mutating);
            if (spec.name == "edit_attribute") QVERIFY(spec.mutating);
        }
    }
    void listHasEffectiveValuesSchemaAndSourceWithoutWriting() {
        QTemporaryDir dir; fixture(dir.path()); Session s(dir.path(), nullptr);
        registerAttributeCommands(s);
        const auto before = disk(dir.path());
        const auto reply = call(s, "list_attributes");
        QVERIFY2(reply["ok"].toBool(), qPrintable(reply["error"].toString()));
        const auto weight = attribute(reply, "weight");
        QCOMPARE(weight["value"].toDouble(), 73.25);
        QCOMPARE(weight["source_file"].toString(), QString("gameplay.json"));
        QCOMPARE(weight["type"].toString(), QString("number"));
        QVERIFY(!weight["description"].toString().isEmpty());
        QVERIFY(!weight["unit"].toString().isEmpty());
        QVERIFY(weight["range"].toObject()["minimum"].isNull()); // schema has no invented physical bounds
        QCOMPARE(attribute(reply, "walk_max_vel")["group"].toString(), QString("ground"));
        QCOMPARE(attribute(reply, "gravity")["value"].toDouble(), 0.125);
        QVERIFY(attribute(reply, "gravity")["source_file"].toString().endsWith("package/geno.json"));
        QCOMPARE(attribute(reply, "initial_shield_size")["group"].toString(), QString("shield_ecb"));
        const auto jumps = attribute(reply, "jumps.max");
        QCOMPARE(jumps["range"].toObject()["minimum"].toInt(), 1);
        QCOMPARE(jumps["range"].toObject()["maximum"].toInt(), 250);
        QCOMPARE(attribute(reply, "jumps.air_vy.1")["value"].toDouble(), 1.75);
        QCOMPARE(disk(dir.path()), before);
        QVERIFY(s.history().entries().isEmpty());
        QVERIFY(!QFileInfo::exists(dir.filePath(".workbench")));
    }
    void scalarEditPreservesBomCrLfOrderAndUnrelatedBytes() {
        QTemporaryDir dir; fixture(dir.path());
        auto before = disk(dir.path()); before.replace("\n", "\r\n"); before.prepend(QByteArray("\xEF\xBB\xBF"));
        wbtest::put(dir.path(), "gameplay.json", before);
        Session s(dir.path(), nullptr); registerAttributeCommands(s);
        const auto reply = call(s, "edit_attribute", {{"name", "weight"}, {"value", 81.5}});
        QVERIFY2(reply["ok"].toBool(), qPrintable(reply["error"].toString()));
        QVERIFY(reply["result"].toObject()["applied"].toBool());
        auto expected = before; expected.replace("73.25", "81.5");
        QCOMPARE(disk(dir.path()), expected);
        QCOMPARE(s.history().entries().size(), 1);
        QCOMPARE(s.history().entries().first().changes.first().before, before);
        QCOMPARE(s.history().entries().first().changes.first().after, expected);
        QCOMPARE(attribute(call(s, "list_attributes"), "weight")["value"].toDouble(), 81.5);
    }
    void missingBlockAndInheritedValuesBecomeSourceOverrides() {
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path());
        wbtest::put(dir.path(), "package/geno.json", R"JSON({"fighters":[{"define":{"key":"synth"},"attributes":{"gravity":0.125}}]})JSON");
        Session s(dir.path(), nullptr); registerAttributeCommands(s);
        const auto built = disk(dir.path(), "package/geno.json");
        auto reply = call(s, "edit_attribute", {{"name", "gravity"}, {"value", 0.2}});
        QVERIFY2(reply["ok"].toBool(), qPrintable(reply["error"].toString()));
        QCOMPARE(QJsonDocument::fromJson(disk(dir.path())).object()["attributes"].toObject()["gravity"].toDouble(), 0.2);
        QCOMPARE(disk(dir.path(), "package/geno.json"), built);
        QVERIFY(disk(dir.path()).indexOf("\"version\"") < disk(dir.path()).indexOf("\"attributes\""));
        QCOMPARE(attribute(call(s, "list_attributes"), "gravity")["source_file"].toString(), QString("gameplay.json"));
    }
    void absentImpulseOffersAnExplicitAppendSlotWithoutInventingDefaults() {
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path());
        Session s(dir.path(), nullptr); registerAttributeCommands(s);
        auto listed = call(s, "list_attributes");
        const auto first = attribute(listed, "jumps.air_vy.0");
        QVERIFY(!first.isEmpty()); QVERIFY(first["value"].isNull());
        QVERIFY(first["source_file"].toString().isEmpty());
        QVERIFY(call(s, "edit_attribute", {{"name", "jumps.air_vy.0"}, {"value", 2.5}})["ok"].toBool());
        listed = call(s, "list_attributes");
        QCOMPARE(attribute(listed, "jumps.air_vy.0")["value"].toDouble(), 2.5);
        QVERIFY(attribute(listed, "jumps.air_vy.1")["value"].isNull());
        QVERIFY(call(s, "edit_attribute", {{"name", "jumps.air_vy.1"}, {"value", 1.75}})["ok"].toBool());
        QCOMPARE(QJsonDocument::fromJson(disk(dir.path())).object()["jumps"].toObject()["air_vy"].toArray(), QJsonArray({2.5, 1.75}));
    }
    void explicitShortArrayDoesNotInheritAnOmittedTail() {
        QTemporaryDir dir; fixture(dir.path());
        wbtest::put(dir.path(), "package/geno.json", R"JSON({"fighters":[{"define":{"key":"synth"},"jumps":{"air_vy":[4,3,2]}}]})JSON");
        Session s(dir.path(), nullptr); registerAttributeCommands(s);
        const auto appended = attribute(call(s, "list_attributes"), "jumps.air_vy.2");
        QVERIFY(!appended.isEmpty()); QVERIFY(appended["value"].isNull());
        QVERIFY(appended["source_file"].toString().isEmpty());
    }
    void inheritedAuthoredImpulseArrayIsPreservedWhenEditingItsTail() {
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path());
        wbtest::put(dir.path(), "package/geno.json", R"JSON({"fighters":[{"define":{"key":"synth"},"jumps":{"max":3,"air_vy":[2.5,1.75]}}]})JSON");
        Session s(dir.path(), nullptr); registerAttributeCommands(s);
        const auto built = disk(dir.path(), "package/geno.json");
        QCOMPARE(attribute(call(s, "list_attributes"), "jumps.air_vy.1")["value"].toDouble(), 1.75);
        const auto reply = call(s, "edit_attribute", {{"name", "jumps.air_vy.1"}, {"value", 3.25}});
        QVERIFY2(reply["ok"].toBool(), qPrintable(reply["error"].toString()));
        const auto impulses = QJsonDocument::fromJson(disk(dir.path())).object()["jumps"].toObject()["air_vy"].toArray();
        QCOMPARE(impulses, QJsonArray({2.5, 3.25}));
        QCOMPARE(disk(dir.path(), "package/geno.json"), built);
        auto listed = call(s, "list_attributes");
        QCOMPARE(attribute(listed, "jumps.air_vy.0")["value"].toDouble(), 2.5);
        QCOMPARE(attribute(listed, "jumps.air_vy.1")["source_file"].toString(), QString("gameplay.json"));
        QVERIFY(call(s, "edit_attribute", {{"name", "jumps.air_vy.0"}, {"value", 4.25}})["ok"].toBool());
        QCOMPARE(attribute(call(s, "list_attributes"), "jumps.air_vy.1")["value"].toDouble(), 3.25);
    }
    void fullSourceImpulseArraySeedsMissingPrimaryWithoutDroppingTail() {
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path());
        auto full = QByteArray(wbtest::kGameplay);
        full.replace("\"version\": 1", "\"version\": 1,\n  \"jumps\": {\"max\": 3, \"air_vy\": [2.5, 1.75]}");
        wbtest::put(dir.path(), "gameplay.full.json", full);
        Session s(dir.path(), nullptr); registerAttributeCommands(s);
        const auto reply = call(s, "edit_attribute", {{"name", "jumps.air_vy.0"}, {"value", 4.25}});
        QVERIFY2(reply["ok"].toBool(), qPrintable(reply["error"].toString()));
        for (const auto &path : {QString("gameplay.json"), QString("gameplay.full.json")})
            QCOMPARE(QJsonDocument::fromJson(disk(dir.path(), path)).object()["jumps"].toObject()["air_vy"].toArray(), QJsonArray({4.25, 1.75}));
        QCOMPARE(s.history().entries().first().changes.size(), 2);
    }
    void shorterPrimaryCanAppendFromTheAuthoritativeExplicitPrefix_data() {
        QTest::addColumn<QByteArray>("primaryImpulses");
        QTest::addColumn<int>("index");
        QTest::addColumn<QJsonArray>("expected");
        QTest::newRow("shorter-primary") << QByteArray("[2.5]") << 2 << QJsonArray({2.5, 1.75, 3.25});
        QTest::newRow("empty-primary") << QByteArray("[]") << 1 << QJsonArray({2.5, 3.25});
    }
    void shorterPrimaryCanAppendFromTheAuthoritativeExplicitPrefix() {
        QFETCH(QByteArray, primaryImpulses); QFETCH(int, index); QFETCH(QJsonArray, expected);
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path());
        auto primary = QByteArray(wbtest::kGameplay);
        primary.replace("\"version\": 1", QByteArray("\"version\": 1,\n  \"jumps\": {\"air_vy\": ") + primaryImpulses + "}");
        auto full = QByteArray(wbtest::kGameplay);
        full.replace("\"version\": 1", "\"version\": 1,\n  \"jumps\": {\"air_vy\": [2.5, 1.75]}");
        wbtest::put(dir.path(), "gameplay.json", primary); wbtest::put(dir.path(), "gameplay.full.json", full);
        Session s(dir.path(), nullptr); registerAttributeCommands(s);
        const auto name = "jumps.air_vy." + QString::number(index);
        const auto reply = call(s, "edit_attribute", {{"name", name}, {"value", 3.25}});
        QVERIFY2(reply["ok"].toBool(), qPrintable(reply["error"].toString()));
        for (const auto &path : {QString("gameplay.json"), QString("gameplay.full.json")})
            QCOMPARE(QJsonDocument::fromJson(disk(dir.path(), path)).object()["jumps"].toObject()["air_vy"].toArray(), expected);
        QCOMPARE(s.history().entries().first().changes.size(), 2);
    }
    void inheritedImpulseArrayMustValidateBeforeItIsAuthored_data() {
        QTest::addColumn<QByteArray>("impulses");
        QTest::newRow("bad-value") << QByteArray("[2.5,\"bad\"]");
        QTest::newRow("too-many") << QByteArray("[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17]");
    }
    void inheritedImpulseArrayMustValidateBeforeItIsAuthored() {
        QFETCH(QByteArray, impulses); QTemporaryDir dir; wbtest::makeSynthFighter(dir.path());
        wbtest::put(dir.path(), "package/geno.json", QByteArray("{\"fighters\":[{\"define\":{\"key\":\"synth\"},\"jumps\":{\"air_vy\":") + impulses + "}}]}");
        Session s(dir.path(), nullptr); registerAttributeCommands(s); const auto before = disk(dir.path());
        QVERIFY(!call(s, "edit_attribute", {{"name", "jumps.air_vy.0"}, {"value", 4.25}})["ok"].toBool());
        QCOMPARE(disk(dir.path()), before); QVERIFY(s.history().entries().isEmpty());
    }
    void schemaTypeRangeAndNameValidation_data() {
        QTest::addColumn<QJsonObject>("args");
        QTest::newRow("unknown") << QJsonObject{{"name", "not_an_attribute"}, {"value", 2}};
        QTest::newRow("string") << QJsonObject{{"name", "weight"}, {"value", "80"}};
        QTest::newRow("bool") << QJsonObject{{"name", "weight"}, {"value", true}};
        QTest::newRow("null") << QJsonObject{{"name", "weight"}, {"value", QJsonValue(QJsonValue::Null)}};
        QTest::newRow("fractional-int") << QJsonObject{{"name", "rapid_jab_window"}, {"value", 4.5}};
        QTest::newRow("jumps-below") << QJsonObject{{"name", "jumps.max"}, {"value", 0}};
        QTest::newRow("jumps-above") << QJsonObject{{"name", "jumps.max"}, {"value", 251}};
        QTest::newRow("jump-index") << QJsonObject{{"name", "jumps.air_vy.16"}, {"value", 2}};
        QTest::newRow("jump-gap") << QJsonObject{{"name", "jumps.air_vy.3"}, {"value", 2}};
        QTest::newRow("missing-value") << QJsonObject{{"name", "weight"}};
        QTest::newRow("missing-name") << QJsonObject{{"value", 80}};
    }
    void schemaTypeRangeAndNameValidation() {
        QFETCH(QJsonObject, args);
        QTemporaryDir dir; fixture(dir.path()); Session s(dir.path(), nullptr);
        registerAttributeCommands(s); const auto before = disk(dir.path());
        const auto reply = call(s, "edit_attribute", args);
        QVERIFY(!reply["ok"].toBool()); QVERIFY(!reply["error"].toString().isEmpty());
        QCOMPARE(disk(dir.path()), before); QVERIFY(s.history().entries().isEmpty());
    }
    void jumpBoundariesAndNegativeUnboundedValuesAreAccepted() {
        QTemporaryDir dir; fixture(dir.path()); Session s(dir.path(), nullptr); registerAttributeCommands(s);
        QVERIFY(call(s, "edit_attribute", {{"name", "jumps.max"}, {"value", 1}})["ok"].toBool());
        QVERIFY(call(s, "edit_attribute", {{"name", "jumps.max"}, {"value", 250}})["ok"].toBool());
        QVERIFY(call(s, "edit_attribute", {{"name", "jumps.air_vy.0"}, {"value", -1.5}})["ok"].toBool());
        QCOMPARE(attribute(call(s, "list_attributes"), "jumps.air_vy.0")["value"].toDouble(), -1.5);
    }
    void agentAndExplicitProposalsLeaveSourceAlone_data() {
        QTest::addColumn<QString>("author"); QTest::addColumn<bool>("propose");
        QTest::newRow("agent-policy") << QString("agent") << false;
        QTest::newRow("human-explicit") << QString("human") << true;
    }
    void agentAndExplicitProposalsLeaveSourceAlone() {
        QFETCH(QString, author); QFETCH(bool, propose);
        QTemporaryDir dir; fixture(dir.path()); Session s(dir.path(), nullptr);
        s.agentProposals = true; registerAttributeCommands(s); registerSaveCommands(s);
        const auto before = disk(dir.path());
        const auto reply = call(s, "edit_attribute", {{"name", "weight"}, {"value", 81.5}, {"propose", propose}}, author);
        QVERIFY2(reply["ok"].toBool(), qPrintable(reply["error"].toString()));
        QVERIFY(reply["result"].toObject()["proposed"].toBool()); QCOMPARE(disk(dir.path()), before);
        QCOMPARE(s.history().entries().first().state, QString("proposed"));
        QVERIFY(call(s, "accept", {{"id", reply["result"].toObject()["entry"]}})["ok"].toBool());
        QVERIFY(disk(dir.path()) != before);
    }
    void editsUndoRedoAndNoopPreservesFormatting() {
        QTemporaryDir dir; fixture(dir.path()); Session s(dir.path(), nullptr);
        registerAttributeCommands(s); registerSaveCommands(s);
        const auto before = disk(dir.path());
        QVERIFY(call(s, "edit_attribute", {{"name", "weight"}, {"value", 73.25}})["ok"].toBool());
        QVERIFY(s.history().entries().isEmpty());
        QVERIFY(call(s, "edit_attribute", {{"name", "weight"}, {"value", 81.5}})["ok"].toBool());
        const auto after = disk(dir.path());
        QVERIFY(call(s, "undo")["ok"].toBool()); QCOMPARE(disk(dir.path()), before);
        QVERIFY(call(s, "redo")["ok"].toBool()); QCOMPARE(disk(dir.path()), after);
    }
    void localFullSourceWinsAndBothFilesArePatched() {
        QTemporaryDir dir; fixture(dir.path());
        auto full = disk(dir.path()); full.replace("73.25", "74.25");
        wbtest::put(dir.path(), "gameplay.full.json", full);
        Session s(dir.path(), nullptr); registerAttributeCommands(s);
        auto listed = attribute(call(s, "list_attributes"), "weight");
        QCOMPARE(listed["value"].toDouble(), 74.25);
        QCOMPARE(listed["source_file"].toString(), QString("gameplay.full.json"));
        const auto reply = call(s, "edit_attribute", {{"name", "weight"}, {"value", 81.5}});
        QVERIFY2(reply["ok"].toBool(), qPrintable(reply["error"].toString()));
        auto expected = full; expected.replace("74.25", "81.5");
        QCOMPARE(disk(dir.path(), "gameplay.full.json"), expected);
        QCOMPARE(s.history().entries().first().changes.size(), 2);
        QCOMPARE(attribute(call(s, "list_attributes"), "weight")["value"].toDouble(), 81.5);
    }
    void externalChangesStayConflictsEvenAfterListing_data() {
        QTest::addColumn<QString>("path"); QTest::addColumn<bool>("create");
        QTest::newRow("gameplay") << QString("gameplay.json") << false;
        QTest::newRow("project") << QString("workbench.json") << false;
        QTest::newRow("full-created") << QString("gameplay.full.json") << true;
        QTest::newRow("full-edited") << QString("gameplay.full.json") << false;
    }
    void externalChangesStayConflictsEvenAfterListing() {
        QFETCH(QString, path); QFETCH(bool, create);
        QTemporaryDir dir; fixture(dir.path());
        if (path.endsWith("full.json") && !create) wbtest::put(dir.path(), path, disk(dir.path()));
        Session s(dir.path(), nullptr); registerAttributeCommands(s);
        QVERIFY(call(s, "list_attributes")["ok"].toBool());
        const auto external = create ? disk(dir.path()) : disk(dir.path(), path) + " ";
        wbtest::put(dir.path(), path, external);
        QVERIFY(call(s, "list_attributes")["ok"].toBool());
        for (const QString &author : {QString("human"), QString("agent")}) {
            const auto reply = call(s, "edit_attribute", {{"name", "weight"}, {"value", 81.5}}, author);
            QVERIFY(!reply["ok"].toBool()); QVERIFY(reply["error"].toString().contains("changed externally"));
        }
        QCOMPARE(disk(dir.path(), path), external); QVERIFY(s.history().entries().isEmpty());
    }
    void invalidOrAmbiguousJsonNeverGetsOverwritten_data() {
        QTest::addColumn<QByteArray>("bytes");
        QTest::newRow("object-type") << QByteArray("{\"attributes\":[]}");
        QTest::newRow("broken") << QByteArray("{broken");
        QTest::newRow("duplicate") << QByteArray("{\"attributes\":{\"weight\":4,\"weight\":5}}");
        QTest::newRow("duplicate-block") << QByteArray("{\"attributes\":{\"weight\":4},\"attributes\":{\"weight\":5}}");
        QTest::newRow("escaped-duplicate") << QByteArray("{\"attributes\":{\"weight\":4,\"\\u0077eight\":5}}");
        QTest::newRow("duplicate-jump") << QByteArray("{\"jumps\":{\"max\":2,\"max\":3}}");
        QTest::newRow("duplicate-unrelated-nested") << QByteArray("{\"moves\":[{\"pick\":{\"clip\":\"a\",\"clip\":\"b\"}}]}");
        QTest::newRow("bad-utf8") << (QByteArray("{}") + QByteArray(1, char(0xff)));
    }
    void invalidOrAmbiguousJsonNeverGetsOverwritten() {
        QFETCH(QByteArray, bytes); QTemporaryDir dir; fixture(dir.path());
        wbtest::put(dir.path(), "gameplay.json", bytes);
        Session s(dir.path(), nullptr); registerAttributeCommands(s);
        QVERIFY(!call(s, "list_attributes")["ok"].toBool());
        QVERIFY(!call(s, "edit_attribute", {{"name", "gravity"}, {"value", 0.2}})["ok"].toBool());
        QCOMPARE(disk(dir.path()), bytes); QVERIFY(s.history().entries().isEmpty());
    }
    void directGenoSourceSelectsFighterByProjectKey() {
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path());
        wbtest::put(dir.path(), "gameplay.json", R"JSON({"geno":11,"fighters":[{"define":{"key":"other"},"attributes":{"weight":40}},{"define":{"key":"synth"},"attributes":{"weight":70}}]})JSON");
        Session s(dir.path(), nullptr); registerAttributeCommands(s);
        registerSaveCommands(s);
        QVERIFY(s.data().reload().isEmpty());
        QVERIFY(s.data().rows().isEmpty());
        const auto before = disk(dir.path());
        const auto reply = call(s, "edit_attribute", {{"name", "weight"}, {"value", 81.5}});
        QVERIFY2(reply["ok"].toBool(), qPrintable(reply["error"].toString()));
        const auto fighters = QJsonDocument::fromJson(disk(dir.path())).object()["fighters"].toArray();
        QCOMPARE(fighters[0].toObject()["attributes"].toObject()["weight"].toInt(), 40);
        QCOMPARE(fighters[1].toObject()["attributes"].toObject()["weight"].toDouble(), 81.5);
        QVERIFY(call(s, "undo")["ok"].toBool()); QCOMPARE(disk(dir.path()), before);
        QVERIFY(call(s, "redo")["ok"].toBool());
        s.agentProposals = true;
        const auto proposal = call(s, "edit_attribute", {{"name", "weight"}, {"value", 84.5}}, "agent");
        QVERIFY(proposal["result"].toObject()["proposed"].toBool());
        QVERIFY(call(s, "accept", {{"id", proposal["result"].toObject()["entry"]}})["ok"].toBool());
    }
};
QTEST_GUILESS_MAIN(AttributesCmdTest)
#include "commands_attributes_test.moc"
