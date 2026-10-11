#pragma once
#include <QTcpServer>
#include <QTcpSocket>
#include <QTimer>
#include <QUrl>

inline QByteArray updateFixture() {
    return R"({"schema":1,"channel":"stable","version":"0.3.0","released":"2026-10-11",
      "netplay_protocol":7,"min_launcher_for_self_update":"0.3.0",
      "notes_url":"https://github.com/GurekamDhillon/gd-melee-workspace/releases/tag/v0.3.0",
      "notes_short":{"en":"An update.","es":"Una actualización."},"critical":false,
      "package":{"url":"https://github.com/GurekamDhillon/gd-melee-workspace/releases/download/v0.3.0/GDMelee-0.3.0-win64.zip",
        "size":1234,"sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},
      "files_manifest_sha256":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"})";
}

// Test-only real HTTP server, with stalls, trickle responses and redirects.
class HttpFixture : public QTcpServer {
public:
    QByteArray response = updateFixture(), request, extraHeaders;
    int count = 0, code = 200;
    bool stall = false, trickle = false;
    HttpFixture() {
        listen(QHostAddress::LocalHost);
        connect(this, &QTcpServer::newConnection, this, [this] {
            while (hasPendingConnections()) {
                auto *socket = nextPendingConnection();
                connect(socket, &QTcpSocket::disconnected, socket, &QObject::deleteLater);
                connect(socket, &QTcpSocket::readyRead, socket, [this, socket] {
                    auto bytes = socket->property("request").toByteArray() + socket->readAll();
                    socket->setProperty("request", bytes);
                    if (!bytes.contains("\r\n\r\n") || socket->property("answered").toBool()) return;
                    socket->setProperty("answered", true); request = bytes; ++count;
                    if (stall) return;
                    socket->write("HTTP/1.1 " + QByteArray::number(code) + " Test\r\nContent-Type: application/json\r\nContent-Length: " + QByteArray::number(response.size()) + "\r\nConnection: close\r\n" + extraHeaders + "\r\n");
                    if (trickle) {
                        socket->write(response.left(1));
                        auto *timer = new QTimer(socket);
                        connect(timer, &QTimer::timeout, socket, [socket] { socket->write(" "); });
                        timer->start(10); return;
                    }
                    socket->write(response); socket->disconnectFromHost();
                });
            }
        });
    }
    QUrl url() const { return QUrl("http://127.0.0.1:" + QString::number(serverPort()) + "/update.json"); }
};
