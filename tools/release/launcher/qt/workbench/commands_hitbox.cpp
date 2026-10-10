#include "commands.h"
#include "analysis.h"

namespace wb {
QJsonObject hitboxJson(const HitboxRef &h) {
    return {{"ordinal", h.ordinal}, {"line", h.line}, {"slot", h.slot}, {"joint", h.joint},
        {"damage", h.damage}, {"size", h.size}, {"x", h.x}, {"y", h.y}, {"z", h.z},
        {"angle", h.angle}, {"kbg", h.kbg}, {"fkb", h.fkb}, {"bkb", h.bkb}, {"element", h.element},
        // The names the engine's hitbox records use (gd.hitboxes): the Blender badges read these.
        {"wbk", h.fkb}, {"shield", h.shield}, {"shield_damage", h.shield}, {"ground", h.ground}, {"air", h.air},
        {"hit_ground", h.ground}, {"hit_air", h.air},
        {"start_frame", h.startFrame}, {"end_frame", h.endFrame}};
}
namespace {
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
    for (const char *key : {"angle", "kbg", "fkb", "bkb", "start_frame", "end_frame", "element"})
        editProperties[key] = argType("integer");
    editProperties["shield"] = argType("integer"); editProperties["slot"] = argType("integer");
    editProperties["ground"] = argType("boolean"); editProperties["air"] = argType("boolean");
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
            if (args.contains("element")) edit.element = intArg(args, "element", 0, 31);
            if (args.contains("shield")) edit.shield = intArg(args, "shield", -128, 127);
            if (args.contains("slot")) {
                const double slot = args["slot"].toDouble(-1);
                if (!args["slot"].isDouble() || slot != std::floor(slot) || slot < 0 || slot >= kHitboxEditableSlots)
                    throw CommandError{t("slot must be between 0 and %1 (higher slot ids are not supported yet)",
                                         "slot must be between 0 and %1 (higher slot ids are not supported yet)").arg(kHitboxEditableSlots - 1)};
                edit.slot = int(slot);
            }
            for (const char *key : {"ground", "air"}) if (args.contains(key)) {
                const auto v = args[key];
                if (!v.isBool() && !(v.isDouble() && (v.toDouble() == 0 || v.toDouble() == 1)))
                    throw CommandError{t("%1 must be true or false", "%1 must be true or false").arg(key)};
                (QString(key) == "ground" ? edit.ground : edit.air) = v.isBool() ? v.toBool() : v.toDouble() != 0;
            }
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
    s.registry().add({"list_hitbox_roles", t("List hitbox bone roles", "Listar los roles de hueso del hitbox"),
        commandSchema(), false,
        [](const QJsonObject &, CommandContext &ctx) {
            QJsonArray roles;
            for (const auto &role : ctx.session.data().availableRoles())
                roles.append(QJsonObject{{"name", role.name}, {"group", role.group},
                    {"joint", ctx.session.data().jointForRole(role.name)}});
            return QJsonObject{{"roles", roles}, {"has_plan", ctx.session.data().hasPlan()}};
        }});
    auto addProperties = QJsonObject{{"row", argType("string")}, {"bone", argType("string")},
        {"frame", argType("integer")}, {"duration", argType("integer")}, {"propose", argType("boolean")}};
    for (const char *key : {"damage", "size", "x", "y", "z"}) addProperties[key] = argType("number");
    for (const char *key : {"angle", "kbg", "fkb", "bkb"}) addProperties[key] = argType("integer");
    s.registry().add({"add_hitbox", t("Add a source hitbox", "Añadir un hitbox al código fuente"),
        commandSchema(addProperties, {"row", "frame"}), true,
        [](const QJsonObject &args, CommandContext &ctx) {
            auto &session = ctx.session;
            const QString row = args["row"].toString();
            needRow(session, row);
            HitboxAdd add;
            add.frame = intArg(args, "frame");
            if (args.contains("duration")) add.duration = intArg(args, "duration", 1);
            QString bone;
            if (args.contains("bone")) bone = roleName(args["bone"].toString());
            else {
                // Default: the floor anchor, else the first role the plan resolves.
                const auto roles = session.data().availableRoles();
                for (const auto &role : roles) if (role.name == "FLOOR") bone = role.name;
                if (bone.isEmpty() && !roles.isEmpty()) bone = roles.first().name;
            }
            if (bone.isEmpty() || (session.data().hasPlan() && session.data().jointForRole(bone) < 0))
                throw CommandError{t("unknown bone: %1", "unknown bone: %1").arg(bone)};
            add.joint = bone;
            if (args.contains("damage")) add.damage = numberArg(args, "damage");
            if (args.contains("size")) add.size = numberArg(args, "size");
            if (add.damage < 0 || add.size < 0)
                throw CommandError{t("damage and size must be nonnegative", "damage and size must be nonnegative")};
            if (args.contains("x")) add.x = numberArg(args, "x");
            if (args.contains("y")) add.y = numberArg(args, "y");
            if (args.contains("z")) add.z = numberArg(args, "z");
            if (args.contains("angle")) add.angle = intArg(args, "angle", std::numeric_limits<int>::min());
            if (args.contains("kbg")) add.kbg = intArg(args, "kbg");
            if (args.contains("fkb")) add.fkb = intArg(args, "fkb");
            if (args.contains("bkb")) add.bkb = intArg(args, "bkb");
            ctx.propose |= args["propose"].toBool();
            QString error;
            int ordinal = -1;
            const auto edits = session.data().addHitbox(row, add, &ordinal, &error);
            if (!error.isEmpty()) throw CommandError{error};
            QVector<FileChange> changes;
            for (const auto &change : edits) if (change.before != change.after) changes.append(change);
            auto result = session.commit(ctx, "add_hitbox", args,
                t("Add hitbox to %1 at frame %2", "Añadir hitbox a %1 en el fotograma %2").arg(row).arg(add.frame), changes);
            result["ordinal"] = ordinal;
            result["bone"] = bone;
            return result;
        }});
    s.registry().add({"delete_hitbox", t("Delete a source hitbox", "Borrar un hitbox del código fuente"),
        commandSchema(QJsonObject{{"row", argType("string")}, {"ordinal", argType("integer")},
                                  {"propose", argType("boolean")}}, {"row", "ordinal"}), true,
        [](const QJsonObject &args, CommandContext &ctx) {
            auto &session = ctx.session;
            const QString row = args["row"].toString();
            const int ordinal = intArg(args, "ordinal");
            needRow(session, row);
            ctx.propose |= args["propose"].toBool();
            QString error;
            const auto edits = session.data().removeHitbox(row, ordinal, &error);
            if (!error.isEmpty()) throw CommandError{error};
            QVector<FileChange> changes;
            for (const auto &change : edits) if (change.before != change.after) changes.append(change);
            return session.commit(ctx, "delete_hitbox", args,
                t("Delete hitbox #%1 in %2", "Borrar hitbox #%1 en %2").arg(ordinal).arg(row), changes);
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
