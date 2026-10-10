#include "panels.h"
#include "atlas.h"
#include "atlas_widgets.h"
#include "session.h"
#include "window.h"
#include <QAction>
#include <QComboBox>
#include <QDoubleSpinBox>
#include <QFrame>
#include <QGridLayout>
#include <QHeaderView>
#include <QHBoxLayout>
#include <QJsonDocument>
#include <QLabel>
#include <QLineEdit>
#include <QPainter>
#include <QPushButton>
#include <QScrollArea>
#include <QSignalBlocker>
#include <QSpinBox>
#include <QStyledItemDelegate>
#include <QToolButton>
#include <QVBoxLayout>
#include <algorithm>
#include <cmath>
#include <limits>

namespace wb {
using launcher::t;
namespace atlas = launcher::atlas;
namespace {
constexpr int RowRole = Qt::UserRole;
constexpr int OrdinalRole = Qt::UserRole + 1;
constexpr int GroupRole = Qt::UserRole + 2;
constexpr int GroupHeadingRole = Qt::UserRole + 3;
constexpr int BadgeRole = Qt::UserRole + 4;
constexpr int WarningRole = Qt::UserRole + 5;
constexpr int EditedRole = Qt::UserRole + 6;
constexpr int GroupedRole = Qt::UserRole + 7;
constexpr int CurrentMoveRole = Qt::UserRole + 8;

int groupIndex(const RowInfo &row) {
    const QString name = row.name.toLower(), tag = row.tag.toLower();
    if (tag.contains("special") || name.contains("special")) return 2;
    if (tag.contains("throw") || tag.contains("grab") || name.contains("throw") || name.contains("grab")) return 3;
    if (row.aerial || tag == "aerial" || name == "nair" || name == "fair" || name == "bair" || name == "uair" || name == "dair") return 1;
    if (tag == "jab" || tag == "tilt" || tag == "smash" || tag == "dash_attack" || tag == "ground" ||
        name.startsWith("jab") || name.contains("tilt") || name.contains("smash") || name == "dash_attack" || name == "dashattack") return 0;
    return 4;
}
QString groupText(int index) {
    switch (index) {
    case 0: return t("Ground attacks", "Ataques en tierra");
    case 1: return t("Aerials", "Ataques aéreos");
    case 2: return t("Specials", "Especiales");
    case 3: return t("Throws", "Lanzamientos");
    default: return t("Movement", "Movimiento");
    }
}
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
QLabel *caption(const QString &text) {
    auto *label = new QLabel(text);
    label->setTextFormat(Qt::PlainText);
    label->setFont(atlas::font(atlas::Role::Cap14));
    label->setWordWrap(true);
    label->setProperty("atlasLabel", true);
    auto palette = label->palette(); palette.setColor(QPalette::WindowText, atlas::colour("muted")); label->setPalette(palette);
    return label;
}
QWidget *labelled(const QString &label, QWidget *editor) {
    auto *field = new QWidget;
    auto *layout = new QVBoxLayout(field); layout->setContentsMargins(0, 0, 0, 0); layout->setSpacing(6);
    auto *heading = caption(label); heading->setBuddy(editor); layout->addWidget(heading); layout->addWidget(editor);
    editor->setMinimumWidth(0); editor->setMinimumHeight(36);
    editor->setSizePolicy(QSizePolicy::Ignored, QSizePolicy::Fixed);
    return field;
}
class MoveDelegate final : public QStyledItemDelegate {
public:
    explicit MoveDelegate(QObject *parent) : QStyledItemDelegate(parent) {}
    QSize sizeHint(const QStyleOptionViewItem &option, const QModelIndex &index) const override {
        if (!index.data(GroupedRole).toBool()) return QStyledItemDelegate::sizeHint(option, index);
        return {180, 36 + (index.data(GroupHeadingRole).toString().isEmpty() ? 0 : 28)};
    }
    void paint(QPainter *painter, const QStyleOptionViewItem &option, const QModelIndex &index) const override {
        if (!index.data(GroupedRole).toBool()) { QStyledItemDelegate::paint(painter, option, index); return; }
        painter->save();
        QRect row = option.rect;
        const QString heading = index.data(GroupHeadingRole).toString();
        if (!heading.isEmpty()) {
            painter->setFont(atlas::font(atlas::Role::Cap14)); painter->setPen(atlas::colour("dim"));
            painter->drawText(row.adjusted(2, 2, -2, 0).topLeft() + QPoint(0, 19), heading.toUpper());
            row.setTop(row.top() + 28);
        }
        const bool selected = option.state.testFlag(QStyle::State_Selected) || index.data(CurrentMoveRole).toBool();
        const bool hover = option.state.testFlag(QStyle::State_MouseOver);
        if (selected || hover) painter->fillRect(row, atlas::colour(selected ? "lift" : "plate2"));
        if (selected) painter->fillRect(QRect(row.left(), row.top(), 3, row.height()), atlas::colour("ember"));
        QRect content = row.adjusted(10, 0, -8, 0);
        const QString badge = index.data(BadgeRole).toString();
        painter->setFont(atlas::numberFont(12));
        const int badgeWidth = qMin(content.width() / 2, painter->fontMetrics().horizontalAdvance(badge));
        painter->setPen(atlas::colour(index.data(WarningRole).toInt() > 0 || index.data(EditedRole).toBool() ? "sun" : "dim"));
        painter->drawText(content, Qt::AlignRight | Qt::AlignVCenter, painter->fontMetrics().elidedText(badge, Qt::ElideRight, badgeWidth));
        content.setRight(content.right() - badgeWidth - (badge.isEmpty() ? 0 : 10));
        painter->setFont(atlas::font(atlas::Role::Row16)); painter->setPen(atlas::colour(selected ? "ivory" : "text2"));
        painter->drawText(content, Qt::AlignLeft | Qt::AlignVCenter,
                          painter->fontMetrics().elidedText(index.data(Qt::DisplayRole).toString(), Qt::ElideRight, qMax(0, content.width())));
        if (option.state.testFlag(QStyle::State_HasFocus)) {
            painter->setPen(atlas::colour("ember")); painter->drawRect(row.adjusted(0, 0, -1, -1));
        }
        painter->restore();
    }
};

QString attributeGroup(const QString &group) {
    if (group == "ground") return t("Ground movement", "Movimiento en tierra");
    if (group == "air") return t("Air movement", "Movimiento aéreo");
    if (group == "jump") return t("Jumps", "Saltos");
    if (group == "landing") return t("Landing", "Aterrizaje");
    if (group == "shield_ecb") return t("Shield and collision", "Escudo y colisión");
    if (group == "misc" || group.isEmpty()) return t("Other attributes", "Otros atributos");
    return group;
}
QString attributeUnit(const QString &unit) {
    if (unit == "count") return t("count", "cantidad");
    if (unit == "frames") return t("frames", "cuadros");
    if (unit == "Melee units/frame^2") return t("Melee units/frame²", "Unidades Melee/cuadro²");
    if (unit == "Melee units/frame") return t("Melee units/frame", "Unidades Melee/cuadro");
    if (unit == "Melee units") return t("Melee units", "Unidades Melee");
    if (unit == "weight") return t("weight", "peso");
    if (unit == "scalar") return {};
    return unit;
}
QJsonObject attributeMetadata(QJsonObject descriptor) {
    descriptor.remove("value"); descriptor.remove("source_file"); descriptor.remove("write_file"); return descriptor;
}
// An absent authored/default value is unknown, not zero. Keep that state separate
// from the spin box's numeric storage until the user types or steps a value.
class AttributeNumberField final : public NumberField {
public:
    explicit AttributeNumberField(QWidget *parent = nullptr) : NumberField(parent) {
        lineEdit()->setPlaceholderText(t("Not set", "Sin definir"));
        connect(lineEdit(), &QLineEdit::textEdited, this, [this](const QString &text) { unset_ = text.trimmed().isEmpty(); });
        connect(this, &QDoubleSpinBox::valueChanged, this, [this](double) { unset_ = false; });
    }
    QJsonValue draft() const {
        if (unset_ && cleanText().isEmpty()) return QJsonValue(QJsonValue::Null);
        bool valid = false; const double value = locale().toDouble(cleanText(), &valid);
        return valid && std::isfinite(value) ? QJsonValue(value) : QJsonValue(QJsonValue::Undefined);
    }
    void showValue(const QJsonValue &value) {
        const QSignalBlocker block(this);
        unset_ = value.isNull() || value.isUndefined();
        setValue(unset_ ? qBound(minimum(), 0.0, maximum()) : value.toDouble());
        if (unset_) lineEdit()->clear();
        else lineEdit()->setText(textFromValue(this->value()));
    }
    void restoreDraft(const QString &text, bool unset) { unset_ = unset; lineEdit()->setText(text); }
    bool isUnset() const { return unset_; }
protected:
    QString textFromValue(double value) const override { return unset_ ? QString{} : NumberField::textFromValue(value); }
    void stepBy(int steps) override { unset_ = false; NumberField::stepBy(steps); }
private:
    bool unset_ = false;
};
} // namespace

QString moveGroup(const RowInfo &row) { return groupText(groupIndex(row)); }

OutlinerPanel::OutlinerPanel(QWidget *parent) : QTreeWidget(parent) {
    setObjectName("wbOutliner"); setAccessibleName(t("Outliner", "Explorador"));
    setHeaderLabels({t("Move", "Movimiento"), t("Clip", "Clip")});
    setSelectionMode(QAbstractItemView::SingleSelection); setEditTriggers(QAbstractItemView::NoEditTriggers);
    setItemDelegate(new MoveDelegate(this)); setMouseTracking(true); setUniformRowHeights(false);
    connect(this, &QTreeWidget::currentItemChanged, this, [this](QTreeWidgetItem *item) {
        if (!item) return;
        const auto row = item->data(0, RowRole).toString();
        const int ordinal = item->data(0, OrdinalRole).toInt();
        updatePresentation();
        if (ordinal < 0) emit rowSelected(row); else emit hitboxSelected(row, ordinal);
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
    const bool hadRows = topLevelItemCount() > 0;
    QSet<QString> collapsed;
    for (int i = 0; i < topLevelItemCount(); ++i)
        if (!topLevelItem(i)->isExpanded()) collapsed.insert(topLevelItem(i)->data(0, RowRole).toString());
    rows_ = rows; hits_ = hits;
    auto ordered = rows_;
    if (grouped_) std::stable_sort(ordered.begin(), ordered.end(), [](const RowInfo &a, const RowInfo &b) { return groupIndex(a) < groupIndex(b); });
    const QSignalBlocker block(this); clear();
    for (const auto &row : ordered) {
        auto *item = new QTreeWidgetItem(this, {row.name, row.effectiveClip()});
        item->setData(0, RowRole, row.name); item->setData(0, OrdinalRole, -1); item->setData(0, GroupRole, groupIndex(row));
        for (const auto &hit : hits_.value(row.name)) {
            auto *child = new QTreeWidgetItem(item, {t("Hitbox %1 · %2", "Caja de golpe %1 · %2").arg(hit.ordinal).arg(hit.joint)});
            child->setData(0, RowRole, row.name); child->setData(0, OrdinalRole, hit.ordinal);
        }
        item->setExpanded(hadRows ? !collapsed.contains(row.name) : !grouped_);
    }
    setSelection(selectedRow, ordinal); updatePresentation();
}
void OutlinerPanel::setSelection(const QString &row, int ordinal) {
    const QSignalBlocker block(this);
    for (int i = 0; i < topLevelItemCount(); ++i) {
        auto *item = topLevelItem(i);
        if (item->data(0, RowRole).toString() != row) continue;
        for (int j = 0; j < item->childCount(); ++j) {
            auto *child = item->child(j);
            if (child->data(0, OrdinalRole).toInt() != ordinal) continue;
            item->setExpanded(true); setCurrentItem(child); updatePresentation(); return;
        }
        setCurrentItem(item); updatePresentation(); return;
    }
    setCurrentItem(nullptr); updatePresentation();
}
void OutlinerPanel::setGrouped(bool grouped) {
    if (grouped_ == grouped) return;
    grouped_ = grouped; setHeaderHidden(grouped); setColumnHidden(1, grouped); setIndentation(grouped ? 12 : 20);
    setRootIsDecorated(!grouped);
    header()->setSectionResizeMode(0, grouped ? QHeaderView::Stretch : QHeaderView::Interactive);
    setRows(rows_, hits_);
}
void OutlinerPanel::setFilter(const QString &filter) { filter_ = filter.trimmed(); updatePresentation(); }
void OutlinerPanel::setBadges(const QSet<QString> &edited, const QMap<QString, int> &warnings) {
    edited_ = edited; warnings_ = warnings; updatePresentation();
}
void OutlinerPanel::updatePresentation() {
    const QSignalBlocker block(this);
    int lastGroup = -1;
    const QString selectedRow = currentItem() ? currentItem()->data(0, RowRole).toString() : QString{};
    for (int i = 0; i < topLevelItemCount(); ++i) {
        auto *item = topLevelItem(i); const auto name = item->data(0, RowRole).toString();
        const auto found = std::find_if(rows_.cbegin(), rows_.cend(), [&](const RowInfo &row) { return row.name == name; });
        if (found == rows_.cend()) continue;
        const bool rowMatches = filter_.isEmpty() || name.contains(filter_, Qt::CaseInsensitive) ||
            found->effectiveClip().contains(filter_, Qt::CaseInsensitive) || found->tag.contains(filter_, Qt::CaseInsensitive);
        bool anyChild = false;
        for (int j = 0; j < item->childCount(); ++j) {
            auto *child = item->child(j); const bool visible = rowMatches || child->text(0).contains(filter_, Qt::CaseInsensitive);
            child->setHidden(!visible); anyChild |= visible;
        }
        item->setHidden(!rowMatches && !anyChild);
        QStringList badges;
        if (edited_.contains(name)) badges.append(t("edited", "editado"));
        const int warnings = qMax(0, warnings_.value(name));
        if (warnings > 0) badges.append((warnings == 1 ? t("%1 warning", "%1 advertencia") : t("%1 warnings", "%1 advertencias")).arg(warnings));
        const QString count = t("%1 hb", "%1 hb").arg(item->childCount());
        const QString badge = badges.isEmpty() ? count : badges.join(t(" · ", " · "));
        item->setData(0, BadgeRole, badge); item->setData(0, EditedRole, edited_.contains(name)); item->setData(0, WarningRole, warnings);
        item->setData(0, GroupedRole, grouped_); item->setData(0, CurrentMoveRole, selectedRow == name);
        const int group = item->data(0, GroupRole).toInt();
        item->setData(0, GroupHeadingRole, grouped_ && !item->isHidden() && group != lastGroup ? groupText(group) : QString{});
        if (!item->isHidden()) lastGroup = group;
        QStringList tooltip{name, found->effectiveClip(), count}; tooltip.append(badges); tooltip.removeAll(QString{});
        item->setToolTip(0, tooltip.join('\n')); item->setToolTip(1, found->effectiveClip());
    }
    doItemsLayout(); viewport()->update();
}

InspectorPanel::InspectorPanel(QWidget *parent) : QWidget(parent) {
    setObjectName("wbInspector"); setAccessibleName(t("Inspector", "Inspector"));
    auto *outer = new QVBoxLayout(this); outer->setContentsMargins(0, 0, 0, 0);
    auto *scroll = new QScrollArea; scroll->setWidgetResizable(true); scroll->setFrameShape(QFrame::NoFrame);
    scroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff); outer->addWidget(scroll);
    auto *body = new QWidget; body->setObjectName("wbInspectorBody"); scroll->setWidget(body);
    auto *shell = new QVBoxLayout(body); shell->setContentsMargins(16, 16, 16, 16); shell->setSpacing(14);
    auto *header = new QHBoxLayout;
    title_ = new QLabel; title_->setObjectName("wbHitboxTitle"); title_->setTextFormat(Qt::PlainText); title_->setWordWrap(true);
    title_->setFont(atlas::font(atlas::Role::Title)); header->addWidget(title_, 1);
    auto *remove = new AtlasButton(t("Delete", "Borrar")); remove->setObjectName("wbDeleteHitbox"); remove->setTone(AtlasButton::Tone::Danger);
    remove->setAccessibleName(t("Delete selected hitbox", "Borrar el hitbox seleccionado")); header->addWidget(remove); shell->addLayout(header); deleteButton_ = remove;
    form_ = new QWidget; form_->setObjectName("wbHitboxForm");
    auto *layout = new QVBoxLayout(form_); layout->setContentsMargins(0, 0, 0, 0); layout->setSpacing(14);
    shell->addWidget(form_);
    emptyCard_ = new QFrame; emptyCard_->setObjectName("wbHitboxEmpty");
    auto *emptyLayout = new QVBoxLayout(emptyCard_); emptyLayout->setContentsMargins(0, 4, 0, 0); emptyLayout->setSpacing(6);
    emptyTitle_ = caption({}); emptyTitle_->setObjectName("wbHitboxEmptyTitle");
    emptyBody_ = new QLabel; emptyBody_->setObjectName("wbHitboxEmptyBody"); emptyBody_->setWordWrap(true); emptyBody_->setTextFormat(Qt::PlainText);
    emptyLayout->addWidget(emptyTitle_); emptyLayout->addWidget(emptyBody_); shell->addWidget(emptyCard_); shell->addStretch();
    connect(remove, &QPushButton::clicked, this, [this] {
        if (!row_.isEmpty() && ordinal_ >= 0) emit editRequested("delete_hitbox", {{"row", row_}, {"ordinal", ordinal_}});
    });
    joint_ = new QComboBox; joint_->setObjectName("wbHitboxJoint"); joint_->setEditable(true); joint_->setInsertPolicy(QComboBox::NoInsert);
    auto *bone = joint_->lineEdit(); bone->setObjectName("wbHitbox_bone"); editors_.insert("bone", bone);
    bone->setAccessibleName(t("Bone", "Hueso")); joint_->setAccessibleName(t("Joint", "Articulación"));
    layout->addWidget(labelled(t("Joint", "Articulación"), joint_));
    connect(bone, &QLineEdit::editingFinished, this, [this, bone] { setField("bone", bone->text()); });
    connect(joint_, &QComboBox::activated, this, [this](int) { setField("bone", joint_->currentText()); });
    auto *grid = new QGridLayout; grid->setHorizontalSpacing(12); grid->setVerticalSpacing(12); grid->setColumnStretch(0, 1); grid->setColumnStretch(1, 1);
    layout->addLayout(grid);
    // Display precision follows the field (damage 1, size 2, offsets 3). A value with more precision than
    // the box shows is never rewritten just by tabbing through: an unchanged display commits nothing.
    const auto number = [this](const QString &key, const QString &label, double minimum, int decimals) {
        auto *edit = new NumberField; edit->setObjectName("wbHitbox_" + key); edit->setAccessibleName(label);
        edit->setDecimals(decimals); edit->setRange(minimum, 1e9); edit->setSingleStep(decimals <= 1 ? 0.5 : 0.1); edit->setKeyboardTracking(false);
        editors_.insert(key, edit);
        connect(edit, &QDoubleSpinBox::editingFinished, this, [this, edit, key] {
            const double stored = values_.value(key).toDouble();
            auto locale = edit->locale(); locale.setNumberOptions(locale.numberOptions() | QLocale::OmitGroupSeparator);
            if (edit->cleanText() == locale.toString(stored, 'f', edit->decimals())) return;
            setField(key, edit->value());
        });
        return labelled(label, edit);
    };
    const auto integer = [this](const QString &key, const QString &label, int minimum) {
        auto *edit = new QSpinBox; edit->setObjectName("wbHitbox_" + key); edit->setAccessibleName(label);
        edit->setFont(atlas::numberFont()); edit->setRange(minimum, std::numeric_limits<int>::max()); edit->setKeyboardTracking(false);
        if (key == "end_frame") edit->setSpecialValueText(t("Not cleared", "Sin limpiar"));
        editors_.insert(key, edit);
        connect(edit, &QSpinBox::editingFinished, this, [this, edit, key] {
            setField(key, key == "end_frame" && edit->value() >= 0 ? edit->value() + 1 : edit->value()); // shown as the last active frame
        });
        return labelled(label, edit);
    };
    grid->addWidget(integer("start_frame", t("First active frame", "Primer cuadro activo"), 0), 0, 0);
    grid->addWidget(integer("end_frame", t("Last active frame", "Último cuadro activo"), -1), 0, 1);
    grid->addWidget(number("damage", t("Damage", "Daño"), 0, 1), 1, 0);
    grid->addWidget(number("size", t("Size", "Tamaño"), 0, 2), 1, 1);
    grid->addWidget(integer("angle", t("Angle", "Ángulo"), std::numeric_limits<int>::min()), 2, 0);
    grid->addWidget(integer("kbg", t("Knockback growth", "Crecimiento de impulso"), 0), 2, 1);
    grid->addWidget(integer("bkb", t("Base knockback", "Impulso base"), 0), 3, 0);
    auto *element = new QComboBox; element->setObjectName("wbHitbox_element"); element->setAccessibleName(t("Element", "Elemento"));
    element->addItem(t("Normal", "Normal"), 0);
    for (int value = 1; value <= 31; ++value) element->addItem(t("Element %1", "Elemento %1").arg(value), value);
    element->setToolTip(t("Source element code (0–31)", "Código de elemento del script (0–31)")); editors_.insert("element", element);
    connect(element, &QComboBox::activated, this, [this, element](int) { setField("element", element->currentData()); });
    grid->addWidget(labelled(t("Element", "Elemento"), element), 3, 1);
    explanationCard_ = new QFrame; explanationCard_->setObjectName("wbHitExplanationCard");
    explanationCard_->setStyleSheet(QString("#wbHitExplanationCard { background: %1; border-left: 3px solid %2; }")
        .arg(atlas::colour("plate2").name(), atlas::colour("jade").name()));
    auto *explanationLayout = new QVBoxLayout(explanationCard_); explanationLayout->setContentsMargins(12, 12, 12, 12);
    auto *explanationTitle = caption(t("What this hit does", "Qué hace este golpe")); explanationLayout->addWidget(explanationTitle);
    explanation_ = new QLabel; explanation_->setObjectName("wbHitExplanation"); explanation_->setTextFormat(Qt::PlainText); explanation_->setWordWrap(true);
    explanationLayout->addWidget(explanation_); layout->addWidget(explanationCard_);
    checksTitle_ = caption({}); layout->addWidget(checksTitle_);
    checks_ = new QLabel; checks_->setObjectName("wbHitboxRowChecks"); checks_->setTextFormat(Qt::PlainText); checks_->setWordWrap(true); layout->addWidget(checks_);
    auto *detailsToggle = new QToolButton; detailsToggle->setText(t("Offsets and fixed knockback", "Desplazamientos e impulso fijo"));
    detailsToggle->setObjectName("wbHitboxDetailsToggle"); detailsToggle->setFont(atlas::font(atlas::Role::Cap14));
    detailsToggle->setCheckable(true); detailsToggle->setToolButtonStyle(Qt::ToolButtonTextBesideIcon); detailsToggle->setArrowType(Qt::RightArrow);
    layout->addWidget(detailsToggle);
    auto *details = new QWidget; details->setObjectName("wbHitboxDetails"); auto *detailGrid = new QGridLayout(details);
    detailGrid->setContentsMargins(0, 0, 0, 0); detailGrid->setHorizontalSpacing(12); detailGrid->setVerticalSpacing(12);
    detailGrid->setColumnStretch(0, 1); detailGrid->setColumnStretch(1, 1);
    detailGrid->addWidget(number("x", t("Offset X", "Desplazamiento X"), -1e9, 3), 0, 0);
    detailGrid->addWidget(number("y", t("Offset Y", "Desplazamiento Y"), -1e9, 3), 0, 1);
    detailGrid->addWidget(number("z", t("Offset Z", "Desplazamiento Z"), -1e9, 3), 1, 0);
    detailGrid->addWidget(integer("fkb", t("Fixed knockback", "Impulso fijo"), 0), 1, 1);
    layout->addWidget(details); details->hide();
    connect(detailsToggle, &QToolButton::toggled, this, [details, detailsToggle](bool open) { details->setVisible(open); detailsToggle->setArrowType(open ? Qt::DownArrow : Qt::RightArrow); });
    layout->addStretch();
    QWidget *previous = joint_;
    for (const auto &key : {"start_frame", "end_frame", "damage", "size", "angle", "kbg", "bkb", "element"}) {
        QWidget::setTabOrder(previous, editors_.value(key)); previous = editors_.value(key);
    }
    QWidget::setTabOrder(previous, detailsToggle); clear();
}
void InspectorPanel::showHitbox(const QString &row, const HitboxRef &h) {
    const QJsonObject values = {{"bone", h.joint}, {"damage", h.damage}, {"size", h.size}, {"x", h.x}, {"y", h.y}, {"z", h.z},
        {"angle", h.angle}, {"kbg", h.kbg}, {"fkb", h.fkb}, {"bkb", h.bkb}, {"element", h.element},
        {"start_frame", h.startFrame}, {"end_frame", h.endFrame}};
    if (row_ == row && ordinal_ == h.ordinal && values_ == values) return;
    const bool same = row_ == row && ordinal_ == h.ordinal;
    const QJsonObject previous = same ? values_ : QJsonObject{};
    if (!same) setExplanation({});
    if (row_ != row) rowChecked_ = false;
    row_ = row; ordinal_ = h.ordinal; values_ = values;
    title_->setText(t("HB%1", "HB%1").arg(h.ordinal));
    title_->setToolTip(t("%1 · Hitbox %2 (slot %3)", "%1 · Caja de golpe %2 (casilla %3)").arg(row).arg(h.ordinal).arg(h.slot));
    setEnabled(true); form_->show(); emptyCard_->hide(); deleteButton_->show(); updateEditors(previous); updateRowChecks();
}
void InspectorPanel::clear(bool rowHasHitboxes) {
    row_.clear(); ordinal_ = -1; values_ = {}; rowChecked_ = false; setEnabled(false);
    title_->setText(t("Select a hitbox", "Selecciona una caja de golpe")); title_->setToolTip({});
    emptyTitle_->setText(rowHasHitboxes ? t("Nothing selected", "Nada seleccionado") : t("No hitboxes on this move", "Este movimiento no tiene hitboxes"));
    emptyBody_->setText(rowHasHitboxes ? t("Click a hitbox bar on the timeline, or a hitbox under the move in the list.",
                                           "Pulsa una barra de hitbox en la línea de tiempo o un hitbox bajo el movimiento en la lista.")
                                       : t("Add one with + Add hitbox under the timeline to edit its damage, size and knockback here.",
                                           "Añade uno con + Añadir hitbox bajo la línea de tiempo para editar aquí su daño, tamaño e impulso."));
    form_->hide(); emptyCard_->show(); deleteButton_->hide();
    setExplanation({}); updateEditors(); updateRowChecks();
}
void InspectorPanel::setRoles(const QVector<RoleInfo> &roles) {
    auto *line = joint_->lineEdit(); const QString draft = line->text(); const int cursor = line->cursorPosition();
    const QSignalBlocker block(joint_), lineBlock(line); joint_->clear();
    QSet<QString> names;
    for (const auto &role : roles) if (!role.name.isEmpty() && !names.contains(role.name)) {
        names.insert(role.name); joint_->addItem(role.name, role.key); joint_->setItemData(joint_->count() - 1, role.group, Qt::ToolTipRole);
    }
    joint_->setEditText(draft); line->setCursorPosition(qMin(cursor, int(draft.size())));
}
void InspectorPanel::setRowChecks(const QVector<Problem> &problems, bool checked) { rowChecks_ = problems; rowChecked_ = checked; updateRowChecks(); }
void InspectorPanel::updateRowChecks() {
    checksTitle_->setText(row_.isEmpty() ? t("Row checks", "Comprobaciones del movimiento") : t("Checks for %1", "Comprobaciones de %1").arg(row_));
    QStringList messages;
    for (const auto &problem : rowChecks_) if (!row_.isEmpty() && problem.row == row_) messages.append(problem.message);
    const bool issues = !messages.isEmpty();
    if (!issues) messages.append(rowChecked_ ? t("No issues reported for this move", "No se han detectado problemas en este movimiento") :
                                           t("Checks have not been run for this move", "No se han ejecutado comprobaciones para este movimiento"));
    checks_->setText(messages.join('\n'));
    auto palette = checks_->palette(); palette.setColor(QPalette::WindowText, atlas::colour(issues ? "sun" : rowChecked_ ? "jade" : "muted")); checks_->setPalette(palette);
}
void InspectorPanel::setExplanation(const QString &text) {
    explanation_->setText(text); explanation_->setVisible(!text.trimmed().isEmpty()); explanationCard_->setVisible(!text.trimmed().isEmpty());
}
void InspectorPanel::updateEditors(const QJsonObject &previous) {
    for (auto it = editors_.cbegin(); it != editors_.cend(); ++it) {
        const auto value = values_.value(it.key()), before = previous.value(it.key());
        // A field differing from its last shown/submitted value contains a newer
        // draft. A queued reply must not replace it or an unfinished spin-box edit.
        if (!before.isUndefined() && before == value) continue;
        QJsonValue displayed;
        if (auto *line = qobject_cast<QLineEdit *>(it.value())) displayed = line->text();
        else if (auto *number = qobject_cast<QDoubleSpinBox *>(it.value())) {
            bool valid = false; const double draft = number->locale().toDouble(number->cleanText(), &valid);
            displayed = valid ? QJsonValue(draft) : QJsonValue(QJsonValue::Undefined);
        } else if (auto *integer = qobject_cast<QSpinBox *>(it.value())) {
            bool valid = false; const int draft = integer->locale().toInt(integer->cleanText(), &valid);
            if (integer->text() == integer->specialValueText()) displayed = integer->minimum();
            else displayed = valid ? QJsonValue(it.key() == "end_frame" ? draft + 1 : draft) : QJsonValue(QJsonValue::Undefined);
        } else if (auto *combo = qobject_cast<QComboBox *>(it.value())) displayed = combo->currentData().toInt();
        if (!before.isUndefined() && displayed != before) continue;
        const QSignalBlocker block(it.value());
        if (auto *line = qobject_cast<QLineEdit *>(it.value())) line->setText(value.toString());
        else if (auto *number = qobject_cast<QDoubleSpinBox *>(it.value())) number->setValue(value.toDouble());
        else if (auto *integer = qobject_cast<QSpinBox *>(it.value()))
            integer->setValue(it.key() == "end_frame" && value.toInt() > 0 ? value.toInt() - 1 : value.toInt());
        else if (auto *combo = qobject_cast<QComboBox *>(it.value())) combo->setCurrentIndex(combo->findData(value.toInt()));
    }
}
void InspectorPanel::setField(const QString &field, const QVariant &raw) {
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
        if (qobject_cast<QSpinBox *>(editors_.value(key)) || key == "element") {
            const double minimum = key == "angle" ? std::numeric_limits<int>::min() : 0;
            const double maximum = key == "element" ? 31 : std::numeric_limits<int>::max();
            if (key == "end_frame" && number == -1 && values_[key].toInt() == -1) return;
            if (std::trunc(number) != number || number < minimum || number > maximum) { updateEditors(); return; }
            value = int(number);
        } else {
            if ((key == "damage" || key == "size") && number < 0) { updateEditors(); return; }
            value = number;
        }
    }
    if (values_.value(key) == value) return;
    const auto previous = values_; values_.insert(key, value); updateEditors(previous);
    emit editRequested("edit_hitbox", {{"row", row_}, {"ordinal", ordinal_}, {key, value}});
}

AttributesPanel::AttributesPanel(QWidget *parent) : QWidget(parent) {
    setObjectName("wbAttributes"); setAccessibleName(t("Attributes", "Atributos"));
    auto *layout = new QVBoxLayout(this); layout->setContentsMargins(0, 0, 0, 0);
    auto *scroll = new QScrollArea; scroll->setWidgetResizable(true); scroll->setFrameShape(QFrame::NoFrame);
    scroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff); layout->addWidget(scroll);
    auto *body = new QWidget; body->setObjectName("wbAttributesBody"); scroll->setWidget(body);
    auto *bodyLayout = new QVBoxLayout(body); bodyLayout->setContentsMargins(16, 16, 16, 16); bodyLayout->setSpacing(14);
    auto *refresh = new AtlasButton(t("Refresh attributes", "Actualizar atributos")); refresh->setObjectName("wbRefreshAttributes"); bodyLayout->addWidget(refresh);
    connect(refresh, &QPushButton::clicked, this, &AttributesPanel::requestRefresh);
    fieldsLayout_ = new QVBoxLayout; fieldsLayout_->setSpacing(14); bodyLayout->addLayout(fieldsLayout_); bodyLayout->addStretch();
    auto *empty = caption(t("Select Attributes to load fighter values", "Selecciona Atributos para cargar los valores del luchador"));
    fieldsLayout_->addWidget(empty); headings_.append(empty);
}
void AttributesPanel::setAttributes(const QJsonArray &attributes) {
    feedback_ = true;
    while (auto *item = fieldsLayout_->takeAt(0)) delete item;
    for (auto *heading : headings_) delete heading;
    headings_.clear();
    QVector<QJsonObject> ordered;
    for (const auto &value : attributes) if (value.isObject() && !value.toObject()["name"].toString().isEmpty()) ordered.append(value.toObject());
    const QStringList order{"ground", "air", "jump", "landing", "shield_ecb", "misc"};
    const auto groupRank = [&order](const QJsonObject &descriptor) {
        const int at = order.indexOf(descriptor["group"].toString()); return at < 0 ? int(order.size()) : at;
    };
    std::stable_sort(ordered.begin(), ordered.end(), [&](const QJsonObject &a, const QJsonObject &b) { return groupRank(a) < groupRank(b); });
    QSet<QString> seen; QString previousGroup; bool first = true;
    for (const auto &descriptor : ordered) {
        const auto name = descriptor["name"].toString(); if (seen.contains(name)) continue; seen.insert(name);
        const auto group = descriptor["group"].toString();
        if (first || group != previousGroup) {
            auto *heading = caption(attributeGroup(group)); heading->setObjectName("wbAttributeGroup_" + group);
            fieldsLayout_->addWidget(heading); headings_.append(heading); previousGroup = group; first = false;
        }
        auto *edit = static_cast<AttributeNumberField *>(editors_.value(name));
        const bool added = edit == nullptr;
        if (added) {
            edit = new AttributeNumberField; edit->setObjectName("wbAttribute_" + name); edit->setAccessibleName(name);
            editors_.insert(name, edit);
            QString label = name; label.replace('_', ' '); if (!label.isEmpty()) label[0] = label.at(0).toUpper();
            auto *field = labelled(label, edit); fields_.insert(name, field);
            auto *unit = caption({}); unit->setObjectName("wbAttributeUnit_" + name); field->layout()->addWidget(unit);
            connect(edit, &QDoubleSpinBox::editingFinished, this, [this, name] { submit(name); });
        }
        const auto before = values_.value(name), current = descriptor.value("value");
        const auto draft = edit->draft(); const QString draftText = edit->text(); const bool draftUnset = edit->isUnset();
        const bool preserveDraft = !added && draft != before;
        const auto previousDescriptor = descriptors_.value(name);
        const bool metadataChanged = added || attributeMetadata(previousDescriptor) != attributeMetadata(descriptor);
        if (metadataChanged) {
            const QSignalBlocker block(edit);
            const auto range = descriptor["range"].toObject();
            const double limit = std::numeric_limits<double>::max();
            edit->setDecimals(descriptor["type"].toString() == "integer" ? 0 : 6);
            edit->setRange(range["minimum"].isDouble() ? range["minimum"].toDouble() : -limit,
                           range["maximum"].isDouble() ? range["maximum"].toDouble() : limit);
            edit->setSingleStep(descriptor["type"].toString() == "integer" ? 1 : 0.1); edit->setKeyboardTracking(false);
            if (preserveDraft) edit->restoreDraft(draftText, draftUnset);
        }
        if (!preserveDraft && (added || before != current || metadataChanged)) edit->showValue(current);
        values_.insert(name, current); descriptors_.insert(name, descriptor);
        const auto unit = attributeUnit(descriptor["unit"].toString());
        auto *unitLabel = fields_[name]->findChild<QLabel *>("wbAttributeUnit_" + name); unitLabel->setText(unit); unitLabel->setVisible(!unit.isEmpty());
        QStringList tooltip{name, descriptor["description"].toString()};
        if (current.isNull() || current.isUndefined()) tooltip.append(t("No authored or generated default is available", "No hay un valor inicial escrito o generado disponible"));
        tooltip.removeAll(QString{}); edit->setToolTip(tooltip.join('\n'));
        fieldsLayout_->addWidget(fields_.value(name));
    }
    for (const auto &name : fields_.keys()) if (!seen.contains(name)) {
        editors_.remove(name); descriptors_.remove(name); values_.remove(name); delete fields_.take(name);
    }
    if (ordered.isEmpty()) {
        auto *empty = caption(t("No fighter attributes are available", "No hay atributos de luchador disponibles"));
        fieldsLayout_->addWidget(empty); headings_.append(empty);
    }
    feedback_ = false;
}
void AttributesPanel::submit(const QString &name) {
    if (feedback_ || !editors_.contains(name)) return;
    auto *edit = static_cast<AttributeNumberField *>(editors_.value(name));
    const auto value = edit->draft(); if (!value.isDouble()) return;
    const double number = value.toDouble(); const auto descriptor = descriptors_.value(name), range = descriptor["range"].toObject();
    if (!std::isfinite(number) || (descriptor["type"].toString() == "integer" && std::trunc(number) != number) ||
        (range["minimum"].isDouble() && number < range["minimum"].toDouble()) ||
        (range["maximum"].isDouble() && number > range["maximum"].toDouble()) || values_.value(name) == value) return;
    values_.insert(name, value);
    emit editRequested("edit_attribute", {{"name", name}, {"value", value}});
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
