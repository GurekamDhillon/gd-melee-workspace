#include "combo_model.h"
#include "geno_data.h"
#include "json_patch.h"
#include <QJsonDocument>
#include <stdexcept>

// The combo graph of the project's combo file (geno.md 25): GenoData owns the cached bytes; these members only build
// FileChanges (one targeted text edit each, so the file's layout and every other byte survive), and every edit goes
// through Session::commit like a hitbox edit: history, undo, propose, and the changed-since-build baseline.
namespace wb {
namespace {
[[noreturn]] void fail(const QString &message) { throw std::runtime_error(message.toUtf8().constData()); }
bool hasBom(const QByteArray &bytes) { return bytes.startsWith("\xEF\xBB\xBF"); }
QByteArray bytesOf(const QString &text, const QByteArray &original) {
    return (hasBom(original) ? QByteArray("\xEF\xBB\xBF") : QByteArray()) + text.toUtf8();
}
JsonPath join(const QStringList &base, const QStringList &rest) { JsonPath p = base; p << rest; return p; }
bool exists(const QString &text, const JsonPath &path) { int s, e; return jsonFind(text, path, &s, &e); }
// Set key `key` of the object at `object`: replace it, or insert it. Same-size arrays of scalars (a window) are
// replaced element by element so the file's own array layout is kept.
QString setKey(QString text, const JsonPath &object, const QString &key, const QJsonValue &now, const QJsonValue &was, QString *err) {
    QString e;
    const JsonPath path = join(object, {key});
    if (!exists(text, path)) {
        const QString out = jsonInsertKey(text, object, key, jsonScalar(now), &e);
        if (out.isNull()) fail(e);
        return out;
    }
    if (now.isArray() && was.isArray() && now.toArray().size() == was.toArray().size() && !now.toArray().isEmpty() &&
        !now.toArray()[0].isObject() && !now.toArray()[0].isArray()) {
        for (int i = 0; i < now.toArray().size(); ++i) {
            if (now.toArray()[i] == was.toArray()[i]) continue;
            const QString out = jsonReplace(text, join(path, {QString("#%1").arg(i)}), jsonScalar(now.toArray()[i]), &e);
            if (out.isNull()) fail(e);
            text = out;
        }
        return text;
    }
    const QString out = jsonReplace(text, path, jsonScalar(now), &e);
    if (out.isNull()) fail(e);
    (void)err;
    return out;
}
} // namespace

QStringList GenoData::comboBase() const {
    const auto root = QJsonDocument::fromJson(comboText_.toUtf8()).object();
    return root.value("combo").isObject() ? QStringList{"combo"} : QStringList{};
}
QJsonObject GenoData::comboBlock() const {
    const auto root = QJsonDocument::fromJson(comboText_.toUtf8()).object();
    return root.value("combo").isObject() ? root.value("combo").toObject() : root;
}
QJsonObject GenoData::comboMeta() const {
    auto block = comboBlock();
    block.remove("routes"); block.remove("strings");
    return block;
}
static QJsonArray indexed(const QJsonArray &list) {
    QJsonArray out;
    for (int i = 0; i < list.size(); ++i) { auto o = list[i].toObject(); o["index"] = i; out.append(o); }
    return out;
}
QJsonArray GenoData::routes() const { return indexed(comboBlock().value("routes").toArray()); }
QJsonArray GenoData::comboStates() const {
    return QJsonDocument::fromJson(comboText_.toUtf8()).object().value("states").toArray();
}
QString GenoData::comboDir() const {
    const int slash = project_.combo.lastIndexOf('/');
    return slash < 0 ? QString() : project_.combo.left(slash);
}
QJsonArray GenoData::strings() const { return indexed(comboBlock().value("strings").toArray()); }

QVector<FileChange> GenoData::editComboItem(const QString &list, int index, const QJsonObject &fields, QString *err) const {
    if (err) err->clear();
    try {
        if (!hasCombo()) fail(QStringLiteral("project has no combo file"));
        const QString conflict = externalError({"workbench.json", project_.combo});
        if (!conflict.isEmpty()) fail(conflict);
        const auto items = comboBlock().value(list).toArray();
        if (index < 0 || index >= items.size()) fail(QStringLiteral("unknown %1: %2").arg(list == "routes" ? "route" : "string").arg(index));
        const auto was = items[index].toObject();
        auto merged = was;
        for (auto it = fields.begin(); it != fields.end(); ++it) {
            if (it.key() == "index") continue;
            merged[it.key()] = it.value();
        }
        const QString problem = list == "routes" ? validateComboRoute(merged) : validateComboString(merged);
        if (!problem.isEmpty()) fail(problem);
        QString text = comboText_;
        const JsonPath item = join(comboBase(), {list, QString("#%1").arg(index)});
        for (auto it = fields.begin(); it != fields.end(); ++it) {
            if (it.key() == "index" || was.value(it.key()) == it.value()) continue;
            text = setKey(text, item, it.key(), it.value(), was.value(it.key()), err);
        }
        if (text == comboText_) return {};
        return {{project_.combo, comboBytes_, bytesOf(text, comboBytes_)}};
    } catch (const std::exception &e) {
        if (err) *err = QString::fromUtf8(e.what());
        return {};
    }
}
QVector<FileChange> GenoData::addComboItem(const QString &list, const QJsonObject &item, int *index, QString *err) const {
    if (err) err->clear();
    try {
        if (!hasCombo()) fail(QStringLiteral("project has no combo file"));
        const QString conflict = externalError({"workbench.json", project_.combo});
        if (!conflict.isEmpty()) fail(conflict);
        const QString problem = list == "routes" ? validateComboRoute(item) : validateComboString(item);
        if (!problem.isEmpty()) fail(problem);
        QJsonObject clean = item;
        clean.remove("index");
        const int count = int(comboBlock().value(list).toArray().size());
        QString e, text = comboText_;
        const JsonPath array = join(comboBase(), {list});
        if (exists(text, array)) text = jsonArrayInsert(text, array, count, clean, &e);
        else text = jsonInsertKey(text, comboBase(), list, jsonScalar(QJsonArray{clean}), &e);
        if (text.isNull()) fail(e);
        if (index) *index = count;
        return {{project_.combo, comboBytes_, bytesOf(text, comboBytes_)}};
    } catch (const std::exception &e) {
        if (err) *err = QString::fromUtf8(e.what());
        return {};
    }
}
QVector<FileChange> GenoData::removeComboItem(const QString &list, int index, QString *err) const {
    if (err) err->clear();
    try {
        if (!hasCombo()) fail(QStringLiteral("project has no combo file"));
        const QString conflict = externalError({"workbench.json", project_.combo});
        if (!conflict.isEmpty()) fail(conflict);
        const int count = int(comboBlock().value(list).toArray().size());
        if (index < 0 || index >= count) fail(QStringLiteral("unknown %1: %2").arg(list == "routes" ? "route" : "string").arg(index));
        QString e;
        const QString text = jsonArrayRemove(comboText_, join(comboBase(), {list}), index, &e);
        if (text.isNull()) fail(e);
        return {{project_.combo, comboBytes_, bytesOf(text, comboBytes_)}};
    } catch (const std::exception &e) {
        if (err) *err = QString::fromUtf8(e.what());
        return {};
    }
}
QVector<FileChange> GenoData::editRoute(int index, const QJsonObject &fields, QString *err) const { return editComboItem("routes", index, fields, err); }
QVector<FileChange> GenoData::addRoute(const QJsonObject &route, int *index, QString *err) const { return addComboItem("routes", route, index, err); }
QVector<FileChange> GenoData::removeRoute(int index, QString *err) const { return removeComboItem("routes", index, err); }
QVector<FileChange> GenoData::editString(int index, const QJsonObject &fields, QString *err) const { return editComboItem("strings", index, fields, err); }
QVector<FileChange> GenoData::addString(const QJsonObject &str, int *index, QString *err) const { return addComboItem("strings", str, index, err); }
QVector<FileChange> GenoData::removeString(int index, QString *err) const { return removeComboItem("strings", index, err); }
} // namespace wb
