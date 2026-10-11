#include "combo_model.h"
#include "commands.h"
#include "geno_asm.h"
#include <QThread>

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

void registerComboPlayCommands(Session &);
void registerComboCommands(Session &s) {
    registerComboPlayCommands(s);
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

namespace {
struct StepData {
    ComboStepInfo info;
    QString clip, kind; // kind: "move" (a Moves row), "state" (a state of the combo file) or "unknown"
    int motion = -1;
    QJsonArray hits;
};
int clipFrames(GenoData &data, const QString &clip) {
    for (const auto &c : data.clips()) if (c.name == clip) return c.frames;
    return 0;
}
QJsonObject hitJson(GenoData &data, const HitboxRef &h) {
    QString bone;
    const int joint = data.jointForRole(h.joint);
    for (const auto &j : data.joints()) if (j.index == joint) bone = j.name;
    return {{"slot", h.slot}, {"role", h.joint}, {"bone", bone}, {"x", h.x}, {"y", h.y}, {"z", h.z}, {"size", h.size},
            {"start_frame", h.startFrame}, {"end_frame", h.endFrame}, {"damage", h.damage}};
}
void fillHits(GenoData &data, const QVector<HitboxRef> &boxes, StepData &out, int &frames) {
    int first = 0;
    for (const auto &hit : boxes) {
        if (hit.startFrame > 0 && (first == 0 || hit.startFrame < first)) first = hit.startFrame;
        frames = qMax(frames, hit.endFrame > 0 ? hit.endFrame - 1 : hit.startFrame);
        out.hits.append(hitJson(data, hit));
    }
    out.info.firstHit = first;
}
StepData rowStep(GenoData &data, const RowInfo &row) {
    StepData out; out.kind = "move"; out.clip = row.effectiveClip();
    out.motion = row.motions.isEmpty() ? -1 : row.motions.first();
    int frames = out.clip.isEmpty() ? 0 : qMax(0, clipFrames(data, out.clip) - row.cropStart);
    if (row.iasa > 0) frames = qMax(frames, row.iasa + 1);
    fillHits(data, data.hitboxes(row.name), out, frames);
    out.info.length = frames;
    return out;
}
StepData stateStep(Session &s, const QString &name) {
    auto &data = s.data();
    StepData out; out.kind = "unknown";
    const QString bare = comboTargetName(name);
    for (const auto &v : data.comboStates()) {
        const auto state = v.toObject();
        if (state.value("name").toString() != bare) continue;
        out.kind = "state"; out.clip = state.value("clip").toString();
        int frames = clipFrames(data, out.clip);
        const QString script = state.value("script").toString();
        if (!script.isEmpty()) {
            const QString dir = data.comboDir();
            QString error;
            const QString rel = FileStore::safeRel(dir.isEmpty() ? script : dir + "/" + script, &error);
            if (error.isEmpty() && s.files().exists(rel)) {
                const auto bytes = s.files().read(rel);
                fillHits(data, GenoAsm::parse(QString::fromUtf8(bytes)).hitboxes(), out, frames);
            }
        }
        out.info.length = frames;
        break;
    }
    return out;
}
StepData stepData(Session &s, const QString &name) {
    for (const auto &row : s.data().rows()) if (row.name == name) return rowStep(s.data(), row);
    return stateStep(s, name);
}
QJsonObject segmentJson(const ComboSegment &seg) {
    return {{"move", seg.move}, {"start", seg.start}, {"cut", seg.cut}, {"length", seg.length}, {"linked", seg.linked},
            {"route", seg.route}, {"input", seg.input}, {"lo", seg.lo}, {"hi", seg.hi}, {"buffer", seg.buffer},
            {"cancel_frame", seg.cancelFrame()}};
}
struct Planned { QStringList steps; QString name; QVector<ComboSegment> plan; QJsonArray stepJson; };
Planned planFor(Session &s, const QJsonObject &args) {
    auto &data = s.data();
    Planned out;
    if (args.contains("steps")) {
        for (const auto &v : args["steps"].toArray()) out.steps << v.toString();
        out.name = args["name"].toString();
    } else {
        const int index = intArg(args, "index", 0, std::numeric_limits<int>::max(), -1);
        const auto strings = data.strings();
        if (index < 0 || index >= strings.size()) throw CommandError{t("unknown string: %1", "unknown string: %1").arg(index)};
        out.name = strings[index].toObject().value("name").toString();
        for (const auto &v : strings[index].toObject().value("steps").toArray()) out.steps << v.toString();
    }
    if (out.steps.isEmpty()) throw CommandError{t("a string needs at least one step", "a string needs at least one step")};
    QHash<QString, ComboStepInfo> info;
    for (const auto &step : out.steps) {
        const auto d = stepData(s, step);
        info.insert(step, d.info);
        out.stepJson.append(QJsonObject{{"move", step}, {"kind", d.kind}, {"clip", d.clip}, {"frames", d.info.length},
                                        {"first_hit", d.info.firstHit}, {"motion", d.motion}, {"hits", d.hits}});
    }
    const int buffer = data.comboMeta().value("buffer").toInt(5);
    out.plan = planComboString(out.steps, data.routes(), info, buffer, args["add_buffer"].toBool());
    return out;
}
} // namespace

void registerComboPlayCommands(Session &s) {
    s.registry().add({"string_plan", t("The moves, clips, hitboxes and cut frames of a combo string", "The moves, clips, hitboxes and cut frames of a combo string"),
        commandSchema({{"index", argType("integer")}, {"steps", argType("array")}, {"name", argType("string")}, {"add_buffer", argType("boolean")}}), false,
        [](const QJsonObject &args, CommandContext &ctx) {
            needCombo(ctx.session);
            const auto p = planFor(ctx.session, args);
            QJsonArray segments;
            for (const auto &seg : p.plan) segments.append(segmentJson(seg));
            return QJsonObject{{"name", p.name}, {"steps", p.stepJson}, {"segments", segments}, {"frames", comboStringFrames(p.plan)},
                               {"routes", ctx.session.data().routes()}, {"buffer", ctx.session.data().comboMeta().value("buffer").toInt(5)}};
        }});
    // Sends the same sequence to the engine: each move is posed on its frames, then the next one, cutting where the plan cuts.
    s.registry().add({"play_string", t("Play a combo string in the game", "Play a combo string in the game"),
        commandSchema({{"index", argType("integer")}, {"steps", argType("array")}, {"add_buffer", argType("boolean")}, {"realtime", argType("boolean")}}), false,
        [](const QJsonObject &args, CommandContext &ctx) {
            needCombo(ctx.session);
            const auto p = planFor(ctx.session, args);
            QJsonArray segments;
            for (const auto &seg : p.plan) segments.append(segmentJson(seg));
            QJsonObject out{{"name", p.name}, {"segments", segments}, {"frames", comboStringFrames(p.plan)}};
            if (!ctx.session.engine()) {
                out["played"] = false;
                out["note"] = t("The game is not running: the plan is returned, nothing was played", "The game is not running: the plan is returned, nothing was played");
                return out;
            }
            int sent = 0;
            for (int i = 0; i < p.plan.size(); ++i) {
                const int motion = p.stepJson[i].toObject().value("motion").toInt(-1);
                if (motion < 0) continue; // a state that is not a Moves row has no motion the engine can pose
                engineCall(ctx.session, "row", {{"motion", motion}});
                for (int f = 1; f <= p.plan[i].cut; ++f) {
                    engineCall(ctx.session, "frame", {{"motion", motion}, {"frame", f}});
                    ++sent;
                    if (args["realtime"].toBool()) QThread::msleep(16);
                }
            }
            out["played"] = true; out["frames_sent"] = sent;
            return out;
        }});
}

// The timing the checks and the string plan need for one Moves row.
QVector<Problem> comboRouteProblems(Session &s) {
    auto &data = s.data();
    if (!data.hasCombo()) return {};
    QHash<QString, ComboRowTiming> timing;
    for (const auto &row : data.rows()) {
        const auto step = rowStep(data, row);
        ComboRowTiming tm; tm.row = row.name; tm.length = step.info.length; tm.firstHit = step.info.firstHit;
        timing.insert(row.name, tm);
        for (int motion : row.motions) timing.insert(QString("motion:%1").arg(motion), tm);
    }
    return comboWindowProblems(data.routes(), timing);
}
} // namespace wb
