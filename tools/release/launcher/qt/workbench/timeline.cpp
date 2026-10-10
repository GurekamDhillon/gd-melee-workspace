#include "timeline.h"
#include "atlas.h"
#include "window.h"
#include <QKeyEvent>
#include <QMouseEvent>
#include <QPainter>
#include <algorithm>
#include <cmath>

namespace wb {
using launcher::t;
namespace atlas = launcher::atlas;
Timeline::Timeline(QWidget *parent) : QWidget(parent) {
    setObjectName("wbTimeline"); setFocusPolicy(Qt::StrongFocus);
    setAccessibleName(t("Timeline", "Línea de tiempo"));
    setToolTip(t("J / L: step. K: play or pause. Home / End: first or last frame.",
                 "J / L: avanzar. K: reproducir o pausar. Inicio / Fin: primer o último cuadro."));
    setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Minimum);
}
void Timeline::setRange(int frames) {
    frames_ = std::max(0, frames); setFrame(frame_);
    if (!frames_) setPlaying(false);
}
void Timeline::setBars(const QVector<QPair<QString, QPair<int, int>>> &bars) {
    bars_ = bars; updateGeometry(); update();
}
void Timeline::setFrame(int f) { frame_ = std::clamp(f, 0, std::max(0, frames_ - 1)); update(); }
void Timeline::setPlaying(bool playing) { playing_ = playing && frames_ > 0; update(); }
QSize Timeline::sizeHint() const { return {400, 68 + int(bars_.size()) * 20}; }
void Timeline::request(int f) {
    if (!frames_) return;
    f = std::clamp(f, 0, frames_ - 1);
    if (f == frame_) return;
    setFrame(f); emit frameRequested(f);
}
void Timeline::scrub(qreal x) {
    const qreal ratio = std::clamp((x - 12) / std::max(1, width() - 24), 0.0, 1.0);
    request(int(std::floor(ratio * frames_)));
}
void Timeline::keyPressEvent(QKeyEvent *e) {
    if (e->modifiers() != Qt::NoModifier) return QWidget::keyPressEvent(e);
    switch (e->key()) {
    case Qt::Key_J: request(frame_ - 1); break;
    case Qt::Key_L: request(frame_ + 1); break;
    case Qt::Key_Home: request(0); break;
    case Qt::Key_End: request(frames_ - 1); break;
    case Qt::Key_K:
        if (!e->isAutoRepeat() && frames_) { setPlaying(!playing_); emit playToggled(playing_); }
        break;
    default: return QWidget::keyPressEvent(e);
    }
    e->accept();
}
void Timeline::mousePressEvent(QMouseEvent *e) {
    if (e->button() != Qt::LeftButton) return QWidget::mousePressEvent(e);
    setFocus(Qt::MouseFocusReason); scrubbing_ = true; scrub(e->position().x()); e->accept();
}
void Timeline::mouseMoveEvent(QMouseEvent *e) {
    if (scrubbing_) scrub(e->position().x()); else QWidget::mouseMoveEvent(e);
}
void Timeline::mouseReleaseEvent(QMouseEvent *e) {
    if (scrubbing_ && e->button() == Qt::LeftButton) { scrub(e->position().x()); scrubbing_ = false; }
    else QWidget::mouseReleaseEvent(e);
}
void Timeline::paintEvent(QPaintEvent *) {
    QPainter p(this); p.fillRect(rect(), atlas::colour("ground2"));
    p.setFont(atlas::font(atlas::Role::Body12)); p.setPen(atlas::colour("ivory"));
    p.drawText(QRect(12, 4, width() - 24, 22), Qt::AlignLeft | Qt::AlignVCenter,
               t("Frame %1", "Cuadro %1").arg(frame_));
    p.drawText(QRect(12, 4, width() - 24, 22), Qt::AlignRight | Qt::AlignVCenter,
               playing_ ? t("Playing", "Reproduciendo") : t("Paused", "En pausa"));
    const qreal span = std::max(1, width() - 24);
    p.setPen(atlas::colour("line2")); p.drawLine(QPointF(12, 36), QPointF(width() - 12, 36));
    if (!frames_) return;
    auto x = [&](int f) { return 12 + span * std::clamp(f, 0, frames_) / frames_; };
    const int tick = std::max(1, int(std::ceil(frames_ / 10.0)));
    for (int f = 0; f < frames_; f += tick) {
        p.setPen(atlas::colour("muted")); p.drawLine(QPointF(x(f), 32), QPointF(x(f), 40));
        p.drawText(QRectF(x(f), 40, 40, 18), Qt::AlignLeft, QString::number(f));
    }
    int y = 62;
    for (const auto &bar : bars_) {
        const int start = std::clamp(bar.second.first, 0, frames_);
        const int end = bar.second.second < 0 ? frames_ : std::clamp(bar.second.second, start, frames_);
        p.fillRect(QRectF(x(start), y, std::max(1.0, x(end) - x(start)), 16), atlas::colour("jade"));
        p.setPen(atlas::colour("ivory"));
        p.drawText(QRectF(16, y, width() - 32, 18), Qt::AlignLeft | Qt::AlignVCenter,
                   atlas::fit(QFontMetricsF(p.font()), bar.first, width() - 32));
        y += 20;
    }
    const qreal cursor = 12 + span * frame_ / frames_;
    p.setPen(QPen(atlas::colour("ember"), 2)); p.drawLine(QPointF(cursor, 28), QPointF(cursor, height() - 4));
    if (hasFocus()) { p.setPen(atlas::colour("ember")); p.drawRect(rect().adjusted(0, 0, -1, -1)); }
}
}
