#include "window.h"
#include "kit.h"
#include "graphics.h"
#include <QGuiApplication>
#include <QDateTime>
#include <QApplication>
#include <QCheckBox>
#include <QClipboard>
#include <QCloseEvent>
#include <QComboBox>
#include <QDesktopServices>
#include <QDir>
#include <QFileDialog>
#include <QFile>
#include <QFormLayout>
#include <QGroupBox>
#include <QHeaderView>
#include <QInputDialog>
#include <QLabel>
#include <QLineEdit>
#include <QMessageBox>
#include <QMenu>
#include <QPushButton>
#include <QPlainTextEdit>
#include <QScrollArea>
#include <QSlider>
#include <QStatusBar>
#include <QTableWidget>
#include <QStackedWidget>
#include <QTimer>
#include <QUrl>
#include <QVBoxLayout>
#include <functional>
#include <algorithm>

namespace launcher {
#ifdef Q_OS_LINUX
static QString osRelease() { QFile f("/etc/os-release"); return f.open(QIODevice::ReadOnly) ? QString::fromUtf8(f.read(16384)) : QString(); }
#endif
bool spanish = false;
QString t(const char *en, const char *es) { return QString::fromUtf8(spanish ? es : en); }
static QLabel *label(const QString &text) { auto *w = new QLabel(text); w->setWordWrap(true); w->setTextFormat(Qt::PlainText); return w; }
static QPushButton *button(QBoxLayout *layout, const QString &text, const std::function<void()> &action) {
    auto *w = new kit::Button(text); layout->addWidget(w); QObject::connect(w, &QPushButton::clicked, w, action); return w;
}
static QTableWidget *table(const QStringList &headers) {
    auto *w = new QTableWidget(0, headers.size()); w->setHorizontalHeaderLabels(headers);
    w->setSelectionBehavior(QAbstractItemView::SelectRows); w->setSelectionMode(QAbstractItemView::SingleSelection);
    w->setEditTriggers(QAbstractItemView::NoEditTriggers); w->verticalHeader()->hide();
    w->horizontalHeader()->setSectionResizeMode(QHeaderView::ResizeToContents);
    w->horizontalHeader()->setStretchLastSection(true); w->setAlternatingRowColors(true);
    return w;
}
Window::Window(QString app, QString user, Settings settings)
    : appDir_(std::move(app)), userDir_(std::move(user)), settings_(std::move(settings)) {
    setWindowTitle("GD's Melee"); resize(1160, 800); setMinimumSize(1000, 730);
    surface_ = new kit::Surface;
    auto *layout = new QVBoxLayout(surface_); layout->setContentsMargins(32, 24, 32, 24); layout->setSpacing(18);
    auto *header = new QHBoxLayout; layout->addLayout(header);
    auto *title = label("GD'S MELEE"); title->setProperty("role", "brand"); header->addWidget(title); header->addStretch();
    auto *edition = label(t("LAUNCHER", "LANZADOR")); edition->setProperty("role", "eyebrow"); header->addWidget(edition);
    auto *body = new QHBoxLayout; body->setSpacing(22); layout->addLayout(body, 1);
    auto *sidebar = new QVBoxLayout; sidebar->setSpacing(10); body->addLayout(sidebar);
    auto *navLabel = label(t("HOME", "INICIO")); navLabel->setProperty("role", "muted"); sidebar->addWidget(navLabel);
    tabs_ = new QStackedWidget;
    const QStringList labels{t("PLAY", "JUGAR"), t("MODS", "MODS"), t("DIAGNOSTICS", "DIAGNÓSTICO"), t("ABOUT", "ACERCA DE")};
    const QStringList icons{"melee", "collection", "options", "data"};
    const QStringList sections{"versus", "collection", "options", "data"};
    const QStringList headings{t("DISC LIBRARY", "BIBLIOTECA DE DISCOS"), t("YOUR CUSTOM CONTENT", "TU CONTENIDO PERSONALIZADO"), t("DIAGNOSTICS", "DIAGNÓSTICO"), t("GD'S MELEE", "GD'S MELEE")};
    for (int i = 0; i < labels.size(); ++i) {
        auto *nav = new kit::Button(labels[i]); nav->setFixedWidth(196); nav->setMinimumHeight(64); nav->setCheckable(true); nav->setKitIcon(icons[i]); nav->setSection(sections[i]); sidebar->addWidget(nav); navigation_.append(nav);
        connect(nav, &QPushButton::clicked, this, [this, i] { tabs_->setCurrentIndex(i); navigation_[i]->setChecked(true); });
    }
    sidebar->addStretch();
    auto *note = label(t("YOUR DISCS.\nYOUR RULES.", "TUS DISCOS.\nTUS REGLAS.")); note->setFont(kit::font(21, true, true)); sidebar->addWidget(note);
    auto *right = new QVBoxLayout; right->setSpacing(12); body->addLayout(right, 1);
    pageHeading_ = label(headings[0]); pageHeading_->setProperty("role", "heading"); right->addWidget(pageHeading_);
    tabs_->addWidget(playTab()); tabs_->addWidget(modsTab()); tabs_->addWidget(diagnosticsTab()); tabs_->addWidget(aboutTab()); right->addWidget(tabs_, 1);
    navigation_[0]->setChecked(true);
    connect(tabs_, &QStackedWidget::currentChanged, this, [this, headings, sections](int index) {
        for (int i = 0; i < navigation_.size(); ++i) navigation_[i]->setChecked(i == index);
        pageHeading_->setText(headings[index]); surface_->setSection(sections[index]);
    });
    setCentralWidget(surface_);
    refreshDiscs(); guarded([&] { refreshMods(); });
    statusBar()->showMessage(t("SELECT A DISC  /  Double-click to play", "ELIGE UN DISCO  /  Doble clic para jugar"));
#ifdef Q_OS_LINUX
    graphicsTimeout_ = new QTimer(this); graphicsTimeout_->setSingleShot(true);
    connect(graphicsTimeout_, &QTimer::timeout, this, [this] { graphicsTimedOut_ = true; graphicsProcess_.kill(); });
    connect(&graphicsProcess_, &QProcess::readyReadStandardOutput, this, [this] {
        graphicsOutput_ += graphicsProcess_.readAllStandardOutput();
        if (graphicsOutput_.size() > 1024 * 1024) { graphicsOutput_.truncate(1024 * 1024); graphicsProcess_.kill(); }
    });
    connect(&graphicsProcess_, &QProcess::readyReadStandardError, this, [this] {
        graphicsErrors_ += graphicsProcess_.readAllStandardError(); graphicsErrors_ = graphicsErrors_.right(64 * 1024);
    });
    connect(&graphicsProcess_, qOverload<int, QProcess::ExitStatus>(&QProcess::finished), this, [this](int code, QProcess::ExitStatus status) { finishGraphics(status == QProcess::NormalExit ? code : -1); });
    connect(&graphicsProcess_, &QProcess::errorOccurred, this, [this](QProcess::ProcessError error) { if (error == QProcess::FailedToStart) { graphicsErrors_ = graphicsProcess_.errorString().toUtf8(); finishGraphics(-1); } });
#endif
    connect(&process_, &QProcess::started, this, [this] { diag_.spawn.started = true; });
    connect(&process_, &QProcess::errorOccurred, this, [this](QProcess::ProcessError error) {
        if (error != QProcess::FailedToStart) return;
        auto &sp = diag_.spawn; sp.started = false; sp.processError = int(error); sp.errorString = process_.errorString(); sp.finished = false;
        QStringList env; for (const auto &k : diag_.spec.environment.keys()) env << k + "=" + diag_.spec.environment.value(k);
        sp.execProbe = execProbe(sp.program, env);
        play_->setEnabled(true); finishLaunchReport(true);
    });
    connect(&process_, qOverload<int, QProcess::ExitStatus>(&QProcess::finished), this, [this](int code, QProcess::ExitStatus status) {
        play_->setEnabled(true);
        auto &sp = diag_.spawn; sp.finished = true; sp.exitCode = code; sp.crashed = status == QProcess::CrashExit; sp.elapsedMs = launchClock_.elapsed();
        // Qt 6 reports the terminating signal number as exitCode() for a CrashExit on Unix (checked on 6.8).
        sp.signal = sp.crashed && code >= 1 && code <= 64 ? signalName(code) : QString();
        auto crash = latestCrash(runDir_);
        const bool failed = status == QProcess::CrashExit || code != 0 || !crash.isEmpty();
        finishLaunchReport(failed);
        if (!failed) { if (quitting_ || settings_.flag("close_on_play")) QApplication::quit(); else statusBar()->showMessage(t("Game closed.", "Juego cerrado.")); }
    });
}
DiagContext Window::diagContext(bool full) const {
    DiagContext c = diag_; c.appDir = appDir_; c.userDir = userDir_; c.runDir = runDir_; c.full = full;
    c.platform = QGuiApplication::platformName(); c.launcherExe = QCoreApplication::applicationFilePath();
    c.graphicsDevice = settings_.option("graphics_device", "auto");
    c.discPaths.clear(); for (const auto &d : settings_.discs) c.discPaths << d.path;
    return c;
}
void Window::finishLaunchReport(bool showDialog) {
    // The slow probes (lspci, vulkaninfo) only run for a failure; a clean exit keeps the quick report.
    auto ctx = diagContext(showDialog); ctx.finished = true;
    auto report = writeDiagnostics(ctx);
    if (!showDialog) return;
    show(); quitting_ = false;
    QString extra;
#ifdef Q_OS_LINUX
    extra = graphicsStartupFailure(runDir_, osRelease());
#endif
    showLaunchFailure(report, extra);
}
void Window::showLaunchFailure(const DiagResult &report, const QString &extra) {
    const auto &v = report.verdict;
    QString text = t("The game could not start or stopped unexpectedly.", "The game could not start or stopped unexpectedly.") + "\n\n" + v.line() + "\n" + v.message;
    if (!v.hint.isEmpty()) text += "\n\n" + t("Hint: ", "Hint: ") + v.hint;
    text += "\n\n" + t("A diagnostics report was saved. Copy it and send it when asking for help.", "A diagnostics report was saved. Copy it and send it when asking for help.");
    QMessageBox dialog(QMessageBox::Warning, t("Game stopped", "El juego se ha detenido"), text, QMessageBox::NoButton, this);
    dialog.setTextFormat(Qt::PlainText);
    dialog.setDetailedText(t("Report: ", "Report: ") + report.latestPath + "\n" + t("Logs are available here:\n", "Registros disponibles aquí:\n") + runDir_ + (extra.isEmpty() ? QString() : "\n\n" + extra));
    auto *copy = dialog.addButton(t("Copy diagnostics", "Copy diagnostics"), QMessageBox::ActionRole);
    auto *open = dialog.addButton(t("Open log folder", "Abrir carpeta de registros"), QMessageBox::ActionRole);
    dialog.addButton(QMessageBox::Ok);
    for (;;) {
        dialog.exec();
        if (dialog.clickedButton() == copy) { QApplication::clipboard()->setText(report.text); statusBar()->showMessage(t("Launch diagnostics copied.", "Launch diagnostics copied.")); }
        else if (dialog.clickedButton() == open) openPath(diagnosticsDir(userDir_));
        else break;
    }
}
void Window::runDiagnosticsOnly() { guarded([&] {
    DiagContext c = diagContext(true); c.spawn = {}; c.haveSpec = false; c.finished = true; c.runDir.clear();
    statusBar()->showMessage(t("Running diagnostics...", "Running diagnostics...")); QApplication::setOverrideCursor(Qt::WaitCursor);
    auto report = writeDiagnostics(c); QApplication::restoreOverrideCursor();
    showLaunchFailure(report);
}); }
void Window::copyDiagnostics() { guarded([&] {
    auto path = diagnosticsDir(userDir_) + "/launch-diagnostics.txt";
    if (!QFile::exists(path)) { statusBar()->showMessage(t("No launch diagnostics yet. Start the game or run diagnostics first.", "No launch diagnostics yet. Start the game or run diagnostics first.")); return; }
    QApplication::clipboard()->setText(readText(path, 4 * 1024 * 1024)); statusBar()->showMessage(t("Launch diagnostics copied.", "Launch diagnostics copied."));
}); }
void Window::guarded(const std::function<void()> &action) {
    try { action(); } catch (const std::exception &e) { QMessageBox::warning(this, t("Could not complete the action", "No se pudo completar la acción"), QString::fromUtf8(e.what())); }
}
void Window::save() { settings_.save(userDir_); }
void Window::openPath(const QString &path) {
    if (!QDesktopServices::openUrl(QUrl::fromLocalFile(path))) QMessageBox::warning(this, t("Open folder or file", "Abrir carpeta o archivo"), path);
}
int Window::selectedDisc() const { int row = discs_->currentRow(); return row >= 0 && row < settings_.discs.size() ? row : -1; }
void Window::refreshDiscs(const QString &id) {
    discs_->setRowCount(settings_.discs.size());
    int selected = settings_.defaultIndex();
    for (int row = 0; row < settings_.discs.size(); ++row) {
        const auto &d = settings_.discs[row];
        QStringList values{(d.id == settings_.defaultId ? "★ " : "") + d.name, d.kind, d.path};
        for (int col = 0; col < values.size(); ++col) { auto *item = new QTableWidgetItem(values[col]); item->setToolTip(values[col]); discs_->setItem(row, col, item); }
        discs_->item(row, 0)->setData(Qt::UserRole, QFileInfo(d.path).fileName());
        discs_->setRowHeight(row, 96);
        if (d.id == id) selected = row;
    }
    if (selected >= 0) discs_->selectRow(selected);
    if (settings_.discs.isEmpty()) discDetails_->setText(t("Add your own Melee NTSC-U 1.02 ISO, Akaneia, or ACE disc image. No game data is included.", "Añade tu propia ISO de Melee NTSC-U 1.02, Akaneia o ACE. No se incluyen datos del juego."));
}
QWidget *Window::playTab() {
    auto *page = new QWidget; auto *layout = new QHBoxLayout(page); layout->setContentsMargins(0, 0, 0, 0); layout->setSpacing(18);
    auto *library = new QWidget; library->setObjectName("contentPanel"); auto *left = new QVBoxLayout(library); left->setContentsMargins(16, 18, 16, 16); left->setSpacing(10); layout->addWidget(library, 5);
    auto *owned = label(t("AVAILABLE DISCS", "DISCOS DISPONIBLES")); owned->setProperty("role", "eyebrow"); left->addWidget(owned);
    discs_ = table({"Disc", "Kind", "Path"}); discs_->setItemDelegate(new kit::DiscDelegate(discs_));
    discs_->horizontalHeader()->hide(); discs_->setColumnHidden(1, true); discs_->setColumnHidden(2, true);
    discs_->horizontalHeader()->setSectionResizeMode(0, QHeaderView::Stretch); discs_->setShowGrid(false); discs_->setAlternatingRowColors(false);
    left->addWidget(discs_, 1);
    discDetails_ = label(t("Each disc has its own saves. Add your vanilla, Akaneia or ACE ISO to get started.", "Cada disco tiene sus propias partidas guardadas. Añade tu ISO de Melee, Akaneia o ACE.")); discDetails_->setProperty("role", "muted"); left->addWidget(discDetails_);
    auto *actions = new QHBoxLayout; left->addLayout(actions);
    button(actions, t("+ ADD DISC", "+ AÑADIR"), [this] { addDisc(); });
    auto *manage = new kit::Button(t("MANAGE…", "GESTIONAR…")); actions->addWidget(manage);
    auto *menu = new QMenu(manage);
    auto menuAction = [&](const QString &title, const std::function<void()> &fn) { auto *a = menu->addAction(title); connect(a, &QAction::triggered, this, [this, fn] { guarded(fn); }); };
    menuAction(t("Change ISO…", "Cambiar ISO…"), [this] {
        int i = selectedDisc(); if (i < 0) return;
        auto path = QFileDialog::getOpenFileName(this, t("Change ISO", "Cambiar ISO"), {}, "Disc images (*.iso *.gcm);;All files (*)"); if (path.isEmpty()) return;
        auto info = probeDisc(path);
        if (info.verdict == DiscInfo::Bad) throw std::runtime_error(info.message.toUtf8().constData());
        if (info.verdict == DiscInfo::Warn && QMessageBox::warning(this, t("Modified disc", "Disco modificado"), info.message, QMessageBox::Ok | QMessageBox::Cancel) != QMessageBox::Ok) return;
        auto &d = settings_.discs[i]; d.path = path; d.kind = info.kind; save(); refreshDiscs(d.id);
    });
    menuAction(t("Rename…", "Renombrar…"), [this] {
        int i = selectedDisc(); if (i < 0) return; bool ok;
        auto name = QInputDialog::getText(this, t("Rename disc", "Renombrar disco"), t("Name", "Nombre"), QLineEdit::Normal, settings_.discs[i].name, &ok).trimmed();
        if (ok && !name.isEmpty()) { settings_.discs[i].name = name; save(); refreshDiscs(settings_.discs[i].id); }
    });
    menuAction(t("Make default", "Usar por defecto"), [this] { int i = selectedDisc(); if (i >= 0) { settings_.defaultId = settings_.discs[i].id; save(); refreshDiscs(settings_.defaultId); } });
    menuAction(t("Open saves", "Abrir partidas guardadas"), [this] { int i = selectedDisc(); if (i >= 0) { auto p = userDir_ + "/saves/" + settings_.discs[i].id; QDir().mkpath(p); openPath(p); } });
    menu->addSeparator();
    menuAction(t("Forget disc…", "Olvidar disco…"), [this] {
        int i = selectedDisc(); if (i < 0) return;
        if (QMessageBox::question(this, t("Forget disc?", "¿Olvidar disco?"), t("Remove this disc from the list? Its ISO and saves will be kept.", "¿Quitar este disco de la lista? Se conservan la ISO y las partidas guardadas.")) != QMessageBox::Yes) return;
        settings_.discs.removeAt(i); if (settings_.defaultIndex() >= 0) settings_.defaultId = settings_.discs[settings_.defaultIndex()].id; else settings_.defaultId.clear(); save(); refreshDiscs();
    });
    connect(manage, &QPushButton::clicked, this, [manage, menu] { menu->exec(manage->mapToGlobal(QPoint(0, manage->height()))); });
    auto *launch = new QWidget; launch->setObjectName("contentPanel"); auto *right = new QVBoxLayout(launch); right->setContentsMargins(0, 0, 0, 14); right->setSpacing(0); layout->addWidget(launch, 4);
    hero_ = new kit::Hero; right->addWidget(hero_);
    auto *details = new QVBoxLayout; details->setContentsMargins(20, 16, 20, 0); details->setSpacing(6); right->addLayout(details);
    auto *ready = label(t("READY WHEN YOU ARE", "LISTO CUANDO QUIERAS")); ready->setProperty("role", "eyebrow"); details->addWidget(ready);
    discTitle_ = label(t("Choose your disc", "Elige tu disco")); discTitle_->setFont(kit::font(25, true)); details->addWidget(discTitle_);
    auto *controller = label(t("Controller connected? Let's play.", "¿Mando conectado? A jugar.")); controller->setProperty("role", "muted"); details->addWidget(controller);
    details->addSpacing(8);
    for (const auto &item : QList<QPair<QString, QString>>{{"unlock_all", t("Unlock everything", "Desbloquear todo")}, {"skip_intro", t("Skip intro", "Saltar introducción")}, {"close_on_play", t("Close launcher on play", "Cerrar lanzador al jugar")}}) {
        auto *check = new QCheckBox(item.second); check->setChecked(settings_.flag(item.first, item.first != "close_on_play")); details->addWidget(check);
        connect(check, &QCheckBox::toggled, this, [this, key = item.first](bool on) { guarded([&] { settings_.options[key] = on ? "1" : "0"; save(); }); });
    }
    details->addStretch();
    auto *audio = new QHBoxLayout; details->addLayout(audio); auto *volLabel = label(t("VOLUME", "VOLUMEN")); volLabel->setProperty("role", "muted"); audio->addWidget(volLabel);
    auto *volume = new QSlider(Qt::Horizontal); volume->setRange(0, 100); volume->setValue(settings_.option("volume", "50").toInt()); audio->addWidget(volume);
    auto *amount = label(QString::number(volume->value()) + "%"); amount->setFixedWidth(42); audio->addWidget(amount);
    connect(volume, &QSlider::valueChanged, this, [this, amount](int value) { amount->setText(QString::number(value) + "%"); guarded([&] { settings_.options["volume"] = QString::number(value); save(); }); });
    auto *play = new kit::Button(t("PLAY  →", "JUGAR  →")); play->setPrimary(true); play->setMinimumHeight(66); play->setDefault(true); details->addWidget(play); play_ = play;
    connect(play_, &QPushButton::clicked, this, [this] { this->play(); });
    connect(discs_, &QTableWidget::itemSelectionChanged, this, [this] {
        int i = selectedDisc(); if (i < 0) return;
        const auto &d = settings_.discs[i]; hero_->setDisc(d.kind); discTitle_->setText(d.name);
        discDetails_->setText(t("Saves stay with this disc, even when you rename it or change its ISO.", "Las partidas guardadas siguen con este disco aunque lo renombres o cambies su ISO."));
    });
    connect(discs_, &QTableWidget::cellDoubleClicked, this, [this] { this->play(); });
    return page;
}
void Window::addDisc(const QString &given) { guarded([&] {
    auto path = given.isEmpty() ? QFileDialog::getOpenFileName(this, t("Add disc", "Añadir disco"), {}, "Disc images (*.iso *.gcm);;All files (*)") : given;
    if (path.isEmpty()) return; path = QFileInfo(path).absoluteFilePath();
    for (const auto &d : settings_.discs) if (QFileInfo(d.path).canonicalFilePath() == QFileInfo(path).canonicalFilePath()) { refreshDiscs(d.id); return; }
    auto info = probeDisc(path);
    if (info.verdict == DiscInfo::Bad) throw std::runtime_error(info.message.toUtf8().constData());
    if (info.verdict == DiscInfo::Warn && QMessageBox::warning(this, t("Modified disc", "Disco modificado"), info.message, QMessageBox::Ok | QMessageBox::Cancel) != QMessageBox::Ok) return;
    Disc d{settings_.newId(info.kind), info.kind, info.kind, path}; settings_.discs.append(d); settings_.defaultId = d.id; save(); refreshDiscs(d.id);
}); }
void Window::play() { guarded([&] {
    if (process_.state() != QProcess::NotRunning) return;
#ifdef Q_OS_LINUX
    if (graphicsBusy_) return;
#endif
    int i = selectedDisc(); if (i < 0) { addDisc(); return; }
    LaunchSpec spec;
    try { spec = prepareLaunch(appDir_, userDir_, settings_, settings_.discs[i]); }
    catch (const std::exception &e) {
        diag_ = {}; diag_.prepareError = QString::fromUtf8(e.what()); runDir_.clear();
        auto ctx = diagContext(true); ctx.finished = true; ctx.discPaths << settings_.discs[i].path;
        showLaunchFailure(writeDiagnostics(ctx)); return;
    }
    save();
#ifdef Q_OS_LINUX
    pendingLaunch_ = spec; checkGraphics(true);
#else
    startGame(spec);
#endif
}); }
void Window::startGame(const LaunchSpec &spec) {
    runDir_ = spec.workingDirectory;
    settings_.options["last_run"] = runDir_; save();
    process_.setProgram(spec.program); process_.setArguments(spec.arguments); process_.setWorkingDirectory(spec.workingDirectory); process_.setProcessEnvironment(spec.environment);
    launcher::captureRedacted(process_, spec.logFile, launcher::redactorForLaunch(spec.arguments));
    play_->setEnabled(false); statusBar()->showMessage(t("Game running. Logs: ", "Juego en ejecución. Registros: ") + runDir_);
    diag_ = {}; diag_.spec = spec; diag_.haveSpec = true; diag_.stamp = QDateTime::currentDateTime().toString("yyyyMMdd-HHmmss");
    auto &sp = diag_.spawn; sp.attempted = true; sp.program = spec.program; sp.arguments = spec.arguments; sp.workingDirectory = spec.workingDirectory; sp.stdoutFile = spec.logFile;
    launchClock_.start();
    process_.start();
    // A report exists from the moment the game starts, so a hang or a killed launcher still leaves one.
    if (sp.started) { auto ctx = diagContext(false); writeDiagnostics(ctx); }
    if (settings_.flag("close_on_play")) hide();
}
#ifdef Q_OS_LINUX
void Window::checkGraphics(bool forLaunch) { guarded([&] {
    if (graphicsBusy_ || process_.state() != QProcess::NotRunning) return;
    auto env = forLaunch ? pendingLaunch_.environment : QProcessEnvironment::systemEnvironment();
    // A launch environment is already the game's own; otherwise build it the same way prepareLaunch does.
    if (!forLaunch) applyGameLibraryEnvironment(env, appDir_);
    graphicsBusy_ = true; graphicsForLaunch_ = forLaunch; graphicsTimedOut_ = false;
    graphicsOutput_.clear(); graphicsErrors_.clear(); play_->setEnabled(false); graphicsDevice_->setEnabled(false);
    graphicsDetails_->setPlainText(t("Checking 32-bit Vulkan drivers...", "Comprobando los controladores Vulkan de 32 bits..."));
    statusBar()->showMessage(t("Checking graphics...", "Comprobando gráficos..."));
    graphicsProcess_.setProgram(appDir_ + "/bin/melee-graphics-probe");
    graphicsProcess_.setWorkingDirectory(appDir_); graphicsProcess_.setProcessEnvironment(env);
    graphicsProcess_.start(); graphicsTimeout_->start(15000);
}); }
void Window::finishGraphics(int code) {
    if (!graphicsBusy_) return;
    graphicsTimeout_->stop(); graphicsBusy_ = false; play_->setEnabled(true); graphicsDevice_->setEnabled(true);
    guarded([&] {
        auto report = parseGraphicsReport(graphicsOutput_, code);
        if (graphicsTimedOut_) report.error = "The 32-bit graphics check timed out.";
        else if (code == -1) report.error = "The 32-bit graphics helper could not run or crashed. " + QString::fromUtf8(graphicsErrors_).left(2048);
        const auto selection = settings_.option("graphics_device", "auto");
        bool selected = report.matchesSelection(selection);
        QString text = report.summary();
        if (graphicsForLaunch_ && report.ready() && !selected) text += "\nThe installed device-selection controls did not isolate the selected GPU. Choose Automatic or update the driver's selection layer.";
        if (!report.ready() || (graphicsForLaunch_ && !selected)) text += "\n\n" + graphicsDriverHelp(osRelease());
        graphicsDetails_->setPlainText(text);
        auto log = graphicsForLaunch_ ? pendingLaunch_.workingDirectory + "/graphics-preflight.log" : userDir_ + "/graphics-preflight.log";
        writeAtomic(log, (text + "\n\nSelected GPU: " + selection + "\nOS:\n" + osRelease() + "\nProbe stdout:\n" + QString::fromUtf8(graphicsOutput_) + "\nProbe stderr:\n" + QString::fromUtf8(graphicsErrors_)).toUtf8());
        if (!graphicsForLaunch_) {
            graphicsDevice_->blockSignals(true); graphicsDevice_->clear();
            graphicsDevice_->addItem(t("Automatic", "Automático"), "auto");
            for (const auto &d : report.devices) if (d.usable && (d.vendor == 0x1002 || d.vendor == 0x8086 || d.vendor == 0x10de) && graphicsDevice_->findData(d.selector()) < 0) graphicsDevice_->addItem(d.name + " (" + d.selector() + ")", d.selector());
            if (graphicsDevice_->findData(selection) < 0) graphicsDevice_->addItem(selection + t(" (saved; unavailable)", " (guardada; no disponible)"), selection);
            graphicsDevice_->setCurrentIndex(graphicsDevice_->findData(selection)); graphicsDevice_->blockSignals(false);
            statusBar()->showMessage(report.ready() ? t("32-bit Vulkan check passed.", "Comprobación de Vulkan de 32 bits correcta.") : t("Graphics check needs attention. See Diagnostics.", "La comprobación requiere atención. Consulta Diagnóstico."));
            return;
        }
        if (!selected) {
            QMessageBox dialog(QMessageBox::Warning, t("Graphics check", "Comprobación de gráficos"), text, QMessageBox::Cancel, this);
            dialog.setTextFormat(Qt::PlainText); dialog.setDetailedText("Preflight log: " + log);
            auto *attempt = dialog.addButton(t("Try game anyway", "Intentar iniciar de todos modos"), QMessageBox::AcceptRole);
            dialog.exec(); if (dialog.clickedButton() != attempt) return;
        }
        startGame(pendingLaunch_);
    });
}
#endif
void Window::refreshMods() {
    auto entries = installedMods(modsDir(appDir_, userDir_)); filling_ = true;
    mods_->setRowCount(entries.size());
    for (int row = 0; row < entries.size(); ++row) {
        const auto &m = entries[row]; auto *check = new QTableWidgetItem(m.id); check->setCheckState(m.enabled ? Qt::Checked : Qt::Unchecked);
        check->setData(Qt::UserRole, m.description + "\n" + t("Requires: ", "Requiere: ") + m.requires.join(", ") + "\n" + t("Conflicts: ", "Conflictos: ") + m.conflicts.join(", "));
        mods_->setItem(row, 0, check); mods_->setItem(row, 1, new QTableWidgetItem(m.name)); mods_->setItem(row, 2, new QTableWidgetItem(m.version));
    }
    filling_ = false;
}
QWidget *Window::modsTab() {
    auto *page = new QWidget; auto *layout = new QVBoxLayout(page);
    layout->addWidget(label(t("Place each local mod in its own folder inside Mods. Changes take effect at the next game launch.", "Coloca cada mod local en su propia carpeta dentro de Mods. Los cambios se aplican al volver a iniciar el juego.")));
    mods_ = table({t("Enabled / ID", "Activado / ID"), t("Name", "Nombre"), t("Version", "Versión")}); layout->addWidget(mods_);
    modDetails_ = label(""); layout->addWidget(modDetails_);
    connect(mods_, &QTableWidget::itemChanged, this, [this](QTableWidgetItem *item) { if (!filling_ && item->column() == 0) {
        guarded([&] { setModEnabled(modsDir(appDir_, userDir_), item->text(), item->checkState() == Qt::Checked); }); guarded([&] { refreshMods(); });
    } });
    connect(mods_, &QTableWidget::itemSelectionChanged, this, [this] { auto *i = mods_->item(mods_->currentRow(), 0); if (i) modDetails_->setText(i->data(Qt::UserRole).toString()); });
    auto *row = new QHBoxLayout; layout->addLayout(row);
    button(row, t("Open mods folder", "Abrir carpeta de mods"), [this] { auto p = modsDir(appDir_, userDir_); QDir().mkpath(p); openPath(p); });
    button(row, t("Open scripts folder", "Abrir carpeta de scripts"), [this] { auto p = QDir(appDir_ + "/scripts").exists() ? appDir_ + "/scripts" : userDir_ + "/scripts"; QDir().mkpath(p); openPath(p); });
    button(row, t("Refresh", "Actualizar"), [this] { guarded([&] { refreshMods(); }); });
    button(row, t("Remove…", "Quitar…"), [this] { guarded([&] {
        auto *item = mods_->item(mods_->currentRow(), 0); if (!item) return;
        if (QMessageBox::question(this, t("Remove mod?", "¿Quitar mod?"), t("Move this mod into Mods/.removed? You can restore it from that folder.", "¿Mover este mod a Mods/.removed? Puedes restaurarlo desde esa carpeta.")) != QMessageBox::Yes) return;
        removeMod(modsDir(appDir_, userDir_), item->text()); refreshMods();
    }); });
    return page;
}
QWidget *Window::diagnosticsTab() {
    auto *scroll = new QScrollArea; scroll->setWidgetResizable(true); auto *page = new QWidget; auto *layout = new QVBoxLayout(page); scroll->setWidget(page);
#ifdef Q_OS_LINUX
    auto *graphics = new QGroupBox(t("Linux graphics", "Gráficos de Linux")); auto *graphicsLayout = new QVBoxLayout(graphics); layout->addWidget(graphics);
    auto *gpuForm = new QFormLayout; graphicsLayout->addLayout(gpuForm); graphicsDevice_ = new QComboBox;
    graphicsDevice_->addItem(t("Automatic", "Automático"), "auto");
    auto savedGpu = settings_.option("graphics_device", "auto");
    if (savedGpu != "auto") { graphicsDevice_->addItem(savedGpu + t(" (saved; check graphics)", " (guardada; comprobar gráficos)"), savedGpu); graphicsDevice_->setCurrentIndex(1); }
    gpuForm->addRow(t("Game GPU", "GPU del juego"), graphicsDevice_);
    connect(graphicsDevice_, qOverload<int>(&QComboBox::currentIndexChanged), this, [this] { guarded([&] { settings_.options["graphics_device"] = graphicsDevice_->currentData().toString(); save(); }); });
    graphicsDetails_ = new QPlainTextEdit; graphicsDetails_->setReadOnly(true); graphicsDetails_->setMinimumHeight(120); graphicsDetails_->setMaximumHeight(180);
    graphicsDetails_->setPlainText(t("Check graphics to list GPUs available to the 32-bit game. Play checks the selected GPU before starting.", "Comprueba los gráficos para ver las GPU disponibles para el juego de 32 bits. Jugar comprueba la GPU seleccionada antes de iniciar.")); graphicsLayout->addWidget(graphicsDetails_);
    auto *graphicsRow = new QHBoxLayout; graphicsLayout->addLayout(graphicsRow);
    button(graphicsRow, t("Check graphics", "Comprobar gráficos"), [this] { checkGraphics(false); });
    button(graphicsRow, t("Driver help", "Ayuda de controladores"), [this] {
        QMessageBox dialog(QMessageBox::Information, t("32-bit graphics drivers", "Controladores gráficos de 32 bits"), graphicsDriverHelp(osRelease()), QMessageBox::Ok, this); dialog.setTextFormat(Qt::PlainText); dialog.exec();
    });
#endif
    auto check = [&](const QString &title, const QString &key, bool fallback) {
        auto *w = new QCheckBox(title); w->setChecked(settings_.flag(key, fallback)); layout->addWidget(w);
        connect(w, &QCheckBox::toggled, this, [this, key](bool v) { guarded([&] { settings_.options[key] = v ? "1" : "0"; save(); }); });
    };
    check(t("Log everything (large logs)", "Registrar todo (registros grandes)"), "log_all", false);
    check(t("Log scene changes", "Registrar cambios de escena"), "log_scene", true);
    auto *form = new QFormLayout; layout->addLayout(form);
    auto combo = [&](const QString &title, const QString &key, const QStringList &choices, int offset, int fallback) {
        auto *w = new QComboBox; w->addItems(choices); w->setCurrentIndex(std::clamp(settings_.option(key, QString::number(fallback)).toInt() - offset, 0, int(choices.size()) - 1)); form->addRow(title, w);
        connect(w, qOverload<int>(&QComboBox::currentIndexChanged), this, [this, key, offset](int v) { guarded([&] { settings_.options[key] = QString::number(v + offset); save(); }); });
    };
    combo(t("Render diagnostics", "Diagnóstico gráfico"), "log_render", {t("Off", "Desactivado"), t("Once per scene", "Una vez por escena"), t("Every block", "Cada bloque")}, -1, 0);
    combo(t("Controller diagnostics", "Diagnóstico de mandos"), "pad_diag", {t("Game default", "Por defecto"), "0", "1", "2"}, -1, -1);
    combo(t("Release adapter on focus loss", "Liberar adaptador al perder el foco"), "pad_release_on_blur", {t("Game default", "Por defecto"), t("Off", "Desactivado"), t("On", "Activado")}, -1, -1);
    const QList<QPair<QString, QString>> categories = {{"watchdog", t("Watchdog samples", "Muestras de ejecución")}, {"mex", t("m-ex internals", "Internos de m-ex")}, {"heap", t("Memory allocations", "Asignaciones de memoria")}, {"dvd", t("Disc file trace", "Accesos a archivos del disco")}, {"tex", t("UI texture loads", "Carga de texturas de la interfaz")}, {"frontend", t("Menu layouts", "Diseños de menús")}, {"audio", t("Sound bank loads", "Carga de bancos de sonido")}};
    const QList<QPair<QString, QString>> traces = {{"gr", t("Stage code trace", "Traza del código de escenarios")}, {"mexcalls", t("m-ex engine calls", "Llamadas de m-ex al motor")}, {"card", t("Memory card diagnostics", "Diagnóstico de tarjetas de memoria")}, {"profile", t("Frame timing", "Tiempos de fotogramas")}, {"fps", t("Show frame rate", "Mostrar fotogramas por segundo")}, {"aurora", t("Renderer log", "Registro gráfico")}, {"osreport", t("Report format trace", "Traza de formatos de informes")}};
    for (const auto &group : {qMakePair(QString("log_categories"), categories), qMakePair(QString("traces"), traces)}) {
        auto *box = new QGroupBox(group.first == "traces" ? t("Traces", "Trazas") : t("Log categories", "Categorías del registro")); auto *grid = new QGridLayout(box); layout->addWidget(box); int n = 0;
        for (const auto &entry : group.second) {
            auto *w = new QCheckBox(entry.second); w->setChecked(settings_.option(group.first).split(',').contains(entry.first)); grid->addWidget(w, n / 2, n % 2); ++n;
            connect(w, &QCheckBox::toggled, this, [this, key = group.first, value = entry.first](bool on) { guarded([&] { auto list = settings_.option(key).split(',', Qt::SkipEmptyParts); list.removeAll(value); if (on) list << value; settings_.options[key] = list.join(','); save(); }); });
        }
    }
    auto *row = new QHBoxLayout; layout->addLayout(row);
    auto lastRun = [this] { return runDir_.isEmpty() ? settings_.option("last_run", userDir_ + "/runs") : runDir_; };
    button(row, t("Open log folder", "Abrir carpeta de registros"), [this, lastRun] { openPath(lastRun()); });
    button(row, t("Open game log", "Abrir registro del juego"), [this, lastRun] { openPath(lastRun() + "/melee-pc.log"); });
    button(row, t("Copy launch diagnostics", "Copy launch diagnostics"), [this] { copyDiagnostics(); });
    button(row, t("Run diagnostics without launching", "Run diagnostics without launching"), [this] { runDiagnosticsOnly(); });
    button(row, t("Copy latest crash report", "Copiar último informe de fallo"), [this, lastRun] { guarded([&] {
        auto report = latestCrash(lastRun()); if (report.isEmpty()) { statusBar()->showMessage(t("No crash report in the last session.", "No hay informe de fallo en la última sesión.")); return; }
        QApplication::clipboard()->setText(readText(report, 64 * 1024)); statusBar()->showMessage(t("Crash report copied.", "Informe de fallo copiado."));
    }); });
    layout->addStretch(); return scroll;
}
QWidget *Window::aboutTab() {
    auto *page = new QWidget; auto *layout = new QVBoxLayout(page); QString version = t("development build", "versión de desarrollo");
    try { version = readText(appDir_ + "/version.txt", 16384).section('\n', 0, 0); } catch (...) {}
    layout->addWidget(label("GD's Melee — " + version + "\nQt " + qVersion()));
    layout->addWidget(label(t("Bring your own disc image. Game data is never bundled with the launcher.", "Usa tu propia imagen de disco. El lanzador no incluye datos del juego.")));
    layout->addWidget(label(t("Game folder: ", "Carpeta del juego: ") + appDir_ + "\n" + t("User data: ", "Datos del usuario: ") + userDir_));
    auto *form = new QFormLayout; layout->addLayout(form); auto *lang = new QComboBox;
    lang->addItem(t("System language", "Idioma del sistema"), "auto"); lang->addItem("English", "en"); lang->addItem("Español", "es");
    lang->setCurrentIndex(std::max(0, lang->findData(settings_.option("language", "auto")))); form->addRow(t("Language (next launch)", "Idioma (al reiniciar)"), lang);
    connect(lang, qOverload<int>(&QComboBox::currentIndexChanged), this, [this, lang] { guarded([&] { settings_.options["language"] = lang->currentData().toString(); save(); }); });
    auto *row = new QHBoxLayout; layout->addLayout(row);
    button(row, t("Open user data", "Abrir datos del usuario"), [this] { openPath(userDir_); });
    button(row, t("Open licences", "Abrir licencias"), [this] { openPath(QDir(appDir_ + "/LICENSES").exists() ? appDir_ + "/LICENSES" : appDir_ + "/licenses"); });
    layout->addStretch(); return page;
}
void Window::selectMods() { tabs_->setCurrentIndex(1); }
void Window::screenshots(const QString &dir) {
    QDir().mkpath(dir); show();
    for (int i = 0; i < tabs_->count(); ++i) { tabs_->setCurrentIndex(i); QApplication::processEvents(); if (!grab().save(dir + "/launcher-" + QString::number(i) + ".png")) throw std::runtime_error("Cannot save screenshot"); }
}
void Window::closeEvent(QCloseEvent *event) {
    if (process_.state() != QProcess::NotRunning) { quitting_ = true; hide(); event->ignore(); }
    else { event->accept(); QApplication::quit(); }
}
}
