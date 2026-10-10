#pragma once
#include "file_store.h"
#include <QJsonArray>
#include <QJsonObject>
#include <QVector>

namespace wb {
struct HistoryEntry {
    int id = 0;
    QString author, command, summary, state; // applied|undone|proposed|rejected
    QJsonObject args;
    QVector<FileChange> changes;
    qint64 time = 0;
};

class History {
public:
    int record(HistoryEntry entry);
    int propose(HistoryEntry entry);
    bool undo(FileStore &fs, QString *err);
    bool redo(FileStore &fs, QString *err);
    bool accept(int id, FileStore &fs, QString *err);
    bool reject(int id, QString *err);
    const QVector<HistoryEntry> &entries() const;
    QJsonArray toJson() const;
    static History fromJson(const QJsonArray &array);
    bool save(const QString &path) const;
    // A missing log starts empty; a corrupt/unreadable existing log throws.
    static History load(const QString &path);

private:
    int append(HistoryEntry entry, const QString &state);
    void clearRedo();
    bool apply(const HistoryEntry &entry, FileStore &fs, bool forward,
               const QString &operation, QString *err);
    QVector<HistoryEntry> entries_;
    int nextId_ = 0;
};
} // namespace wb
