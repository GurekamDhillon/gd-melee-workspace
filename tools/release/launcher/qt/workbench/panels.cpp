#include "panels.h"
#include "session.h"
#include "window.h"
#include <QAction>
#include <QDoubleSpinBox>
#include <QFormLayout>
#include <QHeaderView>
#include <QHBoxLayout>
#include <QJsonDocument>
#include <QLabel>
#include <QLineEdit>
#include <QPushButton>
#include <QSet>
#include <QSignalBlocker>
#include <QSpinBox>
#include <QVBoxLayout>
#include <cmath>
#include <limits>

namespace wb {
using launcher::t;
namespace {
constexpr int RowRole = Qt::UserRole;
constexpr int OrdinalRole = Qt::UserRole + 1;
QString stateText(const QString &state) {
    if (state == "proposed") return t("Proposed", "Propuesto");
    if (state == "applied") return t("Applied", "Aplicado");
    if (state == "undone") return t("Undone", "Deshecho");
    if (state == "rejected") return t("Rejected", "Rechazado");
    return state;
}
QString valueText(const QJsonValue &value) {
    if (value.isString()) return value.toString();
    if (value.isNull() || value.isUndefined()) return {};
    if (value.isArray()) return QString::fromUtf8(QJsonDocument(value.toArray()).toJson(QJsonDocument::Compact));
    if (value.isObject()) return QString::fromUtf8(QJsonDocument(value.toObject()).toJson(QJsonDocument::Compact));
    return value.toVariant().toString();
}
void readOnlyTable(QTableWidget *table) {
    table->setEditTriggers(QAbstractItemView::NoEditTriggers);
    table->setSelectionBehavior(QAbstractItemView::SelectRows);
    table->setSelectionMode(QAbstractItemView::SingleSelection);
    table->verticalHeader()->hide();
    table->horizontalHeader()->setSectionResizeMode(QHeaderView::ResizeToContents);
    table->setWordWrap(false);
}
}

OutlinerPanel::OutlinerPanel(QWidget *parent) : QTreeWidget(parent) {
    setObjectName("wbOutliner"); setAccessibleName(t("Outliner", "Explorador"));
    setHeaderLabels({t("Move", "Movimiento"), t("Clip", "Clip")});
    setSelectionMode(QAbstractItemView::SingleSelection);
    setEditTriggers(QAbstractItemView::NoEditTriggers);
    connect(this, &QTreeWidget::currentItemChanged, this, [this](QTreeWidgetItem *item) {
        if (!item) return;
        const auto row = item->data(0, RowRole).toString();
        const int ordinal = item->data(0, OrdinalRole).toInt();
        if (ordinal < 0) emit rowSelected(row);
        else emit hitboxSelected(row, ordinal);
    });
}
void OutlinerPanel::setSession(Session &session) { session_ = &session; }
void OutlinerPanel::refresh() {
    if (!session_) return;
    const auto rows = session_->data().rows();
    QMap<QString, QVector<HitboxRef>> hits;
    for (const auto &row : rows) hits.insert(row.name, session_->data().hitboxes(row.name));
    setRows(rows, hits);
}
void OutlinerPanel::setRows(const QVector<RowInfo> &rows, const QMap<QString, QVector<HitboxRef>> &hits) {
    const auto *selected = currentItem();
    const QString selectedRow = selected ? selected->data(0, RowRole).toString() : QString();
    const int ordinal = selected ? selected->data(0, OrdinalRole).toInt() : -1;
    QSet<QString> collapsed;
    for (int i = 0; i < topLevelItemCount(); ++i)
        if (!topLevelItem(i)->isExpanded()) collapsed.insert(topLevelItem(i)->data(0, RowRole).toString());
    const QSignalBlocker block(this);
    clear();
    for (const auto &row : rows) {
        auto *item = new QTreeWidgetItem(this, {row.name, row.clip});
        item->setData(0, RowRole, row.name); item->setData(0, OrdinalRole, -1);
        for (const auto &hit : hits.value(row.name)) {
            auto *child = new QTreeWidgetItem(item, {t("Hitbox %1 · %2", "Caja de golpe %1 · %2").arg(hit.ordinal).arg(hit.joint)});
            child->setData(0, RowRole, row.name); child->setData(0, OrdinalRole, hit.ordinal);
        }
        item->setExpanded(!collapsed.contains(row.name));
    }
    setSelection(selectedRow, ordinal);
}
void OutlinerPanel::setSelection(const QString &row, int ordinal) {
    const QSignalBlocker block(this);
    for (int i = 0; i < topLevelItemCount(); ++i) {
        auto *item = topLevelItem(i);
        if (item->data(0, RowRole).toString() != row) continue;
        for (int j = 0; j < item->childCount(); ++j) {
            auto *child = item->child(j);
            if (child->data(0, OrdinalRole).toInt() != ordinal) continue;
            item->setExpanded(true); setCurrentItem(child); return;
        }
        setCurrentItem(item); return;
    }
    setCurrentItem(nullptr);
}

InspectorPanel::InspectorPanel(QWidget *parent) : QWidget(parent) {
    setObjectName("wbInspector"); setAccessibleName(t("Inspector", "Inspector"));
    auto *layout = new QVBoxLayout(this);
    title_ = new QLabel; title_->setTextFormat(Qt::PlainText); title_->setWordWrap(true); layout->addWidget(title_);
    auto *form = new QFormLayout; layout->addLayout(form);
    auto *bone = new QLineEdit; bone->setObjectName("wbHitbox_bone"); editors_.insert("bone", bone);
    bone->setAccessibleName(t("Bone", "Hueso")); form->addRow(t("Bone", "Hueso"), bone);
    connect(bone, &QLineEdit::editingFinished, this, [this, bone] { setField("bone", bone->text()); });
    const auto number = [this, form](const QString &key, const QString &label, double minimum) {
        auto *edit = new QDoubleSpinBox; edit->setObjectName("wbHitbox_" + key); edit->setAccessibleName(label);
        edit->setDecimals(6); edit->setRange(minimum, 1e9); edit->setSingleStep(0.1); edit->setKeyboardTracking(false);
        editors_.insert(key, edit); form->addRow(label, edit);
        connect(edit, &QDoubleSpinBox::editingFinished, this, [this, edit, key] { setField(key, edit->value()); });
    };
    number("damage", t("Damage", "Daño"), 0); number("size", t("Size", "Tamaño"), 0);
    number("x", t("Offset X", "Desplazamiento X"), -1e9);
    number("y", t("Offset Y", "Desplazamiento Y"), -1e9);
    number("z", t("Offset Z", "Desplazamiento Z"), -1e9);
    const auto integer = [this, form](const QString &key, const QString &label, int minimum) {
        auto *edit = new QSpinBox; edit->setObjectName("wbHitbox_" + key); edit->setAccessibleName(label);
        edit->setRange(minimum, std::numeric_limits<int>::max()); edit->setKeyboardTracking(false);
        if (key == "end_frame") edit->setSpecialValueText(t("Not cleared", "Sin limpiar"));
        editors_.insert(key, edit); form->addRow(label, edit);
        connect(edit, &QSpinBox::editingFinished, this, [this, edit, key] { setField(key, edit->value()); });
    };
    integer("angle", t("Angle", "Ángulo"), std::numeric_limits<int>::min());
    integer("kbg", t("Knockback growth", "Crecimiento de impulso"), 0);
    integer("fkb", t("Fixed knockback", "Impulso fijo"), 0);
    integer("bkb", t("Base knockback", "Impulso base"), 0);
    integer("start_frame", t("First active frame", "Primer cuadro activo"), 0);
    integer("end_frame", t("End frame (exclusive)", "Cuadro final (exclusivo)"), -1);
    layout->addStretch(); clear();
}
void InspectorPanel::showHitbox(const QString &row, const HitboxRef &h) {
    const QJsonObject values = {{"bone", h.joint}, {"damage", h.damage}, {"size", h.size}, {"x", h.x}, {"y", h.y}, {"z", h.z},
               {"angle", h.angle}, {"kbg", h.kbg}, {"fkb", h.fkb}, {"bkb", h.bkb},
               {"start_frame", h.startFrame}, {"end_frame", h.endFrame}};
    if (row_ == row && ordinal_ == h.ordinal && values_ == values) return;
    const QJsonObject previous = row_ == row && ordinal_ == h.ordinal ? values_ : QJsonObject{};
    row_ = row; ordinal_ = h.ordinal; values_ = values;
    title_->setText(t("%1 · Hitbox %2 (slot %3)", "%1 · Caja de golpe %2 (casilla %3)").arg(row).arg(h.ordinal).arg(h.slot));
    setEnabled(true); updateEditors(previous);
}
void InspectorPanel::clear() {
    row_.clear(); ordinal_ = -1; values_ = {}; setEnabled(false);
    title_->setText(t("Select a hitbox", "Selecciona una caja de golpe"));
    updateEditors();
}
void InspectorPanel::updateEditors(const QJsonObject &previous) {
    for (auto it = editors_.cbegin(); it != editors_.cend(); ++it) {
        const auto value = values_.value(it.key());
        const auto before = previous.value(it.key());
        // Feedback only changes fields whose source value changed. An editor
        // differing from the last shown/submitted value holds a newer draft:
        // retain it even if a queued command returns an older snapshot.
        if (!before.isUndefined() && before == value) continue;
        QJsonValue displayed;
        if (auto *line = qobject_cast<QLineEdit *>(it.value())) displayed = line->text();
        else if (auto *number = qobject_cast<QDoubleSpinBox *>(it.value())) {
            bool valid = false; const double draft = number->locale().toDouble(number->cleanText(), &valid);
            displayed = valid ? QJsonValue(draft) : QJsonValue(QJsonValue::Undefined);
        } else if (auto *integer = qobject_cast<QSpinBox *>(it.value())) {
            bool valid = false; const int draft = integer->locale().toInt(integer->cleanText(), &valid);
            if (integer->text() == integer->specialValueText()) displayed = integer->minimum();
            else displayed = valid ? QJsonValue(draft) : QJsonValue(QJsonValue::Undefined);
        }
        if (!before.isUndefined() && displayed != before) continue;
        const QSignalBlocker block(it.value());
        if (auto *line = qobject_cast<QLineEdit *>(it.value())) line->setText(value.toString());
        else if (auto *number = qobject_cast<QDoubleSpinBox *>(it.value())) number->setValue(value.toDouble());
        else if (auto *integer = qobject_cast<QSpinBox *>(it.value())) integer->setValue(value.toInt());
    }
}
void InspectorPanel::setField(const QString &field, const QVariant &raw) {
    // Source member names are accepted by the hook; the wire uses Task 10 names.
    const QString key = field == "joint" ? QString("bone") : field == "startFrame" ? QString("start_frame") :
                        field == "endFrame" ? QString("end_frame") : field;
    if (ordinal_ < 0 || row_.isEmpty() || !values_.contains(key)) return;
    QJsonValue value;
    if (key == "bone") {
        const QString bone = raw.toString().trimmed();
        if (bone.isEmpty()) { updateEditors(); return; }
        value = bone;
    } else {
        bool valid = false; const double number = raw.toDouble(&valid);
        if (!valid || !std::isfinite(number)) { updateEditors(); return; }
        if (qobject_cast<QSpinBox *>(editors_.value(key))) {
            const double minimum = key == "angle" ? std::numeric_limits<int>::min() : 0;
            // -1 denotes an existing, never-cleared hitbox, not a valid frame edit.
            if (key == "end_frame" && number == -1 && values_[key].toInt() == -1) return;
            if (std::trunc(number) != number || number < minimum || number > std::numeric_limits<int>::max()) {
                updateEditors(); return;
            }
            value = int(number);
        } else {
            if ((key == "damage" || key == "size") && number < 0) { updateEditors(); return; }
            value = number;
        }
    }
    if (values_.value(key) == value) return;
    const auto previous = values_;
    values_.insert(key, value); updateEditors(previous);
    emit editRequested("edit_hitbox", {{"row", row_}, {"ordinal", ordinal_}, {key, value}});
}

ProblemsPanel::ProblemsPanel(QWidget *parent) : QListWidget(parent) {
    setObjectName("wbProblems"); setAccessibleName(t("Problems", "Problemas"));
    connect(this, &QListWidget::itemActivated, this, [this](QListWidgetItem *item) {
        if (item) emit problemActivated(item->data(RowRole).toString(), item->data(OrdinalRole).toInt());
    });
}
void ProblemsPanel::setProblems(const QVector<Problem> &problems) {
    const QSignalBlocker block(this); clear();
    for (const auto &problem : problems) {
        auto *item = new QListWidgetItem(t("%1: %2", "%1: %2").arg(problem.row, problem.message), this);
        item->setData(RowRole, problem.row); item->setData(OrdinalRole, problem.ordinal);
        item->setToolTip(t("%1 · %2", "%1 · %2").arg(problem.kind, problem.message));
    }
}

ClipBrowserPanel::ClipBrowserPanel(QWidget *parent) : QListWidget(parent) {
    setObjectName("wbClips"); setAccessibleName(t("Clips", "Clips"));
    setSelectionMode(QAbstractItemView::SingleSelection); setContextMenuPolicy(Qt::ActionsContextMenu);
    preview_ = new QAction(t("Preview", "Vista previa"), this); assign_ = new QAction(t("Assign to move", "Asignar al movimiento"), this);
    addAction(preview_); addAction(assign_);
    connect(preview_, &QAction::triggered, this, &ClipBrowserPanel::previewCurrent);
    connect(assign_, &QAction::triggered, this, &ClipBrowserPanel::assignCurrent);
    connect(this, &QListWidget::itemActivated, this, [this](QListWidgetItem *) { previewCurrent(); });
    connect(this, &QListWidget::currentItemChanged, this, [this](QListWidgetItem *item) {
        preview_->setEnabled(item != nullptr); assign_->setEnabled(item != nullptr);
    });
    preview_->setEnabled(false); assign_->setEnabled(false);
}
void ClipBrowserPanel::setClips(const QVector<ClipInfo> &clips, const QString &current) {
    QString selected = currentItem() ? currentItem()->data(Qt::UserRole).toString() : QString();
    if (selected.isEmpty() || current != current_) selected = current;
    current_ = current;
    const QSignalBlocker block(this); clear();
    for (const auto &clip : clips) {
        const QString label = clip.name == current ? t("%1 · %2 frames · current", "%1 · %2 cuadros · actual") :
                                                    t("%1 · %2 frames", "%1 · %2 cuadros");
        auto *item = new QListWidgetItem(label.arg(clip.name).arg(clip.frames), this);
        item->setData(Qt::UserRole, clip.name);
        if (clip.name == current) { auto font = item->font(); font.setBold(true); item->setFont(font); }
        if (clip.name == selected) setCurrentItem(item);
    }
    preview_->setEnabled(currentItem() != nullptr); assign_->setEnabled(currentItem() != nullptr);
}
void ClipBrowserPanel::previewCurrent() {
    if (auto *item = currentItem()) emit previewRequested(item->data(Qt::UserRole).toString());
}
void ClipBrowserPanel::assignCurrent() {
    if (auto *item = currentItem()) emit assignRequested(item->data(Qt::UserRole).toString());
}

FidelityPanel::FidelityPanel(QWidget *parent) : QTableWidget(parent) {
    setObjectName("wbFidelity"); setAccessibleName(t("Fidelity", "Fidelidad"));
    setColumnCount(2); setHorizontalHeaderLabels({t("Field", "Campo"), t("Value", "Valor")}); readOnlyTable(this);
    horizontalHeader()->setSectionResizeMode(1, QHeaderView::Stretch);
}
void FidelityPanel::setFidelity(const QJsonArray &entries, const QString &row, const QVector<int> &motions) {
    const QSignalBlocker block(this); clearContents(); clearSpans(); setRowCount(0);
    const QVector<QPair<QString, QString>> fields{
        {"row", t("Move", "Movimiento")}, {"motion", t("Motion", "Animación")},
        {"status", t("Status", "Estado")}, {"clip", t("Clip", "Clip")},
        {"source", t("Source", "Origen")}, {"source_clip", t("Source clip", "Clip de origen")},
        {"how", t("Method", "Método")}, {"deviation", t("Deviation", "Desviación")},
        {"checked", t("Checked", "Comprobado")}};
    for (const auto &value : entries) {
        const auto entry = value.toObject();
        if (row.isEmpty() || (entry["row"].toString().compare(row, Qt::CaseInsensitive) != 0 &&
                             !(entry["motion"].isDouble() && motions.contains(entry["motion"].toInt())))) continue;
        for (const auto &field : fields) if (entry.contains(field.first)) {
            const int index = rowCount(); insertRow(index);
            setItem(index, 0, new QTableWidgetItem(field.second));
            auto *item = new QTableWidgetItem(valueText(entry[field.first])); item->setToolTip(item->text()); setItem(index, 1, item);
        }
    }
    if (!rowCount()) {
        setRowCount(1); setItem(0, 0, new QTableWidgetItem(t("No fidelity entry for this move", "No hay datos de fidelidad para este movimiento")));
        setSpan(0, 0, 1, 2);
    }
}

ReviewPanel::ReviewPanel(QWidget *parent) : QTableWidget(parent) {
    setObjectName("wbReview"); setAccessibleName(t("History and review", "Historial y revisión"));
    setColumnCount(6); setHorizontalHeaderLabels({t("ID", "ID"), t("Author", "Autor"), t("Command", "Comando"),
        t("Summary", "Resumen"), t("Status", "Estado"), t("Actions", "Acciones")});
    readOnlyTable(this); horizontalHeader()->setSectionResizeMode(3, QHeaderView::Stretch);
    setContextMenuPolicy(Qt::ActionsContextMenu);
    auto *undo = new QAction(t("Undo", "Deshacer"), this); auto *redo = new QAction(t("Redo", "Rehacer"), this);
    addAction(undo); addAction(redo);
    connect(undo, &QAction::triggered, this, &ReviewPanel::undoRequested);
    connect(redo, &QAction::triggered, this, &ReviewPanel::redoRequested);
}
void ReviewPanel::setHistory(const QVector<HistoryEntry> &entries) {
    const int previousId = currentRow() >= 0 && currentRow() < entries_.size() ? entries_[currentRow()].id : -1;
    const QSignalBlocker block(this); setRowCount(0); entries_.clear();
    for (const auto &source : entries) {
        HistoryEntry entry; entry.id = source.id; entry.author = source.author; entry.command = source.command;
        entry.summary = source.summary; entry.state = source.state; entries_.append(entry);
        const int row = rowCount(); insertRow(row);
        const QString author = entry.author == "agent" ? t("agent", "agente") :
                               entry.author == "human" ? t("you", "tú") : entry.author;
        const QStringList cells{QString::number(entry.id), author, entry.command, entry.summary, stateText(entry.state)};
        for (int column = 0; column < cells.size(); ++column) {
            auto *item = new QTableWidgetItem(cells[column]); item->setToolTip(cells[column]); setItem(row, column, item);
        }
        auto *actions = new QWidget; auto *layout = new QHBoxLayout(actions); layout->setContentsMargins(2, 2, 2, 2);
        auto *accept = new QPushButton(t("Accept", "Aceptar")); auto *reject = new QPushButton(t("Reject", "Rechazar"));
        accept->setObjectName("wbAccept_" + QString::number(entry.id)); reject->setObjectName("wbReject_" + QString::number(entry.id));
        accept->setEnabled(actionsEnabled(row)); reject->setEnabled(actionsEnabled(row));
        layout->addWidget(accept); layout->addWidget(reject); setCellWidget(row, 5, actions);
        connect(accept, &QPushButton::clicked, this, [this, id = entry.id] { requestProposal(id, true); });
        connect(reject, &QPushButton::clicked, this, [this, id = entry.id] { requestProposal(id, false); });
        setRowHeight(row, actions->sizeHint().height());
        if (entry.id == previousId) selectRow(row);
    }
}
bool ReviewPanel::actionsEnabled(int row) const {
    return row >= 0 && row < entries_.size() && entries_[row].state == "proposed";
}
void ReviewPanel::requestProposal(int id, bool accepting) {
    for (const auto &entry : entries_) if (entry.id == id && entry.state == "proposed") {
        if (accepting) emit acceptRequested(id); else emit rejectRequested(id);
        return;
    }
}
void ReviewPanel::accept(int row) { if (actionsEnabled(row)) requestProposal(entries_[row].id, true); }
void ReviewPanel::reject(int row) { if (actionsEnabled(row)) requestProposal(entries_[row].id, false); }
} // namespace wb
