#include "hub_panel.h"
#include "atlas_widgets.h"
#include "kit.h"
#include "window.h"
#include <QCheckBox>
#include <QHBoxLayout>
#include <QLabel>
#include <QSignalBlocker>
#include <QVBoxLayout>

namespace wb {
using launcher::t;
namespace kit = launcher::kit;
namespace atlas = launcher::atlas;
namespace {
QLabel *label(const QString &text, atlas::Role role = atlas::Role::Cap14, const char *tone = "muted") {
    auto *value = kit::capLabel(text, role, tone); value->setTextFormat(Qt::PlainText); return value;
}
}
HubPanel::HubPanel(QWidget *parent) : QWidget(parent), layout_(new QVBoxLayout(this)) {
    setObjectName("wbHub"); setFocusPolicy(Qt::StrongFocus);
    layout_->setContentsMargins(0, 0, 0, 0); layout_->setSpacing(0);
    auto *bar = new QWidget; bar->setObjectName("wbTopBar"); bar->setMinimumHeight(60);
    auto *top = new QHBoxLayout(bar); top->setContentsMargins(16, 8, 16, 10); top->setSpacing(12);
    top->addWidget(label(t("Geno Workbench", "Geno Workbench"), atlas::Role::Cap16, "ivory"));
    top->addWidget(label(t("/", "/")));
    project_ = label(t("Fighter project", "Proyecto del luchador")); project_->setObjectName("wbProjectName");
    project_->setMaximumWidth(160); top->addWidget(project_); top->addWidget(label(t("/", "/")));
    move_ = label({}, atlas::Role::Cap16, "ember"); move_->setMaximumWidth(130); top->addWidget(move_);
    top->addStretch();
    engine_ = label({}, atlas::Role::Cap14, "jade"); engine_->setObjectName("wbEngineStatus"); top->addWidget(engine_);
    blenderState_ = label({}, atlas::Role::Cap14, "muted"); blenderState_->setObjectName("wbBlenderState"); top->addWidget(blenderState_);
    pending_ = label({}, atlas::Role::Cap14, "sun"); pending_->setObjectName("wbUnsaved"); top->addWidget(pending_);
    undo_ = new AtlasButton(t("Undo", "Deshacer")); undo_->setObjectName("wbUndo"); top->addWidget(undo_);
    playLab_ = new AtlasButton(t("Play in LAB", "Jugar en LAB")); playLab_->setObjectName("wbPlayLab"); top->addWidget(playLab_);
    playCpu_ = new AtlasButton(t("VS vs CPU", "VS contra CPU")); playCpu_->setObjectName("wbPlayCpu"); top->addWidget(playCpu_);
    auto *rebuild = new AtlasButton(t("Rebuild + reload", "Reconstruir + recargar")); rebuild->setTone(AtlasButton::Ember);
    rebuild_ = rebuild; rebuild_->setObjectName("wbRebuild"); top->addWidget(rebuild_);
    layout_->addWidget(bar);

    // These existing controls live in Render; they no longer consume the centre.
    controls_ = new QWidget(this); auto *controls = new QVBoxLayout(controls_);
    controls->setContentsMargins(0, 0, 0, 0);
    auto *buttons = new QHBoxLayout; controls->addLayout(buttons);
    start_ = new AtlasButton(t("Start", "Iniciar")); start_->setObjectName("wbStart"); buttons->addWidget(start_);
    stop_ = new AtlasButton(t("Stop", "Detener")); stop_->setObjectName("wbStop"); buttons->addWidget(stop_);
    restart_ = new AtlasButton(t("Restart engine", "Reiniciar motor")); restart_->setObjectName("wbRestart"); controls->addWidget(restart_);
    headless_ = new QCheckBox(t("Headless engine (no window)", "Motor sin ventana"));
    headless_->setObjectName("wbHeadless"); headless_->setChecked(true); controls->addWidget(headless_);
    blender_ = new AtlasButton(t("Open in Blender", "Abrir en Blender")); blender_->setObjectName("openInBlender"); controls->addWidget(blender_);
    counts_ = label({}, atlas::Role::Body12); counts_->setObjectName("wbProjectCounts"); counts_->setWordWrap(true);

    auto *blenderPlate = new AtlasPlate(this); blenderPlate->setElevated(true);
    blenderCard_ = blenderPlate; blenderCard_->setObjectName("wbBlenderCard");
    auto *card = new QHBoxLayout(blenderCard_); card->setContentsMargins(12, 10, 12, 12); card->setSpacing(10);
    auto *text = new QVBoxLayout; text->setSpacing(2);
    text->addWidget(label(t("3D view is in Blender", "La vista 3D está en Blender"), atlas::Role::Body14, "ivory"));
    auto *hint = label(t("Follows this move and frame", "Sigue este movimiento y cuadro"), atlas::Role::Body12);
    hint->setObjectName("wbBlenderHint"); text->addWidget(hint); card->addLayout(text, 1);
    showBlender_ = new AtlasButton(t("Show Blender", "Mostrar Blender")); showBlender_->setObjectName("wbShowBlender"); card->addWidget(showBlender_);
    setEngineStatus("stopped"); setBlenderState(false, false); setPendingChanges(0);
    connect(playLab_, &QPushButton::clicked, this, &HubPanel::playInLabRequested);
    connect(playCpu_, &QPushButton::clicked, this, &HubPanel::playVsCpuRequested);
    connect(start_, &QPushButton::clicked, this, &HubPanel::startRequested);
    connect(stop_, &QPushButton::clicked, this, &HubPanel::stopRequested);
    connect(restart_, &QPushButton::clicked, this, &HubPanel::restartRequested);
    connect(blender_, &QPushButton::clicked, this, &HubPanel::openInBlenderRequested);
    connect(showBlender_, &QPushButton::clicked, this, &HubPanel::showBlenderRequested);
    connect(headless_, &QCheckBox::toggled, this, &HubPanel::headlessChanged);
    connect(undo_, &QPushButton::clicked, this, &HubPanel::undoRequested);
    connect(rebuild_, &QPushButton::clicked, this, &HubPanel::rebuildRequested);
}
void HubPanel::setProject(const QString &name, int rows, int hitboxes) {
    project_->setText(name); project_->setToolTip(name);
    counts_->setText(t("%1 moves, %2 hitboxes", "%1 movimientos, %2 cajas de golpe").arg(rows).arg(hitboxes));
}
void HubPanel::setMove(const QString &row) { move_->setText(row); move_->setToolTip(row); }
void HubPanel::setEngineStatus(const QString &status) {
    if (status == "ready" || status == "running") {
        engine_->setText(t("◆ Game", "◆ Juego")); engine_->setToolTip(t("Engine running", "Motor en marcha"));
    } else if (status == "starting") {
        engine_->setText(t("◇ Game starting", "◇ Iniciando juego")); engine_->setToolTip(t("Engine starting", "Iniciando motor"));
    } else {
        engine_->setText(t("◇ Game stopped", "◇ Juego detenido")); engine_->setToolTip(t("Engine not running", "Motor detenido"));
    }
    engine_->setProperty("running", status == "ready" || status == "running");
}
void HubPanel::setHeadless(bool headless) { const QSignalBlocker block(headless_); headless_->setChecked(headless); }
void HubPanel::setPlayControls(bool busy, const QString &error) {
    playLab_->setEnabled(!busy && error.isEmpty()); playCpu_->setEnabled(!busy && error.isEmpty());
    playLab_->setToolTip(error); playCpu_->setToolTip(error);
}
void HubPanel::setControls(bool busy, bool canStop, bool canChangeMode, const QString &blenderError) {
    busy_ = busy;
    start_->setEnabled(!busy); restart_->setEnabled(!busy); stop_->setEnabled(!busy && canStop);
    headless_->setEnabled(!busy && canChangeMode); undo_->setEnabled(!busy);
    rebuild_->setEnabled(!busy && rebuildAvailable_);
    blender_->setEnabled(!busy && blenderError.isEmpty()); blender_->setToolTip(blenderError);
}
void HubPanel::setBlenderState(bool hasProcess, bool synced) {
    showBlender_->setEnabled(hasProcess);
    showBlender_->setToolTip(hasProcess ? t("Bring the fighter's Blender window forward", "Mostrar la ventana de Blender del luchador") :
        t("Open this fighter in Blender from Render first", "Abre primero este luchador en Blender desde Render"));
    blenderState_->setText(synced ? t("◆ Blender synced", "◆ Blender sincronizado") :
        hasProcess ? t("◇ Blender waiting", "◇ Blender en espera") : t("◇ Blender closed", "◇ Blender cerrado"));
    auto palette = blenderState_->palette(); palette.setColor(QPalette::WindowText, atlas::colour(synced ? "jade" : "muted"));
    blenderState_->setPalette(palette);
}
void HubPanel::setPendingChanges(int count) {
    // Source edits are persisted immediately by Session::commit. The badge must
    // never suggest they are unsaved; it counts changes pending the next build.
    pending_->setText(count > 0 ? t("%1 unbuilt", "%1 sin compilar").arg(count) : t("Saved", "Guardado"));
    pending_->setToolTip(t("Source edits are saved immediately. Rebuild to update the package.",
        "Los cambios se guardan inmediatamente. Reconstruye para actualizar el paquete."));
}
void HubPanel::setRebuildAvailable(bool available) { rebuildAvailable_ = available; rebuild_->setEnabled(!busy_ && available); }
}
