#include "../testfixture.h"
#include "commands.h"
#include <QTemporaryDir>
#include <QtTest>
using namespace wb;

namespace {
const QString groundFile = QStringLiteral("ground_modes.json");
const char *emptyGround = "{\n  \"schema\": \"ground-modes/1\",\n  \"rows\": {},\n  \"grounded_clips\": []\n}\n";

QByteArray diskBytes(const QString &dir, const QString &rel = groundFile) {
    QFile file(QDir(dir).filePath(rel));
    if (!file.open(QIODevice::ReadOnly)) return {};
    return file.readAll();
}
QJsonObject call(Session &session, const QString &name, const QJsonObject &args = {},
                 const QString &author = "human") {
    CommandContext ctx{session, author};
    return session.registry().call(name, args, ctx);
}
QJsonObject rowsOnDisk(const QString &dir) {
    return QJsonDocument::fromJson(diskBytes(dir)).object()["rows"].toObject();
}
} // namespace

class GroundCmdTest : public QObject {
    Q_OBJECT
private slots:
    void registeredByAllCommands() {
        QTemporaryDir dir;
        QVERIFY(dir.isValid());
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        registerAllCommands(session);
        QVERIFY(session.registry().has("set_ground_mode"));
        QVERIFY(session.registry().has("get_ground_modes"));
        for (const auto &spec : session.registry().list()) {
            if (spec.name == "set_ground_mode") QVERIFY(spec.mutating);
            if (spec.name == "get_ground_modes") QVERIFY(!spec.mutating);
        }
    }

    void absentGetReturnsEmptyWithoutWriting() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        registerGroundCommands(session);
        const auto reply = call(session, "get_ground_modes");
        QVERIFY2(reply["ok"].toBool(), qPrintable(reply["error"].toString()));
        QCOMPARE(reply["result"].toObject(), (QJsonObject{{"rows", QJsonObject{}}}));
        QVERIFY(!QFileInfo::exists(dir.filePath(groundFile)));
        QVERIFY(!QFileInfo::exists(dir.filePath(".workbench")));
        QVERIFY(session.history().entries().isEmpty());
    }

    void freshSetCreatesOneSourceChangeAndCanBeUpdated() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        registerGroundCommands(session);
        auto reply = call(session, "set_ground_mode",
            {{"row", "Jab1"}, {"mode", "hover"}, {"blend_in", true}, {"blend_out", false}});
        QVERIFY2(reply["ok"].toBool(), qPrintable(reply["error"].toString()));
        QVERIFY(reply["result"].toObject()["applied"].toBool());
        QJsonParseError parseError;
        const QByteArray first = diskBytes(dir.path());
        const auto document = QJsonDocument::fromJson(first, &parseError);
        QCOMPARE(parseError.error, QJsonParseError::NoError);
        QCOMPARE(document.object()["schema"].toString(), QString("ground-modes/1"));
        QCOMPARE(document.object()["grounded_clips"].toArray(), QJsonArray{});
        const QJsonObject entry{{"mode", "hover"}, {"blend_in", true}, {"blend_out", false}};
        QCOMPARE(document.object()["rows"].toObject(), (QJsonObject{{"Jab1", entry}}));
        QCOMPARE(session.history().entries().size(), 1);
        const auto changes = session.history().entries().first().changes;
        QCOMPARE(changes.size(), 1);
        QCOMPARE(changes.first().path, groundFile);
        QVERIFY(changes.first().before.isEmpty());
        QCOMPARE(changes.first().after, first);
        const auto summary = reply["result"].toObject()["changes"].toArray();
        QCOMPARE(summary.size(), 1);
        QCOMPARE(summary.first().toObject()["bytes_before"].toInteger(), qint64(0));

        reply = call(session, "set_ground_mode", {{"row", "Jab1"}, {"mode", "anchored"}});
        QVERIFY2(reply["ok"].toBool(), qPrintable(reply["error"].toString()));
        QByteArray expected = first;
        expected.replace("\"mode\":\"hover\"", "\"mode\":\"anchored\"");
        QCOMPARE(diskBytes(dir.path()), expected);
        QCOMPARE(diskBytes(dir.path()).count("\"Jab1\""), 1);
        QCOMPARE(rowsOnDisk(dir.path())["Jab1"].toObject()["blend_in"], QJsonValue(true));
        QCOMPARE(rowsOnDisk(dir.path())["Jab1"].toObject()["blend_out"], QJsonValue(false));
        QCOMPARE(session.history().entries().size(), 2);
    }

    void acceptsExistingRowNames_data() {
        QTest::addColumn<QString>("row");
        QTest::newRow("fidelity-jab") << QString("Jab1");
        QTest::newRow("fidelity-aerial") << QString("AirDown");
        QTest::newRow("gameplay-jab") << QString("jab1");
        QTest::newRow("gameplay-aerial") << QString("dair");
    }
    void acceptsExistingRowNames() {
        QFETCH(QString, row);
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        // Ground row validation requires source data, not a built plan.
        QVERIFY(QFile::remove(dir.filePath("package/files/plan.json")));
        Session session(dir.path(), nullptr);
        registerGroundCommands(session);
        const auto reply = call(session, "set_ground_mode", {{"row", row}, {"mode", "none"}});
        QVERIFY2(reply["ok"].toBool(), qPrintable(reply["error"].toString()));
        QCOMPARE(rowsOnDisk(dir.path())[row].toObject(), (QJsonObject{{"mode", "none"}}));
    }

    void usesTheConfiguredFidelitySource() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        wbtest::put(dir.path(), "ledger/custom.json", wbtest::kFidelity);
        QVERIFY(QFile::remove(dir.filePath("fidelity.json")));
        auto project = QJsonDocument::fromJson(wbtest::kProject).object();
        project["fidelity"] = "ledger/custom.json";
        wbtest::put(dir.path(), "workbench.json", QJsonDocument(project).toJson());
        Session session(dir.path(), nullptr);
        registerGroundCommands(session);
        const auto reply = call(session, "set_ground_mode", {{"row", "AirDown"}, {"mode", "hover"}});
        QVERIFY2(reply["ok"].toBool(), qPrintable(reply["error"].toString()));
        QCOMPARE(rowsOnDisk(dir.path())["AirDown"].toObject()["mode"].toString(), QString("hover"));
        QCOMPARE(diskBytes(dir.path(), "ledger/custom.json"), QByteArray(wbtest::kFidelity));
    }

    void gameplayNamesWorkWithoutAFidelityLedger() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        QVERIFY(QFile::remove(dir.filePath("fidelity.json")));
        QVERIFY(QFile::remove(dir.filePath("package/files/plan.json")));
        Session session(dir.path(), nullptr);
        registerGroundCommands(session);
        QVERIFY(call(session, "set_ground_mode", {{"row", "dair"}, {"mode", "none"}})["ok"].toBool());
        const auto reply = call(session, "set_ground_mode", {{"row", "AirDown"}, {"mode", "hover"}});
        QVERIFY(!reply["ok"].toBool());
        QVERIFY(reply["error"].toString().contains("unknown row"));
        QCOMPARE(rowsOnDisk(dir.path()).size(), 1);
    }

    void updatesPreserveUnrelatedBytesAndOmittedOptions() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        QByteArray before = R"JSON({
  "schema" : "ground-modes/1",
  "label" : "\u0078",
  "rows" : {
    "AirDown" : {"mode":"none","blend_out":true},
    "Jab1" : {
      "note" : "keep this field",
      "mode" : "hover",
      "blend_in" : true,
      "blend_out" : true
    }
  },
  "grounded_clips" : ["SYN_ATC_007"],
  "untouched" : 1e2
}
)JSON";
        before.replace("\n", "\r\n");
        before.prepend(QByteArray("\xEF\xBB\xBF"));
        wbtest::put(dir.path(), groundFile, before);
        Session session(dir.path(), nullptr);
        registerGroundCommands(session);
        auto reply = call(session, "set_ground_mode",
            {{"row", "Jab1"}, {"mode", "anchored"}, {"blend_out", false}});
        QVERIFY2(reply["ok"].toBool(), qPrintable(reply["error"].toString()));
        QByteArray expected = before;
        expected.replace("\"mode\" : \"hover\"", "\"mode\" : \"anchored\"");
        expected.replace("\"blend_out\" : true", "\"blend_out\" : false");
        QCOMPARE(diskBytes(dir.path()), expected);
        reply = call(session, "set_ground_mode", {{"row", "Jab1"}, {"mode", "none"}});
        QVERIFY2(reply["ok"].toBool(), qPrintable(reply["error"].toString()));
        expected.replace("\"mode\" : \"anchored\"", "\"mode\" : \"none\"");
        QCOMPARE(diskBytes(dir.path()), expected);
        QCOMPARE(diskBytes(dir.path()).count("\"Jab1\""), 1);
    }

    void insertsRowsAndOptionalFieldsWithoutReformatting() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        const QByteArray before =
            "{\r\n \"schema\" : \"ground-modes/1\",\r\n"
            " \"rows\" : {\"AirDown\" : { \"mode\" : \"none\" }},\r\n"
            " \"grounded_clips\" : [ \"SYN_ATC_007\" ], \"keep\" : 3.0\r\n}\r\n";
        wbtest::put(dir.path(), groundFile, before);
        Session session(dir.path(), nullptr);
        registerGroundCommands(session);
        auto reply = call(session, "set_ground_mode", {{"row", "Jab1"}, {"mode", "hover"}});
        QVERIFY2(reply["ok"].toBool(), qPrintable(reply["error"].toString()));
        QByteArray expected = before;
        expected.replace("{ \"mode\" : \"none\" }",
            "{ \"mode\" : \"none\" }, \"Jab1\": {\"mode\":\"hover\"}");
        QCOMPARE(diskBytes(dir.path()), expected);
        reply = call(session, "set_ground_mode",
            {{"row", "Jab1"}, {"mode", "hover"}, {"blend_in", false}});
        QVERIFY2(reply["ok"].toBool(), qPrintable(reply["error"].toString()));
        expected.replace("{\"mode\":\"hover\"}", "{\"mode\":\"hover\", \"blend_in\": false}");
        QCOMPARE(diskBytes(dir.path()), expected);
    }

    void getReturnsOnlyStoredRowsWithoutWriting() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        const QByteArray before =
            "{\"schema\":\"ground-modes/1\",\"rows\":{\"Jab1\":{\"mode\":\"anchored\","
            "\"blend_in\":false}},\"grounded_clips\":[\"SYN_ATC_007\"],\"extra\":9}\n";
        wbtest::put(dir.path(), groundFile, before);
        Session session(dir.path(), nullptr);
        registerGroundCommands(session);
        const auto reply = call(session, "get_ground_modes");
        QVERIFY2(reply["ok"].toBool(), qPrintable(reply["error"].toString()));
        QCOMPARE(reply["result"].toObject(), (QJsonObject{{"rows", rowsOnDisk(dir.path())}}));
        QCOMPARE(diskBytes(dir.path()), before);
        QVERIFY(session.history().entries().isEmpty());
        QVERIFY(!QFileInfo::exists(dir.filePath(".workbench")));
    }

    void unknownRowRejected() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        registerGroundCommands(session);
        const auto reply = call(session, "set_ground_mode", {{"row", "not_a_row"}, {"mode", "hover"}});
        QVERIFY(!reply["ok"].toBool());
        QVERIFY(reply["error"].toString().contains("unknown row"));
        QVERIFY(!QFileInfo::exists(dir.filePath(groundFile)));
        QVERIFY(session.history().entries().isEmpty());
    }

    void badArgumentsRejectedBySchema_data() {
        QTest::addColumn<QJsonObject>("args");
        QTest::addColumn<QString>("error");
        QTest::newRow("old-blend-mode") << QJsonObject{{"row", "Jab1"}, {"mode", "blend"}}
            << QString("mode: not one of the allowed values");
        QTest::newRow("unknown-mode") << QJsonObject{{"row", "Jab1"}, {"mode", "float"}}
            << QString("mode: not one of the allowed values");
        QTest::newRow("mode-type") << QJsonObject{{"row", "Jab1"}, {"mode", true}}
            << QString("mode: expected string");
        QTest::newRow("integer-blend-in") << QJsonObject{{"row", "Jab1"}, {"mode", "hover"}, {"blend_in", 0}}
            << QString("blend_in: expected boolean");
        QTest::newRow("integer-blend-out") << QJsonObject{{"row", "Jab1"}, {"mode", "hover"}, {"blend_out", 3}}
            << QString("blend_out: expected boolean");
        QTest::newRow("missing-mode") << QJsonObject{{"row", "Jab1"}} << QString("missing required: mode");
        QTest::newRow("missing-row") << QJsonObject{{"mode", "hover"}} << QString("missing required: row");
    }
    void badArgumentsRejectedBySchema() {
        QFETCH(QJsonObject, args);
        QFETCH(QString, error);
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        registerGroundCommands(session);
        const auto reply = call(session, "set_ground_mode", args);
        QVERIFY(!reply["ok"].toBool());
        QCOMPARE(reply["error"].toString(), error);
        QVERIFY(!QFileInfo::exists(dir.filePath(groundFile)));
        QVERIFY(session.history().entries().isEmpty());
    }

    void agentProposalDoesNotWrite_data() {
        QTest::addColumn<bool>("exists");
        QTest::newRow("new-file") << false;
        QTest::newRow("existing-file") << true;
    }
    void agentProposalDoesNotWrite() {
        QFETCH(bool, exists);
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        const QByteArray before = exists ? QByteArray(emptyGround) : QByteArray();
        if (exists) wbtest::put(dir.path(), groundFile, before);
        Session session(dir.path(), nullptr);
        session.agentProposals = true; // The same policy the MCP server enables.
        registerGroundCommands(session);
        const auto reply = call(session, "set_ground_mode",
            {{"row", "Jab1"}, {"mode", "hover"}, {"blend_in", true}}, "agent");
        QVERIFY2(reply["ok"].toBool(), qPrintable(reply["error"].toString()));
        QVERIFY(reply["result"].toObject()["proposed"].toBool());
        QVERIFY(!reply["result"].toObject()["applied"].toBool());
        QCOMPARE(QFileInfo::exists(dir.filePath(groundFile)), exists);
        QCOMPARE(diskBytes(dir.path()), before);
        QCOMPARE(session.history().entries().size(), 1);
        const auto entry = session.history().entries().first();
        QCOMPARE(entry.author, QString("agent"));
        QCOMPARE(entry.state, QString("proposed"));
        QCOMPARE(entry.changes.size(), 1);
        QCOMPARE(entry.changes.first().before, before);
        QCOMPARE(QJsonDocument::fromJson(entry.changes.first().after).object()["rows"].toObject()
                     ["Jab1"].toObject()["mode"].toString(), QString("hover"));
        QCOMPARE(History::load(session.historyPath()).entries().first().state, QString("proposed"));
        QCOMPARE(call(session, "get_ground_modes")["result"].toObject()["rows"].toObject(), QJsonObject{});
    }

    void externalChangesRemainConflicts_data() {
        QTest::addColumn<int>("kind");
        QTest::newRow("edit-before-first-command") << 0;
        QTest::newRow("edit-after-read") << 1;
        QTest::newRow("file-created-externally") << 2;
        QTest::newRow("file-deleted-externally") << 3;
    }
    void externalChangesRemainConflicts() {
        QFETCH(int, kind);
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        if (kind != 2) wbtest::put(dir.path(), groundFile, emptyGround);
        Session session(dir.path(), nullptr);
        registerGroundCommands(session);
        if (kind == 1) QVERIFY(call(session, "get_ground_modes")["ok"].toBool());
        const QByteArray external =
            "{\"schema\":\"ground-modes/1\",\"rows\":{\"Jab1\":{\"mode\":\"none\"}},\"grounded_clips\":[]}\n";
        if (kind == 3) QVERIFY(QFile::remove(dir.filePath(groundFile)));
        else wbtest::put(dir.path(), groundFile, external);
        auto reply = call(session, "set_ground_mode", {{"row", "Jab1"}, {"mode", "hover"}});
        QVERIFY(!reply["ok"].toBool());
        QVERIFY(reply["error"].toString().contains("changed externally"));
        // Reads show current disk contents without acknowledging the hand edit.
        reply = call(session, "get_ground_modes");
        QVERIFY2(reply["ok"].toBool(), qPrintable(reply["error"].toString()));
        const auto expectedRows = kind == 3 ? QJsonObject{}
            : QJsonDocument::fromJson(external).object()["rows"].toObject();
        QCOMPARE(reply["result"].toObject(), (QJsonObject{{"rows", expectedRows}}));
        QVERIFY(session.files().externalChanges().contains(groundFile));
        reply = call(session, "set_ground_mode", {{"row", "Jab1"}, {"mode", "anchored"}});
        QVERIFY(!reply["ok"].toBool());
        QVERIFY(reply["error"].toString().contains("changed externally"));
        QCOMPARE(QFileInfo::exists(dir.filePath(groundFile)), kind != 3);
        QCOMPARE(diskBytes(dir.path()), kind == 3 ? QByteArray() : external);
        QVERIFY(session.files().externalChanges().contains(groundFile));
        QVERIFY(session.history().entries().isEmpty());
    }

    void externalEditAfterAppliedSetIsRefused() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        registerGroundCommands(session);
        QVERIFY(call(session, "set_ground_mode", {{"row", "Jab1"}, {"mode", "hover"}})["ok"].toBool());
        const QByteArray external = QByteArray(emptyGround) + " ";
        wbtest::put(dir.path(), groundFile, external);
        const auto reply = call(session, "set_ground_mode", {{"row", "Jab1"}, {"mode", "anchored"}});
        QVERIFY(!reply["ok"].toBool());
        QVERIFY(reply["error"].toString().contains("changed externally"));
        QCOMPARE(diskBytes(dir.path()), external);
        QCOMPARE(session.history().entries().size(), 1);
    }

    void invalidGroundFileIsNeverOverwritten_data() {
        QTest::addColumn<QByteArray>("bytes");
        QTest::newRow("empty-existing-file") << QByteArray("");
        QTest::newRow("bad-json") << QByteArray("{bad json");
        QTest::newRow("array-root") << QByteArray("[]");
        QTest::newRow("wrong-schema") << QByteArray("{\"schema\":\"other/1\",\"rows\":{}}");
        QTest::newRow("bad-rows-type") << QByteArray("{\"schema\":\"ground-modes/1\",\"rows\":[]}");
        QTest::newRow("invalid-utf8") << (QByteArray(emptyGround) + QByteArray(1, char(0xff)));
        QTest::newRow("ambiguous-rows") << QByteArray(
            "{\"schema\":\"ground-modes/1\",\"rows\":{},\"rows\":{}}");
    }
    void invalidGroundFileIsNeverOverwritten() {
        QFETCH(QByteArray, bytes);
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        wbtest::put(dir.path(), groundFile, bytes);
        Session session(dir.path(), nullptr);
        registerGroundCommands(session);
        const auto reply = call(session, "set_ground_mode", {{"row", "Jab1"}, {"mode", "hover"}});
        QVERIFY(!reply["ok"].toBool());
        QVERIFY(reply["error"].toString().contains(groundFile));
        QCOMPARE(diskBytes(dir.path()), bytes);
        QVERIFY(session.history().entries().isEmpty());
    }

    void identicalSetDoesNotAddHistory() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        registerGroundCommands(session);
        const QJsonObject args{{"row", "Jab1"}, {"mode", "none"}, {"blend_out", false}};
        QVERIFY(call(session, "set_ground_mode", args)["ok"].toBool());
        const QByteArray before = diskBytes(dir.path());
        const auto reply = call(session, "set_ground_mode", args);
        QVERIFY2(reply["ok"].toBool(), qPrintable(reply["error"].toString()));
        QVERIFY(!reply["result"].toObject()["applied"].toBool());
        QCOMPARE(diskBytes(dir.path()), before);
        QCOMPARE(session.history().entries().size(), 1);
    }
};
QTEST_GUILESS_MAIN(GroundCmdTest)
#include "commands_ground_test.moc"
