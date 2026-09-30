#pragma once
#include "launcher_core.h"
#include <QMainWindow>
#include <QProcess>
#include <functional>
class QTableWidget;
class QLabel;
class QStackedWidget;
class QPushButton;
class QCloseEvent;

namespace launcher {
namespace kit { class Hero; class Surface; }
extern bool spanish;
QString t(const char *en, const char *es);
class Window : public QMainWindow {
public:
    Window(QString appDir, QString userDir, Settings settings);
    void addDisc(const QString &path = {});
    void play();
    void selectMods();
    void screenshots(const QString &dir);
protected:
    void closeEvent(QCloseEvent *event) override;
private:
    QString appDir_, userDir_, runDir_;
    Settings settings_;
    QProcess process_;
    QStackedWidget *tabs_;
    kit::Surface *surface_;
    kit::Hero *hero_;
    QLabel *discTitle_;
    QLabel *pageHeading_;
    QVector<QPushButton *> navigation_;
    QTableWidget *discs_, *mods_;
    QLabel *discDetails_, *modDetails_;
    QPushButton *play_;
    bool filling_ = false;
    bool quitting_ = false;
    void guarded(const std::function<void()> &action);
    void save();
    void refreshDiscs(const QString &selectId = {});
    void refreshMods();
    int selectedDisc() const;
    QWidget *playTab();
    QWidget *modsTab();
    QWidget *diagnosticsTab();
    QWidget *aboutTab();
    void openPath(const QString &path);
};
}
