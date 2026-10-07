#include "legacy_kit.h"
#include <QApplication>
#include <QFile>
#include <QFontDatabase>
#include <QJsonDocument>
#include <QPainter>
#include <QPainterPath>
#include <QPalette>
#include <QStyleOptionViewItem>
#include <QtEndian>
#include <algorithm>

namespace launcher::legacy {
static QJsonObject tokens;
static int duration = 167;
static QPolygonF plate(QRectF r, qreal slant = -1) {
    const qreal s = slant < 0 ? std::min(r.height() * .25, 22.) : slant;
    return {{r.left() + s, r.top()}, {r.right(), r.top()}, {r.right() - s, r.bottom()}, {r.left(), r.bottom()}};
}
QColor color(const QString &key) { return QColor(tokens["palette"].toObject()[key].toString()); }
QColor sectionColor(const QString &section, const QString &key) { return QColor(tokens["sections"].toObject()[section].toObject()[key].toString()); }
QFont font(int pixels, bool black, bool italic) { QFont f("Source Sans 3"); f.setPixelSize(pixels); f.setWeight(black ? QFont::Black : QFont::DemiBold); f.setItalic(italic); return f; }
void initialize() {
    QFile json(":/kit/kit.json"); json.open(QIODevice::ReadOnly); tokens = QJsonDocument::fromJson(json.readAll()).object();
    QFile motion(":/kit/motion.json"); motion.open(QIODevice::ReadOnly); auto m = QJsonDocument::fromJson(motion.readAll()).object();
    duration = m["events"].toObject()["row_select"].toObject()["length_frames"].toInt(10) * 1000 / m["fps"].toInt(60);
    for (const auto &name : {"bold", "black", "semibold"}) QFontDatabase::addApplicationFont(":/kit/" + QString(name) + ".otf");
    QApplication::setFont(legacy::font(16));
    QPalette palette;
    palette.setColor(QPalette::Window, color("ink")); palette.setColor(QPalette::WindowText, color("bone"));
    palette.setColor(QPalette::Base, color("ink")); palette.setColor(QPalette::AlternateBase, sectionColor("versus", "bg"));
    palette.setColor(QPalette::Text, color("bone")); palette.setColor(QPalette::Button, sectionColor("versus", "face"));
    palette.setColor(QPalette::ButtonText, color("bone")); palette.setColor(QPalette::Highlight, color("gold")); palette.setColor(QPalette::HighlightedText, color("ink"));
    palette.setColor(QPalette::Disabled, QPalette::Text, color("disabled")); palette.setColor(QPalette::Disabled, QPalette::ButtonText, color("disabled"));
    QApplication::setPalette(palette);
    // Geometry and type come from the menu kit; use Qt for focus, accessibility,
    // text entry and layout instead of maintaining a second input system.
    qApp->setStyleSheet(QString(R"(
      QMainWindow, QTabWidget, QStackedWidget, QScrollArea { background: transparent; border: none; }
      QLabel { background: transparent; color: %1; }
      QLabel[role="muted"] { color: %2; font-size: 14px; }
      QLabel[role="eyebrow"] { color: %3; font-weight: 900; font-size: 14px; }
      QLabel[role="heading"] { font-size: 30px; font-weight: 900; font-style: italic; }
      QLabel[role="brand"] { font-size: 38px; font-weight: 900; font-style: italic; }
      QWidget#contentPanel { background: %4; }
      QWidget#launchPanel { background: %5; }
      QTableWidget { background: transparent; border: none; gridline-color: %5; selection-background-color: %3; selection-color: %4; }
      QTableWidget::item { padding: 10px; border: none; }
      QHeaderView::section { background: %5; color: %2; border: none; padding: 10px; font-size: 14px; }
      QGroupBox { border: 1px solid %5; margin-top: 18px; padding: 20px 12px 12px; font-weight: 700; }
      QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: %3; }
      QCheckBox { spacing: 10px; padding: 7px 0; }
      QCheckBox::indicator { width: 16px; height: 16px; border: 2px solid %2; background: %4; }
      QCheckBox::indicator:checked { background: %3; border-color: %3; }
      QCheckBox::indicator:focus, QCheckBox::indicator:hover { border-color: %3; }
      QComboBox, QLineEdit { background: %5; border: 1px solid %2; padding: 7px 12px; color: %1; min-height: 24px; }
      QComboBox:focus, QLineEdit:focus { border-color: %3; }
      QComboBox QAbstractItemView { background: %4; color: %1; selection-background-color: %3; selection-color: %4; }
      QSlider::groove:horizontal { height: 5px; background: %4; }
      QSlider::sub-page:horizontal { background: %3; }
      QSlider::handle:horizontal { width: 10px; margin: -7px 0; background: %3; border: none; }
      QScrollBar:vertical { background: %4; width: 7px; margin: 0; }
      QScrollBar::handle:vertical { background: %5; min-height: 32px; }
      QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
      QStatusBar { background: %4; color: %2; padding: 6px 28px; font-size: 14px; }
      QStatusBar::item { border: none; }
      QToolTip { background: %4; color: %1; border: 1px solid %3; padding: 8px; }
      QDialog QPushButton { background: %5; color: %1; border: 1px solid %2; padding: 8px 20px; }
      QDialog QPushButton:focus, QDialog QPushButton:hover { background: %3; color: %4; }
    )").arg(color("bone").name(), color("muted").name(), color("gold").name(), color("ink").name(), sectionColor("versus", "face").name()));
}
QImage icon(const QString &name, const QColor &tint) {
    static QMap<QString, QImage> masks;
    if (!masks.contains(name)) {
        QFile file(":/kit/" + name + ".gxtex"); if (!file.open(QIODevice::ReadOnly)) return {};
        const auto b = file.readAll(); if (b.size() < 64 || b.left(4) != "GXTX" || qFromBigEndian<quint32>(b.constData() + 8) != 0) return {};
        int w = qFromBigEndian<quint32>(b.constData() + 12), h = qFromBigEndian<quint32>(b.constData() + 16);
        if (w <= 0 || h <= 0 || w > 1024 || h > 1024 || w % 8 || h % 8 || b.size() < 64 + w * h / 2) return {};
        QImage img(w, h, QImage::Format_ARGB32); int offset = 64;
        for (int by = 0; by < h; by += 8) for (int bx = 0; bx < w; bx += 8)
            for (int y = 0; y < 8; ++y) for (int x = 0; x < 8; x += 2) {
                unsigned char v = b[offset++]; img.setPixel(bx + x, by + y, qRgba(255, 255, 255, (v >> 4) * 17)); img.setPixel(bx + x + 1, by + y, qRgba(255, 255, 255, (v & 15) * 17));
            }
        masks[name] = img;
    }
    auto img = masks[name].copy(); QPainter p(&img); p.setCompositionMode(QPainter::CompositionMode_SourceIn); p.fillRect(img.rect(), tint); return img;
}
void Surface::paintEvent(QPaintEvent *) {
    QPainter p(this); p.setRenderHint(QPainter::Antialiasing); p.fillRect(rect(), sectionColor(section_, "bg"));
    p.setPen(Qt::NoPen); p.setBrush(sectionColor(section_, "band"));
    const qreal slant = height() * .25;
    for (const auto &pair : {qMakePair(30., 28.), qMakePair(width() - 92., 52.)}) {
        p.drawPolygon(QPolygonF{{pair.first + slant, 0}, {pair.first + pair.second + slant, 0}, {pair.first + pair.second, qreal(height())}, {pair.first, qreal(height())}});
    }
}
Button::Button(const QString &text, QWidget *parent) : QPushButton(text, parent) {
    setCursor(Qt::PointingHandCursor); setMinimumHeight(44); setFont(legacy::font(16, true));
    setSizePolicy(QSizePolicy::Preferred, QSizePolicy::Fixed); setMouseTracking(true);
    motion_.setDuration(duration); motion_.setEasingCurve(QEasingCurve::OutCubic);
    connect(&motion_, &QVariantAnimation::valueChanged, this, [this](const QVariant &v) { hover_ = v.toReal(); update(); });
}
void Button::enterEvent(QEnterEvent *event) { motion_.stop(); motion_.setStartValue(hover_); motion_.setEndValue(1.); motion_.start(); QPushButton::enterEvent(event); }
void Button::leaveEvent(QEvent *event) { motion_.stop(); motion_.setStartValue(hover_); motion_.setEndValue(0.); motion_.start(); QPushButton::leaveEvent(event); }
void Button::paintEvent(QPaintEvent *) {
    QPainter p(this); p.setRenderHints(QPainter::Antialiasing | QPainter::SmoothPixmapTransform);
    bool active = isChecked() || primary_; qreal lift = isDown() ? 0 : (active ? 3 : hover_ * 3);
    QRectF face(4, 4, width() - 9, height() - 10); p.setPen(Qt::NoPen);
    p.setBrush(active ? color("gold_dk") : color("ink")); p.drawPolygon(plate(face.translated(3, 4)));
    face.translate(-lift, -lift);
    p.setBrush(!isEnabled() ? sectionColor("options", "face") : active || hover_ > .5 ? color("gold") : sectionColor(section_, "face")); p.drawPolygon(plate(face));
    QColor fg = !isEnabled() ? color("disabled") : active || hover_ > .5 ? color("ink") : color("bone");
    p.setPen(fg); p.setFont(legacy::font(primary_ ? 26 : 17, true, true));
    qreal left = face.left() + 18;
    if (!icon_.isEmpty()) { p.drawImage(QRectF(left, face.center().y() - 13, 26, 26), legacy::icon(icon_, fg)); left += 38; }
    const QRectF textRect(left, face.top(), face.right() - left - 14, face.height());
    p.drawText(textRect, (icon_.isEmpty() ? Qt::AlignCenter : Qt::AlignLeft) | Qt::AlignVCenter, p.fontMetrics().elidedText(text(), Qt::ElideRight, int(textRect.width())));
    if (hasFocus()) { p.setPen(QPen(color("bone"), 1, Qt::DashLine)); p.setBrush(Qt::NoBrush); p.drawPolygon(plate(face.adjusted(4, 4, -4, -4))); }
}
void DiscDelegate::paint(QPainter *p, const QStyleOptionViewItem &opt, const QModelIndex &idx) const {
    p->save(); p->setRenderHints(QPainter::Antialiasing | QPainter::SmoothPixmapTransform);
    const bool selected = opt.state & QStyle::State_Selected;
    auto r = QRectF(opt.rect).adjusted(6, 5, -8, -7); p->setPen(Qt::NoPen); p->setBrush(selected ? color("gold_dk") : color("ink")); p->drawPolygon(plate(r.translated(3, 4)));
    if (selected) r.translate(-3, -3);
    p->setBrush(selected ? color("gold") : sectionColor("versus", "face")); p->drawPolygon(plate(r));
    auto fg = selected ? color("ink") : color("bone");
    p->drawImage(QRectF(r.left() + 24, r.center().y() - 20, 40, 40), icon("melee", selected ? color("gold_dk") : sectionColor("versus", "face_hi")));
    qreal x = r.left() + 80, available = r.width() - 103;
    p->setPen(fg); p->setFont(legacy::font(23, true, true));
    p->drawText(QRectF(x, r.top() + 12, available, 31), p->fontMetrics().elidedText(idx.data().toString(), Qt::ElideRight, int(available)));
    p->setFont(legacy::font(14)); p->setPen(selected ? color("ink") : color("muted"));
    p->drawText(QRectF(x, r.top() + 46, available, 24), p->fontMetrics().elidedText(idx.data(Qt::UserRole).toString(), Qt::ElideRight, int(available)));
    p->restore();
}
void Hero::paintEvent(QPaintEvent *) {
    QPainter p(this); p.setRenderHints(QPainter::Antialiasing | QPainter::SmoothPixmapTransform);
    auto section = kind_.contains("ACE") ? "collection" : kind_.contains("Akaneia") ? "data" : "versus";
    p.fillRect(rect(), sectionColor(section, "face")); p.setPen(Qt::NoPen); p.setBrush(sectionColor(section, "bg"));
    const qreal w = width(), h = height();
    p.drawPolygon(QPolygonF{{w * .62, 0}, {w, 0}, {w, h}, {w * .40, h}});
    p.setOpacity(.42); p.drawImage(QRectF(w - 220, -14, 250, 250), icon("melee", sectionColor(section, "face_hi"))); p.setOpacity(1.);
    const auto badge = kind_.contains("ACE") ? "ACE" : kind_.contains("Akaneia") ? "AKANEIA" : "MELEE";
    p.setPen(color("bone")); p.setFont(legacy::font(48, true, true)); p.drawText(QRectF(24, h - 83, w - 40, 68), Qt::AlignLeft | Qt::AlignVCenter, badge);
    p.setPen(color("gold")); p.setFont(legacy::font(13, true)); p.drawText(26, 30, "GD'S MELEE  /  DISC LIBRARY");
    p.fillRect(26, h - 20, 48, 4, color("gold"));
}
}
