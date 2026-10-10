#include "commands.h"
#include "json_patch.h"
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QRegularExpression>
#include <QResource>
#include <cmath>
#include <exception>
#include <optional>

// Explicitly reference the resource object so static-library consumers retain it.
static void initAttributeSchema() { Q_INIT_RESOURCE(attribute_schema); }

namespace wb {
namespace {
const QJsonObject &fighterSchema() {
    static const QJsonObject schema = [] {
        initAttributeSchema();
        QFile file(":/workbench/geno.schema.json");
        if (!file.open(QIODevice::ReadOnly))
            throw CommandError{t("Attribute schema is unavailable", "El esquema de atributos no está disponible")};
        QJsonParseError error;
        const auto doc = QJsonDocument::fromJson(file.readAll(), &error);
        const auto fighter = doc.object()["properties"].toObject()["fighters"].toObject()["items"].toObject()["properties"].toObject();
        if (error.error != QJsonParseError::NoError || fighter["attributes"].toObject()["properties"].toObject().isEmpty())
            throw CommandError{t("Attribute schema is invalid", "El esquema de atributos no es válido")};
        return fighter;
    }();
    return schema;
}
QJsonObject commonRules() { return fighterSchema()["attributes"].toObject()["properties"].toObject(); }
QJsonObject jumpRules() { return fighterSchema()["jumps"].toObject()["properties"].toObject(); }

struct Source {
    QString path, text;
    QByteArray bytes;
    QJsonObject object, fighter;
    JsonPath fighterPath;
};
QJsonObject optionalObject(const QJsonObject &object, const QString &key, const QString &file) {
    if (object.contains(key) && !object[key].isObject())
        throw CommandError{t("Attribute source %1: %2 must be an object", "Fuente de atributos %1: %2 debe ser un objeto").arg(file, key)};
    return object[key].toObject();
}
void selectFighter(Source &source, const ProjectConfig &config) {
    source.fighter = source.object;
    if (!source.object.contains("fighters")) return;
    if (!source.object["fighters"].isArray())
        throw CommandError{t("Attribute source %1: fighters must be an array", "Fuente de atributos %1: fighters debe ser una lista").arg(source.path)};
    const auto fighters = source.object["fighters"].toArray();
    int selected = -1;
    const QString key = config.modId.isEmpty() ? config.id : config.modId;
    for (int i = 0; i < fighters.size(); ++i) {
        const auto fighter = fighters[i].toObject();
        if (!key.isEmpty() && fighter["define"].toObject()["key"].toString() == key) {
            if (selected >= 0)
                throw CommandError{t("Attribute source %1: duplicate fighter key", "Fuente de atributos %1: clave de luchador duplicada").arg(source.path)};
            selected = i;
        }
    }
    if (selected < 0 && fighters.size() == 1) selected = 0;
    if (selected < 0 || !fighters[selected].isObject())
        throw CommandError{t("Attribute source %1: cannot select the project fighter", "Fuente de atributos %1: no se puede seleccionar el luchador del proyecto").arg(source.path)};
    source.fighter = fighters[selected].toObject();
    source.fighterPath = {"fighters", '#' + QString::number(selected)};
}
Source parseSource(const QString &path, const QByteArray &bytes, const ProjectConfig &config) {
    Source source;
    source.path = path; source.bytes = bytes;
    const auto body = bytes.startsWith("\xEF\xBB\xBF") ? bytes.mid(3) : bytes;
    source.text = QString::fromUtf8(body);
    if (source.text.toUtf8() != body)
        throw CommandError{t("Attribute source %1: invalid UTF-8", "Fuente de atributos %1: UTF-8 no válido").arg(path)};
    QJsonParseError error;
    const auto doc = QJsonDocument::fromJson(body, &error);
    if (error.error != QJsonParseError::NoError || !doc.isObject())
        throw CommandError{t("Attribute source %1: invalid JSON object", "Fuente de atributos %1: objeto JSON no válido").arg(path)};
    // Reject duplicate keys throughout the source before Qt's object lookup collapses them.
    if (!jsonHasUniqueKeys(source.text))
        throw CommandError{t("Attribute source %1: ambiguous or invalid JSON", "Fuente de atributos %1: JSON ambiguo o no válido").arg(path)};
    source.object = doc.object();
    selectFighter(source, config);
    optionalObject(source.fighter, "attributes", path);
    const auto jumps = optionalObject(source.fighter, "jumps", path);
    if (jumps.contains("air_vy") && !jumps["air_vy"].isArray())
        throw CommandError{t("Attribute source %1: jumps.air_vy must be an array", "Fuente de atributos %1: jumps.air_vy debe ser una lista").arg(path)};
    return source;
}
QString fullPath(const QString &path) {
    return path.endsWith(".json") && !path.endsWith(".full.json") ? path.chopped(5) + ".full.json" : QString{};
}
QString workspaceRoot(const QString &project) {
    QDir dir(project);
    do { if (QFileInfo::exists(dir.filePath(".git"))) return dir.absolutePath(); } while (dir.cdUp());
    return project;
}
struct Sources {
    ProjectConfig project;
    Source primary;
    std::optional<Source> full, defaults;
    const Source &effective() const { return full ? *full : primary; }
};
Sources readSources(Session &session) {
    // Inspection never acknowledges hand edits in the session's tracked FileStore.
    FileStore disk(session.files().root());
    Sources sources;
    QString error;
    sources.project = ProjectConfig::load(disk, &error);
    if (!error.isEmpty()) throw CommandError{error};
    const auto path = sources.project.gameplay;
    if (!disk.exists(path))
        throw CommandError{t("Attribute source %1: file not found", "Fuente de atributos %1: archivo no encontrado").arg(path)};
    sources.primary = parseSource(path, disk.read(path), sources.project);
    const auto full = fullPath(path);
    if (sources.primary.fighterPath.isEmpty() && !full.isEmpty() && disk.exists(full))
        sources.full = parseSource(full, disk.read(full), sources.project);
    // Generated values are read-only defaults. Only explicit user overrides go into source.
    QString plan = sources.project.planAbs;
    if (!plan.isEmpty()) {
        plan.replace('\\', '/');
        if (QDir::isRelativePath(plan)) plan = QDir(workspaceRoot(disk.root())).filePath(plan);
    } else if (!sources.project.plan.isEmpty()) {
        plan = QDir(disk.root()).filePath(sources.project.plan);
    }
    if (!plan.isEmpty() && sources.primary.fighterPath.isEmpty()) {
        const QString package = QDir(QFileInfo(plan).absolutePath()).filePath("../geno.json");
        QFile file(QDir::cleanPath(package));
        if (file.exists()) {
            if (!file.open(QIODevice::ReadOnly))
                throw CommandError{t("Attribute defaults %1: cannot read file", "Valores iniciales de atributos %1: no se puede leer el archivo").arg(file.fileName())};
            sources.defaults = parseSource(file.fileName(), file.readAll(), sources.project);
        }
    }
    return sources;
}
struct Field { QJsonObject rule; JsonPath path; };
Field field(const QString &name) {
    const auto common = commonRules();
    if (common.contains(name)) return {common[name].toObject(), {"attributes", name}};
    const auto jumps = jumpRules();
    if (name == "jumps.max") return {jumps["max"].toObject(), {"jumps", "max"}};
    const auto match = QRegularExpression("^jumps\\.air_vy\\.(0|[1-9][0-9]*)$").match(name);
    bool ok = false;
    const int index = match.hasMatch() ? match.captured(1).toInt(&ok) : -1;
    const auto air = jumps["air_vy"].toObject();
    if (ok && index >= 0 && index < air["maxItems"].toInt())
        return {air["items"].toObject(), {"jumps", "air_vy", '#' + QString::number(index)}};
    throw CommandError{t("Unknown fighter attribute: %1", "Atributo de luchador desconocido: %1").arg(name)};
}
void validateValue(const QString &name, const QJsonValue &value, const QJsonObject &rule) {
    const double number = value.toDouble();
    if (!value.isDouble() || !std::isfinite(number))
        throw CommandError{t("Attribute %1 requires a finite number", "El atributo %1 requiere un número finito").arg(name)};
    if (rule["type"].toString() == "integer" && std::trunc(number) != number)
        throw CommandError{t("Attribute %1 requires an integer", "El atributo %1 requiere un entero").arg(name)};
    if ((rule.contains("minimum") && number < rule["minimum"].toDouble()) ||
        (rule.contains("maximum") && number > rule["maximum"].toDouble()))
        throw CommandError{t("Attribute %1 is outside its schema range", "El atributo %1 está fuera del rango de su esquema").arg(name)};
}
QJsonValue valueAt(const Source &source, const Field &field) {
    QJsonValue value(source.fighter);
    for (const auto &step : field.path) {
        if (step.startsWith('#')) {
            const int index = step.mid(1).toInt();
            if (!value.isArray() || index < 0 || index >= value.toArray().size()) return QJsonValue(QJsonValue::Undefined);
            value = value.toArray().at(index);
        } else value = value.toObject().value(step);
        if (value.isUndefined()) break;
    }
    return value;
}
void validateImpulses(const QJsonArray &impulses) {
    const auto rule = jumpRules()["air_vy"].toObject();
    if (impulses.size() > rule["maxItems"].toInt())
        throw CommandError{t("Air-jump impulses exceed the schema limit", "Los impulsos de saltos aéreos superan el límite del esquema")};
    for (int i = 0; i < impulses.size(); ++i)
        validateValue("jumps.air_vy." + QString::number(i), impulses[i], rule["items"].toObject());
}
QJsonArray effectiveImpulses(const Sources &sources) {
    auto jumps = sources.effective().fighter["jumps"].toObject();
    if (!jumps.contains("air_vy") && sources.defaults) jumps = sources.defaults->fighter["jumps"].toObject();
    const auto impulses = jumps["air_vy"].toArray();
    validateImpulses(impulses);
    return impulses;
}
QString group(const QString &name) {
    if (name.contains("landing")) return "landing";
    if (name.startsWith("jumps.") || name.contains("jump") || name.startsWith("hop_")) return "jump";
    if (name.contains("shield") || name.contains("ecb")) return "shield_ecb";
    if (name.startsWith("air") || name == "gravity" || name.contains("fall") || name == "terminal_velocity") return "air";
    if (name.startsWith("walk") || name.startsWith("slow_walk") || name.startsWith("mid_walk") ||
        name.startsWith("fast_walk") || name.startsWith("dash") || name.startsWith("run") ||
        name.startsWith("ground") || name == "max_run_brake_frames" || name == "standing_turn_frames") return "ground";
    return "misc";
}
QString unit(const QString &name) {
    if (name == "jumps.max" || name == "max_jumps") return "count";
    if (name.contains("frames") || name.contains("lag") || name.contains("window") || name == "jump_startup_time") return "frames";
    if (name.contains("accel") || name == "gravity" || name == "aerial_drift_base" || name.contains("friction")) return "Melee units/frame^2";
    if (name.contains("velocity") || name.contains("_vel") || name.contains("air_vy") || name == "air_drift_max") return "Melee units/frame";
    if (name.contains("size") || name.contains("height")) return "Melee units";
    if (name == "weight") return "weight";
    return "scalar";
}
QJsonObject descriptor(const Sources &sources, const QString &name) {
    const auto spec = field(name);
    const Source *owner = &sources.effective();
    auto value = valueAt(*owner, spec);
    const bool impulse = spec.path.size() == 3 && spec.path[1] == "air_vy";
    const bool inherit = !impulse || !owner->fighter["jumps"].toObject().contains("air_vy");
    if (value.isUndefined() && inherit && sources.defaults) {
        owner = &*sources.defaults; value = valueAt(*owner, spec);
    }
    if (!value.isUndefined()) validateValue(name, value, spec.rule);
    const auto null = QJsonValue(QJsonValue::Null);
    return {{"name", name}, {"value", value.isUndefined() ? null : value},
        {"type", spec.rule["type"]}, {"group", group(name)}, {"unit", unit(name)},
        {"description", spec.rule["description"]},
        {"range", QJsonObject{{"minimum", spec.rule.contains("minimum") ? spec.rule["minimum"] : null},
                               {"maximum", spec.rule.contains("maximum") ? spec.rule["maximum"] : null}}},
        {"source_file", value.isUndefined() ? QString{} : owner->path}, {"write_file", sources.primary.path}};
}
QString patchSource(const Source &source, const Field &field, const QJsonValue &value, const QJsonArray &impulses) {
    QString text = source.text, error;
    auto parent = source.fighterPath;
    // Preserve a complete explicit impulse override when creating its source array.
    // No array is synthesized from absent (retail disc) engine defaults.
    // Other object ancestors start empty; surrounding bytes are never reserialized.
    for (int i = 0; i < field.path.size() - 1; ++i) {
        const QString key = field.path[i];
        auto child = parent; child.append(key);
        int start = 0, end = 0;
        if (!jsonFind(text, child, &start, &end)) {
            const bool array = field.path[i + 1].startsWith('#');
            text = jsonInsertKey(text, parent, key, array ? jsonScalar(impulses) : QString("{}"), &error);
            if (text.isNull()) throw CommandError{source.path + ": " + error};
        }
        parent = child;
    }
    auto target = parent; target.append(field.path.last());
    int start = 0, end = 0;
    if (jsonFind(text, target, &start, &end)) {
        text = jsonReplace(text, target, jsonScalar(value), &error);
    } else if (field.path.last().startsWith('#')) {
        // Appending may need an explicit prefix when a local full source has a longer array.
        // Only available authored impulses can fill it; absent engine defaults stay absent.
        if (!jsonFind(text, parent, &start, &end)) throw CommandError{source.path + ": " + error};
        const auto doc = QJsonDocument::fromJson(text.mid(start, end - start).toUtf8());
        auto array = doc.array();
        const int index = field.path.last().mid(1).toInt();
        if (index < array.size() || index > impulses.size())
            throw CommandError{t("Attribute %1: fill earlier air-jump impulses first", "Atributo %1: complete primero los impulsos de saltos aéreos anteriores").arg(field.path.last())};
        // Insert at the closing bracket; existing items, spacing and order stay byte-identical.
        int insert = end - 1;
        while (insert > start + 1 && text.at(insert - 1).isSpace()) --insert;
        QStringList appended;
        for (int i = int(array.size()); i < index; ++i) appended.append(jsonScalar(impulses[i]));
        appended.append(jsonScalar(value));
        text.insert(insert, (array.isEmpty() ? QString{} : QString(", ")) + appended.join(", "));
    } else {
        text = jsonInsertKey(text, parent, field.path.last(), jsonScalar(value), &error);
    }
    if (text.isNull()) throw CommandError{source.path + ": " + error};
    return text;
}
QByteArray encoded(const Source &source, const QString &text) {
    return (source.bytes.startsWith("\xEF\xBB\xBF") ? QByteArray("\xEF\xBB\xBF") : QByteArray{}) + text.toUtf8();
}
void requireUnchanged(Session &session) {
    const auto changes = session.files().externalChanges();
    if (!changes.isEmpty()) throw CommandError{t("changed externally: %1", "cambio externo: %1").arg(changes.first())};
}
} // namespace

void registerAttributeCommands(Session &session) {
    // Establish the edit baseline at registration, including an absent local full source.
    // Later list calls use a separate reader and cannot clear a conflict.
    try {
        QString error;
        const auto project = ProjectConfig::load(session.files(), &error);
        if (error.isEmpty()) {
            session.files().read(project.gameplay);
            const auto full = fullPath(project.gameplay);
            if (!full.isEmpty()) session.files().read(full);
        }
    } catch (const std::exception &) { /* Commands report unreadable sources when called. */ }
    session.registry().add({"list_attributes", t("List fighter attributes", "Listar atributos del luchador"),
        commandSchema(), false, [](const QJsonObject &, CommandContext &ctx) {
            const auto sources = readSources(ctx.session);
            QJsonArray attributes;
            for (const auto &name : commonRules().keys()) attributes.append(descriptor(sources, name));
            attributes.append(descriptor(sources, "jumps.max"));
            const auto impulses = effectiveImpulses(sources);
            const int limit = jumpRules()["air_vy"].toObject()["maxItems"].toInt();
            // One unset slot permits an explicit new impulse, without filling gaps or defaults.
            for (int i = 0; i < limit && i <= impulses.size(); ++i)
                attributes.append(descriptor(sources, "jumps.air_vy." + QString::number(i)));
            return QJsonObject{{"attributes", attributes}};
        }});
    session.registry().add({"edit_attribute", t("Edit a fighter attribute", "Editar un atributo del luchador"),
        commandSchema({{"name", argType("string")}, {"value", argType("number")}, {"propose", argType("boolean")}}, {"name", "value"}), true,
        [](const QJsonObject &args, CommandContext &ctx) {
            requireUnchanged(ctx.session);
            const auto sources = readSources(ctx.session);
            const QString name = args["name"].toString();
            const auto spec = field(name);
            validateValue(name, args["value"], spec.rule);
            const bool airImpulse = spec.path.size() == 3 && spec.path[1] == "air_vy";
            const auto impulses = airImpulse ? effectiveImpulses(sources) : QJsonArray{};
            QVector<FileChange> changes;
            auto patch = [&](const Source &source) {
                if (airImpulse) validateImpulses(source.fighter["jumps"].toObject()["air_vy"].toArray());
                const auto beforeValue = valueAt(source, spec);
                if (beforeValue == args["value"]) return; // Avoid rewriting authored number spellings for a no-op.
                const auto after = encoded(source, patchSource(source, spec, args["value"], impulses));
                if (after != source.bytes) changes.append({source.path, source.bytes, after});
            };
            patch(sources.primary);
            if (sources.full) patch(*sources.full);
            requireUnchanged(ctx.session);
            ctx.propose |= args["propose"].toBool();
            auto result = ctx.session.commit(ctx, "edit_attribute", args,
                t("Edit fighter attribute %1", "Editar atributo del luchador %1").arg(name), changes);
            result["changes"] = changeToJson(changes)["changes"];
            return result;
        }});
}
} // namespace wb
