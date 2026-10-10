#include "workbench_window.h"
#include "window.h"
#define WB_CORE_USE_LAUNCHER_T 1
#include "commands.h"
#include "geno_data.h"
#include "session.h"
#include "timeline.h"
#include "viewport.h"
#include "kit.h"
#include "window.h"
#include <QCheckBox>
#include <QCloseEvent>
#include <QComboBox>
#include <QDateTime>
#include <QElapsedTimer>
#include <QFileInfo>
#include <QFutureWatcher>
#include <QHBoxLayout>
#include <QImageReader>
#include <QLabel>
#include <QQueue>
#include <QScrollArea>
#include <QSemaphore>
#include <QShortcut>
#include <QSignalBlocker>
#include <QStatusBar>
#include <QThreadPool>
#include <QTimer>
#include <QVBoxLayout>
#include <QtConcurrent/QtConcurrentRun>
#include <algorithm>
#include <exception>
#include <optional>
#include <utility>

namespace wb {
using launcher::t;
namespace atlas = launcher::atlas;
namespace kit = launcher::kit;
namespace {
QJsonObject failure(const QString &error) { return {{"ok", false}, {"error", error}}; }
QString displayError(const QString &error) {
    if (error.compare("engine not running", Qt::CaseInsensitive) == 0)
        return t("Engine not running", "Motor detenido");
    return t("Command failed: %1", "Error del comando: %1").arg(error);
}
// Created, called and destroyed on the same non-expiring, single-thread pool.
// Starting remains lazy so a fighter can be inspected without a disc or engine.
class ProjectEngine final : public EngineBackend {
public:
    WorkbenchWindow::LaunchFactory factory;
    QString modId;
    std::unique_ptr<EngineLink> link;
    QJsonObject call(const QString &fn, const QJsonObject &args, QString *err) override {
        if (!link) { if (err) *err = "engine not running"; return {}; }
        return link->call(fn, args, err);
    }
    QString status() override { return link ? link->status() : QString("stopped"); }
    bool restart(QString *err) override {
        if (!link) {
            auto launch = factory(); launch.modId = modId;
            link = std::make_unique<EngineLink>(std::move(launch));
        }
        return link->restart(err);
    }
    void stop() { if (link) link->stop(); }
};
struct Snapshot {
    QVector<RowInfo> rows;
    QVector<ClipInfo> clips;
    QMap<QString, QVector<HitboxRef>> hits;
};
struct Reply {
    QJsonObject envelope;
    Snapshot snapshot;
    QDateTime renderStarted;
};
struct Worker {
    Session *session = nullptr;
    QString projectDir;
    WorkbenchWindow::LaunchFactory factory;
    std::unique_ptr<ProjectEngine> engine;
    std::unique_ptr<Session> owned;
    void ensureSession() {
        if (session) return;
        engine = std::make_unique<ProjectEngine>(); engine->factory = factory;
        owned = std::make_unique<Session>(projectDir, engine.get());
        const QString err = owned->data().reload();
        if (!err.isEmpty()) { owned.reset(); engine.reset(); throw CommandError{err}; }
        engine->modId = owned->data().project().modId;
        registerAllCommands(*owned);
        // Lifecycle of the process the UI owns, exposed through the same registry.
        // This adds a command; it does not replace any Task 9/10 command.
        owned->registry().add({"engine_stop", t("Stop engine", "Detener motor"),
            {{"type", "object"}, {"properties", QJsonObject{}}}, false,
            [this](const QJsonObject &, CommandContext &) {
                engine->stop(); return QJsonObject{{"status", "stopped"}};
            }});
        session = owned.get();
    }
    Reply call(const QString &name, const QJsonObject &args) {
        Reply result;
        try {
            ensureSession();
            CommandContext ctx{*session, "human", args.value("propose").toBool()};
            if (name == "render_view") result.renderStarted = QDateTime::currentDateTimeUtc();
            // Owner decision: reload means restart in v1. Do not change the
            // parallel command lane's reload implementation or its interfaces.
            result.envelope = session->registry().call(name == "reload" ? QString("engine_restart") : name, args, ctx);
            if (result.envelope.value("ok").toBool() && (name == "reload" || name == "engine_restart")) {
                const auto err = session->data().reload();
                if (!err.isEmpty()) result.envelope = failure(err);
            }
            result.snapshot.rows = session->data().rows();
            result.snapshot.clips = session->data().clips();
            for (const auto &row : result.snapshot.rows) result.snapshot.hits.insert(row.name, session->data().hitboxes(row.name));
        } catch (const CommandError &e) { result.envelope = failure(e.message); }
          catch (const std::exception &e) { result.envelope = failure(QString::fromUtf8(e.what())); }
          catch (...) { result.envelope = failure("unexpected command failure"); }
        return result;
    }
    void dispose() {
        // Session history flush and all QObject destructors run on their owner thread.
        if (owned) { session = nullptr; owned.reset(); }
        engine.reset();
    }
};
struct Request {
    QString name; QJsonObject args;
    quint64 revision = 0, render = 0, rowIntent = 0, frameIntent = 0;
    std::optional<int> restoreFrame;
};
bool changesView(const QString &name) {
    return name == "set_frame" || name == "set_camera" || name == "set_overlays" ||
           name == "load_row" || name == "play" || name == "preview_clip" ||
           name == "reload" || name == "engine_restart" || name == "engine_stop" ||
           name == "edit_hitbox" || name == "assign_clip";
}
}

struct WorkbenchWindow::Impl {
    WorkbenchWindow *q;
    std::shared_ptr<Worker> worker = std::make_shared<Worker>();
    QThreadPool pool;
    QFutureWatcher<Reply> watcher;
    QQueue<Request> queue;
    std::optional<Request> renderPending;
    Request active;
    bool running = false, closing = false, closeWindow = false, disposing = false, disposed = false;
    quint64 revision = 0, renderNumber = 0, rowIntent = 0, frameIntent = 0;
    bool captureTimedOut = false;
    Viewport *viewport;
    Timeline *timeline;
    QComboBox *rows, *speed;
    QCheckBox *loop;
    kit::Button *play, *start, *stop;
    QTimer pngTimer, playTimer;
    QElapsedTimer pngClock;
    QString pngPath, row;
    QDateTime renderStarted;
    QMap<QString, QPair<QDateTime, qint64>> seenPng;
    quint64 pngRevision = 0, pngNumber = 0;
    Snapshot snapshot;
    QJsonObject camera, overlays{{"hitboxes", true}, {"hurtboxes", false}, {"bones", false}, {"ecb", false}, {"floor", true}};

    explicit Impl(WorkbenchWindow *window) : q(window) {
        pool.setMaxThreadCount(1); pool.setExpiryTimeout(-1);
        q->setObjectName("workbenchWindow"); q->setWindowTitle(t("Creator", "Creador")); q->resize(1000, 760);
        auto *body = new QWidget(q); body->setAutoFillBackground(true);
        auto *layout = new QVBoxLayout(body); layout->setContentsMargins(0, 0, 0, 0); layout->setSpacing(atlas::px("s2"));
        auto *engineRow = new QHBoxLayout; layout->addLayout(engineRow);
        engineRow->addWidget(kit::capLabel(t("Engine", "Motor"), atlas::Role::Cap16));
        start = addButton(engineRow, t("Start", "Iniciar"), [this] { q->runCommand("engine_restart", {}); }); start->setObjectName("wbStart");
        stop = addButton(engineRow, t("Stop", "Detener"), [this] { setPlaying(false); q->runCommand("engine_stop", {}); }); stop->setObjectName("wbStop");
        addButton(engineRow, t("Reload", "Recargar"), [this] { q->runCommand("reload", {}); });
        engineRow->addStretch();
        auto *rowLine = new QHBoxLayout; layout->addLayout(rowLine);
        rowLine->addWidget(kit::capLabel(t("Move", "Movimiento"), atlas::Role::Cap16));
        rows = new QComboBox; rows->setObjectName("wbRows"); rows->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Fixed);
        rows->setAccessibleName(t("Move", "Movimiento")); rowLine->addWidget(rows, 1);
        QObject::connect(rows, qOverload<int>(&QComboBox::activated), q, [this](int i) {
            row = rows->itemData(i).toString(); setPlaying(false); updateTimeline();
            q->runCommand("load_row", {{"row", row}});
        });
        auto *views = new QHBoxLayout; layout->addLayout(views);
        for (const auto &preset : QList<QPair<QString, QString>>{
                 {"side", t("Side", "Lateral")}, {"front", t("Front", "Frontal")},
                 {"top", t("Top", "Superior")}, {"three_quarter", t("Three quarter", "Tres cuartos")}})
            addButton(views, preset.second, [this, key = preset.first] { q->runCommand("set_camera", {{"preset", key}}); });
        views->addStretch();
        auto *toggles = new QHBoxLayout; layout->addLayout(toggles);
        for (const auto &overlay : QList<QPair<QString, QString>>{
                 {"hitboxes", t("Hitboxes", "Cajas de golpe")}, {"hurtboxes", t("Hurtboxes", "Cajas de daño")},
                 {"bones", t("Bones", "Huesos")}, {"ecb", t("ECB", "ECB")}, {"floor", t("Floor", "Suelo")}}) {
            auto *toggle = new QCheckBox(overlay.second); toggle->setObjectName("wbOverlay_" + overlay.first);
            toggle->setChecked(overlays.value(overlay.first).toBool()); toggles->addWidget(toggle);
            QObject::connect(toggle, &QCheckBox::toggled, q, [this, key = overlay.first](bool on) {
                overlays.insert(key, on); q->runCommand("set_overlays", overlays);
            });
        }
        toggles->addStretch();
        viewport = new Viewport; layout->addWidget(viewport, 1);
        QObject::connect(viewport, &Viewport::cameraChanged, q, [this](const QJsonObject &value) { q->runCommand("set_camera", value); });
        timeline = new Timeline;
        auto *timelineScroll = new QScrollArea; timelineScroll->setWidgetResizable(true); timelineScroll->setFrameShape(QFrame::NoFrame);
        timelineScroll->setWidget(timeline); timelineScroll->setMinimumHeight(110); timelineScroll->setMaximumHeight(190);
        layout->addWidget(timelineScroll);
        QObject::connect(timeline, &Timeline::frameRequested, q, [this](int f) { setPlaying(false); q->runCommand("set_frame", {{"frame", f}}); });
        QObject::connect(timeline, &Timeline::playToggled, q, [this](bool on) { setPlaying(on); });
        auto *transport = new QHBoxLayout; layout->addLayout(transport);
        play = addButton(transport, t("Play", "Jugar"), [this] { setPlaying(!playTimer.isActive()); });
        play->setObjectName("wbPlay");
        loop = new QCheckBox(t("Loop", "Repetir")); loop->setChecked(true); transport->addWidget(loop);
        speed = new QComboBox; speed->setAccessibleName(t("Playback speed", "Velocidad de reproducción"));
        speed->addItem(t("0.5x", "0.5x"), 0.5); speed->addItem(t("1x", "1x"), 1.0); speed->addItem(t("2x", "2x"), 2.0); speed->setCurrentIndex(1);
        transport->addWidget(speed); transport->addStretch();
        transport->addWidget(kit::capLabel(t("J / K / L: step, play, step", "J / K / L: cuadro, reproducir, cuadro"), atlas::Role::Body12, "muted"));
        // Timeline handles its own keys. These shortcuts cover a focused viewport,
        // without consuming letters typed into Task 16's inspector and palette.
        for (const auto &key : {Qt::Key_J, Qt::Key_K, Qt::Key_L, Qt::Key_Home, Qt::Key_End}) {
            auto *shortcut = new QShortcut(QKeySequence(key), viewport); shortcut->setContext(Qt::WidgetShortcut);
            QObject::connect(shortcut, &QShortcut::activated, q, [this, key] {
                if (key == Qt::Key_K) { setPlaying(!playTimer.isActive()); return; }
                if (!timeline->frameCount()) return;
                setPlaying(false);
                const int next = key == Qt::Key_Home ? 0 : key == Qt::Key_End ? timeline->frameCount() - 1 : timeline->frame() + (key == Qt::Key_J ? -1 : 1);
                timeline->setFrame(next); q->runCommand("set_frame", {{"frame", timeline->frame()}});
            });
        }
        q->setCentralWidget(body); q->statusBar()->showMessage(t("Engine not running", "Motor detenido"));
        pngTimer.setInterval(50);
        QObject::connect(&pngTimer, &QTimer::timeout, q, [this] { pollPng(); });
        playTimer.setInterval(16);
        QObject::connect(&playTimer, &QTimer::timeout, q, [this] {
            if (busy() || !timeline->frameCount()) return;
            if (timeline->frame() >= timeline->frameCount() - 1) {
                if (loop->isChecked()) q->runCommand("set_frame", {{"frame", 0}});
                else setPlaying(false);
            } else {
                const double rate = speed->currentData().toDouble(); playTimer.setInterval(rate < 1 ? 33 : 16);
                q->runCommand("play", {{"frames", std::min(rate > 1 ? 2 : 1, timeline->frameCount() - 1 - timeline->frame())}, {"step", 1}});
            }
        });
        QObject::connect(&watcher, &QFutureWatcher<Reply>::finished, q, [this] { finished(); });
    }
    kit::Button *addButton(QBoxLayout *layout, const QString &text, std::function<void()> fn) {
        auto *button = new kit::Button(text); layout->addWidget(button);
        QObject::connect(button, &QPushButton::clicked, q, std::move(fn)); return button;
    }
    bool busy() const { return running || !queue.isEmpty() || renderPending.has_value() || pngTimer.isActive(); }
    void setPlaying(bool on) {
        on = on && timeline->frameCount() > 0 && !closing;
        if (on) playTimer.start(); else playTimer.stop();
        timeline->setPlaying(on); play->setText(on ? t("Pause", "Pausar") : t("Play", "Jugar"));
    }
    void status(const QString &text) { q->statusBar()->showMessage(text); }
    void notifyBusy() { emit q->busyChanged(busy()); }
    void enqueue(const QString &name, const QJsonObject &args) {
        if (closing) return;
        if (changesView(name)) {
            ++revision; renderPending.reset();
        }
        if (name == "load_row") ++rowIntent;
        if (name == "set_frame" || name == "play" || name == "preview_clip") ++frameIntent;
        Request request{name, args, revision, 0, rowIntent, frameIntent, std::nullopt};
        if (name == "load_row") request.restoreFrame = std::exchange(restoringFrame, std::nullopt);
        if (name == "render_view" && captureTimedOut) {
            status(captureError()); emit q->commandFinished(name, failure(captureError())); return;
        }
        if (name == "render_view") {
            request.render = ++renderNumber; renderPending = request;
        } else {
            // Preserve edit order; only consecutive seeks are disposable.
            if (!queue.isEmpty() && queue.back().name == name && name == "set_frame") queue.back() = request;
            else queue.enqueue(request);
        }
        pump(); notifyBusy();
    }
    QString captureError() const {
        return t("Screenshot timed out. Restart the engine to capture again.", "La captura agotó el tiempo de espera. Reinicia el motor para capturar de nuevo.");
    }
    void requestRender() {
        if (captureTimedOut) { status(captureError()); return; }
        if (closing || renderPending) return; // keep the latest explicit dimensions
        renderPending = Request{"render_view", {{"w", std::max(1, viewport->width())}, {"h", std::max(1, viewport->height())}}, revision, ++renderNumber};
    }
    void pump() {
        if (running || pngTimer.isActive()) return;
        if (closing) { dispose(); return; }
        if (!queue.isEmpty()) active = queue.dequeue();
        else if (renderPending) { active = *renderPending; renderPending.reset(); }
        else { notifyBusy(); return; }
        running = true;
        if (active.name != "render_view") status(t("Working…", "Procesando…"));
        const auto request = active;
        watcher.setFuture(QtConcurrent::run(&pool, [state = worker, request] { return state->call(request.name, request.args); }));
    }
    void dispose() {
        if (disposed || disposing) return;
        disposing = true; running = true;
        watcher.setFuture(QtConcurrent::run(&pool, [state = worker] { state->dispose(); return Reply{}; }));
    }
    void refresh(const Snapshot &value) {
        snapshot = value;
        QSignalBlocker block(rows); rows->clear();
        for (const auto &r : snapshot.rows) rows->addItem(r.name, r.name);
        int selected = rows->findData(row); if (selected < 0 && rows->count()) selected = 0;
        rows->setCurrentIndex(selected); row = rows->currentData().toString(); updateTimeline();
    }
    void updateTimeline() {
        int frames = 0, iasa = 0;
        for (const auto &r : snapshot.rows) if (r.name == row) {
            iasa = r.iasa;
            for (const auto &clip : snapshot.clips) if (clip.name == r.clip) frames = std::max(0, clip.frames - r.cropStart);
            frames = std::max(frames, r.iasa + 1);
        }
        QVector<QPair<QString, QPair<int, int>>> bars;
        for (const auto &hit : snapshot.hits.value(row)) {
            frames = std::max(frames, std::max(hit.startFrame + 1, hit.endFrame));
            bars.append({t("Hitbox %1", "Caja de golpe %1").arg(hit.slot), {hit.startFrame, hit.endFrame}});
        }
        if (iasa > 0) bars.append({t("IASA", "IASA"), {iasa, frames}});
        timeline->setRange(frames); timeline->setBars(bars);
        timeline->setMinimumHeight(timeline->sizeHint().height());
    }
    void finished() {
        const Reply result = watcher.result();
        if (disposing) {
            disposed = true; disposing = false; running = false; notifyBusy(); emit q->shutdownFinished();
            if (closeWindow) q->close();
            return;
        }
        if (closing) { running = false; dispose(); return; }
        const Request completed = active;
        refresh(result.snapshot);
        const auto reply = result.envelope;
        const bool ok = reply.value("ok").toBool();
        const auto value = reply.value("result").toObject();
        if (!ok) {
            setPlaying(false); status(displayError(reply.value("error").toString()));
        } else if (completed.name == "render_view") {
            // Even superseded captures must finish before the next render: the
            // engine writes every screenshot to the same view.png path.
            pngPath = value.value("path").toString(); renderStarted = result.renderStarted;
            pngRevision = completed.revision; pngNumber = completed.render;
            if (pngPath.isEmpty()) status(t("Screenshot path missing", "Falta la ruta de la captura"));
            else { pngClock.start(); pngTimer.start(); status(t("Waiting for screenshot…", "Esperando captura…")); }
        } else {
            status(t("Ready", "Ready"));
            if (completed.name == "load_row" && completed.rowIntent == rowIntent) {
                row = completed.args.value("row").toString(); refresh(result.snapshot);
                if (completed.frameIntent == frameIntent)
                    q->runCommand("set_frame", {{"frame", completed.restoreFrame.value_or(0)}});
            }
            if (completed.name == "set_camera") {
                if (completed.args.contains("preset")) camera = completed.args;
                else for (auto it = completed.args.begin(); it != completed.args.end(); ++it) camera.insert(it.key(), it.value());
                viewport->setCamera(camera);
            }
            if (completed.name == "set_overlays") {
                for (auto it = completed.args.begin(); it != completed.args.end(); ++it) {
                    overlays.insert(it.key(), it.value()); viewport->setOverlay(it.key(), it.value().toBool());
                }
            }
            if (value.contains("frame") && completed.rowIntent == rowIntent && completed.frameIntent == frameIntent) {
                const FrameInfo fi = FrameInfo::fromJson(value); timeline->setFrame(fi.frame); viewport->setFrameInfo(fi);
            }
            if ((completed.name == "edit_hitbox" || completed.name == "assign_clip") && value.value("applied").toBool()) {
                q->runCommand("reload", {});
            } else if (completed.name == "reload" || completed.name == "engine_restart") {
                captureTimedOut = false; seenPng.clear();
                const int f = timeline->frame();
                q->runCommand("set_overlays", overlays);
                if (!camera.isEmpty()) q->runCommand("set_camera", camera);
                if (!row.isEmpty()) {
                    // load_row's normal follow-up seeks zero. Restore the selection
                    // explicitly via a flag on the UI request, never in command args.
                    restoringFrame = f;
                    q->runCommand("load_row", {{"row", row}});
                } else requestRender();
            } else if (completed.name == "engine_stop") {
                viewport->setImage({}); status(t("Engine not running", "Motor detenido"));
            } else if (changesView(completed.name) && completed.name != "edit_hitbox" && completed.name != "assign_clip") {
                requestRender();
            }
        }
        emit q->commandFinished(completed.name, reply);
        running = false;
        pump(); notifyBusy();
    }
    std::optional<int> restoringFrame;
    void pollPng() {
        if (closing) { pngTimer.stop(); pump(); notifyBusy(); return; }
        const QFileInfo file(pngPath);
        const auto stamp = qMakePair(file.lastModified().toUTC(), file.size());
        const bool fresh = file.isFile() && stamp.first >= renderStarted &&
                           (!seenPng.contains(pngPath) || seenPng.value(pngPath) != stamp);
        if (fresh) {
            QImageReader reader(pngPath, "PNG");
            const QSize size = reader.size();
            // Bound memory on corrupt engine output; normal render resolutions fit.
            if (size.isValid() && qint64(size.width()) * size.height() <= 64 * 1024 * 1024) {
                const QImage image = reader.read();
                if (!image.isNull()) {
                    if (pngRevision == revision && pngNumber == renderNumber) {
                        viewport->setImage(image);
                        status(t("Frame %1", "Cuadro %1").arg(timeline->frame()));
                    }
                    seenPng.insert(pngPath, stamp); pngTimer.stop(); pump(); notifyBusy(); return;
                }
            }
        }
        if (pngClock.elapsed() >= 3000) {
            pngTimer.stop(); setPlaying(false); captureTimedOut = true;
            // A timed-out write may still arrive. The shared capture path cannot
            // be attributed again until restart cancels the old game's capture.
            if (renderPending) {
                renderPending.reset(); emit q->commandFinished("render_view", failure(captureError()));
            }
            status(captureError()); pump(); notifyBusy();
        }
    }
};

WorkbenchWindow::WorkbenchWindow(Session &s, QWidget *parent) : QMainWindow(parent), d_(std::make_unique<Impl>(this)) {
    d_->worker->session = &s;
    d_->stop->setEnabled(s.registry().has("engine_stop"));
    runCommand("list_rows", {});
}
WorkbenchWindow::WorkbenchWindow(const QString &projectDir, LaunchFactory launch, QWidget *parent)
    : QMainWindow(parent), d_(std::make_unique<Impl>(this)) {
    d_->worker->projectDir = projectDir; d_->worker->factory = std::move(launch);
    runCommand("open_fighter", {{"path", projectDir}});
}
WorkbenchWindow::~WorkbenchWindow() {
    d_->pngTimer.stop(); d_->playTimer.stop();
    disconnect(&d_->watcher, nullptr, this, nullptr);
    // Launcher shutdown is asynchronous. This final guard also protects borrowed
    // stack sessions when a caller destroys a window without closing it first.
    // Do not waitForDone before disposal: it destroys the pool thread. Do not
    // wait on a QFuture either: QtConcurrent may steal queued work onto the
    // waiting (GUI) thread. A semaphore lets the worker run its own destructors.
    QSemaphore disposed;
    (void)QtConcurrent::run(&d_->pool, [state = d_->worker, &disposed] { state->dispose(); disposed.release(); });
    disposed.acquire();
    d_->pool.waitForDone();
}
void WorkbenchWindow::runCommand(const QString &name, const QJsonObject &args) { d_->enqueue(name, args); }
QString WorkbenchWindow::statusText() const { return statusBar()->currentMessage(); }
bool WorkbenchWindow::isBusy() const { return d_->busy(); }
bool WorkbenchWindow::shutdownComplete() const { return d_->disposed; }
void WorkbenchWindow::shutdown() {
    if (d_->closing) return;
    d_->closing = true; d_->setPlaying(false); d_->pngTimer.stop(); d_->queue.clear(); d_->renderPending.reset();
    d_->status(t("Stopping Creator…", "Deteniendo Creador…")); d_->pump(); d_->notifyBusy();
}
void WorkbenchWindow::closeEvent(QCloseEvent *event) {
    if (d_->disposed) { event->accept(); return; }
    d_->closeWindow = true; shutdown(); event->ignore();
}
}
