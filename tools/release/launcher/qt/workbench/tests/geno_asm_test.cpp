#include "../testfixture.h"
#include "geno_asm.h"
#include <QtTest>
#include <limits>
using namespace wb;

class GenoAsmTest : public QObject {
    Q_OBJECT
private slots:
    void listsHitboxesWithFrames() {
        auto hb = GenoAsm::parse(wbtest::kDair).hitboxes();
        QCOMPARE(hb.size(), 2);
        QCOMPARE(hb[0].joint, QString("FOOT_L"));
        QCOMPARE(hb[0].startFrame, 6); QCOMPARE(hb[0].endFrame, 9);
        QCOMPARE(hb[1].startFrame, 9); QCOMPARE(hb[1].endFrame, 15);
        QCOMPARE(hb[0].damage, 14.0); QCOMPARE(hb[0].size, 2.8); QCOMPARE(hb[0].angle, 270);
    }
    void unclearedHitboxHasOpenEnd() {
        auto hb = GenoAsm::parse("wait_until 4\nhitbox slot=0 joint=@A@ damage=1 size=1 x=0 y=0 z=0 angle=0 kbg=0 fkb=0 bkb=0\n").hitboxes();
        QCOMPARE(hb.size(), 1); QCOMPARE(hb[0].endFrame, -1);
    }
    void noHitboxesOrEmptyText() {
        QCOMPARE(GenoAsm::parse("").hitboxes().size(), 0);
        QCOMPARE(GenoAsm::parse("wait_until 3\niasa\n").hitboxes().size(), 0);
    }
    void hitboxBeforeAnyWaitStartsAtZero() {
        auto hb = GenoAsm::parse("hitbox slot=0 joint=@A@ damage=1 size=1 x=0 y=0 z=0 angle=0 kbg=0 fkb=0 bkb=0\nclear_hitboxes\n").hitboxes();
        QCOMPARE(hb[0].startFrame, 0); QCOMPARE(hb[0].endFrame, 0);
    }
    void editJointOnlyTouchesThatToken() {
        QString err; HitboxEdit e; e.joint = "HAND_R";
        QString out = GenoAsm::parse(wbtest::kDair).apply(0, e, &err);
        QVERIFY2(!out.isNull(), qPrintable(err));
        QString expect = wbtest::kDair;
        expect.replace(expect.indexOf("@FOOT_L@"), 8, "@HAND_R@");
        QCOMPARE(out, expect);
    }
    void editNumbers() {
        QString err; HitboxEdit e; e.damage = 12; e.size = 3.25; e.angle = 45;
        QString out = GenoAsm::parse(wbtest::kJab).apply(0, e, &err);
        QVERIFY2(!out.isNull(), qPrintable(err));
        auto hb = GenoAsm::parse(out).hitboxes();
        QCOMPARE(hb[0].damage, 12.0); QCOMPARE(hb[0].size, 3.25); QCOMPARE(hb[0].angle, 45);
        QVERIFY(out.contains("size=3.25 "));
        QVERIFY(out.contains("damage=12 "));
    }
    void editFramesRewritesWaits() {
        QString err; HitboxEdit e; e.startFrame = 7; e.endFrame = 11;
        QString out = GenoAsm::parse(wbtest::kDair).apply(0, e, &err);
        QVERIFY2(!out.isNull(), qPrintable(err));
        auto hb = GenoAsm::parse(out).hitboxes();
        QCOMPARE(hb[0].startFrame, 7); QCOMPARE(hb[0].endFrame, 11);
        QCOMPARE(hb[1].startFrame, 9);   // second hitbox unaffected: wait_until is absolute
    }
    void editFramesRefusesWeirdShape() {
        QString text = "hitbox slot=0 joint=@A@ damage=1 size=1 x=0 y=0 z=0 angle=0 kbg=0 fkb=0 bkb=0\nwait 3\nwait 1\nclear_hitboxes\n";
        QString err; HitboxEdit e; e.endFrame = 9;
        QVERIFY(GenoAsm::parse(text).apply(0, e, &err).isNull());
        QVERIFY(err.contains("frames not editable"));
    }
    void editUnknownOrdinalFails() {
        QString err; HitboxEdit e; e.damage = 1;
        QVERIFY(GenoAsm::parse(wbtest::kJab).apply(5, e, &err).isNull());
        QVERIFY(!err.isEmpty());
    }
    void windowsLineEndingsSurvive() {
        QString crlf = QString(wbtest::kJab).replace("\n", "\r\n");
        auto hb = GenoAsm::parse(crlf).hitboxes();
        QCOMPARE(hb.size(), 1); QCOMPARE(hb[0].startFrame, 3);
        QString err; HitboxEdit e; e.damage = 5;
        QString out = GenoAsm::parse(crlf).apply(0, e, &err);
        QVERIFY(out.contains("\r\n") && !out.contains("\n\n"));
    }
    void relativeWaitsClearEveryOpenHitbox() {
        const auto hb = GenoAsm::parse(
            "wait 2\nhitbox slot=1 joint=@A@\nwait 3\nhitbox slot=2 joint=@B@\n"
            "wait 4\nclear_hitboxes\nhitbox slot=0 joint=@C@\n").hitboxes();
        QCOMPARE(hb.size(), 3);
        QCOMPARE(hb[0].ordinal, 0); QCOMPARE(hb[0].line, 1); QCOMPARE(hb[0].slot, 1);
        QCOMPARE(hb[0].startFrame, 2); QCOMPARE(hb[0].endFrame, 9);
        QCOMPARE(hb[1].ordinal, 1); QCOMPARE(hb[1].line, 3); QCOMPARE(hb[1].slot, 2);
        QCOMPARE(hb[1].startFrame, 5); QCOMPARE(hb[1].endFrame, 9);
        QCOMPARE(hb[2].startFrame, 9); QCOMPARE(hb[2].endFrame, -1);
    }
    void inlineCommentsCannotOverrideFields() {
        const auto hb = GenoAsm::parse(
            "# hitbox slot=3\nwait_until 4 # wait 99\n"
            "hitbox slot=1 joint=@A@ damage=2 size=3 # damage=99 joint=@B@ slot=3\n"
            "wait 2 # comment\nclear_hitboxes # hitbox slot=0\n").hitboxes();
        QCOMPARE(hb.size(), 1); QCOMPARE(hb[0].line, 2);
        QCOMPARE(hb[0].slot, 1); QCOMPARE(hb[0].joint, QString("A"));
        QCOMPARE(hb[0].damage, 2.0); QCOMPARE(hb[0].size, 3.0);
        QCOMPARE(hb[0].startFrame, 4); QCOMPARE(hb[0].endFrame, 6);
    }
    void editAllNumericFieldsFormatsOnlyThoseTokens() {
        QString err; HitboxEdit e;
        e.damage = 12.25; e.size = 3; e.x = 1.5; e.y = -2; e.z = 0;
        e.angle = 45; e.kbg = 80; e.fkb = 4; e.bkb = 18;
        const QString out = GenoAsm::parse(wbtest::kJab).apply(0, e, &err);
        QVERIFY2(!out.isNull(), qPrintable(err));
        QCOMPARE(out, QString("# synthetic\nPUT ANIM_RATE 1.0\nwait_until 3\n"
            "hitbox slot=0 joint=@HAND_R@ damage=12.25 size=3.00 x=1.50 y=-2.00 z=0.00 angle=45 kbg=80 fkb=4 bkb=18\n"
            "wait 2\nclear_hitboxes\nwait_until 18\niasa\n"));
    }
    void tokenEditPreservesCommentsSpacingAndMixedEndings() {
        const QString source = "# synthetic\r\n\twait_until 3\n"
            "  hitbox\tslot=0  damage=3 joint=@HAND_R@ extra=keep\t# damage=99\r\n"
            "wait 2\r\nclear_hitboxes\n# final line";
        QString err = "stale error"; HitboxEdit e; e.damage = 5;
        const auto script = GenoAsm::parse(source);
        const QString out = script.apply(0, e, &err);
        QVERIFY2(!out.isNull(), qPrintable(err)); QVERIFY(err.isEmpty());
        QCOMPARE(out, QString("# synthetic\r\n\twait_until 3\n"
            "  hitbox\tslot=0  damage=5 joint=@HAND_R@ extra=keep\t# damage=99\r\n"
            "wait 2\r\nclear_hitboxes\n# final line"));
        QCOMPARE(script.text(), source);
        QCOMPARE(script.apply(0, HitboxEdit{}, nullptr), source);
    }
    void missingFieldIsInsertedBeforeComment() {
        const QString source = "hitbox slot=0\t # damage=99\r\n";
        QString err; HitboxEdit e; e.damage = 7;
        QCOMPARE(GenoAsm::parse(source).apply(0, e, &err),
                 QString("hitbox slot=0 damage=7\t # damage=99\r\n"));
    }
    void jointAcceptsWrappedName() {
        QString err; HitboxEdit e; e.joint = "@FOOT_L@";
        const QString out = GenoAsm::parse("hitbox joint=@HAND_R@\n").apply(0, e, &err);
        QVERIFY2(!out.isNull(), qPrintable(err));
        QCOMPARE(out, QString("hitbox joint=@FOOT_L@\n"));
    }
    void framesPreserveWhitespaceCommentsAndLineEndings() {
        const QString source = "\twait_until 3  # startup\r\n# before\n\n"
            "  hitbox slot=0 joint=@A@\r\n # after\n"
            "  wait\t2 # duration\r\n\n\tclear_hitboxes # clear\r\n";
        QString err; HitboxEdit e; e.startFrame = 4; e.endFrame = 8;
        const QString out = GenoAsm::parse(source).apply(0, e, &err);
        QVERIFY2(!out.isNull(), qPrintable(err));
        QCOMPARE(out, QString("\twait_until 4  # startup\r\n# before\n\n"
            "  hitbox slot=0 joint=@A@\r\n # after\n"
            "  wait\t4 # duration\r\n\n\tclear_hitboxes # clear\r\n"));
    }
    void editingOneFrameBoundaryRetainsTheOther() {
        QString err; HitboxEdit start; start.startFrame = 4;
        const QString shifted = GenoAsm::parse(wbtest::kJab).apply(0, start, &err);
        QVERIFY2(!shifted.isNull(), qPrintable(err));
        const auto shiftedBoxes = GenoAsm::parse(shifted).hitboxes();
        QCOMPARE(shiftedBoxes[0].startFrame, 4); QCOMPARE(shiftedBoxes[0].endFrame, 5);
        HitboxEdit end; end.endFrame = 7;
        const QString extended = GenoAsm::parse(wbtest::kJab).apply(0, end, &err);
        QVERIFY2(!extended.isNull(), qPrintable(err));
        const auto extendedBoxes = GenoAsm::parse(extended).hitboxes();
        QCOMPARE(extendedBoxes[0].startFrame, 3); QCOMPARE(extendedBoxes[0].endFrame, 7);
    }
    void unsafeFrameShapes_data() {
        QTest::addColumn<QString>("source"); QTest::addColumn<int>("ordinal");
        QTest::newRow("missing-start") << QString("hitbox slot=0\nwait 2\nclear_hitboxes\n") << 0;
        QTest::newRow("missing-clear") << QString("wait_until 3\nhitbox slot=0\nwait 2\n") << 0;
        QTest::newRow("extra-op") << QString("wait_until 3\nhitbox slot=0\niasa\nwait 2\nclear_hitboxes\n") << 0;
        QTest::newRow("second-hitbox") << QString("wait_until 3\nhitbox slot=0\nhitbox slot=1\nwait 2\nclear_hitboxes\n") << 0;
        QTest::newRow("earlier-active") << QString("wait_until 2\nhitbox slot=1\nwait_until 3\nhitbox slot=0\nwait 2\nclear_hitboxes\n") << 1;
        QTest::newRow("reused-slot") << QString("wait_until 2\nhitbox slot=0\nwait_until 3\nhitbox slot=0\nwait 2\nclear_hitboxes\n") << 1;
        QTest::newRow("invalid-start") << QString("wait_until nope\nhitbox slot=0\nwait 2\nclear_hitboxes\n") << 0;
        QTest::newRow("fractional-start") << QString("wait_until 3.5\nhitbox slot=0\nwait 2\nclear_hitboxes\n") << 0;
        QTest::newRow("invalid-wait") << QString("wait_until 3\nhitbox slot=0\nwait nope\nclear_hitboxes\n") << 0;
        QTest::newRow("extra-wait-arg") << QString("wait_until 3\nhitbox slot=0\nwait 2 extra\nclear_hitboxes\n") << 0;
        QTest::newRow("extra-clear-arg") << QString("wait_until 3\nhitbox slot=0\nwait 2\nclear_hitboxes extra\n") << 0;
    }
    void unsafeFrameShapes() {
        QFETCH(QString, source); QFETCH(int, ordinal);
        const auto script = GenoAsm::parse(source);
        const auto hb = script.hitboxes();
        QVERIFY(hb.size() > ordinal); QCOMPARE(hb[ordinal].ordinal, ordinal);
        QString err; HitboxEdit e; e.startFrame = 4; e.endFrame = 8; e.damage = 9;
        QVERIFY(script.apply(ordinal, e, &err).isNull());
        QVERIFY2(err.startsWith("frames not editable for this script shape: "), qPrintable(err));
        QCOMPARE(script.text(), source);
        HitboxEdit fields; fields.damage = 9;
        QVERIFY2(!script.apply(ordinal, fields, &err).isNull(), qPrintable(err));
    }
    void nonPositiveDurationIsRejected() {
        QString err; HitboxEdit e; e.startFrame = 5; e.endFrame = 5;
        QVERIFY(GenoAsm::parse(wbtest::kJab).apply(0, e, &err).isNull());
        QVERIFY(err.contains("end frame must be after start frame"));
        e.endFrame = 4;
        QVERIFY(GenoAsm::parse(wbtest::kJab).apply(0, e, nullptr).isNull());
    }
    void negativeFrameIsRejected() {
        QString err; HitboxEdit e; e.startFrame = -1;
        QVERIFY(GenoAsm::parse(wbtest::kJab).apply(0, e, &err).isNull());
        QVERIFY(!err.isEmpty());
    }
    void negativeOrdinalFailsWithOptionalError() {
        QString err;
        QVERIFY(GenoAsm::parse(wbtest::kJab).apply(-1, HitboxEdit{}, &err).isNull());
        QVERIFY(err.contains("no hitbox #-1"));
        QVERIFY(GenoAsm::parse("").apply(0, HitboxEdit{}, nullptr).isNull());
    }
    void invalidFieldValuesAreRejected() {
        QString err; HitboxEdit e; e.joint = "A@\nclear_hitboxes\nhitbox joint=@B";
        QVERIFY(GenoAsm::parse(wbtest::kJab).apply(0, e, &err).isNull());
        QVERIFY(!err.isEmpty());
        e.joint = "@@";
        QVERIFY(GenoAsm::parse(wbtest::kJab).apply(0, e, &err).isNull());
        e = HitboxEdit{}; e.damage = std::numeric_limits<double>::infinity();
        QVERIFY(GenoAsm::parse(wbtest::kJab).apply(0, e, &err).isNull());
        e = HitboxEdit{}; e.x = std::numeric_limits<double>::quiet_NaN();
        QVERIFY(GenoAsm::parse(wbtest::kJab).apply(0, e, &err).isNull());
    }

};
QTEST_MAIN(GenoAsmTest)
#include "geno_asm_test.moc"
