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
    void setProject(const QString &name, int rows, int hitboxes);
    void setEngineStatus(const QString &status);
    void setHeadless(bool headless);
    void setPlayControls(bool busy, const QString &error);
    void setControls(bool busy, bool canStop, bool canChangeMode, const QString &blenderError);
signals:
    void startRequested();
    void stopRequested();
    void restartRequested();
    void openInBlenderRequested();
    void headlessChanged(bool headless);
    void playInLabRequested();
    void playVsCpuRequested();
private:
    QVBoxLayout *layout_;
    QLabel *project_, *counts_, *engine_;
    QPushButton *start_, *stop_, *restart_, *blender_, *playLab_, *playCpu_;
    QLabel *playNote_;
    QCheckBox *headless_;
};
}
