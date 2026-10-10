#include "session.h"
#include <QDir>
#include <QSet>
#include <exception>
#include <utility>

namespace wb {
namespace {
QString exceptionMessage(const std::exception_ptr &error) {
    try {
        std::rethrow_exception(error);
    } catch (const CommandError &failure) {
        return failure.message;
    } catch (const std::exception &failure) {
        return QString::fromUtf8(failure.what());
    } catch (...) {
        return "unknown commit error";
    }
}
QString pathIdentity(const QString &path) {
#ifdef Q_OS_WIN
    return path.toCaseFolded();
#else
    return path;
#endif
}
QVector<FileChange> checkedChanges(const QVector<FileChange> &changes) {
    QVector<FileChange> result;
    QSet<QString> paths;
    result.reserve(changes.size());
    for (const auto &change : changes) {
        QString error;
        const QString path = FileStore::safeRel(change.path, &error);
        if (path.isNull()) throw CommandError{error};
        const QString identity = pathIdentity(path);
        if (paths.contains(identity)) throw CommandError{"duplicate path: " + path};
        paths.insert(identity);
        result.append({path, change.before, change.after});
    }
    return result;
}
}

Session::Session(const QString &projectDir, EngineBackend *engine)
    : files_(projectDir), history_(History::load(historyPath())), engine_(engine) {}
Session::~Session() = default;
FileStore &Session::files() { return files_; }
History &Session::history() { return history_; }
CommandRegistry &Session::registry() { return registry_; }
EngineBackend *Session::engine() { return engine_; }
QString Session::historyPath() const {
    return QDir(files_.root()).filePath(".workbench/history.json");
}
void Session::saveHistory(const History &history) const {
    if (!history.save(historyPath())) throw CommandError{"cannot save history: " + historyPath()};
}

QJsonObject Session::commit(const CommandContext &ctx, const QString &command, const QJsonObject &args,
                            const QString &summary, const QVector<FileChange> &changes) {
    if (changes.isEmpty()) return {{"applied", false}, {"note", "no change"}};
    try {
        HistoryEntry entry;
        entry.author = ctx.author;
        entry.command = command;
        entry.args = args;
        entry.summary = summary;
        entry.changes = checkedChanges(changes);
        History next = history_;
        if (ctx.propose || (ctx.author == "agent" && agentProposals)) {
            const int id = next.propose(std::move(entry));
            saveHistory(next);
            history_ = std::move(next);
            return {{"proposed", true}, {"entry", id}};
        }

        QSet<QString> external;
        for (const auto &path : files_.externalChanges()) external.insert(pathIdentity(path));
        // A separate reader compares the supplied before-bytes without acknowledging
        // hand edits in files_. Preflight every path before changing any source.
        FileStore disk(files_.root());
        QVector<bool> existed;
        existed.reserve(entry.changes.size());
        for (const auto &change : entry.changes) {
            if (external.contains(pathIdentity(change.path)) || disk.read(change.path) != change.before)
                throw CommandError{"changed externally: " + change.path};
            existed.append(disk.exists(change.path));
        }
        // Prepare the history update before writing: even an exhausted id counter
        // must leave source files alone. Failed commits also retain the redo branch.
        const int id = next.record(entry);
        const QString snapshot = files_.beginSnapshot(command);
        qsizetype written = 0;
        try {
            for (const auto &change : entry.changes) {
                files_.write(change.path, change.after);
                ++written;
            }
            saveHistory(next);
        } catch (...) {
            const QString failure = exceptionMessage(std::current_exception());
            QStringList rollbackErrors;
            // FileStore keeps the originals in this snapshot group and refuses
            // rollback if someone edited a successfully written file meanwhile.
            while (written > 0) {
                const qsizetype index = --written;
                const auto &change = entry.changes[index];
                try {
                    if (existed[index]) {
                        files_.write(change.path, change.before);
                    } else if (!files_.remove(change.path)) {
                        throw CommandError{"cannot remove: " + change.path};
                    }
                } catch (...) {
                    rollbackErrors.append(change.path + ": " + exceptionMessage(std::current_exception()));
                }
            }
            QString message = failure;
            if (!rollbackErrors.isEmpty()) message += "; rollback failed: " + rollbackErrors.join("; ");
            throw CommandError{message + "; snapshots: " + snapshot};
        }
        history_ = std::move(next);
        // A refresh error must never turn an applied command into an edit with no
        // undo entry. It remains applied and persisted, and the error says so.
        try {
            if (onApplied) onApplied();
        } catch (...) {
            throw CommandError{QString("changes applied (entry %1); reload failed: %2")
                .arg(id).arg(exceptionMessage(std::current_exception()))};
        }
        return {{"applied", true}, {"entry", id}};
    } catch (const std::exception &error) {
        throw CommandError{QString::fromUtf8(error.what())};
    }
}
} // namespace wb
