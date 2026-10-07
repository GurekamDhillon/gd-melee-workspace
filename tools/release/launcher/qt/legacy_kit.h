#pragma once
#include <QColor>
#include <QFont>
#include <QImage>
#include <QJsonObject>
#include <QPushButton>
#include <QStyledItemDelegate>
#include <QVariantAnimation>
#include <QWidget>
namespace launcher::legacy {
void initialize();
QColor color(const QString &token);
QColor sectionColor(const QString &section, const QString &token);
QFont font(int pixels, bool black = false, bool italic = false);
QImage icon(const QString &name, const QColor &tint);
class Surface : public QWidget {
public:
    explicit Surface(QWidget *parent = nullptr) : QWidget(parent) {}
    void setSection(const QString &value) { section_ = value; update(); }
protected:
    void paintEvent(QPaintEvent *) override;
private:
    QString section_ = "versus";
};
class Button : public QPushButton {
public:
    explicit Button(const QString &text, QWidget *parent = nullptr);
    void setPrimary(bool value) { primary_ = value; update(); }
    void setKitIcon(const QString &name) { icon_ = name; update(); }
    void setSection(const QString &name) { section_ = name; update(); }
protected:
    void paintEvent(QPaintEvent *) override;
    void enterEvent(QEnterEvent *) override;
    void leaveEvent(QEvent *) override;
private:
    bool primary_ = false;
    QString icon_, section_ = "versus";
    QVariantAnimation motion_;
    qreal hover_ = 0;
};
class DiscDelegate : public QStyledItemDelegate {
public:
    using QStyledItemDelegate::QStyledItemDelegate;
    void paint(QPainter *, const QStyleOptionViewItem &, const QModelIndex &) const override;
    QSize sizeHint(const QStyleOptionViewItem &, const QModelIndex &) const override { return {320, 96}; }
};
class Hero : public QWidget {
public:
    explicit Hero(QWidget *parent = nullptr) : QWidget(parent) { setMinimumHeight(190); }
    void setDisc(const QString &kind) { kind_ = kind; update(); }
protected:
    void paintEvent(QPaintEvent *) override;
private:
    QString kind_;
};
}
