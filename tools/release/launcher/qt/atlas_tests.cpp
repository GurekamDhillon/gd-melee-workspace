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
};
QTEST_MAIN(AtlasTests)
#include "atlas_tests.moc"
