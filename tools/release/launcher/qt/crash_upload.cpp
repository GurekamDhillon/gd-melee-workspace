#include "crash_upload.h"
#include "launcher_core.h"
#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QTcpSocket>
#include <QUrl>

namespace launcher {
static const char kMagic[] = "==== GD's Melee crash report ====";

QString crashServer(const QString &appDir) {
    QFile f(appDir + "/netplay_server.txt"); if (!f.open(QIODevice::ReadOnly)) return {};
    for (const auto &raw : f.readAll().split('\n')) {
        auto line = QString::fromUtf8(raw).trimmed();
        if (!line.isEmpty() && !line.startsWith('#')) return line;
    }
    return {};
}

QStringList uploadableCrashes(const QString &runDir, int count) {
    QStringList out;
    auto files = QDir(runDir + "/crashlogs").entryInfoList({"crash-*.log"}, QDir::Files, QDir::Time);   // newest first
    for (const auto &f : files) {
        if (out.size() >= count) break;
        if (f.fileName().endsWith("-full.log", Qt::CaseInsensitive) || f.size() > kCrashUploadMax) continue;
        QFile report(f.filePath()); if (!report.open(QIODevice::ReadOnly)) continue;
        auto head = report.read(2048);
        if (head.startsWith(kMagic) && !head.contains("during shutdown: yes")) out << f.filePath();
    }
    return out;
}

QString scrubCrashReport(QString text, const QString &profile, const QString &user) {
    if (profile.size() > 3) {
        text.replace(profile, "%USERPROFILE%", Qt::CaseInsensitive);
        auto slashes = profile; slashes.replace('\\', '/');
        text.replace(slashes, "%USERPROFILE%", Qt::CaseInsensitive);
    }
    if (user.size() >= 3) text.replace(user, "<user>", Qt::CaseInsensitive);
    return text;
}
QString crashUserName() {
    auto name = qEnvironmentVariable("USERNAME"); if (name.isEmpty()) name = qEnvironmentVariable("USER");
    return name;
}

namespace {
struct Reply { bool ok = false; bool cancelled = false; int status = 0; QString answer, error; };
// Waits in 200 ms slices so a cancel is noticed; true when `step` succeeded (or the socket closed) within timeoutMs.
template <class Step> bool waitSliced(QTcpSocket &socket, Step step, int timeoutMs, const std::atomic<bool> *cancel, bool &cancelled) {
    for (int waited = 0; waited < timeoutMs; waited += 200) {
        if (cancel && cancel->load()) { cancelled = true; return false; }
        if (step(200)) return true;
        if (socket.state() == QAbstractSocket::UnconnectedState) return true;
    }
    return false;
}
// One POST /crash. Plain HTTP/1.1 with Connection: close, as crash_upload_server.py speaks it.
Reply post(const QString &server, const QByteArray &body, const QString &version, int timeoutMs, const std::atomic<bool> *cancel) {
    Reply r; QUrl url("http://" + server + "/crash");
    if (!url.isValid() || url.host().isEmpty()) { r.error = "bad server address " + server; return r; }
    const int port = url.port(80);
    QTcpSocket socket; socket.connectToHost(url.host(), quint16(port));
    auto fail = [&](const QString &why) { r.error = why; return r; };
    if (!waitSliced(socket, [&](int ms) { return socket.waitForConnected(ms); }, timeoutMs, cancel, r.cancelled) || socket.state() != QAbstractSocket::ConnectedState)
        return r.cancelled ? r : fail(socket.error() == QAbstractSocket::UnknownSocketError ? "connection timed out" : socket.errorString());
    QByteArray request = "POST /crash HTTP/1.1\r\nHost: " + url.host().toUtf8() + ":" + QByteArray::number(port) +
        "\r\nUser-Agent: GDMeleeLauncher/" + version.toUtf8() + "\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: " +
        QByteArray::number(body.size()) + "\r\nConnection: close\r\n\r\n" + body;
    socket.write(request);
    while (socket.bytesToWrite() > 0)
        if (!waitSliced(socket, [&](int ms) { return socket.waitForBytesWritten(ms); }, timeoutMs, cancel, r.cancelled)) return r.cancelled ? r : fail(socket.errorString());
    QByteArray response;
    for (;;) {
        // The reply is small; stop once the header and the declared body have arrived, or the server closes.
        const int split = response.indexOf("\r\n\r\n");
        if (split >= 0) {
            const int at = response.toLower().indexOf("content-length:");
            if (at >= 0 && at < split) {
                const int length = response.mid(at + 15, response.indexOf("\r\n", at) - at - 15).trimmed().toInt();
                if (response.size() >= split + 4 + length) break;
            }
        }
        if (response.size() > 64 * 1024) break;
        if (socket.state() != QAbstractSocket::ConnectedState && socket.bytesAvailable() == 0) break;
        if (socket.bytesAvailable() == 0 && !waitSliced(socket, [&](int ms) { return socket.waitForReadyRead(ms); }, timeoutMs, cancel, r.cancelled))
            return r.cancelled ? r : fail(socket.error() == QAbstractSocket::UnknownSocketError ? "the server did not answer in time" : socket.errorString());
        response += socket.readAll();
    }
    response += socket.readAll();
    const int split = response.indexOf("\r\n\r\n");
    const auto statusLine = QString::fromLatin1(response.left(response.indexOf("\r\n"))).split(' ', Qt::SkipEmptyParts);
    if (statusLine.size() < 2 || !statusLine[0].startsWith("HTTP/") || split < 0) return fail("the server did not answer with HTTP");
    r.status = statusLine[1].toInt(); r.answer = QString::fromUtf8(response.mid(split + 4)).trimmed(); r.ok = r.status == 200;
    return r;
}
}

CrashUploadResult uploadCrashReports(const QString &server, const QStringList &files, const QString &version,
                                     const QString &profile, const QString &user, int timeoutMs, const std::atomic<bool> *cancel) {
    CrashUploadResult result; result.server = server; result.total = int(files.size());
    if (files.isEmpty()) { result.failure = CrashUploadResult::NoReports; return result; }
    if (server.isEmpty()) { result.failure = CrashUploadResult::NoServer; return result; }
    for (const auto &path : files) {
        QFile f(path);
        if (!f.open(QIODevice::ReadOnly)) { result.failure = CrashUploadResult::Network; result.detail = f.errorString(); return result; }
        const auto body = scrubCrashReport(QString::fromUtf8(f.readAll()), profile, user).toUtf8();
        f.close();
        if (body.size() > kCrashUploadMax) { result.failure = CrashUploadResult::TooLarge; return result; }
        const auto reply = post(server, body, version, timeoutMs, cancel);
        if (reply.cancelled) { result.failure = CrashUploadResult::Cancelled; return result; }
        if (!reply.ok && reply.status == 0) { result.failure = CrashUploadResult::Network; result.detail = reply.error; return result; }
        if (!reply.ok) {
            if (reply.status == 400) { QFile marker(path + ".sent"); if (marker.open(QIODevice::WriteOnly)) marker.write("refused by the server (400)\n"); }
            result.failure = CrashUploadResult::ServerRefused; result.status = reply.status; result.detail = reply.answer; return result;
        }
        QFile marker(path + ".sent");
        if (marker.open(QIODevice::WriteOnly)) marker.write((QDateTime::currentDateTime().toString(Qt::ISODate) + " " + server + " " + reply.answer + "\n").toUtf8());
        ++result.sent;
    }
    return result;
}
}
