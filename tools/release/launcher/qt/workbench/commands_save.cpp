#include "commands.h"
#include "engine_link.h"
#include "geno_data.h"
#include "project.h"
#include "session.h"
#include <QDir>
#include <QElapsedTimer>
#include <QFileInfo>
#include <QJsonArray>
#include <QProcess>
#include <QRegularExpression>
#include <QStringDecoder>
#include <cmath>
#include <limits>
#include <utility>

namespace wb {
namespace {
QJsonObject schema(const QJsonObject &properties = {}, const QJsonArray &required = {}) {
    return {{"type", "object"}, {"properties", properties}, {"required", required}};
}
void add(Session &session, const QString &name, const QString &description,
         const QJsonObject &input, Handler run) {
    CommandSpec spec;
    spec.name = name;
    spec.description = description;
    spec.inputSchema = input;
    // mutating denotes proposal-capable source edits. These administrative verbs
    // must not run as an edit inside propose (undo/accept would otherwise apply it).
    spec.run = std::move(run);
    session.registry().add(std::move(spec));
}
int integerArg(const QJsonObject &args, const QString &key, int minimum) {
    const auto value = args.value(key);
    const double number = value.toDouble();
    if (!value.isDouble() || !std::isfinite(number) || std::trunc(number) != number ||
        number < minimum || number > std::numeric_limits<int>::max())
        throw CommandError{key + ": integer out of range"};
    return int(number);
}
void requireNoExternalChanges(Session &session) {
    const auto external = session.files().externalChanges();
    if (!external.isEmpty()) throw CommandError{"changed externally: " + external.join(", ")};
}
void refresh(Session &session, const QString &operation) {
    const QString error = session.data().reload();
    if (!error.isEmpty()) throw CommandError{operation + "; data reload failed: " + error};
    if (session.onApplied) session.onApplied();
}
QJsonObject applyHistory(Session &session, const QString &operation, int id = 0) {
    // Refresh reads every source file. Refuse even an unrelated hand edit rather
    // than letting that refresh silently acknowledge it after a history action.
    requireNoExternalChanges(session);
    QString error;
    bool applied = false;
    if (operation == "undo") applied = session.history().undo(session.files(), &error);
    else if (operation == "redo") applied = session.history().redo(session.files(), &error);
    else applied = session.history().accept(id, session.files(), &error);
    if (!applied) {
        // History calls mismatched proposal before-bytes 'stale proposal'. The
        // command API also promises 'changed externally' for this refusal.
        if (error.startsWith("stale proposal:")) error = "changed externally: " + error;
        throw CommandError{error};
    }
    // Keep the new in-memory state even if persistence fails: the files already
    // changed, and a subsequent undo must still refer to their actual state.
    if (!session.history().save(session.historyPath()))
        throw CommandError{operation + " applied; cannot save history: " + session.historyPath()};
    refresh(session, operation + " applied");
    QJsonObject result{{"applied", true}};
    if (operation == "accept") result.insert("entry", id);
    return result;
}
QString rebuildWorkDir(const QString &projectRoot) {
    QDir dir(projectRoot);
    do {
        if (QFileInfo::exists(dir.filePath(".git"))) return dir.absolutePath();
    } while (dir.cdUp());
    // Standalone/exported projects (including the synthetic fixture) have no Git root.
    return projectRoot;
}
QJsonObject rebuild(Session &session) {
    // Read configuration independently so a build doesn't acknowledge hand edits
    // in the session's FileStore or depend on gameplay being parseable already.
    FileStore configFiles(session.files().root());
    QString error;
    QStringList argv = ProjectConfig::load(configFiles, &error).rebuild;
    if (!error.isEmpty()) throw CommandError{error};
    if (argv.isEmpty() || argv.first().isEmpty()) throw CommandError{"rebuild not configured"};
    const QString project = session.files().root();
    const QString package = QDir(project).filePath("package");
    for (auto &arg : argv) {
        arg.replace("{project}", project);
        arg.replace("{package}", package);
    }

    constexpr int timeoutMs = 30 * 60 * 1000;
    constexpr int tailChars = 4000;
    QString stdoutTail, stderrTail;
    QStringDecoder stdoutDecoder(QStringDecoder::Utf8), stderrDecoder(QStringDecoder::Utf8);
    QElapsedTimer timer;
    // Declared after the captured buffers: process destruction cannot outlive them.
    QProcess process;
    process.setProgram(argv.takeFirst());
    process.setArguments(argv);
    process.setWorkingDirectory(rebuildWorkDir(project));
    const auto drain = [&] {
        const QString out = stdoutDecoder(process.readAllStandardOutput());
        const QString err = stderrDecoder(process.readAllStandardError());
        stdoutTail = (stdoutTail + out).right(tailChars);
        stderrTail = (stderrTail + err).right(tailChars);
    };
    QObject::connect(&process, &QProcess::readyReadStandardOutput, &process, drain);
    QObject::connect(&process, &QProcess::readyReadStandardError, &process, drain);
    timer.start();
    process.start(); // An argv vector, never a shell command line.
    if (!process.waitForStarted(30000))
        throw CommandError{"rebuild failed to start: " + process.errorString()};
    const int remaining = qMax(1, timeoutMs - int(timer.elapsed()));
    if (process.state() != QProcess::NotRunning && !process.waitForFinished(remaining) &&
        process.state() != QProcess::NotRunning) {
        process.kill(); // Only this command's child process.
        process.waitForFinished(5000);
        drain();
        throw CommandError{"rebuild timed out: " + (stdoutTail + stderrTail).right(300)};
    }
    drain();
    const QString tail = (stdoutTail + stderrTail).right(tailChars);
    const int exit = process.exitCode();
    if (process.exitStatus() != QProcess::NormalExit || exit != 0) {
        const QString crashed = process.exitStatus() == QProcess::CrashExit ? " (process crashed)" : QString();
        throw CommandError{QString("rebuild failed: exit %1%2: %3").arg(exit).arg(crashed, tail.right(300))};
    }
    // 'tail' is the packet's name; 'output' remains compatible with the Task 9 plan.
    QJsonObject result{{"exit", exit}, {"tail", tail}, {"output", tail}, {"elapsed_ms", double(timer.elapsed())}};
    // A rebuild script may report which build ran: "BUILD_MODE: <mode> <seconds>s" (build.py --auto:
    // gameplay-only or full). The last such line wins; the Blender add-on shows it in its status line.
    static const QRegularExpression modeLine(R"(BUILD_MODE:\s*(\S+)\s+([0-9]+(?:\.[0-9]+)?)s)");
    QRegularExpressionMatchIterator matches = modeLine.globalMatch(tail);
    QRegularExpressionMatch last;
    while (matches.hasNext()) last = matches.next();
    if (last.hasMatch()) {
        result.insert("mode", last.captured(1));
        result.insert("build_seconds", last.captured(2).toDouble());
    }
    return result;
}
} // namespace

QJsonObject changeToJson(const QVector<FileChange> &changes) {
    QJsonArray array;
    for (const auto &change : changes)
        array.append(QJsonObject{{"path", change.path}, {"bytes_before", qint64(change.before.size())},
                                 {"bytes_after", qint64(change.after.size())}});
    return {{"changes", array}};
}

void registerSaveCommands(Session &session) {
    add(session, "save", "Verify source files and report external changes", schema(),
        [](const QJsonObject &, CommandContext &ctx) {
            const auto external = ctx.session.files().externalChanges();
            QJsonObject result{{"dirty", false}, {"external", QJsonArray::fromStringList(external)}};
            if (!external.isEmpty()) result.insert("warning", "changed externally: " + external.join(", "));
            return result;
        });
    add(session, "rebuild", "Run the project's configured rebuild argv", schema(),
        [](const QJsonObject &, CommandContext &ctx) { return rebuild(ctx.session); });
    add(session, "reload", "Restart the engine and reload fighter data", schema(),
        [](const QJsonObject &, CommandContext &ctx) {
            EngineBackend *engine = ctx.session.engine();
            if (!engine) throw CommandError{"engine not running"};
            QString error;
            if (!engine->restart(&error))
                throw CommandError{error.isEmpty() ? QString("engine restart failed") : error};
            refresh(ctx.session, "engine restarted");
            return QJsonObject{{"restarted", true}};
        });
    add(session, "undo", "Undo the latest applied source edit", schema(),
        [](const QJsonObject &, CommandContext &ctx) { return applyHistory(ctx.session, "undo"); });
    add(session, "redo", "Reapply the next undone source edit", schema(),
        [](const QJsonObject &, CommandContext &ctx) { return applyHistory(ctx.session, "redo"); });
    add(session, "history", "List history metadata, optionally limited to recent entries",
        schema({{"limit", QJsonObject{{"type", "integer"}}}}),
        [](const QJsonObject &args, CommandContext &ctx) {
            const auto &entries = ctx.session.history().entries();
            const int limit = args.contains("limit") ? integerArg(args, "limit", 0) : int(entries.size());
            const qsizetype begin = qMax(qsizetype(0), entries.size() - qsizetype(limit));
            QJsonArray array;
            for (qsizetype i = begin; i < entries.size(); ++i) {
                const auto &entry = entries[i];
                array.append(QJsonObject{{"id", entry.id}, {"author", entry.author}, {"command", entry.command},
                    {"summary", entry.summary}, {"state", entry.state}, {"time", entry.time}});
            }
            return QJsonObject{{"entries", array}};
        });
    add(session, "propose", "Propose a validated source-edit command without applying it",
        schema({{"command", QJsonObject{{"type", "string"}}}, {"args", QJsonObject{{"type", "object"}}}},
               QJsonArray{"command", "args"}),
        [](const QJsonObject &args, CommandContext &ctx) {
            const QString name = args["command"].toString();
            const auto commands = ctx.session.registry().list();
            for (const auto &spec : commands) {
                if (spec.name != name) continue;
                if (!spec.mutating) throw CommandError{"command is not a source edit: " + name};
                const auto nested = args["args"].toObject();
                const QString error = CommandRegistry::validate(spec.inputSchema, nested);
                if (!error.isEmpty()) throw CommandError{error};
                CommandContext proposal = ctx;
                proposal.propose = true;
                return spec.run(nested, proposal);
            }
            throw CommandError{"unknown command: " + name};
        });
    const auto idSchema = schema({{"id", QJsonObject{{"type", "integer"}}}}, QJsonArray{"id"});
    add(session, "accept", "Apply a proposal after checking its source versions", idSchema,
        [](const QJsonObject &args, CommandContext &ctx) {
            return applyHistory(ctx.session, "accept", integerArg(args, "id", 1));
        });
    add(session, "reject", "Reject a proposal without changing source files", idSchema,
        [](const QJsonObject &args, CommandContext &ctx) {
            const int id = integerArg(args, "id", 1);
            History next = ctx.session.history();
            QString error;
            if (!next.reject(id, &error)) throw CommandError{error};
            if (!next.save(ctx.session.historyPath()))
                throw CommandError{"cannot save history: " + ctx.session.historyPath()};
            ctx.session.history() = std::move(next);
            return QJsonObject{{"entry", id}, {"state", "rejected"}};
        });
}

void registerAllCommands(Session &session) {
    registerViewCommands(session);
    registerRowCommands(session);
    registerHitboxCommands(session);
    registerClipCommands(session);
    registerSaveCommands(session);
    registerGroundCommands(session);
}
} // namespace wb
