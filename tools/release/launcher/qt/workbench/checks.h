#pragma once
#include <QString>
#include <QStringList>
#include <QHash>
#include <QVector>

namespace wb {
struct BoneSample {
    QString role;
    double displacement = 0; // Distance from the torso at the hitbox's active frame.
    double speed = 0;
};
struct HitboxSample {
    int ordinal = 0;
    QString role;
    int startFrame = 0;
    double lowestY = 0;
};
struct RowAnalysis {
    QString row, tag, clip;
    bool aerial = false, groundedClip = false, hasSwingMotion = false;
    double floorY = 0, rowLowestY = 0;
    QVector<HitboxSample> hitboxes;
    QStringList timingIssues; // The script would not run as gameplay.json declares (a blocker).
    QVector<BoneSample> bones;
    // Engine sweeps keep limb scores at each hitbox's own active frame.
    // Pure/static callers can continue to supply the row-wide bones vector.
    QHash<int, QVector<BoneSample>> bonesByHitbox;
};
struct Problem {
    QString kind, row, message;
    int ordinal = -1;
};

inline bool isLimbRole(const QString &role) {
    for (const char *limb : {"HAND_L", "HAND_R", "FOOT_L", "FOOT_R", "ARM_L", "ARM_R",
                             "LEG_L", "LEG_R", "TOE_L", "TOE_R", "UPARM_L", "UPARM_R",
                             "UPLEG_L", "UPLEG_R", "HEAD"}) {
        if (role == QLatin1String(limb)) return true;
    }
    return false;
}

// Max displacement * (1 + speed) among limb roles; first input wins ties.
// Returns an empty string only when there are no limb samples.
QString suggestBone(const QVector<BoneSample> &bones);
QVector<Problem> runChecks(const QVector<RowAnalysis> &rows);
} // namespace wb
