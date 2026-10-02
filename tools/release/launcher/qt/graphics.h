#pragma once
#include <QProcessEnvironment>
#include <QVector>
#include <QString>
namespace launcher {
struct GraphicsDevice {
    QString name, api, reason;
    quint32 vendor = 0, device = 0;
    bool usable = false;
    QString selector() const;
};
struct GraphicsReport {
    QVector<GraphicsDevice> devices;
    QString error;
    bool valid = false;
    bool ready() const;
    bool matchesSelection(const QString &selection) const;
    QString summary() const;
};
GraphicsReport parseGraphicsReport(const QByteArray &json, int exitCode);
QProcessEnvironment graphicsEnvironment(QProcessEnvironment env, const QString &selection);
QString graphicsDriverHelp(const QString &osRelease);
QString graphicsStartupFailure(const QString &runDir, const QString &osRelease);
}
