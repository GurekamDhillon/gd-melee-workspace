#include "workbench_window.h"
#include "window.h"
#define WB_CORE_USE_LAUNCHER_T 1
#include "commands.h"
#include "blender_launch.h"
#include "geno_data.h"
#include "hub_panel.h"
#include "mcp_server.h"
#include "panels.h"
#include "palette.h"
#include "session.h"
#include "timeline.h"
#include "kit.h"
#include <QCheckBox>
#include <QCloseEvent>
#include <QComboBox>
#include <QDockWidget>
#include <QFileInfo>
#include <QHBoxLayout>
#include <QJsonDocument>
#include <QJsonParseError>
#include <QLabel>
#include <QQueue>
#include <QScopedValueRollback>
#include <QScrollArea>
#include <QSemaphore>
#include <QShortcut>
#include <QSignalBlocker>
#include <QStatusBar>
#include <QThread>
#include <QTimer>
#include <QVBoxLayout>
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
// The session, engine and MCP listener live on one event-loop thread. Start is
// lazy, so an offline fighter can be inspected without a disc or game process.
class ProjectEngine final : public EngineBackend {
public:
    WorkbenchWindow::LaunchFactory factory;
    QString modId;
    bool headless = true;
    std::unique_ptr<EngineLink> link;
    QJsonObject call(const QString &fn, const QJsonObject &args, QString *err) override {
        if (!link) { if (err) *err = "engine not running"; return {}; }
        return link->call(fn, args, err);
    }
    QString status() override { return link ? link->status() : QString("stopped"); }
    bool restart(QString *err) override {
        if (!link) {
            auto launch = factory(); launch.modId = modId; launch.headless = headless;
            link = std::make_unique<EngineLink>(std::move(launch));
        }
        return link->restart(err);
    }
    void setHeadless(bool value) {
        if (headless == value) return;
        stop(); link.reset(); headless = value;
    }
    void stop() { if (link) link->stop(); }
};
struct Snapshot {
    bool valid = false, canStop = false, ownedEngine = false, headless = true;
    QString projectDir, projectName, art, engineStatus, currentRow;
    QVector<RowInfo> rows;
    QVector<ClipInfo> clips;
    QMap<QString, QVector<HitboxRef>> hits;
    QVector<HistoryEntry> history;
    QVector<CommandSpec> commands;
    QJsonArray fidelity;
    QString fidelityError;
};
struct Reply { QJsonObject envelope; Snapshot snapshot; };
struct Worker {
    Session *session = nullptr;
    QString projectDir;
    WorkbenchWindow::LaunchFactory factory;
    QObject *context = nullptr;
    std::unique_ptr<ProjectEngine> engine;
    std::unique_ptr<Session> owned;
    std::unique_ptr<McpServer> server;
    std::function<void(const QString &, const QJsonObject &, const Reply &)> onRemote;
    QQueue<std::function<void()>> pending;
    bool calling = false, stopped = false;
    void submit(std::function<void()> task) { pending.enqueue(std::move(task)); drain(); }
    void drain() {
        // ConsoleClient pumps events while waiting. A queued UI request must not
        // enter the Session in the middle of a socket command (or its shutdown).
        while (!calling && !pending.isEmpty()) { auto task = pending.dequeue(); task(); }
    }
    void ensureSession() {
        if (session) return;
        engine = std::make_unique<ProjectEngine>(); engine->factory = factory;
        owned = std::make_unique<Session>(projectDir, engine.get());
        const QString err = owned->data().reload();
        if (!err.isEmpty()) { owned.reset(); engine.reset(); throw CommandError{err}; }
        engine->modId = owned->data().project().modId;
        registerAllCommands(*owned);
        owned->registry().add({"engine_stop", t("Stop engine", "Detener motor"),
            {{"type", "object"}, {"properties", QJsonObject{}}}, false,
            [this](const QJsonObject &, CommandContext &) {
                engine->stop(); return QJsonObject{{"status", "stopped"}};
            }});
        session = owned.get();
    }
    Snapshot snapshot() {
        Snapshot value;
        const auto &project = session->data().project();
        value.projectDir = session->files().root(); value.projectName = project.id;
        if (value.projectName.isEmpty()) value.projectName = QFileInfo(value.projectDir).fileName();
        value.art = project.artBlend.isEmpty() ? project.artGlb : project.artBlend;
        value.currentRow = session->currentRow;
        value.engineStatus = session->engine() ? session->engine()->status() : QString("stopped");
        value.canStop = session->registry().has("engine_stop"); value.ownedEngine = bool(engine);
        if (engine) value.headless = engine->headless;
        value.rows = session->data().rows(); value.clips = session->data().clips();
        for (const auto &row : value.rows) value.hits.insert(row.name, session->data().hitboxes(row.name));
        for (const auto &entry : session->history().entries()) {
            auto metadata = entry; metadata.changes.clear(); value.history.append(metadata);
        }
        value.commands = session->registry().list();
        // The GUI gets schemas only. Handlers retain worker-owned state.
        for (auto &spec : value.commands) spec.run = {};
        try {
            const auto path = project.fidelity;
            if (!path.isEmpty()) {
                // A display refresh must not acknowledge a hand edit in FileStore.
                FileStore reader(session->files().root()); QJsonParseError parse;
                const auto doc = QJsonDocument::fromJson(reader.read(path), &parse);
                if (parse.error != QJsonParseError::NoError || !doc.isObject() || !doc.object()["rows"].isArray())
                    value.fidelityError = t("Invalid fidelity ledger", "Registro de fidelidad inválido");
                else value.fidelity = doc.object()["rows"].toArray();
            }
        } catch (const CommandError &e) { value.fidelityError = e.message; }
          catch (const std::exception &e) { value.fidelityError = QString::fromUtf8(e.what()); }
        value.valid = true; return value;
    }
    Reply call(const QString &name, const QJsonObject &args, CommandContext *remote = nullptr,
               std::optional<bool> headless = std::nullopt) {
        Reply result;
        if (stopped || calling) {
            result.envelope = failure(stopped ? t("Creator is closing", "El Creador se está cerrando") :
                t("A command is already in progress", "Ya hay un comando en curso"));
            return result;
        }
        QScopedValueRollback<bool> guard(calling, true);
        try {
            ensureSession();
            if (headless && engine) engine->setHeadless(*headless);
            CommandContext local{*session, "human", args.value("propose").toBool()};
            // Preserve the GUI's restart-on-reload behavior. Blender uses the
            // registry directly, including its explicit rebuild/reload stale flow.
            const QString command = !remote && name == "reload" ? QString("engine_restart") : name;
            result.envelope = session->registry().call(command, args, remote ? *remote : local);
            if (!remote && result.envelope.value("ok").toBool() && (name == "reload" || name == "engine_restart")) {
                const auto err = session->data().reload();
                if (!err.isEmpty()) result.envelope = failure(err);
            }
            result.snapshot = snapshot();
        } catch (const CommandError &e) { result.envelope = failure(e.message); }
          catch (const std::exception &e) { result.envelope = failure(QString::fromUtf8(e.what())); }
          catch (...) { result.envelope = failure("unexpected command failure"); }
        // Run deferred UI work after McpServer::handle has unwound its own guard.
        QTimer::singleShot(0, context, [this] { drain(); });
        return result;
    }
    quint16 serve(QString *err) {
        if (stopped) return 0;
        if (server) return server->localPort();
        try {
            ensureSession(); server = std::make_unique<McpServer>(*session); server->setAuthor("human");
            server->setCommandRunner([this](const QString &name, const QJsonObject &args, CommandContext &ctx) {
                const auto reply = call(name, args, &ctx);
                if (onRemote) onRemote(name, args, reply);
                return reply.envelope;
            });
            if (!server->listenLocal(0, err)) { server.reset(); return 0; }
            return server->localPort();
        } catch (const CommandError &e) { if (err) *err = e.message; }
          catch (const std::exception &e) { if (err) *err = QString::fromUtf8(e.what()); }
        return 0;
    }
    void dispose() {
        QScopedValueRollback<bool> guard(calling, true);
        stopped = true; server.reset(); onRemote = {};
        // QObject destruction and the history flush run on their owning thread.
        if (owned) { session = nullptr; owned.reset(); }
        engine.reset();
    }
};
struct Request {
    QString name; QJsonObject args;
    quint64 rowIntent = 0, frameIntent = 0;
    std::optional<int> restoreFrame;
    std::optional<bool> headless;
};
}

struct WorkbenchWindow::Impl {
    WorkbenchWindow *q;
    std::shared_ptr<Worker> worker = std::make_shared<Worker>();
    QThread thread;
    QObject *workerContext;
    QQueue<Request> queue;
    Request active;
    bool running = false, closing = false, closeWindow = false, disposing = false, disposed = false;
    bool pendingBlenderOpen = false;
    quint16 listenerPort = 0;
    quint64 rowIntent = 0, frameIntent = 0;
    HubPanel *hub;
    Timeline *timeline;
    FrameInfo frameInfo; // only the timeline's frame readout; Blender owns the view
    QComboBox *rows, *speed;
    QCheckBox *loop;
    kit::Button *play;
    QTimer playTimer;
    QString row, blenderSetting;
    Snapshot snapshot;
    OutlinerPanel *outliner;
    InspectorPanel *inspector;
    ProblemsPanel *problems;
    ClipBrowserPanel *clips;
    FidelityPanel *fidelity;
    ReviewPanel *review;
    QLabel *fidelityNote;
    CommandRegistry paletteCommands;
    int selectedOrdinal = -1;
    bool clipPreview = false;
    std::optional<int> restoringFrame;

    explicit Impl(WorkbenchWindow *window) : q(window) {
        workerContext = new QObject;
        workerContext->moveToThread(&thread); worker->context = workerContext;
        QObject::connect(&thread, &QThread::finished, workerContext, &QObject::deleteLater);
        worker->onRemote = [this](const QString &name, const QJsonObject &args, const Reply &reply) {
            QMetaObject::invokeMethod(q, [this, name, args, reply] { remoteFinished(name, args, reply); }, Qt::QueuedConnection);
        };
        thread.start();
        q->setObjectName("workbenchWindow"); q->setWindowTitle(t("Creator", "Creador")); q->resize(1000, 760);
        hub = new HubPanel(q); auto *layout = hub->bodyLayout();
        QObject::connect(hub, &HubPanel::startRequested, q, [this] { q->runCommand("engine_restart", {}); });
        QObject::connect(hub, &HubPanel::restartRequested, q, [this] { setPlaying(false); q->runCommand("engine_restart", {}); });
        QObject::connect(hub, &HubPanel::stopRequested, q, [this] { setPlaying(false); q->runCommand("engine_stop", {}); });
        QObject::connect(hub, &HubPanel::headlessChanged, q, [this](bool on) {
            setPlaying(false); enqueue("engine_restart", {}, on);
        });
        QObject::connect(hub, &HubPanel::openInBlenderRequested, q, [this] {
            setPlaying(false);
            if (!blenderError().isEmpty()) { status(blenderError()); return; }
            pendingBlenderOpen = true;
            // A process can die while the hub is idle. Ask the worker for the
            // current state before deciding whether Blender needs an engine start.
            q->runCommand("engine_status", {});
        });
        auto *rowLine = new QHBoxLayout; layout->addLayout(rowLine);
        rowLine->addWidget(kit::capLabel(t("Move", "Movimiento"), atlas::Role::Cap16));
        rows = new QComboBox; rows->setObjectName("wbRows"); rows->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Fixed);
        rows->setAccessibleName(t("Move", "Movimiento")); rowLine->addWidget(rows, 1);
        QObject::connect(rows, qOverload<int>(&QComboBox::activated), q, [this](int i) {
            selectRow(rows->itemData(i).toString());
        });
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
        // Timeline handles its own keys. These shortcuts cover a focused hub,
        // without consuming letters typed into Task 16's inspector and palette.
        for (const auto &key : {Qt::Key_J, Qt::Key_K, Qt::Key_L, Qt::Key_Home, Qt::Key_End}) {
            auto *shortcut = new QShortcut(QKeySequence(key), hub); shortcut->setContext(Qt::WidgetShortcut);
            QObject::connect(shortcut, &QShortcut::activated, q, [this, key] {
                if (key == Qt::Key_K) { setPlaying(!playTimer.isActive()); return; }
                if (!timeline->frameCount()) return;
                setPlaying(false);
                const int next = key == Qt::Key_Home ? 0 : key == Qt::Key_End ? timeline->frameCount() - 1 : timeline->frame() + (key == Qt::Key_J ? -1 : 1);
                timeline->setFrame(next); q->runCommand("set_frame", {{"frame", timeline->frame()}});
            });
        }
        q->setCentralWidget(hub); q->statusBar()->showMessage(t("Engine not running", "Motor detenido"));
        createPanels();
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
    }
    kit::Button *addButton(QBoxLayout *layout, const QString &text, std::function<void()> fn) {
        auto *button = new kit::Button(text); layout->addWidget(button);
        QObject::connect(button, &QPushButton::clicked, q, std::move(fn)); return button;
    }
    QDockWidget *dock(const QString &title, const QString &name, QWidget *content, Qt::DockWidgetArea area) {
        auto *widget = new QDockWidget(title, q); widget->setObjectName(name); widget->setWidget(content);
        q->addDockWidget(area, widget); return widget;
    }
    void createPanels() {
        outliner = new OutlinerPanel; inspector = new InspectorPanel;
        problems = new ProblemsPanel; clips = new ClipBrowserPanel;
        fidelity = new FidelityPanel; review = new ReviewPanel;
        auto *outlineDock = dock(t("Outliner", "Explorador"), "wbOutlinerDock", outliner, Qt::LeftDockWidgetArea);
        auto *inspectorScroll = new QScrollArea; inspectorScroll->setWidgetResizable(true);
        inspectorScroll->setFrameShape(QFrame::NoFrame); inspectorScroll->setWidget(inspector);
        auto *inspectorDock = dock(t("Inspector", "Inspector"), "wbInspectorDock", inspectorScroll, Qt::RightDockWidgetArea);
        auto *clipBody = new QWidget; auto *clipLayout = new QVBoxLayout(clipBody);
        auto *clipActions = new QHBoxLayout; clipLayout->addLayout(clipActions);
        addButton(clipActions, t("Preview", "Vista previa"), [this] { clips->previewCurrent(); });
        addButton(clipActions, t("Assign to move", "Asignar al movimiento"), [this] { clips->assignCurrent(); });
        clipLayout->addWidget(clips);
        auto *clipsDock = dock(t("Clips", "Clips"), "wbClipsDock", clipBody, Qt::RightDockWidgetArea);
        auto *fidelityBody = new QWidget; auto *fidelityLayout = new QVBoxLayout(fidelityBody);
        fidelityNote = new QLabel; fidelityNote->setTextFormat(Qt::PlainText); fidelityNote->setWordWrap(true);
        fidelityLayout->addWidget(fidelityNote); fidelityLayout->addWidget(fidelity);
        auto *fidelityDock = dock(t("Fidelity", "Fidelidad"), "wbFidelityDock", fidelityBody, Qt::RightDockWidgetArea);
        q->tabifyDockWidget(inspectorDock, clipsDock); q->tabifyDockWidget(clipsDock, fidelityDock); inspectorDock->raise();
        auto *problemBody = new QWidget; auto *problemLayout = new QVBoxLayout(problemBody);
        auto *problemActions = new QHBoxLayout; problemLayout->addLayout(problemActions);
        auto *check = addButton(problemActions, t("Run checks", "Ejecutar comprobaciones"), [this] {
            setPlaying(false); q->runCommand("run_checks", {});
        });
        check->setObjectName("wbRunChecks"); problemActions->addStretch(); problemLayout->addWidget(problems);
        auto *problemsDock = dock(t("Problems", "Problemas"), "wbProblemsDock", problemBody, Qt::BottomDockWidgetArea);
        auto *reviewBody = new QWidget; auto *reviewLayout = new QVBoxLayout(reviewBody);
        auto *reviewActions = new QHBoxLayout; reviewLayout->addLayout(reviewActions);
        addButton(reviewActions, t("Undo", "Deshacer"), [this] { emit review->undoRequested(); });
        addButton(reviewActions, t("Redo", "Rehacer"), [this] { emit review->redoRequested(); });
        reviewActions->addStretch(); reviewLayout->addWidget(review);
        auto *reviewDock = dock(t("History and review", "Historial y revisión"), "wbReviewDock", reviewBody, Qt::BottomDockWidgetArea);
        q->tabifyDockWidget(problemsDock, reviewDock); problemsDock->raise();
        q->resizeDocks({outlineDock, inspectorDock}, {210, 300}, Qt::Horizontal);
        q->resizeDocks({problemsDock}, {180}, Qt::Vertical);
        QObject::connect(outliner, &OutlinerPanel::rowSelected, q, [this](const QString &name) { selectRow(name); });
        QObject::connect(outliner, &OutlinerPanel::hitboxSelected, q, [this](const QString &name, int ordinal) { selectRow(name, ordinal); });
        QObject::connect(inspector, &InspectorPanel::editRequested, q, [this](const QString &name, const QJsonObject &args) {
            q->runCommand(name, args);
        });
        QObject::connect(problems, &ProblemsPanel::problemActivated, q, [this, inspectorDock](const QString &name, int ordinal) {
            selectRow(name, ordinal); inspectorDock->raise();
        });
        QObject::connect(clips, &ClipBrowserPanel::previewRequested, q, [this](const QString &clip) {
            setPlaying(false); q->runCommand("preview_clip", {{"clip", clip}});
        });
        QObject::connect(clips, &ClipBrowserPanel::assignRequested, q, [this](const QString &clip) {
            if (row.isEmpty()) { status(t("Select a move first", "Selecciona un movimiento primero")); return; }
            q->runCommand("assign_clip", {{"row", row}, {"clip", clip}});
        });
        QObject::connect(review, &ReviewPanel::acceptRequested, q, [this](int id) { q->runCommand("accept", {{"id", id}}); });
        QObject::connect(review, &ReviewPanel::rejectRequested, q, [this](int id) { q->runCommand("reject", {{"id", id}}); });
        QObject::connect(review, &ReviewPanel::undoRequested, q, [this] { q->runCommand("undo", {}); });
        QObject::connect(review, &ReviewPanel::redoRequested, q, [this] { q->runCommand("redo", {}); });
#if __has_include("palette.h")
        auto *paletteShortcut = new QShortcut(QKeySequence(Qt::CTRL | Qt::Key_P), q);
        QObject::connect(paletteShortcut, &QShortcut::activated, q, [this] {
            if (closing) return;
            if (paletteCommands.list().isEmpty()) { status(t("Commands are loading…", "Cargando comandos…")); return; }
            auto *palette = new CommandPalette(paletteCommands, q); palette->setAttribute(Qt::WA_DeleteOnClose);
            QObject::connect(palette, &CommandPalette::commandChosen, q, [this](const QString &name) {
                for (const auto &spec : paletteCommands.list()) if (spec.name == name) {
                    if (!spec.inputSchema.value("required").toArray().isEmpty()) {
                        status(t("%1 needs arguments. Use the panels.", "%1 necesita argumentos. Usa los paneles.").arg(name)); return;
                    }
                    QJsonObject args; const auto properties = spec.inputSchema.value("properties").toObject();
                    for (auto it = properties.begin(); it != properties.end(); ++it) {
                        const auto property = it.value().toObject();
                        if (property.contains("default")) args.insert(it.key(), property.value("default"));
                    }
                    q->runCommand(name, args); return;
                }
            });
            palette->open();
        });
#endif
    }
    const HitboxRef *selectedHitbox() const {
        const auto it = snapshot.hits.constFind(row);
        if (it == snapshot.hits.cend()) return nullptr;
        for (const auto &hit : it.value()) if (hit.ordinal == selectedOrdinal) return &hit;
        return nullptr;
    }
    void refreshSelection() {
        outliner->setSelection(row, selectedOrdinal);
        const auto *hit = selectedHitbox();
        if (hit) inspector->showHitbox(row, *hit); else { selectedOrdinal = -1; inspector->clear(); }
        QString currentClip; QVector<int> motions;
        for (const auto &entry : snapshot.rows) if (entry.name == row) { currentClip = entry.effectiveClip(); motions = entry.motions; break; }
        clips->setClips(snapshot.clips, currentClip); fidelity->setFidelity(snapshot.fidelity, row, motions);
        fidelityNote->setText(snapshot.fidelityError.isEmpty() ? QString() :
            t("Cannot read fidelity: %1", "No se puede leer la fidelidad: %1").arg(snapshot.fidelityError));
        fidelityNote->setVisible(!snapshot.fidelityError.isEmpty());
    }
    void selectRow(const QString &name, int ordinal = -1) {
        bool found = false; for (const auto &entry : snapshot.rows) if (entry.name == name) { found = true; break; }
        if (!found || closing) return;
        setPlaying(false); row = name; selectedOrdinal = ordinal; clipPreview = false;
        const QSignalBlocker block(rows); rows->setCurrentIndex(rows->findData(row));
        frameInfo = {}; timeline->setFrame(0); updateTimeline(); refreshSelection();
        const auto *hit = selectedHitbox(); restoringFrame = hit ? hit->startFrame : 0;
        q->runCommand("load_row", {{"row", row}});
    }
    bool busy() const { return running || !queue.isEmpty(); }
    void setPlaying(bool on) {
        on = on && timeline->frameCount() > 0 && !closing;
        if (on) playTimer.start(); else playTimer.stop();
        timeline->setPlaying(on); play->setText(on ? t("Pause", "Pausar") : t("Play", "Jugar"));
    }
    void status(const QString &text) { q->statusBar()->showMessage(text); }
    QString blenderError() const {
        const auto blender = findBlender(blenderSetting, QProcessEnvironment::systemEnvironment());
        if (blender.isEmpty()) return t("Blender not found: set GW_BLENDER or the Blender path in Settings",
            "No se encontro Blender: define GW_BLENDER o la ruta de Blender en Ajustes");
        const auto addon = findAddonDir(snapshot.projectDir);
        if (addon.isEmpty()) return t("Workbench Blender add-on not found in this project's checkout",
            "No se encontro el complemento de Blender en el repositorio de este proyecto");
        if (snapshot.art.isEmpty()) return t("Set art_blend or art_glb in workbench.json to open the fighter",
            "Define art_blend o art_glb en workbench.json para abrir el luchador");
        return blenderCommand(blender, addon, snapshot.projectDir, 1, snapshot.art).error;
    }
    void notifyBusy() {
        hub->setControls(busy() || closing, snapshot.canStop, snapshot.ownedEngine, blenderError());
        emit q->busyChanged(busy());
    }
    void openBlender() {
        const auto error = blenderError();
        if (!error.isEmpty()) { status(error); return; }
        const quint16 port = q->serveForBlender(); if (!port) return;
        const auto command = blenderCommand(findBlender(blenderSetting, QProcessEnvironment::systemEnvironment()),
            findAddonDir(snapshot.projectDir), snapshot.projectDir, port, snapshot.art);
        if (!command.error.isEmpty()) { status(command.error); return; }
        if (!QProcess::startDetached(command.program, command.args)) {
            status(t("Could not start Blender. Check the Blender path in Settings.",
                "No se pudo iniciar Blender. Revisa la ruta de Blender en Ajustes.")); return;
        }
        status(t("Blender opened; workbench port %1", "Blender abierto; puerto del banco de trabajo %1").arg(port));
    }
    void enqueue(const QString &name, const QJsonObject &args, std::optional<bool> headless = std::nullopt) {
        if (closing) return;
        if (name == "edit_hitbox" || name == "add_hitbox" || name == "delete_hitbox" || name == "assign_clip" || name == "accept" || name == "undo" || name == "redo")
            setPlaying(false);
        if (name == "load_row") {
            ++rowIntent; clipPreview = false;
            const QString requested = args.value("row").toString();
            for (const auto &entry : snapshot.rows) if (entry.name == requested) {
                if (row != requested) selectedOrdinal = -1;
                row = requested; break;
            }
            frameInfo = {}; refreshSelection();
        }
        if (name == "preview_clip") clipPreview = true;
        if (name == "set_frame" || name == "play" || name == "preview_clip") ++frameIntent;
        Request request{name, args, rowIntent, frameIntent, std::nullopt, headless};
        if (name == "load_row") request.restoreFrame = std::exchange(restoringFrame, std::nullopt);
        // Preserve edits and explicit debug commands; only consecutive seeks are disposable.
        if (!queue.isEmpty() && queue.back().name == name && name == "set_frame") queue.back() = request;
        else queue.enqueue(request);
        pump(); notifyBusy();
    }
    void pump() {
        if (running) return;
        if (closing) { dispose(); return; }
        if (queue.isEmpty()) {
            if (pendingBlenderOpen) { pendingBlenderOpen = false; openBlender(); }
            notifyBusy(); return;
        }
        active = queue.dequeue(); running = true;
        status(t("Working…", "Procesando…"));
        if (active.name == "engine_restart" || active.name == "reload") hub->setEngineStatus("starting");
        const auto request = active;
        QMetaObject::invokeMethod(workerContext, [this, state = worker, request] {
            state->submit([this, state, request] {
                const auto result = state->call(request.name, request.args, nullptr, request.headless);
                QMetaObject::invokeMethod(q, [this, result] { finished(result); }, Qt::QueuedConnection);
            });
        }, Qt::QueuedConnection);
    }
    void dispose() {
        if (disposed || disposing) return;
        disposing = true; running = true;
        QMetaObject::invokeMethod(workerContext, [this, state = worker] {
            state->submit([this, state] {
                state->dispose();
                QMetaObject::invokeMethod(q, [this] { finished(Reply{}); }, Qt::QueuedConnection);
            });
        }, Qt::QueuedConnection);
    }
    void refresh(const Snapshot &value) {
        if (!value.valid) return;
        snapshot = value;
        int hitboxes = 0; for (const auto &hits : snapshot.hits) hitboxes += int(hits.size());
        hub->setProject(snapshot.projectName, int(snapshot.rows.size()), hitboxes);
        hub->setEngineStatus(snapshot.engineStatus); hub->setHeadless(snapshot.headless);
        QSignalBlocker block(rows); rows->clear();
        for (const auto &r : snapshot.rows) rows->addItem(r.name, r.name);
        int selected = rows->findData(row); if (selected < 0 && rows->count()) selected = 0;
        rows->setCurrentIndex(selected); row = rows->currentData().toString(); updateTimeline();
        outliner->setRows(snapshot.rows, snapshot.hits); refreshSelection();
        review->setHistory(snapshot.history);
        paletteCommands = CommandRegistry{};
        for (const auto &spec : snapshot.commands) paletteCommands.add(spec);
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
    void finished(const Reply &result) {
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
            pendingBlenderOpen = false; setPlaying(false); status(displayError(reply.value("error").toString()));
        } else {
            const QString warning = value.value("warning").toString();
            status(warning.isEmpty() ? t("Ready", "Ready") : t("Warning: %1", "Aviso: %1").arg(warning));
            if (completed.name == "engine_status" && pendingBlenderOpen) {
                const auto state = value.value("status").toString();
                if (state != "ready" && state != "running") q->runCommand("engine_restart", {});
            }
            if (completed.name == "load_row" && completed.rowIntent == rowIntent) {
                row = completed.args.value("row").toString(); refresh(result.snapshot);
                if (completed.frameIntent == frameIntent)
                    q->runCommand("set_frame", {{"frame", completed.restoreFrame.value_or(0)}});
            }
            if (completed.name == "run_checks") {
                QVector<Problem> found;
                for (const auto &item : value.value("problems").toArray()) {
                    const auto p = item.toObject();
                    found.append({p["kind"].toString(), p["row"].toString(), p["message"].toString(), p["ordinal"].toInt(-1)});
                }
                problems->setProblems(found);
                // Engine checks sweep motions. Restore the visible move before playback.
                if (value.value("engine").toBool() && !row.isEmpty()) {
                    restoringFrame = timeline->frame(); q->runCommand("load_row", {{"row", row}});
                }
            }
            if (value.contains("frame") && completed.rowIntent == rowIntent && completed.frameIntent == frameIntent) {
                frameInfo = FrameInfo::fromJson(value); timeline->setFrame(frameInfo.frame);
            }
            if ((completed.name == "edit_hitbox" || completed.name == "add_hitbox" || completed.name == "delete_hitbox" || completed.name == "assign_clip" || completed.name == "accept" ||
                 completed.name == "undo" || completed.name == "redo") && value.value("applied").toBool()) {
                problems->setProblems({}); q->runCommand("reload", {});
            } else if (completed.name == "reload" || completed.name == "engine_restart") {
                const int f = timeline->frame();
                if (!row.isEmpty()) {
                    // load_row's normal follow-up seeks zero. Restore the selection
                    // explicitly via a flag on the UI request, never in command args.
                    restoringFrame = f;
                    q->runCommand("load_row", {{"row", row}});
                }
            } else if (completed.name == "engine_stop") {
                frameInfo = {}; status(t("Engine not running", "Motor detenido"));
            }
        }
        emit q->commandFinished(completed.name, reply);
        running = false;
        pump(); notifyBusy();
    }
    void remoteFinished(const QString &name, const QJsonObject &args, const Reply &reply) {
        if (closing) return;
        if (reply.snapshot.valid && !reply.snapshot.currentRow.isEmpty()) row = reply.snapshot.currentRow;
        refresh(reply.snapshot);
        const auto value = reply.envelope.value("result").toObject();
        if (reply.envelope.value("ok").toBool()) {
            if (value.contains("frame")) { frameInfo = FrameInfo::fromJson(value); timeline->setFrame(frameInfo.frame); }
            if (value.value("applied").toBool()) problems->setProblems({});
            if (name == "run_checks") {
                QVector<Problem> found;
                for (const auto &item : value.value("problems").toArray()) {
                    const auto p = item.toObject();
                    found.append({p["kind"].toString(), p["row"].toString(), p["message"].toString(), p["ordinal"].toInt(-1)});
                }
                problems->setProblems(found);
            }
        } else status(displayError(reply.envelope.value("error").toString()));
        // Socket edits stay stale until Blender asks for rebuild/reload. Never
        // synthesize GUI follow-up commands or restart the engine here.
        Q_UNUSED(args);
        emit q->commandFinished(name, reply.envelope); notifyBusy();
    }
};

WorkbenchWindow::WorkbenchWindow(Session &s, QWidget *parent) : QMainWindow(parent), d_(std::make_unique<Impl>(this)) {
    d_->worker->session = &s;
    runCommand("list_rows", {});
}
WorkbenchWindow::WorkbenchWindow(const QString &projectDir, LaunchFactory launch, QWidget *parent)
    : QMainWindow(parent), d_(std::make_unique<Impl>(this)) {
    d_->worker->projectDir = projectDir; d_->worker->factory = std::move(launch);
    runCommand("open_fighter", {{"path", projectDir}});
}
WorkbenchWindow::~WorkbenchWindow() {
    d_->closing = true; d_->playTimer.stop();
    // The async close path normally disposed already. Also protect borrowed
    // stack sessions when a caller destroys a window directly. A semaphore lets
    // a currently pumping socket call finish before its Session is destroyed.
    QSemaphore disposed;
    QMetaObject::invokeMethod(d_->workerContext, [state = d_->worker, &disposed] {
        state->submit([state, &disposed] { state->dispose(); disposed.release(); });
    }, Qt::QueuedConnection);
    disposed.acquire(); d_->thread.quit(); d_->thread.wait();
}
void WorkbenchWindow::runCommand(const QString &name, const QJsonObject &args) { d_->enqueue(name, args); }
void WorkbenchWindow::setBlenderSetting(const QString &path) { d_->blenderSetting = path; d_->notifyBusy(); }
quint16 WorkbenchWindow::serveForBlender() {
    if (d_->closing) return 0;
    if (d_->listenerPort) return d_->listenerPort;
    if (d_->busy()) { d_->status(t("Wait for the current command before opening Blender", "Espera a que termine el comando antes de abrir Blender")); return 0; }
    QString error; quint16 port = 0;
    // No engine calls or other UI work are in flight; this only binds loopback.
    QMetaObject::invokeMethod(d_->workerContext, [&] { port = d_->worker->serve(&error); }, Qt::BlockingQueuedConnection);
    d_->listenerPort = port;
    if (!port) d_->status(t("Cannot start the Blender listener: %1", "No se puede iniciar la conexion de Blender: %1").arg(error));
    return port;
}
QString WorkbenchWindow::statusText() const { return statusBar()->currentMessage(); }
bool WorkbenchWindow::isBusy() const { return d_->busy(); }
bool WorkbenchWindow::shutdownComplete() const { return d_->disposed; }
void WorkbenchWindow::shutdown() {
    if (d_->closing) return;
    d_->closing = true; d_->setPlaying(false); d_->queue.clear(); d_->pendingBlenderOpen = false;
    d_->status(t("Stopping Creator…", "Deteniendo Creador…")); d_->pump(); d_->notifyBusy();
}
void WorkbenchWindow::closeEvent(QCloseEvent *event) {
    if (d_->disposed) { event->accept(); return; }
    d_->closeWindow = true; shutdown(); event->ignore();
}
}
