#pragma once
#include "geno_asm.h"
#include "timeline.h"
#include <QDoubleSpinBox>
#include <QElapsedTimer>
#include <QJsonArray>
#include <QJsonObject>
#include <QPushButton>
#include <QTabWidget>

class QLabel;
class QProgressBar;
class QTimer;

namespace wb {
// Applies only to this widget and its descendants; the launcher's theme is untouched.
void applyAtlasStyle(QWidget *root);

// The approved Workbench plates cut the top-right and bottom-left corners.
// Number fields, combos and sliders only take the mouse wheel while they have keyboard focus;
// otherwise the wheel scrolls the enclosing scroll area. Idempotent; installs on the application.
void installWheelGuard();

class AtlasPlate : public QWidget {
    Q_OBJECT
public:
    explicit AtlasPlate(QWidget *parent = nullptr);
    void setElevated(bool elevated) { elevated_ = elevated; update(); }
protected:
    void paintEvent(QPaintEvent *) override;
private:
    bool elevated_ = false;
};

class AtlasButton : public QPushButton {
    Q_OBJECT
public:
    enum Tone { Normal, Ember, Danger };
    Q_ENUM(Tone)
    explicit AtlasButton(const QString &text, QWidget *parent = nullptr);
    void setTone(Tone tone);
    Tone tone() const { return tone_; }
    QSize sizeHint() const override;
    QSize minimumSizeHint() const override;
protected:
    void paintEvent(QPaintEvent *) override;
private:
    Tone tone_ = Tone::Normal;
};

class NumberField : public QDoubleSpinBox {
    Q_OBJECT
public:
    explicit NumberField(QWidget *parent = nullptr);
};

class InspectorTabs : public QTabWidget {
    Q_OBJECT
public:
    explicit InspectorTabs(QWidget *parent = nullptr);
};

class StatusProgress : public QWidget {
    Q_OBJECT
public:
    explicit StatusProgress(QWidget *parent = nullptr);
    void begin(const QString &phase, bool cancellable = false);
    void setProgress(const QString &phase, int percent = -1, qint64 elapsedMs = -1,
                     bool cancellable = false);
    void finish(const QString &message, bool success = true);
    void setMessage(const QString &message);
    bool isRunning() const { return running_; }
signals:
    void cancelRequested();
private:
    void refreshElapsed();
    QLabel *phase_ = nullptr;
    QLabel *elapsedLabel_ = nullptr;
    QProgressBar *progress_ = nullptr;
    AtlasButton *cancel_ = nullptr;
    QTimer *ticker_ = nullptr;
    QElapsedTimer elapsed_;
    qint64 elapsedBase_ = 0;
    bool running_ = false, cancelPending_ = false;
};

class TimelineView : public Timeline {
    Q_OBJECT
public:
    explicit TimelineView(QWidget *parent = nullptr);
    // Frames are zero-based, as in set_frame. A hitbox end is an exclusive boundary.
    void setMove(const QString &row, int frames, const QVector<HitboxRef> &hits, int iasa,
                 const QJsonArray &events = {});
    void setSelectedHitbox(int ordinal);
    void setRange(int frames) override;
    bool scrubbing() const override { return scrubbing_; }
    // Shared painting/hit-testing geometry, also useful to overlays and accessibility tools.
    qreal framePosition(int boundary) const;
    QRectF hitboxRect(int ordinal) const;
    QRectF rulerRect() const;
    // Width of the row-label column: fits the longest label when there is room, else a share of the width.
    qreal labelColumn() const;
    QSize sizeHint() const override;
    QSize minimumSizeHint() const override;
signals:
    void editRequested(const QString &command, const QJsonObject &args);
    void hitboxSelected(int ordinal);
protected:
    bool event(QEvent *) override;
    void paintEvent(QPaintEvent *) override;
    void keyPressEvent(QKeyEvent *) override;
    void mousePressEvent(QMouseEvent *) override;
    void mouseMoveEvent(QMouseEvent *) override;
    void mouseReleaseEvent(QMouseEvent *) override;
    void focusOutEvent(QFocusEvent *) override;
    void leaveEvent(QEvent *) override;
private:
    enum class Handle { None, Start, End };
    struct Drag {
        Handle handle = Handle::None;
        int index = -1;
        int originalStart = 0, originalEnd = 0;
        int start = 0, end = 0;
        qreal pressX = 0;
    } drag_;
    bool validWindow(const HitboxRef &hit) const;
    int hitboxIndex(int ordinal) const;
    QRectF trackRect(int row) const;
    QRectF windowRect(int start, int end, int row) const;
    QRectF hitboxRectAt(int index) const;
    Handle handleAt(const QRectF &rect, const QPointF &position) const;
    void updateDrag(qreal x);
    void cancelDrag();
    void requestFrame(int frame);
    void seek(qreal x);
    QString row_;
    QVector<HitboxRef> hits_;
    QJsonArray events_;
    int iasa_ = 0, selected_ = -1;
    bool scrubbing_ = false;
};
} // namespace wb
