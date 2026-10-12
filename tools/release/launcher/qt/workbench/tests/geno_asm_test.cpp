#include "../testfixture.h"
#include "geno_asm.h"
#include <QtTest>
#include <limits>
#include <QRegularExpression>
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

    void elementPreservesRawCodeAndEditsOnlyItsToken() {
        const QString source = "hitbox slot=0 element=3 damage=7 # element=31\r\n";
        const auto script = GenoAsm::parse(source); QCOMPARE(script.hitboxes()[0].element, 3);
        QString error; HitboxEdit edit; edit.element = 0;
        QCOMPARE(script.apply(0, edit, &error), QString("hitbox slot=0 element=0 damage=7 # element=31\r\n"));
        QVERIFY(error.isEmpty());
        QCOMPARE(GenoAsm::parse("hitbox slot=0\n").hitboxes()[0].element, 0);
        edit.element = 31;
        QCOMPARE(GenoAsm::parse("hitbox slot=0 # keep\n").apply(0, edit, &error), QString("hitbox slot=0 element=31 # keep\n"));
        edit.element = 32; QVERIFY(script.apply(0, edit, &error).isNull());
        edit.element = -1; QVERIFY(script.apply(0, edit, &error).isNull());
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
        QTest::newRow("earlier-active") << QString("wait_until 2\nhitbox slot=1\nwait_until 3\nhitbox slot=0\nwait 2\nclear_hitboxes\n") << 1;
        QTest::newRow("reused-slot") << QString("wait_until 2\nhitbox slot=0\nwait_until 3\nhitbox slot=0\nwait 2\nclear_hitboxes\n") << 1;
        QTest::newRow("invalid-start") << QString("wait_until nope\nhitbox slot=0\nwait 2\nclear_hitboxes\n") << 0;
        QTest::newRow("fractional-start") << QString("wait_until 3.5\nhitbox slot=0\nwait 2\nclear_hitboxes\n") << 0;
        QTest::newRow("invalid-wait") << QString("wait_until 3\nhitbox slot=0\nwait nope\nclear_hitboxes\n") << 0;
        QTest::newRow("extra-wait-arg") << QString("wait_until 3\nhitbox slot=0\nwait 2 extra\nclear_hitboxes\n") << 0;
        QTest::newRow("extra-clear-arg") << QString("wait_until 3\nhitbox slot=0\nwait 2\nclear_hitboxes extra\n") << 0;
    }
    // ports/goku-xv2/moves/rush.genoasm: three hitboxes on one frame, HBSTUN after them, wait_until (not wait) to the clear.
    static QString rushScript() {
        return QString("PUT ANIM_RATE 1.0\nwait_until 1\nsfx behavior=1 sfx_id=165 volume=127 panning=64\nwait_until 11\n"
            "hitbox slot=0 joint=@FOOT_R@ damage=8 size=2.8 x=0.0391 y=-0.406 z=0.8485 angle=361 kbg=60 fkb=10 bkb=0\n"
            "hitbox slot=1 joint=@LEG_R@ damage=7 size=4.91 x=0.07586 y=-1.697 z=-0.04726 angle=361 kbg=60 fkb=10 bkb=0\n"
            "hitbox slot=2 joint=@UPLEG_R@ damage=6 size=5.04 x=0.1067 y=-1.503 z=-0.002655 angle=361 kbg=60 fkb=10 bkb=0\n"
            "HBSTUN 7 12\nwait_until 15\nclear_hitboxes\nwait_until 62\niasa\n");
    }
    void rushShapeFramesAreEditableAndKeepHbstun() {
        const QString src = rushScript();
        QString err;
        for (int ordinal = 0; ordinal < 3; ++ordinal) {
            HitboxEdit e; e.startFrame = 12; e.endFrame = 18;
            const QString out = GenoAsm::parse(src).apply(ordinal, e, &err);
            QVERIFY2(!out.isNull(), qPrintable(err));
            const auto boxes = GenoAsm::parse(out).hitboxes();
            QCOMPARE(boxes.size(), 3);
            // The moved window reorders by start frame, so find each box by its joint.
            const QStringList joints{"FOOT_R", "LEG_R", "UPLEG_R"};
            for (int j = 0; j < 3; ++j) {
                int found = -1;
                for (int i = 0; i < boxes.size(); ++i) if (boxes[i].joint == joints[j]) found = i;
                QVERIFY(found >= 0);
                QCOMPARE(boxes[found].startFrame, j == ordinal ? 12 : 11);
                QCOMPARE(boxes[found].endFrame, j == ordinal ? 18 : 15);
            }
            QCOMPARE(out.count("HBSTUN 7 12"), 1);   // kept, once
            QVERIFY(out.contains("sfx behavior=1 sfx_id=165 volume=127 panning=64\n"));
            QVERIFY(out.contains("wait_until 62\niasa"));
        }
        // An edit that changes nothing in the frames leaves the file byte for byte.
        HitboxEdit same; same.startFrame = 11; same.endFrame = 15;
        QCOMPARE(GenoAsm::parse(src).apply(1, same, &err), src);
        // Field edits keep the order (hitboxes, then HBSTUN, then the wait).
        HitboxEdit d; d.damage = 9;
        const QString dmg = GenoAsm::parse(src).apply(2, d, &err);
        QVERIFY2(!dmg.isNull(), qPrintable(err));
        QVERIFY(dmg.indexOf("damage=9 ") < dmg.indexOf("HBSTUN 7 12"));
    }
    void companionOpBeforeTheHitboxIsEditableToo() {
        const QString src = "wait_until 3\nHBSTUN 7 12\nhitbox slot=0 joint=@A@\nwait 2\nclear_hitboxes\n";
        QString err; HitboxEdit e; e.startFrame = 4; e.endFrame = 8;
        const QString out = GenoAsm::parse(src).apply(0, e, &err);
        QVERIFY2(!out.isNull(), qPrintable(err));
        QCOMPARE(GenoAsm::parse(out).hitboxes()[0].startFrame, 4);
        QCOMPARE(GenoAsm::parse(out).hitboxes()[0].endFrame, 8);
        QCOMPARE(out.count("HBSTUN 7 12"), 1);
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


    static HitboxAdd spec(const QString &joint, int frame, int duration = 2) {
        HitboxAdd a; a.joint = joint; a.frame = frame; a.duration = duration; return a;
    }
    void addJoinsTheActiveWindowAndDeleteRestoresBytes() {
        QString err; int ordinal = -1;
        const QString out = GenoAsm::parse(wbtest::kJab).addHitbox(spec("HAND_L", 3), &err, &ordinal);
        QVERIFY2(!out.isNull(), qPrintable(err));
        QString expect = wbtest::kJab;
        expect.replace("wait 2\n", "hitbox slot=1 joint=@HAND_L@ damage=6 size=3.00 x=0.00 y=0.00 z=0.00 angle=361 kbg=50 fkb=0 bkb=20\nwait 2\n");
        QCOMPARE(out, expect);
        QCOMPARE(ordinal, 1);
        QCOMPARE(GenoAsm::parse(out).hitboxes()[1].endFrame, 5);
        QCOMPARE(GenoAsm::parse(out).removeHitbox(1, &err), QString(wbtest::kJab));
    }
    void addMidWindowSplitsTheWaitAndDeleteMergesIt() {
        QString err; int ordinal = -1;
        const QString out = GenoAsm::parse(wbtest::kDair).addHitbox(spec("FOOT_R", 7), &err, &ordinal);
        QVERIFY2(!out.isNull(), qPrintable(err));
        QVERIFY(out.contains("wait 1\nhitbox slot=1 joint=@FOOT_R@"));
        QVERIFY(out.contains("bkb=20\nwait 2\nclear_hitboxes\nwait_until 9"));
        const auto boxes = GenoAsm::parse(out).hitboxes();
        QCOMPARE(boxes[ordinal].startFrame, 7); QCOMPARE(boxes[ordinal].endFrame, 9);
        QCOMPARE(boxes[0].endFrame, 9);
        QCOMPARE(GenoAsm::parse(out).removeHitbox(ordinal, &err), QString(wbtest::kDair));
    }
    void addFreshWindowBeforeALaterWaitUntil() {
        QString err; int ordinal = -1;
        const QString out = GenoAsm::parse(wbtest::kJab).addHitbox(spec("FOOT_R", 10, 3), &err, &ordinal);
        QVERIFY2(!out.isNull(), qPrintable(err));
        QVERIFY(out.contains("clear_hitboxes\nwait_until 10\nhitbox slot=0 joint=@FOOT_R@"));
        QVERIFY(out.contains("bkb=20\nwait 3\nclear_hitboxes\nwait_until 18\niasa"));
        const auto boxes = GenoAsm::parse(out).hitboxes();
        QCOMPARE(boxes.size(), 2); QCOMPARE(ordinal, 1);
        QCOMPARE(boxes[1].startFrame, 10); QCOMPARE(boxes[1].endFrame, 13);
        // The new block keeps the editable wait_until / hitbox / wait / clear shape.
        HitboxEdit e; e.endFrame = 15;
        QVERIFY(!GenoAsm::parse(out).apply(1, e, &err).isNull());
        QCOMPARE(GenoAsm::parse(out).removeHitbox(ordinal, &err), QString(wbtest::kJab));
    }
    void addFreshWindowClampsToTheNextWindow() {
        QString err; int ordinal = -1;
        const QString out = GenoAsm::parse(wbtest::kDair).addHitbox(spec("FOOT_R", 4, 5), &err, &ordinal);
        QVERIFY2(!out.isNull(), qPrintable(err));
        const auto boxes = GenoAsm::parse(out).hitboxes();
        QCOMPARE(boxes[ordinal].startFrame, 4); QCOMPARE(boxes[ordinal].endFrame, 6);
        QCOMPARE(boxes.size(), 3);
        QCOMPARE(boxes[ordinal + 1].startFrame, 6);   // the original windows keep their frames
        QCOMPARE(boxes[ordinal + 1].endFrame, 9);
    }
    void addPastTheEndAppends() {
        QString err; int ordinal = -1;
        const QString out = GenoAsm::parse(wbtest::kJab).addHitbox(spec("FOOT_R", 30), &err, &ordinal);
        QVERIFY2(!out.isNull(), qPrintable(err));
        QVERIFY(out.endsWith("iasa\nwait_until 30\nhitbox slot=0 joint=@FOOT_R@ damage=6 size=3.00 x=0.00 y=0.00 z=0.00 angle=361 kbg=50 fkb=0 bkb=20\nwait 2\nclear_hitboxes\n"));
        QCOMPARE(GenoAsm::parse(out).hitboxes()[ordinal].startFrame, 30);
        QCOMPARE(GenoAsm::parse(out).removeHitbox(ordinal, &err), QString(wbtest::kJab));
    }
    void addTakesTheNextFreeSlotAndStopsAtFour() {
        QString err;
        QString text = wbtest::kJab;
        for (int slot = 1; slot < kHitboxSlots; ++slot) {
            text = GenoAsm::parse(text).addHitbox(spec("HAND_R", 3), &err);
            QVERIFY2(!text.isNull(), qPrintable(err));
            QVERIFY(text.contains(QString("hitbox slot=%1 ").arg(slot)));
        }
        QVERIFY(GenoAsm::parse(text).addHitbox(spec("HAND_R", 3), &err).isNull());
        QVERIFY(err.contains("no free hitbox slot"));
        // The slot is free again in a window that does not overlap.
        QVERIFY(!GenoAsm::parse(text).addHitbox(spec("HAND_R", 10), &err).isNull());
    }
    void addRejectsBadInput() {
        QString err;
        QVERIFY(GenoAsm::parse(wbtest::kJab).addHitbox(spec("A B", 3), &err).isNull());
        QVERIFY(GenoAsm::parse(wbtest::kJab).addHitbox(spec("A", -1), &err).isNull());
        QVERIFY(GenoAsm::parse(wbtest::kJab).addHitbox(spec("A", 3, 0), &err).isNull());
        auto bad = spec("A", 3); bad.size = std::numeric_limits<double>::infinity();
        QVERIFY(GenoAsm::parse(wbtest::kJab).addHitbox(bad, &err).isNull());
    }
    void addKeepsCrLfLines() {
        QString text = wbtest::kJab; text.replace("\n", "\r\n");
        QString err; int ordinal = -1;
        const QString out = GenoAsm::parse(text).addHitbox(spec("FOOT_R", 10, 3), &err, &ordinal);
        QVERIFY2(!out.isNull(), qPrintable(err));
        QVERIFY(!out.contains(QRegularExpression("[^\r]\n")));
        QCOMPARE(GenoAsm::parse(out).removeHitbox(ordinal, &err), text);
    }
    void deleteTheLastHitboxDropsItsWindow() {
        QString err;
        const QString out = GenoAsm::parse(wbtest::kJab).removeHitbox(0, &err);
        QVERIFY2(!out.isNull(), qPrintable(err));
        QCOMPARE(out, QString("# synthetic\nPUT ANIM_RATE 1.0\nwait_until 18\niasa\n"));
        QVERIFY(GenoAsm::parse(wbtest::kJab).removeHitbox(5, &err).isNull());
        QVERIFY(err.contains("no hitbox #5"));
    }
    void deleteKeepsTheWaitsWhenLaterLinesDependOnThem() {
        QString err;
        const QString text = "wait_until 3\nhitbox slot=0 joint=@A@ damage=1 size=1 x=0 y=0 z=0 angle=0 kbg=0 fkb=0 bkb=0\n"
                             "wait 2\nclear_hitboxes\njab_rapid state=1\nwait_until 18\niasa\n";
        QCOMPARE(GenoAsm::parse(text).removeHitbox(0, &err), QString("wait_until 3\nwait 2\njab_rapid state=1\nwait_until 18\niasa\n"));
    }

    void reordersWhenAWindowMovesPastTheNext() {
        QString err; HitboxEdit e; e.startFrame = 12; e.endFrame = 16;
        const QString out = GenoAsm::parse(wbtest::kDair).apply(0, e, &err);
        QVERIFY2(!out.isNull(), qPrintable(err));
        const auto hb = GenoAsm::parse(out).hitboxes();
        QCOMPARE(hb.size(), 2);
        QCOMPARE(hb[0].startFrame, 9);  QCOMPARE(hb[0].endFrame, 15);
        QCOMPARE(hb[1].startFrame, 12); QCOMPARE(hb[1].endFrame, 16);
        QVERIFY(hb[0].slot != hb[1].slot);
        QVERIFY(GenoAsm::parse(out).timingProblems().isEmpty());
        QVERIFY2(out.contains("clear_hitbox hit_idx=" + QString::number(hb[0].slot)), qPrintable(out));
        QVERIFY(out.endsWith("wait_until 36\niasa\n"));
    }
    void moreThanFourOverlappingWindowsAreRefused() {
        QString text;
        for (int i = 0; i < 4; ++i)
            text += QString("wait_until %1\nhitbox slot=%2 joint=@A@ damage=1\n").arg(2 + i).arg(i);
        text += "wait_until 20\nclear_hitboxes\n";
        HitboxAdd a; a.joint = "B"; a.frame = 10; a.duration = 3;
        QString err;
        QVERIFY(GenoAsm::parse(text).addHitbox(a, &err).isNull());
        QVERIFY2(err.contains("no free hitbox slot") || err.contains("more than 4"), qPrintable(err));
    }
    void timingProblemsNameARewindAndASlotClash() {
        const QString text = "wait_until 12\nhitbox slot=0 joint=@A@ damage=1\nwait 4\nclear_hitboxes\nwait_until 9\n"
                             "hitbox slot=0 joint=@A@ damage=1\nwait 6\nclear_hitboxes\n";
        const auto problems = GenoAsm::parse(text).timingProblems();
        QVERIFY(!problems.isEmpty());
        QVERIFY2(problems.join("\n").contains("wait_until 9 comes after frame 16"), qPrintable(problems.join("\n")));
        QVERIFY(GenoAsm::parse(wbtest::kDair).timingProblems().isEmpty());
        const QString clash = "wait_until 2\nhitbox slot=0 joint=@A@\nwait_until 3\nhitbox slot=0 joint=@A@\nwait_until 6\nclear_hitboxes\n";
        QVERIFY(GenoAsm::parse(clash).timingProblems().join("\n").contains("different slots"));
    }
    void existingDistinctSlotsAreNeverRenumbered() {
        // Slot ids are hit priority: slot 2 opens after slot 1 here on purpose, and the script is out of order.
        const QString text = "wait_until 12\nhitbox slot=2 joint=@A@ damage=5\nwait 4\nclear_hitboxes\n"
                             "wait_until 9\nhitbox slot=1 joint=@B@ damage=9\nwait 6\nclear_hitboxes\n";
        QString err;
        HitboxEdit frames; frames.startFrame = 12; frames.endFrame = 16;
        const QString sorted = GenoAsm::parse(text).apply(0, frames, &err);
        QVERIFY2(!sorted.isNull(), qPrintable(err));
        const auto hb = GenoAsm::parse(sorted).hitboxes();
        QCOMPARE(hb.size(), 2);
        QCOMPARE(hb[0].joint, QString("B")); QCOMPARE(hb[0].slot, 1);
        QCOMPARE(hb[1].joint, QString("A")); QCOMPARE(hb[1].slot, 2);
    }
    void aNewOverlappingHitboxTakesTheNextFreeHigherSlot() {
        // slot 1 is live over frames 4..10 and slot 0 is free: the new hitbox must not jump the queue to 0.
        const QString text = "wait_until 4\nhitbox slot=1 joint=@A@ damage=5\nwait 6\nclear_hitboxes\n";
        HitboxAdd a; a.joint = "B"; a.frame = 6; a.duration = 2;
        QString err;
        const QString out = GenoAsm::parse(text).addHitbox(a, &err);
        QVERIFY2(!out.isNull(), qPrintable(err));
        const auto hb = GenoAsm::parse(out).hitboxes();
        QCOMPARE(hb.size(), 2);
        QCOMPARE(hb[0].slot, 1); QCOMPARE(hb[1].slot, 2);
        // the same through the one-slot-at-a-time model path (after a clear_hitbox exists)
        const QString perSlot = "wait_until 4\nhitbox slot=1 joint=@A@ damage=5\nhitbox slot=3 joint=@C@ damage=5\nwait_until 8\n"
                                "clear_hitbox hit_idx=3\nwait_until 10\nclear_hitboxes\n";
        const QString out2 = GenoAsm::parse(perSlot).addHitbox(a, &err);
        QVERIFY2(!out2.isNull(), qPrintable(err));
        const auto hb2 = GenoAsm::parse(out2).hitboxes();
        QCOMPARE(hb2.size(), 3);
        for (const auto &h : hb2) if (h.joint == "B") QCOMPARE(h.slot, 0);  // 1 and 3 are live and nothing is free above them: the lowest free id
    }
    void shieldGroundAirParseAndRoundTrip() {
        const QString source = "wait_until 3\nhitbox slot=0 joint=@A@ damage=7 shield=-3 ground=0 air=1 # shield=99\nwait 2\nclear_hitboxes\n";
        const auto script = GenoAsm::parse(source);
        auto h = script.hitboxes()[0];
        QCOMPARE(h.shield, -3); QVERIFY(!h.ground); QVERIFY(h.air);
        const auto plain = GenoAsm::parse("hitbox slot=0\n").hitboxes()[0];   // omitted: 0 / true / true
        QCOMPARE(plain.shield, 0); QVERIFY(plain.ground); QVERIFY(plain.air);
        QString err; HitboxEdit e; e.shield = 10; e.ground = true; e.air = false;
        const QString out = script.apply(0, e, &err); QVERIFY2(!out.isNull(), qPrintable(err));
        QVERIFY(out.contains("shield=10 ground=1 air=0 # shield=99"));
        h = GenoAsm::parse(out).hitboxes()[0];
        QCOMPARE(h.shield, 10); QVERIFY(h.ground); QVERIFY(!h.air);
        HitboxEdit neg; neg.shield = -128;   // the whole signed byte is allowed
        const QString low = GenoAsm::parse("hitbox slot=0\n").apply(0, neg, &err); QVERIFY2(!low.isNull(), qPrintable(err));
        QCOMPARE(GenoAsm::parse(low).hitboxes()[0].shield, -128);
        for (int bad : {-129, 128}) { HitboxEdit b; b.shield = bad; QVERIFY(script.apply(0, b, &err).isNull()); QVERIFY(err.contains("shield")); }
    }
    void slotEditKeepsDistinctSlotsAndRefusesConflictsAndSlotFour() {
        const QString two = "wait_until 4\nhitbox slot=0 joint=@A@ damage=3\nwait_until 6\nhitbox slot=1 joint=@B@ damage=4\n"
                            "wait_until 9\nclear_hitboxes\n";
        const auto script = GenoAsm::parse(two);
        QString err; HitboxEdit e; e.slot = 3;
        QString out = script.apply(1, e, &err); QVERIFY2(!out.isNull(), qPrintable(err));
        auto hb = GenoAsm::parse(out).hitboxes(); QCOMPARE(hb[0].slot, 0); QCOMPARE(hb[1].slot, 3);
        e.slot = 0;   // live together with box 0 on slot 0: refused, nothing renumbered behind the user's back
        QVERIFY(script.apply(1, e, &err).isNull()); QVERIFY2(err.contains("slot 0 is already used"), qPrintable(err));
        e.slot = 4; QVERIFY(script.apply(1, e, &err).isNull()); QVERIFY(err.contains("slot must be between 0 and 3"));
        e.slot = -1; QVERIFY(script.apply(1, e, &err).isNull());
        // sequential (not overlapping) hitboxes may share a slot
        const QString seq = "wait_until 4\nhitbox slot=0 joint=@A@\nwait 2\nclear_hitboxes\nwait_until 8\nhitbox slot=1 joint=@B@\nwait 2\nclear_hitboxes\n";
        e.slot = 0; out = GenoAsm::parse(seq).apply(1, e, &err); QVERIFY2(!out.isNull(), qPrintable(err));
        QCOMPARE(GenoAsm::parse(out).hitboxes()[1].slot, 0);
        // a slot beyond the writable range in an existing script is read back as it is
        QCOMPARE(GenoAsm::parse("hitbox slot=4 joint=@A@\n").hitboxes()[0].slot, 4);
    }
};
QTEST_MAIN(GenoAsmTest)
#include "geno_asm_test.moc"
