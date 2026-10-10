#include "hub_panel.h"
#include "kit.h"
#include "window.h"
#include <QCheckBox>
#include <QHBoxLayout>
#include <QLabel>
#include <QPushButton>
#include <QSignalBlocker>
#include <QVBoxLayout>

namespace wb {
using launcher::t;
namespace kit = launcher::kit;
namespace atlas = launcher::atlas;
HubPanel::HubPanel(QWidget *parent) : QWidget(parent), layout_(new QVBoxLayout(this)) {
    setObjectName("wbHub"); setAutoFillBackground(true); setFocusPolicy(Qt::StrongFocus);
    layout_->setContentsMargins(0, 0, 0, 0); layout_->setSpacing(atlas::px("s2"));
    project_ = kit::capLabel(t("Fighter project", "Proyecto del luchador"), atlas::Role::Cap16);
    project_->setObjectName("wbProjectName"); project_->setTextFormat(Qt::PlainText); layout_->addWidget(project_);
    counts_ = new QLabel; counts_->setObjectName("wbProjectCounts"); layout_->addWidget(counts_);
    engine_ = new QLabel; engine_->setObjectName("wbEngineStatus"); engine_->setTextFormat(Qt::PlainText);
    engine_->setWordWrap(true); layout_->addWidget(engine_); setEngineStatus("stopped");
    auto *buttons = new QHBoxLayout; layout_->addLayout(buttons);
    start_ = new kit::Button(t("Start", "Iniciar")); start_->setObjectName("wbStart"); buttons->addWidget(start_);
    stop_ = new kit::Button(t("Stop", "Detener")); stop_->setObjectName("wbStop"); buttons->addWidget(stop_);
    restart_ = new kit::Button(t("Restart engine", "Reiniciar motor")); restart_->setObjectName("wbRestart"); buttons->addWidget(restart_);
    buttons->addStretch();
    headless_ = new QCheckBox(t("Headless engine (no window)", "Motor sin ventana"));
    headless_->setObjectName("wbHeadless"); headless_->setChecked(true); layout_->addWidget(headless_);
    blender_ = new kit::Button(t("Open in Blender", "Abrir en Blender")); blender_->setObjectName("openInBlender");
    layout_->addWidget(blender_);
    auto *hint = new QLabel(t("Blender shows the fighter; this window keeps the problems, review and history panels.",
        "Blender muestra al luchador; esta ventana conserva los paneles de problemas, revision e historial."));
    hint->setObjectName("wbBlenderHint"); hint->setWordWrap(true); layout_->addWidget(hint);
    connect(start_, &QPushButton::clicked, this, &HubPanel::startRequested);
    connect(stop_, &QPushButton::clicked, this, &HubPanel::stopRequested);
    connect(restart_, &QPushButton::clicked, this, &HubPanel::restartRequested);
    connect(blender_, &QPushButton::clicked, this, &HubPanel::openInBlenderRequested);
    connect(headless_, &QCheckBox::toggled, this, &HubPanel::headlessChanged);
}
void HubPanel::setProject(const QString &name, int rows, int hitboxes) {
    project_->setText(name); counts_->setText(t("%1 moves, %2 hitboxes", "%1 movimientos, %2 cajas de golpe").arg(rows).arg(hitboxes));
}
void HubPanel::setEngineStatus(const QString &status) {
    if (status == "ready" || status == "running") engine_->setText(t("Engine running", "Motor en marcha"));
    else if (status == "stopped") engine_->setText(t("Engine not running", "Motor detenido"));
    else if (status == "starting") engine_->setText(t("Engine starting", "Iniciando motor"));
    else engine_->setText(t("Engine: %1", "Motor: %1").arg(status));
}
void HubPanel::setHeadless(bool headless) { const QSignalBlocker block(headless_); headless_->setChecked(headless); }
void HubPanel::setControls(bool busy, bool canStop, bool canChangeMode, const QString &blenderError) {
    start_->setEnabled(!busy); restart_->setEnabled(!busy); stop_->setEnabled(!busy && canStop);
    headless_->setEnabled(!busy && canChangeMode);
    blender_->setEnabled(!busy && blenderError.isEmpty()); blender_->setToolTip(blenderError);
}
}
