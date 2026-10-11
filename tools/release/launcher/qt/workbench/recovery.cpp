#include "recovery.h"
#include "commands.h"
#include "history.h"
#include "launcher_core.h"
#include <QCoreApplication>
#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonArray>
#include <QMap>
#include <algorithm>
#include <optional>
#include <stdexcept>
#ifdef Q_OS_WIN
#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#else
#include <csignal>
#include <cerrno>
#endif

namespace wb {
namespace {
QString workbenchFile(const QString &root, const char *name) { return QDir(root).filePath(QString(".workbench/") + name); }
// The bytes at `rel` as the journal sees them: a missing file is empty (the history contract for absence).
QByteArray diskBytes(const QString &root, const QString &rel) {
    QFile file(QDir(root).filePath(rel));
    if (!file.exists()) return {};
    if (!file.open(QIODevice::ReadOnly)) throw std::runtime_error((rel + ": " + file.errorString()).toUtf8().constData());
    return file.readAll();
}
struct Classified { QStringList written, pending, conflicts; };
Classified classify(const QString &root, const HistoryEntry &entry) {
    Classified out;
    for (const auto &change : entry.changes) {
        QByteArray now;
        try { now = diskBytes(root, change.path); } catch (const std::exception &) { out.conflicts.append(change.path); continue; }
        if (change.before == change.after) out.written.append(change.path);
        else if (now == change.after) out.written.append(change.path);
        else if (now == change.before) out.pending.append(change.path);
        else out.conflicts.append(change.path);
    }
    return out;
}
std::optional<HistoryEntry> loadJournal(const QString &root) {
    const QString path = journalPath(root);
    if (!QFileInfo::exists(path)) return std::nullopt;
    try {
        const auto history = History::load(path);
        if (history.entries().isEmpty()) return std::nullopt;
        return history.entries().first();
    } catch (const std::exception &) { return std::nullopt; }
}
// Did this journal's commit reach history? (A crash between saving history and removing the journal.)
bool alreadyRecorded(Session &session, const HistoryEntry &journal) {
    for (const auto &entry : session.history().entries()) {
        if (entry.command != journal.command || entry.summary != journal.summary || entry.changes.size() != journal.changes.size()) continue;
        bool same = true;
        for (qsizetype i = 0; i < entry.changes.size() && same; ++i)
            same = entry.changes[i].path == journal.changes[i].path && entry.changes[i].after == journal.changes[i].after &&
                   entry.changes[i].before == journal.changes[i].before;
        if (same) return true;
    }
    return false;
}
// What the edits of a run that began at `since` say each file should hold now.
QMap<QString, QByteArray> expectedBytes(Session &session, qint64 since) {
    QMap<QString, QByteArray> expected;
    for (const auto &entry : session.history().entries()) {
        if (entry.time < since) continue;
        if (entry.state != "applied" && entry.state != "undone") continue;
        for (const auto &change : entry.changes) expected.insert(change.path, entry.state == "applied" ? change.after : change.before);
    }
    return expected;
}
QStringList driftOf(Session &session, qint64 since) {
    QStringList drift;
    const auto expected = expectedBytes(session, since);
    for (auto it = expected.cbegin(); it != expected.cend(); ++it) {
        try { if (diskBytes(session.files().root(), it.key()) != it.value()) drift.append(it.key()); }
        catch (const std::exception &) { drift.append(it.key()); }
    }
    return drift;
}
void putBytes(Session &session, const QString &rel, const QByteArray &bytes) {
    // The bytes were verified against the journal or history by the caller, so whatever FileStore last saw of
    // this file is not a reason to refuse: take the disk as the new known version first.
    try { session.files().acknowledge(rel); } catch (const std::exception &) {}
    if (bytes.isEmpty()) { if (session.files().exists(rel) && !session.files().remove(rel)) throw CommandError{"cannot remove: " + rel}; }
    else session.files().write(rel, bytes);
}
}

int RecoveryInfo::count() const {
    return std::max(unsavedChanges, driftPaths.isEmpty() ? 0 : 1) + (journalPending ? 1 : 0);
}
QJsonObject RecoveryInfo::toJson() const {
    return {{"unclean_exit", uncleanExit}, {"restorable", restorable()}, {"count", count()}, {"time", time()},
            {"previous_start", previousStart}, {"unsaved_changes", unsavedChanges}, {"journal_pending", journalPending}, {"journal_files", journalFiles},
            {"journal_written", journalWritten}, {"journal_summary", journalSummary},
            {"journal_conflicts", QJsonArray::fromStringList(journalConflicts)},
            {"drift", QJsonArray::fromStringList(driftPaths)}, {"last_edit", lastEditTime}};
}

QString journalPath(const QString &root) { return workbenchFile(root, "journal.json"); }
QString sessionMarkPath(const QString &root) { return workbenchFile(root, "session.lock.json"); }
bool processAlive(qint64 pid) {
    if (pid <= 0) return false;
#ifdef Q_OS_WIN
    const HANDLE process = OpenProcess(SYNCHRONIZE, FALSE, DWORD(pid));
    if (!process) return GetLastError() == ERROR_ACCESS_DENIED; // exists but not ours to query
    const bool exited = WaitForSingleObject(process, 0) == WAIT_OBJECT_0;
    CloseHandle(process);
    return !exited;
#else
    return kill(pid_t(pid), 0) == 0 || errno == EPERM;
#endif
}
void writeJournal(const QString &root, const HistoryEntry &entry) {
    History journal;
    journal.record(entry);
    if (!journal.save(journalPath(root))) throw std::runtime_error(("cannot write the recovery journal: " + journalPath(root)).toUtf8().constData());
}
void clearJournal(const QString &root) { QFile::remove(journalPath(root)); }
SessionMark readSessionMark(const QString &root) {
    SessionMark mark;
    QFile file(sessionMarkPath(root));
    if (!file.open(QIODevice::ReadOnly)) return mark;
    const auto object = QJsonDocument::fromJson(file.readAll()).object();
    if (object.isEmpty()) return mark;
    mark.existed = true; mark.pid = object.value("pid").toInteger(); mark.started = object.value("started").toInteger();
    return mark;
}
void markSessionOpen(const QString &root, qint64 pid) {
    try {
        launcher::writeAtomic(sessionMarkPath(root), QJsonDocument(QJsonObject{{"pid", pid},
            {"started", QDateTime::currentSecsSinceEpoch()}}).toJson(QJsonDocument::Compact));
    } catch (const std::exception &) { /* a read-only project still opens; recovery just has no mark */ }
}
void markSessionClosed(const QString &root, qint64 pid) {
    const auto mark = readSessionMark(root);
    if (mark.existed && mark.pid == pid) QFile::remove(sessionMarkPath(root));
}

RecoveryInfo detectRecovery(Session &session, const SessionMark &prior) {
    RecoveryInfo info;
    const QString root = session.files().root();
    const qint64 self = QCoreApplication::applicationPid();
    info.uncleanExit = prior.existed && prior.pid != self && !processAlive(prior.pid);
    info.previousStart = prior.started;
    // The journal is checked whether or not the mark says the close was clean: an interrupted commit is the
    // one case where a file on disk is not what history says.
    if (const auto journal = loadJournal(root)) {
        if (alreadyRecorded(session, *journal)) clearJournal(root);
        else {
            const auto state = classify(root, *journal);
            info.journalFiles = int(journal->changes.size()); info.journalWritten = int(state.written.size());
            info.journalConflicts = state.conflicts; info.journalSummary = journal->summary; info.journalTime = journal->time;
            info.journalPending = true;
        }
    }
    for (const auto &entry : session.history().entries()) if (entry.state == "applied") info.lastEditTime = std::max(info.lastEditTime, entry.time);
    if (info.uncleanExit) info.driftPaths = driftOf(session, info.previousStart);
    try { info.unsavedChanges = int(baselineChanges(session).size()); } catch (...) {}
    return info;
}

QJsonObject resolveRecovery(Session &session, const QString &action) {
    const QString root = session.files().root();
    QJsonObject result{{"action", action}, {"restored", 0}};
    if (action != "restore" && action != "discard" && action != "keep")
        throw CommandError{"recovery action must be restore, discard or keep"};
    if (action == "keep") { session.recovery = {}; return result; }
    const auto journal = loadJournal(root);
    int touched = 0;
    session.files().beginSnapshot("recovery");
    if (journal && !alreadyRecorded(session, *journal)) {
        const auto state = classify(root, *journal);
        if (action == "restore") {
            if (!state.conflicts.isEmpty())
                throw CommandError{"cannot restore: changed since the crash: " + state.conflicts.join(", ")};
            for (const auto &change : journal->changes) {
                if (!state.pending.contains(change.path)) continue;
                putBytes(session, change.path, change.after); ++touched;
            }
            History next = session.history();
            HistoryEntry entry = *journal; entry.state.clear();
            next.record(std::move(entry));
            if (!next.save(session.historyPath())) throw CommandError{"cannot save history: " + session.historyPath()};
            session.history() = std::move(next);
        } else {
            for (const auto &change : journal->changes) {
                if (!state.written.contains(change.path) || change.before == change.after) continue;
                putBytes(session, change.path, change.before); ++touched;
            }
        }
    }
    if (action == "restore") {
        // Drift: put back what the crashed run's own edits say the files hold.
        const qint64 since = session.recovery.value("previous_start").toInteger();
        if (session.recovery.value("unclean_exit").toBool()) {
            const auto expected = expectedBytes(session, since);
            for (const auto &path : driftOf(session, since)) { putBytes(session, path, expected.value(path)); ++touched; }
        }
    }
    clearJournal(root);
    session.recovery = {};
    const QString error = session.data().reload();
    if (!error.isEmpty()) throw CommandError{"data reload failed: " + error};
    if (session.onApplied) session.onApplied();
    result["restored"] = touched;
    return result;
}

void registerRecoveryCommands(Session &session) {
    session.registry().add({"recovery_status", t("Report what a crash left behind", "Informar de lo que dejó un cierre inesperado"),
        commandSchema(), false, [](const QJsonObject &, CommandContext &ctx) {
            return ctx.session.recovery.isEmpty() ? QJsonObject{{"pending", false}}
                       : QJsonObject{{"pending", true}, {"recovery", ctx.session.recovery}};
        }});
    session.registry().add({"recovery_resolve", t("Restore, discard or keep what a crash left behind", "Restaurar, descartar o conservar lo que dejó un cierre inesperado"),
        commandSchema({{"action", argType("string")}}, {"action"}), false, [](const QJsonObject &args, CommandContext &ctx) {
            return resolveRecovery(ctx.session, args.value("action").toString());
        }});
}
}
