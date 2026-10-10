#include "commands.h"
#include <QElapsedTimer>
#include <QHash>

namespace wb {
void registerRowCommands(Session &s) {
    s.registry().add({"list_rows", t("List fighter moves", "List fighter moves"), commandSchema(), false,
        [](const QJsonObject &, CommandContext &ctx) {
            QJsonArray rows;
            QHash<QString, int> clipFrames;
            for (const auto &clip : ctx.session.data().clips()) clipFrames.insert(clip.name, clip.frames);
            for (const auto &row : ctx.session.data().rows()) {
                QJsonArray motions; for (int motion : row.motions) motions.append(motion);
                rows.append(QJsonObject{{"name", row.name}, {"motions", motions}, {"tag", row.tag},
                    {"clip", row.effectiveClip()}, {"aerial", row.aerial},
                    {"frames", qMax(0, clipFrames.value(row.effectiveClip(), 0) - row.cropStart - 1)}, // engine frames 1..N-1 of an N-sample clip (dair 40 -> 39, fair 44 -> 43)
                    {"hitboxes", int(ctx.session.data().hitboxes(row.name).size())}});
            }
            return QJsonObject{{"rows", rows}};
        }});
    s.registry().add({"load_row", t("Load a move in the engine", "Load a move in the engine"),
        commandSchema({{"row", argType("string")}}, {"row"}), false,
        [](const QJsonObject &args, CommandContext &ctx) {
            needEngine(ctx.session);
            const auto row = needRow(ctx.session, args["row"].toString());
            const auto result = engineCall(ctx.session, "row", {{"motion", rowMotion(row)}});
            ctx.session.currentRow = row.name;
            return result;
        }});
    s.registry().add({"set_frame", t("Seek to a move frame", "Seek to a move frame"),
        commandSchema({{"frame", argType("integer")}}, {"frame"}), false,
        [](const QJsonObject &args, CommandContext &ctx) {
            needEngine(ctx.session);
            const int frame = intArg(args, "frame");
            if (ctx.session.currentRow.isEmpty())
                throw CommandError{t("no row loaded; call load_row first", "no row loaded; call load_row first")};
            const auto row = needRow(ctx.session, ctx.session.currentRow);
            QJsonObject frameArgs{{"motion", rowMotion(row)}, {"frame", frame}};
            if (row.aerial) frameArgs.insert("lift", 40); // aerials stage above the floor or they land first
            return engineCall(ctx.session, "frame", frameArgs);
        }});
    s.registry().add({"play", t("Step the move forward", "Step the move forward"),
        commandSchema({{"frames", argType("integer")}, {"step", argType("integer")}}, {"frames"}), false,
        [](const QJsonObject &args, CommandContext &ctx) {
            needEngine(ctx.session);
            int remaining = intArg(args, "frames");
            const int step = intArg(args, "step", 1, std::numeric_limits<int>::max(), 1);
            if (ctx.session.currentRow.isEmpty())
                throw CommandError{t("no row loaded; call load_row first", "no row loaded; call load_row first")};
            if (!remaining) return engineCall(ctx.session, "frame_info");
            QJsonObject result;
            QElapsedTimer timer; timer.start();
            while (remaining > 0) {
                // Bound a bad or enormous request even if the backend replies immediately.
                if (timer.elapsed() >= 30000)
                    throw CommandError{t("play timed out", "play timed out")};
                const int n = qMin(step, remaining);
                result = engineCall(ctx.session, "step", {{"n", n}});
                remaining -= n;
            }
            return result;
        }});
    s.registry().add({"frame_info", t("Read the live fighter frame", "Read the live fighter frame"),
        commandSchema(), false, [](const QJsonObject &, CommandContext &ctx) {
            return engineCall(ctx.session, "frame_info");
        }});
}
} // namespace wb
