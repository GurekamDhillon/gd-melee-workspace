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
    // States that need a platform, partner or item cannot be posed in the bare scene; the engine refuses them (they once
    // died on a jobj assert). Keep in step with gs_wb_unpreviewable (engine) and UNPREVIEWABLE_MOTIONS (rigmap.py).
    bool previewable() const {
        static const int kUnpreviewable[] = {12, 13, 128, 129, 131, 223, 224, 225, 226, 227, 228, 239, 240, 241, 266, 267, 268, 269, 270, 277, 280, 285, 289, 290, 291, 292, 306, 308, 309, 310, 313, 314, 315, 316, 317, 318, 319, 320, 321, 323, 324, 328, 332, 333, 334, 337, 340};
        if (motions.isEmpty()) return true;
        for (int m : motions) {
            bool bad = false;
            for (int u : kUnpreviewable) bad = bad || m == u;
            if (!bad) return true;
        }
        return false;
    }
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
    // Reasons the row's script would not run as gameplay.json declares it: an out-of-order or overlapping-slot
    // script (GenoAsm::timingProblems) and windows that differ from the script's. Empty when they agree.
    QStringList timingProblems(const QString &row) const;
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
    // A copy of one hitbox (same frames, bone, numbers, element, shield and ground/air flags) in the same row.
    QVector<FileChange> duplicateHitbox(const QString &row, int ordinal, int *newOrdinal, QString *err) const;
    QVector<FileChange> assignClip(const QString &row, const QString &clip,
                                   std::optional<int> cropStart, QString *err) const;
    QString rowByMotion(int motion) const;
    // Projectiles (articles of gameplay.json, geno.md 19.2) and the spawns that name them. Edits go through the same
    // FileChange path as hitboxes; gameplay.full.json, when it has the article, gets the same operations.
    QJsonArray articles() const;
    // ops: {op:"set",path:"velocity/#0",value}, {op:"insert",path:"hitboxes",at,value}, {op:"remove",path,at}.
    QVector<FileChange> editArticle(int index, const QJsonArray &ops, QString *err) const;
    QVector<FileChange> addArticle(const QJsonObject &article, int *index, QString *err) const;
    QVector<FileChange> removeArticle(int index, QString *err) const; // last article only, and not spawned by a script
    QJsonArray spawns(const QString &row = {}) const; // {row, ordinal, line, frame, arg, article, variant, angle}
    QVector<FileChange> editSpawn(const QString &row, int ordinal, std::optional<int> frame,
                                  std::optional<quint32> arg, QString *err) const;
    QVector<FileChange> addSpawn(const QString &row, int frame, quint32 arg, int *ordinal, QString *err) const;
    QVector<FileChange> removeSpawn(const QString &row, int ordinal, QString *err) const;

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
