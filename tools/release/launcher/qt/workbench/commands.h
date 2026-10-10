#pragma once
#include "engine_link.h"
#include "geno_data.h"
#include "session.h"
#include <QJsonArray>
#include <cmath>
#include <limits>

namespace wb {
// Core messages use the permitted English/English pairs; language selection is
// in launcher_ui, which this headless command library does not depend on.
inline QString t(const char *english, const char *) { return QString::fromUtf8(english); }

void registerViewCommands(Session &);
void registerRowCommands(Session &);
void registerHitboxCommands(Session &);
void registerClipCommands(Session &);
void registerGroundCommands(Session &); // Task 14.
void registerSaveCommands(Session &);   // Task 9.
void registerAllCommands(Session &);
// {changes:[{path, bytes_before, bytes_after}]}; no source bytes in a command reply.
QJsonObject changeToJson(const QVector<FileChange> &);

inline QJsonObject commandSchema(const QJsonObject &properties = {}, const QJsonArray &required = {}) {
    return {{"type", "object"}, {"properties", properties}, {"required", required}};
}
inline QJsonObject argType(const char *type) { return {{"type", type}}; }

inline EngineBackend &needEngine(Session &s) {
    if (!s.engine()) throw CommandError{t("engine not running", "engine not running")};
    return *s.engine();
}
inline QJsonObject engineCall(Session &s, const QString &fn, const QJsonObject &args = {}) {
    QString error;
    auto result = needEngine(s).call(fn, args, &error);
    if (!error.isEmpty()) throw CommandError{error};
    if (result.contains("ok") && !result["ok"].toBool())
        throw CommandError{result["error"].toString(t("engine call failed", "engine call failed"))};
    return result;
}
inline int intArg(const QJsonObject &args, const QString &key, int minimum = 0,
                  int maximum = std::numeric_limits<int>::max(), int fallback = 0) {
    if (!args.contains(key)) return fallback;
    const double value = args[key].toDouble();
    if (!args[key].isDouble() || !std::isfinite(value) || std::floor(value) != value ||
        value < minimum || value > maximum)
        throw CommandError{t("%1: integer out of range", "%1: integer out of range").arg(key)};
    return int(value);
}
inline double numberArg(const QJsonObject &args, const QString &key) {
    const double value = args[key].toDouble();
    if (!args[key].isDouble() || !std::isfinite(value))
        throw CommandError{t("%1: expected a finite number", "%1: expected a finite number").arg(key)};
    return value;
}
inline RowInfo needRow(Session &s, const QString &name) {
    for (const auto &row : s.data().rows()) if (row.name == name) return row;
    throw CommandError{t("unknown row: %1", "unknown row: %1").arg(name)};
}
inline int rowMotion(const RowInfo &row) {
    if (row.motions.isEmpty())
        throw CommandError{t("row has no motion: %1", "row has no motion: %1").arg(row.name)};
    return row.motions.first();
}
inline ClipInfo needClip(Session &s, const QString &name) {
    for (const auto &clip : s.data().clips()) if (clip.name == name) return clip;
    throw CommandError{t("unknown clip: %1", "unknown clip: %1").arg(name)};
}
} // namespace wb
