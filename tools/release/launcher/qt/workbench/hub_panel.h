#pragma once
#include <QWidget>
class QCheckBox;
class QLabel;
class QPushButton;
class QHBoxLayout;
class QVBoxLayout;

namespace wb {
class HubPanel : public QWidget {
    Q_OBJECT
public:
    explicit HubPanel(QWidget *parent = nullptr);
    QVBoxLayout *bodyLayout() const { return layout_; }
    QWidget *engineControls() const { return controls_; }
    QWidget *blenderCard() const { return blenderCard_; }
    QLabel *projectCounts() const { return counts_; }
    void setProject(const QString &name, int rows, int hitboxes);
    void setMove(const QString &row);
    void setEngineStatus(const QString &status);
    void setEngineDetail(const QString &detail);
    void setHeadless(bool headless);
    void setPlayControls(bool busy, const QString &error);
    void setControls(bool busy, bool canStop, bool canChangeMode, const QString &blenderError);
    void setBlenderState(bool hasProcess, bool synced);
    void setPendingChanges(int count);
    void setRebuildAvailable(bool available);
    // True while the status chips and the secondary buttons sit on a second row.
    bool wrapped() const { return wrapped_; }
signals:
    void startRequested();
    void stopRequested();
    void restartRequested();
    void openInBlenderRequested();
    void showBlenderRequested();
    void revertAllRequested();
    void headlessChanged(bool headless);
    void playInLabRequested();
    void playVsCpuRequested();
    void undoRequested();
    void rebuildRequested();
protected:
    void resizeEvent(QResizeEvent *) override;
    QSize minimumSizeHint() const override;
private:
    void relayoutBar();
    QVBoxLayout *layout_;
    QHBoxLayout *first_ = nullptr, *second_ = nullptr;
    QWidget *secondRow_ = nullptr, *bar_ = nullptr;
    QWidget *breadcrumb_[5] = {};
    bool wrapped_ = false, wrapKnown_ = false;
    QWidget *controls_, *blenderCard_;
    QString engineDetail_, engineBase_;
    QLabel *project_, *counts_, *move_, *pending_;
    QPushButton *engine_, *blenderState_; // status chips that are also the start/stop controls
    bool engineRunning_ = false, engineStarting_ = false, blenderRunning_ = false;
    QPushButton *revertAll_, *start_, *stop_, *restart_, *blender_, *showBlender_, *playLab_, *playCpu_, *undo_, *rebuild_;
    QCheckBox *headless_;
    bool busy_ = false, rebuildAvailable_ = false;
};
}
