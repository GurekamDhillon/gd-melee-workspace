#pragma once
#include <QWidget>
class QCheckBox;
class QLabel;
class QPushButton;
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
    void setHeadless(bool headless);
    void setPlayControls(bool busy, const QString &error);
    void setControls(bool busy, bool canStop, bool canChangeMode, const QString &blenderError);
    void setBlenderState(bool hasProcess, bool synced);
    void setPendingChanges(int count);
    void setRebuildAvailable(bool available);
signals:
    void startRequested();
    void stopRequested();
    void restartRequested();
    void openInBlenderRequested();
    void showBlenderRequested();
    void headlessChanged(bool headless);
    void playInLabRequested();
    void playVsCpuRequested();
    void undoRequested();
    void rebuildRequested();
private:
    QVBoxLayout *layout_;
    QWidget *controls_, *blenderCard_;
    QLabel *project_, *counts_, *engine_, *move_, *blenderState_, *pending_;
    QPushButton *start_, *stop_, *restart_, *blender_, *showBlender_, *playLab_, *playCpu_, *undo_, *rebuild_;
    QCheckBox *headless_;
    bool busy_ = false, rebuildAvailable_ = false;
};
}
