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
    QString statusText() const;
    bool isBusy() const;
    bool shutdownComplete() const;
    // Drop queued work and stop the owned engine after the in-flight command.
    // Used by the launcher before replacing a project or closing its window.
    void shutdown();
signals:
    void commandFinished(const QString &name, const QJsonObject &reply);
    void busyChanged(bool busy);
    void shutdownFinished();
protected:
    void closeEvent(QCloseEvent *event) override;
private:
    struct Impl;
    std::unique_ptr<Impl> d_;
};
}
