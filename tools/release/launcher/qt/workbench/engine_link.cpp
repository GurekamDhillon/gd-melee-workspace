#include "engine_link.h"

#include <QCoreApplication>
#include <QDir>
#include <QEventLoop>
#include <QFile>
#include <QFileInfo>
#include <QHostAddress>
#include <QJsonArray>
#include <QJsonDocument>
#include <QRegularExpression>
#include <QScopedValueRollback>
#include <QTcpServer>
#include <QTimer>
#include <algorithm>
#include <cmath>
#include <utility>

namespace wb {
namespace {
constexpr int kConsoleReplyLimit = 16 * 1024;
constexpr qint64 kPayloadLimit = 32 * 1024 * 1024;
const QString kConnectionLost = QStringLiteral("engine connection lost");

void setError(QString *err, const QString &text) {
    if (err) *err = text;
}
int remaining(const QElapsedTimer &timer, int timeoutMs) {
    return int(std::max<qint64>(0, qint64(timeoutMs) - timer.elapsed()));
}
void pumpFor(int ms) {
    if (ms <= 0) return;
    QEventLoop loop;
    QTimer::singleShot(ms, &loop, &QEventLoop::quit);
    loop.exec(QEventLoop::AllEvents);
}
Vec3 readVec(const QJsonValue &v) {
    const auto o = v.toObject();
    return {o["x"].toDouble(), o["y"].toDouble(), o["z"].toDouble()};
}
QJsonObject vecJson(const Vec3 &v) {
    return {{"x", v.x}, {"y", v.y}, {"z", v.z}};
}
QJsonObject ecbJson(const Vec3 &v) {
    // The game's ECB is 2D; there is deliberately no z key on the wire.
    return {{"x", v.x}, {"y", v.y}};
}
QString quoted(const QString &s) {
    QString out = "\"";
    for (QChar c : s) {
        switch (c.unicode()) {
        case '\\': out += "\\\\"; break;
        case '"': out += "\\\""; break;
        case '\n': out += "\\n"; break;
        case '\r': out += "\\r"; break;
        default:
            if (c.unicode() < 32 || c.unicode() == 127)
                out += '\\' + QString::number(c.unicode()).rightJustified(3, '0');
            else out += c;
        }
    }
    return out + '"';
}
QJsonObject parseObject(const QByteArray &bytes, QString *err) {
    QJsonParseError parse;
    const auto doc = QJsonDocument::fromJson(bytes, &parse);
    if (parse.error != QJsonParseError::NoError) {
        setError(err, "invalid engine JSON: " + parse.errorString());
        return {};
    }
    if (!doc.isObject()) {
        setError(err, "engine JSON must be an object");
        return {};
    }
    return doc.object();
}
}

FrameInfo FrameInfo::fromJson(const QJsonObject &o) {
    FrameInfo f;
    f.row = o["row"].toString();
    f.motion = o["motion"].toInt();
    f.frame = o["frame"].toInt();
    for (const auto &v : o["bones"].toArray()) {
        const auto b = v.toObject();
        f.bones.append({b["joint"].toInt(), b["parent"].toInt(-1), readVec(b["pos"])});
    }
    for (const auto &v : o["hitboxes"].toArray()) {
        const auto h = v.toObject();
        f.hitboxes.append({h["slot"].toInt(), h["joint"].toInt(), readVec(h["offset"]),
                          h["radius"].toDouble(), readVec(h["world"]), h["active"].toBool()});
    }
    for (const auto &v : o["hurtboxes"].toArray()) {
        const auto h = v.toObject();
        f.hurtboxes.append({h["joint"].toInt(), readVec(h["a"]), readVec(h["b"]),
                           h["radius"].toDouble()});
    }
    const auto ecb = o["ecb"].toObject();
    f.ecbBottom = readVec(ecb["bottom"]);
    f.ecbTop = readVec(ecb["top"]);
    f.floorY = o["floorY"].toDouble();
    f.lowestY = o["lowestY"].toDouble();
    return f;
}

QJsonObject FrameInfo::toJson() const {
    QJsonArray bs, hs, hurts;
    for (const auto &b : bones)
        bs.append(QJsonObject{{"joint", b.joint}, {"parent", b.parent}, {"pos", vecJson(b.pos)}});
    for (const auto &h : hitboxes)
        hs.append(QJsonObject{{"slot", h.slot}, {"joint", h.joint}, {"offset", vecJson(h.offset)},
                              {"radius", h.radius}, {"world", vecJson(h.world)}, {"active", h.active}});
    for (const auto &h : hurtboxes)
        hurts.append(QJsonObject{{"joint", h.joint}, {"a", vecJson(h.a)}, {"b", vecJson(h.b)},
                                 {"radius", h.radius}});
    return {{"row", row}, {"motion", motion}, {"frame", frame}, {"bones", bs},
            {"hitboxes", hs}, {"hurtboxes", hurts},
            {"ecb", QJsonObject{{"bottom", ecbJson(ecbBottom)}, {"top", ecbJson(ecbTop)}}},
            {"floorY", floorY}, {"lowestY", lowestY}};
}

QString luaLiteral(const QJsonValue &v) {
    switch (v.type()) {
    case QJsonValue::Bool: return v.toBool() ? "true" : "false";
    case QJsonValue::Double:
        return std::isfinite(v.toDouble()) ? QString::number(v.toDouble(), 'g', 17) : QString("nil");
    case QJsonValue::String: return quoted(v.toString());
    case QJsonValue::Array: {
        QStringList parts;
        for (const auto &item : v.toArray()) parts.append(luaLiteral(item));
        return '{' + parts.join(',') + '}';
    }
    case QJsonValue::Object: {
        QStringList parts;
        const auto o = v.toObject();
        for (auto it = o.begin(); it != o.end(); ++it)
            parts.append('[' + quoted(it.key()) + "]=" + luaLiteral(it.value()));
        return '{' + parts.join(',') + '}';
    }
    default: return "nil";
    }
}

bool ConsoleClient::connected() const {
    return socket_.state() == QAbstractSocket::ConnectedState;
}
QString ConsoleClient::banner() const { return banner_; }
void ConsoleClient::close() {
    socket_.abort();
    buffer_.clear();
    banner_.clear();
}

bool ConsoleClient::readLine(QByteArray *line, const QElapsedTimer &timer,
                             int timeoutMs, QString *err) {
    for (;;) {
        buffer_ += socket_.readAll();
        if (buffer_.size() > kConsoleReplyLimit) {
            setError(err, "console reply too large");
            return false;
        }
        const auto nl = buffer_.indexOf('\n');
        if (nl >= 0) {
            *line = buffer_.left(nl);
            buffer_.remove(0, nl + 1);
            if (line->endsWith('\r')) line->chop(1);
            return true;
        }
        if (!connected()) {
            setError(err, kConnectionLost);
            return false;
        }
        const int left = remaining(timer, timeoutMs);
        if (!left) {
            setError(err, "timeout");
            return false;
        }
        socket_.waitForReadyRead(std::min(10, left));
        QCoreApplication::processEvents(QEventLoop::AllEvents, 1);
    }
}

bool ConsoleClient::connectTo(quint16 port, int timeoutMs, QString *err) {
    setError(err, {});
    if (busy_) { setError(err, "console operation already in progress"); return false; }
    QScopedValueRollback<bool> guard(busy_, true);
    close();
    if (!port) { setError(err, "invalid console port"); return false; }
    QElapsedTimer timer; timer.start();
    socket_.connectToHost(QHostAddress::LocalHost, port);
    while (!connected()) {
        if (socket_.state() == QAbstractSocket::UnconnectedState) {
            setError(err, socket_.errorString()); close(); return false;
        }
        const int left = remaining(timer, timeoutMs);
        if (!left) { setError(err, "timeout"); close(); return false; }
        pumpFor(std::min(10, left));
    }
    QByteArray line;
    if (!readLine(&line, timer, timeoutMs, err)) { close(); return false; }
    if (line != "GD's Melee console (scripting API 1)") {
        setError(err, "unexpected console banner: " + QString::fromUtf8(line));
        close(); return false;
    }
    banner_ = QString::fromUtf8(line);
    return true;
}

ConsoleReply ConsoleClient::call(const QString &line, int timeoutMs) {
    if (busy_) return {false, "console operation already in progress"};
    QScopedValueRollback<bool> guard(busy_, true);
    if (!connected()) return {false, kConnectionLost};
    const auto bytes = line.toUtf8();
    if (bytes.size() > 4095) return {false, "console command exceeds 4095 bytes"};
    if (bytes.contains('\n') || bytes.contains('\r') || bytes.contains('\0'))
        return {false, "console command must be a single line without NUL bytes"};
    QElapsedTimer timer; timer.start();
    if (socket_.write(bytes + '\n') != bytes.size() + 1) {
        close(); return {false, kConnectionLost};
    }
    socket_.flush();
    QStringList output;
    qsizetype total = 0;
    for (;;) {
        QByteArray received; QString err;
        if (!readLine(&received, timer, timeoutMs, &err)) {
            // There are no request ids: abandoning a response invalidates the stream.
            close(); return {false, err};
        }
        if (received == ">>> ok" || received == ">>> error")
            return {received == ">>> ok", output.join('\n')};
        total += received.size() + 1;
        if (total > kConsoleReplyLimit) {
            close(); return {false, "console reply too large"};
        }
        output.append(QString::fromUtf8(received));
    }
}

EngineLink::EngineLink(Launch l) : launch_(std::move(l)) {
    process_.setProcessChannelMode(QProcess::MergedChannels);
    // Do not retain an unbounded game log in QProcess's pipe buffers.
    QObject::connect(&process_, &QProcess::readyReadStandardOutput, &process_,
                     [this] { process_.readAllStandardOutput(); });
}
EngineLink::~EngineLink() { stop(); }

void EngineLink::setTimeoutMs(int timeoutMs) { timeoutMs_ = std::max(1, timeoutMs); }

void EngineLink::stop() {
    ++stopGeneration_;
    console_.close();
    if (ownsProcess_ && process_.state() != QProcess::NotRunning) {
        process_.terminate();
        if (!process_.waitForFinished(3000)) {
            process_.kill();
            process_.waitForFinished(3000);
        }
    }
    ownsProcess_ = false;
    state_ = "stopped";
}

QString EngineLink::status() {
    if (state_ == "ready" && (!console_.connected() ||
            (ownsProcess_ && process_.state() == QProcess::NotRunning)))
        state_ = "error: " + kConnectionLost;
    return state_;
}

bool EngineLink::attach(quint16 port, QString *err) {
    setError(err, {});
    if (busy_) { setError(err, "engine operation already in progress"); return false; }
    QScopedValueRollback<bool> guard(busy_, true);
    stop();
    state_ = "starting";
    const auto generation = stopGeneration_;
    QString error;
    if (!console_.connectTo(port, timeoutMs_, &error) || generation != stopGeneration_) {
        if (generation != stopGeneration_) error = "engine start cancelled";
        else state_ = "error: " + error;
        console_.close(); setError(err, error); return false;
    }
    state_ = "ready";
    return true;
}

QProcessEnvironment EngineLink::buildEnvironment(int port) const {
    auto env = launch_.env.isEmpty() ? QProcessEnvironment::systemEnvironment() : launch_.env;
    env.insert("MELEE_CONSOLE_PORT", QString::number(port));
    env.insert("MELEE_SCENE", "mode=workbench;p1=geno:" + launch_.modId + "/hu;stage=fd");
    env.insert("MELEE_MODS_DIR", launch_.modsDir);
    env.insert("MELEE_WB_DIR", launch_.wbDir);
    env.insert("MELEE_WINDOW_X", "100");
    env.insert("MELEE_WINDOW_Y", "80");
    env.remove("MELEE_NETPLAY");
    env.remove("MELEE_WB_HEADLESS");
    if (launch_.headless) env.insert("MELEE_WB_HEADLESS", "1");
    return env;
}

bool EngineLink::start(QString *err) {
    setError(err, {});
    if (busy_) { setError(err, "engine operation already in progress"); return false; }
    QScopedValueRollback<bool> guard(busy_, true);
    stop();
    return startImpl(err);
}
bool EngineLink::restart(QString *err) { return start(err); }

bool EngineLink::startImpl(QString *err) {
    state_ = "starting";
    const auto generation = stopGeneration_;
    auto fail = [this, err](const QString &message) {
        stop();
        state_ = "error: " + message;
        setError(err, message);
        return false;
    };
    if (launch_.exe.isEmpty()) return fail("engine executable is not configured");
    if (launch_.wbDir.isEmpty()) return fail("workbench payload directory is not configured");
    launch_.wbDir = QFileInfo(launch_.wbDir).absoluteFilePath();
    if (!QDir().mkpath(launch_.wbDir)) return fail("cannot create workbench payload directory");
    if (launch_.port < 0 || launch_.port > 65535) return fail("invalid console port");

    QTcpServer reservation;
    if (!reservation.listen(QHostAddress::LocalHost, quint16(launch_.port)))
        return fail("cannot reserve console port: " + reservation.errorString());
    const quint16 port = reservation.serverPort();
    reservation.close();

    process_.setProcessEnvironment(buildEnvironment(port));
    process_.setWorkingDirectory(launch_.workDir);
    process_.setProgram(launch_.exe);
    process_.setArguments(launch_.extraArgs);
    ownsProcess_ = true;
    QElapsedTimer timer; timer.start();
    process_.start();

    while (remaining(timer, 60000)) {
        if (generation != stopGeneration_) {
            setError(err, "engine start cancelled");
            return false;
        }
        if (process_.state() == QProcess::NotRunning)
            return fail("engine exited before console was ready: " + process_.errorString());
        if (process_.state() == QProcess::Starting) {
            pumpFor(std::min(10, remaining(timer, 60000)));
            continue;
        }
        const auto attempt = timer.elapsed();
        QString error;
        const bool connected = console_.connectTo(port, std::min(250, remaining(timer, 60000)), &error);
        if (generation != stopGeneration_) {
            console_.close(); setError(err, "engine start cancelled"); return false;
        }
        if (connected && process_.state() == QProcess::Running) {
            // The console answers before the scene has seeded the fighter. Wait for it, and when it never
            // appears say why (the game logs the rejected scene) instead of leaving every command to fail.
            QString lastReply;
            while (remaining(timer, 60000)) {
                if (generation != stopGeneration_) { console_.close(); setError(err, "engine start cancelled"); return false; }
                if (process_.state() != QProcess::Running) return fail("engine exited while loading the fighter");
                const auto probe = console_.call("=wb.frame_info()", std::min(3000, remaining(timer, 60000)));
                if (probe.ok && !probe.text.trimmed().isEmpty()) {
                    // The fighter exists while the scene's entry still plays unpaused (about a second). A frame
                    // request made then can stay pending for good, so wait for the workbench's own pause.
                    QElapsedTimer pauseWait; pauseWait.start();
                    while (remaining(pauseWait, 15000) && remaining(timer, 60000)) {
                        if (generation != stopGeneration_) { console_.close(); setError(err, "engine start cancelled"); return false; }
                        if (process_.state() != QProcess::Running) return fail("engine exited while loading the fighter");
                        const auto paused = console_.call("=tostring(gd.paused())", std::min(2000, remaining(timer, 60000)));
                        if (paused.ok && paused.text.trimmed().startsWith("true")) break;
                        pumpFor(std::min(100, remaining(timer, 60000)));
                    }
                    // The scene pauses the fighter in Fall, still above the floor. Run it a few frames so it lands
                    // in Wait: ground rows start from a standing fighter on the floor (the engine records that
                    // pose as its home).
                    console_.call("=wb.step({n=30})", std::min(3000, remaining(timer, 60000)));
                    QElapsedTimer landing; landing.start();
                    while (remaining(landing, 5000) && remaining(timer, 60000)) {   // best effort: never block start-up
                        QString serr;
                        const auto info = request("frame_info", {}, std::min(3000, remaining(timer, 60000)), &serr);
                        if (!serr.isEmpty() || info.value("frame").toDouble(-1) >= 1) break;
                        pumpFor(std::min(50, remaining(timer, 60000)));
                    }
                    state_ = "ready"; setError(err, {}); return true;
                }
                lastReply = probe.text;
                pumpFor(std::min(250, remaining(timer, 60000)));
            }
            QStringList reasons;
            QFile log(QDir(launch_.workDir).filePath("melee-pc.log"));
            if (log.open(QIODevice::ReadOnly)) {
                static const QRegularExpression interesting("scene|geno:|mods|reject|not found|workbench", QRegularExpression::CaseInsensitiveOption);
                const auto lines = QString::fromUtf8(log.readAll()).split(QLatin1Char(10));
                for (const auto &line : lines)
                    if (line.contains("scene", Qt::CaseInsensitive) && (line.contains("reject", Qt::CaseInsensitive) || line.contains("must name", Qt::CaseInsensitive) || line.contains("not found", Qt::CaseInsensitive) || line.contains("error", Qt::CaseInsensitive)))
                        reasons << line.trimmed();
                if (reasons.isEmpty())
                    for (const auto &line : lines) if (interesting.match(line).hasMatch() && line.contains("error", Qt::CaseInsensitive)) reasons << line.trimmed();
            }
            const QString detail = reasons.isEmpty() ? lastReply.trimmed() : reasons.last().left(300);
            return fail("engine: scene rejected or fighter not loaded: " + (detail.isEmpty() ? QString("no fighter on port 1") : detail));
        }
        const int pause = int(std::max<qint64>(0, 250 - (timer.elapsed() - attempt)));
        pumpFor(std::min(pause, remaining(timer, 60000)));
    }
    return fail("timeout waiting for engine console");
}

QString EngineLink::payloadPath(const QString &path, bool allowMissing, QString *err) const {
    if (launch_.wbDir.isEmpty() || path.isEmpty() || path.contains(QChar(0))) {
        setError(err, "workbench payload directory or path is not configured");
        return {};
    }
    const QFileInfo dir(launch_.wbDir);
    const QString root = dir.canonicalFilePath();
    if (root.isEmpty() || !dir.isDir()) {
        setError(err, "workbench payload directory does not exist");
        return {};
    }
    const QFileInfo file(QDir(root).absoluteFilePath(path));
    QString resolved = file.canonicalFilePath();
    if (resolved.isEmpty() && !file.isSymLink()) {
        // A screenshot is scheduled by the game and may not exist yet. Resolve
        // its existing parent, including symlinks, before returning a path.
        const QString parent = QFileInfo(file.absolutePath()).canonicalFilePath();
        if (!parent.isEmpty()) resolved = QDir(parent).filePath(file.fileName());
    }
#ifdef Q_OS_WIN
    constexpr auto pathCase = Qt::CaseInsensitive;
#else
    constexpr auto pathCase = Qt::CaseSensitive;
#endif
    const QString prefix = root.endsWith('/') ? root : root + '/';
    if (resolved.isEmpty() || !resolved.startsWith(prefix, pathCase)) {
        setError(err, "payload outside wb dir: " + path);
        return {};
    }
    if ((!allowMissing && !file.isFile()) || (file.exists() && !file.isFile())) {
        setError(err, "cannot read payload file: " + path);
        return {};
    }
    return resolved;
}

QJsonObject EngineLink::request(const QString &fn, const QJsonObject &args, int timeoutMs,
                                QString *err, bool *pending) {
    setError(err, {});
    if (pending) *pending = false;
    const auto reply = console_.call("=wb." + fn + '(' + luaLiteral(args) + ')', timeoutMs);
    if (!reply.ok) {
        const QString error = reply.text.isEmpty() ? QString("engine command failed") : reply.text;
        if (!console_.connected() && state_ != "stopped") state_ = "error: " + error;
        setError(err, error);
        return {};
    }
    QString last;
    const auto lines = reply.text.split('\n');
    for (const auto &line : lines) if (!line.trimmed().isEmpty()) last = line.trimmed();
    if (last == "ok") return {{"ok", true}};
    if (last == "pending" && pending) { *pending = true; return {}; }
    if (last.startsWith('@')) {
        const QString path = payloadPath(last.mid(1), fn == "render", err);
        if (path.isEmpty()) return {};
        if (fn == "render") return {{"path", path}};
        QFile f(path);
        if (!f.open(QIODevice::ReadOnly)) {
            setError(err, "cannot read payload file: " + f.errorString());
            return {};
        }
        if (f.size() > kPayloadLimit) {
            setError(err, "engine JSON payload too large");
            return {};
        }
        return parseObject(f.read(kPayloadLimit + 1), err);
    }
    if (last.startsWith('{')) return parseObject(last.toUtf8(), err);
    setError(err, "unexpected engine reply: " + last);
    return {};
}

QJsonObject EngineLink::call(const QString &fn, const QJsonObject &args, QString *err) {
    setError(err, {});
    if (busy_) { setError(err, "engine operation already in progress"); return {}; }
    static const QRegularExpression name("^[A-Za-z_][A-Za-z0-9_]*$");
    if (!name.match(fn).hasMatch()) { setError(err, "invalid workbench function name"); return {}; }
    const auto current = status();
    if (current != "ready") {
        setError(err, current.startsWith("error: ") ? current.mid(7) : QString("engine not running"));
        return {};
    }
    QScopedValueRollback<bool> guard(busy_, true);
    QElapsedTimer timer; timer.start();
    QString error; bool pending = false;
    auto result = request(fn, args, timeoutMs_, &error, fn == "frame" ? &pending : nullptr);
    if (!error.isEmpty()) {
        if (fn == "reload" && error.contains("reload needs restart")) {
            // Release the public-operation guard only for the synchronous restart;
            // start() installs its own guard before it pumps any events.
            QScopedValueRollback<bool> allowRestart(busy_, false);
            if (restart(&error)) return {{"ok", true}};
        }
        setError(err, error); return {};
    }
    if (fn != "frame") return result;

    const auto wanted = args.value("frame");
    if (!wanted.isDouble() || wanted.toDouble() < 0 ||
            std::floor(wanted.toDouble()) != wanted.toDouble()) {
        if (pending) { setError(err, "frame request requires a nonnegative integer frame"); return {}; }
        return result;
    }
    auto matches = [&wanted](const QJsonObject &o) {
        const auto frame = o.value("frame");
        return frame.isDouble() && frame.toDouble() == wanted.toDouble();
    };
    // The engine answers frame_info with frame -1 while the request is pending. Any other frame is the
    // finished request: if it is not the wanted one the move ended (or chained into another action) before
    // that frame, so say so now instead of polling until the timeout.
    const int motion = args.value("motion").toInt(-1);
    auto settle = [&](const QJsonObject &o, QString *why) {
        if (matches(o)) { lastGoodFrame_[motion] = std::max(lastGoodFrame_.value(motion), int(wanted.toDouble())); return true; }
        const auto frame = o.value("frame");
        if (!frame.isDouble() || frame.toDouble() < 1) return false; // still pending
        const int last = lastGoodFrame_.value(motion, 0);
        *why = QString("frame %1 is past the end of this move (the fighter is at frame %2 of action %3%4)")
            .arg(int(wanted.toDouble())).arg(int(frame.toDouble())).arg(o.value("motion").toInt(-1))
            .arg(last > 0 ? QString("; last frame %1").arg(last) : QString());
        return true;
    };
    QString why;
    if (!pending && settle(result, &why)) {
        if (why.isEmpty()) return result;
        setError(err, why); return {};
    }
    // A request issued while a freshly started engine is still settling can stay pending for good; a new
    // wb.frame supersedes it. So if the first window passes without an answer, ask again once.
    bool resent = false;
    int window = 2500;
    QElapsedTimer polling; polling.start();
    for (;;) {
        while (remaining(polling, window) && remaining(timer, timeoutMs_)) {
            const int left = std::min(remaining(polling, window), remaining(timer, timeoutMs_));
            pumpFor(std::min(50, left));
            const int callBudget = std::min(remaining(polling, window), remaining(timer, timeoutMs_));
            if (callBudget < 200) break; // a console call cut short by its budget would drop the connection
            result = request("frame_info", {}, callBudget, &error);
            if (!error.isEmpty()) { setError(err, error); return {}; }
            if (settle(result, &why)) {
                if (why.isEmpty()) return result;
                setError(err, why); return {};
            }
        }
        if (resent || !remaining(timer, timeoutMs_)) break;
        resent = true; window = 5000; polling.restart();
        bool again = false;
        result = request(fn, args, std::min(timeoutMs_, remaining(timer, timeoutMs_)), &error, &again);
        if (!error.isEmpty()) { setError(err, error); return {}; }
        if (!again && settle(result, &why)) {
            if (why.isEmpty()) return result;
            setError(err, why); return {};
        }
    }
    setError(err, "timeout waiting for requested frame");
    return {};
}
}
