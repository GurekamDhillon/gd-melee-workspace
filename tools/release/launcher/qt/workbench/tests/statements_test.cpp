#include "../testfixture.h"
#include "commands.h"
#include "statement_model.h"
#include <QTemporaryDir>
#include <QtTest>

using namespace wb;
class StatementsTest : public QObject {
    Q_OBJECT
private slots:
    void aliasesAndEngineTime() {
        const auto a = StatementModel::parse("wait 0x8\nwait_until 3\nthrow_hitbox idx=1 damage=8 unk0=361 hit_x24=100 hit_x28=0 hit_x2C=30\nthrow_flag hit_idx=0\nbody_state state=invincible\n").statements();
        QCOMPARE(a.size(), 3);
        QCOMPARE(a[0].toObject()["kind"].toString(), QString("throw"));
        QCOMPARE(a[0].toObject()["frame"].toInt(), 8);
        QCOMPARE(a[0].toObject()["fields"].toObject()["angle"].toInt(), 361);
        QCOMPARE(a[1].toObject()["kind"].toString(), QString("throw_release"));
        QCOMPARE(a[2].toObject()["fields"].toObject()["state"].toInt(), 1);
    }
    void independentHurtWindowsAndGlobalReset() {
        const auto a = StatementModel::parse("wait 2\nbody_state state=1\nhurtbox_state bone=3 state=2\nwait 3\nhurtboxes_state state=0\nwait 2\nbody_state state=0\n").hurtWindows();
        QCOMPARE(a.size(), 2);
        QCOMPARE(a[0].toObject()["kind"].toString(), QString("body_state"));
        QCOMPARE(a[0].toObject()["start_frame"].toInt(), 2);
        QCOMPARE(a[0].toObject()["end_frame"].toInt(), 7);
        QCOMPARE(a[1].toObject()["end_frame"].toInt(), 5);
    }
    void hurtWindowRoleIdentityUsesResolvedJoint() {
        QTemporaryDir d;wbtest::makeSynthFighter(d.path());
        wbtest::put(d.path(),"package/files/plan.json",QByteArray(wbtest::kPlan).replace("\"hand.R\": [2]","\"hand.R\": [2], \"lower_arm.R\": [2]"));
        wbtest::put(d.path(),"moves/jab1.genoasm","wait 2\nhurtbox_state bone=@HAND_R@ state=2\nwait 3\nhurtbox_state bone=2 state=0\nhurtbox_state bone=2 state=1\nwait 2\nhurtbox_state bone=@ARM_R@ state=0\n");
        Session s(d.path(),nullptr);QVERIFY(s.data().reload().isEmpty());const auto a=s.data().hurtWindows("jab1");
        QCOMPARE(a.size(),2);QCOMPARE(a[0].toObject()["bone"].toString(),QString("@HAND_R@"));
        QCOMPARE(a[0].toObject()["bone_identity"].toString(),QString("2"));
        QCOMPARE(a[1].toObject()["bone_identity"].toString(),QString("2"));
        QCOMPARE(a[0].toObject()["end_frame"].toInt(),5);QCOMPARE(a[1].toObject()["end_frame"].toInt(),7);
    }
    void malformedRawNeverInventsNormalReset() {
        const auto m=StatementModel::parse("body_state state=1\nwait 3\nbody_state raw=0x00000000\nwait 2\nbody_state state=2\n");
        const auto a=m.hurtWindows();QCOMPARE(a.size(),1);QCOMPARE(a[0].toObject()["end_frame"].toInt(),-1);
    }
    void signedPositionalContinuationRemainsEditable() {
        const auto m=StatementModel::parse("throw 8 -1265106944 0x0F000000\n");
        const auto a=m.statements();QCOMPARE(a.size(),1);QVERIFY(a[0].toObject()["editable"].toBool());
        QCOMPARE(a[0].toObject()["fields"].toObject()["angle"].toInt(),361);
        QString e;const auto text=m.edit(0,{{"damage",9}},&e);QVERIFY2(!text.isNull(),qPrintable(e));
        QVERIFY(text.contains("throw 9 -1265106944 0x0F000000"));
    }
    void flowKeepsValuesButRefusesTiming() {
        const auto m = StatementModel::parse("body_state state=1\nloop 2\nhurtboxes_state state=2\n");
        const auto a = m.statements(); QCOMPARE(a.size(), 2);
        QCOMPARE(a[1].toObject()["frame"].toInt(), -1);
        QVERIFY(!a[0].toObject()["timing_editable"].toBool());
        QString e;
        QVERIFY(m.edit(1, {{"state", 0}}, &e).contains("hurtboxes_state state=0"));
        QVERIFY(m.edit(0, {{"frame", 4}}, &e).isNull()); QVERIFY(!e.isEmpty());
        QCOMPARE(m.hurtWindows().size(), 1);
        QCOMPARE(m.hurtWindows()[0].toObject()["end_frame"].toInt(), -1);
    }
    void conditionalModifierMakesLaterTimingUncertain() {
        const auto m=StatementModel::parse("body_state state=1\nCHGAND FALLING\nwait 3\nhurtboxes_state state=2\n");
        const auto a=m.statements();QCOMPARE(a.size(),2);QCOMPARE(a[1].toObject()["frame"].toInt(),-1);
        QVERIFY(!a[0].toObject()["timing_editable"].toBool());QString e;
        QVERIFY(m.edit(0,{{"frame",2}},&e).isNull());
        QCOMPARE(m.hurtWindows().size(),1);
    }
    void malformedDuplicateAndRawAreReadOnly() {
        const auto m = StatementModel::parse("body_state state=3\nhurtbox_state bone=1 bone_idx=2 state=0\nthrow slot=2 damage=8\nthrow 0x88000008 0 0\nthrow_flag hit_idx=1\n");
        const auto a=m.statements(); QCOMPARE(a.size(),5);
        for(const auto &v:a) QVERIFY(!v.toObject()["editable"].toBool());
        QCOMPARE(a[4].toObject()["kind"].toString(),QString("throw_flag"));
        QString e; QVERIFY(m.edit(0,{{"state",0}},&e).isNull());
    }
    void positionalPayloadAndRawStayLossless() {
        const auto m=StatementModel::parse("throw 8 0xB4980000 0x0F000000\nhurtbox_state 0x000C0002\nbody_state raw=0x68000001\n");
        const auto a=m.statements(); QCOMPARE(a.size(),3);
        QCOMPARE(a[0].toObject()["fields"].toObject()["angle"].toInt(),361);
        QCOMPARE(a[0].toObject()["fields"].toObject()["kbg"].toInt(),96);
        QCOMPARE(a[1].toObject()["fields"].toObject()["bone"].toString(),QString("3"));
        QString e; const auto edited=m.edit(0,{{"damage",9}},&e);
        QVERIFY2(!edited.isNull(),qPrintable(e)); QVERIFY(edited.contains("throw 9 0xB4980000 0x0F000000"));
        QVERIFY(!a[2].toObject()["editable"].toBool());
    }
    void leafEditsAndNoopKeepComments() {
        const QString source="  throw_hitbox w0.idx=0 w0.damage=8 w1.unk0=361 w1.hit_x24=100 w1.hit_x28=0 w2.hit_x2C=30 # note\r\n";
        const auto m=StatementModel::parse(source); QString e;
        QCOMPARE(m.edit(0,{{"damage",9}},&e),QString(source).replace("damage=8","damage=9"));
        QCOMPARE(m.edit(0,{{"damage",8}},&e),source);
        QVERIFY(m.edit(0,{{"angle",512}},&e).isNull());
        QVERIFY(m.edit(0,{{"damage",2.5}},&e).isNull());
        QVERIFY(m.edit(0,{{"surprise",1}},&e).isNull());
    }
    void movingOneStatementKeepsOtherCommandsFrames() {
        const auto m=StatementModel::parse("wait 3\nbody_state state=1 # protect\nCALL geno.article.spawn 0\nwait 2\nhurtbox_state bone=@HAND_R@ state=2\nwait_until 9\nbody_state state=0\n");
        QString e; const auto moved=m.edit(0,{{"frame",6}},&e); QVERIFY2(!moved.isNull(),qPrintable(e));
        const auto a=StatementModel::parse(moved).statements();
        QCOMPARE(a.size(),3); QCOMPARE(a[0].toObject()["frame"].toInt(),5);
        QCOMPARE(a[1].toObject()["frame"].toInt(),6); QCOMPARE(a[2].toObject()["frame"].toInt(),9);
        QCOMPARE(GenoAsm::parse(moved).spawns()[0].frame,3);
        QVERIFY(moved.contains("# protect"));
    }
    void addRemoveAndTerminalBoundary() {
        const auto m=StatementModel::parse("wait 2\nthrow_release\nwait_until 8\nend\n"); QString e; int ordinal=-1;
        const auto added=m.add("hurtbox_state",5,{{"bone","@HAND_R@"},{"state",2}},&ordinal,&e);
        QVERIFY2(!added.isNull(),qPrintable(e)); QCOMPARE(ordinal,1);
        const auto a=StatementModel::parse(added).statements(); QCOMPARE(a.size(),2);
        QCOMPARE(a[1].toObject()["frame"].toInt(),5);
        QCOMPARE(StatementModel::parse(StatementModel::parse(added).remove(1,&e)).statements().size(),1);
        QVERIFY(m.add("body_state",9,{{"state",1}},&ordinal,&e).isNull());
    }
    void positionalBoneRoleRetainsSemanticBone() {
        QString e;
        const auto edited=StatementModel::parse("  hurtbox_state 0x000C0002 # capsule\r\n").edit(0,{{"bone","@HAND_R@"}},&e);
        QVERIFY2(!edited.isNull(),qPrintable(e));
        QCOMPARE(StatementModel::parse(edited).statements()[0].toObject()["fields"].toObject()["bone"].toString(),QString("@HAND_R@"));
        QVERIFY(edited.startsWith("  ")); QVERIFY(edited.endsWith(" # capsule\r\n"));
    }
    void deletingTheOnlyStatementProducesEmptySource() {
        QString e;const auto removed=StatementModel::parse("throw_release").remove(0,&e);
        QVERIFY(e.isEmpty()); QVERIFY(!removed.isNull()); QVERIFY(removed.isEmpty());
    }
    void opaqueRawControlAndWrongQualifiedFieldsAreRefused() {
        const auto m=StatementModel::parse("body_state state=1\nIF raw=0xEC100000,0,0,2\nthrow_release\n");
        const auto a=m.statements(); QCOMPARE(a[1].toObject()["frame"].toInt(),-1);
        QVERIFY(!StatementModel::parse("throw_flag w0.state=1\n").statements()[0].toObject()["editable"].toBool());
        QString e;int ordinal=-1;
        QVERIFY(StatementModel::parse("").add("body_state",67108864,{{"state",1}},&ordinal,&e).isNull());
    }
    void retimingReplySelectsTheMovedStatement() {
        QTemporaryDir d;wbtest::makeSynthFighter(d.path());
        wbtest::put(d.path(),"moves/jab1.genoasm","wait 3\nthrow_release\nbody_state state=1\nwait_until 9\n");
        Session s(d.path(),nullptr);QVERIFY(s.data().reload().isEmpty());registerStatementCommands(s);CommandContext c{s};
        const auto reply=s.registry().call("edit_statement",{{"row","jab1"},{"ordinal",0},{"frame",6}},c);
        QVERIFY(reply["ok"].toBool());QCOMPARE(reply["result"].toObject()["ordinal"].toInt(),1);
        QCOMPARE(s.data().statements("jab1")[1].toObject()["kind"].toString(),QString("throw_release"));
    }
    void commandsHistoryBOMAndExternalConflict() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        const QByteArray source=QByteArray::fromHex("efbbbf")+"wait 3\r\nthrow slot=0 damage=8 angle=361 kbg=100 fkb=0 bkb=30 # throw\r\nbody_state state=1\r\n";
        wbtest::put(d.path(),"moves/jab1.genoasm",source);
        Session s(d.path(),nullptr); QVERIFY(s.data().reload().isEmpty()); registerStatementCommands(s);
        CommandContext c{s};
        const auto listed=s.registry().call("list_statements",{{"row","jab1"}},c);
        QCOMPARE(listed["result"].toObject()["statements"].toArray().size(),2);
        const QJsonObject args{{"row","jab1"},{"ordinal",0},{"fields",QJsonObject{{"damage",9}}}};
        QVERIFY(s.registry().call("edit_statement",args,c)["ok"].toBool());
        QFile f(QDir(d.path()).filePath("moves/jab1.genoasm")); QVERIFY(f.open(QIODevice::ReadOnly));
        QCOMPARE(f.readAll(),QByteArray(source).replace("damage=8","damage=9")); f.close();
        QString e; QVERIFY(s.history().undo(s.files(),&e)); s.data().reload();
        QCOMPARE(s.data().statements("jab1")[0].toObject()["fields"].toObject()["damage"].toInt(),8);
        QVERIFY(s.history().redo(s.files(),&e)); s.data().reload();
        QJsonObject proposed=args; proposed["fields"]=QJsonObject{{"damage",10}}; proposed["propose"]=true;
        QVERIFY(s.registry().call("edit_statement",proposed,c)["ok"].toBool());
        QCOMPARE(s.data().statements("jab1")[0].toObject()["fields"].toObject()["damage"].toInt(),9);
        wbtest::put(d.path(),"moves/jab1.genoasm",source+"# hand edit\r\n");
        QVERIFY(!s.registry().call("edit_statement",args,c)["ok"].toBool());
    }
};
QTEST_GUILESS_MAIN(StatementsTest)
#include "statements_test.moc"
