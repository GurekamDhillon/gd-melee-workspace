#include "viewport.h"
#include "atlas.h"
#include "kit.h"
#include "window.h"
#include <QMouseEvent>
#include <QPainter>
#include <QWheelEvent>
#include <algorithm>
#include <cmath>

namespace wb {
using launcher::t;
namespace atlas = launcher::atlas;
Viewport::Viewport(QWidget *parent) : QWidget(parent) {
    setObjectName("wbViewport"); setFocusPolicy(Qt::StrongFocus);
    setMinimumSize(320, 360); setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Expanding);
    setAccessibleName(t("Fighter viewport", "Vista del luchador"));
    setToolTip(t("Drag to orbit. Scroll to zoom.", "Arrastra para orbitar. Desplázate para acercar."));
}
void Viewport::setImage(const QImage &img) { image_ = img; update(); }
void Viewport::setFrameInfo(const FrameInfo &fi) { info_ = fi; haveInfo_ = true; update(); }
void Viewport::setOverlay(const QString &name, bool on) {
    if (!overlays_.contains(name)) return;
    overlays_[name] = on; update();
}
void Viewport::setSelectedHitbox(int slot, int startFrame, int endFrame) {
    selectedSlot_ = slot; selectedStart_ = startFrame; selectedEnd_ = endFrame; update();
}
void Viewport::setCamera(const QJsonObject &camera) {
    const QString preset = camera.value("preset").toString();
    if (!preset.isEmpty()) {
        yaw_ = preset == "front" ? 90 : preset == "three_quarter" ? 45 : 0;
        pitch_ = preset == "top" ? 89 : preset == "three_quarter" ? 20 : 0;
    }
    auto number = [&](const char *key, double fallback) {
        const auto v = camera.value(key);
        return v.isDouble() && std::isfinite(v.toDouble()) ? v.toDouble() : fallback;
    };
    yaw_ = number("yaw", yaw_); pitch_ = std::clamp(number("pitch", pitch_), -89.0, 89.0);
    distance_ = std::clamp(number("distance", distance_), 1.0, 10000.0); update();
}
void Viewport::publishCamera() { emit cameraChanged({{"yaw", yaw_}, {"pitch", pitch_}, {"distance", distance_}}); }
void Viewport::dragTo(const QPointF &position) {
    const auto delta = position - lastMouse_; lastMouse_ = position;
    if (delta.isNull()) return;
    yaw_ += delta.x() * 0.5; pitch_ = std::clamp(pitch_ + delta.y() * 0.5, -89.0, 89.0);
    publishCamera();
}
void Viewport::mousePressEvent(QMouseEvent *e) {
    if (e->button() != Qt::LeftButton) return QWidget::mousePressEvent(e);
    setFocus(Qt::MouseFocusReason); dragging_ = true; lastMouse_ = e->position(); e->accept();
}
void Viewport::mouseMoveEvent(QMouseEvent *e) {
    if (dragging_) dragTo(e->position()); else QWidget::mouseMoveEvent(e);
}
void Viewport::mouseReleaseEvent(QMouseEvent *e) {
    if (dragging_ && e->button() == Qt::LeftButton) { dragTo(e->position()); dragging_ = false; e->accept(); }
    else QWidget::mouseReleaseEvent(e);
}
void Viewport::wheelEvent(QWheelEvent *e) {
    if (!e->angleDelta().y()) return QWidget::wheelEvent(e);
    distance_ = std::clamp(distance_ * std::pow(0.9, e->angleDelta().y() / 120.0), 1.0, 10000.0);
    publishCamera(); e->accept();
}
void Viewport::paintEvent(QPaintEvent *) {
    QPainter p(this); p.fillRect(rect(), atlas::colour("ground2"));
    QRectF picture = rect();
    const bool guide = haveInfo_ && std::any_of(overlays_.cbegin(), overlays_.cend(), [](bool on) { return on; });
    // FrameInfo contains world positions, not the game's projection matrix.
    // Keep the schematic beside the unmodified screenshot: guessed circles over
    // the fighter would incorrectly claim to be aligned to the real camera.
    if (guide && !image_.isNull()) picture.setRight(std::max(100, width() - std::min(200, width() / 3)));
    if (!image_.isNull()) {
        QSizeF size = image_.size(); size.scale(picture.size(), Qt::KeepAspectRatio);
        QRectF target(QPointF(), size); target.moveCenter(picture.center());
        p.setRenderHint(QPainter::SmoothPixmapTransform); p.drawImage(target, image_);
    } else if (!guide) {
        launcher::kit::paintHatch(p, atlas::plate(picture, atlas::px("ch-s")), atlas::colour("line"));
        p.setFont(atlas::font(atlas::Role::Body14)); p.setPen(atlas::colour("muted"));
        p.drawText(picture.adjusted(16, 16, -16, -16), Qt::AlignCenter | Qt::TextWordWrap,
                   t("Start the engine to see the fighter.", "Inicia el motor para ver al luchador."));
    }
    if (guide) paintGuide(p, image_.isNull() ? QRectF(rect()) : QRectF(picture.right(), 0, width() - picture.right(), height()));
}
void Viewport::paintGuide(QPainter &p, const QRectF &area) {
    p.save(); p.setClipRect(area); p.fillRect(area, atlas::colour("plate"));
    p.setFont(atlas::font(atlas::Role::Body12)); p.setPen(atlas::colour("muted"));
    p.drawText(area.adjusted(8, 6, -8, 0), Qt::AlignTop | Qt::AlignHCenter,
               t("2D overlay guide", "Guía de capas 2D"));
    double minX = -5, maxX = 5, minY = info_.floorY - 2, maxY = info_.floorY + 20;
    auto bound = [&](const Vec3 &v, double r = 0) {
        if (!std::isfinite(v.x) || !std::isfinite(v.y) || !std::isfinite(r)) return;
        minX = std::min(minX, v.x - r); maxX = std::max(maxX, v.x + r);
        minY = std::min(minY, v.y - r); maxY = std::max(maxY, v.y + r);
    };
    for (const auto &b : info_.bones) bound(b.pos);
    for (const auto &h : info_.hitboxes) if (h.active) bound(h.world, std::max(0.0, h.radius));
    for (const auto &h : info_.hurtboxes) { bound(h.a, h.radius); bound(h.b, h.radius); }
    bound(info_.ecbBottom); bound(info_.ecbTop);
    const QRectF plot = area.adjusted(12, 32, -12, -12);
    const double scale = std::max(0.1, std::min(plot.width() / (maxX - minX), plot.height() / (maxY - minY)));
    auto pos = [&](const Vec3 &v) { return QPointF(plot.center().x() + (v.x - (minX + maxX) / 2) * scale,
                                                 plot.center().y() - (v.y - (minY + maxY) / 2) * scale); };
    p.setRenderHint(QPainter::Antialiasing);
    if (overlays_.value("floor")) {
        p.setPen(QPen(atlas::colour("muted"), 1));
        const qreal y = pos({0, info_.floorY, 0}).y(); p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y));
    }
    if (overlays_.value("bones")) {
        p.setPen(QPen(atlas::colour("ivory"), 1));
        QMap<int, Vec3> bones; for (const auto &b : info_.bones) bones.insert(b.joint, b.pos);
        for (const auto &b : info_.bones) {
            if (bones.contains(b.parent)) p.drawLine(pos(b.pos), pos(bones.value(b.parent)));
            p.drawEllipse(pos(b.pos), 2, 2);
        }
    }
    if (overlays_.value("hurtboxes")) {
        p.setPen(QPen(atlas::colour("jade"), 1)); p.setBrush(Qt::NoBrush);
        for (const auto &h : info_.hurtboxes) {
            const double r = std::max(0.0, h.radius) * scale;
            p.drawLine(pos(h.a), pos(h.b)); p.drawEllipse(pos(h.a), r, r); p.drawEllipse(pos(h.b), r, r);
        }
    }
    if (overlays_.value("hitboxes")) {
        p.setBrush(Qt::NoBrush);
        for (const auto &h : info_.hitboxes) if (h.active) {
            // A source ordinal may reuse a runtime slot later in the move.
            const bool selected = h.slot == selectedSlot_ && info_.frame >= selectedStart_ &&
                                  (selectedEnd_ < 0 || info_.frame < selectedEnd_);
            p.setPen(QPen(atlas::colour(selected ? "sun" : "ember"), selected ? 3 : 2));
            const double r = std::max(0.0, h.radius) * scale; p.drawEllipse(pos(h.world), r, r);
        }
    }
    if (overlays_.value("ecb")) {
        p.setPen(QPen(atlas::colour("sun"), 2)); p.drawLine(pos(info_.ecbBottom), pos(info_.ecbTop));
        for (const auto &v : {info_.ecbBottom, info_.ecbTop}) {
            const auto at = pos(v); p.drawLine(at - QPointF(5, 0), at + QPointF(5, 0));
        }
    }
    p.restore();
}
}
