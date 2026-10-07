#include "atlas.h"
#include "kit.h"
#include "window.h"
#include <QComboBox>
#include <QScrollArea>
#include <QScrollBar>
#include <QSlider>
#include <QFile>
#include <QDir>
#include <QStackedWidget>
#include <QTableWidget>
#include <QTemporaryDir>
#include <QApplication>
#include <QImage>
#include <QSignalSpy>
#include <QFontDatabase>
#include <QFile>
#include <QFontMetricsF>
#include <QJsonDocument>
#include <QJsonObject>
#include <QtTest>
using namespace launcher;

class AtlasTests : public QObject {
    Q_OBJECT
private slots:
    void initTestCase() { launcher::applyTheme(); }

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

    void tokens_match_the_file() {                                      // the loaded values are the repo's tokens.json, every one
        QFile f(ATLAS_TOKENS_JSON); QVERIFY2(f.open(QIODevice::ReadOnly), ATLAS_TOKENS_JSON);
        const auto doc = QJsonDocument::fromJson(f.readAll()).object();
        const auto colours = doc["colours"].toObject();
        QVERIFY(colours.size() >= 30);
        for (auto it = colours.begin(); it != colours.end(); ++it) {
            const quint32 c = quint32(it.value().toDouble());
            QCOMPARE(atlas::colour(it.key()), QColor(int(c >> 24 & 0xff), int(c >> 16 & 0xff), int(c >> 8 & 0xff), int(c & 0xff)));
        }
        for (const char *group : {"px", "ms"}) {
            const auto o = doc[group].toObject(); QVERIFY(!o.isEmpty());
            for (auto it = o.begin(); it != o.end(); ++it) QCOMPARE(group[0] == 'p' ? atlas::px(it.key()) : atlas::ms(it.key()), it.value().toInt());
        }
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

    static QImage paint(QWidget &w, QSize size) {
        w.resize(size); QImage img(size, QImage::Format_ARGB32_Premultiplied); img.fill(Qt::transparent); w.render(&img, QPoint(), QRegion(), QWidget::RenderFlags()); return img;
    }
    void button_corners_and_focus_cues() {
        kit::Button b("PLAY"); b.setFixedSize(180, 44);
        auto idle = paint(b, {180, 44});
        QCOMPARE(qAlpha(idle.pixel(0, 0)), 0);                     // the chamfered top-left is empty
        QCOMPARE(qAlpha(idle.pixel(179, 43)), 0);                  // and the bottom-right
        QVERIFY(qAlpha(idle.pixel(179, 4)) > 0);                   // the top-right corner is square
        b.setFocus(Qt::TabFocusReason); QApplication::processEvents();
        b.show(); QApplication::processEvents();                    // focus needs a shown window to take
        auto foc = paint(b, {180, 44});
        const QRectF face = atlas::lifted(QRectF(0, 0, 180, 44).adjusted(0, 0, 0, -3), true);
        const QRectF edge = atlas::frontEdge(face.translated(0, 3), atlas::px("ch-xs"));
        QCOMPARE(QColor(foc.pixel(int(edge.center().x()), int(edge.center().y()))).rgb(), atlas::colour("ember").rgb());   // the ember front edge
        QVERIFY(foc != idle);                                       // lift moved something
    }
    void disabled_is_hatched() {
        kit::Button b("PLAY"); b.setFixedSize(180, 44); b.setEnabled(false);
        const auto img = paint(b, {180, 44});
        int a = 0, c = 0;
        for (int y = 6; y < 36; ++y) for (int x = 6; x < 170; ++x) { QColor p = QColor(img.pixel(x, y)); if (p.rgb() == atlas::colour("plate2").rgb()) ++a; else ++c; }
        QVERIFY(a > 0 && c > 0);                                    // two tones in the face: a hatch, not a flat dim fill
        // and the hatch itself, not only the label, is what breaks the flat fill: look at a strip with no text
        int hatch = 0; for (int x = 6; x < 30; ++x) if (QColor(img.pixel(x, 20)).rgb() != atlas::colour("plate2").rgb()) ++hatch;
        QVERIFY2(hatch > 0, "no hatch lines in a text-free strip of the disabled face");
    }
    void toggle_says_its_state() {
        kit::Toggle t; t.setChecked(false); QCOMPARE(t.stateText(), QString("OFF"));
        t.setChecked(true); QCOMPARE(t.stateText(), QString("ON"));
        QSignalSpy spy(&t, &QAbstractButton::toggled); QTest::keyClick(&t, Qt::Key_Space); QCOMPARE(spy.count(), 1); QVERIFY(!t.isChecked());
        // the lit half is jade on the ON side only
        t.setChecked(true); auto on = paint(t, {74, 24});
        QCOMPARE(QColor(on.pixel(60, 3)).rgb(), atlas::colour("jade").rgb());
        QVERIFY(QColor(on.pixel(12, 3)).rgb() != atlas::colour("jade").rgb());
        t.setChecked(false); auto off = paint(t, {74, 24});
        QVERIFY(QColor(off.pixel(60, 3)).rgb() != atlas::colour("jade").rgb());
    }
    void tab_rail_keys_and_signals() {
        kit::TabRail r({"PLAY", "MODS", "DIAGNOSTICS", "ABOUT"}); r.resize(204, 300); r.show();
        QSignalSpy spy(&r, &kit::TabRail::currentChanged);
        QCOMPARE(r.current(), 0);
        QTest::keyClick(&r, Qt::Key_Down); QCOMPARE(r.current(), 1);
        QTest::keyClick(&r, Qt::Key_Down); QTest::keyClick(&r, Qt::Key_Down); QCOMPARE(r.current(), 3);
        QTest::keyClick(&r, Qt::Key_Down); QCOMPARE(r.current(), 0);          // wraps
        QTest::keyClick(&r, Qt::Key_Up); QCOMPARE(r.current(), 3);
        QTest::mouseClick(&r, Qt::LeftButton, {}, QPoint(20, 20)); QCOMPARE(r.current(), 0);   // the first row's hit rectangle
        QVERIFY(spy.count() >= 5);
        QTest::keyClick(&r, Qt::Key_End); QCOMPARE(r.current(), 3); QTest::keyClick(&r, Qt::Key_Home); QCOMPARE(r.current(), 0);
    }
    void key_chip_and_tag_fit() {
        kit::Tag t("A tag with far too many words in it", kit::Tag::Jade); t.setMaximumWidth(80);
        QVERIFY(t.sizeHint().width() <= 80 + 2);                   // never wider than its cap
        kit::KeyChip k("Ctrl"); QVERIFY(k.sizeHint().height() >= 20);
    }
    void pane_keeps_count_elides_heading() {
        kit::Pane p("A VERY LONG HEADING THAT WILL NOT FIT IN THE PANE WIDTH AT ALL"); p.setFixedWidth(240); p.setCount("123456 discs");
        QImage img = paint(p, {240, 120}); QVERIFY(!img.isNull());
        QFontMetricsF fm(atlas::font(atlas::Role::Cap14));
        QVERIFY(p.property("headingShown").toString().endsWith(QChar(0x2026)));
        QVERIFY(fm.horizontalAdvance(p.property("headingShown").toString()) <= 240 - 16 - QFontMetricsF(atlas::font(atlas::Role::Body12)).horizontalAdvance("123456 discs"));
    }
    void icons_exist() {
        for (auto n : {"disc", "mods", "data", "check", "plus", "right", "left", "up", "down", "star", "x", "folder"}) QVERIFY2(!kit::icon(n).isEmpty(), n);
        QVERIFY(kit::icon("no-such-icon").isEmpty());
    }
    void reduced_motion_is_a_cut() {
        QVERIFY(atlas::motion("m-focus") == 0 || atlas::motion("m-focus") == atlas::ms("m-focus"));
    }

    void layout_four_places_at_three_sizes() {
        QTemporaryDir dir; auto settings = launcher::Settings::load(dir.path());
        for (QSize s : {QSize(900, 600), QSize(960, 640), QSize(1160, 800)}) {
            launcher::Window w(dir.path(), dir.path(), settings); w.resize(s); w.show(); QApplication::processEvents();
            auto *rail = w.findChild<QWidget *>("atlasRail"), *trail = w.findChild<QWidget *>("atlasTrail"), *keys = w.findChild<QWidget *>("atlasKeys");
            QVERIFY(rail && trail && keys);
            QCOMPARE(rail->width(), 204);
            QVERIFY(trail->geometry().bottom() <= rail->geometry().top() + 1);               // trail above the rail
            auto *tabs = w.findChild<QStackedWidget *>("atlasTabs"); QVERIFY(tabs);
            QVERIFY(keys->mapTo(&w, QPoint(0, 0)).y() >= tabs->mapTo(&w, QPoint(0, 0)).y() + tabs->height() - 1);   // keys below the tab bodies
            for (auto *child : w.findChildren<QWidget *>()) {                                // nothing outside the window
                if (!child->isVisible() || child->windowFlags() & Qt::Window) continue;
                const QRect g(child->mapTo(&w, QPoint(0, 0)), child->size());
                QVERIFY2(QRect(QPoint(0, 0), w.size()).adjusted(-1, -1, 1, 1).intersects(g), qPrintable(child->objectName() + " is off the window"));
            }
        }
    }
    void first_run_focus() {                                                                 // no disc yet: something real has focus
        QTemporaryDir dir; launcher::Window w(dir.path(), dir.path(), launcher::Settings::load(dir.path())); w.show(); QApplication::processEvents();
        QVERIFY(QApplication::focusWidget() != nullptr);
        QVERIFY(qobject_cast<QPushButton *>(QApplication::focusWidget()) || qobject_cast<kit::TabRail *>(QApplication::focusWidget()));
    }

    void play_signals() {
        QTemporaryDir dir; auto settings = launcher::Settings::load(dir.path()); launcher::Window w(dir.path(), dir.path(), settings); w.show();
        auto *play = w.findChild<kit::Button *>("atlasPlay"); QVERIFY(play);
        QVERIFY(play->isDefault());                                     // Enter plays
        QCOMPARE(play->text().contains("PLAY"), true);
        auto *discs = w.findChild<QTableWidget *>("atlasDiscs"); QVERIFY(discs);
        QCOMPARE(discs->rowCount(), 0);                                 // first run: empty
        QVERIFY(w.findChild<QPushButton *>("atlasAddDisc")->isEnabled());              // Add disc is always available
        QVERIFY(w.findChild<kit::Toggle *>("opt_unlock_all") && w.findChild<kit::Toggle *>("opt_skip_intro") && w.findChild<kit::Toggle *>("opt_close_on_play"));
        QVERIFY(w.findChild<QSlider *>("atlasVolume"));
    }
    void play_options_write_settings() {                                // the toggles and the slider still write what the checkboxes wrote
        QTemporaryDir dir; launcher::Window w(dir.path(), dir.path(), launcher::Settings::load(dir.path())); w.show();
        auto *skip = w.findChild<kit::Toggle *>("opt_skip_intro"); const bool before = skip->isChecked();
        QTest::keyClick(skip, Qt::Key_Space); QCOMPARE(skip->isChecked(), !before);
        w.findChild<QSlider *>("atlasVolume")->setValue(33);
        auto saved = launcher::Settings::load(dir.path());
        QCOMPARE(saved.option("skip_intro"), QString(before ? "0" : "1"));
        QCOMPARE(saved.option("volume"), QString("33"));
    }
    void play_reasons() {                                               // a hatched button says why
        QTemporaryDir dir; launcher::Window w(dir.path(), dir.path(), launcher::Settings::load(dir.path())); w.show();
        auto *play = w.findChild<kit::Button *>("atlasPlay");
        // with no disc the button stays enabled and opens the add-disc dialog (the old behaviour: play() calls addDisc() when nothing is selected)
        QVERIFY(play->isEnabled());
        QVERIFY(!play->toolTip().isEmpty());                            // "Add a disc first." until a disc exists
    }
    void tab_focus() {
        QTemporaryDir dir; launcher::Window w(dir.path(), dir.path(), launcher::Settings::load(dir.path())); w.show();
        auto *rail = w.findChild<kit::TabRail *>("atlasRail");
        rail->setCurrent(1); QApplication::processEvents();
        QVERIFY(w.findChild<QStackedWidget *>("atlasTabs")->currentIndex() == 1);
        QTest::keyClick(&w, Qt::Key_M, Qt::ControlModifier); QCOMPARE(rail->current(), 1);   // Ctrl+M selects Mods from anywhere
        rail->setCurrent(3); QTest::keyClick(&w, Qt::Key_M, Qt::ControlModifier); QCOMPARE(rail->current(), 1);
        QTest::keyClick(&w, Qt::Key_1, Qt::ControlModifier); QCOMPARE(rail->current(), 0);
    }

    void mods_tab_keeps_its_behaviour() {
        QTemporaryDir dir; QDir(dir.path()).mkpath("mods/demo");
        QFile f(dir.path() + "/mods/demo/mod.json"); QVERIFY(f.open(QIODevice::WriteOnly)); f.write(R"({"id":"demo","name":"Demo","version":"1.0"})"); f.close();
        launcher::Window w(dir.path(), dir.path(), launcher::Settings::load(dir.path())); w.show(); w.selectMods(); QApplication::processEvents();
        auto *mods = w.findChild<QTableWidget *>("atlasMods"); QVERIFY(mods);
        QCOMPARE(mods->rowCount(), 1); QCOMPARE(mods->item(0, 0)->text(), QString("demo"));
        QVERIFY(mods->item(0, 0)->flags() & Qt::ItemIsUserCheckable);                     // the checkbox column is still the toggle
        QVERIFY(w.findChild<QWidget *>("atlasExplainer"));                                // the explainer shows the selected mod
        // toggling the item (what the row's ON/OFF does) writes the mod's enabled state through setModEnabled
        const bool before = mods->item(0, 0)->checkState() == Qt::Checked;
        mods->item(0, 0)->setCheckState(before ? Qt::Unchecked : Qt::Checked); QApplication::processEvents();
        QCOMPARE(mods->item(0, 0)->checkState() == Qt::Checked, !before);                 // survived the refresh the handler runs
        QCOMPARE(launcher::installedMods(launcher::modsDir(dir.path(), dir.path()))[0].enabled, !before);
    }
    void diagnostics_scrolls_not_clips() {
        QTemporaryDir dir; launcher::Window w(dir.path(), dir.path(), launcher::Settings::load(dir.path())); w.resize(900, 600); w.show();
        w.findChild<kit::TabRail *>("atlasRail")->setCurrent(2); QApplication::processEvents();
        auto *scroll = w.findChild<QScrollArea *>("atlasDiagnostics"); QVERIFY(scroll);
        QVERIFY(scroll->widget()->height() > scroll->viewport()->height());               // longer than the window: it scrolls
        QVERIFY(scroll->verticalScrollBar()->maximum() > 0);
        for (auto *b : scroll->widget()->findChildren<QPushButton *>()) QVERIFY2(b->width() > 0 && b->isVisible(), qPrintable(b->text()));
        QVERIFY(scroll->widget()->findChild<kit::Toggle *>("diag_log_scene"));
    }
    void about_has_language_and_licences() {
        QTemporaryDir dir; launcher::Window w(dir.path(), dir.path(), launcher::Settings::load(dir.path())); w.show();
        QVERIFY(w.findChild<QComboBox *>("atlasLanguage"));                               // kept until the owner decides about Spanish
        QVERIFY(w.findChild<QPushButton *>("atlasLicences"));
    }
    void every_tab_fits_at_900_x_600() {
        QTemporaryDir dir; launcher::Window w(dir.path(), dir.path(), launcher::Settings::load(dir.path())); w.resize(900, 600); w.show();
        auto *tabs = w.findChild<QStackedWidget *>("atlasTabs");
        for (int i = 0; i < 4; ++i) {
            w.findChild<kit::TabRail *>("atlasRail")->setCurrent(i); QApplication::processEvents();
            auto *ex = tabs->currentWidget()->findChild<QWidget *>("atlasExplainer"); QVERIFY(ex);
            QVERIFY2(ex->width() >= 240, qPrintable(QString("explainer %1 px wide on tab %2").arg(ex->width()).arg(i)));
            for (auto *p : tabs->currentWidget()->findChildren<QPushButton *>()) {
                if (!p->isVisible() || p->property("clipped").isValid()) continue;
                if (tabs->currentWidget()->findChild<QScrollArea *>("atlasDiagnostics") && tabs->currentWidget()->findChild<QScrollArea *>("atlasDiagnostics")->isAncestorOf(p)) continue;   // scrolls
                const QRect g(p->mapTo(&w, QPoint(0, 0)), p->size());
                QVERIFY2(QRect(QPoint(0, 0), w.size()).contains(g), qPrintable(p->text() + " is cut off on tab " + QString::number(i)));
            }
        }
    }
};
QTEST_MAIN(AtlasTests)
#include "atlas_tests.moc"
