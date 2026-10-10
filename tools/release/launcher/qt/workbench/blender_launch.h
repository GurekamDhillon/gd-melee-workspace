#pragma once
#include <QProcessEnvironment>
#include <QString>
#include <QStringList>

namespace wb {
struct BlenderCommand { QString program; QStringList args; QString error; };
// Explicit values are returned as supplied, like geno_workbench/launch.py.
// Search order: setting, GW_BLENDER, then the supplied environment's PATH.
QString findBlender(const QString &setting, const QProcessEnvironment &env);
// Nearest .git ancestor (directory OR worktree file), with a usable bootstrap.py.
QString findAddonDir(const QString &projectDir);
BlenderCommand blenderCommand(const QString &blender, const QString &addonDir,
                              const QString &projectDir, quint16 port);
// Art paths, like plan_abs, are absolute or relative to the nearest .git ancestor.
// With no checkout ancestor they are relative to the project itself.
BlenderCommand blenderCommand(const QString &blender, const QString &addonDir,
                              const QString &projectDir, quint16 port, const QString &art);
}
