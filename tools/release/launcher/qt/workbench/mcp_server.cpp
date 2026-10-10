#include "mcp_server.h"
#include "command_registry.h"
#include "session.h"
#include <QHostAddress>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonParseError>
#include <QPointer>
#include <QScopedValueRollback>
#include <QTcpSocket>
#include <iostream>
#include <memory>
#include <string>

namespace wb {
namespace {
QJsonObject rpcError(const QJsonValue &id, int code, const QString &message) {
    return {{"jsonrpc", "2.0"}, {"id", id},
            {"error", QJsonObject{{"code", code}, {"message", message}}}};
}
QJsonObject toolResult(const QJsonObject &envelope) {
    const bool ok = envelope.value("ok").toBool();
    const auto body = ok ? envelope.value("result").toObject()
                         : QJsonObject{{"error", envelope.value("error")}};
    return {{"content", QJsonArray{QJsonObject{
                {"type", "text"}, {"text", QString::fromUtf8(QJsonDocument(body).toJson(QJsonDocument::Compact))}}}},
            {"isError", !ok}};
}
QString humanOnlyCommand(QString name, QJsonObject args) {
    // The propose command dispatches another registry handler. Checking only the
    // outer name would allow an agent to accept its own proposal through it.
    while (name == "propose") {
        name = args.value("command").toString();
        args = args.value("args").toObject();
    }
    // History operations write source directly, outside Session::commit's
    // proposal path. Keep them listed, but reserve execution for the human CLI/UI.
    if (name == "accept" || name == "reject" || name == "undo" || name == "redo") return name;
    return {};
}
} // namespace

McpServer::McpServer(Session &session) : session_(session) {
    session_.agentProposals = true;
    QObject::connect(&server_, &QTcpServer::newConnection, &server_, [this] {
        while (server_.hasPendingConnections()) {
            QTcpSocket *socket = server_.nextPendingConnection();
            const QPointer<QTcpSocket> client(socket);
            auto draining = std::make_shared<bool>(false);
            auto drain = [this, client, draining] {
                if (*draining) return;
                QScopedValueRollback<bool> guard(*draining, true);
                // QTcpSocket retains partial lines, independently per client.
                // A command may pump events; the guard defers that client's next
                // request, and QPointer tolerates disconnection during the call.
                while (client && client->canReadLine()) {
                    const QByteArray reply = handleLine(client->readLine());
                    if (!reply.isEmpty() && client && client->state() == QAbstractSocket::ConnectedState)
                        client->write(reply + '\n');
                }
            };
            QObject::connect(socket, &QTcpSocket::readyRead, socket, drain);
            QObject::connect(socket, &QTcpSocket::disconnected, socket, &QObject::deleteLater);
            drain();
        }
    });
}

void McpServer::setAuthor(const QString &author) {
    author_ = author == "human" ? "human" : "agent";
    propose_ = author_ == "agent";
    session_.agentProposals = propose_;
}

QJsonObject McpServer::toolSchema(const CommandSpec &spec) {
    auto schema = spec.inputSchema;
    // Registry arguments are always objects, including no-argument commands.
    schema["type"] = "object";
    if (!schema.contains("properties")) schema["properties"] = QJsonObject{};
    return {{"name", spec.name}, {"description", spec.description}, {"inputSchema", schema}};
}

QJsonObject McpServer::handle(const QJsonObject &request) {
    const auto id = request.value("id");
    const bool validId = id.isUndefined() || id.isNull() || id.isString() || id.isDouble();
    const auto methodValue = request.value("method");
    if (request.value("jsonrpc") != QJsonValue("2.0") || !methodValue.isString() ||
        methodValue.toString().isEmpty() || !validId)
        return rpcError(QJsonValue::Null, -32600, "Invalid Request");

    const bool notification = !request.contains("id");
    auto error = [&](int code, const QString &message) {
        return notification ? QJsonObject{} : rpcError(id, code, message);
    };
    auto result = [&](const QJsonObject &body) {
        return notification ? QJsonObject{} : QJsonObject{{"jsonrpc", "2.0"}, {"id", id}, {"result", body}};
    };
    if (request.contains("params") && !request.value("params").isObject())
        return error(-32602, "params must be an object");
    const QString method = methodValue.toString();
    const auto params = request.value("params").toObject();
    if (method == "initialize")
        return result({{"protocolVersion", "2024-11-05"},
                       {"capabilities", QJsonObject{{"tools", QJsonObject{}}}},
                       {"serverInfo", QJsonObject{{"name", "gd-melee-workbench"}, {"version", "1"}}}});
    if (method == "ping" || (method == "notifications/initialized" && notification)) return result({});
    if (method == "tools/list") {
        QJsonArray tools;
        for (const auto &spec : session_.registry().list()) tools.append(toolSchema(spec));
        return result({{"tools", tools}});
    }
    if (method != "tools/call") return error(-32601, "Method not found: " + method);
    if (!params.value("name").isString() || params.value("name").toString().isEmpty())
        return error(-32602, "name must be a nonempty string");
    if (params.contains("arguments") && !params.value("arguments").isObject())
        return error(-32602, "arguments must be an object");
    const QString name = params.value("name").toString();
    const auto args = params.value("arguments").toObject();
    bool found = false;
    for (const auto &spec : session_.registry().list()) {
        if (spec.name != name) continue;
        found = true;
        const QString invalid = CommandRegistry::validate(spec.inputSchema, args);
        if (!invalid.isEmpty()) return error(-32602, invalid);
        break;
    }
    if (!found) return error(-32602, "Unknown tool: " + name);
    const QString humanOnly = humanOnlyCommand(name, args);
    if (!humanOnly.isEmpty() && author_ == "agent")
        return result(toolResult({{"ok", false}, {"error", humanOnly + ": requires a human author"}}));
    if (calling_) return error(-32000, "A tool call is already in progress");
    QScopedValueRollback<bool> guard(calling_, true);
    // Do not trust the caller's propose:false, or a UI change to session policy.
    session_.agentProposals = propose_;
    CommandContext context{session_, author_, propose_};
    return result(toolResult(runner_ ? runner_(name, args, context) : session_.registry().call(name, args, context)));
}

QByteArray McpServer::handleLine(const QByteArray &line) {
    if (line.trimmed().isEmpty()) return {};
    QJsonParseError parse;
    const auto document = QJsonDocument::fromJson(line, &parse);
    QJsonObject reply;
    if (parse.error != QJsonParseError::NoError) {
        // QJsonDocument only accepts top-level objects/arrays. A JSON scalar is
        // syntactically valid JSON, but not a JSON-RPC request (Invalid Request).
        QJsonParseError scalarError;
        const auto scalar = QJsonDocument::fromJson(QByteArray("[") + line + ']', &scalarError);
        if (scalarError.error == QJsonParseError::NoError && scalar.isArray() && scalar.array().size() == 1)
            reply = rpcError(QJsonValue::Null, -32600, "Invalid Request: expected an object");
        else
            reply = rpcError(QJsonValue::Null, -32700, "Parse error: " + parse.errorString());
    } else if (!document.isObject())
        reply = rpcError(QJsonValue::Null, -32600, "Invalid Request: expected an object");
    else
        reply = handle(document.object());
    return reply.isEmpty() ? QByteArray{} : QJsonDocument(reply).toJson(QJsonDocument::Compact);
}

int McpServer::runStdio() {
    std::string line;
    while (std::getline(std::cin, line)) {
        const QByteArray reply = handleLine(QByteArray::fromStdString(line));
        if (reply.isEmpty()) continue;
        std::cout << reply.constData() << '\n' << std::flush;
        if (!std::cout) return 1;
    }
    return std::cin.bad() ? 1 : 0;
}

bool McpServer::listenLocal(quint16 port, QString *err) {
    if (err) err->clear();
    if (server_.isListening()) {
        if (err) *err = "MCP listener is already running";
        return false;
    }
    if (server_.listen(QHostAddress::LocalHost, port)) return true;
    if (err) *err = server_.errorString();
    return false;
}
quint16 McpServer::localPort() const { return server_.serverPort(); }
} // namespace wb
