#include "combo_model.h"
#include "commands.h"

// The combo graph (geno.md 25): list/edit/add/delete the routes and strings of the project's combo file. Every write is a
// Session::commit, so it lands in the history, can be proposed, undone and reverted like a hitbox edit. The Workbench's
// Combo tab, the route lanes under the move timeline, the string map and Blender's "Play string" are clients.
namespace wb {
namespace {
QVector<FileChange> real(const QVector<FileChange> &edits) {
    QVector<FileChange> out;
    for (const auto &change : edits) if (change.before != change.after) out.append(change);
    return out;
}
const QStringList &routeKeys() {
    static const QStringList keys{"name", "from", "to", "input", "dir", "on", "where", "window", "buffer", "hold", "priority",
                                  "ki_cost", "ki_min", "depth", "once", "starts", "when", "source"};
    return keys;
}
const QStringList &stringKeys() {
    static const QStringList keys{"name", "steps", "intent"};
    return keys;
}
// Fields come as `fields` (an object) and/or as top-level keys of the call.
QJsonObject fieldsOf(const QJsonObject &args, const QStringList &known) {
    QJsonObject out = args.value("fields").toObject();
    for (const auto &key : known) if (args.contains(key)) out[key] = args[key];
    return out;
}
QJsonObject needCombo(Session &s) {
    if (!s.data().hasCombo())
        throw CommandError{t("This project declares no combo file (workbench.json \"combo\")", "This project declares no combo file (workbench.json \"combo\")")};
    return {};
}
QJsonObject schemaWithKeys(const QStringList &keys, const QJsonArray &required) {
    QJsonObject props{{"index", argType("integer")}, {"fields", argType("object")}, {"propose", argType("boolean")}};
    for (const auto &key : keys) if (!props.contains(key)) props[key] = QJsonObject{};
    return commandSchema(props, required);
}
} // namespace

void registerComboCommands(Session &s) {
    s.registry().add({"list_routes", t("List the combo routes", "List the combo routes"),
        commandSchema({{"from", argType("string")}}), false,
        [](const QJsonObject &args, CommandContext &ctx) {
            auto &data = ctx.session.data();
            QJsonArray list;
            const QString from = args["from"].toString();
            QStringList tokens;
            if (!from.isEmpty()) {
                tokens << from;
                for (const auto &row : data.rows())
                    if (row.name == from) for (int motion : row.motions) tokens << QString("motion:%1").arg(motion);
            }
            for (const auto &value : data.routes()) {
                const auto route = value.toObject();
                bool keep = from.isEmpty();
                for (const auto &source : comboRouteSources(route)) if (tokens.contains(source)) keep = true;
                if (keep) list.append(route);
            }
            return QJsonObject{{"routes", list}, {"count", list.size()}, {"meta", data.comboMeta()},
                               {"file", data.project().combo}, {"declared", data.hasCombo()}};
        }});
    s.registry().add({"edit_route", t("Edit a combo route", "Edit a combo route"), schemaWithKeys(routeKeys(), {"index"}), true,
        [](const QJsonObject &args, CommandContext &ctx) {
            needCombo(ctx.session);
            const int index = intArg(args, "index");
            const auto fields = fieldsOf(args, routeKeys());
            if (fields.isEmpty()) throw CommandError{t("nothing to change", "nothing to change")};
            ctx.propose |= args["propose"].toBool();
            QString error;
            const auto edits = ctx.session.data().editRoute(index, fields, &error);
            if (!error.isEmpty()) throw CommandError{error};
            return ctx.session.commit(ctx, "edit_route", args, t("Edit combo route #%1", "Edit combo route #%1").arg(index), real(edits));
        }});
    s.registry().add({"add_route", t("Add a combo route", "Add a combo route"),
        commandSchema({{"route", argType("object")}, {"propose", argType("boolean")}}, {"route"}), true,
        [](const QJsonObject &args, CommandContext &ctx) {
            needCombo(ctx.session);
            if (!args["route"].isObject()) throw CommandError{t("route: expected an object", "route: expected an object")};
            ctx.propose |= args["propose"].toBool();
            QString error;
            int index = -1;
            const auto route = args["route"].toObject();
            const auto edits = ctx.session.data().addRoute(route, &index, &error);
            if (!error.isEmpty()) throw CommandError{error};
            auto result = ctx.session.commit(ctx, "add_route", args,
                t("Add combo route %1", "Add combo route %1").arg(route.value("name").toString()), real(edits));
            result["index"] = index;
            return result;
        }});
    s.registry().add({"delete_route", t("Delete a combo route", "Delete a combo route"),
        commandSchema({{"index", argType("integer")}, {"propose", argType("boolean")}}, {"index"}), true,
        [](const QJsonObject &args, CommandContext &ctx) {
            needCombo(ctx.session);
            const int index = intArg(args, "index");
            ctx.propose |= args["propose"].toBool();
            QString error;
            const auto edits = ctx.session.data().removeRoute(index, &error);
            if (!error.isEmpty()) throw CommandError{error};
            return ctx.session.commit(ctx, "delete_route", args, t("Delete combo route #%1", "Delete combo route #%1").arg(index), real(edits));
        }});
    s.registry().add({"list_strings", t("List the combo strings", "List the combo strings"), commandSchema(), false,
        [](const QJsonObject &, CommandContext &ctx) {
            const auto list = ctx.session.data().strings();
            return QJsonObject{{"strings", list}, {"count", list.size()}, {"declared", ctx.session.data().hasCombo()}};
        }});
    s.registry().add({"edit_string", t("Edit a combo string", "Edit a combo string"), schemaWithKeys(stringKeys(), {"index"}), true,
        [](const QJsonObject &args, CommandContext &ctx) {
            needCombo(ctx.session);
            const int index = intArg(args, "index");
            const auto fields = fieldsOf(args, stringKeys());
            if (fields.isEmpty()) throw CommandError{t("nothing to change", "nothing to change")};
            ctx.propose |= args["propose"].toBool();
            QString error;
            const auto edits = ctx.session.data().editString(index, fields, &error);
            if (!error.isEmpty()) throw CommandError{error};
            return ctx.session.commit(ctx, "edit_string", args, t("Edit combo string #%1", "Edit combo string #%1").arg(index), real(edits));
        }});
    s.registry().add({"add_string", t("Add a combo string", "Add a combo string"),
        commandSchema({{"string", argType("object")}, {"propose", argType("boolean")}}, {"string"}), true,
        [](const QJsonObject &args, CommandContext &ctx) {
            needCombo(ctx.session);
            if (!args["string"].isObject()) throw CommandError{t("string: expected an object", "string: expected an object")};
            ctx.propose |= args["propose"].toBool();
            QString error;
            int index = -1;
            const auto str = args["string"].toObject();
            const auto edits = ctx.session.data().addString(str, &index, &error);
            if (!error.isEmpty()) throw CommandError{error};
            auto result = ctx.session.commit(ctx, "add_string", args,
                t("Add combo string %1", "Add combo string %1").arg(str.value("name").toString()), real(edits));
            result["index"] = index;
            return result;
        }});
    s.registry().add({"delete_string", t("Delete a combo string", "Delete a combo string"),
        commandSchema({{"index", argType("integer")}, {"propose", argType("boolean")}}, {"index"}), true,
        [](const QJsonObject &args, CommandContext &ctx) {
            needCombo(ctx.session);
            const int index = intArg(args, "index");
            ctx.propose |= args["propose"].toBool();
            QString error;
            const auto edits = ctx.session.data().removeString(index, &error);
            if (!error.isEmpty()) throw CommandError{error};
            return ctx.session.commit(ctx, "delete_string", args, t("Delete combo string #%1", "Delete combo string #%1").arg(index), real(edits));
        }});
}

// The check behind run_checks: route windows against the moves they leave (declared in commands.h).
QVector<Problem> comboRouteProblems(Session &s) {
    auto &data = s.data();
    if (!data.hasCombo()) return {};
    QHash<QString, ComboRowTiming> timing;
    for (const auto &row : data.rows()) {
        ComboRowTiming tm;
        tm.row = row.name;
        int frames = 0;
        for (const auto &clip : data.clips()) if (clip.name == row.effectiveClip()) frames = qMax(0, clip.frames - row.cropStart);
        frames = qMax(frames, row.iasa + 1 > 1 ? row.iasa + 1 : 0);
        int first = 0;
        for (const auto &hit : data.hitboxes(row.name)) {
            if (hit.startFrame > 0 && (first == 0 || hit.startFrame < first)) first = hit.startFrame;
            frames = qMax(frames, hit.endFrame > 0 ? hit.endFrame - 1 : hit.startFrame);
        }
        tm.length = frames; tm.firstHit = first;
        timing.insert(row.name, tm);
        for (int motion : row.motions) timing.insert(QString("motion:%1").arg(motion), tm);
    }
    return comboWindowProblems(data.routes(), timing);
}
} // namespace wb
