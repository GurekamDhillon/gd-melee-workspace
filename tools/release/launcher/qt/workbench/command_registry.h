#pragma once
#include <QJsonObject>
#include <QString>
#include <QVector>
#include <functional>

namespace wb {
class Session;
struct CommandContext {
    Session &session;
    QString author = "human";
    bool propose = false;
};
struct CommandError { QString message; };
using Handler = std::function<QJsonObject(const QJsonObject &args, CommandContext &ctx)>;
struct CommandSpec {
    QString name, description;
    QJsonObject inputSchema; // JSON Schema subset: type, properties, required, enum.
    bool mutating = false;
    Handler run;
};

class CommandRegistry {
public:
    void add(CommandSpec spec); // Duplicate names are a programming error (qFatal).
    bool has(const QString &name) const;
    QVector<CommandSpec> list() const; // Registration order.
    // Returns {ok:true,result:{...}} or {ok:false,error:"..."}; handlers never throw out.
    QJsonObject call(const QString &name, const QJsonObject &args, CommandContext &ctx) const;
    static QString validate(const QJsonObject &schema, const QJsonObject &args);

private:
    QVector<CommandSpec> commands_;
};
} // namespace wb
