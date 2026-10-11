#include "hub_panel.h"
#include "atlas_widgets.h"
#include "kit.h"
#include "window.h"
#include <QCheckBox>
#include <QHBoxLayout>
#include <QFontMetrics>
#include <QLabel>
#include <QMenu>
#include <QPushButton>
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
// A flat status chip that is also a control; its colour follows the state it reports.
QPushButton *chip(const QString &name) {
    auto *value = new QPushButton; value->setObjectName(name); value->setFlat(true); value->setCursor(Qt::PointingHandCursor);
    value->setFont(atlas::font(atlas::Role::Cap14)); return value;
}
void tint(QPushButton *button, const char *tone) {
    button->setStyleSheet(QString("QPushButton { color: %1; background: transparent; border: 0; padding: 2px 4px; text-align: left; }"
                                  "QPushButton:hover { background: %2; } QPushButton:focus { border-bottom: 2px solid %3; }")
        .arg(atlas::colour(tone).name(), atlas::colour("plate2").name(), atlas::colour("ember").name()));
}
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
    engine_ = chip("wbEngineStatus"); blenderState_ = chip("wbBlenderState");
    pending_ = label({}, atlas::Role::Cap14, "sun"); pending_->setObjectName("wbUnsaved");
    queued_ = label({}, atlas::Role::Cap14, "ember"); queued_->setObjectName("wbQueued"); queued_->hide();
    undo_ = new AtlasButton(t("Undo", "Deshacer")); undo_->setObjectName("wbUndo");
    revertAll_ = new AtlasButton(t("Revert all", "Revertir todo")); revertAll_->setObjectName("wbRevertAll"); revertAll_->hide();
    revertAll_->setToolTip(t("Restore every changed field to the value in the built game", "Restaurar todos los campos cambiados al valor del juego compilado"));
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
    connect(engine_, &QPushButton::clicked, this, [this] {
        if (engineStarting_) return;
        if (!engineRunning_) { emit startRequested(); return; }
        QMenu menu(this);
        connect(menu.addAction(t("Restart game", "Reiniciar juego")), &QAction::triggered, this, &HubPanel::restartRequested);
        connect(menu.addAction(t("Stop game", "Detener juego")), &QAction::triggered, this, &HubPanel::stopRequested);
        menu.exec(engine_->mapToGlobal(QPoint(0, engine_->height())));
    });
    connect(blenderState_, &QPushButton::clicked, this, [this] { if (blenderRunning_) emit showBlenderRequested(); else emit openInBlenderRequested(); });
    connect(revertAll_, &QPushButton::clicked, this, &HubPanel::revertAllRequested);
    connect(rebuild_, &QPushButton::clicked, this, &HubPanel::rebuildRequested);
}
QSize HubPanel::minimumSizeHint() const { return {680, QWidget::minimumSizeHint().height()}; }
void HubPanel::resizeEvent(QResizeEvent *e) { QWidget::resizeEvent(e); relayoutBar(); }
void HubPanel::relayoutBar() {
    if (!bar_) return;
    const QWidget *chips[] = {engine_, blenderState_, pending_, queued_, revertAll_, undo_, playLab_, playCpu_};
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
        for (QWidget *w : {static_cast<QWidget *>(engine_), static_cast<QWidget *>(blenderState_), static_cast<QWidget *>(pending_), static_cast<QWidget *>(queued_), static_cast<QWidget *>(revertAll_)}) second_->addWidget(w);
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
    engineRunning_ = status == "ready" || status == "running"; engineStarting_ = status == "starting";
    if (engineRunning_) {
        engine_->setText(t("◆ Game running ▸ Restart / Stop", "◆ Juego en marcha ▸ Reiniciar / Detener")); engine_->setToolTip(t("Engine running", "Motor en marcha")); tint(engine_, "jade");
    } else if (engineStarting_) {
        engine_->setText(t("◇ Game starting", "◇ Iniciando juego")); engine_->setToolTip(t("Engine starting", "Iniciando motor")); tint(engine_, "muted");
    } else {
        engine_->setText(t("◇ Game stopped ▸ Start game", "◇ Juego detenido ▸ Iniciar juego")); engine_->setToolTip(t("Engine not running", "Motor detenido")); tint(engine_, "muted");
    }
    engineBase_ = engine_->toolTip();
    if (!engineDetail_.isEmpty()) engine_->setToolTip(engineBase_ + "\n" + engineDetail_);
    engine_->setProperty("running", engineRunning_); relayoutBar();
}
void HubPanel::setEngineDetail(const QString &detail) {
    engineDetail_ = detail;
    engine_->setToolTip(engineDetail_.isEmpty() ? engineBase_ : engineBase_ + "\n" + engineDetail_);
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
    showBlender_->setEnabled(true);
    showBlender_->setToolTip(hasProcess ? t("Bring the fighter's Blender window forward", "Mostrar la ventana de Blender del luchador") :
        t("Blender is closed: click to start it with this fighter", "Blender está cerrado: pulsa para iniciarlo con este luchador"));
    blenderRunning_ = hasProcess;
    blenderState_->setText(synced ? t("◆ Blender linked ▸ Show", "◆ Blender enlazado ▸ Mostrar") :
        hasProcess ? t("◇ Blender waiting ▸ Show", "◇ Blender en espera ▸ Mostrar") : t("◇ Blender closed ▸ Start Blender", "◇ Blender cerrado ▸ Iniciar Blender"));
    tint(blenderState_, synced ? "jade" : "muted"); relayoutBar();
}
void HubPanel::setPendingChanges(int count) {
    // Source edits are persisted immediately by Session::commit. The badge must
    // never suggest they are unsaved; it counts changes pending the next build.
    pending_->setText(count > 0 ? (count == 1 ? t("1 change not in game", "1 cambio fuera del juego") : t("%1 changes not in game", "%1 cambios fuera del juego").arg(count))
                                : t("In game", "En el juego"));
    pending_->setToolTip(t("Source edits are saved immediately. Rebuild + reload to put them in the game.",
        "Los cambios se guardan inmediatamente. Reconstruye y recarga para llevarlos al juego."));
    revertAll_->setVisible(count > 0); wrapKnown_ = false; relayoutBar();
}
void HubPanel::setRebuildAvailable(bool available) { rebuildAvailable_ = available; rebuild_->setEnabled(!busy_ && available); }
void HubPanel::setQueued(int count) {
    queued_->setVisible(count > 0);
    queued_->setText(count == 1 ? t("1 edit queued: in next rebuild", "1 edición en cola: en la próxima reconstrucción")
                                : t("%1 edits queued: in next rebuild", "%1 ediciones en cola: en la próxima reconstrucción").arg(count));
    queued_->setToolTip(t("These edits wait for the running rebuild to finish, then apply and count as changes for the next rebuild.",
        "Estas ediciones esperan a que termine la reconstrucción en curso y cuentan como cambios para la siguiente."));
    wrapKnown_ = false; relayoutBar();
}
void HubPanel::setRebuildAgain(int newChanges) {
    rebuildAgain_ = newChanges;
    rebuild_->setText(newChanges <= 0 ? t("Rebuild + reload", "Reconstruir + recargar")
        : newChanges == 1 ? t("Rebuild again (1 new change)", "Reconstruir de nuevo (1 cambio nuevo)")
                          : t("Rebuild again (%1 new changes)", "Reconstruir de nuevo (%1 cambios nuevos)").arg(newChanges));
    rebuild_->setToolTip(newChanges <= 0 ? QString() : t("Edits made while the last rebuild was running are not in the game yet.",
        "Las ediciones hechas durante la última reconstrucción aún no están en el juego."));
    wrapKnown_ = false; relayoutBar();
}
}
