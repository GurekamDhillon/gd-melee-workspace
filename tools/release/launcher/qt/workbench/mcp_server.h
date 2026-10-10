#pragma once
#include <QByteArray>
#include <QJsonObject>
#include <QString>
#include <QTcpServer>

namespace wb {
class Session;
struct CommandSpec;

// Default author "agent": every call is a proposal and history operations are refused. setAuthor("human")
// (the Blender add-on / hub socket, --serve) applies edits directly and allows undo/redo/accept/reject.
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
    void setAuthor(const QString &author);
    QString author() const { return author_; }
    static QJsonObject toolSchema(const CommandSpec &spec);

private:
    Session &session_;
    QTcpServer server_;
    bool calling_ = false;
    QString author_ = "agent";
    bool propose_ = true;
};
} // namespace wb
