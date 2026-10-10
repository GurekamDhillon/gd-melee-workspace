#include "file_store.h"
#include <QTemporaryDir>
#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <stdexcept>
#include <QtTest>
using namespace wb;

class FileStoreTest : public QObject {
    Q_OBJECT
private slots:
    void writeAndRead() {
        QTemporaryDir d; FileStore fs(d.path());
        fs.write("a/b.txt", "one");
        QCOMPARE(fs.read("a/b.txt"), QByteArray("one"));
    }
    void snapshotKeepsOldBytesBeforeOverwrite() {
        QTemporaryDir d; FileStore fs(d.path());
        fs.write("x.json", "old");
        QString snap = fs.beginSnapshot("save");
        fs.write("x.json", "new");
        fs.write("x.json", "newer");   // second write in the same group must not re-snapshot "new"
        QFile f(snap + "/x.json");
        QVERIFY(f.open(QIODevice::ReadOnly));
        QCOMPARE(f.readAll(), QByteArray("old"));
    }
    void detectsExternalChange() {
        QTemporaryDir d; FileStore fs(d.path());
        fs.write("g.json", "A");
        QVERIFY(fs.externalChanges().isEmpty());
        QFile f(d.filePath("g.json")); QVERIFY(f.open(QIODevice::WriteOnly)); f.write("B"); f.close();
        QCOMPARE(fs.externalChanges(), QStringList{"g.json"});
        fs.acknowledge("g.json");
        QVERIFY(fs.externalChanges().isEmpty());
    }
    void detectsExternalDelete() {
        QTemporaryDir d; FileStore fs(d.path());
        fs.write("g.json", "A");
        QFile::remove(d.filePath("g.json"));
        QCOMPARE(fs.externalChanges(), QStringList{"g.json"});
    }
    void rejectsEscapingPaths() {
        QString err;
        QVERIFY(FileStore::safeRel("../x", &err).isNull());
        QVERIFY(FileStore::safeRel("/etc/x", &err).isNull());
        QVERIFY(FileStore::safeRel("C:/x", &err).isNull());
        QVERIFY(FileStore::safeRel("", &err).isNull());
        QCOMPARE(FileStore::safeRel("a\\b.txt", &err), QString("a/b.txt"));
    }
    void refusesExternalOverwriteWithoutAcknowledgingIt() {
        QTemporaryDir d; FileStore fs(d.path());
        fs.write("f", "old");
        const QDateTime mtime = QFileInfo(d.filePath("f")).lastModified();
        QFile f(d.filePath("f"));
        QVERIFY(f.open(QIODevice::WriteOnly));
        QCOMPARE(f.write("HAND"), qint64(4));
        QVERIFY(f.setFileTime(mtime, QFileDevice::FileModificationTime));
        f.close();
        QVERIFY_EXCEPTION_THROWN(fs.write("f", "new"), std::runtime_error);
        QCOMPARE(fs.externalChanges(), QStringList{"f"});
        QVERIFY(f.open(QIODevice::ReadOnly));
        QCOMPARE(f.readAll(), QByteArray("HAND"));
    }
    void missingReadsAndRemovalsTrackExternalCreation() {
        QTemporaryDir d; FileStore fs(d.path());
        QVERIFY(fs.read("f").isEmpty());
        QFile f(d.filePath("f"));
        QVERIFY(f.open(QIODevice::WriteOnly)); f.write("external"); f.close();
        QCOMPARE(fs.externalChanges(), QStringList{"f"});
        QVERIFY_EXCEPTION_THROWN(fs.write("f", "new"), std::runtime_error);
        fs.acknowledge("f");
        QVERIFY(fs.remove("f"));
        QVERIFY(fs.externalChanges().isEmpty());
        QVERIFY(f.open(QIODevice::WriteOnly)); f.write("back"); f.close();
        QCOMPARE(fs.externalChanges(), QStringList{"f"});
        QVERIFY_EXCEPTION_THROWN(fs.remove("f"), std::runtime_error);
    }
    void pathAliasesShareKnownStateAndSnapshot() {
        QTemporaryDir d; FileStore fs(d.path());
        fs.write("a\\b", "old");
        const QString snap = fs.beginSnapshot("save");
        fs.write("./a/b", "new");
        fs.write("a//b", "newer");
        QFile f(snap + "/a/b"); QVERIFY(f.open(QIODevice::ReadOnly));
        QCOMPARE(f.readAll(), QByteArray("old"));
        QVERIFY(fs.externalChanges().isEmpty());
        QCOMPARE(fs.read("a/b"), QByteArray("newer"));
    }
    void snapshotGroupsAreUniqueAndLabelsCannotEscape() {
        QTemporaryDir d; FileStore fs(d.path());
        const QString one = fs.beginSnapshot("../../save");
        const QString two = fs.beginSnapshot("../../save");
        QVERIFY(one != two);
        const QString base = d.filePath(".workbench/snapshots");
        QCOMPARE(QFileInfo(one).absolutePath(), base);
        QCOMPARE(QFileInfo(two).absolutePath(), base);
    }
    void removeSnapshotsOldBytes() {
        QTemporaryDir d; FileStore fs(d.path());
        fs.write("f", "old");
        const QString snap = fs.beginSnapshot("delete");
        QVERIFY(fs.remove("f"));
        QVERIFY(!fs.exists("f"));
        QFile f(snap + "/f"); QVERIFY(f.open(QIODevice::ReadOnly));
        QCOMPARE(f.readAll(), QByteArray("old"));
        QVERIFY(fs.externalChanges().isEmpty());
        QVERIFY(fs.remove("f"));
    }
    void snapshotFailurePreventsOverwrite() {
        QTemporaryDir d; FileStore fs(d.path());
        fs.write("f", "old");
        const QString snap = fs.beginSnapshot("save");
        QVERIFY(QDir().mkdir(snap + "/f"));
        QVERIFY_EXCEPTION_THROWN(fs.write("f", "new"), std::runtime_error);
        QCOMPARE(fs.read("f"), QByteArray("old"));
    }
    void ungroupedOverwritesEachTakeASnapshot() {
        QTemporaryDir d; FileStore fs(d.path());
        fs.write("f", "old"); fs.write("f", "new"); fs.write("f", "newer");
        const QDir snapshots(d.filePath(".workbench/snapshots"));
        const auto groups = snapshots.entryList(QDir::Dirs | QDir::NoDotAndDotDot);
        QCOMPARE(groups.size(), 2);
        QList<QByteArray> saved;
        for (const auto &group : groups) {
            QFile f(snapshots.filePath(group + "/f"));
            QVERIFY(f.open(QIODevice::ReadOnly)); saved.append(f.readAll());
        }
        QVERIFY(saved.contains("old")); QVERIFY(saved.contains("new"));
    }
    void newFileIsNotResnapshottedWithinGroup() {
        QTemporaryDir d; FileStore fs(d.path());
        const QString snap = fs.beginSnapshot("save");
        fs.write("f", "new"); fs.write("f", "newer");
        QVERIFY(!QFile::exists(snap + "/f"));
    }
    void detectsMtimeOnlyChange() {
        QTemporaryDir d; FileStore fs(d.path()); fs.write("f", "same");
        const QDateTime later = QFileInfo(d.filePath("f")).lastModified().addSecs(10);
        QFile f(d.filePath("f")); QVERIFY(f.open(QIODevice::ReadWrite));
        QVERIFY(f.setFileTime(later, QFileDevice::FileModificationTime)); f.close();
        QCOMPARE(fs.externalChanges(), QStringList{"f"});
        QVERIFY_EXCEPTION_THROWN(fs.write("f", "new"), std::runtime_error);
        fs.acknowledge("f"); fs.write("f", "new");
        QVERIFY(fs.externalChanges().isEmpty());
    }
    void rejectsUnsafeAliasesAndRuntimePaths() {
        QString err;
        for (const QString &path : {QString("a/../x"), QString("a\\..\\x"), QString("\\\\host\\x"),
                                   QString("C:x"), QString("file:stream"), QString("."),
                                   QString("name."), QString("name "), QString(".. /escape"),
                                   QString("a") + QChar(0) + "b"}) {
            QVERIFY2(FileStore::safeRel(path, &err).isNull(), qPrintable(path));
            QVERIFY(!err.isEmpty());
        }
        QTemporaryDir d; FileStore fs(d.path());
        QVERIFY_EXCEPTION_THROWN(fs.write("../escape", "x"), std::runtime_error);
        QVERIFY_EXCEPTION_THROWN(fs.read("../escape"), std::runtime_error);
        QVERIFY_EXCEPTION_THROWN(fs.remove("../escape"), std::runtime_error);
    }
    void symlinkCannotEscapeProjectOrSnapshotDirectory() {
#ifndef Q_OS_UNIX
        QSKIP("QFile::link creates shortcuts on Windows, not filesystem symlinks");
#else
        QTemporaryDir d; QTemporaryDir outside; FileStore fs(d.path());
        QVERIFY(QFile::link(outside.path(), d.filePath("link")));
        QVERIFY_EXCEPTION_THROWN(fs.write("link/f", "x"), std::runtime_error);
        QVERIFY(!QFile::exists(outside.filePath("f")));
        QVERIFY(QFile::link(outside.path(), d.filePath(".workbench")));
        QVERIFY_EXCEPTION_THROWN(fs.beginSnapshot("save"), std::runtime_error);
        QVERIFY(!QFile::exists(outside.filePath("snapshots")));
#endif
    }

    void windowsCaseAliasesShareConflictAndSnapshotState() {
#ifndef Q_OS_WIN
        QSKIP("Windows case-insensitive filesystem regression");
#else
        QTemporaryDir d; FileStore fs(d.path()); fs.write("Mixed.txt", "old");
        QFile f(d.filePath("Mixed.txt")); QVERIFY(f.open(QIODevice::WriteOnly)); f.write("HAND"); f.close();
        QVERIFY_EXCEPTION_THROWN(fs.write("MIXED.TXT", "stale"), std::runtime_error);
        QCOMPARE(fs.externalChanges(), QStringList{"Mixed.txt"});
        fs.acknowledge("Mixed.txt");
        const QString snap = fs.beginSnapshot("save");
        fs.write("MIXED.TXT", "new"); fs.write("mixed.txt", "newer");
        QFile saved(snap + "/Mixed.txt"); QVERIFY(saved.open(QIODevice::ReadOnly));
        QCOMPARE(saved.readAll(), QByteArray("HAND"));
        QVERIFY(fs.externalChanges().isEmpty());
        QVERIFY(fs.read("Absent.txt").isEmpty());
        QFile created(d.filePath("ABSENT.TXT"));
        QVERIFY(created.open(QIODevice::WriteOnly)); created.write("outside"); created.close();
        QVERIFY_EXCEPTION_THROWN(fs.write("absent.txt", "stale"), std::runtime_error);
#endif
    }

};
QTEST_MAIN(FileStoreTest)
#include "file_store_test.moc"
