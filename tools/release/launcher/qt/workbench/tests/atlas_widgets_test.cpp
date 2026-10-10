#include "atlas_widgets.h"
#include "atlas.h"
#include "window.h"
#include <QApplication>
#include <QFile>
#include <QFontDatabase>
#include <QFontInfo>
#include <QJsonDocument>
#include <QLabel>
#include <QProgressBar>
#include <QPalette>
#include <QSignalSpy>
#include <QtTest>

using namespace wb;
namespace atlas = launcher::atlas;

namespace {
HitboxRef hit(int ordinal, int start, int end, int slot = 0) {
    HitboxRef h; h.ordinal = ordinal; h.slot = slot; h.joint = "HAND_R";
    h.startFrame = start; h.endFrame = end; return h;
}
void showTimeline(TimelineView &view) {
    view.resize(780, view.sizeHint().height()); view.show(); QApplication::processEvents();
}
QPoint edgePoint(const TimelineView &view, int ordinal, bool end) {
    const auto bar = view.hitboxRect(ordinal);
    return QPoint(qRound(end ? bar.right() : bar.left()), qRound(bar.center().y()));
}
void moveEdge(TimelineView &view, int ordinal, bool end, int boundary) {
    QTest::mousePress(&view, Qt::LeftButton, Qt::NoModifier, edgePoint(view, ordinal, end));
    QTest::mouseMove(&view, QPoint(qRound(view.framePosition(boundary)), edgePoint(view, ordinal, end).y()));
    QTest::mouseRelease(&view, Qt::LeftButton, Qt::NoModifier,
        QPoint(qRound(view.framePosition(boundary)), edgePoint(view, ordinal, end).y()));
}
}

class AtlasWidgetsTest : public QObject {
    Q_OBJECT
private slots:
    void initTestCase() { launcher::spanish = false; atlas::initialize(); }
    void everyColourMatchesTheEmbeddedSource() {
        QFile source(":/atlas/tokens.json"); QVERIFY(source.open(QIODevice::ReadOnly));
        const auto colours = QJsonDocument::fromJson(source.readAll()).object()["colours"].toObject();
        QVERIFY(!colours.isEmpty());
        QFile checkedIn(QString::fromUtf8(ATLAS_TOKENS_JSON)); QVERIFY(checkedIn.open(QIODevice::ReadOnly));
        QCOMPARE(colours, QJsonDocument::fromJson(checkedIn.readAll()).object()["colours"].toObject());
        for (auto it = colours.begin(); it != colours.end(); ++it) {
            const quint32 packed = quint32(it.value().toDouble());
            const QColor expected(int((packed >> 24) & 255), int((packed >> 16) & 255),
                                  int((packed >> 8) & 255), int(packed & 255));
            QCOMPARE(atlas::colour(it.key()), expected);
        }
        QVERIFY(!atlas::colour("unknown-token").isValid());
    }
    void scopedStylePreservesExplicitLabelTones() {
        QWidget root;
        QLabel label("Status", &root);
        auto palette = label.palette(); palette.setColor(QPalette::WindowText, atlas::colour("jade"));
        label.setPalette(palette);
        applyAtlasStyle(&root); root.ensurePolished(); label.ensurePolished();
        QCOMPARE(label.palette().color(QPalette::WindowText), atlas::colour("jade"));
    }
    void numberFontIsEmbeddedAndLoaded() {
        QVERIFY(QFile::exists(":/fonts/hasklug-medium.otf"));
        const auto number = atlas::numberFont(19);
        QCOMPARE(number.pixelSize(), 19);
        QVERIFY(number.family().contains("Hasklug", Qt::CaseInsensitive));
        QVERIFY(QFontDatabase::families().contains(number.family()));
        QVERIFY(QFontInfo(number).family().contains("Hasklug", Qt::CaseInsensitive));
        NumberField field; QCOMPARE(field.font().family(), atlas::numberFont().family());
    }
    void endDragSendsOneExclusiveWindowForTheOrdinal() {
        TimelineView view; view.setMove("jab1", 20, {hit(7, 3, 6, 1)}, 12); showTimeline(view);
        QSignalSpy edits(&view, &TimelineView::editRequested);
        QSignalSpy selections(&view, &TimelineView::hitboxSelected);
        const auto end = edgePoint(view, 7, true);
        QTest::mousePress(&view, Qt::LeftButton, Qt::NoModifier, end);
        const auto destination = QPoint(qRound(view.framePosition(9)), end.y());
        QTest::mouseMove(&view, destination); QVERIFY(edits.isEmpty());
        QTest::mouseRelease(&view, Qt::LeftButton, Qt::NoModifier, destination);
        QCOMPARE(edits.size(), 1); QCOMPARE(edits[0][0].toString(), QString("edit_hitbox"));
        const QJsonObject expected{{"row", "jab1"}, {"ordinal", 7}, {"start_frame", 3}, {"end_frame", 9}};
        QCOMPARE(edits[0][1].value<QJsonObject>(), expected);
        QCOMPARE(selections.size(), 1); QCOMPARE(selections[0][0].toInt(), 7);
    }
    void handlesClampToNonemptyMoveBounds() {
        TimelineView view; view.setMove("jab1", 20, {hit(2, 3, 6)}, 12); showTimeline(view);
        QSignalSpy edits(&view, &TimelineView::editRequested);
        moveEdge(view, 2, false, 15);
        QCOMPARE(edits.last()[1].value<QJsonObject>()["start_frame"].toInt(), 5);
        view.setMove("jab1", 20, {hit(2, 3, 6)}, 12);
        moveEdge(view, 2, true, 0);
        QCOMPARE(edits.last()[1].value<QJsonObject>()["end_frame"].toInt(), 4);
        view.setMove("jab1", 20, {hit(2, 3, 6)}, 12);
        moveEdge(view, 2, true, 20);
        QCOMPARE(edits.last()[1].value<QJsonObject>()["end_frame"].toInt(), 20);
    }
    void unchangedAndEscapeCancelledDragsSendNothing() {
        TimelineView view; view.setMove("jab1", 20, {hit(0, 3, 6)}, 0); showTimeline(view);
        QSignalSpy edits(&view, &TimelineView::editRequested);
        QTest::mouseClick(&view, Qt::LeftButton, Qt::NoModifier, edgePoint(view, 0, true));
        QVERIFY(edits.isEmpty());
        const auto original = view.hitboxRect(0);
        const auto end = edgePoint(view, 0, true);
        QTest::mousePress(&view, Qt::LeftButton, Qt::NoModifier, end);
        QTest::mouseMove(&view, QPoint(qRound(view.framePosition(10)), end.y()));
        QTest::keyClick(&view, Qt::Key_Escape);
        QTest::mouseRelease(&view, Qt::LeftButton, Qt::NoModifier, end);
        QVERIFY(edits.isEmpty()); QCOMPARE(view.hitboxRect(0), original);
    }
    void incomingSnapshotDoesNotReplaceTheDragPreview() {
        TimelineView view; const QVector<HitboxRef> hits{hit(3, 3, 6)};
        view.setMove("jab1", 20, hits, 10); showTimeline(view);
        QSignalSpy edits(&view, &TimelineView::editRequested);
        const auto end = edgePoint(view, 3, true);
        QTest::mousePress(&view, Qt::LeftButton, Qt::NoModifier, end);
        const auto destination = QPoint(qRound(view.framePosition(9)), end.y());
        QTest::mouseMove(&view, destination);
        view.setMove("jab1", 20, hits, 10);
        QVERIFY(qAbs(view.hitboxRect(3).right() - view.framePosition(9)) < 1);
        QTest::mouseRelease(&view, Qt::LeftButton, Qt::NoModifier, destination);
        QCOMPARE(edits.size(), 1);
        QCOMPARE(edits[0][1].value<QJsonObject>()["end_frame"].toInt(), 9);
    }
    void deletingEarlierHitboxCancelsDragBeforeOrdinalsAreReused() {
        TimelineView view; const QVector<HitboxRef> original{hit(0, 1, 3), hit(1, 4, 7), hit(2, 9, 12)};
        view.setMove("jab1", 20, original, 0); showTimeline(view);
        QSignalSpy edits(&view, &TimelineView::editRequested);
        const auto end = edgePoint(view, 1, true);
        const auto destination = QPoint(qRound(view.framePosition(8)), end.y());
        QTest::mousePress(&view, Qt::LeftButton, Qt::NoModifier, end);
        QTest::mouseMove(&view, destination);
        // Deleting HB0 renumbers the old HB2 to HB1, the ordinal held by this drag.
        QVector<HitboxRef> renumbered{original[1], original[2]};
        renumbered[0].ordinal = 0; renumbered[1].ordinal = 1;
        view.setMove("jab1", 20, renumbered, 0);
        QCOMPARE(view.hitboxRect(1).left(), view.framePosition(9));
        QCOMPARE(view.hitboxRect(1).right(), view.framePosition(12));
        QTest::mouseRelease(&view, Qt::LeftButton, Qt::NoModifier, destination);
        QVERIFY(edits.isEmpty());
    }
    void reorderedElementsCancelDragEvenWhenOrdinalsAndWindowsMatch() {
        TimelineView view; QVector<HitboxRef> original{hit(0, 3, 6), hit(1, 3, 6)};
        original[0].element = 1; original[1].element = 2;
        view.setMove("jab1", 20, original, 0); showTimeline(view);
        QSignalSpy edits(&view, &TimelineView::editRequested);
        const auto end = edgePoint(view, 1, true);
        const auto destination = QPoint(qRound(view.framePosition(9)), end.y());
        QTest::mousePress(&view, Qt::LeftButton, Qt::NoModifier, end);
        QTest::mouseMove(&view, destination);
        QVector<HitboxRef> reordered{original[1], original[0]};
        reordered[0].ordinal = 0; reordered[1].ordinal = 1;
        view.setMove("jab1", 20, reordered, 0);
        QCOMPARE(view.hitboxRect(1).right(), view.framePosition(6));
        QTest::mouseRelease(&view, Qt::LeftButton, Qt::NoModifier, destination);
        QVERIFY(edits.isEmpty());
    }
    void changedSourceWindowCancelsDrag() {
        TimelineView view; view.setMove("jab1", 20, {hit(0, 3, 6)}, 0); showTimeline(view);
        QSignalSpy edits(&view, &TimelineView::editRequested);
        const auto end = edgePoint(view, 0, true);
        const auto destination = QPoint(qRound(view.framePosition(9)), end.y());
        QTest::mousePress(&view, Qt::LeftButton, Qt::NoModifier, end);
        QTest::mouseMove(&view, destination);
        view.setMove("jab1", 20, {hit(0, 4, 7)}, 0);
        QCOMPARE(view.hitboxRect(0).left(), view.framePosition(4));
        QCOMPARE(view.hitboxRect(0).right(), view.framePosition(7));
        QTest::mouseRelease(&view, Qt::LeftButton, Qt::NoModifier, destination);
        QVERIFY(edits.isEmpty());
    }
    void changedMoveLengthCancelsDrag() {
        TimelineView view; const QVector<HitboxRef> hits{hit(0, 3, 6)};
        view.setMove("jab1", 20, hits, 0); showTimeline(view);
        QSignalSpy edits(&view, &TimelineView::editRequested);
        const auto end = edgePoint(view, 0, true);
        const auto destination = QPoint(qRound(view.framePosition(9)), end.y());
        QTest::mousePress(&view, Qt::LeftButton, Qt::NoModifier, end);
        QTest::mouseMove(&view, destination);
        view.setMove("jab1", 30, hits, 0); QCOMPARE(view.frameCount(), 30);
        QTest::mouseRelease(&view, Qt::LeftButton, Qt::NoModifier, destination);
        QVERIFY(edits.isEmpty());
    }
    void changingMoveCancelsTheOldDrag() {
        TimelineView view; view.setMove("jab1", 20, {hit(0, 3, 6)}, 0); showTimeline(view);
        QSignalSpy edits(&view, &TimelineView::editRequested);
        const auto end = edgePoint(view, 0, true);
        QTest::mousePress(&view, Qt::LeftButton, Qt::NoModifier, end);
        QTest::mouseMove(&view, QPoint(qRound(view.framePosition(9)), end.y()));
        view.setMove("jab2", 15, {hit(0, 2, 4)}, 0);
        QTest::mouseRelease(&view, Qt::LeftButton, Qt::NoModifier, end);
        QVERIFY(edits.isEmpty());
    }
    void openEndIsPreservedUntilTheEndHandleMoves() {
        TimelineView view; view.setMove("jab1", 20, {hit(4, 3, -1)}, 0); showTimeline(view);
        QSignalSpy edits(&view, &TimelineView::editRequested);
        moveEdge(view, 4, false, 5);
        const auto startEdit = edits.last()[1].value<QJsonObject>();
        QCOMPARE(startEdit["start_frame"].toInt(), 5); QVERIFY(!startEdit.contains("end_frame"));
        view.setMove("jab1", 20, {hit(4, 3, -1)}, 0);
        moveEdge(view, 4, true, 12);
        QCOMPARE(edits.last()[1].value<QJsonObject>()["end_frame"].toInt(), 12);
    }
    void rulerAndKeyboardRequestFramesWithoutEchoingFeedback() {
        TimelineView view; view.setMove("jab1", 20, {}, 0); showTimeline(view);
        QSignalSpy frames(&view, &Timeline::frameRequested), playing(&view, &Timeline::playToggled);
        Timeline *legacy = &view; legacy->setFrame(4); legacy->setPlaying(true);
        QVERIFY(frames.isEmpty()); QVERIFY(playing.isEmpty());
        QTest::keyClick(&view, Qt::Key_Right); QTest::keyClick(&view, Qt::Key_Left);
        QTest::keyClick(&view, Qt::Key_L); QTest::keyClick(&view, Qt::Key_J);
        QCOMPARE(frames.size(), 4); QCOMPARE(frames[0][0].toInt(), 5); QCOMPARE(frames[3][0].toInt(), 4);
        QTest::keyClick(&view, Qt::Key_Home); QCOMPARE(view.frame(), 0);
        QTest::keyClick(&view, Qt::Key_End); QCOMPARE(view.frame(), 19);
        QTest::keyClick(&view, Qt::Key_Space); QTest::keyClick(&view, Qt::Key_K);
        QCOMPARE(playing.size(), 2); QVERIFY(!playing[0][0].toBool()); QVERIFY(playing[1][0].toBool());
        const qreal centre = (view.framePosition(8) + view.framePosition(9)) / 2;
        QTest::mouseClick(&view, Qt::LeftButton, Qt::NoModifier,
                          QPoint(qRound(centre), qRound(view.rulerRect().center().y())));
        QCOMPARE(view.frame(), 8); QCOMPARE(frames.last()[0].toInt(), 8);
    }
    void emptyAndMalformedRangesAreNotEditable() {
        TimelineView view; view.setMove("jab1", 20,
            {hit(0, -1, 3), hit(1, 6, 5), hit(2, 20, 21), hit(3, 2, 40), hit(4, 3, -2)}, 0);
        showTimeline(view); QSignalSpy edits(&view, &TimelineView::editRequested);
        for (int ordinal = 0; ordinal < 5; ++ordinal) QVERIFY(view.hitboxRect(ordinal).isEmpty());
        QVERIFY(view.hitboxRect(99).isEmpty());
        Timeline *legacy = &view; legacy->setRange(-10); QCOMPARE(view.frameCount(), 0);
        QSignalSpy frames(&view, &Timeline::frameRequested), playing(&view, &Timeline::playToggled);
        QTest::keyClick(&view, Qt::Key_End); QTest::keyClick(&view, Qt::Key_Space);
        QTest::mouseClick(&view, Qt::LeftButton, Qt::NoModifier, QPoint(400, 20));
        QVERIFY(frames.isEmpty()); QVERIFY(playing.isEmpty()); QVERIFY(edits.isEmpty());
    }
    void progressStaysIndeterminateUntilTheBackendReportsAPercent() {
        StatusProgress status; status.show();
        auto *bar = status.findChild<QProgressBar *>("wbRebuildProgressBar"); QVERIFY(bar);
        auto *elapsed = status.findChild<QLabel *>("wbRebuildElapsed"); QVERIFY(elapsed);
        auto *cancel = status.findChild<AtlasButton *>("wbRebuildCancel"); QVERIFY(cancel);
        QSignalSpy requests(&status, &StatusProgress::cancelRequested);
        status.begin("Compiling", false); QVERIFY(status.isRunning());
        QCOMPARE(bar->minimum(), 0); QCOMPARE(bar->maximum(), 0); QVERIFY(cancel->isVisible()); QVERIFY(!cancel->isEnabled());
        QVERIFY(!cancel->toolTip().isEmpty());
        status.setProgress("Linking", 42, 1200, true);
        QCOMPARE(bar->maximum(), 100); QCOMPARE(bar->value(), 42); QVERIFY(cancel->isVisible());
        const auto reported = elapsed->text(); QTRY_VERIFY(elapsed->text() != reported);
        cancel->click(); QCOMPARE(requests.size(), 1); QVERIFY(status.isRunning());
        status.setProgress("Cancelling", 42, -1, true); QVERIFY(!cancel->isEnabled());
        status.finish("Finished"); QVERIFY(!status.isRunning()); QCOMPARE(bar->value(), 100);
        QVERIFY(!cancel->isVisible());
    }
};
QTEST_MAIN(AtlasWidgetsTest)
#include "atlas_widgets_test.moc"
