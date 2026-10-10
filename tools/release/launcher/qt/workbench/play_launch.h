#pragma once
#include <QProcessEnvironment>
#include <QStringList>

namespace wb {
struct PlayCommand {
    QString program;
    QStringList args;
    QString workingDir, error;
};
// Builds arguments for the shared Python resolver; all resolution remains there.
PlayCommand playCommand(const QString &project, bool vsCpu, const QString &row,
                        const QProcessEnvironment &env = QProcessEnvironment::systemEnvironment());
}
