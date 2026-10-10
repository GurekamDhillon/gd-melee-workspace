#include "file_store.h"
#include "launcher_core.h"
#include <QCryptographicHash>
#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QRegularExpression>
#include <QUuid>
#include <stdexcept>

namespace wb {
namespace {
[[noreturn]] void fail(const QString &message) {
    throw std::runtime_error(message.toUtf8().constData());
}
}

FileStore::FileStore(QString root) : root_(QDir(root).absolutePath()) {
    const QString canonical = QFileInfo(root_).canonicalFilePath();
    if (!canonical.isEmpty()) root_ = canonical;
}
QString FileStore::root() const { return root_; }

QString FileStore::safeRel(const QString &rel, QString *err) {
    if (err) err->clear();
    // fromNativeSeparators alone does not translate backslashes on Linux.
    QString path = rel;
    path.replace('\\', '/');
    bool unsafe = path.isEmpty() || path.startsWith('/') || path.contains(':') ||
                        path.contains(QChar(0)) || path.split('/').contains("..");
    // Windows strips trailing spaces/dots from path components. Reject those
    // ambiguous spellings on both platforms so a project stays portable.
    for (const QString &part : path.split('/'))
        if (part != "." && (part.endsWith('.') || part.endsWith(' '))) unsafe = true;
    path = QDir::cleanPath(path);
    if (unsafe || path == ".") {
        if (err) *err = "unsafe path: " + rel;
        return QString();
    }
    return path;
}
QString FileStore::hash(const QByteArray &data) {
    return QString::fromLatin1(QCryptographicHash::hash(data, QCryptographicHash::Sha256).toHex());
}
QString FileStore::key(const QString &rel) const {
    QString err;
    const QString path = safeRel(rel, &err);
    if (path.isNull()) fail(err);
    return path;
}
QString FileStore::identity(const QString &rel) {
#ifdef Q_OS_WIN
    return rel.toCaseFolded();
#else
    return rel;
#endif
}
void FileStore::remember(const QString &rel, const DiskFile &file) {
    known_[identity(rel)] = {rel, file.signature};
}
QString FileStore::absolute(const QString &rel) const {
    const QString path = key(rel);
    const QString prefix = root_.endsWith('/') ? root_ : root_ + '/';
#ifdef Q_OS_WIN
    constexpr auto sensitivity = Qt::CaseInsensitive;
#else
    constexpr auto sensitivity = Qt::CaseSensitive;
#endif
    QString current = root_;
    // Check each existing ancestor as well as the leaf: lexical checks alone
    // would let a symlink/junction write outside the project or snapshot group.
    for (const QString &part : path.split('/')) {
        current = QDir(current).filePath(part);
        const QFileInfo info(current);
        const QString canonical = info.canonicalFilePath();
        if (info.isSymLink() || (!canonical.isEmpty() &&
            canonical.compare(root_, sensitivity) != 0 && !canonical.startsWith(prefix, sensitivity)))
            fail("unsafe path: " + rel);
    }
    return current;
}
FileStore::DiskFile FileStore::inspect(const QString &rel) const {
    const QString path = absolute(rel);
    QFileInfo info(path);
    DiskFile result;
    if (!info.exists()) return result;
    if (!info.isFile()) fail("not a file: " + rel);
    const QDateTime modified = info.lastModified();
    const qint64 size = info.size();
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly)) fail(rel + ": " + file.errorString());
    result.bytes = file.readAll();
    if (file.error() != QFileDevice::NoError) fail(rel + ": " + file.errorString());
    info.refresh();
    if (!info.exists() || size != info.size() || modified != info.lastModified() || result.bytes.size() != size)
        fail("changed externally: " + rel);
    result.exists = true;
    result.signature = hash(result.bytes) + ':' + QString::number(modified.toMSecsSinceEpoch());
    return result;
}
void FileStore::requireKnown(const QString &rel, const DiskFile &file) const {
    const auto known = known_.constFind(identity(rel));
    if (known != known_.cend() && known.value().signature != file.signature)
        fail("changed externally: " + rel);
}
bool FileStore::exists(const QString &rel) const {
    return QFileInfo::exists(absolute(rel));
}
QByteArray FileStore::read(const QString &rel) {
    const QString path = key(rel);
    const DiskFile file = inspect(path);
    remember(path, file);
    return file.bytes;
}
QString FileStore::createSnapshot(const QString &label) const {
    QString safeLabel = label.left(64);
    safeLabel.replace(QRegularExpression("[^A-Za-z0-9_-]"), "_");
    if (safeLabel.isEmpty()) safeLabel = "snapshot";
    const QString name = QDateTime::currentDateTimeUtc().toString("yyyyMMdd-HHmmsszzz") + '-' +
                         QUuid::createUuid().toString(QUuid::WithoutBraces) + '-' + safeLabel;
    const QString path = absolute(".workbench/snapshots/" + name);
    if (!QDir().mkpath(path)) fail("cannot create snapshot: " + path);
    return path;
}
QString FileStore::beginSnapshot(const QString &label) {
    snapDir_ = createSnapshot(label);
    snapped_.clear();
    return snapDir_;
}
void FileStore::snapshot(const QString &rel, const DiskFile &file) {
    if (!snapDir_.isEmpty() && snapped_.contains(identity(rel))) return;
    if (file.exists) {
        const QString group = snapDir_.isEmpty() ? createSnapshot("write") : snapDir_;
        const QString destination = absolute(QDir(root_).relativeFilePath(group) + '/' + rel);
        if (QFileInfo::exists(destination)) fail("snapshot already exists: " + rel);
        launcher::writeAtomic(destination, file.bytes);
    }
    // A file created within an explicit group had no previous bytes to save.
    if (!snapDir_.isEmpty()) snapped_.insert(identity(rel));
}
void FileStore::write(const QString &rel, const QByteArray &data) {
    const QString path = key(rel);
    const DiskFile before = inspect(path);
    requireKnown(path, before);
    snapshot(path, before);
    // Snapshot creation can take time; recheck before replacing the source.
    if (inspect(path).signature != before.signature) fail("changed externally: " + path);
    launcher::writeAtomic(absolute(path), data);
    const DiskFile after = inspect(path);
    if (!after.exists || after.bytes != data) fail("changed externally: " + path);
    remember(path, after);
}
bool FileStore::remove(const QString &rel) {
    const QString path = key(rel);
    const DiskFile before = inspect(path);
    requireKnown(path, before);
    if (before.exists) {
        snapshot(path, before);
        if (inspect(path).signature != before.signature) fail("changed externally: " + path);
        if (!QFile::remove(absolute(path))) return false;
    }
    remember(path, DiskFile());
    return true;
}
QStringList FileStore::externalChanges() const {
    QStringList changes;
    for (auto it = known_.cbegin(); it != known_.cend(); ++it) {
        try {
            if (inspect(it.value().path).signature != it.value().signature) changes.append(it.value().path);
        } catch (const std::exception &) {
            // A formerly readable file becoming inaccessible is also a conflict.
            changes.append(it.value().path);
        }
    }
    changes.sort();
    return changes;
}
void FileStore::acknowledge(const QString &rel) {
    const QString path = key(rel);
    remember(path, inspect(path));
}
} // namespace wb
