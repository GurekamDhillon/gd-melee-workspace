#pragma once
#include "file_store.h"
#include <QString>
#include <QStringList>

namespace wb {
struct ProjectConfig {
    QString id, gameplay, movesDir, fidelity, plan, modId;
    // Read-only plan outside the source tree; absolute or workspace-relative.
    QString planAbs;
    QStringList rebuild, importClip;
    static ProjectConfig load(FileStore &fs, QString *err);
};
} // namespace wb
