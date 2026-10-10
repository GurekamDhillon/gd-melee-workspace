#include "commands.h"
#include <QDir>
#include <QFileInfo>

namespace wb {
void registerViewCommands(Session &s) {
    s.registry().add({"open_fighter", t("Open the fighter source project", "Open the fighter source project"),
        commandSchema({{"path", argType("string")}}, {"path"}), false,
        [](const QJsonObject &args, CommandContext &ctx) {
            const auto requested = QFileInfo(args["path"].toString()).canonicalFilePath();
            const auto current = QFileInfo(ctx.session.files().root()).canonicalFilePath();
#ifdef Q_OS_WIN
            constexpr auto sensitivity = Qt::CaseInsensitive;
#else
            constexpr auto sensitivity = Qt::CaseSensitive;
#endif
            // FileStore and History belong to one project. UI/CLI create a new
            // Session when switching directories; never silently keep the old store.
            if (requested.isEmpty() || current.compare(requested, sensitivity) != 0)
                throw CommandError{t("opening another project requires a new session",
                                     "opening another project requires a new session")};
            const auto error = ctx.session.data().reload();
            if (!error.isEmpty()) throw CommandError{error};
            ctx.session.currentRow.clear();
            return QJsonObject{{"rows", int(ctx.session.data().rows().size())}};
        }});
    s.registry().add({"engine_status", t("Read engine status", "Read engine status"), commandSchema(), false,
        [](const QJsonObject &, CommandContext &ctx) {
            auto *engine = ctx.session.engine();
            return QJsonObject{{"status", engine ? engine->status() : QString("stopped")}};
        }});
    s.registry().add({"engine_restart", t("Restart the workbench engine", "Restart the workbench engine"),
        commandSchema(), false, [](const QJsonObject &, CommandContext &ctx) {
            auto &engine = needEngine(ctx.session);
            QString error;
            if (!engine.restart(&error))
                throw CommandError{error.isEmpty() ? t("engine restart failed", "engine restart failed") : error};
            ctx.session.currentRow.clear();
            return QJsonObject{{"status", engine.status()}};
        }});
    const QJsonObject cameraProperties{
        {"preset", QJsonObject{{"type", "string"}, {"enum", QJsonArray{"side", "front", "top", "three_quarter"}}}},
        {"yaw", argType("number")}, {"pitch", argType("number")}, {"distance", argType("number")},
        {"target_joint", argType("integer")}};
    s.registry().add({"set_camera", t("Debug only (frozen; the viewer is Blender): set the viewport camera", "Debug only (frozen; the viewer is Blender): set the viewport camera"),
        commandSchema(cameraProperties), false, [cameraProperties](const QJsonObject &args, CommandContext &ctx) {
            auto camera = ctx.session.camera;
            for (auto it = cameraProperties.constBegin(); it != cameraProperties.constEnd(); ++it) {
                if (!args.contains(it.key())) continue;
                if (it.key() == "target_joint") intArg(args, it.key());
                else if (it.key() != "preset") {
                    const double value = numberArg(args, it.key());
                    if (it.key() == "distance" && value <= 0)
                        throw CommandError{t("distance must be positive", "distance must be positive")};
                }
                camera[it.key()] = args[it.key()];
            }
            ctx.session.camera = camera;
            return QJsonObject{{"camera", camera}};
        }});
    const QJsonObject overlayProperties{{"hitboxes", argType("boolean")}, {"hurtboxes", argType("boolean")},
        {"bones", argType("boolean")}, {"ecb", argType("boolean")}, {"floor", argType("boolean")}};
    s.registry().add({"set_overlays", t("Debug only (frozen; the viewer is Blender): set viewport overlays", "Debug only (frozen; the viewer is Blender): set viewport overlays"),
        commandSchema(overlayProperties), false, [overlayProperties](const QJsonObject &args, CommandContext &ctx) {
            for (auto it = overlayProperties.constBegin(); it != overlayProperties.constEnd(); ++it)
                if (args.contains(it.key())) ctx.session.overlays[it.key()] = args[it.key()];
            return QJsonObject{{"overlays", ctx.session.overlays}};
        }});
    s.registry().add({"render_view", t("Debug only (frozen; the viewer is Blender): render the current frame", "Debug only (frozen; the viewer is Blender): render the current frame"),
        commandSchema({{"w", argType("integer")}, {"h", argType("integer")}}), false,
        [](const QJsonObject &args, CommandContext &ctx) {
            needEngine(ctx.session);
            QJsonObject request{{"camera", ctx.session.camera}, {"overlays", ctx.session.overlays}};
            for (const char *key : {"w", "h"}) if (args.contains(key)) request[key] = intArg(args, key, 1);
            const auto result = engineCall(ctx.session, "render", request);
            if (!result["path"].isString() || result["path"].toString().isEmpty())
                throw CommandError{t("engine render returned no PNG path", "engine render returned no PNG path")};
            return result;
        }});
}
} // namespace wb
