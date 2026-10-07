#pragma once
#include "crash_upload.h"
#include "diagnostics.h"
#include "launcher_core.h"
#include <QMainWindow>
#include <QElapsedTimer>
#include <QProcess>
#include <atomic>
#include <functional>
class QTableWidget;
class QLabel;
class QStackedWidget;
class QPushButton;
class QCloseEvent;
class QComboBox;
class QPlainTextEdit;
class QTimer;
class QThread;

namespace launcher {
namespace kit { class TabRail; }
extern bool spanish;
QString t(const char *en, const char *es);
void applyTheme();                      // atlas tokens, fonts, palette and the style sheet for what Qt draws itself
class Window : public QMainWindow {
public:
    Window(QString appDir, QString userDir, Settings settings);
    ~Window() override;
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
    kit::TabRail *rail_;
    QWidget *keys_;
    QLabel *pageSub_;
    QLabel *discTitle_;
    QLabel *pageHeading_;
    QTableWidget *discs_, *mods_;
    QLabel *discDetails_, *modDetails_;
    QLabel *modTitle_ = nullptr, *modVersion_ = nullptr, *modRequires_ = nullptr, *modConflicts_ = nullptr;
    QPushButton *play_ = nullptr;
    QWidget *playNote_ = nullptr;
    QLabel *modsOnLabel_ = nullptr;
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
    // "Upload last 3 crash logs": the only way anything leaves the machine, and only with the opt-in on.
    QPushButton *crashUpload_ = nullptr;
    QThread *uploadThread_ = nullptr;
    std::atomic<bool> uploadCancel_{false};
    void uploadCrashes();
    void finishCrashUpload(const CrashUploadResult &result);
    void startGame(const LaunchSpec &spec);
    void guarded(const std::function<void()> &action);
    void save();
    void refreshDiscs(const QString &selectId = {});
    void refreshMods();
    void showSelectedDisc();
    void showSelectedMod();
    void updatePlayState();
    int selectedDisc() const;
    QWidget *playTab();
    QWidget *modsTab();
    QWidget *diagnosticsTab();
    QWidget *aboutTab();
    void openPath(const QString &path);
    void setKeys(int tab);
};
}
