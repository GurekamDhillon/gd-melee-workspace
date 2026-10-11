#pragma once
#include "geno_data.h"
#include <QJsonArray>
#include <QJsonObject>
#include <QMap>
#include <QWidget>

class QComboBox;
class QLabel;
class QListWidget;
class QPushButton;
class QSpinBox;
namespace wb {
class TimelineView;

// Snapshot-driven editors. All writes use the same commands/history as the hitbox inspector.
class StatementsPanel : public QWidget {
    Q_OBJECT
public:
    explicit StatementsPanel(QWidget *parent = nullptr);
    void setData(const QString &row, const QJsonArray &statements, const QJsonObject &standIn,
                 const QVector<RoleInfo> &roles);
    void selectStatement(int ordinal);
signals:
    void editRequested(const QString &command, const QJsonObject &args);
    void addRequested(const QString &kind, const QJsonObject &fields);
    void statementSelected(int ordinal);
private:
    QJsonObject current() const;
    void refreshFields();
    void submit(const QString &key, const QJsonValue &value);
    QString row_;
    QJsonArray statements_;
    QJsonObject standIn_;
    bool feedback_ = false, initialized_ = false;
    QVector<RoleInfo> roles_;
    QListWidget *list_;
    QWidget *form_;
    QLabel *empty_, *note_, *window_, *standInNote_;
    QComboBox *kind_, *state_, *bone_, *slot_, *standInChoice_;
    QSpinBox *frame_;
    QPushButton *add_, *remove_, *restore_;
    QMap<QString, QWidget *> fields_, rows_;
};

// Separate from timeline playback/scrubbing: authored hurt-state windows share its ruler geometry.
class HurtStateLanes : public QWidget {
    Q_OBJECT
public:
    explicit HurtStateLanes(QWidget *parent = nullptr);
    void setTimeline(TimelineView *timeline);
    void setWindows(const QJsonArray &windows);
    void selectStatement(int ordinal);
    int windowCount() const { return int(windows_.size()); }
    QRectF windowRect(int ordinal) const;
    QSize sizeHint() const override;
    QSize minimumSizeHint() const override { return {80, sizeHint().height()}; }
signals:
    void statementSelected(int ordinal);
protected:
    void paintEvent(QPaintEvent *) override;
    void mousePressEvent(QMouseEvent *) override;
    bool event(QEvent *) override;
private:
    QString label(const QJsonObject &) const;
    qreal xOfFrame(int frame) const;
    int laneFor(const QJsonObject &) const;
    TimelineView *timeline_ = nullptr;
    QJsonArray windows_;
    QStringList lanes_;
    int selected_ = -1;
};
} // namespace wb
