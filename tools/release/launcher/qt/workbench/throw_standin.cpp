#include "throw_standin.h"
#include "commands.h"
#include "json_patch.h"
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <cmath>
#include <exception>
#include <optional>

namespace wb {
namespace {
// gn_vanilla / gn_retail_kind in melee/pc/platform/geno_registry.c and
// geno_define_registry.inc (geno.md 22.10). Nana cannot be a stand-in.
QJsonArray choices() {
    return {"mario", "fox", "captain", "donkey", "kirby", "koopa", "link",
        "seak", "ness", "peach", "popo", "pikachu", "samus", "yoshi",
        "purin", "mewtwo", "luigi", "mars", "zelda", "clink", "drmario",
        "falco", "pichu", "gamewatch", "ganon", "emblem"};
}
QString canonical(const QString &value) {
    const QString token = value.toLower();
    if (choices().contains(token)) return token;
    static const QHash<QString, QString> aliases{
        {"falcon", "captain"}, {"dk", "donkey"}, {"bowser", "koopa"},
        {"sheik", "seak"}, {"jigglypuff", "purin"}, {"marth", "mars"},
        {"younglink", "clink"}, {"gnw", "gamewatch"}, {"ganondorf", "ganon"}, {"roy", "emblem"}};
    return aliases.value(token);
}
struct Source {
    QString path, text;
    QByteArray bytes;
    QJsonObject object, fighter;
    JsonPath fighterPath;
};
QString fullPath(const QString &path) {
    return path.endsWith(".json") && !path.endsWith(".full.json") ? path.chopped(5) + ".full.json" : QString{};
}
Source parse(const QString &path, const QByteArray &bytes, const ProjectConfig &project) {
    Source source;
    source.path = path; source.bytes = bytes;
    const auto body = bytes.startsWith("\xEF\xBB\xBF") ? bytes.mid(3) : bytes;
    source.text = QString::fromUtf8(body);
    if (source.text.toUtf8() != body)
        throw CommandError{t("Throw stand-in source %1: invalid UTF-8", "Fuente del sustituto de lanzamiento %1: UTF-8 no válido").arg(path)};
    QJsonParseError error;
    const auto document = QJsonDocument::fromJson(body, &error);
    if (error.error != QJsonParseError::NoError || !document.isObject() || !jsonHasUniqueKeys(source.text))
        throw CommandError{t("Throw stand-in source %1: invalid or ambiguous JSON object", "Fuente del sustituto de lanzamiento %1: objeto JSON no válido o ambiguo").arg(path)};
    source.object = document.object(); source.fighter = source.object;
    if (!source.object.contains("fighters")) return source;
    if (!source.object["fighters"].isArray())
        throw CommandError{t("Throw stand-in source %1: fighters must be an array", "Fuente del sustituto de lanzamiento %1: fighters debe ser una lista").arg(path)};
    const auto fighters = source.object["fighters"].toArray();
    const QString key = project.modId.isEmpty() ? project.id : project.modId;
    int selected = -1;
    for (int i = 0; i < fighters.size(); ++i) {
        if (!key.isEmpty() && fighters[i].toObject()["define"].toObject()["key"].toString() == key) {
            if (selected >= 0)
                throw CommandError{t("Throw stand-in source %1: duplicate fighter key", "Fuente del sustituto de lanzamiento %1: clave de luchador duplicada").arg(path)};
            selected = i;
        }
    }
    if (selected < 0 && fighters.size() == 1) selected = 0;
    if (selected < 0 || !fighters[selected].isObject())
        throw CommandError{t("Throw stand-in source %1: cannot select the project fighter", "Fuente del sustituto de lanzamiento %1: no se puede seleccionar el luchador del proyecto").arg(path)};
    source.fighter = fighters[selected].toObject();
    source.fighterPath = {"fighters", '#' + QString::number(selected)};
    return source;
}
QString workspaceRoot(const QString &project) {
    QDir dir(project);
    do { if (QFileInfo::exists(dir.filePath(".git"))) return dir.absolutePath(); } while (dir.cdUp());
    return project;
}
struct Sources {
    Source primary;
    std::optional<Source> full, defaults;
    const Source &effective() const { return full ? *full : primary; }
};
Sources readSources(Session &session) {
    // A separate reader never acknowledges external edits to the session baseline.
    FileStore disk(session.files().root());
    QString error;
    const auto project = ProjectConfig::load(disk, &error);
    if (!error.isEmpty()) throw CommandError{error};
    if (!disk.exists(project.gameplay))
        throw CommandError{t("Throw stand-in source %1: file not found", "Fuente del sustituto de lanzamiento %1: archivo no encontrado").arg(project.gameplay)};
    Sources sources;
    sources.primary = parse(project.gameplay, disk.read(project.gameplay), project);
    const auto full = fullPath(project.gameplay);
    if (sources.primary.fighterPath.isEmpty() && !full.isEmpty() && disk.exists(full)) {
        sources.full = parse(full, disk.read(full), project);
        if (!sources.full->fighterPath.isEmpty())
            throw CommandError{t("Throw stand-in source %1: the full source must use the same flat authoring format", "Fuente del sustituto de lanzamiento %1: la fuente completa debe usar el mismo formato de autoría plano").arg(full)};
    }
    if (!sources.primary.fighterPath.isEmpty()) return sources;
    QString plan = project.planAbs;
    if (!plan.isEmpty()) {
        plan.replace('\\', '/');
        if (QDir::isRelativePath(plan)) plan = QDir(workspaceRoot(disk.root())).filePath(plan);
    } else if (!project.plan.isEmpty()) plan = QDir(disk.root()).filePath(project.plan);
    if (!plan.isEmpty()) {
        QFile package(QDir::cleanPath(QDir(QFileInfo(plan).absolutePath()).filePath("../geno.json")));
        if (package.exists()) {
            if (!package.open(QIODevice::ReadOnly))
                throw CommandError{t("Throw stand-in defaults %1: cannot read file", "Valores iniciales del sustituto de lanzamiento %1: no se puede leer el archivo").arg(package.fileName())};
            sources.defaults = parse(package.fileName(), package.readAll(), project);
        }
    }
    return sources;
}
QJsonObject unavailable(const QString &reason, const QString &value = {}) {
    return {{"value", value}, {"choices", choices()}, {"editable", false}, {"note", reason}};
}
QString invalidValue(const Source &source) {
    if (!source.fighter.contains("thrown_as")) return {};
    const auto value = source.fighter["thrown_as"];
    if (!value.isString() || canonical(value.toString()).isEmpty())
        return t("Throw stand-in source %1: thrown_as must name a supported retail fighter other than Nana", "Fuente del sustituto de lanzamiento %1: thrown_as debe nombrar un luchador comercial compatible que no sea Nana").arg(source.path);
    return {};
}
QJsonObject describe(const Sources &sources) {
    // Both authored files must be valid even when the full source overrides the primary.
    for (const auto *source : {&sources.primary, sources.full ? &*sources.full : nullptr}) {
        if (!source) continue;
        const QString error = invalidValue(*source);
        if (!error.isEmpty()) return unavailable(error, source->fighter["thrown_as"].toString());
    }
    const Source *owner = &sources.effective();
    if (!owner->fighter.contains("thrown_as") && sources.defaults) owner = &*sources.defaults;
    const QString error = invalidValue(*owner);
    if (!error.isEmpty()) return unavailable(error, owner->fighter["thrown_as"].toString());
    const QString authored = owner->fighter.contains("thrown_as") ? owner->fighter["thrown_as"].toString() : QString("captain");
    const QString value = canonical(authored);
    const auto &primary = sources.primary;
    if (!primary.fighterPath.isEmpty()) {
        if (!primary.fighter["define"].isObject() || primary.fighter["define"].toObject()["base"].toString() != "none")
            return unavailable(t("Throw stand-ins require a define with base none", "Los sustitutos de lanzamiento requieren una definición con base none"), value);
        const auto version = primary.object["geno"];
        if (!version.isDouble() || !std::isfinite(version.toDouble()) || std::floor(version.toDouble()) != version.toDouble() || version.toDouble() < 10)
            return unavailable(t("Throw stand-ins require Geno format 10 or later", "Los sustitutos de lanzamiento requieren el formato Geno 10 o posterior"), value);
    } else if (sources.defaults && (!sources.defaults->fighter["define"].isObject() || sources.defaults->fighter["define"].toObject()["base"].toString() != "none")) {
        return unavailable(t("The built project fighter is not a define with base none", "El luchador compilado del proyecto no es una definición con base none"), value);
    }
    QString note = t("Retail victims use this fighter's thrown animations. Rebuild to apply the source setting.", "Las víctimas comerciales usan las animaciones de lanzamiento de este luchador. Vuelve a compilar para aplicar el ajuste de la fuente.");
    if (authored != value)
        note += ' ' + t("Authored alias: %1", "Alias de autoría: %1").arg(authored);
    return {{"value", value}, {"choices", choices()}, {"editable", true}, {"note", note}};
}
void requireUnchanged(Session &session) {
    const auto changes = session.files().externalChanges();
    if (!changes.isEmpty()) throw CommandError{t("changed externally: %1", "changed externally: %1").arg(changes.first())};
}
FileChange patch(const Source &source, const QString &value) {
    auto target = source.fighterPath; target.append("thrown_as");
    QString error;
    int start = 0, end = 0;
    const QString text = jsonFind(source.text, target, &start, &end)
        ? jsonReplace(source.text, target, jsonScalar(value), &error)
        : jsonInsertKey(source.text, source.fighterPath, "thrown_as", jsonScalar(value), &error);
    if (text.isNull()) throw CommandError{source.path + ": " + error};
    const auto bytes = (source.bytes.startsWith("\xEF\xBB\xBF") ? QByteArray("\xEF\xBB\xBF") : QByteArray{}) + text.toUtf8();
    return {source.path, source.bytes, bytes};
}
} // namespace

QJsonObject throwStandIn(Session &session) {
    try { return describe(readSources(session)); }
    catch (const CommandError &error) { return unavailable(error.message); }
    catch (const std::exception &error) { return unavailable(QString::fromUtf8(error.what())); }
}
void registerThrowStandInCommands(Session &session) {
    // Track missing mirrors as well, so a later list cannot clear an external-file conflict.
    try {
        QString error;
        const auto project = ProjectConfig::load(session.files(), &error);
        if (error.isEmpty()) {
            session.files().read(project.gameplay);
            const auto full = fullPath(project.gameplay);
            if (!full.isEmpty()) session.files().read(full);
        }
    } catch (const std::exception &) { /* Inspection reports the read error. */ }
    session.registry().add({"list_throw_standin", t("List the throw animation stand-in", "Listar el sustituto de animaciones de lanzamiento"),
        commandSchema(), false, [](const QJsonObject &, CommandContext &ctx) { return throwStandIn(ctx.session); }});
    session.registry().add({"edit_throw_standin", t("Edit the throw animation stand-in", "Editar el sustituto de animaciones de lanzamiento"),
        commandSchema({{"value", QJsonObject{{"type", "string"}, {"enum", choices()}}}, {"propose", argType("boolean")}}, {"value"}), true,
        [](const QJsonObject &args, CommandContext &ctx) {
            requireUnchanged(ctx.session);
            const auto sources = readSources(ctx.session);
            const auto descriptor = describe(sources);
            if (!descriptor["editable"].toBool()) throw CommandError{descriptor["note"].toString()};
            const QString value = args["value"].toString();
            if (!args["value"].isString() || !choices().contains(value))
                throw CommandError{t("Unknown throw animation stand-in: %1", "Sustituto de animaciones de lanzamiento desconocido: %1").arg(value)};
            QVector<FileChange> changes;
            auto add = [&](const Source &source) {
                // An inherited default still needs an explicit authored override.
                if (source.fighter["thrown_as"] == args["value"]) return;
                auto change = patch(source, value);
                if (change.before != change.after) changes.append(change);
            };
            add(sources.primary); if (sources.full) add(*sources.full);
            requireUnchanged(ctx.session);
            ctx.propose |= args["propose"].toBool();
            auto result = ctx.session.commit(ctx, "edit_throw_standin", args,
                t("Edit throw animation stand-in to %1", "Editar el sustituto de animaciones de lanzamiento a %1").arg(value), changes);
            result["changes"] = changeToJson(changes)["changes"];
            return result;
        }});
}
}
