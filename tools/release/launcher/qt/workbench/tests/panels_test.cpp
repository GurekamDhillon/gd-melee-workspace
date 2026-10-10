#include "window.h"
#define WB_CORE_USE_LAUNCHER_T 1
#include "commands.h"
#include "../testfixture.h"
#include "panels.h"
#include "session.h"
#include "timeline.h"
#include "workbench_window.h"
#include <QComboBox>
#include <QDoubleSpinBox>
#include <QLabel>
#include <QJsonDocument>
#include <QLineEdit>
#include <QPushButton>
#include <QSemaphore>
#include <atomic>
#include <QSignalSpy>
#include <QTemporaryDir>
#include <QtTest>
using namespace wb;

class PanelEngine : public wbtest::FakeEngine {
public:
    QJsonObject call(const QString &fn, const QJsonObject &args, QString *error) override {
        const auto result = FakeEngine::call(fn, args, error);
        if (fn != "frame" || !failWith.isEmpty()) return result;
        FrameInfo info; info.frame = args["frame"].toInt(); info.motion = args["motion"].toInt();
        info.hitboxes = {{0, 3, {}, 2.4, {0, 8, 0}, true}};
        return info.toJson();
    }
};

class DelayedPanelEngine : public PanelEngine {
public:
    QSemaphore entered, release;
    std::atomic<bool> blockNext{false};
    QJsonObject call(const QString &fn, const QJsonObject &args, QString *error) override {
        if (blockNext.exchange(false)) {
            entered.release(); release.tryAcquire(1, 3000);
        }
        return PanelEngine::call(fn, args, error);
    }
};

class PanelsTest : public QObject {
    Q_OBJECT
private slots:
    void initTestCase() { launcher::spanish = false; launcher::applyTheme(); }
    void outlinerShowsRowsAndHitboxes() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); Session s(d.path(), nullptr);
        QVERIFY(s.data().reload().isEmpty()); registerAllCommands(s);
        OutlinerPanel o; o.setSession(s); o.refresh();
        QCOMPARE(o.topLevelItemCount(), 2);
        QCOMPARE(o.topLevelItem(1)->text(0), QString("dair"));
        QCOMPARE(o.topLevelItem(1)->childCount(), 2);
        QSignalSpy spy(&o, &OutlinerPanel::hitboxSelected);
        o.setCurrentItem(o.topLevelItem(1)->child(1));
        QCOMPARE(spy.size(), 1); QCOMPARE(spy[0][0].toString(), QString("dair"));
        QCOMPARE(spy[0][1].toInt(), 1);
    }
    void outlinerRefreshKeepsSelectionWithoutIssuingCommands() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); Session s(d.path(), nullptr);
        QVERIFY(s.data().reload().isEmpty()); OutlinerPanel o; o.setSession(s); o.refresh();
        o.setCurrentItem(o.topLevelItem(1)->child(1));
        QSignalSpy hits(&o, &OutlinerPanel::hitboxSelected), rows(&o, &OutlinerPanel::rowSelected);
        o.refresh(); QVERIFY(hits.isEmpty()); QVERIFY(rows.isEmpty());
        QCOMPARE(o.currentItem(), o.topLevelItem(1)->child(1));
        o.setCurrentItem(o.topLevelItem(0)); QCOMPARE(rows.size(), 1);
        QCOMPARE(rows[0][0].toString(), QString("jab1"));
    }

    void moveRailFilteringAndBadgesKeepHitboxIdentity() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); Session s(d.path(), nullptr);
        QVERIFY(s.data().reload().isEmpty()); OutlinerPanel o; o.setSession(s); o.setGrouped(true); o.refresh();
        o.setSelection("dair", 1); o.setBadges({"jab1"}, {{"dair", 2}});
        QSignalSpy hits(&o, &OutlinerPanel::hitboxSelected), rows(&o, &OutlinerPanel::rowSelected);
        o.setFilter("DAIR");
        QVERIFY(o.topLevelItem(0)->isHidden()); QVERIFY(!o.topLevelItem(1)->isHidden());
        QVERIFY(o.topLevelItem(0)->toolTip(0).contains("edited"));
        QVERIFY(o.topLevelItem(1)->toolTip(0).contains("2 warnings"));
        o.refresh(); QVERIFY(o.topLevelItem(0)->isHidden());
        QCOMPARE(o.currentItem(), o.topLevelItem(1)->child(1));
        QVERIFY(hits.isEmpty()); QVERIFY(rows.isEmpty());
        o.setFilter("SYN_ATC_002"); QVERIFY(!o.topLevelItem(0)->isHidden()); QVERIFY(o.topLevelItem(1)->isHidden());
        o.setFilter({}); QCOMPARE(o.currentItem(), o.topLevelItem(1)->child(1));
        o.setCurrentItem(o.topLevelItem(1)->child(0));
        QCOMPARE(hits.size(), 1); QCOMPARE(hits[0][0].toString(), QString("dair")); QCOMPARE(hits[0][1].toInt(), 0);
    }
    void inspectorRolesPreserveDraftAndDeleteSelectedOccurrence() {
        InspectorPanel p; HitboxRef h; h.ordinal = 1; h.slot = 0; h.joint = "FOOT_L";
        p.showHitbox("dair", h); QSignalSpy edits(&p, &InspectorPanel::editRequested);
        auto *bone = p.findChild<QLineEdit *>("wbHitbox_bone"); QVERIFY(bone); bone->setText("TAIL");
        p.setRoles({{"HAND_R", "hand.R", "arms"}, {"FOOT_L", "foot.L", "legs"}});
        QCOMPARE(bone->text(), QString("TAIL")); QVERIFY(edits.isEmpty());
        auto *joint = p.findChild<QComboBox *>("wbHitboxJoint"); QVERIFY(joint);
        const int hand = joint->findText("HAND_R"); QVERIFY(hand >= 0);
        joint->setCurrentIndex(hand); joint->activated(hand);
        QCOMPARE(edits.size(), 1); QCOMPARE(edits[0][1].toJsonObject()["bone"].toString(), QString("HAND_R"));
        auto *remove = p.findChild<QPushButton *>("wbDeleteHitbox"); QVERIFY(remove); remove->click();
        QCOMPARE(edits.size(), 2); QCOMPARE(edits[1][0].toString(), QString("delete_hitbox"));
        QCOMPARE(edits[1][1].toJsonObject(), (QJsonObject{{"row", "dair"}, {"ordinal", 1}}));
        p.clear(); remove->click(); QCOMPARE(edits.size(), 2);
    }
    void inspectorElementEditsUseSourceCodeAndFeedbackIsSilent() {
        InspectorPanel p; HitboxRef h; h.joint = "HAND_R"; h.element = 3; p.showHitbox("jab1", h);
        QSignalSpy edits(&p, &InspectorPanel::editRequested);
        auto *element = p.findChild<QComboBox *>("wbHitbox_element"); QVERIFY(element);
        QCOMPARE(element->currentData().toInt(), 3);
        const int normal = element->findData(0); QVERIFY(normal >= 0);
        element->setCurrentIndex(normal); element->activated(normal);
        QCOMPARE(edits.size(), 1);
        QCOMPARE(edits[0][1].toJsonObject(), (QJsonObject{{"row", "jab1"}, {"ordinal", 0}, {"element", 0}}));
        p.setField("element", 32); p.setField("element", -1); p.setField("element", 1.5); QCOMPARE(edits.size(), 1);
        h.element = 31; p.showHitbox("jab1", h); QCOMPARE(element->currentData().toInt(), 31); QCOMPARE(edits.size(), 1);
    }
    void inspectorChecksAndExplanationOnlyShowSuppliedEvidence() {
        InspectorPanel p; HitboxRef h; p.showHitbox("jab1", h);
        auto *explanation = p.findChild<QLabel *>("wbHitExplanation"); QVERIFY(explanation); QVERIFY(explanation->isHidden());
        p.setExplanation("Measured against the selected target"); QVERIFY(!explanation->isHidden());
        QCOMPARE(explanation->text(), QString("Measured against the selected target"));
        p.setRowChecks({{"bounds", "dair", "Wrong row", 0}, {"bounds", "jab1", "Source window exceeds clip", 0}}, true);
        auto *checks = p.findChild<QLabel *>("wbHitboxRowChecks"); QVERIFY(checks);
        QVERIFY(checks->text().contains("Source window exceeds clip")); QVERIFY(!checks->text().contains("Wrong row"));
        p.showHitbox("dair", h); QVERIFY(explanation->isHidden());
        p.setRowChecks({}, false); QVERIFY(!checks->text().contains("No issues"));
    }
    void attributesRespectSchemaAndEmitOnlyExplicitEdits() {
        AttributesPanel p;
        const QJsonArray attributes{
            QJsonObject{{"name", "weight"}, {"value", 90}, {"type", "number"}, {"group", "misc"}, {"unit", "weight"},
                {"range", QJsonObject{{"minimum", 1}, {"maximum", 999}}}},
            QJsonObject{{"name", "jumps.max"}, {"value", QJsonValue(QJsonValue::Null)}, {"type", "integer"}, {"group", "jump"}, {"unit", "count"},
                {"range", QJsonObject{{"minimum", 1}, {"maximum", 8}}}}};
        QSignalSpy edits(&p, &AttributesPanel::editRequested); p.setAttributes(attributes); QVERIFY(edits.isEmpty());
        auto *weight = p.findChild<QDoubleSpinBox *>("wbAttribute_weight"); QVERIFY(weight);
        QCOMPARE(weight->minimum(), 1.0); QCOMPARE(weight->maximum(), 999.0); QCOMPARE(weight->value(), 90.0);
        auto *jumps = p.findChild<QDoubleSpinBox *>("wbAttribute_jumps.max"); QVERIFY(jumps); QCOMPARE(jumps->decimals(), 0);
        QCOMPARE(jumps->cleanText(), QString()); jumps->editingFinished(); QVERIFY(edits.isEmpty());
        auto *text = jumps->findChild<QLineEdit *>(); QVERIFY(text);
        p.show(); text->setFocus(); QTest::keyClicks(text, "3"); QTest::keyClick(text, Qt::Key_Return);
        QCOMPARE(edits.size(), 1); QCOMPARE(edits[0][0].toString(), QString("edit_attribute"));
        QCOMPARE(edits[0][1].toJsonObject(), (QJsonObject{{"name", "jumps.max"}, {"value", 3}}));
        p.setAttributes(attributes); QCOMPARE(edits.size(), 1); QCOMPARE(jumps->cleanText(), QString());
    }

    void attributesUnsetValueCanBeExplicitlySetToZero() {
        AttributesPanel p;
        const QJsonObject descriptor{{"name", "landing_lag"}, {"value", QJsonValue(QJsonValue::Null)},
            {"type", "number"}, {"group", "landing"}, {"unit", "frames"},
            {"range", QJsonObject{{"minimum", 0}, {"maximum", 100}}}};
        p.setAttributes({descriptor}); p.show();
        auto *field = p.findChild<QDoubleSpinBox *>("wbAttribute_landing_lag"); QVERIFY(field);
        auto *text = field->findChild<QLineEdit *>(); QVERIFY(text);
        QSignalSpy edits(&p, &AttributesPanel::editRequested); text->setFocus(); QTest::keyClicks(text, "0"); QTest::keyClick(text, Qt::Key_Return);
        QCOMPARE(edits.size(), 1);
        QCOMPARE(edits[0][1].toJsonObject(), (QJsonObject{{"name", "landing_lag"}, {"value", 0}}));
        p.setAttributes({descriptor}); QCOMPARE(field->cleanText(), QString()); QCOMPARE(edits.size(), 1);
    }
    void attributesFeedbackPreservesUnsubmittedNumericDraft() {
        AttributesPanel p;
        QJsonObject weight{{"name", "weight"}, {"value", 90}, {"type", "number"}, {"group", "misc"}, {"unit", "weight"},
            {"range", QJsonObject{{"minimum", 1}, {"maximum", 999}}}};
        p.setAttributes({weight}); p.show();
        auto *field = p.findChild<QDoubleSpinBox *>("wbAttribute_weight"); QVERIFY(field);
        auto *text = field->findChild<QLineEdit *>(); QVERIFY(text); text->setFocus(); text->selectAll(); QTest::keyClicks(text, "110");
        QSignalSpy edits(&p, &AttributesPanel::editRequested); weight["value"] = 100; p.setAttributes({weight});
        QCOMPARE(text->text(), QString("110")); QVERIFY(edits.isEmpty());
        QTest::keyClick(text, Qt::Key_Return); QCOMPARE(edits.size(), 1);
        QCOMPARE(edits[0][1].toJsonObject(), (QJsonObject{{"name", "weight"}, {"value", 110}}));
    }
    void inspectorEmitsOnlyChangedFields() {
        InspectorPanel p; HitboxRef h; h.ordinal = 0; h.joint = "FOOT_L"; h.damage = 14; h.size = 2.8;
        p.showHitbox("dair", h);
        QSignalSpy spy(&p, &InspectorPanel::editRequested);
        p.setField("damage", 14); QCOMPARE(spy.size(), 0);
        p.setField("damage", 16); QCOMPARE(spy.size(), 1);
        QCOMPARE(spy[0][0].toString(), QString("edit_hitbox"));
        const auto args = spy[0][1].value<QJsonObject>();
        QCOMPARE(args["damage"].toInt(), 16); QCOMPARE(args["row"].toString(), QString("dair"));
        QCOMPARE(args["ordinal"].toInt(), 0); QCOMPARE(args.size(), 3);
        p.setField("damage", 16); QCOMPARE(spy.size(), 1);
        p.showHitbox("dair", h); QCOMPARE(spy.size(), 1); // Rejected edit feedback is silent.
        p.setField("damage", 16); QCOMPARE(spy.size(), 2); // Retrying must work.
    }
    void inspectorControlsUseRegistryFieldNamesAndIgnoreUnknownFields() {
        InspectorPanel p; HitboxRef h; h.ordinal = 1; h.joint = "FOOT_L"; h.startFrame = 9; h.endFrame = 15;
        QSignalSpy spy(&p, &InspectorPanel::editRequested); p.showHitbox("dair", h);
        QVERIFY(spy.isEmpty());
        auto *bone = p.findChild<QLineEdit *>("wbHitbox_bone"); QVERIFY(bone);
        bone->setText("HAND_R"); bone->editingFinished();
        QCOMPARE(spy.size(), 1);
        QCOMPARE(spy[0][1].toJsonObject()["bone"].toString(), QString("HAND_R"));
        QVERIFY(!spy[0][1].toJsonObject().contains("joint"));
        p.setField("start_frame", 10); p.setField("end_frame", 16);
        QCOMPARE(spy.size(), 3);
        QCOMPARE(spy[1][1].toJsonObject()["start_frame"].toInt(), 10);
        QCOMPARE(spy[2][1].toJsonObject()["end_frame"].toInt(), 16);
        p.setField("slot", 7); p.setField("damage", -1); p.setField("angle", 1.5);
        QCOMPARE(spy.size(), 3);
        p.clear(); p.setField("damage", 4); QCOMPARE(spy.size(), 3);
    }
    void inspectorFeedbackPreservesAnUnsubmittedDraft() {
        InspectorPanel p; HitboxRef h; h.joint = "FOOT_L"; p.showHitbox("dair", h);
        auto *bone = p.findChild<QLineEdit *>("wbHitbox_bone"); QVERIFY(bone);
        bone->setText("HAND_R"); QSignalSpy edits(&p, &InspectorPanel::editRequested);
        p.showHitbox("dair", h); QCOMPARE(bone->text(), QString("HAND_R")); QVERIFY(edits.isEmpty());
        bone->editingFinished(); QCOMPARE(edits.size(), 1);
        QCOMPARE(edits[0][1].toJsonObject()["bone"].toString(), QString("HAND_R"));
    }
    void inspectorChangedFeedbackPreservesOtherDrafts() {
        InspectorPanel p; HitboxRef h; h.joint = "FOOT_L"; h.damage = 14; p.showHitbox("dair", h);
        auto *bone = p.findChild<QLineEdit *>("wbHitbox_bone"); QVERIFY(bone); bone->setText("HAND_R");
        h.damage = 18; p.showHitbox("dair", h);
        QCOMPARE(bone->text(), QString("HAND_R"));
        QCOMPARE(p.findChild<QDoubleSpinBox *>("wbHitbox_damage")->value(), 18.0);
    }
    void sourceFeedbackKeepsUnsubmittedSpinBoxText() {
        InspectorPanel p; HitboxRef h; h.joint = "FOOT_L"; h.damage = 14; p.showHitbox("dair", h); p.show();
        auto *damage = p.findChild<QDoubleSpinBox *>("wbHitbox_damage"); QVERIFY(damage);
        auto *text = damage->findChild<QLineEdit *>(); QVERIFY(text); text->setFocus(); text->selectAll();
        QTest::keyClicks(text, "18");
        QSignalSpy edits(&p, &InspectorPanel::editRequested); h.damage = 16; p.showHitbox("dair", h);
        QCOMPARE(text->text(), QString("18")); QVERIFY(edits.isEmpty());
        QTest::keyClick(text, Qt::Key_Return); QCOMPARE(edits.size(), 1);
        QCOMPARE(edits[0][1].toJsonObject()["damage"].toInt(), 18);
    }
    void reviewPanelEnablesActionsOnlyForProposals() {
        ReviewPanel r;
        HistoryEntry a; a.id = 1; a.state = "applied"; a.author = "human"; a.summary = "x";
        HistoryEntry b; b.id = 2; b.state = "proposed"; b.author = "agent"; b.summary = "y";
        r.setHistory({a, b}); QCOMPARE(r.rowCount(), 2);
        QVERIFY(!r.actionsEnabled(0)); QVERIFY(r.actionsEnabled(1));
        QSignalSpy spy(&r, &ReviewPanel::acceptRequested);
        r.accept(0); r.accept(-1); r.accept(8); QVERIFY(spy.isEmpty());
        r.accept(1); QCOMPARE(spy.size(), 1); QCOMPARE(spy[0][0].toInt(), 2);
        b.state = "rejected"; r.setHistory({b, a}); r.accept(0); QCOMPARE(spy.size(), 1);
    }
    void reviewButtonsCarryIdsAfterRefreshAndTranslateAuthors() {
        ReviewPanel r; HistoryEntry entry; entry.id = 23; entry.state = "proposed"; entry.author = "agent";
        r.setHistory({entry});
        QSignalSpy reject(&r, &ReviewPanel::rejectRequested);
        auto *button = r.findChild<QPushButton *>("wbReject_23"); QVERIFY(button); button->click();
        QCOMPARE(reject.size(), 1); QCOMPARE(reject[0][0].toInt(), 23);
        launcher::spanish = true; r.setHistory({entry});
        QCOMPARE(r.item(0, 1)->text(), QString::fromUtf8("agente"));
        entry.author = "human"; r.setHistory({entry});
        QCOMPARE(r.item(0, 1)->text(), QString::fromUtf8("tú")); launcher::spanish = false;
    }
    void problemsPanelActivationCarriesRowAndOrdinal() {
        ProblemsPanel p; p.setProblems({{"wrong_limb", "dair", "msg", 0}});
        QSignalSpy spy(&p, &ProblemsPanel::problemActivated); p.itemActivated(p.item(0));
        QCOMPARE(spy.size(), 1);
        QCOMPARE(spy[0][0].toString(), QString("dair")); QCOMPARE(spy[0][1].toInt(), 0);
        p.setProblems({{"duplicate_clip", "jab1", "msg", -1}}); p.itemActivated(p.item(0));
        QCOMPARE(spy[1][1].toInt(), -1); p.setProblems({}); QCOMPARE(p.count(), 0);
    }
    void clipBrowserFeedbackIsSilentAndActionsUseClipIdentity() {
        ClipBrowserPanel p;
        QSignalSpy preview(&p, &ClipBrowserPanel::previewRequested), assign(&p, &ClipBrowserPanel::assignRequested);
        p.setClips({{"SYN_ATC_002", 30}, {"SYN_ATC_007", 40}}, "SYN_ATC_007");
        QVERIFY(preview.isEmpty()); QVERIFY(assign.isEmpty()); QCOMPARE(p.currentRow(), 1);
        p.previewCurrent(); p.assignCurrent();
        QCOMPARE(preview.size(), 1); QCOMPARE(preview[0][0].toString(), QString("SYN_ATC_007"));
        QCOMPARE(assign.size(), 1); QCOMPARE(assign[0][0].toString(), QString("SYN_ATC_007"));
        p.setClips({}, {}); p.previewCurrent(); p.assignCurrent();
        QCOMPARE(preview.size(), 1); QCOMPARE(assign.size(), 1);
    }
    void fidelityMatchesLedgerByMotionWhenNamesDiffer() {
        FidelityPanel p; const auto entries = QJsonDocument::fromJson(wbtest::kFidelity).object()["rows"].toArray();
        p.setFidelity(entries, "dair", {70});
        bool found = false;
        for (int row = 0; row < p.rowCount(); ++row) {
            if (p.item(row, 1) && p.item(row, 1)->text() == "SYN_ATC_007") found = true;
            if (p.item(row, 1)) QVERIFY(p.item(row, 1)->text() != "SYN_ATC_002");
        }
        QVERIFY(found);
        p.setFidelity(entries, "missing", {});
        for (int row = 0; row < p.rowCount(); ++row)
            if (p.item(row, 1)) QVERIFY(p.item(row, 1)->text() != "SYN_ATC_007");
    }
    void windowSelectionSeeksTheSelectedOccurrenceAndEditsAsHuman() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); PanelEngine engine; Session s(d.path(), &engine);
        QVERIFY(s.data().reload().isEmpty()); registerAllCommands(s); s.agentProposals = true;
        WorkbenchWindow w(s); QTRY_VERIFY(!w.isBusy());
        auto *outliner = w.findChild<OutlinerPanel *>(); auto *inspector = w.findChild<InspectorPanel *>();
        auto *review = w.findChild<ReviewPanel *>(); QVERIFY(outliner); QVERIFY(inspector); QVERIFY(review);
        outliner->setCurrentItem(outliner->topLevelItem(1)->child(1)); QTRY_VERIFY(!w.isBusy());
        QCOMPARE(w.findChild<Timeline *>()->frame(), 9);
        bool sought = false;
        for (const auto &call : engine.calls) if (call.first == "frame") {
            sought = true; QCOMPARE(call.second["motion"].toInt(), 70); QCOMPARE(call.second["frame"].toInt(), 9);
        }
        QVERIFY(sought);
        inspector->setField("damage", 12); QTRY_VERIFY(!w.isBusy());
        QCOMPARE(s.data().hitboxes("dair")[1].damage, 12.0);
        QCOMPARE(s.data().hitboxes("dair")[0].damage, 14.0);
        QCOMPARE(s.history().entries().size(), 1);
        QCOMPARE(s.history().entries()[0].author, QString("human"));
        QCOMPARE(s.history().entries()[0].state, QString("applied"));
        QCOMPARE(review->rowCount(), 1); QVERIFY(!review->actionsEnabled(0));
    }
    void delayedReplyDoesNotEraseAnInspectorDraftWhileAnEditIsQueued() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); DelayedPanelEngine engine; Session s(d.path(), &engine);
        QVERIFY(s.data().reload().isEmpty()); registerAllCommands(s); WorkbenchWindow w(s); QTRY_VERIFY(!w.isBusy());
        auto *outline = w.findChild<OutlinerPanel *>(); QVERIFY(outline);
        outline->setCurrentItem(outline->topLevelItem(1)->child(0)); QTRY_VERIFY(!w.isBusy());
        auto *inspector = w.findChild<InspectorPanel *>(); QVERIFY(inspector);
        auto *bone = inspector->findChild<QLineEdit *>("wbHitbox_bone"); QVERIFY(bone);
        QString draftAfterOldReply;
        connect(&w, &WorkbenchWindow::commandFinished, &w, [&](const QString &name, const QJsonObject &) {
            if (name == "frame_info") draftAfterOldReply = bone->text();
        });
        engine.blockNext = true; w.runCommand("frame_info", {}); QTRY_VERIFY(engine.entered.available() > 0);
        inspector->setField("damage", 16); bone->setText("HAND_R"); engine.release.release();
        QTRY_VERIFY(!w.isBusy()); QCOMPARE(draftAfterOldReply, QString("HAND_R"));
        QCOMPARE(bone->text(), QString("HAND_R")); QCOMPARE(s.data().hitboxes("dair")[0].damage, 16.0);
        bone->editingFinished(); QTRY_VERIFY(!w.isBusy());
        QCOMPARE(s.data().hitboxes("dair")[0].joint, QString("HAND_R"));
    }
    void windowReviewActionsRefreshHistoryAndSource() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); Session s(d.path(), nullptr);
        QVERIFY(s.data().reload().isEmpty()); registerAllCommands(s);
        CommandContext ctx{s, "agent", true};
        QVERIFY(s.registry().call("edit_hitbox", {{"row", "dair"}, {"ordinal", 0}, {"damage", 16}}, ctx)["ok"].toBool());
        WorkbenchWindow w(s); QTRY_VERIFY(!w.isBusy()); auto *review = w.findChild<ReviewPanel *>(); QVERIFY(review);
        QCOMPARE(review->rowCount(), 1); QVERIFY(review->actionsEnabled(0));
        review->accept(0); QTRY_VERIFY(!w.isBusy());
        QCOMPARE(s.data().hitboxes("dair")[0].damage, 16.0); QVERIFY(!review->actionsEnabled(0));
        review->undoRequested(); QTRY_VERIFY(!w.isBusy()); QCOMPARE(s.data().hitboxes("dair")[0].damage, 14.0);
        QCOMPARE(s.history().entries()[0].state, QString("undone"));
        review->redoRequested(); QTRY_VERIFY(!w.isBusy()); QCOMPARE(s.data().hitboxes("dair")[0].damage, 16.0);
        QCOMPARE(s.history().entries()[0].state, QString("applied"));
    }
    void fidelityRefreshDoesNotAcknowledgeExternalEdits() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); Session s(d.path(), nullptr);
        QVERIFY(s.data().reload().isEmpty()); registerAllCommands(s); WorkbenchWindow w(s); QTRY_VERIFY(!w.isBusy());
        QByteArray changed(wbtest::kFidelity); changed.replace("SOURCE-RETIMED", "HAND-EDITED");
        wbtest::put(d.path(), "fidelity.json", changed);
        w.runCommand("history", {}); QTRY_VERIFY(!w.isBusy());
        QSignalSpy done(&w, &WorkbenchWindow::commandFinished);
        w.runCommand("save", {}); QTRY_VERIFY(!w.isBusy());
        QCOMPARE(done.size(), 1); QVERIFY(done[0][1].toJsonObject()["ok"].toBool());
        QVERIFY(done[0][1].toJsonObject()["result"].toObject()["external"].toArray().contains("fidelity.json"));
        QVERIFY(w.statusText().contains("changed externally"));
        QVERIFY(w.statusText().contains("fidelity.json"));
    }
    void windowClipsAndProblemsUseTheSelectedRow() {
        QTemporaryDir d; wbtest::makeSynthFighter(d.path()); PanelEngine engine; Session s(d.path(), &engine);
        QVERIFY(s.data().reload().isEmpty()); registerAllCommands(s); WorkbenchWindow w(s); QTRY_VERIFY(!w.isBusy());
        auto *problems = w.findChild<ProblemsPanel *>(); auto *clips = w.findChild<ClipBrowserPanel *>();
        QVERIFY(problems); QVERIFY(clips);
        problems->setProblems({{"wrong_limb", "dair", "synthetic", 1}}); problems->itemActivated(problems->item(0));
        QTRY_VERIFY(!w.isBusy()); QCOMPARE(w.findChild<Timeline *>()->frame(), 9);
        clips->setCurrentRow(2); clips->previewCurrent(); QTRY_VERIFY(!w.isBusy());
        bool previewed = false; for (const auto &call : engine.calls) if (call.first == "clip") {
            previewed = true; QCOMPARE(call.second["clip"].toString(), QString("SYN_ATC_009"));
        }
        QVERIFY(previewed);
        clips->assignCurrent(); QTRY_VERIFY(!w.isBusy());
        QCOMPARE(s.data().rows()[1].clip, QString("SYN_ATC_009"));
        QCOMPARE(s.data().rows()[0].clip, QString("SYN_ATC_002"));
    }
};
QTEST_MAIN(PanelsTest)
#include "panels_test.moc"
