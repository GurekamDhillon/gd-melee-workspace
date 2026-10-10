#include "command_registry.h"
#include <QJsonArray>
#include <cmath>
#include <exception>
#include <utility>

namespace wb {
namespace {
QJsonObject failure(const QString &message) {
    return {{"ok", false}, {"error", message}};
}
}

void CommandRegistry::add(CommandSpec spec) {
    if (has(spec.name)) qFatal("duplicate command: %s", qPrintable(spec.name));
    commands_.append(std::move(spec));
}
bool CommandRegistry::has(const QString &name) const {
    for (const auto &spec : commands_)
        if (spec.name == name) return true;
    return false;
}
QVector<CommandSpec> CommandRegistry::list() const { return commands_; }

QString CommandRegistry::validate(const QJsonObject &schema, const QJsonObject &args) {
    for (const QJsonValue &required : schema["required"].toArray())
        if (!args.contains(required.toString())) return "missing required: " + required.toString();
    const QJsonObject properties = schema["properties"].toObject();
    for (auto it = args.constBegin(); it != args.constEnd(); ++it) {
        if (!properties.contains(it.key())) continue; // Unknown keys are tolerated.
        const QJsonObject property = properties[it.key()].toObject();
        const QString type = property["type"].toString();
        const QJsonValue value = it.value();
        const bool valid = type.isEmpty() ||
            (type == "string" && value.isString()) ||
            (type == "boolean" && value.isBool()) ||
            (type == "number" && value.isDouble()) ||
            (type == "integer" && value.isDouble() && value.toDouble() == std::floor(value.toDouble())) ||
            (type == "object" && value.isObject()) ||
            (type == "array" && value.isArray());
        if (!valid) return it.key() + ": expected " + type;
        if (property.contains("enum")) {
            bool found = false;
            for (const QJsonValue &allowed : property["enum"].toArray()) {
                if (allowed == value) { found = true; break; }
            }
            if (!found) return it.key() + ": not one of the allowed values";
        }
    }
    return {};
}

QJsonObject CommandRegistry::call(const QString &name, const QJsonObject &args, CommandContext &ctx) const {
    try {
        // Retain handlers if a running command registers another command.
        const auto commands = commands_;
        for (const auto &spec : commands) {
            if (spec.name != name) continue;
            const QString error = validate(spec.inputSchema, args);
            if (!error.isEmpty()) return failure(error);
            return {{"ok", true}, {"result", spec.run(args, ctx)}};
        }
        return failure("unknown command: " + name);
    } catch (const CommandError &error) {
        return failure(error.message);
    } catch (const std::exception &error) {
        return failure(QString::fromUtf8(error.what()));
    } catch (...) {
        return failure("unknown command error");
    }
}
} // namespace wb
