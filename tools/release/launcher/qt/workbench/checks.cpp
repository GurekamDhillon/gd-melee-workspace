#include "checks.h"
#include <QHash>
#include <QSet>

namespace wb {
namespace {
double score(const BoneSample &bone) {
    return bone.displacement * (1.0 + bone.speed);
}

const BoneSample *mostActiveLimb(const QVector<BoneSample> &bones) {
    const BoneSample *best = nullptr;
    for (const auto &bone : bones) {
        if (isLimbRole(bone.role) && (!best || score(bone) > score(*best))) best = &bone;
    }
    return best;
}

const BoneSample *sampleForRole(const QVector<BoneSample> &bones, const QString &role) {
    const BoneSample *best = nullptr;
    for (const auto &bone : bones) {
        if (bone.role == role && (!best || score(bone) > score(*best))) best = &bone;
    }
    return best;
}

// Core diagnostics use the permitted English/English pairs. The launcher's
// language selector lives in launcher_ui, which workbench_core cannot depend on.
QString t(const char *english, const char *) {
    return QString::fromUtf8(english);
}
} // namespace

QString suggestBone(const QVector<BoneSample> &bones) {
    const auto *best = mostActiveLimb(bones);
    return best ? best->role : QString();
}

QVector<Problem> runChecks(const QVector<RowAnalysis> &rows) {
    QVector<Problem> problems;
    QHash<QString, QSet<QString>> clipRows;
    for (const auto &row : rows) {
        for (const auto &hitbox : row.hitboxes) {
            const auto samples = row.bonesByHitbox.constFind(hitbox.ordinal);
            const auto &bones = samples == row.bonesByHitbox.constEnd() ? row.bones : samples.value();
            const auto *suggested = mostActiveLimb(bones);
            if (!suggested || hitbox.role == suggested->role) continue;
            const auto *current = sampleForRole(bones, hitbox.role);
            // An absent sample is unknown, not a measured stationary bone.
            if (!current) continue;
            const double suggestedScore = score(*suggested);
            const double currentScore = score(*current);
            if (suggestedScore > currentScore && suggestedScore >= 1.5 * currentScore) {
                problems.append({"wrong_limb", row.row,
                    t("hitbox #%1 is on %2 but %3 moves most at frame %4",
                      "hitbox #%1 is on %2 but %3 moves most at frame %4")
                        .arg(hitbox.ordinal).arg(hitbox.role, suggested->role).arg(hitbox.startFrame),
                    hitbox.ordinal});
            }
        }
        if (!row.aerial && row.rowLowestY < row.floorY - 0.5) {
            problems.append({"below_floor", row.row,
                t("row %1 falls below the floor by more than 0.5 units",
                  "row %1 falls below the floor by more than 0.5 units").arg(row.row)});
        }
        if (!row.clip.isEmpty()) {
            auto &seenRows = clipRows[row.clip];
            if (!seenRows.isEmpty() && !seenRows.contains(row.row)) {
                problems.append({"duplicate_clip", row.row,
                    t("row %1 shares clip %2 with another row",
                      "row %1 shares clip %2 with another row").arg(row.row, row.clip)});
            }
            seenRows.insert(row.row);
        }
        if (row.aerial && row.groundedClip) {
            problems.append({"grounded_clip_on_aerial", row.row,
                t("aerial row %1 uses a grounded clip",
                  "aerial row %1 uses a grounded clip").arg(row.row)});
        }
        if (row.hasSwingMotion && row.hitboxes.isEmpty()) {
            problems.append({"swing_without_hitbox", row.row,
                t("row %1 has swing motion but no hitbox",
                  "row %1 has swing motion but no hitbox").arg(row.row)});
        }
    }
    return problems;
}
} // namespace wb
