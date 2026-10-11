#include "projectile_widgets.h"
#include "atlas.h"
#include "atlas_widgets.h"
#include "window.h"
#include <QCheckBox>
#include <QComboBox>
#include <QDoubleSpinBox>
#include <QFormLayout>
#include <QHBoxLayout>
#include <QHeaderView>
#include <QKeyEvent>
#include <QLabel>
#include <QListWidget>
#include <QMouseEvent>
#include <QPainter>
#include <QPushButton>
#include <QScrollArea>
#include <QSignalBlocker>
#include <QSpinBox>
#include <QTableWidget>
#include <QVBoxLayout>
#include <algorithm>
#include <cmath>

namespace wb {
using launcher::t;
namespace atlas = launcher::atlas;
namespace {
const QColor kSpawn(255, 180, 60);
// Per-article scalar fields: path, label, kind (i int, f float), minimum, maximum, default.
struct Field { const char *path, *label, *kind; double lo, hi, def; };
const Field kFields[] = {
    {"lifetime", "Lifetime (frames)", "i", 1, 9999, 60},
    {"velocity/0", "Speed forward", "f", -99, 99, 0},
    {"velocity/1", "Speed up", "f", -99, 99, 0},
    {"angle", "Launch angle (deg)", "f", -360, 360, 0},
    {"gravity", "Gravity", "f", -9.99, 9.99, 0},
    {"max_fall", "Max fall speed", "f", 0, 99, 0},
    {"accel", "Acceleration", "f", -9.99, 9.99, 0},
    {"max_speed", "Max speed", "f", 0, 99, 0},
    {"min_speed", "Min speed (brake)", "f", 0, 99, 0},
    {"spawn/0", "Spawn forward", "f", -999, 999, 0},
    {"spawn/1", "Spawn up", "f", -999, 999, 0},
    {"scale", "Model scale", "f", 0.01, 99, 1},
    {"max_live", "Max live", "i", 1, 64, 4},
    {"bone", "Spawn bone (part, -1 none)", "i", -1, 127, -1},
    {"homing/turn", "Homing turn (deg/frame)", "f", 0, 180, 0},
    {"homing/range", "Homing range", "f", 0, 999, 0},
    {"homing/delay", "Homing delay", "i", 0, 9999, 0},
};
const char *kDespawn[] = {"hit", "shield", "stage", "clank"};
double leaf(const QJsonObject &article, const QString &path, double def) {
    const auto parts = path.split('/');
    if (parts.size() == 1) return article.contains(parts[0]) ? article[parts[0]].toDouble(def) : def;
    const auto v = article.value(parts[0]);
    if (v.isArray()) { const auto a = v.toArray(); const int i = parts[1].toInt(); return i < a.size() ? a[i].toDouble(def) : def; }
    return v.toObject().contains(parts[1]) ? v.toObject()[parts[1]].toDouble(def) : def;
}
// Hitbox columns: key (array element as key/i), header, kind, default.
struct Col { const char *key, *head, *kind; double def; };
const Col kCols[] = {
    {"slot", "Slot", "i", 0}, {"damage", "Dmg", "f", 1}, {"size", "Size", "f", 3},
    {"offset/0", "X", "f", 0}, {"offset/1", "Y", "f", 0}, {"offset/2", "Z", "f", 0},
    {"angle", "Angle", "i", 361}, {"kbg", "KBG", "i", 100}, {"bkb", "BKB", "i", 0},
    {"start", "From", "i", 1}, {"end", "To", "i", 0},
};
QString number(double v) { return QString::number(v, 'g', 6); }
} // namespace

// ---- SpawnLane ---------------------------------------------------------------------------------------------------
SpawnLane::SpawnLane(QWidget *parent) : QWidget(parent) {
    setObjectName("wbSpawnLane"); setFocusPolicy(Qt::StrongFocus); setMouseTracking(true);
    setAccessibleName(t("Projectile spawns", "Lanzamientos de proyectil"));
    setToolTip(t("Projectile spawns: drag a marker to change the frame it fires on", "Lanzamientos de proyectil: arrastra un marcador para cambiar su fotograma"));
}
void SpawnLane::setTimeline(TimelineView *timeline) { timeline_ = timeline; update(); }
void SpawnLane::setSpawns(const QString &row, const QJsonArray &spawns, const QStringList &names) {
    row_ = row; names_ = names; spawns_ = QJsonArray();
    for (const auto &v : spawns) if (v.toObject().value("row").toString() == row) spawns_.append(v);
    if (selected_ >= spawns_.size()) selected_ = -1;
    dragging_ = -1; update();
}
qreal SpawnLane::xOfFrame(int frame) const {
    if (!timeline_) return 0;
    const QPointF global = timeline_->mapToGlobal(QPointF(timeline_->framePosition(frame), 0).toPoint());
    return mapFromGlobal(global).x();
}
int SpawnLane::frameAt(qreal x) const {
    if (!timeline_ || timeline_->frameCount() <= 0) return 0;
    const qreal local = timeline_->mapFromGlobal(mapToGlobal(QPointF(x, 0).toPoint())).x();
    const auto ruler = timeline_->rulerRect();
    const qreal f = (local - ruler.left()) / ruler.width() * timeline_->frameCount();
    return std::clamp(int(std::lround(f)), 0, std::max(0, timeline_->frameCount() - 1));
}
QRectF SpawnLane::chipRect(int ordinal) const {
    for (int i = 0; i < spawns_.size(); ++i) {
        const auto o = spawns_[i].toObject();
        if (o["ordinal"].toInt() != ordinal) continue;
        const int frame = dragging_ == i ? dragFrame_ : o["frame"].toInt();
        const int article = o["article"].toInt();
        const QString text = article >= 0 && article < names_.size() ? names_[article] : QString("#%1").arg(article);
        const qreal w = std::max<qreal>(46, fontMetrics().horizontalAdvance(text) + 22);
        return {xOfFrame(frame) - 6, 4, w, qreal(height() - 8)};
    }
    return {};
}
int SpawnLane::hit(const QPointF &p) const {
    for (int i = spawns_.size() - 1; i >= 0; --i)
        if (chipRect(spawns_[i].toObject()["ordinal"].toInt()).contains(p)) return i;
    return -1;
}
void SpawnLane::paintEvent(QPaintEvent *) {
    QPainter p(this); p.setRenderHint(QPainter::Antialiasing, false);
    p.fillRect(rect(), atlas::colour("ground2"));
    p.setFont(atlas::numberFont(11));
    if (spawns_.isEmpty()) {
        p.setPen(atlas::colour("dim"));
        p.drawText(rect().adjusted(8, 0, -8, 0), Qt::AlignLeft | Qt::AlignVCenter,
                   row_.isEmpty() ? QString() : t("No projectile spawns in this move", "Este movimiento no lanza proyectiles"));
        return;
    }
    for (int i = 0; i < spawns_.size(); ++i) {
        const auto o = spawns_[i].toObject();
        const QRectF r = chipRect(o["ordinal"].toInt());
        const int article = o["article"].toInt();
        const QString name = article >= 0 && article < names_.size() ? names_[article] : QString("#%1").arg(article);
        QColor fill = kSpawn; fill.setAlpha(i == selected_ || i == dragging_ ? 255 : 190);
        p.fillRect(r, fill);
        p.setPen(QPen(atlas::colour("ink"), 1)); p.drawRect(r.adjusted(0, 0, -1, -1));
        p.drawText(r.adjusted(8, 0, -4, 0), Qt::AlignLeft | Qt::AlignVCenter, name);
        p.fillRect(QRectF(r.left(), r.top(), 3, r.height()), atlas::colour("ink"));
    }
}
void SpawnLane::mousePressEvent(QMouseEvent *e) {
    setFocus(); const int i = hit(e->position());
    selected_ = i; dragging_ = -1;
    if (i >= 0 && e->button() == Qt::LeftButton) {
        dragging_ = i; dragFrame_ = spawns_[i].toObject()["frame"].toInt();
        grab_ = e->position().x() - chipRect(spawns_[i].toObject()["ordinal"].toInt()).left();
        emit spawnSelected(spawns_[i].toObject()["ordinal"].toInt());
    }
    update(); e->accept();
}
void SpawnLane::mouseMoveEvent(QMouseEvent *e) {
    if (dragging_ < 0) { setCursor(hit(e->position()) >= 0 ? Qt::SizeHorCursor : Qt::ArrowCursor); return; }
    const int f = frameAt(e->position().x() - grab_ + 6);
    if (f != dragFrame_) { dragFrame_ = f; update(); }
}
void SpawnLane::mouseReleaseEvent(QMouseEvent *e) {
    if (dragging_ < 0) return;
    const auto o = spawns_[dragging_].toObject();
    const int ordinal = o["ordinal"].toInt(), was = o["frame"].toInt(), now = dragFrame_;
    dragging_ = -1; update(); e->accept();
    if (now != was) emit editRequested("edit_spawn", {{"row", row_}, {"ordinal", ordinal}, {"frame", now}});
}
void SpawnLane::keyPressEvent(QKeyEvent *e) {
    if (selected_ < 0 || selected_ >= spawns_.size()) { QWidget::keyPressEvent(e); return; }
    const auto o = spawns_[selected_].toObject();
    if (e->key() == Qt::Key_Delete || e->key() == Qt::Key_Backspace) {
        emit editRequested("delete_spawn", {{"row", row_}, {"ordinal", o["ordinal"].toInt()}}); e->accept(); return;
    }
    if (e->key() == Qt::Key_Left || e->key() == Qt::Key_Right) {
        const int to = std::max(0, o["frame"].toInt() + (e->key() == Qt::Key_Left ? -1 : 1));
        emit editRequested("edit_spawn", {{"row", row_}, {"ordinal", o["ordinal"].toInt()}, {"frame", to}}); e->accept(); return;
    }
    QWidget::keyPressEvent(e);
}

// ---- ProjectilesPanel ---------------------------------------------------------------------------------------------
ProjectilesPanel::ProjectilesPanel(QWidget *parent) : QWidget(parent) {
    setObjectName("wbProjectiles"); setAccessibleName(t("Projectiles", "Proyectiles"));
    auto *outer = new QVBoxLayout(this); outer->setContentsMargins(0, 0, 0, 0);
    auto *scroll = new QScrollArea; scroll->setWidgetResizable(true); scroll->setFrameShape(QFrame::NoFrame);
    scroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff); outer->addWidget(scroll);
    auto *body = new QWidget; body->setObjectName("wbProjectilesBody"); scroll->setWidget(body);
    auto *layout = new QVBoxLayout(body); layout->setContentsMargins(16, 16, 16, 16); layout->setSpacing(10);
    note_ = new QLabel; note_->setWordWrap(true); note_->setObjectName("wbProjectilesNote"); layout->addWidget(note_);
    list_ = new QListWidget; list_->setObjectName("wbProjectileList"); list_->setMinimumHeight(110);
    list_->setAccessibleName(t("Projectiles", "Proyectiles")); layout->addWidget(list_);
    auto *listButtons = new QHBoxLayout; layout->addLayout(listButtons);
    addArticle_ = new AtlasButton(t("+ Projectile", "+ Proyectil")); addArticle_->setObjectName("wbAddProjectile");
    removeArticle_ = new AtlasButton(t("Delete last", "Borrar el último")); removeArticle_->setObjectName("wbDeleteProjectile");
    listButtons->addWidget(addArticle_); listButtons->addWidget(removeArticle_); listButtons->addStretch();
    form_ = new QWidget; form_->setObjectName("wbProjectileForm"); layout->addWidget(form_);
    auto *form = new QFormLayout(form_); form->setContentsMargins(0, 0, 0, 0);
    for (const auto &f : kFields) {
        QWidget *editor;
        if (QString(f.kind) == "i") {
            auto *s = new QSpinBox; s->setRange(int(f.lo), int(f.hi)); s->setKeyboardTracking(false); editor = s;
            connect(s, &QSpinBox::valueChanged, this, [this, path = QString(f.path)](int v) { if (!feedback_) setOp(path, v); });
        } else {
            auto *s = new QDoubleSpinBox; s->setRange(f.lo, f.hi); s->setDecimals(3); s->setSingleStep(0.1); s->setKeyboardTracking(false); editor = s;
            connect(s, &QDoubleSpinBox::valueChanged, this, [this, path = QString(f.path)](double v) { if (!feedback_) setOp(path, v); });
        }
        editor->setObjectName(QString("wbProj_") + QString(f.path).replace('/', '_')); editor->setAccessibleName(t(f.label, f.label));
        editors_.insert(f.path, editor); form->addRow(t(f.label, f.label), editor);
    }
    for (const char *name : kDespawn) {
        auto *box = new QCheckBox(t("Despawn on ", "Desaparece al ") + QString(name));
        box->setObjectName(QString("wbProj_despawn_") + name);
        connect(box, &QCheckBox::toggled, this, [this, name](bool on) { if (!feedback_) setOp(QString("despawn/") + name, on); });
        editors_.insert(QString("despawn/") + name, box); form->addRow(box);
    }
    layout->addWidget(new QLabel(t("Hitboxes (offset from the projectile, size is the radius)", "Hitboxes (desde el proyectil; el tamaño es el radio)")));
    boxes_ = new QTableWidget(0, int(std::size(kCols))); boxes_->setObjectName("wbProjectileBoxes");
    QStringList heads; for (const auto &c : kCols) heads << c.head;
    boxes_->setHorizontalHeaderLabels(heads); boxes_->verticalHeader()->setVisible(false);
    boxes_->horizontalHeader()->setSectionResizeMode(QHeaderView::Stretch); boxes_->setMinimumHeight(140);
    layout->addWidget(boxes_);
    auto *boxButtons = new QHBoxLayout; layout->addLayout(boxButtons);
    addBox_ = new AtlasButton(t("+ Hitbox", "+ Hitbox")); addBox_->setObjectName("wbProjAddHitbox");
    removeBox_ = new AtlasButton(t("Delete hitbox", "Borrar hitbox")); removeBox_->setObjectName("wbProjRemoveHitbox");
    boxButtons->addWidget(addBox_); boxButtons->addWidget(removeBox_); boxButtons->addStretch();
    layout->addWidget(new QLabel(t("Spawns in this move (also on the timeline)", "Lanzamientos en este movimiento (también en la línea de tiempo)")));
    spawnList_ = new QListWidget; spawnList_->setObjectName("wbProjSpawnList"); spawnList_->setMinimumHeight(70); layout->addWidget(spawnList_);
    auto *spawnButtons = new QHBoxLayout; layout->addLayout(spawnButtons);
    addSpawn_ = new AtlasButton(t("+ Spawn at this frame", "+ Lanzar en este fotograma")); addSpawn_->setObjectName("wbProjAddSpawn");
    removeSpawn_ = new AtlasButton(t("Delete spawn", "Borrar lanzamiento")); removeSpawn_->setObjectName("wbProjRemoveSpawn");
    spawnButtons->addWidget(addSpawn_); spawnButtons->addWidget(removeSpawn_); spawnButtons->addStretch();
    layout->addStretch();

    connect(list_, &QListWidget::currentRowChanged, this, [this](int) { rebuildFields(); });
    connect(addArticle_, &QPushButton::clicked, this, [this] {
        QStringList names = articleNames(); QString name; int n = int(articles_.size()) + 1;
        do name = QString("Projectile%1").arg(n++); while (names.contains(name));
        emit editRequested("add_article", {{"article", QJsonObject{{"name", name}, {"lifetime", 40}, {"velocity", QJsonArray{2.0, 0}},
            {"spawn", QJsonArray{8, 8}}, {"max_live", 2}, {"hitboxes", QJsonArray{QJsonObject{{"slot", 0}, {"damage", 5}, {"size", 3.0},
            {"offset", QJsonArray{0, 0, 0}}, {"angle", 361}, {"kbg", 50}, {"bkb", 20}, {"start", 1}, {"end", 0}}}}}}});
    });
    connect(removeArticle_, &QPushButton::clicked, this, [this] {
        if (!articles_.isEmpty()) emit editRequested("delete_article", {{"index", int(articles_.size()) - 1}});
    });
    connect(addBox_, &QPushButton::clicked, this, [this] {
        const int i = selectedArticle(); if (i < 0) return;
        const int n = int(current().value("hitboxes").toArray().size());
        emit editRequested("edit_article", {{"index", i}, {"ops", QJsonArray{QJsonObject{{"op", "insert"}, {"path", "hitboxes"}, {"at", n},
            {"value", QJsonObject{{"slot", n % 4}, {"damage", 5}, {"size", 3.0}, {"offset", QJsonArray{0, 0, 0}}, {"angle", 361},
            {"kbg", 50}, {"bkb", 20}, {"start", 1}, {"end", 0}}}}}}});
    });
    connect(removeBox_, &QPushButton::clicked, this, [this] {
        const int i = selectedArticle(), r = boxes_->currentRow(); if (i < 0 || r < 0) return;
        emit editRequested("edit_article", {{"index", i}, {"ops", QJsonArray{QJsonObject{{"op", "remove"}, {"path", "hitboxes"}, {"at", r}}}}});
    });
    connect(boxes_, &QTableWidget::itemChanged, this, [this](QTableWidgetItem *item) {
        if (feedback_) return;
        const int i = selectedArticle(); if (i < 0) return;
        const Col &c = kCols[item->column()]; bool ok = false; const double v = item->text().toDouble(&ok);
        if (!ok) { rebuildFields(); return; }
        const QString key = c.key; const int row = item->row();
        if (key.startsWith("offset/")) {
            const auto hb = current().value("hitboxes").toArray()[row].toObject();
            QJsonArray off = hb.value("offset").toArray(); while (off.size() < 3) off.append(0);
            off[key.mid(7).toInt()] = v;
            setOp(QString("hitboxes/#%1/offset").arg(row), off);
        } else setOp(QString("hitboxes/#%1/%2").arg(row).arg(key), QString(c.kind) == "i" ? QJsonValue(int(std::lround(v))) : QJsonValue(v));
    });
    connect(addSpawn_, &QPushButton::clicked, this, [this] { const int i = selectedArticle(); if (i >= 0) emit addSpawnRequested(i); });
    connect(removeSpawn_, &QPushButton::clicked, this, [this] {
        const int r = spawnList_->currentRow(); if (r < 0) return;
        emit editRequested("delete_spawn", {{"row", row_}, {"ordinal", spawnList_->item(r)->data(Qt::UserRole).toInt()}});
    });
    rebuildFields();
}
QStringList ProjectilesPanel::articleNames() const {
    QStringList out; for (const auto &a : articles_) out << a.toObject().value("name").toString(); return out;
}
int ProjectilesPanel::selectedArticle() const { const int r = list_->currentRow(); return r >= 0 && r < articles_.size() ? r : -1; }
void ProjectilesPanel::selectArticle(int index) { if (index >= 0 && index < list_->count()) list_->setCurrentRow(index); }
QJsonObject ProjectilesPanel::current() const { const int i = selectedArticle(); return i < 0 ? QJsonObject() : articles_[i].toObject(); }
void ProjectilesPanel::setOp(const QString &path, const QJsonValue &value) {
    const int i = selectedArticle(); if (i < 0) return;
    QString where = path; QJsonValue what = value;
    const auto parts = path.split('/');
    // velocity and spawn are [forward, up]: always write the whole pair (the key may be absent).
    if (parts.size() == 2 && (parts[0] == "velocity" || parts[0] == "spawn") && (parts[1] == "0" || parts[1] == "1")) {
        QJsonArray pair = current().value(parts[0]).toArray();
        while (pair.size() < 2) pair.append(0.0);
        pair[parts[1].toInt()] = value; where = parts[0]; what = pair;
    }
    emit editRequested("edit_article", {{"index", i}, {"ops", QJsonArray{QJsonObject{{"op", "set"}, {"path", where}, {"value", what}}}}});
}
void ProjectilesPanel::setData(const QJsonArray &articles, const QJsonArray &spawns, const QString &row) {
    const int keep = selectedArticle();
    articles_ = articles; spawns_ = spawns; row_ = row;
    feedback_ = true;
    {
        QSignalBlocker block(list_); list_->clear();
        for (const auto &v : articles_) {
            const auto a = v.toObject(); const auto vel = a.value("velocity").toArray();
            const double speed = std::hypot(vel.size() > 0 ? vel[0].toDouble() : 0, vel.size() > 1 ? vel[1].toDouble() : 0);
            list_->addItem(QString("%1   %2 f   speed %3").arg(a.value("name").toString()).arg(a.value("lifetime").toInt(60)).arg(speed, 0, 'f', 2));
        }
        if (!articles_.isEmpty()) list_->setCurrentRow(std::clamp(keep, 0, int(articles_.size()) - 1));
    }
    feedback_ = false;
    rebuildFields();
}
void ProjectilesPanel::rebuildFields() {
    feedback_ = true;
    const auto a = current(); const bool has = !a.isEmpty();
    form_->setEnabled(has); boxes_->setEnabled(has); addBox_->setEnabled(has); removeBox_->setEnabled(has);
    addSpawn_->setEnabled(has && !row_.isEmpty()); removeArticle_->setEnabled(!articles_.isEmpty());
    note_->setText(articles_.isEmpty() ? t("This project has no projectiles (articles).", "Este proyecto no tiene proyectiles.")
                                       : t("Edits go to the source; Rebuild + reload applies them in the game.", "Los cambios van al código fuente; reconstruye y recarga para verlos en el juego."));
    for (const auto &f : kFields) {
        const double v = leaf(a, f.path, f.def);
        if (auto *s = qobject_cast<QSpinBox *>(editors_.value(f.path))) { QSignalBlocker b(s); s->setValue(int(std::lround(v))); }
        else if (auto *d = qobject_cast<QDoubleSpinBox *>(editors_.value(f.path))) { QSignalBlocker b(d); d->setValue(v); }
    }
    for (const char *name : kDespawn) {
        auto *box = qobject_cast<QCheckBox *>(editors_.value(QString("despawn/") + name)); QSignalBlocker b(box);
        const auto d = a.value("despawn").toObject(); box->setChecked(d.contains(name) ? d[name].toBool(true) : true);
    }
    QSignalBlocker blockTable(boxes_);
    const auto hbs = a.value("hitboxes").toArray();
    boxes_->setRowCount(int(hbs.size()));
    for (int r = 0; r < hbs.size(); ++r) {
        const auto hb = hbs[r].toObject();
        for (int c = 0; c < int(std::size(kCols)); ++c) {
            double v = kCols[c].def;
            if (QString(kCols[c].key) == "slot") v = hb.contains("slot") ? hb["slot"].toDouble() : r % 4;
            else v = leaf(hb, kCols[c].key, kCols[c].def);
            auto *item = new QTableWidgetItem(number(v)); item->setTextAlignment(Qt::AlignCenter);
            boxes_->setItem(r, c, item);
        }
    }
    spawnList_->clear();
    for (const auto &v : spawns_) {
        const auto s = v.toObject(); if (s["row"].toString() != row_) continue;
        const int article = s["article"].toInt();
        const QString name = article >= 0 && article < articles_.size() ? articles_[article].toObject()["name"].toString() : QString("#%1").arg(article);
        auto *item = new QListWidgetItem(QString("frame %1   %2").arg(s["frame"].toInt()).arg(name));
        item->setData(Qt::UserRole, s["ordinal"].toInt()); spawnList_->addItem(item);
    }
    feedback_ = false;
}
} // namespace wb
