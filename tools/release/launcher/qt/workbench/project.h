#pragma once
#include "file_store.h"
#include <QString>
#include <QStringList>

namespace wb {
struct ProjectConfig {
    QString id, gameplay, movesDir, fidelity, plan, modId;
    // The combo graph (routes, strings; geno.md 25): a project-relative JSON file with a "combo" object, or one that is the
    // block itself. Empty when the project declares none.
    QString combo;
    // Read-only plan outside the source tree; absolute or workspace-relative.
    QString planAbs;
    // Names/paths of the artist .blend / .glb (read-only, resolved like planAbs; no art data).
    QString artBlend, artGlb;
    QStringList rebuild, importClip;
    static ProjectConfig load(FileStore &fs, QString *err);
};
} // namespace wb
