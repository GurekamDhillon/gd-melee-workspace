#pragma once
#include <QPair>
#include <QVector>
#include <QWidget>

namespace wb {
class Timeline : public QWidget {
    Q_OBJECT
public:
    explicit Timeline(QWidget *parent = nullptr);
    virtual void setRange(int frames);
    void setBars(const QVector<QPair<QString, QPair<int, int>>> &bars);
    void setFrame(int f);
    void setPlaying(bool playing); // feedback only; never echoes playToggled
    bool scrubbing() const { return scrubbing_; }
    int frame() const { return frame_; }
    int frameCount() const { return frames_; }
    QSize sizeHint() const override;
signals:
    void frameRequested(int f);
    void playToggled(bool playing);
protected:
    void paintEvent(QPaintEvent *) override;
    void keyPressEvent(QKeyEvent *) override;
    void mousePressEvent(QMouseEvent *) override;
    void mouseMoveEvent(QMouseEvent *) override;
    void mouseReleaseEvent(QMouseEvent *) override;
private:
    void request(int f);
    void scrub(qreal x);
    int frames_ = 0, frame_ = 0;
    bool playing_ = false, scrubbing_ = false;
    QVector<QPair<QString, QPair<int, int>>> bars_;
};
}
