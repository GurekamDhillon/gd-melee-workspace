#include "atlas.h"
#include <QFontDatabase>
#include <QFontMetricsF>
#include <QtTest>
using namespace launcher;

class AtlasTests : public QObject {
    Q_OBJECT
private slots:
    void initTestCase() { atlas::initialize(); }

    void tokens_load() {
        QCOMPARE(atlas::colour("ember"), QColor(0xff, 0x7a, 0x3d));
        QCOMPARE(atlas::colour("jade"), QColor(0x4f, 0xd6, 0xaa));
        QCOMPARE(atlas::colour("plate"), QColor(0x1a, 0x1f, 0x29));
        QCOMPARE(atlas::colour("scrim").alpha(), 0xb8);              // rgba(5,7,10,.72)
        QVERIFY(!atlas::colour("no-such-token").isValid());
        QCOMPARE(atlas::px("t-row"), 16); QCOMPARE(atlas::px("ch"), 8); QCOMPARE(atlas::px("ch-s"), 5); QCOMPARE(atlas::px("ch-xs"), 3);
        QCOMPARE(atlas::px("s1"), 4); QCOMPARE(atlas::px("s5"), 24);
        QCOMPARE(atlas::ms("m-focus"), 80); QCOMPARE(atlas::ms("m-tab"), 120);
        QCOMPARE(atlas::px("no-such-token"), 0);
    }

    void fonts_loaded() {
        const auto families = QFontDatabase::families();
        QVERIFY2(families.contains("Barlow Condensed"), "Barlow Condensed is not registered: the qrc entry is missing or the file is damaged");
        QVERIFY(families.contains("Source Sans 3"));
        QVERIFY(atlas::font(atlas::Role::Cap16).family().startsWith("Barlow Condensed"));
        QCOMPARE(atlas::font(atlas::Role::Cap16).pixelSize(), 16);
        QCOMPARE(atlas::font(atlas::Role::Cap12).pixelSize(), 12);
        QVERIFY(atlas::font(atlas::Role::Cap12).letterSpacing() > 0);   // tracked +0.10 em
        QVERIFY(atlas::font(atlas::Role::Title).bold());                // Barlow Condensed Bold
        QVERIFY(atlas::font(atlas::Role::Row16).family().startsWith("Source Sans 3"));
        // the role really is the face: a string measures differently in Barlow Condensed than in a generic family
        QFont generic("Arial"); generic.setPixelSize(16);
        QVERIFY(QFontMetricsF(atlas::font(atlas::Role::Cap16)).horizontalAdvance("GD'S MELEE LAUNCHER") != QFontMetricsF(generic).horizontalAdvance("GD'S MELEE LAUNCHER"));
    }
    void roles_never_below_floor() {
        for (auto r : {atlas::Role::Cap12, atlas::Role::Cap14, atlas::Role::Cap16, atlas::Role::Cap20, atlas::Role::Title, atlas::Role::Hero,
                       atlas::Role::Body12, atlas::Role::Body14, atlas::Role::Row16})
            QVERIFY(atlas::font(r).pixelSize() >= 12);
    }

    void chamfer_is_top_left_and_bottom_right() {
        const QPolygonF p = atlas::plate(QRectF(10, 20, 100, 40), 5);
        QCOMPARE(p.size(), 6);
        QVERIFY(!p.containsPoint(QPointF(10.2, 20.2), Qt::OddEvenFill));      // top-left cut
        QVERIFY(!p.containsPoint(QPointF(109.8, 59.8), Qt::OddEvenFill));     // bottom-right cut
        QVERIFY(p.containsPoint(QPointF(109.8, 20.2), Qt::OddEvenFill));      // top-right square
        QVERIFY(p.containsPoint(QPointF(10.2, 59.8), Qt::OddEvenFill));       // bottom-left square
        QCOMPARE(p.boundingRect(), QRectF(10, 20, 100, 40));
        QCOMPARE(atlas::plate(QRectF(0, 0, 4, 4), 5).size(), 4);              // a chamfer larger than the plate degrades to a rectangle
    }
    void lift_and_front_edge() {
        QCOMPARE(atlas::lifted(QRectF(0, 10, 50, 30), true), QRectF(0, 8, 50, 30));
        QCOMPARE(atlas::lifted(QRectF(0, 10, 50, 30), false), QRectF(0, 10, 50, 30));
        QCOMPARE(atlas::frontEdge(QRectF(0, 10, 50, 30), 3), QRectF(0, 37, 50, 3));
    }
    void focus_marks() {
        const QRectF r(0, 0, 200, 34);
        QCOMPARE(atlas::tick(r), QRectF(0, 6, 4, 22));                         // 4 px wide, centred, inset 6
        const auto b = atlas::brackets(QRectF(0, 0, 60, 60), 8, 2);
        QCOMPARE(b.size(), 8);                                                 // four corners, two strokes each
        for (const auto &s : b) QVERIFY(QRectF(0, 0, 60, 60).contains(s));
    }
    void fit_steps_down_then_elides() {
        QFontMetricsF fm(atlas::font(atlas::Role::Row16));
        QCOMPARE(atlas::fit(fm, "Short", 400), QString("Short"));
        const QString s = atlas::fit(fm, "A very long disc name that cannot possibly fit in a narrow row", 90);
        QVERIFY(fm.horizontalAdvance(s) <= 90.01);
        QVERIFY(s.endsWith(QChar(0x2026)));
        QVERIFY(atlas::fit(fm, "x", 2).isEmpty());                              // under 8 px of room: nothing is drawn
        QVERIFY(atlas::fit(fm, "", 100).isEmpty());
    }
    void contrast_table() {                                                      // spec 4.2: only dim text is under 4.5:1
        const auto plate = atlas::colour("plate");
        QVERIFY(atlas::contrast(atlas::colour("ivory"), plate) >= 4.5);
        QVERIFY(atlas::contrast(atlas::colour("text2"), plate) >= 4.5);
        QVERIFY(atlas::contrast(atlas::colour("muted"), plate) >= 4.5);
        QVERIFY(atlas::contrast(atlas::colour("dim"), plate) < 4.5);
        QVERIFY(atlas::contrast(atlas::colour("ember"), plate) >= 3.0);          // a focus edge is a component, not text
        QVERIFY(atlas::contrast(atlas::colour("jade"), plate) >= 3.0);
        QVERIFY(atlas::contrast(atlas::colour("ink"), atlas::colour("ember")) >= 4.5);   // the Play label on the ember button
        QCOMPARE(atlas::contrast(QColor(0, 0, 0), QColor(255, 255, 255)), 21.0);
    }
};
QTEST_MAIN(AtlasTests)
#include "atlas_tests.moc"
