#include "play_launch.h"
#include "commands.h"
#include <QDir>
#include <QFileInfo>
#include <QStandardPaths>

namespace wb {
namespace {
PlayCommand failed(const QString &error) { return {{}, {}, {}, error}; }
}
PlayCommand playCommand(const QString &project, bool vsCpu, const QString &row,
                        const QProcessEnvironment &env) {
    const QFileInfo info(project);
    if (!info.exists())
        return failed(t("Fighter project was not found", "No se encontró el proyecto del luchador"));
    const auto projectDir = info.isDir() ? info.absoluteFilePath() : info.absolutePath();
    QString root;
    for (QDir directory(projectDir); ; ) {
        if (QFileInfo::exists(directory.filePath(".git"))) { root = directory.absolutePath(); break; }
        if (!directory.cdUp()) break;
    }
    if (root.isEmpty() || !QFileInfo(QDir(root).filePath("tools/geno/play.py")).isFile())
        return failed(t("Play tool was not found in this project's checkout",
                        "No se encontró la herramienta de juego en el repositorio de este proyecto"));
    QString python = env.value("GW_PYTHON").trimmed();
    if (python.isEmpty()) {
        const auto paths = env.value("PATH").split(QDir::listSeparator(), Qt::SkipEmptyParts);
        if (!paths.isEmpty()) {
            python = QStandardPaths::findExecutable("python", paths);
            if (python.isEmpty()) python = QStandardPaths::findExecutable("python3", paths);
        }
    }
    if (python.isEmpty())
        return failed(t("Python was not found: set GW_PYTHON or add Python to PATH",
                        "No se encontró Python: define GW_PYTHON o añade Python a PATH"));
    QStringList args{QDir(root).filePath("tools/geno/play.py"), "--project", info.absoluteFilePath()};
    if (vsCpu) args << "--vs" << "cpu";
    else {
        args << "--lab";
        if (!row.isEmpty()) args << "--clip" << row;
    }
    args << "--json";
    return {python, args, root, {}};
}
}
