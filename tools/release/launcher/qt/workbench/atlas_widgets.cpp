#include "atlas_widgets.h"
#include "atlas.h"
#include "window.h"
#include <QAbstractScrollArea>
#include <QSlider>
#include <QAbstractSpinBox>
#include <QApplication>
#include <QComboBox>
#include <QFocusEvent>
#include <QWheelEvent>
#include <QHBoxLayout>
#include <QKeyEvent>
#include <QLabel>
#include <QMap>
#include <QMouseEvent>
#include <QPainter>
#include <QPainterPath>
#include <QPalette>
#include <QProgressBar>
#include <QStyle>
#include <QTabBar>
#include <QTimer>
#include <QToolTip>
#include <QHelpEvent>
#include <algorithm>
#include <cmath>
#include <iterator>

namespace wb {
using launcher::t;
namespace atlas = launcher::atlas;
namespace {
class WheelGuard final : public QObject {
public:
    using QObject::QObject;
    bool eventFilter(QObject *object, QEvent *event) override {
        if (event->type() != QEvent::Wheel) return false;
        auto *widget = qobject_cast<QWidget *>(object);
        if (!widget || !(qobject_cast<QAbstractSpinBox *>(widget) || qobject_cast<QComboBox *>(widget) || qobject_cast<QSlider *>(widget))) return false;
        if (widget->hasFocus()) return false;
        widget->setFocusPolicy(Qt::StrongFocus);
        for (QWidget *p = widget->parentWidget(); p; p = p->parentWidget())
            if (auto *area = qobject_cast<QAbstractScrollArea *>(p)) {
                // A fresh event for the viewport; the original is consumed here so the field never sees it.
                auto *wheel = static_cast<QWheelEvent *>(event);
                const QPointF local = area->viewport()->mapFromGlobal(wheel->globalPosition());
                QWheelEvent forwarded(local, wheel->globalPosition(), wheel->pixelDelta(), wheel->angleDelta(), wheel->buttons(),
                                      wheel->modifiers(), wheel->phase(), wheel->inverted(), wheel->source());
                QCoreApplication::sendEvent(area->viewport(), &forwarded);
                event->accept();
                return true;
            }
        event->ignore();
        return true;
    }
};
constexpr int kRulerHeight = 36, kRowHeight = 40, kBarHeight = 28, kLegendHeight = 42;
QPolygonF chamfer(const QRectF &r, qreal cut) {
    cut = std::min({cut, r.width() / 3, r.height() / 3});
    return {{r.left(), r.top()}, {r.right() - cut, r.top()}, {r.right(), r.top() + cut},
            {r.right(), r.bottom()}, {r.left() + cut, r.bottom()}, {r.left(), r.bottom() - cut}};
}
QColor translucent(const char *token, int alpha) {
    auto colour = atlas::colour(QString::fromLatin1(token)); colour.setAlpha(alpha); return colour;
}
QString colourName(const char *token) { return atlas::colour(QString::fromLatin1(token)).name(); }
void restyle(QWidget *widget) {
    widget->style()->unpolish(widget); widget->style()->polish(widget); widget->update();
}
bool sameHitboxSource(const QVector<HitboxRef> &before, const QVector<HitboxRef> &after) {
    if (before.size() != after.size()) return false;
    return std::equal(before.cbegin(), before.cend(), after.cbegin(), [](const HitboxRef &a, const HitboxRef &b) {
        // Ordinals are positions in the source, not stable identities: deletion or reordering can reuse them.
        return a.ordinal == b.ordinal && a.line == b.line && a.slot == b.slot && a.joint == b.joint
            && a.damage == b.damage && a.size == b.size && a.x == b.x && a.y == b.y && a.z == b.z
            && a.angle == b.angle && a.kbg == b.kbg && a.fkb == b.fkb && a.bkb == b.bkb && a.element == b.element
            && a.shield == b.shield && a.ground == b.ground && a.air == b.air
            && a.startFrame == b.startFrame && a.endFrame == b.endFrame && a.clearLine == b.clearLine;
    });
}
}

void applyAtlasStyle(QWidget *root) {
    if (!root) return;
    atlas::initialize();
    root->setProperty("atlasWorkbench", true);
    root->setFont(atlas::font(atlas::Role::Body14));
    auto palette = root->palette();
    palette.setColor(QPalette::WindowText, atlas::colour("text2"));
    palette.setColor(QPalette::Text, atlas::colour("ivory"));
    root->setPalette(palette);
    QString qss = QStringLiteral(R"QSS(
QWidget[atlasWorkbench="true"] { background: @ground@; }
QLabel { background: transparent; }
QLabel[atlasRole="muted"] { color: @muted@; }
QLabel[atlasRole="dim"] { color: @dim@; }
QLabel[atlasRole="info"] { color: @jade@; }
QLabel[atlasRole="warning"] { color: @sun@; }
QLabel[atlasRole="danger"] { color: @rose@; }
QLabel[atlasRole="heading"] { color: @muted@; font-family: "@caps@"; font-size: 14px; }
QLabel[atlasRole="number"] { color: @ivory@; font-family: "@numbers@"; }
#wbTopBar { background: @ground2@; border-bottom: 2px solid @edge@; }
#wbMovesRail { background: @ground2@; border-right: 2px solid @edge@; }
#wbCentreHost { background: @ground@; }
#wbInspectorTabs { background: @ground2@; }
#wbMoveTitle { color: @ivory@; font-family: "@caps@"; font-size: 44px; font-weight: 700; }
QLineEdit, QAbstractSpinBox, QComboBox, QTextEdit, QPlainTextEdit {
    background: @ground@; color: @ivory@; border: 1px solid @line@; border-radius: 0;
    padding: 5px; selection-background-color: @lift@; selection-color: @ivory@;
}
QLineEdit:focus, QAbstractSpinBox:focus, QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid @ember@;
}
QLineEdit:disabled, QAbstractSpinBox:disabled, QComboBox:disabled { color: @dim@; border-color: @ground2@; }
QAbstractSpinBox { padding-right: 18px; }
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button { background: @plate2@; width: 16px; border: 0; }
QDoubleSpinBox[atlasNumber="true"] { font-family: "@numbers@"; }
QComboBox::drop-down { width: 18px; background: @plate2@; border: 0; }
QComboBox QAbstractItemView { background: @plate2@; color: @ivory@; selection-background-color: @lift@; }
QPushButton { background: @plate2@; color: @text2@; border: 0; border-bottom: 2px solid @edge2@; padding: 7px 12px; }
QPushButton:hover { background: @lift@; color: @ivory@; }
QPushButton:pressed { background: @ground2@; }
QPushButton:focus { border: 1px solid @ember@; border-bottom-width: 2px; }
QPushButton:disabled { color: @dim@; background: @ground2@; }
QTabWidget::pane { background: @plate@; border: 0; border-top: 1px solid @line@; }
QTabBar::tab { background: @ground2@; color: @muted@; border: 0; border-bottom: 2px solid @edge@;
    min-height: 28px; padding: 6px 10px; font-family: "@caps@"; font-size: 15px; }
QTabBar::tab:selected { background: @plate@; color: @ivory@; border-bottom-color: @ember@; }
QTabBar::tab:hover { background: @plate2@; color: @ivory@; }
QTabBar::tab:focus { border: 1px solid @ember@; border-bottom-width: 2px; }
QTabBar::tab:disabled { color: @dim@; }
QTreeView, QListView, QTableView { background: @ground2@; alternate-background-color: @plate@; color: @text2@;
    border: 0; outline: 0; gridline-color: @line@; selection-background-color: @lift@; selection-color: @ivory@; }
QTreeView::item, QListView::item { padding: 5px 6px; border-left: 3px solid transparent; }
QTreeView::item:selected, QListView::item:selected { background: @lift@; color: @ivory@; border-left-color: @ember@; }
QTreeView::item:hover, QListView::item:hover { background: @plate2@; }
QTreeView:focus, QListView:focus, QTableView:focus { border: 1px solid @ember@; }
QHeaderView::section { background: @plate2@; color: @muted@; border: 0; border-bottom: 2px solid @edge2@; padding: 5px; }
QGroupBox { color: @muted@; border: 1px solid @line@; margin-top: 10px; padding: 10px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
QCheckBox { color: @text2@; spacing: 7px; }
QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid @line2@; background: @ground@; }
QCheckBox::indicator:checked { background: @jade@; border-color: @jade@; }
QCheckBox::indicator:focus { border-color: @ember@; }
QProgressBar { background: @ground@; border: 0; min-height: 6px; max-height: 8px; }
QProgressBar::chunk { background: @ember@; }
QProgressBar[atlasResult="success"]::chunk { background: @jade@; }
QProgressBar[atlasResult="failure"]::chunk { background: @rose@; }
QScrollArea { background: transparent; border: 0; }
QScrollBar:vertical { background: @ground@; width: 8px; margin: 0; }
QScrollBar:horizontal { background: @ground@; height: 8px; margin: 0; }
QScrollBar::handle { background: @line2@; min-height: 20px; min-width: 20px; }
QScrollBar::handle:hover { background: @muted@; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QSplitter::handle { background: @edge@; }
QStatusBar, #wbStatusProgress { background: @ground2@; color: @muted@; border-top: 1px solid @line@; }
QStatusBar::item { border: 0; }
QToolTip { background: @lift@; color: @ivory@; border: 1px solid @line2@; padding: 5px; }
)QSS");
    for (const char *token : {"ground", "ground2", "plate", "plate2", "lift", "edge", "edge2", "line", "line2",
                              "ivory", "text2", "muted", "dim", "ember", "jade", "sun", "rose"})
        qss.replace("@" + QString::fromLatin1(token) + "@", colourName(token));
    qss.replace("@caps@", atlas::font(atlas::Role::Cap14).family());
    qss.replace("@numbers@", atlas::numberFont().family());
    root->setStyleSheet(qss);
}

AtlasPlate::AtlasPlate(QWidget *parent) : QWidget(parent) { atlas::initialize(); }
void AtlasPlate::paintEvent(QPaintEvent *) {
    QPainter painter(this); painter.setRenderHint(QPainter::Antialiasing);
    const QRectF bounds = QRectF(rect()).adjusted(0.5, 0.5, -0.5, -0.5);
    const auto shape = chamfer(bounds, atlas::px("ch"));
    painter.setPen(Qt::NoPen); painter.setBrush(atlas::colour(elevated_ ? "plate2" : "plate"));
    painter.drawPolygon(shape);
    QPainterPath clip; clip.addPolygon(shape); clip.closeSubpath(); painter.setClipPath(clip);
    painter.fillRect(atlas::frontEdge(bounds, elevated_ ? 2 : 3), atlas::colour("edge2"));
}

AtlasButton::AtlasButton(const QString &text, QWidget *parent) : QPushButton(text, parent) {
    atlas::initialize();
    setFont(atlas::font(atlas::Role::Cap14)); setFocusPolicy(Qt::StrongFocus);
    setAttribute(Qt::WA_Hover); setCursor(Qt::PointingHandCursor);
    setSizePolicy(QSizePolicy::Minimum, QSizePolicy::Fixed);
}
void AtlasButton::setTone(Tone tone) { if (tone_ != tone) { tone_ = tone; update(); } }
QSize AtlasButton::sizeHint() const {
    const int iconWidth = icon().isNull() ? 0 : iconSize().width() + 8;
    return {std::max(40, fontMetrics().horizontalAdvance(text().toUpper()) + 30 + iconWidth),
            std::max(36, fontMetrics().height() + 16)};
}
QSize AtlasButton::minimumSizeHint() const { return sizeHint(); }
void AtlasButton::paintEvent(QPaintEvent *) {
    QPainter p(this); p.setRenderHint(QPainter::Antialiasing);
    const QRectF r = QRectF(rect()).adjusted(0.5, 0.5, -0.5, -0.5);
    const qreal cut = atlas::px(tone_ == Tone::Ember ? "ch" : "ch-s");
    const auto shape = chamfer(r, cut);
    QColor fill = atlas::colour(underMouse() ? "lift" : "plate2");
    QColor ink = atlas::colour("text2"), edge = atlas::colour("edge2");
    if (tone_ == Tone::Ember) {
        fill = atlas::colour(isDown() ? "ember-d" : "ember");
        ink = atlas::colour(isDown() ? "ivory" : "ink"); edge = atlas::colour("ember-d");
    } else if (tone_ == Tone::Danger) {
        fill = atlas::colour(isDown() ? "ground" : "plate"); ink = atlas::colour("rose"); edge = ink;
    } else if (isDown()) fill = atlas::colour("ground2");
    if (!isEnabled()) { fill = atlas::colour("ground2"); ink = atlas::colour("dim"); edge = atlas::colour("edge2"); }
    p.setPen(Qt::NoPen); p.setBrush(fill); p.drawPolygon(shape);
    QPainterPath clip; clip.addPolygon(shape); clip.closeSubpath(); p.setClipPath(clip);
    p.fillRect(atlas::frontEdge(r, isDown() ? 1 : 2), edge); p.setClipping(false);
    if (tone_ == Tone::Danger && isEnabled()) {
        p.setBrush(Qt::NoBrush); p.setPen(QPen(atlas::colour("rose"), 1)); p.drawPolygon(shape);
    }
    if (hasFocus()) {
        const auto ring = chamfer(r.adjusted(1.5, 1.5, -1.5, -1.5), std::max(1.0, cut - 1));
        p.setBrush(Qt::NoBrush);
        if (tone_ == Tone::Ember) { p.setPen(QPen(atlas::colour("ink"), 4)); p.drawPolygon(ring); }
        p.setPen(QPen(atlas::colour("ember"), 2)); p.drawPolygon(ring);
    }
    QRectF content = r.adjusted(12, 3, -12, -4).translated(0, isDown() ? 1 : 0);
    p.setFont(font()); p.setPen(ink);
    if (!icon().isNull()) {
        const int groupWidth = std::min(int(content.width()), iconSize().width() + 8 + fontMetrics().horizontalAdvance(text().toUpper()));
        const int x = qRound(content.center().x() - groupWidth / 2.0);
        icon().paint(&p, QRect(x, qRound(content.center().y() - iconSize().height() / 2.0), iconSize().width(), iconSize().height()),
                     Qt::AlignCenter, isEnabled() ? QIcon::Normal : QIcon::Disabled, isChecked() ? QIcon::On : QIcon::Off);
        content.setLeft(x + iconSize().width() + 8);
    }
    p.drawText(content, Qt::AlignCenter | Qt::TextShowMnemonic,
               atlas::fit(QFontMetricsF(font()), text().toUpper(), content.width()));
}

NumberField::NumberField(QWidget *parent) : QDoubleSpinBox(parent) {
    installWheelGuard();
    atlas::initialize(); setProperty("atlasNumber", true); setFont(atlas::numberFont());
    setMinimumHeight(34); setKeyboardTracking(false); setAlignment(Qt::AlignRight);
}
InspectorTabs::InspectorTabs(QWidget *parent) : QTabWidget(parent) {
    atlas::initialize(); setObjectName("wbInspectorTabs"); setFont(atlas::font(atlas::Role::Cap14));
    setDocumentMode(true); setUsesScrollButtons(true); tabBar()->setExpanding(true);
    setAccessibleName(t("Inspector", "Inspector"));
}

StatusProgress::StatusProgress(QWidget *parent) : QWidget(parent) {
    atlas::initialize(); setObjectName("wbStatusProgress");
    auto *layout = new QHBoxLayout(this); layout->setContentsMargins(12, 6, 12, 6); layout->setSpacing(12);
    phase_ = new QLabel(t("Ready", "Ready"), this); phase_->setObjectName("wbRebuildPhase");
    phase_->setFont(atlas::font(atlas::Role::Body14)); phase_->setTextFormat(Qt::PlainText);
    phase_->setSizePolicy(QSizePolicy::Ignored, QSizePolicy::Preferred); phase_->setMinimumWidth(100);
    progress_ = new QProgressBar(this); progress_->setObjectName("wbRebuildProgressBar");
    progress_->setTextVisible(false); progress_->setMinimumWidth(100); progress_->setMaximumWidth(360);
    progress_->setAccessibleName(t("Rebuild progress", "Progreso de reconstrucción")); progress_->hide();
    elapsedLabel_ = new QLabel(this); elapsedLabel_->setObjectName("wbRebuildElapsed");
    elapsedLabel_->setFont(atlas::numberFont(12)); elapsedLabel_->setMinimumWidth(58);
    elapsedLabel_->setAlignment(Qt::AlignRight | Qt::AlignVCenter); elapsedLabel_->hide();
    cancel_ = new AtlasButton(t("Cancel", "Cancelar"), this); cancel_->setObjectName("wbRebuildCancel"); cancel_->hide();
    layout->addWidget(phase_, 1); layout->addWidget(progress_, 1); layout->addWidget(elapsedLabel_); layout->addWidget(cancel_);
    ticker_ = new QTimer(this); ticker_->setInterval(100);
    connect(ticker_, &QTimer::timeout, this, &StatusProgress::refreshElapsed);
    connect(cancel_, &QPushButton::clicked, this, [this] { cancelPending_ = true; cancel_->setEnabled(false); emit cancelRequested(); });
}
void StatusProgress::begin(const QString &phase, bool cancellable) {
    running_ = true; cancelPending_ = false; elapsedBase_ = 0; elapsed_.start(); ticker_->start();
    progress_->setProperty("atlasResult", QString()); restyle(progress_);
    progress_->setRange(0, 0); progress_->show(); elapsedLabel_->show();
    phase_->setText(phase); phase_->setToolTip(phase);
    cancel_->setEnabled(cancellable); cancel_->show();
    cancel_->setToolTip(cancellable ? QString() : t("Cancellation is not available for this rebuild", "La cancelación no está disponible para esta reconstrucción"));
    refreshElapsed();
}
void StatusProgress::setProgress(const QString &phase, int percent, qint64 elapsedMs, bool cancellable) {
    if (!running_) begin(phase, cancellable);
    phase_->setText(phase); phase_->setToolTip(phase);
    if (percent < 0) progress_->setRange(0, 0);
    else { progress_->setRange(0, 100); progress_->setValue(std::clamp(percent, 0, 100)); }
    if (elapsedMs >= 0) { elapsedBase_ = elapsedMs; elapsed_.restart(); }
    cancel_->setEnabled(cancellable && !cancelPending_); cancel_->show();
    cancel_->setToolTip(cancellable ? QString() : t("Cancellation is not available for this rebuild", "La cancelación no está disponible para esta reconstrucción"));
    refreshElapsed();
}
void StatusProgress::finish(const QString &message, bool success) {
    if (running_) refreshElapsed();
    running_ = false; ticker_->stop(); cancel_->hide();
    const int last = progress_->maximum() > 0 ? std::max(0, progress_->value()) : 0;
    progress_->setRange(0, 100); progress_->setValue(success ? 100 : last);
    progress_->setProperty("atlasResult", success ? "success" : "failure"); restyle(progress_);
    phase_->setText(message); phase_->setToolTip(message);
}
void StatusProgress::setMessage(const QString &message) {
    phase_->setText(message); phase_->setToolTip(message);
    if (!running_) { progress_->hide(); elapsedLabel_->hide(); cancel_->hide(); }
}
void StatusProgress::refreshElapsed() {
    const qint64 elapsedMs = elapsedBase_ + (elapsed_.isValid() ? elapsed_.elapsed() : 0);
    elapsedLabel_->setText(t("%1 s", "%1 s").arg(QString::number(elapsedMs / 1000.0, 'f', 1)));
}

TimelineView::TimelineView(QWidget *parent) : Timeline(parent) {
    atlas::initialize(); setMouseTracking(true); setSizePolicy(QSizePolicy::Expanding, QSizePolicy::MinimumExpanding);
    setToolTip(t("Drag a hitbox edge to change its window. Click the ruler to seek. Arrows or J / L step; K or Space plays; Escape cancels a drag.",
                 "Arrastra un borde del hitbox para cambiar su intervalo. Pulsa la regla para ir a un cuadro. Flechas o J / L avanzan; K o Espacio reproducen; Escape cancela el arrastre."));
}
void TimelineView::setMove(const QString &row, int frames, const QVector<HitboxRef> &hits, int iasa, const QJsonArray &events) {
    // Keep the preview only when feedback still describes the source the gesture began on.
    // A source mutation can reuse an ordinal for a different hitbox, so accept it only after cancelling.
    if (drag_.handle != Handle::None && row == row_ && std::max(0, frames) == frameCount()
        && sameHitboxSource(hits_, hits)) {
        iasa_ = iasa; events_ = events; update(); return;
    }
    const bool changedRow = row != row_;
    cancelDrag(); scrubbing_ = false; row_ = row; hits_ = hits; iasa_ = iasa; events_ = events;
    Timeline::setRange(frames);
    if (changedRow || hitboxIndex(selected_) < 0) selected_ = -1;
    updateGeometry(); update();
}
void TimelineView::setSelectedHitbox(int ordinal) {
    selected_ = hitboxIndex(ordinal) >= 0 ? ordinal : -1; update();
}
void TimelineView::setRange(int frames) {
    if (frames != frameCount()) { cancelDrag(); scrubbing_ = false; }
    Timeline::setRange(frames); updateGeometry(); update();
}
qreal TimelineView::labelColumn() const {
    const QFontMetricsF fm(atlas::font(atlas::Role::Cap14));
    qreal full = 0;
    for (const auto &text : {t("Phases", "Fases"), t("Cancel window", "Ventana de cancelación"), t("Sounds · effects", "Sonidos · efectos")})
        full = std::max(full, fm.horizontalAdvance(text.toUpper()));
    full += 28; // 12 px left pad, 16 px gap before the bars
    return std::floor(std::min(full, std::max(112.0, width() * 0.3)));
}
bool TimelineView::event(QEvent *e) {
    if (e->type() == QEvent::ToolTip) {
        const auto *help = static_cast<QHelpEvent *>(e);
        const int row = int(std::floor((help->pos().y() - kRulerHeight) / double(kRowHeight)));
        QString text;
        if (help->pos().x() < labelColumn() && row >= 0) {
            if (row == 0) text = t("Phases", "Fases");
            else if (row <= hits_.size()) text = t("HB%1 · %2", "HB%1 · %2").arg(hits_[row - 1].ordinal).arg(hits_[row - 1].joint);
            else if (row == hits_.size() + 1) text = t("Cancel window", "Ventana de cancelación");
            else if (row == hits_.size() + 2) text = t("Sounds · effects", "Sonidos · efectos");
        }
        if (!text.isEmpty()) { QToolTip::showText(help->globalPos(), text, this); return true; }
    }
    return Timeline::event(e);
}
QRectF TimelineView::rulerRect() const {
    const qreal left = labelColumn();
    return {left, 4, std::max(1.0, width() - left - 12), 28};
}
qreal TimelineView::framePosition(int boundary) const {
    const auto ruler = rulerRect();
    return ruler.left() + (frameCount() > 0 ? ruler.width() * std::clamp(boundary, 0, frameCount()) / frameCount() : 0);
}
QRectF TimelineView::trackRect(int row) const {
    return {rulerRect().left(), qreal(kRulerHeight + row * kRowHeight + 6), rulerRect().width(), kBarHeight};
}
QRectF TimelineView::windowRect(int start, int end, int row) const {
    if (frameCount() <= 0 || start < 0 || end <= start || end > frameCount()) return {};
    const auto track = trackRect(row);
    return {framePosition(start), track.top(), framePosition(end) - framePosition(start), track.height()};
}
bool TimelineView::validWindow(const HitboxRef &hit) const {
    return frameCount() > 0 && hit.ordinal >= 0 && hit.startFrame >= 0 && hit.startFrame < frameCount()
        && (hit.endFrame == -1 || (hit.endFrame > hit.startFrame && hit.endFrame <= frameCount()));
}
int TimelineView::hitboxIndex(int ordinal) const {
    for (int i = 0; i < hits_.size(); ++i) if (hits_[i].ordinal == ordinal) return i;
    return -1;
}
QRectF TimelineView::hitboxRectAt(int index) const {
    if (index < 0 || index >= hits_.size() || !validWindow(hits_[index])) return {};
    const auto &hit = hits_[index];
    const bool preview = drag_.handle != Handle::None && drag_.index == index;
    const int start = preview ? drag_.start : hit.startFrame;
    const int end = preview ? drag_.end : hit.endFrame;
    return windowRect(start, end == -1 ? frameCount() : end, index + 1);
}
QRectF TimelineView::hitboxRect(int ordinal) const { return hitboxRectAt(hitboxIndex(ordinal)); }
QSize TimelineView::sizeHint() const { return {620, kRulerHeight + (int(hits_.size()) + 3) * kRowHeight + kLegendHeight}; }
QSize TimelineView::minimumSizeHint() const { return {300, sizeHint().height()}; }
TimelineView::Handle TimelineView::handleAt(const QRectF &bar, const QPointF &position) const {
    if (bar.isEmpty() || position.y() < bar.top() - 3 || position.y() > bar.bottom() + 3) return Handle::None;
    const qreal left = std::abs(position.x() - bar.left()), right = std::abs(position.x() - bar.right());
    if (std::min(left, right) > 7) return Handle::None;
    return left < right ? Handle::Start : Handle::End;
}
void TimelineView::cancelDrag() {
    if (drag_.handle != Handle::None) { drag_ = {}; unsetCursor(); update(); }
}
void TimelineView::updateDrag(qreal x) {
    if (drag_.handle == Handle::None || frameCount() <= 0) return;
    const qreal cell = rulerRect().width() / frameCount();
    const qint64 delta = qRound64((x - drag_.pressX) / cell);
    const int originalEnd = drag_.originalEnd == -1 ? frameCount() : drag_.originalEnd;
    if (drag_.handle == Handle::Start)
        drag_.start = int(std::clamp(qint64(drag_.originalStart) + delta, qint64(0), qint64(originalEnd - 1)));
    else drag_.end = int(std::clamp(qint64(originalEnd) + delta, qint64(drag_.originalStart + 1), qint64(frameCount())));
    update();
}
void TimelineView::requestFrame(int requested) {
    if (frameCount() <= 0) return;
    requested = std::clamp(requested, 0, frameCount() - 1);
    if (requested == frame()) return;
    setFrame(requested); emit frameRequested(requested);
}
void TimelineView::seek(qreal x) {
    if (frameCount() <= 0) return;
    const qreal ratio = std::clamp((x - rulerRect().left()) / rulerRect().width(), 0.0, 1.0);
    requestFrame(std::min(frameCount() - 1, int(std::floor(ratio * frameCount()))));
}
void TimelineView::mousePressEvent(QMouseEvent *event) {
    if (event->button() != Qt::LeftButton) return QWidget::mousePressEvent(event);
    setFocus(Qt::MouseFocusReason);
    for (int i = 0; i < hits_.size(); ++i) {
        const auto bar = hitboxRectAt(i);
        const auto handle = handleAt(bar, event->position());
        const auto label = QRectF(0, trackRect(i + 1).top(), rulerRect().left() - 8, kBarHeight);
        if (handle == Handle::None && !bar.contains(event->position()) && !label.contains(event->position())) continue;
        if (handle != Handle::None && !row_.isEmpty()) {
            const auto &hit = hits_[i];
            drag_ = {handle, i, hit.startFrame, hit.endFrame, hit.startFrame, hit.endFrame, event->position().x()};
            setCursor(Qt::SizeHorCursor);
        }
        selected_ = hits_[i].ordinal; update(); emit hitboxSelected(selected_); event->accept(); return;
    }
    if (frameCount() > 0 && rulerRect().adjusted(0, -4, 0, 4).contains(event->position())) {
        scrubbing_ = true; seek(event->position().x()); event->accept(); return;
    }
    QWidget::mousePressEvent(event);
}
void TimelineView::mouseMoveEvent(QMouseEvent *event) {
    if (drag_.handle != Handle::None) { updateDrag(event->position().x()); event->accept(); return; }
    if (scrubbing_) { seek(event->position().x()); event->accept(); return; }
    bool overHandle = false;
    for (int i = 0; i < hits_.size(); ++i) if (handleAt(hitboxRectAt(i), event->position()) != Handle::None) { overHandle = true; break; }
    if (overHandle && !row_.isEmpty()) setCursor(Qt::SizeHorCursor); else unsetCursor();
    QWidget::mouseMoveEvent(event);
}
void TimelineView::mouseReleaseEvent(QMouseEvent *event) {
    if (event->button() == Qt::LeftButton && drag_.handle != Handle::None) {
        updateDrag(event->position().x());
        const auto drag = drag_; drag_ = {}; unsetCursor();
        const int oldVisibleEnd = drag.originalEnd == -1 ? frameCount() : drag.originalEnd;
        const int newVisibleEnd = drag.end == -1 ? frameCount() : drag.end;
        const bool changed = drag.start != drag.originalStart || newVisibleEnd != oldVisibleEnd;
        if (changed && drag.index >= 0 && drag.index < hits_.size()) {
            auto &hit = hits_[drag.index]; hit.startFrame = drag.start;
            // Moving a never-cleared hitbox's start must not invent a clear operation.
            if (drag.handle == Handle::End) hit.endFrame = drag.end;
            QJsonObject args{{"row", row_}, {"ordinal", hit.ordinal}, {"start_frame", hit.startFrame}};
            if (hit.endFrame >= 0) args["end_frame"] = hit.endFrame;
            emit editRequested("edit_hitbox", args);
        }
        update(); event->accept(); return;
    }
    if (event->button() == Qt::LeftButton && scrubbing_) {
        seek(event->position().x()); scrubbing_ = false; event->accept(); return;
    }
    QWidget::mouseReleaseEvent(event);
}
void TimelineView::keyPressEvent(QKeyEvent *event) {
    if (event->key() == Qt::Key_Escape && drag_.handle != Handle::None) {
        cancelDrag(); event->accept(); return;
    }
    if (event->modifiers() != Qt::NoModifier) return QWidget::keyPressEvent(event);
    if (event->key() == Qt::Key_Left || event->key() == Qt::Key_Right) {
        requestFrame(frame() + (event->key() == Qt::Key_Left ? -1 : 1)); event->accept(); return;
    }
    if (event->key() == Qt::Key_Space) {
        QKeyEvent play(QEvent::KeyPress, Qt::Key_K, Qt::NoModifier, QString(), event->isAutoRepeat(), event->count());
        Timeline::keyPressEvent(&play); event->accept(); return;
    }
    Timeline::keyPressEvent(event);
}
void TimelineView::focusOutEvent(QFocusEvent *event) { cancelDrag(); scrubbing_ = false; QWidget::focusOutEvent(event); }
void TimelineView::leaveEvent(QEvent *event) { if (drag_.handle == Handle::None) unsetCursor(); QWidget::leaveEvent(event); }

void TimelineView::paintEvent(QPaintEvent *) {
    QPainter p(this); p.fillRect(rect(), atlas::colour("plate"));
    if (frameCount() <= 0) {
        p.setFont(atlas::font(atlas::Role::Body14)); p.setPen(atlas::colour("muted"));
        p.drawText(rect().adjusted(16, 16, -16, -16), Qt::AlignCenter | Qt::TextWordWrap,
                   t("Select a move with frame data to inspect its timeline.", "Selecciona un movimiento con datos de cuadros para ver su línea de tiempo."));
        if (hasFocus()) { p.setPen(QPen(atlas::colour("ember"), 1)); p.drawRect(rect().adjusted(0, 0, -1, -1)); }
        return;
    }
    const qreal cell = rulerRect().width() / frameCount();
    const int tick = std::max(1, int(std::ceil(34.0 / cell)));
    const qreal trackBottom = trackRect(int(hits_.size()) + 2).bottom();
    p.setFont(atlas::numberFont(12));
    for (qint64 f = 0; f < frameCount(); f += tick) {
        const qreal x = framePosition(int(f));
        p.setPen(QPen(atlas::colour("ground2"), 1)); p.drawLine(QPointF(x, kRulerHeight), QPointF(x, trackBottom));
        p.setPen(atlas::colour("dim"));
        p.drawText(QRectF(x + cell / 2 - 15, 4, 30, 28), Qt::AlignCenter, QString::number(f));
    }
    const qreal currentX = framePosition(frame());
    const qreal markerWidth = std::min(rulerRect().width(), std::max(cell, QFontMetricsF(p.font()).horizontalAdvance(QString::number(frame())) + 8));
    QRectF marker(currentX + cell / 2 - markerWidth / 2, 4, markerWidth, 28);
    if (marker.left() < rulerRect().left()) marker.moveLeft(rulerRect().left());
    if (marker.right() > rulerRect().right()) marker.moveRight(rulerRect().right());
    p.fillRect(marker, atlas::colour("ember")); p.setPen(atlas::colour("ink"));
    p.drawText(marker, Qt::AlignCenter, QString::number(frame()));

    auto label = [&](int row, const QString &text) {
        p.setFont(atlas::font(atlas::Role::Cap14)); p.setPen(atlas::colour("muted"));
        p.drawText(QRectF(12, trackRect(row).top(), rulerRect().left() - 24, kBarHeight), Qt::AlignLeft | Qt::AlignVCenter,
                   atlas::fit(QFontMetricsF(p.font()), text.toUpper(), rulerRect().left() - 24));
    };
    auto note = [&](int row, const QString &text, const char *colour = "dim") {
        p.setFont(atlas::font(atlas::Role::Body12)); p.setPen(atlas::colour(QString::fromLatin1(colour)));
        p.drawText(trackRect(row).adjusted(6, 0, -6, 0), Qt::AlignLeft | Qt::AlignVCenter,
                   atlas::fit(QFontMetricsF(p.font()), text, trackRect(row).width() - 12));
    };
    auto phase = [&](int start, int end, const char *colour, const QString &text, const char *ink) {
        const auto band = windowRect(start, end, 0); if (band.isEmpty()) return;
        p.fillRect(band.adjusted(0, 0, -1, 0), atlas::colour(QString::fromLatin1(colour)));
        p.setFont(atlas::font(atlas::Role::Body12)); p.setPen(atlas::colour(QString::fromLatin1(ink)));
        if (band.width() > 24) p.drawText(band.adjusted(6, 0, -4, 0), Qt::AlignLeft | Qt::AlignVCenter,
                                       atlas::fit(QFontMetricsF(p.font()), text, band.width() - 10));
    };
    label(0, t("Phases", "Fases"));
    QVector<QPair<int, int>> active;
    for (int i = 0; i < hits_.size(); ++i) if (validWindow(hits_[i])) {
        const bool preview = drag_.handle != Handle::None && drag_.index == i;
        const int start = preview ? drag_.start : hits_[i].startFrame;
        const int end = preview ? drag_.end : hits_[i].endFrame;
        active.append({start, end == -1 ? frameCount() : end});
    }
    std::sort(active.begin(), active.end(), [](auto a, auto b) { return a.first < b.first; });
    QVector<QPair<int, int>> merged;
    for (auto window : active) {
        if (!merged.isEmpty() && window.first <= merged.last().second) merged.last().second = std::max(merged.last().second, window.second);
        else merged.append(window);
    }
    if (merged.isEmpty()) note(0, t("No active hitbox windows", "No hay intervalos de hitbox activos"));
    else {
        int previous = 0; bool first = true;
        for (auto window : merged) {
            phase(previous, window.first, first ? "line2" : "lift",
                  first ? t("Startup", "Inicio") : t("Recovery", "Recuperación"), first ? "ivory" : "text2");
            phase(window.first, window.second, "rose", t("Active", "Activo"), "ink");
            previous = window.second; first = false;
        }
        phase(previous, frameCount(), "lift", t("Recovery", "Recuperación"), "text2");
    }
    for (int i = 0; i < hits_.size(); ++i) {
        const auto &hit = hits_[i]; const auto track = trackRect(i + 1), bar = hitboxRectAt(i);
        p.setFont(atlas::font(atlas::Role::Body14)); p.setPen(atlas::colour(selected_ == hit.ordinal ? "ivory" : "text2"));
        const QString name = t("HB%1", "HB%1").arg(hit.ordinal);
        p.drawText(QRectF(12, track.top(), 48, kBarHeight), Qt::AlignLeft | Qt::AlignVCenter, name);
        p.setFont(atlas::numberFont(12)); p.setPen(atlas::colour("muted"));
        p.drawText(QRectF(58, track.top(), rulerRect().left() - 70, kBarHeight), Qt::AlignLeft | Qt::AlignVCenter,
                   atlas::fit(QFontMetricsF(p.font()), hit.joint, rulerRect().left() - 70));
        if (bar.isEmpty()) { note(i + 1, t("Invalid hitbox window", "Intervalo de hitbox no válido"), "sun"); continue; }
        const bool selected = selected_ == hit.ordinal;
        const QColor outline = atlas::colour(selected ? "ember" : "rose");
        p.fillRect(bar, translucent("rose", 56));
        p.setPen(QPen(outline, selected ? 2 : 1, hit.endFrame == -1 ? Qt::DashLine : Qt::SolidLine));
        p.setBrush(Qt::NoBrush); p.drawRect(bar.adjusted(0.5, 0.5, -0.5, -0.5));
        if (bar.width() >= 8) {
            const qreal grip = std::min(4.0, bar.width() / 4);
            p.fillRect(QRectF(bar.left() + 3, bar.top() + 6, grip, bar.height() - 12), outline);
            p.fillRect(QRectF(bar.right() - grip - 3, bar.top() + 6, grip, bar.height() - 12), outline);
        }
    }
    const int cancelRow = int(hits_.size()) + 1, eventRow = cancelRow + 1;
    label(cancelRow, t("Cancel window", "Ventana de cancelación"));
    if (iasa_ > 0 && iasa_ < frameCount()) {
        const auto cancel = windowRect(iasa_, frameCount(), cancelRow);
        p.fillRect(cancel, translucent("jade", 46)); p.setPen(QPen(atlas::colour("jade"), 2)); p.setBrush(Qt::NoBrush);
        p.drawRect(cancel.adjusted(1, 1, -1, -1));
        p.setFont(atlas::numberFont(12)); p.setPen(atlas::colour("jade"));
        if (cancel.width() >= 64) p.drawText(cancel.adjusted(6, 0, -6, 0), Qt::AlignLeft | Qt::AlignVCenter, QString::number(iasa_));
    } else note(cancelRow, iasa_ >= frameCount() ? t("Outside move range", "Fuera del intervalo del movimiento") : t("Not set", "Sin definir"));
    label(eventRow, t("Sounds · effects", "Sonidos · efectos"));
    QMap<int, QStringList> markers;
    for (const auto &value : events_) {
        const auto event = value.toObject(); const auto at = event.value("frame"); const QString text = event.value("label").toString();
        const int eventFrame = at.toInt(-1);
        if (at.isDouble() && at.toDouble() == eventFrame && eventFrame >= 0 && eventFrame < frameCount() && !text.isEmpty())
            markers[eventFrame].append(text);
    }
    if (markers.isEmpty()) note(eventRow, t("No event data", "Sin datos de eventos"));
    for (auto it = markers.cbegin(); it != markers.cend(); ++it) {
        const qreal left = framePosition(it.key()); const auto next = std::next(it);
        const qreal right = next == markers.cend() ? rulerRect().right() : framePosition(next.key());
        const QRectF markerBar(left, trackRect(eventRow).top(), std::max(1.0, std::min(110.0, right - left - 2)), kBarHeight);
        p.fillRect(markerBar, atlas::colour("plate2")); p.fillRect(QRectF(left, markerBar.top(), std::min(3.0, markerBar.width()), kBarHeight), atlas::colour("sun"));
        p.setFont(atlas::font(atlas::Role::Body12)); p.setPen(atlas::colour("text2"));
        p.drawText(markerBar.adjusted(6, 0, -2, 0), Qt::AlignLeft | Qt::AlignVCenter,
                   atlas::fit(QFontMetricsF(p.font()), it.value().join(" · "), markerBar.width() - 8));
    }
    p.setPen(QPen(atlas::colour("ember"), 1));
    p.drawLine(QPointF(currentX + cell / 2, kRulerHeight), QPointF(currentX + cell / 2, trackBottom + 4));

    p.setFont(atlas::font(atlas::Role::Body12));
    qreal legendX = 12, legendY = std::max(trackBottom + 16, qreal(height() - 24));
    const QVector<QPair<QString, QString>> legend{{t("Startup", "Inicio"), "line2"}, {t("Active", "Activo"), "rose"},
        {t("Recovery", "Recuperación"), "lift"}, {t("Selected", "Seleccionado"), "ember"},
        {t("Cancel window", "Ventana de cancelación"), "jade"}};
    for (int i = 0; i < legend.size(); ++i) {
        const auto &item = legend[i]; const qreal entry = QFontMetricsF(p.font()).horizontalAdvance(item.first) + 34;
        if (legendX + entry > width() - 8) break;
        const QRectF swatch(legendX, legendY + 4, 12, 8);
        if (i < 3) p.fillRect(swatch, atlas::colour(item.second));
        else { p.setPen(QPen(atlas::colour(item.second), 2)); p.setBrush(Qt::NoBrush); p.drawRect(swatch); }
        p.setPen(atlas::colour("muted")); p.drawText(QPointF(legendX + 18, legendY + 12), item.first); legendX += entry;
    }
    if (hasFocus()) { p.setBrush(Qt::NoBrush); p.setPen(QPen(atlas::colour("ember"), 1)); p.drawRect(rect().adjusted(0, 0, -1, -1)); }
}
void installWheelGuard() {
    static WheelGuard *guard = nullptr;
    if (guard || !QCoreApplication::instance()) return;
    guard = new WheelGuard(QCoreApplication::instance());
    QCoreApplication::instance()->installEventFilter(guard);
}
} // namespace wb
