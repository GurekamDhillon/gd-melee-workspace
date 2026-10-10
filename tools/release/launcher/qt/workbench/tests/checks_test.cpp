#include "checks.h"
#include <QtTest>
using namespace wb;

static RowAnalysis row(const QString &name) { RowAnalysis r; r.row = name; r.tag = "jab"; return r; }

class ChecksTest : public QObject {
    Q_OBJECT
private slots:
    void suggestPicksFastestFarthestLimb() {
        QVector<BoneSample> b{{"CHEST", 9, 9}, {"HAND_R", 5, 1}, {"FOOT_L", 6, 3}, {"HAND_L", 1, 0}};
        QCOMPARE(suggestBone(b), QString("FOOT_L"));    // non-limbs ignored
    }
    void suggestEmptyWhenNoLimbs() { QCOMPARE(suggestBone({{"CHEST", 9, 9}}), QString()); QCOMPARE(suggestBone({}), QString()); }
    void wrongLimbFlagged() {
        RowAnalysis r = row("dair"); r.hitboxes = {{0, "HAND_R", 6, 0}}; r.bones = {{"HAND_R", 1, 0}, {"FOOT_L", 6, 4}};
        auto p = runChecks({r});
        QCOMPARE(p.size(), 1); QCOMPARE(p[0].kind, QString("wrong_limb")); QCOMPARE(p[0].ordinal, 0); QVERIFY(p[0].message.contains("FOOT_L"));
    }
    void closeCallIsNotWrongLimb() {
        RowAnalysis r = row("jab"); r.hitboxes = {{0, "HAND_R", 3, 0}}; r.bones = {{"HAND_R", 5, 1}, {"HAND_L", 5.2, 1}};
        QVERIFY(runChecks({r}).isEmpty());
    }
    void belowFloorOnGroundOnly() {
        RowAnalysis g = row("dtilt"); g.floorY = 0; g.rowLowestY = -1.2;
        RowAnalysis a = row("dair"); a.aerial = true; a.floorY = 0; a.rowLowestY = -3;
        auto p = runChecks({g, a});
        QCOMPARE(p.size(), 1); QCOMPARE(p[0].kind, QString("below_floor")); QCOMPARE(p[0].row, QString("dtilt"));
    }
    void duplicateClip() {
        RowAnalysis a = row("a"), b = row("b"), c = row("c"); a.clip = b.clip = "X"; c.clip = "Y";
        auto p = runChecks({a, b, c});
        QCOMPARE(p.size(), 1); QCOMPARE(p[0].kind, QString("duplicate_clip")); QCOMPARE(p[0].row, QString("b"));
    }
    void emptyClipsAreNotDuplicates() { RowAnalysis a = row("a"), b = row("b"); QVERIFY(runChecks({a, b}).isEmpty()); }
    void groundedClipOnAerial() {
        RowAnalysis a = row("uair"); a.aerial = true; a.groundedClip = true;
        auto p = runChecks({a}); QCOMPARE(p.size(), 1);
        QCOMPARE(p[0].kind, QString("grounded_clip_on_aerial"));
    }
    void swingWithoutHitbox() {
        RowAnalysis a = row("ftilt"); a.hasSwingMotion = true;
        auto p = runChecks({a}); QCOMPARE(p.size(), 1);
        QCOMPARE(p[0].kind, QString("swing_without_hitbox"));
    }
    void allLimbRolesAreEligible() {
        for (const char *role : {"HAND_L", "HAND_R", "FOOT_L", "FOOT_R", "ARM_L", "ARM_R",
                                 "LEG_L", "LEG_R", "TOE_L", "TOE_R", "UPARM_L", "UPARM_R",
                                 "UPLEG_L", "UPLEG_R", "HEAD"}) {
            QVERIFY2(isLimbRole(role), role);
            QCOMPARE(suggestBone({{role, 2, 1}, {"CHEST", 10, 10}}), QString(role));
        }
        for (const char *role : {"", "CHEST", "ROOT", "HAND", "HAND_X", "HAND_R_EXTRA",
                                 "hand.R", "HEAD_L", "@HAND_R@"}) {
            QVERIFY2(!isLimbRole(role), role);
            QCOMPARE(suggestBone({{role, 10, 10}}), QString());
        }
    }
    void suggestionUsesDisplacementAndSpeed() {
        QCOMPARE(suggestBone({{"HAND_R", 5, 0}, {"FOOT_L", 1, 3}}), QString("HAND_R"));
    }
    void suggestionTiesKeepFirstLimbEvenAtRest() {
        QCOMPARE(suggestBone({{"HAND_R", 2, 2}, {"FOOT_L", 3, 1}}), QString("HAND_R"));
        QCOMPARE(suggestBone({{"CHEST", 0, 0}, {"FOOT_L", 0, 0}, {"HAND_R", 0, 0}}), QString("FOOT_L"));
    }
    void wrongLimbThresholdIsInclusive() {
        RowAnalysis r = row("jab"); r.hitboxes = {{0, "HAND_R", 3, 0}};
        r.bones = {{"HAND_R", 2, 1}, {"FOOT_L", 2, 2}};
        auto p = runChecks({r});
        QCOMPARE(p.size(), 1); // scores 4 and 6: exactly 1.5x
        QCOMPARE(p[0].kind, QString("wrong_limb"));
        r.bones[1].speed = 1.99;
        QVERIFY(runChecks({r}).isEmpty());
    }
    void wrongLimbUsesEachHitboxOrdinalAndFrame() {
        RowAnalysis r = row("dair");
        r.hitboxes = {{7, "HAND_R", 6, 0}, {2, "FOOT_L", 9, 0}, {12, "HAND_L", 11, 0}};
        r.bones = {{"HAND_R", 1, 0}, {"HAND_L", 2, 0}, {"FOOT_L", 6, 4}};
        auto p = runChecks({r});
        QCOMPARE(p.size(), 2);
        QCOMPARE(p[0].kind, QString("wrong_limb")); QCOMPARE(p[1].kind, QString("wrong_limb"));
        QCOMPARE(p[0].row, QString("dair")); QCOMPARE(p[1].row, QString("dair"));
        QCOMPARE(p[0].ordinal, 7); QCOMPARE(p[1].ordinal, 12);
        QVERIFY(p[0].message.contains("#7")); QVERIFY(p[0].message.contains("HAND_R"));
        QVERIFY(p[1].message.contains("frame 11"));
    }
    void nonLimbCurrentBoneStillHasAScore() {
        RowAnalysis r = row("jab"); r.hitboxes = {{0, "CHEST", 3, 0}};
        r.bones = {{"CHEST", 10, 0}, {"HAND_R", 6, 1}};
        QVERIFY(runChecks({r}).isEmpty()); // 12 does not exceed 10 by 1.5x
        r.bones[0].displacement = 1;
        auto p = runChecks({r});
        QCOMPARE(p.size(), 1); QCOMPARE(p[0].kind, QString("wrong_limb"));
    }
    void missingSamplesDoNotAccuseWrongLimb() {
        RowAnalysis r = row("jab"); r.hitboxes = {{0, "HAND_R", 3, 0}};
        QVERIFY(runChecks({r}).isEmpty());
        r.bones = {{"FOOT_L", 6, 4}}; // no measured score for the current bone
        QVERIFY(runChecks({r}).isEmpty());
        r.bones = {{"CHEST", 9, 9}};
        QVERIFY(runChecks({r}).isEmpty());
    }
    void stationaryBonesDoNotAccuseWrongLimb() {
        RowAnalysis r = row("jab"); r.hitboxes = {{0, "HAND_R", 3, 0}};
        r.bones = {{"FOOT_L", 0, 0}, {"HAND_R", 0, 0}};
        QVERIFY(runChecks({r}).isEmpty());
        r.bones[0].displacement = 1;
        auto p = runChecks({r});
        QCOMPARE(p.size(), 1); QCOMPARE(p[0].kind, QString("wrong_limb"));
    }
    void belowFloorUsesStrictMarginAndFloorHeight() {
        RowAnalysis r = row("dtilt"); r.floorY = 10; r.rowLowestY = 9.5;
        QVERIFY(runChecks({r}).isEmpty());
        r.rowLowestY = 9.49;
        auto p = runChecks({r});
        QCOMPARE(p.size(), 1); QCOMPARE(p[0].kind, QString("below_floor"));
        QCOMPARE(p[0].ordinal, -1);
    }
    void duplicateClipReportsEachExtraDistinctRowOnce() {
        RowAnalysis a = row("a"), b = row("b"), c = row("c"); a.clip = b.clip = c.clip = "X";
        auto p = runChecks({a, a, b, b, c, a, c});
        QCOMPARE(p.size(), 2);
        QCOMPARE(p[0].kind, QString("duplicate_clip")); QCOMPARE(p[0].row, QString("b"));
        QCOMPARE(p[1].kind, QString("duplicate_clip")); QCOMPARE(p[1].row, QString("c"));
        QCOMPARE(p[0].ordinal, -1); QCOMPARE(p[1].ordinal, -1);
    }
    void groundedClipCheckNeedsBothFlags() {
        RowAnalysis g = row("jab"), a = row("uair"); g.groundedClip = true; a.aerial = true;
        QVERIFY(runChecks({g, a}).isEmpty());
    }
    void swingWithHitboxIsNotAProblem() {
        RowAnalysis r = row("ftilt"); r.hasSwingMotion = true; r.hitboxes = {{0, "HAND_R", 3, 0}};
        QVERIFY(runChecks({r}).isEmpty());
    }
    void reportsAllApplicableChecks() {
        RowAnalysis a = row("a"), b = row("b"); a.clip = b.clip = "X";
        b.aerial = b.groundedClip = b.hasSwingMotion = true;
        auto p = runChecks({a, b});
        QCOMPARE(p.size(), 3);
        QStringList kinds;
        for (const auto &problem : p) {
            QCOMPARE(problem.row, QString("b")); QCOMPARE(problem.ordinal, -1);
            QVERIFY(!problem.message.isEmpty()); kinds.append(problem.kind);
        }
        QVERIFY(kinds.contains("duplicate_clip"));
        QVERIFY(kinds.contains("grounded_clip_on_aerial"));
        QVERIFY(kinds.contains("swing_without_hitbox"));
    }
    void noRowsNoProblems() { QVERIFY(runChecks({}).isEmpty()); }
};
QTEST_MAIN(ChecksTest)
#include "checks_test.moc"
