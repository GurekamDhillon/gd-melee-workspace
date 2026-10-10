#pragma once
#include <QByteArray>
#include <QHash>
#include <QSet>
#include <QString>
#include <QStringList>

namespace wb {
struct FileChange {
    QString path; // Project-relative source path.
    QByteArray before;
    QByteArray after;
};

class FileStore {
public:
    explicit FileStore(QString root);
    QString root() const;
    bool exists(const QString &rel) const;
    // Reading (including a missing path) establishes the known disk version.
    QByteArray read(const QString &rel);
    // I/O failures, unsafe paths and external changes throw std::runtime_error.
    // Writes without an explicit group take an individual snapshot if needed.
    void write(const QString &rel, const QByteArray &data);
    bool remove(const QString &rel);
    QString beginSnapshot(const QString &label);
    QStringList externalChanges() const;
    void acknowledge(const QString &rel);
    static QString safeRel(const QString &rel, QString *err);
    static QString hash(const QByteArray &data);

private:
    friend class History;
    struct DiskFile {
        bool exists = false;
        QByteArray bytes;
        QString signature = QStringLiteral("<missing>");
    };
    struct KnownFile { QString path, signature; };
    QString key(const QString &rel) const;
    static QString identity(const QString &rel);
    void remember(const QString &rel, const DiskFile &file);
    QString absolute(const QString &rel) const;
    DiskFile inspect(const QString &rel) const;
    void requireKnown(const QString &rel, const DiskFile &file) const;
    QString createSnapshot(const QString &label) const;
    void snapshot(const QString &rel, const DiskFile &file);

    QString root_;
    QHash<QString, KnownFile> known_; // Filesystem identity -> spelling + hash/mtime.
    QString snapDir_;
    QSet<QString> snapped_;
};
} // namespace wb
