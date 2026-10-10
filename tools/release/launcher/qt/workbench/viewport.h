#pragma once
#include "engine_link.h"
#include <QImage>
#include <QMap>
#include <QPointF>
#include <QWidget>

class QPainter;

namespace wb {
class Viewport : public QWidget {
    Q_OBJECT
public:
    explicit Viewport(QWidget *parent = nullptr);
    void setImage(const QImage &img);
    void setFrameInfo(const FrameInfo &fi);
    void setOverlay(const QString &name, bool on);
    void setCamera(const QJsonObject &camera); // feedback; does not emit
signals:
    void cameraChanged(const QJsonObject &camera);
protected:
    void paintEvent(QPaintEvent *) override;
    void mousePressEvent(QMouseEvent *) override;
    void mouseMoveEvent(QMouseEvent *) override;
    void mouseReleaseEvent(QMouseEvent *) override;
    void wheelEvent(QWheelEvent *) override;
private:
    void dragTo(const QPointF &position);
    void publishCamera();
    void paintGuide(QPainter &p, const QRectF &area);
    QImage image_;
    FrameInfo info_;
    bool haveInfo_ = false, dragging_ = false;
    QPointF lastMouse_;
    double yaw_ = 0, pitch_ = 0, distance_ = 40;
    QMap<QString, bool> overlays_{{"hitboxes", true}, {"hurtboxes", false},
                                  {"bones", false}, {"ecb", false}, {"floor", true}};
};
}
