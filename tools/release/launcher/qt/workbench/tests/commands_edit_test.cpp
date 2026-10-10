#include "../testfixture.h"
#include "commands.h"
#include "analysis.h"
#include <QCoreApplication>
#include <QElapsedTimer>
#include <cmath>
#include "session.h"
#include <QTemporaryDir>
#include <QtTest>
using namespace wb;

static QString prepareRig(const QString &dir) {
    wbtest::makeSynthFighter(dir);
    auto plan = QJsonDocument::fromJson(wbtest::kPlan).object();
    auto roles = plan["roles"].toObject(); roles["chest"] = QJsonArray{1}; plan["roles"] = roles;
    wbtest::put(dir, "package/files/plan.json", QJsonDocument(plan).toJson());
    return dir;
}

class SamplingEngine : public wbtest::FakeEngine {
public:
    QMap<int, QJsonObject> frames;
    QJsonObject call(const QString &fn, const QJsonObject &args, QString *err) override {
        if (fn == "frame" && frames.contains(args["frame"].toInt()) && failWith.isEmpty()) {
            calls.append({fn, args}); if (err) err->clear(); return frames.value(args["frame"].toInt());
        }
        return FakeEngine::call(fn, args, err);
    }
};

struct Rig {
    QTemporaryDir d; SamplingEngine eng; Session s;
    Rig() : d(), s(prepareRig(d.path()), &eng) {
        s.agentProposals = true; s.data().reload();
        registerViewCommands(s); registerRowCommands(s); registerHitboxCommands(s); registerClipCommands(s);
    }
    QJsonObject call(const QString &n, QJsonObject a = {}, const QString &who = "human") { CommandContext c{s, who}; return s.registry().call(n, a, c); }
};

static QJsonObject frameJson(int f, double footY) {
    return QJsonObject{{"row", "dair"}, {"frame", f}, {"motion", 70},
        {"bones", QJsonArray{QJsonObject{{"joint", 1}, {"parent", 0}, {"pos", QJsonObject{{"x", 0}, {"y", 5}, {"z", 0}}}},
                              QJsonObject{{"joint", 2}, {"parent", 1}, {"pos", QJsonObject{{"x", 1}, {"y", 5}, {"z", 0}}}},
                              QJsonObject{{"joint", 3}, {"parent", 1}, {"pos", QJsonObject{{"x", 0}, {"y", footY}, {"z", 0}}}}}},
        {"hitboxes", QJsonArray{}}, {"hurtboxes", QJsonArray{}},
        {"ecb", QJsonObject{{"bottom", QJsonObject{{"x", 0}, {"y", 0}}}, {"top", QJsonObject{{"x", 0}, {"y", 5}}}}},
        {"floorY", 0}, {"lowestY", footY}};
}


static QByteArray bytesOnDisk(const QString &dir, const QString &rel) {
    QFile file(QDir(dir).filePath(rel));
    if (!file.open(QIODevice::ReadOnly)) return {};
    return file.readAll();
}

static QString configureImport(Rig &r, const QStringList &argv) {
    auto project = QJsonDocument::fromJson(wbtest::kProject).object();
    project["import_clip"] = QJsonArray::fromStringList(argv);
    wbtest::put(r.d.path(), "workbench.json", QJsonDocument(project).toJson());
    return r.s.data().reload();
}

static QStringList importHelper(const QString &mode = "ok") {
    return {QString::fromUtf8(WB_IMPORT_HELPER), mode, "{source}", "{target}"};
}

class EditCmdTest : public QObject {
    Q_OBJECT
private slots:
    void listRowsAndHitboxes() {
        Rig r;
        QCOMPARE(r.call("list_rows")["result"].toObject()["rows"].toArray().size(), 2);
        QCOMPARE(r.call("list_hitboxes", {{"row", "dair"}})["result"].toObject()["hitboxes"].toArray().size(), 2);
    }
    void editHitboxWritesSourceAndReloads() {
        Rig r;
        QJsonObject res = r.call("edit_hitbox", {{"row", "dair"}, {"ordinal", 0}, {"bone", "HAND_R"}});
        QVERIFY(res["ok"].toBool());
        QVERIFY(r.s.files().read("moves/dair.genoasm").contains("@HAND_R@"));
        QCOMPARE(r.s.data().hitboxes("dair")[0].joint, QString("HAND_R"));
    }
    void editHitboxUnknownBoneRejected() {
        Rig r;
        QJsonObject res = r.call("edit_hitbox", {{"row", "dair"}, {"ordinal", 0}, {"bone", "TAIL"}});
        QVERIFY(!res["ok"].toBool()); QVERIFY(res["error"].toString().contains("unknown bone"));
    }
    void editHitboxAgentProposalDoesNotWrite() {
        Rig r; QByteArray old = r.s.files().read("moves/dair.genoasm");
        QJsonObject res = r.call("edit_hitbox", {{"row", "dair"}, {"ordinal", 0}, {"bone", "HAND_R"}, {"propose", true}}, "agent");
        QVERIFY(res["result"].toObject()["proposed"].toBool());
        QCOMPARE(r.s.files().read("moves/dair.genoasm"), old);
    }
    void listHitboxRolesFollowsThePlanInGroupOrder() {
        Rig r;
        const auto roles = r.call("list_hitbox_roles")["result"].toObject()["roles"].toArray();
        QStringList names, groups;
        for (const auto &v : roles) { names << v.toObject()["name"].toString(); groups << v.toObject()["group"].toString(); }
        QCOMPARE(names, QStringList({"CHEST", "HAND_R", "FOOT_L"}));
        QCOMPARE(groups, QStringList({"body", "arms", "legs"}));
        QVERIFY(r.call("list_hitbox_roles")["result"].toObject()["has_plan"].toBool());
    }
    void addHitboxWritesSourceAndDeleteRestoresIt() {
        Rig r; const QByteArray old = r.s.files().read("moves/dair.genoasm");
        QJsonObject res = r.call("add_hitbox", {{"row", "dair"}, {"frame", 6}, {"bone", "HAND_R"}});
        QVERIFY(res["ok"].toBool());
        QCOMPARE(res["result"].toObject()["ordinal"].toInt(), 1);
        QCOMPARE(r.s.data().hitboxes("dair").size(), 3);
        QCOMPARE(r.s.data().hitboxes("dair")[1].joint, QString("HAND_R"));
        QCOMPARE(r.s.data().hitboxes("dair")[1].slot, 1);
        res = r.call("delete_hitbox", {{"row", "dair"}, {"ordinal", 1}});
        QVERIFY(res["ok"].toBool());
        QCOMPARE(r.s.files().read("moves/dair.genoasm"), old);
        QCOMPARE(r.s.data().hitboxes("dair").size(), 2);
    }
    void addHitboxDefaultsToAResolvableRole() {
        Rig r;
        QVERIFY(r.call("add_hitbox", {{"row", "jab1"}, {"frame", 10}})["ok"].toBool());
        QCOMPARE(r.s.data().hitboxes("jab1").last().joint, QString("CHEST"));  // no FLOOR in this plan: the first role
    }
    void addHitboxRejectsUnknownBoneRowAndSlotOverflow() {
        Rig r; const QByteArray old = r.s.files().read("moves/dair.genoasm");
        QVERIFY(r.call("add_hitbox", {{"row", "dair"}, {"frame", 6}, {"bone", "TAIL"}})["error"].toString().contains("unknown bone"));
        QVERIFY(!r.call("add_hitbox", {{"row", "nope"}, {"frame", 6}})["ok"].toBool());
        QVERIFY(!r.call("add_hitbox", {{"row", "dair"}})["ok"].toBool());
        QVERIFY(!r.call("delete_hitbox", {{"row", "dair"}, {"ordinal", 9}})["ok"].toBool());
        QCOMPARE(r.s.files().read("moves/dair.genoasm"), old);
    }
    void addAndDeleteHitboxAsAgentAreProposals() {
        Rig r; const QByteArray old = r.s.files().read("moves/dair.genoasm");
        auto res = r.call("add_hitbox", {{"row", "dair"}, {"frame", 6}, {"bone", "HAND_R"}}, "agent");
        QVERIFY(res["result"].toObject()["proposed"].toBool());
        res = r.call("delete_hitbox", {{"row", "dair"}, {"ordinal", 0}}, "agent");
        QVERIFY(res["result"].toObject()["proposed"].toBool());
        QCOMPARE(r.s.files().read("moves/dair.genoasm"), old);
    }
    void frameCommandsHitEngine() {
        Rig r; r.eng.canned["frame"] = frameJson(6, 0);
        QVERIFY(r.call("load_row", {{"row", "dair"}})["ok"].toBool());
        QJsonObject res = r.call("set_frame", {{"frame", 6}});
        QCOMPARE(res["result"].toObject()["frame"].toInt(), 6);
        QCOMPARE(r.eng.calls.last().first, QString("frame"));
        QCOMPARE(r.eng.calls.last().second["motion"].toInt(), 70);
    }
    void engineCommandsErrorWithoutEngine() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); Session s(d.path(), nullptr); s.data().reload();
        registerViewCommands(s); registerRowCommands(s);
        CommandContext c{s};
        QJsonObject res = s.registry().call("render_view", {}, c);
        QVERIFY(!res["ok"].toBool()); QVERIFY(res["error"].toString().contains("engine not running"));
    }
    void engineErrorPropagates() {
        Rig r; r.eng.failWith = "engine connection lost";
        QJsonObject res = r.call("frame_info");
        QVERIFY(!res["ok"].toBool()); QVERIFY(res["error"].toString().contains("lost"));
    }
    void suggestBoneUsesEngineSamples() {
        Rig r;
        // the same canned reply is used for both samples; speed 0, foot is 5 below chest, hand is 1 away: suggests FOOT_L
        r.eng.canned["frame"] = frameJson(6, 0);
        QJsonObject res = r.call("suggest_hitbox_bone", {{"row", "dair"}, {"ordinal", 0}});
        QVERIFY2(res["ok"].toBool(), qPrintable(res["error"].toString()));
        QCOMPARE(res["result"].toObject()["suggested"].toString(), QString("FOOT_L"));
    }
    void assignClipAndListClips() {
        Rig r;
        QCOMPARE(r.call("list_clips")["result"].toObject()["clips"].toArray().size(), 3);
        QVERIFY(r.call("assign_clip", {{"row", "dair"}, {"clip", "SYN_ATC_009"}})["ok"].toBool());
        QVERIFY(r.s.files().read("gameplay.json").contains("SYN_ATC_009"));
        QCOMPARE(r.s.data().rows()[1].clip, QString("SYN_ATC_009"));
    }
    void importClipRunsConfiguredTool() {
        Rig r;
        QJsonObject res = r.call("import_clip", {{"source", "x.anim"}, {"target_name", "SYN_IMPORTED"}});
        QVERIFY2(res["ok"].toBool(), qPrintable(res["error"].toString()));
        QCOMPARE(res["result"].toObject()["clip"].toString(), QString("SYN_IMPORTED"));
    }
    void importClipBadOutputIsError() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        wbtest::put(d.path(), "workbench.json", QString(wbtest::kProject).replace("import sys,json; print(json.dumps({'clip': 'SYN_IMPORTED', 'frames': 20}))", "print('not json')").toUtf8());
        wbtest::FakeEngine eng; Session s(d.path(), &eng); s.data().reload(); registerClipCommands(s);
        CommandContext c{s};
        QJsonObject res = s.registry().call("import_clip", {{"source", "x"}, {"target_name", "y"}}, c);
        QVERIFY(!res["ok"].toBool()); QVERIFY(res["error"].toString().contains("not JSON"));
    }
    void runChecksStaticWithoutEngine() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        // make both rows share a clip
        QString g = wbtest::kGameplay; g.replace("SYN_ATC_007", "SYN_ATC_002");
        wbtest::put(d.path(), "gameplay.json", g.toUtf8());
        Session s(d.path(), nullptr); s.data().reload(); registerHitboxCommands(s);
        CommandContext c{s};
        QJsonObject res = s.registry().call("run_checks", {}, c)["result"].toObject();
        QVERIFY(!res["engine"].toBool());
        QCOMPARE(res["problems"].toArray()[0].toObject()["kind"].toString(), QString("duplicate_clip"));
    }
    void allCommandFamiliesAreWired() {
        QTemporaryDir d; prepareRig(d.path()); Session s(d.path(), nullptr);
        QVERIFY(s.data().reload().isEmpty()); registerAllCommands(s);
        CommandContext c{s};
        for (const char *name : {"open_fighter", "engine_status", "engine_restart",
                "set_camera", "set_overlays", "render_view", "list_rows", "load_row",
                "set_frame", "play", "frame_info", "list_hitboxes", "edit_hitbox", "add_hitbox", "delete_hitbox",
                "list_hitbox_roles",
                "suggest_hitbox_bone", "list_clips", "preview_clip", "assign_clip",
                "import_clip", "run_checks"})
            QVERIFY2(s.registry().has(name), name);
        QCOMPARE(s.registry().call("engine_status", {}, c)["result"].toObject()["status"].toString(),
                 QString("stopped"));
        QCOMPARE(s.registry().call("list_rows", {}, c)["result"].toObject()["rows"].toArray().size(), 2);
    }

    void viewStateMergesAndReachesRenderer() {
        Rig r;
        QVERIFY(r.call("set_camera", {{"preset", "side"}, {"yaw", 15}, {"distance", 8}})["ok"].toBool());
        QVERIFY(r.call("set_camera", {{"pitch", -12}})["ok"].toBool());
        QCOMPARE(r.s.camera["yaw"].toInt(), 15);
        QCOMPARE(r.s.camera["preset"].toString(), QString("side"));
        QVERIFY(r.call("set_overlays", {{"bones", true}, {"floor", true}})["ok"].toBool());
        QVERIFY(r.call("set_overlays", {{"bones", false}})["ok"].toBool());
        QVERIFY(r.s.overlays["floor"].toBool()); QVERIFY(!r.s.overlays["bones"].toBool());
        r.eng.canned["render"] = {{"path", "synthetic-view.png"}};
        auto res = r.call("render_view", {{"w", 320}, {"h", 240}});
        QVERIFY(res["ok"].toBool());
        QCOMPARE(res["result"].toObject()["path"].toString(), QString("synthetic-view.png"));
        QCOMPARE(r.eng.calls.last().first, QString("render"));
        QCOMPARE(r.eng.calls.last().second["w"].toInt(), 320);
        QCOMPARE(r.eng.calls.last().second["camera"].toObject()["pitch"].toInt(), -12);
        QVERIFY(r.eng.calls.last().second["overlays"].toObject()["floor"].toBool());
    }

    void openFighterReloadsOnlyTheCurrentProject() {
        Rig r;
        QByteArray gameplay = wbtest::kGameplay; gameplay.replace("\"iasa\": 36", "\"iasa\": 40");
        wbtest::put(r.d.path(), "gameplay.json", gameplay);
        auto res = r.call("open_fighter", {{"path", r.d.path()}});
        QVERIFY(res["ok"].toBool());
        QCOMPARE(res["result"].toObject()["rows"].toInt(), 2);
        QCOMPARE(r.s.data().rows()[1].iasa, 40);
        QTemporaryDir other; wbtest::makeSynthFighter(other.path());
        res = r.call("open_fighter", {{"path", other.path()}});
        QVERIFY(!res["ok"].toBool());
        QVERIFY(res["error"].toString().contains("new session"));
        QCOMPARE(r.s.files().root(), QDir(r.d.path()).absolutePath());
    }

    void engineRestartReportsFailure() {
        Rig r;
        QVERIFY(r.call("engine_restart")["ok"].toBool());
        QCOMPARE(r.call("engine_status")["result"].toObject()["status"].toString(), QString("ready"));
        r.eng.failWith = "engine restart failed";
        auto res = r.call("engine_restart");
        QVERIFY(!res["ok"].toBool()); QVERIFY(res["error"].toString().contains("restart failed"));
    }

    void offlineEngineCommands_data() {
        QTest::addColumn<QString>("name"); QTest::addColumn<QJsonObject>("args");
        QTest::newRow("restart") << QString("engine_restart") << QJsonObject{};
        QTest::newRow("render") << QString("render_view") << QJsonObject{};
        QTest::newRow("row") << QString("load_row") << QJsonObject{{"row", "dair"}};
        QTest::newRow("frame") << QString("set_frame") << QJsonObject{{"frame", 6}};
        QTest::newRow("play") << QString("play") << QJsonObject{{"frames", 3}};
        QTest::newRow("info") << QString("frame_info") << QJsonObject{};
        QTest::newRow("suggest") << QString("suggest_hitbox_bone") << QJsonObject{{"row", "dair"}, {"ordinal", 0}};
        QTest::newRow("preview") << QString("preview_clip") << QJsonObject{{"clip", "SYN_ATC_007"}};
    }
    void offlineEngineCommands() {
        QFETCH(QString, name); QFETCH(QJsonObject, args);
        QTemporaryDir d; prepareRig(d.path()); Session s(d.path(), nullptr);
        QVERIFY(s.data().reload().isEmpty()); registerAllCommands(s); CommandContext c{s};
        auto res = s.registry().call(name, args, c);
        QVERIFY(!res["ok"].toBool()); QVERIFY(res["error"].toString().contains("engine not running"));
    }

    void schemasRejectBadTypesBeforeSideEffects_data() {
        QTest::addColumn<QString>("name"); QTest::addColumn<QJsonObject>("args");
        QTest::newRow("damage") << QString("edit_hitbox") << QJsonObject{{"row", "dair"}, {"ordinal", 0}, {"damage", "x"}};
        QTest::newRow("ordinal") << QString("edit_hitbox") << QJsonObject{{"row", "dair"}, {"ordinal", 0.5}};
        QTest::newRow("bone") << QString("edit_hitbox") << QJsonObject{{"row", "dair"}, {"ordinal", 0}, {"bone", false}};
        QTest::newRow("frame") << QString("edit_hitbox") << QJsonObject{{"row", "dair"}, {"ordinal", 0}, {"start_frame", 1.5}};
        QTest::newRow("proposal") << QString("assign_clip") << QJsonObject{{"row", "dair"}, {"clip", "SYN_ATC_009"}, {"propose", "true"}};
        QTest::newRow("camera") << QString("set_camera") << QJsonObject{{"preset", "unknown"}};
        QTest::newRow("overlays") << QString("set_overlays") << QJsonObject{{"hitboxes", 1}};
        QTest::newRow("import") << QString("import_clip") << QJsonObject{{"source", "x"}};
    }
    void schemasRejectBadTypesBeforeSideEffects() {
        QFETCH(QString, name); QFETCH(QJsonObject, args); Rig r;
        QVERIFY(!r.call(name, args)["ok"].toBool());
        QCOMPARE(bytesOnDisk(r.d.path(), "moves/dair.genoasm"), QByteArray(wbtest::kDair));
        QVERIFY(r.s.history().entries().isEmpty()); QVERIFY(r.eng.calls.isEmpty());
    }

    void frameRequiresLoadedRowAndFailedLoadKeepsSelection() {
        Rig r; auto res = r.call("set_frame", {{"frame", 6}});
        QVERIFY(!res["ok"].toBool()); QVERIFY(res["error"].toString().contains("load_row first"));
        QVERIFY(r.eng.calls.isEmpty());
        QVERIFY(r.call("load_row", {{"row", "dair"}})["ok"].toBool());
        r.eng.failWith = "connection lost";
        QVERIFY(!r.call("load_row", {{"row", "jab1"}})["ok"].toBool());
        QCOMPARE(r.s.currentRow, QString("dair"));
    }

    void playUsesBoundedChunksAndRejectsInvalidRanges() {
        Rig r; r.eng.canned["step"] = frameJson(13, 0);
        QVERIFY(r.call("load_row", {{"row", "dair"}})["ok"].toBool()); r.eng.calls.clear();
        auto res = r.call("play", {{"frames", 7}, {"step", 3}});
        QVERIFY(res["ok"].toBool()); QCOMPARE(res["result"].toObject()["frame"].toInt(), 13);
        QCOMPARE(r.eng.calls.size(), 3);
        QCOMPARE(r.eng.calls[0].second["n"].toInt(), 3);
        QCOMPARE(r.eng.calls[1].second["n"].toInt(), 3);
        QCOMPARE(r.eng.calls[2].second["n"].toInt(), 1);
        r.eng.calls.clear();
        QVERIFY(!r.call("play", {{"frames", 7}, {"step", 0}})["ok"].toBool());
        QVERIFY(!r.call("play", {{"frames", -1}})["ok"].toBool());
        QVERIFY(!r.call("set_frame", {{"frame", 1e20}})["ok"].toBool());
        QVERIFY(r.eng.calls.isEmpty());
        r.eng.canned["frame_info"] = frameJson(13, 0);
        QVERIFY(r.call("play", {{"frames", 0}})["ok"].toBool());
        QCOMPARE(r.eng.calls.last().first, QString("frame_info"));
    }

    void rowsWithoutMotionsAndUnknownRowsAreErrors() {
        Rig r;
        QVERIFY(!r.call("list_hitboxes", {{"row", "missing"}})["ok"].toBool());
        QVERIFY(!r.call("run_checks", {{"row", "missing"}})["ok"].toBool());
        QByteArray gameplay = wbtest::kGameplay; gameplay.replace("[70]", "[]");
        wbtest::put(r.d.path(), "gameplay.json", gameplay); QVERIFY(r.s.data().reload().isEmpty());
        auto res = r.call("load_row", {{"row", "dair"}});
        QVERIFY(!res["ok"].toBool()); QVERIFY(res["error"].toString().contains("no motion"));
        QVERIFY(r.eng.calls.isEmpty());
    }

    void editHitboxAgentDefaultsToProposalEvenWithProposeFalse() {
        Rig r;
        auto res = r.call("edit_hitbox", {{"row", "dair"}, {"ordinal", 0}, {"damage", 16}, {"propose", false}}, "agent");
        QVERIFY(res["ok"].toBool()); QVERIFY(res["result"].toObject()["proposed"].toBool());
        QCOMPARE(bytesOnDisk(r.d.path(), "moves/dair.genoasm"), QByteArray(wbtest::kDair));
        QCOMPARE(r.s.data().hitboxes("dair")[0].damage, 14.0);
        QCOMPARE(r.s.history().entries().last().state, QString("proposed"));
        QVERIFY(QFile::exists(r.s.historyPath()));
    }

    void editHitboxChangesAllFieldsAndFrames() {
        Rig r;
        auto res = r.call("edit_hitbox", {{"row", "jab1"}, {"ordinal", 0}, {"bone", "@FOOT_L@"},
            {"damage", 5}, {"size", 4.2}, {"x", 1}, {"y", 2}, {"z", 3}, {"angle", 45},
            {"kbg", 70}, {"fkb", 10}, {"bkb", 12}, {"start_frame", 4}, {"end_frame", 6}});
        QVERIFY2(res["ok"].toBool(), qPrintable(res["error"].toString()));
        auto h = r.s.data().hitboxes("jab1").first();
        QCOMPARE(h.joint, QString("FOOT_L")); QCOMPARE(h.damage, 5.0); QCOMPARE(h.size, 4.2);
        QCOMPARE(h.x, 1.0); QCOMPARE(h.y, 2.0); QCOMPARE(h.z, 3.0); QCOMPARE(h.angle, 45);
        QCOMPARE(h.kbg, 70); QCOMPARE(h.fkb, 10); QCOMPARE(h.bkb, 12);
        QCOMPARE(h.startFrame, 4); QCOMPARE(h.endFrame, 6);
        QCOMPARE(r.s.history().entries().last().changes.size(), 1);
    }

    void malformedFrameEditsAndExternalChangesNeverWrite() {
        Rig r;
        const QByteArray unusual = "hitbox slot=0 joint=@FOOT_L@ damage=1\n";
        wbtest::put(r.d.path(), "moves/dair.genoasm", unusual); QVERIFY(r.s.data().reload().isEmpty());
        auto res = r.call("edit_hitbox", {{"row", "dair"}, {"ordinal", 0}, {"start_frame", 3}, {"end_frame", 4}});
        QVERIFY(!res["ok"].toBool()); QVERIFY(res["error"].toString().contains("frames not editable"));
        QCOMPARE(bytesOnDisk(r.d.path(), "moves/dair.genoasm"), unusual);
        wbtest::put(r.d.path(), "moves/dair.genoasm", "hand edit\n");
        res = r.call("edit_hitbox", {{"row", "dair"}, {"ordinal", 0}, {"damage", 5}});
        QVERIFY(!res["ok"].toBool()); QVERIFY(res["error"].toString().contains("changed externally"));
        QCOMPARE(bytesOnDisk(r.d.path(), "moves/dair.genoasm"), QByteArray("hand edit\n"));
        QVERIFY(r.s.history().entries().isEmpty());
    }

    void boneValidationDistinguishesMissingAndLoadedEmptyPlans() {
        Rig r;
        wbtest::put(r.d.path(), "package/files/plan.json", "{}"); QVERIFY(r.s.data().reload().isEmpty());
        auto res = r.call("edit_hitbox", {{"row", "dair"}, {"ordinal", 0}, {"bone", "TAIL"}});
        QVERIFY(!res["ok"].toBool()); QVERIFY(res["error"].toString().contains("unknown bone"));
        QVERIFY(QFile::remove(QDir(r.d.path()).filePath("package/files/plan.json")));
        QVERIFY(r.s.data().reload().isEmpty());
        QVERIFY(r.call("edit_hitbox", {{"row", "dair"}, {"ordinal", 0}, {"bone", "TAIL"}})["ok"].toBool());
        QCOMPARE(r.s.data().hitboxes("dair")[0].joint, QString("TAIL"));
    }

    void clipProposalPreservesGameplayAndFidelity() {
        Rig r; auto res = r.call("assign_clip", {{"row", "dair"}, {"clip", "SYN_ATC_009"}, {"crop_start", 4}}, "agent");
        QVERIFY(res["ok"].toBool()); QVERIFY(res["result"].toObject()["proposed"].toBool());
        QCOMPARE(bytesOnDisk(r.d.path(), "gameplay.json"), QByteArray(wbtest::kGameplay));
        QCOMPARE(bytesOnDisk(r.d.path(), "fidelity.json"), QByteArray(wbtest::kFidelity));
        QCOMPARE(r.s.history().entries().last().changes.size(), 2);
        QCOMPARE(r.s.data().rows()[1].clip, QString("SYN_ATC_007"));
    }

    void previewClipValidatesAndUsesRequestedFrame() {
        Rig r; r.eng.canned["clip"] = frameJson(8, 0);
        auto res = r.call("preview_clip", {{"clip", "SYN_ATC_007"}, {"frame", 8}});
        QVERIFY(res["ok"].toBool()); QCOMPARE(res["result"].toObject()["frame"].toInt(), 8);
        QCOMPARE(r.eng.calls.last().first, QString("clip"));
        QCOMPARE(r.eng.calls.last().second["clip"].toString(), QString("SYN_ATC_007"));
        QCOMPARE(r.eng.calls.last().second["frame"].toInt(), 8);
        QVERIFY(!r.call("preview_clip", {{"clip", "missing"}})["ok"].toBool());
        QVERIFY(!r.call("assign_clip", {{"row", "dair"}, {"clip", "missing"}})["ok"].toBool());
        QVERIFY(r.s.history().entries().isEmpty());
    }

    void importClipNotConfiguredIsAnError() {
        Rig r; QVERIFY(configureImport(r, {}).isEmpty());
        auto res = r.call("import_clip", {{"source", "x"}, {"target_name", "y"}});
        QVERIFY(!res["ok"].toBool()); QVERIFY(res["error"].toString().contains("import_clip not configured"));
    }

    void importClipFailuresLeaveSourceAlone_data() {
        QTest::addColumn<QString>("mode"); QTest::addColumn<QString>("error");
        QTest::newRow("non-json") << QString("not-json") << QString("not JSON");
        QTest::newRow("exit") << QString("nonzero") << QString("exit");
        QTest::newRow("bad-shape") << QString("bad-shape") << QString("frames");
        QTest::newRow("built-output") << QString("built") << QString("built output");
        QTest::newRow("deleted-source") << QString("delete") << QString("deleted");
    }
    void importClipFailuresLeaveSourceAlone() {
        QFETCH(QString, mode); QFETCH(QString, error); Rig r;
        QVERIFY(configureImport(r, importHelper(mode)).isEmpty());
        const auto oldPlan = bytesOnDisk(r.d.path(), "package/files/plan.json");
        auto res = r.call("import_clip", {{"source", "x"}, {"target_name", "SYN_IMPORTED"}});
        QVERIFY(!res["ok"].toBool()); QVERIFY2(res["error"].toString().contains(error), qPrintable(res["error"].toString()));
        QVERIFY(!QFile::exists(QDir(r.d.path()).filePath("bank/SYN_IMPORTED.anim")));
        QCOMPARE(bytesOnDisk(r.d.path(), "moves/dair.genoasm"), QByteArray(wbtest::kDair));
        QCOMPARE(bytesOnDisk(r.d.path(), "package/files/plan.json"), oldPlan);
        QVERIFY(r.s.history().entries().isEmpty());
    }

    void importClipUsesArgvTemplatesAndIsUndoable() {
        Rig r; wbtest::put(r.d.path(), "bank/SYN_IMPORTED.anim", "old clip\n");
        QVERIFY(configureImport(r, importHelper()).isEmpty());
        auto res = r.call("import_clip", {{"source", "source clip{target}.anim"}, {"target_name", "SYN_IMPORTED"}});
        QVERIFY2(res["ok"].toBool(), qPrintable(res["error"].toString()));
        auto result = res["result"].toObject();
        QCOMPARE(result["clip"].toString(), QString("SYN_IMPORTED"));
        QCOMPARE(result["frames"].toInt(), 20); QVERIFY(result["applied"].toBool());
        QCOMPARE(result["source"].toString(), QDir(r.d.path()).filePath("source clip{target}.anim"));
        QCOMPARE(bytesOnDisk(r.d.path(), "bank/SYN_IMPORTED.anim"), QByteArray("synthetic imported clip\n"));
        QCOMPARE(r.s.history().entries().last().command, QString("import_clip"));
        QVERIFY(r.s.history().entries().last().changes.size() >= 1);
        QString error; QVERIFY2(r.s.history().undo(r.s.files(), &error), qPrintable(error));
        QCOMPARE(bytesOnDisk(r.d.path(), "bank/SYN_IMPORTED.anim"), QByteArray("old clip\n"));
    }

    void importedSourceCanBeProposedAndAccepted() {
        Rig r; QVERIFY(configureImport(r, importHelper()).isEmpty());
        auto res = r.call("import_clip", {{"source", "x"}, {"target_name", "SYN_IMPORTED"}}, "agent");
        QVERIFY2(res["ok"].toBool(), qPrintable(res["error"].toString()));
        auto result = res["result"].toObject(); QVERIFY(result["proposed"].toBool());
        QVERIFY(!QFile::exists(QDir(r.d.path()).filePath("bank/SYN_IMPORTED.anim")));
        const auto &entry = r.s.history().entries().last();
        QCOMPARE(entry.state, QString("proposed"));
        QCOMPARE(entry.changes.first().path, QString("bank/SYN_IMPORTED.anim"));
        QString error; QVERIFY2(r.s.history().accept(result["entry"].toInt(), r.s.files(), &error), qPrintable(error));
        QCOMPARE(bytesOnDisk(r.d.path(), "bank/SYN_IMPORTED.anim"), QByteArray("synthetic imported clip\n"));
    }

    void explicitHumanImportProposalAlsoLeavesSourceAlone() {
        Rig r; QVERIFY(configureImport(r, importHelper()).isEmpty());
        auto res = r.call("import_clip", {{"source", "x"}, {"target_name", "SYN_IMPORTED"}, {"propose", true}});
        QVERIFY2(res["ok"].toBool(), qPrintable(res["error"].toString()));
        QVERIFY(res["result"].toObject()["proposed"].toBool());
        QVERIFY(!QFile::exists(QDir(r.d.path()).filePath("bank/SYN_IMPORTED.anim")));
    }

    void importClipRefusesExternalEditsAndMissingProgram() {
        Rig r; QVERIFY(configureImport(r, importHelper()).isEmpty());
        wbtest::put(r.d.path(), "moves/dair.genoasm", "hand edit\n");
        auto res = r.call("import_clip", {{"source", "x"}, {"target_name", "SYN_IMPORTED"}});
        QVERIFY(!res["ok"].toBool()); QVERIFY(res["error"].toString().contains("changed externally"));
        QCOMPARE(bytesOnDisk(r.d.path(), "moves/dair.genoasm"), QByteArray("hand edit\n"));
        QVERIFY(!QFile::exists(QDir(r.d.path()).filePath("bank/SYN_IMPORTED.anim")));
        QVERIFY(configureImport(r, {"./missing-import-program"}).isEmpty());
        res = r.call("import_clip", {{"source", "x"}, {"target_name", "SYN_IMPORTED"}});
        QVERIFY(!res["ok"].toBool()); QVERIFY(res["error"].toString().contains("start"));
        QVERIFY(r.s.history().entries().isEmpty());
    }

    void samplesMeasureTorsoDistanceAndPreviousFrameSpeed() {
        Rig r; r.eng.frames[5] = frameJson(5, 4); r.eng.frames[6] = frameJson(6, 0);
        QString error;
        auto samples = sampleBones(r.eng, r.s.data(), r.s.data().rows()[1], 6, &error);
        QVERIFY2(error.isEmpty(), qPrintable(error));
        bool foot = false, hand = false;
        for (const auto &sample : samples) {
            if (sample.role == "FOOT_L") {
                foot = true; QCOMPARE(sample.displacement, 5.0); QCOMPARE(sample.speed, 4.0);
            }
            if (sample.role == "HAND_R") {
                hand = true; QCOMPARE(sample.displacement, 1.0); QCOMPARE(sample.speed, 0.0);
            }
        }
        QVERIFY(foot); QVERIFY(hand);
        QCOMPARE(r.eng.calls[0].first, QString("row"));
        QCOMPARE(r.eng.calls[0].second["motion"].toInt(), 70);
        QVector<int> frames;
        for (const auto &call : r.eng.calls) if (call.first == "frame") frames.append(call.second["frame"].toInt());
        QCOMPARE(frames, QVector<int>({5, 6}));
    }

    void frameZeroNeverSamplesNegativeFramesAndMissingTorsoIsAnError() {
        Rig r; r.eng.canned["frame"] = frameJson(0, 0); QString error;
        auto samples = sampleBones(r.eng, r.s.data(), r.s.data().rows()[1], 0, &error);
        QVERIFY2(error.isEmpty(), qPrintable(error)); QVERIFY(!samples.isEmpty());
        for (const auto &call : r.eng.calls)
            if (call.first == "frame") QCOMPARE(call.second["frame"].toInt(), 1);   // the engine numbers frames from 1; frame 0 is clamped up
        wbtest::put(r.d.path(), "package/files/plan.json", wbtest::kPlan);
        QVERIFY(r.s.data().reload().isEmpty());
        QVERIFY(sampleBones(r.eng, r.s.data(), r.s.data().rows()[1], 6, &error).isEmpty());
        QVERIFY(error.contains("CHEST"));
    }

    void runChecksUsesEachHitboxActiveFrame() {
        Rig r;
        r.eng.frames[5] = frameJson(5, 0); r.eng.frames[6] = frameJson(6, 0);
        auto later = frameJson(9, 5);
        auto bones = later["bones"].toArray(); auto hand = bones[1].toObject();
        hand["pos"] = QJsonObject{{"x", 10}, {"y", 5}, {"z", 0}}; bones[1] = hand; later["bones"] = bones;
        r.eng.frames[8] = later; r.eng.frames[9] = later;
        auto res = r.call("run_checks", {{"row", "dair"}});
        QVERIFY2(res["ok"].toBool(), qPrintable(res["error"].toString()));
        auto result = res["result"].toObject(); QVERIFY(result["engine"].toBool());
        auto problems = result["problems"].toArray();
        QCOMPARE(problems.size(), 1); QCOMPARE(problems[0].toObject()["kind"].toString(), QString("wrong_limb"));
        QCOMPARE(problems[0].toObject()["ordinal"].toInt(), 1);
    }

    void staticChecksIncludeGroundFlagsAndCompareClipsAcrossRowFilter() {
        QTemporaryDir d; prepareRig(d.path());
        QByteArray gameplay = wbtest::kGameplay; gameplay.replace("SYN_ATC_007", "SYN_ATC_002");
        wbtest::put(d.path(), "gameplay.json", gameplay); wbtest::put(d.path(), "moves/dair.genoasm", "# no hitboxes\n");
        wbtest::put(d.path(), "ground_modes.json", R"JSON({"grounded_clips":["SYN_ATC_002"]})JSON");
        Session s(d.path(), nullptr); QVERIFY(s.data().reload().isEmpty()); registerAllCommands(s); CommandContext c{s};
        auto res = s.registry().call("run_checks", {{"row", "dair"}}, c);
        QVERIFY(res["ok"].toBool()); auto result = res["result"].toObject(); QVERIFY(!result["engine"].toBool());
        QStringList kinds;
        for (const auto &p : result["problems"].toArray()) {
            QCOMPARE(p.toObject()["row"].toString(), QString("dair")); kinds.append(p.toObject()["kind"].toString());
        }
        QCOMPARE(kinds, QStringList({"duplicate_clip", "grounded_clip_on_aerial", "swing_without_hitbox"}));
    }

    void analysisFailurePropagatesWithoutMisleadingProblems() {
        Rig r; r.eng.failWith = "engine connection lost";
        auto res = r.call("run_checks", {{"row", "dair"}});
        QVERIFY(!res["ok"].toBool()); QVERIFY(res["error"].toString().contains("lost"));
        QVERIFY(!res.contains("result"));
    }

    void diagnosticCommandsInvalidatePlaybackSelection_data() {
        QTest::addColumn<QString>("command"); QTest::addColumn<QJsonObject>("args");
        QTest::addColumn<bool>("fail");
        for (bool fail : {false, true}) {
            QTest::newRow(fail ? "checks-fail" : "checks") << QString("run_checks")
                << QJsonObject{{"row", "dair"}} << fail;
            QTest::newRow(fail ? "suggest-fail" : "suggest") << QString("suggest_hitbox_bone")
                << QJsonObject{{"row", "dair"}, {"ordinal", 0}} << fail;
            QTest::newRow(fail ? "preview-fail" : "preview") << QString("preview_clip")
                << QJsonObject{{"clip", "SYN_ATC_007"}} << fail;
        }
    }
    void diagnosticCommandsInvalidatePlaybackSelection() {
        QFETCH(QString, command); QFETCH(QJsonObject, args); QFETCH(bool, fail);
        Rig r; r.eng.canned["frame"] = frameJson(6, 0); r.eng.canned["clip"] = frameJson(6, 0);
        QVERIFY(r.call("load_row", {{"row", "jab1"}})["ok"].toBool());
        if (fail) r.eng.failWith = "engine connection lost";
        const auto res = r.call(command, args);
        QCOMPARE(res["ok"].toBool(), !fail);
        QVERIFY(r.s.currentRow.isEmpty());
        const auto calls = r.eng.calls.size();
        const auto play = r.call("play", {{"frames", 1}});
        QVERIFY(!play["ok"].toBool()); QVERIFY(play["error"].toString().contains("load_row first"));
        const auto seek = r.call("set_frame", {{"frame", 1}});
        QVERIFY(!seek["ok"].toBool()); QVERIFY(seek["error"].toString().contains("load_row first"));
        QCOMPARE(r.eng.calls.size(), calls);
    }

    void importProtectsWorkspaceRelativePlan() {
        Rig r;
        wbtest::put(r.d.path(), "generated/plan.json", wbtest::kPlan);
        auto project = QJsonDocument::fromJson(wbtest::kProject).object();
        project.remove("plan"); project["plan_abs"] = "generated/plan.json";
        project["import_clip"] = QJsonArray::fromStringList(importHelper("relative-plan"));
        wbtest::put(r.d.path(), "workbench.json", QJsonDocument(project).toJson());
        QVERIFY(r.s.data().reload().isEmpty());
        const auto res = r.call("import_clip", {{"source", "x"}, {"target_name", "SYN_IMPORTED"}});
        QVERIFY(!res["ok"].toBool()); QVERIFY(res["error"].toString().contains("built output"));
        QCOMPARE(bytesOnDisk(r.d.path(), "generated/plan.json"), QByteArray(wbtest::kPlan));
        QVERIFY(!QFile::exists(QDir(r.d.path()).filePath("bank/SYN_IMPORTED.anim")));
        QVERIFY(r.s.history().entries().isEmpty());
    }

    void importTimeoutLeavesSourceAndHistoryAlone() {
        Rig r; QVERIFY(configureImport(r, importHelper("timeout")).isEmpty());
        QElapsedTimer timer; timer.start();
        auto res = r.call("import_clip", {{"source", "x"}, {"target_name", "SYN_IMPORTED"}});
        QVERIFY(!res["ok"].toBool()); QVERIFY(res["error"].toString().contains("timed out"));
        QVERIFY2(timer.elapsed() < 40000, "import timeout exceeded its bounded cleanup window");
        QVERIFY(!QFile::exists(QDir(r.d.path()).filePath("bank/SYN_IMPORTED.anim")));
        QVERIFY(r.s.history().entries().isEmpty());
    }

};
QTEST_GUILESS_MAIN(EditCmdTest)
#include "commands_edit_test.moc"
