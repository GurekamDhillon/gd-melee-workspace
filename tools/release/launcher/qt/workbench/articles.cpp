#include "geno_data.h"
#include "json_patch.h"
#include <QJsonDocument>
#include <QRegularExpression>
#include <cmath>
#include <stdexcept>

// Projectiles: the articles of gameplay.json and the spawn calls of the move scripts. GenoData owns the cached
// bytes; these members only build FileChanges, so every edit goes through Session::commit like a hitbox edit.
namespace wb {
namespace {
[[noreturn]] void fail(const QString &message) { throw std::runtime_error(message.toUtf8().constData()); }
bool hasBom(const QByteArray &bytes) { return bytes.startsWith("\xEF\xBB\xBF"); }
QString textOf(const QByteArray &bytes, const QString &path) {
    const QByteArray body = hasBom(bytes) ? bytes.mid(3) : bytes;
    const QString text = QString::fromUtf8(body);
    if (text.toUtf8() != body) fail(path + ": invalid UTF-8");
    return text;
}
QByteArray bytesOf(const QString &text, const QByteArray &original) {
    return (hasBom(original) ? QByteArray("\xEF\xBB\xBF") : QByteArray()) + text.toUtf8();
}
constexpr int kMaxArticles = 16; // GENO_MAX_ARTICLES (geno.md 19.8)

JsonPath pathOf(const QString &articlePath, int index) {
    JsonPath p{QStringLiteral("articles"), QStringLiteral("#%1").arg(index)};
    for (const auto &part : articlePath.split('/', Qt::SkipEmptyParts)) p << part;
    return p;
}
QJsonValue nested(const QStringList &rest, const QJsonValue &leaf) {
    if (rest.isEmpty()) return leaf;
    if (rest[0].startsWith('#')) return QJsonArray{nested(rest.mid(1), leaf)};
    return QJsonObject{{rest[0], nested(rest.mid(1), leaf)}};
}

// One operation on the article at `index` inside `text`.
QString applyOp(QString text, int index, const QJsonObject &op, QString *err) {
    const QString kind = op.value("op").toString();
    const QString path = op.value("path").toString();
    if (path.isEmpty() && kind != "set") fail(QStringLiteral("operation without a path"));
    const JsonPath full = pathOf(path, index);
    QString e;
    int s, en;
    if (kind == "set") {
        if (path.isEmpty()) fail(QStringLiteral("set needs a path"));
        const QString value = jsonScalar(op.value("value"));
        if (jsonFind(text, full, &s, &en)) {
            const QString out = jsonReplace(text, full, value, &e);
            if (out.isNull()) fail(e);
            return out;
        }
        // Missing: insert under the longest existing object, nesting what is missing below it.
        const QStringList parts = path.split('/', Qt::SkipEmptyParts);
        for (int keep = int(parts.size()) - 1; keep >= 0; --keep) {
            const JsonPath parent = pathOf(parts.mid(0, keep).join('/'), index);
            if (!jsonFind(text, parent, &s, &en) || text[s] != '{') continue;
            if (parts[keep].startsWith('#')) fail(QStringLiteral("cannot set %1: the array has no such element").arg(path));
            const QJsonValue leaf = nested(parts.mid(keep + 1), op.value("value"));
            const QString out = jsonInsertKey(text, parent, parts[keep], jsonScalar(leaf), &e);
            if (out.isNull()) fail(e);
            return out;
        }
        fail(QStringLiteral("cannot set %1").arg(path));
    }
    if (kind == "insert" || kind == "remove") {
        const int at = op.value("at").toInt(-1);
        if (kind == "remove") {
            const QString out = jsonArrayRemove(text, full, at, &e);
            if (out.isNull()) fail(e);
            return out;
        }
        if (!jsonFind(text, full, &s, &en)) {
            // The array is missing: create it holding the one element.
            const QStringList parts = path.split('/', Qt::SkipEmptyParts);
            const JsonPath parent = pathOf(parts.mid(0, parts.size() - 1).join('/'), index);
            if (at != 0) fail(QStringLiteral("insert position out of range"));
            const QString out = jsonInsertKey(text, parent, parts.last(), jsonScalar(QJsonArray{op.value("value")}), &e);
            if (out.isNull()) fail(e);
            return out;
        }
        const QString out = jsonArrayInsert(text, full, at, op.value("value"), &e);
        if (out.isNull()) fail(e);
        return out;
    }
    if (kind == "unset") fail(QStringLiteral("removing a key is not supported: set it to its default instead"));
    fail(QStringLiteral("unknown operation: %1").arg(kind));
}
} // namespace

QJsonArray GenoData::articles() const {
    QJsonParseError parseError;
    const auto doc = QJsonDocument::fromJson(gameplayText_.toUtf8(), &parseError);
    return doc.object().value("articles").toArray();
}

QVector<FileChange> GenoData::editArticle(int index, const QJsonArray &ops, QString *err) const {
    if (err) err->clear();
    try {
        if (project_.gameplay.isEmpty()) fail(QStringLiteral("project has no gameplay.json"));
        const QString conflict = externalError({"workbench.json", project_.gameplay});
        if (!conflict.isEmpty()) fail(conflict);
        if (index < 0 || index >= articles().size()) fail(QStringLiteral("unknown article: %1").arg(index));
        QString text = gameplayText_;
        for (const auto &op : ops) text = applyOp(text, index, op.toObject(), err);
        QVector<FileChange> out;
        if (text != gameplayText_) out.append({project_.gameplay, gameplayBytes_, bytesOf(text, gameplayBytes_)});
        QString full = project_.gameplay;
        if (full.endsWith(".json") && out.size()) {
            full.chop(5); full += ".full.json";
            if (fs_.exists(full)) {
                const auto fullBytes = fs_.read(full);
                QString fullText = textOf(fullBytes, full);
                const auto fullDoc = QJsonDocument::fromJson(fullText.toUtf8()).object().value("articles").toArray();
                // Only when the full file carries the same article at the same index (the build reads it first).
                if (index < fullDoc.size() && fullDoc[index].toObject().value("name") == articles()[index].toObject().value("name")) {
                    for (const auto &op : ops) fullText = applyOp(fullText, index, op.toObject(), err);
                    if (fullText != textOf(fullBytes, full)) out.append({full, fullBytes, bytesOf(fullText, fullBytes)});
                }
            }
        }
        return out;
    } catch (const std::exception &e) {
        if (err) *err = QString::fromUtf8(e.what());
        return {};
    }
}

QVector<FileChange> GenoData::addArticle(const QJsonObject &article, int *index, QString *err) const {
    if (err) err->clear();
    try {
        if (project_.gameplay.isEmpty()) fail(QStringLiteral("project has no gameplay.json"));
        const QString conflict = externalError({"workbench.json", project_.gameplay});
        if (!conflict.isEmpty()) fail(conflict);
        if (article.value("name").toString().isEmpty()) fail(QStringLiteral("an article needs a name"));
        const int count = int(articles().size());
        if (count >= kMaxArticles) fail(QStringLiteral("a fighter has at most %1 articles").arg(kMaxArticles));
        for (const auto &existing : articles())
            if (existing.toObject().value("name") == article.value("name"))
                fail(QStringLiteral("an article named %1 exists").arg(article.value("name").toString()));
        QString e;
        QString text = gameplayText_;
        JsonPath root{QStringLiteral("articles")};
        int s, en;
        if (jsonFind(text, root, &s, &en)) {
            text = jsonArrayInsert(text, root, count, article, &e);
        } else {
            text = jsonInsertKey(text, {}, QStringLiteral("articles"), jsonScalar(QJsonArray{article}), &e);
        }
        if (text.isNull()) fail(e);
        if (index) *index = count;
        return {{project_.gameplay, gameplayBytes_, bytesOf(text, gameplayBytes_)}};
    } catch (const std::exception &e) {
        if (err) *err = QString::fromUtf8(e.what());
        return {};
    }
}

QVector<FileChange> GenoData::removeArticle(int index, QString *err) const {
    if (err) err->clear();
    try {
        if (project_.gameplay.isEmpty()) fail(QStringLiteral("project has no gameplay.json"));
        const QString conflict = externalError({"workbench.json", project_.gameplay});
        if (!conflict.isEmpty()) fail(conflict);
        const int count = int(articles().size());
        if (index < 0 || index >= count) fail(QStringLiteral("unknown article: %1").arg(index));
        if (index != count - 1)
            fail(QStringLiteral("scripts name articles by number: only the last article can be deleted"));
        for (const auto &spawn : spawns())
            if (spawn.toObject().value("article").toInt(-1) == index)
                fail(QStringLiteral("row %1 spawns this article: delete that spawn first").arg(spawn.toObject().value("row").toString()));
        QString e;
        const QString text = jsonArrayRemove(gameplayText_, {QStringLiteral("articles")}, index, &e);
        if (text.isNull()) fail(e);
        return {{project_.gameplay, gameplayBytes_, bytesOf(text, gameplayBytes_)}};
    } catch (const std::exception &e) {
        if (err) *err = QString::fromUtf8(e.what());
        return {};
    }
}

QJsonArray GenoData::spawns(const QString &row) const {
    QJsonArray out;
    for (const auto &r : rows_) {
        if (!row.isEmpty() && r.name != row) continue;
        if (r.script.isEmpty() || !scripts_.contains(r.script)) continue;
        for (const auto &s : GenoAsm::parse(textOf(scripts_.value(r.script), r.script)).spawns())
            out.append(QJsonObject{{"row", r.name}, {"ordinal", s.ordinal}, {"line", s.line}, {"frame", s.frame},
                                   {"arg", double(s.arg)}, {"article", s.article}, {"variant", s.variant},
                                   {"angle", s.angle}});
    }
    return out;
}

namespace {
const RowInfo *rowNamed(const QVector<RowInfo> &rows, const QString &name) {
    for (const auto &r : rows) if (r.name == name) return &r;
    return nullptr;
}
} // namespace

QVector<FileChange> GenoData::editSpawn(const QString &name, int ordinal, std::optional<int> frame,
                                        std::optional<quint32> arg, QString *err) const {
    if (err) err->clear();
    try {
        const auto *row = rowNamed(rows_, name);
        if (!row) fail("unknown row: " + name);
        if (row->script.isEmpty()) fail("row has no script: " + name);
        const QString conflict = externalError({"workbench.json", project_.gameplay, row->script});
        if (!conflict.isEmpty()) fail(conflict);
        const auto bytes = scripts_.value(row->script);
        QString text = textOf(bytes, row->script), error;
        if (arg) {
            text = GenoAsm::parse(text).setSpawnArg(ordinal, *arg, &error);
            if (text.isNull()) fail(row->script + ": " + error);
        }
        if (frame) {
            text = GenoAsm::parse(text).moveSpawn(ordinal, *frame, &error);
            if (text.isNull()) fail(row->script + ": " + error);
        }
        if (arg && ((*arg & 0xFF) >= quint32(articles().size())))
            fail(QStringLiteral("article %1 does not exist").arg(*arg & 0xFF));
        return {{row->script, bytes, bytesOf(text, bytes)}};
    } catch (const std::exception &e) {
        if (err) *err = QString::fromUtf8(e.what());
        return {};
    }
}

QVector<FileChange> GenoData::addSpawn(const QString &name, int frame, quint32 arg, int *ordinal, QString *err) const {
    if (err) err->clear();
    try {
        const auto *row = rowNamed(rows_, name);
        if (!row) fail("unknown row: " + name);
        if (row->script.isEmpty()) fail("row has no script: " + name);
        const QString conflict = externalError({"workbench.json", project_.gameplay, row->script});
        if (!conflict.isEmpty()) fail(conflict);
        if ((arg & 0xFF) >= quint32(articles().size())) fail(QStringLiteral("article %1 does not exist").arg(arg & 0xFF));
        const auto bytes = scripts_.value(row->script);
        QString error;
        const QString text = GenoAsm::parse(textOf(bytes, row->script)).addSpawn(frame, arg, &error, ordinal);
        if (text.isNull()) fail(row->script + ": " + error);
        return {{row->script, bytes, bytesOf(text, bytes)}};
    } catch (const std::exception &e) {
        if (err) *err = QString::fromUtf8(e.what());
        return {};
    }
}

QVector<FileChange> GenoData::removeSpawn(const QString &name, int ordinal, QString *err) const {
    if (err) err->clear();
    try {
        const auto *row = rowNamed(rows_, name);
        if (!row) fail("unknown row: " + name);
        if (row->script.isEmpty()) fail("row has no script: " + name);
        const QString conflict = externalError({"workbench.json", project_.gameplay, row->script});
        if (!conflict.isEmpty()) fail(conflict);
        const auto bytes = scripts_.value(row->script);
        QString error;
        const QString text = GenoAsm::parse(textOf(bytes, row->script)).removeSpawn(ordinal, &error);
        if (text.isNull()) fail(row->script + ": " + error);
        return {{row->script, bytes, bytesOf(text, bytes)}};
    } catch (const std::exception &e) {
        if (err) *err = QString::fromUtf8(e.what());
        return {};
    }
}
} // namespace wb
