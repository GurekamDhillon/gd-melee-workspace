#include "geno_data.h"
#include "json_patch.h"
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QSet>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace wb {
namespace {
[[noreturn]] void fail(const QString &message) {
    throw std::runtime_error(message.toUtf8().constData());
}
bool hasBom(const QByteArray &bytes) { return bytes.startsWith("\xEF\xBB\xBF"); }
QString sourceText(const QByteArray &bytes, const QString &path) {
    const QByteArray body = hasBom(bytes) ? bytes.mid(3) : bytes;
    const QString text = QString::fromUtf8(body);
    if (text.toUtf8() != body) fail(path + ": invalid UTF-8");
    return text;
}
QByteArray sourceBytes(const QString &text, const QByteArray &original) {
    return (hasBom(original) ? QByteArray("\xEF\xBB\xBF") : QByteArray()) + text.toUtf8();
}
QJsonObject parseObject(const QByteArray &bytes, const QString &path, QString *raw = nullptr) {
    const QString text = sourceText(bytes, path);
    QJsonParseError error;
    const auto document = QJsonDocument::fromJson(text.toUtf8(), &error);
    if (error.error != QJsonParseError::NoError)
        fail(QString("%1: %2 at offset %3").arg(path, error.errorString())
             .arg(error.offset + (hasBom(bytes) ? 3 : 0)));
    if (!document.isObject()) fail(path + ": expected an object");
    if (raw) *raw = text;
    return document.object();
}
int integer(const QJsonValue &value, const QString &where) {
    const double number = value.toDouble();
    if (!value.isDouble() || !std::isfinite(number) || std::trunc(number) != number ||
        number < std::numeric_limits<int>::min() || number > std::numeric_limits<int>::max())
        fail(where + ": expected integer");
    return int(number);
}
int intField(const QJsonObject &object, const QString &key, const QString &where) {
    return object.contains(key) ? integer(object.value(key), where + '/' + key) : 0;
}
QString stringField(const QJsonObject &object, const QString &key, const QString &where) {
    const auto value = object.value(key);
    if (!value.isUndefined() && !value.isString()) fail(where + '/' + key + ": expected string");
    return value.toString();
}
QJsonObject objectField(const QJsonObject &object, const QString &key, const QString &where) {
    const auto value = object.value(key);
    if (!value.isUndefined() && !value.isObject()) fail(where + '/' + key + ": expected object");
    return value.toObject();
}
QString workspaceRoot(const QString &projectRoot) {
    QDir dir(projectRoot);
    do {
        if (QFileInfo::exists(dir.filePath(".git"))) return dir.absolutePath();
    } while (dir.cdUp());
    // Standalone synthetic/exported projects have no Git metadata.
    return projectRoot;
}
QByteArray readPlan(FileStore &fs, const ProjectConfig &project, QString *name, bool *exists) {
    *exists = false;
    if (project.planAbs.isEmpty()) {
        *name = project.plan;
        if (name->isEmpty()) return {};
        const auto bytes = fs.read(*name);
        *exists = fs.exists(*name);
        return bytes;
    }
    QString path = project.planAbs;
    path.replace('\\', '/');
    if (QDir::isRelativePath(path)) path = QDir(workspaceRoot(fs.root())).filePath(path);
    *name = QDir::cleanPath(path);
    QFile file(*name);
    if (!file.exists()) return {};
    *exists = true;
    if (!file.open(QIODevice::ReadOnly)) fail(*name + ": " + file.errorString());
    const auto bytes = file.readAll();
    if (file.error() != QFileDevice::NoError) fail(*name + ": " + file.errorString());
    return bytes;
}
QString replaceValue(const QString &text, const JsonPath &path, const QJsonValue &value,
                     const QString &file, bool insertMissing = false) {
    QString error;
    QString changed;
    int start = 0, end = 0;
    if (insertMissing && !jsonFind(text, path, &start, &end)) {
        auto parent = path;
        const QString key = parent.takeLast();
        changed = jsonInsertKey(text, parent, key, jsonScalar(value), &error);
    } else {
        changed = jsonReplace(text, path, jsonScalar(value), &error);
    }
    if (changed.isNull()) fail(file + ": " + error);
    return changed;
}
} // namespace

GenoData::GenoData(FileStore &fs) : fs_(fs) {}
const ProjectConfig &GenoData::project() const { return project_; }
QVector<RowInfo> GenoData::rows() const { return rows_; }
QVector<ClipInfo> GenoData::clips() const { return clips_; }
QVector<Joint> GenoData::joints() const { return joints_; }
bool GenoData::hasPlan() const { return hasPlan_; }
QString GenoData::planPath() const { return planPath_; }

QString GenoData::reload() {
    project_ = {};
    hasPlan_ = false;
    planPath_.clear();
    rows_.clear(); clips_.clear(); joints_.clear(); roles_ = {};
    fidelityRows_ = {}; scripts_.clear();
    gameplayBytes_.clear(); fidelityBytes_.clear();
    gameplayText_.clear(); fidelityText_.clear();
    try {
        QString error;
        const ProjectConfig project = ProjectConfig::load(fs_, &error);
        if (!error.isEmpty()) return error;
        const auto gameplayBytes = fs_.read(project.gameplay);
        if (!fs_.exists(project.gameplay)) fail(project.gameplay + ": file not found");
        QString gameplayText;
        const auto gameplay = parseObject(gameplayBytes, project.gameplay, &gameplayText);
        if (!gameplay.value("moves").isArray()) fail(project.gameplay + ": moves must be an array");
        const auto moves = gameplay.value("moves").toArray();
        QVector<RowInfo> rows;
        QSet<QString> names;
        QHash<QString, QByteArray> scripts;
        for (int i = 0; i < moves.size(); ++i) {
            const QString where = project.gameplay + QString("/moves/#%1").arg(i);
            if (!moves[i].isObject()) fail(where + ": expected object");
            const auto move = moves[i].toObject();
            RowInfo row;
            row.moveIndex = i;
            row.name = stringField(move, "name", where);
            if (row.name.isEmpty()) fail(where + ": name is required");
            if (names.contains(row.name)) fail(where + ": duplicate row name: " + row.name);
            names.insert(row.name);
            const auto motions = move.value("motions");
            if (!motions.isUndefined() && !motions.isArray()) fail(where + "/motions: expected array");
            for (const auto &motion : motions.toArray()) row.motions.append(integer(motion, where + "/motions"));
            row.tag = stringField(move, "tag", where);
            row.aerial = row.tag == "aerial";
            row.iasa = intField(move, "iasa", where);
            row.script = stringField(move, "script", where);
            if (!row.script.isEmpty()) {
                row.script = FileStore::safeRel(row.script, &error);
                if (!error.isEmpty()) fail(where + ": " + error);
                if (!scripts.contains(row.script)) {
                    const auto bytes = fs_.read(row.script);
                    sourceText(bytes, row.script); // Reject lossy decoding before an edit is offered.
                    scripts.insert(row.script, bytes);
                }
            }
            const auto pick = objectField(move, "pick", where);
            row.clip = stringField(pick, "clip", where + "/pick");
            row.cropStart = intField(pick, "crop_start", where + "/pick");
            rows.append(row);
        }
        QString planName;
        bool planExists = false;
        const auto planBytes = readPlan(fs_, project, &planName, &planExists);
        const auto plan = planExists ? parseObject(planBytes, planName) : QJsonObject();
        QVector<Joint> joints;
        const auto planJoints = plan.value("joints");
        if (!planJoints.isUndefined() && !planJoints.isArray()) fail(planName + "/joints: expected array");
        for (const auto &value : planJoints.toArray()) {
            if (!value.isObject()) fail(planName + "/joints: expected object");
            const auto joint = value.toObject();
            const auto parent = joint.value("parent");
            joints.append({integer(joint.value("index"), planName + "/joints/index"),
                           stringField(joint, "name", planName + "/joints"),
                           parent.isNull() || parent.isUndefined() ? -1 : integer(parent, planName + "/joints/parent")});
        }
        const auto roles = objectField(plan, "roles", planName);
        QVector<ClipInfo> clips;
        const auto bank = objectField(plan, "bank", planName);
        const auto bankClips = objectField(bank, "clips", planName + "/bank");
        for (auto it = bankClips.constBegin(); it != bankClips.constEnd(); ++it) {
            if (!it.value().isObject()) fail(planName + "/bank/clips/" + it.key() + ": expected object");
            clips.append({it.key(), intField(it.value().toObject(), "frames", planName + "/bank/clips/" + it.key())});
        }
        // Rows without a gameplay pick (Goku) take their clip from the plan: motion_rows, then row_clips[motion].
        QHash<int, QString> planClipByMotion;
        const auto motionRows = plan.value("motion_rows");
        if (!motionRows.isUndefined() && !motionRows.isArray()) fail(planName + "/motion_rows: expected array");
        for (const auto &value : motionRows.toArray()) {
            if (!value.isObject()) continue;
            const auto entry = value.toObject();
            if (entry.value("clip").isString() && entry.value("motion").isDouble())
                planClipByMotion.insert(entry.value("motion").toInt(), entry.value("clip").toString());
        }
        const auto rowClips = plan.value("row_clips").toArray();
        for (auto &row : rows) {
            for (int motion : row.motions) {
                QString name = planClipByMotion.value(motion);
                if (name.isEmpty() && motion >= 0 && motion < rowClips.size() && rowClips[motion].isString())
                    name = rowClips[motion].toString();
                if (!name.isEmpty()) { row.planClip = name; break; }
            }
        }
        QByteArray fidelityBytes;
        QString fidelityText;
        QJsonArray fidelityRows;
        if (!project.fidelity.isEmpty()) {
            fidelityBytes = fs_.read(project.fidelity);
            if (fs_.exists(project.fidelity)) {
                const auto fidelity = parseObject(fidelityBytes, project.fidelity, &fidelityText);
                if (!fidelity.value("rows").isArray()) fail(project.fidelity + ": rows must be an array");
                fidelityRows = fidelity.value("rows").toArray();
                for (const auto &value : fidelityRows) {
                    if (!value.isObject()) fail(project.fidelity + "/rows: expected object");
                    integer(value.toObject().value("motion"), project.fidelity + "/rows/motion");
                }
            }
        }
        // Publish a complete model only; any failure above leaves all views empty.
        project_ = project;
        rows_ = rows; scripts_ = scripts;
        clips_ = clips; joints_ = joints; roles_ = roles;
        hasPlan_ = planExists;
        planPath_ = planName;
        gameplayBytes_ = gameplayBytes; gameplayText_ = gameplayText;
        fidelityBytes_ = fidelityBytes; fidelityText_ = fidelityText; fidelityRows_ = fidelityRows;
        return {};
    } catch (const std::exception &e) {
        return QString::fromUtf8(e.what());
    }
}

const RowInfo *GenoData::findRow(const QString &name) const {
    for (const auto &row : rows_) if (row.name == name) return &row;
    return nullptr;
}
QString GenoData::rowByMotion(int motion) const {
    for (const auto &row : rows_) if (row.motions.contains(motion)) return row.name;
    return {};
}
QVector<HitboxRef> GenoData::hitboxes(const QString &name) const {
    const auto *row = findRow(name);
    if (!row || row->script.isEmpty()) return {};
    return GenoAsm::parse(sourceText(scripts_.value(row->script), row->script)).hitboxes();
}
const QVector<RoleInfo> &GenoData::roleVocabulary() {
    // The assembler's role names (ports/*/tools/build.py ROLE) and the plan key each resolves through.
    static const QVector<RoleInfo> roles = {
        {"HEAD", "head", "body"}, {"NECK", "neck", "body"}, {"CHEST", "chest", "body"},
        {"SPINE", "spine", "body"}, {"HIPS", "hips", "body"},
        {"UPARM_R", "upper_arm.R", "arms"}, {"UPARM_L", "upper_arm.L", "arms"},
        {"ARM_R", "lower_arm.R", "arms"}, {"ARM_L", "lower_arm.L", "arms"},
        {"HAND_R", "hand.R", "arms"}, {"HAND_L", "hand.L", "arms"},
        {"UPLEG_R", "upper_leg.R", "legs"}, {"UPLEG_L", "upper_leg.L", "legs"},
        {"LEG_R", "lower_leg.R", "legs"}, {"LEG_L", "lower_leg.L", "legs"},
        {"FOOT_R", "foot.R", "legs"}, {"FOOT_L", "foot.L", "legs"},
        {"TOE_R", "toe.R", "legs"}, {"TOE_L", "toe.L", "legs"},
        {"FLOOR", "translation", "anchors"},
    };
    return roles;
}
QVector<RoleInfo> GenoData::availableRoles() const {
    if (!hasPlan_) return roleVocabulary();
    QVector<RoleInfo> out;
    for (const auto &role : roleVocabulary()) if (jointForRole(role.name) >= 0) out.append(role);
    return out;
}
int GenoData::jointForRole(const QString &role) const {
    QString name = role;
    if (name.startsWith('@') && name.endsWith('@') && name.size() > 2) name = name.mid(1, name.size() - 2);
    QString key;
    for (const auto &info : roleVocabulary()) if (info.name == name) { key = info.key; break; }
    if (key.isEmpty()) return -1;
    const auto indices = roles_.value(key).toArray();
    if (indices.isEmpty()) return -1;
    const int index = indices.first().toInt(-1);
    if (index < 0) return -1;
    for (const auto &joint : joints_) if (joint.index == index) return index;
    return -1;
}
QString GenoData::externalError(const QStringList &paths) const {
    const auto changed = fs_.externalChanges();
#ifdef Q_OS_WIN
    constexpr auto sensitivity = Qt::CaseInsensitive;
#else
    constexpr auto sensitivity = Qt::CaseSensitive;
#endif
    for (const auto &path : paths)
        if (!path.isEmpty() && changed.contains(path, sensitivity)) return "changed externally: " + path;
    return {};
}
QVector<FileChange> GenoData::editHitbox(const QString &name, int ordinal, const HitboxEdit &edit, QString *err) const {
    if (err) err->clear();
    try {
        const auto *row = findRow(name);
        if (!row) fail("unknown row: " + name);
        if (row->script.isEmpty()) fail("row has no script: " + name);
        const QString conflict = externalError({"workbench.json", project_.gameplay, row->script});
        if (!conflict.isEmpty()) fail(conflict);
        const auto bytes = scripts_.value(row->script);
        QString error;
        const auto changed = GenoAsm::parse(sourceText(bytes, row->script)).apply(ordinal, edit, &error);
        if (!error.isEmpty() || changed.isNull()) fail(row->script + ": " + error);
        return {{row->script, bytes, sourceBytes(changed, bytes)}};
    } catch (const std::exception &e) {
        if (err) *err = QString::fromUtf8(e.what());
        return {};
    }
}
QVector<FileChange> GenoData::addHitbox(const QString &name, const HitboxAdd &add, int *ordinal, QString *err) const {
    if (err) err->clear();
    try {
        const auto *row = findRow(name);
        if (!row) fail("unknown row: " + name);
        if (row->script.isEmpty()) fail("row has no script: " + name);
        const QString conflict = externalError({"workbench.json", project_.gameplay, row->script});
        if (!conflict.isEmpty()) fail(conflict);
        const auto bytes = scripts_.value(row->script);
        QString error;
        const auto changed = GenoAsm::parse(sourceText(bytes, row->script)).addHitbox(add, &error, ordinal);
        if (!error.isEmpty() || changed.isNull()) fail(row->script + ": " + error);
        return {{row->script, bytes, sourceBytes(changed, bytes)}};
    } catch (const std::exception &e) {
        if (err) *err = QString::fromUtf8(e.what());
        return {};
    }
}
QVector<FileChange> GenoData::removeHitbox(const QString &name, int ordinal, QString *err) const {
    if (err) err->clear();
    try {
        const auto *row = findRow(name);
        if (!row) fail("unknown row: " + name);
        if (row->script.isEmpty()) fail("row has no script: " + name);
        const QString conflict = externalError({"workbench.json", project_.gameplay, row->script});
        if (!conflict.isEmpty()) fail(conflict);
        const auto bytes = scripts_.value(row->script);
        QString error;
        const auto changed = GenoAsm::parse(sourceText(bytes, row->script)).removeHitbox(ordinal, &error);
        if (!error.isEmpty() || changed.isNull()) fail(row->script + ": " + error);
        return {{row->script, bytes, sourceBytes(changed, bytes)}};
    } catch (const std::exception &e) {
        if (err) *err = QString::fromUtf8(e.what());
        return {};
    }
}
QVector<FileChange> GenoData::assignClip(const QString &name, const QString &clip,
                                        std::optional<int> cropStart, QString *err) const {
    if (err) err->clear();
    try {
        const auto *row = findRow(name);
        if (!row) fail("unknown row: " + name);
        bool knownClip = false;
        for (const auto &candidate : clips_) if (candidate.name == clip) { knownClip = true; break; }
        if (!knownClip) fail("unknown clip: " + clip);
        const QString conflict = externalError({"workbench.json", project_.gameplay, project_.fidelity});
        if (!conflict.isEmpty()) fail(conflict);
        const QString move = '#' + QString::number(row->moveIndex);
        QString gameplay = replaceValue(gameplayText_, {"moves", move, "pick", "clip"}, clip, project_.gameplay);
        if (cropStart)
            gameplay = replaceValue(gameplay, {"moves", move, "pick", "crop_start"}, *cropStart, project_.gameplay, true);
        QString fidelity = fidelityText_;
        bool changedFidelity = false;
        for (int i = 0; i < fidelityRows_.size(); ++i) {
            const auto entry = fidelityRows_[i].toObject();
            if (!row->motions.contains(entry.value("motion").toInt())) continue;
            const QString item = '#' + QString::number(i);
            fidelity = replaceValue(fidelity, {"rows", item, "clip"}, clip, project_.fidelity);
            QString deviation = stringField(entry, "deviation", project_.fidelity + "/rows/" + item);
            if (!deviation.isEmpty()) deviation += "; ";
            deviation += "workbench: clip reassigned";
            fidelity = replaceValue(fidelity, {"rows", item, "deviation"}, deviation, project_.fidelity, true);
            changedFidelity = true;
        }
        QVector<FileChange> changes{{project_.gameplay, gameplayBytes_, sourceBytes(gameplay, gameplayBytes_)}};
        if (changedFidelity) changes.append({project_.fidelity, fidelityBytes_, sourceBytes(fidelity, fidelityBytes_)});
        return changes;
    } catch (const std::exception &e) {
        if (err) *err = QString::fromUtf8(e.what());
        return {};
    }
}
} // namespace wb
