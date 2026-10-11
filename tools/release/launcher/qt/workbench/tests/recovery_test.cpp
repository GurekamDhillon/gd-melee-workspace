#include "../testfixture.h"
#include "commands.h"
#include "geno_data.h"
#include "history.h"
#include "recovery.h"
#include "session.h"
#include <QCoreApplication>
#include <QDateTime>
#include <QTemporaryDir>
#include <QtTest>

using namespace wb;

namespace {
constexpr qint64 kDeadPid = 2147483000; // no such process
QByteArray readAll(const QString &dir, const QString &rel) {
    QFile f(QDir(dir).filePath(rel));
    return f.open(QIODevice::ReadOnly) ? f.readAll() : QByteArray();
}
void writeFile(const QString &dir, const QString &rel, const QByteArray &bytes) {
    QFile f(QDir(dir).filePath(rel));
    QVERIFY(f.open(QIODevice::WriteOnly | QIODevice::Truncate));
    f.write(bytes);
}
HitboxEdit damageEdit(double d) { HitboxEdit e; e.damage = d; return e; }
// A crashed run's mark: a process that no longer exists, started `ago` seconds back.
void plantDeadMark(const QString &dir, qint64 ago) {
    QDir().mkpath(QDir(dir).filePath(".workbench"));
    writeFile(dir, ".workbench/session.lock.json",
              QJsonDocument(QJsonObject{{"pid", kDeadPid}, {"started", QDateTime::currentSecsSinceEpoch() - ago}}).toJson());
}
}

class RecoveryTest : public QObject {
    Q_OBJECT
private slots:
    void aCleanCommitLeavesNoJournal() {
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path());
        Session s(dir.path(), nullptr); registerAllCommands(s);
        QString err; const auto changes = s.data().editHitbox("dair", 0, damageEdit(19), &err);
        QVERIFY2(!changes.isEmpty(), qPrintable(err));
        CommandContext ctx{s};
        QVERIFY(s.commit(ctx, "edit_hitbox", {}, "dair damage", changes)["applied"].toBool());
        QVERIFY(!QFileInfo::exists(journalPath(dir.path())));
        QVERIFY(QFileInfo::exists(s.historyPath()));
    }
    void aCommitThatFailsLeavesNoJournalEither() {
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path());
        Session s(dir.path(), nullptr); registerAllCommands(s);
        QString err; const auto changes = s.data().editHitbox("dair", 0, damageEdit(19), &err);
        writeFile(dir.path(), "moves/dair.genoasm", readAll(dir.path(), "moves/dair.genoasm") + "# hand edit\n");
        CommandContext ctx{s};
        QVERIFY_EXCEPTION_THROWN(s.commit(ctx, "edit_hitbox", {}, "dair damage", changes), CommandError);
        QVERIFY(!QFileInfo::exists(journalPath(dir.path())));
    }
    void interruptedCommitIsOfferedAndRestored() {
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path());
        QVector<FileChange> changes;
        {
            Session s(dir.path(), nullptr);
            QString err; changes = s.data().editHitbox("dair", 0, damageEdit(19), &err);
            QVERIFY2(changes.size() >= 1, qPrintable(err));
        }
        // The process died after the journal and the first file, before the rest and the history.
        HistoryEntry entry; entry.author = "human"; entry.command = "edit_hitbox"; entry.summary = "dair damage"; entry.changes = changes;
        writeJournal(dir.path(), entry);
        writeFile(dir.path(), changes[0].path, changes[0].after);

        Session s(dir.path(), nullptr); registerAllCommands(s);
        const auto info = detectRecovery(s, SessionMark{});
        QVERIFY(info.journalPending); QVERIFY(info.restorable()); QVERIFY(info.any());
        QCOMPARE(info.journalFiles, int(changes.size())); QVERIFY(info.journalWritten >= 1);
        QVERIFY(info.journalConflicts.isEmpty());
        QCOMPARE(info.journalSummary, QString("dair damage"));
        QVERIFY(info.count() >= 1);
        s.recovery = info.toJson();

        const auto result = resolveRecovery(s, "restore");
        QVERIFY(result["restored"].toInt() >= 0);
        for (const auto &change : changes) QCOMPARE(readAll(dir.path(), change.path), change.after);
        QVERIFY(!QFileInfo::exists(journalPath(dir.path())));
        QVERIFY(s.recovery.isEmpty());
        QCOMPARE(s.history().entries().size(), qsizetype(1));
        QCOMPARE(s.history().entries().first().state, QString("applied"));
        QCOMPARE(s.data().hitboxes("dair").first().damage, 19.0);
        // The restored edit is an ordinary history entry: undo works.
        CommandContext ctx{s};
        QVERIFY(s.registry().call("undo", {}, ctx)["ok"].toBool());
        QCOMPARE(s.data().hitboxes("dair").first().damage, 14.0);
    }
    void interruptedCommitCanBeDiscarded() {
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path());
        QVector<FileChange> changes;
        { Session s(dir.path(), nullptr); QString err; changes = s.data().editHitbox("dair", 0, damageEdit(19), &err); }
        HistoryEntry entry; entry.author = "human"; entry.command = "edit_hitbox"; entry.summary = "dair damage"; entry.changes = changes;
        writeJournal(dir.path(), entry);
        writeFile(dir.path(), changes[0].path, changes[0].after);
        Session s(dir.path(), nullptr); registerAllCommands(s);
        s.recovery = detectRecovery(s, SessionMark{}).toJson();
        resolveRecovery(s, "discard");
        for (const auto &change : changes) QCOMPARE(readAll(dir.path(), change.path), change.before);
        QVERIFY(!QFileInfo::exists(journalPath(dir.path())));
        QVERIFY(s.history().entries().isEmpty());
        QCOMPARE(s.data().hitboxes("dair").first().damage, 14.0);
    }
    void aFileChangedSinceTheCrashBlocksRestoreButNotDiscard() {
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path());
        QVector<FileChange> changes;
        { Session s(dir.path(), nullptr); QString err; changes = s.data().editHitbox("dair", 0, damageEdit(19), &err); }
        HistoryEntry entry; entry.command = "edit_hitbox"; entry.summary = "dair damage"; entry.changes = changes;
        writeJournal(dir.path(), entry);
        writeFile(dir.path(), changes[0].path, "# someone else wrote this\n");
        Session s(dir.path(), nullptr); registerAllCommands(s);
        const auto info = detectRecovery(s, SessionMark{});
        QVERIFY(info.journalConflicts.contains(changes[0].path));
        QVERIFY_EXCEPTION_THROWN(resolveRecovery(s, "restore"), CommandError);
        QVERIFY(QFileInfo::exists(journalPath(dir.path()))); // still there to decide on
        resolveRecovery(s, "keep");
        QVERIFY(s.recovery.isEmpty());
    }
    void aJournalWhoseCommitReachedHistoryIsDropped() {
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path());
        {
            Session s(dir.path(), nullptr); registerAllCommands(s);
            QString err; const auto changes = s.data().editHitbox("dair", 0, damageEdit(19), &err);
            CommandContext ctx{s};
            s.commit(ctx, "edit_hitbox", {}, "dair damage", changes);
            // Died between saving history and removing the journal.
            writeJournal(dir.path(), s.history().entries().first());
        }
        Session s(dir.path(), nullptr); registerAllCommands(s);
        const auto info = detectRecovery(s, SessionMark{});
        QVERIFY(!info.journalPending);
        QVERIFY(!QFileInfo::exists(journalPath(dir.path())));
    }
    void anUncleanExitWithEditsSinceTheBuildIsReported() {
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path());
        plantDeadMark(dir.path(), 100);
        Session s(dir.path(), nullptr); registerAllCommands(s);
        const auto prior = readSessionMark(dir.path());
        QVERIFY(prior.existed); QCOMPARE(prior.pid, kDeadPid);
        captureBaseline(s); // the "last build"
        QString err; const auto changes = s.data().editHitbox("dair", 0, damageEdit(19), &err);
        CommandContext ctx{s};
        s.commit(ctx, "edit_hitbox", {}, "dair damage", changes);
        const auto info = detectRecovery(s, prior);
        QVERIFY(info.uncleanExit);
        QCOMPARE(info.unsavedChanges, 1);
        QVERIFY(info.any()); QVERIFY(!info.restorable());
        QCOMPARE(info.count(), 1);
        QVERIFY(info.time() > 0);
        QCOMPARE(info.toJson()["unsaved_changes"].toInt(), 1);
        // "keep" changes nothing and clears the notice.
        s.recovery = info.toJson();
        resolveRecovery(s, "keep");
        QCOMPARE(s.data().hitboxes("dair").first().damage, 19.0);
        QVERIFY(s.recovery.isEmpty());
    }
    void aLiveOrOwnProcessIsNotACrash() {
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path());
        markSessionOpen(dir.path(), QCoreApplication::applicationPid());
        Session s(dir.path(), nullptr); registerAllCommands(s);
        QVERIFY(!detectRecovery(s, readSessionMark(dir.path())).uncleanExit);
        QVERIFY(processAlive(QCoreApplication::applicationPid()));
        QVERIFY(!processAlive(kDeadPid)); QVERIFY(!processAlive(0));
        markSessionClosed(dir.path(), kDeadPid); // someone else's mark stays
        QVERIFY(QFileInfo::exists(sessionMarkPath(dir.path())));
        markSessionClosed(dir.path(), QCoreApplication::applicationPid());
        QVERIFY(!QFileInfo::exists(sessionMarkPath(dir.path())));
        QVERIFY(!readSessionMark(dir.path()).existed);
    }
    void aFileThatLostItsEditIsRestoredFromHistory() {
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path());
        plantDeadMark(dir.path(), 100);
        QVector<FileChange> changes;
        {
            Session s(dir.path(), nullptr); registerAllCommands(s);
            QString err; changes = s.data().editHitbox("dair", 0, damageEdit(19), &err);
            CommandContext ctx{s};
            s.commit(ctx, "edit_hitbox", {}, "dair damage", changes);
        }
        writeFile(dir.path(), changes[0].path, changes[0].before); // e.g. a stray checkout wiped the edit
        Session s(dir.path(), nullptr); registerAllCommands(s);
        const auto info = detectRecovery(s, readSessionMark(dir.path()));
        QVERIFY(info.uncleanExit); QVERIFY(info.driftPaths.contains(changes[0].path)); QVERIFY(info.restorable());
        s.recovery = info.toJson();
        resolveRecovery(s, "restore");
        QCOMPARE(readAll(dir.path(), changes[0].path), changes[0].after);
        QCOMPARE(s.data().hitboxes("dair").first().damage, 19.0);
    }
    void recoveryCommandsReportAndRejectBadActions() {
        QTemporaryDir dir; wbtest::makeSynthFighter(dir.path());
        Session s(dir.path(), nullptr); registerAllCommands(s);
        CommandContext ctx{s};
        QVERIFY(!s.registry().call("recovery_status", {}, ctx)["result"].toObject()["pending"].toBool());
        s.recovery = QJsonObject{{"count", 2}};
        QVERIFY(s.registry().call("recovery_status", {}, ctx)["result"].toObject()["pending"].toBool());
        QVERIFY(!s.registry().call("recovery_resolve", {{"action", "explode"}}, ctx)["ok"].toBool());
        QVERIFY(s.registry().call("recovery_resolve", {{"action", "keep"}}, ctx)["ok"].toBool());
        QVERIFY(s.recovery.isEmpty());
    }
};
QTEST_MAIN(RecoveryTest)
#include "recovery_test.moc"
