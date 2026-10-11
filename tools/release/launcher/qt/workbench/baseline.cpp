#include "commands.h"
#include <QDir>
#include <QDirIterator>
#include <QFile>
#include <QFileInfo>
#include <QSet>
#include <cmath>

// "Changed since last build": the baseline is a mirror of the source files as of the last successful
// rebuild (or, before any rebuild, as of the first open), kept under <project>/.workbench/baseline.
// Differences are computed by reading the mirror with a second, engine-less Session.
namespace wb {
namespace {
QString mirrorDir(Session &s) { return QDir(s.files().root()).filePath(".workbench/baseline"); }
QString fullSibling(const QString &path) {
    return path.endsWith(".json") && !path.endsWith(".full.json") ? path.chopped(5) + ".full.json" : QString{};
}
QStringList sourcePaths(Session &s) {
    QSet<QString> out{"workbench.json"};
    FileStore reader(s.files().root());
    QString error;
    const auto project = ProjectConfig::load(reader, &error);
    if (!error.isEmpty()) return {};
    for (const auto &path : {project.gameplay, fullSibling(project.gameplay), project.fidelity, project.plan, project.combo})
        if (!path.isEmpty()) out.insert(path);
    for (const auto &row : s.data().rows()) if (!row.script.isEmpty()) out.insert(row.script);
    if (!project.movesDir.isEmpty()) {
        const QDir root(s.files().root());
        QDirIterator it(root.filePath(project.movesDir), QDir::Files, QDirIterator::Subdirectories);
        while (it.hasNext()) out.insert(root.relativeFilePath(it.next()));
    }
    auto list = QStringList(out.begin(), out.end());
    list.sort();
    return list;
}
bool same(const QJsonValue &a, const QJsonValue &b) {
    if (a.isDouble() && b.isDouble()) return std::fabs(a.toDouble() - b.toDouble()) < 1e-9;
    return a == b;
}
QJsonValue editValue(const QString &field, const QJsonObject &hitbox) {
    if (field == "bone") return hitbox.value("joint");
    return hitbox.value(field);
}
const QStringList &hitboxFields() {
    static const QStringList fields{"bone", "start_frame", "end_frame", "damage", "size", "angle", "kbg", "bkb", "fkb",
                                    "x", "y", "z", "element", "shield", "slot", "ground", "air"};
    return fields;
}
QJsonObject attributesByName(Session &s) {
    QJsonObject out;
    CommandContext ctx{s};
    const auto reply = s.registry().call("list_attributes", {}, ctx);
    if (!reply.value("ok").toBool()) return out;
    for (const auto &entry : reply.value("result").toObject().value("attributes").toArray()) {
        const auto descriptor = entry.toObject();
        out.insert(descriptor.value("name").toString(), descriptor.value("value"));
    }
    return out;
}
} // namespace

void captureBaseline(Session &s) {
    s.baselineSession.reset();
    QDir(mirrorDir(s)).removeRecursively();
    for (const auto &rel : sourcePaths(s)) {
        const QString from = QDir(s.files().root()).filePath(rel);
        if (!QFileInfo(from).isFile()) continue;
        const QString to = QDir(mirrorDir(s)).filePath(rel);
        QDir().mkpath(QFileInfo(to).absolutePath());
        QFile::remove(to);
        QFile::copy(from, to);
    }
}
Session *baselineSession(Session &s) {
    if (s.baselineSession) return s.baselineSession.get();
    if (!QFileInfo(QDir(mirrorDir(s)).filePath("workbench.json")).isFile()) captureBaseline(s);
    if (!QFileInfo(QDir(mirrorDir(s)).filePath("workbench.json")).isFile()) return nullptr;
    auto base = std::make_unique<Session>(mirrorDir(s), nullptr);
    registerAllCommands(*base);
    if (!base->data().reload().isEmpty()) return nullptr;
    s.baselineSession = std::move(base);
    return s.baselineSession.get();
}
QJsonArray baselineChanges(Session &s) {
    QJsonArray out;
    Session *base = baselineSession(s);
    if (!base) return out;
    QSet<QString> baseRows;
    for (const auto &row : base->data().rows()) baseRows.insert(row.name);
    for (const auto &row : s.data().rows()) {
        if (!baseRows.contains(row.name)) continue;
        const auto was = base->data().hitboxes(row.name), now = s.data().hitboxes(row.name);
        for (int i = 0; i < qMin(was.size(), now.size()); ++i) {
            const auto a = hitboxJson(was[i]), b = hitboxJson(now[i]);
            for (const auto &field : hitboxFields()) {
                const auto before = editValue(field, a), after = editValue(field, b);
                if (!same(before, after))
                    out.append(QJsonObject{{"kind", "hitbox"}, {"row", row.name}, {"ordinal", i}, {"field", field}, {"was", before}, {"now", after}});
            }
        }
        if (was.size() != now.size())
            out.append(QJsonObject{{"kind", "hitboxes"}, {"row", row.name}, {"ordinal", -1}, {"field", ""}, {"was", was.size()}, {"now", now.size()}});
    }
    // Combo routes: matched by name (the file's own key), then field by field.
    {
        const auto was = base->data().routes(), now = s.data().routes();
        QHash<QString, QJsonObject> byName;
        for (const auto &v : was) byName.insert(v.toObject().value("name").toString(), v.toObject());
        static const QStringList routeFields{"from", "to", "input", "dir", "on", "where", "window", "buffer", "hold", "priority",
                                             "ki_cost", "ki_min", "depth", "once", "starts", "source"};
        for (const auto &v : now) {
            const auto route = v.toObject();
            const QString name = route.value("name").toString();
            if (!byName.contains(name)) continue;
            const auto old = byName.value(name);
            for (const auto &field : routeFields)
                if (!same(old.value(field), route.value(field)))
                    out.append(QJsonObject{{"kind", "route"}, {"row", name}, {"ordinal", route.value("index").toInt()}, {"field", field},
                                           {"was", old.value(field)}, {"now", route.value(field)}});
        }
        if (was.size() != now.size())
            out.append(QJsonObject{{"kind", "routes"}, {"row", ""}, {"ordinal", -1}, {"field", ""}, {"was", was.size()}, {"now", now.size()}});
    }
    try {
        const auto was = attributesByName(*base), now = attributesByName(s);
        for (auto it = now.begin(); it != now.end(); ++it)
            if (was.contains(it.key()) && !same(was.value(it.key()), it.value()))
                out.append(QJsonObject{{"kind", "attribute"}, {"name", it.key()}, {"field", it.key()}, {"row", ""}, {"ordinal", -1},
                                       {"was", was.value(it.key())}, {"now", it.value()}});
    } catch (...) { /* attributes unavailable: hitbox changes still report */ }
    return out;
}

namespace {
QJsonObject revertChange(Session &s, const QJsonObject &args, CommandContext &ctx) {
    Session *base = baselineSession(s);
    if (!base) throw CommandError{t("No build baseline is available", "No hay una base de compilación disponible")};
    const QString kind = args.value("kind").toString();
    QJsonObject call;
    QString command;
    if (kind == "hitbox") {
        const QString row = args.value("row").toString(), field = args.value("field").toString();
        const int ordinal = args.value("ordinal").toInt(-1);
        const auto was = base->data().hitboxes(row);
        if (ordinal < 0 || ordinal >= was.size() || !hitboxFields().contains(field))
            throw CommandError{t("Nothing to revert for that field", "No hay nada que revertir en ese campo")};
        auto value = editValue(field, hitboxJson(was[ordinal]));
        if (field == "ground" || field == "air") value = value.toBool();
        command = "edit_hitbox"; call = {{"row", row}, {"ordinal", ordinal}, {field, value}};
    } else if (kind == "attribute") {
        const QString name = args.value("name").toString();
        const auto was = attributesByName(*base);
        if (!was.contains(name) || !was.value(name).isDouble())
            throw CommandError{t("This attribute was unset in the built game; use Revert all", "Este atributo no estaba definido en el juego; usa Revertir todo")};
        command = "edit_attribute"; call = {{"name", name}, {"value", was.value(name)}};
    } else if (kind == "route") {
        const QString name = args.value("row").toString(), field = args.value("field").toString();
        QJsonObject old;
        for (const auto &v : base->data().routes()) if (v.toObject().value("name").toString() == name) old = v.toObject();
        int index = -1;
        for (const auto &v : s.data().routes()) if (v.toObject().value("name").toString() == name) index = v.toObject().value("index").toInt();
        if (index < 0 || old.isEmpty() || !old.contains(field))
            throw CommandError{t("This route field was unset in the built game; use Revert all", "Este campo no estaba definido en el juego; usa Revertir todo")};
        command = "edit_route"; call = {{"index", index}, {field, old.value(field)}};
    } else if (kind == "routes") {
        const int baseCount = base->data().routes().size(), nowCount = s.data().routes().size();
        if (nowCount <= baseCount) throw CommandError{t("A removed route can only be restored with Revert all", "Una ruta borrada solo se restaura con Revertir todo")};
        command = "delete_route"; call = {{"index", nowCount - 1}};
    } else if (kind == "hitboxes") {
        // A hitbox was added: delete the extras, newest first. A removed hitbox needs Revert all.
        const QString row = args.value("row").toString();
        const int baseCount = base->data().hitboxes(row).size(), nowCount = s.data().hitboxes(row).size();
        if (nowCount <= baseCount) throw CommandError{t("A removed hitbox can only be restored with Revert all", "Un hitbox borrado solo se restaura con Revertir todo")};
        command = "delete_hitbox"; call = {{"row", row}, {"ordinal", nowCount - 1}};
    } else throw CommandError{t("Unknown change kind", "Tipo de cambio desconocido")};
    const auto reply = s.registry().call(command, call, ctx);
    if (!reply.value("ok").toBool()) throw CommandError{reply.value("error").toString()};
    return reply.value("result").toObject();
}
QJsonObject revertAll(Session &s, CommandContext &ctx) {
    Session *base = baselineSession(s);
    if (!base) throw CommandError{t("No build baseline is available", "No hay una base de compilación disponible")};
    QVector<FileChange> changes;
    for (const auto &rel : sourcePaths(s)) {
        if (rel == "workbench.json") continue;
        const QString from = QDir(mirrorDir(s)).filePath(rel);
        if (!QFileInfo(from).isFile()) continue;
        QFile file(from); if (!file.open(QIODevice::ReadOnly)) continue;
        const QByteArray baseline = file.readAll();
        const QByteArray current = s.files().exists(rel) ? s.files().read(rel) : QByteArray{};
        if (current != baseline) changes.append({rel, current, baseline});
    }
    return s.commit(ctx, "revert_all", {}, t("Revert all changes since the last build", "Revertir todos los cambios desde la última compilación"), changes);
}
} // namespace

void registerBaselineCommands(Session &session) {
    session.registry().add({"list_changes", t("List fields changed since the last build", "Listar campos cambiados desde la última compilación"),
        commandSchema(), false, [](const QJsonObject &, CommandContext &ctx) {
            const auto changes = baselineChanges(ctx.session);
            return QJsonObject{{"changes", changes}, {"count", changes.size()}};
        }});
    session.registry().add({"revert_change", t("Restore one field to its last-built value", "Restaurar un campo a su valor compilado"),
        commandSchema({{"kind", argType("string")}, {"row", argType("string")}, {"ordinal", argType("integer")},
                       {"field", argType("string")}, {"name", argType("string")}}, {"kind"}), true,
        [](const QJsonObject &args, CommandContext &ctx) { return revertChange(ctx.session, args, ctx); }});
    session.registry().add({"revert_all", t("Restore every changed field to its last-built value", "Restaurar todos los campos a su valor compilado"),
        commandSchema(), true, [](const QJsonObject &, CommandContext &ctx) { return revertAll(ctx.session, ctx); }});
}
} // namespace wb
