#include "commands.h"
#include "json_patch.h"
#include <QJsonDocument>

namespace wb {
namespace {
const QString groundFile = QStringLiteral("ground_modes.json");
const QString emptyGround = QStringLiteral(
    "{\n  \"schema\": \"ground-modes/1\",\n  \"rows\": {},\n  \"grounded_clips\": []\n}\n");

bool hasBom(const QByteArray &bytes) { return bytes.startsWith("\xEF\xBB\xBF"); }
QString sourceText(const QByteArray &bytes, const QString &path) {
    const QByteArray body = hasBom(bytes) ? bytes.mid(3) : bytes;
    const QString text = QString::fromUtf8(body);
    if (text.toUtf8() != body)
        throw CommandError{t("%1: invalid UTF-8", "%1: invalid UTF-8").arg(path)};
    return text;
}
QJsonObject parseObject(const QString &text, const QString &path) {
    QJsonParseError error;
    const auto document = QJsonDocument::fromJson(text.toUtf8(), &error);
    if (error.error != QJsonParseError::NoError)
        throw CommandError{t("%1: %2 at offset %3", "%1: %2 at offset %3")
            .arg(path, error.errorString()).arg(error.offset)};
    if (!document.isObject())
        throw CommandError{t("%1: expected an object", "%1: expected an object").arg(path)};
    return document.object();
}
void requireUnchanged(Session &session) {
    const auto external = session.files().externalChanges();
    if (!external.isEmpty())
        throw CommandError{t("changed externally: %1", "changed externally: %1").arg(external.first())};
}
void needGroundRow(Session &session, const QString &name) {
    auto &data = session.data();
    if (!name.isEmpty()) {
        for (const auto &row : data.rows()) if (row.name == name) return;
        // GenoData exposes the configured fidelity path, but not its cached
        // fidelity rows. Read that existing source with a separate reader so
        // validation cannot acknowledge hand edits in the session's FileStore.
        const QString fidelity = data.project().fidelity;
        if (!fidelity.isEmpty()) {
            FileStore disk(session.files().root());
            if (disk.exists(fidelity)) {
                const auto ledger = parseObject(sourceText(disk.read(fidelity), fidelity), fidelity);
                for (const auto &value : ledger["rows"].toArray())
                    if (value.toObject()["row"].toString() == name) return;
            }
        }
    }
    throw CommandError{t("unknown row: %1", "unknown row: %1").arg(name)};
}
struct GroundSource {
    QByteArray before;
    QString text;
    QJsonObject rows;
};
GroundSource readGround(Session &session) {
    // Reads must not change the session's tracked version. In particular, a
    // get after a hand edit must not silently enable the next set/commit.
    FileStore disk(session.files().root());
    GroundSource source;
    source.before = disk.read(groundFile);
    source.text = disk.exists(groundFile)
        ? sourceText(source.before, groundFile) : emptyGround;
    const auto object = parseObject(source.text, groundFile);
    if (object["schema"].toString() != "ground-modes/1")
        throw CommandError{t("%1: unsupported schema", "%1: unsupported schema").arg(groundFile)};
    if (!object["rows"].isObject())
        throw CommandError{t("%1: rows must be an object", "%1: rows must be an object").arg(groundFile)};
    int start = 0, end = 0;
    if (!jsonFind(source.text, {"rows"}, &start, &end))
        throw CommandError{t("%1: invalid or ambiguous rows", "%1: invalid or ambiguous rows").arg(groundFile)};
    source.rows = object["rows"].toObject();
    return source;
}
QString patchField(const QString &text, const QString &row, const QString &key,
                   const QJsonValue &value, bool exists) {
    QString error;
    const QString changed = exists
        ? jsonReplace(text, {"rows", row, key}, jsonScalar(value), &error)
        : jsonInsertKey(text, {"rows", row}, key, jsonScalar(value), &error);
    if (changed.isNull()) throw CommandError{groundFile + ": " + error};
    return changed;
}
} // namespace

void registerGroundCommands(Session &session) {
    // Track the initial disk version without creating the optional file.
    session.files().read(groundFile);
    session.registry().add({"set_ground_mode", t("Set a row's ground mode", "Set a row's ground mode"),
        commandSchema({{"row", argType("string")},
            {"mode", QJsonObject{{"type", "string"}, {"enum", QJsonArray{"hover", "anchored", "none"}}}},
            {"blend_in", argType("boolean")}, {"blend_out", argType("boolean")}}, {"row", "mode"}), true,
        [](const QJsonObject &args, CommandContext &ctx) {
            auto &session = ctx.session;
            // An applied commit reloads GenoData. Do not let that refresh
            // acknowledge unrelated source edits while changing ground modes.
            requireUnchanged(session);
            const QString row = args["row"].toString();
            needGroundRow(session, row);
            auto source = readGround(session);
            if (source.rows.contains(row)) {
                if (!source.rows[row].isObject())
                    throw CommandError{t("%1: row %2 must be an object", "%1: row %2 must be an object")
                        .arg(groundFile, row)};
                const auto existing = source.rows[row].toObject();
                for (const char *key : {"mode", "blend_in", "blend_out"}) {
                    if (!args.contains(key) || existing.value(key) == args.value(key)) continue;
                    source.text = patchField(source.text, row, QString::fromUtf8(key),
                                             args.value(key), existing.contains(key));
                }
            } else {
                QJsonObject entry{{"mode", args["mode"]}};
                for (const char *key : {"blend_in", "blend_out"})
                    if (args.contains(key)) entry[key] = args[key];
                QString error;
                const auto changed = jsonInsertKey(source.text, {"rows"}, row, jsonScalar(entry), &error);
                if (changed.isNull()) throw CommandError{groundFile + ": " + error};
                source.text = changed;
            }
            const QByteArray after = (hasBom(source.before) ? QByteArray("\xEF\xBB\xBF") : QByteArray())
                + source.text.toUtf8();
            QVector<FileChange> changes;
            if (source.before != after) changes.append({groundFile, source.before, after});
            auto result = session.commit(ctx, "set_ground_mode", args,
                t("Set ground mode %1 for %2", "Set ground mode %1 for %2")
                    .arg(args["mode"].toString(), row), changes);
            result["changes"] = changeToJson(changes)["changes"];
            return result;
        }});
    session.registry().add({"get_ground_modes", t("Get row ground modes", "Get row ground modes"),
        commandSchema(), false,
        [](const QJsonObject &, CommandContext &ctx) {
            return QJsonObject{{"rows", readGround(ctx.session).rows}};
        }});
}
} // namespace wb
