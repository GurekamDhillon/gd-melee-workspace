#include "../testfixture.h"
#include "geno_data.h"
#include <QTemporaryDir>
#include <QtTest>
#include <functional>

using namespace wb;

namespace {
QByteArray diskBytes(const QString &dir, const QString &rel) {
    QFile file(QDir(dir).filePath(rel));
    return file.open(QIODevice::ReadOnly) ? file.readAll() : QByteArray();
}
const RowInfo *findIn(const GenoData &data, const QString &name) {
    static QVector<RowInfo> keep;
    keep = data.rows();
    for (const auto &row : keep) if (row.name == name) return &row;
    return nullptr;
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
    void specialStatesAreRowsAndEditTheirOwnScript() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        QJsonObject gameplay = QJsonDocument::fromJson(wbtest::kGameplay).object();
        gameplay["states"] = QJsonArray{
            QJsonObject{{"name", "KameCharge"}, {"behavior", "geno.ground"}, {"subaction", 295}},
            QJsonObject{{"name", "Rush"}, {"behavior", "geno.ground"}, {"subaction", 299}},
            QJsonObject{{"name", "Flight"}, {"behavior", "geno.air"}, {"subaction", "clip:SYN_ATC_009"}},
            QJsonObject{{"name", "RushCombo"}, {"behavior", "geno.ground"}, {"subaction", "clip:SYN_ATC_007"}},
            QJsonObject{{"name", "FlightNair"}, {"behavior", "geno.air"}, {"subaction", "clip:SYN_ATC_009"}, {"move_tag", "aerial"}}};
        gameplay["specials"] = QJsonObject{{"s", "geno:Rush"}, {"air_s", "geno:Rush"}, {"hi", "geno:Flight"}};
        gameplay["special_adaptations"] = QJsonArray{
            QJsonObject{{"name", "Rush"}, {"script", "moves/rush.genoasm"}, {"windows", QJsonArray{QJsonValue(QJsonArray{3, 2})}}},
            QJsonObject{{"name", "Flight"}, {"script", "moves/flight.genoasm"}},
            QJsonObject{{"name", "RushCombo"}, {"script", "moves/rushcombo.genoasm"}},
            QJsonObject{{"name", "FlightNair"}, {"script", "moves/nair.genoasm"}},
            QJsonObject{{"name", "KameCharge"}, {"script", "moves/missing.genoasm"}}};
        wbtest::put(d.path(), "gameplay.json", QJsonDocument(gameplay).toJson());
        wbtest::put(d.path(), "moves/rush.genoasm", wbtest::kJab);
        wbtest::put(d.path(), "moves/flight.genoasm", "# flight\nwait 2\n");
        wbtest::put(d.path(), "moves/rushcombo.genoasm", "# combo\nwait 2\n");
        FileStore fs(d.path()); GenoData data(fs);
        const QString reload = data.reload(); QVERIFY2(reload.isEmpty(), qPrintable(reload));
        QStringList names; for (const auto &row : data.rows()) names << row.name;
        // moves first, then the specials that have a script on disk; the aerial state and the missing script are left out
        QCOMPARE(names, QStringList({"jab1", "dair", "side_b (Rush)", "up_b (Flight)", "RushCombo (special)"}));
        const auto *rush = findIn(data, "side_b (Rush)");
        QVERIFY(rush);
        QCOMPARE(rush->motions, QVector<int>({0x401}));
        QCOMPARE(rush->script, QString("moves/rush.genoasm"));
        QCOMPARE(rush->section, QString("special_adaptations"));
        QVERIFY(rush->previewable());
        QVERIFY(findIn(data, "up_b (Flight)")->aerial);
        QCOMPARE(findIn(data, "up_b (Flight)")->stateClip, QString("SYN_ATC_009"));
        QCOMPARE(findIn(data, "up_b (Flight)")->effectiveClip(), QString("SYN_ATC_009"));
        QCOMPARE(rush->stateClip, QString("Rush")); // no such clip in the bank: no fixed clip, still playable
        QCOMPARE(data.hitboxes("side_b (Rush)").size(), 1);
        QString err; HitboxEdit edit; edit.startFrame = 5; edit.endFrame = 9; edit.damage = 11;
        const auto changes = data.editHitbox("side_b (Rush)", 0, edit, &err);
        QVERIFY2(err.isEmpty() && !changes.isEmpty(), qPrintable(err));
        QStringList paths; for (const auto &c : changes) paths << c.path;
        QVERIFY(paths.contains("moves/rush.genoasm"));
        QVERIFY(!paths.contains("moves/jab1.genoasm"));
        for (const auto &c : changes) {
            if (c.path == "moves/rush.genoasm") QVERIFY(QString::fromUtf8(c.after).contains("damage=11"));
            if (c.path == "gameplay.json") {
                const auto adapted = QJsonDocument::fromJson(c.after).object()["special_adaptations"].toArray()[0].toObject();
                QCOMPARE(QJsonDocument(adapted["windows"].toArray()).toJson(QJsonDocument::Compact), QByteArray("[[5,4]]"));
            }
        }
        QVERIFY(paths.contains("gameplay.json"));
        QVERIFY(data.assignClip("side_b (Rush)", "SYN_ATC_009", {}, &err).isEmpty());
        QVERIFY(err.contains("special"));
    }
    void emptyPickTakesClipFromPlan() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        QString gameplay = QString::fromUtf8(wbtest::kGameplay);
        gameplay.replace("\"clip\": \"SYN_ATC_002\", ", "").replace("\"clip\": \"SYN_ATC_007\", ", "");
        wbtest::put(d.path(), "gameplay.json", gameplay.toUtf8().constData());
        FileStore fs(d.path()); GenoData data(fs);
        QVERIFY(data.reload().isEmpty());
        const auto rows = data.rows();
        QCOMPARE(rows[0].clip, QString());
        QCOMPARE(rows[0].effectiveClip(), QString("SYN_ATC_002"));
        QCOMPARE(rows[1].effectiveClip(), QString("SYN_ATC_007"));
    }
    void explicitEmptyPickDoesNotBorrowClipFromPlan() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        QByteArray gameplay = wbtest::kGameplay;
        gameplay.replace("\"clip\": \"SYN_ATC_002\"", "\"clip\": \"\"");
        wbtest::put(d.path(), "gameplay.json", gameplay);
        FileStore fs(d.path()); GenoData data(fs);
        QVERIFY(data.reload().isEmpty());
        QCOMPARE(data.rows()[0].planClip, QString("SYN_ATC_002"));
        QVERIFY(data.rows()[0].effectiveClip().isEmpty());
        QCOMPARE(data.rows()[1].effectiveClip(), QString("SYN_ATC_007"));
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
    void timelineEventsUseCachedSourceAndLiteralFrames() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        wbtest::put(d.path(), "moves/jab1.genoasm", "wait_until 3\nsound id=7 # note\nwait 2\nsound id=9\n");
        FileStore fs(d.path()); GenoData data(fs); QVERIFY(data.reload().isEmpty());
        auto events = data.timelineEvents("jab1"); QCOMPARE(events.size(), 2);
        QCOMPARE(events[0].toObject()["frame"].toInt(), 3); QCOMPARE(events[1].toObject()["frame"].toInt(), 5);
        QCOMPARE(events[0].toObject()["label"].toString(), QString("sound id=7"));
        wbtest::put(d.path(), "moves/jab1.genoasm", "wait_until 40\nsound id=8\n");
        QCOMPARE(data.timelineEvents("jab1"), events); // A UI refresh cannot acknowledge a hand edit.
        QVERIFY(fs.externalChanges().contains("moves/jab1.genoasm"));
        QVERIFY(data.timelineEvents("unknown").isEmpty());
    }
    void timelineEventsStopAtNonlinearControlFlow() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        wbtest::put(d.path(), "moves/jab1.genoasm", "wait_until 3\nsound id=7\nloop 2\nwait 2\nsound id=9\n");
        FileStore fs(d.path()); GenoData data(fs); QVERIFY(data.reload().isEmpty());
        QCOMPARE(data.timelineEvents("jab1").size(), 1);
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
    void artKeysAreReadOptionally() {
        QTemporaryDir d;
        wbtest::makeSynthFighter(d.path());
        {
            FileStore fs(d.path()); GenoData data(fs);
            QVERIFY(data.reload().isEmpty());
            QVERIFY(data.project().artBlend.isEmpty() && data.project().artGlb.isEmpty());
        }
        auto config = projectFixture();
        config["art_blend"] = "_build/synth/rig.blend"; config["art_glb"] = "_build/synth/rig.glb";
        putProject(d.path(), config);
        {
            FileStore fs(d.path()); GenoData data(fs);
            QVERIFY(data.reload().isEmpty());
            QCOMPARE(data.project().artBlend, QString("_build/synth/rig.blend"));
            QCOMPARE(data.project().artGlb, QString("_build/synth/rig.glb"));
        }
        config["art_glb"] = QString("a") + QChar(0) + "b";
        putProject(d.path(), config);
        FileStore fs(d.path()); GenoData data(fs);
        QVERIFY(!data.reload().isEmpty());
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
    // The owner's dair sequence (2026-10-10): move window 0 from 6 to 12 (length 4), then add FOOT_L at 12
    // for 3 frames. The script must stay in start-frame order with distinct slots, and gameplay.json's
    // windows must equal the script's timing.
    void ownerDairSequenceStaysOrderedAndDeclared() {
        static const char *dair =
            "# PICK: provisional\nPUT ANIM_RATE 1.0\nwait_until 4\ncmd_var idx=0 value=1\nwait_until 4\n"
            "sfx behavior=1 sfx_id=164 volume=127 panning=64\nwait_until 6\n"
            "hitbox slot=0 joint=@FOOT_R@ damage=14 size=2.80 x=0.00 y=0.00 z=0.00 angle=270 kbg=90 fkb=0 bkb=20\n"
            "wait 3\nclear_hitboxes\nwait_until 9\n"
            "hitbox slot=0 joint=@FOOT_R@ damage=10 size=2.40 x=0.00 y=0.00 z=0.00 angle=361 kbg=90 fkb=0 bkb=15\n"
            "wait 6\nclear_hitboxes\nwait_until 26\ncmd_var idx=0 value=0\nwait_until 36\niasa\n";
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        QJsonObject gameplay = QJsonDocument::fromJson(wbtest::kGameplay).object();
        QJsonArray moves = gameplay["moves"].toArray();
        QJsonObject dairMove = moves[1].toObject();
        dairMove["windows"] = QJsonArray{QJsonArray{6, 3}, QJsonArray{9, 6}};
        dairMove["design"] = QJsonObject{{"window_roles", QJsonArray{"FOOT_R", "FOOT_R"}}};
        moves[1] = dairMove; gameplay["moves"] = moves;
        wbtest::put(d.path(), "gameplay.json", QJsonDocument(gameplay).toJson());
        wbtest::put(d.path(), "moves/dair.genoasm", dair);
        const auto step = [&](const std::function<QVector<FileChange>(GenoData &, QString *)> &op) {
            FileStore fs(d.path()); GenoData data(fs);
            const QString reload = data.reload(); QVERIFY2(reload.isEmpty(), qPrintable(reload));
            QString err; const auto changes = op(data, &err);
            QVERIFY2(err.isEmpty() && !changes.isEmpty(), qPrintable(err));
            for (const auto &c : changes) wbtest::put(d.path(), c.path, c.after);
        };
        step([](GenoData &data, QString *err) {
            HitboxEdit e; e.startFrame = 12; e.endFrame = 16; return data.editHitbox("dair", 0, e, err); });
        step([](GenoData &data, QString *err) {
            HitboxAdd a; a.joint = "FOOT_L"; a.frame = 12; a.duration = 3; return data.addHitbox("dair", a, nullptr, err); });
        FileStore fs(d.path()); GenoData data(fs); QVERIFY(data.reload().isEmpty());
        const QString script = QString::fromUtf8(diskBytes(d.path(), "moves/dair.genoasm"));
        const auto boxes = data.hitboxes("dair");
        QVERIFY2(boxes.size() == 3, qPrintable(script));
        // Start-frame order, and no two windows that overlap share a slot.
        for (int i = 1; i < boxes.size(); ++i) QVERIFY2(boxes[i - 1].startFrame <= boxes[i].startFrame, qPrintable(script));
        for (int i = 0; i < boxes.size(); ++i) for (int j = i + 1; j < boxes.size(); ++j) {
            const bool overlap = boxes[i].startFrame < boxes[j].endFrame && boxes[j].startFrame < boxes[i].endFrame;
            QVERIFY2(!overlap || boxes[i].slot != boxes[j].slot, qPrintable(script));
        }
        QCOMPARE(boxes[0].startFrame, 9);  QCOMPARE(boxes[0].endFrame, 15);
        QCOMPARE(boxes[1].startFrame, 12); QCOMPARE(boxes[1].endFrame, 16); QCOMPARE(boxes[1].joint, QString("FOOT_R"));
        QCOMPARE(boxes[2].startFrame, 12); QCOMPARE(boxes[2].endFrame, 15); QCOMPARE(boxes[2].joint, QString("FOOT_L"));
        // Other commands keep their frames.
        QVERIFY(GenoAsm::parse(script).timingProblems().isEmpty());
        QVERIFY2(script.contains("wait_until 4\ncmd_var idx=0 value=1"), qPrintable(script));
        QVERIFY2(script.contains("wait_until 26\ncmd_var idx=0 value=0\nwait_until 36\niasa"), qPrintable(script));
        // gameplay.json windows and roles equal the script, and the checks find nothing.
        const auto json = QJsonDocument::fromJson(diskBytes(d.path(), "gameplay.json")).object();
        const auto move = json["moves"].toArray()[1].toObject();
        QCOMPARE(QJsonDocument(move["windows"].toArray()).toJson(QJsonDocument::Compact), QByteArray("[[9,6],[12,4],[12,3]]"));
        QCOMPARE(QJsonDocument(move["design"].toObject()["window_roles"].toArray()).toJson(QJsonDocument::Compact),
                 QByteArray("[\"FOOT_R\",\"FOOT_R\",\"FOOT_L\"]"));
        QVERIFY2(data.timingProblems("dair").isEmpty(), qPrintable(data.timingProblems("dair").join("\n")));
    }
    void timingCheckNamesAScriptThatDisagreesWithGameplay() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        QJsonObject gameplay = QJsonDocument::fromJson(wbtest::kGameplay).object();
        QJsonArray moves = gameplay["moves"].toArray();
        QJsonObject dairMove = moves[1].toObject();
        dairMove["windows"] = QJsonArray{QJsonArray{12, 4}, QJsonArray{9, 6}};  // what the buggy write declared
        moves[1] = dairMove; gameplay["moves"] = moves;
        wbtest::put(d.path(), "gameplay.json", QJsonDocument(gameplay).toJson());
        wbtest::put(d.path(), "moves/dair.genoasm",
            "wait_until 12\nhitbox slot=0 joint=@A@ damage=1\nwait 4\nclear_hitboxes\nwait_until 9\n"
            "hitbox slot=0 joint=@A@ damage=1\nwait 6\nclear_hitboxes\n");
        FileStore fs(d.path()); GenoData data(fs); QVERIFY(data.reload().isEmpty());
        const QString all = data.timingProblems("dair").join("\n");
        QVERIFY2(all.contains("wait_until 9 comes after frame 16"), qPrintable(all));
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
