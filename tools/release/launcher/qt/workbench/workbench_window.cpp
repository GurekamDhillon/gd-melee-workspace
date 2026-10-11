#include "workbench_window.h"
#include "combo_widgets.h"
#include "projectile_widgets.h"
#include "window.h"
#define WB_CORE_USE_LAUNCHER_T 1
#include "commands.h"
#include "error_help.h"
#include "recovery.h"
#include "blender_launch.h"
#include "game_exe.h"
#include "play_launch.h"
#include "geno_data.h"
#include "hub_panel.h"
#include "mcp_server.h"
#include "panels.h"
#include "palette.h"
#include "session.h"
#include "timeline.h"
#include "atlas_widgets.h"
#include "kit.h"
#include <QCheckBox>
#include <QCloseEvent>
#include <QLocale>
#include <QDateTime>
#include <QDialog>
#include <QKeyEvent>
#include <QApplication>
#include <QAbstractItemView>
#include <QAbstractSpinBox>
#include <QAbstractSlider>
#include <QPlainTextEdit>
#include <QTextEdit>
#include <QTabBar>
#include <QToolButton>
#include <QResizeEvent>
#include <QComboBox>
#include <QElapsedTimer>
#include <QFormLayout>
#include <QFrame>
#include <QGridLayout>
#include <QLineEdit>
#include <QSet>
#include <QSplitter>
#include <QTemporaryFile>
#include <QTabWidget>
#include <QFile>
#include <QFileInfo>
#include <QHBoxLayout>
#include <QJsonDocument>
#include <QJsonParseError>
#include <QLabel>
#include <QMessageBox>
#include <QPointer>
#include <QProcess>
#include <QQueue>
#include <QScopedValueRollback>
#include <QScrollArea>
#include <QSettings>
#include <QCoreApplication>
#include <QSemaphore>
#include <QShortcut>
#include <QSignalBlocker>
#include <QStatusBar>
#include <QThread>
#include <QTimer>
#include <QVBoxLayout>
#include <algorithm>
#include <exception>
#include <limits>
#include <optional>
#include <utility>
#ifdef Q_OS_WIN
#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#endif

namespace wb {
using launcher::t;
namespace atlas = launcher::atlas;
namespace kit = launcher::kit;
namespace {
QJsonObject failure(const QString &error) { return {{"ok", false}, {"error", error}}; }
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
    QMap<QString, QJsonArray> events;
    QJsonArray articles, spawns; // projectiles (geno.md 19) and the spawn calls of the move scripts
    QJsonArray routes, strings; // the combo graph (geno.md 25)
    QJsonObject comboMeta;
    bool hasCombo = false;
    QVector<HistoryEntry> history;
    QVector<CommandSpec> commands;
    QJsonArray fidelity;
    QString fidelityError;
    QVector<RoleInfo> roles;
    bool canRebuild = false;
    QJsonArray changes; // fields that differ from the last build (baseline.cpp)
    qint64 blenderPid = 0, blenderAck = 0, viewRevision = 0;
    QJsonObject recovery; // what the previous run left behind, until the user decides
};
struct Reply { QJsonObject envelope; Snapshot snapshot; QJsonArray attributes; bool hasAttributes = false; };
struct Worker {
    Session *session = nullptr;
    QString projectDir;
    WorkbenchWindow::LaunchFactory factory;
    QObject *context = nullptr;
    std::unique_ptr<ProjectEngine> engine;
    std::unique_ptr<Session> owned;
    std::unique_ptr<McpServer> server;
    std::function<void(const QString &, const QJsonObject &, const Reply &)> onRemote;
    std::function<void(const QString &)> onRebuildStarted;
    QQueue<std::function<void()>> pending;
    bool calling = false, stopped = false, recoveryChecked = false, markedOpen = false;
    QString markedRoot;
    void submit(std::function<void()> task) { pending.enqueue(std::move(task)); drain(); }
    void drain() {
        // ConsoleClient pumps events while waiting. A queued UI request must not
        // enter the Session in the middle of a socket command (or its shutdown).
        while (!calling && !pending.isEmpty()) { auto task = pending.dequeue(); task(); }
    }
    void installUiStateCommand() {
        if (session->registry().has("ui_view_state")) return;
        session->registry().add({"ui_view_state", t("Read the Qt move and frame", "Leer el movimiento y cuadro de Qt"),
            commandSchema({{"revision", argType("integer")}, {"pid", argType("integer")}}), false,
            [](const QJsonObject &args, CommandContext &ctx) {
                auto &s = ctx.session;
                const auto pid = args.value("pid").toInteger();
                const auto revision = args.value("revision").toInteger();
                if (pid > 0 && pid == s.blenderPid)
                    s.blenderAckRevision = s.uiView.value("available").toBool() && revision == s.uiView.value("revision").toInteger() ? revision : 0;
                return s.uiView.isEmpty() ? QJsonObject{{"revision", 0}, {"available", false}} : s.uiView;
            }});
    }
    void ensureSession() {
        if (session) { installUiStateCommand(); return; }
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
        session = owned.get(); installUiStateCommand();
    }
    // First command on a project: note whether the last run closed badly, then mark this run as open.
    void checkRecovery() {
        if (recoveryChecked || !session) return;
        recoveryChecked = true;
        try {
            const QString root = session->files().root();
            const auto prior = readSessionMark(root);
            markSessionOpen(root, QCoreApplication::applicationPid());
            markedOpen = true; markedRoot = root;
            const auto info = detectRecovery(*session, prior);
            if (info.any()) session->recovery = info.toJson();
        } catch (...) { /* recovery is a courtesy: never block opening a project */ }
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
        value.roles = session->data().availableRoles();
        value.canRebuild = !project.rebuild.isEmpty();
        value.recovery = session->recovery;
        value.blenderPid = session->blenderPid; value.blenderAck = session->blenderAckRevision;
        value.viewRevision = session->uiView.value("revision").toInteger();
        value.articles = session->data().articles(); value.spawns = session->data().spawns();
        value.routes = session->data().routes(); value.strings = session->data().strings();
        value.comboMeta = session->data().comboMeta(); value.hasCombo = session->data().hasCombo();
        for (const auto &row : value.rows) {
            value.hits.insert(row.name, session->data().hitboxes(row.name));
            value.events.insert(row.name, session->data().timelineEvents(row.name));
        }
        for (const auto &entry : session->history().entries()) {
            auto metadata = entry; metadata.changes.clear(); value.history.append(metadata);
        }
        try { value.changes = baselineChanges(*session); } catch (...) {}
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
        // Blender's follower polls ui_view_state ~10x a second. It only reads the view Qt already published, so it
        // is answered even while a slow engine command is in flight (Play issues one back to back); refusing it as
        // "a command is already in progress" starved Blender of every frame while Qt played.
        if (name == "ui_view_state" && calling && !stopped && session) {
            CommandContext poll{*session, "human", false};
            result.envelope = session->registry().call(name, args, poll);
            return result;
        }
        if (stopped || calling) {
            result.envelope = failure(stopped ? t("Creator is closing", "El Creador se está cerrando") :
                t("A command is already in progress", "Ya hay un comando en curso"));
            return result;
        }
        QScopedValueRollback<bool> guard(calling, true);
        try {
            ensureSession();
            checkRecovery();
            if (headless && engine) engine->setHeadless(*headless);
            CommandContext local{*session, "human", args.value("propose").toBool()};
            // Preserve the GUI's restart-on-reload behavior. Blender uses the
            // registry directly, including its explicit rebuild/reload stale flow.
            const QString command = !remote && name == "reload" ? QString("engine_restart") : name;
            if (name == "rebuild" && onRebuildStarted) onRebuildStarted(t("Rebuilding gameplay", "Reconstruyendo jugabilidad"));
            result.envelope = session->registry().call(command, args, remote ? *remote : local);
            if (!remote && result.envelope.value("ok").toBool() && (name == "reload" || name == "engine_restart")) {
                const auto err = session->data().reload();
                if (!err.isEmpty()) result.envelope = failure(err);
            }
            const auto commandValue = result.envelope.value("result").toObject();
            if (result.envelope.value("ok").toBool() && session->uiView.value("available").toBool() &&
                (name == "load_row" || name == "preview_clip" || name == "open_fighter" || name == "reload" ||
                 name == "engine_restart" || name == "engine_stop" || name == "rebuild" ||
                 (remote && (commandValue.contains("frame") || session->currentRow != session->uiView.value("row").toString())))) {
                // Bootstrap/calibration and Blender-local gestures may replace
                // the view before a Qt request is consumed. Retire that request
                // without resetting the monotonic revision sequence.
                session->uiView = {{"revision", session->uiView.value("revision").toInteger() + 1}, {"available", false}};
                session->blenderAckRevision = 0;
            }
            if (!remote && result.envelope.value("ok").toBool()) {
                const auto value = commandValue;
                if ((name == "set_frame" || name == "play") && value.contains("frame") && !session->currentRow.isEmpty()) {
                    QJsonArray hits;
                    for (const auto &h : session->data().hitboxes(session->currentRow))
                        hits.append(hitboxJson(h));   // the same record list_hitboxes returns, so Blender's badges see element/shield/ground/air
                    session->uiView = {{"revision", session->uiView.value("revision").toInteger() + 1},
                        {"available", true}, {"row", session->currentRow}, {"info", value}, {"hitboxes", hits}};
                    session->blenderAckRevision = 0;
                }
            }
            // Reconcile optimistic field edits and history without a follow-up UI
            // command, which would hide an edit failure behind a new Ready status.
            if (session->registry().has("list_attributes") && (name == "edit_attribute" || name == "undo" ||
                name == "redo" || name == "accept" || name == "reload" || name == "engine_restart")) {
                CommandContext readContext{*session, "human", false};
                const auto attributes = session->registry().call("list_attributes", {}, readContext);
                if (attributes.value("ok").toBool()) {
                    result.attributes = attributes.value("result").toObject().value("attributes").toArray();
                    result.hasAttributes = true;
                }
            }
            // A Blender heartbeat is a cheap state read, never an engine query
            // or an excuse to rebuild every panel and interrupt a field draft.
            if (name != "ui_view_state") result.snapshot = snapshot();
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
        stopped = true; server.reset(); onRemote = {}; onRebuildStarted = {};
        if (markedOpen) { markSessionClosed(markedRoot, QCoreApplication::applicationPid()); markedOpen = false; }
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
    bool duringBuild = false; // an edit made while a rebuild ran: it applies after the build, for the next one
};
// An application-wide key filter for the plain keys (Left, Right, Space, Delete), which a QShortcut would
// take from buttons, lists and text fields. The owner decides per key press whether the focus is "typing".
class PlainKeyFilter : public QObject {
public:
    std::function<bool(QKeyEvent *)> handle;
    using QObject::QObject;
    bool eventFilter(QObject *, QEvent *event) override {
        return event->type() == QEvent::KeyPress && handle && handle(static_cast<QKeyEvent *>(event));
    }
};
bool isEditName(const QString &name) {
    return name == "edit_hitbox" || name == "edit_attribute" || name == "add_hitbox" || name == "delete_hitbox" ||
           name == "duplicate_hitbox" || name == "assign_clip";
}
bool isStructuralName(const QString &name) {
    return name == "add_hitbox" || name == "delete_hitbox" || name == "duplicate_hitbox";
}
// True when the focused widget takes typed text: shortcuts that would eat a character must stand down.
bool typingIn(const QWidget *w) {
    if (!w) return false;
    if (qobject_cast<const QLineEdit *>(w) || qobject_cast<const QAbstractSpinBox *>(w) ||
        qobject_cast<const QTextEdit *>(w) || qobject_cast<const QPlainTextEdit *>(w)) return true;
    if (const auto *combo = qobject_cast<const QComboBox *>(w)) return combo->isEditable();
    return false;
}
struct ShortcutDef {
    QString id, keys, label;
    QList<QKeySequence> sequences; // empty for the plain keys the filter handles
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
    bool pendingBlenderOpen = false, playLaunching = false;
    PlayCommand pendingPlay;
    QPointer<QProcess> playProcess;
    QPointer<QMessageBox> playDialog;
    quint16 listenerPort = 0;
    quint64 rowIntent = 0, frameIntent = 0;
    HubPanel *hub;
    TimelineView *timeline;
    InspectorTabs *tabs;
    StatusProgress *progress = nullptr;
    AttributesPanel *attributes;
    ProjectilesPanel *projectiles = nullptr;
    SpawnLane *spawnLane = nullptr;
    RouteLanes *routeLanes = nullptr;
    ComboPanel *combo = nullptr;
    QLineEdit *search;
    QLabel *moveTitle, *moveGroupLabel, *moveStats, *frameReadout;
    QVBoxLayout *centreLayout;
    QGridLayout *headerGrid = nullptr;
    QScrollArea *timelineScroll = nullptr;
    QWidget *centreHost = nullptr, *timelinePlate = nullptr;
    enum class Mode { Unset, Wide, Narrow } layoutMode = Mode::Unset;
    bool cardBelow = false, portraitLayout = false, railInTabs = false;
    QWidget *hitboxTab = nullptr, *attributesTab = nullptr;
    QPushButton *moveChip = nullptr;
    QCheckBox *autoHitbox = nullptr;
    QWidget *movesRail;
    QSplitter *columns;
    FrameInfo frameInfo; // only the timeline's frame readout; Blender owns the view
    QComboBox *rows, *speed;
    QCheckBox *loop;
    AtlasButton *play;
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
    QVector<Problem> rowProblems;
    bool checksCurrent = false, rebuildReload = false, rebuildReloading = false;
    QSet<QString> editedRows;
    int pendingChanges = 0;
    qint64 blenderPid = 0, viewRevision = 0;
    QElapsedTimer blenderHeartbeat;
    QTimer blenderMonitor;
    std::unique_ptr<QTemporaryFile> blenderDriver;
    std::optional<int> restoringFrame;
    // R1: the one action that can fix the last error
    AtlasButton *fixButton = nullptr;
    FixKind currentFix = FixKind::None;
    // R2: a crashed run's leftovers, offered once
    QFrame *recoveryBanner = nullptr;
    QLabel *recoveryText = nullptr;
    AtlasButton *recoveryRestore = nullptr, *recoveryKeep = nullptr, *recoveryDiscard = nullptr, *recoveryRevert = nullptr;
    // R3: edits made during a rebuild
    int queuedDuringBuild = 0, newSinceBuild = 0;
    QSet<QString> queuedRows;
    QString stickyNote; // shown as the status after the follow-up reloads, until the next edit
    // R4: keyboard
    QVector<ShortcutDef> shortcuts;
    QDialog *shortcutSheet = nullptr;

    explicit Impl(WorkbenchWindow *window) : q(window) {
        workerContext = new QObject;
        workerContext->moveToThread(&thread); worker->context = workerContext;
        QObject::connect(&thread, &QThread::finished, workerContext, &QObject::deleteLater);
        worker->onRemote = [this](const QString &name, const QJsonObject &args, const Reply &reply) {
            QMetaObject::invokeMethod(q, [this, name, args, reply] { remoteFinished(name, args, reply); }, Qt::QueuedConnection);
        };
        worker->onRebuildStarted = [this](const QString &phase) {
            QMetaObject::invokeMethod(q, [this, phase] { q->reportRebuildProgress(phase, -1, 0, false); }, Qt::QueuedConnection);
        };
        thread.start();
        atlas::initialize();
        q->setObjectName("workbenchWindow"); q->setWindowTitle(t("Geno Workbench", "Geno Workbench")); q->resize(1440, 900);
        applyAtlasStyle(q); // no explicit minimum: the layout hints drive the Creator tab scroll area
        hub = new HubPanel(q); auto *layout = hub->bodyLayout();
        QObject::connect(hub, &HubPanel::undoRequested, q, [this] { q->runCommand("undo", {}); });
        QObject::connect(hub, &HubPanel::rebuildRequested, q, [this] { rebuildAndReload(); });
        QObject::connect(hub, &HubPanel::showBlenderRequested, q, [this] { showBlender(); });
        QObject::connect(hub, &HubPanel::revertAllRequested, q, [this] { q->runCommand("revert_all", {}); });
        QObject::connect(hub, &HubPanel::startRequested, q, [this] { q->runCommand("engine_restart", {}); });
        QObject::connect(hub, &HubPanel::restartRequested, q, [this] { setPlaying(false); q->runCommand("engine_restart", {}); });
        QObject::connect(hub, &HubPanel::stopRequested, q, [this] { setPlaying(false); q->runCommand("engine_stop", {}); });
        QObject::connect(hub, &HubPanel::headlessChanged, q, [this](bool on) {
            setPlaying(false); enqueue("engine_restart", {}, on);
        });
        QObject::connect(hub, &HubPanel::openInBlenderRequested, q, [this] { startBlender(); });
        QObject::connect(hub, &HubPanel::playInLabRequested, q, [this] { playFighter(false); });
        QObject::connect(hub, &HubPanel::playVsCpuRequested, q, [this] { playFighter(true); });
        rows = new QComboBox(hub); rows->setObjectName("wbRows"); rows->hide();
        // Keep the existing move selector API for integrations; the visible
        // grouped rail is the navigation surface.
        QObject::connect(rows, qOverload<int>(&QComboBox::activated), q, [this](int i) { selectRow(rows->itemData(i).toString()); });
        columns = new QSplitter(Qt::Horizontal); columns->setObjectName("wbColumns");
        columns->setChildrenCollapsible(false); columns->setHandleWidth(2); layout->addWidget(columns, 1);
        movesRail = new QWidget; movesRail->setObjectName("wbMovesRail"); movesRail->setMinimumWidth(190);
        auto *movesLayout = new QVBoxLayout(movesRail); movesLayout->setContentsMargins(12, 16, 12, 12); movesLayout->setSpacing(8);
        movesLayout->addWidget(kit::capLabel(t("Moves", "Movimientos"), atlas::Role::Cap14, "muted"));
        search = new QLineEdit; search->setObjectName("wbMoveSearch"); search->setClearButtonEnabled(true);
        search->setAccessibleName(t("Search moves", "Buscar movimientos")); movesLayout->addWidget(search);
        autoHitbox = new QCheckBox(t("Open Hitbox after picking a move", "Abrir Hitbox al elegir un movimiento")); autoHitbox->setObjectName("wbAutoHitbox");
        autoHitbox->hide(); movesLayout->addWidget(autoHitbox);
        columns->addWidget(movesRail);
        auto *centre = new QWidget; centre->setObjectName("wbCentreHost"); centre->setMinimumWidth(440); centreHost = centre;
        centreLayout = new QVBoxLayout(centre); centreLayout->setContentsMargins(24, 20, 24, 20); centreLayout->setSpacing(20);
        auto *header = new QGridLayout; header->setHorizontalSpacing(20); header->setVerticalSpacing(4); headerGrid = header;
        moveGroupLabel = kit::capLabel({}, atlas::Role::Cap14, "muted"); moveGroupLabel->setTextFormat(Qt::PlainText);
        moveTitle = kit::capLabel({}, atlas::Role::Hero); moveTitle->setObjectName("wbMoveTitle"); moveTitle->setTextFormat(Qt::PlainText);
        moveStats = new QLabel; moveStats->setObjectName("wbMoveStats"); moveStats->setTextFormat(Qt::PlainText); moveStats->setWordWrap(true);
        moveStats->setFont(atlas::numberFont(14));
        auto *groupLine = new QHBoxLayout; groupLine->setContentsMargins(0, 0, 0, 0); groupLine->setSpacing(10);
        groupLine->addWidget(moveGroupLabel);
        moveChip = new QPushButton; moveChip->setObjectName("wbMoveChip"); moveChip->setFlat(true); moveChip->hide();
        moveChip->setToolTip(t("Current move; click to open the Moves list", "Movimiento actual; pulsa para abrir la lista de movimientos"));
        moveChip->setStyleSheet(QString("QPushButton { color: %1; background: %2; border: 0; border-left: 3px solid %1; padding: 2px 10px; }").arg(atlas::colour("ember").name(), atlas::colour("plate2").name()));
        groupLine->addWidget(moveChip); groupLine->addStretch(1);
        header->addLayout(groupLine, 0, 0); header->addWidget(moveTitle, 1, 0);
        header->addWidget(moveStats, 2, 0, 1, 2); header->addWidget(hub->blenderCard(), 0, 1, 2, 1);
        header->setColumnStretch(0, 1); centreLayout->addLayout(header);
        auto *plate = new AtlasPlate; plate->setObjectName("wbTimelinePlate");
        auto *timelineLayout = new QVBoxLayout(plate); timelineLayout->setContentsMargins(20, 16, 20, 20); timelineLayout->setSpacing(12);
        auto *transport = new QHBoxLayout; timelineLayout->addLayout(transport);
        transport->addWidget(kit::capLabel(t("Timeline", "Línea de tiempo"), atlas::Role::Cap14, "muted")); transport->addStretch();
        auto *previous = addButton(transport, t("‹", "‹"), [this] { stepFrame(-1); });
        previous->setAccessibleName(t("Previous frame", "Cuadro anterior")); previous->setToolTip(previous->accessibleName()); previous->setFixedWidth(40);
        play = addButton(transport, t("Play", "Jugar"), [this] { setPlaying(!playTimer.isActive()); }); play->setObjectName("wbPlay");
        auto *next = addButton(transport, t("›", "›"), [this] { stepFrame(1); });
        next->setAccessibleName(t("Next frame", "Cuadro siguiente")); next->setToolTip(next->accessibleName()); next->setFixedWidth(40);
        frameReadout = new QLabel; frameReadout->setObjectName("wbFrameReadout"); frameReadout->setFont(atlas::numberFont(12));
        frameReadout->setToolTip(t("Frame 0 is the entry pose; frame 1 is the move's first frame. A hitbox listed as active 3–4 is visible on frames 3 and 4, in Blender too.",
                                   "El cuadro 0 es la pose de entrada; el cuadro 1 es el primer cuadro del movimiento. Un hitbox activo 3–4 se ve en los cuadros 3 y 4, también en Blender.")); transport->addWidget(frameReadout);
        auto *options = transport; // Loop and speed share the transport row, which saves a row of height
        loop = new QCheckBox(t("Loop", "Repetir")); loop->setChecked(true); options->insertWidget(1, loop);
        speed = new QComboBox; speed->setAccessibleName(t("Playback speed", "Velocidad de reproducción"));
        speed->addItem(t("0.5x", "0.5x"), 0.5); speed->addItem(t("1x", "1x"), 1.0); speed->addItem(t("2x", "2x"), 2.0); speed->setCurrentIndex(1); options->insertWidget(2, speed);
        timeline = new TimelineView;
        timelineScroll = new QScrollArea; timelineScroll->setObjectName("wbTimelineScroll"); timelineScroll->setWidgetResizable(true); timelineScroll->setFrameShape(QFrame::NoFrame);
        timelineScroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
        timelineScroll->setWidget(timeline); timelineLayout->addWidget(timelineScroll);
        spawnLane = new SpawnLane; spawnLane->setTimeline(timeline); timelineLayout->addWidget(spawnLane);
        QObject::connect(spawnLane, &SpawnLane::editRequested, q, [this](const QString &name, const QJsonObject &args) { q->runCommand(name, args); });
        routeLanes = new RouteLanes; routeLanes->setTimeline(timeline); timelineLayout->addWidget(routeLanes);
        QObject::connect(routeLanes, &RouteLanes::editRequested, q, [this](const QString &name, const QJsonObject &args) { q->runCommand(name, args); });
        QObject::connect(timeline, &Timeline::frameRequested, q, [this](int f) { setPlaying(false); q->runCommand("set_frame", {{"frame", f}}); updateFrameReadout(); });
        QObject::connect(timeline, &Timeline::playToggled, q, [this](bool on) { setPlaying(on); });
        QObject::connect(timeline, &TimelineView::editRequested, q, [this](const QString &name, const QJsonObject &args) { q->runCommand(name, args); });
        QObject::connect(timeline, &TimelineView::hitboxSelected, q, [this](int ordinal) {
            selectedOrdinal = ordinal; refreshSelection(); showHitboxTab();
        });
        auto *addLine = new QHBoxLayout; timelineLayout->addLayout(addLine);
        auto *add = addButton(addLine, t("+ Add hitbox", "+ Añadir hitbox"), [this] {
            if (!row.isEmpty()) q->runCommand("add_hitbox", {{"row", row}, {"frame", timeline->frame()}});
        }); add->setObjectName("wbAddHitbox");
        auto *hint = kit::capLabel(t("Drag the ends to change active frames. Click the ruler to seek Blender.",
            "Arrastra los extremos para cambiar los cuadros activos. Pulsa la regla para mover Blender."), atlas::Role::Body12, "muted");
        hint->setWordWrap(true); addLine->addWidget(hint, 1); addLine->setSpacing(16);
        timelinePlate = plate; plate->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Preferred);
        centreLayout->addWidget(plate); centreLayout->addStretch(1); columns->addWidget(centre);
        q->setCentralWidget(hub);
        progress = new StatusProgress(q); progress->setObjectName("wbStatusProgress");
        q->statusBar()->setSizeGripEnabled(false); q->statusBar()->addPermanentWidget(progress, 1);
        fixButton = new AtlasButton(QString(), q); fixButton->setObjectName("wbStatusFix"); fixButton->setTone(AtlasButton::Ember); fixButton->hide();
        q->statusBar()->addPermanentWidget(fixButton);
        QObject::connect(fixButton, &QPushButton::clicked, q, [this] { performFix(currentFix); });
        buildRecoveryBanner(); buildShortcuts();
        QObject::connect(progress, &StatusProgress::cancelRequested, q, &WorkbenchWindow::rebuildCancelRequested);
        status(t("Engine not running", "Motor detenido")); createPanels();
        movesLayout->addWidget(outliner, 1); movesLayout->addWidget(hub->projectCounts());
        QObject::connect(search, &QLineEdit::textChanged, outliner, &OutlinerPanel::setFilter);
        columns->setStretchFactor(0, 0); columns->setStretchFactor(1, 1); columns->setStretchFactor(2, 0);
        columns->setSizes({256, 828, 352}); applyLayout();
        QWidget::setTabOrder(search, outliner); QWidget::setTabOrder(outliner, previous);
        QWidget::setTabOrder(previous, play); QWidget::setTabOrder(play, next);
        QWidget::setTabOrder(next, timeline); QWidget::setTabOrder(timeline, add); QWidget::setTabOrder(add, tabs);
        blenderMonitor.setInterval(1000);
        QObject::connect(&blenderMonitor, &QTimer::timeout, q, [this] {
            #ifdef Q_OS_WIN
            if (blenderPid > 0) {
                const HANDLE process = OpenProcess(SYNCHRONIZE, FALSE, DWORD(blenderPid));
                if (process) {
                    const bool exited = WaitForSingleObject(process, 0) == WAIT_OBJECT_0;
                    CloseHandle(process);
                    if (exited) { q->setBlenderProcessId(0); blenderClosedNotice(); return; }
                } else if (GetLastError() == ERROR_INVALID_PARAMETER) {
                    q->setBlenderProcessId(0); blenderClosedNotice(); return;
                }
            }
#endif
            if (blenderHeartbeat.isValid() && blenderHeartbeat.elapsed() > 2000) hub->setBlenderState(blenderPid > 0, false);
        }); blenderMonitor.start();
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
    void blenderClosedNotice() {
        statusHelp({t("Blender was closed. Start it again to keep the 3D view in step.", "Blender se cerró. Inícialo de nuevo para mantener la vista 3D al día."),
                    FixKind::StartBlender, t("Start Blender", "Iniciar Blender")});
    }
    // R3: a rebuild is queued, running, or reloading the game after it
    bool rebuildActive() const {
        return rebuildReload || rebuildReloading || (running && active.name == "rebuild") ||
               std::any_of(queue.cbegin(), queue.cend(), [](const Request &r) { return r.name == "rebuild"; });
    }
    bool structuralPending() const {
        return (running && isStructuralName(active.name)) ||
               std::any_of(queue.cbegin(), queue.cend(), [](const Request &r) { return isStructuralName(r.name); });
    }
    // Edits are allowed while a rebuild runs (they queue behind it); anything else busy still blocks them.
    bool canEdit() const { return !closing && !structuralPending() && (!busy() || rebuildActive()); }
    void updateRebuildLabel() { hub->setRebuildAgain(rebuildActive() ? 0 : newSinceBuild); hub->setQueued(queuedDuringBuild); }
    // R2: the notice for what the previous run left behind
    void buildRecoveryBanner() {
        recoveryBanner = new QFrame; recoveryBanner->setObjectName("wbRecoveryBanner"); recoveryBanner->hide();
        recoveryBanner->setStyleSheet(QString("QFrame#wbRecoveryBanner { background: %1; border-left: 3px solid %2; }")
            .arg(atlas::colour("plate2").name(), atlas::colour("ember").name()));
        auto *row = new QHBoxLayout(recoveryBanner); row->setContentsMargins(14, 10, 14, 10); row->setSpacing(10);
        recoveryText = new QLabel; recoveryText->setObjectName("wbRecoveryText"); recoveryText->setWordWrap(true);
        recoveryText->setTextFormat(Qt::PlainText); recoveryText->setFont(atlas::font(atlas::Role::Body14));
        row->addWidget(recoveryText, 1);
        const auto button = [&](const QString &text, const char *name, auto fn) {
            auto *b = new AtlasButton(text); b->setObjectName(name); row->addWidget(b);
            QObject::connect(b, &QPushButton::clicked, q, fn); return b;
        };
        recoveryRestore = button(t("Restore", "Restaurar"), "wbRecoveryRestore", [this] { resolveRecovery("restore"); });
        recoveryRestore->setTone(AtlasButton::Ember);
        recoveryDiscard = button(t("Discard", "Descartar"), "wbRecoveryDiscard", [this] { resolveRecovery("discard"); });
        recoveryKeep = button(t("Keep", "Conservar"), "wbRecoveryKeep", [this] { resolveRecovery("keep"); });
        recoveryRevert = button(t("Revert to last build", "Volver al valor compilado"), "wbRecoveryRevert", [this] {
            resolveRecovery("keep"); q->runCommand("revert_all", {});
        });
        hub->bodyLayout()->insertWidget(1, recoveryBanner); // under the top bar, above the three columns
    }
    void resolveRecovery(const QString &action) {
        recoveryBanner->hide();
        q->runCommand("recovery_resolve", {{"action", action}});
    }
    void updateRecovery() {
        if (!recoveryBanner) return;
        const auto note = snapshot.recovery;
        recoveryBanner->setVisible(!note.isEmpty());
        if (note.isEmpty()) return;
        const bool restorable = note.value("restorable").toBool();
        const int count = note.value("count").toInt();
        const qint64 when = note.value("time").toInteger();
        const QString time = when > 0 ? QLocale().toString(QDateTime::fromSecsSinceEpoch(when), QLocale::ShortFormat) : t("earlier", "antes");
        if (restorable)
            recoveryText->setText(count == 1 ? t("Restore 1 unsaved change from %1?", "¿Restaurar 1 cambio sin guardar de %1?").arg(time)
                                             : t("Restore %1 unsaved changes from %2?", "¿Restaurar %1 cambios sin guardar de %2?").arg(count).arg(time));
        else
            recoveryText->setText(count == 1 ? t("The last session ended unexpectedly. Its 1 change from %1 was saved as you made it.",
                                                 "La última sesión terminó de forma inesperada. Su cambio de %1 se guardó al hacerlo.").arg(time)
                                             : t("The last session ended unexpectedly. Its %1 changes (latest %2) were saved as you made them.",
                                                 "La última sesión terminó de forma inesperada. Sus %1 cambios (el último %2) se guardaron al hacerlos.").arg(count).arg(time));
        recoveryText->setToolTip(note.value("journal_summary").toString());
        recoveryRestore->setVisible(restorable); recoveryDiscard->setVisible(note.value("journal_pending").toBool());
        recoveryKeep->setText(restorable ? t("Keep as is", "Dejar como está") : t("Keep", "Conservar"));
        recoveryRevert->setVisible(note.value("unsaved_changes").toInt() > 0);
    }
    // R4: the keys. Ctrl and function keys are QShortcuts scoped to this widget; the plain keys go through
    // PlainKeyFilter so a text field, a list or a button keeps them.
    void buildShortcuts() {
        shortcuts = {
            {"undo", "Ctrl+Z", t("Undo the last edit", "Deshacer la última edición"), {QKeySequence(Qt::CTRL | Qt::Key_Z)}},
            {"redo", "Ctrl+Y, Ctrl+Shift+Z", t("Redo", "Rehacer"), {QKeySequence(Qt::CTRL | Qt::Key_Y), QKeySequence(Qt::CTRL | Qt::SHIFT | Qt::Key_Z)}},
            {"rebuild", "F5", t("Rebuild + reload the game", "Reconstruir y recargar el juego"), {QKeySequence(Qt::Key_F5)}},
            {"prev_frame", "Left", t("Previous frame", "Cuadro anterior"), {}},
            {"next_frame", "Right", t("Next frame", "Cuadro siguiente"), {}},
            {"play_pause", "Space", t("Play or pause", "Reproducir o pausar"), {}},
            {"duplicate", "Ctrl+D", t("Duplicate the selected hitbox", "Duplicar el hitbox seleccionado"), {QKeySequence(Qt::CTRL | Qt::Key_D)}},
            {"delete", "Delete", t("Delete the selected hitbox (Ctrl+Z brings it back)", "Borrar el hitbox seleccionado (Ctrl+Z lo recupera)"), {}},
            {"find", "Ctrl+F", t("Search moves", "Buscar movimientos"), {QKeySequence(Qt::CTRL | Qt::Key_F)}},
            {"palette", "Ctrl+P", t("Command palette", "Paleta de comandos"), {}},
            {"help", "F1", t("Show this list", "Mostrar esta lista"), {QKeySequence(Qt::Key_F1)}},
        };
        for (const auto &def : shortcuts) for (const auto &sequence : def.sequences) {
            auto *shortcut = new QShortcut(sequence, q); shortcut->setContext(Qt::WidgetWithChildrenShortcut);
            shortcut->setObjectName("wbShortcut_" + def.id);
            QObject::connect(shortcut, &QShortcut::activated, q, [this, id = def.id] { runShortcut(id); });
        }
        auto *filter = new PlainKeyFilter(q); filter->setObjectName("wbPlainKeys");
        filter->handle = [this](QKeyEvent *event) { return plainKey(event); };
        qApp->installEventFilter(filter);
    }
    bool focusIsMine() const {
        QWidget *focus = QApplication::focusWidget();
        return focus && (focus == q || q->isAncestorOf(focus));
    }
    bool plainKey(QKeyEvent *event) {
        if (closing || !focusIsMine()) return false;
        if (event->modifiers() & (Qt::ControlModifier | Qt::AltModifier | Qt::MetaModifier)) return false;
        QWidget *focus = QApplication::focusWidget();
        if (typingIn(focus)) return false;
        const bool inList = qobject_cast<QAbstractItemView *>(focus) != nullptr;
        const bool selector = inList || qobject_cast<QComboBox *>(focus) || qobject_cast<QTabBar *>(focus) || qobject_cast<QAbstractSlider *>(focus);
        const bool timelineFocus = qobject_cast<Timeline *>(focus) != nullptr; // it steps and plays by itself
        switch (event->key()) {
        case Qt::Key_Left: case Qt::Key_Right:
            if (selector || timelineFocus) return false;
            runShortcut(event->key() == Qt::Key_Left ? "prev_frame" : "next_frame"); return true;
        case Qt::Key_Space:
            if (selector || timelineFocus || qobject_cast<QAbstractButton *>(focus)) return false;
            if (!event->isAutoRepeat()) runShortcut("play_pause");
            return true;
        case Qt::Key_Delete:
            if (inList && focus != outliner && !outliner->isAncestorOf(focus)) return false;
            runShortcut("delete"); return true;
        default: return false;
        }
    }
    void runShortcut(const QString &id) {
        if (closing) return;
        QWidget *focus = QApplication::focusWidget();
        const bool typing = typingIn(focus);
        if (id == "undo") { if (!typing) q->runCommand("undo", {}); }
        else if (id == "redo") { if (!typing) q->runCommand("redo", {}); }
        else if (id == "rebuild") rebuildAndReload();
        else if (id == "prev_frame") stepFrame(-1);
        else if (id == "next_frame") stepFrame(1);
        else if (id == "play_pause") setPlaying(!playTimer.isActive());
        else if (id == "duplicate" || id == "delete") {
            if (typing) return;
            const auto *hit = selectedHitbox();
            if (!hit) { status(t("Select a hitbox first", "Selecciona primero un hitbox")); return; }
            if (!canEdit()) return;
            q->runCommand(id == "delete" ? "delete_hitbox" : "duplicate_hitbox", {{"row", row}, {"ordinal", hit->ordinal}});
        }
        else if (id == "find") {
            if (railInTabs) tabs->setCurrentWidget(movesRail);
            search->setFocus(Qt::ShortcutFocusReason); search->selectAll();
        }
        else if (id == "help") toggleShortcutSheet();
    }
    void toggleShortcutSheet() {
        if (shortcutSheet && shortcutSheet->isVisible()) { shortcutSheet->close(); return; }
        if (!shortcutSheet) {
            shortcutSheet = new QDialog(q); shortcutSheet->setObjectName("wbShortcutSheet");
            shortcutSheet->setWindowTitle(t("Keyboard shortcuts", "Atajos de teclado")); shortcutSheet->setModal(false);
            applyAtlasStyle(shortcutSheet);
            auto *outer = new QVBoxLayout(shortcutSheet); outer->setContentsMargins(0, 0, 0, 0);
            auto *plate = new AtlasPlate; auto *body = new QVBoxLayout(plate); body->setContentsMargins(24, 20, 24, 20); body->setSpacing(10);
            outer->addWidget(plate);
            body->addWidget(kit::capLabel(t("Keyboard shortcuts", "Atajos de teclado"), atlas::Role::Cap16, "ivory"));
            auto *grid = new QGridLayout; grid->setHorizontalSpacing(24); grid->setVerticalSpacing(8); body->addLayout(grid);
            int rowIndex = 0;
            for (const auto &def : shortcuts) {
                auto *keys = new QLabel(def.keys); keys->setObjectName("wbShortcutKeys_" + def.id); keys->setTextFormat(Qt::PlainText);
                keys->setFont(atlas::numberFont(13));
                QPalette pal = keys->palette(); pal.setColor(QPalette::WindowText, atlas::colour("ember")); keys->setPalette(pal);
                auto *what = new QLabel(def.label); what->setObjectName("wbShortcutLabel_" + def.id); what->setTextFormat(Qt::PlainText);
                what->setFont(atlas::font(atlas::Role::Body14)); what->setWordWrap(true);
                grid->addWidget(keys, rowIndex, 0, Qt::AlignTop); grid->addWidget(what, rowIndex, 1); ++rowIndex;
            }
            grid->setColumnStretch(1, 1);
            body->addWidget(kit::capLabel(t("Plain keys stay with a text field, list or button when it has focus.",
                "Las teclas simples se quedan con un campo de texto, lista o botón cuando tienen el foco."), atlas::Role::Body12, "muted"));
            auto *close = new AtlasButton(t("Close", "Cerrar")); close->setObjectName("wbShortcutClose");
            QObject::connect(close, &QPushButton::clicked, shortcutSheet, &QDialog::close);
            body->addWidget(close, 0, Qt::AlignRight);
            shortcutSheet->resize(520, shortcutSheet->sizeHint().height());
        }
        shortcutSheet->show(); shortcutSheet->raise();
    }
    // R1: three columns when wide; moves | centre with the inspector under the timeline when narrow
    // or tall. The same widgets move, so state (tabs, edits, focus order) is kept.
    void applyLayout() {
        if (!tabs || !centreHost) return;
        const int w = q->width(), h = q->height();
        const bool portrait = h > w, narrow = w < 1400 || portrait;
        // Clearly tall (a second monitor turned upright): the Moves rail joins the lower strip. A bench that is merely a
        // little taller than wide keeps the two-column narrow layout.
        const bool tall = h * 4 > w * 5;
        const Mode mode = narrow ? Mode::Narrow : Mode::Wide;
        if (mode != layoutMode || tall != portraitLayout) {
            layoutMode = mode; portraitLayout = tall;
            columns->setUpdatesEnabled(false);
            QWidget *current = tabs->currentWidget();
            // Tall window: the Moves rail joins the lower strip as its first tab and the Move view spans the width.
            if (!tall && railInTabs) {
                tabs->removeTab(tabs->indexOf(movesRail)); columns->insertWidget(0, movesRail); movesRail->setMinimumWidth(190); movesRail->show();
                railInTabs = false; autoHitbox->hide(); moveChip->hide();
            }
            if (narrow) {
                tabs->setMinimumWidth(0); tabs->setMinimumHeight(portrait ? 420 : 300);
                if (centreLayout->indexOf(tabs) < 0) { centreLayout->insertWidget(2, tabs, 1); centreLayout->setStretch(3, 0); }
                if (tall && !railInTabs) {
                    movesRail->setMinimumWidth(0); tabs->insertTab(0, movesRail, t("Moves", "Movimientos"));
                    railInTabs = true; autoHitbox->show(); moveChip->show();
                    if (current) tabs->setCurrentWidget(current);
                }
                columns->setSizes(tall ? QList<int>{w} : QList<int>{260, std::max(440, w - 260)});
            } else if (centreLayout->indexOf(tabs) >= 0) {
                centreLayout->removeWidget(tabs); tabs->setMinimumHeight(0); tabs->setMinimumWidth(310);
                columns->addWidget(tabs); centreLayout->setStretch(2, 1);
                columns->setSizes({256, std::max(440, w - 256 - 352), 352});
            }
            columns->setUpdatesEnabled(true);
        }
        // The centre column's blender card drops under the title when the centre is narrow.
        const int centreWidth = tall ? w : narrow ? w - 260 : w - 256 - 352; // the splitter has not laid out yet
        const bool below = centreWidth < 780;
        if (below != cardBelow && headerGrid) {
            cardBelow = below; auto *card = hub->blenderCard();
            headerGrid->removeWidget(card);
            if (below) headerGrid->addWidget(card, 3, 0, 1, 2); else headerGrid->addWidget(card, 0, 1, 2, 1);
        }
        fitTimelineHeight();
    }
    // R4: the timeline panel is as tall as its rows, capped so the inspector keeps the rest.
    void fitTimelineHeight() {
        if (!timelineScroll || !timeline) return;
        const int natural = timeline->sizeHint().height();
        const bool narrow = layoutMode == Mode::Narrow, portrait = q->height() > q->width();
        const bool tall = q->height() * 4 > q->width() * 5;
        const int cap = narrow ? std::max(tall ? 360 : portrait ? 260 : 190, int(q->height() * (tall ? 0.40 : portrait ? 0.30 : 0.26)))
                               : std::max(260, int(q->height() * 0.62));
        timelineScroll->setFixedHeight(std::min(natural + 2, cap));
    }
    AtlasButton *addButton(QBoxLayout *layout, const QString &text, std::function<void()> fn) {
        auto *button = new AtlasButton(text); layout->addWidget(button);
        QObject::connect(button, &QPushButton::clicked, q, std::move(fn)); return button;
    }
    void createPanels() {
        outliner = new OutlinerPanel; outliner->setGrouped(true);
        inspector = new InspectorPanel; attributes = new AttributesPanel;
        problems = new ProblemsPanel; clips = new ClipBrowserPanel;
        fidelity = new FidelityPanel; review = new ReviewPanel;
        tabs = new InspectorTabs; tabs->setObjectName("wbInspectorTabs"); tabs->setMinimumWidth(310);
        const auto scroll = [](QWidget *content) {
            auto *area = new QScrollArea; area->setWidgetResizable(true); area->setFrameShape(QFrame::NoFrame); area->setWidget(content); return area;
        };
        hitboxTab = scroll(inspector); attributesTab = scroll(attributes);
        tabs->addTab(hitboxTab, t("Hitbox", "Hitbox"));
        tabs->addTab(attributesTab, t("Attributes", "Atributos"));
        projectiles = new ProjectilesPanel;
        QObject::connect(projectiles, &ProjectilesPanel::editRequested, q, [this](const QString &name, const QJsonObject &args) { q->runCommand(name, args); });
        QObject::connect(projectiles, &ProjectilesPanel::addSpawnRequested, q, [this](int article) {
            if (!row.isEmpty()) q->runCommand("add_spawn", {{"row", row}, {"frame", timeline->frame()}, {"article", article}});
        });
        auto *checksBody = new QWidget; auto *checksLayout = new QVBoxLayout(checksBody);
        auto *problemActions = new QHBoxLayout; checksLayout->addLayout(problemActions);
        auto *check = addButton(problemActions, t("Run checks", "Ejecutar comprobaciones"), [this] { setPlaying(false); q->runCommand("run_checks", {}); });
        check->setObjectName("wbRunChecks"); problemActions->addStretch();
        auto *checksTabs = new QTabWidget; checksLayout->addWidget(checksTabs, 1);
        checksTabs->addTab(problems, t("Problems", "Problemas"));
        auto *fidelityBody = new QWidget; auto *fidelityLayout = new QVBoxLayout(fidelityBody);
        fidelityNote = new QLabel; fidelityNote->setTextFormat(Qt::PlainText); fidelityNote->setWordWrap(true);
        fidelityLayout->addWidget(fidelityNote); fidelityLayout->addWidget(fidelity);
        checksTabs->addTab(fidelityBody, t("Fidelity", "Fidelidad"));
        auto *reviewBody = new QWidget; auto *reviewLayout = new QVBoxLayout(reviewBody);
        auto *reviewActions = new QHBoxLayout; reviewLayout->addLayout(reviewActions);
        addButton(reviewActions, t("Undo", "Deshacer"), [this] { emit review->undoRequested(); });
        addButton(reviewActions, t("Redo", "Rehacer"), [this] { emit review->redoRequested(); });
        reviewActions->addStretch(); reviewLayout->addWidget(review);
        checksTabs->addTab(reviewBody, t("History and review", "Historial y revisión"));
        tabs->addTab(checksBody, t("Checks", "Comprobaciones"));
        auto *renderBody = new QWidget; auto *renderLayout = new QVBoxLayout(renderBody);
        renderLayout->addWidget(kit::capLabel(t("Game and Blender", "Juego y Blender"), atlas::Role::Cap16, "muted"));
        renderLayout->addWidget(hub->engineControls());
        renderLayout->addWidget(kit::capLabel(t("Clips", "Clips"), atlas::Role::Cap16, "muted"));
        auto *clipActions = new QHBoxLayout; renderLayout->addLayout(clipActions);
        addButton(clipActions, t("Preview", "Vista previa"), [this] { clips->previewCurrent(); });
        addButton(clipActions, t("Assign to move", "Asignar al movimiento"), [this] { clips->assignCurrent(); });
        clips->setMinimumHeight(140); renderLayout->addWidget(clips);
        renderLayout->addWidget(kit::capLabel(t("Frame export", "Exportar cuadro"), atlas::Role::Cap16, "muted"));
        auto *camera = new QComboBox; camera->setAccessibleName(t("Camera preset", "Vista de cámara"));
        camera->addItem(t("Side", "Lateral"), "side"); camera->addItem(t("Front", "Frontal"), "front");
        camera->addItem(t("Top", "Superior"), "top"); camera->addItem(t("Three quarter", "Tres cuartos"), "three_quarter");
        renderLayout->addWidget(camera);
        QObject::connect(camera, qOverload<int>(&QComboBox::activated), q, [this, camera] { q->runCommand("set_camera", {{"preset", camera->currentData().toString()}}); });
        const QVector<QPair<QString, QString>> overlayNames{{"hitboxes", t("Hitboxes", "Hitboxes")},
            {"hurtboxes", t("Hurtboxes", "Hurtboxes")}, {"bones", t("Bones", "Huesos")},
            {"ecb", t("ECB", "ECB")}, {"floor", t("Floor", "Suelo")}};
        for (const auto &entry : overlayNames) {
            auto *toggle = new QCheckBox(entry.second); renderLayout->addWidget(toggle);
            QObject::connect(toggle, &QCheckBox::toggled, q, [this, key = entry.first](bool on) { q->runCommand("set_overlays", {{key, on}}); });
        }
        auto *renderActions = new QHBoxLayout; renderLayout->addLayout(renderActions);
        addButton(renderActions, t("Export frame PNG", "Exportar cuadro PNG"), [this] { q->runCommand("render_view", {{"w", 640}, {"h", 480}}); });
        renderLayout->addStretch(); tabs->addTab(scroll(renderBody), t("Render", "Renderizar"));
        tabs->addTab(projectiles, t("Projectiles", "Proyectiles")); // last: the tabs before it keep their positions
        combo = new ComboPanel;
        QObject::connect(combo, &ComboPanel::editRequested, q, [this](const QString &name, const QJsonObject &args) { q->runCommand(name, args); });
        QObject::connect(combo, &ComboPanel::moveRequested, q, [this](const QString &name) { selectRow(name); });
        QObject::connect(combo, &ComboPanel::routeSelected, q, [this](int index) { if (routeLanes) routeLanes->selectRoute(index); });
        QObject::connect(routeLanes, &RouteLanes::routeSelected, q, [this](int index) { if (combo) { combo->selectRoute(index); tabs->setCurrentWidget(combo); } });
        QObject::connect(combo, &ComboPanel::playStringRequested, q, [this](int index) { q->runCommand("play_string", {{"index", index}, {"realtime", true}}); });
        tabs->addTab(combo, t("Combo", "Combo"));
        columns->addWidget(tabs);
        QObject::connect(inspector, &InspectorPanel::revertRequested, q, [this](const QJsonObject &args) { q->runCommand("revert_change", args); });
        QObject::connect(attributes, &AttributesPanel::revertRequested, q, [this](const QJsonObject &args) { q->runCommand("revert_change", args); });
        QObject::connect(attributes, &AttributesPanel::requestRefresh, q, [this] { q->runCommand("list_attributes", {}); });
        QObject::connect(attributes, &AttributesPanel::editRequested, q, [this](const QString &command, const QJsonObject &args) { q->runCommand(command, args); });
        QObject::connect(tabs, &QTabWidget::currentChanged, q, [this](int index) {
            if (tabs->widget(index) == attributesTab && !closing) q->runCommand("list_attributes", {});
        });
        QObject::connect(outliner, &OutlinerPanel::rowSelected, q, [this](const QString &name) { selectRow(name); if (railInTabs && autoHitbox->isChecked()) showHitboxTab(); });
        QObject::connect(outliner, &OutlinerPanel::hitboxSelected, q, [this](const QString &name, int ordinal) { selectRow(name, ordinal); if (railInTabs && autoHitbox->isChecked()) showHitboxTab(); });
        QObject::connect(moveChip, &QPushButton::clicked, q, [this] { if (railInTabs) tabs->setCurrentWidget(movesRail); });
        QObject::connect(inspector, &InspectorPanel::editRequested, q, [this](const QString &name, const QJsonObject &args) {
            q->runCommand(name, args);
        });
        QObject::connect(problems, &ProblemsPanel::problemActivated, q, [this](const QString &name, int ordinal) {
            selectRow(name, ordinal); showHitboxTab();
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
        if (selectedOrdinal < 0 && !snapshot.hits.value(row).isEmpty()) selectedOrdinal = snapshot.hits.value(row).first().ordinal;
        outliner->setSelection(row, selectedOrdinal);
        timeline->setSelectedHitbox(selectedOrdinal);
        inspector->setRoles(snapshot.roles);
        const auto *hit = selectedHitbox();
        if (hit) { inspector->showHitbox(row, *hit); inspector->setChanges(row, snapshot.changes); } else { selectedOrdinal = -1; inspector->clear(!snapshot.hits.value(row).isEmpty()); }
        inspector->setRowChecks(rowProblems, checksCurrent);
        QString currentClip; QVector<int> motions;
        for (const auto &entry : snapshot.rows) if (entry.name == row) { currentClip = entry.effectiveClip(); motions = entry.motions; break; }
        clips->setClips(snapshot.clips, currentClip); fidelity->setFidelity(snapshot.fidelity, row, motions);
        fidelityNote->setText(snapshot.fidelityError.isEmpty() ? QString() :
            t("Cannot read fidelity: %1", "No se puede leer la fidelidad: %1").arg(snapshot.fidelityError));
        fidelityNote->setVisible(!snapshot.fidelityError.isEmpty());
    }
    static QString lastRowFor(const QString &project) {
        if (QCoreApplication::organizationName().isEmpty() || project.isEmpty()) return {};
        return QSettings().value("workbench/lastRow/" + project).toString();
    }
    void rememberRow(const QString &name) {
        if (QCoreApplication::organizationName().isEmpty() || snapshot.projectName.isEmpty()) return;
        QSettings().setValue("workbench/lastRow/" + snapshot.projectName, name);
    }
    void showHitboxTab() { if (hitboxTab) tabs->setCurrentWidget(hitboxTab); }
    void selectRow(const QString &name, int ordinal = -1) {
        bool found = false; for (const auto &entry : snapshot.rows) if (entry.name == name) { found = true; break; }
        if (!found || closing) return;
        setPlaying(false); row = name; selectedOrdinal = ordinal; clipPreview = false; rememberRow(name);
        const QSignalBlocker block(rows); rows->setCurrentIndex(rows->findData(row));
        frameInfo = {}; timeline->setFrame(0); updateTimeline(); refreshSelection();
        const auto *hit = selectedHitbox(); restoringFrame = ordinal >= 0 && hit ? hit->startFrame : 0;
        q->runCommand("load_row", {{"row", row}});
    }
    bool busy() const { return running || playLaunching || !queue.isEmpty(); }
    void setPlaying(bool on) {
        on = on && timeline->frameCount() > 0 && !closing;
        if (on) playTimer.start(); else playTimer.stop();
        timeline->setPlaying(on); play->setText(on ? t("Pause", "Pausar") : t("Play", "Jugar"));
    }
    QString lastStatus;
    void setFix(FixKind fix, const QString &label) {
        currentFix = fix;
        if (!fixButton) return;
        fixButton->setText(label); fixButton->setAccessibleName(label);
        fixButton->setProperty("fix", fixName(fix)); fixButton->setVisible(fix != FixKind::None);
    }
    // Plain text, no action.
    void status(const QString &text) {
        lastStatus = text; setFix(FixKind::None, {});
        if (progress && !progress->isRunning()) progress->setMessage(text);
    }
    // An error that says what to do and, where one action helps, offers it as a button.
    void statusHelp(const ErrorHelp &help) {
        lastStatus = help.message; setFix(help.fix, help.fixLabel);
        if (progress && !progress->isRunning()) progress->setMessage(help.message);
    }
    void statusError(const QString &command, const QString &raw) { statusHelp(explainError(command, raw)); }
    void statusLaunch(const QString &raw) { statusHelp(explainStatus(raw)); }
    void performFix(FixKind fix) {
        switch (fix) {
        case FixKind::ChooseGameExe: emit q->gameExePickRequested(); break;
        case FixKind::ChooseBlender: emit q->blenderPickRequested(); break;
        case FixKind::StartGame: setPlaying(false); q->runCommand("engine_restart", {}); break;
        case FixKind::StartBlender: startBlender(); break;
        case FixKind::Rebuild: rebuildAndReload(); break;
        case FixKind::ReloadFromDisk: setPlaying(false); q->runCommand("reload_from_disk", {}); break;
        case FixKind::None: break;
        }
    }
    void startBlender() {
        setPlaying(false);
        if (!blenderError().isEmpty()) { statusLaunch(blenderError()); return; }
        pendingBlenderOpen = true;
        // A process can die while the hub is idle. Ask the worker for the
        // current state before deciding whether Blender needs an engine start.
        q->runCommand("engine_status", {});
    }
    void updateFrameReadout() {
        frameReadout->setText(t("Frame %1 / %2", "Cuadro %1 / %2").arg(timeline->frame()).arg(qMax(0, timeline->frameCount() - 1)));
    }
    void stepFrame(int amount) {
        if (!timeline->frameCount()) return;
        setPlaying(false); timeline->setFrame(timeline->frame() + amount); updateFrameReadout();
        q->runCommand("set_frame", {{"frame", timeline->frame()}});
    }
    void rebuildAndReload() {
        if (busy() || closing) return;
        setPlaying(false); rebuildReload = true; newSinceBuild = 0; updateRebuildLabel();
        progress->begin(t("Rebuilding", "Reconstruyendo"), false);
        q->reportRebuildProgress(t("Rebuilding gameplay", "Reconstruyendo jugabilidad"), -1, 0, false);
        q->runCommand("rebuild", {});
    }
    void updateBadges() {
        QMap<QString, int> warnings;
        for (const auto &problem : rowProblems) ++warnings[problem.row];
        outliner->setBadges(editedRows + queuedRows, warnings); hub->setPendingChanges(pendingChanges);
    }
    void showBlender() {
        if (blenderPid <= 0) {
            if (!blenderError().isEmpty()) { statusLaunch(blenderError()); return; }
            if (QMessageBox::question(q, t("Blender is closed", "Blender está cerrado"),
                    t("Blender is not running. Start it with this fighter project?", "Blender no está en marcha. ¿Iniciarlo con este proyecto del luchador?"),
                    QMessageBox::Yes | QMessageBox::No, QMessageBox::Yes) == QMessageBox::Yes) openBlender();
            return;
        }
#ifdef Q_OS_WIN
        struct Search { DWORD pid; HWND window = nullptr; } found{DWORD(blenderPid)};
        if (blenderPid > 0) EnumWindows([](HWND window, LPARAM data) -> BOOL {
            auto *match = reinterpret_cast<Search *>(data); DWORD pid = 0;
            GetWindowThreadProcessId(window, &pid);
            if (pid == match->pid && IsWindowVisible(window) && GetWindow(window, GW_OWNER) == nullptr) {
                match->window = window; return FALSE;
            }
            return TRUE;
        }, reinterpret_cast<LPARAM>(&found));
        if (found.window) {
            if (IsIconic(found.window)) ShowWindow(found.window, SW_RESTORE);
            if (SetForegroundWindow(found.window)) return;
            FLASHWINFO flash{sizeof(FLASHWINFO), found.window, FLASHW_TRAY, 3, 0}; FlashWindowEx(&flash);
            status(t("Blender is ready on the taskbar", "Blender está listo en la barra de tareas")); return;
        }
        status(t("Blender window is not available yet", "La ventana de Blender aún no está disponible"));
#else
        status(t("Use your desktop window switcher to show Blender", "Usa el selector de ventanas para mostrar Blender"));
#endif
    }
    QString blenderExe() const {
        const auto env = QProcessEnvironment::systemEnvironment();
        auto found = findBlender(blenderSetting, env);
        return found.isEmpty() ? discoverBlender(snapshot.projectDir, env) : found;
    }
    QString blenderError() const {
        const auto blender = blenderExe();
        if (blender.isEmpty()) return t("Blender not found: set GW_BLENDER or the Blender path in Settings",
            "No se encontro Blender: define GW_BLENDER o la ruta de Blender en Ajustes");
        const auto addon = findAddonDir(snapshot.projectDir);
        if (addon.isEmpty()) return t("Workbench Blender add-on not found in this project's checkout",
            "No se encontro el complemento de Blender en el repositorio de este proyecto");
        if (snapshot.art.isEmpty()) return t("Set art_blend or art_glb in workbench.json to open the fighter",
            "Define art_blend o art_glb en workbench.json para abrir el luchador");
        return blenderCommand(blender, addon, snapshot.projectDir, 1, snapshot.art).error;
    }
    void finishPlay(const QString &message) {
        playLaunching = false;
        if (!closing) statusLaunch(message);
        pump(); notifyBusy();
    }
    void startPlayProcess(bool check, bool rebuild = false) {
        if (closing) { finishPlay({}); return; }
        playLaunching = true; notifyBusy();
        status(check ? t("Checking package…", "Comprobando el paquete…") :
            rebuild ? t("Rebuilding gameplay before play…", "Reconstruyendo la jugabilidad antes de jugar…") :
                      t("Opening game…", "Abriendo el juego…"));
        auto *process = new QProcess(q); playProcess = process;
        process->setProgram(pendingPlay.program);
        auto args = pendingPlay.args;
        if (check) args << "--check";
        if (rebuild) args << "--rebuild";
        process->setArguments(args); process->setWorkingDirectory(pendingPlay.workingDir);
        QObject::connect(process, &QProcess::errorOccurred, q, [this, process](QProcess::ProcessError error) {
            if (playProcess != process || error != QProcess::FailedToStart) return;
            const auto message = process->errorString(); playProcess = nullptr; process->deleteLater();
            finishPlay(t("Could not start the play tool: %1. Check that Python is installed (or set GW_PYTHON), then try again.",
                    "No se pudo iniciar la herramienta de juego: %1. Comprueba que Python esté instalado (o define GW_PYTHON) y vuelve a intentarlo.").arg(message));
        });
        QObject::connect(process, qOverload<int, QProcess::ExitStatus>(&QProcess::finished), q,
            [this, process, check](int code, QProcess::ExitStatus exit) {
                if (playProcess != process) return;
                const auto output = process->readAllStandardOutput();
                const auto stderrText = QString::fromUtf8(process->readAllStandardError()).trimmed();
                playProcess = nullptr; process->deleteLater();
                if (closing) { finishPlay({}); return; }
                QJsonParseError parse;
                const auto document = QJsonDocument::fromJson(output.trimmed(), &parse);
                const auto result = document.object();
                if (exit != QProcess::NormalExit || code != 0 || parse.error != QJsonParseError::NoError ||
                    !document.isObject() || !result.value("ok").toBool()) {
                    QString error = result.value("error").toString();
                    if (error.isEmpty()) error = stderrText;
                    if (error.isEmpty()) error = t("Play tool returned an invalid result", "La herramienta de juego devolvió un resultado inválido");
                    finishPlay(t("Play failed: %1", "No se pudo jugar: %1").arg(error)); return;
                }
                if (!check) {
                    finishPlay(t("Game launch started. Log: %1", "Se inició el juego. Registro: %1")
                        .arg(result.value("log_path").toString())); return;
                }
                const auto stale = result.value("stale").toArray();
                if (stale.isEmpty()) { startPlayProcess(false); return; }
                if (!result.value("can_rebuild").toBool()) {
                    finishPlay(t("Package is stale. Configure a gameplay rebuild in workbench.json before playing.",
                        "El paquete está desactualizado. Configura una reconstrucción de jugabilidad en workbench.json antes de jugar."));
                    return;
                }
                auto *dialog = new QMessageBox(QMessageBox::Warning,
                    t("Rebuild before play", "Reconstruir antes de jugar"),
                    t("The package is stale. Rebuild gameplay before opening the game?",
                      "El paquete está desactualizado. ¿Reconstruir la jugabilidad antes de abrir el juego?"),
                    QMessageBox::Cancel, q);
                dialog->setObjectName("wbPlayRebuild"); dialog->setAttribute(Qt::WA_DeleteOnClose);
                QStringList reasons; for (const auto &reason : stale) reasons << reason.toString();
                dialog->setDetailedText(reasons.join('\n'));
                auto *accept = dialog->addButton(t("Rebuild and play", "Reconstruir y jugar"), QMessageBox::AcceptRole);
                accept->setObjectName("wbPlayRebuildAccept"); dialog->setDefaultButton(accept);
                playDialog = dialog;
                QObject::connect(dialog, &QMessageBox::finished, q, [this, dialog, accept](int) {
                    const bool rebuild = dialog->clickedButton() == accept;
                    playDialog = nullptr;
                    if (rebuild && !closing) startPlayProcess(false, true);
                    else finishPlay(t("Play cancelled", "Juego cancelado"));
                });
                dialog->open();
            });
        process->start();
        process->closeWriteChannel();
    }
    void playFighter(bool vsCpu) {
        if (busy() || closing) return;
        setPlaying(false);
        pendingPlay = playCommand(snapshot.projectDir, vsCpu, row);
        if (!pendingPlay.error.isEmpty()) { statusLaunch(pendingPlay.error); return; }
        // Freeze project/move arguments across the check and rebuild prompt.
        startPlayProcess(true);
    }
    void notifyBusy() {
        hub->setControls(busy() || closing, snapshot.canStop, snapshot.ownedEngine, blenderError());
        hub->setPlayControls(busy() || closing, playCommand(snapshot.projectDir, false, row).error);
        hub->setRebuildAvailable(snapshot.canRebuild);
        const bool structuralPending = this->structuralPending();
        inspector->setEnabled(!structuralPending && !closing && selectedHitbox());
        timeline->setEnabled(!structuralPending && !closing);
        // Structural edits renumber source ordinals: never enqueue a second
        // add/delete against the still-visible pre-edit occurrence.
        if (auto *remove = inspector->findChild<QPushButton *>("wbDeleteHitbox"))
            remove->setEnabled(canEdit() && selectedHitbox());
        if (auto *add = q->findChild<QPushButton *>("wbAddHitbox"))
            add->setEnabled(canEdit() && !row.isEmpty());
        updateRebuildLabel();
        emit q->busyChanged(busy());
    }
    void openBlender() {
        const auto error = blenderError();
        if (!error.isEmpty()) { statusLaunch(error); return; }
        const quint16 port = q->serveForBlender(); if (!port) return;
        const auto command = blenderCommand(blenderExe(),
            findAddonDir(snapshot.projectDir), snapshot.projectDir, port, snapshot.art);
        if (!command.error.isEmpty()) { statusLaunch(command.error); return; }
        if (!blenderDriver) {
            QFile source(":/workbench/blender_sync.py");
            auto driver = std::make_unique<QTemporaryFile>();
            if (!source.open(QIODevice::ReadOnly) || !driver->open()) {
                status(t("Cannot prepare Blender synchronization", "No se puede preparar la sincronización de Blender")); return;
            }
            const auto bytes = source.readAll();
            if (driver->write(bytes) != bytes.size() || !driver->flush()) {
                status(t("Cannot prepare Blender synchronization", "No se puede preparar la sincronización de Blender")); return;
            }
            driver->close(); blenderDriver = std::move(driver);
        }
        QProcess process; process.setProgram(command.program); process.setArguments(command.args);
        auto environment = QProcessEnvironment::systemEnvironment();
        environment.insert("GW_WB_DRIVER", blenderDriver->fileName()); process.setProcessEnvironment(environment);
        qint64 pid = 0;
        if (!process.startDetached(&pid)) {
            statusLaunch(t("Could not start Blender. Check the Blender path in Settings.",
                "No se pudo iniciar Blender. Revisa la ruta de Blender en Ajustes.")); return;
        }
        q->setBlenderProcessId(pid);
        status(t("Blender opened; workbench port %1", "Blender abierto; puerto del banco de trabajo %1").arg(port));
    }
    void enqueue(const QString &name, const QJsonObject &args, std::optional<bool> headless = std::nullopt) {
        if (closing) return;
        if (isEditName(name) || name == "accept" || name == "undo" || name == "redo" || name == "revert_change" || name == "revert_all") {
            setPlaying(false); stickyNote.clear();
        }
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
        if (isEditName(name) && rebuildActive()) {
            // Allowed and queued behind the build; it applies afterwards and belongs to the next rebuild.
            request.duringBuild = true; ++queuedDuringBuild;
            const QString editedRow = args.value("row").toString();
            if (!editedRow.isEmpty()) queuedRows.insert(editedRow);
            updateBadges();
        }
        // Preserve edits and explicit debug commands; only consecutive seeks are disposable.
        if (!queue.isEmpty() && queue.back().name == name && name == "set_frame") queue.back() = request;
        else queue.enqueue(request);
        pump(); notifyBusy();
    }
    void pump() {
        if (running || playLaunching) return;
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
    void applyChanges() {
        editedRows.clear();
        for (const auto &entry : snapshot.changes) {
            const QString changedRow = entry.toObject().value("row").toString();
            if (!changedRow.isEmpty()) editedRows.insert(changedRow);
        }
        pendingChanges = int(snapshot.changes.size());
        attributes->setChanges(snapshot.changes);
    }
    void refresh(const Snapshot &value) {
        if (!value.valid) return;
        snapshot = value;
        int hitboxes = 0; for (const auto &hits : snapshot.hits) hitboxes += int(hits.size());
        hub->setProject(snapshot.projectName, int(snapshot.rows.size()), hitboxes);
        hub->setEngineStatus(snapshot.engineStatus); hub->setHeadless(snapshot.headless);
        viewRevision = snapshot.viewRevision;
        hub->setBlenderState(blenderPid > 0, blenderHeartbeat.isValid() && blenderHeartbeat.elapsed() < 2000 && snapshot.blenderAck > 0 && snapshot.blenderAck == viewRevision);
        search->setPlaceholderText(t("Search %1 rows", "Buscar %1 filas").arg(snapshot.rows.size()));
        QSignalBlocker block(rows); rows->clear();
        for (const auto &r : snapshot.rows) rows->addItem(r.name, r.name);
        int selected = rows->findData(row);
        if (selected < 0 && rows->count()) {
            // First open: the last-used move of this project, else the first move that has hitboxes.
            selected = 0;
            const QString last = lastRowFor(snapshot.projectName);
            if (!last.isEmpty() && rows->findData(last) >= 0) selected = rows->findData(last);
            else for (int i = 0; i < rows->count(); ++i) if (!snapshot.hits.value(rows->itemData(i).toString()).isEmpty()) { selected = i; break; }
        }
        rows->setCurrentIndex(selected); row = rows->currentData().toString(); updateTimeline();
        outliner->setRows(snapshot.rows, snapshot.hits); applyChanges(); refreshSelection(); updateBadges();
        review->setHistory(snapshot.history);
        updateRecovery();
        paletteCommands = CommandRegistry{};
        for (const auto &spec : snapshot.commands) paletteCommands.add(spec);
    }
    void updateTimeline() {
        const auto bounded = [](qint64 value) { return int(std::clamp(value, qint64(0), qint64(std::numeric_limits<int>::max()))); };
        int frames = 0, iasa = 0;
        for (const auto &r : snapshot.rows) if (r.name == row) {
            iasa = r.iasa; moveGroupLabel->setText(moveGroup(r));
            for (const auto &clip : snapshot.clips) if (clip.name == r.effectiveClip()) frames = bounded(qint64(clip.frames) - r.cropStart);
            frames = std::max(frames, bounded(qint64(r.iasa) + 1));
        }
        const auto hits = snapshot.hits.value(row);
        for (const auto &hit : hits)
            frames = std::max(frames, std::max(bounded(qint64(hit.startFrame) + 1), hit.endFrame));
        QVector<QPair<int, int>> windows;
        for (const auto &hit : hits) {
            const int end = hit.endFrame < 0 ? frames : hit.endFrame;
            if (hit.startFrame >= 0 && end > hit.startFrame) windows.append({hit.startFrame, end});
        }
        std::sort(windows.begin(), windows.end());
        QVector<QPair<int, int>> merged;
        for (const auto &window : windows) {
            if (merged.isEmpty() || window.first > merged.last().second) merged.append(window);
            else merged.last().second = std::max(merged.last().second, window.second);
        }
        QStringList activeRanges;
        for (const auto &window : merged)
            activeRanges.append(window.second == window.first + 1 ? QString::number(window.first) :
                t("%1–%2", "%1–%2").arg(window.first).arg(window.second - 1));
        timeline->setMove(row, frames, hits, iasa, snapshot.events.value(row));
        if (projectiles) projectiles->setData(snapshot.articles, snapshot.spawns, row);
        if (spawnLane) { spawnLane->setSpawns(row, snapshot.spawns, projectiles->articleNames()); spawnLane->update(); }
        if (routeLanes && combo) {
            QStringList tokens{row}, moveNames;
            for (const auto &entry : snapshot.rows) { moveNames << entry.name; if (entry.name == row) for (int m : entry.motions) tokens << QString("motion:%1").arg(m); }
            routeLanes->setRoutes(row, tokens, snapshot.routes);
            combo->setData(snapshot.routes, snapshot.strings, snapshot.comboMeta, moveNames, row, tokens, snapshot.hasCombo);
        }
        timeline->setMinimumHeight(timeline->sizeHint().height()); fitTimelineHeight();
        moveTitle->setText(row.isEmpty() ? t("Choose a move", "Elige un movimiento") : row);
        moveChip->setText(row.isEmpty() ? t("No move", "Sin movimiento") : row);
        hub->setMove(row);
        const auto active = activeRanges.isEmpty() ? t("None", "Ninguno") : activeRanges.join(t(", ", ", "));
        moveStats->setText(t("Total %1f    Active %2    Cancel %3", "Total %1f    Activo %2    Cancelar %3")
            .arg(frames).arg(active).arg(iasa > 0 ? QString::number(iasa) : t("None", "Ninguno")));
        moveStats->setToolTip(t("Frames start at 0. Hitbox end fields are exclusive.", "Los cuadros empiezan en 0. Los campos finales de hitbox son exclusivos."));
        updateFrameReadout();
    }
    void finished(const Reply &result) {
        if (disposing) {
            disposed = true; disposing = false; running = false; notifyBusy(); emit q->shutdownFinished();
            if (closeWindow) q->close();
            return;
        }
        if (closing) { running = false; dispose(); return; }
        const Request completed = active;
        if (isStructuralName(completed.name) &&
            result.envelope.value("ok").toBool() && result.envelope.value("result").toObject().value("applied").toBool()) {
            inspector->clear(); selectedOrdinal = -1;
        }
        if (completed.duringBuild) {
            queuedDuringBuild = std::max(0, queuedDuringBuild - 1);
            if (queuedDuringBuild == 0) queuedRows.clear();
            if (result.envelope.value("ok").toBool() && result.envelope.value("result").toObject().value("applied").toBool())
                ++newSinceBuild;
        }
        refresh(result.snapshot);
        if (result.hasAttributes) attributes->setAttributes(result.attributes);
        const auto reply = result.envelope;
        const bool ok = reply.value("ok").toBool();
        const auto value = reply.value("result").toObject();
        if (!ok) {
            pendingBlenderOpen = false; setPlaying(false); statusError(completed.name, reply.value("error").toString());
            if (rebuildReload || rebuildReloading || completed.name == "rebuild") {
                rebuildReload = rebuildReloading = false; progress->finish(lastStatus, false);
            }
        } else {
            if (completed.name == "list_attributes") attributes->setAttributes(value.value("attributes").toArray());
            if (completed.name == "delete_hitbox" && value.value("applied").toBool())
                stickyNote = t("Hitbox deleted. Press Ctrl+Z to bring it back.", "Hitbox borrado. Pulsa Ctrl+Z para recuperarlo.");
            if (completed.name == "render_view" && value.contains("path"))
                status(t("Frame exported: %1", "Cuadro exportado: %1").arg(value.value("path").toString()));
            const QString warning = value.value("warning").toString();
            if (completed.name != "render_view")
                status(warning.isEmpty() ? (stickyNote.isEmpty() ? t("Ready", "Ready") : stickyNote) : t("Warning: %1", "Aviso: %1").arg(warning));
            if (completed.name == "rebuild") {
                if (rebuildReload) {
                    rebuildReload = false; rebuildReloading = true;
                    q->reportRebuildProgress(t("Restarting game", "Reiniciando juego"), -1, -1, false);
                    q->runCommand("reload", {});
                } else progress->finish(t("Rebuild complete", "Reconstrucción completa"));
            }
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
                rowProblems = found; checksCurrent = true; problems->setProblems(found);
                inspector->setRowChecks(rowProblems, true); updateBadges();
                // Engine checks sweep motions. Restore the visible move before playback.
                if (value.value("engine").toBool() && !row.isEmpty()) {
                    restoringFrame = timeline->frame(); q->runCommand("load_row", {{"row", row}});
                }
            }
            if (value.contains("frame") && completed.rowIntent == rowIntent && completed.frameIntent == frameIntent) {
                frameInfo = FrameInfo::fromJson(value); timeline->setFrame(frameInfo.frame); updateFrameReadout();
            }
            if (completed.name == "reload_from_disk" || completed.name == "recovery_resolve") {
                rowProblems.clear(); checksCurrent = false; problems->setProblems({}); updateBadges();
                if (snapshot.engineStatus == "ready" || snapshot.engineStatus == "running") q->runCommand("reload", {});
                status(completed.name == "reload_from_disk" ? t("Reloaded from disk", "Recargado desde el disco")
                                                            : t("Recovery done", "Recuperación hecha"));
            }
            if ((isEditName(completed.name) || completed.name == "accept" || completed.name == "revert_change" || completed.name == "revert_all" ||
                 completed.name == "undo" || completed.name == "redo") && value.value("applied").toBool()) {
                rowProblems.clear(); checksCurrent = false; problems->setProblems({});
                if (completed.name == "add_hitbox" || completed.name == "duplicate_hitbox") { selectedOrdinal = value.value("ordinal").toInt(-1); refreshSelection(); }
                updateBadges(); q->runCommand("reload", {});
            } else if (completed.name == "reload" || completed.name == "engine_restart") {
                if (rebuildReloading) {
                    rebuildReloading = false; updateBadges();
                    progress->finish(t("Rebuilt and reloaded", "Reconstruido y recargado"));
                }
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
        if (name == "ui_view_state") {
            if (reply.envelope.value("ok").toBool() && blenderPid > 0 && args.value("pid").toInteger() == blenderPid) {
                blenderHeartbeat.restart();
                const auto revision = reply.envelope.value("result").toObject().value("revision").toInteger();
                hub->setBlenderState(true, reply.envelope.value("result").toObject().value("available").toBool() &&
                    revision > 0 && args.value("revision").toInteger() == revision);
            }
            return;
        }
        if (isStructuralName(name) && reply.envelope.value("ok").toBool() &&
            reply.envelope.value("result").toObject().value("applied").toBool()) {
            inspector->clear(); selectedOrdinal = -1;
        }
        if (reply.snapshot.valid && !reply.snapshot.currentRow.isEmpty()) row = reply.snapshot.currentRow;
        refresh(reply.snapshot);
        if (reply.hasAttributes) attributes->setAttributes(reply.attributes);
        const auto value = reply.envelope.value("result").toObject();
        if (reply.envelope.value("ok").toBool()) {
            if (value.contains("frame")) { frameInfo = FrameInfo::fromJson(value); timeline->setFrame(frameInfo.frame); updateFrameReadout(); }
            if (value.value("applied").toBool()) {
                rowProblems.clear(); checksCurrent = false; problems->setProblems({});
                updateBadges();
            }
            if (name == "list_attributes") attributes->setAttributes(value.value("attributes").toArray());
            if (name == "run_checks") {
                QVector<Problem> found;
                for (const auto &item : value.value("problems").toArray()) {
                    const auto p = item.toObject();
                    found.append({p["kind"].toString(), p["row"].toString(), p["message"].toString(), p["ordinal"].toInt(-1)});
                }
                rowProblems = found; checksCurrent = true; problems->setProblems(found);
                inspector->setRowChecks(rowProblems, true); updateBadges();
            }
            if (name == "rebuild") progress->finish(t("Rebuild complete", "Reconstrucción completa"));
        } else {
            statusError(name, reply.envelope.value("error").toString());
            if (name == "rebuild") progress->finish(lastStatus, false);
        }
        // Socket edits stay stale until Blender asks for rebuild/reload. Never
        // synthesize GUI follow-up commands or restart the engine here.
        emit q->commandFinished(name, reply.envelope); notifyBusy();
    }
};

WorkbenchWindow::WorkbenchWindow(Session &s, QWidget *parent) : QMainWindow(parent), d_(std::make_unique<Impl>(this)) {
    installWheelGuard();
    d_->worker->session = &s;
    runCommand("list_rows", {});
}
WorkbenchWindow::WorkbenchWindow(const QString &projectDir, LaunchFactory launch, QWidget *parent)
    : QMainWindow(parent), d_(std::make_unique<Impl>(this)) {
    installWheelGuard();
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
void WorkbenchWindow::reportRebuildProgress(const QString &phase, int percent, qint64 elapsedMs, bool cancellable) {
    if (QThread::currentThread() != thread()) {
        QMetaObject::invokeMethod(this, [this, phase, percent, elapsedMs, cancellable] {
            reportRebuildProgress(phase, percent, elapsedMs, cancellable);
        }, Qt::QueuedConnection); return;
    }
    if (d_->closing) return;
    if (!d_->progress->isRunning()) d_->progress->begin(phase, cancellable);
    d_->progress->setProgress(phase, percent, elapsedMs, cancellable);
    emit rebuildProgress(phase, percent, elapsedMs, cancellable);
}
void WorkbenchWindow::setBlenderProcessId(qint64 pid) {
    d_->blenderPid = qMax(qint64(0), pid); d_->blenderHeartbeat.invalidate();
    d_->hub->setBlenderState(d_->blenderPid > 0, false);
    QMetaObject::invokeMethod(d_->workerContext, [state = d_->worker, pid = d_->blenderPid] {
        state->submit([state, pid] { state->ensureSession(); state->session->blenderPid = pid; state->session->blenderAckRevision = 0; });
    }, Qt::QueuedConnection);
}
void WorkbenchWindow::startGame() { d_->setPlaying(false); runCommand("engine_restart", {}); }
void WorkbenchWindow::startBlender() { d_->startBlender(); }
void WorkbenchWindow::setGameExeInfo(const QString &text) { d_->hub->setEngineDetail(text); }
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
QString WorkbenchWindow::statusText() const { return d_->lastStatus; }
bool WorkbenchWindow::isBusy() const { return d_->busy(); }
bool WorkbenchWindow::shutdownComplete() const { return d_->disposed; }
void WorkbenchWindow::shutdown() {
    if (d_->closing) return;
    d_->closing = true; d_->setPlaying(false); d_->queue.clear(); d_->pendingBlenderOpen = false;
    if (d_->playDialog) d_->playDialog->reject();
    d_->status(t("Stopping Creator…", "Deteniendo Creador…")); d_->pump(); d_->notifyBusy();
}
void WorkbenchWindow::resizeEvent(QResizeEvent *event) {
    QMainWindow::resizeEvent(event);
    if (d_) d_->applyLayout();
}
void WorkbenchWindow::closeEvent(QCloseEvent *event) {
    if (d_->disposed) { event->accept(); return; }
    d_->closeWindow = true; shutdown(); event->ignore();
}
}
