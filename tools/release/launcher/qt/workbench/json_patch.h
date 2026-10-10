#pragma once
#include <QJsonValue>
#include <QString>
#include <QStringList>

namespace wb {
using JsonPath = QStringList;  // object keys, or "#N" for array index N

// Validate syntax and reject duplicate keys in every object, including escaped aliases.
bool jsonHasUniqueKeys(const QString &text);

// Offsets are QString (UTF-16) indices; end is exclusive. An empty path selects
// the root value. Malformed JSON, missing paths and ambiguous keys fail.
bool jsonFind(const QString &text, const JsonPath &path, int *start, int *end);

// Only the selected span (or the inserted member) changes. Failures return a
// null QString and set err when supplied; success clears err. valueText must
// contain exactly one JSON value. Insertion refuses an existing key.
QString jsonReplace(const QString &text, const JsonPath &path, const QString &valueText, QString *err);
QString jsonInsertKey(const QString &text, const JsonPath &objectPath, const QString &key, const QString &valueText, QString *err);
QString jsonScalar(const QJsonValue &v);
}
