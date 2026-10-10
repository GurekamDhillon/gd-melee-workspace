#include "../testfixture.h"
#include "geno_data.h"
#include <QTemporaryDir>
#include <QtTest>

using namespace wb;

namespace {
QByteArray diskBytes(const QString &dir, const QString &rel) {
    QFile file(QDir(dir).filePath(rel));
    return file.open(QIODevice::ReadOnly) ? file.readAll() : QByteArray();
}
void putProject(const QString &dir, const QJsonObject &project) {
    wbtest::put(dir, "workbench.json", QJsonDocument(project).toJson());
}
QJsonObject projectFixture() {
    return QJsonDocument::fromJson(wbtest::kProject).object();
}
}

class GenoDataTest : public QObject {
    Q_OBJECT
private slots:
    void projectConfigLoadsFieldsAndArgv() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        FileStore fs(d.path()); QString err = "old error";
        const auto config = ProjectConfig::load(fs, &err);
        QVERIFY2(err.isEmpty(), qPrintable(err));
        QCOMPARE(config.id, QString("synth"));
        QCOMPARE(config.gameplay, QString("gameplay.json"));
        QCOMPARE(config.movesDir, QString("moves"));
        QCOMPARE(config.fidelity, QString("fidelity.json"));
        QCOMPARE(config.plan, QString("package/files/plan.json"));
        QVERIFY(config.planAbs.isEmpty());
        QCOMPARE(config.modId, QString("synth"));
        QCOMPARE(config.rebuild, QStringList({"python", "-c", "print('rebuilt')"}));
        QCOMPARE(config.importClip.size(), 3);
    }
    void listsRows() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        FileStore fs(d.path()); GenoData data(fs);
        QVERIFY(data.reload().isEmpty());
        const auto rows = data.rows();
        QCOMPARE(rows.size(), 2);
        QCOMPARE(rows[1].name, QString("dair")); QVERIFY(rows[1].aerial);
        QCOMPARE(rows[1].moveIndex, 1);
        QCOMPARE(rows[1].cropStart, 2); QCOMPARE(rows[1].iasa, 36);
        QCOMPARE(rows[0].clip, QString("SYN_ATC_002"));
        QCOMPARE(rows[0].motions, QVector<int>({44}));
        QVERIFY(!rows[0].aerial);
        QCOMPARE(data.rowByMotion(70), QString("dair"));
        QVERIFY(data.rowByMotion(999).isEmpty());
    }
    void aerialComesOnlyFromTagAndScriptIsOptional() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        QByteArray gameplay = wbtest::kGameplay;
        gameplay.replace("\"tag\": \"aerial\"", "\"tag\": \"grounded\"");
        gameplay.replace("\"script\": \"moves/jab1.genoasm\",", "");
        wbtest::put(d.path(), "gameplay.json", gameplay);
        FileStore fs(d.path()); GenoData data(fs);
        QVERIFY(data.reload().isEmpty());
        QVERIFY(!data.rows()[1].aerial);
        QVERIFY(data.hitboxes("jab1").isEmpty());
        QString err; HitboxEdit edit; edit.damage = 4;
        QVERIFY(data.editHitbox("jab1", 0, edit, &err).isEmpty());
        QVERIFY(!err.isEmpty());
    }
    void hitboxesForRow() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        FileStore fs(d.path()); GenoData data(fs); QVERIFY(data.reload().isEmpty());
        const auto hitboxes = data.hitboxes("dair");
        QCOMPARE(hitboxes.size(), 2);
        QCOMPARE(hitboxes[0].joint, QString("FOOT_L"));
        QCOMPARE(hitboxes[0].startFrame, 6); QCOMPARE(hitboxes[0].endFrame, 9);
        QVERIFY(data.hitboxes("nope").isEmpty());
    }
    void rolesAndClips() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        FileStore fs(d.path()); GenoData data(fs); QVERIFY(data.reload().isEmpty());
        QCOMPARE(data.jointForRole("FOOT_L"), 3);
        QCOMPARE(data.jointForRole("@HAND_R@"), 2);
        QCOMPARE(data.jointForRole("HEAD"), -1);
        QCOMPARE(data.jointForRole("NOPE"), -1);
        const auto clips = data.clips();
        QCOMPARE(clips.size(), 3);
        QCOMPARE(clips[0].name, QString("SYN_ATC_002")); QCOMPARE(clips[0].frames, 30);
        const auto joints = data.joints();
        QCOMPARE(joints.size(), 4);
        QCOMPARE(joints[0].parent, -1);
        QCOMPARE(joints[3].index, 3); QCOMPARE(joints[3].name, QString("foot_l"));
        QCOMPARE(joints[3].parent, 1);
    }
    void planAbsWithoutPlanIsReadOnly() {
        QTemporaryDir d; QTemporaryDir built;
        wbtest::makeSynthFighter(d.path());
        wbtest::put(built.path(), "plan.json", wbtest::kPlan);
        auto config = projectFixture(); config.remove("plan");
        config["plan_abs"] = QDir(built.path()).filePath("plan.json");
        putProject(d.path(), config);
        FileStore fs(d.path()); GenoData data(fs);
        QVERIFY(data.reload().isEmpty());
        QCOMPARE(data.project().planAbs, config["plan_abs"].toString());
        QCOMPARE(data.jointForRole("FOOT_L"), 3);
        QString err;
        QCOMPARE(data.assignClip("dair", "SYN_ATC_009", {}, &err).size(), 2);
        QCOMPARE(diskBytes(built.path(), "plan.json"), QByteArray(wbtest::kPlan));
        wbtest::put(built.path(), "plan.json", "{}");
        QVERIFY(fs.externalChanges().isEmpty()); // Built output is never a FileStore source.
    }
    void planAbsResolvesFromWorkspaceAncestor() {
        QTemporaryDir workspace;
        wbtest::put(workspace.path(), ".git", "gitdir: synthetic\n");
        const QString project = QDir(workspace.path()).filePath("ports/synth");
        wbtest::makeSynthFighter(project);
        wbtest::put(workspace.path(), "_build/synth/plan.json", wbtest::kPlan);
        auto config = projectFixture(); config.remove("plan");
        config["plan_abs"] = "_build/synth/plan.json";
        putProject(project, config);
        FileStore fs(project); GenoData data(fs);
        QVERIFY(data.reload().isEmpty());
        QCOMPARE(data.jointForRole("HAND_R"), 2);
    }
    void editHitboxProducesOneFileChange() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        FileStore fs(d.path()); GenoData data(fs); QVERIFY(data.reload().isEmpty());
        QString err = "old error"; HitboxEdit edit; edit.joint = "HAND_R";
        const auto changes = data.editHitbox("dair", 0, edit, &err);
        QVERIFY2(changes.size() == 1, qPrintable(err)); QVERIFY(err.isEmpty());
        QCOMPARE(changes[0].path, QString("moves/dair.genoasm"));
        QCOMPARE(changes[0].before, QByteArray(wbtest::kDair));
        QByteArray expected = wbtest::kDair;
        expected.replace(expected.indexOf("@FOOT_L@"), 8, "@HAND_R@");
        QCOMPARE(changes[0].after, expected);
        QCOMPARE(diskBytes(d.path(), changes[0].path), QByteArray(wbtest::kDair));
        QVERIFY(data.editHitbox("nope", 0, edit, &err).isEmpty()); QVERIFY(err.contains("unknown row"));
        QVERIFY(data.editHitbox("dair", 10, edit, &err).isEmpty()); QVERIFY(!err.isEmpty());
    }
    void assignClipPatchesGameplayAndFidelityKeepingOtherBytes() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        FileStore fs(d.path()); GenoData data(fs); QVERIFY(data.reload().isEmpty());
        QString err = "old error";
        const auto changes = data.assignClip("dair", "SYN_ATC_009", 4, &err);
        QVERIFY2(changes.size() == 2, qPrintable(err)); QVERIFY(err.isEmpty());
        QCOMPARE(changes[0].path, QString("gameplay.json"));
        QCOMPARE(changes[0].before, QByteArray(wbtest::kGameplay));
        QByteArray gameplay = wbtest::kGameplay;
        gameplay.replace("\"SYN_ATC_007\", \"crop_start\": 2", "\"SYN_ATC_009\", \"crop_start\": 4");
        QCOMPARE(changes[0].after, gameplay);
        QCOMPARE(changes[1].path, QString("fidelity.json"));
        QCOMPARE(changes[1].before, QByteArray(wbtest::kFidelity));
        QByteArray fidelity = wbtest::kFidelity;
        fidelity.replace("SYN_ATC_007", "SYN_ATC_009");
        const int lastDeviation = fidelity.lastIndexOf("\"deviation\": \"\"");
        fidelity.replace(lastDeviation, 15, "\"deviation\": \"workbench: clip reassigned\"");
        QCOMPARE(changes[1].after, fidelity);
        QCOMPARE(diskBytes(d.path(), "gameplay.json"), QByteArray(wbtest::kGameplay));
        QCOMPARE(diskBytes(d.path(), "fidelity.json"), QByteArray(wbtest::kFidelity));
    }
    void assignClipUpdatesEveryMatchingMotionAndAppendsDeviation() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        QByteArray gameplay = wbtest::kGameplay; gameplay.replace("[70]", "[70, 71]");
        wbtest::put(d.path(), "gameplay.json", gameplay);
        const QByteArray fidelity = R"JSON({"rows":[
 {"motion":44,"clip":"SYN_ATC_002","deviation":"untouched"},
 {"motion":70,"clip":"SYN_ATC_007","deviation":"manual note"},
 {"motion":71,"clip":"SYN_ATC_007","deviation":""},
 {"motion":70,"clip":"SYN_ATC_007","deviation":"another"}
]})JSON";
        wbtest::put(d.path(), "fidelity.json", fidelity);
        FileStore fs(d.path()); GenoData data(fs); QVERIFY(data.reload().isEmpty());
        QString err; const auto changes = data.assignClip("dair", "SYN_ATC_009", {}, &err);
        QVERIFY2(changes.size() == 2, qPrintable(err));
        QByteArray expectedGameplay = gameplay; expectedGameplay.replace("SYN_ATC_007", "SYN_ATC_009");
        QCOMPARE(changes[0].after, expectedGameplay); // Omitted crop keeps the original crop.
        QByteArray expected = fidelity; expected.replace("SYN_ATC_007", "SYN_ATC_009");
        expected.replace("manual note", "manual note; workbench: clip reassigned");
        expected.replace("\"deviation\":\"\"", "\"deviation\":\"workbench: clip reassigned\"");
        expected.replace("\"another\"", "\"another; workbench: clip reassigned\"");
        QCOMPARE(changes[1].after, expected);
    }
    void assignClipInsertsAbsentCropAndDeviation() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        QByteArray gameplay = wbtest::kGameplay; gameplay.replace(", \"crop_start\": 2", "");
        wbtest::put(d.path(), "gameplay.json", gameplay);
        wbtest::put(d.path(), "fidelity.json", R"JSON({"rows":[{"motion":70,"clip":"SYN_ATC_007"}]})JSON");
        FileStore fs(d.path()); GenoData data(fs); QVERIFY(data.reload().isEmpty());
        QString err; const auto changes = data.assignClip("dair", "SYN_ATC_009", 0, &err);
        QVERIFY2(changes.size() == 2, qPrintable(err));
        const auto pick = QJsonDocument::fromJson(changes[0].after).object()["moves"].toArray()[1].toObject()["pick"].toObject();
        QVERIFY(pick.contains("crop_start")); QCOMPARE(pick["crop_start"].toInt(-1), 0);
        const auto row = QJsonDocument::fromJson(changes[1].after).object()["rows"].toArray()[0].toObject();
        QCOMPARE(row["deviation"].toString(), QString("workbench: clip reassigned"));
    }
    void editsPreserveBomCrLfAndUnicode() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        QByteArray gameplay = QByteArray("\xEF\xBB\xBF") + wbtest::kGameplay;
        gameplay.replace("\n", "\r\n");
        gameplay.replace("\"version\": 1,", "\"version\": 1, \"note\": \"caf\xC3\xA9\",");
        QByteArray script = QByteArray("\xEF\xBB\xBF") + wbtest::kDair;
        script.replace("\n", "\r\n");
        wbtest::put(d.path(), "gameplay.json", gameplay);
        wbtest::put(d.path(), "moves/dair.genoasm", script);
        FileStore fs(d.path()); GenoData data(fs); QVERIFY(data.reload().isEmpty());
        QString err;
        const auto clips = data.assignClip("dair", "SYN_ATC_009", {}, &err);
        QVERIFY2(clips.size() == 2, qPrintable(err));
        QByteArray expected = gameplay; expected.replace("SYN_ATC_007", "SYN_ATC_009");
        QCOMPARE(clips[0].before, gameplay); QCOMPARE(clips[0].after, expected);
        HitboxEdit edit; edit.joint = "HAND_R";
        const auto hitboxes = data.editHitbox("dair", 0, edit, &err);
        QVERIFY2(hitboxes.size() == 1, qPrintable(err));
        expected = script; expected.replace(expected.indexOf("@FOOT_L@"), 8, "@HAND_R@");
        QCOMPARE(hitboxes[0].before, script); QCOMPARE(hitboxes[0].after, expected);
    }
    void assignClipRejectsUnknownClipAndRow() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        FileStore fs(d.path()); GenoData data(fs); QVERIFY(data.reload().isEmpty()); QString err;
        QVERIFY(data.assignClip("dair", "NOPE", {}, &err).isEmpty()); QVERIFY(err.contains("unknown clip"));
        QVERIFY(data.assignClip("zzz", "SYN_ATC_009", {}, &err).isEmpty()); QVERIFY(err.contains("unknown row"));
    }
    void missingProjectFileReportsError() {
        QTemporaryDir d; FileStore fs(d.path()); GenoData data(fs);
        QVERIFY(data.reload().contains("workbench.json"));
    }
    void badProjectSchemaAndMalformedJsonReportErrors() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        auto config = projectFixture(); config["schema"] = "workbench/2"; putProject(d.path(), config);
        FileStore fs(d.path()); GenoData data(fs);
        QVERIFY(data.reload().contains("unsupported schema"));
        wbtest::put(d.path(), "workbench.json", "{ broken");
        QVERIFY(data.reload().contains("workbench.json")); QVERIFY(data.rows().isEmpty());
    }
    void malformedGameplayReportsErrorNotCrashAndClearsOldRows() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        FileStore fs(d.path()); GenoData data(fs); QVERIFY(data.reload().isEmpty());
        wbtest::put(d.path(), "gameplay.json", "{ not json");
        const QString err = data.reload();
        QVERIFY(err.contains("gameplay.json")); QVERIFY(err.contains("offset"));
        QVERIFY(data.rows().isEmpty()); QVERIFY(data.clips().isEmpty()); QVERIFY(data.hitboxes("dair").isEmpty());
        wbtest::put(d.path(), "gameplay.json", R"JSON({"moves":{}})JSON");
        QVERIFY(!data.reload().isEmpty());
    }
    void optionalMissingPlanAndFidelityAreAllowed() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        QVERIFY(QFile::remove(QDir(d.path()).filePath("package/files/plan.json")));
        QVERIFY(QFile::remove(QDir(d.path()).filePath("fidelity.json")));
        FileStore fs(d.path()); GenoData data(fs);
        QVERIFY(data.reload().isEmpty()); QCOMPARE(data.rows().size(), 2);
        QVERIFY(data.clips().isEmpty()); QVERIFY(data.joints().isEmpty());
        QCOMPARE(data.jointForRole("FOOT_L"), -1);
        wbtest::put(d.path(), "package/files/plan.json", wbtest::kPlan);
        QVERIFY(data.reload().isEmpty()); QString err;
        const auto changes = data.assignClip("dair", "SYN_ATC_009", {}, &err);
        QVERIFY2(changes.size() == 1, qPrintable(err));
    }
    void malformedOptionalFilesAndUnsafeSourcePathsReportErrors() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        FileStore fs(d.path()); GenoData data(fs);
        wbtest::put(d.path(), "fidelity.json", "{ broken");
        QVERIFY(data.reload().contains("fidelity.json")); QVERIFY(data.rows().isEmpty());
        wbtest::put(d.path(), "fidelity.json", wbtest::kFidelity);
        wbtest::put(d.path(), "package/files/plan.json", "{ broken");
        QVERIFY(data.reload().contains("plan.json"));
        auto config = projectFixture(); config["gameplay"] = "../escape.json"; putProject(d.path(), config);
        QVERIFY(data.reload().contains("unsafe path"));
    }
    void everyRoleUsesThePlanRoleKey() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        const QVector<QPair<QString, QString>> roles = {
            {"HAND_R", "hand.R"}, {"HAND_L", "hand.L"},
            {"FOOT_R", "foot.R"}, {"FOOT_L", "foot.L"}, {"CHEST", "chest"},
            {"ARM_R", "lower_arm.R"}, {"ARM_L", "lower_arm.L"},
            {"LEG_R", "lower_leg.R"}, {"LEG_L", "lower_leg.L"},
            {"HIPS", "hips"}, {"FLOOR", "translation"},
            {"UPLEG_R", "upper_leg.R"}, {"UPLEG_L", "upper_leg.L"},
            {"UPARM_R", "upper_arm.R"}, {"UPARM_L", "upper_arm.L"},
            {"HEAD", "head"}, {"NECK", "neck"}, {"SPINE", "spine"},
            {"TOE_R", "toe.R"}, {"TOE_L", "toe.L"}
        };
        QJsonArray joints; QJsonObject mapping;
        for (int i = 0; i < roles.size(); ++i) {
            joints.append(QJsonObject{{"index", i}, {"name", QString("joint_%1").arg(i)}, {"parent", -1}});
            mapping[roles[i].second] = QJsonArray{i};
        }
        wbtest::put(d.path(), "package/files/plan.json",
                    QJsonDocument(QJsonObject{{"joints", joints}, {"roles", mapping}}).toJson());
        FileStore fs(d.path()); GenoData data(fs); QVERIFY(data.reload().isEmpty());
        for (int i = 0; i < roles.size(); ++i) {
            QCOMPARE(data.jointForRole(roles[i].first), i);
            QCOMPARE(data.jointForRole("@" + roles[i].first + "@"), i);
        }
    }
    void planAbsTakesPrecedenceOverPlan() {
        QTemporaryDir d; QTemporaryDir built; wbtest::makeSynthFighter(d.path());
        auto config = projectFixture();
        config["plan_abs"] = QDir(built.path()).filePath("plan.json");
        putProject(d.path(), config);
        wbtest::put(built.path(), "plan.json", R"JSON({"bank":{"clips":{"SYN_OTHER":{"frames":12}}}})JSON");
        FileStore fs(d.path()); GenoData data(fs); QVERIFY(data.reload().isEmpty());
        QCOMPARE(data.clips().size(), 1);
        QCOMPARE(data.clips()[0].name, QString("SYN_OTHER"));
        QCOMPARE(data.jointForRole("FOOT_L"), -1);
        QVERIFY(QFile::remove(QDir(built.path()).filePath("plan.json")));
        QVERIFY(data.reload().isEmpty());
        QVERIFY(data.clips().isEmpty()); // Missing override never silently reads a stale package plan.
    }
    void projectRejectsInvalidFieldTypes() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); FileStore fs(d.path()); QString err;
        auto config = projectFixture(); config["rebuild"] = "python build.py";
        putProject(d.path(), config); ProjectConfig::load(fs, &err);
        QVERIFY(err.contains("rebuild"));
        config = projectFixture(); config["import_clip"] = QJsonArray{"python", 42};
        putProject(d.path(), config); ProjectConfig::load(fs, &err);
        QVERIFY(err.contains("import_clip"));
        config = projectFixture(); config.remove("gameplay");
        putProject(d.path(), config); ProjectConfig::load(fs, &err);
        QVERIFY(err.contains("gameplay"));
    }
    void reloadReflectsAppliedChanges() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        FileStore fs(d.path()); GenoData data(fs); QVERIFY(data.reload().isEmpty()); QString err;
        const auto clips = data.assignClip("dair", "SYN_ATC_009", 4, &err);
        QVERIFY2(clips.size() == 2, qPrintable(err));
        fs.beginSnapshot("assign_clip");
        for (const auto &change : clips) fs.write(change.path, change.after);
        QVERIFY(data.reload().isEmpty());
        QCOMPARE(data.rows()[1].clip, QString("SYN_ATC_009"));
        QCOMPARE(data.rows()[1].cropStart, 4);
        HitboxEdit edit; edit.joint = "HAND_R";
        const auto boxes = data.editHitbox("dair", 0, edit, &err);
        QVERIFY2(boxes.size() == 1, qPrintable(err));
        fs.beginSnapshot("edit_hitbox"); fs.write(boxes[0].path, boxes[0].after);
        QVERIFY(data.reload().isEmpty());
        QCOMPARE(data.hitboxes("dair")[0].joint, QString("HAND_R"));
    }
    void fidelityHandEditIsNeverAcknowledgedByAssignClip() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        FileStore fs(d.path()); GenoData data(fs); QVERIFY(data.reload().isEmpty());
        const QByteArray handEdit = QByteArray(wbtest::kFidelity) + "\n";
        wbtest::put(d.path(), "fidelity.json", handEdit);
        QString err;
        QVERIFY(data.assignClip("dair", "SYN_ATC_009", {}, &err).isEmpty());
        QVERIFY(err.contains("changed externally"));
        QVERIFY(fs.externalChanges().contains("fidelity.json"));
        QCOMPARE(diskBytes(d.path(), "fidelity.json"), handEdit);
        QCOMPARE(diskBytes(d.path(), "gameplay.json"), QByteArray(wbtest::kGameplay));
    }
    void failedFidelityPatchReturnsNoPartialGameplayChange() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        wbtest::put(d.path(), "fidelity.json", R"JSON({"rows":[{"motion":70,"deviation":"kept"}]})JSON");
        FileStore fs(d.path()); GenoData data(fs); QVERIFY(data.reload().isEmpty()); QString err;
        QVERIFY(data.assignClip("dair", "SYN_ATC_009", {}, &err).isEmpty());
        QVERIFY(err.contains("fidelity.json"));
        QCOMPARE(diskBytes(d.path(), "gameplay.json"), QByteArray(wbtest::kGameplay));
    }
    void unsafeScriptAndInvalidUtf8FailWithoutRewritingSource() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        QByteArray gameplay = wbtest::kGameplay;
        gameplay.replace("moves/dair.genoasm", "../dair.genoasm");
        wbtest::put(d.path(), "gameplay.json", gameplay);
        FileStore fs(d.path()); GenoData data(fs);
        QVERIFY(data.reload().contains("unsafe path")); QVERIFY(data.rows().isEmpty());
        wbtest::put(d.path(), "gameplay.json", wbtest::kGameplay);
        const QByteArray script = QByteArray(wbtest::kDair) + "# bad \xFF\n";
        wbtest::put(d.path(), "moves/dair.genoasm", script);
        QVERIFY(!data.reload().isEmpty());
        HitboxEdit edit; edit.damage = 20; QString err;
        QVERIFY(data.editHitbox("dair", 0, edit, &err).isEmpty());
        QCOMPARE(diskBytes(d.path(), "moves/dair.genoasm"), script);
    }
    void malformedRowsDoNotTurnIntoDefaultMotionZero() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        QByteArray gameplay = wbtest::kGameplay; gameplay.replace("[70]", "[\"70\"]");
        wbtest::put(d.path(), "gameplay.json", gameplay);
        FileStore fs(d.path()); GenoData data(fs);
        QVERIFY(data.reload().contains("motions")); QVERIFY(data.rows().isEmpty());
        gameplay = wbtest::kGameplay; gameplay.replace("\"name\": \"dair\"", "\"name\": \"jab1\"");
        wbtest::put(d.path(), "gameplay.json", gameplay);
        QVERIFY(data.reload().contains("duplicate")); QVERIFY(data.rows().isEmpty());
    }
    void nonStringDeviationCannotBeSilentlyDiscarded() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        const QByteArray fidelity = R"JSON({"rows":[{"motion":70,"clip":"SYN_ATC_007","deviation":["keep"]}]})JSON";
        wbtest::put(d.path(), "fidelity.json", fidelity);
        FileStore fs(d.path()); GenoData data(fs); QVERIFY(data.reload().isEmpty()); QString err;
        QVERIFY(data.assignClip("dair", "SYN_ATC_009", {}, &err).isEmpty());
        QVERIFY(err.contains("deviation")); QCOMPARE(diskBytes(d.path(), "fidelity.json"), fidelity);
    }
    void inspectionAndEditsNeverAcknowledgeExternalChanges() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        FileStore fs(d.path()); GenoData data(fs); QVERIFY(data.reload().isEmpty());
        wbtest::put(d.path(), "moves/dair.genoasm", QByteArray(wbtest::kDair) + "# hand edit\n");
        data.hitboxes("dair");
        QVERIFY(fs.externalChanges().contains("moves/dair.genoasm"));
        QString err; HitboxEdit edit; edit.damage = 16;
        QVERIFY(data.editHitbox("dair", 0, edit, &err).isEmpty());
        QVERIFY(err.contains("changed externally"));
        wbtest::put(d.path(), "gameplay.json", QByteArray(wbtest::kGameplay) + "\n");
        QVERIFY(data.assignClip("dair", "SYN_ATC_009", {}, &err).isEmpty());
        QVERIFY(err.contains("changed externally"));
        QVERIFY(fs.externalChanges().contains("gameplay.json"));
    }
};

QTEST_GUILESS_MAIN(GenoDataTest)
#include "geno_data_test.moc"
