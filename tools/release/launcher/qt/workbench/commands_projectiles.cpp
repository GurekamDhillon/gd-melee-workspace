#include "commands.h"

// Projectiles (geno.md 19): list/edit/add/delete the articles of gameplay.json, and list/edit/add/delete the
// `CALL geno.article.spawn` calls of a move. Every write is a Session::commit, so it lands in the history, can be
// proposed, undone and reverted like a hitbox edit. The Blender "Projectiles" collection and the Workbench's
// Projectiles tab are clients of these commands.
namespace wb {
namespace {
QVector<FileChange> real(const QVector<FileChange> &edits) {
    QVector<FileChange> out;
    for (const auto &change : edits) if (change.before != change.after) out.append(change);
    return out;
}
quint32 argArg(const QJsonObject &args, const QString &key) {
    const double v = args[key].toDouble(-1);
    if (!args[key].isDouble() || !std::isfinite(v) || std::floor(v) != v || v < 0 || v > 4294967295.0)
        throw CommandError{t("%1: integer out of range", "%1: integer out of range").arg(key)};
    return quint32(v);
}
quint32 spawnArg(const QJsonObject &args) {
    // Either the raw `arg`, or article (+ variant, angle) packed as the engine's hook argument.
    if (args.contains("arg")) return argArg(args, "arg");
    const int article = intArg(args, "article", 0, 255), variant = intArg(args, "variant", 0, 255);
    const int angle = intArg(args, "angle", -32768, 32767);
    return quint32(article) | (quint32(variant) << 8) | (quint32(angle & 0xFFFF) << 16);
}
} // namespace

void registerProjectileCommands(Session &s) {
    s.registry().add({"list_articles", t("List the fighter's projectiles (articles)", "List the fighter's projectiles (articles)"),
        commandSchema(), false,
        [](const QJsonObject &, CommandContext &ctx) {
            QJsonArray list;
            int i = 0;
            for (const auto &a : ctx.session.data().articles()) {
                QJsonObject o = a.toObject();
                o["index"] = i++;
                list.append(o);
            }
            return QJsonObject{{"articles", list}};
        }});
    s.registry().add({"edit_article", t("Edit a projectile (article)", "Edit a projectile (article)"),
        commandSchema({{"index", argType("integer")}, {"ops", argType("array")}, {"propose", argType("boolean")}},
                      {"index", "ops"}),
        true,
        [](const QJsonObject &args, CommandContext &ctx) {
            const int index = intArg(args, "index");
            if (!args["ops"].isArray()) throw CommandError{t("ops: expected an array", "ops: expected an array")};
            ctx.propose |= args["propose"].toBool();
            QString error;
            const auto edits = ctx.session.data().editArticle(index, args["ops"].toArray(), &error);
            if (!error.isEmpty()) throw CommandError{error};
            return ctx.session.commit(ctx, "edit_article", args,
                t("Edit projectile #%1", "Edit projectile #%1").arg(index), real(edits));
        }});
    s.registry().add({"add_article", t("Add a projectile (article)", "Add a projectile (article)"),
        commandSchema({{"article", argType("object")}, {"propose", argType("boolean")}}, {"article"}), true,
        [](const QJsonObject &args, CommandContext &ctx) {
            if (!args["article"].isObject()) throw CommandError{t("article: expected an object", "article: expected an object")};
            ctx.propose |= args["propose"].toBool();
            QString error;
            int index = -1;
            const auto edits = ctx.session.data().addArticle(args["article"].toObject(), &index, &error);
            if (!error.isEmpty()) throw CommandError{error};
            auto result = ctx.session.commit(ctx, "add_article", args,
                t("Add projectile %1", "Add projectile %1").arg(args["article"].toObject()["name"].toString()), real(edits));
            result["index"] = index;
            return result;
        }});
    s.registry().add({"delete_article", t("Delete the last projectile (article)", "Delete the last projectile (article)"),
        commandSchema({{"index", argType("integer")}, {"propose", argType("boolean")}}, {"index"}), true,
        [](const QJsonObject &args, CommandContext &ctx) {
            const int index = intArg(args, "index");
            ctx.propose |= args["propose"].toBool();
            QString error;
            const auto edits = ctx.session.data().removeArticle(index, &error);
            if (!error.isEmpty()) throw CommandError{error};
            return ctx.session.commit(ctx, "delete_article", args,
                t("Delete projectile #%1", "Delete projectile #%1").arg(index), real(edits));
        }});
    s.registry().add({"list_spawns", t("List projectile spawns in move scripts", "List projectile spawns in move scripts"),
        commandSchema({{"row", argType("string")}}), false,
        [](const QJsonObject &args, CommandContext &ctx) {
            const QString row = args["row"].toString();
            if (args.contains("row")) needRow(ctx.session, row);
            return QJsonObject{{"spawns", ctx.session.data().spawns(row)}};
        }});
    s.registry().add({"edit_spawn", t("Move or retarget a projectile spawn", "Move or retarget a projectile spawn"),
        commandSchema({{"row", argType("string")}, {"ordinal", argType("integer")}, {"frame", argType("integer")},
                       {"arg", argType("integer")}, {"article", argType("integer")}, {"variant", argType("integer")},
                       {"angle", argType("integer")}, {"propose", argType("boolean")}},
                      {"row", "ordinal"}),
        true,
        [](const QJsonObject &args, CommandContext &ctx) {
            const QString row = args["row"].toString();
            const int ordinal = intArg(args, "ordinal");
            needRow(ctx.session, row);
            std::optional<int> frame;
            std::optional<quint32> arg;
            if (args.contains("frame")) frame = intArg(args, "frame");
            if (args.contains("arg") || args.contains("article")) {
                // Keep unspecified parts of the packed argument.
                quint32 current = 0; bool found = false;
                for (const auto &sp : ctx.session.data().spawns(row))
                    if (sp.toObject()["ordinal"].toInt() == ordinal) { current = quint32(sp.toObject()["arg"].toDouble()); found = true; }
                if (!found) throw CommandError{t("unknown spawn ordinal: %1", "unknown spawn ordinal: %1").arg(ordinal)};
                if (args.contains("arg")) arg = argArg(args, "arg");
                else {
                    QJsonObject merged{{"article", args["article"]},
                        {"variant", args.contains("variant") ? args["variant"] : QJsonValue(int((current >> 8) & 0xFF))},
                        {"angle", args.contains("angle") ? args["angle"] : QJsonValue(int(qint16(current >> 16)))}};
                    arg = spawnArg(merged);
                }
            }
            if (!frame && !arg) throw CommandError{t("nothing to change", "nothing to change")};
            ctx.propose |= args["propose"].toBool();
            QString error;
            const auto edits = ctx.session.data().editSpawn(row, ordinal, frame, arg, &error);
            if (!error.isEmpty()) throw CommandError{error};
            return ctx.session.commit(ctx, "edit_spawn", args,
                t("Edit projectile spawn #%1 in %2", "Edit projectile spawn #%1 in %2").arg(ordinal).arg(row), real(edits));
        }});
    s.registry().add({"add_spawn", t("Add a projectile spawn to a move", "Add a projectile spawn to a move"),
        commandSchema({{"row", argType("string")}, {"frame", argType("integer")}, {"arg", argType("integer")},
                       {"article", argType("integer")}, {"variant", argType("integer")}, {"angle", argType("integer")},
                       {"propose", argType("boolean")}},
                      {"row", "frame"}),
        true,
        [](const QJsonObject &args, CommandContext &ctx) {
            const QString row = args["row"].toString();
            needRow(ctx.session, row);
            const int frame = intArg(args, "frame");
            const quint32 arg = spawnArg(args);
            ctx.propose |= args["propose"].toBool();
            QString error;
            int ordinal = -1;
            const auto edits = ctx.session.data().addSpawn(row, frame, arg, &ordinal, &error);
            if (!error.isEmpty()) throw CommandError{error};
            auto result = ctx.session.commit(ctx, "add_spawn", args,
                t("Add projectile spawn to %1 at frame %2", "Add projectile spawn to %1 at frame %2").arg(row).arg(frame), real(edits));
            result["ordinal"] = ordinal;
            return result;
        }});
    s.registry().add({"delete_spawn", t("Delete a projectile spawn", "Delete a projectile spawn"),
        commandSchema({{"row", argType("string")}, {"ordinal", argType("integer")}, {"propose", argType("boolean")}},
                      {"row", "ordinal"}),
        true,
        [](const QJsonObject &args, CommandContext &ctx) {
            const QString row = args["row"].toString();
            const int ordinal = intArg(args, "ordinal");
            needRow(ctx.session, row);
            ctx.propose |= args["propose"].toBool();
            QString error;
            const auto edits = ctx.session.data().removeSpawn(row, ordinal, &error);
            if (!error.isEmpty()) throw CommandError{error};
            return ctx.session.commit(ctx, "delete_spawn", args,
                t("Delete projectile spawn #%1 in %2", "Delete projectile spawn #%1 in %2").arg(ordinal).arg(row), real(edits));
        }});
}
} // namespace wb
