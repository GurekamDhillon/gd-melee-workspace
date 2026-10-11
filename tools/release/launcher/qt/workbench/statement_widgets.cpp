#include "statement_widgets.h"
#include "atlas.h"
#include "atlas_widgets.h"
#include "window.h"
#include <QComboBox>
#include <QGridLayout>
#include <QHelpEvent>
#include <QLabel>
#include <QLineEdit>
#include <QListWidget>
#include <QMouseEvent>
#include <QPainter>
#include <QSignalBlocker>
#include <QSpinBox>
#include <QToolTip>
#include <QVBoxLayout>
#include <algorithm>
#include <limits>

namespace wb {
using launcher::t;
namespace atlas = launcher::atlas;
namespace {
QString kindLabel(const QString &kind) {
    if (kind == "throw") return t("Throw damage", "Daño de lanzamiento");
    if (kind == "throw_release") return t("Throw release", "Liberar lanzamiento");
    if (kind == "body_state") return t("Whole body", "Cuerpo entero");
    if (kind == "hurtboxes_state") return t("All hurtboxes", "Todas las cajas de daño");
    if (kind == "hurtbox_state") return t("One bone", "Un hueso");
    return t("Throw flag", "Indicador de lanzamiento");
}
QString stateLabel(int state) {
    if (state == 0) return t("Normal", "Normal");
    if (state == 1) return t("Invincible", "Invencible");
    if (state == 2) return t("Intangible", "Intangible");
    return t("Unknown state %1", "Estado desconocido %1").arg(state);
}
bool hurtKind(const QString &kind) { return kind == "body_state" || kind == "hurtboxes_state" || kind == "hurtbox_state"; }
QString scopeKey(const QJsonObject &window) {
    const QString bone = window.contains("bone_identity") ? window["bone_identity"].toString() : window["bone"].toString();
    return window["kind"].toString() + ':' + bone;
}
QWidget *labelled(const QString &label, QWidget *field) {
    auto *wrap = new QWidget; auto *layout = new QVBoxLayout(wrap);
    layout->setContentsMargins(0, 0, 0, 0); layout->setSpacing(5);
    auto *caption = new QLabel(label); caption->setFont(atlas::font(atlas::Role::Cap14)); caption->setWordWrap(true);
    caption->setBuddy(field); layout->addWidget(caption); layout->addWidget(field);
    field->setAccessibleName(label); return wrap;
}
QLabel *note(const QString &text = {}) {
    auto *label = new QLabel(text); label->setWordWrap(true); label->setTextFormat(Qt::PlainText); return label;
}
QString statementNote(const QJsonObject &item) {
    return launcher::spanish && item.contains("note_es") ? item["note_es"].toString() : item["note"].toString();
}
} // namespace

StatementsPanel::StatementsPanel(QWidget *parent) : QWidget(parent) {
    installWheelGuard(); setObjectName("wbStatements");
    setAccessibleName(t("Throws and hurtboxes", "Lanzamientos y cajas de daño"));
    auto *layout = new QVBoxLayout(this); layout->setContentsMargins(16, 16, 16, 16); layout->setSpacing(14);
    auto *title = note(t("Throws and hurtboxes", "Lanzamientos y cajas de daño"));
    title->setFont(atlas::font(atlas::Role::Title)); layout->addWidget(title);
    list_ = new QListWidget; list_->setObjectName("wbStatementList"); list_->setMinimumHeight(120); list_->setMaximumHeight(220);
    list_->setAccessibleName(t("Move statements", "Instrucciones del movimiento")); layout->addWidget(list_);
    empty_ = note(t("This move has no throw or hurtbox statements. Add one at the current frame.",
                   "Este movimiento no tiene instrucciones de lanzamiento ni de cajas de daño. Añade una en el cuadro actual."));
    layout->addWidget(empty_);
    auto *addLine = new QVBoxLayout; kind_ = new QComboBox; kind_->setObjectName("wbStatementKind");
    for (const auto &k : {"throw", "throw_release", "body_state", "hurtboxes_state", "hurtbox_state"}) kind_->addItem(kindLabel(k), k);
    kind_->setAccessibleName(t("New statement", "Nueva instrucción")); addLine->addWidget(kind_);
    add_ = new AtlasButton(t("Add at cursor", "Añadir en el cursor")); add_->setObjectName("wbAddStatement"); addLine->addWidget(add_); layout->addLayout(addLine);
    form_ = new QWidget; auto *form = new QVBoxLayout(form_); form->setContentsMargins(0, 0, 0, 0); form->setSpacing(12);
    frame_ = new QSpinBox; frame_->setObjectName("wbStatement_frame"); frame_->setRange(-1, std::numeric_limits<int>::max());
    frame_->setMaximum(0x3ffffff); frame_->setSpecialValueText(t("Unknown", "Desconocido")); frame_->setKeyboardTracking(false); frame_->setFont(atlas::numberFont());
    form->addWidget(labelled(t("Statement frame", "Cuadro de la instrucción"), frame_));
    window_ = note(); window_->setObjectName("wbStatementWindow"); form->addWidget(window_);
    auto *grid = new QGridLayout; grid->setHorizontalSpacing(12); grid->setVerticalSpacing(12); grid->setColumnStretch(0, 1); grid->setColumnStretch(1, 1); form->addLayout(grid);
    const auto integer = [this, grid](const QString &key, const QString &label, int maximum, int r, int c) {
        auto *field = new QSpinBox; field->setRange(0, maximum); field->setKeyboardTracking(false); field->setFont(atlas::numberFont());
        field->setObjectName("wbStatement_" + key); fields_[key] = field;
        auto *wrap = labelled(label, field); rows_[key] = wrap; grid->addWidget(wrap, r, c);
        connect(field, &QSpinBox::editingFinished, this, [this, key, field] { submit(key, field->value()); });
    };
    integer("damage", t("Damage", "Daño"), 0x7fffff, 0, 0);
    integer("angle", t("Angle", "Ángulo"), 511, 0, 1);
    integer("kbg", t("Knockback growth", "Crecimiento de impulso"), 511, 1, 0);
    integer("bkb", t("Base knockback", "Impulso base"), 511, 1, 1);
    integer("fkb", t("Fixed knockback", "Impulso fijo"), 511, 2, 0);
    integer("element", t("Element", "Elemento"), 15, 2, 1);
    integer("sfx_severity", t("Sound severity", "Intensidad del sonido"), 7, 3, 0);
    integer("sfx_kind", t("Sound kind", "Tipo de sonido"), 15, 3, 1);
    slot_ = new QComboBox; slot_->setObjectName("wbStatement_slot");
    slot_->addItem(t("0 · Throw", "0 · Lanzamiento"), 0); slot_->addItem(t("1 · Catch", "1 · Agarre"), 1);
    rows_["slot"] = labelled(t("Throw record", "Registro de lanzamiento"), slot_); form->addWidget(rows_["slot"]);
    state_ = new QComboBox; state_->setObjectName("wbStatement_state");
    for (int i = 0; i < 3; ++i) state_->addItem(stateLabel(i), i);
    rows_["state"] = labelled(t("Hurtbox state", "Estado de la caja de daño"), state_); form->addWidget(rows_["state"]);
    bone_ = new QComboBox; bone_->setObjectName("wbStatement_bone"); bone_->setEditable(true); bone_->setInsertPolicy(QComboBox::NoInsert);
    rows_["bone"] = labelled(t("Bone", "Hueso"), bone_); form->addWidget(rows_["bone"]);
    auto *actions = new QHBoxLayout;
    restore_ = new AtlasButton(t("Restore normal at cursor", "Restaurar normal aquí")); restore_->setObjectName("wbRestoreHurtState");
    remove_ = new AtlasButton(t("Delete", "Borrar")); static_cast<AtlasButton *>(remove_)->setTone(AtlasButton::Danger); remove_->setObjectName("wbDeleteStatement");
    actions->addWidget(restore_, 1); actions->addWidget(remove_); form->addLayout(actions); layout->addWidget(form_);
    note_ = note(); note_->setObjectName("wbStatementNote"); layout->addWidget(note_);
    layout->addWidget(note(t("Invincible hurtboxes still register contact; intangible hurtboxes cannot be hit. Whole-body protection takes priority. A bone can override an all-hurtbox state. The lanes show authored scopes; add a normal state to end a window.",
                            "Las cajas invencibles aún registran contacto; las intangibles no reciben golpes. La protección del cuerpo tiene prioridad. Un hueso puede cambiar el estado general de las cajas. Las pistas muestran los ámbitos escritos; añade el estado normal para cerrar una ventana.")));
    standInChoice_ = new QComboBox; standInChoice_->setObjectName("wbThrowStandIn");
    layout->addWidget(labelled(t("Throw animation stand-in", "Sustituto de animación de lanzamiento"), standInChoice_));
    standInNote_ = note(); layout->addWidget(standInNote_); layout->addStretch();
    connect(list_, &QListWidget::currentRowChanged, this, [this] { refreshFields(); if (!feedback_) emit statementSelected(current()["ordinal"].toInt(-1)); });
    connect(frame_, &QSpinBox::editingFinished, this, [this] { submit("frame", frame_->value()); });
    connect(slot_, &QComboBox::activated, this, [this] { submit("slot", slot_->currentData().toInt()); });
    connect(state_, &QComboBox::activated, this, [this] { submit("state", state_->currentData().toInt()); });
    const auto editBone = [this] { submit("bone", bone_->currentText().trimmed()); };
    connect(bone_, &QComboBox::activated, this, editBone); connect(bone_->lineEdit(), &QLineEdit::editingFinished, this, editBone);
    connect(remove_, &QPushButton::clicked, this, [this] { if (current()["editable"].toBool()) emit editRequested("delete_statement", {{"row", row_}, {"ordinal", current()["ordinal"]}}); });
    connect(add_, &QPushButton::clicked, this, [this] {
        if (row_.isEmpty()) return;
        const QString kind = kind_->currentData().toString(); QJsonObject fields;
        if (kind == "throw") fields = {{"slot", 0}, {"damage", 8}, {"angle", 45}, {"kbg", 100}, {"bkb", 30}};
        if (hurtKind(kind)) fields["state"] = 2;
        if (kind == "hurtbox_state") fields["bone"] = bone_->count() ? bone_->itemText(0) : QString("0");
        emit addRequested(kind, fields);
    });
    connect(restore_, &QPushButton::clicked, this, [this] {
        const auto item = current(); const QString kind = item["kind"].toString();
        if (!hurtKind(kind) || !item["editable"].toBool()) return;
        QJsonObject fields{{"state", 0}};
        if (kind == "hurtbox_state") fields["bone"] = item["fields"].toObject()["bone"];
        emit addRequested(kind, fields);
    });
    connect(standInChoice_, &QComboBox::activated, this, [this] {
        const QString value = standInChoice_->currentData().toString();
        if (!feedback_ && standIn_["editable"].toBool() && value != standIn_["value"].toString()) emit editRequested("edit_throw_standin", {{"value", value}});
    });
    setData({}, {}, {}, {});
}
QJsonObject StatementsPanel::current() const {
    const int i = list_->currentRow(); return i >= 0 && i < statements_.size() ? statements_[i].toObject() : QJsonObject{};
}
void StatementsPanel::setData(const QString &row, const QJsonArray &statements, const QJsonObject &standIn, const QVector<RoleInfo> &roles) {
    bool sameRoles = roles.size() == roles_.size();
    for (int i = 0; sameRoles && i < roles.size(); ++i) sameRoles = roles[i].name == roles_[i].name;
    if (initialized_ && row == row_ && statements == statements_ && standIn == standIn_ && sameRoles) return;
    initialized_ = true; roles_ = roles;
    const int ordinal = row == row_ ? current()["ordinal"].toInt(-1) : -1;
    feedback_ = true; row_ = row; statements_ = statements; standIn_ = standIn;
    const QSignalBlocker block(list_); list_->clear();
    for (const auto &v : statements_) {
        const auto o = v.toObject(); const int frame = o["frame"].toInt(-1); const auto fields = o["fields"].toObject();
        QString label = kindLabel(o["kind"].toString());
        if (hurtKind(o["kind"].toString())) label += " · " + stateLabel(fields["state"].toInt(-1));
        if (o["kind"] == "hurtbox_state") label += " · " + fields["bone"].toString();
        if (o["kind"] == "throw") label += t(" · %1 damage", " · %1 de daño").arg(fields["damage"].toInt());
        auto *item = new QListWidgetItem((frame < 0 ? QString("?f") : QString::number(frame) + 'f') + "  " + label, list_);
        item->setData(Qt::UserRole, o["ordinal"].toInt()); item->setToolTip(statementNote(o));
    }
    bone_->clear(); for (const auto &role : roles) bone_->addItem('@' + role.name + '@');
    standInChoice_->clear(); for (const auto &v : standIn["choices"].toArray()) standInChoice_->addItem(v.toString(), v.toString());
    const QString value = standIn["value"].toString();
    if (standInChoice_->findData(value) < 0 && !value.isEmpty()) standInChoice_->addItem(value, value);
    standInChoice_->setCurrentIndex(standInChoice_->findData(value)); standInChoice_->setEnabled(standIn["editable"].toBool());
    standInNote_->setText(standIn["note"].toString() + '\n' + t("Fighter-wide. Rebuild to use this victim animation family in all four throws.", "Para todo el luchador. Reconstruye para usar esta familia de animaciones de víctima en los cuatro lanzamientos."));
    empty_->setVisible(statements_.isEmpty()); add_->setEnabled(!row_.isEmpty());
    int select = statements_.isEmpty() ? -1 : 0;
    for (int i = 0; i < statements_.size(); ++i) if (statements_[i].toObject()["ordinal"].toInt() == ordinal) select = i;
    list_->setCurrentRow(select); feedback_ = false; refreshFields();
}
void StatementsPanel::selectStatement(int ordinal) {
    for (int i = 0; i < list_->count(); ++i) if (list_->item(i)->data(Qt::UserRole).toInt() == ordinal) { list_->setCurrentRow(i); return; }
}
void StatementsPanel::refreshFields() {
    const auto item = current(); const QString kind = item["kind"].toString(); const auto values = item["fields"].toObject();
    feedback_ = true; form_->setVisible(!item.isEmpty()); const bool editable = item["editable"].toBool();
    frame_->setMaximum(std::max(0x3ffffff, item["frame"].toInt(-1)));
    frame_->setValue(item["frame"].toInt(-1)); frame_->setEnabled(editable && item["timing_editable"].toBool());
    for (auto it = fields_.cbegin(); it != fields_.cend(); ++it) {
        auto *field = static_cast<QSpinBox *>(it.value());
        // Out-of-range source is read-only: expand display, never silently show a clamped value.
        field->setMaximum(std::max(field->maximum(), values[it.key()].toInt())); field->setValue(values[it.key()].toInt()); field->setEnabled(editable);
        rows_[it.key()]->setVisible(kind == "throw");
    }
    slot_->setCurrentIndex(slot_->findData(values["slot"].toInt(-1))); slot_->setEnabled(editable); rows_["slot"]->setVisible(kind == "throw");
    state_->setCurrentIndex(state_->findData(values["state"].toInt(-1))); state_->setEnabled(editable); rows_["state"]->setVisible(hurtKind(kind));
    bone_->setEditText(values["bone"].toString()); bone_->setEnabled(editable); rows_["bone"]->setVisible(kind == "hurtbox_state");
    restore_->setVisible(hurtKind(kind)); restore_->setEnabled(editable && item["timing_editable"].toBool()); remove_->setEnabled(editable);
    const int end = item["end_frame"].toInt(-1);
    window_->setVisible(hurtKind(kind) && values["state"].toInt() != 0);
    window_->setText(end < 0 ? t("No known restore in this script", "Sin restauración conocida en este script") : t("Active until frame %1 (exclusive)", "Activo hasta el cuadro %1 (exclusivo)").arg(end));
    note_->setText(statementNote(item)); feedback_ = false;
}
void StatementsPanel::submit(const QString &key, const QJsonValue &value) {
    const auto item = current(); if (feedback_ || !isEnabled() || !item["editable"].toBool()) return;
    const bool timing = key == "frame";
    if (timing && (!item["timing_editable"].toBool() || value.toInt(-1) < 0)) return;
    const auto previous = timing ? item["frame"] : item["fields"].toObject()[key]; if (value == previous) return;
    QJsonObject args{{"row", row_}, {"ordinal", item["ordinal"]}};
    if (timing) args["frame"] = value; else args["fields"] = QJsonObject{{key, value}};
    emit editRequested("edit_statement", args);
}

HurtStateLanes::HurtStateLanes(QWidget *parent) : QWidget(parent) {
    setObjectName("wbHurtStateLanes"); setAccessibleName(t("Hurtbox state windows", "Ventanas de estado de cajas de daño"));
    setMouseTracking(true);
}
void HurtStateLanes::setTimeline(TimelineView *timeline) { timeline_ = timeline; update(); }
void HurtStateLanes::setWindows(const QJsonArray &windows) {
    windows_ = windows; lanes_.clear();
    for (const auto &v : windows_) { const QString key = scopeKey(v.toObject()); if (!lanes_.contains(key)) lanes_ << key; }
    setMinimumHeight(sizeHint().height()); updateGeometry(); update();
}
void HurtStateLanes::selectStatement(int ordinal) { selected_ = ordinal; update(); }
int HurtStateLanes::laneFor(const QJsonObject &o) const { return lanes_.indexOf(scopeKey(o)); }
QSize HurtStateLanes::sizeHint() const { return {200, std::max(1, int(lanes_.size())) * 28}; }
qreal HurtStateLanes::xOfFrame(int frame) const {
    if (!timeline_) return 0;
    return mapFromGlobal(timeline_->mapToGlobal(QPoint(qRound(timeline_->framePosition(frame)), 0))).x();
}
QRectF HurtStateLanes::windowRect(int ordinal) const {
    if (!timeline_) return {};
    for (const auto &v : windows_) {
        const auto o = v.toObject(); if (o["ordinal"].toInt() != ordinal) continue;
        const int start = o["start_frame"].toInt(), end = o["end_frame"].toInt(-1);
        const int boundary = end < 0 ? timeline_->frameCount() : end;
        if (start < 0 || boundary <= start) return {};
        const qreal left = xOfFrame(start), right = xOfFrame(boundary);
        return {left, qreal(laneFor(o) * 28 + 4), std::max<qreal>(1, right - left), 20};
    }
    return {};
}
QString HurtStateLanes::label(const QJsonObject &o) const {
    return o["kind"] == "hurtbox_state" ? t("Bone %1", "Hueso %1").arg(o["bone"].toString()) : kindLabel(o["kind"].toString());
}
void HurtStateLanes::paintEvent(QPaintEvent *) {
    QPainter p(this); p.fillRect(rect(), atlas::colour("ground2")); p.setFont(atlas::numberFont(11));
    if (windows_.isEmpty()) { p.setPen(atlas::colour("dim")); p.drawText(rect().adjusted(8, 0, -8, 0), Qt::AlignVCenter,
        t("No hurtbox state windows in this move", "Este movimiento no tiene ventanas de estado de cajas de daño")); return; }
    for (const auto &v : windows_) {
        const auto o = v.toObject(); const auto bar = windowRect(o["ordinal"].toInt()); if (bar.isEmpty()) continue;
        const int lane = laneFor(o); const qreal labelWidth = std::max<qreal>(0, xOfFrame(0) - 8);
        p.setPen(atlas::colour("muted"));
        p.drawText(QRectF(8, lane * 28, labelWidth, 28), Qt::AlignVCenter, p.fontMetrics().elidedText(label(o), Qt::ElideRight, int(labelWidth)));
        QColor colour = o["state"].toInt() == 2 ? QColor(91, 163, 231) : atlas::colour("jade");
        colour.setAlpha(o["ordinal"].toInt() == selected_ ? 255 : 180); p.fillRect(bar, colour);
        p.setPen(QPen(atlas::colour("ink"), 1, o["end_frame"].toInt(-1) < 0 ? Qt::DashLine : Qt::SolidLine)); p.drawRect(bar.adjusted(0, 0, -1, -1));
        p.setPen(atlas::colour("ink")); p.drawText(bar.adjusted(4, 0, -3, 0), Qt::AlignVCenter, p.fontMetrics().elidedText(stateLabel(o["state"].toInt()), Qt::ElideRight, std::max(0, int(bar.width() - 7))));
    }
}
void HurtStateLanes::mousePressEvent(QMouseEvent *e) {
    if (e->button() == Qt::LeftButton) for (const auto &v : windows_) {
        const int ordinal = v.toObject()["ordinal"].toInt();
        if (windowRect(ordinal).contains(e->position())) { selectStatement(ordinal); emit statementSelected(ordinal); e->accept(); return; }
    }
    QWidget::mousePressEvent(e);
}
bool HurtStateLanes::event(QEvent *e) {
    if (e->type() == QEvent::ToolTip) {
        const auto *help = static_cast<QHelpEvent *>(e);
        for (const auto &v : windows_) { const auto o = v.toObject(); if (!windowRect(o["ordinal"].toInt()).contains(help->pos())) continue;
            const int end = o["end_frame"].toInt(-1);
            QToolTip::showText(help->globalPos(), label(o) + " · " + stateLabel(o["state"].toInt()) + '\n' +
                (end < 0 ? t("From frame %1; no known restore", "Desde el cuadro %1; sin restauración conocida").arg(o["start_frame"].toInt()) :
                 t("Frames %1–%2 (end exclusive)", "Cuadros %1–%2 (final exclusivo)").arg(o["start_frame"].toInt()).arg(end)), this); return true;
        }
        QToolTip::hideText();
    }
    return QWidget::event(e);
}
} // namespace wb
