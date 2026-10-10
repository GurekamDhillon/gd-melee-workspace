#pragma once
#include "geno_asm.h"
#include "project.h"
#include <QHash>
#include <QJsonArray>
#include <QJsonObject>
#include <QVector>
#include <optional>

namespace wb {
struct RowInfo {
    QString name;
    int moveIndex = 0;
    QVector<int> motions;
    QString script, tag, clip;
    int cropStart = 0;
    int iasa = 0;
    bool aerial = false;
};
struct ClipInfo { QString name; int frames = 0; };
struct Joint { int index; QString name; int parent; };

class GenoData {
public:
    explicit GenoData(FileStore &fs);
    QString reload();
    const ProjectConfig &project() const;
    QVector<RowInfo> rows() const;
    QVector<HitboxRef> hitboxes(const QString &row) const;
    QVector<ClipInfo> clips() const;
    QVector<Joint> joints() const;
    bool hasPlan() const;
    QString planPath() const; // Read-only plan as actually resolved by reload().
    int jointForRole(const QString &role) const;
    QVector<FileChange> editHitbox(const QString &row, int ordinal, const HitboxEdit &e, QString *err) const;
    QVector<FileChange> assignClip(const QString &row, const QString &clip,
                                   std::optional<int> cropStart, QString *err) const;
    QString rowByMotion(int motion) const;

private:
    const RowInfo *findRow(const QString &name) const;
    QString externalError(const QStringList &paths) const;
    FileStore &fs_;
    ProjectConfig project_;
    QVector<RowInfo> rows_;
    QVector<ClipInfo> clips_;
    QVector<Joint> joints_;
    QJsonObject roles_;
    bool hasPlan_ = false;
    QString planPath_;
    QJsonArray fidelityRows_;
    QByteArray gameplayBytes_, fidelityBytes_;
    QString gameplayText_, fidelityText_;
    // Only reload reads FileStore: inspecting/editing cannot acknowledge a hand edit.
    QHash<QString, QByteArray> scripts_;
};
} // namespace wb
