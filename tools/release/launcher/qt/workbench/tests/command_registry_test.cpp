#include "../testfixture.h"
#include "command_registry.h"
#include "session.h"
#include <QDirIterator>
#include <QTemporaryDir>
#include <QtTest>
#include <stdexcept>

using namespace wb;

static CommandSpec echo() {
    CommandSpec spec;
    spec.name = "echo";
    spec.description = "echo";
    spec.inputSchema = QJsonDocument::fromJson(R"JSON({"type":"object","required":["n"],"properties":{"n":{"type":"integer"},"mode":{"type":"string","enum":["a","b"]}}})JSON").object();
    spec.run = [](const QJsonObject &args, CommandContext &) { return QJsonObject{{"n", args["n"]}}; };
    return spec;
}

static QByteArray diskBytes(const QString &path) {
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly)) qFatal("cannot read test file: %s", qPrintable(path));
    return file.readAll();
}

class RegistryTest : public QObject {
    Q_OBJECT
private slots:
    void callsAndWrapsResult() {
        QTemporaryDir dir;
        Session session(dir.path(), nullptr);
        CommandContext context{session};
        session.registry().add(echo());
        const auto result = session.registry().call("echo", {{"n", 3}}, context);
        QVERIFY(result["ok"].toBool());
        QCOMPARE(result["result"].toObject()["n"].toInt(), 3);
        QVERIFY(!result.contains("error"));
    }
    void registrationOrderAndMetadataArePreserved() {
        CommandRegistry registry;
        auto first = echo();
        first.name = "z_last_alphabetically";
        first.mutating = true;
        registry.add(first);
        registry.add(echo());
        QVERIFY(registry.has(first.name));
        QVERIFY(!registry.has("missing"));
        const auto specs = registry.list();
        QCOMPARE(specs.size(), 2);
        QCOMPARE(specs[0].name, first.name);
        QCOMPARE(specs[0].description, first.description);
        QCOMPARE(specs[0].inputSchema, first.inputSchema);
        QVERIFY(specs[0].mutating);
        QCOMPARE(specs[1].name, QString("echo"));
    }
    void unknownCommand() {
        QTemporaryDir dir;
        Session session(dir.path(), nullptr);
        CommandContext context{session};
        const auto result = session.registry().call("nope", {}, context);
        QVERIFY(!result["ok"].toBool());
        QVERIFY(result["error"].toString().contains("unknown command"));
        QVERIFY(!result.contains("result"));
    }
    void validationErrors() {
        QTemporaryDir dir;
        Session session(dir.path(), nullptr);
        CommandContext context{session};
        auto spec = echo();
        bool called = false;
        spec.run = [&](const QJsonObject &, CommandContext &) { called = true; return QJsonObject{}; };
        session.registry().add(spec);
        QVERIFY(session.registry().call("echo", {}, context)["error"].toString().contains("missing required: n"));
        QVERIFY(session.registry().call("echo", {{"n", "x"}}, context)["error"].toString().contains("n: expected integer"));
        QVERIFY(session.registry().call("echo", {{"n", 1.5}}, context)["error"].toString().contains("n: expected integer"));
        QVERIFY(session.registry().call("echo", {{"n", 1}, {"mode", "z"}}, context)["error"].toString().contains("mode: not one of"));
        QVERIFY(!called);
    }
    void schemaTypes_data() {
        QTest::addColumn<QString>("type");
        QTest::addColumn<QJsonValue>("value");
        QTest::addColumn<bool>("valid");
        QTest::newRow("string") << QString("string") << QJsonValue("text") << true;
        QTest::newRow("boolean") << QString("boolean") << QJsonValue(false) << true;
        QTest::newRow("number") << QString("number") << QJsonValue(1.5) << true;
        QTest::newRow("integer") << QString("integer") << QJsonValue(-3) << true;
        QTest::newRow("object") << QString("object") << QJsonValue(QJsonObject{}) << true;
        QTest::newRow("array") << QString("array") << QJsonValue(QJsonArray{}) << true;
        QTest::newRow("untyped") << QString() << QJsonValue(QJsonValue::Null) << true;
        QTest::newRow("null-is-not-string") << QString("string") << QJsonValue(QJsonValue::Null) << false;
        QTest::newRow("integer-is-not-boolean") << QString("boolean") << QJsonValue(1) << false;
        QTest::newRow("numeric-string") << QString("number") << QJsonValue("1.5") << false;
        QTest::newRow("boolean-is-not-integer") << QString("integer") << QJsonValue(true) << false;
        QTest::newRow("fraction-is-not-integer") << QString("integer") << QJsonValue(-0.5) << false;
        QTest::newRow("array-is-not-object") << QString("object") << QJsonValue(QJsonArray{}) << false;
        QTest::newRow("object-is-not-array") << QString("array") << QJsonValue(QJsonObject{}) << false;
    }
    void schemaTypes() {
        QFETCH(QString, type);
        QFETCH(QJsonValue, value);
        QFETCH(bool, valid);
        const QJsonObject schema{{"type", "object"}, {"properties", QJsonObject{{"value", QJsonObject{{"type", type}}}}}};
        const auto error = CommandRegistry::validate(schema, {{"value", value}});
        QCOMPARE(error.isEmpty(), valid);
        if (!valid) QVERIFY(error.contains("value: expected " + type));
    }
    void optionalAndUnknownKeysAreTolerated() {
        const auto schema = echo().inputSchema;
        QVERIFY(CommandRegistry::validate(schema, {{"n", 0}, {"extra", QJsonArray{1}}}).isEmpty());
        QVERIFY(CommandRegistry::validate(schema, {{"n", 1}, {"mode", "a"}}).isEmpty());
        QVERIFY(CommandRegistry::validate(schema, {{"n", 1}, {"mode", "b"}}).isEmpty());
        const QJsonObject enumSchema{{"properties", QJsonObject{{"v", QJsonObject{{"enum", QJsonArray{1, 2}}}}}}};
        QVERIFY(CommandRegistry::validate(enumSchema, {{"v", 1}}).isEmpty());
        QVERIFY(!CommandRegistry::validate(enumSchema, {{"v", "1"}}).isEmpty());
    }
    void handlerExceptionBecomesError() {
        QTemporaryDir dir;
        Session session(dir.path(), nullptr);
        CommandContext context{session};
        auto spec = echo();
        spec.run = [](const QJsonObject &, CommandContext &) -> QJsonObject { throw CommandError{"bad thing"}; };
        session.registry().add(spec);
        const auto result = session.registry().call("echo", {{"n", 1}}, context);
        QVERIFY(!result["ok"].toBool());
        QCOMPARE(result["error"].toString(), QString("bad thing"));
    }
    void otherExceptionsNeverEscape() {
        QTemporaryDir dir;
        Session session(dir.path(), nullptr);
        CommandContext context{session};
        auto standard = echo();
        standard.name = "standard";
        standard.run = [](const QJsonObject &, CommandContext &) -> QJsonObject { throw std::runtime_error("standard failure"); };
        auto unknown = echo();
        unknown.name = "unknown";
        unknown.run = [](const QJsonObject &, CommandContext &) -> QJsonObject { throw 42; };
        auto empty = echo();
        empty.name = "empty";
        empty.run = {};
        session.registry().add(standard);
        session.registry().add(unknown);
        session.registry().add(empty);
        for (const auto &name : {"standard", "unknown", "empty"}) {
            const auto result = session.registry().call(name, {{"n", 1}}, context);
            QVERIFY(!result["ok"].toBool());
            QVERIFY(!result["error"].toString().isEmpty());
        }
        QCOMPARE(session.registry().call("standard", {{"n", 1}}, context)["error"].toString(), QString("standard failure"));
    }
    void commitWritesSnapshotsAndRecords() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        CommandContext context{session};
        session.files().read("fidelity.json");
        const auto before = session.files().read("moves/jab1.genoasm");
        int reloads = 0;
        QByteArray reloaded;
        session.onApplied = [&] { ++reloads; reloaded = session.files().read("moves/jab1.genoasm"); };
        const QJsonObject args{{"row", "jab1"}};
        const auto result = session.commit(context, "edit", args, "test", {{"moves/jab1.genoasm", before, "changed\n"}});
        QVERIFY(result["applied"].toBool());
        QCOMPARE(reloads, 1);
        QCOMPARE(reloaded, QByteArray("changed\n"));
        QCOMPARE(session.history().entries().size(), 1);
        const auto &entry = session.history().entries().first();
        QCOMPARE(entry.id, result["entry"].toInt());
        QCOMPARE(entry.author, QString("human"));
        QCOMPARE(entry.command, QString("edit"));
        QCOMPARE(entry.args, args);
        QCOMPARE(entry.summary, QString("test"));
        QCOMPARE(entry.state, QString("applied"));
        QCOMPARE(entry.changes.first().before, before);
        QCOMPARE(entry.changes.first().after, QByteArray("changed\n"));
        QDirIterator snapshots(dir.filePath(".workbench/snapshots"), {"jab1.genoasm"}, QDir::Files, QDirIterator::Subdirectories);
        QVERIFY(snapshots.hasNext());
        QCOMPARE(diskBytes(snapshots.next()), before);
        QVERIFY(!snapshots.hasNext());
        Session reopened(dir.path(), nullptr);
        QCOMPARE(reopened.history().entries().size(), 1);
        QString error;
        QVERIFY2(reopened.history().undo(reopened.files(), &error), qPrintable(error));
        QCOMPARE(diskBytes(dir.filePath("moves/jab1.genoasm")), before);
    }
    void commitRefusesWhenFileChangedExternally() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        CommandContext context{session};
        const auto before = session.files().read("moves/jab1.genoasm");
        wbtest::put(dir.path(), "moves/jab1.genoasm", "HAND\n");
        bool refused = false;
        try { session.commit(context, "edit", {}, "test", {{"moves/jab1.genoasm", before, "x\n"}}); }
        catch (const CommandError &error) { refused = error.message.contains("changed externally"); }
        QVERIFY(refused);
        QCOMPARE(diskBytes(dir.filePath("moves/jab1.genoasm")), QByteArray("HAND\n"));
        QVERIFY(session.history().entries().isEmpty());
        QVERIFY(!QFile::exists(session.historyPath()));
    }
    void conflictOnLaterAliasedPathLeavesAllFilesAlone() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        CommandContext context{session};
        const auto jab = session.files().read("moves/jab1.genoasm");
        const auto dair = session.files().read("moves/dair.genoasm");
        wbtest::put(dir.path(), "moves/dair.genoasm", "HAND\n");
        bool refused = false;
        try { session.commit(context, "edit", {}, "test", {{"moves/jab1.genoasm", jab, "x\n"}, {"./moves\\dair.genoasm", dair, "y\n"}}); }
        catch (const CommandError &error) { refused = error.message.contains("changed externally"); }
        QVERIFY(refused);
        QCOMPARE(diskBytes(dir.filePath("moves/jab1.genoasm")), jab);
        QCOMPARE(diskBytes(dir.filePath("moves/dair.genoasm")), QByteArray("HAND\n"));
        QCOMPARE(session.files().externalChanges(), QStringList{"moves/dair.genoasm"});
        QVERIFY(session.history().entries().isEmpty());
        QVERIFY(!QDir(dir.filePath(".workbench/snapshots")).exists());
    }
    void staleUntrackedChangeIsRefused() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        CommandContext context{session};
        wbtest::put(dir.path(), "moves/jab1.genoasm", "HAND\n");
        bool refused = false;
        try { session.commit(context, "edit", {}, "test", {{"moves/jab1.genoasm", wbtest::kJab, "x\n"}}); }
        catch (const CommandError &error) { refused = error.message.contains("changed externally"); }
        QVERIFY(refused);
        QCOMPARE(diskBytes(dir.filePath("moves/jab1.genoasm")), QByteArray("HAND\n"));
    }
    void unrelatedExternalChangeDoesNotBlockCommit() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        CommandContext context{session};
        session.files().read("fidelity.json");
        const auto before = session.files().read("moves/jab1.genoasm");
        wbtest::put(dir.path(), "fidelity.json", "HAND\n");
        QVERIFY(session.commit(context, "edit", {}, "test", {{"moves/jab1.genoasm", before, "x\n"}})["applied"].toBool());
        QCOMPARE(diskBytes(dir.filePath("fidelity.json")), QByteArray("HAND\n"));
        QCOMPARE(session.files().externalChanges(), QStringList{"fidelity.json"});
    }
    void emptyCommitHasNoSideEffects() {
        QTemporaryDir dir;
        Session session(dir.path(), nullptr);
        CommandContext context{session, "agent", true};
        int reloads = 0;
        session.onApplied = [&] { ++reloads; };
        const auto result = session.commit(context, "edit", {}, "test", {});
        QVERIFY(!result["applied"].toBool());
        QCOMPARE(result["note"].toString(), QString("no change"));
        QVERIFY(!result.contains("entry"));
        QVERIFY(session.history().entries().isEmpty());
        QVERIFY(!QDir(dir.filePath(".workbench")).exists());
        QCOMPARE(reloads, 0);
    }
    void proposalPolicy_data() {
        QTest::addColumn<QString>("author");
        QTest::addColumn<bool>("explicitProposal");
        QTest::addColumn<bool>("agentProposals");
        QTest::addColumn<bool>("proposed");
        QTest::newRow("agent-opt-in") << QString("agent") << false << true << true;
        QTest::newRow("explicit-human") << QString("human") << true << false << true;
        QTest::newRow("explicit-agent") << QString("agent") << true << false << true;
        QTest::newRow("agent-default") << QString("agent") << false << false << false;
        QTest::newRow("human-unaffected") << QString("human") << false << true << false;
    }
    void proposalPolicy() {
        QFETCH(QString, author);
        QFETCH(bool, explicitProposal);
        QFETCH(bool, agentProposals);
        QFETCH(bool, proposed);
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        session.agentProposals = agentProposals;
        CommandContext context{session, author, explicitProposal};
        const auto before = session.files().read("moves/jab1.genoasm");
        int reloads = 0;
        session.onApplied = [&] { ++reloads; };
        const auto result = session.commit(context, "edit", {}, "test", {{"moves/jab1.genoasm", before, "x\n"}});
        QCOMPARE(result["proposed"].toBool(), proposed);
        QCOMPARE(result["applied"].toBool(), !proposed);
        QCOMPARE(diskBytes(dir.filePath("moves/jab1.genoasm")), proposed ? before : QByteArray("x\n"));
        QCOMPARE(reloads, proposed ? 0 : 1);
        Session reopened(dir.path(), nullptr);
        QCOMPARE(reopened.history().entries().size(), 1);
        const auto &entry = reopened.history().entries().first();
        QCOMPARE(entry.id, result["entry"].toInt());
        QCOMPARE(entry.author, author);
        QCOMPARE(entry.state, proposed ? QString("proposed") : QString("applied"));
        QCOMPARE(entry.changes.first().before, before);
        if (proposed) QVERIFY(!QDir(dir.filePath(".workbench/snapshots")).exists());
    }
    void invalidOrDuplicatePathsAreRefusedBeforeWriting() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        CommandContext context{session};
        const auto before = session.files().read("moves/jab1.genoasm");
        for (const auto &path : {"./moves\\jab1.genoasm", "../outside.genoasm"}) {
            bool refused = false;
            try { session.commit(context, "edit", {}, "test", {{"moves/jab1.genoasm", before, "x\n"}, {path, before, "y\n"}}); }
            catch (const CommandError &) { refused = true; }
            QVERIFY(refused);
            QCOMPARE(diskBytes(dir.filePath("moves/jab1.genoasm")), before);
            QVERIFY(session.history().entries().isEmpty());
        }
    }
    void reloadFailureKeepsPersistedUndo() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        CommandContext context{session};
        const auto before = session.files().read("moves/jab1.genoasm");
        session.onApplied = [] { throw std::runtime_error("reload failed"); };
        CommandSpec spec;
        spec.name = "edit";
        spec.mutating = true;
        spec.run = [&](const QJsonObject &args, CommandContext &ctx) {
            return ctx.session.commit(ctx, "edit", args, "test", {{"moves/jab1.genoasm", before, "changed\n"}});
        };
        session.registry().add(spec);
        const auto result = session.registry().call("edit", {}, context);
        QVERIFY(!result["ok"].toBool());
        QVERIFY(result["error"].toString().contains("reload failed"));
        QCOMPARE(diskBytes(dir.filePath("moves/jab1.genoasm")), QByteArray("changed\n"));
        Session reopened(dir.path(), nullptr);
        QCOMPARE(reopened.history().entries().size(), 1);
        QString error;
        QVERIFY2(reopened.history().undo(reopened.files(), &error), qPrintable(error));
        QCOMPARE(diskBytes(dir.filePath("moves/jab1.genoasm")), before);
    }
    void writeFailureRestoresEarlierFilesAndPreservesRedo() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        CommandContext context{session};
        const auto before = session.files().read("moves/jab1.genoasm");
        session.commit(context, "edit", {}, "test", {{"moves/jab1.genoasm", before, "first\n"}});
        QString error;
        QVERIFY2(session.history().undo(session.files(), &error), qPrintable(error));
        QVERIFY(session.history().save(session.historyPath()));
        const auto historyBefore = session.history().toJson();
        const auto persistedBefore = diskBytes(session.historyPath());
        wbtest::put(dir.path(), "moves/blocker", "not a directory\n");
        int reloads = 0;
        session.onApplied = [&] { ++reloads; };
        bool refused = false;
        try {
            session.commit(context, "edit", {}, "test", {
                {"moves/jab1.genoasm", before, "changed\n"},
                {"moves/blocker/new.genoasm", {}, "new\n"}
            });
        } catch (const CommandError &) { refused = true; }
        QVERIFY(refused);
        QCOMPARE(diskBytes(dir.filePath("moves/jab1.genoasm")), before);
        QCOMPARE(diskBytes(dir.filePath("moves/blocker")), QByteArray("not a directory\n"));
        QCOMPARE(session.history().toJson(), historyBefore);
        QCOMPARE(diskBytes(session.historyPath()), persistedBefore);
        QCOMPARE(reloads, 0);
        QVERIFY2(session.history().redo(session.files(), &error), qPrintable(error));
        QCOMPARE(diskBytes(dir.filePath("moves/jab1.genoasm")), QByteArray("first\n"));
    }
    void appliedHistorySaveFailureRestoresFiles() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        wbtest::put(dir.path(), "moves/empty.genoasm", "");
        Session session(dir.path(), nullptr);
        CommandContext context{session};
        const auto before = session.files().read("moves/jab1.genoasm");
        QVERIFY(QDir().mkpath(session.historyPath()));
        int reloads = 0;
        session.onApplied = [&] { ++reloads; };
        bool refused = false;
        try {
            session.commit(context, "edit", {}, "test", {
                {"moves/jab1.genoasm", before, "changed\n"},
                {"moves/empty.genoasm", {}, "filled\n"},
                {"moves/new.genoasm", {}, "new\n"}
            });
        } catch (const CommandError &error) { refused = error.message.contains("history"); }
        QVERIFY(refused);
        QCOMPARE(diskBytes(dir.filePath("moves/jab1.genoasm")), before);
        QVERIFY(QFile::exists(dir.filePath("moves/empty.genoasm")));
        QVERIFY(diskBytes(dir.filePath("moves/empty.genoasm")).isEmpty());
        QVERIFY(!QFile::exists(dir.filePath("moves/new.genoasm")));
        QVERIFY(session.files().externalChanges().isEmpty());
        QVERIFY(session.history().entries().isEmpty());
        QCOMPARE(reloads, 0);
    }
    void historySaveFailureIsReported() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        CommandContext context{session, "agent", true};
        const auto before = session.files().read("moves/jab1.genoasm");
        QVERIFY(QDir().mkpath(session.historyPath())); // A directory cannot be replaced by a history file.
        bool refused = false;
        try { session.commit(context, "edit", {}, "test", {{"moves/jab1.genoasm", before, "x\n"}}); }
        catch (const CommandError &error) { refused = error.message.contains("history"); }
        QVERIFY(refused);
        QCOMPARE(diskBytes(dir.filePath("moves/jab1.genoasm")), before);
        QVERIFY(session.history().entries().isEmpty());
        QVERIFY(QDir().rmdir(session.historyPath()));
        const auto result = session.commit(context, "edit", {}, "test", {{"moves/jab1.genoasm", before, "x\n"}});
        QVERIFY(result["proposed"].toBool());
        QCOMPARE(result["entry"].toInt(), 1);
        Session reopened(dir.path(), nullptr);
        QCOMPARE(reopened.history().entries().size(), 1);
        QCOMPARE(reopened.history().entries().first().state, QString("proposed"));
        QCOMPARE(diskBytes(dir.filePath("moves/jab1.genoasm")), before);
    }
};
QTEST_GUILESS_MAIN(RegistryTest)
#include "command_registry_test.moc"
