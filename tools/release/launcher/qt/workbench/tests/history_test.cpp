#include "history.h"
#include <QTemporaryDir>
#include <QDateTime>
#include <QFile>
#include <QFileInfo>
#include <stdexcept>
#include <QtTest>
using namespace wb;

static HistoryEntry edit(const QString &path, const QByteArray &b, const QByteArray &a, const QString &author = "human") {
    HistoryEntry e; e.author = author; e.command = "t"; e.summary = "s";
    e.changes.append({path, b, a});
    return e;
}

class HistoryTest : public QObject {
    Q_OBJECT
private slots:
    void undoRedoRoundTrip() {
        QTemporaryDir d; FileStore fs(d.path()); History h;
        fs.write("f", "1");
        fs.write("f", "2");
        h.record(edit("f", "1", "2"));
        QString err;
        QVERIFY2(h.undo(fs, &err), qPrintable(err));
        QCOMPARE(fs.read("f"), QByteArray("1"));
        QVERIFY2(h.redo(fs, &err), qPrintable(err));
        QCOMPARE(fs.read("f"), QByteArray("2"));
    }
    void undoRefusesAfterExternalEdit() {
        QTemporaryDir d; FileStore fs(d.path()); History h;
        fs.write("f", "2"); h.record(edit("f", "1", "2"));
        QFile f(d.filePath("f")); QVERIFY(f.open(QIODevice::WriteOnly)); f.write("HAND"); f.close();
        QString err;
        QVERIFY(!h.undo(fs, &err));
        QVERIFY(err.contains("changed externally"));
        QCOMPARE(fs.read("f"), QByteArray("HAND"));   // untouched
    }
    void newRecordClearsRedo() {
        QTemporaryDir d; FileStore fs(d.path()); History h; QString err;
        fs.write("f", "2"); h.record(edit("f", "1", "2")); QVERIFY(h.undo(fs, &err));
        fs.write("f", "9"); h.record(edit("f", "1", "9"));
        QVERIFY(!h.redo(fs, &err));
    }
    void proposalDoesNotTouchFilesUntilAccepted() {
        QTemporaryDir d; FileStore fs(d.path()); History h; QString err;
        fs.write("f", "1");
        int id = h.propose(edit("f", "1", "2", "agent"));
        QCOMPARE(fs.read("f"), QByteArray("1"));
        QVERIFY2(h.accept(id, fs, &err), qPrintable(err));
        QCOMPARE(fs.read("f"), QByteArray("2"));
    }
    void staleProposalIsRefused() {
        QTemporaryDir d; FileStore fs(d.path()); History h; QString err;
        fs.write("f", "1");
        int id = h.propose(edit("f", "1", "2", "agent"));
        fs.write("f", "OTHER");
        QVERIFY(!h.accept(id, fs, &err));
        QVERIFY(err.contains("stale proposal"));
    }
    void rejectMarksRejected() {
        History h; QString err;
        int id = h.propose(edit("f", "1", "2", "agent"));
        QVERIFY(h.reject(id, &err));
        QCOMPARE(h.entries().first().state, QString("rejected"));
    }
    void persistsAcrossSessions() {
        QTemporaryDir d; History h;
        h.record(edit("f", QByteArray("\x00\x01", 2), "2"));
        QVERIFY(h.save(d.filePath("history.json")));
        History h2 = History::load(d.filePath("history.json"));
        QCOMPARE(h2.entries().size(), 1);
        QCOMPARE(h2.entries().first().changes.first().before, QByteArray("\x00\x01", 2));
    }
    void newFileUndoDeletesIt() {
        QTemporaryDir d; FileStore fs(d.path()); History h; QString err;
        fs.write("new.txt", "x"); h.record(edit("new.txt", "", "x"));
        QVERIFY2(h.undo(fs, &err), qPrintable(err));
        QVERIFY(!fs.exists("new.txt"));
    }
    void undoChecksEveryFileBeforeWritingAnything() {
        QTemporaryDir d; FileStore fs(d.path()); History h; QString err;
        fs.write("a", "2"); fs.write("b", "HAND");
        HistoryEntry e = edit("a", "1", "2"); e.changes.append({"b", "1", "2"}); h.record(e);
        QVERIFY(!h.undo(fs, &err)); QVERIFY(err.contains("changed externally: b"));
        QCOMPARE(fs.read("a"), QByteArray("2")); QCOMPARE(fs.read("b"), QByteArray("HAND"));
        QCOMPARE(h.entries().first().state, QString("applied"));
    }
    void redoChecksEveryFileBeforeWritingAnything() {
        QTemporaryDir d; FileStore fs(d.path()); History h; QString err;
        fs.write("a", "2"); fs.write("b", "2");
        HistoryEntry e = edit("a", "1", "2"); e.changes.append({"b", "1", "2"}); h.record(e);
        QVERIFY(h.undo(fs, &err)); fs.write("b", "HAND");
        QVERIFY(!h.redo(fs, &err)); QVERIFY(err.contains("changed externally: b"));
        QCOMPARE(fs.read("a"), QByteArray("1")); QCOMPARE(fs.read("b"), QByteArray("HAND"));
        QCOMPARE(h.entries().first().state, QString("undone"));
    }
    void acceptChecksEveryFileBeforeWritingAnything() {
        QTemporaryDir d; FileStore fs(d.path()); History h; QString err;
        fs.write("a", "1"); fs.write("b", "HAND");
        HistoryEntry e = edit("a", "1", "2"); e.changes.append({"b", "1", "2"});
        const int id = h.propose(e);
        QVERIFY(!h.accept(id, fs, &err)); QVERIFY(err.contains("stale proposal: b"));
        QCOMPARE(fs.read("a"), QByteArray("1"));
        QCOMPARE(h.entries().first().state, QString("proposed"));
    }
    void undoDoesNotAcknowledgeAConflictingHandEdit() {
        QTemporaryDir d; FileStore fs(d.path()); History h; QString err;
        fs.write("f", "2"); h.record(edit("f", "1", "2"));
        QFile f(d.filePath("f")); QVERIFY(f.open(QIODevice::WriteOnly)); f.write("HAND"); f.close();
        QVERIFY(!h.undo(fs, &err));
        QCOMPARE(fs.externalChanges(), QStringList{"f"});
    }
    void undoRefusesMtimeOnlyExternalEdit() {
        QTemporaryDir d; FileStore fs(d.path()); History h; QString err;
        fs.write("f", "2"); h.record(edit("f", "1", "2"));
        const QDateTime later = QFileInfo(d.filePath("f")).lastModified().addSecs(10);
        QFile f(d.filePath("f")); QVERIFY(f.open(QIODevice::ReadWrite));
        QVERIFY(f.setFileTime(later, QFileDevice::FileModificationTime)); f.close();
        QVERIFY(!h.undo(fs, &err)); QVERIFY(err.contains("changed externally"));
        QCOMPARE(fs.externalChanges(), QStringList{"f"});
    }
    void multipleUndosRedoInApplyOrder() {
        QTemporaryDir d; FileStore fs(d.path()); History h; QString err;
        fs.write("f", "2"); h.record(edit("f", "1", "2"));
        fs.write("f", "3"); h.record(edit("f", "2", "3"));
        QVERIFY(h.undo(fs, &err)); QVERIFY(h.undo(fs, &err));
        QCOMPARE(fs.read("f"), QByteArray("1"));
        QVERIFY(h.redo(fs, &err)); QCOMPARE(fs.read("f"), QByteArray("2"));
        QVERIFY(h.redo(fs, &err)); QCOMPARE(fs.read("f"), QByteArray("3"));
        QVERIFY(!h.redo(fs, &err));
    }
    void acceptedOldProposalIsUndoneBeforeLaterRecordedWork() {
        QTemporaryDir d; FileStore fs(d.path()); History h; QString err;
        fs.write("f", "1"); const int proposal = h.propose(edit("f", "1", "2", "agent"));
        fs.write("g", "b"); h.record(edit("g", "a", "b"));
        QVERIFY(h.accept(proposal, fs, &err));
        History loaded = History::fromJson(h.toJson());
        QVERIFY(loaded.undo(fs, &err));
        QCOMPARE(fs.read("f"), QByteArray("1")); QCOMPARE(fs.read("g"), QByteArray("b"));
        QCOMPARE(loaded.entries().last().id, proposal);
    }
    void acceptanceClearsRedoAndPersistsIdHighWaterMark() {
        QTemporaryDir d; FileStore fs(d.path()); History h; QString err;
        fs.write("f", "1"); const int proposal = h.propose(edit("f", "1", "2"));
        fs.write("g", "b"); const int laterId = h.record(edit("g", "a", "b"));
        QVERIFY(h.undo(fs, &err));
        QVERIFY(h.accept(proposal, fs, &err));
        QVERIFY(!h.redo(fs, &err));
        History loaded = History::fromJson(h.toJson());
        QVERIFY(!loaded.redo(fs, &err));
        QVERIFY(loaded.propose(edit("h", "x", "y")) > laterId);
    }
    void persistedUndoAndProposalRemainUsable() {
        QTemporaryDir d; FileStore fs(d.path()); History h; QString err;
        fs.write("f", "2"); h.record(edit("f", "1", "2")); QVERIFY(h.undo(fs, &err));
        HistoryEntry proposal = edit("g", "", QByteArray("\0\1\xff", 3), "agent");
        proposal.command = "binary"; proposal.summary = "binary file"; proposal.args = {{"row", "synthetic"}};
        const int id = h.propose(proposal);
        QVERIFY(h.save(d.filePath("history.json")));
        History loaded = History::load(d.filePath("history.json"));
        QCOMPARE(loaded.entries().last().args, proposal.args);
        QCOMPARE(loaded.entries().last().author, QString("agent"));
        QVERIFY(loaded.entries().last().time > 0);
        QVERIFY(loaded.redo(fs, &err)); QCOMPARE(fs.read("f"), QByteArray("2"));
        QVERIFY(loaded.accept(id, fs, &err)); QCOMPARE(fs.read("g"), QByteArray("\0\1\xff", 3));
        QVERIFY(loaded.undo(fs, &err)); QVERIFY(!fs.exists("g"));
        QVERIFY(loaded.redo(fs, &err)); QCOMPARE(fs.read("g"), QByteArray("\0\1\xff", 3));
    }
    void redoDoesNotOverwriteNewExternalFile() {
        QTemporaryDir d; FileStore fs(d.path()); History h; QString err;
        fs.write("new", "x"); h.record(edit("new", "", "x")); QVERIFY(h.undo(fs, &err));
        QFile f(d.filePath("new")); QVERIFY(f.open(QIODevice::WriteOnly)); f.write("HAND"); f.close();
        QVERIFY(!h.redo(fs, &err)); QVERIFY(err.contains("changed externally"));
        QCOMPARE(fs.read("new"), QByteArray("HAND"));
    }
    void invalidAndDuplicatePathsFailBeforeAnyWrite() {
        QTemporaryDir d; FileStore fs(d.path()); QString err; fs.write("f", "1");
        for (const QString &other : {QString("../escape"), QString("./f")}) {
            History h; HistoryEntry e = edit("f", "1", "2"); e.changes.append({other, "1", "2"});
            const int id = h.propose(e);
            QVERIFY(!h.accept(id, fs, &err)); QVERIFY(!err.isEmpty());
            QCOMPARE(fs.read("f"), QByteArray("1"));
            QCOMPARE(h.entries().first().state, QString("proposed"));
        }
    }
    void invalidTransitionsAndEmptyStacksReportErrors() {
        QTemporaryDir d; FileStore fs(d.path()); History h; QString err;
        QVERIFY(!h.undo(fs, &err)); QVERIFY(!err.isEmpty());
        QVERIFY(!h.redo(fs, &err)); QVERIFY(!err.isEmpty());
        QVERIFY(!h.accept(99, fs, &err)); QVERIFY(!h.reject(99, &err));
        const int id = h.propose(edit("f", "", "x")); QVERIFY(h.reject(id, &err)); QVERIFY(err.isEmpty());
        QVERIFY(!h.accept(id, fs, &err)); QVERIFY(!h.reject(id, &err)); QVERIFY(!fs.exists("f"));
    }
    void invalidPersistenceCannotSilentlyEraseHistory() {
        QTemporaryDir d; QFile f(d.filePath("history.json"));
        QVERIFY(f.open(QIODevice::WriteOnly)); f.write("{broken"); f.close();
        QVERIFY_EXCEPTION_THROWN(History::load(f.fileName()), std::runtime_error);
        History h; h.record(edit("f", "1", "2")); QJsonArray json = h.toJson();
        QJsonObject entry = json.first().toObject(); QJsonArray changes = entry["changes"].toArray();
        QJsonObject change = changes.first().toObject(); change["before"] = "not base64!";
        changes[0] = change; entry["changes"] = changes; json[0] = entry;
        QVERIFY_EXCEPTION_THROWN(History::fromJson(json), std::runtime_error);
        QVERIFY(!h.save(d.path()));
        QVERIFY(History::load(d.filePath("missing.json")).entries().isEmpty());
    }

    void windowsCaseAliasesCannotHideDuplicateChanges() {
#ifndef Q_OS_WIN
        QSKIP("Windows case-insensitive filesystem regression");
#else
        QTemporaryDir d; FileStore fs(d.path()); History h; QString err;
        fs.write("Mixed.txt", "1");
        HistoryEntry e = edit("Mixed.txt", "1", "2"); e.changes.append({"MIXED.TXT", "1", "3"});
        const int id = h.propose(e);
        QVERIFY(!h.accept(id, fs, &err)); QVERIFY(err.contains("duplicate path"));
        QCOMPARE(fs.read("Mixed.txt"), QByteArray("1"));
        QCOMPARE(h.entries().first().state, QString("proposed"));
#endif
    }

};
QTEST_MAIN(HistoryTest)
#include "history_test.moc"
