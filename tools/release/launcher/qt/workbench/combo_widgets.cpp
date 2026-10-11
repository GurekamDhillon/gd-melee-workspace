#include "combo_widgets.h"
#include "atlas.h"
#include "atlas_widgets.h"
#include "window.h"
#include <QCheckBox>
#include <QComboBox>
#include <QFormLayout>
#include <QHBoxLayout>
#include <QHelpEvent>
#include <QKeyEvent>
#include <QLabel>
#include <QLineEdit>
#include <QListWidget>
#include <QMouseEvent>
#include <QPainter>
#include <QPainterPath>
#include <QPlainTextEdit>
#include <QPushButton>
#include <QScrollArea>
#include <QSignalBlocker>
#include <QSpinBox>
#include <QToolTip>
#include <QVBoxLayout>
#include <algorithm>
#include <cmath>

namespace wb {
using launcher::t;
namespace atlas = launcher::atlas;
namespace {
constexpr int kMaxLanes = 8;
QString shortName(const QString &name) { return comboTargetName(name); }
QString windowText(const QJsonObject &route) {
    const auto w = comboRouteWindow(route);
    return w.second > 0 ? t("frames %1 to %2", "cuadros %1 a %2").arg(w.first).arg(w.second)
                        : t("frame %1 to the end", "cuadro %1 hasta el final").arg(w.first);
}
} // namespace

QColor comboInputColour(const QString &c) {
    if (c == "light") return QColor(96, 200, 140);
    if (c == "heavy") return QColor(240, 128, 64);
    if (c == "special") return QColor(110, 150, 255);
    if (c == "jump") return QColor(240, 210, 80);
    if (c == "grab") return QColor(206, 124, 226);
    if (c == "shield") return QColor(112, 206, 224);
    return QColor(160, 160, 160);
}

// ---- RouteLanes --------------------------------------------------------------------------------------------------
RouteLanes::RouteLanes(QWidget *parent) : QWidget(parent) {
    setObjectName("wbRouteLanes"); setFocusPolicy(Qt::StrongFocus); setMouseTracking(true);
    setAccessibleName(t("Combo routes leaving this move", "Rutas de combo desde este movimiento"));
    setToolTip(t("Combo routes: drag a bar to move its window, drag an end to resize it", "Rutas de combo: arrastra una barra para mover su ventana, un extremo para cambiar su tamaño"));
    setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Fixed);
}
void RouteLanes::setTimeline(TimelineView *timeline) { timeline_ = timeline; update(); }
void RouteLanes::setRoutes(const QString &row, const QStringList &tokens, const QJsonArray &routes) {
    row_ = row; lanes_ = QJsonArray();
    for (const auto &v : routes) {
        const auto route = v.toObject();
        for (const auto &source : comboRouteSources(route))
            if (tokens.contains(source)) { lanes_.append(route); break; }
    }
    if (selected_ >= 0) {
        bool found = false;
        for (const auto &v : lanes_) found |= v.toObject().value("index").toInt() == selected_;
        if (!found) selected_ = -1;
    }
    dragLane_ = -1; grab_ = Grab::None;
    updateGeometry(); update();
}
int RouteLanes::routeIndexAt(int lane) const { return lane >= 0 && lane < lanes_.size() ? lanes_[lane].toObject().value("index").toInt() : -1; }
QSize RouteLanes::sizeHint() const { return {200, qMax(1, qMin(int(lanes_.size()), kMaxLanes) + (lanes_.size() > kMaxLanes ? 1 : 0)) * laneHeight() + 4}; }
QSize RouteLanes::minimumSizeHint() const { return {80, sizeHint().height()}; }
qreal RouteLanes::xOfBoundary(int boundary) const {
    if (!timeline_) return 0;
    return mapFromGlobal(timeline_->mapToGlobal(QPointF(timeline_->framePosition(boundary), 0).toPoint())).x();
}
int RouteLanes::boundaryAt(qreal x) const {
    if (!timeline_ || timeline_->frameCount() <= 0) return 0;
    const qreal local = timeline_->mapFromGlobal(mapToGlobal(QPointF(x, 0).toPoint())).x();
    const auto ruler = timeline_->rulerRect();
    const qreal f = (local - ruler.left()) / ruler.width() * timeline_->frameCount();
    return std::clamp(int(std::lround(f)), 0, timeline_->frameCount());
}
QPair<int, int> RouteLanes::shown(int lane) const {
    if (lane == dragLane_) return {dragLo_, dragHi_};
    return comboRouteWindow(lanes_[lane].toObject());
}
QRectF RouteLanes::barRect(int lane) const {
    if (lane < 0 || lane >= lanes_.size() || !timeline_) return {};
    const auto w = shown(lane);
    const int frames = timeline_->frameCount();
    // A window past the end of the move is drawn at the edge (the Problems list says why it never opens).
    const int endBoundary = w.second > 0 ? qMin(w.second + 1, frames) : frames;
    const qreal x0 = xOfBoundary(qMin(w.first, frames)), x1 = xOfBoundary(endBoundary);
    return {x0, lane * laneHeight() + 3.0, qMax<qreal>(6, x1 - x0), laneHeight() - 6.0};
}
int RouteLanes::laneAt(const QPointF &p) const {
    for (int i = qMin(int(lanes_.size()), kMaxLanes) - 1; i >= 0; --i)
        if (barRect(i).adjusted(-3, 0, 3, 0).contains(p)) return i;
    return -1;
}
void RouteLanes::selectRoute(int routeIndex) { selected_ = routeIndex; update(); }
QString RouteLanes::tipFor(int lane) const {
    const auto r = lanes_[lane].toObject();
    QString tip = QString("%1: %2 %3\n%4").arg(r.value("name").toString(), QString::fromUtf8("→"), comboRouteLabel(r), windowText(r));
    if (!r.value("source").toString().isEmpty()) tip += "\n" + r.value("source").toString();
    return tip;
}
bool RouteLanes::event(QEvent *e) {
    if (e->type() == QEvent::ToolTip) {
        const auto *help = static_cast<QHelpEvent *>(e);
        const int lane = laneAt(help->pos());
        if (lane >= 0) QToolTip::showText(help->globalPos(), tipFor(lane), this); else QToolTip::hideText();
        return true;
    }
    return QWidget::event(e);
}
void RouteLanes::paintEvent(QPaintEvent *) {
    QPainter p(this);
    p.fillRect(rect(), atlas::colour("ground2"));
    p.setFont(atlas::numberFont(11));
    if (lanes_.isEmpty()) {
        p.setPen(atlas::colour("dim"));
        p.drawText(rect().adjusted(8, 0, -8, 0), Qt::AlignLeft | Qt::AlignVCenter,
                   row_.isEmpty() ? QString() : t("No combo routes leave this move", "Ninguna ruta de combo sale de este movimiento"));
        return;
    }
    const QFontMetricsF fm(p.font());
    for (int i = 0; i < qMin(int(lanes_.size()), kMaxLanes); ++i) {
        const auto route = lanes_[i].toObject();
        const QRectF bar = barRect(i);
        QColor fill = comboInputColour(comboInputClass(route));
        const bool on = route.value("index").toInt() == selected_ || i == dragLane_;
        fill.setAlpha(on ? 255 : 185);
        p.fillRect(bar, fill);
        p.setPen(QPen(atlas::colour(on ? "ivory" : "ink"), 1)); p.drawRect(bar.adjusted(0, 0, -1, -1));
        const QString label = QString::fromUtf8("→ ") + comboRouteLabel(route);
        const qreal need = fm.horizontalAdvance(label) + 12;
        if (bar.width() >= need) {
            p.setPen(atlas::colour("ink")); p.drawText(bar.adjusted(6, 0, -4, 0), Qt::AlignLeft | Qt::AlignVCenter, label);
        } else {
            const bool right = bar.right() + need + 4 < width();
            const QRectF where = right ? QRectF(bar.right() + 6, bar.top(), width() - bar.right() - 8, bar.height())
                                       : QRectF(4, bar.top(), qMax<qreal>(20, bar.left() - 10), bar.height());
            p.setPen(atlas::colour("ivory"));
            p.drawText(where, (right ? Qt::AlignLeft : Qt::AlignRight) | Qt::AlignVCenter, atlas::fit(fm, label, where.width()));
        }
    }
    if (lanes_.size() > kMaxLanes) {
        p.setPen(atlas::colour("dim"));
        p.drawText(QRectF(8, kMaxLanes * laneHeight(), width() - 16, laneHeight()), Qt::AlignLeft | Qt::AlignVCenter,
                   t("+%1 more in the Combo tab", "+%1 más en la pestaña Combo").arg(lanes_.size() - kMaxLanes));
    }
}
void RouteLanes::mousePressEvent(QMouseEvent *e) {
    setFocus();
    const int lane = laneAt(e->position());
    if (lane < 0) { selected_ = -1; update(); return; }
    selected_ = routeIndexAt(lane); emit routeSelected(selected_);
    if (e->button() == Qt::LeftButton) {
        const QRectF bar = barRect(lane);
        const auto w = comboRouteWindow(lanes_[lane].toObject());
        dragLane_ = lane; dragLo_ = originLo_ = w.first; dragHi_ = originHi_ = w.second;
        pressBoundary_ = boundaryAt(e->position().x());
        const qreal edge = qMin<qreal>(7, bar.width() / 3);
        grab_ = e->position().x() <= bar.left() + edge ? Grab::Start : e->position().x() >= bar.right() - edge ? Grab::End : Grab::Move;
    }
    update(); e->accept();
}
void RouteLanes::mouseMoveEvent(QMouseEvent *e) {
    if (dragLane_ < 0) {
        const int lane = laneAt(e->position());
        if (lane < 0) { setCursor(Qt::ArrowCursor); return; }
        const QRectF bar = barRect(lane); const qreal edge = qMin<qreal>(7, bar.width() / 3);
        setCursor(e->position().x() <= bar.left() + edge || e->position().x() >= bar.right() - edge ? Qt::SizeHorCursor : Qt::OpenHandCursor);
        return;
    }
    const int frames = timeline_ ? timeline_->frameCount() : 0;
    const int b = boundaryAt(e->position().x());
    if (grab_ == Grab::Start) {
        dragLo_ = std::clamp(b, 1, originHi_ > 0 ? originHi_ : qMax(1, frames)); dragHi_ = originHi_;
    } else if (grab_ == Grab::End) {
        dragLo_ = originLo_;
        dragHi_ = b >= frames ? 0 : qMax(originLo_, b - 1);
    } else {
        const int lo = qMax(1, originLo_ + b - pressBoundary_);
        dragLo_ = lo; dragHi_ = originHi_ > 0 ? originHi_ + (lo - originLo_) : 0;
    }
    update();
}
void RouteLanes::mouseReleaseEvent(QMouseEvent *e) {
    if (dragLane_ < 0) return;
    const int index = routeIndexAt(dragLane_), lo = dragLo_, hi = dragHi_;
    const bool changed = lo != originLo_ || hi != originHi_;
    dragLane_ = -1; grab_ = Grab::None; update(); e->accept();
    if (changed) emit editRequested("edit_route", {{"index", index}, {"window", QJsonArray{lo, hi}}});
}
void RouteLanes::keyPressEvent(QKeyEvent *e) {
    int lane = -1;
    for (int i = 0; i < lanes_.size(); ++i) if (routeIndexAt(i) == selected_) lane = i;
    if (lane < 0) { QWidget::keyPressEvent(e); return; }
    const auto w = comboRouteWindow(lanes_[lane].toObject());
    if (e->key() == Qt::Key_Delete) { emit editRequested("delete_route", {{"index", selected_}}); e->accept(); return; }
    if (e->key() == Qt::Key_Left || e->key() == Qt::Key_Right) {
        const int d = e->key() == Qt::Key_Left ? -1 : 1;
        const int lo = qMax(1, w.first + d), hi = w.second > 0 ? w.second + (lo - w.first) : 0;
        if (lo != w.first) emit editRequested("edit_route", {{"index", selected_}, {"window", QJsonArray{lo, hi}}});
        e->accept(); return;
    }
    QWidget::keyPressEvent(e);
}

// ---- StringMap ---------------------------------------------------------------------------------------------------
namespace {
constexpr qreal kNodeW = 92, kNodeH = 26, kGapX = 36, kGapY = 12, kPad = 12;
}
StringMap::StringMap(QWidget *parent) : QWidget(parent) {
    setObjectName("wbStringMap"); setAccessibleName(t("String map", "Mapa de cadenas"));
    setToolTip(t("Moves are nodes and combo routes are arrows. Click a move to select it.", "Los movimientos son nodos y las rutas de combo, flechas. Haz clic en un movimiento para elegirlo."));
}
void StringMap::setGraph(const QJsonArray &routes, const QJsonArray &strings, const QStringList &moves) {
    routes_ = routes; strings_ = strings; moves_ = moves; graph_ = buildComboGraph(routes, strings);
    if (active_ >= strings_.size()) active_ = -1;
    updateGeometry(); update();
}
void StringMap::setSelectedMove(const QString &name) { selected_ = name; update(); }
void StringMap::setActiveString(int index) { active_ = index; update(); }
QSize StringMap::sizeHint() const {
    return {int(kPad * 2 + graph_.cols * (kNodeW + kGapX) - kGapX), int(kPad * 2 + graph_.rows * (kNodeH + kGapY) - kGapY)};
}
QRectF StringMap::rectOf(int n) const {
    const auto &node = graph_.nodes[n];
    return {kPad + node.col * (kNodeW + kGapX), kPad + node.row * (kNodeH + kGapY), kNodeW, kNodeH};
}
QRectF StringMap::nodeRect(const QString &name) const { const int i = graph_.node(name); return i < 0 ? QRectF() : rectOf(i); }
QString StringMap::nodeAt(const QPointF &p) const {
    for (int i = 0; i < graph_.nodes.size(); ++i) if (rectOf(i).contains(p)) return graph_.nodes[i].name;
    return {};
}
void StringMap::mousePressEvent(QMouseEvent *e) {
    const QString name = nodeAt(e->position());
    if (name.isEmpty()) return;
    emit nodeClicked(name);
    if (moves_.contains(name)) emit moveClicked(name);
    e->accept();
}
void StringMap::paintEvent(QPaintEvent *) {
    QPainter p(this); p.setRenderHint(QPainter::Antialiasing, true);
    p.fillRect(rect(), atlas::colour("ground2"));
    if (graph_.nodes.isEmpty()) {
        p.setPen(atlas::colour("dim"));
        p.drawText(rect().adjusted(8, 0, -8, 0), Qt::AlignLeft | Qt::AlignVCenter, t("No combo routes", "Sin rutas de combo"));
        return;
    }
    // The active string's consecutive steps, to draw their edges bold.
    QSet<QPair<int, int>> bold;
    if (active_ >= 0 && active_ < strings_.size()) {
        const auto steps = strings_[active_].toObject().value("steps").toArray();
        for (int i = 0; i + 1 < steps.size(); ++i) bold.insert({graph_.node(steps[i].toString()), graph_.node(steps[i + 1].toString())});
    }
    for (int e = 0; e < graph_.edges.size(); ++e) {
        const auto &edge = graph_.edges[e];
        const QRectF a = rectOf(edge.from), b = rectOf(edge.to);
        QColor colour = comboInputColour(edge.input);
        const bool isBold = bold.contains({edge.from, edge.to});
        colour.setAlpha(isBold ? 255 : (bold.isEmpty() ? 200 : 90));
        p.setPen(QPen(colour, isBold ? 3.0 : 1.5));
        QPainterPath path;
        // Parallel edges between the same pair fan out a little.
        int same = 0; for (int k = 0; k < e; ++k) if (graph_.edges[k].from == edge.from && graph_.edges[k].to == edge.to) ++same;
        const qreal fan = same * 5.0;
        QPointF from, to;
        if (b.left() > a.right()) {
            from = QPointF(a.right(), a.center().y() + fan); to = QPointF(b.left(), b.center().y() + fan);
            path.moveTo(from); path.cubicTo(from + QPointF(kGapX * 0.5, 0), to - QPointF(kGapX * 0.5, 0), to);
        } else {
            // Same column or backwards: an arc round the right-hand side of the nodes.
            from = QPointF(a.right(), a.center().y() + fan); to = QPointF(b.right(), b.center().y() + fan);
            path.moveTo(from); path.cubicTo(from + QPointF(kGapX * 0.9, 0), to + QPointF(kGapX * 0.9, 0), to);
        }
        p.drawPath(path);
        const QPointF dir = b.left() > a.right() ? QPointF(1, 0) : QPointF(-1, 0);
        QPolygonF head; head << to << to - dir * 7 + QPointF(0, 3.5) << to - dir * 7 - QPointF(0, 3.5);
        p.setBrush(colour); p.setPen(Qt::NoPen); p.drawPolygon(head); p.setBrush(Qt::NoBrush);
    }
    p.setFont(atlas::numberFont(10));
    const QFontMetricsF fm(p.font());
    for (int i = 0; i < graph_.nodes.size(); ++i) {
        const auto &name = graph_.nodes[i].name;
        const QRectF r = rectOf(i);
        const bool real = moves_.contains(name), sel = name == selected_;
        p.setPen(QPen(atlas::colour(sel ? "ember" : "line2"), sel ? 2 : 1));
        p.setBrush(atlas::colour(real ? "plate2" : "ground"));
        p.drawRoundedRect(r, 4, 4);
        p.setPen(atlas::colour(real ? "ivory" : "dim"));
        p.drawText(r.adjusted(5, 0, -5, 0), Qt::AlignCenter, atlas::fit(fm, shortName(name), r.width() - 10));
    }
}

// ---- ComboPanel --------------------------------------------------------------------------------------------------
namespace {
QComboBox *vocabulary(const QStringList &items, const QString &name) {
    auto *box = new QComboBox; box->setObjectName(name); box->setAccessibleName(name); box->addItems(items);
    box->setSizeAdjustPolicy(QComboBox::AdjustToMinimumContentsLengthWithIcon); box->setMinimumContentsLength(6);
    box->setSizePolicy(QSizePolicy::Ignored, QSizePolicy::Fixed); return box;
}
}
ComboPanel::ComboPanel(QWidget *parent) : QWidget(parent) {
    setObjectName("wbCombo"); setAccessibleName(t("Combo", "Combo"));
    auto *outer = new QVBoxLayout(this); outer->setContentsMargins(0, 0, 0, 0);
    auto *scroll = new QScrollArea; scroll->setWidgetResizable(true); scroll->setFrameShape(QFrame::NoFrame);
    scroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff); outer->addWidget(scroll);
    auto *body = new QWidget; body->setObjectName("wbComboBody"); scroll->setWidget(body);
    auto *layout = new QVBoxLayout(body); layout->setContentsMargins(16, 16, 16, 16); layout->setSpacing(10);
    note_ = new QLabel; note_->setWordWrap(true); note_->setObjectName("wbComboNote"); layout->addWidget(note_);
    layout->addWidget(new QLabel(t("Routes", "Rutas")));
    all_ = new QCheckBox(t("All routes", "Todas las rutas")); all_->setObjectName("wbComboAll");
    layout->addWidget(all_);
    list_ = new QListWidget; list_->setObjectName("wbComboRoutes"); list_->setMinimumHeight(120);
    list_->setAccessibleName(t("Routes", "Rutas")); layout->addWidget(list_);
    auto *buttons = new QHBoxLayout; layout->addLayout(buttons);
    add_ = new AtlasButton(t("+ Route", "+ Ruta")); add_->setObjectName("wbComboAdd");
    remove_ = new AtlasButton(t("Delete route", "Borrar ruta")); remove_->setObjectName("wbComboDelete");
    buttons->addWidget(add_); buttons->addWidget(remove_); buttons->addStretch();
    form_ = new QWidget; form_->setObjectName("wbComboForm"); layout->addWidget(form_);
    auto *form = new QFormLayout(form_); form->setContentsMargins(0, 0, 0, 0);
    form->setRowWrapPolicy(QFormLayout::WrapLongRows); form->setFieldGrowthPolicy(QFormLayout::AllNonFixedFieldsGrow);
    name_ = new QLineEdit; name_->setObjectName("wbComboName"); form->addRow(t("Name", "Nombre"), name_);
    from_ = new QLineEdit; from_->setObjectName("wbComboFrom"); from_->setToolTip(t("One move, or several separated by commas", "Un movimiento, o varios separados por comas"));
    form->addRow(t("From", "Desde"), from_);
    to_ = new QLineEdit; to_->setObjectName("wbComboTo"); form->addRow(t("To", "Hacia"), to_);
    input_ = vocabulary(comboInputs(), "wbComboInput"); form->addRow(t("Input", "Entrada"), input_);
    dir_ = vocabulary(comboDirs(), "wbComboDir"); form->addRow(t("Direction", "Dirección"), dir_);
    on_ = vocabulary(comboOns(), "wbComboOn"); form->addRow(t("When", "Cuándo"), on_);
    where_ = vocabulary(comboWheres(), "wbComboWhere"); form->addRow(t("Where", "Dónde"), where_);
    lo_ = new QSpinBox; lo_->setObjectName("wbComboLo"); lo_->setRange(1, 9999); lo_->setKeyboardTracking(false);
    hi_ = new QSpinBox; hi_->setObjectName("wbComboHi"); hi_->setRange(0, 9999); hi_->setSpecialValueText(t("to the end", "hasta el final")); hi_->setKeyboardTracking(false);
    auto *window = new QHBoxLayout; window->addWidget(lo_); window->addWidget(new QLabel(t("to", "a"))); window->addWidget(hi_);
    form->addRow(t("Window (frames)", "Ventana (cuadros)"), window);
    buffer_ = new QSpinBox; buffer_->setObjectName("wbComboBuffer"); buffer_->setRange(0, 60); buffer_->setKeyboardTracking(false);
    buffer_->setToolTip(t("Frames a press stays usable (the combo default when not set)", "Cuadros que una pulsación sigue siendo válida"));
    form->addRow(t("Buffer", "Búfer"), buffer_);
    priority_ = new QSpinBox; priority_->setObjectName("wbComboPriority"); priority_->setRange(-99, 99); priority_->setKeyboardTracking(false);
    form->addRow(t("Priority", "Prioridad"), priority_);
    kiCost_ = new QSpinBox; kiCost_->setObjectName("wbComboKi"); kiCost_->setRange(0, 100); kiCost_->setKeyboardTracking(false);
    form->addRow(t("Ki cost", "Coste de ki"), kiCost_);
    layout->addWidget(new QLabel(t("Source (where this route comes from)", "Origen (de dónde viene esta ruta)")));
    source_ = new QPlainTextEdit; source_->setObjectName("wbComboSource"); source_->setReadOnly(true); source_->setMaximumHeight(96);
    source_->setAccessibleName(t("Route source", "Origen de la ruta")); layout->addWidget(source_);
    moveNote_ = new QLabel; moveNote_->setWordWrap(true); moveNote_->setObjectName("wbComboMoveNote"); layout->addWidget(moveNote_);

    layout->addWidget(new QLabel(t("Strings", "Cadenas")));
    stringList_ = new QListWidget; stringList_->setObjectName("wbComboStrings"); stringList_->setMinimumHeight(80); layout->addWidget(stringList_);
    auto *stringForm = new QFormLayout; layout->addLayout(stringForm);
    stringName_ = new QLineEdit; stringName_->setObjectName("wbComboStringName"); stringForm->addRow(t("Name", "Nombre"), stringName_);
    stepsEdit_ = new QLineEdit; stepsEdit_->setObjectName("wbComboSteps"); stepsEdit_->setToolTip(t("Moves in order, separated by commas", "Movimientos en orden, separados por comas"));
    stringForm->addRow(t("Steps", "Pasos"), stepsEdit_);
    auto *stringButtons = new QHBoxLayout; layout->addLayout(stringButtons);
    addString_ = new AtlasButton(t("+ String", "+ Cadena")); addString_->setObjectName("wbComboAddString");
    removeString_ = new AtlasButton(t("Delete string", "Borrar cadena")); removeString_->setObjectName("wbComboDeleteString");
    play_ = new AtlasButton(t("Play string", "Reproducir cadena")); play_->setObjectName("wbComboPlay");
    play_->setToolTip(t("Plays the string's moves back to back in the game, cutting at each route's window. Blender has its own Play string (Geno > Combo).",
                        "Reproduce los movimientos de la cadena seguidos en el juego, cortando en la ventana de cada ruta. Blender tiene su propio Reproducir cadena (Geno > Combo)."));
    stringButtons->addWidget(addString_); stringButtons->addWidget(removeString_); stringButtons->addStretch();
    auto *playRow = new QHBoxLayout; layout->addLayout(playRow); playRow->addWidget(play_); playRow->addStretch();
    layout->addWidget(new QLabel(t("String map", "Mapa de cadenas")));
    map_ = new StringMap;
    auto *mapScroll = new QScrollArea; mapScroll->setObjectName("wbComboMapScroll"); mapScroll->setWidgetResizable(false); mapScroll->setFrameShape(QFrame::NoFrame);
    mapScroll->setWidget(map_); mapScroll->setMinimumHeight(210); mapScroll->setVerticalScrollBarPolicy(Qt::ScrollBarAsNeeded);
    layout->addWidget(mapScroll);
    layout->addStretch();

    connect(all_, &QCheckBox::toggled, this, [this] { rebuildList(); });
    connect(list_, &QListWidget::currentRowChanged, this, [this](int) {
        rebuildForm(); if (!feedback_) emit routeSelected(selectedRoute());
    });
    connect(add_, &QPushButton::clicked, this, [this] {
        QString to;
        for (const auto &m : moves_) if (m != row_) { to = m; break; }
        if (to.isEmpty()) to = row_;
        emit editRequested("add_route", {{"route", QJsonObject{{"name", QString("%1>%2").arg(row_.isEmpty() ? QString("move") : row_, to)},
            {"from", row_.isEmpty() ? to : row_}, {"to", to}, {"input", "light"}, {"on", "hit"}, {"where", "any"}, {"window", QJsonArray{1, 0}}}}});
    });
    connect(remove_, &QPushButton::clicked, this, [this] { const int i = selectedRoute(); if (i >= 0) emit editRequested("delete_route", {{"index", i}}); });
    connect(name_, &QLineEdit::editingFinished, this, [this] { if (!feedback_ && name_->text() != current().value("name").toString()) edit("name", name_->text()); });
    connect(to_, &QLineEdit::editingFinished, this, [this] { if (!feedback_ && to_->text() != current().value("to").toString()) edit("to", to_->text().trimmed()); });
    connect(from_, &QLineEdit::editingFinished, this, [this] {
        if (feedback_) return;
        QStringList parts; for (const auto &p : from_->text().split(',', Qt::SkipEmptyParts)) parts << p.trimmed();
        if (parts == comboRouteSources(current())) return;
        if (parts.size() == 1) edit("from", parts[0]); else edit("from", QJsonArray::fromStringList(parts));
    });
    const auto bindBox = [this](QComboBox *box, const char *key) {
        connect(box, &QComboBox::activated, this, [this, box, key] { if (!feedback_ && box->currentText() != current().value(key).toString()) edit(key, box->currentText()); });
    };
    bindBox(input_, "input"); bindBox(dir_, "dir"); bindBox(on_, "on"); bindBox(where_, "where");
    connect(lo_, &QSpinBox::valueChanged, this, [this] { if (!feedback_) editWindow(); });
    connect(hi_, &QSpinBox::valueChanged, this, [this] { if (!feedback_) editWindow(); });
    connect(buffer_, &QSpinBox::valueChanged, this, [this](int v) { if (!feedback_) edit("buffer", v); });
    connect(priority_, &QSpinBox::valueChanged, this, [this](int v) { if (!feedback_) edit("priority", v); });
    connect(kiCost_, &QSpinBox::valueChanged, this, [this](int v) { if (!feedback_) edit("ki_cost", v); });
    connect(stringList_, &QListWidget::currentRowChanged, this, [this](int) {
        const auto s = selectedString() >= 0 ? strings_[selectedString()].toObject() : QJsonObject();
        feedback_ = true;
        stringName_->setText(s.value("name").toString());
        QStringList steps; for (const auto &v : s.value("steps").toArray()) steps << v.toString();
        stepsEdit_->setText(steps.join(", "));
        feedback_ = false;
        play_->setEnabled(selectedString() >= 0); removeString_->setEnabled(selectedString() >= 0);
        map_->setActiveString(selectedString());
    });
    connect(stringName_, &QLineEdit::editingFinished, this, [this] {
        const int i = selectedString();
        if (!feedback_ && i >= 0 && stringName_->text() != strings_[i].toObject().value("name").toString())
            emit editRequested("edit_string", {{"index", i}, {"name", stringName_->text()}});
    });
    connect(stepsEdit_, &QLineEdit::editingFinished, this, [this] {
        const int i = selectedString(); if (feedback_ || i < 0) return;
        QStringList parts; for (const auto &p : stepsEdit_->text().split(',', Qt::SkipEmptyParts)) parts << p.trimmed();
        QStringList was; for (const auto &v : strings_[i].toObject().value("steps").toArray()) was << v.toString();
        if (parts != was) emit editRequested("edit_string", {{"index", i}, {"steps", QJsonArray::fromStringList(parts)}});
    });
    connect(addString_, &QPushButton::clicked, this, [this] {
        emit editRequested("add_string", {{"string", QJsonObject{{"name", t("New string", "Cadena nueva")},
            {"steps", QJsonArray{row_.isEmpty() && !moves_.isEmpty() ? moves_.first() : row_}}}}});
    });
    connect(removeString_, &QPushButton::clicked, this, [this] { const int i = selectedString(); if (i >= 0) emit editRequested("delete_string", {{"index", i}}); });
    connect(play_, &QPushButton::clicked, this, [this] { const int i = selectedString(); if (i >= 0) emit playStringRequested(i); });
    connect(map_, &StringMap::moveClicked, this, [this](const QString &name) { moveNote_->clear(); emit moveRequested(name); });
    connect(map_, &StringMap::nodeClicked, this, [this](const QString &name) {
        if (!moves_.contains(name))
            moveNote_->setText(t("%1 is a state of the combo graph with no row in the Moves list.", "%1 es un estado del grafo de combos sin fila en la lista de movimientos.").arg(shortName(name)));
    });
    rebuildForm();
}
int ComboPanel::selectedRoute() const {
    const auto *item = list_->currentItem();
    return item ? item->data(Qt::UserRole).toInt() : -1;
}
int ComboPanel::selectedString() const { const int r = stringList_->currentRow(); return r >= 0 && r < strings_.size() ? r : -1; }
void ComboPanel::selectRoute(int routeIndex) {
    for (int i = 0; i < list_->count(); ++i)
        if (list_->item(i)->data(Qt::UserRole).toInt() == routeIndex) { list_->setCurrentRow(i); return; }
}
QJsonObject ComboPanel::current() const {
    const int i = selectedRoute();
    return i >= 0 && i < routes_.size() ? routes_[i].toObject() : QJsonObject();
}
void ComboPanel::edit(const QString &key, const QJsonValue &value) {
    const int i = selectedRoute(); if (i < 0) return;
    emit editRequested("edit_route", {{"index", i}, {key, value}});
}
void ComboPanel::editWindow() {
    const auto w = comboRouteWindow(current());
    if (lo_->value() == w.first && hi_->value() == w.second) return;
    int hi = hi_->value();
    if (hi != 0 && hi < lo_->value()) hi = lo_->value();
    edit("window", QJsonArray{lo_->value(), hi});
}
void ComboPanel::setData(const QJsonArray &routes, const QJsonArray &strings, const QJsonObject &meta, const QStringList &moves,
                         const QString &row, const QStringList &tokens, bool declared) {
    const int keepRoute = selectedRoute(), keepString = selectedString();
    routes_ = routes; strings_ = strings; meta_ = meta; moves_ = moves; row_ = row; tokens_ = tokens; declared_ = declared;
    rebuildList();
    rebuildStrings();
    if (keepRoute >= 0) selectRoute(keepRoute);
    if (keepString >= 0 && keepString < stringList_->count()) stringList_->setCurrentRow(keepString);
    map_->setGraph(routes_, strings_, moves_); map_->setSelectedMove(row_); map_->setActiveString(selectedString());
    map_->resize(map_->sizeHint());
    note_->setText(!declared_ ? t("This project declares no combo graph (workbench.json \"combo\").", "Este proyecto no declara un grafo de combos (workbench.json \"combo\").")
                              : t("Routes are cancels the attacker takes. Edits go to the source; Rebuild + reload applies them in the game.",
                                  "Las rutas son cancelaciones del atacante. Los cambios van al código fuente; reconstruye y recarga para verlos en el juego."));
}
void ComboPanel::rebuildList() {
    feedback_ = true;
    const int keep = selectedRoute();
    list_->clear();
    for (const auto &v : routes_) {
        const auto r = v.toObject();
        bool mine = row_.isEmpty() || all_->isChecked();
        for (const auto &s : comboRouteSources(r)) if (tokens_.contains(s)) mine = true;
        if (!mine) continue;
        auto *item = new QListWidgetItem(QString("%1   → %2").arg(r.value("name").toString(), comboRouteLabel(r)));
        item->setData(Qt::UserRole, r.value("index").toInt());
        item->setForeground(comboInputColour(comboInputClass(r)));
        item->setToolTip(r.value("source").toString());
        list_->addItem(item);
    }
    add_->setEnabled(declared_);
    feedback_ = false;
    if (keep >= 0) selectRoute(keep);
    if (list_->currentRow() < 0 && list_->count()) list_->setCurrentRow(0);
    rebuildForm();
}
void ComboPanel::rebuildStrings() {
    feedback_ = true;
    const int keep = stringList_->currentRow();
    stringList_->clear();
    for (const auto &v : strings_) {
        const auto s = v.toObject();
        stringList_->addItem(QString("%1  (%2)").arg(s.value("name").toString()).arg(s.value("steps").toArray().size()));
    }
    feedback_ = false;
    addString_->setEnabled(declared_);
    if (stringList_->count()) stringList_->setCurrentRow(std::clamp(keep, 0, stringList_->count() - 1));
    play_->setEnabled(selectedString() >= 0); removeString_->setEnabled(selectedString() >= 0);
}
void ComboPanel::rebuildForm() {
    feedback_ = true;
    const auto r = current(); const bool has = !r.isEmpty();
    form_->setEnabled(has); remove_->setEnabled(has); source_->setEnabled(has);
    name_->setText(r.value("name").toString());
    from_->setText(comboRouteSources(r).join(", "));
    to_->setText(r.value("to").toString());
    const auto pick = [&](QComboBox *box, const char *key, const char *def) {
        const int i = box->findText(r.contains(key) ? r.value(key).toString() : QString(def)); box->setCurrentIndex(qMax(0, i));
    };
    pick(input_, "input", "light"); pick(dir_, "dir", "any"); pick(on_, "on", "hit"); pick(where_, "where", "any");
    const auto w = comboRouteWindow(r);
    lo_->setValue(w.first); hi_->setValue(w.second);
    buffer_->setValue(r.contains("buffer") ? r.value("buffer").toInt() : meta_.value("buffer").toInt(5));
    priority_->setValue(r.value("priority").toInt()); kiCost_->setValue(r.value("ki_cost").toInt());
    source_->setPlainText(has ? (r.value("source").toString().isEmpty() ? t("(no source recorded)", "(sin origen registrado)") : r.value("source").toString()) : QString());
    moveNote_->clear();
    feedback_ = false;
}
} // namespace wb
