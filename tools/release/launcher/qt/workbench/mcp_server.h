#pragma once
#include <QByteArray>
#include <QJsonObject>
#include <QTcpServer>

namespace wb {
class Session;
struct CommandSpec;

// All calls use the agent author and proposal policy, including the UI socket.
// The session must outlive the server. Use both on their owning Qt thread.
class McpServer {
public:
    explicit McpServer(Session &session);
    McpServer(const McpServer &) = delete;
    McpServer &operator=(const McpServer &) = delete;
    QJsonObject handle(const QJsonObject &request);
    QByteArray handleLine(const QByteArray &line);
    int runStdio();
    bool listenLocal(quint16 port, QString *err);
    quint16 localPort() const;
    static QJsonObject toolSchema(const CommandSpec &spec);

private:
    Session &session_;
    QTcpServer server_;
    bool calling_ = false;
};
} // namespace wb
