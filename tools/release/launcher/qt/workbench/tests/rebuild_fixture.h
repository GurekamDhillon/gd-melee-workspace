#pragma once
#include "../testfixture.h"
#include <QStringList>

namespace wbtest {
inline QStringList rebuildHelper(const QString &mode = "ok", const QStringList &args = {}) {
    return QStringList{QString::fromUtf8(WB_REBUILD_HELPER), mode} + args;
}

// Keep the generic schema fixture intact; only tests that run a rebuild need this process fixture.
inline QString makeRebuildFighter(const QString &dir) {
    makeSynthFighter(dir);
    auto project = QJsonDocument::fromJson(kProject).object();
    project["rebuild"] = QJsonArray::fromStringList(rebuildHelper());
    put(dir, "workbench.json", QJsonDocument(project).toJson());
    return dir;
}
}
