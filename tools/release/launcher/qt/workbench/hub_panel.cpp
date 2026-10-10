#include "hub_panel.h"
#include "atlas_widgets.h"
#include "kit.h"
#include "window.h"
#include <QCheckBox>
#include <QHBoxLayout>
#include <QFontMetrics>
#include <QLabel>
#include <QPainter>
#include <QResizeEvent>
#include <QSignalBlocker>
#include <QVBoxLayout>
#include <algorithm>
#include <iterator>

namespace wb {
using launcher::t;
namespace kit = launcher::kit;
namespace atlas = launcher::atlas;
namespace {
// A label that elides instead of clipping, so the breadcrumb never pushes the buttons off the bar.
class ElidedLabel : public QLabel {
public:
    using QLabel::QLabel;
    QSize minimumSizeHint() const override { return {48, QLabel::sizeHint().height()}; }
protected:
    void paintEvent(QPaintEvent *) override {
        QPainter p(this); p.setFont(font()); p.setPen(palette().color(QPalette::WindowText));
        p.drawText(rect(), Qt::AlignLeft | Qt::AlignVCenter, QFontMetrics(font()).elidedText(text(), Qt::ElideRight, width()));
    }
};
QLabel *label(const QString &text, atlas::Role role = atlas::Role::Cap14, const char *tone = "muted") {
    auto *value = kit::capLabel(text, role, tone); value->setTextFormat(Qt::PlainText); return value;
}
}
HubPanel::HubPanel(QWidget *parent) : QWidget(parent), layout_(new QVBoxLayout(this)) {
    setObjectName("wbHub"); setFocusPolicy(Qt::StrongFocus);
    layout_->setContentsMargins(0, 0, 0, 0); layout_->setSpacing(0);
    // Two rows when the bar is too narrow: breadcrumb + Rebuild stay on the first, the chips and
    // the secondary buttons wrap to the second. Rebuild is always the rightmost control of row one.
    bar_ = new QWidget; bar_->setObjectName("wbTopBar");
    auto *barLayout = new QVBoxLayout(bar_); barLayout->setContentsMargins(16, 8, 16, 10); barLayout->setSpacing(8);
    auto *firstRow = new QWidget; first_ = new QHBoxLayout(firstRow); first_->setContentsMargins(0, 0, 0, 0); first_->setSpacing(12);
    secondRow_ = new QWidget; second_ = new QHBoxLayout(secondRow_); second_->setContentsMargins(0, 0, 0, 0); second_->setSpacing(12);
    barLayout->addWidget(firstRow); barLayout->addWidget(secondRow_);
    auto *title = label(t("Geno Workbench", "Geno Workbench"), atlas::Role::Cap16, "ivory");
    auto *slashA = label(t("/", "/")), *slashB = label(t("/", "/"));
    auto *project = new ElidedLabel(t("Fighter project", "Proyecto del luchador")); project->setFont(atlas::font(atlas::Role::Cap14));
    { QPalette pal = project->palette(); pal.setColor(QPalette::WindowText, atlas::colour("muted")); project->setPalette(pal); }
    project_ = project; project_->setObjectName("wbProjectName"); project_->setMaximumWidth(160); project_->setTextFormat(Qt::PlainText);
    auto *move = new ElidedLabel; move->setFont(atlas::font(atlas::Role::Cap16));
    { QPalette pal = move->palette(); pal.setColor(QPalette::WindowText, atlas::colour("ember")); move->setPalette(pal); }
    move_ = move; move_->setTextFormat(Qt::PlainText); move_->setMaximumWidth(150);
    engine_ = label({}, atlas::Role::Cap14, "jade"); engine_->setObjectName("wbEngineStatus");
    blenderState_ = label({}, atlas::Role::Cap14, "muted"); blenderState_->setObjectName("wbBlenderState");
    pending_ = label({}, atlas::Role::Cap14, "sun"); pending_->setObjectName("wbUnsaved");
    undo_ = new AtlasButton(t("Undo", "Deshacer")); undo_->setObjectName("wbUndo");
    playLab_ = new AtlasButton(t("Play in LAB", "Jugar en LAB")); playLab_->setObjectName("wbPlayLab");
    playCpu_ = new AtlasButton(t("VS vs CPU", "VS contra CPU")); playCpu_->setObjectName("wbPlayCpu");
    auto *rebuild = new AtlasButton(t("Rebuild + reload", "Reconstruir + recargar")); rebuild->setTone(AtlasButton::Ember);
    rebuild_ = rebuild; rebuild_->setObjectName("wbRebuild");
    breadcrumb_[0] = title; breadcrumb_[1] = slashA; breadcrumb_[2] = project; breadcrumb_[3] = slashB; breadcrumb_[4] = move;
    layout_->addWidget(bar_);
    relayoutBar();

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
QSize HubPanel::minimumSizeHint() const { return {680, QWidget::minimumSizeHint().height()}; }
void HubPanel::resizeEvent(QResizeEvent *e) { QWidget::resizeEvent(e); relayoutBar(); }
void HubPanel::relayoutBar() {
    if (!bar_) return;
    const QWidget *chips[] = {engine_, blenderState_, pending_, undo_, playLab_, playCpu_};
    const int spacing = 12;
    int need = 32 + int(std::size(breadcrumb_) + std::size(chips) + 1 - 1) * spacing;
    for (auto *w : breadcrumb_) need += w->maximumWidth() < 100000 ? std::min(w->sizeHint().width(), w->maximumWidth()) : w->sizeHint().width();
    for (auto *w : chips) need += w->sizeHint().width();
    need += rebuild_->sizeHint().width() + 80; // breathing room so the one-row form never elides the breadcrumb
    const bool wrap = width() < need;
    if (wrapKnown_ && wrap == wrapped_) return;
    wrapKnown_ = true; wrapped_ = wrap;
    for (auto *l : {first_, second_}) while (auto *item = l->takeAt(0)) delete item;
    for (auto *w : breadcrumb_) first_->addWidget(w);
    first_->addStretch();
    if (wrap) {
        for (QWidget *w : {static_cast<QWidget *>(engine_), static_cast<QWidget *>(blenderState_), static_cast<QWidget *>(pending_)}) second_->addWidget(w);
        second_->addStretch();
        for (QWidget *w : {static_cast<QWidget *>(undo_), static_cast<QWidget *>(playLab_), static_cast<QWidget *>(playCpu_)}) second_->addWidget(w);
    } else {
        for (const QWidget *cw : chips) first_->addWidget(const_cast<QWidget *>(cw));
    }
    first_->addWidget(rebuild_);
    secondRow_->setVisible(wrap);
}
void HubPanel::setProject(const QString &name, int rows, int hitboxes) {
    project_->setText(name); project_->setToolTip(name);
    counts_->setText(t("%1 moves, %2 hitboxes", "%1 movimientos, %2 cajas de golpe").arg(rows).arg(hitboxes));
}
void HubPanel::setMove(const QString &row) { move_->setText(row); move_->setToolTip(row); relayoutBar(); }
void HubPanel::setEngineStatus(const QString &status) {
    if (status == "ready" || status == "running") {
        engine_->setText(t("◆ Game", "◆ Juego")); engine_->setToolTip(t("Engine running", "Motor en marcha"));
    } else if (status == "starting") {
        engine_->setText(t("◇ Game starting", "◇ Iniciando juego")); engine_->setToolTip(t("Engine starting", "Iniciando motor"));
    } else {
        engine_->setText(t("◇ Game stopped", "◇ Juego detenido")); engine_->setToolTip(t("Engine not running", "Motor detenido"));
    }
    engine_->setProperty("running", status == "ready" || status == "running"); relayoutBar();
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
    blenderState_->setPalette(palette); relayoutBar();
}
void HubPanel::setPendingChanges(int count) {
    // Source edits are persisted immediately by Session::commit. The badge must
    // never suggest they are unsaved; it counts changes pending the next build.
    pending_->setText(count > 0 ? t("%1 unbuilt", "%1 sin compilar").arg(count) : t("Saved", "Guardado"));
    pending_->setToolTip(t("Source edits are saved immediately. Rebuild to update the package.",
        "Los cambios se guardan inmediatamente. Reconstruye para actualizar el paquete.")); relayoutBar();
}
void HubPanel::setRebuildAvailable(bool available) { rebuildAvailable_ = available; rebuild_->setEnabled(!busy_ && available); }
}
