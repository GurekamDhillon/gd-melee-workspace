#pragma once
#include "session.h"
#include <QJsonObject>
#include <QStringList>

// Crash recovery for a Workbench project. Source edits are already written (atomically, with a snapshot and a
// history entry) the moment they are made; what a crash can leave behind is
//   - an interrupted commit: the write-ahead journal (.workbench/journal.json) outlives the commit it covered;
//   - an unclean close: the session mark (.workbench/session.lock.json) names a process that is gone;
//   - drift: a file an applied edit of that run should have left different.
// On the next open the Workbench offers "Restore N unsaved changes from <time>?" using this.
namespace wb {
struct HistoryEntry;

struct SessionMark {
    bool existed = false;
    qint64 pid = 0, started = 0; // started: seconds since the epoch
};
struct RecoveryInfo {
    bool uncleanExit = false;
    qint64 previousStart = 0;
    bool journalPending = false;
    int journalFiles = 0, journalWritten = 0;
    QStringList journalConflicts; // files that match neither the journal's before nor after bytes
    QString journalSummary;
    qint64 journalTime = 0;
    QStringList driftPaths;
    int unsavedChanges = 0;      // fields that differ from the last build (the baseline mirror)
    qint64 lastEditTime = 0;     // newest applied history entry, seconds since the epoch
    bool restorable() const { return journalPending || !driftPaths.isEmpty(); }
    bool any() const { return restorable() || (uncleanExit && unsavedChanges > 0); }
    int count() const;
    qint64 time() const { return journalPending && journalTime ? journalTime : lastEditTime; }
    QJsonObject toJson() const;
};

QString journalPath(const QString &root);
QString sessionMarkPath(const QString &root);
bool processAlive(qint64 pid);
// The write-ahead journal: written before a commit touches any source file, removed once history is saved.
void writeJournal(const QString &root, const HistoryEntry &entry); // throws std::runtime_error
void clearJournal(const QString &root);
SessionMark readSessionMark(const QString &root);
void markSessionOpen(const QString &root, qint64 pid);
void markSessionClosed(const QString &root, qint64 pid); // only removes a mark this process wrote
// Reads only; nothing is changed. `prior` is the mark read before markSessionOpen replaced it.
RecoveryInfo detectRecovery(Session &session, const SessionMark &prior);
// action: "restore" (finish an interrupted commit, re-apply drifted files), "discard" (roll an interrupted commit
// back), "keep" (nothing to change). Clears Session::recovery. Throws CommandError.
QJsonObject resolveRecovery(Session &session, const QString &action);
void registerRecoveryCommands(Session &);
}
