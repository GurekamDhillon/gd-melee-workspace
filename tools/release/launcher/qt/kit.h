#pragma once
#include "atlas.h"
#include <QAbstractButton>
#include <QPainterPath>
#include <QPushButton>
#include <QStyledItemDelegate>
#include <QVariantAnimation>
#include <QWidget>
class QPainter;
namespace launcher::kit {
// Item roles the RowDelegate reads (Qt::DisplayRole is the name; CheckStateRole, when set, draws an ON/OFF toggle).
enum RowRole { SubRole = Qt::UserRole, TagTextRole = Qt::UserRole + 1, BadgeRole = Qt::UserRole + 2, TagToneRole = Qt::UserRole + 3, TitleRole = Qt::UserRole + 4 };

QPainterPath icon(const QString &name);                            // atlas_icons.h; 24 x 24
void paintIcon(QPainter &p, const QString &name, const QRectF &target, const QColor &colour);   // stroked 1.6 px, the one place antialiasing is on
void paintPlate(QPainter &p, const QRectF &r, const QColor &face, const QColor &edge, qreal edgePx, qreal chamfer);  // face and the front edge, chamfered
void paintHatch(QPainter &p, const QPolygonF &area, const QColor &line);

class Pane : public QWidget {                                       // E1: plate, 3 px edge, 8 px chamfer, a heading and a count
    Q_OBJECT
public:
    explicit Pane(const QString &heading = {}, QWidget *parent = nullptr);
    void setHeading(const QString &text);
    void setCount(const QString &text);
    QWidget *body() const { return body_; }
protected:
    void paintEvent(QPaintEvent *) override;
private:
    QString heading_, count_; QWidget *body_;
};
class Button : public QPushButton {                                 // primary = ember (the one action), else plate2; disabled = hatched
    Q_OBJECT
public:
    explicit Button(const QString &text, QWidget *parent = nullptr);
    void setPrimary(bool on) { primary_ = on; updateGeometry(); update(); }
    bool primary() const { return primary_; }
    void setKitIcon(const QString &name) { icon_ = name; updateGeometry(); update(); }
    QSize sizeHint() const override;
    QSize minimumSizeHint() const override;                            // narrow: a long label is elided (and shown whole in a tooltip), it never widens its column
protected:
    bool event(QEvent *) override;
    void paintEvent(QPaintEvent *) override;
    void enterEvent(QEnterEvent *) override;
    void leaveEvent(QEvent *) override;
private:
    atlas::Role role() const { return primary_ ? atlas::Role::Cap20 : atlas::Role::Cap16; }
    bool primary_ = false; QString icon_; qreal hover_ = 0; QVariantAnimation motion_; mutable bool elided_ = false;
};
void paintToggle(QPainter &p, const QRectF &r, bool on, bool focus);
class Toggle : public QAbstractButton {                              // the word ON or OFF, the lit half jade
    Q_OBJECT
public:
    explicit Toggle(QWidget *parent = nullptr);
    QString stateText() const { return isChecked() ? "ON" : "OFF"; }
    QSize sizeHint() const override { return {74, 24}; }
protected:
    void paintEvent(QPaintEvent *) override;
};
class Tag : public QWidget {
public:
    enum Tone { Plain, Jade, Ember, Sun, Rose };
    Tag(const QString &text, Tone tone = Plain, QWidget *parent = nullptr);
    QSize sizeHint() const override;
protected:
    void paintEvent(QPaintEvent *) override;
private:
    QString text_; Tone tone_;
};
void paintTag(QPainter &p, const QRectF &r, const QString &text, Tag::Tone tone);
qreal tagWidth(const QString &text);
class KeyChip : public QWidget {                                     // "Enter", "Ctrl", "M"
public:
    explicit KeyChip(const QString &text, QWidget *parent = nullptr);
    QSize sizeHint() const override;
protected:
    void paintEvent(QPaintEvent *) override;
private:
    QString text_;
};
class TabRail : public QWidget {                                     // the four tabs as rows on the left
    Q_OBJECT
public:
    explicit TabRail(const QStringList &names, QWidget *parent = nullptr);
    int current() const { return current_; }
    void setCurrent(int i);
    void setIcons(const QStringList &names) { icons_ = names; update(); }
    QSize sizeHint() const override { return {204, 16 + 4 * 50}; }
signals:
    void currentChanged(int index);
protected:
    void paintEvent(QPaintEvent *) override;
    void keyPressEvent(QKeyEvent *) override;
    void mousePressEvent(QMouseEvent *) override;
private:
    QRectF rowRect(int i) const;
    QStringList names_, icons_; int current_ = 0;
};
class RowDelegate : public QStyledItemDelegate {                     // a disc or mod row: badge, name, sub line, a tag, an optional toggle
public:
    using QStyledItemDelegate::QStyledItemDelegate;
    void paint(QPainter *, const QStyleOptionViewItem &, const QModelIndex &) const override;
    QSize sizeHint(const QStyleOptionViewItem &, const QModelIndex &) const override { return {320, rowHeight()}; }
    bool editorEvent(QEvent *, QAbstractItemModel *, const QStyleOptionViewItem &, const QModelIndex &) override;
    static int rowHeight() { return 46 + 5; }                        // the tall row (46) plus a 5 px gap; the 2 px lift hides in the gap
};
}
