#pragma once
#include "engine_link.h"
#include <QMainWindow>
#include <functional>
#include <memory>

namespace wb {
class Session;
class WorkbenchWindow : public QMainWindow {
    Q_OBJECT
public:
    // The caller retains ownership and gives this window exclusive access until
    // destruction. A QObject-backed engine must be constructed on the worker;
    // use the owned-project overload for the real EngineLink.
    explicit WorkbenchWindow(Session &s, QWidget *parent = nullptr);
    // The factory runs on the persistent worker when the engine is first started
    // or its mode changes. Open in Blender starts a stopped engine before launch.
    using LaunchFactory = std::function<EngineLink::Launch()>;
    WorkbenchWindow(const QString &projectDir, LaunchFactory launch, QWidget *parent = nullptr);
    ~WorkbenchWindow() override;
    void runCommand(const QString &name, const QJsonObject &args);
    // Starts one human-author localhost listener on this window's Session.
    // Returns zero while initializing/busy or after shutdown.
    quint16 serveForBlender();
    void setBlenderSetting(const QString &path);
    // Shown as the tooltip of the game status chip: which exe the engine starts.
    void setGameExeInfo(const QString &text);
    QString statusText() const;
    // The two Fix actions that need a file picker the launcher owns (it holds the Settings).
    // Start the game / Blender the way the buttons do.
    void startGame();
    void startBlender();
    // Async rebuild lane: connect progress here and cancellation to the job,
    // bypassing the serial command queue. percent < 0 means indeterminate.
    void reportRebuildProgress(const QString &phase, int percent = -1, qint64 elapsedMs = -1, bool cancellable = false);
    void setBlenderProcessId(qint64 pid);
    bool isBusy() const;
    bool shutdownComplete() const;
    // Drop queued work and stop the owned engine after the in-flight command.
    // Used by the launcher before replacing a project or closing its window.
    void shutdown();
signals:
    void commandFinished(const QString &name, const QJsonObject &reply);
    void busyChanged(bool busy);
    void shutdownFinished();
    void rebuildProgress(const QString &phase, int percent, qint64 elapsedMs, bool cancellable);
    void rebuildCancelRequested();
    // The status bar's Fix button asks the launcher for the picker; the launcher stores the choice.
    void gameExePickRequested();
    void blenderPickRequested();
protected:
    void closeEvent(QCloseEvent *event) override;
    void resizeEvent(QResizeEvent *event) override;
private:
    struct Impl;
    std::unique_ptr<Impl> d_;
};
}
