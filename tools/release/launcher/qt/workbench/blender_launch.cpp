#include "blender_launch.h"
#include "commands.h"
#include <QDir>
#include <QFileInfo>
#include <QStandardPaths>

namespace wb {
namespace {
QString workspaceRoot(const QString &projectDir) {
    if (projectDir.isEmpty() || !QFileInfo(projectDir).isDir()) return {};
    for (QDir dir(QFileInfo(projectDir).absoluteFilePath()); ; ) {
        if (QFileInfo::exists(dir.filePath(".git"))) return dir.absolutePath();
        if (!dir.cdUp()) return {};
    }
}
BlenderCommand failed(const QString &error) { return {{}, {}, error}; }
}
QString findBlender(const QString &setting, const QProcessEnvironment &env) {
    if (!setting.trimmed().isEmpty()) return setting;
    const auto override = env.value("GW_BLENDER");
    if (!override.trimmed().isEmpty()) return override;
    const auto paths = env.value("PATH").split(QDir::listSeparator(), Qt::SkipEmptyParts);
    // An empty QStandardPaths search list would search the real process PATH.
    return paths.isEmpty() ? QString{} : QStandardPaths::findExecutable("blender", paths);
}
QString findAddonDir(const QString &projectDir) {
    const auto root = workspaceRoot(projectDir);
    if (root.isEmpty()) return {};
    const auto addon = QDir(root).filePath("tools/blender/geno_workbench");
    return QFileInfo(QDir(addon).filePath("bootstrap.py")).isFile() ? addon : QString{};
}
BlenderCommand blenderCommand(const QString &blender, const QString &addonDir,
                              const QString &projectDir, quint16 port) {
    if (blender.trimmed().isEmpty()) return failed(t("Blender executable is not configured", "El ejecutable de Blender no está configurado"));
    const auto bootstrap = QDir(addonDir).filePath("bootstrap.py");
    if (addonDir.isEmpty() || !QFileInfo(bootstrap).isFile())
        return failed(t("Workbench Blender bootstrap.py was not found", "No se encontró bootstrap.py de Blender para el Workbench"));
    if (projectDir.isEmpty() || !QFileInfo(projectDir).isDir())
        return failed(t("Fighter project directory was not found", "No se encontró el directorio del proyecto del luchador"));
    if (!port) return failed(t("Workbench listener has no port", "El oyente del Workbench no tiene puerto"));
    return {blender, {"--python", QDir::fromNativeSeparators(bootstrap), "--", "--project", projectDir,
                     "--port", QString::number(port)}, {}};
}
BlenderCommand blenderCommand(const QString &blender, const QString &addonDir,
                              const QString &projectDir, quint16 port, const QString &art) {
    auto command = blenderCommand(blender, addonDir, projectDir, port);
    if (!command.error.isEmpty() || art.isEmpty()) return command;
    const auto root = workspaceRoot(projectDir);
    const auto path = QDir::cleanPath(QDir::isAbsolutePath(art) ? art : QDir(root.isEmpty() ? projectDir : root).filePath(art));
    if (!QFileInfo(path).isFile())
        return failed(t("Fighter art file was not found: %1", "No se encontró el archivo de arte del luchador: %1").arg(path));
    command.args << "--art" << QDir::fromNativeSeparators(path);
    return command;
}
}
