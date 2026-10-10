#include "commands.h"
#include "analysis.h"

namespace wb {
namespace {
QJsonObject hitboxJson(const HitboxRef &h) {
    return {{"ordinal", h.ordinal}, {"line", h.line}, {"slot", h.slot}, {"joint", h.joint},
        {"damage", h.damage}, {"size", h.size}, {"x", h.x}, {"y", h.y}, {"z", h.z},
        {"angle", h.angle}, {"kbg", h.kbg}, {"fkb", h.fkb}, {"bkb", h.bkb},
        {"start_frame", h.startFrame}, {"end_frame", h.endFrame}};
}
HitboxRef needHitbox(Session &s, const QString &row, int ordinal) {
    needRow(s, row);
    const auto hitboxes = s.data().hitboxes(row);
    if (ordinal < 0 || ordinal >= hitboxes.size())
        throw CommandError{t("unknown hitbox ordinal: %1", "unknown hitbox ordinal: %1").arg(ordinal)};
    return hitboxes[ordinal];
}
QString roleName(QString bone) {
    if (bone.startsWith('@') && bone.endsWith('@') && bone.size() > 2)
        bone = bone.mid(1, bone.size() - 2);
    return bone;
}
} // namespace

void registerHitboxCommands(Session &s) {
    const QJsonObject rowOrdinal{{"row", argType("string")}, {"ordinal", argType("integer")}};
    s.registry().add({"list_hitboxes", t("List source hitboxes", "List source hitboxes"),
        commandSchema({{"row", argType("string")}}, {"row"}), false,
        [](const QJsonObject &args, CommandContext &ctx) {
            const auto row = needRow(ctx.session, args["row"].toString());
            QJsonArray hitboxes;
            for (const auto &h : ctx.session.data().hitboxes(row.name)) hitboxes.append(hitboxJson(h));
            return QJsonObject{{"hitboxes", hitboxes}};
        }});
    auto editProperties = rowOrdinal;
    editProperties["bone"] = argType("string"); editProperties["propose"] = argType("boolean");
    for (const char *key : {"damage", "size", "x", "y", "z"}) editProperties[key] = argType("number");
    for (const char *key : {"angle", "kbg", "fkb", "bkb", "start_frame", "end_frame"})
        editProperties[key] = argType("integer");
    s.registry().add({"edit_hitbox", t("Edit a source hitbox", "Edit a source hitbox"),
        commandSchema(editProperties, {"row", "ordinal"}), true,
        [](const QJsonObject &args, CommandContext &ctx) {
            auto &session = ctx.session;
            const QString row = args["row"].toString();
            const int ordinal = intArg(args, "ordinal");
            needRow(session, row);
            HitboxEdit edit;
            if (args.contains("bone")) {
                const QString bone = roleName(args["bone"].toString());
                if (bone.isEmpty() || (session.data().hasPlan() && session.data().jointForRole(bone) < 0))
                    throw CommandError{t("unknown bone: %1", "unknown bone: %1").arg(bone)};
                edit.joint = bone;
            }
            if (args.contains("damage")) edit.damage = numberArg(args, "damage");
            if (args.contains("size")) edit.size = numberArg(args, "size");
            if ((edit.damage && *edit.damage < 0) || (edit.size && *edit.size < 0))
                throw CommandError{t("damage and size must be nonnegative", "damage and size must be nonnegative")};
            if (args.contains("x")) edit.x = numberArg(args, "x");
            if (args.contains("y")) edit.y = numberArg(args, "y");
            if (args.contains("z")) edit.z = numberArg(args, "z");
            if (args.contains("angle")) edit.angle = intArg(args, "angle", std::numeric_limits<int>::min());
            if (args.contains("kbg")) edit.kbg = intArg(args, "kbg");
            if (args.contains("fkb")) edit.fkb = intArg(args, "fkb");
            if (args.contains("bkb")) edit.bkb = intArg(args, "bkb");
            if (args.contains("start_frame")) edit.startFrame = intArg(args, "start_frame");
            if (args.contains("end_frame")) edit.endFrame = intArg(args, "end_frame");
            ctx.propose |= args["propose"].toBool();
            QString error;
            const auto edits = session.data().editHitbox(row, ordinal, edit, &error);
            if (!error.isEmpty()) throw CommandError{error};
            QVector<FileChange> changes;
            for (const auto &change : edits) if (change.before != change.after) changes.append(change);
            return session.commit(ctx, "edit_hitbox", args,
                t("Edit hitbox #%1 in %2", "Edit hitbox #%1 in %2").arg(ordinal).arg(row), changes);
        }});
    s.registry().add({"suggest_hitbox_bone", t("Suggest the active limb for a hitbox", "Suggest the active limb for a hitbox"),
        commandSchema(rowOrdinal, {"row", "ordinal"}), false,
        [](const QJsonObject &args, CommandContext &ctx) {
            auto &engine = needEngine(ctx.session);
            const auto row = needRow(ctx.session, args["row"].toString());
            const auto h = needHitbox(ctx.session, row.name, intArg(args, "ordinal"));
            QString error;
            ctx.session.currentRow.clear();
            const auto bones = sampleBones(engine, ctx.session.data(), row, h.startFrame, &error);
            if (!error.isEmpty()) throw CommandError{error};
            QJsonArray scores;
            for (const auto &bone : bones) if (isLimbRole(bone.role))
                scores.append(QJsonObject{{"role", bone.role}, {"displacement", bone.displacement},
                    {"speed", bone.speed}, {"score", bone.displacement * (1.0 + bone.speed)}});
            return QJsonObject{{"suggested", suggestBone(bones)}, {"current", h.joint}, {"scores", scores}};
        }});
    s.registry().add({"run_checks", t("Check fighter moves", "Check fighter moves"),
        commandSchema({{"row", argType("string")}}), false,
        [](const QJsonObject &args, CommandContext &ctx) {
            auto &session = ctx.session;
            const QString filter = args["row"].toString();
            if (args.contains("row")) needRow(session, filter);
            QVector<RowAnalysis> rows;
            for (const auto &row : session.data().rows()) {
                QString error;
                const bool sweep = session.engine() && (filter.isEmpty() || filter == row.name);
                rows.append(sweep ? analyzeRow(session, row, &error) : analyzeStaticRow(session, row, &error));
                if (!error.isEmpty()) throw CommandError{error};
            }
            // Keep all static rows for duplicate-clip comparison; only the
            // requested row needs an engine sweep or appears in the filtered result.
            QJsonArray problems;
            for (const auto &p : runChecks(rows)) {
                if (!filter.isEmpty() && p.row != filter) continue;
                problems.append(QJsonObject{{"kind", p.kind}, {"row", p.row}, {"message", p.message}, {"ordinal", p.ordinal}});
            }
            return QJsonObject{{"problems", problems}, {"engine", session.engine() != nullptr}};
        }});
}
} // namespace wb
