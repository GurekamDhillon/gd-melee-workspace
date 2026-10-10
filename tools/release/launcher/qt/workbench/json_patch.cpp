#include "json_patch.h"
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QSet>
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

// Reuse the validated source scanners so keys are checked before Qt collapses
// duplicate object members. This includes nested objects and escaped key spellings.
bool uniqueKeys(const QString &text, int start, int end) {
    if (text[start] == '{') {
        QSet<QString> keys;
        int cursor = start + 1;
        Member member;
        while (nextMember(text, &cursor, end, &member)) {
            if (keys.contains(member.key)) return false;
            keys.insert(member.key);
            if (!uniqueKeys(text, member.valueStart, member.valueEnd)) return false;
        }
    } else if (text[start] == '[') {
        int cursor = skipWs(text, start + 1);
        while (cursor < end - 1) {
            const int valueEnd = skipValue(text, cursor);
            if (valueEnd < 0 || !uniqueKeys(text, cursor, valueEnd)) return false;
            cursor = skipWs(text, valueEnd);
            if (cursor < end - 1 && text[cursor] == ',') cursor = skipWs(text, cursor + 1);
        }
    }
    return true;
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

bool jsonHasUniqueKeys(const QString &text) {
    if (!validValue(text)) return false;
    const int start = skipWs(text, 0);
    const int end = skipValue(text, start);
    return end >= 0 && uniqueKeys(text, start, end);
}

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

QString jsonScalar(const QJsonValue &v) {
    if (v.isArray()) return QString::fromUtf8(QJsonDocument(v.toArray()).toJson(QJsonDocument::Compact));
    if (v.isObject()) return QString::fromUtf8(QJsonDocument(v.toObject()).toJson(QJsonDocument::Compact));
    const QString wrapped = QString::fromUtf8(QJsonDocument(QJsonArray{v}).toJson(QJsonDocument::Compact));
    return wrapped.mid(1, wrapped.size() - 2);
}
}  // namespace wb
