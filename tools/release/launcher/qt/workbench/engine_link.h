#pragma once
#include <QHash>

#include <QByteArray>
#include <QElapsedTimer>
#include <QJsonObject>
#include <QJsonValue>
#include <QProcess>
#include <QProcessEnvironment>
#include <QString>
#include <QStringList>
#include <QTcpSocket>
#include <QVector>

namespace wb {
struct Vec3 { double x = 0, y = 0, z = 0; };
struct BoneLive { int joint = 0; int parent = -1; Vec3 pos; };
struct HitLive {
    int slot = 0; int joint = 0; Vec3 offset; double radius = 0;
    Vec3 world; bool active = false;
};
struct HurtLive { int joint = 0; Vec3 a, b; double radius = 0; };
struct FrameInfo {
    QString row; int motion = 0; int frame = 0;
    QVector<BoneLive> bones;
    QVector<HitLive> hitboxes;
    QVector<HurtLive> hurtboxes;
    Vec3 ecbBottom, ecbTop;
    double floorY = 0, lowestY = 0;
    static FrameInfo fromJson(const QJsonObject &o);
    QJsonObject toJson() const;
};

class EngineBackend {
public:
    virtual ~EngineBackend() = default;
    virtual QJsonObject call(const QString &fn, const QJsonObject &args, QString *err) = 0;
    virtual QString status() = 0;
    virtual bool restart(QString *err) = 0;
};

struct ConsoleReply { bool ok = false; QString text; };

// Synchronous, bounded calls service the owning thread's Qt event loop.
// Use on one thread; a call re-entered by the event pump is refused.
class ConsoleClient {
public:
    bool connectTo(quint16 port, int timeoutMs, QString *err);
    ConsoleReply call(const QString &line, int timeoutMs);
    bool connected() const;
    void close();
    QString banner() const;

private:
    bool readLine(QByteArray *line, const QElapsedTimer &timer, int timeoutMs, QString *err);
    QTcpSocket socket_;
    QByteArray buffer_;
    QString banner_;
    bool busy_ = false;
};

QString luaLiteral(const QJsonValue &v);

class EngineLink : public EngineBackend {
public:
    struct Launch {
        QString exe, workDir, modsDir, modId, wbDir;
        QStringList extraArgs;
        QProcessEnvironment env;
        int port = 0;
        bool headless = false; // MELEE_WB_HEADLESS=1: Dawn null backend, no window
    };
    explicit EngineLink(Launch l);
    ~EngineLink() override;
    bool start(QString *err);
    void stop();
    QJsonObject call(const QString &fn, const QJsonObject &args, QString *err) override;
    // Engine wb.frame numbering is one ahead of the script numbering the rest of the Workbench uses.
    static constexpr int kEngineFrameLag = 1;
    QString status() override;
    bool restart(QString *err) override;
    bool attach(quint16 port, QString *err);
    void setTimeoutMs(int timeoutMs);
    // The environment the engine process gets for a console port (testable without a process).
    QProcessEnvironment buildEnvironment(int port) const;

private:
    bool startImpl(QString *err);
    QJsonObject request(const QString &fn, const QJsonObject &args, int timeoutMs,
                        QString *err, bool *pending = nullptr);
    QString payloadPath(const QString &path, bool allowMissing, QString *err) const;
    Launch launch_;
    ConsoleClient console_;
    QProcess process_;
    QString state_ = "stopped";
    int timeoutMs_ = 8000;
    bool busy_ = false;
    bool ownsProcess_ = false;
    QJsonObject callEngine(const QString &fn, const QJsonObject &args, QString *err);
    QHash<int, int> lastGoodFrame_; // motion -> highest frame the engine confirmed (a move's known length)
    quint64 stopGeneration_ = 0;
};
}
