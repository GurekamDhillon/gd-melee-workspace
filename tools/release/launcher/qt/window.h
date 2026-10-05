#pragma once
#include "diagnostics.h"
#include "launcher_core.h"
#include <QMainWindow>
#include <QElapsedTimer>
#include <QProcess>
#include <functional>
class QTableWidget;
class QLabel;
class QStackedWidget;
class QPushButton;
class QCloseEvent;
class QComboBox;
class QPlainTextEdit;
class QTimer;

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
#ifdef Q_OS_LINUX
    QProcess graphicsProcess_;
    QTimer *graphicsTimeout_ = nullptr;
    QComboBox *graphicsDevice_ = nullptr;
    QPlainTextEdit *graphicsDetails_ = nullptr;
    QByteArray graphicsOutput_, graphicsErrors_;
    LaunchSpec pendingLaunch_;
    bool graphicsBusy_ = false, graphicsForLaunch_ = false, graphicsTimedOut_ = false;
    void checkGraphics(bool forLaunch);
    void finishGraphics(int code);
#endif
    // Launch diagnostics: a report is written for every attempt (see diagnostics.h).
    DiagContext diag_;
    QElapsedTimer launchClock_;
    DiagContext diagContext(bool full) const;
    void finishLaunchReport(bool showDialog);
    void showLaunchFailure(const DiagResult &report, const QString &extra = {});
    void runDiagnosticsOnly();
    void copyDiagnostics();
    void startGame(const LaunchSpec &spec);
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
