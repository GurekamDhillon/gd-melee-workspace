#pragma once
#include "command_registry.h"
#include <QDialog>

class QLineEdit;
class QListWidget;

namespace wb {
class CommandPalette : public QDialog {
    Q_OBJECT
public:
    explicit CommandPalette(CommandRegistry &, QWidget *parent = nullptr);
    static QVector<CommandSpec> filter(const QVector<CommandSpec> &, const QString &query);

signals:
    void commandChosen(const QString &name);

protected:
    bool eventFilter(QObject *watched, QEvent *event) override;

private:
    void refresh(const QString &query);
    void chooseCurrent();

    const QVector<CommandSpec> commands_;
    QLineEdit *query_;
    QListWidget *list_;
};
} // namespace wb
