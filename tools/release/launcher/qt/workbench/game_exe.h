#pragma once
#include <QProcessEnvironment>
#include <QString>

namespace wb {
struct GameExe {
    QString path;    // empty when nothing was found
    QString source;  // human label of the rule that matched ("Settings", "GW_ENGINE_EXE", ...)
    QString error;   // set when path is empty: what was searched
};
// Workspace of a project: GW_ROOT, else the nearest ancestor holding .env, else the nearest .git ancestor.
QString workspaceRootOf(const QString &projectDir, const QProcessEnvironment &env);
// Order: explicit setting, GW_ENGINE_EXE, workbench.json "engine" (absolute, or relative to the
// project then the workspace), <workspace>/_build/melee-pc.exe, then beside the launcher (appDir).
// Explicit values (setting, GW_ENGINE_EXE) are returned as given so a wrong one fails loudly.
GameExe resolveGameExe(const QString &setting, const QProcessEnvironment &env,
                       const QString &projectDir, const QString &appDir);
// Blender beyond setting/GW_BLENDER/PATH: workspace .env, _build/tools.json, Program Files, Steam libraries.
QString discoverBlender(const QString &projectDir, const QProcessEnvironment &env);
}
