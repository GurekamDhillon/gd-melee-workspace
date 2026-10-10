#include "../testfixture.h"
#include "geno_data.h"
#include "mcp_server.h"
#include "session.h"
#include "workbench_main.h"
#include <QCoreApplication>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonParseError>
#include <QSet>
#include <QTemporaryDir>
#include <QtTest>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <vector>

using namespace wb;

namespace {
QJsonObject req(const QJsonValue &id, const QString &method, QJsonObject params = {}) {
    return {{"jsonrpc", "2.0"}, {"id", id}, {"method", method}, {"params", params}};
}
QJsonObject call(const QString &name, QJsonObject args = {}) {
    return req(1, "tools/call", {{"name", name}, {"arguments", args}});
}
QByteArray line(const QJsonObject &object) {
    return QJsonDocument(object).toJson(QJsonDocument::Compact) + '\n';
}
QJsonObject payload(const QJsonObject &response) {
    const auto content = response.value("result").toObject().value("content").toArray();
    if (content.size() != 1) return {};
    return QJsonDocument::fromJson(content[0].toObject().value("text").toString().toUtf8()).object();
}
QByteArray readFile(const QString &path) {
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly)) qFatal("cannot read test file");
    return file.readAll();
}

// Only the registry's command implementations are synthetic. The server, schema
// validator, Session, source edits, persisted history and transports are real.
struct McpRig {
    QTemporaryDir dir;
    Session session;
    McpServer server;
    McpRig() : session(wbtest::makeSynthFighter(dir.path()), nullptr), server(session) {
        session.registry() = CommandRegistry{}; // Independent of later task registrations.
        const QJsonObject empty{{"type", "object"}, {"properties", QJsonObject{}}};
        session.registry().add({"inspect", "Inspect the synthetic fighter", empty, false,
            [](const QJsonObject &, CommandContext &ctx) {
                return QJsonObject{{"rows", int(ctx.session.data().rows().size())}, {"author", ctx.author}};
            }});
        session.registry().add({"edit", "Set synthetic dair damage",
            {{"type", "object"}, {"properties", QJsonObject{
                {"damage", QJsonObject{{"type", "number"}}},
                {"propose", QJsonObject{{"type", "boolean"}}}}},
             {"required", QJsonArray{"damage"}}}, true,
            [](const QJsonObject &args, CommandContext &ctx) {
                HitboxEdit edit; edit.damage = args["damage"].toDouble();
                QString error;
                auto changes = ctx.session.data().editHitbox("dair", 0, edit, &error);
                if (!error.isEmpty()) throw CommandError{error};
                // Deliberately try to opt out: the server must retain agent policy.
                auto local = ctx;
                local.propose = args.value("propose").toBool(false);
                return ctx.session.commit(local, "edit", args, "Synthetic damage", changes);
            }});
        session.registry().add({"fail", "Report a command failure", empty, false,
            [](const QJsonObject &, CommandContext &) -> QJsonObject { throw CommandError{"synthetic failure"}; }});
        session.registry().add({"throw", "Report a standard exception", empty, false,
            [](const QJsonObject &, CommandContext &) -> QJsonObject { throw std::runtime_error("synthetic exception"); }});
        for (const QString &name : {QString("accept"), QString("reject"), QString("undo"), QString("redo")}) {
            session.registry().add({name, "Human history action", empty, true,
                [name](const QJsonObject &args, CommandContext &ctx) {
                    QString error;
                    bool ok = false;
                    if (name == "accept") ok = ctx.session.history().accept(args["id"].toInt(), ctx.session.files(), &error);
                    if (name == "reject") ok = ctx.session.history().reject(args["id"].toInt(), &error);
                    if (name == "undo") ok = ctx.session.history().undo(ctx.session.files(), &error);
                    if (name == "redo") ok = ctx.session.history().redo(ctx.session.files(), &error);
                    if (!ok) throw CommandError{error};
                    return QJsonObject{{"applied", true}};
                }});
        }
        session.registry().add({"propose", "Propose a command",
            {{"type", "object"}, {"properties", QJsonObject{
                {"command", QJsonObject{{"type", "string"}}}, {"args", QJsonObject{{"type", "object"}}}}},
             {"required", QJsonArray{"command", "args"}}}, true,
            [](const QJsonObject &args, CommandContext &ctx) {
                auto proposal = ctx; proposal.propose = true;
                const auto result = ctx.session.registry().call(args["command"].toString(), args["args"].toObject(), proposal);
                if (!result["ok"].toBool()) throw CommandError{result["error"].toString()};
                return result["result"].toObject();
            }});
    }
};

class Streams {
public:
    explicit Streams(const QByteArray &input = {}) : in(input.toStdString()),
        cinState(std::cin.rdstate()), coutState(std::cout.rdstate()), cerrState(std::cerr.rdstate()),
        cinBuffer(std::cin.rdbuf(in.rdbuf())), coutBuffer(std::cout.rdbuf(out.rdbuf())),
        cerrBuffer(std::cerr.rdbuf(err.rdbuf())) { std::cin.clear(); std::cout.clear(); std::cerr.clear(); }
    ~Streams() {
        std::cin.rdbuf(cinBuffer); std::cin.clear(cinState);
        std::cout.rdbuf(coutBuffer); std::cout.clear(coutState);
        std::cerr.rdbuf(cerrBuffer); std::cerr.clear(cerrState);
    }
    std::istringstream in;
    std::ostringstream out, err;
private:
    std::ios::iostate cinState, coutState, cerrState;
    std::streambuf *cinBuffer, *coutBuffer, *cerrBuffer;
};
struct Args {
    std::vector<QByteArray> storage;
    std::vector<char *> argv;
    explicit Args(const QStringList &args) {
        storage.reserve(size_t(args.size()));
        for (const auto &arg : args) storage.push_back(arg.toLocal8Bit());
        for (auto &arg : storage) argv.push_back(arg.data());
        argv.push_back(nullptr);
    }
    int count() const { return int(storage.size()); }
};
} // namespace

class McpTest : public QObject {
    Q_OBJECT
private slots:
    void initializeAndList() {
        McpRig r;
        const auto response = r.server.handle(req("init", "initialize"));
        QCOMPARE(response["jsonrpc"].toString(), QString("2.0"));
        QCOMPARE(response["id"].toString(), QString("init"));
        const auto init = response["result"].toObject();
        QCOMPARE(init["protocolVersion"].toString(), QString("2024-11-05"));
        QVERIFY(init["capabilities"].toObject()["tools"].isObject());
        QCOMPARE(init["serverInfo"].toObject()["name"].toString(), QString("gd-melee-workbench"));
        QCOMPARE(init["serverInfo"].toObject()["version"].toString(), QString("1"));
        const auto tools = r.server.handle(req(2, "tools/list"))["result"].toObject()["tools"].toArray();
        QCOMPARE(tools.size(), 9);
        QSet<QString> names;
        for (const auto &tool : tools) {
            const auto object = tool.toObject();
            names.insert(object["name"].toString());
            QVERIFY(!object["description"].toString().isEmpty());
            QCOMPARE(object["inputSchema"].toObject()["type"].toString(), QString("object"));
            if (object["name"] == "edit") {
                const auto schema = object["inputSchema"].toObject();
                QCOMPARE(schema["required"].toArray(), QJsonArray{"damage"});
                QCOMPARE(schema["properties"].toObject()["damage"].toObject()["type"].toString(), QString("number"));
            }
        }
        QCOMPARE(names, (QSet<QString>{"inspect", "edit", "fail", "throw", "accept", "reject", "undo", "redo", "propose"}));
    }
    void toolListReflectsLateRegistration() {
        McpRig r;
        r.session.registry().add({"later", "Added after server construction", {{"type", "object"}}, false,
            [](const QJsonObject &, CommandContext &) { return QJsonObject{}; }});
        const auto tools = r.server.handle(req(2, "tools/list"))["result"].toObject()["tools"].toArray();
        QCOMPARE(tools.last().toObject()["name"].toString(), QString("later"));
    }
    void emptyCommandSchemaIsAnObjectSchema() {
        McpRig r;
        r.session.registry().add({"no_args", "Command with no arguments", {}, false,
            [](const QJsonObject &, CommandContext &) { return QJsonObject{{"value", 7}}; }});
        const auto tools = r.server.handle(req(2, "tools/list"))["result"].toObject()["tools"].toArray();
        const auto schema = tools.last().toObject()["inputSchema"].toObject();
        QCOMPARE(schema["type"].toString(), QString("object"));
        QVERIFY(schema["properties"].isObject());
        QCOMPARE(payload(r.server.handle(call("no_args")))["value"].toInt(), 7);
    }
    void callEveryToolWithEmptyArgsNeverCrashes() {
        McpRig r;
        for (const auto &spec : r.session.registry().list()) {
            const auto response = r.server.handle(call(spec.name));
            QVERIFY2(response.contains("result") || response.contains("error"), qPrintable(spec.name));
            QVERIFY(r.server.handle(req(2, "ping")).contains("result"));
        }
    }
    void toolCallReturnsTextContentAndAgentAuthor() {
        McpRig r;
        const auto response = r.server.handle(call("inspect"));
        const auto result = response["result"].toObject();
        QVERIFY(!result["isError"].toBool(true));
        QCOMPARE(result["content"].toArray().size(), 1);
        QCOMPARE(result["content"].toArray()[0].toObject()["type"].toString(), QString("text"));
        QCOMPARE(payload(response)["rows"].toInt(), 2);
        QCOMPARE(payload(response)["author"].toString(), QString("agent"));
    }
    void handlerErrorsAreToolErrors() {
        McpRig r;
        for (const auto &name : {"fail", "throw"}) {
            const auto response = r.server.handle(call(name));
            QVERIFY(!response.contains("error"));
            QVERIFY(response["result"].toObject()["isError"].toBool());
            QVERIFY(payload(response)["error"].toString().contains("synthetic"));
            QVERIFY(r.server.handle(req(2, "ping")).contains("result"));
        }
    }
    void invalidCalls_data() {
        QTest::addColumn<QJsonObject>("request");
        QTest::addColumn<int>("code");
        QTest::newRow("unknown method") << req(1, "bogus/method") << -32601;
        QTest::newRow("unknown tool") << call("nope") << -32602;
        QTest::newRow("missing name") << req(1, "tools/call") << -32602;
        QTest::newRow("wrong name type") << req(1, "tools/call", {{"name", 3}}) << -32602;
        QTest::newRow("missing required field") << call("edit") << -32602;
        QTest::newRow("wrong field type") << call("edit", {{"damage", "bad"}}) << -32602;
        QTest::newRow("arguments array") << req(1, "tools/call", {{"name", "inspect"}, {"arguments", QJsonArray{}}}) << -32602;
        QTest::newRow("arguments null") << req(1, "tools/call", {{"name", "inspect"}, {"arguments", QJsonValue::Null}}) << -32602;
        auto arrayParams = req(1, "tools/call"); arrayParams["params"] = QJsonArray{};
        QTest::newRow("params array") << arrayParams << -32602;
        auto badVersion = req(1, "ping"); badVersion["jsonrpc"] = "1.0";
        QTest::newRow("version") << badVersion << -32600;
        auto badMethod = req(1, "ping"); badMethod["method"] = false;
        QTest::newRow("method type") << badMethod << -32600;
        QTest::newRow("id type") << req(true, "ping") << -32600;
    }
    void invalidCalls() {
        QFETCH(QJsonObject, request);
        QFETCH(int, code);
        McpRig r;
        const auto before = readFile(r.dir.filePath("moves/dair.genoasm"));
        const auto response = r.server.handle(request);
        QCOMPARE(response["error"].toObject()["code"].toInt(), code);
        QCOMPARE(response["jsonrpc"].toString(), QString("2.0"));
        QVERIFY(response.contains("id"));
        QVERIFY(!response.contains("result"));
        QVERIFY(r.session.history().entries().isEmpty());
        QCOMPARE(readFile(r.dir.filePath("moves/dair.genoasm")), before);
        QVERIFY(r.server.handle(req(2, "ping")).contains("result"));
    }
    void notificationsHaveNoResponse() {
        McpRig r;
        QVERIFY(r.server.handle({{"jsonrpc", "2.0"}, {"method", "notifications/initialized"}}).isEmpty());
        for (auto request : {call("inspect"), call("nope"), call("edit"), req(2, "bogus/method")}) {
            request.remove("id");
            QVERIFY(r.server.handle(request).isEmpty());
            QVERIFY(r.server.handleLine(line(request)).isEmpty());
        }
        auto edit = call("edit", {{"damage", 22}}); edit.remove("id");
        QVERIFY(r.server.handle(edit).isEmpty());
        QCOMPARE(r.session.history().entries().size(), 1);
        QCOMPARE(r.session.history().entries().last().state, QString("proposed"));
        const auto nullId = r.server.handle(req(QJsonValue::Null, "ping"));
        QVERIFY(nullId["id"].isNull());
        QVERIFY(nullId.contains("result"));
    }
    void malformedJsonLinesRecover() {
        McpRig r;
        for (const auto &bad : {QByteArray("{ nope"), QByteArray("{\"id\":1")}) {
            const auto response = QJsonDocument::fromJson(r.server.handleLine(bad)).object();
            QCOMPARE(response["error"].toObject()["code"].toInt(), -32700);
            QVERIFY(response["id"].isNull());
        }
        for (const auto &bad : {QByteArray("[]"), QByteArray("[{}]"), QByteArray("{}"),
                                QByteArray("null"), QByteArray("true"), QByteArray("42"), QByteArray("\"text\"")}) {
            const auto response = QJsonDocument::fromJson(r.server.handleLine(bad)).object();
            QCOMPARE(response["error"].toObject()["code"].toInt(), -32600);
            QVERIFY(response["id"].isNull());
        }
        QVERIFY(r.server.handleLine(" \r\n").isEmpty());
        const auto good = QJsonDocument::fromJson(r.server.handleLine(line(req("still-alive", "ping")))).object();
        QCOMPARE(good["id"].toString(), QString("still-alive"));
        QVERIFY(good["result"].isObject());
    }
    void editsStayProposalsEvenWithExplicitOptOut() {
        McpRig r;
        QVERIFY(r.session.agentProposals);
        const auto before = readFile(r.dir.filePath("moves/dair.genoasm"));
        for (const auto &args : {QJsonObject{{"damage", 21}}, QJsonObject{{"damage", 22}, {"propose", false}}}) {
            const auto response = r.server.handle(call("edit", args));
            QVERIFY(payload(response)["proposed"].toBool());
            QCOMPARE(readFile(r.dir.filePath("moves/dair.genoasm")), before);
            QCOMPARE(r.session.history().entries().last().author, QString("agent"));
            QCOMPARE(r.session.history().entries().last().state, QString("proposed"));
        }
        r.session.agentProposals = false; // A UI preference must not lower MCP policy.
        QVERIFY(payload(r.server.handle(call("edit", {{"damage", 23}, {"propose", false}})))["proposed"].toBool());
        QCOMPARE(readFile(r.dir.filePath("moves/dair.genoasm")), before);
        const auto history = History::load(r.session.historyPath());
        QCOMPARE(history.entries().size(), 3);
        QCOMPARE(history.entries().last().state, QString("proposed"));
    }
    void agentsCannotAcceptOrRejectEvenThroughPropose() {
        McpRig r;
        const auto before = readFile(r.dir.filePath("moves/dair.genoasm"));
        const int id = payload(r.server.handle(call("edit", {{"damage", 21}})))["entry"].toInt();
        for (const auto &name : {"accept", "reject"}) {
            const QJsonObject args{{"id", id}};
            auto nested = call("propose", {{"command", name}, {"args", args}});
            auto twice = call("propose", {{"command", "propose"}, {"args", nested["params"].toObject()["arguments"]}});
            for (const auto &request : {call(name, args), nested, twice}) {
                const auto response = r.server.handle(request);
                QVERIFY(response["result"].toObject()["isError"].toBool());
                QVERIFY(payload(response)["error"].toString().contains("human"));
                QCOMPARE(r.session.history().entries().last().state, QString("proposed"));
                QCOMPARE(readFile(r.dir.filePath("moves/dair.genoasm")), before);
            }
        }
        // Creating an MCP server must not prevent the separate human path.
        CommandContext human{r.session, "human"};
        QVERIFY(r.session.registry().call("accept", {{"id", id}}, human)["ok"].toBool());
        QVERIFY(readFile(r.dir.filePath("moves/dair.genoasm")) != before);
    }
    void humanServerAllowsUndo() {
        McpRig r;
        r.server.setAuthor("human");
        const auto edited = r.server.handle(call("edit", {{"damage", 21}}));
        QVERIFY(!edited["result"].toObject()["isError"].toBool());
        const auto undo = r.server.handle(call("undo"));
        QVERIFY(!payload(undo)["error"].toString().contains("human author"));
        QVERIFY(payload(undo)["applied"].toBool());
    }
    void agentServerStillRefusesUndo() {
        McpRig r;
        QCOMPARE(r.server.author(), QString("agent"));
        QVERIFY(payload(r.server.handle(call("undo")))["error"].toString().contains("human author"));
    }
    void humanServerAppliesEditDirectly() {
        McpRig r;
        r.server.setAuthor("human");
        const auto before = readFile(r.dir.filePath("moves/dair.genoasm"));
        const auto body = payload(r.server.handle(call("edit", {{"damage", 24}})));
        QVERIFY(!body["proposed"].toBool());
        QVERIFY(readFile(r.dir.filePath("moves/dair.genoasm")) != before);
        QCOMPARE(r.session.history().entries().last().author, QString("human"));
        QCOMPARE(r.session.history().entries().last().state, QString("applied"));
    }
    void agentsCannotApplyUndoOrRedo() {
        McpRig r;
        CommandContext human{r.session, "human"};
        QVERIFY(r.session.registry().call("edit", {{"damage", 21}}, human)["ok"].toBool());
        const auto edited = readFile(r.dir.filePath("moves/dair.genoasm"));
        const auto undo = r.server.handle(call("undo"));
        QVERIFY(payload(undo)["error"].toString().contains("human"));
        QCOMPARE(readFile(r.dir.filePath("moves/dair.genoasm")), edited);
        QVERIFY(r.session.registry().call("undo", {}, human)["ok"].toBool());
        const auto undone = readFile(r.dir.filePath("moves/dair.genoasm"));
        const auto redo = r.server.handle(call("propose", {{"command", "redo"}, {"args", QJsonObject{}}}));
        QVERIFY(payload(redo)["error"].toString().contains("human"));
        QCOMPARE(readFile(r.dir.filePath("moves/dair.genoasm")), undone);
    }
    void runStdioSkipsBlanksAndNotificationsAndRecovers() {
        McpRig r;
        Streams streams(QByteArray("\n \r\n{bad\n") + line({{"jsonrpc", "2.0"}, {"method", "notifications/initialized"}})
                        + line(call("inspect")) + line(req(9, "ping")).trimmed());
        QCOMPARE(r.server.runStdio(), 0);
        const auto output = QByteArray::fromStdString(streams.out.str());
        QVERIFY(output.endsWith('\n'));
        const auto replies = output.trimmed().split('\n');
        QCOMPARE(replies.size(), 3);
        QCOMPARE(QJsonDocument::fromJson(replies[0]).object()["error"].toObject()["code"].toInt(), -32700);
        QCOMPARE(payload(QJsonDocument::fromJson(replies[1]).object())["rows"].toInt(), 2);
        QCOMPARE(QJsonDocument::fromJson(replies[2]).object()["id"].toInt(), 9);
    }
    void localSocketRoundTripAndFraming() {
        McpRig r; QString error;
        QVERIFY2(r.server.listenLocal(0, &error), qPrintable(error));
        QTcpSocket first, second;
        first.connectToHost(QHostAddress::LocalHost, r.server.localPort());
        second.connectToHost(QHostAddress::LocalHost, r.server.localPort());
        QVERIFY(first.waitForConnected(2000));
        QVERIFY(second.waitForConnected(2000));
        QCOMPARE(first.peerAddress(), QHostAddress(QHostAddress::LocalHost));
        const auto request = line(req(20, "ping"));
        first.write(request.left(8)); first.flush();
        second.write(line(req(30, "ping"))); second.flush();
        QTRY_VERIFY_WITH_TIMEOUT(second.canReadLine(), 3000);
        QCOMPARE(QJsonDocument::fromJson(second.readLine()).object()["id"].toInt(), 30);
        QCOMPARE(first.bytesAvailable(), qint64(0));
        first.write(request.mid(8) + "\n{bad\n" + line({{"jsonrpc", "2.0"}, {"method", "notifications/initialized"}})
                    + line(req(21, "ping")));
        first.flush();
        QTRY_VERIFY_WITH_TIMEOUT(first.canReadLine(), 3000);
        QCOMPARE(QJsonDocument::fromJson(first.readLine()).object()["id"].toInt(), 20);
        QTRY_VERIFY_WITH_TIMEOUT(first.canReadLine(), 3000);
        QCOMPARE(QJsonDocument::fromJson(first.readLine()).object()["error"].toObject()["code"].toInt(), -32700);
        QTRY_VERIFY_WITH_TIMEOUT(first.canReadLine(), 3000);
        QCOMPARE(QJsonDocument::fromJson(first.readLine()).object()["id"].toInt(), 21);
    }
    void reentrantToolCallIsRefused() {
        McpRig r;
        r.session.registry().add({"nested", "Pump another tool call", {{"type", "object"}}, false,
            [&r](const QJsonObject &, CommandContext &) { return r.server.handle(call("edit", {{"damage", 25}})); }});
        const auto nested = payload(r.server.handle(call("nested")));
        QVERIFY(nested.contains("error"));
        QVERIFY(r.session.history().entries().isEmpty());
        QVERIFY(payload(r.server.handle(call("edit", {{"damage", 25}})))["proposed"].toBool());
    }
    void cliModeSelectionPreservesExistingValues() {
        for (const QString &flag : {QString("--mcp"), QString("--wb-call")}) {
            Args direct({"launcher", flag}); QVERIFY(isWorkbenchCli(direct.count(), direct.argv.data()));
            Args afterValue({"launcher", "--project", "synth", flag}); QVERIFY(isWorkbenchCli(afterValue.count(), afterValue.argv.data()));
            for (const QString &old : {"--app-dir", "--data-dir", "--lang", "--add-iso", "--probe", "--enable-mod", "--disable-mod", "--shots"}) {
                Args value({"launcher", old, flag}); QVERIFY(!isWorkbenchCli(value.count(), value.argv.data()));
            }
            Args positional({"launcher", "--", flag}); QVERIFY(!isWorkbenchCli(positional.count(), positional.argv.data()));
        }
    }
    void cliRejectsMalformedArgumentsWithFailureEnvelope_data() {
        QTest::addColumn<QStringList>("options");
        QTest::newRow("missing call args") << QStringList{"--wb-call", "nope"};
        QTest::newRow("bad json") << QStringList{"--wb-call", "nope", "{bad"};
        QTest::newRow("array args") << QStringList{"--wb-call", "nope", "[]"};
        QTest::newRow("null args") << QStringList{"--wb-call", "nope", "null"};
        QTest::newRow("unknown tool") << QStringList{"--wb-call", "__unregistered_synthetic_command__", "{}"};
        QTest::newRow("port zero") << QStringList{"--wb-call", "nope", "{}", "--engine-port", "0"};
        QTest::newRow("port too large") << QStringList{"--wb-call", "nope", "{}", "--engine-port", "65536"};
        QTest::newRow("port not numeric") << QStringList{"--wb-call", "nope", "{}", "--engine-port", "x"};
        QTest::newRow("port and exe") << QStringList{"--wb-call", "nope", "{}", "--engine-port", "1234", "--engine-exe", "fake"};
        QTest::newRow("both modes") << QStringList{"--wb-call", "nope", "{}", "--mcp"};
        QTest::newRow("missing project") << QStringList{"--wb-call", "nope", "{}", "--project"};
    }
    void cliRejectsMalformedArgumentsWithFailureEnvelope() {
        QFETCH(QStringList, options);
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path());
        Args args(QStringList{"launcher", "--project", dir.path()} + options);
        Streams streams;
        QCOMPARE(runWorkbenchCli(args.count(), args.argv.data()), 1);
        QJsonParseError error;
        const auto response = QJsonDocument::fromJson(QByteArray::fromStdString(streams.out.str()), &error).object();
        QCOMPARE(error.error, QJsonParseError::NoError);
        QVERIFY(!response["ok"].toBool(true));
        QVERIFY(!response["error"].toString().isEmpty());
    }
    void cliMcpCanListWithoutProject() {
        QTemporaryDir dir;
        Args args({"launcher", "--mcp", "--project", dir.filePath("not-a-project")});
        Streams streams(line(req(1, "initialize")) + line(req(2, "tools/list")));
        QCOMPARE(runWorkbenchCli(args.count(), args.argv.data()), 0);
        const auto replies = QByteArray::fromStdString(streams.out.str()).trimmed().split('\n');
        QCOMPARE(replies.size(), 2);
        QVERIFY(QJsonDocument::fromJson(replies[0]).object()["result"].toObject().contains("protocolVersion"));
        QVERIFY(QJsonDocument::fromJson(replies[1]).object()["result"].toObject()["tools"].isArray());
    }
    void invalidMcpOptionsKeepStdoutClean_data() {
        QTest::addColumn<QStringList>("options");
        QTest::newRow("invalid port") << QStringList{"--mcp", "--engine-port", "bad"};
        QTest::newRow("flag-like project on parse error") << QStringList{"--mcp", "--project", "--wb-call", "--unknown"};
    }
    void invalidMcpOptionsKeepStdoutClean() {
        QFETCH(QStringList, options);
        Args args(QStringList{"launcher"} + options);
        Streams streams;
        QCOMPARE(runWorkbenchCli(args.count(), args.argv.data()), 1);
        QVERIFY(streams.out.str().empty());
        QVERIFY(!streams.err.str().empty());
    }
};
QTEST_GUILESS_MAIN(McpTest)
#include "mcp_test.moc"
