#include "history.h"
#include "launcher_core.h"
#include <QDateTime>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonParseError>
#include <algorithm>
#include <limits>
#include <stdexcept>
#include <utility>

namespace wb {
namespace {
bool error(QString *err, const QString &message) {
    if (err) *err = message;
    return false;
}
[[noreturn]] void invalidHistory() {
    throw std::runtime_error("invalid workbench history");
}
QByteArray decodeBytes(const QJsonValue &value) {
    if (!value.isString()) invalidHistory();
    const QByteArray encoded = value.toString().toLatin1();
    const QByteArray decoded = QByteArray::fromBase64(encoded);
    // Our writer always emits canonical base64. The default Qt decoder alone
    // would silently ignore corrupt characters and restore different bytes.
    if (QString::fromLatin1(decoded.toBase64()) != value.toString()) invalidHistory();
    return decoded;
}
}

void History::clearRedo() {
    entries_.erase(std::remove_if(entries_.begin(), entries_.end(), [](const HistoryEntry &entry) {
        return entry.state == "undone";
    }), entries_.end());
}
int History::append(HistoryEntry entry, const QString &state) {
    if (nextId_ == std::numeric_limits<int>::max())
        throw std::runtime_error("history id limit reached");
    entry.id = ++nextId_;
    entry.state = state;
    entry.time = QDateTime::currentSecsSinceEpoch();
    if (state == "applied") clearRedo();
    entries_.append(std::move(entry));
    return nextId_;
}
int History::record(HistoryEntry entry) { return append(std::move(entry), "applied"); }
int History::propose(HistoryEntry entry) { return append(std::move(entry), "proposed"); }

bool History::apply(const HistoryEntry &entry, FileStore &fs, bool forward,
                    const QString &operation, QString *err) {
    if (err) err->clear();
    struct Pending {
        QString path;
        FileStore::DiskFile disk;
        QByteArray target;
    };
    QVector<Pending> pending;
    QSet<QString> paths;
    try {
        // No FileStore::read here: a failed preflight must not acknowledge a
        // hand edit, nor may it modify an earlier file in this same command.
        for (const FileChange &change : entry.changes) {
            const QString path = fs.key(change.path);
            const QString identity = FileStore::identity(path);
            if (paths.contains(identity)) return error(err, "duplicate path: " + path);
            paths.insert(identity);
            const auto disk = fs.inspect(path);
            const QByteArray &expected = forward ? change.before : change.after;
            const auto known = fs.known_.constFind(identity);
            if (disk.bytes != expected || (known != fs.known_.cend() && known.value().signature != disk.signature)) {
                const QString message = operation == "accept"
                    ? "stale proposal: " + path + " changed since it was proposed"
                    : "changed externally: " + path;
                return error(err, message);
            }
            pending.append({path, disk, forward ? change.after : change.before});
        }
        fs.beginSnapshot(operation);
        // Prepare every snapshot before overwriting any source file. A failure
        // to preserve any of the originals therefore leaves all sources alone.
        for (const auto &change : pending) fs.snapshot(change.path, change.disk);
        for (const auto &change : pending) {
            if (fs.inspect(change.path).signature != change.disk.signature) {
                return error(err, operation == "accept"
                    ? "stale proposal: " + change.path + " changed since it was proposed"
                    : "changed externally: " + change.path);
            }
        }
        for (const auto &change : pending) fs.remember(change.path, change.disk);
        for (const auto &change : pending) {
            // Empty source bytes represent absence (the Task 3 v1 contract).
            if (change.target.isEmpty()) {
                if (!fs.remove(change.path)) return error(err, "cannot remove: " + change.path);
            } else {
                fs.write(change.path, change.target);
            }
        }
        return true;
    } catch (const std::exception &exception) {
        return error(err, QString::fromUtf8(exception.what()));
    }
}
bool History::undo(FileStore &fs, QString *err) {
    for (qsizetype i = entries_.size(); i > 0; --i) {
        auto &entry = entries_[i - 1];
        if (entry.state != "applied") continue;
        if (!apply(entry, fs, false, "undo", err)) return false;
        entry.state = "undone";
        return true;
    }
    return error(err, "nothing to undo");
}
bool History::redo(FileStore &fs, QString *err) {
    for (auto &entry : entries_) {
        if (entry.state != "undone") continue;
        if (!apply(entry, fs, true, "redo", err)) return false;
        entry.state = "applied";
        return true;
    }
    return error(err, "nothing to redo");
}
bool History::accept(int id, FileStore &fs, QString *err) {
    for (qsizetype i = 0; i < entries_.size(); ++i) {
        if (entries_[i].id != id) continue;
        if (entries_[i].state != "proposed") return error(err, "not a proposal");
        if (!apply(entries_[i], fs, true, "accept", err)) return false;
        HistoryEntry accepted = entries_.takeAt(i);
        accepted.state = "applied";
        clearRedo();
        // The proposal keeps its id, but undo must follow application order,
        // including when it was proposed before other, already applied work.
        entries_.append(std::move(accepted));
        return true;
    }
    return error(err, "no such entry");
}
bool History::reject(int id, QString *err) {
    for (auto &entry : entries_) {
        if (entry.id != id) continue;
        if (entry.state != "proposed") return error(err, "not a proposal");
        entry.state = "rejected";
        if (err) err->clear();
        return true;
    }
    return error(err, "no such entry");
}
const QVector<HistoryEntry> &History::entries() const { return entries_; }

QJsonArray History::toJson() const {
    QJsonArray array;
    for (const auto &entry : entries_) {
        QJsonArray changes;
        for (const auto &change : entry.changes) {
            changes.append(QJsonObject{{"path", change.path},
                {"before", QString::fromLatin1(change.before.toBase64())},
                {"after", QString::fromLatin1(change.after.toBase64())}});
        }
        QJsonObject object{{"id", entry.id}, {"author", entry.author}, {"command", entry.command},
            {"summary", entry.summary}, {"state", entry.state}, {"args", entry.args},
            {"time", entry.time}, {"changes", changes}};
        // Accepting an old proposal can discard the largest id on a redo
        // branch. Retain that high-water mark so future sessions never reuse it.
        if (array.isEmpty()) object.insert("last_id", nextId_);
        array.append(object);
    }
    return array;
}
History History::fromJson(const QJsonArray &array) {
    History history;
    QSet<int> ids;
    for (const QJsonValue &value : array) {
        if (!value.isObject()) invalidHistory();
        const QJsonObject object = value.toObject();
        HistoryEntry entry;
        entry.id = object["id"].toInt();
        if (entry.id <= 0 || ids.contains(entry.id)) invalidHistory();
        ids.insert(entry.id);
        for (const char *field : {"author", "command", "summary", "state"})
            if (!object[field].isString()) invalidHistory();
        entry.author = object["author"].toString();
        entry.command = object["command"].toString();
        entry.summary = object["summary"].toString();
        entry.state = object["state"].toString();
        if (entry.state != "applied" && entry.state != "undone" &&
            entry.state != "proposed" && entry.state != "rejected") invalidHistory();
        if (!object["args"].isObject() || !object["changes"].isArray() ||
            !object["time"].isDouble()) invalidHistory();
        entry.args = object["args"].toObject();
        entry.time = object["time"].toInteger(-1);
        if (entry.time < 0) invalidHistory();
        for (const QJsonValue &item : object["changes"].toArray()) {
            if (!item.isObject()) invalidHistory();
            const auto change = item.toObject();
            const QString path = change["path"].toString();
            if (FileStore::safeRel(path, nullptr).isNull()) invalidHistory();
            entry.changes.append({path, decodeBytes(change["before"]), decodeBytes(change["after"])});
        }
        if (object.contains("last_id")) {
            const int lastId = object["last_id"].toInt();
            if (lastId < entry.id) invalidHistory();
            history.nextId_ = std::max(history.nextId_, lastId);
        }
        history.nextId_ = std::max(history.nextId_, entry.id);
        history.entries_.append(std::move(entry));
    }
    return history;
}
bool History::save(const QString &path) const {
    try {
        launcher::writeAtomic(path, QJsonDocument(toJson()).toJson(QJsonDocument::Compact));
        return true;
    } catch (const std::exception &) {
        return false;
    }
}
History History::load(const QString &path) {
    QFile file(path);
    if (!QFileInfo::exists(path)) return History();
    if (!file.open(QIODevice::ReadOnly))
        throw std::runtime_error((path + ": " + file.errorString()).toUtf8().constData());
    const QByteArray bytes = file.readAll();
    if (file.error() != QFileDevice::NoError)
        throw std::runtime_error((path + ": " + file.errorString()).toUtf8().constData());
    QJsonParseError parseError;
    const auto document = QJsonDocument::fromJson(bytes, &parseError);
    if (parseError.error != QJsonParseError::NoError || !document.isArray()) invalidHistory();
    return fromJson(document.array());
}
} // namespace wb
