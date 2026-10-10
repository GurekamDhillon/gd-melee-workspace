#include "json_patch.h"
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QPair>
#include <QVector>
#include <limits>

namespace wb {
namespace {
bool validValue(const QString &text) {
    if (text.size() > std::numeric_limits<int>::max()) return false;
    // Qt validates syntax only: never serialize the source document. Wrapping
    // allows scalar roots, which QJsonDocument alone does not accept.
    // Qt tolerates unknown escapes such as "\q"; strict JSON does not.
    {
        bool inStr = false;
        for (int k = 0; k < text.size(); ++k) {
            const QChar c = text[k];
            if (!inStr) { if (c == '"') inStr = true; continue; }
            if (c == '"') inStr = false;
            else if (c == '\\') {
                if (++k >= text.size() || !QStringLiteral("\"\\/bfnrtu").contains(text[k])) return false;
            }
        }
    }
    QJsonParseError error;
    const auto doc = QJsonDocument::fromJson("[" + text.toUtf8() + "]", &error);
    return error.error == QJsonParseError::NoError && doc.isArray() && doc.array().size() == 1;
}

bool isWs(QChar c) {
    return c == ' ' || c == '\t' || c == '\r' || c == '\n';
}

int skipWs(const QString &text, int i) {
    while (i < text.size() && isWs(text[i])) ++i;
    return i;
}

// Scanners operate on JSON validated at the public API boundary.
int skipString(const QString &text, int i) {
    for (++i; i < text.size(); ++i) {
        if (text[i] == '\\') ++i;
        else if (text[i] == '"') return i + 1;
    }
    return -1;
}

int skipValue(const QString &text, int i) {
    if (text[i] == '"') return skipString(text, i);
    if (text[i] == '{' || text[i] == '[') {
        int depth = 0;
        for (; i < text.size(); ++i) {
            if (text[i] == '"') {
                i = skipString(text, i);
                if (i < 0) return -1;
                --i;
            } else if (text[i] == '{' || text[i] == '[') {
                ++depth;
            } else if (text[i] == '}' || text[i] == ']') {
                if (--depth == 0) return i + 1;
            }
        }
        return -1;
    }
    while (i < text.size() && !isWs(text[i]) && text[i] != ',' && text[i] != '}' && text[i] != ']') ++i;
    return i;
}

struct Member {
    QString key;
    int keyStart;
    int valueStart;
    int valueEnd;
};

bool nextMember(const QString &text, int *cursor, int end, Member *member) {
    const int keyStart = skipWs(text, *cursor);
    if (keyStart >= end - 1) return false;
    const int keyEnd = skipString(text, keyStart);
    if (keyEnd < 0) return false;
    // Decode escapes for path comparisons, retaining the original key text.
    const auto keyDoc = QJsonDocument::fromJson("[" + text.mid(keyStart, keyEnd - keyStart).toUtf8() + "]");
    const int valueStart = skipWs(text, skipWs(text, keyEnd) + 1);  // ':'
    const int valueEnd = skipValue(text, valueStart);
    if (valueEnd < 0) return false;
    *member = {keyDoc.array()[0].toString(), keyStart, valueStart, valueEnd};
    *cursor = skipWs(text, valueEnd);
    if (*cursor < end - 1 && text[*cursor] == ',') ++*cursor;
    return true;
}

bool child(const QString &text, int start, int end, const QString &step, int *cs, int *ce) {
    if (text[start] == '{') {
        int cursor = start + 1;
        Member member;
        bool found = false;
        while (nextMember(text, &cursor, end, &member)) {
            if (member.key != step) continue;
            if (found) return false;  // Duplicate keys make an edit ambiguous.
            *cs = member.valueStart;
            *ce = member.valueEnd;
            found = true;
        }
        return found;
    }
    if (text[start] != '[' || !step.startsWith('#') || step.size() < 2) return false;
    for (int i = 1; i < step.size(); ++i) {
        if (step[i] < '0' || step[i] > '9') return false;
    }
    bool ok;
    const int wanted = step.mid(1).toInt(&ok);
    if (!ok) return false;
    int cursor = skipWs(text, start + 1);
    for (int index = 0; cursor < end - 1; ++index) {
        const int valueEnd = skipValue(text, cursor);
        if (valueEnd < 0) return false;
        if (index == wanted) {
            *cs = cursor;
            *ce = valueEnd;
            return true;
        }
        cursor = skipWs(text, valueEnd);
        if (cursor < end - 1 && text[cursor] == ',') cursor = skipWs(text, cursor + 1);
    }
    return false;
}

QString fail(QString *err, const QString &message) {
    if (err) *err = message;
    return QString();
}

QString lineEnding(const QString &text, int newline) {
    return newline > 0 && text[newline - 1] == '\r' ? QStringLiteral("\r\n") : QStringLiteral("\n");
}

QString leadingIndent(const QString &text, int lineStart, int limit) {
    int end = lineStart;
    while (end < limit && (text[end] == ' ' || text[end] == '\t')) ++end;
    return text.mid(lineStart, end - lineStart);
}
}  // namespace

bool jsonFind(const QString &text, const JsonPath &path, int *start, int *end) {
    if (!start || !end || !validValue(text)) return false;
    int s = skipWs(text, 0);
    int e = skipValue(text, s);
    if (e < 0) return false;
    for (const QString &step : path) {
        int cs, ce;
        if (!child(text, s, e, step, &cs, &ce)) return false;
        s = cs;
        e = ce;
    }
    *start = s;
    *end = e;
    return true;
}

QString jsonReplace(const QString &text, const JsonPath &path, const QString &valueText, QString *err) {
    if (err) err->clear();
    int s, e;
    if (!jsonFind(text, path, &s, &e))
        return fail(err, "invalid JSON or path not found/ambiguous: " + path.join('/'));
    if (!validValue(valueText)) return fail(err, QStringLiteral("invalid JSON replacement value"));
    return text.left(s) + valueText + text.mid(e);
}

QString jsonInsertKey(const QString &text, const JsonPath &objectPath, const QString &key, const QString &valueText, QString *err) {
    if (err) err->clear();
    int s, e;
    if (!jsonFind(text, objectPath, &s, &e) || text[s] != '{')
        return fail(err, "invalid JSON or object not found/ambiguous: " + objectPath.join('/'));
    if (!validValue(valueText)) return fail(err, QStringLiteral("invalid JSON member value"));

    int cursor = s + 1;
    int lastKey = -1;
    int lastEnd = -1;
    Member member;
    while (nextMember(text, &cursor, e, &member)) {
        if (member.key == key) return fail(err, "json key already exists: " + key);
        lastKey = member.keyStart;
        lastEnd = member.valueEnd;
    }
    const QString added = jsonScalar(QJsonValue(key)) + ": " + valueText;
    if (lastEnd < 0) {
        const int newline = static_cast<int>(text.indexOf('\n', s + 1));
        if (newline >= 0 && newline < e - 1) {
            const int closeLine = static_cast<int>(text.lastIndexOf('\n', e - 2)) + 1;
            const QString closeIndent = leadingIndent(text, closeLine, e - 1);
            // No previous member: use the closing indent plus one level.
            const QString indent = closeIndent + (closeIndent.contains('\t') ? "\t" : "  ");
            return text.left(s + 1) + lineEnding(text, newline) + indent + added + text.mid(s + 1);
        }
        return text.left(s + 1) + added + text.mid(s + 1);
    }

    // Use the last member's KEY line, not a key inside its nested value.
    const int newline = static_cast<int>(text.lastIndexOf('\n', lastKey - 1));
    const QString separator = newline > s
        ? "," + lineEnding(text, newline) + leadingIndent(text, newline + 1, lastKey)
        : QStringLiteral(", ");
    return text.left(lastEnd) + separator + added + text.mid(lastEnd);
}


namespace {
bool arrayElements(const QString &text, const JsonPath &path, int *arrayStart, int *arrayEnd, QVector<QPair<int, int>> *elements) {
    if (!jsonFind(text, path, arrayStart, arrayEnd) || text[*arrayStart] != '[') return false;
    for (int i = 0;; ++i) {
        int s, e;
        auto child = path;
        child << '#' + QString::number(i);
        if (!jsonFind(text, child, &s, &e)) break;
        elements->append({s, e});
    }
    return true;
}
QString layoutValue(const QString &text, const QPair<int, int> &neighbour, const QJsonValue &value) {
    const QString compact = jsonScalar(value);
    if (!text.mid(neighbour.first, neighbour.second - neighbour.first).contains('\n') || !value.isArray())
        return compact;
    // A flat array laid out one item per line, like its neighbour.
    const int lineStart = static_cast<int>(text.lastIndexOf('\n', neighbour.first - 1)) + 1;
    const QString indent = leadingIndent(text, lineStart, neighbour.first);
    const QString unit = indent.contains('\t') ? "\t" : "  ";
    const QString eol = lineEnding(text, lineStart > 0 ? lineStart - 1 : 0);
    QStringList items;
    for (const auto &item : value.toArray()) {
        if (item.isArray() || item.isObject()) return compact;
        items << eol + indent + unit + jsonScalar(item);
    }
    return items.isEmpty() ? compact : "[" + items.join(",") + eol + indent + "]";
}
}  // namespace

QString jsonArrayInsert(const QString &text, const JsonPath &arrayPath, int index, const QJsonValue &value, QString *err) {
    if (err) err->clear();
    int s, e;
    QVector<QPair<int, int>> el;
    if (!arrayElements(text, arrayPath, &s, &e, &el))
        return fail(err, "invalid JSON or array not found/ambiguous: " + arrayPath.join('/'));
    if (index < 0 || index > el.size()) return fail(err, QStringLiteral("array index out of range"));
    if (el.isEmpty()) return text.left(s + 1) + jsonScalar(value) + text.mid(s + 1);
    const int ref = qMin(index, int(el.size()) - 1);
    const QString laid = layoutValue(text, el[ref], value);
    if (index < el.size()) {
        // Same separator as the one that follows this element (or precedes it for the last).
        const QString sep = index + 1 < el.size() ? text.mid(el[index].second, el[index + 1].first - el[index].second)
                                                  : QStringLiteral(", ");
        const QString usedSep = index + 1 < el.size() ? sep : (el.size() >= 2 ? text.mid(el[0].second, el[1].first - el[0].second) : sep);
        return text.left(el[index].first) + laid + usedSep + text.mid(el[index].first);
    }
    const QString sep = el.size() >= 2 ? text.mid(el[el.size() - 2].second, el.last().first - el[el.size() - 2].second)
                                       : QStringLiteral(", ");
    return text.left(el.last().second) + sep + laid + text.mid(el.last().second);
}

QString jsonArrayRemove(const QString &text, const JsonPath &arrayPath, int index, QString *err) {
    if (err) err->clear();
    int s, e;
    QVector<QPair<int, int>> el;
    if (!arrayElements(text, arrayPath, &s, &e, &el))
        return fail(err, "invalid JSON or array not found/ambiguous: " + arrayPath.join('/'));
    if (index < 0 || index >= el.size()) return fail(err, QStringLiteral("array index out of range"));
    if (el.size() == 1) return text.left(el[0].first) + text.mid(el[0].second);
    if (index + 1 < el.size()) return text.left(el[index].first) + text.mid(el[index + 1].first);
    return text.left(el[index - 1].second) + text.mid(el[index].second);
}

QString jsonScalar(const QJsonValue &v) {
    if (v.isArray()) return QString::fromUtf8(QJsonDocument(v.toArray()).toJson(QJsonDocument::Compact));
    if (v.isObject()) return QString::fromUtf8(QJsonDocument(v.toObject()).toJson(QJsonDocument::Compact));
    const QString wrapped = QString::fromUtf8(QJsonDocument(QJsonArray{v}).toJson(QJsonDocument::Compact));
    return wrapped.mid(1, wrapped.size() - 2);
}
}  // namespace wb
