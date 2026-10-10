#include "palette.h"
#include "window.h"
#include <QKeyEvent>
#include <QLineEdit>
#include <QListWidget>
#include <QPointer>
#include <QVBoxLayout>
#include <algorithm>

namespace wb {
using launcher::t;
namespace {
bool matchesSubsequence(const QString &text, const QString &foldedQuery) {
    const QString foldedText = text.toCaseFolded();
    qsizetype position = 0;
    for (const QChar character : foldedQuery) {
        position = foldedText.indexOf(character, position);
        if (position < 0) return false;
        ++position;
    }
    return true;
}
}

CommandPalette::CommandPalette(CommandRegistry &registry, QWidget *parent)
    : QDialog(parent), commands_(registry.list()), query_(new QLineEdit(this)), list_(new QListWidget(this)) {
    setObjectName("wbCommandPalette");
    setWindowTitle(t("Command palette", "Paleta de comandos"));
    setModal(true);
    resize(560, 360);

    query_->setObjectName("wbPaletteQuery");
    query_->setPlaceholderText(t("Type a command", "Escribe un comando"));
    query_->setAccessibleName(t("Type a command", "Escribe un comando"));
    query_->installEventFilter(this);
    list_->setObjectName("wbPaletteCommands");
    list_->setAccessibleName(t("Matching commands", "Comandos coincidentes"));
    list_->setSelectionMode(QAbstractItemView::SingleSelection);
    // Mouse selection and arrow navigation leave typing in the query field.
    list_->setFocusPolicy(Qt::NoFocus);

    auto *layout = new QVBoxLayout(this);
    layout->addWidget(query_);
    layout->addWidget(list_);
    setFocusProxy(query_);
    query_->setFocus(Qt::OtherFocusReason);

    connect(query_, &QLineEdit::textChanged, this, &CommandPalette::refresh);
    connect(query_, &QLineEdit::returnPressed, this, &CommandPalette::chooseCurrent);
    connect(list_, &QListWidget::itemDoubleClicked, this, [this](QListWidgetItem *item) {
        list_->setCurrentItem(item);
        chooseCurrent();
    });
    refresh({});
}

QVector<CommandSpec> CommandPalette::filter(const QVector<CommandSpec> &commands, const QString &query) {
    if (query.isEmpty()) return commands;
    const QString foldedQuery = query.toCaseFolded();
    QVector<CommandSpec> nameMatches, descriptionMatches;
    nameMatches.reserve(commands.size());
    for (const auto &command : commands) {
        if (matchesSubsequence(command.name, foldedQuery))
            nameMatches.append(command);
        else if (matchesSubsequence(command.description, foldedQuery))
            descriptionMatches.append(command);
    }
    nameMatches += descriptionMatches;
    return nameMatches;
}

void CommandPalette::refresh(const QString &query) {
    list_->clear();
    for (const auto &command : filter(commands_, query)) {
        QString text = command.description.isEmpty()
            ? command.name : t("%1 — %2", "%1 — %2").arg(command.name, command.description);
        if (command.mutating) text += t(" [modifies project]", " [modifica el proyecto]");
        auto *item = new QListWidgetItem(text, list_);
        item->setData(Qt::UserRole, command.name);
        item->setToolTip(command.description);
    }
    list_->setCurrentRow(list_->count() > 0 ? 0 : -1);
}

bool CommandPalette::eventFilter(QObject *watched, QEvent *event) {
    if (watched == query_ && event->type() == QEvent::KeyPress) {
        const int key = static_cast<QKeyEvent *>(event)->key();
        if (key == Qt::Key_Up || key == Qt::Key_Down) {
            if (list_->count() > 0) {
                const int delta = key == Qt::Key_Down ? 1 : -1;
                const int row = std::clamp(list_->currentRow() + delta, 0, list_->count() - 1);
                list_->setCurrentRow(row);
                list_->scrollToItem(list_->currentItem());
            }
            return true;
        }
    }
    return QDialog::eventFilter(watched, event);
}

void CommandPalette::chooseCurrent() {
    const auto *item = list_->currentItem();
    if (!item) return;
    const QString name = item->data(Qt::UserRole).toString();
    // The consumer may destroy the dialog while handling the chosen command.
    QPointer<CommandPalette> alive(this);
    emit commandChosen(name);
    if (alive) accept();
}
} // namespace wb
