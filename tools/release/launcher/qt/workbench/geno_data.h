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
    QString planClip; // the plan's motion_rows/row_clips name for the row's first motion (clip stays the gameplay pick)
    QString effectiveClip() const { return clip.isEmpty() && !clipSpecified ? planClip : clip; }
    int cropStart = 0;
    int iasa = 0;
    bool aerial = false;
    bool clipSpecified = false; // An explicit empty pick means this state has no fixed clip.
};
struct ClipInfo { QString name; int frames = 0; };
struct RoleInfo { QString name, key, group; }; // role as written in joint=@NAME@, its plan key, its panel group
struct Joint { int index; QString name; int parent; };

class GenoData {
public:
    explicit GenoData(FileStore &fs);
    QString reload();
    const ProjectConfig &project() const;
    QVector<RowInfo> rows() const;
    QVector<HitboxRef> hitboxes(const QString &row) const;
    QJsonArray timelineEvents(const QString &row) const; // source-authored sound/effect markers, cached bytes only
    QVector<ClipInfo> clips() const;
    QVector<Joint> joints() const;
    bool hasPlan() const;
    QString planPath() const; // Read-only plan as actually resolved by reload().
    int jointForRole(const QString &role) const;
    static const QVector<RoleInfo> &roleVocabulary(); // every name the assembler accepts, grouped and ordered
    QVector<RoleInfo> availableRoles() const;         // those this project's plan resolves (all when it has no plan)
    QVector<FileChange> editHitbox(const QString &row, int ordinal, const HitboxEdit &e, QString *err) const;
    QVector<FileChange> addHitbox(const QString &row, const HitboxAdd &add, int *ordinal, QString *err) const;
    QVector<FileChange> removeHitbox(const QString &row, int ordinal, QString *err) const;
    QVector<FileChange> assignClip(const QString &row, const QString &clip,
                                   std::optional<int> cropStart, QString *err) const;
    QString rowByMotion(int motion) const;

private:
    const RowInfo *findRow(const QString &name) const;
    QString externalError(const QStringList &paths) const;
    void syncGameplay(QVector<FileChange> &out, int moveIndex, const QVector<HitboxRef> &before,
                      const QVector<HitboxRef> &after, int added, int removed) const;
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
