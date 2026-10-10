#include "../testfixture.h"
#include "commands.h"
#include "geno_data.h"
#include "session.h"
#include <QFile>
#include <QJsonDocument>
#include <QTemporaryDir>
#include <QtTest>
#include <limits>

using namespace wb;

static QJsonObject callCmd(Session &s, const QString &name, const QJsonObject &args = {},
                           const QString &author = "human") {
    CommandContext ctx{s, author};
    return s.registry().call(name, args, ctx);
}

static QByteArray diskBytes(const QString &path) {
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly)) qFatal("test: cannot read %s", qPrintable(path));
    return file.readAll();
}

// Exercises proposal validation and the real GenoData/Session write path without Task 10.
static void addEditCommand(Session &session) {
    CommandSpec edit;
    edit.name = "test_edit";
    edit.mutating = true;
    edit.inputSchema = {{"type", "object"}, {"required", QJsonArray{"damage"}},
        {"properties", QJsonObject{{"damage", QJsonObject{{"type", "number"}}}}}};
    edit.run = [](const QJsonObject &args, CommandContext &ctx) {
        HitboxEdit change;
        change.damage = args["damage"].toDouble();
        QString error;
        const auto changes = ctx.session.data().editHitbox("dair", 0, change, &error);
        if (!error.isEmpty()) throw CommandError{error};
        return ctx.session.commit(ctx, "test_edit", args, "dair damage", changes);
    };
    session.registry().add(edit);
}

static void setRebuild(const QString &root, const QStringList &argv) {
    QJsonObject config = QJsonDocument::fromJson(wbtest::kProject).object();
    config["rebuild"] = QJsonArray::fromStringList(argv);
    wbtest::put(root, "workbench.json", QJsonDocument(config).toJson());
}

class SaveCmdTest : public QObject {
    Q_OBJECT
private slots:
    void registrationIsExplicitAndIndependentOfTask10() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        QVERIFY(session.registry().list().isEmpty());
        registerAllCommands(session);
        const QStringList names{"save", "rebuild", "reload", "undo", "redo", "history", "propose", "accept", "reject"};
        QVERIFY(session.registry().list().size() >= names.size()); // registerAllCommands also registers the view/row/hitbox/clip commands (Task 10)
        for (const auto &name : names) QVERIFY(session.registry().has(name));
        QVERIFY(!session.agentProposals);
    }

    void undoRedoViaCommandsRefreshAndPersist() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        registerSaveCommands(session);
        addEditCommand(session);
        const QByteArray old = session.files().read("moves/dair.genoasm");
        QVERIFY(callCmd(session, "test_edit", {{"damage", 19}})["ok"].toBool());
        const QByteArray edited = diskBytes(dir.filePath("moves/dair.genoasm"));
        QCOMPARE(session.data().hitboxes("dair").first().damage, 19.0);
        QVERIFY(callCmd(session, "undo")["ok"].toBool());
        QCOMPARE(diskBytes(dir.filePath("moves/dair.genoasm")), old);
        QCOMPARE(session.data().hitboxes("dair").first().damage, 14.0);
        QCOMPARE(History::load(session.historyPath()).entries().first().state, QString("undone"));
        // Redo survives a new session, including its cached fighter model.
        Session reopened(dir.path(), nullptr);
        registerSaveCommands(reopened);
        QCOMPARE(reopened.data().hitboxes("dair").first().damage, 14.0);
        QVERIFY(callCmd(reopened, "redo")["ok"].toBool());
        QCOMPARE(diskBytes(dir.filePath("moves/dair.genoasm")), edited);
        QCOMPARE(reopened.data().hitboxes("dair").first().damage, 19.0);
        QCOMPARE(History::load(reopened.historyPath()).entries().first().state, QString("applied"));
    }

    void undoReportsExternalChangeWithoutAcknowledgingIt() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        registerSaveCommands(session);
        addEditCommand(session);
        QVERIFY(callCmd(session, "test_edit", {{"damage", 19}})["ok"].toBool());
        wbtest::put(dir.path(), "moves/dair.genoasm", "# HAND\n");
        const auto reply = callCmd(session, "undo");
        QVERIFY(!reply["ok"].toBool());
        QVERIFY(reply["error"].toString().contains("changed externally"));
        QCOMPARE(diskBytes(dir.filePath("moves/dair.genoasm")), QByteArray("# HAND\n"));
        QVERIFY(session.files().externalChanges().contains("moves/dair.genoasm"));
        QCOMPARE(session.history().entries().first().state, QString("applied"));
        QCOMPARE(session.data().hitboxes("dair").first().damage, 19.0);
    }

    void redoReportsExternalChange() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        registerSaveCommands(session);
        addEditCommand(session);
        QVERIFY(callCmd(session, "test_edit", {{"damage", 19}})["ok"].toBool());
        QVERIFY(callCmd(session, "undo")["ok"].toBool());
        wbtest::put(dir.path(), "moves/dair.genoasm", "# HAND\n");
        const auto reply = callCmd(session, "redo");
        QVERIFY(!reply["ok"].toBool());
        QVERIFY(reply["error"].toString().contains("changed externally"));
        QCOMPARE(diskBytes(dir.filePath("moves/dair.genoasm")), QByteArray("# HAND\n"));
        QCOMPARE(session.history().entries().first().state, QString("undone"));
    }

    void undoDoesNotAcknowledgeAnUnrelatedHandEdit() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        registerSaveCommands(session);
        addEditCommand(session);
        QVERIFY(callCmd(session, "test_edit", {{"damage", 19}})["ok"].toBool());
        wbtest::put(dir.path(), "gameplay.json", "{}\n");
        const auto reply = callCmd(session, "undo");
        QVERIFY(!reply["ok"].toBool());
        QVERIFY(reply["error"].toString().contains("changed externally"));
        QCOMPARE(session.data().hitboxes("dair").first().damage, 19.0);
        QVERIFY(session.files().externalChanges().contains("gameplay.json"));
    }

    void saveIsVerificationWithoutANewSnapshot() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        session.data();
        registerSaveCommands(session);
        const auto reply = callCmd(session, "save");
        QVERIFY(reply["ok"].toBool());
        const auto result = reply["result"].toObject();
        QVERIFY(result.contains("dirty"));
        QVERIFY(!result["dirty"].toBool());
        QVERIFY(result["external"].toArray().isEmpty());
        QVERIFY(!result.contains("warning"));
        QVERIFY(!QFileInfo::exists(dir.filePath(".workbench")));
    }

    void saveReportsExternalChangesWithoutWriting() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        session.data();
        registerSaveCommands(session);
        wbtest::put(dir.path(), "gameplay.json", "{}\n");
        const auto reply = callCmd(session, "save");
        // The Task 9 save verb is read-only: success plus a warning, never an overwrite.
        QVERIFY(reply["ok"].toBool());
        const auto result = reply["result"].toObject();
        QCOMPARE(result["external"].toArray(), QJsonArray{"gameplay.json"});
        QVERIFY(result["warning"].toString().contains("changed externally"));
        QVERIFY(!result["dirty"].toBool());
        QCOMPARE(diskBytes(dir.filePath("gameplay.json")), QByteArray("{}\n"));
        QCOMPARE(session.files().externalChanges(), QStringList{"gameplay.json"});
        QVERIFY(!QFileInfo::exists(dir.filePath(".workbench")));
    }

    void proposeAcceptRejectPersistAndRefresh() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        registerSaveCommands(session);
        addEditCommand(session);
        const QByteArray old = session.files().read("moves/dair.genoasm");
        const auto proposal = callCmd(session, "propose",
            {{"command", "test_edit"}, {"args", QJsonObject{{"damage", 19}}}}, "agent");
        QVERIFY(proposal["ok"].toBool());
        const auto result = proposal["result"].toObject();
        QVERIFY(result["proposed"].toBool());
        const int id = result["entry"].toInt();
        QCOMPARE(diskBytes(dir.filePath("moves/dair.genoasm")), old);
        QCOMPARE(session.data().hitboxes("dair").first().damage, 14.0);
        const auto saved = History::load(session.historyPath());
        QCOMPARE(saved.entries().first().state, QString("proposed"));
        QCOMPARE(saved.entries().first().author, QString("agent"));
        QVERIFY(callCmd(session, "accept", {{"id", id}})["ok"].toBool());
        QCOMPARE(session.data().hitboxes("dair").first().damage, 19.0);
        QCOMPARE(History::load(session.historyPath()).entries().first().state, QString("applied"));
        const QByteArray accepted = diskBytes(dir.filePath("moves/dair.genoasm"));
        const auto second = callCmd(session, "propose",
            {{"command", "test_edit"}, {"args", QJsonObject{{"damage", 22}}}}, "agent");
        QVERIFY(second["ok"].toBool());
        const int rejectedId = second["result"].toObject()["entry"].toInt();
        QVERIFY(callCmd(session, "reject", {{"id", rejectedId}})["ok"].toBool());
        QCOMPARE(diskBytes(dir.filePath("moves/dair.genoasm")), accepted);
        QCOMPARE(session.data().hitboxes("dair").first().damage, 19.0);
        QCOMPARE(History::load(session.historyPath()).entries().last().state, QString("rejected"));
        QVERIFY(!callCmd(session, "accept", {{"id", rejectedId}})["ok"].toBool());
        QVERIFY(callCmd(session, "undo")["ok"].toBool());
        QCOMPARE(diskBytes(dir.filePath("moves/dair.genoasm")), old);
    }

    void acceptReportsExternalChangeWithoutAcknowledgingIt() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        registerSaveCommands(session);
        addEditCommand(session);
        const auto proposed = callCmd(session, "propose",
            {{"command", "test_edit"}, {"args", QJsonObject{{"damage", 19}}}});
        QVERIFY(proposed["ok"].toBool());
        const int id = proposed["result"].toObject()["entry"].toInt();
        wbtest::put(dir.path(), "moves/dair.genoasm", "# HAND\n");
        const auto reply = callCmd(session, "accept", {{"id", id}});
        QVERIFY(!reply["ok"].toBool());
        QVERIFY(reply["error"].toString().contains("changed externally"));
        QCOMPARE(diskBytes(dir.filePath("moves/dair.genoasm")), QByteArray("# HAND\n"));
        QVERIFY(session.files().externalChanges().contains("moves/dair.genoasm"));
        QCOMPARE(session.history().entries().first().state, QString("proposed"));
        QCOMPARE(History::load(session.historyPath()).entries().first().state, QString("proposed"));
        QCOMPARE(session.data().hitboxes("dair").first().damage, 14.0);
    }

    void acceptRefusesStaleProposalAfterAnotherToolEdit() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        registerSaveCommands(session);
        addEditCommand(session);
        const auto proposed = callCmd(session, "propose",
            {{"command", "test_edit"}, {"args", QJsonObject{{"damage", 19}}}});
        QVERIFY(proposed["ok"].toBool());
        const int id = proposed["result"].toObject()["entry"].toInt();
        QVERIFY(callCmd(session, "test_edit", {{"damage", 22}})["ok"].toBool());
        QVERIFY(session.files().externalChanges().isEmpty());
        const auto reply = callCmd(session, "accept", {{"id", id}});
        QVERIFY(!reply["ok"].toBool());
        QVERIFY(reply["error"].toString().contains("changed externally"));
        QCOMPARE(session.data().hitboxes("dair").first().damage, 22.0);
        QCOMPARE(session.history().entries().first().state, QString("proposed"));
    }

    void agentProposalPolicyRemainsControlledByTheCaller() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        registerSaveCommands(session);
        addEditCommand(session);
        QVERIFY(!session.agentProposals);
        QVERIFY(callCmd(session, "test_edit", {{"damage", 19}}, "agent")["result"].toObject()["applied"].toBool());
        session.agentProposals = true; // MCP's policy; registration never changes it.
        QVERIFY(callCmd(session, "test_edit", {{"damage", 22}}, "agent")["result"].toObject()["proposed"].toBool());
        QCOMPARE(session.data().hitboxes("dair").first().damage, 19.0);
    }

    void proposeValidatesTheNestedCommandAndPreservesContext() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        registerSaveCommands(session);
        addEditCommand(session);
        QVERIFY(!callCmd(session, "propose", {{"command", "absent"}, {"args", QJsonObject{}}})["ok"].toBool());
        QVERIFY(!callCmd(session, "propose", {{"command", "history"}, {"args", QJsonObject{}}})["ok"].toBool());
        // Administrative commands cannot be executed through the proposal wrapper.
        QVERIFY(!callCmd(session, "propose", {{"command", "undo"}, {"args", QJsonObject{}}})["ok"].toBool());
        auto reply = callCmd(session, "propose", {{"command", "test_edit"}, {"args", QJsonObject{}}});
        QVERIFY(!reply["ok"].toBool());
        QVERIFY(reply["error"].toString().contains("missing required: damage"));
        reply = callCmd(session, "propose", {{"command", "test_edit"}, {"args", QJsonObject{{"damage", "bad"}}}});
        QVERIFY(!reply["ok"].toBool());
        QVERIFY(reply["error"].toString().contains("expected number"));
        QVERIFY(session.history().entries().isEmpty());
        CommandContext ctx{session, "agent"};
        reply = session.registry().call("propose",
            {{"command", "test_edit"}, {"args", QJsonObject{{"damage", 19}}}}, ctx);
        QVERIFY(reply["ok"].toBool());
        QVERIFY(!ctx.propose);
        reply = session.registry().call("test_edit", {{"damage", 22}}, ctx);
        QVERIFY(reply["result"].toObject()["applied"].toBool());
    }

    void historyListsRecentMetadataWithoutBytes() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        registerSaveCommands(session);
        addEditCommand(session);
        QVERIFY(callCmd(session, "test_edit", {{"damage", 19}})["ok"].toBool());
        QVERIFY(callCmd(session, "test_edit", {{"damage", 22}})["ok"].toBool());
        const auto history = callCmd(session, "history")["result"].toObject()["entries"].toArray();
        QCOMPARE(history.size(), 2);
        const auto entry = history.last().toObject();
        QCOMPARE(entry["id"].toInt(), 2);
        QCOMPARE(entry["author"].toString(), QString("human"));
        QCOMPARE(entry["command"].toString(), QString("test_edit"));
        QCOMPARE(entry["summary"].toString(), QString("dair damage"));
        QCOMPARE(entry["state"].toString(), QString("applied"));
        QVERIFY(entry["time"].toInteger() > 0);
        QCOMPARE(entry.size(), 6);
        const auto limited = callCmd(session, "history", {{"limit", 1}})["result"].toObject()["entries"].toArray();
        QCOMPARE(limited.size(), 1);
        QCOMPARE(limited.first().toObject()["id"].toInt(), 2);
        QVERIFY(callCmd(session, "history", {{"limit", 0}})["result"].toObject()["entries"].toArray().isEmpty());
        QCOMPARE(callCmd(session, "history", {{"limit", 10}})["result"].toObject()["entries"].toArray().size(), 2);
        QVERIFY(!callCmd(session, "history", {{"limit", -1}})["ok"].toBool());
    }

    void invalidArgumentsAndEmptyHistoryAreErrors() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        registerSaveCommands(session);
        QVERIFY(!callCmd(session, "undo")["ok"].toBool());
        QVERIFY(!callCmd(session, "redo")["ok"].toBool());
        QVERIFY(!callCmd(session, "accept")["ok"].toBool());
        QVERIFY(!callCmd(session, "reject", {{"id", "one"}})["ok"].toBool());
        QVERIFY(!callCmd(session, "accept", {{"id", 1.5}})["ok"].toBool());
        QVERIFY(!callCmd(session, "accept", {{"id", 0}})["ok"].toBool());
        QVERIFY(!callCmd(session, "reject", {{"id", 99}})["ok"].toBool());
        QVERIFY(!callCmd(session, "history", {{"limit", "one"}})["ok"].toBool());
        QVERIFY(!callCmd(session, "history", {{"limit", 1.5}})["ok"].toBool());
        const double huge = double(std::numeric_limits<int>::max()) + 1;
        QVERIFY(!callCmd(session, "history", {{"limit", huge}})["ok"].toBool());
        QVERIFY(!callCmd(session, "accept", {{"id", huge}})["ok"].toBool());
        QVERIFY(!callCmd(session, "propose", {{"command", "test_edit"}, {"args", 4}})["ok"].toBool());
        QVERIFY(!callCmd(session, "propose", {{"command", "test_edit"}})["ok"].toBool());
    }

    void changeSummaryContainsCountsWithoutSourceBytes() {
        const QVector<FileChange> changes{{"moves/test.genoasm", QByteArray("\0\1", 2), "after\n"},
                                          {"new.txt", {}, "new"}};
        const auto summary = changeToJson(changes)["changes"].toArray();
        QCOMPARE(summary.size(), 2);
        QCOMPARE(summary[0].toObject(), (QJsonObject{{"path", "moves/test.genoasm"}, {"bytes_before", 2}, {"bytes_after", 6}}));
        QCOMPARE(summary[1].toObject(), (QJsonObject{{"path", "new.txt"}, {"bytes_before", 0}, {"bytes_after", 3}}));
        QVERIFY(changeToJson({})["changes"].toArray().isEmpty());
    }

    void rebuildRunsConfiguredCommand() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        registerSaveCommands(session);
        const auto reply = callCmd(session, "rebuild");
        QVERIFY2(reply["ok"].toBool(), qPrintable(reply["error"].toString()));
        const auto result = reply["result"].toObject();
        QCOMPARE(result["exit"].toInt(-1), 0);
        QVERIFY(result["tail"].toString().contains("rebuilt"));
        QCOMPARE(result["output"].toString(), result["tail"].toString());
    }

    void rebuildFailureIsError() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        setRebuild(dir.path(), {"python", "-c", "import sys; print('before failure'); sys.stderr.write('stderr failure'); raise SystemExit(3)"});
        Session session(dir.path(), nullptr);
        registerSaveCommands(session);
        const auto reply = callCmd(session, "rebuild");
        QVERIFY(!reply["ok"].toBool());
        QVERIFY(reply["error"].toString().contains("exit 3"));
        QVERIFY(reply["error"].toString().contains("stderr failure"));
    }

    void rebuildExpandsArgvAndUsesWorkspaceRootWithoutAShell() {
        QTemporaryDir dir;
        const QString project = QDir(dir.path()).filePath("ports/synthetic fighter");
        wbtest::makeSynthFighter(project);
        wbtest::put(dir.path(), ".git", "synthetic workspace marker\n");
        const QString literal = "literal ; $(echo wb) with spaces and quotes ' \"";
        setRebuild(project, {"python", "-c", "import json,os,sys; print(json.dumps({'cwd':os.getcwd(),'args':sys.argv[1:]}))",
            "{project}", "{package}", literal});
        Session session(project, nullptr);
        registerSaveCommands(session);
        const auto reply = callCmd(session, "rebuild");
        QVERIFY2(reply["ok"].toBool(), qPrintable(reply["error"].toString()));
        const auto payload = QJsonDocument::fromJson(reply["result"].toObject()["tail"].toString().toUtf8()).object();
        QCOMPARE(QDir(payload["cwd"].toString()).canonicalPath(), QDir(dir.path()).canonicalPath());
        const auto argv = payload["args"].toArray();
        QCOMPARE(argv.size(), 3);
        QCOMPARE(QDir(argv[0].toString()).canonicalPath(), QDir(project).canonicalPath());
        QCOMPARE(QDir(argv[1].toString()).canonicalPath(), QDir(QDir(project).filePath("package")).canonicalPath());
        QCOMPARE(argv[2].toString(), literal);
    }

    void rebuildKeepsOnlyTheTailOfBothStreams() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        setRebuild(dir.path(), {"python", "-c", "import sys; sys.stdout.write('O'*5000); sys.stderr.write('stderr-tail')"});
        Session session(dir.path(), nullptr);
        registerSaveCommands(session);
        const auto reply = callCmd(session, "rebuild");
        QVERIFY2(reply["ok"].toBool(), qPrintable(reply["error"].toString()));
        const auto result = reply["result"].toObject();
        QCOMPARE(result["tail"].toString(), QString(3989, QChar('O')) + "stderr-tail");
        QCOMPARE(result["output"].toString(), result["tail"].toString());
    }

    void rebuildNotConfiguredAndStartFailureAreErrors() {
        QTemporaryDir empty;
        wbtest::makeSynthFighter(empty.path());
        setRebuild(empty.path(), {});
        Session noCommand(empty.path(), nullptr);
        registerSaveCommands(noCommand);
        auto reply = callCmd(noCommand, "rebuild");
        QVERIFY(!reply["ok"].toBool());
        QVERIFY(reply["error"].toString().contains("not configured"));
        QTemporaryDir missing;
        wbtest::makeSynthFighter(missing.path());
        setRebuild(missing.path(), {"wb-t9-executable-that-does-not-exist"});
        Session cannotStart(missing.path(), nullptr);
        registerSaveCommands(cannotStart);
        reply = callCmd(cannotStart, "rebuild");
        QVERIFY(!reply["ok"].toBool());
        QVERIFY(reply["error"].toString().contains("failed to start"));
    }

    void reloadRestartsTheEngineAndRefreshesData() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        wbtest::FakeEngine engine;
        Session session(dir.path(), &engine);
        QCOMPARE(session.data().hitboxes("dair").first().damage, 14.0);
        registerSaveCommands(session);
        wbtest::put(dir.path(), "moves/dair.genoasm", QByteArray(wbtest::kDair).replace("damage=14", "damage=19"));
        const auto reply = callCmd(session, "reload");
        QVERIFY2(reply["ok"].toBool(), qPrintable(reply["error"].toString()));
        QCOMPARE(engine.calls.size(), 1);
        QCOMPARE(engine.calls.first().first, QString("restart"));
        QCOMPARE(session.data().hitboxes("dair").first().damage, 19.0);
        QVERIFY(session.files().externalChanges().isEmpty());
    }

    void reloadEngineFailureDoesNotAcknowledgeHandEdits() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        wbtest::FakeEngine engine;
        engine.failWith = "engine stopped";
        Session session(dir.path(), &engine);
        QCOMPARE(session.data().hitboxes("dair").first().damage, 14.0);
        registerSaveCommands(session);
        wbtest::put(dir.path(), "moves/dair.genoasm", "# HAND\n");
        const auto reply = callCmd(session, "reload");
        QVERIFY(!reply["ok"].toBool());
        QVERIFY(reply["error"].toString().contains("engine stopped"));
        QCOMPARE(session.data().hitboxes("dair").first().damage, 14.0);
        QVERIFY(session.files().externalChanges().contains("moves/dair.genoasm"));
    }

    void reloadWithoutEngineAndMalformedDataAreErrors() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session offline(dir.path(), nullptr);
        registerSaveCommands(offline);
        auto reply = callCmd(offline, "reload");
        QVERIFY(!reply["ok"].toBool());
        QVERIFY(reply["error"].toString().contains("engine not running"));
        wbtest::FakeEngine engine;
        Session session(dir.path(), &engine);
        session.data();
        registerSaveCommands(session);
        wbtest::put(dir.path(), "gameplay.json", "{invalid");
        reply = callCmd(session, "reload");
        QVERIFY(!reply["ok"].toBool());
        QVERIFY(reply["error"].toString().contains("reload failed"));
        QCOMPARE(engine.calls.size(), 1);
        QVERIFY(session.data().rows().isEmpty());
    }
};
QTEST_GUILESS_MAIN(SaveCmdTest)
#include "commands_save_test.moc"
