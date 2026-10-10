#include "window.h"
#define WB_CORE_USE_LAUNCHER_T 1
#include "commands.h"
#include "../testfixture.h"
#include "palette.h"
#include <QLineEdit>
#include <QListWidget>
#include <QSignalSpy>
#include <QTemporaryDir>
#include <QtTest>

using namespace wb;

namespace {
CommandSpec command(const QString &name, const QString &description = {}, bool mutating = false) {
    CommandSpec spec;
    spec.name = name;
    spec.description = description;
    spec.mutating = mutating;
    return spec;
}
QStringList names(const QVector<CommandSpec> &specs) {
    QStringList result;
    for (const auto &spec : specs) result.append(spec.name);
    return result;
}
CommandRegistry sampleRegistry() {
    CommandRegistry registry;
    registry.add(command("list_rows", "Rows (hitbox counts)"));
    registry.add(command("edit_hitbox", "Edit one hitbox", true));
    registry.add(command("show_hitbox", "Inspect size"));
    return registry;
}
}

class PaletteTest : public QObject {
    Q_OBJECT
private slots:
    void init() { launcher::spanish = false; }
    void cleanup() { launcher::spanish = false; }

    void paletteFilterRanksNameMatchesFirst() {
        QVector<CommandSpec> specs;
        CommandSpec a; a.name = "edit_hitbox"; a.description = "Edit one hitbox"; specs << a;
        CommandSpec b; b.name = "list_rows"; b.description = "Rows (hitbox counts)"; specs << b;
        auto f = CommandPalette::filter(specs, "hit");
        QCOMPARE(f.size(), 2); QCOMPARE(f[0].name, QString("edit_hitbox"));
        QCOMPARE(CommandPalette::filter(specs, "zzz").size(), 0);
        QCOMPARE(CommandPalette::filter(specs, "").size(), 2);
        QCOMPARE(CommandPalette::filter(specs, "ehb").size(), 1);
    }

    void filterPreservesOrderWithinEachMatchClass() {
        const QVector<CommandSpec> specs = {
            command("inspect", "Hitbox details"),
            command("edit_hitbox", "Modify size", true),
            command("list_rows", "Hitbox counts"),
            command("show_hitbox", "Inspect size"),
            command("save", "Write project", true)
        };
        const auto filtered = CommandPalette::filter(specs, "hit");
        QCOMPARE(names(filtered), QStringList({"edit_hitbox", "show_hitbox", "inspect", "list_rows"}));
        QVERIFY(filtered[0].mutating);
        QCOMPARE(filtered[0].description, QString("Modify size"));
    }

    void emptyQueryReturnsAllInRegistrationOrder() {
        const QVector<CommandSpec> specs = {
            command("save", "Write project", true), command("list_rows", "Read rows"), command("edit_hitbox")
        };
        QCOMPARE(names(CommandPalette::filter(specs, "")), QStringList({"save", "list_rows", "edit_hitbox"}));
        QVERIFY(CommandPalette::filter({}, "").isEmpty());
    }

    void noMatchReturnsNoCommands() {
        const QVector<CommandSpec> specs = {command("edit_hitbox", "Edit one hitbox")};
        QVERIFY(CommandPalette::filter(specs, "zzz").isEmpty());
        QVERIFY(CommandPalette::filter(specs, "bxh").isEmpty()); // Wrong subsequence order.
        QVERIFY(CommandPalette::filter({}, "hit").isEmpty());
    }

    void filterIsCaseInsensitiveForNamesAndDescriptions() {
        const QVector<CommandSpec> specs = {
            command("Edit_HitBOX", "Modify size"), command("list_rows", "Rows (Hitbox COUNTS)")
        };
        QCOMPARE(names(CommandPalette::filter(specs, "EHB")), QStringList({"Edit_HitBOX"}));
        QCOMPARE(names(CommandPalette::filter(specs, "hct")), QStringList({"list_rows"}));
        QCOMPARE(names(CommandPalette::filter(specs, "HCT")), QStringList({"list_rows"}));
    }

    void filterDoesNotJoinNameAndDescription() {
        QVERIFY(CommandPalette::filter({command("abc", "xyz")}, "cx").isEmpty());
    }

    void paletteListsRegisteredCommandsOffline() {
        QTemporaryDir dir;
        QVERIFY(dir.isValid());
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        QVERIFY(session.data().reload().isEmpty());
        registerAllCommands(session);
        CommandPalette palette(session.registry());
        auto *list = palette.findChild<QListWidget *>();
        QVERIFY(list);
        const auto specs = session.registry().list();
        QVERIFY(!specs.isEmpty());
        QCOMPARE(list->count(), specs.size());
        for (int i = 0; i < list->count(); ++i)
            QCOMPARE(list->item(i)->data(Qt::UserRole).toString(), specs[i].name);
        QCOMPARE(list->currentRow(), 0);
    }

    void enterEmitsHighlightedCommandAndCloses_data() {
        QTest::addColumn<int>("key");
        QTest::newRow("return") << int(Qt::Key_Return);
        QTest::newRow("keypad-enter") << int(Qt::Key_Enter);
    }
    void enterEmitsHighlightedCommandAndCloses() {
        QFETCH(int, key);
        auto registry = sampleRegistry();
        CommandPalette palette(registry);
        auto *edit = palette.findChild<QLineEdit *>();
        auto *list = palette.findChild<QListWidget *>();
        QVERIFY(edit); QVERIFY(list);
        palette.show(); palette.activateWindow();
        QTRY_VERIFY(edit->hasFocus());
        list->setCurrentRow(1);
        QSignalSpy chosen(&palette, &CommandPalette::commandChosen);
        QVERIFY(chosen.isValid());
        QTest::keyClick(edit, Qt::Key(key));
        QCOMPARE(chosen.size(), 1);
        QCOMPARE(chosen[0][0].toString(), QString("edit_hitbox"));
        QVERIFY(!palette.isVisible());
        QCOMPARE(palette.result(), int(QDialog::Accepted));
    }

    void typingRefiltersAndResetsSelection() {
        auto registry = sampleRegistry();
        CommandPalette palette(registry);
        auto *edit = palette.findChild<QLineEdit *>();
        auto *list = palette.findChild<QListWidget *>();
        QVERIFY(edit); QVERIFY(list);
        palette.show(); palette.activateWindow();
        QTRY_VERIFY(edit->hasFocus());
        list->setCurrentRow(2);
        QTest::keyClicks(edit, "hit");
        QCOMPARE(list->count(), 3);
        QCOMPARE(list->currentRow(), 0);
        QCOMPARE(list->item(0)->data(Qt::UserRole).toString(), QString("edit_hitbox"));
        QCOMPARE(list->item(1)->data(Qt::UserRole).toString(), QString("show_hitbox"));
        QCOMPARE(list->item(2)->data(Qt::UserRole).toString(), QString("list_rows"));
        edit->setText("zzz");
        QCOMPARE(list->count(), 0);
        QCOMPARE(list->currentRow(), -1);
        edit->clear();
        QCOMPARE(list->count(), 3);
        QCOMPARE(list->currentRow(), 0);
        QCOMPARE(list->item(0)->data(Qt::UserRole).toString(), QString("list_rows"));
        edit->setText("ehb");
        QCOMPARE(list->count(), 1);
        QSignalSpy chosen(&palette, &CommandPalette::commandChosen);
        QTest::keyClick(edit, Qt::Key_Return);
        QCOMPARE(chosen.size(), 1);
        QCOMPARE(chosen[0][0].toString(), QString("edit_hitbox"));
    }

    void upDownMovesSelectionAndKeepsEditFocus() {
        auto registry = sampleRegistry();
        CommandPalette palette(registry);
        auto *edit = palette.findChild<QLineEdit *>();
        auto *list = palette.findChild<QListWidget *>();
        QVERIFY(edit); QVERIFY(list);
        palette.show(); palette.activateWindow();
        QTRY_VERIFY(edit->hasFocus());
        QSignalSpy chosen(&palette, &CommandPalette::commandChosen);
        const QVector<QPair<Qt::Key, int>> steps = {
            {Qt::Key_Up, 0}, {Qt::Key_Down, 1}, {Qt::Key_Down, 2}, {Qt::Key_Down, 2},
            {Qt::Key_Up, 1}, {Qt::Key_Up, 0}, {Qt::Key_Up, 0}
        };
        for (const auto &step : steps) {
            QTest::keyClick(edit, step.first);
            QCOMPARE(list->currentRow(), step.second);
            QVERIFY(edit->hasFocus());
        }
        QVERIFY(chosen.isEmpty());
        QCOMPARE(edit->text(), QString());
        QTest::keyClicks(edit, "ehb");
        QCOMPARE(list->count(), 1);
        QCOMPARE(list->currentItem()->data(Qt::UserRole).toString(), QString("edit_hitbox"));
    }

    void enterWithNoMatchesDoesNotChooseOrClose() {
        auto registry = sampleRegistry();
        CommandPalette palette(registry);
        auto *edit = palette.findChild<QLineEdit *>();
        auto *list = palette.findChild<QListWidget *>();
        QVERIFY(edit); QVERIFY(list);
        palette.show(); palette.activateWindow();
        QTRY_VERIFY(edit->hasFocus());
        QTest::keyClicks(edit, "zzz");
        QCOMPARE(list->count(), 0);
        QSignalSpy chosen(&palette, &CommandPalette::commandChosen);
        QTest::keyClick(edit, Qt::Key_Down); QTest::keyClick(edit, Qt::Key_Up);
        QTest::keyClick(edit, Qt::Key_Return);
        QVERIFY(chosen.isEmpty());
        QVERIFY(palette.isVisible());
        QVERIFY(edit->hasFocus());
    }

    void emptyRegistryHandlesNavigationAndEnter() {
        CommandRegistry registry;
        CommandPalette palette(registry);
        auto *edit = palette.findChild<QLineEdit *>();
        auto *list = palette.findChild<QListWidget *>();
        QVERIFY(edit); QVERIFY(list);
        QCOMPARE(list->count(), 0);
        palette.show(); palette.activateWindow();
        QTRY_VERIFY(edit->hasFocus());
        QSignalSpy chosen(&palette, &CommandPalette::commandChosen);
        QTest::keyClick(edit, Qt::Key_Up); QTest::keyClick(edit, Qt::Key_Down);
        QTest::keyClick(edit, Qt::Key_Enter);
        QCOMPARE(list->currentRow(), -1);
        QVERIFY(chosen.isEmpty());
        QVERIFY(palette.isVisible());
        QVERIFY(edit->hasFocus());
    }

    void mutatingCommandsAreMarkedInListText() {
        auto registry = sampleRegistry();
        CommandPalette palette(registry);
        auto *list = palette.findChild<QListWidget *>();
        QVERIFY(list);
        QVERIFY(!list->item(0)->text().contains("[modifies project]"));
        QVERIFY(list->item(1)->text().contains("[modifies project]"));
        QVERIFY(!list->item(2)->text().contains("[modifies project]"));
        QVERIFY(list->item(1)->text().contains("Edit one hitbox"));
        QCOMPARE(list->item(1)->data(Qt::UserRole).toString(), QString("edit_hitbox"));
    }

    void spanishLabelsUseLauncherTranslation() {
        launcher::spanish = true;
        auto registry = sampleRegistry();
        CommandPalette palette(registry);
        auto *edit = palette.findChild<QLineEdit *>();
        auto *list = palette.findChild<QListWidget *>();
        QVERIFY(edit); QVERIFY(list);
        QCOMPARE(palette.windowTitle(), QString::fromUtf8("Paleta de comandos"));
        QCOMPARE(edit->placeholderText(), QString::fromUtf8("Escribe un comando"));
        QVERIFY(list->item(1)->text().contains(QString::fromUtf8("[modifica el proyecto]")));
        QVERIFY(!list->item(1)->text().contains("[modifies project]"));
    }

    void doubleClickEmitsClickedCommandAndCloses() {
        auto registry = sampleRegistry();
        CommandPalette palette(registry);
        auto *edit = palette.findChild<QLineEdit *>();
        auto *list = palette.findChild<QListWidget *>();
        QVERIFY(edit); QVERIFY(list);
        palette.show(); palette.activateWindow();
        QTRY_VERIFY(edit->hasFocus());
        QSignalSpy chosen(&palette, &CommandPalette::commandChosen);
        const QRect rect = list->visualItemRect(list->item(1));
        QVERIFY(!rect.isEmpty());
        QTest::mouseClick(list->viewport(), Qt::LeftButton, Qt::NoModifier, rect.center());
        QVERIFY(chosen.isEmpty());
        QVERIFY(palette.isVisible());
        QTest::mouseDClick(list->viewport(), Qt::LeftButton, Qt::NoModifier, rect.center());
        QCOMPARE(chosen.size(), 1);
        QCOMPARE(chosen[0][0].toString(), QString("edit_hitbox"));
        QVERIFY(!palette.isVisible());
        QCOMPARE(palette.result(), int(QDialog::Accepted));
    }

    void escapeClosesWithoutChoosing() {
        auto registry = sampleRegistry();
        CommandPalette palette(registry);
        auto *edit = palette.findChild<QLineEdit *>();
        QVERIFY(edit);
        palette.show(); palette.activateWindow();
        QTRY_VERIFY(edit->hasFocus());
        QSignalSpy chosen(&palette, &CommandPalette::commandChosen);
        QTest::keyClick(edit, Qt::Key_Escape);
        QVERIFY(chosen.isEmpty());
        QVERIFY(!palette.isVisible());
        QCOMPARE(palette.result(), int(QDialog::Rejected));
    }
};

QTEST_MAIN(PaletteTest)
#include "palette_test.moc"
