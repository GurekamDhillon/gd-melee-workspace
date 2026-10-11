#include "testfixture.h"
#include "commands.h"
#include "workbench_window.h"
#include "statement_widgets.h"
#include "statement_model.h"
#include "atlas_widgets.h"
#include "window.h"
#include <QLabel>
#include <QListWidget>
#include <QComboBox>
#include <QSpinBox>
#include <QTemporaryDir>
#include <QVBoxLayout>
#include <QtTest>
using namespace wb;

class StatementWidgetsTest : public QObject {
    Q_OBJECT
private slots:
    void initTestCase() { launcher::spanish = false; launcher::applyTheme(); }
    void editingTheInspectorWritesSourceAndUndoRestoresIt() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        const QByteArray script = "throw idx=0 damage=8 unk0=45 hit_x24=70 hit_x2C=30 # keep\n"
            "wait 3\nbody_state state=2\nwait 4\nbody_state state=0\nthrow_flag hit_idx=0\n";
        wbtest::put(d.path(), "moves/jab1.genoasm", script);
        Session session(d.path(), nullptr); QVERIFY(session.data().reload().isEmpty()); registerAllCommands(session);
        WorkbenchWindow window(session); QTRY_VERIFY(!window.isBusy());
        auto *moves = window.findChild<QComboBox *>("wbRows"); QVERIFY(moves);
        moves->setCurrentIndex(moves->findData("jab1")); moves->activated(moves->currentIndex()); QTRY_VERIFY(!window.isBusy());
        auto *list = window.findChild<QListWidget *>("wbStatementList"); QVERIFY(list);
        QCOMPARE(list->count(), 4); list->setCurrentRow(0);
        auto *damage = window.findChild<QSpinBox *>("wbStatement_damage"); QVERIFY(damage);
        QCOMPARE(damage->value(), 8); damage->setValue(11); damage->editingFinished();
        QTRY_VERIFY(!window.isBusy());
        QFile source(d.filePath("moves/jab1.genoasm")); QVERIFY(source.open(QIODevice::ReadOnly));
        QCOMPARE(source.readAll(), QByteArray(script).replace("damage=8", "damage=11")); source.close();
        window.runCommand("undo", {}); QTRY_VERIFY(!window.isBusy());
        QVERIFY(source.open(QIODevice::ReadOnly)); QCOMPARE(source.readAll(), script);
    }
    void retimingKeepsTheEditedStatementSelected() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path());
        wbtest::put(d.path(), "moves/jab1.genoasm", "wait 3\nbody_state state=1\nwait 2\nhurtbox_state bone=3 state=2\n");
        Session session(d.path(), nullptr); QVERIFY(session.data().reload().isEmpty()); registerAllCommands(session);
        WorkbenchWindow window(session); QTRY_VERIFY(!window.isBusy());
        auto *moves = window.findChild<QComboBox *>("wbRows"); QVERIFY(moves);
        moves->setCurrentIndex(moves->findData("jab1")); moves->activated(moves->currentIndex()); QTRY_VERIFY(!window.isBusy());
        auto *frame = window.findChild<QSpinBox *>("wbStatement_frame"); QVERIFY(frame);
        QCOMPARE(frame->value(), 3); frame->setValue(6); frame->editingFinished(); QTRY_VERIFY(!window.isBusy());
        auto *list = window.findChild<QListWidget *>("wbStatementList"); QVERIFY(list);
        QCOMPARE(list->currentItem()->data(Qt::UserRole).toInt(), 1);
        auto *state = window.findChild<QComboBox *>("wbStatement_state"); QVERIFY(state);
        state->setCurrentIndex(state->findData(0)); state->activated(state->currentIndex()); QTRY_VERIFY(!window.isBusy());
        const auto values = session.data().statements("jab1");
        QCOMPARE(values[0].toObject()["fields"].toObject()["state"].toInt(), 2);
        QCOMPARE(values[1].toObject()["fields"].toObject()["state"].toInt(), 0);
    }
    void panelUsesCanonicalValuesAndPreservesAnUncommittedDraft() {
        StatementsPanel panel; applyAtlasStyle(&panel);
        const QJsonArray values{QJsonObject{{"ordinal", 0}, {"kind", "hurtbox_state"}, {"frame", 3}, {"end_frame", 7},
            {"editable", true}, {"timing_editable", true}, {"fields", QJsonObject{{"bone", "@HAND_R@"}, {"state", 2}}}}};
        const QJsonObject standIn{{"value", "captain"}, {"choices", QJsonArray{"captain", "fox"}}, {"editable", true}};
        panel.setData("jab1", values, standIn, {{"HAND_R", "hand.R", "arm"}});
        QSignalSpy edits(&panel, &StatementsPanel::editRequested), adds(&panel, &StatementsPanel::addRequested);
        auto *bone = panel.findChild<QComboBox *>("wbStatement_bone"); QVERIFY(bone);
        bone->setEditText("12"); panel.setData("jab1", values, standIn, {{"HAND_R", "hand.R", "arm"}});
        QCOMPARE(bone->currentText(), QString("12")); QCOMPARE(edits.size(), 0);
        panel.findChild<QPushButton *>("wbRestoreHurtState")->click(); QCOMPARE(adds.size(), 1);
        QCOMPARE(adds[0][0].toString(), QString("hurtbox_state"));
        QCOMPARE(adds[0][1].toJsonObject(), (QJsonObject{{"bone", "@HAND_R@"}, {"state", 0}}));
        auto *choice = panel.findChild<QComboBox *>("wbThrowStandIn"); choice->setCurrentIndex(1); choice->activated(1);
        QCOMPARE(edits.size(), 1); QCOMPARE(edits[0][0].toString(), QString("edit_throw_standin"));
        QCOMPARE(edits[0][1].toJsonObject()["value"].toString(), QString("fox"));
        panel.resize(350, 880); panel.show(); QCoreApplication::processEvents();
        if (!qEnvironmentVariable("WB_WIDGET_CAPTURE").isEmpty()) QVERIFY(panel.grab().save(qEnvironmentVariable("WB_WIDGET_CAPTURE")));
    }
    void unknownSourceIsReadOnlyAndChangingRowsClearsSelection() {
        StatementsPanel panel;
        const QJsonArray values{QJsonObject{{"ordinal", 0}, {"kind", "body_state"}, {"frame", -1}, {"editable", false},
            {"timing_editable", false}, {"note", "Opaque source"}, {"fields", QJsonObject{{"state", 91}}}}};
        panel.setData("jab1", values, {}, {});
        QVERIFY(!panel.findChild<QComboBox *>("wbStatement_state")->isEnabled());
        QVERIFY(!panel.findChild<QSpinBox *>("wbStatement_frame")->isEnabled());
        QCOMPARE(panel.findChild<QLabel *>("wbStatementNote")->text(), QString("Opaque source"));
        panel.setData("dair", {}, {}, {});
        QCOMPARE(panel.findChild<QListWidget *>("wbStatementList")->count(), 0);
    }
    void fieldsFitANarrowInspector_data() {
        QTest::addColumn<bool>("spanish"); QTest::addColumn<QString>("source");
        for (const bool spanish : {false, true}) {
            QTest::newRow(spanish ? "throw-es" : "throw-en") << spanish << QString("throw damage=8 angle=361 kbg=100 bkb=30");
            QTest::newRow(spanish ? "hurt-es" : "hurt-en") << spanish << QString("hurtbox_state bone=3 state=2");
        }
    }
    void fieldsFitANarrowInspector() {
        QFETCH(bool, spanish); QFETCH(QString, source);
        launcher::spanish = spanish;
        StatementsPanel panel; applyAtlasStyle(&panel);
        panel.setData("jab1", StatementModel::parse(source).statements(), {}, {});
        panel.resize(350, 1100); panel.show(); QCoreApplication::processEvents();
        launcher::spanish = false;
        QVERIFY2(panel.minimumSizeHint().width() <= 350, qPrintable(QString("Panel requires %1px").arg(panel.minimumSizeHint().width())));
        const auto directory = qEnvironmentVariable("WB_STATEMENT_SHOTS");
        if (!directory.isEmpty()) QVERIFY(panel.grab().save(QDir(directory).filePath(QString::fromLatin1(QTest::currentDataTag()) + ".png")));
    }
    void hurtLanesShareRulerBoundariesAndSelectSource() {
        QWidget shell; auto *layout = new QVBoxLayout(&shell);
        auto *timeline = new TimelineView; auto *lanes = new HurtStateLanes; layout->addWidget(timeline); layout->addWidget(lanes);
        timeline->setMove("jab1", 30, {}, 20); lanes->setTimeline(timeline);
        lanes->setWindows({QJsonObject{{"ordinal", 0}, {"kind", "body_state"}, {"state", 1}, {"start_frame", 3}, {"end_frame", 7}},
                           QJsonObject{{"ordinal", 2}, {"kind", "hurtbox_state"}, {"bone", "3"}, {"bone_identity", "3"}, {"state", 2}, {"start_frame", 5}, {"end_frame", -1}},
                           QJsonObject{{"ordinal", 3}, {"kind", "hurtbox_state"}, {"bone", "@HAND_R@"}, {"bone_identity", "3"}, {"state", 1}, {"start_frame", 1}, {"end_frame", 3}}});
        QSignalSpy selected(lanes, &HurtStateLanes::statementSelected);
        for (int width : {900, 340}) {
            shell.resize(width, 280); shell.show(); QCoreApplication::processEvents();
            QCOMPARE(lanes->windowCount(), 3);
            const auto bar = lanes->windowRect(0);
            const auto boundary = lanes->mapFromGlobal(timeline->mapToGlobal(QPoint(qRound(timeline->framePosition(3)), 0)));
            QVERIFY(qAbs(bar.left() - boundary.x()) <= 1);
            const auto open = lanes->windowRect(2);
            QVERIFY(open.top() > bar.top());
            QCOMPARE(lanes->windowRect(3).top(), open.top());
            QVERIFY(qAbs(open.right() - lanes->mapFromGlobal(timeline->mapToGlobal(QPoint(qRound(timeline->framePosition(30)), 0))).x()) <= 1);
            QTest::mouseClick(lanes, Qt::LeftButton, {}, open.center().toPoint());
            QCOMPARE(selected.last()[0].toInt(), 2);
        }
    }
};
QTEST_MAIN(StatementWidgetsTest)
#include "statement_widgets_test.moc"
